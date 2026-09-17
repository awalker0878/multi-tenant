#!/usr/bin/env python3
"""Validate delivered Terraform sources on an approved connected toolchain host.

Copies sources to a temporary directory and disables backend initialization.
Never runs an apply. Optional Terraform tests use mock providers only. Initialization
can download and execute provider plugins, so package trust must be approved first.
A missing executable or failed initialization is BLOCKED, not a passing test.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def plan_only_mock_tests(directory: Path) -> bool:
    """Conservative safeguard: every supplied module test is provider-mocked and plan-only."""
    configs = list((directory / "tests").glob("*.tftest.hcl"))
    if not configs:
        return False
    required = json.loads((directory / "main.tf.json").read_text())["terraform"]["required_providers"]
    for path in configs:
        text = path.read_text()
        commands = re.findall(r"command\s*=\s*([A-Za-z]+)", text)
        run_count = len(re.findall(r'\brun\s+"', text))
        mocked = set(re.findall(r'mock_provider\s+"([^"\n]+)"', text))
        if not commands or any(c != "plan" for c in commands) or len(commands) != run_count:
            return False
        if not set(required) <= mocked:
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mock-tests", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "quality/terraform_validation.json")
    args = parser.parse_args()
    started = time.monotonic()
    report: dict[str, Any] = {
        "kind": "TERRAFORM_TOOLCHAIN_CHECK",
        "target_infrastructure": "NOT_CONTACTED_BY_THIS_SCRIPT",
        "live_qualification": "NOT_RUN",
        "mock_tests_requested": args.mock_tests,
        "modules": [],
        "roots": [],
        "planned_module_count": len(list((ROOT/"terraform/modules").glob("*/main.tf.json"))),
        "planned_root_count": len(list((ROOT/"terraform/roots").glob("*/main.tf.json"))),
        "schema_export": "NOT_RUN",
    }

    def finish(status: str, reason: str | None = None) -> int:
        report["status"] = status
        if reason:
            report["reason"] = reason
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(status)
        return 0 if status == "PASSED_TOOLCHAIN_ONLY" else 2

    binary = shutil.which("terraform")
    if not binary:
        return finish("BLOCKED_TOOLCHAIN", "terraform executable is not installed")

    # Keep approved mirror/trust settings, but remove ambient cloud/CLI credentials.
    forbidden_prefixes = ("TF_VAR_", "TF_CLI_ARGS", "OS_", "NUTANIX_", "NSXT_", "VSPHERE_", "TF_HTTP_")
    env = {key: value for key, value in os.environ.items() if not key.startswith(forbidden_prefixes)}
    env.update(TF_IN_AUTOMATION="true", TF_INPUT="0", CHECKPOINT_DISABLE="1")

    def run(argv: list[str], timeout: int = 240) -> dict[str, Any]:
        try:
            result = subprocess.run(
                [binary, *argv], capture_output=True, text=True, env=env,
                timeout=timeout, check=False,
            )
            return {"exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
        except subprocess.TimeoutExpired:
            return {"exit_code": 124, "stdout": "", "stderr": "Toolchain command timed out."}
        except OSError:
            return {"exit_code": 126, "stdout": "", "stderr": "Cannot execute the toolchain."}

    version = run(["version", "-json"], 30)
    if version["exit_code"] != 0:
        return finish("BLOCKED_TOOLCHAIN", "Terraform version query failed")
    try:
        report["terraform_version"] = json.loads(version["stdout"])["terraform_version"]
    except (ValueError, KeyError, TypeError):
        return finish("BLOCKED_TOOLCHAIN", "Invalid Terraform version output")

    with tempfile.TemporaryDirectory(prefix="hosting-tf-check-") as temporary:
        work = Path(temporary) / "terraform"
        shutil.copytree(
            ROOT / "terraform", work,
            ignore=shutil.ignore_patterns(".terraform", "*.tfstate*", "*.tfplan", "*.tfvars", "*.tfvars.json"),
        )
        for family in ("modules", "roots"):
            for directory in sorted((work / family).iterdir()):
                if not directory.is_dir():
                    continue
                entry: dict[str, Any] = {
                    "name": directory.name, "validation": "NOT_RUN",
                    "mock_tests": "NOT_RUN" if family == "modules" else "NOT_APPLICABLE_ROOT",
                }
                init = run([f"-chdir={directory}", "init", "-backend=false", "-input=false"])
                if init["exit_code"] != 0:
                    entry.update(
                        validation="BLOCKED_INITIALIZATION", init_exit=init["exit_code"],
                        diagnostic=init["stderr"][-8000:],
                    )
                    report[family].append(entry)
                    continue
                check = run([f"-chdir={directory}", "validate", "-json"])
                try:
                    diagnostic = json.loads(check["stdout"])
                    valid = isinstance(diagnostic, dict) and diagnostic.get("valid") is True
                except ValueError:
                    diagnostic, valid = {"valid": False, "parse_error": True}, False
                entry["validation"] = "PASSED" if check["exit_code"] == 0 and valid else "FAILED"
                entry["validation_report"] = diagnostic
                if family == "modules" and args.mock_tests and entry["validation"] == "PASSED":
                    if not plan_only_mock_tests(directory):
                        entry["mock_tests"] = "BLOCKED_UNSAFE_OR_UNMOCKED_TEST_SOURCE"
                        report[family].append(entry)
                        continue
                    tested = run([f"-chdir={directory}", "test", "-no-color"], 300)
                    entry["mock_tests"] = "PASSED" if tested["exit_code"] == 0 else "FAILED"
                    entry["mock_output"] = tested["stdout"][-8000:]
                    entry["mock_exit"] = tested["exit_code"]
                schema_result = run([f"-chdir={directory}", "providers", "schema", "-json"])
                try:
                    schema = json.loads(schema_result["stdout"])
                    if schema_result["exit_code"] != 0 or not schema.get("provider_schemas"):
                        raise ValueError("Schema export unavailable")
                    destination = args.output.parent / "toolchain-schemas" / family / directory.name
                    destination.mkdir(parents=True, exist_ok=True)
                    schema_path = destination / "provider-schema.json"
                    schema_path.write_text(json.dumps(schema, indent=2) + "\n")
                    entry["schema_export"] = "EXPORTED_FROM_ACTUAL_PLUGINS"
                    entry["schema_sha256"] = hashlib.sha256(schema_path.read_bytes()).hexdigest()
                    report["schema_export"] = "SEE_PER_DIRECTORY_RESULTS"
                except (ValueError, TypeError):
                    entry["schema_export"] = "FAILED"
                lock = directory / ".terraform.lock.hcl"
                if lock.is_file():
                    destination = args.output.parent / "toolchain-locks" / family / directory.name
                    destination.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(lock, destination / lock.name)
                report[family].append(entry)

    validated = all(report[family] and all(item["validation"] == "PASSED" and item.get("schema_export") == "EXPORTED_FROM_ACTUAL_PLUGINS" for item in report[family])
                    for family in ("modules", "roots"))
    mocked = not args.mock_tests or all(item["mock_tests"] == "PASSED" for item in report["modules"])
    return finish("PASSED_TOOLCHAIN_ONLY" if validated and mocked else "INCOMPLETE_OR_FAILED_TOOLCHAIN")


if __name__ == "__main__":
    raise SystemExit(main())
