"""Exact P09 tranche and directed-route contracts; declarations never grant support."""

from itertools import product
from typing import Any

from planning.domain.model import (
    DIMENSIONS,
    PLATFORMS,
    Rejected,
    digest,
    identifier,
    integer,
    sha,
    shape,
)

METHODS = ("cold_export", "rebuild_restore", "application_delta", "file_delta", "block_replication")
GUESTS = ("linux", "windows", "appliance")
OPERATIONS = (
    "power_on",
    "shutdown",
    "power_off",
    "resize_cpu",
    "resize_memory",
    "policy_change",
    "patch",
    "credential_rotation",
    "scale_out",
    "scale_in",
    "ha_failover",
    "relocate",
    "adopt",
)
RETEST = (
    "artifact",
    "platform",
    "api",
    "backend",
    "guest",
    "method",
    "policy",
    "service",
    "topology",
    "recovery",
    "ownership",
    "expiry",
    "revocation",
)


def text(value: Any) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= 160 or any(ord(c) < 32 for c in value):
        raise Rejected("invalid_expansion_label")
    return value


def distinct(value: Any, allowed: set[str], minimum: int = 1) -> list[str]:
    if (
        not isinstance(value, list)
        or not minimum <= len(value) <= len(allowed)
        or any(not isinstance(v, str) or v not in allowed for v in value)
        or len(set(value)) != len(value)
    ):
        raise Rejected("invalid_expansion_choices")
    return list(value)


def platform_tuple(value: Any) -> dict[str, Any]:
    row = shape(value, {"platform", "installation_id", "profile_sha256", "versions", "dimensions"})
    if row["platform"] not in PLATFORMS:
        raise Rejected("unsupported_expansion_platform")
    identifier(row["installation_id"])
    sha(row["profile_sha256"])
    shape(row["versions"], {"platform", "api", "network", "storage"})
    for version in row["versions"].values():
        text(version)
    shape(row["dimensions"], set(DIMENSIONS))
    for dimension in row["dimensions"].values():
        sha(dimension)
    return row


def route(value: Any) -> dict[str, Any]:
    row = shape(
        value,
        {
            "id",
            "source",
            "target",
            "guest",
            "guest_profile_sha256",
            "method",
            "topology_sha256",
            "data_sha256",
            "policy_sha256",
            "services_sha256",
            "recovery_sha256",
            "artifacts_sha256",
            "constraints",
            "requirement_ids",
            "exclusions",
        },
    )
    identifier(row["id"])
    platform_tuple(row["source"])
    platform_tuple(row["target"])
    if row["guest"] not in GUESTS or row["method"] not in METHODS:
        raise Rejected("unsupported_expansion_guest_or_method")
    for key in row:
        if key.endswith("_sha256"):
            sha(row[key])
    constraints = shape(
        row["constraints"],
        {
            "boot",
            "disk_format",
            "driver_profile",
            "encryption",
            "guest_mutation",
            "data_consistency",
            "writer_fencing",
            "target_write_recovery",
            "maximum_outage_seconds",
            "maximum_data_loss_seconds",
        },
    )
    for key in ("boot", "disk_format", "driver_profile", "encryption", "data_consistency"):
        text(constraints[key])
    if constraints["guest_mutation"] not in {"copy_only", "prohibited"}:
        raise Rejected("source_guest_mutation_prohibited")
    if row["guest"] == "appliance" and constraints["guest_mutation"] != "prohibited":
        raise Rejected("appliance_guest_mutation_prohibited")
    for key in ("writer_fencing", "target_write_recovery"):
        sha(constraints[key])
    for key in ("maximum_outage_seconds", "maximum_data_loss_seconds"):
        integer(constraints[key])
    distinct(row["requirement_ids"], {f"R{i:02}" for i in range(1, 36)})
    exclusions = row["exclusions"]
    if not isinstance(exclusions, list) or len(exclusions) > 64:
        raise Rejected("invalid_expansion_exclusions")
    for exclusion in exclusions:
        text(exclusion)
    if len(set(exclusions)) != len(exclusions):
        raise Rejected("duplicate_expansion_exclusion")
    return row


def tranche(value: Any) -> dict[str, Any]:
    row = shape(
        value,
        {
            "schema_version",
            "id",
            "revision",
            "release_sha256",
            "owner_role",
            "expires_at",
            "routes",
            "operations",
            "deferred_directions",
            "retest_triggers",
        },
    )
    if type(row["schema_version"]) is not int or row["schema_version"] != 1:
        raise Rejected("unsupported_expansion_contract")
    identifier(row["id"])
    integer(row["revision"], 1)
    integer(row["expires_at"], 1)
    sha(row["release_sha256"])
    text(row["owner_role"])
    routes = row["routes"]
    if not isinstance(routes, list) or not 1 <= len(routes) <= 512:
        raise Rejected("expansion_route_bound")
    seen: set[str] = set()
    selected: set[str] = set()
    tuples: set[str] = set()
    for item in routes:
        route(item)
        fingerprint = digest({k: v for k, v in item.items() if k != "id"})
        if item["id"] in seen or fingerprint in tuples:
            raise Rejected("duplicate_expansion_route")
        seen.add(item["id"])
        tuples.add(fingerprint)
        selected.add(item["source"]["platform"] + "->" + item["target"]["platform"])
    directions = {a + "->" + b for a, b in product(PLATFORMS, repeat=2)}
    deferred = distinct(row["deferred_directions"], directions, 0)
    if selected & set(deferred) or selected | set(deferred) != directions:
        raise Rejected("expansion_direction_coverage_required")
    distinct(row["operations"], set(OPERATIONS), 0)
    if set(distinct(row["retest_triggers"], set(RETEST))) != set(RETEST):
        raise Rejected("expansion_retest_triggers_required")
    return row


def qualification_plan(row: dict[str, Any]) -> dict[str, Any]:
    route(row)
    cases = ["Q08.01", "Q08.02", "Q08.03", "Q08.04", "Q04", "Q06", "Q07"]
    if row["source"]["platform"] == row["target"]["platform"]:
        cases.append("Q08.05")
    checks = [
        "boot_and_drivers",
        "all_disks_and_nics",
        "policy_denials",
        "shared_services",
        "source_writer_fence",
        "pre_target_write_recovery",
        "post_target_write_recovery",
        "measured_outage_and_data_loss",
        "owned_cleanup",
    ]
    if row["guest"] == "windows":
        checks += ["windows_license", "identity_and_sysprep", "encryption_key_recovery"]
    if row["guest"] == "appliance":
        checks += ["vendor_export_import_contract", "no_guest_mutation", "external_readiness"]
    if row["method"] != "cold_export":
        checks += ["dataset_inventory", "consistency_boundary", "lag_and_final_sync"]
    if row["method"] == "block_replication":
        checks.append("replication_entitlement_and_native_fencing")
    return {
        "route_id": row["id"],
        "route_sha256": digest(row),
        "cases": cases,
        "checks": checks,
        "native_write_authorized": False,
    }


def matrix(value: dict[str, Any], records: list[dict[str, Any]], now: int) -> list[dict[str, Any]]:
    """Records come from Assurance's authenticated owner port, never a Console request."""
    baseline = tranche(value)
    result: list[dict[str, Any]] = []
    for source, target in product(PLATFORMS, repeat=2):
        selected = [
            r
            for r in baseline["routes"]
            if r["source"]["platform"] == source and r["target"]["platform"] == target
        ]
        if not selected:
            result.append({"direction": source + "->" + target, "state": "deferred", "routes": []})
            continue
        rows = []
        for r in selected:
            matches = [
                q
                for q in records
                if q.get("route_sha256") == digest(r)
                and q.get("tranche_sha256") == digest(baseline)
                and q.get("release_sha256") == baseline["release_sha256"]
            ]
            native = [q for q in matches if q.get("level") == "E3"]
            operating = [q for q in matches if q.get("level") == "E4"]
            blockers = []
            q = native[0] if len(native) == 1 else {}
            if len(native) != 1:
                blockers.append("missing_or_ambiguous_exact_qualification")
            if baseline["expires_at"] <= now:
                blockers.append("tranche_expired")
            if (
                q.get("level") != "E3"
                or q.get("decision") != "accepted"
                or q.get("revoked") is not False
            ):
                blockers.append("native_qualification_unaccepted")
            if type(q.get("expires_at")) is not int or q.get("expires_at", 0) <= now:
                blockers.append("qualification_expired_or_missing")
            if not isinstance(q.get("evidence_sha256"), str):
                blockers.append("qualification_evidence_missing")
            else:
                sha(q["evidence_sha256"])
            rows.append(
                qualification_plan(r)
                | {
                    "guest": r["guest"],
                    "method": r["method"],
                    "source": r["source"],
                    "target": r["target"],
                    "guest_profile_sha256": r["guest_profile_sha256"],
                    "constraints": r["constraints"],
                    "requirement_ids": r["requirement_ids"],
                    "exclusions": r["exclusions"],
                    "blockers": blockers,
                    "native_qualified": not blockers,
                    "operationally_accepted": not blockers
                    and len(operating) == 1
                    and operating[0].get("decision") == "accepted"
                    and operating[0].get("revoked") is False
                    and type(operating[0].get("expires_at")) is int
                    and operating[0]["expires_at"] > now
                    and isinstance(operating[0].get("evidence_sha256"), str)
                    and sha(operating[0]["evidence_sha256"]) is not None,
                }
            )
        result.append({"direction": source + "->" + target, "state": "selected", "routes": rows})
    return result
