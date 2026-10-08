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
