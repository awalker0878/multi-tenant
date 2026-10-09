"""Native effective-policy resolvers. No E2 catalogue can authorize migration.

A normalized E4 document is produced by a platform-version-qualified observer.
Provider semantics stay here, NOT in the vendor-neutral admission service.
Unknown attachments, identities, priorities and service expansion fail closed.
"""
from __future__ import annotations

from ipaddress import ip_address, ip_network
from typing import Any

class Unqualified(ValueError):
    pass

DFW_CATEGORIES = ("Emergency", "Infrastructure", "Environment", "Application")
GATEWAY_CATEGORIES = ("Emergency", "SystemRules", "SharedPreRules", "SharedExternalRules",
                      "LocalGatewayRules", "AutoServiceRules", "Default")
MAX_ITEMS = 2048


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise Unqualified(reason)


def identity(document: dict[str, Any], logical: str) -> dict[str, Any]:
    bindings = document.get("workloads")
    require(isinstance(bindings, dict) and logical in bindings,
            "native_workload_binding_missing")
    row = bindings[logical]
    require(isinstance(row, dict) and row.get("complete") is True
            and row.get("observed_by") == document.get("observer_principal")
            and isinstance(row.get("native_vm_id"), str) and row["native_vm_id"]
            and isinstance(row.get("tenant_id"), str) and row["tenant_id"]
            and isinstance(row.get("port_id"), str) and row["port_id"]
            and isinstance(row.get("ips"), list) and row["ips"]
            and isinstance(row.get("attachment_revision"), str)
            and row["attachment_revision"], "native_workload_binding_unqualified")
    for address in row["ips"]:
        try:
            ip_address(address)
        except (ValueError, TypeError):
            raise Unqualified("native_workload_ip_invalid") from None
    return row


def groups_services(document: dict[str, Any]) -> None:
    groups, services = document.get("groups"), document.get("services")
    require(isinstance(groups, dict) and 0 < len(groups) <= MAX_ITEMS
            and isinstance(services, dict) and 0 < len(services) <= MAX_ITEMS
            and document.get("effective_membership_observed") is True,
            "effective_group_or_service_catalogue_missing")
    for name, row in groups.items():
        require(isinstance(name, str) and name and isinstance(row, dict)
                and row.get("resolution") == "effective_native_members"
                and row.get("complete") is True
                and isinstance(row.get("native_revision"), str)
                and row["native_revision"]
                and isinstance(row.get("members"), list)
                and len(row["members"]) <= MAX_ITEMS
                and len(row["members"]) == len(set(row["members"])),
                "effective_group_membership_unverified")
    for name, row in services.items():
        require(isinstance(name, str) and name and isinstance(row, dict)
                and row.get("resolution") == "native_expanded"
                and row.get("complete") is True
                and isinstance(row.get("native_revision"), str)
                and row["native_revision"]
                and row.get("protocol") in ("tcp", "udp", "icmp")
                and isinstance(row.get("ports"), list)
                and len(row["ports"]) <= 256
                and all(type(port) is int and 0 <= port <= 65535
                        for port in row["ports"]),
                "effective_service_reference_unverified")


def matches(document: dict[str, Any], rule: dict[str, Any],
            flow: dict[str, Any]) -> bool:
    for field in ("source_group", "destination_group", "service_ref"):
        require(isinstance(rule.get(field), str), "native_rule_reference_unresolved")
    src = document["groups"].get(rule["source_group"])
    dst = document["groups"].get(rule["destination_group"])
    service = document["services"].get(rule["service_ref"])
    require(src is not None and dst is not None and service is not None,
            "native_rule_reference_unresolved")
    source = identity(document, flow["from"])
    target = identity(document, flow["to"])
    return (source["native_vm_id"] in src["members"]
            and target["native_vm_id"] in dst["members"]
            and service["protocol"] == flow["protocol"]
            and (flow["port"] in service["ports"]
                 or (flow["protocol"] == "icmp" and flow["port"] is None
                     and not service["ports"])))


def _common_rules(document: dict[str, Any]) -> list[dict[str, Any]]:
    groups_services(document)
    rows = document.get("rules")
    require(isinstance(rows, list) and len(rows) <= MAX_ITEMS
            and document.get("rules_complete") is True,
            "native_effective_rule_set_incomplete")
    seen = set()
    for row in rows:
        require(isinstance(row, dict)
                and isinstance(row.get("native_ref"), str)
                and row["native_ref"] not in seen
                and row.get("enabled") is True
                and row.get("effective_scope_qualified") is True
                and row.get("action") in ("allow", "deny", "reject")
                and row.get("direction") in ("in", "out", "both")
                and isinstance(row.get("native_revision"), str)
                and row["native_revision"],
                "native_rule_unqualified")
        seen.add(row["native_ref"])
    return rows


def nsx(document: dict[str, Any], flow: dict[str, Any]) -> tuple[str, str | None]:
    require(document.get("native_api_qualified") is True
            and document.get("enforcement_layer") in ("dfw", "gateway"),
            "nsx_installed_api_or_firewall_layer_unqualified")
    layer = document["enforcement_layer"]
    categories = DFW_CATEGORIES if layer == "dfw" else GATEWAY_CATEGORIES
    source, target = identity(document, flow["from"]), identity(document, flow["to"])
    rows = []
    seen_priority = set()
    for rule in _common_rules(document):
        category = rule.get("category")
        require(category in categories
                and type(rule.get("policy_sequence")) is int
                and type(rule.get("priority")) is int,
                "nsx_native_rule_precedence_unresolved")
        key = (categories.index(category), rule["policy_sequence"], rule["priority"])
        require(key not in seen_priority, "nsx_effective_order_ambiguous")
        seen_priority.add(key)
        # Scope must be calculated by the installed Policy API's applied-to
        # precedence. Policy scope overrides rule scope when present.
        policy_scope = rule.get("policy_applied_to")
        rule_scope = rule.get("rule_applied_to")
        require(isinstance(policy_scope, list) and isinstance(rule_scope, list)
                and all(isinstance(x, str) for x in policy_scope + rule_scope)
                and rule.get("scope_precedence_verified") is True,
                "nsx_applied_to_unverified")
        effective_scope = policy_scope if policy_scope else rule_scope
        require(effective_scope and set(effective_scope).issubset(document["groups"]),
                "nsx_applied_to_unverified")
        if source["native_vm_id"] not in {
            member for group in effective_scope
            for member in document["groups"][group]["members"]
        } and target["native_vm_id"] not in {
            member for group in effective_scope
            for member in document["groups"][group]["members"]
        }:
            continue
        rows.append((key, rule))
    for _, rule in sorted(rows, key=lambda item: item[0]):
        if matches(document, rule, flow):
            return ("allow" if rule["action"] == "allow" else "deny", rule["native_ref"])
    return "deny", document.get("default_deny_native_ref")


def ahv(document: dict[str, Any], flow: dict[str, Any]) -> tuple[str, str | None]:
    require(document.get("native_api_qualified") is True
            and document.get("microseg_policy_priority_qualified") is True
            and document.get("policy_types_complete") is True,
            "ahv_effective_policy_semantics_unqualified")
    rows = []
    seen_priority = set()
    for rule in _common_rules(document):
        require(rule.get("policy_state") == "ENFORCE"
                and rule.get("policy_type") in ("application", "isolation", "quarantine")
                and type(rule.get("effective_priority")) is int
                and isinstance(rule.get("attached_vm_ids"), list)
                and rule.get("attachment_observed") is True,
                "ahv_rule_order_or_attachment_unqualified")
        priority = rule["effective_priority"]
        require(priority not in seen_priority, "ahv_effective_order_ambiguous")
        seen_priority.add(priority)
        source, target = identity(document, flow["from"]), identity(document, flow["to"])
        if source["native_vm_id"] not in rule["attached_vm_ids"] and target["native_vm_id"] not in rule["attached_vm_ids"]:
            continue
        rows.append((priority, rule))
    for _, rule in sorted(rows, key=lambda item: item[0]):
        if matches(document, rule, flow):
            return ("allow" if rule["action"] == "allow" else "deny", rule["native_ref"])
    return "deny", document.get("default_deny_native_ref")


def neutron(document: dict[str, Any], flow: dict[str, Any]) -> tuple[str, str | None]:
    """Neutron uses additive per-port security-group allow rules, not priority."""
    require(document.get("native_api_qualified") is True
            and document.get("rules_complete") is True
            and document.get("default_action") == "deny",
            "neutron_effective_security_unqualified")
    source, target = identity(document, flow["from"]), identity(document, flow["to"])
    ports = document.get("ports")
    groups = document.get("security_groups")
    rules = document.get("rules")
    require(isinstance(ports, dict) and isinstance(groups, dict)
            and isinstance(rules, list) and len(rules) <= MAX_ITEMS,
            "neutron_port_security_unobserved")
    for workload in (source, target):
        port = ports.get(workload["port_id"])
        require(isinstance(port, dict) and port.get("port_security_enabled") is True
                and port.get("project_id") == workload["tenant_id"]
                and isinstance(port.get("security_groups"), list)
                and port.get("attached_groups_observed") is True
                and port.get("native_revision"),
                "neutron_port_attachment_unqualified")
        for group in port["security_groups"]:
            require(group in groups and groups[group].get("stateful") is True
                    and groups[group].get("complete") is True,
                    "neutron_group_statefulness_unqualified")
    family = flow.get("address_family", document.get("address_family"))
    require(family in ("ipv4", "ipv6"), "neutron_address_family_required")

    def permits(port_id: str, direction: str, remote: dict[str, Any]) -> str | None:
        attached = set(ports[port_id]["security_groups"])
        for rule in rules:
            require(isinstance(rule, dict) and isinstance(rule.get("native_ref"), str)
                    and rule.get("action") == "allow"
                    and rule.get("direction") in ("ingress", "egress")
                    and rule.get("ethertype") in ("ipv4", "ipv6")
                    and isinstance(rule.get("security_group_id"), str),
                    "neutron_native_rule_unqualified")
            if rule["security_group_id"] not in attached or rule["direction"] != direction or rule["ethertype"] != family:
                continue
            if rule.get("protocol") not in (None, flow["protocol"]):
                continue
            lower, upper = rule.get("port_range_min"), rule.get("port_range_max")
            if flow["port"] is not None and (lower is not None or upper is not None):
                require(type(lower) is int and type(upper) is int,
                        "neutron_port_range_unverified")
                if not lower <= flow["port"] <= upper:
                    continue
            elif flow["port"] is None and (lower is not None or upper is not None):
                continue
            member_ids = rule.get("effective_remote_vm_ids")
            require(isinstance(member_ids, list) and rule.get("remote_scope_complete") is True,
                    "neutron_remote_group_unresolved")
            if remote["native_vm_id"] in member_ids:
                return rule["native_ref"]
        return None

    egress = permits(source["port_id"], "egress", target)
    ingress = permits(target["port_id"], "ingress", source)
    return ("allow", ingress) if egress and ingress else ("deny", document.get("default_deny_native_ref"))


RESOLVERS = {"vmware": nsx, "ahv": ahv, "openstack": neutron}


def decision(document: dict[str, Any], flow: dict[str, Any]) -> tuple[str, str | None]:
    require(isinstance(document, dict) and document.get("platform") in RESOLVERS
            and document.get("schema_version") == 2
            and document.get("default_action") == "deny",
            "effective_security_contract_v2_required")
    for key in ("from", "to", "protocol", "port"):
        require(key in flow, "incomplete_application_flow")
    return RESOLVERS[document["platform"]](document, flow)
