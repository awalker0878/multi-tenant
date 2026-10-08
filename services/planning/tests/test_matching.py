"""Typed objective boundaries and conservative multi-profile selection (A08, A15)."""

from typing import Any

import pytest
from planning_fixture import NOW, inputs

from planning.domain.assessment import assess
from planning.domain.matching import matches


@pytest.mark.parametrize("seconds,expected", [(60, True), (120, True), (180, False)])
def test_seconds_are_maximum_bounds(seconds: int, expected: bool) -> None:
    assert matches("recovery.rpo_seconds", 120, [seconds]) is expected
    assert matches("recovery.rto_seconds", {"value": 120, "unit": "seconds"}, [seconds]) is expected


@pytest.mark.parametrize(
    "value",
    [True, -1, 1.5, "60", {"value": 60, "unit": "minutes"}, {"value": 60, "unit": "bytes"}],
)
def test_wrong_type_or_units_cannot_establish_objectives(value: Any) -> None:
    assert matches("recovery.rpo_seconds", 120, [value]) is False


def test_unscoped_profiles_do_not_choose_the_best_measurement() -> None:
    assert matches("recovery.rpo_seconds", 120, [60, 180]) is False
    assert matches("recovery.rpo_seconds", 120, []) is False
    assert matches("new.platform.feature", True, [True]) is None
    assert matches("placement.tenant_isolation", True, [1]) is False


def test_registered_matcher_is_used_by_both_observation_and_qualification() -> None:
    intent, destination, profile, policy, qualification = inputs()
    for dataset in intent["datasets"]:
        dataset["recovery"]["rpo_seconds"] = 120
    for record in (destination, qualification):
        record["capabilities"]["recovery.rpo_seconds"]["values"] = [60]
    assert assess(
        intent,
        destination,
        profile,
        policy,
        qualification,
        "application.provision",
        "native_api",
        NOW,
    )["operationally_eligible"]
    qualification["capabilities"]["recovery.rpo_seconds"]["values"] = [180]
    assert not assess(
        intent,
        destination,
        profile,
        policy,
        qualification,
        "application.provision",
        "native_api",
        NOW,
    )["operationally_eligible"]
