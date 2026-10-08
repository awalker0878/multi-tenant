"""Retained NFC/OVF custody; synthetic byte stream and native descriptor responses."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from test_native import Journal
from test_native import binding as binding
from test_native_copy import copy_campaign as copy_campaign
from test_vmware_capture import config

from lifecycle_worker.application.native import NativeBinding, NativeHeld, digest
from lifecycle_worker.infrastructure.migration_archive import MigrationArchive, validate_descriptor
from lifecycle_worker.infrastructure.native_copy import DownloadSink, NativeVmCopy, VmwareExport


def ovf(size: int) -> str:
    return (
        '<Envelope xmlns="http://schemas.dmtf.org/ovf/envelope/1" '
        'xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1"><References>'
        f'<File ovf:id="f1" ovf:href="disk-2000.vmdk" ovf:size="{size}"/>'
        '</References><DiskSection><Disk ovf:diskId="d1" ovf:fileRef="f1" '
        'ovf:capacity="1048576"/></DiskSection></Envelope>'
    )


class Source(VmwareExport):
    def __init__(self) -> None:
        self.configuration = config()
        self.configuration["hardware"]["device"] = self.configuration["hardware"]["device"][:2]
        self.api: Any = self
        self.calls: list[str] = []
        self.data = b"synthetic-vmdk" * 128
        self.fault = ""

    def request(self, method: str, path: str, boundary: Any, body: Any = None) -> Any:
        boundary()
        self.calls.append(path)
        if path.endswith("/config"):
            return self.configuration
        assert path.endswith("/CreateDescriptor")
        assert body["obj"]["value"] == "vm-2"
        assert body["cdp"]["ovfFiles"] == [
            {
                "deviceId": "disk-2000",
                "path": "disk-2000.vmdk",
                "size": len(self.data),
                "capacity": 1048576,
            }
        ]
        return {
            "ovfDescriptor": ovf(len(self.data)),
            "warning": ["unresolved"] if self.fault == "warning" else [],
            "error": [],
        }

    def start(self, plan: dict[str, Any], boundary: Any) -> str:
        boundary()
        assert plan["source"]["vm_id"] == "vm-2"
        assert plan["source"]["config_sha256"] == digest(self.configuration)
        self.calls.append("ExportVm")
        return "lease-1"

    def ready(self, plan: dict[str, Any], lease: str, boundary: Any) -> dict[str, Any]:
        boundary()
        return {
            "leaseTimeout": 60,
            "deviceUrl": [
                {"key": "disk-2000", "disk": True, "url": "https://native.invalid/scoped-ticket"}
            ],
        }

    def download(
        self,
        url: str,
        limit: int,
        target: DownloadSink,
        heartbeat: Any,
        *,
        allow_range_continuation: bool = False,
        on_continuation: Any = None,
    ) -> dict[str, Any]:
        heartbeat()
        target.write(self.data)
        target.flush()
        if self.fault == "lost_stream":
            raise NativeHeld("native_export_outcome_unknown")
        return {
            "size": len(self.data),
            "sha256": hashlib.sha256(self.data).hexdigest(),
            "sha512": hashlib.sha512(self.data).hexdigest(),
        }

    def call(
        self, plan: dict[str, Any], lease: str, operation: str, boundary: Any, body: Any = None
    ) -> Any:
        boundary()
        self.calls.append(operation)
        if operation == "HttpNfcLeaseGetManifest":
            return [
                {
                    "key": "disk-2000",
                    "disk": True,
                    "size": len(self.data),
                    "capacity": 1048576,
                    "checksumType": "sha256",
                    "checksum": "a" * 64
                    if self.fault == "manifest"
                    else hashlib.sha256(self.data).hexdigest(),
                }
            ]
        return None


@pytest.fixture
def archive(
    binding: NativeBinding, tmp_path: Path
) -> tuple[NativeBinding, MigrationArchive, Source, Journal]:
    source = Source()

    class Custody:
        def capture(self, b: NativeBinding, plan_sha256: str) -> dict[str, Any]:
            assert plan_sha256 == digest("capture")
            return {
                "source_vm_id": "vm-1",
                "clone_vm_id": "vm-2",
                "clone_config_sha256": digest(source.configuration),
                "snapshot_id": "snapshot-1",
                "network_devices": 0,
                "power_state": "poweredOff",
            }

    p = {
        "schema_version": 1,
        "kind": "vmware_export_archive",
        "capture_plan_sha256": digest("capture"),
        "source_vm_id": "vm-1",
        "api_version": "9.1.1.0",
        "ovf_manager_id": "OvfManager",
        "disks": [{"key": "disk-2000", "capacity": 1048576, "max_bytes": 1048576}],
        "max_seconds": 60,
        "bytes_per_second": 2**30,
        "spool_bytes": 1048576,
    }
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(p))
    spool = tmp_path / "spool"
    spool.mkdir(mode=0o700)
    b = replace(binding, operation_plan_sha256=digest(p))
    journal = Journal()
    journal.claim(b)
    return b, MigrationArchive(plan_file, source, journal, Custody(), spool), source, journal


def test_descriptor_precedes_completion_and_archive_is_retained(archive: Any) -> None:
    b, tool, source, journal = archive
    tool.execute(b, lambda: None)
    folder = tool.spool / b.operation_id
    assert (folder / "disk-2000.vmdk").read_bytes() == source.data
    assert (folder / "machine.ovf").read_text() == ovf(len(source.data))
    assert source.calls[-1] == "HttpNfcLeaseComplete"
    assert source.calls[-2].endswith("CreateDescriptor")
    assert journal.events[-1][0] == "export_complete"
    assert "scoped-ticket" not in str(journal.events)
    count = len(source.calls)
    with pytest.raises(FileExistsError):
        tool.execute(b, lambda: None)
    assert source.calls[count:] == [source.calls[0]]  # read only; no second lease


@pytest.mark.parametrize("fault", ["lost_stream", "warning", "manifest"])
def test_failed_archive_retains_bytes_without_completing_lease(archive: Any, fault: str) -> None:
    b, tool, source, journal = archive
    source.fault = fault
    with pytest.raises(NativeHeld):
        tool.execute(b, lambda: None)
    assert (tool.spool / b.operation_id / "disk-2000.vmdk").read_bytes() == source.data
    assert "HttpNfcLeaseComplete" not in source.calls
    assert source.calls.count("ExportVm") == 1


@pytest.mark.parametrize(
    "fault", ["traversal", "length", "missing", "duplicate", "entity", "disk_reference"]
)
def test_ovf_mapping_ambiguity_denied(fault: str) -> None:
    descriptor = ovf(99)
    if fault == "traversal":
        descriptor = descriptor.replace("disk-2000.vmdk", "../disk-2000.vmdk")
    if fault == "length":
        descriptor = descriptor.replace('ovf:size="99"', 'ovf:size="98"')
    if fault == "missing":
        descriptor = descriptor.replace("<File ", "<Missing ")
    if fault == "duplicate":
        descriptor = descriptor.replace(
            "</References>",
            '<File ovf:id="f2" ovf:href="disk-2000.vmdk" ovf:size="99"/></References>',
        )
    if fault == "entity":
        descriptor = '<!DOCTYPE Envelope [<!ENTITY e SYSTEM "file:///private">]>' + descriptor
    if fault == "disk_reference":
        descriptor = descriptor.replace('ovf:fileRef="f1"', 'ovf:fileRef="wrong"')
    with pytest.raises(NativeHeld):
        validate_descriptor(descriptor, [{"path": "disk-2000.vmdk", "size": 99}])


@pytest.mark.parametrize("continuation", [False, True])
def test_retained_archive_over_real_tls(
    copy_campaign: Any, tmp_path: Path, continuation: bool
) -> None:
    b, execution, fixture, journal = copy_campaign
    old = execution.adapter
    assert isinstance(old, NativeVmCopy)
    copy = json.loads(old.plan_file.read_text())

    class Custody:
        def capture(self, binding: NativeBinding, plan_sha256: str) -> dict[str, Any]:
            return {
                "source_vm_id": "vm-99",
                "clone_vm_id": copy["source"]["vm_id"],
                "clone_config_sha256": copy["source"]["config_sha256"],
                "snapshot_id": "snapshot-1",
                "network_devices": 0,
                "power_state": "poweredOff",
            }

    p = {
        "schema_version": 1,
        "kind": "vmware_export_archive",
        "capture_plan_sha256": digest("capture"),
        "source_vm_id": "vm-99",
        "api_version": copy["source"]["api_version"],
        "ovf_manager_id": "OvfManager",
        "disks": [{k: d[k] for k in ("key", "capacity", "max_bytes")} for d in copy["disks"]],
        "max_seconds": 60,
        "bytes_per_second": 2**30,
        "spool_bytes": 1048576,
    }
    if continuation:
        p.update(schema_version=2, range_continuation=True)
        fixture["range_fault"] = "continue"
    plan_file = tmp_path / "archive.json"
    plan_file.write_text(json.dumps(p))
    bound = replace(b, operation_plan_sha256=digest(p))
    journal.claim(bound)
    tool = MigrationArchive(plan_file, old.source, journal, Custody(), old.spool)
    tool.execute(bound, lambda: None)
    assert (old.spool / bound.operation_id / "machine.ovf").is_file()
    paths = [r["path"].rsplit("/", 1)[-1] for r in fixture["calls"]]
    assert paths.index("CreateDescriptor") < paths.index("HttpNfcLeaseComplete")
    assert journal.events[-1][0] == "export_complete"
    assert sum(kind == "transfer_continued" for kind, _ in journal.events) == int(continuation)
    assert paths.count("ExportVm") == 1
