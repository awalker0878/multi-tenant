"""One fail-closed migration route-readiness projection shared with native admission.

Planning composes this projection; it never signs native observations or acts
as a substitute for Catalogue, Inventory or Assurance custody. A route record
is NOT a VM-level admission receipt. A specific workload must also pass the
separately owned confirmed-review, source-intent and native-effect gates.
"""

from typing import Any

from planning.domain.model import digest


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
