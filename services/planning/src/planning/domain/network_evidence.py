"""Evaluate directed routes, default-deny policy and measured required/forbidden traffic."""

from typing import Any

from planning.domain.model import digest
from planning.domain.placement import PlacementUnknown, fit


FLOW_KEYS = ("from", "to", "protocol", "port")
CONTEXT_KEYS = ("address_family", "vrf_id", "direction", "return_path_policy")


def flow_context(flow: dict[str, Any], policy: dict[str, Any]) -> dict[str, str] | None:
    """No four-tuple may authorize traffic outside its reviewed network context."""
    mapping = policy.get("network_flow_contexts")
    if not isinstance(mapping, dict):
        return None
    identity = digest({k: flow[k] for k in FLOW_KEYS})
    context = mapping.get(identity)
    if (
        not isinstance(context, dict)
        or set(context) != set(CONTEXT_KEYS)
        or any(not isinstance(context[k], str) or not context[k] for k in CONTEXT_KEYS)
        or context["address_family"] not in {"ipv4", "ipv6"}
        or context["direction"] != "source_to_destination"
        or context["return_path_policy"] != "stateful_allow"
    ):
        return None
    return context


def traffic(flow: dict[str, Any], network: dict[str, Any], policy: dict[str, Any], now: int) -> str:
    topology = network["topology"]
    context = flow_context(flow, policy)
    if context is None or (
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
            edge["to"]
            for edge in edges
            if edge["from"] in reached
            and edge["to"] in nodes
            and edge["native_ref"]
            and edge.get("context") == context
        }
        if added <= reached:
            break
        reached |= added
    allowed = flow["to"] in reached and any(
        all(rule.get(k) == flow[k] for k in FLOW_KEYS)
        and rule.get("context") == context
        and rule.get("action") == "allow"
        and rule.get("egress_action") == "allow"
        and rule.get("ingress_action") == "allow"
        and rule.get("native_ref")
        for rule in network["firewall_rules"]
    )
    rows = [
        row
        for row in network["measurements"]
        if all(row.get(k) == flow[k] for k in FLOW_KEYS)
        and row.get("context") == context
    ]
    if not rows:
        return "unknown"
    latest = max(rows, key=lambda row: row["sequence"])
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
    if expected == "allow":
        if not allowed:
            return "blocked"
        reverse = [
            row
            for row in network.get("return_paths", [])
            if row.get("from") == flow["to"]
            and row.get("to") == flow["from"]
            and row.get("protocol") == flow["protocol"]
            and row.get("port") == flow["port"]
            and row.get("context") == context
        ]
        if not reverse:
            return "unknown"
        current = max(reverse, key=lambda row: row["sequence"])
        if (
            type(current.get("observed_at")) is not int
            or not 0 <= now - current["observed_at"] <= 60
            or current.get("expires_at", 0) <= now
            or current.get("topology_sha256") != network["topology_sha256"]
            or current.get("policy_sha256") != network["policy_sha256"]
            or not current.get("native_ref")
        ):
            return "unknown"
        if current.get("outcome") != "allow":
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
    freshness = (
        type(isolation.get("observed_at")) is int
        and 0 <= now - isolation["observed_at"] <= 60
        and type(isolation.get("expires_at")) is int
        and isolation["expires_at"] > now
    )
    if not freshness:
        tenant_status = "unknown"
    elif (
        isolation.get("native_scope") != scope
        or isolation.get("tenant_id") != destination["tenant_id"]
        or isolation.get("policy_sha256") != digest(policy)
        or isolation.get("observer_principal") == isolation.get("writer_principal")
    ):
        tenant_status = "blocked"
    elif not all(
        isolation.get(k)
        for k in ("native_project_id", "observer_principal", "writer_principal")
    ):
        tenant_status = "unknown"
    else:
        tenant_status = "eligible"

    domains = isolation.get("domains")
    expected_domains = {w["security_domain"]["id"] for w in intent["workloads"]}
    if not isinstance(domains, dict) or any(not domains.get(d) for d in expected_domains):
        domain_status = "unknown"
    elif any(
        domains.get(d) != destination["domain_bindings"].get(d) for d in expected_domains
    ) or len({domains[d] for d in expected_domains}) != len(expected_domains):
        domain_status = "blocked"
    else:
        domain_status = "eligible"

    negative = isolation.get("negative_flows")
    if not isinstance(negative, list):
        negative_status = "unknown"
    else:
        covered = {f.get("security_domain_id") for f in negative if f.get("kind") == "domain"}
        tenant_controls = any(f.get("kind") == "tenant" for f in negative)
        if not tenant_controls or not expected_domains <= covered:
            negative_status = "unknown"
        else:
            states = [
                traffic(flow | {"expectation": "deny"}, data["network"], policy, now)
                for flow in negative
            ]
            negative_status = (
                "blocked" if "blocked" in states else
                "unknown" if "unknown" in states else "eligible"
            )

    def combine(*states: str) -> str:
        if "blocked" in states:
            return "blocked"
        if "unknown" in states:
            return "unknown"
        return "eligible"

    checks = [
        (
            "placement.tenant_boundary",
            combine(tenant_status, negative_status),
            "measured_tenant_isolation"
            if combine(tenant_status, negative_status) == "eligible"
            else "tenant_isolation_unverified",
            True,
        ),
        (
            "placement.security_domains",
            combine(domain_status, negative_status),
            "measured_domain_isolation"
            if combine(domain_status, negative_status) == "eligible"
            else "domain_isolation_unverified",
            True,
        ),
    ]
    controls = isolation.get("boundary_controls")
    for kind in ("rbac", "storage", "keys"):
        proof = controls.get(kind) if isinstance(controls, dict) else None
        if not isinstance(proof, dict) or not proof.get("native_ref") or (
            type(proof.get("observed_at")) is not int
            or not 0 <= now - proof["observed_at"] <= 60
            or proof.get("expires_at", 0) <= now
            or proof.get("policy_sha256") != digest(policy)
            or proof.get("native_scope") != scope
        ):
            status = "unknown"
        else:
            status = "eligible" if proof.get("outcome") == "passed" else "blocked"
        checks.append((
            "placement.isolation." + kind,
            status,
            "measured_" + kind + "_isolation" if status == "eligible"
            else kind + "_isolation_unverified",
            True,
        ))

    hierarchy = isolation.get("fault_hierarchy")
    hierarchy_status = "unknown"
    if isinstance(hierarchy, dict):
        try:
            placed = fit(intent, data["pools"], policy, now)
            if placed["status"] != "eligible":
                hierarchy_status = "blocked"
            else:
                pools = {pool["id"]: pool for pool in data["pools"]}
                if any(alloc["workload_id"] not in hierarchy for alloc in placed["allocations"]):
                    hierarchy_status = "unknown"
                else:
                    hierarchy_status = "eligible"
                    for allocation in placed["allocations"]:
                        row = hierarchy[allocation["workload_id"]]
                        pool = pools[allocation["pool_id"]]
                        if not isinstance(row, dict) or not all(
                            row.get(k) for k in ("native_ref", "rack", "zone", "site_id")
                        ):
                            hierarchy_status = "unknown"
                            break
                        if (
                            row["native_ref"] != allocation["native_ref"]
                            or row["rack"] != allocation["failure_domain"]
                            or row["zone"] != pool["zone"]
                            or row["site_id"] != destination["site_id"]
                        ):
                            hierarchy_status = "blocked"
                            break
        except (PlacementUnknown, KeyError, TypeError, ValueError):
            hierarchy_status = "unknown"
    checks.append((
        "placement.fault_hierarchy",
        hierarchy_status,
        "verified_native_fault_hierarchy" if hierarchy_status == "eligible"
        else "native_fault_hierarchy_unverified",
        True,
    ))
    return checks
