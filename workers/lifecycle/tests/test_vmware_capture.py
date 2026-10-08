"""Synthetic VI API contract, task-loss and clone-isolation regressions."""

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from test_native import Journal
from test_native import binding as binding

from lifecycle_worker.application.native import NativeBinding, NativeHeld, digest
from lifecycle_worker.infrastructure.native_json import NativeJson
from lifecycle_worker.infrastructure.vmware_capture import VmwareCapture, disk_inventory, reference


def config() -> dict[str, Any]:
    return {
        "instanceUuid": str(uuid4()),
        "uuid": str(uuid4()),
        "guestId": "otherLinux64Guest",
        "firmware": "bios",
        "hardware": {
            "numCPU": 2,
            "memoryMB": 4096,
            "device": [
                {"_typeName": "VirtualLsiLogicController", "key": 1000, "busNumber": 0},
                {
                    "_typeName": "VirtualDisk",
                    "key": 2000,
                    "capacityInBytes": 1048576,
                    "controllerKey": 1000,
                    "unitNumber": 0,
                    "backing": {
                        "_typeName": "VirtualDiskFlatVer2BackingInfo",
                        "diskMode": "persistent",
                        "fileName": "[source] vm/disk.vmdk",
                    },
                },
                {
                    "_typeName": "VirtualVmxnet3",
                    "key": 4000,
                    "macAddress": "00:50:56:00:00:01",
                    "connectable": {
                        "connected": True,
                        "startConnected": True,
                        "allowGuestControl": True,
                    },
                },
            ],
        },
    }


class Api(NativeJson):
    def __init__(self, configuration: dict[str, Any], vcenter: str) -> None:
        self.config, self.vcenter = configuration, vcenter
        self.clone = deepcopy(configuration)
        self.clone["instanceUuid"] = str(uuid4())
        self.clone["hardware"]["device"] = self.clone["hardware"]["device"][:2]
        self.fault = ""
        self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

    def request(
        self,
        method: str,
        path: str,
        boundary: Any,
        body: dict[str, Any] | None = None,
        expected: int = 200,
    ) -> Any:
        boundary()
        self.calls.append((method, path, body))
        field = path.rsplit("/", 1)[-1]
        if field == "content":
            return {"about": {"instanceUuid": self.vcenter}}
        if "/Task/" in path:
            if self.fault == "task_scope":
                return {"entity": reference("VirtualMachine", "vm-999"), "state": "success"}
            is_snapshot = "task-snapshot" in path
            return {
                "entity": reference("VirtualMachine", "vm-1"),
                "state": "error" if self.fault == "task_failed" else "success",
                "result": reference("VirtualMachineSnapshot", "snapshot-1")
                if is_snapshot
                else reference("VirtualMachine", "vm-2"),
            }
        if field == "runtime":
            return {
                "powerState": "poweredOn" if self.fault == "power" else "poweredOff",
                "host": reference("HostSystem", "host-1"),
            }
        if field == "capability":
            return {
                "snapshotConfigSupported": self.fault != "snapshot_capability",
                "cloneFromSnapshotSupported": self.fault != "clone_capability",
            }
        if field == "vm":
            return reference("VirtualMachine", "vm-1")
        if field == "config":
            if "/vm-2/" in path:
                return self.config if self.fault == "clone_identity" else self.clone
            return self.config
        if method == "POST":
            if self.fault == "lost_task":
                raise NativeHeld("native_api_outcome_unknown")
            return reference(
                "Task", "task-snapshot" if field == "CreateSnapshotEx_Task" else "task-clone"
            )
        raise AssertionError(path)


@pytest.fixture
def capture(
    binding: NativeBinding, tmp_path: Path
) -> tuple[NativeBinding, VmwareCapture, Api, Journal]:
    c, vc = config(), str(uuid4())
    p = {
        "schema_version": 1,
        "kind": "vmware_snapshot_clone",
        "source": {
            "vm_id": "vm-1",
            "instance_uuid": c["instanceUuid"],
            "vcenter_uuid": vc,
            "api_version": "9.1.1.0",
            "config_sha256": digest(c),
        },
        "folder_id": "group-v1",
        "pool_id": "resgroup-1",
        "datastore_id": "datastore-1",
        "clone_name": "isolated-copy",
        "snapshot_name": "migration-S0",
        "max_seconds": 60,
    }
    path = tmp_path / "capture.json"
    path.write_text(json.dumps(p))
    b = replace(binding, operation_plan_sha256=digest(p))
    api, journal = Api(c, vc), Journal()
    journal.claim(b)
    return b, VmwareCapture(path, api, journal), api, journal


def test_exact_snapshot_clone_has_no_production_network(capture: Any) -> None:
    b, tool, api, journal = capture
    original = deepcopy(api.config)
    tool.execute(b, lambda: None)
    calls = [c for c in api.calls if c[0] == "POST"]
    assert [c[1].rsplit("/", 1)[-1] for c in calls] == ["CreateSnapshotEx_Task", "CloneVM_Task"]
    assert calls[0][2]["memory"] is False
    spec = calls[1][2]["spec"]
    assert spec["snapshot"] == reference("VirtualMachineSnapshot", "snapshot-1")
    assert spec["powerOn"] is False
    assert spec["config"]["deviceChange"] == [
        {"operation": "remove", "device": {"_typeName": "VirtualVmxnet3", "key": 4000}}
    ]
    assert api.config == original
    assert journal.events[-1][0] == "clone_bound"
    assert "fileName" not in json.dumps(journal.events)


@pytest.mark.parametrize(
    "fault",
    [
        "power",
        "snapshot_capability",
        "clone_capability",
        "lost_task",
        "task_scope",
        "task_failed",
        "clone_identity",
    ],
)
def test_capture_failure_never_retries_or_powers_source(capture: Any, fault: str) -> None:
    b, tool, api, journal = capture
    api.fault = fault
    with pytest.raises(NativeHeld):
        tool.execute(b, lambda: None)
    posts = [c for c in api.calls if c[0] == "POST"]
    assert len(posts) <= 2
    assert not any("PowerOn" in c[1] for c in api.calls)
    assert sum(c[1].endswith("CreateSnapshotEx_Task") for c in posts) <= 1


@pytest.mark.parametrize(
    "fault", ["rdm", "independent", "encrypted", "shared", "empty", "duplicate", "unknown_nic"]
)
def test_unsupported_disks_devices_hold(fault: str) -> None:
    c = config()
    rows = c["hardware"]["device"]
    disk = rows[1]
    if fault == "rdm":
        disk["backing"]["_typeName"] = "VirtualDiskRawDiskMappingVer1BackingInfo"
    if fault == "independent":
        disk["backing"]["diskMode"] = "independent_persistent"
    if fault == "encrypted":
        disk["backing"]["keyId"] = {"keyId": "private"}
    if fault == "shared":
        disk["backing"]["sharing"] = "sharingMultiWriter"
    if fault == "empty":
        rows.pop(1)
    if fault == "duplicate":
        rows.append(deepcopy(disk))
    if fault == "unknown_nic":
        rows[2]["_typeName"] = "UnknownNetworkDevice"
    with pytest.raises(NativeHeld):
        disk_inventory(c)
