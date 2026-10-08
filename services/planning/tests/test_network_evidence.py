"""A07/A08: equality and boolean declarations cannot replace measured native controls."""

from copy import deepcopy

import pytest

from planning_fixture import NOW, inputs

from planning.domain.network_evidence import isolation_checks, network_checks, traffic


def test_missing_route_and_failed_negative_control_block() -> None:
    intent, destination, _, policy, _ = inputs()
    data = destination["capability_snapshot"]["data"]
    assert all(s == "eligible" for _, s, _, _ in network_checks(intent, data, policy, NOW))
    missing = deepcopy(data)
    missing["network"]["topology"]["routes"] = []
    from planning.domain.model import digest

    missing["network"]["topology_sha256"] = digest(missing["network"]["topology"])
    assert any(s != "eligible" for _, s, _, _ in network_checks(intent, missing, policy, NOW))
    failed = deepcopy(data)
    failed["network"]["measurements"][-1]["outcome"] = "allow"
    assert any(
        s == "blocked" for _, s, _, _ in isolation_checks(intent, destination, failed, policy, NOW)
    )


def test_domain_aliasing_and_same_observer_writer_are_rejected() -> None:
    intent, destination, _, policy, _ = inputs()
    data = destination["capability_snapshot"]["data"]
    domains = data["isolation"]["domains"]
    names = list(domains)
    domains[names[1]] = domains[names[0]]
    data["isolation"]["observer_principal"] = data["isolation"]["writer_principal"]
    assert all(
        s == "blocked" for _, s, _, _ in isolation_checks(intent, destination, data, policy, NOW)
    )


@pytest.mark.parametrize(
    ("fault", "expected"),
    [
        ("wrong_vrf", "unknown"),
        ("wrong_family", "unknown"),
        ("missing_context", "unknown"),
        ("missing_return", "unknown"),
        ("return_denied", "blocked"),
        ("ingress_denied", "blocked"),
        ("egress_denied", "blocked"),
    ],
)
def test_identical_four_tuple_cannot_cross_native_network_contexts(
    fault: str, expected: str
) -> None:
    intent, destination, _, policy, _ = inputs()
    data = deepcopy(destination["capability_snapshot"]["data"]["network"])
    flow = next(d for d in intent["dependencies"] if d["kind"] == "communication")
    if fault == "wrong_vrf":
        data["measurements"][0]["context"]["vrf_id"] = "different-vrf"
    elif fault == "wrong_family":
        data["measurements"][0]["context"]["address_family"] = "ipv6"
    elif fault == "missing_context":
        data["measurements"][0].pop("context")
    elif fault == "missing_return":
        data["return_paths"] = []
    elif fault == "return_denied":
        data["return_paths"][0]["outcome"] = "deny"
    elif fault == "ingress_denied":
        data["firewall_rules"][0]["ingress_action"] = "deny"
    elif fault == "egress_denied":
        data["firewall_rules"][0]["egress_action"] = "deny"
    assert traffic(flow, data, policy, NOW) == expected
