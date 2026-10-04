"""Build and inspect one isolated development image; never publish or run native work."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import tomllib
from typing import Any


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def safe_relative(value: str) -> Path:
    path = Path(value)
    require(bool(value) and not path.is_absolute() and ".." not in path.parts,
            f"Unsafe relative path: {value}")
    return path


def load_inputs(workspace: Path, component_id: str) -> tuple[dict[str, Any], dict[str, Any], list[Path]]:
    lock = json.loads((workspace / "deploy/build/inputs.lock.json").read_text())
    registry = json.loads((workspace / "deploy/build/components.json").read_text())
    require(lock["schema_version"] == registry["schema_version"] == 1, "Unsupported schema")
    require(lock["platform"] == "linux/amd64", "Unmeasured image platform")
    require(set(lock["images"]) == {"python", "uv"}, "Unexpected build inputs")
    for image in lock["images"].values():
        require(bool(re.fullmatch(r"[^\s@]+@sha256:[0-9a-f]{64}", image["reference"])),
                "Base images must use immutable SHA-256 references")
        require(image["reference"].endswith("@" + image["digest"]), "Digest/reference mismatch")
    entries = registry["components"]
    require(len({entry["id"] for entry in entries}) == len(entries), "Duplicate component ID")
    matching = [entry for entry in entries if entry["id"] == component_id]
    require(len(matching) == 1, "Unknown component")
    component = matching[0]
    context = safe_relative(component["context"])
    require(len(context.parts) == 2 and context.parts[0] in {"services", "workers"},
            "Build context must be an owned service or worker root")
    require(bool(re.fullmatch(r"[a-z][a-z0-9_]*", component["module"])), "Invalid module")
    require(bool(re.fullmatch(r"[a-z][a-z0-9-]*", component["id"])), "Invalid component ID")
    require(component["dockerfile"] == "Dockerfile" and component["target"] == "runtime",
            "Unexpected build target")
    require(set(component["inputs"]) == {
        "Dockerfile", ".dockerignore", ".python-version", "pyproject.toml", "uv.lock", "README.md", "src"
    }, "Unexpected context input list")
    root = workspace / context
    require(root.resolve() == root.absolute(), "Symlinked component root")
    files: list[Path] = []
    for selected in component["inputs"]:
        source = root / safe_relative(selected)
        require(source.exists() and not source.is_symlink(), f"Missing or symlinked input: {source}")
        candidates = sorted(source.rglob("*")) if source.is_dir() else [source]
        for candidate in candidates:
            require(not candidate.is_symlink(), f"Symlinked image input: {candidate}")
            if "__pycache__" in candidate.parts or candidate.suffix == ".pyc" or any(
                part.endswith(".egg-info") for part in candidate.parts
            ):
                continue
            if candidate.is_file():
                files.append(candidate)
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    require(project["name"] == component["distribution"] and project["version"] == component["version"],
            "Distribution identity differs from registry")
    require(project["dependencies"] == [], "Runtime dependency installation requires an explicit image change")
    require((root / ".python-version").read_text().strip() == lock["python_version"],
            "Interpreter selection differs from image lock")
    require(component["entrypoint"] == "/opt/venv/bin/" + next(iter(project["scripts"])),
            "Entrypoint differs from package manifest")
    dockerfile = (root / "Dockerfile").read_text()
    for key in ("python", "uv"):
        require(f"ARG {key.upper()}_BASE={lock['images'][key]['reference']}\n" in dockerfile,
                f"Standalone {key} base differs from input lock")
    require("COPY ../" not in dockerfile and "spikes/" not in dockerfile,
            "Image cannot copy sibling or spike inputs")
    return lock, component, sorted(files)


class Recorder:
    def __init__(self, output: Path, report: dict[str, Any]) -> None:
        self.output = output
        self.report = report

    def run(self, name: str, argv: list[str], *, cwd: Path, expected: int = 0, timeout: int = 60) -> bytes:
        number = len(self.report["commands"]) + 1
        prefix = f"{number:02d}-{name}"
        started = time.monotonic()
        timed_out = False
        try:
            result = subprocess.run(argv, cwd=cwd, capture_output=True, timeout=timeout, check=False)
            returncode, stdout, stderr = result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired as error:
            timed_out = True
            returncode, stdout, stderr = None, error.stdout or b"", error.stderr or b""
        item: dict[str, Any] = {
            "name": name, "argv": argv, "cwd": str(cwd), "expected_exit": expected,
            "exit_code": returncode, "timed_out": timed_out,
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
        for stream in ("stdout", "stderr"):
            path = self.output / f"{prefix}.{stream}.log"
            path.write_bytes(stdout if stream == "stdout" else stderr)
            item[stream] = {"path": path.name, "sha256": sha256(path), "bytes": path.stat().st_size}
        self.report["commands"].append(item)
        print(f"{name}: exit {returncode}, expected {expected}", flush=True)
        require(returncode == expected and not timed_out,
                f"{name}: unexpected exit {returncode}, timed_out={timed_out}; see retained logs")
        return stdout


def isolation_program(component: dict[str, Any]) -> str:
    return f'''import importlib, importlib.metadata, json, os, pathlib, sys
module = importlib.import_module({component['module']!r})
root = pathlib.Path('/opt/venv')
status = dict(line.split(':', 1) for line in pathlib.Path('/proc/self/status').read_text().splitlines() if ':' in line)
mount = next(line.split() for line in pathlib.Path('/proc/self/mountinfo').read_text().splitlines() if line.split()[4] == '/')
result = {{
 'python_version': '.'.join(map(str, sys.version_info[:3])),
 'uid': os.getuid(), 'gid': os.getgid(),
 'capabilities_effective': int(status['CapEff'].strip(), 16),
 'no_new_privileges': int(status['NoNewPrivs'].strip()),
 'root_read_only': 'ro' in mount[5].split(','),
 'network_interfaces': sorted(p.name for p in pathlib.Path('/sys/class/net').iterdir()),
 'module_file': module.__file__,
 'installed_distributions': sorted((d.metadata['Name'], d.version) for d in importlib.metadata.distributions()),
 'application_source_absent': not pathlib.Path('/app/src').exists() and not pathlib.Path('/build').exists(),
}}
assert result['uid'] == result['gid'] == 10001
assert result['capabilities_effective'] == 0 and result['no_new_privileges'] == 1
assert result['root_read_only'] and result['network_interfaces'] == ['lo']
assert pathlib.Path(module.__file__).is_relative_to(root)
assert result['installed_distributions'] == [({component['distribution']!r}, {component['version']!r})]
assert result['application_source_absent']
print(json.dumps(result, sort_keys=True))
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--component", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--source-revision", default=os.environ.get("GITHUB_SHA", ""))
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    lock, component, sources = load_inputs(workspace, args.component)
    if args.validate_only:
        print(json.dumps({"component": component["id"], "inputs": len(sources), "valid": True}))
        return 0
    require(bool(re.fullmatch(r"[0-9a-f]{40}", args.source_revision)), "Exact source revision required")
    require(args.output is not None, "Output directory required")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    bound = sources + [workspace / path for path in (
        "scripts/p01/run_images.py", "deploy/build/components.json", "deploy/build/inputs.lock.json",
        ".github/workflows/p01-images.yml",
    )]
    report: dict[str, Any] = {
        "schema_version": 1, "result": "FAILED", "component": component["id"],
        "scope": "P01 isolated development bootstrap image; no persistent service or native work",
        "source_revision": args.source_revision, "started_at": datetime.now(UTC).isoformat(),
        "source_sha256": {str(path.relative_to(workspace)): sha256(path) for path in sorted(bound)},
        "image_inputs": lock, "commands": [],
    }
    recorder = Recorder(output, report)
    image = f"p01-{component['id']}:{args.source_revision}"
    try:
        revision = recorder.run("source-revision", ["git", "rev-parse", "HEAD"], cwd=workspace).decode().strip()
        require(revision == args.source_revision, "Checkout revision differs from requested evidence revision")
        dirty = recorder.run("source-clean", [
            "git", "status", "--porcelain", "--untracked-files=all", "--",
            *[str(path.relative_to(workspace)) for path in sorted(bound)],
        ], cwd=workspace)
        require(not dirty.strip(), "Build inputs differ from the recorded Git revision")
        recorder.run("docker-version", ["docker", "version"], cwd=workspace)
        recorder.run("buildx-version", ["docker", "buildx", "version"], cwd=workspace)
        with tempfile.TemporaryDirectory(prefix=f"p01-{component['id']}-") as temporary:
            context = Path(temporary)
            root = workspace / component["context"]
            for source in sources:
                destination = context / source.relative_to(root)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
            recorder.run("build", [
                "docker", "buildx", "build", "--load", "--pull", "--platform", lock["platform"],
                "--provenance=false", "--progress=plain", "--target", component["target"],
                "--build-arg", f"PYTHON_BASE={lock['images']['python']['reference']}",
                "--build-arg", f"UV_BASE={lock['images']['uv']['reference']}",
                "--build-arg", f"SOURCE_REVISION={args.source_revision}",
                "--file", str(context / component["dockerfile"]), "--tag", image, str(context),
            ], cwd=context, timeout=900)
        # The entire copied source context is gone before runtime checks.
        inspected = json.loads(recorder.run("image-inspect", ["docker", "image", "inspect", image], cwd=output))[0]
        configuration = inspected["Config"]
        require(configuration["User"] == "10001:10001", "Image must default to a non-root identity")
        require(configuration["Entrypoint"] == [component["entrypoint"]], "Unexpected entrypoint")
        require(configuration["Cmd"] == ["liveness"], "Unexpected default probe")
        require(configuration.get("Healthcheck", {}).get("Test") == ["NONE"], "Bootstrap image cannot claim persistent health")
        require(not configuration.get("ExposedPorts"), "Bootstrap image cannot expose a service port")
        require(configuration["Labels"]["org.opencontainers.image.revision"] == args.source_revision,
                "Image source label does not match build revision")
        require(inspected["Architecture"] == "amd64" and inspected["Os"] == "linux", "Wrong image platform")
        report["image"] = {"id": inspected["Id"], "tag": image, "size": inspected["Size"],
                           "platform": lock["platform"], "identity_kind": "local_image_configuration_digest"}
        docker = ["docker", "run", "--rm", "--read-only", "--network", "none", "--cap-drop", "ALL",
                  "--security-opt", "no-new-privileges", "--pids-limit", "64", "--memory", "256m", "--cpus", "1"]
        live = json.loads(recorder.run("liveness", [*docker, image], cwd=output))
        require(live == component["probe_base"] | {"probe": "liveness", "status": "ok"}, "Liveness scope mismatch")
        ready = json.loads(recorder.run("readiness", [*docker, image, "readiness"], cwd=output, expected=1))
        require(ready == component["probe_base"] | {"probe": "readiness", "status": "not_ready", "reason": component["readiness_reason"]},
                "Unimplemented dependency readiness must fail explicitly")
        invalid = recorder.run("rejected-override", [*docker, image, "readiness", "--force"], cwd=output, expected=2)
        require(not invalid, "Rejected input emitted a success payload")
        inventory = json.loads(recorder.run("runtime-isolation", [
            *docker, "--entrypoint", "/opt/venv/bin/python", image, "-I", "-c", isolation_program(component)
        ], cwd=output))
        require(inventory["python_version"] == lock["python_version"], "Interpreter differs from selected patch")
        report["runtime"] = inventory
        report["result"] = "PASSED"
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        report["error"] = f"{type(error).__name__}: {error}"
        print(report["error"], flush=True)
    finally:
        report["completed_at"] = datetime.now(UTC).isoformat()
        (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return 0 if report["result"] == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
