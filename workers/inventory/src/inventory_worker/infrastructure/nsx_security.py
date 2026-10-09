"""Read-only, explicitly enrolled NSX Policy API firewall catalogue.

NSX is a separate managed API/credential boundary from vCenter. This collector
must only be called with an NSX-specific enrolled origin and commissioned domain.
It does NOT establish which NSX policies apply to a VM, resolve groups/service
objects or approve equivalence with VMware/AHV/OpenStack rules.
"""
import re
from collections.abc import Callable
from typing import Any

from inventory_worker.infrastructure.native import CollectionFailure, exchange, secret
from inventory_worker.infrastructure.profile_digest import fingerprint

ID = re.compile(r"^[A-Za-z0-9_-]{1,100}$")
PAGE_SIZE = 100
MAX_POLICIES = 16


def collect_nsx_policy_rules(
    stream: dict[str, Any], domain_id: str, before_request: Callable[[], None],
) -> dict[str, Any]:
    if (
        stream.get("kind") != "nsx_policy"
        or stream.get("domain_id") != domain_id
        or not isinstance(domain_id, str)
        or not ID.fullmatch(domain_id)
    ):
        raise CollectionFailure("permission_denied")

    root = "/policy/api/v1/infra/domains/" + domain_id + "/security-policies"
    headers = {"Authorization": "Basic " + secret(stream["credential_file"])}
    # Never consume a response supplied next URL or cross the enrolled origin.
    before_request()
    reply = exchange(stream, root + "?page_size=100", headers)
    if not isinstance(reply, dict) or reply.get("cursor"):
        raise CollectionFailure("invalid_response")
    policies = reply.get("results")
    if not isinstance(policies, list) or len(policies) > MAX_POLICIES:
        raise CollectionFailure("invalid_response")
    entries = []
    seen_policies: set[str] = set()
    for policy in policies:
        if not isinstance(policy, dict):
            raise CollectionFailure("invalid_response")
        identity = policy.get("id")
        if (
            not isinstance(identity, str) or not ID.fullmatch(identity)
            or identity in seen_policies or policy.get("marked_for_delete") is True
        ):
            raise CollectionFailure("invalid_response")
        seen_policies.add(identity)
        before_request()
        response = exchange(stream, root + "/" + identity + "/rules?page_size=100", headers)
        if not isinstance(response, dict) or response.get("cursor"):
            raise CollectionFailure("invalid_response")
        rules = response.get("results")
        if not isinstance(rules, list) or len(rules) > PAGE_SIZE:
            raise CollectionFailure("invalid_response")
        seen_rules: set[str] = set()
        observed_rules = []
        for rule in rules:
            if not isinstance(rule, dict):
                raise CollectionFailure("invalid_response")
            native_id = rule.get("id")
            if (
                not isinstance(native_id, str) or not ID.fullmatch(native_id)
                or native_id in seen_rules or rule.get("marked_for_delete") is True
                or rule.get("action") not in {"ALLOW", "DROP", "REJECT"}
                or rule.get("direction") not in {"IN", "OUT", "IN_OUT"}
            ):
                raise CollectionFailure("invalid_response")
            seen_rules.add(native_id)
            observed_rules.append({
                "id": native_id,
                "action": rule["action"],
                "direction": rule["direction"],
                "disabled": rule.get("disabled") is True,
                "native_sha256": fingerprint(rule),
                "service_reference_status": "unresolved",
                "group_reference_status": "unresolved",
            })
        entries.append({
            "id": identity,
            "sequence_number": policy.get("sequence_number"),
            "scope_sha256": fingerprint(policy.get("scope")),
            "native_sha256": fingerprint(policy),
            "rules": observed_rules,
        })
    return {
        "domain_id": domain_id,
        "api": "nsx-policy-v1",
        "policies": entries,
        "semantic_qualification": "unresolved",
        "source_vm_attachment": "unverified",
        "native_write_authorized": False,
    }
