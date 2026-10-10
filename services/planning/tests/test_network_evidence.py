"""A07/A08: equality and boolean declarations cannot replace measured native controls."""

from copy import deepcopy

import pytest

from planning_fixture import NOW, inputs

from planning.domain.network_evidence import isolation_checks, native_application_flow_choices, network_checks, selected_native_flow, traffic


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


@pytest.mark.parametrize(("change", "expected"), [
    ("missing_mapping", "unknown"),
    ("made_up_rule", "blocked"),
    ("made_up_route", "blocked"),
    ("changed_rule", "blocked"),
    ("stale_mapping", "unknown"),
    ("wrong_policy", "unknown"),
    ("same_writer", "blocked"),
    ("wrong_network_context", "blocked"),
])
def test_source_approved_application_flow_must_select_current_existing_native_controls(
    change: str, expected: str
) -> None:
    intent, destination, _, policy, _ = inputs()
    network = deepcopy(destination["capability_snapshot"]["data"]["network"])
    flow = next(d for d in intent["dependencies"] if d["kind"] == "communication")
    from planning.domain.model import digest

    key = digest({k: flow[k] for k in ("from", "to", "protocol", "port")})
    selection = network["application_flow_selections"][key]
    if change == "missing_mapping":
        del network["application_flow_selections"][key]
    elif change == "made_up_rule":
        selection["rule_native_ref"] = "fixture://not-an-api-id"
    elif change == "made_up_route":
        selection["route_native_ref"] = "fixture://not-an-api-route"
    elif change == "changed_rule":
        network["firewall_rules"][0]["ingress_action"] = "deny"
    elif change == "stale_mapping":
        selection["expires_at"] = NOW
    elif change == "wrong_policy":
        selection["policy_sha256"] = "b" * 64
    elif change == "same_writer":
        selection["observer_principal"] = "fixture-writer"
    elif change == "wrong_network_context":
        network["firewall_rules"][0]["context"]["vrf_id"] = "unexpected"
    assert selected_native_flow(flow, network, policy, NOW) == expected
    results = network_checks(intent, {"network": network}, policy, NOW)
    assert any(
        name == "network.application_flow_selection" and state == expected and required
        for name, state, _, required in results
    )


def test_native_application_selection_cannot_replace_independent_traffic_measurement() -> None:
    intent, destination, _, policy, _ = inputs()
    network = deepcopy(destination["capability_snapshot"]["data"]["network"])
    flow = next(d for d in intent["dependencies"] if d["kind"] == "communication")
    assert selected_native_flow(flow, network, policy, NOW) == "eligible"
    network["measurements"] = []
    assert traffic(flow, network, policy, NOW) == "unknown"
    checks = network_checks(intent, {"network": network}, policy, NOW)
    assert any(n == "network.reachability" and status == "unknown" for n, status, _, _ in checks)


def test_application_flow_dropdown_choices_are_existing_native_controls_only() -> None:
    intent, destination, _, policy, _ = inputs()
    network = deepcopy(destination["capability_snapshot"]["data"]["network"])
    choices = native_application_flow_choices(intent, network, policy)
    flow = next(d for d in intent["dependencies"] if d["kind"] == "communication")
    item = next(row for row in choices if row["source"]["from"] == flow["from"]
                and row["source"]["to"] == flow["to"])
    assert item["status"] == "choices_observed"
    assert item["destination_firewall_rule_ids"] == ["fixture://native-firewall-rule"]
    assert item["destination_route_ids"] == ["fixture://route"]
    assert item["native_write_authorized"] is False
    network["firewall_rules"][0]["action"] = "deny"
    damaged = native_application_flow_choices(intent, network, policy)
    assert "fixture://native-firewall-rule" not in next(
        row for row in damaged if row["source"]["from"] == flow["from"]
        and row["source"]["to"] == flow["to"]
    )["destination_firewall_rule_ids"]
    network["topology"]["routes"] = []
    assert all(row["status"] == "held_unobserved"
               for row in native_application_flow_choices(intent, network, policy))
