"""Cold AHV disk capture through v4.3 image creation from immutable VM disks.

All disks are captured while the source remains OFF. Shared/external disks and
passthrough/key-bearing devices require their own route qualification. Native
task acceptance is retained before polling and uncertain submissions are held.
"""



import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

from lifecycle_worker.application.api_plan import shape
from lifecycle_worker.application.native import (
    NativeBinding,
    NativeHeld,
    decode,
    digest,
    identity,
    sha256,
)
from lifecycle_worker.infrastructure.ahv_http import COLLECTIONS, AhvTransport, read
from lifecycle_worker.infrastructure.ahv_source_contract import configuration
from lifecycle_worker.infrastructure.ahv_tasks import AhvJournal, completed, submit
from lifecycle_worker.infrastructure.migration_budget import seconds
from lifecycle_worker.infrastructure.native_files import protected_read


MIGRATION_API_CAPABILITIES = frozenset({"vm.disk.export"})


def validate(p: dict[str, Any], binding: NativeBinding) -> dict[str, Any]:
    shape(
        p,
        {
            "schema_version",
            "kind",
            "method",
            "source_project_id",
            "source_vm_id",
            "cluster_id",
            "source_profile_sha256",
            "vm_sha256",
            "disks",
            "max_seconds",
        },
    )
    if (
        type(p["schema_version"]) is not int
        or p["schema_version"] != 2
        or p["kind"] != "ahv_capture"
        or p["method"] != "VM_COLD_EXPORT"
        or digest(p) != binding.operation_plan_sha256
        or not sha256(p["source_profile_sha256"])
        or not sha256(p["vm_sha256"])
    ):
        raise NativeHeld("ahv_capture_plan_changed")
    for field in ("source_project_id", "source_vm_id", "cluster_id"):
        identity(p[field])
    seconds(p)
    if not isinstance(p["disks"], list) or not 1 <= len(p["disks"]) <= 32:
        raise NativeHeld("ahv_capture_disks_invalid")
    keys, ids = set(), set()
    for disk in p["disks"]:
        shape(disk, {"key", "disk_id", "source_sha256", "virtual_bytes", "export_format"})
        if (
            not isinstance(disk["key"], str)
            or re.fullmatch(r"[A-Za-z0-9_-]{1,80}", disk["key"]) is None
            or disk["key"] in keys
            or disk["disk_id"] in ids
            or not sha256(disk["source_sha256"])
            or disk["export_format"] not in {"raw", "qcow2"}
            or type(disk["virtual_bytes"]) is not int
            or not 512 <= disk["virtual_bytes"] <= 2**46
        ):
            raise NativeHeld("ahv_capture_disks_invalid")
        keys.add(disk["key"])
        ids.add(identity(disk["disk_id"]))
    return p


def source_vm(api: AhvTransport, p: dict[str, Any], current: Callable[[], None]) -> dict[str, Any]:
    vm = read(api, COLLECTIONS["server"] + "/" + p["source_vm_id"], current)
    if any(not isinstance(vm.get(k, {}), dict) for k in ("project", "cluster", "bootConfig")):
        raise NativeHeld("ahv_source_configuration_unconfirmed")
    if (
        vm.get("extId") != p["source_vm_id"]
        or vm.get("powerState") != "OFF"
        or vm.get("projectExtId", vm.get("project", {}).get("extId")) != p["source_project_id"]
        or vm.get("project", {}).get("extId", p["source_project_id"]) != p["source_project_id"]
        or vm.get("cluster", {}).get("extId") != p["cluster_id"]
        or digest(configuration("vm", vm)) != p["vm_sha256"]
    ):
        raise NativeHeld("ahv_source_not_stopped_or_changed")
    if (
        any(vm.get(k) for k in ("gpus", "pcieDevices", "vtpmConfig"))
        or vm.get("bootConfig", {}).get("isSecureBootEnabled") is True
    ):
        raise NativeHeld("ahv_source_device_unqualified")
    disks = vm.get("disks")
    if (
        not isinstance(disks, list)
        or len(disks) != len(p["disks"])
        or any(not isinstance(d, dict) or not isinstance(d.get("extId"), str) for d in disks)
        or {d.get("extId") for d in disks} != {d["disk_id"] for d in p["disks"]}
    ):
        raise NativeHeld("ahv_source_disk_inventory_changed")
    for wanted in p["disks"]:
        disk = next(d for d in disks if d["extId"] == wanted["disk_id"])
        backing = disk.get("backingInfo", {})
        if (
            digest(disk) != wanted["source_sha256"]
            or not isinstance(backing, dict)
            or backing.get("$objectType") != "vmm.v4.ahv.config.VmDisk"
            or backing.get("diskSizeBytes") != wanted["virtual_bytes"]
        ):
            raise NativeHeld("ahv_source_disk_changed")
    return vm


def image_facts(row: dict[str, Any], capture: dict[str, Any], key: str) -> dict[str, Any]:
    disk = capture["disks"][key]
    sources = [d for d in capture["source_disks"] if d["key"] == key]
    if len(sources) != 1:
        raise NativeHeld("ahv_capture_disk_mapping_changed")
    source = sources[0]
    checksum = row.get("checksum", {})
    if not isinstance(checksum, dict) or not isinstance(row.get("source"), dict):
        raise NativeHeld("ahv_capture_image_unconfirmed")
    if (
        row.get("extId") != disk["image_id"]
        or row.get("name") != disk["name"]
        or row.get("description") != capture["marker"]
        or row.get("type") != "DISK_IMAGE"
        or row.get("projectExtId") != capture["source_project_id"]
        or row.get("isSharedWithAllProjects") is not False
        or row.get("clusterLocationExtIds") != [capture["cluster_id"]]
        or row.get("source", {}).get("$objectType") != "vmm.v4.content.VmDiskSource"
        or row.get("source", {}).get("extId") != source["disk_id"]
        or row.get("source", {}).get("vmExtId") != capture["source_vm_id"]
        or checksum.get("$objectType") != "vmm.v4.content.ImageSha256Checksum"
        or not sha256(checksum.get("hexDigest"))
        or type(row.get("sizeBytes")) is not int
        or not 0 < row["sizeBytes"] <= 2**46
        or disk["format"] == "raw"
        and row["sizeBytes"] != source["virtual_bytes"]
    ):
        raise NativeHeld("ahv_capture_image_unconfirmed")
    return {
        "image_id": row["extId"],
        "name": row["name"],
        "format": disk["format"],
        "size": row["sizeBytes"],
        "checksum_algorithm": "sha256",
        "checksum": checksum["hexDigest"],
    }


def capture_receipt(p: dict[str, Any], binding: NativeBinding) -> dict[str, Any]:
    return {
        "source_platform": "ahv",
        "consistency": "cold_powered_off",
        **{k: p[k] for k in ("source_project_id", "source_vm_id", "cluster_id", "vm_sha256")},
        "marker": "migration:" + binding.fingerprint,
        "disks": {},
        "source_disks": p["disks"],
    }


def reconcile_capture(
    plan: dict[str, Any],
    binding: NativeBinding,
    api: AhvTransport,
    journal: AhvJournal,
    boundary: Callable[[], None],
) -> dict[str, Any]:
    """Recover custody after interrupted polling using native reads only.

    Every source disk needs a retained accepted task. A lost POST response or a
    partially submitted capture therefore cannot silently become a new capture.
    """
    p = validate(plan, binding)
    deadline = time.monotonic() + seconds(p)

    def current() -> None:
        boundary()
        if time.monotonic() >= deadline or digest(plan) != binding.operation_plan_sha256:
            raise NativeHeld("ahv_capture_deadline_or_plan_changed")

    tasks, resources = journal.ahv_tasks(binding), journal.resources(binding)
    keys = {disk["key"] for disk in p["disks"]}
    if set(tasks) != keys or not set(resources) <= keys:
        raise NativeHeld("ahv_capture_tasks_incomplete")
    source_vm(api, p, current)
    capture = capture_receipt(p, binding)
    for disk in p["disks"]:
        key = disk["key"]
        task = tasks[key]
        if (
            task.get("resource_key") != key
            or task.get("kind") != "image"
            or task.get("request_id") != str(uuid5(UUID(binding.operation_id), key))
        ):
            raise NativeHeld("ahv_capture_task_binding_changed")
        native_id = completed(api, task, current)
        if native_id is None:
            raise NativeHeld("ahv_capture_task_incomplete")
        if key in resources and resources[key] != {"kind": "image", "id": native_id}:
            raise NativeHeld("ahv_capture_task_object_changed")
        capture["disks"][key] = {
            "image_id": native_id,
            "name": "migration-" + binding.operation_id + "-" + key,
            "format": disk["export_format"],
        }
        row = read(api, COLLECTIONS["image"] + "/" + native_id, current)
        capture["disks"][key] = image_facts(row, capture, key) | {
            "virtual_bytes": disk["virtual_bytes"]
        }
        if key not in resources:
            journal.record(
                binding,
                "request_accepted",
                {
                    "resource_key": key,
                    "kind": "image",
                    "native_id": native_id,
                    "task_id": task["task_id"],
                    "request_id": task["request_id"],
                },
            )
    source_vm(api, p, current)
    journal.record(binding, "source_capture_bound", capture)
    return capture


class AhvCapture:
    def __init__(
        self, plan_file: Path, api: AhvTransport, journal: AhvJournal, interval: float = 1
    ) -> None:
        if not 0 <= interval <= 5:
            raise NativeHeld("invalid_ahv_poll_interval")
        self.plan_file, self.api, self.journal, self.interval = plan_file, api, journal, interval

    def plan(self, binding: NativeBinding) -> dict[str, Any]:
        return validate(decode(protected_read(self.plan_file, 1048576)), binding)

    def inspect(self, binding: NativeBinding) -> dict[str, Any]:
        return {
            "operation_plan_sha256": digest(self.plan(binding)),
            "native_write_authorized": False,
        }

    def reconcile_capture(
        self, binding: NativeBinding, boundary: Callable[[], None]
    ) -> dict[str, Any]:
        return reconcile_capture(self.plan(binding), binding, self.api, self.journal, boundary)

    def execute(self, binding: NativeBinding, boundary: Callable[[], None]) -> None:
        p = self.plan(binding)
        deadline = time.monotonic() + seconds(p)

        def current() -> None:
            boundary()
            if (
                time.monotonic() >= deadline
                or digest(self.plan(binding)) != binding.operation_plan_sha256
            ):
                raise NativeHeld("ahv_capture_deadline_or_plan_changed")

        if self.journal.resources(binding) or self.journal.ahv_tasks(binding):
            raise NativeHeld("ahv_capture_requires_reconciliation")
        source_vm(self.api, p, current)
        capture = capture_receipt(p, binding)
        for disk in p["disks"]:
            source_vm(self.api, p, current)
            key = disk["key"]
            name = "migration-" + binding.operation_id + "-" + key
            body = {
                "name": name,
                "description": capture["marker"],
                "type": "DISK_IMAGE",
                "source": {
                    "$objectType": "vmm.v4.content.VmDiskSource",
                    "extId": disk["disk_id"],
                    "vmExtId": p["source_vm_id"],
                },
                "projectExtId": p["source_project_id"],
                "isSharedWithAllProjects": False,
                "clusterLocationExtIds": [p["cluster_id"]],
            }
            image_id = submit(
                self.api, self.journal, binding, key, "image", body, current, self.interval
            )
            capture["disks"][key] = {
                "image_id": image_id,
                "name": name,
                "format": disk["export_format"],
            }
            row = read(self.api, COLLECTIONS["image"] + "/" + image_id, current)
            capture["disks"][key] = image_facts(row, capture, key) | {
                "virtual_bytes": disk["virtual_bytes"]
            }
        source_vm(self.api, p, current)
        self.journal.record(binding, "source_capture_bound", capture)
