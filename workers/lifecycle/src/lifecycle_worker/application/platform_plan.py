"""Bounded VMware/AHV lifecycle plans with exact baseline and field ownership."""

import re
from typing import Any

from lifecycle_worker.application.native import NativeBinding, NativeHeld, digest, identity, sha256

OPERATIONS = {"power_on", "power_off", "shutdown", "resize_cpu", "resize_memory"}


def validate(plan: dict[str, Any], binding: NativeBinding) -> dict[str, Any]:
    if set(plan) != {
        "schema_version",
        "platform",
        "api_contract",
        "project_id",
        "object_id",
        "operation",
        "baseline_sha256",
        "desired",
        "tuple_sha256",
        "route_sha256",
        "adapter_sha256",
        "ownership_digest",
        "custody_id",
        "custody_generation",
    }:
        raise NativeHeld("invalid_platform_plan")
    if (
        type(plan["schema_version"]) is not int
        or plan["schema_version"] != 1
        or plan["platform"] not in {"vmware", "ahv"}
        or plan["operation"] not in OPERATIONS
        or digest(plan) != binding.operation_plan_sha256
    ):
        raise NativeHeld("platform_plan_changed_or_unsupported")
    expected_api = "vcenter-rest-v1" if plan["platform"] == "vmware" else "vmm-v4.0"
    if plan["api_contract"] != expected_api:
        raise NativeHeld("platform_api_contract_unsupported")
    for name in ("project_id", "ownership_digest", "custody_id", "custody_generation"):
        if digest(plan[name]) != digest(binding.document()[name]):
            raise NativeHeld("platform_plan_scope_changed")
    for name in ("baseline_sha256", "tuple_sha256", "route_sha256", "adapter_sha256"):
        if not sha256(plan[name]):
            raise NativeHeld("invalid_platform_digest")
    if plan["platform"] == "vmware":
        if (
            not isinstance(plan["object_id"], str)
            or re.fullmatch(r"vm-[1-9][0-9]{0,15}", plan["object_id"]) is None
        ):
            raise NativeHeld("invalid_vmware_object")
    else:
        identity(plan["object_id"])
    desired = plan["desired"]
    allowed = {"resize_cpu": {"count"}, "resize_memory": {"size_mib"}}.get(plan["operation"], set())
    if not isinstance(desired, dict) or set(desired) != allowed:
        raise NativeHeld("platform_owned_fields_invalid")
    for name, value in desired.items():
        if type(value) is not int or not 1 <= value <= (1024 if name == "count" else 16777216):
            raise NativeHeld("platform_resize_bound")
    return dict(plan)


def request(
    plan: dict[str, Any], current: dict[str, Any], etag: str, request_id: str
) -> dict[str, Any]:
    """Only fixed API routes; AHV full PUT preserves every unowned observed field."""
    if digest(current) != plan["baseline_sha256"]:
        raise NativeHeld("platform_baseline_drift")
    operation, platform = plan["operation"], plan["platform"]
    if platform == "vmware":
        base = "/api/vcenter/vm/" + plan["object_id"]
        if operation.startswith("resize_"):
            if current.get("power_state") != "POWERED_OFF":
                raise NativeHeld("platform_offline_resize_required")
            suffix = "/hardware/cpu" if operation == "resize_cpu" else "/hardware/memory"
            body = (
                plan["desired"]
                if operation == "resize_cpu"
                else {"size_MiB": plan["desired"]["size_mib"]}
            )
            return {"method": "PATCH", "path": base + suffix, "body": body, "headers": {}}
        suffix = {
            "power_on": "/power?action=start",
            "power_off": "/power?action=stop",
            "shutdown": "/guest/power?action=shutdown",
        }[operation]
        return {"method": "POST", "path": base + suffix, "body": None, "headers": {}}
    if current.get("extId") != plan["object_id"]:
        raise NativeHeld("platform_object_changed")
    if (
        not isinstance(etag, str)
        or not 1 <= len(etag) <= 256
        or any(ord(c) < 32 or ord(c) > 126 for c in etag)
    ):
        raise NativeHeld("ahv_etag_required")
    identity(request_id)
    headers = {"If-Match": etag, "Ntnx-Request-Id": request_id}
    base = "/api/vmm/v4.0/ahv/config/vms/" + plan["object_id"]
    if operation.startswith("resize_"):
        if current.get("powerState") != "OFF":
            raise NativeHeld("platform_offline_resize_required")
        body = dict(current)
        if operation == "resize_cpu":
            cores = current.get("numCoresPerSocket")
            if type(cores) is not int or cores < 1 or plan["desired"]["count"] % cores:
                raise NativeHeld("ahv_cpu_topology_unrepresentable")
            body["numSockets"] = plan["desired"]["count"] // cores
        else:
            body["memorySizeBytes"] = plan["desired"]["size_mib"] * 1024 * 1024
        return {"method": "PUT", "path": base, "body": body, "headers": headers}
    suffix = {"power_on": "power-on", "power_off": "power-off", "shutdown": "shutdown"}[operation]
    return {
        "method": "POST",
        "path": base + "/$actions/" + suffix,
        "body": None,
        "headers": headers,
    }


def achieved(plan: dict[str, Any], current: dict[str, Any]) -> bool:
    op = plan["operation"]
    if plan["platform"] == "vmware":
        if op in {"power_on", "power_off", "shutdown"}:
            return current.get("power_state") == (
                "POWERED_ON" if op == "power_on" else "POWERED_OFF"
            )
        if op == "resize_cpu":
            return bool(current.get("cpu", {}).get("count") == plan["desired"]["count"])
        return bool(current.get("memory", {}).get("size_MiB") == plan["desired"]["size_mib"])
    if current.get("extId") != plan["object_id"]:
        return False
    if op in {"power_on", "power_off", "shutdown"}:
        return current.get("powerState") == ("ON" if op == "power_on" else "OFF")
    if op == "resize_cpu":
        cores, sockets = current.get("numCoresPerSocket"), current.get("numSockets")
        return (
            type(cores) is int
            and type(sockets) is int
            and cores * sockets == plan["desired"]["count"]
        )
    return bool(current.get("memorySizeBytes") == plan["desired"]["size_mib"] * 1024 * 1024)
