"""Complete provisioning/retirement proposals from qualified plans and owned recipes."""

import re
from copy import deepcopy
from typing import Any

from planning.domain.model import Rejected, digest, identifier, integer, sha, shape

STAGES = {
    "provision": ("reserve", "provision", "configure_guest", "enroll_services", "activate"),
    "retire": ("retire", "release"),
}


def native_details(base: dict[str, Any], value: dict[str, Any]) -> None:
    shape(
        value,
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
    if value["ownership_digest"] != digest(base["ownership"]) or any(
        value[k] != base["native_api"][k] for k in ("custody_id", "custody_generation")
    ):
        raise Rejected("native_recipe_custody_changed", 423)
    identifier(value["custody_id"])
    integer(value["custody_generation"])
    sha(value["tuple_digest"])
    config = shape(value["configuration"], {"revision", "digest"})
    integer(config["revision"], 1)
    sha(config["digest"])
    if not isinstance(value["source_revision"], str) or not re.fullmatch(
        r"[a-f0-9]{40}", value["source_revision"]
    ):
        raise Rejected("invalid_native_source_revision", 422)
    cases = value["policy_cases"]
    if not isinstance(cases, list) or not 6 <= len(cases) <= 256:
        raise Rejected("native_policy_matrix_required", 422)
    names, covered = set(), set()
    for case in cases:
        shape(case, {"id", "boundary", "expectation", "family", "direction"})
        if (
            not isinstance(case["id"], str)
            or not re.fullmatch(r"[a-z0-9_-]{1,80}", case["id"])
            or case["id"] in names
            or case["boundary"] not in {"same_host_subnet", "inter_host", "edge"}
            or case["expectation"] not in {"allow", "deny"}
            or case["family"] not in {"ipv4", "ipv6"}
            or case["direction"] not in {"forward", "return"}
        ):
            raise Rejected("invalid_native_policy_case", 422)
        names.add(case["id"])
        covered.add((case["boundary"], case["expectation"]))
    if covered != {
        (b, e) for b in ("same_host_subnet", "inter_host", "edge") for e in ("allow", "deny")
    }:
        raise Rejected("native_policy_coverage_incomplete", 422)


def compose_native(base: dict[str, Any], recipe: dict[str, Any], now: int) -> dict[str, Any]:
    base, recipe = deepcopy(base), deepcopy(recipe)
    shape(
        recipe,
        {
            "schema_version",
            "scope",
            "base_content_sha256",
            "purpose",
            "source_job_id",
            "expires_at",
            "intents",
            "native",
        },
    )
    purpose = recipe["purpose"]
    if type(recipe["schema_version"]) is not int or recipe["schema_version"] != 1:
        raise Rejected("invalid_native_recipe", 422)
    if purpose not in STAGES or base.get("action") != "application." + purpose:
        raise Rejected("native_recipe_action_changed", 423)
    scope = shape(
        recipe["scope"], {"tenant_id", "site_id", "environment", "resource_id", "project_id"}
    )
    for key in ("tenant_id", "site_id", "environment", "resource_id"):
        identifier(scope[key])
    if (
        any(k in base for k in ("native_migration", "native_provisioning"))
        or base.get("execution_ready") is not True
        or base.get("lane") != "operational"
        or base.get("holds") != []
        or digest(base) != sha(recipe["base_content_sha256"])
        or any(base["scope"].get(k) != scope[k] for k in scope if k != "project_id")
        or base["scope"].get("native_scope") != "project:" + str(scope["project_id"])
    ):
        raise Rejected("current_qualified_base_plan_required", 423)
    project = scope["project_id"]
    if not isinstance(project, str) or re.fullmatch(r"[a-f0-9]{32}", project) is None:
        identifier(project)
    if purpose == "retire":
        identifier(recipe["source_job_id"])
    elif recipe["source_job_id"] is not None:
        raise Rejected("unexpected_native_source_job", 422)
    stages = STAGES[purpose]
    intents = shape(recipe["intents"], set(stages))
    for value in intents.values():
        sha(value)
    if len(set(intents.values())) != len(stages):
        raise Rejected("native_stage_artifacts_ambiguous", 422)
    if intents[purpose] != base["native_api"]["operation_plan_sha256"]:
        raise Rejected("native_operation_artifact_changed", 423)
    native_details(base, recipe["native"])
    expiry = min(
        integer(recipe["expires_at"], 1),
        integer(base["valid_until"], 1),
        integer(base["input_fresh_until"], 1),
    )
    if expiry <= now:
        raise Rejected("native_plan_expired", 423)
    base.update(
        valid_until=expiry,
        native_provisioning={
            "schema_version": 1,
            "scope": scope,
            "purpose": purpose,
            "source_job_id": recipe["source_job_id"],
            "intents": intents,
            "native": recipe["native"],
            "recipe_sha256": digest(recipe),
        },
    )
    base["effects"] = [
        {
            "id": stage,
            "after": [] if i == 0 else [stages[i - 1]],
            "owner": "lifecycle",
            "scope": base["scope"],
            "artifact_digest": intents[stage],
            "destructive": True,
            "boundary": "independent_native_stage_observation",
            "on_unknown": "hold_and_observe_before_retry",
            "authority_recheck": "immediately_before_effect",
        }
        for i, stage in enumerate(stages)
    ]
    return base
