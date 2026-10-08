"""Exact native create plan; no commands, arbitrary URLs or generated write-time intent."""

import ipaddress
import re
from typing import Any

from lifecycle_worker.application.native import NativeBinding, NativeHeld, digest, native_identity


def shape(value: Any, keys: set[str]) -> None:
    if not isinstance(value, dict) or set(value) != keys:
        raise NativeHeld("invalid_native_operation_plan")


def name(value: Any) -> None:
    if (
        not isinstance(value, str)
        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_. -]{0,127}", value) is None
    ):
        raise NativeHeld("invalid_native_name")


def validate_api_plan(plan: dict[str, Any], binding: NativeBinding) -> dict[str, dict[str, Any]]:
    shape(
        plan,
        {
            "schema_version",
            "project_id",
            "ownership_digest",
            "custody_id",
            "custody_generation",
            "api_versions",
            "resources",
        },
    )
    if type(plan["schema_version"]) is not int or plan["schema_version"] != 1:
        raise NativeHeld("invalid_native_operation_version")
    if digest(plan) != binding.operation_plan_sha256:
        raise NativeHeld("native_operation_plan_changed")
    for key in ("project_id", "ownership_digest", "custody_id", "custody_generation"):
        if digest(plan[key]) != digest(binding.document()[key]):
            raise NativeHeld("native_operation_scope_changed")
    if plan["api_versions"] != {"compute": "2.1", "network": "2.0", "volume": "3.0"}:
        raise NativeHeld("native_api_contract_not_supported")
    rows = plan["resources"]
    if not isinstance(rows, list) or not 3 <= len(rows) <= 128:
        raise NativeHeld("native_resource_bound")
    resources: dict[str, dict[str, Any]] = {}
    claimed: set[str] = set()
    for row in rows:
        shape(row, {"key", "kind", "spec"})
        key, kind, spec = row["key"], row["kind"], row["spec"]
        if (
            not isinstance(key, str)
            or re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", key) is None
            or key in resources
        ):
            raise NativeHeld("invalid_native_resource_key")
        if kind == "port":
            shape(
                spec,
                {
                    "name",
                    "network_id",
                    "fixed_ips",
                    "security_groups",
                    "admin_state_up",
                    "port_security_enabled",
                },
            )
            native_identity(spec["network_id"])
            if spec["admin_state_up"] is not False or spec["port_security_enabled"] is not True:
                raise NativeHeld("native_quarantine_required")
            groups, addresses = spec["security_groups"], spec["fixed_ips"]
            if (
                not isinstance(groups, list)
                or not 1 <= len(groups) <= 20
                or len(set(groups)) != len(groups)
            ):
                raise NativeHeld("native_security_groups_required")
            for group in groups:
                native_identity(group)
            if not isinstance(addresses, list) or not 1 <= len(addresses) <= 16:
                raise NativeHeld("native_addresses_required")
            seen: set[tuple[str, str]] = set()
            for address in addresses:
                shape(address, {"subnet_id", "ip_address"})
                native_identity(address["subnet_id"])
                if not isinstance(address["ip_address"], str):
                    raise NativeHeld("invalid_native_address")
                parsed = ipaddress.ip_address(address["ip_address"])
                pair = (address["subnet_id"], str(parsed))
                if pair in seen or str(parsed) != address["ip_address"]:
                    raise NativeHeld("invalid_native_address")
                seen.add(pair)
        elif kind == "volume":
            shape(spec, {"name", "size", "volume_type", "availability_zone", "imageRef"})
            if type(spec["size"]) is not int or not 1 <= spec["size"] <= 65536:
                raise NativeHeld("invalid_native_volume_size")
            name(spec["volume_type"])
            name(spec["availability_zone"])
            if spec["imageRef"] is not None:
                native_identity(spec["imageRef"])
        elif kind == "server":
            shape(
                spec, {"name", "flavorRef", "availability_zone", "config_drive", "ports", "volumes"}
            )
            name(spec["flavorRef"])
            name(spec["availability_zone"])
            if spec["config_drive"] is not True:
                raise NativeHeld("native_config_drive_required")
            ports, disks = spec["ports"], spec["volumes"]
            if (
                not isinstance(ports, list)
                or not 1 <= len(ports) <= 16
                or not isinstance(disks, list)
                or not 1 <= len(disks) <= 32
            ):
                raise NativeHeld("invalid_native_device_map")
            references = [(port, "port") for port in ports]
            boot = 0
            for disk in disks:
                shape(disk, {"key", "boot_index"})
                if type(disk["boot_index"]) is not int or disk["boot_index"] not in {-1, 0}:
                    raise NativeHeld("invalid_native_boot_map")
                boot += disk["boot_index"] == 0
                references.append((disk["key"], "volume"))
            if boot != 1:
                raise NativeHeld("one_native_boot_volume_required")
            for reference, expected_kind in references:
                if (
                    not isinstance(reference, str)
                    or reference in claimed
                    or resources.get(reference, {}).get("kind") != expected_kind
                ):
                    raise NativeHeld("native_device_dependency_or_ownership_conflict")
                claimed.add(reference)
            boot_key = next(disk["key"] for disk in disks if disk["boot_index"] == 0)
            if resources[boot_key]["spec"]["imageRef"] is None:
                raise NativeHeld("native_boot_image_required")
        else:
            raise NativeHeld("unsupported_native_resource")
        name(spec["name"])
        resources[key] = row
    if claimed != {key for key, row in resources.items() if row["kind"] != "server"} or not claimed:
        raise NativeHeld("native_device_mapping_incomplete")
    return resources


def native_payload(
    binding: NativeBinding, resource: dict[str, Any], objects: dict[str, dict[str, str]]
) -> dict[str, Any]:
    kind, spec = resource["kind"], resource["spec"]
    metadata = {
        "product_tenant_id": binding.tenant_id,
        "product_resource_id": binding.resource_id,
        "product_operation_id": binding.operation_id,
        "product_object_key": resource["key"],
    }
    if kind == "port":
        return {
            "port": spec
            | {
                "project_id": binding.project_id,
                "description": (
                    f"product:{binding.tenant_id}:{binding.resource_id}:{resource['key']}"
                ),
            }
        }
    if kind == "volume":
        return {
            "volume": {key: value for key, value in spec.items() if value is not None}
            | {"metadata": metadata}
        }
    return {
        "server": {key: value for key, value in spec.items() if key not in {"ports", "volumes"}}
        | {
            "metadata": metadata,
            "networks": [{"port": objects[key]["id"]} for key in spec["ports"]],
            "block_device_mapping_v2": [
                {
                    "uuid": objects[disk["key"]]["id"],
                    "source_type": "volume",
                    "destination_type": "volume",
                    "boot_index": disk["boot_index"],
                    "delete_on_termination": False,
                }
                for disk in spec["volumes"]
            ],
        }
    }
