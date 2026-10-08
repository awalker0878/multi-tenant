"""Evaluate directed routes, default-deny policy and measured required/forbidden traffic."""

from typing import Any

from planning.domain.model import digest


def traffic(flow: dict[str, Any], network: dict[str, Any], policy: dict[str, Any], now: int) -> str:
    topology = network["topology"]
    if (
        network["policy_sha256"] != digest(policy)
        or network["topology_sha256"] != digest(topology)
        or network["default_action"] != "deny"
    ):
        return "unknown"
    nodes, edges = topology["nodes"], topology["routes"]
    if (
        len(nodes) > 512
        or len(edges) > 2048
        or not nodes.get(flow["from"])
        or not nodes.get(flow["to"])
    ):
        return "unknown"
    reached = {flow["from"]}
    for _ in range(len(nodes)):
        added = {
            e["to"] for e in edges if e["from"] in reached and e["to"] in nodes and e["native_ref"]
        }
        if added <= reached:
            break
        reached |= added
    allowed = flow["to"] in reached and any(
        all(rule.get(k) == flow[k] for k in ("from", "to", "protocol", "port"))
        and rule.get("action") == "allow"
        and rule.get("native_ref")
        for rule in network["firewall_rules"]
    )
    rows = [
        m
        for m in network["measurements"]
        if all(m.get(k) == flow[k] for k in ("from", "to", "protocol", "port"))
    ]
    if not rows:
        return "unknown"
    latest = max(rows, key=lambda m: m["sequence"])
    if (
        type(latest["sequence"]) is not int
        or type(latest["observed_at"]) is not int
        or not 0 <= now - latest["observed_at"] <= 60
        or latest["expires_at"] <= now
        or latest["topology_sha256"] != network["topology_sha256"]
        or latest["policy_sha256"] != network["policy_sha256"]
        or not latest["native_subjects"]
    ):
        return "unknown"
    expected = flow.get("expectation", "allow")
    if latest["outcome"] != expected:
        return "blocked"
    if expected == "allow" and not allowed:
        return "blocked"
    if expected == "deny" and allowed:
        return "blocked"
    return "eligible"


def network_checks(
    intent: dict[str, Any], data: dict[str, Any], policy: dict[str, Any], now: int
) -> list[tuple[str, str, str, bool]]:
    network = data["network"]
    checks = []
    for dependency in intent["dependencies"]:
        if dependency["kind"] == "communication":
            status = traffic(dependency, network, policy, now)
            checks.append(
                (
                    "network.reachability",
                    status,
                    "required_native_flow_" + status,
                    dependency["strength"] == "required",
                )
            )
    forbidden = policy.get("forbidden_flows")
    if not isinstance(forbidden, list) or not forbidden:
        checks.append(
            ("network.default_deny", "unknown", "negative_traffic_controls_missing", True)
        )
    else:
        for flow in forbidden:
            status = traffic(flow | {"expectation": "deny"}, network, policy, now)
            checks.append(
                ("network.forbidden_flow", status, "forbidden_native_flow_" + status, True)
            )
    return checks


def isolation_checks(
    intent: dict[str, Any],
    destination: dict[str, Any],
    data: dict[str, Any],
    policy: dict[str, Any],
    now: int,
) -> list[tuple[str, str, str, bool]]:
    isolation = data["isolation"]
    scope = destination["native_scope"]
    tenant_ok = (
        isolation["native_scope"] == scope
        and isolation["tenant_id"] == destination["tenant_id"]
        and bool(isolation["native_project_id"])
        and isolation["policy_sha256"] == digest(policy)
        and isolation["observer_principal"] != isolation["writer_principal"]
        and bool(isolation["observer_principal"])
        and bool(isolation["writer_principal"])
        and type(isolation["observed_at"]) is int
        and 0 <= now - isolation["observed_at"] <= 60
        and isolation["expires_at"] > now
    )
    domains = isolation["domains"]
    domain_ok = all(
        domains.get(w["security_domain"]["id"])
        == destination["domain_bindings"].get(w["security_domain"]["id"])
        and bool(domains.get(w["security_domain"]["id"]))
        for w in intent["workloads"]
    )
    distinct = {w["security_domain"]["id"] for w in intent["workloads"]}
    domain_ok = domain_ok and len({domains.get(d) for d in distinct}) == len(distinct)
    negative = isolation["negative_flows"]
    expected_domains = {w["security_domain"]["id"] for w in intent["workloads"]}
    covered = {f.get("security_domain_id") for f in negative if f.get("kind") == "domain"}
    tenant_controls = any(f.get("kind") == "tenant" for f in negative)
    controls_ok = (
        tenant_controls
        and expected_domains <= covered
        and all(
            traffic(flow | {"expectation": "deny"}, data["network"], policy, now) == "eligible"
            for flow in negative
        )
    )
    return [
        (
            "placement.tenant_boundary",
            "eligible" if tenant_ok and controls_ok else "blocked",
            "measured_tenant_isolation"
            if tenant_ok and controls_ok
            else "tenant_isolation_unverified",
            True,
        ),
        (
            "placement.security_domains",
            "eligible" if domain_ok and controls_ok else "blocked",
            "measured_domain_isolation"
            if domain_ok and controls_ok
            else "domain_isolation_unverified",
            True,
        ),
    ]
