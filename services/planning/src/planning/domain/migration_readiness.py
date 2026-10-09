"""One fail-closed migration route-readiness projection shared with native admission.

Planning composes this projection; it never signs native observations or acts
as a substitute for Catalogue, Inventory or Assurance custody. A route record
is NOT a VM-level admission receipt. A specific workload must also pass the
separately owned confirmed-review, source-intent and native-effect gates.
"""

from typing import Any

from planning.domain.model import digest


def eligible_field_dispositions(workloads: Any) -> bool:
    """Fail closed on aggregate 'matched' claims with unresolved required fields.

    Wire v2 does not carry an independently reusable E4 transformation receipt.
    Until a new signed provenance contract is commissioned, a required
    qualified_transformation cannot independently establish admission.
    """
    if not isinstance(workloads, list) or not workloads or len(workloads) > 100:
        return False
    ids: set[str] = set()
    for row in workloads:
        if not isinstance(row, dict) or row.get("status") != "matched" or row.get("holds") != []:
            return False
        workload_id = row.get("workload_id")
        if not isinstance(workload_id, str) or not workload_id or workload_id in ids:
            return False
        ids.add(workload_id)
        fields = row.get("field_dispositions")
        if not isinstance(fields, list) or len(fields) > 256:
            return False
        seen: set[str] = set()
        for field in fields:
            if not isinstance(field, dict) or not isinstance(field.get("field"), str):
                return False
            name = field["field"]
            if not name or name in seen:
                return False
            seen.add(name)
            if field.get("required") is True and (
                field.get("disposition") != "matched"
                or field.get("evidence_source") not in {
                    "inventory_native_profile", "independent_e4",
                }
                or field.get("evidence_age_seconds") is None
            ):
                return False
    return True


def resolve(
    route: dict[str, Any], native: dict[str, Any], api: dict[str, Any],
    scope: dict[str, str], tranche_sha256: str, release_sha256: str,
    expires_at: int, now: int,
) -> dict[str, Any]:
    """Materialize route-wide findings without trusting browser declarations."""
    blockers = list(native.get("blockers", []))
    if not isinstance(route.get("api_usage"), list) or not route["api_usage"]:
        blockers.append("route_api_usage_manifest_required")
    if not isinstance(api.get("cases"), list) or not api["cases"]:
        blockers.append("api_capability_evidence_missing")
    if api.get("operationally_eligible") is not True:
        blockers.append("api_capabilities_unresolved")
    if native.get("native_qualified") is not True:
        blockers.append("independent_e3_route_qualification_required")
    if native.get("operationally_accepted") is not True:
        blockers.append("independent_e4_receiving_acceptance_required")
    if expires_at <= now:
        blockers.append("migration_tranche_expired")
    # Each admitted operation is bound to the earlier of its installed
    # namespace/entitlement discovery and exact-version qualification.
    # Native qualification expiry is authoritative when present.
    deadlines = [expires_at]
    native_deadline = native.get("expires_at")
    if type(native_deadline) is int:
        deadlines.append(native_deadline)
    for case in api.get("cases", []) if isinstance(api.get("cases"), list) else []:
        if case.get("status") == "eligible" or case.get("omission_accepted") is True:
            deadline = case.get("expires_at")
            if type(deadline) is not int or deadline <= now:
                blockers.append("api_capability_evidence_expired_or_unbounded")
            else:
                deadlines.append(deadline)
    expires_at = min(deadlines)
    if expires_at <= now:
        blockers.append("migration_readiness_evidence_expired")
    if route["source"]["installation_id"] == route["target"]["installation_id"]:
        blockers.append("distinct_migration_environments_required")
    if native.get("route_sha256") != digest(route):
        blockers.append("route_qualification_binding_changed")
    if any(case.get("status") != "eligible" and not case.get("omission_accepted", False)
           for case in api.get("cases", [])):
        blockers.append("api_feature_unresolved")
    unique = sorted(set(blockers))
    result: dict[str, Any] = {
        "schema_version": 1,
        "kind": "migration_route_readiness",
        "scope": scope,
        "route_sha256": digest(route),
        "tranche_sha256": tranche_sha256,
        "release_sha256": release_sha256,
        "source": {
            "platform": route["source"]["platform"],
            "installation_id": route["source"]["installation_id"],
            "profile_sha256": route["source"]["profile_sha256"],
            "versions": route["source"]["versions"],
        },
        "target": {
            "platform": route["target"]["platform"],
            "installation_id": route["target"]["installation_id"],
            "profile_sha256": route["target"]["profile_sha256"],
            "versions": route["target"]["versions"],
        },
        "method": route["method"],
        "api_compatibility": api,
        "native_e3_qualified": native.get("native_qualified") is True,
        "receiving_e4_accepted": native.get("operationally_accepted") is True,
        "status": "eligible" if not unique else "held",
        "holds": unique,
        "expires_at": expires_at,
        "evaluated_at": now,
        "workload_admission_authorized": False,
        "native_write_authorized": False,
    }
    result["readiness_sha256"] = digest(result)
    return result


def resolve_workload(
    route: dict[str, Any], reconciliation: dict[str, Any],
    collection_coverages: list[dict[str, Any]] | None, now: int,
    collection_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Upgrade an E3/E4 route preview to the effect-facing workload contract.

    Inventory must independently provide full per-field coverage across source,
    target and owner attributes. Missing records hold every effect.
    """
    holds = list(route["holds"])
    if (reconciliation.get("status") != "matched"
            or reconciliation.get("holds") != []
            or reconciliation.get("native_write_authorized") is not False
            or reconciliation.get("reconciliation_sha256") != digest({
                k: v for k, v in reconciliation.items()
                if k != "reconciliation_sha256"
            })
            or type(reconciliation.get("expires_at")) is not int
            or reconciliation["expires_at"] <= now):
        holds.append("catalogue_native_workload_reconciliation_required")
    # A matched parent cannot override held children, regardless of recomputed digests.
    workloads = reconciliation.get("workloads")
    if not eligible_field_dispositions(workloads):
        holds.append("catalogue_native_nested_workload_reconciliation_required")
    # A coverage summary cannot define its own required attribute universe.
    # Deployment release custody independently pins the full manifest and
    # exact platform/scope IDs; any unbound release is held.
    manifest_valid = (
        isinstance(collection_manifest, dict)
        and collection_manifest.get("release_sha256") == route.get("release_sha256")
        and isinstance(collection_manifest.get("manifest_sha256"), str)
        and len(collection_manifest["manifest_sha256"]) == 64
        and isinstance(collection_manifest.get("platforms"), dict)
    )
    if not manifest_valid:
        holds.append("collection_manifest_release_binding_required")
    expected_scopes = {"source", "target", "owner"}
    if (not isinstance(collection_coverages, list)
            or len(collection_coverages) != 3
            or {c.get("scope") for c in collection_coverages
                if isinstance(c, dict)} != expected_scopes):
        holds.append("migration_field_collection_evidence_required")
    else:
        for entry in collection_coverages:
            if (
                entry.get("status") != "complete"
                or entry.get("holds") != []
                or not isinstance(entry.get("attributes"), list)
                or not entry["attributes"]
                or len({a.get("attribute_id") for a in entry["attributes"]
                        if isinstance(a, dict)}) != len(entry["attributes"])
                or any(not isinstance(a, dict)
                       or a.get("status") not in {"observed", "not_applicable"}
                       for a in entry["attributes"])
                or entry.get("native_write_authorized") is not False
                or entry.get("independent_e3_e4_qualification") is not False
                or type(entry.get("expires_at")) is not int
                or entry["expires_at"] <= now
                or type(entry.get("evaluated_at")) is not int
                or not 0 <= now - entry["evaluated_at"] <= 5
                or entry.get("coverage_sha256") != digest({
                    k: v for k, v in entry.items() if k != "coverage_sha256"
                })
            ):
                holds.append("migration_field_collection_stale_or_incomplete")
            if manifest_valid:
                side = entry.get("scope")
                platform = route["target"]["platform"] if side == "target" else route["source"]["platform"]
                declared = collection_manifest["platforms"].get(platform, {})
                expected = declared.get(side) if isinstance(declared, dict) else None
                seen = {a.get("attribute_id") for a in entry.get("attributes", [])
                        if isinstance(a, dict)}
                if (not isinstance(expected, list) or not expected
                        or len(expected) != len(set(expected))
                        or set(expected) != seen
                        or entry.get("manifest_sha256") != collection_manifest["manifest_sha256"]):
                    holds.append("migration_collection_manifest_attributes_changed")
            side = entry.get("scope")
            expected_side = "target" if side == "target" else "source"
            if (entry.get("platform") != route[expected_side]["platform"]
                    or entry.get("installation_id")
                    != route[expected_side]["installation_id"]):
                holds.append("migration_field_collection_installation_changed")
    upgraded = {
        **{k: v for k, v in route.items() if k != "readiness_sha256"},
        "schema_version": 2,
        "kind": "migration_workload_readiness",
        "workload_reconciliation": reconciliation,
        "collection_coverages": collection_coverages or [],
        "status": "eligible" if not holds else "held",
        "holds": sorted(set(holds)),
        "native_write_authorized": False,
        "workload_admission_authorized": False,
    }
    nested_expiry = reconciliation.get("expires_at")
    coverage_expiries = [
        entry["expires_at"] for entry in collection_coverages or []
        if isinstance(entry, dict) and type(entry.get("expires_at")) is int
    ]
    upgraded["expires_at"] = min(
        [route["expires_at"],
         nested_expiry if type(nested_expiry) is int else route["expires_at"]]
        + coverage_expiries
    )
    upgraded["readiness_sha256"] = digest(upgraded)
    return upgraded
