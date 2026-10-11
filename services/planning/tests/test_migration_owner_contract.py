"""Planning consumer contracts: no cross-context code imports.

Inventory producer integration is owned by tests/contracts/test_inventory_planning_contract.py.
"""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[3]


def test_active_inventory_v4_is_the_exact_installed_planning_schema() -> None:
    canonical = json.loads(
        (ROOT / "contracts/schemas/planning/migration-input-v4.json").read_text()
    )
    installed = json.loads(
        (ROOT / "services/planning/src/planning/infrastructure/inputs/migration-input-v4.json").read_text()
    )
    api = json.loads(
        (ROOT / "contracts/openapi/inventory-native-input-v1.2.json").read_text()
    )
    response = next(iter(api["paths"].values()))["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert canonical == installed == response
    Draft202012Validator.check_schema(installed)
    assert "collection_coverages" in installed["properties"]
    assert "source_associations" in installed["properties"]
