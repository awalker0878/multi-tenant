"""Explicit continuation of immutable GETs, under the original live grant.

An exclusive spool lock excludes concurrent byte writers, including a worker that
is still alive. A restart rechecks the capture and each native checksum. No native
create/action request is retried, and the original time budget is never extended.
"""

import fcntl
import json
import math
import os
import stat
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from lifecycle_worker.application.native import NativeBinding, NativeHeld, decode, digest
from lifecycle_worker.infrastructure.image_conversion import file_digest
from lifecycle_worker.infrastructure.migration_transfer import RateBound
from lifecycle_worker.infrastructure.native_files import protected_read, sync_directory
from lifecycle_worker.infrastructure.native_image_archive import ResumableImageSource

if TYPE_CHECKING:
    from lifecycle_worker.infrastructure.native_image_archive import NativeImageArchive


def archive(
    adapter: "NativeImageArchive", b: NativeBinding, boundary: Callable[[], None], *, resume: bool
) -> None:
    p = adapter.plan(b)
    directory = adapter.spool / b.operation_id
    if not resume:
        directory.mkdir(mode=0o700)
        sync_directory(adapter.spool)
    if not directory.is_dir() or directory.is_symlink() or directory.stat().st_mode & 0o077:
        raise NativeHeld("native_archive_custody_invalid")
    fd = os.open(
        directory / "writer.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600
    )
    with os.fdopen(fd, "rb+") as lock:
        lock_info = os.fstat(lock.fileno())
        if (
            not stat.S_ISREG(lock_info.st_mode)
            or lock_info.st_nlink != 1
            or lock_info.st_mode & 0o077
        ):
            raise NativeHeld("native_archive_custody_invalid")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise NativeHeld("prior_transfer_writer_not_excluded") from None
        boundary()
        state_path = directory / "checkpoint.json"
        capture = adapter.custody.capture(b, p["capture_plan_sha256"])
        if (
            capture.get("source_platform") != p["source_platform"]
            or capture.get("consistency") != "cold_powered_off"
            or set(capture.get("disks", {})) != {d["key"] for d in p["disks"]}
        ):
            raise NativeHeld("migration_capture_receipt_invalid")
        state = (
            decode(protected_read(state_path, 65536))
            if resume
            else {
                "binding_sha256": b.fingerprint,
                "capture_sha256": digest(capture),
                "deadline": min(time.time() + p["max_seconds"], b.expires_at),
                "continuations": 0,
            }
        )
        if (
            set(state) != {"binding_sha256", "capture_sha256", "deadline", "continuations"}
            or state["binding_sha256"] != b.fingerprint
            or state["capture_sha256"] != digest(capture)
            or type(state["deadline"]) not in {int, float}
            or not math.isfinite(state["deadline"])
            or state["deadline"] > b.expires_at
            or type(state["continuations"]) is not int
            or not 0 <= state["continuations"] <= p["max_continuations"]
        ):
            raise NativeHeld("native_archive_checkpoint_changed")

        def current() -> None:
            boundary()
            if time.time() >= min(state["deadline"], b.expires_at):
                raise NativeHeld("migration_archive_original_deadline")

        current()
        if resume:
            state["continuations"] += 1
            if state["continuations"] > p["max_continuations"]:
                raise NativeHeld("native_archive_continuation_bound")
        temp = directory / "checkpoint.next"
        checkpoint_fd = os.open(temp, os.O_CREAT | os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(checkpoint_fd, "wb") as file:
            file.write(json.dumps(state, allow_nan=False).encode())
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp, state_path)
        dir_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
        adapter.source.current(b, capture, current)
        assert adapter.continuation_custody is not None
        try:
            completed = adapter.continuation_custody.artifact(b, b.operation_plan_sha256, "archive")
        except NativeHeld as error:
            if str(error) != "migration_artifact_incomplete":
                raise
            completed = None
        existing = adapter.journal.transfers(b)
        receipts: dict[str, Any] = {}
        if not set(existing) <= {d["key"] for d in p["disks"]}:
            raise NativeHeld("native_archive_receipts_changed")
        for disk in p["disks"]:
            current()
            key = disk["key"]
            image = adapter.source.image(b, capture, key, current)
            if (
                image.get("format") not in {"raw", "qcow2", "vmdk"}
                or type(image.get("size")) is not int
                or not 0 < image["size"] <= disk["max_bytes"]
            ):
                raise NativeHeld("native_image_archive_mapping_changed")
            path = directory / (key + "." + image["format"])
            file_fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
            with os.fdopen(file_fd, "r+b") as stream:
                info = os.fstat(stream.fileno())
                if (
                    not stat.S_ISREG(info.st_mode)
                    or info.st_nlink != 1
                    or info.st_mode & 0o077
                    or info.st_size > image["size"]
                ):
                    raise NativeHeld("native_archive_partial_file_invalid")
                if info.st_size < image["size"]:
                    if key in existing or completed is not None:
                        raise NativeHeld("native_archive_retained_bytes_missing")
                    stream.seek(0, os.SEEK_END)
                    sink = RateBound(
                        stream, p["bytes_per_second"], image["size"] - info.st_size, current
                    )
                    adapter.journal.record(
                        b,
                        "transfer_continued" if resume else "transfer_started",
                        {
                            "resource_key": key,
                            "offset": info.st_size,
                            "image_sha256": digest(image),
                        },
                    )
                    if info.st_size:
                        assert isinstance(adapter.source, ResumableImageSource)
                        with path.open("rb") as prefix:
                            adapter.source.download_remaining(image, sink, prefix, current)
                    else:
                        adapter.source.download(image, sink, current)
                    sink.flush()
            result = file_digest(path, image["size"], current)
            if (
                result["size"] != image["size"]
                or result[image["checksum_algorithm"]] != image["checksum"]
            ):
                raise NativeHeld("native_archive_retained_checksum_changed")
            if adapter.source.image(b, capture, key, current) != image:
                raise NativeHeld("source_image_changed_during_transfer")
            receipt = result | {"format": image["format"], "image_sha256": digest(image)}
            receipts[key] = receipt
            # Make the new directory entry durable before recording successful
            # byte custody in PostgreSQL, including after a worker restart.
            directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
            if key in existing:
                if existing[key] != receipt | {"resource_key": key}:
                    raise NativeHeld("native_archive_receipt_changed")
            else:
                adapter.journal.record(b, "disk_transferred", {"resource_key": key, **receipt})
        adapter.source.current(b, capture, current)
        if completed is None:
            adapter.journal.record(
                b,
                "export_complete",
                {
                    "bytes": sum(r["size"] for r in receipts.values()),
                    "disks_sha256": digest(receipts),
                    "capture_sha256": digest(capture),
                },
            )
        elif completed["completion"]["disks_sha256"] != digest(receipts):
            raise NativeHeld("native_archive_completion_changed")
