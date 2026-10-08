"""Immutable review proposals; a plan and an approval never themselves allocate resources."""

from copy import deepcopy
from typing import Any

from planning.domain.model import (
    CANONICALIZATION,
    Rejected,
    digest,
    identifier,
    integer,
    sha,
    shape,
)


def graph_order(effects: list[dict[str, Any]]) -> list[str]:
    if not 1 <= len(effects) <= 500 or len({e["id"] for e in effects}) != len(effects):
        raise Rejected("invalid_effect_graph")
    remaining = {e["id"]: set(e["after"]) for e in effects}
    if any(dependencies - remaining.keys() for dependencies in remaining.values()):
        raise Rejected("missing_effect_dependency")
    ordered: list[str] = []
    while remaining:
        ready = sorted(k for k, deps in remaining.items() if not deps)
        if not ready:
            raise Rejected("cyclic_effect_graph")
        for key in ready:
            ordered.append(key)
            del remaining[key]
        for deps in remaining.values():
            deps.difference_update(ready)
    return ordered


def compile_plan(
    assessment: dict[str, Any], candidate: int, request: dict[str, Any]
) -> dict[str, Any]:
    assessment = deepcopy(assessment)
    shape(request, {"action", "method", "lane", "executor_ids", "valid_until"})
    result = assessment["results"][integer(candidate, 0, len(assessment["results"]) - 1)]
    intent = assessment["intent"]["intent"]
    policy = assessment["inputs"][candidate]["policy"]
    destination = assessment["inputs"][candidate]["destination"]
    if request["action"] != assessment["action"] or request["method"] != assessment["method"]:
        raise Rejected("assessment_operation_changed", 409)
    if request["lane"] not in {"operational", "isolated_campaign"}:
        raise Rejected("invalid_lane")
    executors = request["executor_ids"]
    if not isinstance(executors, list) or not 1 <= len(executors) <= 32:
        raise Rejected("invalid_executors")
    executors = sorted({identifier(e) for e in executors})
    expiry = integer(request["valid_until"], 1)
    if expiry > assessment["created_at"] + 3600:
        raise Rejected("plan_expiry_bound")
    holds = sorted(
        {f["reason"] for f in result["findings"] if f["mandatory"] and f["status"] != "eligible"}
    )
    artifacts = policy["artifacts"]
    for kind in ("compiler", "adapter", "automation", "contracts"):
        sha(artifacts[kind])
    native_api = policy["native_api"]
    ownership = policy["ownership"]
    if native_api is None:
        holds.append("reviewed_native_operation_plan_missing")
    else:
        shape(
            native_api,
            {
                "operation_plan",
                "operation_plan_sha256",
                "api_contracts_sha256",
                "adapter_sha256",
                "custody_ref",
                "custody_id",
                "custody_generation",
                "fence_owner",
            },
        )
        for key in ("operation_plan_sha256", "api_contracts_sha256", "adapter_sha256"):
            sha(native_api[key])
        integer(native_api["custody_generation"])
        identifier(native_api["custody_id"])
        if any(
            not isinstance(native_api[key], str) or not native_api[key]
            for key in ("custody_ref", "fence_owner")
        ):
            raise Rejected("invalid_native_custody_binding")
        if (
            not isinstance(native_api["operation_plan"], dict)
            or digest(native_api["operation_plan"]) != native_api["operation_plan_sha256"]
            or native_api["adapter_sha256"] != artifacts["adapter"]
            or native_api["api_contracts_sha256"] != artifacts["contracts"]
        ):
            raise Rejected("native_operation_artifacts_changed")
    if ownership is None:
        holds.append("managed_field_ownership_missing")
        ownership = []
    owned: set[tuple[str, str]] = set()
    for row in ownership:
        shape(row, {"resource", "fields", "writer", "custody_ref", "native_identity"})
        if row["writer"] not in {"lifecycle", "external"} or not row["fields"]:
            raise Rejected("invalid_ownership")
        for field in row["fields"]:
            owned_field = (row["resource"], field)
            if owned_field in owned:
                raise Rejected("overlapping_field_ownership")
            owned.add(owned_field)
    if native_api is not None:
        operation = native_api["operation_plan"]
        if (
            operation.get("ownership_digest") != digest(ownership)
            or operation.get("custody_id") != native_api["custody_id"]
            or operation.get("custody_generation") != native_api["custody_generation"]
            or destination["native_scope"] != "project:" + str(operation.get("project_id"))
        ):
            raise Rejected("native_operation_scope_changed")
    mappings = []
    for w in sorted(intent["workloads"], key=lambda item: item["id"]):
        mapping = {
            "workload_id": w["id"],
            "tenant_id": assessment["tenant_id"],
            "wsd": w["wsd"],
            "security_domain": w["security_domain"],
            "site_id": destination["site_id"],
            "native_scope": destination["native_scope"],
            "domain_instance": destination["domain_bindings"].get(w["security_domain"]["id"]),
            "native_identity": destination["workload_bindings"].get(w["id"]),
            "devices": {"disks": w["disks"], "nics": w["nics"]},
            "desired": {"compute": w["compute"], "guest": w["guest"]},
        }
        if mapping["domain_instance"] is None:
            holds.append("domain_instance_binding_missing")
        if (w["id"], "infrastructure") not in owned:
            holds.append("managed_field_ownership_missing")
        mappings.append(mapping)
    scope = {
        "tenant_id": assessment["tenant_id"],
        "site_id": destination["site_id"],
        "environment": assessment["environment"],
        "resource_id": assessment["application_id"],
        "endpoint_id": destination["endpoint_id"],
        "native_scope": destination["native_scope"],
    }
    effects: list[dict[str, Any]] = []

    def effect(key: str, after: list[str], owner: str, destructive: bool, boundary: str) -> None:
        effects.append(
            {
                "id": key,
                "after": after,
                "owner": owner,
                "scope": scope,
                "artifact_digest": artifacts[
                    "adapter" if key == "execute_native_api_plan" else "automation"
                ],
                "destructive": destructive,
                "boundary": boundary,
                "on_unknown": "hold_and_observe_before_retry",
                "authority_recheck": "immediately_before_effect",
            }
        )

    effect("reserve", [], "lifecycle", False, "authoritative_owner_receipts")
    effect(
        "preflight", ["reserve"], "lifecycle", False, "current_scope_artifact_state_and_approval"
    )
    previous = "preflight"
    if assessment["action"] in {"application.migrate", "application.recover"}:
        effect(
            "fence_source_writers", [previous], "lifecycle", True, "independent_fence_observation"
        )
        effect(
            "final_data_checkpoint",
            ["fence_source_writers"],
            "lifecycle",
            False,
            "dataset_consistency_and_objectives",
        )
        previous = "final_data_checkpoint"
    if assessment["action"] == "application.migrate":
        effect(
            "export_source_vm", [previous], "lifecycle", True, "powered_off_vm_native_export_lease"
        )
        effect(
            "import_native_disks",
            ["export_source_vm"],
            "lifecycle",
            True,
            "manifest_verified_native_image_import",
        )
        previous = "import_native_disks"
    effect(
        "execute_native_api_plan",
        [previous],
        "lifecycle",
        assessment["action"] == "application.retire",
        "exact_native_requests_and_current_custody",
    )
    if assessment["action"] == "application.retire":
        effect(
            "verify_retention_and_deletion",
            ["execute_native_api_plan"],
            "lifecycle",
            True,
            "separate_retention_and_release_authority",
        )
        previous = "verify_retention_and_deletion"
    else:
        effect(
            "verify_guest_and_imported_disks",
            ["execute_native_api_plan"],
            "lifecycle",
            True,
            "isolated_target_no_business_effects",
        )
        effect(
            "verify_application",
            ["verify_guest_and_imported_disks"],
            "lifecycle",
            False,
            "independent_application_and_security_postconditions",
        )
        effect("activate_target", ["verify_application"], "lifecycle", True, "target_first_write")
        previous = "activate_target"
    effect(
        "confirm_owner_allocations", [previous], "lifecycle", False, "observe_actual_consumption"
    )
    graph_order(effects)
    reservations = [
        {
            "owner": policy["reservation_owners"].get(kind),
            "kind": kind,
            "amount": amount,
            "scope": scope,
            "ttl_seconds": 300,
            "authority": "intent_only",
            "on_expiry": "hold_until_owner_readback",
        }
        for kind, amount in sorted(result["demand"].items())
    ]
    if any(r["owner"] is None for r in reservations):
        holds.append("reservation_owner_missing")
    return {
        "schema_version": 1,
        "canonicalization": CANONICALIZATION,
        "scope": scope,
        "action": request["action"],
        "method": request["method"],
        "lane": request["lane"],
        "executor_ids": executors,
        "valid_until": expiry,
        "input_fresh_until": result["expires_at"],
        "input_digests": result["input_digests"],
        "intent_revision": assessment["intent"]["id"],
        "inventory_generation": destination["generation_id"],
        "installed_tuple": destination["installed_tuple"],
        "artifacts": artifacts,
        "native_api": native_api,
        "ownership": ownership,
        "mappings": mappings,
        "effects": effects,
        "reservation_intents": reservations,
        "budgets": {
            "demand": result["demand"],
            "max_parallel_effects": 1,
            "downtime_seconds": policy["downtime_seconds"],
            "downtime_basis": "assumption_requires_application_acceptance",
        },
        "recovery": {
            "before_target_write": "restore_confirmed_source_after_target_fence",
            "after_target_write": "forward_recovery_or_approved_reconciled_source_return",
            "automatic_source_restart": False,
            "expiry_releases_live_resources": False,
        },
        "execution_ready": not holds and request["lane"] == "operational",
        "holds": sorted(set(holds)),
        "native_write_authorized": False,
    }


def bind(content: dict[str, Any], plan_id: str, actor: str) -> dict[str, Any]:
    binding = {
        "plan_id": identifier(plan_id),
        "revision": 1,
        **{k: content["scope"][k] for k in ("tenant_id", "site_id", "environment", "resource_id")},
        "action": content["action"],
        "requested_by": identifier(actor),
        "executor_ids": content["executor_ids"],
        "valid_until": content["valid_until"],
        "content_digest": digest(content),
        "canonicalization": CANONICALIZATION,
        "lane": content["lane"],
    }
    return binding | {"digest": digest(binding)}


def diff(before: Any, after: Any, path: str = "") -> list[dict[str, str]]:
    if digest(before) == digest(after):
        return []
    if isinstance(before, dict) and isinstance(after, dict):
        rows = []
        for key in sorted(before.keys() | after.keys()):
            if key not in before or key not in after:
                rows.append(
                    {"path": path + "/" + key, "change": "added" if key in after else "removed"}
                )
            else:
                rows.extend(diff(before[key], after[key], path + "/" + key))
        return rows
    return [{"path": path or "/", "change": "changed"}]
