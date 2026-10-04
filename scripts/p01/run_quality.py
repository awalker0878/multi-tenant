#!/usr/bin/env python3
"""Measure one private foundation package, retaining exact source and command evidence."""
from __future__ import annotations

import argparse
import base64
import datetime as dt
from email.parser import Parser
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
import tomllib
import urllib.error
import urllib.request
import zipfile

from python_lock import canonical_name, production_inventory


EXCLUDED = {
    "vendor", "node_modules", ".venv", ".cache", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".import_linter_cache", ".phpunit.cache", "test-results", "verification", "dist", "build",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def files(root: Path) -> list[Path]:
    return [
        path for path in sorted(root.rglob("*"))
        if path.is_file()
        and not any(part in EXCLUDED or part.endswith(".egg-info") for part in path.relative_to(root).parts)
    ]


class Evidence:
    def __init__(self, output: Path, state: dict):
        self.output = output
        self.root = output / "evidence"
        self.root.mkdir(parents=True, exist_ok=False)
        self.state = state
        self.env = {key: value for key, value in os.environ.items() if key not in {"PYTHONPATH", "VIRTUAL_ENV"}}
        self.env.update({"UV_PYTHON_DOWNLOADS": "never", "UV_NO_PROGRESS": "1"})
        self.save()

    def save(self) -> None:
        (self.root / "report.json").write_text(json.dumps(self.state, indent=2) + "\n")

    def require(self, label: str, condition: bool) -> None:
        self.state["checks"].append({"name": label, "passed": condition})
        self.save()
        if not condition:
            raise RuntimeError(f"Check failed: {label}")

    def run(self, label: str, argv: list[str], cwd: Path, *, expected: int = 0, timeout: int = 300) -> bytes:
        ordinal = len(self.state["commands"]) + 1
        prefix = f"{ordinal:02d}-{label}"
        entry = {
            "name": label, "command": argv, "cwd": str(cwd.relative_to(self.output)),
            "started_at": now(), "timeout_seconds": timeout, "expected_exit_code": expected,
            "stdout": prefix + ".stdout.log", "stderr": prefix + ".stderr.log",
        }
        self.state["commands"].append(entry)
        self.save()
        started = time.monotonic()
        with (self.root / entry["stdout"]).open("wb") as stdout, (self.root / entry["stderr"]).open("wb") as stderr:
            try:
                process = subprocess.Popen(argv, cwd=cwd, env=self.env, stdout=stdout, stderr=stderr, start_new_session=True)
                try:
                    entry["exit_code"] = process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=10)
                    entry["exit_code"] = 124
                    entry["timed_out"] = True
                    stderr.write(b"\nBounded command timeout; process group stopped.\n")
            except OSError as error:
                entry["exit_code"] = 127
                stderr.write((str(error) + "\n").encode())
        entry.update({
            "finished_at": now(), "duration_seconds": round(time.monotonic() - started, 3),
            "stdout_sha256": sha256(self.root / entry["stdout"]),
            "stderr_sha256": sha256(self.root / entry["stderr"]),
            "passed": entry["exit_code"] == expected and not entry.get("timed_out", False),
        })
        self.save()
        print(f"{label}: exit {entry['exit_code']} (expected {expected})", flush=True)
        if not entry["passed"]:
            raise RuntimeError(f"{label}: exit {entry['exit_code']} (expected {expected}); see retained logs")
        return (self.root / entry["stdout"]).read_bytes()


def python_quality(e: Evidence, component: Path, config: dict, candidate: dict) -> None:
    e.require("committed-uv-lock-present", (component / "uv.lock").is_file())
    lock_hash = sha256(component / "uv.lock")
    e.state["input_lock_sha256"] = lock_hash
    version = e.run("python-version", [sys.executable, "-c", "import sys; print(sys.version.split()[0])"], component, timeout=20).decode().strip()
    e.require("exact-python-version", version == candidate["python_version"])
    e.require("accepted-python-platform", sys.platform == "linux" and sys.implementation.name == "cpython")
    uv_version = e.run("uv-version", ["uv", "--version"], component, timeout=20).decode().split()
    e.require("exact-uv-version", uv_version[:2] == ["uv", candidate["uv_version"]])
    e.run("lock-check", ["uv", "lock", "--check", "--no-managed-python"], component)
    e.run("clean-locked-install", ["uv", "sync", "--locked", "--group", "build", "--no-managed-python", "--no-editable"], component)
    env_python = component / ".venv/bin/python"
    e.run("installed-quality-inventory", ["uv", "pip", "list", "--python", str(env_python), "--format", "json"], component)
    quality = [
        ("ruff", ["ruff", "check", "src", "tests"]),
        ("format", ["ruff", "format", "--check", "src", "tests"]),
        ("mypy", ["mypy"]),
        ("tests", ["pytest", "-q"]),
    ]
    failures = []
    for label, command in quality:
        try:
            e.run(label, ["uv", "run", "--locked", "--no-sync", *command], component)
        except RuntimeError as error:
            failures.append(str(error))
    if failures:
        raise RuntimeError("; ".join(failures))
    e.run("wheel-build", ["uv", "build", "--no-build-isolation", "--wheel"], component)
    wheels = list((component / "dist").glob("*.whl"))
    e.require("one-owned-wheel", len(wheels) == 1)
    wheel = wheels[0]
    module = config["module"]
    project = tomllib.loads((component / "pyproject.toml").read_text())["project"]
    expected_inventory = production_inventory(project, tomllib.loads((component / "uv.lock").read_text()))
    e.state["expected_runtime_distributions"] = expected_inventory
    with zipfile.ZipFile(wheel) as archive:
        members = archive.namelist()
        metadata = [name for name in members if name.endswith(".dist-info/METADATA")]
        e.require("one-wheel-metadata", len(metadata) == 1)
        metadata_root = metadata[0].split("/", 1)[0]
        e.require("wheel-contains-only-private-module-and-metadata", all(name.startswith((module + "/", metadata_root + "/")) for name in members))
        wheel_metadata = Parser().parsestr(archive.read(metadata[0]).decode())
        e.require("wheel-identity-matches-owned-project", canonical_name(wheel_metadata["Name"]) == canonical_name(project["name"]) and wheel_metadata["Version"] == project["version"])
        normalize = lambda requirements: sorted(re.sub(r"\s+", "", value) for value in requirements)
        e.require("wheel-runtime-requirements-match-manifest", normalize(wheel_metadata.get_all("Requires-Dist", [])) == normalize(project["dependencies"]))
        e.state["wheel_members"] = members
    runtime = e.output / "runtime"
    e.run("empty-runtime", ["uv", "venv", "--no-managed-python", "--python", candidate["python_version"], str(runtime)], component)
    executable = runtime / "bin/python"
    requirements = e.root / "production-requirements.txt"
    e.run("export-production-lock", ["uv", "export", "--locked", "--no-default-groups", "--no-emit-project", "--no-annotate", "--no-header", "--format", "requirements.txt", "--output-file", str(requirements)], component)
    e.run("isolated-production-install", ["uv", "pip", "sync", "--python", str(executable), "--require-hashes", "--only-binary", ":all:", str(requirements)], component)
    e.run("isolated-wheel-install", ["uv", "pip", "install", "--python", str(executable), "--no-index", "--no-deps", str(wheel)], component)
    e.run("runtime-dependency-check", ["uv", "pip", "check", "--python", str(executable)], runtime)
    inventory = json.loads(e.run("runtime-inventory", ["uv", "pip", "list", "--python", str(executable), "--format", "json"], runtime))
    observed_inventory = {canonical_name(package["name"]): package["version"] for package in inventory}
    e.require("exact-production-lock-runtime-distributions", observed_inventory == expected_inventory and len(inventory) == len(expected_inventory))
    e.state["runtime_distributions"] = observed_inventory
    imported = e.run("isolated-import", [str(executable), "-I", "-c", f"import {module}; print({module}.__file__)"], runtime, timeout=20).decode().strip()
    e.require("import-resolves-inside-installed-runtime", Path(imported).is_relative_to(runtime))
    live = json.loads(e.run("isolated-liveness", [str(executable), "-I", "-m", module + ".bootstrap.health", "liveness"], runtime, timeout=20))
    e.require("liveness-bounded-to-process", live.get("scope") == "process_bootstrap" and live.get("native_operations_enabled") is False and live.get("status") == "ok")
    ready = json.loads(e.run("isolated-readiness", [str(executable), "-I", "-m", module + ".bootstrap.health", "readiness"], runtime, expected=1, timeout=20))
    e.require("readiness-rejects-unimplemented-dependencies", ready.get("status") == "not_ready" and ready.get("native_operations_enabled") is False)
    invalid = e.run("isolated-invalid-input", [str(executable), "-I", "-m", module + ".bootstrap.health", "readiness", "--force"], runtime, expected=2, timeout=20)
    e.require("invalid-input-produces-no-success-document", not invalid)
    installed = json.loads(e.run("installed-entrypoint", [str(runtime / "bin" / config["entrypoint"]), "liveness"], runtime, timeout=20))
    e.require("installed-command-agrees-with-module", installed == live)
    server_entrypoint = module + "-serve"
    if server_entrypoint in project["scripts"]:
        python_http(e, runtime, module, server_entrypoint)
    e.require("lock-unchanged", sha256(component / "uv.lock") == lock_hash)
    envelope = {"schema_version": 1, "filename": wheel.name, "size": wheel.stat().st_size, "sha256": sha256(wheel), "encoding": "base64", "content": base64.b64encode(wheel.read_bytes()).decode()}
    (e.root / "wheel-envelope.json").write_text(json.dumps(envelope, indent=2) + "\n")
    e.state["wheel_sha256"] = envelope["sha256"]


def python_http(e: Evidence, runtime: Path, service: str, entrypoint: str) -> None:
    """Probe the installed persistent entrypoint without any real database settings."""
    with socket.socket() as port_source:
        port_source.bind(("127.0.0.1", 0))
        port = port_source.getsockname()[1]
    token = "synthetic-quality-fixture-token-0000000000"
    token_file = e.output / "synthetic-health-token"
    token_file.write_text(token + "\n")
    token_file.chmod(0o600)
    environment = {key: value for key, value in e.env.items() if not key.startswith(("DB_", "PG", "HEALTH_"))}
    environment["HEALTH_TOKEN_FILE"] = str(token_file)
    command = [str(runtime / "bin" / entrypoint), "--host", "127.0.0.1", "--port", str(port)]
    entry = {"command": command, "started_at": now(), "log": "http-server.log", "bound_address": f"127.0.0.1:{port}"}
    e.state["http_server"] = entry
    e.state["http_responses"] = []
    e.save()
    with (e.root / entry["log"]).open("wb") as log:
        process = subprocess.Popen(command, cwd=runtime, env=environment, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            deadline = time.monotonic() + 30
            while True:
                if process.poll() is not None:
                    raise RuntimeError("Installed ASGI entrypoint exited during startup")
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/health/live", timeout=2) as response:
                        if response.status == 200:
                            break
                except OSError:
                    pass
                if time.monotonic() >= deadline:
                    raise RuntimeError("Installed ASGI startup exceeded 30 seconds")
                time.sleep(0.1)
            dependency_base = {"service": service, "scope": "foundation_dependencies", "native_operations_enabled": False}
            cases = [
                ("/health/live", False, 200, {"service": service, "status": "alive", "scope": "process"}),
                ("/health/ready", False, 503, {"service": service, "status": "not_ready", "scope": "service", "reason": "foundation_only"}),
                ("/health/dependencies", False, 401, dependency_base | {"status": "unauthorized"}),
                ("/health/dependencies", True, 503, dependency_base | {"status": "not_ready", "reason": "dependencies_unavailable"}),
            ]
            for route, authenticated, status, payload in cases:
                request = urllib.request.Request(f"http://127.0.0.1:{port}" + route)
                if authenticated:
                    request.add_header("Authorization", "Bearer " + token)
                try:
                    response = urllib.request.urlopen(request, timeout=10)
                except urllib.error.HTTPError as error:
                    response = error
                with response:
                    raw = response.read()
                    e.state["http_responses"].append({"route": route, "authenticated": authenticated, "status": response.status, "headers": dict(response.headers), "body": raw.decode(), "body_sha256": hashlib.sha256(raw).hexdigest()})
                    label = f"http-{route}-{'authenticated' if authenticated else 'public'}"
                    e.require(label + "-status", response.status == status)
                    e.require(label + "-body", json.loads(raw) == payload)
                    e.require(label + "-no-cache", "no-store" in response.headers.get("Cache-Control", ""))
                    if status == 503:
                        e.require(label + "-retry-after", response.headers.get("Retry-After") == "10")
        finally:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=5)
            except ProcessLookupError:
                pass
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
            entry.update({"exit_code_after_stop": process.poll(), "stopped_at": now(), "cleanup_passed": process.poll() is not None})
            entry["log_sha256"] = sha256(e.root / entry["log"])
            token_file.unlink(missing_ok=True)
            e.save()


def php_http(e: Evidence, component: Path, service: str, *, browser: bool = False) -> None:
    command = ["php", "artisan", "serve", "--host=127.0.0.1", "--port=8031", "--no-reload"]
    entry = {"command": command, "started_at": now(), "log": "http-server.log", "bound_address": "127.0.0.1:8031"}
    e.state["http_server"] = entry
    e.save()
    with (e.root / entry["log"]).open("wb") as log:
        process = subprocess.Popen(command, cwd=component, env=e.env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            deadline = time.monotonic() + 30
            while True:
                if process.poll() is not None:
                    raise RuntimeError("Laravel HTTP process exited during startup")
                try:
                    with urllib.request.urlopen("http://127.0.0.1:8031/health/live", timeout=2) as response:
                        if response.status == 200:
                            break
                except OSError:
                    pass
                if time.monotonic() >= deadline:
                    raise RuntimeError("Laravel HTTP startup exceeded 30 seconds")
                time.sleep(0.2)
            cases = [
                ("/health/live", 200, {"service": service, "status": "alive", "scope": "process"}),
                ("/health/ready", 503, {"service": service, "status": "not_ready", "scope": "service", "reason": "foundation_only"}),
            ]
            e.state["http_responses"] = []
            for route, expected, body in cases:
                try:
                    response = urllib.request.urlopen("http://127.0.0.1:8031" + route, timeout=5)
                except urllib.error.HTTPError as error:
                    response = error
                with response:
                    raw = response.read()
                    observed = {"route": route, "status": response.status, "headers": dict(response.headers), "body": raw.decode(), "body_sha256": hashlib.sha256(raw).hexdigest()}
                    e.state["http_responses"].append(observed)
                    e.require(f"http-{route}-status", response.status == expected)
                    e.require(f"http-{route}-body", json.loads(raw) == body)
                    e.require(f"http-{route}-no-cache", "no-store" in response.headers.get("Cache-Control", ""))
                    if route.endswith("ready"):
                        e.require("unready-retry-after", response.headers.get("Retry-After") == "10")
            if browser:
                e.run("chromium-browser", ["npm", "run", "browser:test"], component, timeout=120)
                report = json.loads((component / "test-results/browser.json").read_text())
                stats = report["stats"]
                e.require("browser-executed-without-failures-skips-or-retries", stats["expected"] >= 1 and all(stats.get(key) == 0 for key in ["unexpected", "flaky", "skipped"]))
                e.state["browser_stats"] = stats
        finally:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=5)
            except ProcessLookupError:
                pass
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
            entry.update({"exit_code_after_stop": process.poll(), "stopped_at": now(), "cleanup_passed": process.poll() is not None})
    entry["log_sha256"] = sha256(e.root / entry["log"])
    e.save()


def php_quality(e: Evidence, component: Path, config: dict, candidate: dict, mode: str) -> None:
    lock = component / "composer.lock"
    e.state["input_lock_sha256"] = sha256(lock) if lock.exists() else None
    e.state["dependency_mode"] = mode
    if mode == "replay":
        e.require("replay-requires-committed-lock", lock.is_file())
    e.env.update({
        "APP_ENV": "testing", "APP_DEBUG": "false", "APP_URL": "http://127.0.0.1:8031",
        "APP_KEY": "base64:" + base64.b64encode(b"0" * 32).decode(),
        "COMPOSER_HOME": str(e.output / "composer-home"),
        "COMPOSER_CACHE_DIR": str(e.output / "composer-cache"),
        "COMPOSER_NO_INTERACTION": "1", "COMPOSER_PROCESS_TIMEOUT": "300",
        "CONSOLE_BASE_URL": "http://127.0.0.1:8031", "SESSION_SECURE_COOKIE": "false",
    })
    (component / ".env").write_text("# Isolated synthetic test settings come from the runner.\n")
    for path in ["bootstrap/cache", "storage/framework/cache", "storage/framework/sessions", "storage/framework/views", "storage/logs"]:
        (component / path).mkdir(parents=True, exist_ok=True)
    php = json.loads(e.run("php-version", ["php", "-r", 'echo json_encode(["version"=>PHP_VERSION,"extensions"=>get_loaded_extensions()],JSON_THROW_ON_ERROR);'], component, timeout=20))
    e.require("exact-php-version", php["version"] == candidate["php_version"])
    composer = e.run("composer-version", ["composer", "--version", "--no-ansi"], component, timeout=20).decode()
    e.require("exact-composer-version", re.search(r"Composer version " + re.escape(candidate["composer_version"]) + r"(?:\s|$)", composer) is not None)
    flags = ["--no-interaction", "--prefer-dist", "--no-scripts", "--no-progress"]
    e.run("resolve-dependencies" if mode == "resolve" else "locked-install", ["composer", "update" if mode == "resolve" else "install", *flags], component)
    resolved = sha256(lock)
    e.state["resolved_lock_sha256"] = resolved
    if mode == "replay":
        e.require("replay-lock-unchanged", resolved == e.state["input_lock_sha256"])
    e.run("composer-validate", ["composer", "validate", "--strict", "--no-check-all", "--no-interaction"], component)
    e.run("platform-requirements", ["composer", "check-platform-reqs", "--no-interaction"], component)
    snapshot = ('require "vendor/autoload.php"; $p=[]; foreach (Composer\\InstalledVersions::getInstalledPackages() as $name) {'
                '$p[$name]=["version"=>Composer\\InstalledVersions::getPrettyVersion($name),"reference"=>Composer\\InstalledVersions::getReference($name)];}'
                'ksort($p); echo json_encode($p,JSON_THROW_ON_ERROR|JSON_PRETTY_PRINT);')
    initial = json.loads(e.run("installed-packages-initial", ["php", "-r", snapshot], component))
    shutil.rmtree(component / "vendor")
    e.run("clean-locked-install", ["composer", "install", *flags], component)
    e.require("clean-install-lock-unchanged", sha256(lock) == resolved)
    installed = json.loads(e.run("installed-packages-replay", ["php", "-r", snapshot], component))
    e.require("clean-install-package-versions-references-match", initial == installed)
    e.state["installed_packages"] = installed
    failures = []
    if config.get("frontend"):
        node = e.run("node-version", ["node", "--version"], component, timeout=20).decode().strip()
        e.require("exact-node-version", node == "v" + candidate["node_version"])
        e.run("npm-version", ["npm", "--version"], component, timeout=20)
        e.require("committed-npm-lock-present", (component / "package-lock.json").is_file())
        npm_lock = sha256(component / "package-lock.json")
        e.run("frontend-clean-install", ["npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund"], component)
        e.run("frontend-boundaries", ["npm", "run", "test:boundaries"], component)
        e.run("frontend-typecheck", ["npm", "run", "typecheck"], component)
        e.run("frontend-build", ["npm", "run", "build"], component)
        e.require("frontend-lock-unchanged", sha256(component / "package-lock.json") == npm_lock)
        e.run("chromium-install", ["npm", "run", "browser:install"], component)
        e.state["frontend_assets"] = {str(path.relative_to(component)): sha256(path) for path in files(component / "public/build")}
    commands = [
        ("pint", ["composer", "run", "test:format"]),
        ("larastan", ["composer", "run", "test:types"]),
        ("deptrac", ["composer", "run", "test:architecture"]),
        ("pest", ["composer", "run", "test"]),
        ("quality-canaries", ["composer", "run", "test:canaries"]),
        ("config-cache", ["php", "artisan", "config:cache"]),
        ("route-cache", ["php", "artisan", "route:cache"]),
    ]
    for label, command in commands:
        try:
            e.run(label, command, component)
        except RuntimeError as error:
            failures.append(str(error))
    php_http(e, component, e.state["component"], browser=bool(config.get("frontend")))
    if failures:
        raise RuntimeError("; ".join(failures))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--component", required=True)
    parser.add_argument("--dependency-mode", choices=["resolve", "replay"])
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    candidate = json.loads((workspace / "scripts/p01/candidates.json").read_text())
    if args.component not in candidate["components"]:
        parser.error("Unknown registered candidate component")
    config = candidate["components"][args.component]
    output = args.output.resolve()
    if output.is_relative_to(workspace):
        parser.error("Output must be outside the repository to preserve source isolation")
    output.mkdir(parents=True, exist_ok=False)
    e = Evidence(output, {
        "schema_version": 1, "result": "RUNNING", "component": args.component,
        "scope": candidate["scope"], "recorded_at": now(),
        "source_sha": os.environ.get("GITHUB_SHA"), "source_ref": os.environ.get("GITHUB_REF"),
        "run_id": os.environ.get("GITHUB_RUN_ID"), "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "commands": [], "checks": [], "source_sha256": {},
    })
    component = output / "component"
    try:
        source = workspace / config["path"]
        e.require("component-path-inside-repository", source.resolve().is_relative_to(workspace))
        e.require("component-source-present", source.is_dir())
        source_files = files(source)
        e.require("component-has-no-symlink-input", all(not path.is_symlink() and all(not parent.is_symlink() for parent in path.parents if parent.is_relative_to(source)) for path in source_files))
        for path in source_files:
            target = component / path.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            e.state["source_sha256"][str(path.relative_to(workspace))] = sha256(path)
        for path in [*files(workspace / "scripts/p01"), workspace / ".github/workflows/p01-foundations.yml"]:
            e.state["source_sha256"][str(path.relative_to(workspace))] = sha256(path)
        e.save()
        if config["language"] == "python":
            python_quality(e, component, config, candidate)
        elif config["language"] == "php":
            php_quality(e, component, config, candidate, args.dependency_mode or candidate["php_dependency_mode"])
        else:
            raise RuntimeError("Unknown component language")
        e.state["result"] = "PASS"
    except Exception as error:
        e.state["result"] = "FAIL"
        e.state["failure"] = f"{type(error).__name__}: {error}"
        print(e.state["failure"], file=sys.stderr)
    finally:
        for filename in ["composer.json", "composer.lock", "package.json", "package-lock.json", "pyproject.toml", "uv.lock"]:
            if (component / filename).is_file():
                shutil.copyfile(component / filename, e.root / filename)
        logs = component / "storage/logs"
        if logs.is_dir():
            shutil.copytree(logs, e.root / "application-logs")
        browser_results = component / "test-results"
        if browser_results.is_dir():
            envelopes = []
            for path in files(browser_results):
                data = path.read_bytes()
                envelopes.append({"path": str(path.relative_to(browser_results)), "size": len(data), "sha256": sha256(path), "encoding": "base64", "content": base64.b64encode(data).decode()})
            (e.root / "browser-artifact-envelope.json").write_text(json.dumps({"schema_version": 1, "files": envelopes}, indent=2) + "\n")
        e.state["artifact_sha256"] = {str(path.relative_to(e.root)): sha256(path) for path in files(e.root) if path.name != "report.json"}
        e.state["completed_at"] = now()
        e.save()
    return 0 if e.state["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
