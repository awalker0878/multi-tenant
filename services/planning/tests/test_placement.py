"""A05/A06: totals cannot hide fragmentation, reservations or failure-domain constraints."""

from copy import deepcopy

import pytest
from planning_fixture import NOW, inputs

from planning.domain.assessment import assess
from planning.domain.placement import PlacementUnknown, fit


def test_fragmentation_and_concurrent_pending_debits_block_placement() -> None:
    intent, destination, _, policy, _ = inputs()
    pools = destination["capability_snapshot"]["data"]["pools"]
    assert fit(intent, pools, policy, NOW)["status"] == "eligible"
    fragmented = deepcopy(pools)
    fragmented[0]["total"]["memory_mib"] = 2048
    fragmented[1]["total"]["memory_mib"] = 6144
    assert fit(intent, fragmented, policy, NOW)["status"] == "blocked"
    pending = deepcopy(pools)
    pending[0]["pending"]["vcpus"] = 1
    assert fit(intent, pending, policy, NOW)["status"] == "blocked"


def test_fault_domains_and_invalid_overcommit_do_not_default_to_true() -> None:
    intent, destination, _, policy, _ = inputs()
    pools = destination["capability_snapshot"]["data"]["pools"]
    pools[1]["failure_domain"] = pools[0]["failure_domain"]
    assert fit(intent, pools, policy, NOW)["status"] == "blocked"
    pools[0]["overcommit"] = {"numerator": 2, "denominator": 0}
    with pytest.raises((PlacementUnknown, KeyError)):
        fit(intent, pools, policy, NOW)


@pytest.mark.parametrize("fault", ["absent", "source", "scope", "stale", "definition"])
def test_asserted_capacity_without_bound_native_evidence_cannot_be_eligible(fault: str) -> None:
    intent, destination, profile, policy, qualification = inputs()
    current = destination["capability_snapshot"]
    if fault == "absent":
        destination["capability_snapshot"] = None
    elif fault in {"source", "scope", "definition"}:
        current[fault + "_sha256"] = "f" * 64
    else:
        current["observed_at"] = NOW - 61
    result = assess(
        intent, destination, profile, policy, qualification, "application.provision", "native_api", NOW
    )
    assert not result["operationally_eligible"]
