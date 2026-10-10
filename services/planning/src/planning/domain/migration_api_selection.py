"""Immutable migration API execution selection from current owner qualification.

Only the exact installed, entitled, independently qualified and executor-
supported operation/version pair may be bound into an effect plan. A request
for a different release is not a compatible substitution.
"""
from typing import Any

from planning.domain.model import Rejected, digest


def pin(readiness: dict[str, Any], now: int) -> dict[str, Any]:
    if (not isinstance(readiness, dict)
            or readiness.get("status") != "eligible"
            or readiness.get("holds") != []
            or readiness.get("native_write_authorized") is not False
            or readiness.get("expires_at", 0) <= now):
        raise Rejected("migration_api_selection_readiness_required", 423)
    api = readiness.get("api_compatibility")
    if not isinstance(api, dict) or api.get("operationally_eligible") is not True:
        raise Rejected("migration_api_selection_qualification_required", 423)
    cases = api.get("cases")
    if not isinstance(cases, list) or not 1 <= len(cases) <= 256:
        raise Rejected("migration_api_selection_cases_required", 423)
    result = []
    identities: set[tuple[str, str]] = set()
    for case in cases:
        if not isinstance(case, dict):
            raise Rejected("migration_api_selection_case_invalid", 423)
        if case.get("omission_accepted") is True:
            # Omitted features cannot be invoked by native workers.
            if case.get("criticality") != "optional":
                raise Rejected("migration_api_selection_critical_omitted", 423)
            continue
        if case.get("status") != "eligible":
            raise Rejected("migration_api_selection_qualification_required", 423)
        key = (case.get("capability_id"), case.get("side"))
        if key in identities or not all(isinstance(x, str) and x for x in key):
            raise Rejected("migration_api_selection_duplicate", 423)
        identities.add(key)
        if (case.get("side") not in {"source", "target"}
                or not all(isinstance(case.get(k), str)
                           and case[k] for k in ("selected_api_family",
                                                "selected_api_version"))
                or not isinstance(case.get("evidence_sha256"), str)
                or len(case["evidence_sha256"]) != 64
                or type(case.get("expires_at")) is not int
                or case["expires_at"] <= now):
            raise Rejected("migration_api_selection_evidence_unbound", 423)
        if (readiness.get(case["side"], {}).get("platform") == "ahv"
                and case["selected_api_version"] != "v4.3"):
            raise Rejected("migration_api_selection_unimplemented", 423)
        result.append({
            "capability_id": case["capability_id"],
            "side": case["side"],
            "api_family": case["selected_api_family"],
            "api_version": case["selected_api_version"],
            "evidence_sha256": case["evidence_sha256"],
            "expires_at": case["expires_at"],
        })
    if not result:
        raise Rejected("migration_api_selection_no_native_operations", 423)
    selected = {
        "schema_version": 1,
        "route_sha256": readiness["route_sha256"],
        "release_sha256": readiness["release_sha256"],
        "source_profile_sha256": readiness["source"]["profile_sha256"],
        "target_profile_sha256": readiness["target"]["profile_sha256"],
        "operations": sorted(result, key=lambda r: (r["side"], r["capability_id"])),
    }
    selected["selection_sha256"] = digest(selected)
    return selected
