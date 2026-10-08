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
