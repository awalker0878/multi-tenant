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


@pytest.mark.parametrize("fault", ["", "guest_identity"])
def test_complete_preparation_pipeline_only_mutates_isolated_copies(
    binding: NativeBinding, tmp_path: Path, fault: str
) -> None:
    from test_guest_preparation import setup

    from lifecycle_worker.infrastructure.guest_preparation import GuestPreparation
    from lifecycle_worker.infrastructure.image_conversion import file_digest

    appliance, selected, _, _ = setup(tmp_path)
    if fault:
        appliance.fault = "os"

    class RawEngine(Engine):
        def run(
            self,
            arguments: list[str],
            source: Path,
            output: Path,
            max_bytes: int,
            deadline: float,
            current: Any,
        ) -> bytes:
            result = super().run(arguments, source, output, max_bytes, deadline, current)
            if arguments[0] == "convert" and arguments[arguments.index("-O") + 1] == "raw":
                (output / "disk.raw").write_bytes(b"a" * 512)
            return result

    engine = RawEngine()
    spool = tmp_path / "pipeline"
    spool.mkdir(mode=0o700)
    source_op = str(uuid4())
    source = spool / source_op
    source.mkdir(mode=0o700)
    disks = {}
    for key in ("root", "data"):
        f = source / (key + ".raw")
        f.write_bytes(b"a" * 512)
        disks[key] = file_digest(f, 512, lambda: None) | {"format": "raw"}
    p = {
        "schema_version": 4,
        "kind": "migration_copy_conversion",
        "export_plan_sha256": digest("export"),
        "artifact_sha256": engine.artifact_sha256,
        "guest_profile": selected,
        "max_seconds": 30,
        "bytes_per_second": 1048576,
        "disks": [
            {"key": key, "virtual_bytes": 512, "target_format": "vmdk", "max_output_bytes": 2048}
            for key in disks
        ],
    }
    path = tmp_path / "pipeline-plan.json"
    path.write_text(json.dumps(p))
    b = replace(binding, operation_plan_sha256=digest(p))
    journal = Journal()
    journal.claim(b)

    class Custody:
        def artifact(self, bound: NativeBinding, sha: str, kind: str) -> dict[str, Any]:
            assert bound == b and sha == p["export_plan_sha256"] and kind == "archive"
            return {"operation_id": source_op, "disks": disks}

    conversion = MigrationConversion(
        path, CopyConverter(engine), journal, Custody(), spool, GuestPreparation(appliance)
    )
    if fault:
        with pytest.raises(NativeHeld):
            conversion.execute(b, lambda: None)
        assert not any(event == "conversion_complete" for event, _ in journal.events)
    else:
        conversion.execute(b, lambda: None)
        receipts = [f for e, f in journal.events if e == "conversion_observed"]
        assert len(receipts) == 2
        assert all(
            f["guest_transformation"] == "prepared_offline"
            and f["original_source_sha256"] == disks[f["resource_key"]]["sha256"]
            for f in receipts
        )
        assert journal.events[-1][0] == "conversion_complete"
        assert len([c for c in engine.calls if c[0] == "compare"]) == 4
    assert all((source / (key + ".raw")).read_bytes() == b"a" * 512 for key in disks)
