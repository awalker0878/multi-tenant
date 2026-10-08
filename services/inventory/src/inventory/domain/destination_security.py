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
