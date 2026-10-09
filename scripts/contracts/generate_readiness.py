"""Rebuild the Planning OpenAPI readiness component from canonical wire v2.

The stronger v2.1 validation profile is intentionally not a new payload
schema_version; no historical canonical contract may be overwritten here.
"""
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "contracts/schemas/planning/migration-readiness-v2.json"
FRAGMENT = (ROOT / "contracts/source/openapi/planning-migration-v1.6/"
            "components-schemas/workload-readiness.json")


def embedded_payload() -> dict:
    schema = deepcopy(json.loads(SOURCE.read_text(encoding="utf-8")))
    schema.pop("$id", None)
    schema.pop("$schema", None)

    def update_refs(value: object) -> None:
        if isinstance(value, list):
            for item in value:
                update_refs(item)
        elif isinstance(value, dict):
            reference = value.get("$ref")
            if isinstance(reference, str) and reference.startswith("#/$defs/"):
                value["$ref"] = (
                    "#/components/schemas/MigrationReadinessPayload/" + reference[2:]
                )
            for item in value.values():
                update_refs(item)

    update_refs(schema)
    return schema


def run(write: bool = False) -> None:
    fragment = json.loads(FRAGMENT.read_text(encoding="utf-8"))
    expected = embedded_payload()
    if write:
        fragment["MigrationReadinessPayload"] = expected
        FRAGMENT.write_text(json.dumps(fragment, indent=2) + "\n", encoding="utf-8")
    elif fragment["MigrationReadinessPayload"] != expected:
        raise ValueError("Planning readiness source projection is stale")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    run(args.write)
    print("Planning embedded wire readiness v2 matches canonical JSON Schema")
