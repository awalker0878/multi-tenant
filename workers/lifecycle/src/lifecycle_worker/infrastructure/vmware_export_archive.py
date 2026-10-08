"""Bounded NFC archive with retained disks and final native OVF descriptor.

The source clone is resolved from the preceding capture's durable receipt in the
same approved job, never from a caller-supplied VM ID. Failed archives are retained;
resubmission needs explicit reconciliation rather than another export lease.
"""

import hashlib
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, BinaryIO, Protocol
from xml.etree import ElementTree

from lifecycle_worker.application.api_plan import shape
from lifecycle_worker.application.native import (
    NativeBinding,
    NativeHeld,
    NativeJournal,
    decode,
    digest,
    sha256,
)
from lifecycle_worker.infrastructure.migration_budget import seconds
from lifecycle_worker.infrastructure.native_files import protected_read
from lifecycle_worker.infrastructure.vmware_capture import NICS, devices, moref
from lifecycle_worker.infrastructure.vmware_export import VmwareExport

OVF = "{http://schemas.dmtf.org/ovf/envelope/1}"


class CaptureCustody(Protocol):
    def capture(self, binding: NativeBinding, plan_sha256: str) -> dict[str, Any]: ...


def validate_descriptor(descriptor: Any, files: list[dict[str, Any]]) -> bytes:
    if not isinstance(descriptor, str):
        raise NativeHeld("ovf_descriptor_missing")
    raw = descriptor.encode()
    if len(raw) > 1048576 or b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise NativeHeld("ovf_descriptor_unsafe")
    try:
        root = ElementTree.fromstring(raw)
    except ElementTree.ParseError:
        raise NativeHeld("ovf_descriptor_invalid") from None
    if root.tag != OVF + "Envelope":
        raise NativeHeld("ovf_descriptor_invalid")
    entries = root.findall(OVF + "References/" + OVF + "File")
    expected = {row["path"]: row["size"] for row in files}
    actual: dict[str, int] = {}
    ids: set[str] = set()
    for entry in entries:
        href, size, identifier = (entry.get(OVF + k) for k in ("href", "size", "id"))
        if (
            not isinstance(href, str)
            or href not in expected
            or href in actual
            or not isinstance(size, str)
            or not size.isdigit()
            or not identifier
            or identifier in ids
        ):
            raise NativeHeld("ovf_file_mapping_changed")
        actual[href] = int(size)
        ids.add(identifier)
    if actual != expected:
        raise NativeHeld("ovf_file_mapping_incomplete")
    disk_refs = [d.get(OVF + "fileRef") for d in root.findall(OVF + "DiskSection/" + OVF + "Disk")]
    if len(disk_refs) != len(ids) or set(disk_refs) != ids:
        raise NativeHeld("ovf_disk_mapping_incomplete")
    return raw


class RateBound:
    """A cumulative byte limit and rate cap with authority checks during throttling."""

    def __init__(
        self, stream: BinaryIO, rate: int, limit: int, current: Callable[[], None]
    ) -> None:
        self.stream, self.rate, self.limit, self.current = stream, rate, limit, current
        self.size, self.started = 0, time.monotonic()

    def write(self, data: bytes) -> int:
        self.current()
        self.size += len(data)
        if self.size > self.limit:
            raise NativeHeld("migration_spool_bound")
        while (delay := self.size / self.rate - (time.monotonic() - self.started)) > 0:
            self.current()
            time.sleep(min(delay, 0.1))
        return self.stream.write(data)

    def flush(self) -> None:
        self.stream.flush()
        os.fsync(self.stream.fileno())

    def seek(self, offset: int, whence: int = 0) -> int:
        return self.stream.seek(offset, whence)


class VmwareExportArchive:
    def __init__(
        self,
        plan_file: Path,
        source: VmwareExport,
        journal: NativeJournal,
        custody: CaptureCustody,
        spool: Path,
    ) -> None:
        self.plan_file, self.source, self.journal, self.custody, self.spool = (
            plan_file,
            source,
            journal,
            custody,
            spool,
        )

    def plan(self, binding: NativeBinding) -> dict[str, Any]:
        p = decode(protected_read(self.plan_file, 1048576))
        shape(
            p,
            {
                "schema_version",
                "kind",
                "capture_plan_sha256",
                "source_vm_id",
                "api_version",
                "ovf_manager_id",
                "disks",
                "max_seconds",
                "bytes_per_second",
                "spool_bytes",
            }
            | ({"range_continuation"} if "range_continuation" in p else set()),
        )
        if (
            type(p["schema_version"]) is not int
            or p["schema_version"] not in {1, 2}
            or p["kind"] != "vmware_export_archive"
            or digest(p) != binding.operation_plan_sha256
            or not sha256(p["capture_plan_sha256"])
        ):
            raise NativeHeld("migration_archive_plan_changed")
        if "range_continuation" in p and (
            p["schema_version"] != 2 or type(p["range_continuation"]) is not bool
        ):
            raise NativeHeld("migration_continuation_policy_invalid")
        # Validate the exact route before any lease can be opened.
        import re

        if not isinstance(p["api_version"], str) or not re.fullmatch(
            r"[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+", p["api_version"]
        ):
            raise NativeHeld("migration_archive_version_invalid")
        moref({"type": "OvfManager", "value": p["ovf_manager_id"]}, "OvfManager")
        moref({"type": "VirtualMachine", "value": p["source_vm_id"]}, "VirtualMachine")
        for key, minimum, maximum in (
            ("max_seconds", 1, seconds(p)),
            ("bytes_per_second", 65536, 2**34),
            ("spool_bytes", 1, 2**50),
        ):
            if type(p[key]) is not int or not minimum <= p[key] <= maximum:
                raise NativeHeld("migration_archive_budget_invalid")
        rows = p["disks"]
        if not isinstance(rows, list) or not 1 <= len(rows) <= 32:
            raise NativeHeld("migration_archive_disks_invalid")
        keys = set()
        demand = 0
        for d in rows:
            shape(d, {"key", "capacity", "max_bytes"})
            if (
                not isinstance(d["key"], str)
                or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", d["key"])
                or d["key"] in keys
            ):
                raise NativeHeld("migration_archive_mapping_ambiguous")
            keys.add(d["key"])
            for field in ("capacity", "max_bytes"):
                if type(d[field]) is not int or not 1 <= d[field] <= 2**46:
                    raise NativeHeld("migration_archive_budget_invalid")
            demand += d["max_bytes"]
        if demand > p["spool_bytes"]:
            raise NativeHeld("migration_spool_reservation_insufficient")
        if (
            not self.spool.is_absolute()
            or any(q.is_symlink() for q in (self.spool, *self.spool.parents))
            or not self.spool.is_dir()
            or self.spool.stat().st_mode & 0o077
        ):
            raise NativeHeld("private_native_spool_required")
        return p

    def inspect(self, binding: NativeBinding) -> dict[str, Any]:
        p = self.plan(binding)
        return {
            "operation_plan_sha256": digest(p),
            "disk_count": len(p["disks"]),
            "native_write_authorized": False,
        }

    def execute(self, binding: NativeBinding, boundary: Callable[[], None]) -> None:
        p = self.plan(binding)
        deadline = time.monotonic() + p["max_seconds"]

        def current() -> None:
            if time.monotonic() >= deadline:
                raise NativeHeld("migration_archive_deadline")
            boundary()

        current()
        capture = self.custody.capture(binding, p["capture_plan_sha256"])
        if (
            capture.get("source_vm_id") != p["source_vm_id"]
            or capture.get("clone_vm_id") == p["source_vm_id"]
            or type(capture.get("network_devices")) is not int
            or capture["network_devices"] != 0
            or capture.get("power_state") != "poweredOff"
            or not sha256(capture.get("clone_config_sha256"))
        ):
            raise NativeHeld("migration_capture_receipt_invalid")
        clone = moref(
            {"type": "VirtualMachine", "value": capture.get("clone_vm_id")}, "VirtualMachine"
        )
        resolved = {
            "source": {
                "vm_id": clone,
                "config_sha256": capture["clone_config_sha256"],
                "api_version": p["api_version"],
            }
        }
        config = self.source.api.request(
            "GET", self.source.path(resolved, "VirtualMachine", clone, "config"), current
        )
        if any(d.get("_typeName") in NICS for d in devices(config)):
            raise NativeHeld("migration_copy_network_not_isolated")
        directory = self.spool / binding.operation_id
        directory.mkdir(mode=0o700)  # Existing custody is a hold, never truncation/restart.
        parent = os.open(self.spool, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)
        self.journal.record(
            binding, "request_started", {"kind": "export", "capture_sha256": digest(capture)}
        )
        lease = self.source.start(resolved, current)
        self.journal.record(
            binding,
            "export_lease",
            {"lease_id": lease, "clone_vm_id": clone, "capture_sha256": digest(capture)},
        )
        info = self.source.ready(resolved, lease, current)
        urls = [d for d in info.get("deviceUrl", []) if d.get("disk") is True]
        devices_by_key = {d["key"]: d for d in urls}
        if len(devices_by_key) != len(urls) or set(devices_by_key) != {
            d["key"] for d in p["disks"]
        }:
            raise NativeHeld("export_disk_inventory_changed")
        renewed = 0.0
        transferred = 0

        def heartbeat() -> None:
            nonlocal renewed
            current()
            if time.monotonic() - renewed >= min(5, info["leaseTimeout"] / 3):
                self.source.call(
                    resolved,
                    lease,
                    "HttpNfcLeaseProgress",
                    current,
                    {"percent": min(99, transferred * 100 // p["spool_bytes"])},
                )
                renewed = time.monotonic()

        receipts: dict[str, dict[str, Any]] = {}
        files = []
        for disk in p["disks"]:
            filename = disk["key"] + ".vmdk"
            with (directory / filename).open("x+b") as stream:
                stream_bound = RateBound(
                    stream, p["bytes_per_second"], disk["max_bytes"], heartbeat
                )
                # VmwareExport's download accepts a seekable write sink; the wrapper
                # checks rate/custody before every write and fsyncs on completion.
                if p.get("range_continuation") is True:

                    def continuation(facts: dict[str, Any], key: str = disk["key"]) -> None:
                        current()
                        self.journal.record(
                            binding, "transfer_continued", {"resource_key": key, **facts}
                        )

                    receipt = self.source.download(
                        devices_by_key[disk["key"]]["url"],
                        disk["max_bytes"],
                        stream_bound,
                        heartbeat,
                        allow_range_continuation=True,
                        on_continuation=continuation,
                    )
                else:
                    receipt = self.source.download(
                        devices_by_key[disk["key"]]["url"],
                        disk["max_bytes"],
                        stream_bound,
                        heartbeat,
                    )
            transferred += receipt["size"]
            receipts[disk["key"]] = receipt
            files.append(
                {
                    "deviceId": disk["key"],
                    "path": filename,
                    "size": receipt["size"],
                    "capacity": disk["capacity"],
                }
            )
            self.journal.record(
                binding,
                "transfer_progress",
                {
                    "resource_key": disk["key"],
                    "bytes": receipt["size"],
                    "sha256": receipt["sha256"],
                },
            )
        manifest = self.source.call(resolved, lease, "HttpNfcLeaseGetManifest", current)
        if not isinstance(manifest, list) or len(manifest) != len(receipts):
            raise NativeHeld("export_manifest_inventory_changed")
        entries = {d["key"]: d for d in manifest if d.get("disk") is True}
        if set(entries) != set(receipts) or len(entries) != len(manifest):
            raise NativeHeld("export_manifest_inventory_changed")
        for disk in p["disks"]:
            entry, receipt = entries[disk["key"]], receipts[disk["key"]]
            algorithm = entry.get("checksumType")
            if (
                algorithm not in {"sha256", "sha512"}
                or entry.get("checksum") != receipt[algorithm]
                or type(entry.get("size")) is not int
                or entry["size"] != receipt["size"]
                or type(entry.get("capacity")) is not int
                or entry["capacity"] != disk["capacity"]
            ):
                raise NativeHeld("export_manifest_integrity_failed")
            self.journal.record(
                binding, "disk_transferred", {"resource_key": disk["key"], **receipt}
            )
        descriptor = self.source.api.request(
            "POST",
            self.source.path(resolved, "OvfManager", p["ovf_manager_id"], "CreateDescriptor"),
            current,
            {"obj": {"type": "VirtualMachine", "value": clone}, "cdp": {"ovfFiles": files}},
        )
        if not isinstance(descriptor, dict) or descriptor.get("error") or descriptor.get("warning"):
            raise NativeHeld("ovf_descriptor_findings_unresolved")
        raw = validate_descriptor(descriptor.get("ovfDescriptor"), files)
        with (directory / "machine.ovf").open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        self.journal.record(
            binding,
            "ovf_retained",
            {
                "descriptor_sha256": hashlib.sha256(raw).hexdigest(),
                "files_sha256": digest(files),
                "capture_sha256": digest(capture),
            },
        )
        self.source.call(resolved, lease, "HttpNfcLeaseComplete", current)
        self.journal.record(
            binding,
            "export_complete",
            {
                "lease_id": lease,
                "manifest_sha256": digest(manifest),
                "descriptor_sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": transferred,
                "disks_sha256": digest(receipts),
            },
        )
