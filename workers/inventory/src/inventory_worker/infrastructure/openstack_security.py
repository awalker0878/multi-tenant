"""Canonical Neutron policy rule signatures for exact, scoped comparisons.

Only literal CIDR/port/protocol rules are candidates for field-level
equivalence. Native group/address references need separate owner-qualified
dependency remapping and cannot be compared by ID across installations.
"""
from ipaddress import ip_network
from typing import Any

from inventory_worker.infrastructure.native import CollectionFailure
from inventory_worker.infrastructure.profile_digest import fingerprint

RULE_FIELDS = ("direction", "ethertype", "protocol", "port_range_min",
               "port_range_max", "remote_ip_prefix")


def security_semantics(group: dict[str, Any]) -> str | None:
    if type(group.get("stateful")) is not bool:
        return None
    rules = group.get("security_group_rules")
    if not isinstance(rules, list) or len(rules) > 512:
        raise CollectionFailure("invalid_response")
    canonical = []
    for row in rules:
        if not isinstance(row, dict) or row.get("direction") not in {"ingress", "egress"}:
            raise CollectionFailure("invalid_response")
        if row.get("ethertype") not in {"IPv4", "IPv6"}:
            raise CollectionFailure("invalid_response")
        if row.get("remote_group_id") or row.get("remote_address_group_id"):
            return None
        obj = {k: row.get(k) for k in RULE_FIELDS}
        if obj["protocol"] is not None and not isinstance(obj["protocol"], (str, int)):
            raise CollectionFailure("invalid_response")
        if isinstance(obj["protocol"], str):
            obj["protocol"] = obj["protocol"].lower()
        for p in ("port_range_min", "port_range_max"):
            if obj[p] is not None and (type(obj[p]) is not int or not 0 <= obj[p] <= 65535):
                raise CollectionFailure("invalid_response")
        if obj["remote_ip_prefix"] is not None:
            if not isinstance(obj["remote_ip_prefix"], str):
                raise CollectionFailure("invalid_response")
            try:
                obj["remote_ip_prefix"] = str(ip_network(obj["remote_ip_prefix"], strict=False))
            except ValueError:
                raise CollectionFailure("invalid_response") from None
        canonical.append(obj)
    return fingerprint({"stateful": group["stateful"],
                        "rules": sorted(canonical, key=lambda r: str(sorted(r.items())))})
