"""Earn current producer/consumer evidence by EXECUTING exact bounded tests.

Never award proof from a test filename, hard-coded fixture, test collection,
schema-byte equality, or an unexecuted check. The test must finish successfully.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from xml.etree import ElementTree
from pathlib import Path

from assurance import inventory, operation_key

ROOT = Path(__file__).resolve().parents[2]
TESTS = {
    "tests/contracts/test_inventory_planning_contract.py::"
    "test_real_inventory_planning_response_validates_installed_strict_schema": (
        ("inventory", "GET",
         "/internal/tenants/{tenant}/migration-inputs/"
         "{application}/{environment}/{site}/{revision}/{digest}",
         ("producer", "consumer")),
    ),
    "services/planning/tests/test_owner_operation_contracts.py::"
    "test_real_owner_transport_validates_qualified_assurance_response": (
        ("assurance", "POST",
         "/v1/tenants/{tenant}/migration-qualifications", ("consumer",)),
    ),
    "services/planning/tests/test_owner_operation_contracts.py::"
    "test_catalogue_current_owner_response_uses_real_published_intent": (
        ("catalogue", "GET",
         "/internal/tenants/{tenant}/applications/{application}/"
         "environments/{environment}/current-planning-intent", ("consumer",)),
    ),
    "services/planning/tests/test_owner_operation_contracts.py::"
    "test_capacity_and_governance_owner_responses_are_schema_and_scope_validated": (
        ("governance", "POST", "/v1/tenants/{tenant}/delegated-authorizations", ("consumer",)),
    ),
    "tests/contracts/test_authority_boundaries.py::"
    "OwnerBoundaryContracts::test_real_asgi_owner_and_planning_consumer_roundtrip": (
        ("lifecycle", "POST",
         "/internal/tenants/{tenant}/placement-reservations/checks", ("producer", "consumer")),
    ),
    "tests/contracts/test_authority_boundaries.py::"
    "OwnerBoundaryContracts::test_all_placement_owner_operations_use_strict_openapi": (
        ("lifecycle", "POST",
         "/internal/tenants/{tenant}/placement-reservations/reserve", ("producer",)),
        ("lifecycle", "POST",
         "/internal/tenants/{tenant}/placement-reservations/confirm", ("producer",)),
        ("lifecycle", "POST",
         "/internal/tenants/{tenant}/placement-reservations/renew", ("producer",)),
        ("lifecycle", "POST",
         "/internal/tenants/{tenant}/placement-reservations/release", ("producer",)),
    ),
    "tests/contracts/test_authority_boundaries.py::"
    "LifecycleOwnerTransportContracts::test_real_lifecycle_consumer_validates_current_assurance_receipt": (
        ("assurance", "POST", "/v1/tenants/{tenant}/evidence-uploads", ("consumer",)),
    ),
    "tests/contracts/test_authority_boundaries.py::"
    "LifecycleOwnerTransportContracts::test_planning_execution_plan_asgi_response_reaches_lifecycle_installed_validator": (
        ("planning", "GET",
         "/v1/tenants/{tenant}/execution-plans/{plan}/revisions/{revision}",
         ("consumer",)),
    ),
    "tests/contracts/test_simulation_owner.py::"
    "SimulationOwnerContracts::test_authenticated_worker_and_lifecycle_consumer": (
        ("lifecycle-workers", "POST", "/v1/effects", ("route", "producer", "consumer", "authorization")),
        ("lifecycle-workers", "POST", "/v1/reconciliations", ("route", "producer", "consumer", "authorization")),
    ),
    "tests/contracts/test_simulation_owner.py::"
    "SimulationOwnerContracts::test_independent_observation_audience_and_payload": (
        ("lifecycle-workers", "POST", "/v1/observations", ("route", "producer", "authorization")),
    ),
}


# Non-HTTP proof is earned only by a single test exercising both live sides.
RELEASE_TESTS = {
    "tests/contracts/test_authority_boundaries.py::"
    "OwnerBoundaryContracts::test_real_asgi_owner_and_planning_consumer_roundtrip": (
        "contracts/schemas/planning/placement-reservation-v1.json", ("producer", "consumer")
    ),
    "tests/contracts/test_alert_owner.py::"
    "AlertOwnerContracts::test_installed_alert_contract_fences_external_receipts": (
        "contracts/schemas/lifecycle/alert-delivery-v1.json", ("producer", "consumer")
    ),
    "tests/contracts/test_inventory_planning_contract.py::"
    "test_real_inventory_planning_response_validates_installed_strict_schema": (
        "contracts/schemas/planning/migration-input-v4.json", ("producer", "consumer")
    ),
    "services/planning/tests/test_owner_operation_contracts.py::"
    "test_capacity_and_governance_owner_responses_are_schema_and_scope_validated": (
        "contracts/schemas/planning/governance-delegation-response-v2.json", ("consumer",)
    ),
}


def verified_consumers(root: Path = ROOT) -> list[dict]:
    current = {operation["key"]: operation for operation in inventory(root)["operations"]}
    cases = sorted(set(TESTS) | set(RELEASE_TESTS))
    # The executed test includes independently exercised producer logic,
    # installed consumer validation, and changed-version/malformed rejections.
    with tempfile.TemporaryDirectory(prefix="contract-consumer-") as temporary:
        receipt = Path(temporary) / "measured-junit.xml"
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--import-mode=importlib",
             "--strict-config", "-q", f"--junitxml={receipt}", *cases],
            cwd=root, capture_output=True, text=True, timeout=180,
        )
        if result.returncode:
            raise RuntimeError("Exact producer/consumer qualification failed:\n"
                               + (result.stdout + result.stderr)[-9000:])
        # pytest exits zero for skipped/xfail cases. Such cases did not prove
        # their contract; every selector must have a passing JUnit testcase.
        try:
            suites = ElementTree.parse(receipt)
            observations = list(suites.iter("testcase"))
        except (OSError, ElementTree.ParseError) as exc:
            raise RuntimeError("Missing valid producer/consumer execution receipts") from exc
        names = [node.attrib.get("name", "") for node in observations]
        if (not observations or any(node.find(tag) is not None
                                    for node in observations
                                    for tag in ("skipped", "failure", "error"))):
            raise RuntimeError("Producer/consumer receipt includes skipped or failed tests")
        for selector in cases:
            test_name = selector.rsplit("::", 1)[-1]
            if not any(name == test_name or name.startswith(test_name + "[")
                       for name in names):
                raise RuntimeError("Producer/consumer selector did not execute: " + selector)
    evidence = []
    for test, bindings in TESTS.items():
        for owner, method, path, claims in bindings:
            key = operation_key(owner, method, path)
            if key not in current:
                raise ValueError(f"Producer/consumer test does not target an active operation: {key}")
            for claim in claims:
                evidence.append({
                    "key": key,
                    "claim": claim,
                    "source": {"route": "live-router", "producer": "live-producer",
                               "consumer": "live-consumer",
                               "authorization": "live-denial"}[claim],
                    "result": "PASS", "release_sha256": current[key]["release_sha256"],
                    "test": test,
                    **({"denial_kind": "invalid-credential", "status_code": 403}
                       if claim == "authorization" else {}),
                })
    releases = {release["path"]: release for release in inventory(root)["releases"]}
    for test, (path, claims) in RELEASE_TESTS.items():
        if path not in releases:
            raise ValueError("Non-HTTP test targets an inactive release: " + path)
        for claim in claims:
            evidence.append({
                "key": path, "claim": claim,
                "source": "live-producer" if claim == "producer" else "live-consumer",
                "result": "PASS", "release_sha256": releases[path]["sha256"], "test": test,
            })
    for observation in evidence:
        observation["run_id"] = os.environ.get("GITHUB_RUN_ID")
        observation["revision"] = os.environ.get("GITHUB_SHA")
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    evidence = verified_consumers()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"Validated {len(set(TESTS) | set(RELEASE_TESTS))} executable producer/consumer tests, "
          f"{len(evidence)} operation proofs")


if __name__ == "__main__":
    main()
