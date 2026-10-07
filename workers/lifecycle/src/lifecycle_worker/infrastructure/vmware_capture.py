"""Single-submission vSphere snapshot and isolated exact-snapshot clone.

Uses only the commissioned VI JSON API. An uncertain task is retained for read-only
reconciliation; neither task submission nor production power-on is retried here.
"""

import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from lifecycle_worker.application.api_plan import name, shape
from lifecycle_worker.application.native import (
    NativeBinding,
    NativeHeld,
    NativeJournal,
    decode,
    digest,
)
from lifecycle_worker.infrastructure.native_copy import NativeJson
from lifecycle_worker.infrastructure.native_files import protected_read

NICS = {
    "VirtualE1000",
    "VirtualE1000e",
    "VirtualPCNet32",
    "VirtualVmxnet",
    "VirtualVmxnet2",
    "VirtualVmxnet3",
    "VirtualVmxnet3Vrdma",
    "VirtualSriovEthernetCard",
}
DISK_BACKINGS = {
    "VirtualDiskFlatVer2BackingInfo",
    "VirtualDiskSparseVer2BackingInfo",
    "VirtualDiskSeSparseBackingInfo",
}


def moref(value: Any, kind: str) -> str:
    if (
        not isinstance(value, dict)
        or value.get("type") != kind
        or not isinstance(value.get("value"), str)
        or re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,127}", value["value"]) is None
    ):
        raise NativeHeld("invalid_vmware_native_identity")
    return str(value["value"])


def reference(kind: str, value: str) -> dict[str, str]:
    moref({"type": kind, "value": value}, kind)
    return {"type": kind, "value": value}


def devices(config: dict[str, Any]) -> list[dict[str, Any]]:
    rows = config.get("hardware", {}).get("device")
    if (
        not isinstance(rows, list)
        or not 1 <= len(rows) <= 128
        or any(not isinstance(d, dict) or type(d.get("key")) is not int for d in rows)
        or len({d["key"] for d in rows}) != len(rows)
    ):
        raise NativeHeld("vmware_device_inventory_ambiguous")
    # Unknown connectable/passthrough hardware cannot silently escape clone isolation.
    for d in rows:
        kind = d.get("_typeName", "")
        if (
            ("connectable" in d or "Ethernet" in kind)
            and kind not in NICS
            and kind not in {"VirtualCdrom", "VirtualFloppy"}
        ):
            raise NativeHeld("vmware_unqualified_connectable_device")
        if kind in {"VirtualPCIPassthrough", "VirtualUSB", "VirtualTPM", "VirtualNVDIMM"}:
            raise NativeHeld("vmware_device_requires_separate_qualification")
    return list(rows)


def disk_inventory(config: dict[str, Any]) -> list[dict[str, Any]]:
    rows = devices(config)
    result = []
    for d in rows:
        if d.get("_typeName") != "VirtualDisk":
            continue
        capacity = d.get("capacityInBytes")
        if type(capacity) is not int or not 1 <= capacity <= 2**46:
            raise NativeHeld("vmware_disk_capacity_unknown")
        backing = d.get("backing")
        chain: list[str] = []
        while backing is not None:
            if (
                not isinstance(backing, dict)
                or len(chain) >= 32
                or backing.get("_typeName") not in DISK_BACKINGS
                or backing.get("diskMode") != "persistent"
                or backing.get("sharing", "sharingNone") != "sharingNone"
                or backing.get("keyId") is not None
                or not isinstance(backing.get("fileName"), str)
                or not backing["fileName"]
            ):
                raise NativeHeld("vmware_disk_backing_unqualified")
            chain.append(digest({k: v for k, v in backing.items() if k != "parent"}))
            backing = backing.get("parent")
        if not chain or len(set(chain)) != len(chain):
            raise NativeHeld("vmware_disk_chain_ambiguous")
        result.append(
            {
                "key": d["key"],
                "capacity_bytes": capacity,
                "controller_key": d.get("controllerKey"),
                "unit_number": d.get("unitNumber"),
                "backing_chain_sha256": digest(chain),
            }
        )
    if not 1 <= len(result) <= 32:
        raise NativeHeld("vmware_disk_inventory_required")
    return sorted(result, key=lambda d: d["key"])


class VmwareCapture:
    def __init__(self, plan_file: Path, api: NativeJson, journal: NativeJournal) -> None:
        self.plan_file, self.api, self.journal = plan_file, api, journal

    def plan(self, binding: NativeBinding) -> dict[str, Any]:
        p = decode(protected_read(self.plan_file, 1048576))
        shape(
            p,
            {
                "schema_version",
                "kind",
                "source",
                "folder_id",
                "pool_id",
                "datastore_id",
                "clone_name",
                "snapshot_name",
                "max_seconds",
            },
        )
        if (
            type(p["schema_version"]) is not int
            or p["schema_version"] != 1
            or p["kind"] != "vmware_snapshot_clone"
            or digest(p) != binding.operation_plan_sha256
        ):
            raise NativeHeld("vmware_capture_plan_changed")
        shape(
            p["source"], {"vm_id", "instance_uuid", "vcenter_uuid", "api_version", "config_sha256"}
        )
        source = p["source"]
        moref(reference("VirtualMachine", source["vm_id"]), "VirtualMachine")
        if not re.fullmatch(
            r"[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+", source["api_version"]
        ) or not re.fullmatch(r"[a-f0-9]{64}", source["config_sha256"]):
            raise NativeHeld("vmware_capture_version_or_digest_invalid")
        for field, kind in (
            ("folder_id", "Folder"),
            ("pool_id", "ResourcePool"),
            ("datastore_id", "Datastore"),
        ):
            reference(kind, p[field])
        for field in ("clone_name", "snapshot_name"):
            name(p[field])
        if type(p["max_seconds"]) is not int or not 1 <= p["max_seconds"] <= 600:
            raise NativeHeld("vmware_capture_deadline_invalid")
        return p

    def inspect(self, binding: NativeBinding) -> dict[str, Any]:
        return {
            "operation_plan_sha256": digest(self.plan(binding)),
            "native_write_authorized": False,
        }

    def route(self, p: dict[str, Any], kind: str, object_id: str, operation: str) -> str:
        reference(kind, object_id)
        return f"/sdk/vim25/{p['source']['api_version']}/{kind}/{object_id}/{operation}"

    def read(
        self, p: dict[str, Any], kind: str, object_id: str, field: str, boundary: Callable[[], None]
    ) -> Any:
        return self.api.request("GET", self.route(p, kind, object_id, field), boundary)

    def task(
        self,
        binding: NativeBinding,
        p: dict[str, Any],
        operation: str,
        payload: dict[str, Any],
        boundary: Callable[[], None],
    ) -> Any:
        # The outer attempt has already been durably claimed before this intent.
        self.journal.record(
            binding,
            "vmware_request_started",
            {"operation": operation, "payload_sha256": digest(payload)},
        )
        ref = self.api.request(
            "POST",
            self.route(p, "VirtualMachine", p["source"]["vm_id"], operation),
            boundary,
            payload,
        )
        task_id = moref(ref, "Task")
        self.journal.record(
            binding, "vmware_task_accepted", {"operation": operation, "task_id": task_id}
        )
        result = self.observe_task(p, task_id, boundary)
        self.journal.record(
            binding, "vmware_task_observed", {"task_id": task_id, "result_sha256": digest(result)}
        )
        return result

    def observe_task(self, p: dict[str, Any], task_id: str, boundary: Callable[[], None]) -> Any:
        while True:
            info = self.read(p, "Task", task_id, "info", boundary)
            if (
                not isinstance(info, dict)
                or moref(info.get("entity"), "VirtualMachine") != p["source"]["vm_id"]
            ):
                raise NativeHeld("vmware_task_scope_changed")
            if info.get("state") == "success":
                return info.get("result")
            if info.get("state") not in {"queued", "running"}:
                raise NativeHeld("vmware_task_not_confirmed")
            time.sleep(0.1)

    def execute(self, binding: NativeBinding, boundary: Callable[[], None]) -> None:
        p = self.plan(binding)
        deadline = time.monotonic() + p["max_seconds"]

        def current() -> None:
            if time.monotonic() >= deadline:
                raise NativeHeld("vmware_capture_deadline")
            boundary()

        vm = p["source"]["vm_id"]
        about = self.read(p, "ServiceInstance", "ServiceInstance", "content", current)
        if about.get("about", {}).get("instanceUuid") != p["source"]["vcenter_uuid"]:
            raise NativeHeld("vmware_vcenter_identity_changed")
        runtime = self.read(p, "VirtualMachine", vm, "runtime", current)
        config = self.read(p, "VirtualMachine", vm, "config", current)
        capability = self.read(p, "VirtualMachine", vm, "capability", current)
        host = moref(runtime.get("host"), "HostSystem")
        host_capability = self.read(p, "HostSystem", host, "capability", current)
        if (
            runtime.get("powerState") != "poweredOff"
            or config.get("instanceUuid") != p["source"]["instance_uuid"]
            or digest(config) != p["source"]["config_sha256"]
            or config.get("keyId") is not None
            or capability.get("snapshotConfigSupported") is not True
            or host_capability.get("cloneFromSnapshotSupported") is not True
        ):
            raise NativeHeld("vmware_capture_preconditions_unconfirmed")
        inventory = disk_inventory(config)
        snapshot_id = moref(
            self.task(
                binding,
                p,
                "CreateSnapshotEx_Task",
                {"name": p["snapshot_name"], "memory": False},
                current,
            ),
            "VirtualMachineSnapshot",
        )
        if self.read(p, "VirtualMachineSnapshot", snapshot_id, "vm", current) != reference(
            "VirtualMachine", vm
        ):
            raise NativeHeld("vmware_snapshot_owner_changed")
        snapshot_config = self.read(p, "VirtualMachineSnapshot", snapshot_id, "config", current)
        if (
            snapshot_config.get("instanceUuid") != p["source"]["instance_uuid"]
            or disk_inventory(snapshot_config) != inventory
        ):
            raise NativeHeld("vmware_snapshot_disk_inventory_changed")
        self.journal.record(
            binding,
            "snapshot_bound",
            {"snapshot_id": snapshot_id, "source_vm_id": vm, "disks_sha256": digest(inventory)},
        )
        # Removing every source NIC and removable media at clone creation avoids even
        # a transient production connection. The source device configuration is unchanged.
        remove = [
            {"operation": "remove", "device": {"_typeName": d["_typeName"], "key": d["key"]}}
            for d in devices(snapshot_config)
            if d.get("_typeName") in NICS | {"VirtualCdrom", "VirtualFloppy"}
        ]
        spec = {
            "location": {
                "pool": reference("ResourcePool", p["pool_id"]),
                "datastore": reference("Datastore", p["datastore_id"]),
                "diskMoveType": "moveAllDiskBackingsAndDisallowSharing",
            },
            "template": False,
            "powerOn": False,
            "snapshot": reference("VirtualMachineSnapshot", snapshot_id),
            "config": {"deviceChange": remove},
        }
        clone_id = moref(
            self.task(
                binding,
                p,
                "CloneVM_Task",
                {
                    "folder": reference("Folder", p["folder_id"]),
                    "name": p["clone_name"],
                    "spec": spec,
                },
                current,
            ),
            "VirtualMachine",
        )
        if clone_id == vm:
            raise NativeHeld("vmware_copy_identity_not_distinct")
        clone = self.read(p, "VirtualMachine", clone_id, "config", current)
        clone_runtime = self.read(p, "VirtualMachine", clone_id, "runtime", current)
        clone_disks = disk_inventory(clone)
        expected = [{k: v for k, v in d.items() if k != "backing_chain_sha256"} for d in inventory]
        actual = [{k: v for k, v in d.items() if k != "backing_chain_sha256"} for d in clone_disks]
        if (
            clone_runtime.get("powerState") != "poweredOff"
            or actual != expected
            or not clone.get("instanceUuid")
            or clone["instanceUuid"] == p["source"]["instance_uuid"]
            or any(d.get("_typeName") in NICS for d in devices(clone))
        ):
            raise NativeHeld("vmware_clone_isolation_or_mapping_unconfirmed")
        self.journal.record(
            binding,
            "clone_bound",
            {
                "source_vm_id": vm,
                "snapshot_id": snapshot_id,
                "clone_vm_id": clone_id,
                "clone_config_sha256": digest(clone),
                "disks_sha256": digest(clone_disks),
                "power_state": "poweredOff",
                "network_devices": 0,
            },
        )
