"""Conservative effective security/path qualification; no native API list confers E4.

The input must come from independent, signed Assurance custody. This module
never interprets an NSX/Prism policy *name*, a policy-list fingerprint, or
unresolved dynamic expression as a definitive VM-to-rule binding.

Version 1 is an intentionally narrow, fully observed certificate profile:
a unique effective rule order, exact group membership and service expansion,
explicit per-hop route/translation, plus independent allow and deny witnesses.
Unsupported semantics produce a hold rather than guessed equivalence.
"""
from __future__ import annotations

from ipaddress import ip_address
from typing import Any

from planning.domain.model import digest

MAX_RULES = 512
MAX_NODES = 512
MAX_HOPS = 32
MAX_PROBES = 1024
NSX_CATEGORIES = ("Ethernet", "Emergency", "Infrastructure", "Environment", "Application")


def hold(reason: str) -> dict[str, Any]:
    return {"status": "held", "reason": reason, "native_write_authorized": False}


def text(value: Any) -> bool:
    return isinstance(value, str) and 0 < len(value) <= 512


def fresh(proof: dict[str, Any], now: int) -> bool:
    return (type(proof.get("observed_at")) is int
            and type(proof.get("expires_at")) is int
            and 0 <= now - proof["observed_at"] <= 30
            and now < proof["expires_at"] <= proof["observed_at"] + 60)


def addresses_match(before: str, after: str) -> bool:
    try:
        return ip_address(before).version == ip_address(after).version
    except (ValueError, TypeError):
        return False


def effective_rules(document: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
    """Expand only *effective* observed membership and transport-service objects.

    Completeness is explicit; expressions and nested group references must have
    already been resolved by native APIs and independently checked. Their
    presence is evidence of an unresolved source, not a selector to guess.
    """
    platform = document.get("platform")
    if platform not in {"vmware", "ahv", "openstack"}:
        return [], "unknown_security_platform"
    rules, groups, services = (
        document.get("rules"), document.get("groups"), document.get("services")
    )
    if (not isinstance(rules, list) or len(rules) > MAX_RULES
            or not isinstance(groups, dict) or len(groups) > MAX_NODES
            or not isinstance(services, dict) or len(services) > MAX_NODES):
        return [], "effective_security_catalogue_incomplete"
    if document.get("effective_membership_observed") is not True:
        return [], "effective_group_membership_unverified"

    for native, group in groups.items():
        if (not text(native) or not isinstance(group, dict)
                or group.get("resolution") != "effective_native_members"
                or group.get("complete") is not True
                or not isinstance(group.get("members"), list)
                or len(group["members"]) > MAX_NODES
                or any(not text(m) for m in group["members"])
                or len(set(group["members"])) != len(group["members"])
                or not text(group.get("native_revision"))):
            return [], "effective_group_membership_unverified"
    for native, service in services.items():
        if (not text(native) or not isinstance(service, dict)
                or service.get("resolution") != "native_expanded"
                or service.get("complete") is not True
                or service.get("protocol") not in {"tcp", "udp", "icmp"}
                or not isinstance(service.get("ports"), list)
                or len(service["ports"]) > 256
                or any(type(p) is not int or not 0 <= p <= 65535
                       for p in service["ports"])
                or not text(service.get("native_revision"))):
            return [], "effective_service_reference_unverified"

    ordered: list[tuple[Any, dict[str, Any]]] = []
    seen_order: set[tuple[Any, ...]] = set()
    seen_native: set[str] = set()
    for rule in rules:
        if not isinstance(rule, dict):
            return [], "invalid_effective_security_rule"
        native = rule.get("native_ref")
        if not text(native) or native in seen_native:
            return [], "ambiguous_effective_security_rule"
        seen_native.add(native)
        if rule.get("action") not in {"allow", "deny", "reject"}:
            return [], "unsupported_native_security_action"
        if rule.get("direction") not in {"in", "out", "both"}:
            return [], "unsupported_native_security_direction"
        if type(rule.get("priority")) is not int or rule["priority"] < 0:
            return [], "native_security_priority_unresolved"
        if not text(rule.get("native_revision")) or rule.get("enabled") is not True:
            return [], "native_security_rule_state_unresolved"
        if rule.get("effective_scope_qualified") is not True:
            return [], "native_security_attachment_unverified"
        source, target, service_id = (
            rule.get("source_group"), rule.get("destination_group"),
            rule.get("service_ref")
        )
        if source not in groups or target not in groups or service_id not in services:
            return [], "native_rule_reference_unresolved"
        if platform == "vmware":
            cat = rule.get("category")
            if cat not in NSX_CATEGORIES:
                return [], "nsx_security_category_unresolved"
            # NSX category + policy sequence + rule priority must form a
            # unique order. Overlapping identical keys cannot be assumed.
            if type(rule.get("policy_sequence")) is not int:
                return [], "nsx_policy_sequence_unresolved"
            key = (NSX_CATEGORIES.index(cat), rule["policy_sequence"], rule["priority"])
        elif platform == "ahv":
            if rule.get("policy_state") != "ENFORCE":
                return [], "ahv_policy_enforcement_unverified"
            key = (rule["priority"],)
        else:
            key = (rule["priority"],)
        if key in seen_order:
            return [], "effective_security_order_ambiguous"
        seen_order.add(key)
        ordered.append((key, rule))
    return [rule for _, rule in sorted(ordered, key=lambda x: x[0])], None


def path_evidence(document: dict[str, Any], flow: dict[str, Any]) -> tuple[str | None, str | None]:
    """Deterministic directed, single-path hop and NAT certificate.

    A graph-wide reachability guess is unsafe with ECMP, policy routing and
    overlapping address spaces. The independent observer must record the
    actual traversed edges in order, including each stateful NAT binding.
    """
    path = document.get("path")
    if not isinstance(path, dict):
        return None, "native_network_path_unobserved"
    nodes, hops = path.get("nodes"), path.get("hops")
    if not isinstance(nodes, list) or not 2 <= len(nodes) <= MAX_HOPS + 1:
        return None, "native_network_path_unobserved"
    if (not isinstance(hops, list) or len(hops) != len(nodes) - 1
            or len(hops) > MAX_HOPS
            or any(not text(node) for node in nodes)
            or len(set(nodes)) != len(nodes)
            or nodes[0] != flow.get("from") or nodes[-1] != flow.get("to")
            or not text(path.get("scope"))
            or path.get("multipath_resolved") is not True
            or path.get("complete") is not True):
        return None, "native_network_path_incomplete"
    if (not text(path.get("source_address"))
            or not text(path.get("destination_address"))
            or not addresses_match(path["source_address"], path["destination_address"])):
        return None, "native_path_addresses_unverified"
    src, dst = path["source_address"], path["destination_address"]
    port = flow.get("port")
    if type(port) not in {int, type(None)}:
        return None, "native_path_port_unverified"
    current_scope = path["scope"]
    used_refs: set[str] = set()
    for index, hop in enumerate(hops):
        if not isinstance(hop, dict) or (
            hop.get("from") != nodes[index] or hop.get("to") != nodes[index + 1]
            or not text(hop.get("native_ref"))
            or hop["native_ref"] in used_refs
            or hop.get("scope") != current_scope
            or hop.get("forward_observed") is not True
            or hop.get("reverse_observed") is not True
        ):
            return None, "native_route_hop_unqualified"
        used_refs.add(hop["native_ref"])
        translation = hop.get("nat")
        next_scope = hop.get("next_scope", current_scope)
        if translation is not None:
            if (not isinstance(translation, dict)
                    or translation.get("kind") not in {"snat", "dnat", "twice_nat"}
                    or not text(translation.get("native_ref"))
                    or translation.get("stateful_return_observed") is not True
                    or translation.get("before_source") != src
                    or translation.get("before_destination") != dst
                    or translation.get("before_port") != port
                    or type(translation.get("after_port")) not in {int, type(None)}
                    or not addresses_match(src, translation.get("after_source"))
                    or not addresses_match(dst, translation.get("after_destination"))):
                return None, "native_nat_translation_unqualified"
            if (next_scope != current_scope
                    and translation.get("cross_scope_authorized") is not True):
                return None, "native_nat_cross_scope_unqualified"
            src, dst = translation["after_source"], translation["after_destination"]
            port = translation["after_port"]
        elif next_scope != current_scope:
            return None, "native_untranslated_scope_crossing"
        if not text(next_scope):
            return None, "native_route_scope_unverified"
        current_scope = next_scope
    if (src != path.get("observed_egress_source")
            or dst != path.get("observed_egress_destination")
            or port != path.get("observed_egress_port", flow.get("port"))
            or current_scope != path.get("destination_scope", path["scope"])
            or path.get("reverse_path_measured") is not True):
        return None, "native_return_path_unqualified"
    return digest(path), None


def measured(document: dict[str, Any], flow: dict[str, Any], path_sha: str, now: int) -> str | None:
    """Allow a defined required flow and deny a *separate* forbidden flow.

    Both checks must come from the independent native observer, be tied to
    the same current topology, and have first-class native probe receipts.
    A single flow cannot simultaneously succeed and be denied.
    """
    probes, forbidden = document.get("probes"), document.get("forbidden_flow")
    if (not isinstance(probes, list) or len(probes) != 2
            or not isinstance(forbidden, dict)
            or set(forbidden) != {"from", "to", "protocol", "port"}
            or any(not text(forbidden.get(k)) for k in ("from", "to", "protocol"))
            or type(forbidden.get("port")) not in {int, type(None)}
            or all(forbidden.get(k) == flow.get(k)
                   for k in ("from", "to", "protocol", "port"))):
        return "independent_negative_flow_missing"
    expected = (("allow", flow), ("deny", forbidden))
    for probe, (outcome, expected_flow) in zip(probes, expected):
        if (not isinstance(probe, dict) or not fresh(probe, now)
                or (probe.get("path_sha256") != path_sha if outcome == "allow"
                    else (probe.get("denied_at_native_ref")
                          != document.get("default_deny_native_ref")
                          or probe.get("enforcement_scope")
                          != document.get("path", {}).get("scope")))
                or any(probe.get(k) != expected_flow.get(k)
                       for k in ("from", "to", "protocol", "port"))
                or probe.get("outcome") != outcome
                or not text(probe.get("native_receipt"))
                or not text(probe.get("observer"))
                or probe.get("observer") != document.get("observer_principal")
                or probe.get("observer") == document.get("writer_principal")
                or probe.get("topology_sha256") != document.get("topology_sha256")):
            return "independent_security_probes_unverified"
    if probes[0]["native_receipt"] == probes[1]["native_receipt"]:
        return "independent_negative_witness_reused"
    return None


def qualify(document: Any, flow: dict[str, Any], now: int) -> dict[str, Any]:
    """Fail-closed E4 *evidence inspection*, not an authorization or signature."""
    if (not isinstance(document, dict) or document.get("schema_version") != 1
            or document.get("source") != "independent_native_observer"
            or not text(document.get("observer_principal"))
            or not text(document.get("writer_principal"))
            or document["observer_principal"] == document["writer_principal"]
            or not fresh(document, now)
            or not text(document.get("topology_sha256"))
            or not text(document.get("default_deny_native_ref"))):
        return hold("independent_native_security_evidence_missing")
    rules, error = effective_rules(document)
    if error:
        return hold(error)
    path_sha, error = path_evidence(document, flow)
    if error:
        return hold(error)
    relevant = []
    for rule in rules:
        group_src = document["groups"][rule["source_group"]]["members"]
        group_dst = document["groups"][rule["destination_group"]]["members"]
        service = document["services"][rule["service_ref"]]
        if (flow.get("from") in group_src
                and flow.get("to") in group_dst
                and service["protocol"] == flow.get("protocol")
                and (flow.get("port") in service["ports"]
                     or (service["protocol"] == "icmp"
                         and flow.get("port") is None
                         and service["ports"] == []))):
            relevant.append(rule)
    if not relevant:
        return hold("effective_native_allow_rule_missing")
    # First matching rule wins. Never skip a higher-priority deny.
    if relevant[0]["action"] != "allow":
        return hold("higher_priority_native_deny")
    if (relevant[0].get("direction") != "both"
            or relevant[0].get("stateful") is not True):
        return hold("native_security_return_state_unqualified")
    if (document["platform"] == "vmware"
            and relevant[0].get("category") == "Ethernet"):
        return hold("nsx_l2_rule_cannot_qualify_ip_flow")
    if not rules or document.get("default_action") != "deny":
        return hold("native_default_deny_unverified")
    error = measured(document, flow, path_sha, now)
    if error:
        return hold(error)
    return {
        "status": "qualified", "reason": None, "native_write_authorized": False,
        "path_sha256": path_sha,
        "effective_rule_native_ref": relevant[0]["native_ref"],
        "evidence_sha256": digest(document),
    }
