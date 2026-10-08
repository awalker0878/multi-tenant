"""Compose reviewed profiles with a commissioned recipe into immutable operational bytes.

This creates a proposal for independent approval. The recipe is infrastructure-owned,
never a browser payload, and supplies explicit stage artifacts and resource budgets.
"""

from copy import deepcopy
from typing import Any

from planning.domain.model import Rejected, digest, identifier, integer, sha, shape

CAPTURE = (
    "source_prepare",
    "capture",
    "export_copy",
    "convert_copy",
    "import_target",
    "transform_copy",
)
RECOVERY = {
    "rollback": ("fence_target", "verify_no_divergence", "restore_source", "verify_source"),
    "forward_recovery": ("fence_target", "preserve_target", "recover_target", "verify_recovery"),
    "reverse_recovery": (
        "fence_target",
        "preserve_target",
        "reverse_sync",
        "verify_source_data",
        "restore_source",
        "verify_source",
    ),
    "cleanup": (
        "remove_copy",
        "remove_snapshot",
        "verify_consolidation",
        "revoke_migration_access",
    ),
}
DELTA = {
    "VM_SNAPSHOT_BASELINE_APP_DELTA": "application",
    "VM_SNAPSHOT_BASELINE_FILE_DELTA": "file",
    "VM_COLD_EXPORT": "none",
    "APPLICATION_REBUILD_RESTORE": "restore",
    "EXTERNAL_BLOCK_REPLICATION": "block",
}
PHASES = {"capture", "transfer", "conversion", "import", "validation", "cutover"}


def stage_order(mode: str, method: str) -> tuple[str, ...]:
    if method not in DELTA or mode not in {"rehearsal", "cutover", *RECOVERY}:
        raise Rejected("unsupported_migration_recipe", 422)
    if mode in RECOVERY:
        return RECOVERY[mode]
    capture: tuple[str, ...] = CAPTURE
    if DELTA[method] in {"application", "file"}:
        capture = CAPTURE[:2] + ("restart_baseline_source",) + CAPTURE[2:]
    elif method == "APPLICATION_REBUILD_RESTORE":
        capture = ("source_prepare", "export_copy", "import_target", "transform_copy")
    elif method == "EXTERNAL_BLOCK_REPLICATION":
        capture = ("source_prepare", "capture", "import_target", "transform_copy")
    return capture + (
        ("rehearsal_validate", "retain_rehearsal")
        if mode == "rehearsal"
        else (
            "fence_source",
            "final_sync",
            "shutdown_source",
            "validate_target",
            "admit_writes",
            "verify_activation",
        )
    )


def compose_migration(
    base: dict[str, Any], bound: dict[str, Any], recipe: dict[str, Any], now: int
) -> dict[str, Any]:
    base, bound, recipe = deepcopy(base), deepcopy(bound), deepcopy(recipe)
    shape(
        recipe,
        {
            "schema_version",
            "scope",
            "base_content_sha256",
            "source_identity_sha256",
            "target_identity_sha256",
            "mode",
            "method",
            "expires_at",
            "delta",
            "artifacts",
            "rehearsal_sha256",
            "recovery_of_sha256",
            "source_job_id",
            "intents",
            "native",
            "campaign",
        }
        | ({"destination_sha256"} if "destination_sha256" in bound else set()),
    )
    if type(recipe["schema_version"]) is not int or recipe["schema_version"] != (
        2 if "destination_sha256" in bound else 1
    ):
        raise Rejected("invalid_migration_recipe", 422)
    if "destination_sha256" in bound and (
        sha(recipe["destination_sha256"]) != bound["destination_sha256"]
    ):
        raise Rejected("migration_destination_mapping_changed", 423)
    scope = shape(
        recipe["scope"], {"tenant_id", "site_id", "environment", "resource_id", "project_id"}
    )
    if (
        base.get("action") != "application.migrate"
        or "native_migration" in base
        or base.get("execution_ready") is not True
        or base.get("lane") != "operational"
        or base.get("holds") != []
        or digest(base) != sha(recipe["base_content_sha256"])
        or any(
            base["scope"].get(k) != scope[k]
            for k in ("tenant_id", "site_id", "environment", "resource_id")
        )
        or base["scope"].get("native_scope") != "project:" + str(scope["project_id"])
    ):
        raise Rejected("current_qualified_base_plan_required", 423)
    for side in ("source", "target"):
        profile = bound[side]
        if profile["native_identity_sha256"] != sha(recipe[side + "_identity_sha256"]):
            raise Rejected("migration_recipe_scope_changed", 423)
        for key in ("native_identity_sha256", "profile_sha256", "tuple_sha256"):
            sha(profile[key])
        if (
            not 0 <= now - integer(profile["observed_at"]) <= 3600
            or integer(profile["expires_at"]) <= now
        ):
            raise Rejected("migration_profile_stale", 423)
    if recipe["method"] != bound["method"]:
        raise Rejected("migration_method_changed", 423)
    order = stage_order(recipe["mode"], recipe["method"])
    intents = shape(recipe["intents"], set(order))
    for intent in intents.values():
        sha(intent)
    if len(set(intents.values())) != len(intents):
        raise Rejected("migration_stage_artifacts_ambiguous", 422)
    if "destination_sha256" in bound and recipe["mode"] not in RECOVERY:
        destination_plan = base["native_api"].get("operation_plan", {})
        if (
            destination_plan.get("kind") != "ahv_destination"
            or destination_plan.get("destination_sha256") != bound["destination_sha256"]
            or digest(destination_plan) != intents.get("import_target")
        ):
            raise Rejected("migration_destination_artifact_changed", 423)
    delta = shape(recipe["delta"], {"kind", "requires_running_guest", "qualification_sha256"})
    if (
        delta["kind"] != DELTA[recipe["method"]]
        or type(delta["requires_running_guest"]) is not bool
        or (delta["kind"] == "none" and delta["requires_running_guest"])
    ):
        raise Rejected("migration_delta_method_changed", 422)
    sha(delta["qualification_sha256"])
    for value in shape(
        recipe["artifacts"], {"capture", "transfer", "conversion", "guest", "delta", "recovery"}
    ).values():
        sha(value)
    if recipe["mode"] == "cutover":
        sha(recipe["rehearsal_sha256"])
    elif recipe["rehearsal_sha256"] is not None:
        raise Rejected("unexpected_rehearsal_reference", 422)
    if recipe["mode"] in RECOVERY:
        sha(recipe["recovery_of_sha256"])
        identifier(recipe["source_job_id"])
    elif recipe["recovery_of_sha256"] is not None or recipe["source_job_id"] is not None:
        raise Rejected("unexpected_recovery_reference", 422)
    native = shape(
        recipe["native"],
        {
            "configuration",
            "tuple_digest",
            "source_revision",
            "ownership_digest",
            "custody_id",
            "custody_generation",
            "policy_cases",
        },
    )
    if native["ownership_digest"] != digest(base["ownership"]):
        raise Rejected("migration_ownership_changed", 423)
    api = base["native_api"]
    if any(native[k] != api[k] for k in ("custody_id", "custody_generation")):
        raise Rejected("migration_custody_changed", 423)
    sha(native["tuple_digest"])
    identifier(native["custody_id"])
    integer(native["custody_generation"])
    shape(native["configuration"], {"revision", "digest"})
    integer(native["configuration"]["revision"], 1)
    sha(native["configuration"]["digest"])
    import re

    if (
        not isinstance(native["source_revision"], str)
        or re.fullmatch(r"[a-f0-9]{40}", native["source_revision"]) is None
    ):
        raise Rejected("invalid_migration_source_revision", 422)
    cases = native["policy_cases"]
    if not isinstance(cases, list) or not 6 <= len(cases) <= 256:
        raise Rejected("migration_policy_matrix_required", 422)
    names, coverage = set(), set()
    for case in cases:
        shape(case, {"id", "boundary", "expectation", "family", "direction"})
        if (
            not isinstance(case["id"], str)
            or re.fullmatch(r"[a-z0-9_-]{1,80}", case["id"]) is None
            or case["id"] in names
            or case["boundary"] not in {"same_host_subnet", "inter_host", "edge"}
            or case["expectation"] not in {"allow", "deny"}
            or case["family"] not in {"ipv4", "ipv6"}
            or case["direction"] not in {"forward", "return"}
        ):
            raise Rejected("invalid_migration_policy_case", 422)
        names.add(case["id"])
        coverage.add((case["boundary"], case["expectation"]))
    if coverage != {
        (b, e) for b in ("same_host_subnet", "inter_host", "edge") for e in ("allow", "deny")
    }:
        raise Rejected("migration_policy_coverage_incomplete", 422)
    campaign = shape(recipe["campaign"], {"route_sha256", "sizes", "demands"})
    sha(campaign["route_sha256"])
    for value in shape(campaign["sizes"], PHASES).values():
        integer(value, 0, 2**60)
    # These are approved infrastructure budgets, never browser-supplied rates or observations.
    demands = campaign["demands"]
    if not isinstance(demands, dict) or not 1 <= len(demands) <= 32:
        raise Rejected("migration_resource_budgets_required", 422)
    for key, value in demands.items():
        if not isinstance(key, str) or re.fullmatch(r"[A-Za-z0-9_.:/-]{1,200}", key) is None:
            raise Rejected("invalid_migration_resource_pool", 422)
        integer(value, 1, 2**60)
    total = sum(integer(d["capacity_bytes"], 1) for d in bound["disks"])
    if recipe["mode"] not in RECOVERY and any(
        campaign["sizes"][p] < total for p in ("transfer", "conversion", "import")
    ):
        raise Rejected("migration_data_budget_insufficient", 423)
    expiry = min(
        integer(recipe["expires_at"], 1),
        base["valid_until"],
        base["input_fresh_until"],
        bound["source"]["expires_at"],
        bound["target"]["expires_at"],
    )
    if expiry <= now:
        raise Rejected("migration_plan_expired", 423)
    migration = {
        "schema_version": 3 if "destination_sha256" in bound else 2,
        **bound,
        **{
            k: recipe[k]
            for k in ("mode", "delta", "artifacts", "rehearsal_sha256", "recovery_of_sha256")
        },
    }
    base.update(
        valid_until=expiry,
        native_migration={
            "schema_version": 1,
            "scope": scope,
            "migration": migration,
            "intents": intents,
            "native": native,
            "source_job_id": recipe["source_job_id"],
            "recipe_sha256": digest(recipe),
        },
        migration_campaign={**campaign, "mode": recipe["mode"], "method": recipe["method"]},
    )
    base["effects"] = [
        {
            "id": stage,
            "after": [] if index == 0 else [order[index - 1]],
            "owner": "lifecycle",
            "scope": base["scope"],
            "artifact_digest": intents[stage],
            "destructive": True,
            "boundary": "independent_native_stage_observation",
            "on_unknown": "hold_and_observe_before_retry",
            "authority_recheck": "immediately_before_effect",
        }
        for index, stage in enumerate(order)
    ]
    return base
