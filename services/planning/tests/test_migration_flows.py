"""An application owner may select observed native references, never assert evidence."""
from copy import deepcopy
from types import SimpleNamespace

import pytest
from planning_fixture import NOW, inputs
from planning.application.migration_flows import MigrationFlows
from planning.domain.model import Rejected
from planning.domain.network_evidence import native_application_flow_choices


def synthetic_current():
    intent, destination, _, policy, _ = inputs()
    native = deepcopy(destination["capability_snapshot"]["data"])
    native["network"]["observer_principal"] = "separately-verified-observer"
    choices = native_application_flow_choices(intent, native["network"], policy)
    return {
        "intent": intent, "destination": destination, "policy": policy,
        "data": native, "choices": choices,
        "context_sha256": "a" * 64,
        "expires_at": NOW + 120,
    }


def complete_selections(current):
    return [
        {
            "source_flow_id": c["source_flow_id"],
            "rule_native_ref": c["destination_firewall_rule_ids"][0],
            "route_native_ref": c["destination_route_ids"][0],
        }
        for c in current["choices"] if c["required"]
    ]


def test_owner_approved_flow_requirements_still_require_independent_traffic_and_isolation():
    current = synthetic_current()
    selected = complete_selections(current)
    assert MigrationFlows.evaluate(current, selected, NOW) == []
    missing = selected[:-1]
    assert "application_flow_required_selection_missing" in MigrationFlows.evaluate(
        current, missing, NOW)
    invalid = deepcopy(selected)
    invalid[0]["rule_native_ref"] = "manually-created-firewall-rule"
    with pytest.raises(Rejected, match="unobserved_application_flow_destination"):
        MigrationFlows.evaluate(current, invalid, NOW)
    duplicate = [selected[0], selected[0]]
    with pytest.raises(Rejected, match="unapproved_application_flow"):
        MigrationFlows.evaluate(current, duplicate, NOW)
    denied = deepcopy(current)
    denied["data"]["network"]["measurements"] = []
    assert any("flow" in h for h in MigrationFlows.evaluate(denied, selected, NOW))
    no_isolation = deepcopy(current)
    no_isolation["data"]["isolation"]["negative_flows"] = []
    assert MigrationFlows.evaluate(no_isolation, selected, NOW)
    same_observer = deepcopy(current)
    same_observer["data"]["network"]["observer_principal"] = "fixture-writer"
    assert MigrationFlows.evaluate(same_observer, selected, NOW) == [
        "independent_native_flow_observer_required"]


def test_flow_evidence_expiry_and_unknown_choices_remain_held():
    current = synthetic_current()
    assert MigrationFlows.evaluate(current, complete_selections(current), NOW + 121) == [
        "independent_native_flow_observer_required"]
    current["data"]["network"]["firewall_rules"] = []
    current["choices"] = native_application_flow_choices(
        current["intent"], current["data"]["network"], current["policy"])
    assert any(row["status"] == "held_unobserved" for row in current["choices"])
    with pytest.raises(Rejected, match="unobserved_application_flow_destination"):
        MigrationFlows.evaluate(current, [{
            "source_flow_id": row["source_flow_id"],
            "rule_native_ref": "unknown",
            "route_native_ref": "fixture://route",
        } for row in current["choices"]], NOW)


def test_source_intent_or_destination_changes_invalidate_saved_owner_selections():
    current = synthetic_current()
    saved = {
        "context_sha256": "b" * 64,
        "revision": 3,
        "payload": {"selections": complete_selections(current)},
        "updated_at": NOW,
    }
    class Database:
        def transaction(self):
            from contextlib import nullcontext
            return nullcontext(self)
        def one(self, sql, params):
            return saved
    flows = MigrationFlows(SimpleNamespace(database=Database(), clock=lambda: NOW))
    flows.current = lambda actor, site, token: current
    from planning.domain.model import Actor
    actor = Actor("10000000-0000-4000-8000-000000000001",
                  "10000000-0000-4000-8000-000000000002",
                  "plan.read",
                  "10000000-0000-4000-8000-000000000003",
                  "10000000-0000-4000-8000-000000000004")
    result = flows.read(actor, "10000000-0000-4000-8000-000000000005", "delegation")
    assert result["status"] == "invalidated"
    assert result["selections"] == []
    assert "application_flow_evidence_changed" in result["holds"]
    assert result["revision"] == 3
    assert result["native_write_authorized"] is False


def test_optional_application_dependency_cannot_be_silently_discarded() -> None:
    current = synthetic_current()
    required = complete_selections(current)
    optional = deepcopy(current["choices"][0])
    optional["source_flow_id"] = "b" * 64
    optional["required"] = False
    current["choices"].append(optional)
    assert MigrationFlows.evaluate(current, required, NOW) == [
        "application_flow_optional_omission_declaration_required"
    ]
    omission = [{"source_flow_id": optional["source_flow_id"],
                 "reason_code": "replaced_by_native_service"}]
    assert MigrationFlows.evaluate(current, required, NOW, omission) == [
        "application_flow_optional_omission_approval_required"
    ]
