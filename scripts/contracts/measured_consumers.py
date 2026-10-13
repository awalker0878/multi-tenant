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
        # The locally exercised Lifecycle sender and installed receipt decoder
        # do not execute the external alert receiver. They prove only the
        # consumer boundary; never qualify an unavailable external producer.
        "contracts/schemas/lifecycle/alert-delivery-v1.json", ("consumer",)
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
        if (not observations or any(node.find(tag) is not None
                                    for node in observations
                                    for tag in ("skipped", "failure", "error"))):
            raise RuntimeError("Producer/consumer receipt includes skipped or failed tests")
        # Pytest JUnit identifies the actual executing module/class independently
        # of the test's short name. Another module with the same test name must
        # never be credited as a registered producer or consumer.
        executed = set()
        for node in observations:
            classname = node.attrib.get("classname", "")
            name = node.attrib.get("name", "")
            if not name:
                raise RuntimeError("Producer/consumer receipt has no test name: "
                                   + repr(node.attrib))
            # pytest --import-mode=importlib can emit classname="" for a
            # top-level test function. The subprocess received explicit test
            # selectors; such a receipt may count only when its *exact* test
            # name is unique among those selected. A nonempty classname must
            # still match the real module/class below.
            if not classname and sum(
                selector.rsplit("::", 1)[-1] == name for selector in cases
            ) != 1:
                raise RuntimeError("Ambiguous unqualified pytest test identity: " + name)
            identity = (classname, name)
            if identity in executed:
                raise RuntimeError("Duplicated producer/consumer execution receipt: " + repr(identity))
            executed.add(identity)
        for selector in cases:
            path, *parts = selector.split("::")
            if not parts:
                raise RuntimeError("Producer/consumer selector must name one executable test")
            classname = ".".join(Path(path).with_suffix("").parts)
            if len(parts) > 1:
                classname += "." + ".".join(parts[:-1])
            test_name = parts[-1]
            # Pytest importlib mode may abbreviate the module to its file
            # stem. An abbreviation is admissible only if that stem belongs
            # to one selected file and the test name is unique; never accept
            # an unrelated module that merely shares a test function name.
            module_stem = Path(path).stem
            stem_unique = len({
                candidate.split("::", 1)[0] for candidate in cases
                if Path(candidate.split("::", 1)[0]).stem == module_stem
            }) == 1
            name_unique = sum(
                candidate.rsplit("::", 1)[-1] == test_name for candidate in cases
            ) == 1
            selected_class = ".".join(parts[:-1])
            class_unique = bool(selected_class) and sum(
                "::".join(candidate.split("::")[1:-1]) == "::".join(parts[:-1])
                for candidate in cases
            ) == sum(
                candidate.split("::", 1)[0] == path
                and "::".join(candidate.split("::")[1:-1]) == "::".join(parts[:-1])
                for candidate in cases
            )
            def matches(candidate: str, name: str) -> bool:
                if not (name == test_name or name.startswith(test_name + "[")):
                    return False
                if candidate == classname:
                    return True
                if not name_unique or name != test_name:
                    return False
                if not candidate:
                    return True
                # Pytest may omit the module but preserve an explicitly
                # selected unittest.TestCase class. A unique class/test
                # selector is the only admissible abbreviated class identity.
                if (class_unique and candidate in {
                    "." + selected_class, selected_class
                }):
                    return True
                return (stem_unique and classname.endswith("." + candidate)
                        and candidate.split(".")[-1] == module_stem)
            if not any(matches(candidate, name) for candidate, name in executed):
                raise RuntimeError("Producer/consumer selector did not execute: " + selector
                                   + "; observed=" + repr(sorted(executed)))
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
