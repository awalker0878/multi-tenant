"""Earn current producer/consumer evidence by EXECUTING exact bounded tests.

Never award proof from a test filename, hard-coded fixture, test collection,
schema-byte equality, or an unexecuted check. The test must finish successfully.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
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
}


def verified_consumers(root: Path = ROOT) -> list[dict]:
    current = {operation["key"]: operation for operation in inventory(root)["operations"]}
    cases = list(TESTS)
    # The executed test includes independently exercised producer logic,
    # installed consumer validation, and changed-version/malformed rejections.
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--import-mode=importlib",
         "--strict-config", "-q", *cases],
        cwd=root, capture_output=True, text=True, timeout=180,
    )
    if result.returncode:
        raise RuntimeError("Exact producer/consumer qualification failed:\n"
                           + (result.stdout + result.stderr)[-9000:])
    evidence = []
    for test, (owner, method, path, claims) in TESTS.items():
        key = operation_key(owner, method, path)
        if key not in current:
            raise ValueError(f"Producer/consumer test does not target an active operation: {key}")
        for claim in claims:
            evidence.append({
                "key": key,
                "claim": claim,
                "source": "live-producer" if claim == "producer" else "live-consumer",
                "result": "PASS", "release_sha256": current[key]["release_sha256"],
                "test": test,
            })
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    evidence = verified_consumers()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"Validated {len(TESTS)} executable producer/consumer tests, "
          f"{len(evidence)} operation proofs")


if __name__ == "__main__":
    main()
