"""Controlled independent network probe orchestration.

A connection timeout alone is never proof of firewall denial. Independent
native trace/drop-counter receipts must correlate every probe. Signed E4
acceptance, native write authority, and probe campaign commissioning remain
owned by Assurance and separate from this worker.
"""
from collections.abc import Callable
from typing import Any

from inventory_worker.infrastructure.native import CollectionFailure
from inventory_worker.infrastructure.profile_digest import fingerprint

MAX_PROBES = 1024


def collect(
    approved: dict[str, Any],
    execute: Callable[[dict[str, Any]], dict[str, Any]],
    observe_native: Callable[[dict[str, Any]], dict[str, Any]],
    now: int,
) -> dict[str, Any]:
    items = approved.get("probes")
    if (
        approved.get("schema_version") != 1
        or approved.get("independent_approval_verified") is not True
        or approved.get("native_write_authorized") is not False
        or approved.get("authorized_scope") is None
        or not isinstance(items, list) or not 2 <= len(items) <= MAX_PROBES
        or approved.get("observer_principal") == approved.get("writer_principal")
        or not approved.get("observer_principal")
        or not approved.get("writer_principal")
        or type(approved.get("expires_at")) is not int
        or approved["expires_at"] <= now
    ):
        raise CollectionFailure("independent_probe_campaign_not_commissioned")
    identities = set()
    evidence = []
    for item in items:
        if (not isinstance(item, dict)
                or item.get("expected") not in ("allow", "deny")
                or not isinstance(item.get("id"), str)
                or item["id"] in identities
                or not isinstance(item.get("source_vm_id"), str)
                or not isinstance(item.get("target_vm_id"), str)
                or not isinstance(item.get("protocol"), str)
                or item.get("authorized_scope") != approved["authorized_scope"]
                or not item.get("native_enforcement_point")):
            raise CollectionFailure("invalid_scoped_native_probe")
        identities.add(item["id"])
        result = execute(item)
        native = observe_native(item)
        if (not isinstance(result, dict) or not isinstance(native, dict)
                or native.get("enforcement_point") != item["native_enforcement_point"]
                or native.get("packet_identity_sha256") != fingerprint(item)
                or native.get("observed_by") != approved["observer_principal"]
                or native.get("observed_at") != now
                or not native.get("native_trace_receipt")
                or native.get("native_policy_generation") !=
                    approved.get("native_policy_generation")):
            raise CollectionFailure("independent_native_probe_proof_missing")
        # Connect success must be backed by an application handshake and
        # matching allow trace; denial needs a matching native deny/drop trace.
        if item["expected"] == "allow":
            passed = (result.get("application_handshake") is True
                      and result.get("connected") is True
                      and native.get("decision") == "allow")
        else:
            passed = (result.get("connected") is False
                      and native.get("decision") == "deny"
                      and native.get("counter_increased") is True)
        if not passed:
            raise CollectionFailure("independent_native_probe_failed")
        evidence.append({
            "id": item["id"], "packet_sha256": fingerprint(item),
            "outcome": item["expected"],
            "native_receipt": native["native_trace_receipt"],
            "native_enforcement_point": native["enforcement_point"],
            "observed_at": now, "expires_at": min(now + 30, approved["expires_at"]),
        })
    if (not any(v["outcome"] == "allow" for v in evidence)
            or not any(v["outcome"] == "deny" for v in evidence)):
        raise CollectionFailure("allow_and_deny_probe_coverage_required")
    return {
        "schema_version": 1, "status": "observed_not_authorized",
        "observer_principal": approved["observer_principal"],
        "native_policy_generation": approved["native_policy_generation"],
        "probes": evidence, "receipt_sha256": fingerprint(evidence),
        "native_write_authorized": False,
    }
