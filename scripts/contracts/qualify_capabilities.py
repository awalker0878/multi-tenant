"""Fail-closed Phase 4 E2 capability qualification from executed worker JUnit.

A catalogue entry, handler filename, string literal or generated type does not
qualify support. All method×mode runtime tests, every native data-operation
dispatch, cold capture, revocation and independent readback tests must pass.

E2 uses synthetic owner/platform peers and DOES NOT grant installed-version E3,
provider credentials, execution authority, or a production-ready migration.
"""
from __future__ import annotations

import argparse
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
    for testcase in tree.iter("testcase"):
        name = testcase.get("name")
        if not name:
            raise ValueError("JUnit contains unnamed test result")
        if any(testcase.find(tag) is not None for tag in ("failure", "error", "skipped")):
            raise ValueError("E2 capability qualification has failed/skipped test: " + name)
        items.append({"name": name, "classname": testcase.get("classname", "")})
    if not items:
        raise ValueError("JUnit has no actual executed tests")
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
        if not any(name.startswith(required) for name in names):
            raise ValueError("Missing mandatory native qualification execution: " + required)
    for method, record in methods.items():
        alias = record["v1_alias"]
        # The typed data-operation implementations are covered by their own
        # parameterized execution test, not merely the registry's file paths.
        if record["implementation"]["handler"].endswith("/migration_method.py"):
            for stage in {
                stage for stages in record["stages"].values() for stage in stages
            }:
                from_stage = [n for n in names if
                              n.startswith("test_protected_runtime_dispatches_exact_data_mechanism_in_every_direction[")
                              and alias in n and stage in n]
                # Only stages with an actual native data-operation handler
                # are checked by this dispatch test. Remaining stages are
                # checked by the stage matrix and native ownership controls.
                if stage in {
                    "capture", "restart_baseline_source", "export_copy",
                    "import_target", "final_sync", "reverse_sync",
                } and not from_stage:
                    # Verify against the canonical operation map, never a
                    # guessed stage applicability.
                    import ast
                    code = (root / record["implementation"]["handler"]).read_text()
                    module = ast.parse(code)
                    table = next((node.value for node in module.body
                                  if isinstance(node, ast.Assign)
                                  and any(isinstance(target, ast.Name)
                                          and target.id == "OPERATIONS"
                                          for target in node.targets)), None)
                    if table is None:
                        raise ValueError("Missing actual typed native dispatch table: " + method)
                    operations = ast.literal_eval(table)
                    if stage in operations.get(alias, {}):
                        raise ValueError("Native stage dispatch lacks executed evidence: " + method + "/" + stage)
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
