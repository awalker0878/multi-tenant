"""Version-tolerant API capability admission with explicit omission warnings.

All inputs are owner-provided immutable projections. Documentation, a version
string, a probe and a native Assurance decision are separate forms of evidence.
This module never grants an effect or upgrades an E2 result to E3/E4.
"""

import re
from typing import Any

from planning.domain.model import Rejected, digest, identifier, integer, sha, shape

CAPABILITY = re.compile(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*){1,7}\Z")
API_FAMILY = re.compile(r"[a-z][a-z0-9_.-]{0,63}\Z")
API_VERSION = re.compile(r"v?[0-9]+(?:\.[0-9]+){0,3}\Z")

# These are safety invariants, not a vendor feature catalogue. An owner cannot
# relabel any of them 'optional' to suppress admission failure.
CRITICAL_PREFIXES = (
    "vm.disk.", "vm.boot.", "vm.power.", "storage.data.",
    "data.", "recovery.", "security.isolation.", "security.encryption.",
    "network.required.", "network.isolation.",
)
STATES = {"supported", "unsupported", "degraded", "unknown"}
SOURCES = {"spec_diff", "live_probe", "contract_test", "operator"}


def usage(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list) or not 1 <= len(rows) <= 128:
        raise Rejected("migration_api_usage_required", 422)
    seen: set[tuple[str, str]] = set()
    for row in rows:
        shape(row, {"capability_id", "side", "criticality", "reason"})
        cap = row["capability_id"]
        if not isinstance(cap, str) or not CAPABILITY.fullmatch(cap):
            raise Rejected("migration_api_capability_id_invalid", 422)
        if row["side"] not in {"source", "target", "both"}:
            raise Rejected("migration_api_usage_side_invalid", 422)
        if row["criticality"] not in {"critical", "optional"}:
            raise Rejected("migration_api_criticality_invalid", 422)
        if not isinstance(row["reason"], str) or not 1 <= len(row["reason"]) <= 240:
            raise Rejected("migration_api_usage_reason_missing", 422)
        if row["criticality"] == "optional" and cap.startswith(CRITICAL_PREFIXES):
            raise Rejected("migration_api_safety_cannot_be_optional", 422)
        for side in ("source", "target") if row["side"] == "both" else (row["side"],):
            if (cap, side) in seen:
                raise Rejected("migration_api_usage_duplicate", 422)
            seen.add((cap, side))
    return rows


def version_tuple(value: Any) -> tuple[int, ...]:
    if not isinstance(value, str) or not API_VERSION.fullmatch(value):
        raise Rejected("migration_api_version_invalid", 422)
    return tuple(int(part) for part in value.removeprefix("v").split("."))


def environment(profile: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    shape(
        snapshot,
        {
            "installation_id", "profile_sha256", "apis", "entitlements",
            "observed_at", "expires_at", "source", "evidence_sha256",
        },
    )
    if (
        identifier(snapshot["installation_id"]) != profile["installation_id"]
        or sha(snapshot["profile_sha256"]) != profile["profile_sha256"]
    ):
        raise Rejected("migration_api_environment_scope_changed", 423)
    integer(snapshot["observed_at"])
    integer(snapshot["expires_at"])
    sha(snapshot["evidence_sha256"])
    if snapshot["source"] not in {"live_probe", "operator"}:
        raise Rejected("migration_api_environment_source_invalid", 422)
    if snapshot["expires_at"] <= snapshot["observed_at"]:
        raise Rejected("migration_api_environment_time_invalid", 422)
    apis = snapshot["apis"]
    if not isinstance(apis, dict) or len(apis) > 32:
        raise Rejected("migration_api_version_inventory_invalid", 422)
    for family, versions in apis.items():
        if not isinstance(family, str) or not API_FAMILY.fullmatch(family):
            raise Rejected("migration_api_family_invalid", 422)
        if not isinstance(versions, list) or not 1 <= len(versions) <= 40:
            raise Rejected("migration_api_version_inventory_invalid", 422)
        for v in versions:
            version_tuple(v)
        if len(set(versions)) != len(versions):
            raise Rejected("migration_api_version_inventory_invalid", 422)
    entitlements = snapshot["entitlements"]
    if not isinstance(entitlements, dict) or len(entitlements) > 512:
        raise Rejected("migration_api_entitlements_invalid", 422)
    for cap, state in entitlements.items():
        if not isinstance(cap, str) or not CAPABILITY.fullmatch(cap):
            raise Rejected("migration_api_entitlements_invalid", 422)
        if state not in {"allowed", "denied", "unknown"}:
            raise Rejected("migration_api_entitlements_invalid", 422)
    return snapshot


def record(value: dict[str, Any], now: int) -> None:
    shape(
        value,
        {
            "installation_id", "profile_sha256", "capability_id",
            "api_family", "api_version", "result", "source",
            "observed_at", "expires_at", "evidence_sha256",
            "qualification_level", "qualification_decision",
            "qualification_sha256",
        },
    )
    identifier(value["installation_id"])
    sha(value["profile_sha256"])
    if not isinstance(value["capability_id"], str) or not CAPABILITY.fullmatch(
        value["capability_id"]
    ):
        raise Rejected("migration_api_observation_invalid", 422)
    if not isinstance(value["api_family"], str) or not API_FAMILY.fullmatch(
        value["api_family"]
    ):
        raise Rejected("migration_api_observation_invalid", 422)
    version_tuple(value["api_version"])
    if value["result"] not in STATES or value["source"] not in SOURCES:
        raise Rejected("migration_api_observation_invalid", 422)
    integer(value["observed_at"])
    integer(value["expires_at"])
    sha(value["evidence_sha256"])
    if value["qualification_level"] not in {"none", "E2", "E3", "E4"}:
        raise Rejected("migration_api_observation_invalid", 422)
    if value["qualification_decision"] not in {"not_reviewed", "accepted", "rejected"}:
        raise Rejected("migration_api_observation_invalid", 422)
    if value["qualification_sha256"] is not None:
        sha(value["qualification_sha256"])
    if value["observed_at"] > now or value["expires_at"] <= value["observed_at"]:
        raise Rejected("migration_api_observation_timestamp_invalid", 422)


def evaluate(
    selected: dict[str, Any], evidence: dict[str, Any] | None,
    now: int, *, tenant_id: str | None = None,
    application_id: str | None = None, environment_id: str | None = None,
) -> dict[str, Any]:
    """Evaluate exactly this route's code/owner-defined usage, never user input."""
    declared = usage(selected["api_usage"])
    if evidence is None:
        evidence = {
            "route_sha256": digest(selected),
            "environments": {},
            "observations": [],
            "omissions": [],
        }
    shape(evidence, {"route_sha256", "environments", "observations", "omissions"})
    if sha(evidence["route_sha256"]) != digest(selected):
        raise Rejected("migration_api_evidence_route_changed", 423)
    environments = evidence["environments"]
    if not isinstance(environments, dict) or set(environments) - {"source", "target"}:
        raise Rejected("migration_api_environments_invalid", 422)
    envs = {
        side: environment(selected[side], environments[side])
        for side in ("source", "target") if side in environments
    }
    facts = evidence["observations"]
    if not isinstance(facts, list) or len(facts) > 512:
        raise Rejected("migration_api_observation_bound", 422)
    for fact in facts:
        if not isinstance(fact, dict):
            raise Rejected("migration_api_observation_invalid", 422)
        record(fact, now)
    omissions = evidence["omissions"]
    if not isinstance(omissions, list) or len(omissions) > 64:
        raise Rejected("migration_api_omissions_invalid", 422)
    alerts: list[dict[str, Any]] = []
    cases: list[dict[str, Any]] = []
    blocking = False
    conditional = False
    for required in declared:
        for side in ("source", "target") if required["side"] == "both" else (required["side"],):
            cap = required["capability_id"]
            env = envs.get(side)
            status, reason, ref = "unknown", "api_observation_missing", None
            if env is not None and (
                env["observed_at"] > now or env["expires_at"] <= now
            ):
                env = None
                reason = "api_environment_discovery_stale"
            api_family: str | None = None
            api_version: str | None = None
            evidence_expiry: int | None = None
            if env is not None and env["source"] != "live_probe":
                # Operator/configured version listings are not independent
                # discovery and must never promote a qualified API operation.
                reason = "installed_api_namespace_live_probe_required"
                env = None
            if env is not None:
                entitlement = env["entitlements"].get(cap, "unknown")
                candidates = [
                    f for f in facts
                    if f["installation_id"] == env["installation_id"]
                    and f["profile_sha256"] == env["profile_sha256"]
                    and f["capability_id"] == cap
                    and f["api_version"] in env["apis"].get(f["api_family"], [])
                    and f["expires_at"] > now
                ]
                # Several independently negotiated versions may be installed.
                # A capability is usable if at least one *specific* version
                # is qualified. Conflicting receipts for the same version hold.
                identities = [(f["api_family"], f["api_version"]) for f in candidates]
                if entitlement == "denied":
                    status, reason = "blocked", "api_entitlement_denied"
                elif entitlement != "allowed":
                    reason = "api_entitlement_unconfirmed"
                elif len(identities) != len(set(identities)):
                    reason = "api_observation_ambiguous"
                else:
                    usable = [
                        f for f in candidates
                        if f["result"] == "supported"
                        and f["source"] == "live_probe"
                        and f["qualification_level"] in {"E3", "E4"}
                        and f["qualification_decision"] == "accepted"
                        and f["qualification_sha256"] is not None
                    ]
                    if usable:
                        # Prefer the lowest exact qualified release for this
                        # operation; never assume the newest API is supported.
                        observation = min(
                            usable, key=lambda f: (
                                f["api_family"], version_tuple(f["api_version"])
                            )
                        )
                        status, reason = "eligible", "api_operation_qualified"
                        ref = observation["evidence_sha256"]
                        api_family = observation["api_family"]
                        api_version = observation["api_version"]
                        evidence_expiry = min(env["expires_at"], observation["expires_at"])
                        # Lifecycle's currently commissioned AHV native operation
                        # routes are fixed to v4.3. A qualified v4.2 observation
                        # must never silently run against a v4.3 endpoint. A
                        # version-aware executor manifest is needed to expand.
                        if selected[side]["platform"] == "ahv" and (
                            api_family.rsplit(".", 1)[-1]
                            in {"vmm", "prism", "clustermgmt",
                                "networking", "microseg", "iam"}
                            and api_version != "v4.3"
                        ):
                            status, reason = (
                                "blocked", "selected_api_version_not_executable"
                            )
                            ref, api_family, api_version, evidence_expiry = (
                                None, None, None, None
                            )
                    elif any(f["result"] == "degraded" for f in candidates):
                        status, reason = "conditional", "api_behavior_degraded"
                    elif candidates and all(f["result"] == "unsupported" for f in candidates):
                        status, reason = "blocked", "api_operation_unsupported"
                    elif candidates:
                        reason = "api_declared_but_not_native_qualified"
            warning = None
            omission_accepted = False
            if status != "eligible":
                if required["criticality"] == "critical":
                    blocking = True
                else:
                    for item in omissions:
                        if (
                            tenant_id is not None and application_id is not None
                            and environment_id is not None
                            and item.get("capability_id") == cap
                            and item.get("side") == side
                            and item.get("route_sha256") == digest(selected)
                            and item.get("tenant_id") == tenant_id
                            and item.get("application_id") == application_id
                            and item.get("environment_id") == environment_id
                            and item.get("decision") == "accepted"
                            and item.get("evidence_level") == "E4"
                            and type(item.get("expires_at")) is int
                            and item["expires_at"] > now
                            and isinstance(item.get("approval_sha256"), str)
                            and re.fullmatch(r"[a-f0-9]{64}", item["approval_sha256"])
                            and isinstance(item.get("effect_suppressed_sha256"), str)
                            and re.fullmatch(
                                r"[a-f0-9]{64}", item["effect_suppressed_sha256"]
                            )
                        ):
                            omission_accepted = True
                            deadline = item["expires_at"]
                            evidence_expiry = min(
                                evidence_expiry, deadline
                            ) if evidence_expiry is not None else deadline
                    if not omission_accepted:
                        conditional = True
                warning = {
                    "capability_id": cap, "side": side,
                    "severity": "blocker" if required["criticality"] == "critical" else "warning",
                    "reason": reason,
                    "impact": required["reason"],
                    "action": "resolve_critical_api_requirement"
                    if required["criticality"] == "critical"
                    else "approve_and_omit_nonessential_feature",
                    "omission_accepted": omission_accepted,
                }
                alerts.append(warning)
            cases.append({
                "capability_id": cap,
                "side": side,
                "criticality": required["criticality"],
                "status": status,
                "reason": reason,
                "evidence_sha256": ref,
                "selected_api_family": api_family,
                "selected_api_version": api_version,
                "omission_accepted": omission_accepted,
                # The authority's native/entitlement and approved-omission
                # receipts constrain runtime readiness, never tranche TTL.
                "expires_at": evidence_expiry,
            })
    return {
        "status": "blocked" if blocking else "conditional" if conditional else "eligible",
        "operationally_eligible": not blocking and not conditional,
        "cases": cases,
        "administrator_alerts": alerts,
        "native_write_authorized": False,
    }
