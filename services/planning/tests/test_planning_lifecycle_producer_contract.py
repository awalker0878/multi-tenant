"""Real Planning producer methods against the registered Lifecycle read contracts.

This uses deterministic owned records and placement inputs, not a mocked
PlanningApp response. A validated read is not a native execution grant.
"""
from __future__ import annotations

import json
from contextlib import nullcontext
from pathlib import Path
from typing import Any, cast
from unittest.mock import Mock

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from planning.application.planning import Planning
from planning.application.ports import Database, Sources
from planning.application.validation import PlanValidation
from planning.domain.model import Rejected, digest


ROOT = Path(__file__).resolve().parents[3]


def test_real_execution_and_placement_producers_match_lifecycle_wire() -> None:
    fixture = json.loads(
        (ROOT / "contracts/fixtures/planning/synthetic-plan-v1.1.json").read_text()
    )
    native = json.loads(
        (ROOT / "contracts/fixtures/planning/synthetic-inputs-v1.json").read_text()
    )
    api = json.loads(
        (ROOT / "contracts/openapi/planning-lifecycle-reads-v1.json").read_text()
    )
    content, binding = fixture["content"], fixture["binding"]
    tenant, identity = content["scope"]["tenant_id"], binding["plan_id"]
    policy = {"allowed_zones": ["zone-a", "zone-b"]}
    zero = {
        "vcpus": 0, "memory_mib": 0, "storage_gib": 0,
        "addresses": 0, "storage_gib:standard": 0, "addresses:private:ipv4": 0,
    }
    capacity = {
        "vcpus": 8, "memory_mib": 32768, "storage_gib": 200,
        "addresses": 8, "storage_gib:standard": 200, "addresses:private:ipv4": 8,
    }
    pools = [
        {
            "id": "pool-" + zone, "native_ref": "native-" + zone,
            "failure_domain": "domain-" + zone,
            "zone": zone, "ledger_revision": 1,
            "policy_sha256": digest(policy), "architecture": "x86_64",
            "storage_classes": ["standard"], "network_classes": ["private"],
            "total": capacity, "used": zero, "pending": zero,
        }
        for zone in policy["allowed_zones"]
    ]
    record = {
        "id": identity, "assessment_id": content["intent_revision"],
        "candidate": 0, "content": content, "binding": binding,
    }
    assessment = {
        "intent": {"intent": native["intent"]},
        "inputs": [{"destination": {"capability_snapshot": {"data": {"pools": pools}}},
                    "policy": policy}],
    }
    qualification = {"scope_sha256": "a" * 64, "state": "qualified", "invalidated": False}

    class Transaction:
        def one(self, query: str, params: tuple[Any, ...]) -> dict[str, Any]:
            if "planning_plan_qualification_scopes" in query:
                return qualification
            if "kind='assessment'" in query:
                return {"payload": assessment}
            return {"payload": record}

    class TestDatabase:
        def transaction(self) -> Any:
            return nullcontext(Transaction())

    now = lambda: 1000
    planning = Planning(
        cast(Database, TestDatabase()), cast(Sources, Mock()),
        now, PlanValidation.unavailable(now),
    )
    response = planning.execution_plan(tenant, identity, 1)
    proposal = planning.placement_proposal(tenant, identity, 1)
    assert response["invalidated"] is False
    assert proposal["native_write_authorized"] is False
    assert len(proposal["allocations"]) == len(native["intent"]["workloads"])
    format_checker = FormatChecker()
    for key, value in (("ExecutionPlan", response), ("PlacementProposal", proposal)):
        validator = Draft202012Validator(
            {"$ref": "#/components/schemas/" + key, "components": api["components"]},
            format_checker=format_checker,
        )
        validator.validate(value)
        assert not validator.is_valid(value | {"native_write_authorized": True})

    # Revoke the independent qualification head. Neither read may succeed,
    # even if an immutable historical plan and placement inputs still exist.
    qualification["state"] = "revoked"
    with pytest.raises(Rejected):
        planning.execution_plan(tenant, identity, 1)
    with pytest.raises(Rejected):
        planning.placement_proposal(tenant, identity, 1)
