"""Read-only source workload profile from an enrolled vSphere VM.

Application membership/consistency remain owner inputs. Native facts cannot be
filled by administrator guesses; missing facts produce explicit readiness holds.
"""

import hashlib
import json
import re
from collections.abc import Callable
from typing import Any

from inventory_worker.infrastructure.native import CollectionFailure, exchange, secret


def fingerprint(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode()
    ).hexdigest()


def ref(value: Any, kind: str) -> str:
    if (
        not isinstance(value, dict)
        or value.get("type") != kind
        or not isinstance(value.get("value"), str)
        or re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,127}", value["value"]) is None
    ):
        raise CollectionFailure("invalid_response")
    return str(value["value"])


def normalize(vm: str, release: str, records: dict[str, Any], observed_at: int) -> dict[str, Any]:
    config, runtime, guest = records["config"], records["runtime"], records["guest"]
    about = records["content"].get("about", {})
    holds: list[str] = []
    for key in ("uuid", "instanceUuid", "guestId", "firmware"):
        if not isinstance(config.get(key), str) or not config[key]:
            holds.append("source_" + key + "_unknown")
    if not about.get("instanceUuid") or not about.get("version") or not about.get("apiVersion"):
        holds.append("vcenter_identity_or_version_unknown")
    hardware = config.get("hardware", {})
    if any(type(hardware.get(k)) is not int or hardware[k] <= 0 for k in ("numCPU", "memoryMB")):
        holds.append("compute_shape_unknown")
    rows = hardware.get("device")
    if (
        not isinstance(rows, list)
        or not 1 <= len(rows) <= 128
        or any(not isinstance(d, dict) or type(d.get("key")) is not int for d in rows)
        or len({d["key"] for d in rows}) != len(rows)
    ):
        raise CollectionFailure("invalid_response")
    disks, nics, controllers = [], [], []
    for d in rows:
        kind = d.get("_typeName", "")
        if not isinstance(kind, str):
            raise CollectionFailure("invalid_response")
        if kind == "VirtualDisk":
            chain: list[dict[str, Any]] = []
            backing = d.get("backing")
            while backing is not None:
                if not isinstance(backing, dict) or len(chain) >= 32:
                    raise CollectionFailure("invalid_response")
                chain.append(
                    {
                        "type": backing.get("_typeName"),
                        "mode": backing.get("diskMode"),
                        "identity_sha256": fingerprint(
                            {k: v for k, v in backing.items() if k != "parent"}
                        ),
                        "encrypted": backing.get("keyId") is not None,
                        "datastore": backing.get("datastore"),
                        "sharing": backing.get("sharing"),
                    }
                )
                backing = backing.get("parent")
            if not chain or any(
                c["type"]
                not in {
                    "VirtualDiskFlatVer2BackingInfo",
                    "VirtualDiskSparseVer2BackingInfo",
                    "VirtualDiskSeSparseBackingInfo",
                }
                or c["mode"] != "persistent"
                or c["encrypted"]
                or c["sharing"] not in {None, "sharingNone"}
                for c in chain
            ):
                holds.append("disk_backing_requires_qualification")
            if type(d.get("capacityInBytes")) is not int or d["capacityInBytes"] <= 0:
                holds.append("disk_capacity_unknown")
            disks.append(
                {
                    "key": d["key"],
                    "capacity_bytes": d.get("capacityInBytes"),
                    "controller_key": d.get("controllerKey"),
                    "unit_number": d.get("unitNumber"),
                    "backing_chain": chain,
                    "native_sha256": fingerprint(d),
                }
            )
        elif "macAddress" in d or "Ethernet" in kind or "Vmxnet" in kind or "E1000" in kind:
            nics.append(
                {
                    "key": d["key"],
                    "model": kind,
                    "mac": d.get("macAddress"),
                    "backing_sha256": fingerprint(d.get("backing")),
                    "connectable": {
                        k: d.get("connectable", {}).get(k)
                        for k in ("connected", "startConnected", "allowGuestControl")
                    },
                }
            )
        elif "busNumber" in d:
            controllers.append(
                {
                    "key": d["key"],
                    "model": kind,
                    "bus": d["busNumber"],
                    "sharing": d.get("sharedBus"),
                }
            )
        elif kind in {"VirtualTPM", "VirtualPCIPassthrough", "VirtualUSB", "VirtualNVDIMM"}:
            holds.append("device_requires_separate_qualification")
        elif "connectable" in d and kind not in {"VirtualCdrom", "VirtualFloppy"}:
            holds.append("unknown_connectable_device")
    if not disks:
        holds.append("disk_inventory_empty")
    controller_keys = {c["key"] for c in controllers}
    if any(d["controller_key"] not in controller_keys for d in disks):
        holds.append("disk_controller_unknown")
    if config.get("keyId") is not None:
        holds.append("encryption_key_custody_required")
    if records["capability"].get("snapshotConfigSupported") is not True:
        holds.append("snapshot_configuration_unsupported")
    if records["host_capability"].get("cloneFromSnapshotSupported") is not True:
        holds.append("exact_snapshot_clone_unsupported")
    if config.get("firmware") not in {"bios", "efi"}:
        holds.append("firmware_unknown")
    if runtime.get("powerState") not in {"poweredOff", "poweredOn"}:
        holds.append("source_power_state_unsupported")
    return {
        "schema_version": 1,
        "profile_type": "SourceWorkloadProfile",
        "platform": "vmware",
        "vm_id": vm,
        "instance_uuid": config.get("instanceUuid"),
        "bios_uuid": config.get("uuid"),
        "vcenter_uuid": about.get("instanceUuid"),
        "vcenter_version": about.get("version"),
        "api_version": release,
        "native_api_version": about.get("apiVersion"),
        "config_sha256": fingerprint(config),
        "observations_sha256": fingerprint(records),
        "observed_at": observed_at,
        "power_state": runtime.get("powerState"),
        "guest_id": config.get("guestId"),
        "tools_status": guest.get("toolsRunningStatus"),
        "tools_version": guest.get("toolsVersion"),
        "firmware": config.get("firmware"),
        "cpu": hardware.get("numCPU"),
        "memory_mb": hardware.get("memoryMB"),
        "disks": disks,
        "nics": nics,
        "controllers": controllers,
        "snapshot_tree_sha256": fingerprint(records["snapshot"]),
        "key_custody_sha256": fingerprint(config.get("keyId")),
        "required_owner_inputs": [
            "datasets_and_dependencies",
            "application_consistency",
            "guest_transformation_profile",
            "outage_and_data_objectives",
        ],
        "holds": sorted(set(holds)),
        "native_qualification": "not_established",
    }


class VmwareWorkloadDiscovery:
    def __init__(
        self, stream: dict[str, Any], allowed_vms: set[str], release: str, clock: Callable[[], int]
    ) -> None:
        if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+", release) is None:
            raise CollectionFailure("unsupported_api")
        self.stream, self.allowed_vms, self.release, self.clock = (
            stream,
            frozenset(allowed_vms),
            release,
            clock,
        )

    def read(self, kind: str, native_id: str, field: str) -> Any:
        ref({"type": kind, "value": native_id}, kind)
        return exchange(
            self.stream,
            f"/sdk/vim25/{self.release}/{kind}/{native_id}/{field}",
            {"vmware-api-session-id": secret(self.stream["credential_file"])},
        )

    def collect(self, vm: str) -> dict[str, Any]:
        if vm not in self.allowed_vms:
            raise CollectionFailure("permission_denied")
        records = {
            field: self.read("VirtualMachine", vm, field)
            for field in ("config", "runtime", "guest", "capability", "snapshot")
        }
        records["content"] = self.read("ServiceInstance", "ServiceInstance", "content")
        host = ref(records["runtime"].get("host"), "HostSystem")
        records["host_capability"] = self.read("HostSystem", host, "capability")
        if fingerprint(self.read("VirtualMachine", vm, "config")) != fingerprint(records["config"]):
            raise CollectionFailure("source_changed")
        return normalize(vm, self.release, records, self.clock())


def target_profile(project_id: str, records: dict[str, Any], observed_at: int) -> dict[str, Any]:
    """Normalize observed OpenStack capabilities without inferring guest/driver support.

    Callers supply the existing commissioned discovery results for the selected
    project; catalog-returned addresses never become new request destinations.
    """
    required = {
        "image_schema",
        "image_import",
        "flavors",
        "volume_types",
        "network_extensions",
        "compute_version",
        "volume_version",
    }
    if set(records) != required or not isinstance(project_id, str) or not project_id:
        raise CollectionFailure("invalid_response")
    schema = records["image_schema"]
    methods = records["image_import"].get("import-methods", {}).get("value")
    formats = schema.get("properties", {}).get("disk_format", {}).get("enum")
    holds = []
    if not isinstance(formats, list) or not formats or not all(isinstance(v, str) for v in formats):
        formats = []
        holds.append("image_formats_unobserved")
    if not isinstance(methods, list) or not all(isinstance(v, str) for v in methods):
        methods = []
        holds.append("image_import_methods_unobserved")
    flavors = records["flavors"].get("flavors")
    types = records["volume_types"].get("volume_types")
    extensions = records["network_extensions"].get("extensions")
    for response in (records["flavors"], records["volume_types"], records["network_extensions"]):
        for key, links in response.items():
            if key.endswith("links") and (
                not isinstance(links, list)
                or any(not isinstance(link, dict) or link.get("rel") == "next" for link in links)
            ):
                raise CollectionFailure("invalid_response")
    for rows in (flavors, types, extensions):
        if (
            not isinstance(rows, list)
            or len(rows) >= 100
            or not all(isinstance(v, dict) for v in rows)
        ):
            raise CollectionFailure("invalid_response")
    # These services can hide deployment choices behind policy or custom backends.
    # The API advertises what was observed, never an assumed firmware/driver tuple.
    return {
        "schema_version": 1,
        "profile_type": "TargetCapabilityProfile",
        "platform": "openstack",
        "project_id": project_id,
        "observed_at": observed_at,
        "observations_sha256": fingerprint(records),
        "disk_formats": sorted(set(formats)),
        "image_import_methods": sorted(set(methods)),
        "flavors": [
            {k: row.get(k) for k in ("id", "vcpus", "ram", "disk", "OS-FLV-EXT-DATA:ephemeral")}
            for row in flavors
        ],
        "volume_types": [
            {
                "id": row.get("id"),
                "is_public": row.get("is_public"),
                "constraints_sha256": fingerprint(row.get("extra_specs", {})),
            }
            for row in types
        ],
        "network_extensions": sorted(str(row["alias"]) for row in extensions if "alias" in row),
        "compute_version": {
            k: records["compute_version"].get(k) for k in ("min_version", "version")
        },
        "volume_version": {k: records["volume_version"].get(k) for k in ("min_version", "version")},
        "required_capability_evidence": [
            "firmware_and_device_support",
            "guest_driver_profile",
            "metadata_and_config_drive_profile",
            "security_path_qualification",
            "service_attachments",
            "capacity_and_transfer_reservations",
        ],
        "holds": holds,
        "native_qualification": "not_established",
    }
