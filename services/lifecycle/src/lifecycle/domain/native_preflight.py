"""Offline P07 native plan comparison; no native or retry authority is issued."""

import re
from typing import Any

from lifecycle.domain.admission import digest
from lifecycle.domain.commissioning import (
    assess,
    exact_id,
    sha256,
    timestamp,
)
from lifecycle.domain.execution import Rejected, shape

CUSTODY_KEYS = {"custody_ref", "custody_id", "custody_generation", "fence_owner"}
NATIVE_KEYS = CUSTODY_KEYS | {
    "operation_plan",
    "operation_plan_sha256",
    "api_contracts_sha256",
    "adapter_sha256",
}


def validate_contracts(manifest: dict[str, Any]) -> None:
    shape(manifest, {"schema_version", "api_versions", "adapter_sha256", "worker_image_digest"})
    if (
        type(manifest["schema_version"]) is not int
        or manifest["schema_version"] != 1
        or manifest["api_versions"] != {"compute": "2.1", "network": "2.0", "volume": "3.0"}
        or not sha256(manifest["adapter_sha256"])
        or not isinstance(manifest["worker_image_digest"], str)
        or re.fullmatch(r"sha256:[a-f0-9]{64}", manifest["worker_image_digest"]) is None
    ):
        raise Rejected("unpinned_native_api_contracts", 422)


def validate_custody(state: dict[str, Any]) -> None:
    if (
        not all(exact_id(state[k]) for k in ("custody_id", "fence_owner"))
        or not isinstance(state["custody_ref"], str)
        or re.fullmatch(r"evidence://[A-Za-z0-9_-]+/[A-Za-z0-9._/-]+", state["custody_ref"]) is None
        or ".." in state["custody_ref"].split("/")
        or state["custody_ref"].endswith("/")
        or type(state["custody_generation"]) is not int
        or not 0 <= state["custody_generation"] <= 2**63 - 1
    ):
        raise Rejected("invalid_native_custody_binding", 422)


def validate_ownership(owners: Any, custody_ref: str) -> None:
    if not isinstance(owners, list) or not 1 <= len(owners) <= 512:
        raise Rejected("invalid_native_ownership", 422)
    seen: set[tuple[str, str]] = set()
    for owner in owners:
        shape(owner, {"resource", "fields", "writer", "custody_ref", "native_identity"})
        if (
            not exact_id(owner["resource"])
            or not exact_id(owner["writer"])
            or not isinstance(owner["fields"], list)
            or not 1 <= len(owner["fields"]) <= 128
            or not all(exact_id(f) for f in owner["fields"])
            or owner["custody_ref"] != custody_ref
            or (owner["native_identity"] is not None and not exact_id(owner["native_identity"]))
        ):
            raise Rejected("invalid_native_ownership", 422)
        for field in owner["fields"]:
            key = (owner["resource"], field)
            if key in seen:
                raise Rejected("native_field_ownership_collision", 409)
            seen.add(key)


def assess_native_plan(
    plan: dict[str, Any],
    commissioning: dict[str, Any],
    api_contracts: dict[str, Any],
    snapshot: dict[str, Any],
    operation_plan_sha256: str,
    now: int,
) -> dict[str, Any]:
    """All inputs are supplied records; callers must not interpret comparison as a grant."""
    readiness = assess(commissioning, now)
    shape(plan, {"content", "binding"})
    content, binding = plan["content"], plan["binding"]
    if not isinstance(content, dict) or not isinstance(binding, dict):
        raise Rejected("invalid_plan_envelope", 422)
    if (
        binding.get("digest") != digest({k: v for k, v in binding.items() if k != "digest"})
        or binding.get("content_digest") != digest(content)
        or content.get("canonicalization") != "p05-json-v1"
        or binding.get("canonicalization") != "p05-json-v1"
        or type(content.get("schema_version")) is not int
        or content["schema_version"] != 1
    ):
        raise Rejected("plan_integrity", 422)
    native_api = content["native_api"]
    shape(native_api, NATIVE_KEYS)
    validate_custody(native_api)
    if not all(sha256(native_api[k]) for k in ("operation_plan_sha256", "api_contracts_sha256")):
        raise Rejected("unpinned_native_plan", 422)
    operation = native_api["operation_plan"]
    if (
        not isinstance(operation, dict)
        or digest(operation) != native_api["operation_plan_sha256"]
        or operation.get("ownership_digest") != digest(content["ownership"])
        or operation.get("custody_id") != native_api["custody_id"]
        or operation.get("custody_generation") != native_api["custody_generation"]
        or content["scope"]["native_scope"] != "project:" + str(operation.get("project_id"))
        or native_api["adapter_sha256"] != content["artifacts"]["adapter"]
    ):
        raise Rejected("native_operation_scope_changed", 422)
    validate_contracts(api_contracts)
    validate_ownership(content["ownership"], native_api["custody_ref"])
    shape(
        snapshot,
        {
            "scope",
            "installed_tuple",
            "artifacts",
            "native_api",
            "ownership",
            "api_contracts_sha256",
            "observed_at",
            "observer_id",
            "executor_id",
            "outstanding_operation_ids",
        },
    )
    shape(snapshot["native_api"], CUSTODY_KEYS | {"lock_id", "fence", "lease_expires_at", "held"})
    validate_custody(snapshot["native_api"])
    if (
        not timestamp(snapshot["observed_at"])
        or not exact_id(snapshot["observer_id"])
        or not exact_id(snapshot["executor_id"])
        or not sha256(operation_plan_sha256)
        or not sha256(snapshot["api_contracts_sha256"])
        or not isinstance(snapshot["outstanding_operation_ids"], list)
        or len(snapshot["outstanding_operation_ids"]) > 128
        or not all(exact_id(o) for o in snapshot["outstanding_operation_ids"])
    ):
        raise Rejected("invalid_native_snapshot", 422)
    holds: list[str] = []
    if not readiness["record_complete"]:
        holds.append("commissioning_not_complete")
    cb = commissioning["binding"]
    if cb is None or any(
        cb[k] != v
        for k, v in {
            "scope": content["scope"],
            "plan_digest": binding["digest"],
            "installed_tuple_sha256": digest(content["installed_tuple"]),
            "artifact_set_sha256": digest(content["artifacts"]),
            "ownership_sha256": digest(content["ownership"]),
            "api_contracts_sha256": native_api["api_contracts_sha256"],
            "custody_binding_sha256": digest({k: native_api[k] for k in CUSTODY_KEYS}),
        }.items()
    ):
        holds.append("commissioning_plan_mismatch")
    if (
        content.get("action") != "application.provision"
        or content.get("method") != "native_api"
        or content.get("lane") != "isolated_campaign"
        or content["installed_tuple"].get("platform") != "openstack"
    ):
        holds.append("outside_initial_native_campaign")
    if any(
        binding.get(k) != content.get(k) for k in ("action", "lane", "executor_ids", "valid_until")
    ) or any(
        binding.get(k) != content["scope"].get(k)
        for k in ("tenant_id", "site_id", "environment", "resource_id")
    ):
        holds.append("plan_binding_mismatch")
    if (
        not timestamp(content["valid_until"])
        or not timestamp(content["input_fresh_until"])
        or min(content["valid_until"], content["input_fresh_until"]) <= now
    ):
        holds.append("plan_or_facts_expired")
    if native_api["operation_plan_sha256"] != operation_plan_sha256:
        holds.append("native_operation_plan_changed")
    if (
        not native_api["api_contracts_sha256"]
        == digest(api_contracts)
        == snapshot["api_contracts_sha256"]
        or api_contracts["adapter_sha256"] != native_api["adapter_sha256"]
        or api_contracts["api_versions"] != operation.get("api_versions")
    ):
        holds.append("api_contracts_changed")
    for key in ("scope", "installed_tuple", "artifacts", "ownership"):
        if snapshot[key] != content[key]:
            holds.append(key + "_changed")
    if any(snapshot["native_api"][k] != native_api[k] for k in CUSTODY_KEYS):
        holds.append("native_custody_changed")
    lock = snapshot["native_api"]
    if (
        lock["held"] is not True
        or not exact_id(lock["lock_id"])
        or type(lock["fence"]) is not int
        or lock["fence"] < 1
        or not timestamp(lock["lease_expires_at"])
        or lock["lease_expires_at"] <= now
    ):
        holds.append("current_custody_lock_missing")
    if snapshot["observer_id"] == snapshot["executor_id"]:
        holds.append("independent_native_observer_missing")
    if snapshot["executor_id"] not in content["executor_ids"]:
        holds.append("executor_changed")
    if snapshot["observed_at"] > now or now - snapshot["observed_at"] > 5:
        holds.append("native_snapshot_stale")
    if snapshot["outstanding_operation_ids"]:
        holds.append("outstanding_effect_requires_reconciliation")
    return {
        "result": "HELD" if holds else "PRECHECK_PASSED_REQUIRES_CURRENT_AUTHORITY",
        "holds": sorted(set(holds)),
        "plan_digest": binding["digest"],
        "snapshot_sha256": digest(snapshot),
        "commissioning_record_sha256": digest(commissioning),
        "evaluated_at": now,
        "native_write_authorized": False,
        "retry_authorized": False,
        "limitations": [
            "Record and byte comparison only; no authenticated owner read or evidence fetch.",
            "Execution checks adapter bytes, authentic owners and current lock possession.",
            "Native operation schemas are validated again by the worker before any request.",
        ],
    }
