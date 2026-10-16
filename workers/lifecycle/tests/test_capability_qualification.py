"""Executable E2 method/mode capability qualification matrix.

Every currently registered method/mode traverses the native worker's stage
contracts. Native data operations invoke the real contract and independent
readback validators with both positive and fail-closed evidence. This never
qualifies an installed site/provider tuple or grants native writes.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from test_method_protocol import measurement, method_plan

from lifecycle_worker.application.migration_runtime import MIGRATION_STAGES
from lifecycle_worker.application.native import NativeHeld
from lifecycle_worker.domain.capability_definitions import AFTER, BEFORE, STAGES
from lifecycle_worker.infrastructure.migration_method import OPERATIONS, contract, measured

ROOT = Path(__file__).resolve().parents[3]
DEFINITIONS = json.loads((ROOT / "contracts/capabilities/definitions-v1.json").read_text())
MATRIX = [(method, mode) for method in DEFINITIONS["methods"] for mode in DEFINITIONS["modes"]]


@pytest.mark.parametrize(
    ("method", "mode"),
    MATRIX,
    ids=[f"MATRIX_{method}__{mode}" for method, mode in MATRIX],
)
def test_current_capability_method_mode_execution_and_denial(method: str, mode: str) -> None:
    entry = DEFINITIONS["methods"][method]
    wire_method = entry["v1_alias"]
    declared = tuple(entry["stages"][mode])
    assert declared and tuple(STAGES[(mode, wire_method)]) == declared
    assert all(stage in MIGRATION_STAGES for stage in declared)
    assert all(BEFORE[stage] and AFTER[stage] for stage in declared)
    # Unlike filename/literal tests, this executes the worker's actual method
    # validators for every stage that requests native application/file/block IO.
    for stage in declared:
        operation = OPERATIONS.get(wire_method, {}).get(stage)
        if operation is None:
            continue
        plan = method_plan(wire_method, stage)
        native = contract(plan["method_contract"], stage)
        assert native["operation"] == operation
        observed = measurement(native)
        assert measured(observed, native, 100) == observed
        changed = copy.deepcopy(native)
        changed["operation"] = "uncommissioned_native_effect"
        with pytest.raises(NativeHeld):
            contract(changed, stage)
        foreign = copy.deepcopy(native)
        foreign["source"]["installation_id"] = native["target"]["installation_id"]
        with pytest.raises(NativeHeld):
            contract(foreign, stage)
        stale = copy.deepcopy(observed)
        next(iter(stale["datasets"].values()))["observed_at"] = 1
        with pytest.raises(NativeHeld):
            measured(stale, native, 100)


def test_current_definition_has_no_unqualified_method_mode_and_no_unknown_stage() -> None:
    assert len(MATRIX) == len(DEFINITIONS["methods"]) * len(DEFINITIONS["modes"])
    assert DEFINITIONS["methods"] and DEFINITIONS["modes"]
    assert all(
        entry["implementation_required"] is True for entry in DEFINITIONS["methods"].values()
    )
    assert all(
        set(entry["stages"]) == set(DEFINITIONS["modes"])
        for entry in DEFINITIONS["methods"].values()
    )
    current = {
        stage
        for entry in DEFINITIONS["methods"].values()
        for ordered in entry["stages"].values()
        for stage in ordered
    }
    assert current == MIGRATION_STAGES
