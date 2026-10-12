"""Fail-closed Phase 4 E2 capability qualification from executed worker JUnit.

A catalogue entry, handler filename, string literal or generated type does not
qualify support. All method×mode runtime tests, every native data-operation
dispatch, cold capture, revocation and independent readback tests must pass.

E2 uses synthetic owner/platform peers and DOES NOT grant installed-version E3,
provider credentials, execution authority, or a production-ready migration.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
MANDATORY = (
    "test_cold_capture_includes_root_and_every_volume_without_uploading_production_volume",
    "test_capture_failure_retains_partial_receipts_and_never_replays",
    "test_mismatched_data_method_is_held_before_native_submission",
    "test_independent_dataset_readback_enforces_every_limit",
    "test_data_method_tls_effect_and_independent_readback_are_separate",
    "test_inflight_registry_revocation_stops_the_next_effect_boundary",
)


def tests_from_xml(path: Path) -> list[dict]:
    if not path.is_file():
        raise ValueError("Worker JUnit execution evidence missing: " + str(path))
    tree = ET.parse(path)
    items = []
    seen = set()
    suites = list(tree.iter("testsuite"))
    if not suites:
        raise ValueError("JUnit contains no executed test suite")
    for suite in suites:
        for status in ("failures", "errors", "skipped"):
            if int(suite.get(status, "0")):
                raise ValueError("E2 qualification JUnit suite reports " + status)
    for testcase in tree.iter("testcase"):
        name = testcase.get("name")
        classname = testcase.get("classname")
        if not name or not classname:
            raise ValueError("JUnit contains unnamed or unowned test result")
        if any(testcase.find(tag) is not None for tag in ("failure", "error", "skipped")):
            raise ValueError("E2 capability qualification has failed/skipped test: " + name)
        identity = (classname, name)
        if identity in seen:
            raise ValueError("Duplicate JUnit execution identity: " + name)
        seen.add(identity)
        items.append({"name": name, "classname": classname})
    if not items:
        raise ValueError("JUnit has no actual executed tests")
    if sum(int(suite.get("tests", len(items))) for suite in suites) < len(items):
        raise ValueError("JUnit test totals do not match actual testcases")
    return items


def qualify(root: Path, xml: Path) -> dict:
    source = root / "contracts/capabilities/definitions-v1.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    observed = tests_from_xml(xml)
    names = [case["name"] for case in observed]
    methods = data["methods"]
    modes = data["modes"]
    expected = [(method, mode) for method in methods for mode in modes]
    matrix = {}
    for method, mode in expected:
        marker = "test_current_capability_method_mode_execution_and_denial[MATRIX_" + method + "__" + mode + "]"
        hits = [case for case in observed if case["name"] == marker]
        if len(hits) != 1 or "test_capability_qualification" not in hits[0]["classname"]:
            raise ValueError("Missing executed method/mode qualification: " + method + "/" + mode)
        matrix[method + ":" + mode] = {
            "method": method, "mode": mode, "test": marker,
            "stages": data["methods"][method]["stages"][mode],
            "positive_native_contract": True,
            "negative_native_contract": True,
            "installed_provider_qualified": False,
        }
    for required in MANDATORY:
        if not any(case["name"].split("[", 1)[0] == required
                   and "test_" in case["classname"] for case in observed):
            raise ValueError("Missing mandatory native qualification execution: " + required)
    # Independently prove every typed operation across ALL nine native
    # source/target platform directions. A substring match is not evidence.
    fault_cases = {
        "test_mismatched_data_method_is_held_before_native_submission": {
            "operation", "platform", "same_environment", "mechanism",
            "dataset", "predecessor", "reverse", "parameters",
        },
    }
    for test, expected_faults in fault_cases.items():
        actual = {
            case["name"].removeprefix(test + "[").removesuffix("]")
            for case in observed
            if case["name"].startswith(test + "[")
            and "test_method_protocol" in case["classname"]
        }
        if actual != expected_faults:
            raise ValueError("Incomplete native negative cases: " + test)
    readback = [
        case for case in observed
        if case["name"].startswith("test_independent_dataset_readback_enforces_every_limit[")
        and "test_method_protocol" in case["classname"]
    ]
    if len(readback) != 12:
        raise ValueError("Incomplete independent readback denial matrix")
    for method, record in methods.items():
        handler_path = record["implementation"]["handler"]
        if not handler_path.endswith("/migration_method.py"):
            continue
        module = ast.parse((root / handler_path).read_text())
        node = next((n.value for n in module.body
                     if isinstance(n, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id == "OPERATIONS"
                             for t in n.targets)), None)
        if node is None:
            raise ValueError("Missing typed native dispatch table: " + method)
        implementations = ast.literal_eval(node)
        alias = record["v1_alias"]
        for stage in implementations.get(alias, {}):
            if not any(stage in rows for rows in record["stages"].values()):
                raise ValueError("Unreachable native stage implementation: " + method + "/" + stage)
            for source_platform in data["platforms"]:
                for target_platform in data["platforms"]:
                    case_name = (
                        "test_protected_runtime_dispatches_exact_data_mechanism_in_every_direction"
                        f"[{alias}-{stage}-{source_platform}-{target_platform}]"
                    )
                    hits = [case for case in observed
                            if case["name"] == case_name
                            and "test_method_protocol" in case["classname"]]
                    if len(hits) != 1:
                        raise ValueError("Native stage dispatch lacks executed evidence: "
                                         + method + "/" + stage + "/"
                                         + source_platform + "/" + target_platform)
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root,
                                        text=True, timeout=15).strip()
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("Invalid source revision for qualification")
    return {
        "schema_version": 1,
        "evidence_level": "E2",
        "source_revision": revision,
        "definition_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "worker_junit_sha256": hashlib.sha256(xml.read_bytes()).hexdigest(),
        "all_tests_passed": True,
        "method_count": len(methods), "mode_count": len(modes),
        "qualified_method_modes": len(matrix),
        "expected_method_modes": len(expected),
        "native_platforms_tested": [],
        "installed_provider_qualified": False,
        "native_write_authorized": False,
        "matrix": matrix,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker-junit", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = qualify(ROOT, args.worker_junit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in (
        "evidence_level", "method_count", "mode_count",
        "qualified_method_modes", "installed_provider_qualified"
    )}, sort_keys=True))


if __name__ == "__main__":
    main()
