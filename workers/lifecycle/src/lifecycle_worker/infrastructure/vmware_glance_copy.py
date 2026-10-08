"""Vmware glance copy; platform mechanisms retain native semantics."""

import re
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, BinaryIO

from lifecycle_worker.application.api_plan import name, shape
from lifecycle_worker.application.native import (
    NativeBinding,
    NativeHeld,
    NativeJournal,
    decode,
    digest,
    identity,
    sha256,
)
from lifecycle_worker.infrastructure.native_files import protected_read
from lifecycle_worker.infrastructure.openstack_image_transport import GlanceImport
from lifecycle_worker.infrastructure.vmware_export import VmwareExport


def copy_plan(document: dict[str, Any], binding: NativeBinding) -> dict[str, Any]:
    shape(
        document,
        {
            "schema_version",
            "method",
            "project_id",
            "ownership_digest",
            "custody_id",
            "custody_generation",
            "source",
            "disks",
            "max_seconds",
        },
    )
    if (
        type(document["schema_version"]) is not int
        or document["schema_version"] != 1
        or document["method"] != "native_api_export_import"
        or digest(document) != binding.operation_plan_sha256
    ):
        raise NativeHeld("invalid_native_copy_plan")
    for key in ("project_id", "ownership_digest", "custody_id", "custody_generation"):
        if digest(document[key]) != digest(binding.document()[key]):
            raise NativeHeld("native_copy_scope_changed")
    source = document["source"]
    shape(source, {"vm_id", "api_version", "config_sha256"})
    if (
        not isinstance(source["vm_id"], str)
        or re.fullmatch(r"vm-[1-9][0-9]*", source["vm_id"]) is None
        or not isinstance(source["api_version"], str)
        or re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+", source["api_version"]) is None
        or not sha256(source["config_sha256"])
    ):
        raise NativeHeld("invalid_native_copy_source")
    if type(document["max_seconds"]) is not int or not 1 <= document["max_seconds"] <= 86400:
        raise NativeHeld("invalid_native_copy_deadline")
    disks = document["disks"]
    if not isinstance(disks, list) or not 1 <= len(disks) <= 32:
        raise NativeHeld("invalid_native_copy_disks")
    keys: set[str] = set()
    images: set[str] = set()
    for disk in disks:
        shape(
            disk,
            {"key", "capacity", "max_bytes", "image_id", "name", "hw_firmware_type", "hw_disk_bus"},
        )
        name(disk["key"])
        name(disk["name"])
        identity(disk["image_id"])
        if (
            disk["key"] in keys
            or disk["image_id"] in images
            or type(disk["capacity"]) is not int
            or not 1 <= disk["capacity"] <= 2**46
            or type(disk["max_bytes"]) is not int
            or not 1 <= disk["max_bytes"] <= 2**46
            or disk["hw_firmware_type"] not in {"bios", "uefi"}
            or disk["hw_disk_bus"] not in {"scsi", "virtio", "ide"}
        ):
            raise NativeHeld("invalid_native_copy_disk_mapping")
        keys.add(disk["key"])
        images.add(disk["image_id"])
    return document


class NativeVmCopy:
    def __init__(
        self,
        plan_file: Path,
        source: VmwareExport,
        destination: GlanceImport,
        journal: NativeJournal,
        spool: Path,
    ) -> None:
        self.plan_file, self.source, self.destination, self.journal, self.spool = (
            plan_file,
            source,
            destination,
            journal,
            spool,
        )

    def inspect(self, binding: NativeBinding) -> dict[str, Any]:
        plan = copy_plan(decode(protected_read(self.plan_file, 1048576)), binding)
        if (
            not self.spool.is_absolute()
            or self.spool.is_symlink()
            or not self.spool.is_dir()
            or self.spool.stat().st_mode & 0o077
        ):
            raise NativeHeld("private_native_spool_required")
        return {
            "operation_plan_sha256": digest(plan),
            "disk_count": len(plan["disks"]),
            "native_write_authorized": False,
        }

    def execute(self, binding: NativeBinding, boundary: Callable[[], None]) -> None:
        plan = copy_plan(decode(protected_read(self.plan_file, 1048576)), binding)
        deadline = time.monotonic() + plan["max_seconds"]

        def current() -> None:
            if time.monotonic() >= deadline:
                raise NativeHeld("native_copy_deadline")
            boundary()

        self.destination.preflight(binding, current)
        self.journal.record(
            binding, "request_started", {"kind": "export", "source_sha256": digest(plan["source"])}
        )
        lease = self.source.start(plan, current)
        self.journal.record(
            binding, "export_lease", {"lease_id": lease, "source_sha256": digest(plan["source"])}
        )
        info = self.source.ready(plan, lease, current)
        devices = {row["key"]: row for row in info.get("deviceUrl", []) if row.get("disk") is True}
        if set(devices) != {disk["key"] for disk in plan["disks"]} or len(devices) != sum(
            row.get("disk") is True for row in info.get("deviceUrl", [])
        ):
            raise NativeHeld("export_disk_inventory_changed")
        renewed = 0.0

        def heartbeat() -> None:
            nonlocal renewed
            current()
            if time.monotonic() - renewed >= min(5, info["leaseTimeout"] / 3):
                self.source.call(plan, lease, "HttpNfcLeaseProgress", current, {"percent": 0})
                renewed = time.monotonic()

        streams: dict[str, BinaryIO] = {}
        receipts: dict[str, dict[str, Any]] = {}
        try:
            for disk in plan["disks"]:
                stream = tempfile.TemporaryFile(mode="w+b", dir=self.spool)
                streams[disk["key"]] = stream
                receipts[disk["key"]] = self.source.download(
                    devices[disk["key"]]["url"], disk["max_bytes"], stream, heartbeat
                )
            manifest = self.source.call(plan, lease, "HttpNfcLeaseGetManifest", current)
            if not isinstance(manifest, list):
                raise NativeHeld("export_manifest_missing")
            entries = {row["key"]: row for row in manifest if row.get("disk") is True}
            if len(entries) != len(manifest) or set(entries) != set(receipts):
                raise NativeHeld("export_manifest_inventory_changed")
            for disk in plan["disks"]:
                entry, receipt = entries[disk["key"]], receipts[disk["key"]]
                algorithm = entry.get("checksumType")
                if (
                    algorithm not in {"sha256", "sha512"}
                    or entry.get("checksum") != receipt[algorithm]
                    or entry.get("size") != receipt["size"]
                    or entry.get("capacity") != disk["capacity"]
                ):
                    raise NativeHeld("export_manifest_integrity_failed")
                self.journal.record(
                    binding, "disk_transferred", {"resource_key": disk["key"], **receipt}
                )
            self.source.call(plan, lease, "HttpNfcLeaseComplete", current)
            self.journal.record(
                binding, "export_complete", {"lease_id": lease, "manifest_sha256": digest(manifest)}
            )
            for disk in plan["disks"]:
                current()
                self.journal.record(
                    binding,
                    "request_started",
                    {"resource_key": disk["key"], "kind": "image", "payload_sha256": digest(disk)},
                )
                image = self.destination.create(binding, disk, current)
                self.journal.record(
                    binding,
                    "request_accepted",
                    {
                        "resource_key": disk["key"],
                        "kind": "image",
                        "native_id": disk["image_id"],
                        "response_sha256": digest(image),
                    },
                )
                self.destination.stage(
                    binding, disk, streams[disk["key"]], receipts[disk["key"]], current
                )
                self.destination.finish(binding, disk, receipts[disk["key"]], current)
                self.journal.record(
                    binding,
                    "poll_observed",
                    {
                        "resource_key": disk["key"],
                        "native_id": disk["image_id"],
                        "status": "active",
                        **receipts[disk["key"]],
                    },
                )
        finally:
            for opened in streams.values():
                opened.close()
