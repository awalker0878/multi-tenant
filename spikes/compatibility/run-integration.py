#!/usr/bin/env python3
"""Run the disposable PHP/browser probe and retain source-bound command evidence."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import urllib.request


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dependency-mode", choices=["resolve", "install"], default="install")
    args = parser.parse_args()
    source = args.workspace.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    evidence = output / "evidence"
    evidence.mkdir()
    probe = source / "spikes/compatibility"
    php = output / "php"
    frontend = output / "frontend"
    excluded = shutil.ignore_patterns("vendor", "node_modules", ".cache", "test-results", "__pycache__", "build")
    shutil.copytree(probe / "php", php, ignore=excluded)
    shutil.copytree(probe / "frontend", frontend, ignore=excluded)
    for relative in ["bootstrap/cache", "storage/framework/cache", "storage/framework/sessions", "storage/framework/views", "storage/logs"]:
        (php / relative).mkdir(parents=True, exist_ok=True)
    state = {
        "schema_version": 1, "result": "RUNNING",
        "scope": "P00.03 isolated Laravel HTTP, PHP quality and Chromium/Inertia probe; no product or native acceptance",
        "source_sha": os.environ.get("GITHUB_SHA"),
        "source_ref": os.environ.get("GITHUB_REF"),
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "dependency_mode": args.dependency_mode,
        "source_sha256": {}, "commands": [],
    }
    for root in [probe / "php", probe / "frontend"]:
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root)
            if path.is_file() and not any(part in {"vendor", "node_modules", ".cache", "test-results", "__pycache__", "build"} for part in relative.parts):
                state["source_sha256"][str(path.relative_to(source))] = digest(path)
    for relative in ["spikes/compatibility/run-integration.py", ".github/workflows/p00-php-compatibility.yml"]:
        state["source_sha256"][relative] = digest(source / relative)

    def save() -> None:
        (evidence / "report.json").write_text(json.dumps(state, indent=2) + "\n")

    environment = os.environ.copy()
    environment.update({
        "APP_ENV": "local", "APP_DEBUG": "false", "APP_URL": "http://127.0.0.1:8000",
        "APP_KEY": "base64:" + "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=",
        "P00_BASE_URL": "http://127.0.0.1:8000",
        "PLAYWRIGHT_JSON_OUTPUT_FILE": str(evidence / "browser.json"),
    })

    def run(label: str, argv: list[str], cwd: Path = php, timeout: int = 300) -> None:
        entry = {"label": label, "command": argv, "cwd": str(cwd.relative_to(output)),
                 "started_at": dt.datetime.now(dt.timezone.utc).isoformat(), "log": label + ".log"}
        state["commands"].append(entry)
        save()
        started = time.monotonic()
        with (evidence / entry["log"]).open("w") as log:
            try:
                process = subprocess.Popen(argv, cwd=cwd, env=environment, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    entry["exit_code"] = process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
                    entry["exit_code"] = 124
                    log.write("\nCommand group exceeded the bounded timeout and was stopped.\n")
            except OSError as error:
                entry["exit_code"] = 127
                log.write(str(error) + "\n")
        entry["duration_seconds"] = round(time.monotonic() - started, 3)
        save()
        print(f"{label}: exit {entry['exit_code']}", flush=True)
        print((evidence / entry["log"]).read_text(), flush=True)
        if entry["exit_code"]:
            raise RuntimeError(f"{label} failed with exit {entry['exit_code']}")

    failures: list[str] = []

    def check(label: str, argv: list[str], cwd: Path = php, timeout: int = 300) -> None:
        try:
            run(label, argv, cwd, timeout)
        except RuntimeError as error:
            failures.append(str(error))

    lock = php / "composer.lock"
    flags = ["--no-interaction", "--prefer-dist", "--no-scripts", "--no-progress"]
    package_snapshot = ('require "vendor/autoload.php"; $packages=[]; '
                        'foreach (Composer\\InstalledVersions::getInstalledPackages() as $name) {'
                        '$packages[$name]=["version"=>Composer\\InstalledVersions::getPrettyVersion($name),'
                        '"reference"=>Composer\\InstalledVersions::getReference($name)];}'
                        'ksort($packages); echo json_encode($packages,JSON_THROW_ON_ERROR|JSON_PRETTY_PRINT).PHP_EOL;')
    server = None
    server_log = None
    try:
        state["input_lock_sha256"] = digest(lock) if lock.exists() else None
        run("php-runtime", ["php", "-r", 'echo json_encode(["php"=>PHP_VERSION,"extensions"=>get_loaded_extensions()],JSON_THROW_ON_ERROR).PHP_EOL;'], timeout=30)
        run("composer-version", ["composer", "--version", "--no-ansi"], timeout=30)
        run("initial-dependencies", ["composer", "update" if args.dependency_mode == "resolve" else "install", *flags])
        state["resolved_lock_sha256"] = digest(lock)
        if args.dependency_mode == "install" and state["input_lock_sha256"] != state["resolved_lock_sha256"]:
            raise RuntimeError("Install changed the committed lock")
        run("validate", ["composer", "validate", "--strict", "--no-interaction"])
        run("platform", ["composer", "check-platform-reqs", "--no-interaction"])
        run("packages-initial", ["php", "-r", package_snapshot], timeout=30)
        run("smoke-initial", ["php", "smoke.php"], timeout=60)
        shutil.rmtree(php / "vendor")
        run("clean-install", ["composer", "install", *flags])
        run("validate-clean", ["composer", "validate", "--strict", "--no-interaction"])
        run("platform-clean", ["composer", "check-platform-reqs", "--no-interaction"])
        run("packages-clean", ["php", "-r", package_snapshot], timeout=30)
        state["replayed_lock_sha256"] = digest(lock)
        if state["resolved_lock_sha256"] != state["replayed_lock_sha256"]:
            raise RuntimeError("Clean install changed the resolved lock")
        first = json.loads((evidence / "packages-initial.log").read_text())
        second = json.loads((evidence / "packages-clean.log").read_text())
        if first != second:
            raise RuntimeError("Clean install changed installed versions or references")
        state["packages"] = second
        run("smoke-clean", ["php", "smoke.php"], timeout=60)
        check("pint", ["php", "vendor/bin/pint", "--test"])
        check("larastan", ["php", "vendor/bin/phpstan", "analyse", "--no-progress", "--memory-limit=1G"])
        check("deptrac", ["php", "vendor/bin/deptrac", "analyse", "--no-cache", "--fail-on-uncovered"])
        check("pest", ["php", "vendor/bin/pest", "--colors=never", "--display-warnings", "--fail-on-warning", "--fail-on-risky", "--fail-on-empty-test-suite"])
        check("quality-canaries", ["python3", "tools/verify_quality_canaries.py"])
        check("composer-audit", ["composer", "audit", "--locked", "--no-interaction"])
        run("node-runtime", ["node", "--version"], frontend, 30)
        run("npm-runtime", ["npm", "--version"], frontend, 30)
        run("npm-clean-install", ["npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund"], frontend)
        run("vue-typecheck", ["npm", "run", "typecheck"], frontend)
        run("vite-build", ["npm", "run", "build"], frontend)
        run("browser-install", ["npm", "run", "browser:install"], frontend)
        run("npm-audit", ["npm", "audit", "--json", "--audit-level=low"], frontend)
        shutil.copytree(frontend / "public/build", php / "public/build", dirs_exist_ok=True)
        server_log = (evidence / "http-server.log").open("w")
        server = subprocess.Popen(["php", "artisan", "serve", "--host=127.0.0.1", "--port=8000", "--no-reload"], cwd=php, env=environment, stdout=server_log, stderr=subprocess.STDOUT, start_new_session=True)
        deadline = time.monotonic() + 30
        while True:
            if time.monotonic() >= deadline:
                raise RuntimeError("HTTP server did not become ready in 30 seconds")
            if server.poll() is not None:
                raise RuntimeError("HTTP server exited before readiness")
            try:
                with urllib.request.urlopen("http://127.0.0.1:8000/compatibility", timeout=2) as response:
                    if response.status == 200:
                        break
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError("HTTP server did not become ready in 30 seconds")
                time.sleep(0.25)
        run("browser", ["npm", "run", "browser:test"], frontend, 120)
        browser_report = json.loads((evidence / "browser.json").read_text())
        if browser_report["stats"]["expected"] < 1 or any(browser_report["stats"][key] for key in ["unexpected", "flaky", "skipped"]):
            raise RuntimeError("Browser report contains no executed test, a failure, a retry or a skip")
        if failures:
            raise RuntimeError("; ".join(failures))
        state["result"] = "PASS"
    except Exception as error:
        state["result"] = "FAIL"
        state["failure"] = str(error)
        state["quality_failures"] = failures
    finally:
        if server is not None:
            try:
                os.killpg(server.pid, signal.SIGTERM)
                server.wait(timeout=5)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                if server.poll() is None:
                    os.killpg(server.pid, signal.SIGKILL)
                    server.wait(timeout=5)
        if server_log:
            server_log.close()
        for filename in ["composer.json", "composer.lock"]:
            if (php / filename).is_file():
                shutil.copyfile(php / filename, evidence / filename)
        if (php / "storage/logs").exists():
            shutil.copytree(php / "storage/logs", evidence / "laravel-logs", dirs_exist_ok=True)
        if (frontend / "test-results").exists():
            shutil.copytree(frontend / "test-results", evidence / "browser-artifacts", dirs_exist_ok=True)
        state["completed_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        save()
    return 0 if state["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
