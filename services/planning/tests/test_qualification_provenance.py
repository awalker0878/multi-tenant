"""A01/A02/A03/A10: trusted positive results require current resolved record provenance."""

import pytest
from planning_fixture import NOW, inputs

from planning.domain.assessment import assess


@pytest.mark.parametrize(
    "fault",
    ["legacy", "reference_only", "tampered", "definition", "runtime_expired", "cached", "future"],
)
def test_asserted_or_stale_qualification_never_becomes_eligible(fault: str) -> None:
    intent, destination, profile, policy, qualification = inputs()
    if fault == "legacy":
        qualification["version"] = 1
    elif fault == "reference_only":
        del qualification["verification"]
    elif fault == "tampered":
        qualification["capabilities"]["guest.image"]["values"].append("unreviewed-image")
    elif fault == "definition":
        qualification["verification"]["definition_sha256"] = "f" * 64
    elif fault == "runtime_expired":
        qualification["verification"]["expires_at"] = NOW
    elif fault == "cached":
        qualification["verification"]["resolved_at"] = NOW - 6
    else:
        qualification["verification"]["resolved_at"] = NOW + 1
    result = assess(
        intent,
        destination,
        profile,
        policy,
        qualification,
        "application.provision",
        "native_api",
        NOW,
    )
    assert result["operationally_eligible"] is False
    assert result["reserved"] is False


def test_runtime_observation_validity_bounds_the_next_plan() -> None:
    intent, destination, profile, policy, qualification = inputs()
    qualification["verification"]["expires_at"] = NOW + 15
    result = assess(
        intent,
        destination,
        profile,
        policy,
        qualification,
        "application.provision",
        "native_api",
        NOW,
    )
    assert result["operationally_eligible"] is True
    assert result["expires_at"] == NOW + 15


def test_unattended_plan_read_holds_when_current_owner_revokes_support() -> None:
    from unittest.mock import MagicMock, Mock

    from test_native_plans import native_values

    from planning.application.planning import Planning
    from planning.application.validation import (
        MigrationValidation,
        NativeValidation,
        PlanValidation,
    )
    from planning.domain.model import Rejected
    from planning.domain.native_plan import compose_native

    base, recipe = native_values()
    content = compose_native(base, recipe, 1000)
    content["native_provisioning"]["recipe_id"] = "selected"
    recipes = Mock(return_value=recipe)
    support = Mock(side_effect=Rejected("current_qualification_required", 423))
    clock = Mock(return_value=1000)
    validation = PlanValidation(
        NativeValidation(recipes, clock),
        MigrationValidation(Mock(), Mock(), Mock(), clock),
        support,
    )
    planner = Planning(MagicMock(), Mock(), clock, validation)
    with pytest.raises(Rejected, match="current_qualification_required"):
        planner.check_native_recipe({"content": content, "binding": {"requested_by": "actor"}})
    recipes.assert_not_called()


def test_runtime_refresh_does_not_change_the_reviewed_record_binding() -> None:
    from copy import deepcopy

    from planning.domain.qualification import binding_digest, verified

    record = inputs()[4]
    refreshed = deepcopy(record)
    refreshed["verification"].update(resolved_at=NOW + 2, runtime_sha256="c" * 64)
    assert binding_digest(record) == binding_digest(refreshed)
    assert verified(refreshed, NOW + 2)
    assert not verified(record, NOW + 6)
    refreshed["verification"]["decision_sha256"] = "d" * 64
    assert binding_digest(record) != binding_digest(refreshed)


def test_current_observation_renewal_preserves_semantics_but_never_freshness() -> None:
    from copy import deepcopy

    from planning.domain.operational_evidence import inventory_digest

    intent, destination, profile, policy, qualification = inputs()
    original = deepcopy(destination)
    renewed = deepcopy(destination)
    data = renewed["capability_snapshot"]["data"]
    network = data["network"]
    observations = [data["isolation"], *data["isolation"]["boundary_controls"].values()]
    observations += network["measurements"] + network["return_paths"]
    observations += list(network["application_flow_selections"].values())
    observations += data["recovery_measurements"]
    for row in [renewed["capability_snapshot"], *observations]:
        row.update(observed_at=NOW + 30, expires_at=NOW + 150)
    renewed["capability_snapshot"]["source_sha256"] = "c" * 64
    qualification["verification"].update(resolved_at=NOW + 30, runtime_sha256="c" * 64)
    assert inventory_digest(destination) == inventory_digest(renewed)
    assert destination == original
    assert assess(
        intent,
        renewed,
        profile,
        policy,
        qualification,
        "application.provision",
        "native_api",
        NOW + 30,
    )["operationally_eligible"]
    # Matching bytes and an unchanged plan digest never waive live freshness.
    qualification["verification"]["resolved_at"] = NOW + 100
    assert not assess(
        intent,
        renewed,
        profile,
        policy,
        qualification,
        "application.provision",
        "native_api",
        NOW + 100,
    )["operationally_eligible"]
    for change in ("policy_sha256", "sequence", "failure_at", "readback_sha256"):
        changed = deepcopy(renewed)
        sample = changed["capability_snapshot"]["data"]["recovery_measurements"][0]
        sample[change] = sample[change] + 1 if type(sample[change]) is int else "f" * 64
        assert inventory_digest(renewed) != inventory_digest(changed)


def test_synthetic_fault_hierarchy_is_valid_for_reordered_workload_ids() -> None:
    from copy import deepcopy

    from planning_fixture import snapshot_fixture

    from planning.domain.model import digest
    from planning.domain.network_evidence import isolation_checks

    intent, destination, _, policy, qualification = inputs()
    # Live fixtures rebind IDs randomly. Equal-sized workloads may consequently
    # sort in the opposite order from the input list during physical placement.
    reversed_intent = deepcopy(intent)
    reversed_intent["workloads"].reverse()
    context = next(iter(policy["network_flow_contexts"].values()))
    for i, workload in enumerate(reversed_intent["workloads"]):
        flow = {
            "from": "foreign-domain-" + str(i),
            "to": workload["id"],
            "protocol": "tcp",
            "port": 22,
        }
        policy["network_flow_contexts"][digest(flow)] = context
    observed = snapshot_fixture(reversed_intent, destination, policy, qualification)
    checks = isolation_checks(reversed_intent, destination, observed["data"], policy, NOW)
    hierarchy = next(row for row in checks if row[0] == "placement.fault_hierarchy")
    assert hierarchy[1] == "eligible"
