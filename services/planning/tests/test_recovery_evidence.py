"""A09/A10: latest representative measured recovery, never a best-case declaration."""

from copy import deepcopy

import pytest
from planning_fixture import NOW, inputs

from planning.domain.recovery_evidence import recovery_checks


@pytest.mark.parametrize("fault", ["none", "failure", "rpo", "rto", "unit", "bytes", "load", "scope"])
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
    elif fault == "unit":
        latest["unit"] = "bytes"
    elif fault == "bytes":
        latest["representative_bytes"] = 1
    elif fault == "load":
        latest["load"] = 0
    elif fault == "scope":
        latest["native_scope"] = "foreign"
    data["recovery_measurements"].append(latest)
    checks = recovery_checks(intent, destination, profile, policy, data, NOW)
    assert checks[0][1] == ("eligible" if fault == "none" else (
        "blocked" if fault in {"failure", "rpo", "rto"} else "unknown"
    ))
