"""Read-only NSX Policy API observation: precedence, groups, services, scope.

This is E2 discovery, never a VM's *effective* firewall verdict.
Nested/dynamic group expressions and service expansions require a separately
authorized effective-member/entry collector and E3/E4 independent witness.
"""
import re
from collections.abc import Callable
from typing import Any

from inventory_worker.infrastructure.native import CollectionFailure, exchange, secret
from inventory_worker.infrastructure.profile_digest import fingerprint

ID = re.compile(r"^[A-Za-z0-9_-]{1,100}$")
PAGE_SIZE = 100
MAX_POLICIES = 16
MAX_REFS = 100
NSX_CATEGORY = {"Ethernet", "Emergency", "Infrastructure", "Environment", "Application"}


def _list(
    stream: dict[str, Any], url: str, headers: dict[str, str],
    before_request: Callable[[], None],
) -> list[dict[str, Any]]:
    before_request()
    result = exchange(stream, url + "?page_size=100", headers)
    if not isinstance(result, dict) or result.get("cursor"):
        raise CollectionFailure("invalid_response")
    rows = result.get("results")
    if (not isinstance(rows, list) or len(rows) > PAGE_SIZE
            or any(not isinstance(row, dict) for row in rows)):
        raise CollectionFailure("invalid_response")
    return rows


def _refs(value: Any) -> list[str]:
    if (not isinstance(value, list) or len(value) > MAX_REFS
            or any(not isinstance(v, str)
                   or not (v == "ANY" or v.startswith("/infra/"))
                   or len(v) > 512 or ".." in v for v in value)):
        raise CollectionFailure("invalid_response")
    return sorted(set(value))


def collect_nsx_policy_rules(
    stream: dict[str, Any], domain_id: str, before_request: Callable[[], None],
) -> dict[str, Any]:
    if (stream.get("kind") != "nsx_policy" or stream.get("domain_id") != domain_id
            or not isinstance(domain_id, str) or not ID.fullmatch(domain_id)):
        raise CollectionFailure("permission_denied")

    root = "/policy/api/v1/infra/domains/" + domain_id
    headers = {"Authorization": "Basic " + secret(stream["credential_file"])}
    groups = _list(stream, root + "/groups", headers, before_request)
    services = _list(stream, "/policy/api/v1/infra/services", headers, before_request)
    policies = _list(stream, root + "/security-policies", headers, before_request)
    if len(policies) > MAX_POLICIES:
        raise CollectionFailure("invalid_response")

    def project_catalogue(rows: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
        seen: set[str] = set()
        observed = []
        for item in rows:
            native_id = item.get("id")
            if (not isinstance(native_id, str) or not ID.fullmatch(native_id)
                    or native_id in seen or item.get("marked_for_delete") is True):
                raise CollectionFailure("invalid_response")
            seen.add(native_id)
            observed.append({
                "id": native_id,
                "native_sha256": fingerprint(item),
                "definition_sha256": fingerprint(
                    item.get("expression") if kind == "group"
                    else item.get("service_entries")
                ),
                # A group expression, or an embedded service-list entry, is
                # never evidence that it is effective on a particular VM.
                "resolution": "unverified",
            })
        return observed

    catalogue_groups = project_catalogue(groups, "group")
    catalogue_services = project_catalogue(services, "service")
    entries = []
    seen_policies: set[str] = set()
    for policy in policies:
        identity = policy.get("id")
        if (not isinstance(identity, str) or not ID.fullmatch(identity)
                or identity in seen_policies or policy.get("marked_for_delete") is True):
            raise CollectionFailure("invalid_response")
        seen_policies.add(identity)
        rules = _list(
            stream, root + "/security-policies/" + identity + "/rules",
            headers, before_request,
        )
        scope = _refs(policy.get("scope", []))
        seen_rules: set[str] = set()
        observed_rules = []
        for rule in rules:
            native_id = rule.get("id")
            if (not isinstance(native_id, str) or not ID.fullmatch(native_id)
                    or native_id in seen_rules or rule.get("marked_for_delete") is True
                    or rule.get("action") not in {"ALLOW", "DROP", "REJECT"}
                    or rule.get("direction") not in {"IN", "OUT", "IN_OUT"}):
                raise CollectionFailure("invalid_response")
            seen_rules.add(native_id)
            observed_rules.append({
                "id": native_id, "action": rule["action"],
                "direction": rule["direction"],
                "disabled": rule.get("disabled") is True,
                "sequence_number": rule.get("sequence_number"),
                "source_groups": _refs(rule.get("source_groups", [])),
                "destination_groups": _refs(rule.get("destination_groups", [])),
                "services": _refs(rule.get("services", [])),
                "native_sha256": fingerprint(rule),
                "service_reference_status": "unresolved",
                "group_reference_status": "unresolved",
            })
        entries.append({
            "id": identity,
            "category": policy.get("category"),
            "stateful": policy.get("stateful"),
            "sequence_number": policy.get("sequence_number"),
            "scope": scope,
            "scope_sha256": fingerprint(policy.get("scope")),
            "native_sha256": fingerprint(policy),
            "rules": observed_rules,
        })
    known_groups = {
        "/infra/domains/" + domain_id + "/groups/" + item["id"]
        for item in catalogue_groups
    }
    known_services = {
        "/infra/services/" + item["id"] for item in catalogue_services
    }
    holds = []
    for item in entries:
        if (item["category"] not in NSX_CATEGORY
                or type(item["sequence_number"]) is not int
                or type(item["stateful"]) is not bool):
            holds.append("nsx_native_policy_order_or_state_unknown")
        if set(item["scope"]) - known_groups:
            holds.append("nsx_native_policy_scope_unresolved")
        for rule in item["rules"]:
            if "ANY" in (rule["source_groups"] + rule["destination_groups"] + rule["services"]):
                holds.append("nsx_wildcard_scope_requires_independent_qualification")
            if type(rule["sequence_number"]) is not int:
                holds.append("nsx_rule_order_unresolved")
            if (set(rule["source_groups"] + rule["destination_groups"]) - known_groups
                    or set(rule["services"]) - known_services):
                holds.append("nsx_native_rule_references_missing")
    # All dynamic membership, nesting, service-entry and applied-to semantics
    # stay unresolved until separately qualified; no E2 success escapes.
    holds.extend(["nsx_effective_membership_unverified",
                  "nsx_service_expansion_unverified",
                  "nsx_policy_precedence_unqualified"])
    return {
        "domain_id": domain_id,
        "api": "nsx-policy-v1",
        "policies": entries,
        "groups": catalogue_groups,
        "services": catalogue_services,
        "holds": sorted(set(holds)),
        "semantic_qualification": "unresolved",
        "source_vm_attachment": "unverified",
        "native_write_authorized": False,
    }
