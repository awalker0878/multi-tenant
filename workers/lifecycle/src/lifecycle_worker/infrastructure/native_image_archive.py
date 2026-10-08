"""Platform-neutral archive of owned, immutable native images into copy custody."""

import os
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, BinaryIO, Protocol, runtime_checkable

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
from lifecycle_worker.infrastructure.migration_custody import ArtifactCustody, CaptureCustody
from lifecycle_worker.infrastructure.migration_transfer import BlobSink, RateBound
from lifecycle_worker.infrastructure.native_files import protected_read, sync_directory


class NativeImageSource(Protocol):
    def current(
        self, binding: NativeBinding, capture: dict[str, Any], boundary: Callable[[], None]
    ) -> None: ...
    def image(
        self,
        binding: NativeBinding,
        capture: dict[str, Any],
        key: str,
        boundary: Callable[[], None],
    ) -> dict[str, Any]: ...
    def download(
        self, image: dict[str, Any], sink: BlobSink, boundary: Callable[[], None]
    ) -> dict[str, Any]: ...


@runtime_checkable
class ResumableImageSource(NativeImageSource, Protocol):
    def download_remaining(
        self, image: dict[str, Any], sink: BlobSink, prefix: BinaryIO, boundary: Callable[[], None]
    ) -> dict[str, Any]: ...


class NativeImageArchive:
    def __init__(
        self,
        plan_file: Path,
        source: NativeImageSource,
        journal: NativeJournal,
        custody: CaptureCustody,
        spool: Path,
        continuation_custody: ArtifactCustody | None = None,
    ) -> None:
        self.continuation_custody = continuation_custody
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
                "source_platform",
                "capture_plan_sha256",
                "disks",
                "max_seconds",
                "bytes_per_second",
                "spool_bytes",
            }
            | ({"max_continuations"} if p.get("schema_version") == 3 else set()),
        )
        if (
            type(p["schema_version"]) is not int
            or p["schema_version"] not in {2, 3}
            or p["kind"] != "native_image_archive"
            or p["source_platform"] not in {"openstack", "ahv"}
            or not sha256(p["capture_plan_sha256"])
            or digest(p) != binding.operation_plan_sha256
        ):
            raise NativeHeld("native_image_archive_plan_changed")
        seconds(p)
        if p["schema_version"] == 3 and (
            type(p["max_continuations"]) is not int
            or not 1 <= p["max_continuations"] <= 32
            or self.continuation_custody is None
            or not isinstance(self.source, ResumableImageSource)
        ):
            raise NativeHeld("native_transfer_continuation_unqualified")
        if (
            type(p["bytes_per_second"]) is not int
            or not 65536 <= p["bytes_per_second"] <= 2**34
            or type(p["spool_bytes"]) is not int
            or not 1 <= p["spool_bytes"] <= 2**50
            or not isinstance(p["disks"], list)
            or not 1 <= len(p["disks"]) <= 32
        ):
            raise NativeHeld("native_image_archive_budget_invalid")
        keys: set[str] = set()
        for disk in p["disks"]:
            shape(disk, {"key", "max_bytes"})
            if (
                not isinstance(disk["key"], str)
                or re.fullmatch(r"[A-Za-z0-9_-]{1,80}", disk["key"]) is None
                or disk["key"] in keys
                or type(disk["max_bytes"]) is not int
                or not 1 <= disk["max_bytes"] <= 2**46
            ):
                raise NativeHeld("native_image_archive_mapping_invalid")
            keys.add(disk["key"])
        if sum(d["max_bytes"] for d in p["disks"]) > p["spool_bytes"]:
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
        return {
            "operation_plan_sha256": digest(self.plan(binding)),
            "native_write_authorized": False,
        }

    def execute(self, binding: NativeBinding, boundary: Callable[[], None]) -> None:
        p = self.plan(binding)
        if p["schema_version"] == 3:
            from lifecycle_worker.infrastructure.native_archive_continuation import archive

            archive(self, binding, boundary, resume=False)
            return
        deadline = time.monotonic() + seconds(p)

        def current() -> None:
            boundary()
            if time.monotonic() >= deadline:
                raise NativeHeld("migration_archive_deadline")

        capture = self.custody.capture(binding, p["capture_plan_sha256"])
        if (
            capture.get("source_platform") != p["source_platform"]
            or capture.get("consistency") != "cold_powered_off"
            or not isinstance(capture.get("disks"), dict)
            or set(capture["disks"]) != {d["key"] for d in p["disks"]}
        ):
            raise NativeHeld("migration_capture_receipt_invalid")
        self.source.current(binding, capture, current)
        directory = self.spool / binding.operation_id
        directory.mkdir(mode=0o700)
        sync_directory(self.spool)
        receipts = {}
        for disk in p["disks"]:
            current()
            key = disk["key"]
            image = self.source.image(binding, capture, key, current)
            if (
                image.get("format") not in {"raw", "qcow2", "vmdk"}
                or type(image.get("size")) is not int
                or not 0 < image["size"] <= disk["max_bytes"]
            ):
                raise NativeHeld("native_image_archive_mapping_changed")
            self.journal.record(
                binding, "transfer_started", {"resource_key": key, "image_sha256": digest(image)}
            )
            with (directory / (key + "." + image["format"])).open("xb") as stream:
                sink = RateBound(stream, p["bytes_per_second"], disk["max_bytes"], current)
                result = self.source.download(image, sink, current)
                sink.flush()
            if self.source.image(binding, capture, key, current) != image:
                raise NativeHeld("source_image_changed_during_transfer")
            receipt = result | {"format": image["format"], "image_sha256": digest(image)}
            receipts[key] = receipt
            sync_directory(directory)
            self.journal.record(binding, "disk_transferred", {"resource_key": key, **receipt})
        self.source.current(binding, capture, current)
        fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        self.journal.record(
            binding,
            "export_complete",
            {
                "bytes": sum(r["size"] for r in receipts.values()),
                "disks_sha256": digest(receipts),
                "capture_sha256": digest(capture),
            },
        )

    def resume_transfer(self, binding: NativeBinding, boundary: Callable[[], None]) -> None:
        if self.plan(binding)["schema_version"] != 3:
            raise NativeHeld("native_transfer_continuation_not_selected")
        from lifecycle_worker.infrastructure.native_archive_continuation import archive

        archive(self, binding, boundary, resume=True)
