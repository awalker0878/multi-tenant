"""Inventory-owned, bounded evaluation of migration collection-manifest observations.

A proposed field crosswalk is never evidence. Every observed attribute must
have a scoped, fresh, independently identifiable collection receipt; owner and
conditional fields remain held unless explicitly resolved. This reports data
completeness, not Assurance E3/E4 qualification or native permission.
"""

import re
from typing import Any

from inventory.domain.discovery import Rejected, digest


def installed_version_supported(
    api_version: Any, family: Any,
    installed: dict[str, list[str] | dict[str, str]] | None,
) -> bool:
    """Exact namespace or bounded, native-discovered microversion range only."""
    if not isinstance(api_version, str) or not isinstance(family, str) or installed is None:
        return False
    candidate = installed.get(family)
    if isinstance(candidate, list):
        return api_version in candidate
    if not isinstance(candidate, dict) or set(candidate) != {"min_version", "max_version"}:
        return False
    def number(value: Any) -> tuple[int, ...] | None:
        if not isinstance(value, str) or not re.fullmatch(r"v?[0-9]+(?:\\.[0-9]+){1,3}", value):
            return None
        return tuple(int(part) for part in value.removeprefix("v").split("."))
    actual = number(api_version)
    lower = number(candidate["min_version"])
    upper = number(candidate["max_version"])
    return bool(
        actual is not None and lower is not None and upper is not None
        and len(actual) == len(lower) == len(upper)
        and actual[0] == lower[0] == upper[0]
        and lower <= actual <= upper
    )


def evaluate(
    manifest: dict[str, Any], platform: str, scope: str,
    installation_id: str, generation_id: str, installed_tuple_sha256: str,
    observations: list[dict[str, Any]], applicability: list[dict[str, Any]], now: int,
    installed_namespaces: dict[str, list[str] | dict[str, str]] | None = None,
    receipt_expires_at: int | None = None,
) -> dict[str, Any]:
    if (manifest.get("schema_version") != 1 or platform not in manifest.get("platforms", {})
            or scope not in {"source", "target", "owner"} or type(now) is not int):
        raise Rejected("migration_collection_contract_invalid")
    rows = manifest["platforms"][platform].get("attributes")
    if not isinstance(rows, list) or not rows or len(rows) > 256:
        raise Rejected("migration_collection_manifest_invalid")
    if (not isinstance(observations, list) or len(observations) > 512
            or not isinstance(applicability, list) or len(applicability) > 256):
        raise Rejected("migration_collection_receipt_bound")
    expected = {"installation_id": installation_id, "generation_id": generation_id,
                "installed_tuple_sha256": installed_tuple_sha256, "scope": scope}
    allowed_ids = {row["id"] for row in rows if row["scope"] == scope}
    if len(allowed_ids) != sum(row["scope"] == scope for row in rows):
        raise Rejected("migration_collection_manifest_duplicate")
    for collection in (observations, applicability):
        keys: set[str] = set()
        for item in collection:
            if not isinstance(item, dict) or any(item.get(k) != v for k, v in expected.items()):
                raise Rejected("migration_collection_cross_scope_evidence", 403)
            identity = item.get("attribute_id")
            if not isinstance(identity, str) or identity in keys:
                raise Rejected("migration_collection_ambiguous_receipt")
            if identity not in allowed_ids:
                raise Rejected("migration_collection_undeclared_attribute", 423)
            keys.add(identity)
    facts = {row["attribute_id"]: row for row in observations}
    predicates = {row["attribute_id"]: row for row in applicability}
    results: list[dict[str, Any]] = []
    deadlines: list[int] = []
    for requirement in rows:
        if requirement["scope"] != scope:
            continue
        key = requirement["id"]
        if any(existing["attribute_id"] == key for existing in results):
            raise Rejected("migration_collection_manifest_duplicate")
        status, reason = "held", "field_unobserved"
        conditional = requirement["condition"] != "always"
        predicate = predicates.get(key)
        predicate_deadline: int | None = None
        applicable = not conditional
        if conditional:
            if predicate is None or predicate.get("condition") != requirement["condition"]:
                reason = "applicability_not_independently_resolved"
            elif (type(predicate.get("applicable")) is not bool
                  or not isinstance(predicate.get("evidence_sha256"), str)
                  or not re.fullmatch(r"[a-f0-9]{64}", predicate["evidence_sha256"])
                  or type(predicate.get("observed_at")) is not int
                  or not 0 <= now - predicate["observed_at"] < requirement["max_age_seconds"]):
                reason = "applicability_evidence_stale_or_invalid"
            elif predicate["applicable"] is False:
                status, reason = "not_applicable", "independently_observed_absent"
                predicate_deadline = predicate["observed_at"] + requirement["max_age_seconds"]
            else:
                applicable = True
                predicate_deadline = predicate["observed_at"] + requirement["max_age_seconds"]
        if status == "not_applicable":
            if predicate_deadline is not None:
                deadlines.append(predicate_deadline)
            results.append({"attribute_id": key, "status": status, "reason": reason,
                            "severity": requirement["severity"]})
            continue
        if not applicable:
            results.append({"attribute_id": key, "status": status,
                            "reason": reason, "severity": requirement["severity"]})
            continue
        evidence = facts.get(key)
        if evidence is not None:
            if (evidence.get("collection_method") != requirement["collection_method"]
                    or evidence.get("api_family") != requirement["api_family"]):
                reason = "collection_provenance_mismatch"
            elif (evidence.get("value_present") is not True
                  or not isinstance(evidence.get("evidence_sha256"), str)
                  or not re.fullmatch(r"[a-f0-9]{64}", evidence["evidence_sha256"])):
                reason = "collection_evidence_missing"
            elif (type(evidence.get("observed_at")) is not int
                  or not 0 <= now - evidence["observed_at"] < requirement["max_age_seconds"]):
                reason = "collection_evidence_stale"
            elif requirement["collection_method"] == "native_get" and (
                    not isinstance(evidence.get("native_operation"), str)
                    or not re.fullmatch(
                        r"GET /[A-Za-z0-9_./:%?=&-]{1,400}",
                        evidence["native_operation"])
                    or not isinstance(evidence.get("value_sha256"), str)
                    or not re.fullmatch(r"[a-f0-9]{64}", evidence["value_sha256"])):
                reason = "native_get_operation_or_value_digest_missing"
            elif requirement["collection_status"] == "external_evidence_required" and (
                    evidence.get("independent_review") is not True):
                reason = "independent_owner_evidence_required"
            elif requirement["api_family"] is not None and not installed_version_supported(
                    evidence.get("api_version"), requirement["api_family"],
                    installed_namespaces,
            ):
                # A string alone is not an installed namespace witness.
                reason = "installed_api_version_not_observed"
            else:
                status, reason = "observed", "scoped_fresh_observation"
                deadline = evidence["observed_at"] + requirement["max_age_seconds"]
                if predicate_deadline is not None:
                    deadline = min(deadline, predicate_deadline)
                deadlines.append(deadline)
        results.append({"attribute_id": key, "status": status,
                        "reason": reason, "severity": requirement["severity"]})
    holds = sorted(row["attribute_id"] + ":" + row["reason"] for row in results
                   if row["status"] == "held")
    expiry = min(deadlines) if len(deadlines) == len(results) else now
    if receipt_expires_at is not None:
        if type(receipt_expires_at) is not int:
            raise Rejected("migration_collection_receipt_expiry_invalid")
        expiry = min(expiry, receipt_expires_at)
    if expiry <= now and not holds:
        holds.append("migration_collection_evidence_expired")
    result = {
        "schema_version": 1, "platform": platform, "scope": scope,
        "installation_id": installation_id, "generation_id": generation_id,
        "installed_tuple_sha256": installed_tuple_sha256,
        "manifest_sha256": digest(manifest), "evaluated_at": now,
        "expires_at": expiry,
        "status": "complete" if not holds else "held",
        "attributes": results, "holds": holds,
        "independent_e3_e4_qualification": False,
        "native_write_authorized": False,
    }
    result["coverage_sha256"] = digest(result)
    return result
