"""Missing or mismatched validation composition cannot authorize native plans (A12)."""

from dataclasses import FrozenInstanceError
from typing import Any
from unittest.mock import Mock

import pytest

from planning.application.migration_plans import MigrationPlans
from planning.application.native_plans import NativePlans
from planning.application.planning import Planning
from planning.application.validation import MigrationValidation, NativeValidation, PlanValidation
from planning.domain.model import Rejected


def test_validation_is_required_and_cannot_be_rewired_after_construction() -> None:
    clock = Mock(return_value=100)
    validation = PlanValidation.unavailable(clock)
    planner: Any = Planning(Mock(), Mock(), clock, validation)
    with pytest.raises(TypeError):
        Planning(Mock(), Mock(), clock)  # type: ignore[call-arg]
    with pytest.raises(ValueError, match="required_plan_validation"):
        Planning(Mock(), Mock(), clock, None)  # type: ignore[arg-type]
    with pytest.raises(AttributeError):
        planner.migration_current = Mock()
    with pytest.raises(AttributeError):
        planner.validation = PlanValidation.unavailable(clock)
    with pytest.raises(FrozenInstanceError):
        validation.migration.support = Mock()  # type: ignore[misc]


def test_plan_services_cannot_use_different_validation_authority() -> None:
    clock = Mock(return_value=100)
    validation = PlanValidation.unavailable(clock)
    planner = Planning(Mock(), Mock(), clock, validation)
    with pytest.raises(ValueError, match="composition_mismatch"):
        MigrationPlans(planner, MigrationValidation(Mock(), Mock(), Mock(), clock))
    with pytest.raises(ValueError, match="composition_mismatch"):
        NativePlans(planner, NativeValidation(Mock(), clock))
    with pytest.raises(ValueError, match="required_migration_validation"):
        MigrationValidation(Mock(), Mock(), None, clock)  # type: ignore[arg-type]


def test_unattended_execution_cannot_skip_support_read() -> None:
    from test_migration_plans import values

    from planning.domain.migration_plan import compose_migration

    base, bound, recipe = values()
    content = compose_migration(base, bound, recipe, 1000)
    content["native_migration"]["recipe_id"] = "selected"
    recipes = Mock(return_value=recipe)
    support = Mock(side_effect=Rejected("qualification_revoked", 423))
    validation = MigrationValidation(Mock(), recipes, support, lambda: 1000)
    with pytest.raises(Rejected, match="qualification_revoked"):
        validation.execution_current({"content": content, "binding": {"requested_by": "actor"}})
    recipes.assert_not_called()
