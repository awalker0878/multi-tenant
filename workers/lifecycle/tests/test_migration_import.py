"""Glance-direct import of retained synthetic converted bytes over actual TLS."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from test_native import binding as binding
from test_native_copy import copy_campaign as copy_campaign

from lifecycle_worker.application.native import NativeHeld, digest
from lifecycle_worker.infrastructure.openstack_image_import import OpenStackImageImport
from lifecycle_worker.infrastructure.vmware_glance_copy import NativeVmCopy


@pytest.mark.parametrize("version", [1, 2])
@pytest.mark.parametrize("fault", ["", "digest", "lost_image", "stage", "mapping", "format"])
def test_retained_image_import_exact_method_and_custody(
    copy_campaign: Any, tmp_path: Path, fault: str, version: int
) -> None:
    b, execution, fixture, journal = copy_campaign
    old = execution.adapter
    assert isinstance(old, NativeVmCopy)
    fixture["formats"] = ["raw"]
    data = b"synthetic-vmdk-stream" * 8000
    receipt = {
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "sha512": hashlib.sha512(data).hexdigest(),
        "format": "raw",
        "virtual_bytes": len(data),
        "sector_comparison": "passed",
    }
    source_op = str(uuid4())
    folder = old.spool / source_op / "disk-2000"
    folder.mkdir(parents=True)
    (folder / "disk.raw").write_bytes(data)

    class Custody:
        def artifact(self, binding: Any, plan_sha256: str, kind: str) -> dict[str, Any]:
            return {
                "operation_id": source_op,
                "disks": {"wrong" if fault == "mapping" else "disk-2000": receipt},
            }

    p: dict[str, Any] = {
        "schema_version": version,
        "kind": "migration_image_import",
        "conversion_plan_sha256": digest("convert"),
        "route": "glance-direct",
        "max_seconds": 60 if version == 1 else 3600,
        "disks": [
            {
                "key": "disk-2000",
                "image_id": str(uuid4()),
                "name": "migrated-copy",
                "disk_format": "raw",
                "hw_firmware_type": "bios",
                "hw_disk_bus": "virtio",
                "virtual_bytes": len(data),
            }
        ],
    }
    plan_file = tmp_path / "import.json"
    plan_file.write_text(json.dumps(p))
    bound = replace(b, operation_plan_sha256=digest(p))
    journal.claim(bound)
    adapter = OpenStackImageImport(plan_file, old.destination, journal, Custody(), old.spool)
    if fault == "digest":
        receipt["sha256"] = "a" * 64
    if fault == "format":
        receipt["format"] = "qcow2"
    if fault in {"stage", "lost_image"}:
        fixture["fault"] = fault
    if fault:
        with pytest.raises(NativeHeld):
            adapter.execute(bound, lambda: None)
        assert sum(r["path"] == "/v2/images" for r in fixture["calls"]) <= 1
        assert not any(
            "/file" in r["path"] or "web-download" in r["path"] for r in fixture["calls"]
        )
    else:
        adapter.execute(bound, lambda: None)
        image = fixture["images"][p["disks"][0]["image_id"]]
        assert image["status"] == "active" and image["disk_format"] == "raw"
        assert image["os_hash_value"] == receipt["sha512"]
        assert journal.events[-1][0] == "poll_observed"
    assert (folder / "disk.raw").read_bytes() == data
