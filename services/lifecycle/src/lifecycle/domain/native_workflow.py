"""Exact native journey contracts. Native observations never follow from a process exit."""

import re
from typing import Any

from lifecycle.domain.admission import digest
from lifecycle.domain.execution import Rejected, identity

PROVISION = ("reserve", "provision", "configure_guest", "enroll_services", "activate")
RETIRE = ("retire", "release")
SERVICES = ("ipam", "dns", "identity", "time", "trust", "logging", "monitoring", "backup")
BEFORE = {
    "reserve": ("commissioning",),
    "provision": ("allocations_confirmed",),
    "configure_guest": ("infrastructure_quarantined",),
    "enroll_services": ("guest_hardened",),
    "activate": (
        "infrastructure_quarantined",
        "guest_hardened",
        *SERVICES,
        "backup_restore",
        "application_health",
        "data_integrity",
        "policy_paths",
    ),
    "retire": (
        "retention_authorized",
        "retained_data_readable",
        "retained_keys_readable",
        "owned_inventory",
        "traffic_quarantined",
    ),
    "release": ("owned_objects_absent", "retained_data_readable", "retained_keys_readable"),
}
AFTER = {
    "reserve": ("allocations_confirmed",),
    "provision": ("infrastructure_quarantined",),
    "configure_guest": ("guest_hardened",),
    "enroll_services": SERVICES + ("backup_restore",),
    "activate": ("application_health", "data_integrity", "policy_paths", "traffic_active"),
    "retire": ("owned_objects_absent", "retained_data_readable", "retained_keys_readable"),
    "release": ("allocations_released", "retained_data_readable", "retained_keys_readable"),
}

# Advancing after readback also requires independently observed provider drain.
AFTER = {stage: cases + ("provider_requests_quiescent",) for stage, cases in AFTER.items()}


def exact(value: Any, fields: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise Rejected("invalid_native_contract", 422)
    return value


def checksum(value: Any) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[a-f0-9]{64}", value) is None:
        raise Rejected("invalid_native_digest", 422)
    return value


def integer(value: Any, minimum: int = 0) -> int:
    if type(value) is not int or not minimum <= value < 2**63:
        raise Rejected("invalid_native_integer", 422)
    return value


def validate_plan(plan: dict[str, Any], now: int) -> None:
    migration = plan.get("purpose") == "migrate"
    exact(
        plan,
        {
            "schema_version",
            "scope",
            "plan_id",
            "plan_revision",
            "plan_digest",
            "approval_id",
            "actor_id",
            "requester_id",
            "approver_id",
            "executor_id",
            "campaign_id",
            "epoch",
            "configuration",
            "tuple_digest",
            "source_revision",
            "purpose",
            "source_job_id",
            "ownership_digest",
            "custody_id",
            "custody_generation",
            "operation_plan_sha256",
            "expires_at",
            "intents",
            "policy_cases",
        }
        | ({"migration"} if migration else set()),
    )
    if type(plan["schema_version"]) is not int or plan["schema_version"] != (2 if migration else 1):
        raise Rejected("invalid_native_version", 422)
    scope = exact(
        plan["scope"],
        {
            "tenant_id",
            "site_id",
            "environment",
            "resource_id",
            "project_id",
        },
    )
    for key, value in scope.items():
        if key == "project_id" and isinstance(value, str):
            if re.fullmatch(r"[a-f0-9]{32}", value):
                continue
            if re.fullmatch(r"datacenter-[1-9][0-9]{0,18}", value):
                if (
                    migration
                    and plan["migration"].get("outcomes", {}).get("target_platform") == "vmware"
                ):
                    continue
                raise Rejected("invalid_native_destination_scope", 422)
        identity(value)
    for key in (
        "plan_id",
        "approval_id",
        "actor_id",
        "requester_id",
        "approver_id",
        "executor_id",
        "campaign_id",
        "epoch",
        "custody_id",
    ):
        identity(plan[key])
    if plan["approver_id"] in {plan["actor_id"], plan["requester_id"]}:
        raise Rejected("independent_native_approval_required", 403)
    for key in ("plan_digest", "operation_plan_sha256", "tuple_digest"):
        checksum(plan[key])
    config = exact(plan["configuration"], {"revision", "digest"})
    integer(config["revision"], 1)
    checksum(config["digest"])
    integer(plan["plan_revision"], 1)
    integer(plan["custody_generation"])
    if integer(plan["expires_at"], 1) <= now:
        raise Rejected("native_plan_expired", 423)
    if not isinstance(plan["source_revision"], str) or not re.fullmatch(
        r"[a-f0-9]{40}", plan["source_revision"]
    ):
        raise Rejected("invalid_native_source", 422)
    checksum(plan["ownership_digest"])
    if plan["purpose"] not in {"provision", "retire", "migrate"}:
        raise Rejected("unsupported_native_purpose", 422)
    if migration:
        from lifecycle.domain.migration import RECOVERY, validate

        validate(plan["migration"], now)
        if plan["migration"]["mode"] in RECOVERY:
            identity(plan["source_job_id"])
        elif plan["source_job_id"] is not None:
            raise Rejected("invalid_migration_source_job", 422)
    elif plan["purpose"] == "retire":
        identity(plan["source_job_id"])
    elif plan["source_job_id"] is not None:
        raise Rejected("invalid_native_source_job", 422)
    stages = stages_for(plan)
    if not isinstance(plan["intents"], dict) or set(plan["intents"]) != set(stages):
        raise Rejected("native_stage_contracts_required", 422)
    # Only immutable, separately resolved intent hashes enter the durable control journal.
    for value in plan["intents"].values():
        checksum(value)
    cases = plan["policy_cases"]
    if not isinstance(cases, list) or not 6 <= len(cases) <= 256:
        raise Rejected("native_policy_matrix_required", 422)
    names: set[str] = set()
    covered: set[tuple[str, str]] = set()
    for case in cases:
        exact(case, {"id", "boundary", "expectation", "family", "direction"})
        if (
            not isinstance(case["id"], str)
            or not re.fullmatch(r"[a-z0-9_-]{1,80}", case["id"])
            or case["id"] in names
        ):
            raise Rejected("invalid_native_policy_case", 422)
        names.add(case["id"])
        if case["boundary"] not in {"same_host_subnet", "inter_host", "edge"} or case[
            "expectation"
        ] not in {"allow", "deny"}:
            raise Rejected("invalid_native_policy_case", 422)
        if case["family"] not in {"ipv4", "ipv6"} or case["direction"] not in {"forward", "return"}:
            raise Rejected("invalid_native_policy_case", 422)
        covered.add((case["boundary"], case["expectation"]))
    if covered != {
        (b, e) for b in ("same_host_subnet", "inter_host", "edge") for e in ("allow", "deny")
    }:
        raise Rejected("native_policy_coverage_incomplete", 422)


def current_authority(
    plan: dict[str, Any], binding: dict[str, Any], receipt: dict[str, Any], now: int
) -> None:
    """The caller obtains this receipt from authenticated owners, never from an API body."""
    expected = {
        "binding_sha256": digest(binding),
        "plan_digest": plan["plan_digest"],
        "configuration": plan["configuration"],
        "tuple_digest": plan["tuple_digest"],
        "epoch": plan["epoch"],
        "executor_id": plan["executor_id"],
        "authority_use": "native_boundary",
        "allowed": True,
        "native_write_authorized": True,
        "stop_clear": True,
        "configuration_current": True,
        "approval_current": True,
        "ownership_current": True,
        "provider_fence_current": True,
        "plan_current": True,
        "state_current": True,
        "artifacts_current": True,
        "entitlement_current": True,
        "campaign_current": True,
    }
    if plan["purpose"] == "migrate":
        from lifecycle.domain.migration import current_profiles

        current_profiles(plan, receipt.get("migration_input"), now)
        expected.update(
            {
                "migration_sha256": digest(plan["migration"]),
                "source_profile_current": True,
                "target_profile_current": True,
                "migration_method_qualified": True,
                "all_datasets_accounted": True,
            }
        )
    if any(digest(receipt.get(k)) != digest(v) for k, v in expected.items()):
        raise Rejected("native_authority_not_current", 423)
    evaluated = integer(receipt.get("evaluated_at"))
    expires = integer(receipt.get("expires_at"), 1)
    if not 0 <= now - evaluated <= 5 or not now < expires <= plan["expires_at"]:
        raise Rejected("native_authority_expired", 423)
    if plan["expires_at"] <= now:
        raise Rejected("native_plan_expired", 423)


def observations(
    plan: dict[str, Any],
    binding: dict[str, Any],
    phase: str,
    records: list[dict[str, Any]],
    now: int,
) -> str:
    """Exact complete independent evidence; no 'not applicable' exemption for mandatory services."""
    stage = binding["stage"]
    required = required_observations(plan, stage, phase)
    if not isinstance(records, list) or len(records) != len(required):
        raise Rejected("native_observations_incomplete", 423)
    outcome_requirements = {}
    if plan.get("migration", {}).get("schema_version") == 4:
        from lifecycle.domain.migration_outcomes import requirements

        outcome_requirements = requirements(plan["migration"]["outcomes"])
    seen = set()
    for record in records:
        exact(
            record,
            {
                "case",
                "phase",
                "binding_sha256",
                "intent_digest",
                "observer_id",
                "observed_at",
                "expires_at",
                "outcome",
                "evidence_sha256",
                "policy_results",
            }
            | ({"requirement_sha256"} if record.get("case") in outcome_requirements else set()),
        )
        name = record["case"]
        if not isinstance(name, str) or name not in required or name in seen:
            raise Rejected("native_observations_incomplete", 423)
        seen.add(name)
        if (
            record["phase"] != phase
            or record["binding_sha256"] != digest(binding)
            or record["intent_digest"] != plan["intents"][stage]
            or record["outcome"] != "passed"
            or identity(record["observer_id"])
            in {
                plan["actor_id"],
                plan["requester_id"],
                plan["executor_id"],
            }
        ):
            raise Rejected("native_observation_not_independent_and_bound", 423)
        if (
            name in outcome_requirements
            and record["requirement_sha256"] != outcome_requirements[name]
        ):
            raise Rejected("native_outcome_requirement_changed", 423)
        checksum(record["evidence_sha256"])
        if (
            not 0 <= now - integer(record["observed_at"]) <= 60
            or integer(record["expires_at"], 1) <= now
        ):
            raise Rejected("native_observation_expired", 423)
        if name == "policy_paths":
            expected = {c["id"]: c["expectation"] for c in plan["policy_cases"]}
            if digest(record["policy_results"]) != digest(expected):
                raise Rejected("native_policy_not_observed", 423)
        elif record["policy_results"] != {}:
            raise Rejected("unexpected_native_policy_results", 422)
    return digest(records)


def stages_for(plan: dict[str, Any]) -> tuple[str, ...]:
    if plan["purpose"] == "migrate":
        from lifecycle.domain.migration import stages

        return stages(plan["migration"])
    return PROVISION if plan["purpose"] == "provision" else RETIRE


def terminal_for(plan: dict[str, Any]) -> str:
    if plan["purpose"] == "migrate":
        from lifecycle.domain.migration import TERMINALS

        return TERMINALS[plan["migration"]["mode"]]
    return "active" if plan["purpose"] == "provision" else "retired"


def required_observations(plan: dict[str, Any], stage: str, phase: str) -> tuple[str, ...]:
    if phase not in {"before", "after"}:
        raise Rejected("invalid_native_observation_phase", 422)
    if plan["purpose"] == "migrate":
        from lifecycle.domain.migration import cases

        return cases(plan, stage, phase)
    return BEFORE[stage] if phase == "before" else AFTER[stage]


def api_stage(plan: dict[str, Any], stage: str) -> bool:
    return stage == "provision" or plan["purpose"] == "migrate"
