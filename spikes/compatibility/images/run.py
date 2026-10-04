#!/usr/bin/env python3
"""Build and exercise disposable OCI candidates with immutable base references."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
import urllib.parse
import uuid

DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
EXCLUDED = {"vendor", "node_modules", ".venv", "__pycache__", ".cache", ".pytest_cache",
            ".mypy_cache", ".ruff_cache", ".import_linter_cache", "test-results", "build"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_lock(lock: dict, candidates: dict, candidate_sha: str) -> None:
    if lock.get("schema_version") != 1 or lock.get("candidate_sha256") != candidate_sha:
        raise ValueError("Image lock does not describe the current candidate manifest")
    if lock.get("platform") != candidates["platform"]:
        raise ValueError("Image lock selects a different platform")
    if set(lock.get("images", {})) != set(candidates["images"]):
        raise ValueError("Image lock has missing or unexpected image entries")
    for name, candidate in candidates["images"].items():
        item = lock["images"][name]
        repository = candidate.rsplit(":", 1)[0]
        if item.get("candidate") != candidate or not DIGEST.fullmatch(item.get("digest", "")):
            raise ValueError(f"Image lock has an invalid reference for {name}")
        if item.get("reference") != repository + "@" + item["digest"]:
            raise ValueError(f"Image lock has an unexpected repository or mutable reference for {name}")
        if not DIGEST.fullmatch(item.get("index_digest", "")):
            raise ValueError(f"Image lock has no resolved upstream manifest identity for {name}")


def lock_negative_controls(lock: dict, candidates: dict, candidate_sha: str) -> list[dict]:
    cases = []
    for name, mutate in [
        ("mutable-image-reference", lambda x: x["images"]["php"].update(reference=candidates["images"]["php"])),
        ("unapproved-repository", lambda x: x["images"]["php"].update(reference="other.invalid/php@" + x["images"]["php"]["digest"])),
        ("changed-candidate-input", lambda x: x.update(candidate_sha256="0" * 64)),
        ("different-platform", lambda x: x.update(platform="linux/arm64")),
    ]:
        changed = json.loads(json.dumps(lock))
        mutate(changed)
        try:
            validate_lock(changed, candidates, candidate_sha)
        except ValueError as error:
            cases.append({"case": name, "result": "EXPECTED_REJECTION", "diagnostic": str(error)})
        else:
            raise RuntimeError(f"Image lock negative control was accepted: {name}")
    return cases


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=["resolve", "replay"], default="replay")
    parser.add_argument("--lock", type=Path)
    args = parser.parse_args()
    source = args.workspace.resolve()
    probe = source / "spikes/compatibility"
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    evidence = output / "evidence"
    evidence.mkdir()
    context = output / "context"
    context.mkdir()
    for name in ["images", "php", "python", "frontend"]:
        shutil.copytree(probe / name, context / name, ignore=shutil.ignore_patterns(*EXCLUDED))
    shutil.copyfile(probe / "images/context.dockerignore", context / ".dockerignore")
    candidates_path = probe / "images/candidates.json"
    candidates = json.loads(candidates_path.read_text())
    lock_path = args.lock or probe / "images/inputs.lock.json"
    state = {
        "schema_version": 1, "result": "RUNNING", "mode": args.mode,
        "scope": "P00.03 OCI candidate build and probe replay; no product, production, mirror or native acceptance",
        "source_sha": os.environ.get("GITHUB_SHA"), "source_ref": os.environ.get("GITHUB_REF"),
        "run_id": os.environ.get("GITHUB_RUN_ID"), "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "candidate": candidates, "source_sha256": {}, "commands": [], "images": {},
    }
    for name in ["images", "php", "python", "frontend"]:
        for path in sorted((context / name).rglob("*")):
            if path.is_file():
                state["source_sha256"][str(Path("spikes/compatibility") / path.relative_to(context))] = sha(path)
    for path in sorted((source / ".github/workflows").glob("*.yml")):
        state["source_sha256"][str(path.relative_to(source))] = sha(path)
    live_containers: list[str] = []
    token = uuid.uuid4().hex[:12]

    def save() -> None:
        (evidence / "report.json").write_text(json.dumps(state, indent=2) + "\n")

    def run(label: str, command: list[str], timeout: int = 180) -> str:
        entry = {"label": label, "command": command, "log": label + ".log",
                 "started_at": dt.datetime.now(dt.timezone.utc).isoformat()}
        state["commands"].append(entry)
        save()
        started = time.monotonic()
        with (evidence / entry["log"]).open("w") as log:
            try:
                process = subprocess.Popen(command, cwd=context, text=True, stdout=log,
                                           stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    entry["exit_code"] = process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
                    entry["exit_code"] = 124
                    log.write("\nBounded command timeout exceeded.\n")
            except OSError as error:
                entry["exit_code"] = 127
                log.write(str(error) + "\n")
        entry["duration_seconds"] = round(time.monotonic() - started, 3)
        content = (evidence / entry["log"]).read_text()
        entry["log_sha256"] = sha(evidence / entry["log"])
        save()
        print(f"{label}: exit {entry['exit_code']}", flush=True)
        if entry["exit_code"]:
            print(content[-16000:], flush=True)
            raise RuntimeError(f"{label}: exit {entry['exit_code']}")
        return content

    def container(label: str, image: str, command: list[str], *, readonly: bool = True,
                  timeout: int = 180) -> str:
        name = f"p00-{token}-{label}"
        live_containers.append(name)
        flags = ["docker", "run", "--rm", "--name", name, "--network", "none",
                 "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true",
                 "--pids-limit", "256", "--memory", "2g", "--cpus", "2"]
        if readonly:
            flags += ["--read-only", "--tmpfs", "/tmp:rw,nosuid,nodev,size=64m,uid=10001,gid=10001"]
        return run(label, [*flags, image, *command], timeout)

    try:
        run("docker-version", ["docker", "version"], 30)
        run("buildx-version", ["docker", "buildx", "version"], 30)
        if args.mode == "resolve":
            lock = {"schema_version": 1, "platform": candidates["platform"],
                    "candidate_sha256": sha(candidates_path),
                    "resolved_at": dt.datetime.now(dt.timezone.utc).isoformat(), "images": {}}
            for name, candidate in candidates["images"].items():
                detail = run(f"resolve-{name}", ["docker", "buildx", "imagetools", "inspect", candidate])
                match = re.search(r"^Digest:\s+(sha256:[0-9a-f]{64})\s*$", detail, re.MULTILINE)
                if not match:
                    raise RuntimeError(f"No upstream manifest digest returned for {candidate}")
                index_digest = match.group(1)
                repository = candidate.rsplit(":", 1)[0]
                raw = run(f"manifest-{name}", ["docker", "buildx", "imagetools", "inspect", "--raw", repository + "@" + index_digest])
                manifest = json.loads(raw)
                if "manifests" in manifest:
                    matches = [item for item in manifest["manifests"]
                               if item.get("platform", {}).get("os") == "linux"
                               and item.get("platform", {}).get("architecture") == "amd64"]
                    if len(matches) != 1:
                        raise RuntimeError(f"Expected one linux/amd64 image manifest for {candidate}")
                    selected = matches[0]["digest"]
                else:
                    selected = index_digest
                lock["images"][name] = {"candidate": candidate, "index_digest": index_digest,
                                        "digest": selected, "reference": repository + "@" + selected}
        else:
            lock = json.loads(lock_path.read_text())
        validate_lock(lock, candidates, sha(candidates_path))
        state["lock_negative_controls"] = lock_negative_controls(lock, candidates, sha(candidates_path))
        (evidence / "inputs.lock.json").write_text(json.dumps(lock, indent=2) + "\n")
        state["input_lock_sha256"] = sha(evidence / "inputs.lock.json")
        references = {name: item["reference"] for name, item in lock["images"].items()}
        for name, reference in references.items():
            run(f"pull-{name}", ["docker", "pull", "--platform", candidates["platform"], reference], 300)
            base = json.loads(run(f"base-{name}", ["docker", "image", "inspect", reference], 30))[0]
            if (base["Os"], base["Architecture"]) != ("linux", "amd64"):
                raise RuntimeError(f"Pulled wrong platform for {name}")
            state.setdefault("base_images", {})[name] = {
                "reference": reference, "config_digest": base["Id"], "repo_digests": base["RepoDigests"],
                "os": base["Os"], "architecture": base["Architecture"], "layers": base["RootFS"]["Layers"],
            }
        build_args = ["--build-arg", "DEBIAN_SNAPSHOT=" + candidates["debian_snapshot"]]
        for name in references:
            build_args += ["--build-arg", name.upper() + "_BASE=" + references[name]]
        images = {}
        for target in ["php-quality", "php-runtime", "python-quality", "python-runtime"]:
            tag = f"p00-{token}:{target}"
            run("build-" + target, ["docker", "buildx", "build", "--load", "--platform", candidates["platform"],
                                   "--progress", "plain", "--metadata-file", str(evidence / (target + "-build.json")),
                                   "--target", target, "-f", "images/" + target.split("-")[0] + ".Dockerfile",
                                   "-t", tag, *build_args, "."], 900)
            inspect = json.loads(run("inspect-" + target, ["docker", "image", "inspect", tag], 30))[0]
            if inspect["Config"]["User"] != "10001:10001":
                raise RuntimeError(f"Unexpected privileged user for {target}")
            images[target] = inspect["Id"]
            state["images"][target] = {"local_config_digest": inspect["Id"], "layers": inspect["RootFS"]["Layers"],
                                        "user": inspect["Config"]["User"], "size_bytes": inspect["Size"],
                                        "registry_publication": "NOT_PUBLISHED"}
            os_release = container("os-" + target, inspect["Id"], ["cat", "/etc/os-release"])
            packages = container("packages-" + target, inspect["Id"], ["dpkg-query", "-W", "-f=${Package}\t${Version}\t${Architecture}\n"])
            (evidence / (target + "-bom.json")).write_text(json.dumps({
                **state["images"][target], "os_release": os_release, "dpkg_packages": packages.splitlines(),
                "source_sha": state["source_sha"], "input_lock_sha256": state["input_lock_sha256"],
            }, indent=2) + "\n")
        php_info = json.loads(container("php-runtime-identity", images["php-runtime"], ["php", "-r",
            'require "vendor/autoload.php"; echo json_encode(["php"=>PHP_VERSION,"uid"=>posix_geteuid(),'
            '"extensions"=>get_loaded_extensions(),"pdo_drivers"=>PDO::getAvailableDrivers(),'
            '"packages"=>Composer\\InstalledVersions::getAllRawData(),'
            '"pest_present"=>class_exists("Pest\\TestSuite")],JSON_THROW_ON_ERROR);']))
        if php_info["php"] != candidates["expected_versions"]["php"] or php_info["uid"] != 10001:
            raise RuntimeError("Unexpected PHP candidate patch or runtime identity")
        if set(candidates["php_required_extensions"]) - set(php_info["extensions"]):
            raise RuntimeError("Missing required PHP candidate extension")
        if php_info["pest_present"] or not {"sqlite", "pgsql"} <= set(php_info["pdo_drivers"]):
            raise RuntimeError("Development dependencies leaked or a selected PDO driver is missing")
        (evidence / "php-runtime.json").write_text(json.dumps(php_info, indent=2) + "\n")
        container("php-runtime-negative-controls", images["php-runtime"], ["php", "-r",
            '$tests=["source_write"=>@file_put_contents("/app/app/p00-should-not-exist", "x")===false,'
            '"root_write"=>@file_put_contents("/etc/p00-should-not-exist", "x")===false,'
            '"scratch_write"=>file_put_contents("/tmp/p00-allowed", "x")===1,'
            '"no_test_tree"=>!is_dir("/app/tests"),"no_composer_binary"=>!is_file("/usr/local/bin/composer"),'
            '"no_node_binary"=>!is_file("/usr/local/bin/node")];'
            'echo json_encode($tests,JSON_THROW_ON_ERROR); if(in_array(false,$tests,true)) exit(1);'])
        container("php-fpm-configuration", images["php-runtime"], ["php-fpm", "-t"])
        container("php-quality", images["php-quality"], [], readonly=False, timeout=600)
        container("python-quality", images["python-quality"], [], readonly=False, timeout=600)
        python_info = json.loads(container("python-runtime-identity", images["python-runtime"], ["python", "-c",
            'import importlib.metadata as m, importlib.util, json, os, platform; '
            'print(json.dumps({"python":platform.python_version(), "uid":os.geteuid(), '
            '"packages":{d.metadata["Name"]:d.version for d in m.distributions()}, '
            '"dev_present":any(importlib.util.find_spec(x) is not None for x in ("pytest","mypy","ruff","importlinter"))}))']))
        if python_info["python"] != candidates["expected_versions"]["python"] or python_info["uid"] != 10001 or python_info["dev_present"]:
            raise RuntimeError("Unexpected Python runtime patch, user, or development dependency leakage")
        (evidence / "python-runtime.json").write_text(json.dumps(python_info, indent=2) + "\n")
        container("python-runtime-smoke", images["python-runtime"], [])
        python_denials = """from pathlib import Path
import json
results = {}
for name, path in [("source_write", "/app/src/p00-should-not-exist"), ("root_write", "/etc/p00-should-not-exist")]:
    try:
        Path(path).write_text("x")
        results[name] = False
    except OSError:
        results[name] = True
results["scratch_write"] = Path("/tmp/p00-allowed").write_text("x") == 1
results["no_uv_binary"] = not Path("/usr/local/bin/uv").exists()
print(json.dumps(results))
assert all(results.values())
"""
        container("python-runtime-negative-controls", images["python-runtime"],
                  ["python", "-c", python_denials])
        # Test the built runtime's HTTP kernel and assets through the actual container.
        # PHP's development server is only the bounded fixture transport, not the
        # proposed production ingress/FPM topology.
        http_name = f"p00-{token}-http"
        live_containers.append(http_name)
        run("http-start", ["docker", "run", "--detach", "--name", http_name,
            "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true",
            "--pids-limit", "128", "--memory", "512m", "--cpus", "1",
            "--tmpfs", "/tmp:rw,nosuid,nodev,size=64m,uid=10001,gid=10001",
            "--tmpfs", "/app/storage:rw,nosuid,nodev,size=32m,uid=10001,gid=10001",
            "--tmpfs", "/app/bootstrap/cache:rw,nosuid,nodev,size=8m,uid=10001,gid=10001",
            "-e", "APP_KEY=base64:MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=",
            "-p", "127.0.0.1::8000", images["php-runtime"], "php", "artisan", "serve",
            "--host=0.0.0.0", "--port=8000", "--no-reload"], 30)
        binding = json.loads(run("http-port", ["docker", "inspect", "--format", "{{json .NetworkSettings.Ports}}", http_name], 30))
        address = "http://127.0.0.1:" + binding["8000/tcp"][0]["HostPort"]
        deadline = time.monotonic() + 30
        while True:
            try:
                with urllib.request.urlopen(address + "/compatibility", timeout=2) as response:
                    html = response.read().decode()
                    assert response.status == 200
                    break
            except (OSError, AssertionError):
                if time.monotonic() >= deadline:
                    raise RuntimeError("Container HTTP readiness failed within 30 seconds")
                time.sleep(0.25)
        assert '<div id="app"' in html and "/build/assets/" in html, "Missing rendered Inertia page or built asset links"
        request = urllib.request.Request(address + "/compatibility", headers={"X-Inertia": "true", "X-Inertia-Version": "p00-compatibility-v1", "X-Requested-With": "XMLHttpRequest", "Accept": "text/html, application/xhtml+xml"})
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.load(response)
            assert response.status == 200 and response.headers.get("X-Inertia") == "true"
            assert payload["component"] == "Compatibility" and payload["props"]["sampleCount"] == 0
        try:
            urllib.request.urlopen(urllib.request.Request(address + "/compatibility/validate", data=b"name=valid", headers={"Content-Type": "application/x-www-form-urlencoded"}), timeout=5)
        except urllib.error.HTTPError as error:
            assert error.code == 419, f"Unexpected CSRF rejection: {error.code}"
        else:
            raise RuntimeError("CSRF-less request was accepted")
        asset_paths = sorted(set(re.findall(r'(?:src|href)="([^" ]*/build/assets/[^" ]+)"', html)))
        assert asset_paths, "No asset references were exercised"
        for asset in asset_paths:
            asset_path = urllib.parse.urlparse(asset).path
            with urllib.request.urlopen(address + asset_path, timeout=5) as response:
                assert response.status == 200 and len(response.read()) > 0
        state["http_controls"] = {"html": "PASS", "inertia_json": "PASS", "csrf_missing": "EXPECTED_419", "asset_count": len(asset_paths), "transport": "bounded PHP development server in built runtime"}
        run("http-logs", ["docker", "logs", http_name], 30)
        state["result"] = "PASS"
    except Exception as error:
        state["result"] = "FAIL"
        state["failure"] = f"{type(error).__name__}: {error}"
        print(state["failure"], flush=True)
        for name in live_containers:
            try:
                result = subprocess.run(["docker", "logs", name], text=True, capture_output=True, timeout=10, check=False)
                if result.returncode == 0:
                    (evidence / (name + "-failure.log")).write_text(result.stdout + result.stderr)
            except (OSError, subprocess.TimeoutExpired):
                pass
    finally:
        for name in live_containers:
            try:
                subprocess.run(["docker", "rm", "--force", name], capture_output=True, timeout=15, check=False)
            except (OSError, subprocess.TimeoutExpired):
                pass
        state["completed_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        save()
    return 0 if state["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
