"""A09/A10: latest recovery proves the whole outage and dependent readiness."""

from copy import deepcopy

import pytest
from planning_fixture import NOW, inputs

from planning.domain.model import digest
from planning.domain.recovery_evidence import recovery_checks


@pytest.mark.parametrize(
    "fault",
    [
        "none", "failure", "rpo", "rto", "delayed_start", "unit",
        "bytes", "load", "scope", "missing_keys", "failed_keys",
        "missing_dependency", "failed_dependency", "missing_application",
        "stale_review",
    ],
)
def test_restore_measurements_feed_back_into_the_next_assessment(fault: str) -> None:
    intent, destination, profile, policy, _ = inputs()
    data = destination["capability_snapshot"]["data"]
    original = data["recovery_measurements"][0]
    latest = deepcopy(original)
    latest["sequence"] = 2
    if fault == "failure":
        latest["outcome"] = "failed"
    elif fault == "rpo":
        latest["last_consistent_checkpoint_at"] -= 1
    elif fault == "rto":
        intent["datasets"][0]["recovery"]["rto_seconds"] = 20
    elif fault == "delayed_start":
        # The old restore-start boundary incorrectly measured 30 seconds.
        # The actual failure-to-ready RTO is 90 seconds.
        latest["failure_at"] = NOW - 90
        latest["last_consistent_checkpoint_at"] = NOW - 90
        intent["datasets"][0]["recovery"]["rto_seconds"] = 60
    elif fault == "unit":
        latest["unit"] = "bytes"
    elif fault == "bytes":
        latest["representative_bytes"] = 1
    elif fault == "load":
        latest["load"] = 0
    elif fault == "scope":
        latest["native_scope"] = "foreign"
    elif fault == "missing_keys":
        latest.pop("key_readiness")
    elif fault == "failed_keys":
        latest["key_readiness"]["available"] = False
    elif fault == "missing_dependency":
        latest["dependency_readiness"] = {}
    elif fault == "failed_dependency":
        next(iter(latest["dependency_readiness"].values()))["verified"] = False
    elif fault == "missing_application":
        latest.pop("application_readiness")
    elif fault == "stale_review":
        policy["recovery_profile"]["review"]["expires_at"] = NOW - 1
        latest["policy_sha256"] = digest(policy)
    data["recovery_measurements"].append(latest)
    checks = recovery_checks(intent, destination, profile, policy, data, NOW)
    expected = (
        "eligible"
        if fault == "none"
        else "blocked"
        if fault in {
            "failure", "rpo", "rto", "delayed_start",
            "failed_keys", "failed_dependency",
        }
        else "unknown"
    )
    assert checks[0][1] == expected


def test_restore_start_delay_counts_against_rto() -> None:
    intent, destination, profile, policy, _ = inputs()
    sample = destination["capability_snapshot"]["data"]["recovery_measurements"][0]
    sample["failure_at"] = NOW - 300
    sample["last_consistent_checkpoint_at"] = NOW - 300
    intent["datasets"][0]["recovery"]["rto_seconds"] = 120
    assert sample["application_ready_at"] - sample["restore_started_at"] < 120
    assert recovery_checks(
        intent, destination, profile, policy,
        destination["capability_snapshot"]["data"], NOW,
    )[0][1:] == (
        "blocked", "measured_restore_exceeds_objectives", True,
    )
