"""Emit route evidence only after running the real service-owned conformance probe."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from assurance import inventory, operation_key
from route_conformance import (
    routes_in_laravel, verify_app, verify_inventory, verify_lifecycle_native,
    verify_planning_immutable, verify_planning_lifecycle_reads,
    verify_planning_migration, verify_python_composition,
)

ROOT = Path(__file__).resolve().parents[2]
CHECKED = {
    "inventory": {
        "contracts/openapi/inventory-v1.9.json",
        "contracts/openapi/inventory-collection-worker-v1.json",
        "contracts/openapi/inventory-native-input-v1.3.json",
    },
    "python-composed": {
        "contracts/openapi/planning-v1.2.json",
        "contracts/openapi/planning-migration-v1.6.json",
        "contracts/openapi/planning-native-v1.json",
        "contracts/openapi/planning-immutable-plan-v1.1.json",
        "contracts/openapi/planning-lifecycle-reads-v1.json",
        "contracts/openapi/planning-qualification-events-v1.json",
        "contracts/openapi/lifecycle-v1.json",
        "contracts/openapi/lifecycle-migration-campaigns-v1.json",
        "contracts/openapi/lifecycle-internal-authority-v1.json",
    },
    "lifecycle-native": {"contracts/openapi/lifecycle-migration-boundary-v2.json"},
    "planning-immutable": {"contracts/openapi/planning-immutable-plan-v1.1.json"},
    "planning-lifecycle": {"contracts/openapi/planning-lifecycle-reads-v1.json"},
    "planning-migration": {"contracts/openapi/planning-migration-v1.6.json"},
}
CHECKS = {
    "inventory": verify_inventory,
    "python-composed": verify_python_composition,
    "lifecycle-native": verify_lifecycle_native,
    "planning-immutable": verify_planning_immutable,
    "planning-lifecycle": verify_planning_lifecycle_reads,
    "planning-migration": verify_planning_migration,
}


def prove(app: str, route_list: Path | None = None, root: Path = ROOT,
          producer_only: bool = False) -> list[dict]:
    data = inventory(root)
    if app in {"catalogue", "governance", "assurance"}:
        if route_list is None:
            raise ValueError("Laravel router evidence must come from an actual route:list capture")
        runtime = routes_in_laravel(json.loads(route_list.read_text()))
        verify_app(app, runtime, root)
        observed = {(app, verb, path) for verb, path in runtime}
        matched = [
            op for op in data["operations"]
            if (op["owner"], op["method"], op["path"]) in observed
        ]
        if any(op["owner"] == app and op not in matched for op in data["operations"]):
            raise ValueError(f"Incomplete Laravel route evidence: {app}")
        check_name = "route_conformance.verify_app"
    else:
        if app not in CHECKS:
            raise ValueError(f"No executable route verifier for {app}")
        # This call must succeed BEFORE evidence is emitted.
        CHECKS[app](root)
        matched = [op for op in data["operations"] if op["release"] in CHECKED[app]]
        if not matched:
            raise ValueError(f"Empty verified route group: {app}")
        check_name = "route_conformance." + CHECKS[app].__name__
    if producer_only and app not in {"planning-immutable", "planning-lifecycle"}:
        raise ValueError("No independent positive producer validator for: " + app)
    # These probes issue actual ASGI requests with controlled owner fixtures,
    # then validate exact returned JSON against the current response schemas.
    # Structural route matching alone is NEVER promoted to producer evidence.
    positive_probes = {"lifecycle-native", "planning-immutable", "planning-lifecycle"}
    rows = []
    for op in matched:
        key = operation_key(op["owner"], op["method"], op["path"])
        if not producer_only:
            rows.append({
                "key": key, "claim": "route", "source": "live-router",
                "result": "PASS", "release_sha256": op["release_sha256"],
                "test": check_name,
            })
        if app in positive_probes:
            rows.append({
                "key": key, "claim": "producer", "source": "live-producer",
                "result": "PASS", "release_sha256": op["release_sha256"],
                "test": check_name + ":actual_ASGI_200_validated",
            })
            if app == "planning-lifecycle":
                rows.append({
                    "key": key, "claim": "authorization", "source": "live-denial",
                    "result": "PASS", "release_sha256": op["release_sha256"],
                    "test": check_name + ":invalid_workload_403",
                })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", required=True)
    parser.add_argument("--routes", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--producer-only", action="store_true")
    args = parser.parse_args()
    evidence = prove(args.app, args.routes, producer_only=args.producer_only)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"{args.app}: {len(evidence)} executable routes verified")


if __name__ == "__main__":
    main()
