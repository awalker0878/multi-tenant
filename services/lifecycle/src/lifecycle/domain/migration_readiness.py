"""Verify Planning's current, bounded migration-readiness contract at admission.

This is a consumer-side verification of an authenticated Planning owner read,
not a second capability resolver and not an execution grant. Lifecycle retains
independent Inventory, Governance and custody rechecks at every effect.
"""

import json
from functools import lru_cache
from importlib.resources import files
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from lifecycle.domain.admission import digest
from lifecycle.domain.capability_definitions import METHOD_ALIASES
from lifecycle.domain.execution import Rejected


REQUIRED = {
    "schema_version", "kind", "scope", "route_sha256", "tranche_sha256",
    "release_sha256", "source", "target", "method", "api_compatibility",
    "native_e3_qualified", "receiving_e4_accepted", "status", "holds",
    "expires_at", "evaluated_at", "workload_admission_authorized",
    "native_write_authorized", "readiness_sha256",
    "workload_reconciliation", "collection_coverages",
}


@lru_cache(maxsize=1)
def _readiness_validator() -> Draft202012Validator:
    schema = json.loads(
        files("lifecycle.infrastructure.contracts")
        .joinpath("migration-readiness-v2.1.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def verify(value: Any, content: dict[str, Any], tenant: str, now: int) -> None:
    if not isinstance(value, dict) or set(value) != REQUIRED:
        raise Rejected("migration_readiness_missing", 423)
    if not _readiness_validator().is_valid(value):
        raise Rejected("migration_readiness_contract_invalid", 423)
    actual = {k: v for k, v in value.items() if k != "readiness_sha256"}
    if value.get("readiness_sha256") != digest(actual):
        raise Rejected("migration_readiness_integrity_changed", 423)
    scope = content["scope"]
    expected = {
        "tenant_id": tenant,
        "application_id": scope["resource_id"],
        "environment_id": scope["environment"],
        "site_id": scope["site_id"],
    }
    campaign = content.get("migration_campaign", {})
    native = content.get("native_migration", {}).get("migration", {})
    route = campaign.get("route_sha256")
    if "outcomes" in native and native["outcomes"].get("route_sha256") != route:
        raise Rejected("migration_readiness_route_changed", 423)
    api = value.get("api_compatibility")
    if not isinstance(api, dict):
        raise Rejected("migration_readiness_api_held", 423)
    if (
        value["schema_version"] != 2
        or value["kind"] != "migration_workload_readiness"
        or value["scope"] != expected
        or value["route_sha256"] != route
        or value["method"] != METHOD_ALIASES.get(native.get("method"))
        or value["native_e3_qualified"] is not True
        or value["receiving_e4_accepted"] is not True
        or value["status"] != "eligible"
        or value["holds"] != []
        or value["workload_admission_authorized"] is not False
        or value["native_write_authorized"] is not False
        or type(value["evaluated_at"]) is not int
        or not 0 <= now - value["evaluated_at"] <= 5
        or type(value["expires_at"]) is not int
        or value["expires_at"] <= now
        or api.get("operationally_eligible") is not True
    ):
        raise Rejected("migration_readiness_not_current", 423)
    for side in ("source", "target"):
        if (
            not isinstance(value[side], dict)
            or value[side].get("profile_sha256") != native[side]["profile_sha256"]
            or not isinstance(value[side].get("installation_id"), str)
            or not value[side]["installation_id"]
            or not isinstance(value[side].get("versions"), dict)
        ):
            raise Rejected("migration_readiness_installation_changed", 423)
    if value["source"]["installation_id"] == value["target"]["installation_id"]:
        raise Rejected("migration_readiness_installation_changed", 423)
    cases = api.get("cases")
    if not isinstance(cases, list) or not cases or any(
        not isinstance(case, dict)
        or (case.get("status") != "eligible" and case.get("omission_accepted") is not True)
        for case in cases
    ):
        raise Rejected("migration_readiness_api_held", 423)


    # Route eligibility cannot substitute for the one-to-one, full-application
    # workload reconciliation or all independently scoped collection fields.
    reconciliation = value["workload_reconciliation"]
    if (not isinstance(reconciliation, dict)
            or reconciliation.get("status") != "matched"
            or reconciliation.get("holds") != []
            or reconciliation.get("native_write_authorized") is not False
            or reconciliation.get("source_profile_sha256")
                != native["source"]["profile_sha256"]
            or reconciliation.get("native_review_sha256")
                != native.get("review", {}).get("digest")
            or type(reconciliation.get("expires_at")) is not int
            or reconciliation["expires_at"] <= now
            or reconciliation.get("reconciliation_sha256") != digest({
                k: v for k, v in reconciliation.items()
                if k != "reconciliation_sha256"
            })):
        raise Rejected("migration_workload_reconciliation_not_current", 423)
    workloads = reconciliation.get("workloads")
    if (not isinstance(workloads, list) or not workloads
            or any(not isinstance(row, dict) or row.get("status") != "matched"
                   or row.get("holds") != [] for row in workloads)):
        raise Rejected("migration_nested_workload_reconciliation_held", 423)
    coverage = value["collection_coverages"]
    if (not isinstance(coverage, list) or len(coverage) != 3
            or {c.get("scope") for c in coverage if isinstance(c, dict)}
                != {"source", "target", "owner"}):
        raise Rejected("migration_collection_coverage_required", 423)
    for item in coverage:
        if (
            item.get("status") != "complete"
            or item.get("holds") != []
            or not isinstance(item.get("attributes"), list)
            or not item["attributes"]
            or len({a.get("attribute_id") for a in item["attributes"]
                    if isinstance(a, dict)}) != len(item["attributes"])
            or any(not isinstance(a, dict)
                   or a.get("status") not in {"observed", "not_applicable"}
                   for a in item["attributes"])
            or type(item.get("expires_at")) is not int
            or item["expires_at"] <= now
            or item["expires_at"] < value["expires_at"]
            or item.get("native_write_authorized") is not False
            or item.get("independent_e3_e4_qualification") is not False
            or type(item.get("evaluated_at")) is not int
            or not 0 <= now - item["evaluated_at"] <= 5
            or item.get("coverage_sha256") != digest({
                k: v for k, v in item.items() if k != "coverage_sha256"
            })
        ):
            raise Rejected("migration_collection_coverage_not_current", 423)
        side = item["scope"]
        expected_side = "target" if side == "target" else "source"
        if (
            item.get("platform") != value[expected_side]["platform"]
            or item.get("installation_id") != value[expected_side]["installation_id"]
            or item.get("installed_tuple_sha256")
                != native[expected_side].get("tuple_sha256")
        ):
            raise Rejected("migration_collection_identity_changed", 423)
        if side in {"source", "owner"} and (
            item.get("generation_id")
            != reconciliation.get("source_generation_id")
        ):
            raise Rejected("migration_collection_generation_changed", 423)
