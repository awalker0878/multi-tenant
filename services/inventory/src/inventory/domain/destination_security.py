"""Source-derived security requirements: never synthesize required flows.

Only Neutron port security-group attachment IDs have a known canonical
source in the current workloads. Other hypervisors require a commissioned
native source-policy observer before a destination security mapping can be
authorized. Missing observation is UNKNOWN, not an empty required set.
"""
from typing import Any

from inventory.domain.discovery import Rejected


def source_security_ids(source: dict[str, Any]) -> list[str] | None:
    if not source.get("nics"):
        return []
    if source.get("platform") != "openstack" or source.get("schema_version") != 3:
        return None
    native = source.get("native")
    metadata = native.get("metadata") if isinstance(native, dict) else None
    ports = metadata.get("ports") if isinstance(metadata, dict) else None
    if not isinstance(ports, list) or len(ports) != len(source["nics"]):
        return None
    scope = source.get("native_scope")
    if not isinstance(scope, str) or not scope:
        return None
    keys: set[str] = set()
    port_ids: set[str] = set()
    for port in ports:
        if not isinstance(port, dict):
            return None
        port_id = port.get("id")
        groups = port.get("security_groups")
        if (
            not isinstance(port_id, str) or not port_id
            or port_id in port_ids
            or port.get("project_id", port.get("tenant_id")) != scope
            or type(port.get("port_security_enabled")) is not bool
            or not isinstance(groups, list)
            or len(groups) > 64
            or any(not isinstance(group, str) or not group for group in groups)
            or len(groups) != len(set(groups))
        ):
            return None
        port_ids.add(port_id)
        if port["port_security_enabled"] is False:
            # Explicitly bypassed port security is a security behavior, not
            # "there are no required flows". Independent mapping is needed.
            return None
        keys.update(groups)
    return sorted(keys)


def select_security_mappings(
    chosen: Any, source_ids: list[str] | None,
    destination_ids: set[str],
) -> list[str]:
    if source_ids is None:
        raise Rejected("source_security_policy_observation_required")
    if not isinstance(chosen, list) or len(chosen) != len(source_ids) or len(chosen) > 64:
        raise Rejected("required_security_mappings_incomplete")
    seen_source: set[str] = set()
    seen_target: set[str] = set()
    for row in chosen:
        if not isinstance(row, dict) or set(row) != {"source_id", "destination_id"}:
            raise Rejected("invalid_security_mapping")
        original, destination = row["source_id"], row["destination_id"]
        if (
            not isinstance(original, str)
            or not isinstance(destination, str)
            or original not in source_ids
            or original in seen_source
            or destination not in destination_ids
            or destination in seen_target
        ):
            raise Rejected("unobserved_security_mapping")
        seen_source.add(original)
        seen_target.add(destination)
    if seen_source != set(source_ids):
        raise Rejected("required_security_mappings_incomplete")
    return [row["destination_id"] for row in chosen]

def require_matching_openstack_rules(
    source: dict[str, Any], chosen: list[dict[str, str]], target: dict[str, Any],
) -> None:
    """Selection is allowed only where observed rules are behaviorally identical.

    Unknown statefulness, group references, missing proofs and differing
    allow/deny rules fail closed, pending a separately qualified translation.
    """
    native = source.get("native", {})
    metadata = native.get("metadata", {}) if isinstance(native, dict) else {}
    originals = metadata.get("security_groups") if isinstance(metadata, dict) else None
    if not isinstance(originals, list):
        raise Rejected("source_security_rules_unobserved")
    source_by_id = {row.get("id"): row for row in originals if isinstance(row, dict)}
    if len(source_by_id) != len(originals):
        raise Rejected("source_security_rules_ambiguous")
    destination_by_id = {row["id"]: row for row in target["security_groups"]}
    for mapping in chosen:
        original = source_by_id.get(mapping["source_id"])
        destination = destination_by_id.get(mapping["destination_id"])
        if (
            not isinstance(original, dict)
            or destination is None
            or not isinstance(original.get("semantics_sha256"), str)
            or not original["semantics_sha256"]
            or original["semantics_sha256"] != destination.get("semantics_sha256")
        ):
            raise Rejected("destination_security_flow_equivalence_unproven")


def source_rule_choices(source: dict[str, Any]) -> list[dict[str, str]] | None:
    """Observed source Neutron ACL rules, not inferred application dependencies.

    None means incomplete/unsupported source discovery and must never turn
    into an empty list of requirements. The source group must be attached to
    a VM port and its native project must match the VM's project.
    """
    groups = source_security_ids(source)
    if groups is None:
        return None
    if not groups:
        return []
    metadata = source.get("native", {}).get("metadata", {})
    observed = metadata.get("security_groups")
    if not isinstance(observed, list) or len(observed) > 64:
        return None
    by_id = {g.get("id"): g for g in observed if isinstance(g, dict)}
    if len(by_id) != len(observed):
        return None
    rows = []
    for group_id in groups:
        group = by_id.get(group_id)
        if not isinstance(group, dict) or group.get("project_id") != source["native_scope"]:
            return None
        rules = group.get("rules")
        if not isinstance(rules, list) or len(rules) > 512:
            return None
        rule_ids = set()
        for rule in rules:
            if not isinstance(rule, dict):
                return None
            identity, semantics = rule.get("id"), rule.get("semantic_sha256")
            if (
                not isinstance(identity, str) or not identity or identity in rule_ids
                or not isinstance(semantics, str) or len(semantics) != 64
                or any(c not in "0123456789abcdef" for c in semantics)
            ):
                return None
            rule_ids.add(identity)
            rows.append({"source_group_id": group_id, "source_rule_id": identity,
                         "semantic_sha256": semantics})
            if len(rows) > 1024:
                return None
    return rows


def validate_security_flow_choices(
    source: dict[str, Any], destination: dict[str, Any],
    groups: list[dict[str, str]], selected: Any,
) -> bool:
    """Require API-discovered destination IDs for every source ACL rule.

    Returns False only for incomplete source observations that must hold
    review confirmation. No caller may treat False as an accepted mapping.
    """
    requirements = source_rule_choices(source)
    if requirements is None:
        if selected not in (None, []):
            raise Rejected("source_security_rule_observation_required")
        return False
    # A verified empty source rule inventory must not require invented rules
    # or manufacture a destination feature solely to satisfy the form.
    if not requirements and selected is None:
        return True
    if not isinstance(selected, list) or len(selected) != len(requirements):
        raise Rejected("required_security_flow_mappings_incomplete")
    binding = {row["source_id"]: row["destination_id"] for row in groups}
    observed = {g["id"]: g for g in destination["security_groups"]}
    required = {(r["source_group_id"], r["source_rule_id"]): r for r in requirements}
    seen_source, seen_target = set(), set()
    for row in selected:
        if not isinstance(row, dict) or set(row) != {
            "source_group_id", "source_rule_id", "destination_rule_id"
        }:
            raise Rejected("invalid_security_flow_mapping")
        group_id, source_rule = row["source_group_id"], row["source_rule_id"]
        destination_rule = row["destination_rule_id"]
        original = required.get((group_id, source_rule)) if isinstance(group_id, str) and isinstance(source_rule, str) else None
        target_group = observed.get(binding.get(group_id)) if isinstance(group_id, str) else None
        native_rules = target_group.get("rules") if isinstance(target_group, dict) else None
        match = (
            next((rule for rule in native_rules
                  if isinstance(rule, dict) and rule.get("id") == destination_rule), None)
            if isinstance(native_rules, list) and isinstance(destination_rule, str) else None
        )
        if (
            original is None or match is None
            or match.get("semantic_sha256") != original["semantic_sha256"]
            or (group_id, source_rule) in seen_source
            or (binding[group_id], destination_rule) in seen_target
        ):
            raise Rejected("destination_security_rule_choice_unproven")
        seen_source.add((group_id, source_rule))
        seen_target.add((binding[group_id], destination_rule))
    if seen_source != set(required):
        raise Rejected("required_security_flow_mappings_incomplete")
    return True
