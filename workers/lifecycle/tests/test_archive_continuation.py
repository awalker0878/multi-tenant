"""Durable same-grant continuation never replays capture or permits two byte writers."""

import fcntl
import hashlib
import json
import time
from dataclasses import replace
from pathlib import Path
from typing import Any, BinaryIO

import pytest
from test_native import Journal
from test_native import binding as binding

from lifecycle_worker.application.native import NativeBinding, NativeHeld, digest
from lifecycle_worker.infrastructure.native_image_archive import NativeImageArchive


class Source:
    data = b"original immutable image bytes" * 100

    def __init__(self) -> None:
        self.reads: list[int] = []
        self.drift = False

    def current(self, b: Any, capture: Any, current: Any) -> None:
        current()
        if self.drift:
            raise NativeHeld("source_drift")

    def image(self, b: Any, capture: Any, key: str, current: Any) -> dict[str, Any]:
        current()
        return {
            "format": "raw",
            "size": len(self.data),
            "checksum_algorithm": "sha256",
            "checksum": hashlib.sha256(self.data).hexdigest(),
        }

    def download(self, image: Any, sink: Any, current: Any) -> dict[str, Any]:
        self.reads.append(0)
        sink.write(self.data[:512])
        sink.flush()
        raise NativeHeld("process_interrupted")

    def download_remaining(
        self, image: Any, sink: Any, prefix: BinaryIO, current: Any
    ) -> dict[str, Any]:
        retained = prefix.read()
        assert retained == self.data[: len(retained)]
        self.reads.append(len(retained))
        sink.write(self.data[len(retained) :])
        sink.flush()
        return {}


def setup(
    binding: NativeBinding, tmp_path: Path
) -> tuple[NativeImageArchive, NativeBinding, Source, Journal]:
    spool = tmp_path / "spool"
    spool.mkdir(mode=0o700)
    plan = {
        "schema_version": 3,
        "kind": "native_image_archive",
        "source_platform": "ahv",
        "capture_plan_sha256": digest("capture"),
        "disks": [{"key": "root", "max_bytes": 4096}],
        "max_seconds": 120,
        "bytes_per_second": 1048576,
        "spool_bytes": 4096,
        "max_continuations": 3,
    }
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan))
    b = replace(binding, operation_plan_sha256=digest(plan), expires_at=int(time.time()) + 180)
    journal = Journal()
    journal.claim(b)

    class Custody:
        def capture(self, binding: NativeBinding, plan_sha256: str) -> dict[str, Any]:
            return {
                "source_platform": "ahv",
                "consistency": "cold_powered_off",
                "disks": {"root": {}},
            }

        def artifact(self, binding: NativeBinding, plan_sha256: str, kind: str) -> dict[str, Any]:
            completed = [f for e, f in journal.events if e == "export_complete"]
            if not completed:
                raise NativeHeld("migration_artifact_incomplete")
            assert len(completed) == 1
            return {"completion": completed[0]}

    source = Source()
    custody = Custody()
    return NativeImageArchive(path, source, journal, custody, spool, custody), b, source, journal


def test_restarts_on_the_same_immutable_image_and_emits_one_complete_receipt(
    binding: NativeBinding, tmp_path: Path
) -> None:
    adapter, b, source, journal = setup(binding, tmp_path)
    with pytest.raises(NativeHeld, match="interrupted"):
        adapter.execute(b, lambda: None)
    assert not any(e == "export_complete" for e, _ in journal.events)
    directory = adapter.spool / b.operation_id
    original_deadline = json.loads((directory / "checkpoint.json").read_text())["deadline"]
    adapter.resume_transfer(b, lambda: None)
    assert source.reads == [0, 512]
    assert (directory / "root.raw").read_bytes() == source.data
    adapter.resume_transfer(b, lambda: None)
    assert source.reads == [0, 512]
    assert sum(e == "export_complete" for e, _ in journal.events) == 1
    assert json.loads((directory / "checkpoint.json").read_text())["deadline"] == original_deadline


@pytest.mark.parametrize("fault", ["lock", "drift", "binding", "corrupt", "deadline", "authority"])
def test_uncertain_or_conflicting_continuation_never_completes(
    binding: NativeBinding, tmp_path: Path, fault: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    adapter, b, source, journal = setup(binding, tmp_path)
    with pytest.raises(NativeHeld):
        adapter.execute(b, lambda: None)
    directory = adapter.spool / b.operation_id
    lock = None
    if fault == "lock":
        lock = (directory / "writer.lock").open("rb+")
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if fault == "drift":
        source.drift = True
    if fault == "binding":
        b = replace(b, epoch="cccccccc-cccc-4ccc-8ccc-cccccccccccc")
    if fault == "corrupt":
        (directory / "root.raw").write_bytes(b"wrong")
    if fault == "deadline":
        monkeypatch.setattr(
            "lifecycle_worker.infrastructure.native_archive_continuation.time.time",
            lambda: b.expires_at + 1,
        )

    def current() -> None:
        if fault == "authority":
            raise NativeHeld("revoked")

    try:
        with pytest.raises((NativeHeld, AssertionError)):
            adapter.resume_transfer(b, current)
    finally:
        if lock:
            lock.close()
    assert not any(e == "export_complete" for e, _ in journal.events)
