"""Offline P07 saved-plan comparison; no apply, retry or native authority is issued."""

import re
from typing import Any

from lifecycle.domain.admission import digest
from lifecycle.domain.commissioning import (
    assess,
    exact_id,
    sha256,
    timestamp,
    validate_evidence,
)
from lifecycle.domain.execution import Rejected, shape

STATE_KEYS = {"backend_ref", "workspace", "state_lineage", "state_serial", "lock_owner"}
TERRAFORM_KEYS = STATE_KEYS | {"saved_plan_sha256", "toolchain_sha256"}


def _version(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", value) is not None


def validate_toolchain(manifest: dict[str, Any]) -> None:
    shape(
        manifest,
        {
            "schema_version",
            "terraform",
            "providers",
            "modules",
            "dependency_lock_sha256",
            "worker_image_digest",
        },
    )
    shape(manifest["terraform"], {"version", "sha256"})
    if (
        type(manifest["schema_version"]) is not int
        or manifest["schema_version"] != 1
        or not _version(manifest["terraform"]["version"])
        or not sha256(manifest["terraform"]["sha256"])
        or not sha256(manifest["dependency_lock_sha256"])
        or not isinstance(manifest["worker_image_digest"], str)
        or re.fullmatch(r"sha256:[a-f0-9]{64}", manifest["worker_image_digest"]) is None
    ):
        raise Rejected("unpinned_native_toolchain", 422)
    providers = manifest["providers"]
    if not isinstance(providers, list) or not 1 <= len(providers) <= 32:
        raise Rejected("invalid_provider_inventory", 422)
    seen: set[str] = set()
    for provider in providers:
        shape(provider, {"source", "version", "sha256"})
        source = provider["source"]
        if (
            not isinstance(source, str)
            or re.fullmatch(r"[a-z0-9.-]+/[a-z0-9_-]+/[a-z0-9_-]+", source) is None
            or source in seen
            or not _version(provider["version"])
            or not sha256(provider["sha256"])
        ):
            raise Rejected("unpinned_or_duplicate_provider", 422)
        seen.add(source)
    modules = manifest["modules"]
    if not isinstance(modules, list) or not 1 <= len(modules) <= 64:
        raise Rejected("invalid_module_inventory", 422)
    seen = set()
    for module in modules:
        shape(module, {"id", "uri", "revision", "sha256"})
        if not exact_id(module["id"]) or module["id"] in seen:
            raise Rejected("invalid_or_duplicate_module", 422)
        # Immutable protected module identities use the same reference rules as commissioning.
        validate_evidence(
            {k: v for k, v in module.items() if k != "id"}
            | {"level": "E1", "binding_sha256": digest(manifest["terraform"])},
            digest(manifest["terraform"]),
        )
        seen.add(module["id"])


def validate_state(state: dict[str, Any]) -> None:
    if (
        not all(exact_id(state[k]) for k in ("workspace", "state_lineage", "lock_owner"))
        or not isinstance(state["backend_ref"], str)
        or re.fullmatch(r"evidence://[A-Za-z0-9_-]+/[A-Za-z0-9._/-]+", state["backend_ref"]) is None
        or ".." in state["backend_ref"].split("/")
        or state["backend_ref"].endswith("/")
        or type(state["state_serial"]) is not int
        or not 0 <= state["state_serial"] <= 2**63 - 1
    ):
        raise Rejected("invalid_native_state_binding", 422)


def validate_ownership(owners: Any, backend_ref: str) -> None:
    if not isinstance(owners, list) or not 1 <= len(owners) <= 512:
        raise Rejected("invalid_native_ownership", 422)
    seen: set[tuple[str, str]] = set()
    for owner in owners:
        shape(owner, {"resource", "fields", "writer", "state_ref", "native_identity"})
        if (
            not exact_id(owner["resource"])
            or not exact_id(owner["writer"])
            or not isinstance(owner["fields"], list)
            or not 1 <= len(owner["fields"]) <= 128
            or not all(exact_id(f) for f in owner["fields"])
            or owner["state_ref"] != backend_ref
            or (owner["native_identity"] is not None and not exact_id(owner["native_identity"]))
        ):
            raise Rejected("invalid_native_ownership", 422)
        for field in owner["fields"]:
            key = (owner["resource"], field)
            if key in seen:
                raise Rejected("native_field_ownership_collision", 409)
            seen.add(key)


def assess_saved_plan(
    plan: dict[str, Any],
    commissioning: dict[str, Any],
    toolchain: dict[str, Any],
    snapshot: dict[str, Any],
    saved_plan_sha256: str,
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
    terraform = content["terraform"]
    shape(terraform, TERRAFORM_KEYS)
    validate_state(terraform)
    if not all(sha256(terraform[k]) for k in ("saved_plan_sha256", "toolchain_sha256")):
        raise Rejected("unpinned_saved_plan", 422)
    validate_toolchain(toolchain)
    validate_ownership(content["ownership"], terraform["backend_ref"])
    shape(
        snapshot,
        {
            "scope",
            "installed_tuple",
            "artifacts",
            "terraform",
            "ownership",
            "toolchain_sha256",
            "observed_at",
            "observer_id",
            "executor_id",
            "outstanding_operation_ids",
        },
    )
    shape(snapshot["terraform"], STATE_KEYS | {"lock_id", "fence", "lease_expires_at", "held"})
    validate_state(snapshot["terraform"])
    if (
        not timestamp(snapshot["observed_at"])
        or not exact_id(snapshot["observer_id"])
        or not exact_id(snapshot["executor_id"])
        or not sha256(saved_plan_sha256)
        or not sha256(snapshot["toolchain_sha256"])
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
            "toolchain_sha256": terraform["toolchain_sha256"],
            "state_binding_sha256": digest({k: terraform[k] for k in STATE_KEYS}),
        }.items()
    ):
        holds.append("commissioning_plan_mismatch")
    if (
        content.get("action") != "application.provision"
        or content.get("method") != "saved_plan"
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
    if terraform["saved_plan_sha256"] != saved_plan_sha256:
        holds.append("saved_plan_bytes_changed")
    if not terraform["toolchain_sha256"] == digest(toolchain) == snapshot["toolchain_sha256"]:
        holds.append("toolchain_changed")
    for key in ("scope", "installed_tuple", "artifacts", "ownership"):
        if snapshot[key] != content[key]:
            holds.append(key + "_changed")
    if any(snapshot["terraform"][k] != terraform[k] for k in STATE_KEYS):
        holds.append("terraform_state_changed")
    lock = snapshot["terraform"]
    if (
        lock["held"] is not True
        or not exact_id(lock["lock_id"])
        or type(lock["fence"]) is not int
        or lock["fence"] < 1
        or not timestamp(lock["lease_expires_at"])
        or lock["lease_expires_at"] <= now
    ):
        holds.append("current_state_lock_missing")
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
            "Saved-plan bytes are not parsed or applied; semantic changes need independent review.",
            "Actual executable/provider/module bytes and lock possession are not verified here.",
            "Native grant redemption, fencing and post-effect readback remain unimplemented.",
        ],
    }
