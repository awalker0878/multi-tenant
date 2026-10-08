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


@pytest.mark.parametrize(
    ("fault", "key", "expected"),
    [
        ("missing_rbac", "placement.isolation.rbac", "unknown"),
        ("failed_rbac", "placement.isolation.rbac", "blocked"),
        ("missing_storage", "placement.isolation.storage", "unknown"),
        ("failed_keys", "placement.isolation.keys", "blocked"),
        ("missing_hierarchy", "placement.fault_hierarchy", "unknown"),
        ("wrong_hierarchy", "placement.fault_hierarchy", "blocked"),
        ("missing_negative", "placement.tenant_boundary", "unknown"),
    ],
)
def test_native_isolation_controls_distinguish_missing_from_failed(
    fault: str, key: str, expected: str
) -> None:
    intent, destination, _, policy, _ = inputs()
    data = deepcopy(destination["capability_snapshot"]["data"])
    isolation = data["isolation"]
    if fault == "missing_rbac":
        isolation["boundary_controls"].pop("rbac")
    elif fault == "failed_rbac":
        isolation["boundary_controls"]["rbac"]["outcome"] = "failed"
    elif fault == "missing_storage":
        isolation["boundary_controls"].pop("storage")
    elif fault == "failed_keys":
        isolation["boundary_controls"]["keys"]["outcome"] = "failed"
    elif fault == "missing_hierarchy":
        isolation.pop("fault_hierarchy")
    elif fault == "wrong_hierarchy":
        first = intent["workloads"][0]["id"]
        isolation["fault_hierarchy"][first]["rack"] = "different-rack"
    elif fault == "missing_negative":
        isolation["negative_flows"] = []
    results = isolation_checks(intent, destination, data, policy, NOW)
    assert next(status for name, status, _, _ in results if name == key) == expected
