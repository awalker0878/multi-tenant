"""Initial AHV destination: raw disks, BIOS, SCSI, disconnected VirtIO NICs, powered off."""

import re
from typing import Any

from lifecycle_worker.application.api_plan import name, shape
from lifecycle_worker.application.native import NativeBinding, NativeHeld, digest, identity, sha256


def validate(p: dict[str, Any], binding: NativeBinding) -> dict[str, Any]:
    shape(
        p,
        {
            "api_versions",
            "custody_id",
            "custody_generation",
            "ownership_digest",
            "schema_version",
            "kind",
            "project_id",
            "prism_central_id",
            "cluster_id",
            "destination_sha256",
            "conversion_plan_sha256",
            "name",
            "cpu",
            "memory_bytes",
            "disks",
            "nics",
            "category_ids",
            "policy_ids",
            "shared_resource_ids",
            "max_seconds",
        },
    )
    if (
        type(p["schema_version"]) is not int
        or p["schema_version"] != 1
        or p["kind"] != "ahv_destination"
        or p["project_id"] != binding.project_id
        or digest(p) != binding.operation_plan_sha256
        or not sha256(p["destination_sha256"])
        or not sha256(p["conversion_plan_sha256"])
    ):
        raise NativeHeld("ahv_destination_plan_changed")
    if p["api_versions"] != dict.fromkeys(
        ("vmm", "prism", "clustermgmt", "networking", "microseg", "iam"), "v4.3"
    ) or any(
        p[k] != binding.document()[k]
        for k in ("custody_id", "custody_generation", "ownership_digest")
    ):
        raise NativeHeld("ahv_custody_or_api_contract_changed")
    for field in ("project_id", "prism_central_id", "cluster_id"):
        identity(p[field])
    name(p["name"])
    for field, lower, upper in (
        ("cpu", 1, 256),
        ("memory_bytes", 1048576, 2**44),
        ("max_seconds", 1, 86400),
    ):
        if type(p[field]) is not int or not lower <= p[field] <= upper:
            raise NativeHeld("invalid_ahv_shape")
    for field in ("category_ids", "policy_ids"):
        if (
            not isinstance(p[field], list)
            or not 1 <= len(p[field]) <= 32
            or len(set(p[field])) != len(p[field])
        ):
            raise NativeHeld("invalid_ahv_security_mapping")
        for key in p[field]:
            identity(key)
    if (
        not isinstance(p["disks"], list)
        or not 1 <= len(p["disks"]) <= 32
        or not isinstance(p["nics"], list)
        or len(p["nics"]) > 32
    ):
        raise NativeHeld("invalid_ahv_device_map")
    shared = p["shared_resource_ids"]
    if (
        not isinstance(shared, list)
        or len(shared) > 96
        or len(set(shared)) != len(shared)
        or not set(shared)
        <= {
            *(p["policy_ids"]),
            *(n[k] for n in p["nics"] for k in ("quarantine_subnet_id", "production_subnet_id")),
        }
    ):
        raise NativeHeld("invalid_ahv_shared_resources")
    for key in shared:
        identity(key)
    keys = set()
    for index, d in enumerate(p["disks"]):
        shape(d, {"key", "index", "virtual_bytes", "storage_container_id", "format"})
        if (
            not isinstance(d["key"], str)
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", d["key"])
            or d["key"] == "vm"
            or d["key"] in keys
            or type(d["index"]) is not int
            or d["index"] != index
            or d["format"] != "raw"
            or type(d["virtual_bytes"]) is not int
            or not 512 <= d["virtual_bytes"] <= 2**46
        ):
            raise NativeHeld("invalid_ahv_disk_map")
        keys.add(d["key"])
        identity(d["storage_container_id"])
    nic_keys: set[int] = set()
    for nic in p["nics"]:
        shape(nic, {"source_key", "quarantine_subnet_id", "production_subnet_id"})
        if (
            type(nic["source_key"]) is not int
            or nic["source_key"] in nic_keys
            or nic["source_key"] < 0
            or nic["quarantine_subnet_id"] == nic["production_subnet_id"]
        ):
            raise NativeHeld("invalid_ahv_network_map")
        nic_keys.add(nic["source_key"])
        identity(nic["quarantine_subnet_id"])
        identity(nic["production_subnet_id"])
    return p


def marker(binding: NativeBinding) -> str:
    return "migration:" + binding.fingerprint


def image_body(
    p: dict[str, Any], d: dict[str, Any], receipt: dict[str, Any], url: str, binding: NativeBinding
) -> dict[str, Any]:
    return {
        "name": p["name"] + "-" + d["key"],
        "type": "DISK_IMAGE",
        "description": marker(binding),
        "projectExtId": p["project_id"],
        "isSharedWithAllProjects": False,
        "clusterLocationExtIds": [p["cluster_id"]],
        "categoryExtIds": p["category_ids"],
        "checksum": {
            "$objectType": "vmm.v4.content.ImageSha256Checksum",
            "hexDigest": receipt["sha256"],
        },
        "source": {
            "$objectType": "vmm.v4.content.UrlSource",
            "url": url,
            "shouldAllowInsecureUrl": False,
        },
    }


def vm_body(p: dict[str, Any], images: dict[str, str], binding: NativeBinding) -> dict[str, Any]:
    return {
        "name": p["name"],
        "description": marker(binding),
        "projectExtId": p["project_id"],
        "cluster": {"extId": p["cluster_id"]},
        "numSockets": p["cpu"],
        "numCoresPerSocket": 1,
        "numThreadsPerCore": 1,
        "memorySizeBytes": p["memory_bytes"],
        "powerState": "OFF",
        "bootConfig": {"$objectType": "vmm.v4.ahv.config.LegacyBoot", "bootOrder": ["DISK"]},
        "categories": [{"extId": key} for key in p["category_ids"]],
        "disks": [
            {
                "diskAddress": {"busType": "SCSI", "index": d["index"]},
                "backingInfo": {
                    "$objectType": "vmm.v4.ahv.config.VmDisk",
                    "diskSizeBytes": d["virtual_bytes"],
                    "storageContainer": {"extId": d["storage_container_id"]},
                    "dataSource": {
                        "reference": {
                            "$objectType": "vmm.v4.ahv.config.ImageReference",
                            "imageExtId": images[d["key"]],
                        }
                    },
                },
            }
            for d in p["disks"]
        ],
        "nics": [
            {
                "backingInfo": {"model": "VIRTIO", "isConnected": False},
                "networkInfo": {
                    "nicType": "NORMAL_NIC",
                    "vlanMode": "ACCESS",
                    "subnet": {"extId": n["quarantine_subnet_id"]},
                },
            }
            for n in p["nics"]
        ],
    }
