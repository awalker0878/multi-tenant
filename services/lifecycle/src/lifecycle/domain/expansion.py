"""P09 exact ownership and enterprise operation safety rules."""

import re
from typing import Any

from lifecycle.domain.admission import digest
from lifecycle.domain.campaign import dependency_order, intervals
from lifecycle.domain.execution import Rejected, identity
from lifecycle.domain.native_workflow import checksum, exact, integer

OPERATIONS = frozenset(
    {
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
    }
)


def scope(value: Any) -> dict[str, Any]:
    exact(
        value,
        {
            "site_id",
            "endpoint_id",
            "native_scope",
            "object_id",
            "platform",
            "tuple_sha256",
            "environment",
            "resource_id",
        },
    )
    for key in ("site_id", "endpoint_id", "environment", "resource_id"):
        identity(value[key])
    checksum(value["tuple_sha256"])
    if value["platform"] not in {"vmware", "ahv", "openstack"}:
        raise Rejected("unsupported_expansion_platform", 422)
    for key in ("native_scope", "object_id"):
        if (
            not isinstance(value[key], str)
            or re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", value[key]) is None
        ):
            raise Rejected("invalid_native_object_scope", 422)
    return dict(value)


def fields(value: Any) -> list[str]:
    if (
        not isinstance(value, list)
        or not 1 <= len(value) <= 128
        or any(
            not isinstance(v, str) or re.fullmatch(r"[a-z][a-z0-9_.]{0,127}", v) is None
            for v in value
        )
        or len(set(value)) != len(value)
    ):
        raise Rejected("invalid_adoption_fields", 422)
    return sorted(value)


def field_keys(native_scope: dict[str, Any], selected: list[str]) -> list[str]:
    # A different tenant/application/profile cannot partition a physical field claim.
    physical = {k: native_scope[k] for k in ("site_id", "endpoint_id", "native_scope", "object_id")}
    return [digest({"scope": physical, "field": f}) for f in fields(selected)]


def observation(
    value: Any, tenant: str, native_scope: dict[str, Any], selected: list[str], now: int
) -> dict[str, Any]:
    exact(
        value,
        {
            "tenant_id",
            "scope",
            "fields",
            "observer_id",
            "writer_id",
            "observed_at",
            "expires_at",
            "epoch",
            "ownership_revision",
            "old_writers",
            "fenced_writers",
            "transfer_to",
            "active_effects",
            "certain",
            "grant_sha256",
        },
    )
    if (
        value["tenant_id"] != tenant
        or value["scope"] != native_scope
        or value["certain"] is not True
    ):
        raise Rejected("adoption_observation_uncertain", 423)
    identity(value["observer_id"])
    identity(value["writer_id"])
    identity(value["epoch"])
    checksum(value["grant_sha256"])
    integer(value["ownership_revision"], 1)
    observed, expiry = integer(value["observed_at"]), integer(value["expires_at"], 1)
    if not 0 <= now - observed <= 30 or expiry <= now or value["observer_id"] == value["writer_id"]:
        raise Rejected("adoption_observation_not_current_or_independent", 423)
    exact(value["fields"], set(selected))
    for current in value["fields"].values():
        checksum(current)
    exact(value["old_writers"], set(selected))
    for writers in [
        *value["old_writers"].values(),
        value["fenced_writers"],
        value["active_effects"],
    ]:
        if not isinstance(writers, list) or len(writers) > 128 or len(set(writers)) != len(writers):
            raise Rejected("adoption_writer_inventory_invalid", 423)
        for writer in writers:
            identity(writer)
    if value["transfer_to"] is not None:
        identity(value["transfer_to"])
    return dict(value)


def transferable(value: dict[str, Any]) -> None:
    old = {w for writers in value["old_writers"].values() for w in writers}
    if (
        not old
        or not old.issubset(value["fenced_writers"])
        or value["writer_id"] in old
        or value["transfer_to"] != value["writer_id"]
        or value["active_effects"]
    ):
        raise Rejected("old_writer_transfer_unverified", 423)


def operation(value: Any) -> dict[str, Any]:
    exact(
        value,
        {
            "id",
            "tenant_id",
            "scope",
            "operation",
            "plan_sha256",
            "adapter_sha256",
            "prerequisites",
            "demands",
            "impact_pool",
            "depends_on",
            "windows",
            "blackouts",
            "priority",
            "not_before",
            "deadline",
            "maximum_seconds",
        },
    )
    identity(value["id"])
    identity(value["tenant_id"])
    scope(value["scope"])
    if value["operation"] not in OPERATIONS:
        raise Rejected("unsupported_enterprise_operation", 422)
    for key in ("plan_sha256", "adapter_sha256", "impact_pool"):
        checksum(value[key])
    exact(
        value["prerequisites"],
        {"safety", "policy", "services", "recovery", "ownership", "capacity"},
    )
    for proof in value["prerequisites"].values():
        checksum(proof)
    demands = value["demands"]
    if not isinstance(demands, dict) or not 3 <= len(demands) <= 64:
        raise Rejected("enterprise_budgets_required", 422)
    for pool, amount in demands.items():
        checksum(pool)
        integer(amount, 1)
    if not value["windows"]:
        raise Rejected("enterprise_windows_required", 422)
    intervals(value["windows"])
    intervals(value["blackouts"])
    integer(value["priority"])
    if value["priority"] > 100:
        raise Rejected("enterprise_priority_bound", 422)
    integer(value["not_before"])
    integer(value["deadline"], value["not_before"] + 1)
    integer(value["maximum_seconds"], 1)
    if value["maximum_seconds"] > 86400:
        raise Rejected("enterprise_duration_bound", 422)
    expected = {
        digest({"tenant": value["tenant_id"]}),
        digest({"endpoint": value["scope"]["endpoint_id"]}),
        value["impact_pool"],
    }
    if not expected.issubset(demands):
        raise Rejected("tenant_and_endpoint_budgets_required", 422)
    return dict(value)


def wave(operations: Any) -> list[str]:
    if not isinstance(operations, list) or not 1 <= len(operations) <= 1000:
        raise Rejected("enterprise_wave_bound", 422)
    for item in operations:
        operation(item)
    return dependency_order(operations)


def window_open(spec: dict[str, Any], now: int) -> bool:
    end = now + spec["maximum_seconds"]
    return bool(
        spec["not_before"] <= now < end <= spec["deadline"]
        and any(w["start"] <= now and end <= w["end"] for w in spec["windows"])
        and not any(now < w["end"] and end > w["start"] for w in spec["blackouts"])
    )
