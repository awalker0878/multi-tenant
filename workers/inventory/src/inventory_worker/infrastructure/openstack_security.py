"""Canonical Neutron policy rules; permit only literal project-scoped flow choices.

Security-group identities are selectable separately from individual native rules.
A VM's application-required flows cannot be inferred from these ACLs; they still
require owner approval and independent end-to-end allow/deny measurements.
"""
from ipaddress import ip_network
from typing import Any

from inventory_worker.infrastructure.native import CollectionFailure
from inventory_worker.infrastructure.profile_digest import fingerprint

RULE_FIELDS = ("direction", "ethertype", "protocol", "port_range_min",
               "port_range_max", "remote_ip_prefix")


def rule_choices(group: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Return verified native rule IDs and their portable *literal* semantics.

    Referenced groups/address groups and unknown stateful behavior deliberately
    have no equivalent rule-choice dropdown; no cross-cloud IDs are guessed.
    """
    if type(group.get("stateful")) is not bool:
        return None
    rules = group.get("security_group_rules")
    if not isinstance(rules, list) or len(rules) > 512:
        raise CollectionFailure("invalid_response")
    chosen = []
    seen = set()
    for row in rules:
        if not isinstance(row, dict) or row.get("direction") not in {"ingress", "egress"}:
            raise CollectionFailure("invalid_response")
        if row.get("ethertype") not in {"IPv4", "IPv6"}:
            raise CollectionFailure("invalid_response")
        if row.get("remote_group_id") or row.get("remote_address_group_id"):
            return None
        identity = row.get("id")
        if not isinstance(identity, str) or not identity or identity in seen:
            raise CollectionFailure("invalid_response")
        seen.add(identity)
        obj = {k: row.get(k) for k in RULE_FIELDS}
        if obj["protocol"] is not None and (
            type(obj["protocol"]) not in (str, int) or
            (type(obj["protocol"]) is str and not obj["protocol"])
        ):
            raise CollectionFailure("invalid_response")
        if type(obj["protocol"]) is str:
            obj["protocol"] = obj["protocol"].lower()
        for field in ("port_range_min", "port_range_max"):
            if obj[field] is not None and (
                type(obj[field]) is not int or not 0 <= obj[field] <= 65535
            ):
                raise CollectionFailure("invalid_response")
        if obj["remote_ip_prefix"] is not None:
            if not isinstance(obj["remote_ip_prefix"], str):
                raise CollectionFailure("invalid_response")
            try:
                obj["remote_ip_prefix"] = str(ip_network(obj["remote_ip_prefix"], strict=False))
            except ValueError:
                raise CollectionFailure("invalid_response") from None
        chosen.append({"id": identity, **obj, "semantic_sha256": fingerprint(obj)})
    return sorted(chosen, key=lambda r: r["id"])


def security_semantics(group: dict[str, Any]) -> str | None:
    choices = rule_choices(group)
    if choices is None:
        return None
    return fingerprint({"stateful": group["stateful"],
                        "rules": sorted(
                            [{k: item[k] for k in RULE_FIELDS} for item in choices],
                            key=lambda rule: str(sorted(rule.items())),
                        )})
