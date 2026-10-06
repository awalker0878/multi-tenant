"""P05 admission contract evaluation. P06 owns durable jobs and immediate effect checks."""

import hashlib
import json
from typing import Any


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(",", ":")
        ).encode()
    ).hexdigest()


def evaluate(
    content: dict[str, Any], binding: dict[str, Any], current: dict[str, Any], now: int
) -> dict[str, Any]:
    """Only independently authenticated owner adapters may supply current receipts."""
    holds: list[str] = []
    material = {k: v for k, v in binding.items() if k != "digest"}
    if (
        binding.get("digest") != digest(material)
        or binding.get("content_digest") != digest(content)
        or binding.get("canonicalization") != "p05-json-v1"
        or content.get("canonicalization") != "p05-json-v1"
    ):
        holds.append("plan_integrity")
    scope = content["scope"]
    if any(
        binding.get(k) != scope.get(k)
        for k in ("tenant_id", "site_id", "environment", "resource_id")
    ):
        holds.append("scope_changed")
    for key in ("action", "lane", "executor_ids", "valid_until"):
        if content.get(key) != binding.get(key):
            holds.append("binding_changed")
    if min(content["valid_until"], content["input_fresh_until"]) <= now:
        holds.append("expired_plan_or_facts")
    if current.get("scope") != scope:
        holds.append("scope_changed")
    if current.get("input_digests") != content["input_digests"]:
        holds.append("input_changed")
    if current.get("artifacts") != content["artifacts"]:
        holds.append("artifact_changed")
    for key in (
        "entitled",
        "commissioned",
        "ownership_current",
        "state_current",
        "change_window",
        "emergency_stop_clear",
    ):
        if current.get(key) is not True:
            holds.append(key + "_not_confirmed")
    if current.get("actor_id") not in binding["executor_ids"]:
        holds.append("executor_mismatch")
    approval = current.get("approval", {})
    if (
        approval.get("state") != "approved"
        or approval.get("revoked") is not False
        or approval.get("plan_digest") != binding["digest"]
        or approval.get("plan_id") != binding["plan_id"]
        or approval.get("plan_revision") != binding["revision"]
        or approval.get("scope") != scope
        or approval.get("approver_grant_current") is not True
        or approval.get("expires_at", 0) <= now
        or approval.get("approver_id") in {binding["requested_by"], current.get("actor_id")}
    ):
        holds.append("approval_not_current_and_bound")
    if content["lane"] == "operational":
        if not content["execution_ready"] or content["holds"]:
            holds.append("plan_not_operationally_eligible")
        if current.get("exact_tuple_qualified") is not True or current.get(
            "qualification_level"
        ) not in {"E3", "E4"}:
            holds.append("exact_tuple_qualification_missing")
        if current.get("lane") != "operational":
            holds.append("lane_mismatch")
    else:
        campaign = current.get("campaign", {})
        required = {
            "scope": scope,
            "action": content["action"],
            "method": content["method"],
            "installed_tuple": content["installed_tuple"],
            "artifacts": content["artifacts"],
            "plan_digest": binding["digest"],
            "actor_id": current.get("actor_id"),
        }
        if (
            current.get("lane") != "isolated_campaign"
            or current.get("environment_class") != "isolated_lab"
            or campaign.get("environment_class") != "isolated_lab"
            or any(campaign.get(k) != v for k, v in required.items())
            or campaign.get("expires_at", 0) <= now
            or campaign.get("revoked") is not False
            or not campaign.get("endpoint_allowlist")
            or not campaign.get("credential_scope_refs")
            or not campaign.get("data_scope")
            or not campaign.get("cleanup_owner")
            or campaign.get("max_effects", 0) < len(content["effects"])
            or current.get("endpoints") != campaign.get("endpoint_allowlist")
            or current.get("credential_scope_refs") != campaign.get("credential_scope_refs")
        ):
            holds.append("campaign_scope_not_authorized")
        # Lab authority may waive qualification alone, never missing isolation/custody/facts.
        permitted = {"exact_tuple_qualification_missing_or_stale", "dimension_not_qualified"}
        if set(content["holds"]) - permitted:
            holds.append("campaign_safety_inputs_missing")
    receipts = current.get("reservations", [])
    for intent in content["reservation_intents"]:
        matches = [
            r
            for r in receipts
            if all(r.get(k) == intent.get(k) for k in ("owner", "kind", "amount", "scope"))
        ]
        if (
            len(matches) != 1
            or matches[0].get("state") not in {"reserved", "confirmed"}
            or matches[0].get("plan_digest") != binding["digest"]
            or matches[0].get("expires_at", 0) <= now
            or not matches[0].get("receipt_id")
        ):
            holds.append("reservation_not_confirmed:" + intent["kind"])
    if current.get("evaluated_at", 0) > now or now - current.get("evaluated_at", 0) > 5:
        holds.append("authority_snapshot_stale")
    return {
        "contract_version": 1,
        "admissible": not holds,
        "holds": sorted(set(holds)),
        "plan_digest": binding["digest"],
        "content_digest": binding["content_digest"],
        "scope": scope,
        "lane": content["lane"],
        "evaluated_at": now,
        "current_receipts_digest": digest(current),
        "native_write_authorized": False,
        "atomic_record_required": [
            "admission",
            "command_receipt",
            "reservation_bindings",
            "dispatch_outbox",
        ],
        "recheck_boundaries": [
            "admission_transaction",
            "before_each_effect",
            "after_uncertain_outcome",
            "after_revocation",
            "after_restore",
            "after_state_or_artifact_change",
        ],
    }
