"""Inventory-owned, bounded evaluation of migration collection-manifest observations.

A proposed field crosswalk is never evidence. Every observed attribute must
have a scoped, fresh, independently identifiable collection receipt; owner and
conditional fields remain held unless explicitly resolved. This reports data
completeness, not Assurance E3/E4 qualification or native permission.
"""

from typing import Any

from inventory.domain.discovery import Rejected, digest


def evaluate(
    manifest: dict[str, Any], platform: str, scope: str,
    installation_id: str, generation_id: str, installed_tuple_sha256: str,
    observations: list[dict[str, Any]], applicability: list[dict[str, Any]], now: int,
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
    for collection in (observations, applicability):
        keys: set[str] = set()
        for item in collection:
            if not isinstance(item, dict) or any(item.get(k) != v for k, v in expected.items()):
                raise Rejected("migration_collection_cross_scope_evidence", 403)
            identity = item.get("attribute_id")
            if not isinstance(identity, str) or identity in keys:
                raise Rejected("migration_collection_ambiguous_receipt")
            keys.add(identity)
    facts = {row["attribute_id"]: row for row in observations}
    predicates = {row["attribute_id"]: row for row in applicability}
    results: list[dict[str, Any]] = []
    for requirement in rows:
        if requirement["scope"] != scope:
            continue
        key = requirement["id"]
        if any(existing["attribute_id"] == key for existing in results):
            raise Rejected("migration_collection_manifest_duplicate")
        status, reason = "held", "field_unobserved"
        conditional = requirement["condition"] != "always"
        predicate = predicates.get(key)
        if conditional:
            if predicate is None or predicate.get("condition") != requirement["condition"]:
                reason = "applicability_not_independently_resolved"
            elif (type(predicate.get("applicable")) is not bool
                  or not isinstance(predicate.get("evidence_sha256"), str)
                  or type(predicate.get("observed_at")) is not int
                  or not 0 <= now - predicate["observed_at"] < requirement["max_age_seconds"]):
                reason = "applicability_evidence_stale_or_invalid"
            elif predicate["applicable"] is False:
                status, reason = "not_applicable", "independently_observed_absent"
        if status == "not_applicable":
            results.append({"attribute_id": key, "status": status, "reason": reason,
                            "severity": requirement["severity"]})
            continue
        if conditional and (predicate is None or predicate.get("applicable") is not True
                            or predicate.get("condition") != requirement["condition"]
                            or type(predicate.get("observed_at")) is not int
                            or not 0 <= now - predicate["observed_at"]
                            < requirement["max_age_seconds"]):
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
                  or len(evidence["evidence_sha256"]) != 64):
                reason = "collection_evidence_missing"
            elif (type(evidence.get("observed_at")) is not int
                  or not 0 <= now - evidence["observed_at"] < requirement["max_age_seconds"]):
                reason = "collection_evidence_stale"
            elif requirement["collection_status"] == "external_evidence_required" and (
                    evidence.get("independent_review") is not True):
                reason = "independent_owner_evidence_required"
            elif requirement["api_family"] is not None and not isinstance(
                    evidence.get("api_version"), str):
                reason = "installed_api_version_unresolved"
            else:
                status, reason = "observed", "scoped_fresh_observation"
        results.append({"attribute_id": key, "status": status,
                        "reason": reason, "severity": requirement["severity"]})
    holds = sorted(row["attribute_id"] + ":" + row["reason"] for row in results
                   if row["status"] == "held")
    result = {
        "schema_version": 1, "platform": platform, "scope": scope,
        "installation_id": installation_id, "generation_id": generation_id,
        "installed_tuple_sha256": installed_tuple_sha256,
        "manifest_sha256": digest(manifest), "evaluated_at": now,
        "status": "complete" if not holds else "held",
        "attributes": results, "holds": holds,
        "independent_e3_e4_qualification": False,
        "native_write_authorized": False,
    }
    result["coverage_sha256"] = digest(result)
    return result
