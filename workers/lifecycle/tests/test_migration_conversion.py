"""Retained archive-to-conversion handoff, using the explicit synthetic engine."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from test_image_conversion import Engine
from test_native import Journal
from test_native import binding as binding

from lifecycle_worker.application.native import NativeBinding, NativeHeld, digest
from lifecycle_worker.infrastructure.image_conversion import CopyConverter
from lifecycle_worker.infrastructure.migration_conversion import MigrationConversion


@pytest.mark.parametrize("version", [1, 2])
@pytest.mark.parametrize("fault", ["", "mapping", "bytes", "digest", "custody", "lost"])
def test_conversion_resolves_only_complete_archive_with_exact_bytes(
    binding: NativeBinding, tmp_path: Path, fault: str, version: int
) -> None:
    engine = Engine()
    source_op = str(uuid4())
    spool = tmp_path / "custody"
    spool.mkdir(mode=0o700)
    source_dir = spool / source_op
    source_dir.mkdir(mode=0o700)
    raw = b"synthetic-vmdk"
    (source_dir / "disk-2000.vmdk").write_bytes(raw)
    prior = {"size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    plan = {
        "schema_version": version,
        "kind": "migration_copy_conversion",
        "export_plan_sha256": digest("approved-archive"),
        "artifact_sha256": engine.artifact_sha256,
        "max_seconds": 30 if version == 1 else 3600,
        "bytes_per_second": 1048576,
        "disks": [
            {
                "key": "disk-2000",
                "virtual_bytes": 512,
                "target_format": "qcow2",
                "max_output_bytes": 1048576,
            }
        ],
    }

    class Custody:
        def artifact(self, b: NativeBinding, plan_sha256: str, kind: str) -> dict[str, Any]:
            assert b == bound and plan_sha256 == plan["export_plan_sha256"] and kind == "archive"
            if fault == "custody":
                raise NativeHeld("migration_artifact_incomplete")
            return {
                "operation_id": source_op,
                "disks": {"wrong" if fault == "mapping" else "disk-2000": prior},
            }

    if fault == "bytes":
        prior["size"] = len(raw) + 1
    if fault == "digest":
        prior["sha256"] = "a" * 64
    if fault == "lost":
        engine.fault = "lost"
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan))
    bound = replace(binding, operation_plan_sha256=digest(plan))
    journal = Journal()
    journal.claim(bound)
    conversion = MigrationConversion(path, CopyConverter(engine), journal, Custody(), spool)
    if fault:
        with pytest.raises(NativeHeld):
            conversion.execute(bound, lambda: None)
        assert not any(event == "conversion_complete" for event, _ in journal.events)
        if fault != "lost":
            assert engine.calls == []
    else:
        conversion.execute(bound, lambda: None)
        receipts = {
            facts["resource_key"]: {k: v for k, v in facts.items() if k != "resource_key"}
            for event, facts in journal.events
            if event == "conversion_observed"
        }
        assert journal.events[-1] == (
            "conversion_complete",
            {"disks_sha256": digest(receipts), "source_operation_id": source_op},
        )
        assert (spool / bound.operation_id / "disk-2000/disk.qcow2").is_file()
        calls = len(engine.calls)
        with pytest.raises(FileExistsError):
            conversion.execute(bound, lambda: None)
        assert len(engine.calls) == calls
    assert (source_dir / "disk-2000.vmdk").read_bytes() == raw
