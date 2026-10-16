#!/usr/bin/env python3
"""Run exact owner-boundary integration tests and retain fail-closed JUnit receipts.

This is diagnostic runtime evidence ONLY. Never award producer/consumer qualification
from a passing test without validating the exact active contract and installed consumer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

CONFIG = {
    "governance": {
        "directory": "services/governance",
        "source": "tests/Feature/ContractBoundaryExecutionTest.php",
        "command": ["vendor/bin/pest", "tests/Feature/ContractBoundaryExecutionTest.php", "--log-junit={receipt}"],
        "expected_name": "executes governance tenant-directory and denies a foreign tenant to the same actor",
    },
    "inventory": {
        "directory": "services/inventory",
        "source": "tests/test_contract_boundary_execution.py",
        "command": ["uv", "run", "--locked", "--no-sync", "pytest", "-q", "tests/test_contract_boundary_execution.py", "--junitxml={receipt}"],
        "expected_name": "test_inventory_operator_readiness_owner_tenant_and_authority_boundaries",
    },
}


def verify_receipt(receipt: Path, service: str) -> dict:
    root = ET.parse(receipt).getroot()
    cases = list(root.iter("testcase"))
    if len(cases) != 1:
        raise ValueError(f"Expected exactly one JUnit testcase; got {len(cases)}")
    case = cases[0]
    if any(case.find(tag) is not None for tag in ("error", "failure", "skipped")):
        raise ValueError("JUnit reported error/failure/skip")
    name = case.attrib.get("name", "")
    expected = CONFIG[service]["expected_name"]
    if service == "inventory":
        matching = name == expected
    else:
        # Pest may prefix descriptive test names with 'it '.
        matching = name == expected or name == "it " + expected
    if not matching:
        raise ValueError(f"Unexpected JUnit test identity: {name!r}")
    suite_summary = root.attrib if root.tag == "testsuite" else {}
    return {
        "test_name": name,
        "classname": case.attrib.get("classname"),
        "testsuite": suite_summary.get("name"),
        "receipt_sha256": hashlib.sha256(receipt.read_bytes()).hexdigest(),
        "testcases": len(cases),
    }


def run(root: Path, output: Path, service: str) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)
    results = {
        "qualification_awarded": False,
        "status": "BLOCKED",
        "revision": os.getenv("GITHUB_SHA"),
        "run_id": os.getenv("GITHUB_RUN_ID"),
        "run_attempt": os.getenv("GITHUB_RUN_ATTEMPT"),
        "services": {},
    }
    selected = list(CONFIG) if service == "all" else [service]
    ci = os.getenv("GITHUB_ACTIONS") == "true"
    runner_temp = os.getenv("RUNNER_TEMP")
    stage_root = Path(runner_temp) / "quality/staged" if ci and runner_temp else root
    report_file = Path(runner_temp) / "quality/evidence/report.json" if ci and runner_temp else None
    for owner in selected:
        entry = CONFIG[owner]
        cwd = stage_root / entry["directory"]
        source = cwd / entry["source"]
        checkout_source = root / entry["directory"] / entry["source"]
        receipt = output.parent / (owner + "-owner-junit.xml")
        receipt.unlink(missing_ok=True)
        state = {"status": "BLOCKED"}
        missing = [str(p) for p in (root / ".git", source, checkout_source) if not p.exists()]
        if ci and not runner_temp:
            missing.append("RUNNER_TEMP")
        if ci and report_file and not report_file.is_file():
            missing.append(str(report_file))
        if owner == "governance" and not (cwd / "vendor/bin/pest").is_file():
            missing.append(str(cwd / "vendor/bin/pest"))
        if owner == "inventory" and not (cwd / ".venv/bin/pytest").is_file():
            missing.append(str(cwd / ".venv/bin/pytest"))
        if missing:
            state["missing"] = missing
        elif ci:
            try:
                quality = json.loads(report_file.read_text())  # type: ignore[union-attr]
                relative = str(checkout_source.relative_to(root))
                recorded = quality["source_sha256"][relative]
                staged_hash = hashlib.sha256(source.read_bytes()).hexdigest()
                checkout_hash = hashlib.sha256(checkout_source.read_bytes()).hexdigest()
                identity = all((
                    quality.get("component") == owner,
                    quality.get("result") == "PASS",
                    quality.get("run_id") == os.getenv("GITHUB_RUN_ID"),
                    quality.get("run_attempt") == os.getenv("GITHUB_RUN_ATTEMPT"),
                    quality.get("source_sha") == os.getenv("GITHUB_SHA"),
                    recorded == staged_hash == checkout_hash,
                ))
                if not identity:
                    state["reason"] = "Isolated quality source/commit/run evidence mismatch"
            except (OSError, ValueError, KeyError, TypeError) as error:
                state["reason"] = "Invalid isolated quality manifest: " + type(error).__name__
        if not missing and not state.get("reason"):
            command = [arg.replace("{receipt}", str(receipt)) for arg in entry["command"]]
            try:
                proc = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=600)
                state.update({
                    "status": "FAILED", "exit_code": proc.returncode,
                    "log_tail": (proc.stdout + proc.stderr)[-12000:],
                })
                if proc.returncode == 0:
                    if receipt.is_file():
                        try:
                            state.update(verify_receipt(receipt, owner))
                            state["status"] = "PASSED"
                            state["receipt"] = str(receipt)
                        except (ET.ParseError, ValueError) as error:
                            state["reason"] = str(error)
                    else:
                        state["reason"] = "JUnit missing despite successful exit"
            except (OSError, subprocess.TimeoutExpired) as error:
                state["reason"] = type(error).__name__
        results["services"][owner] = state
    if all(x.get("status") == "PASSED" for x in results["services"].values()):
        results["status"] = "OWNER_TESTS_PASSED_NOT_QUALIFIED"
    else:
        results["status"] = "FAILED_OR_BLOCKED"
    output.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))
    return 0 if results["status"] == "OWNER_TESTS_PASSED_NOT_QUALIFIED" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--service", choices=(*CONFIG, "all"), default="all")
    args = parser.parse_args()
    return run(args.root.resolve(), args.output.resolve(), args.service)


if __name__ == "__main__":
    sys.exit(main())
