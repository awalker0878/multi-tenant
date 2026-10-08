"""Independent verification of captured-image identity and retained transfer integrity."""

from collections.abc import Callable
from typing import Any

from lifecycle_worker.application.native import (
    NativeBinding,
    NativeHeld,
    NativeJournal,
    digest,
    native_identity,
)
from lifecycle_worker.infrastructure.migration_custody import CaptureCustody
from lifecycle_worker.infrastructure.native_image_archive import NativeImageSource


class CapturedImageObserver:
    """Separate native identity checks image metadata and durable transfer hashes.

    This proves copy custody only. It never claims guest or application health.
    """

    def __init__(
        self,
        source: NativeImageSource,
        plan: dict[str, Any],
        custody: CaptureCustody,
        journal: NativeJournal,
        writer_id: str,
        observer_id: str,
        clock: Callable[[], int],
        current: Callable[[], None] = lambda: None,
        capture_recovery: Callable[[NativeBinding], dict[str, Any]] | None = None,
    ) -> None:
        if native_identity(observer_id) == native_identity(writer_id):
            raise NativeHeld("independent_native_identity_required")
        self.source, self.plan, self.custody, self.journal, self.clock = (
            source,
            plan,
            custody,
            journal,
            clock,
        )
        self.current = current
        self.capture_recovery = capture_recovery

    def observe(self, binding: NativeBinding, objects: dict[str, Any]) -> dict[str, Any]:
        self.current()
        is_archive = self.plan["kind"] == "native_image_archive"
        try:
            capture = self.custody.capture(
                binding,
                self.plan["capture_plan_sha256"] if is_archive else binding.operation_plan_sha256,
            )
        except NativeHeld as error:
            if (
                str(error) != "migration_capture_receipt_missing"
                or is_archive
                or self.capture_recovery is None
            ):
                raise
            self.capture_recovery(binding)
            capture = self.custody.capture(binding, binding.operation_plan_sha256)
            objects = self.journal.resources(binding)
        self.source.current(binding, capture, self.current)
        expected = {d["key"] for d in self.plan["disks"]}
        expected_objects = (
            {
                key: {"kind": "image", "id": disk["image_id"]}
                for key, disk in capture["disks"].items()
            }
            if capture.get("source_platform") == "ahv" and not is_archive
            else {}
        )
        if set(capture["disks"]) != expected or objects != expected_objects:
            raise NativeHeld("source_capture_inventory_changed")
        receipts = self.journal.transfers(binding) if is_archive else {}
        if is_archive and set(receipts) != expected:
            raise NativeHeld("source_transfer_receipts_incomplete")
        for key in sorted(expected):
            image = self.source.image(binding, capture, key, self.current)
            if is_archive:
                receipt = receipts[key]
                if (
                    receipt.get("size") != image["size"]
                    or receipt.get(image["checksum_algorithm"]) != image["checksum"]
                    or receipt.get("image_sha256") != digest(image)
                    or receipt.get("format") != image["format"]
                ):
                    raise NativeHeld("source_transfer_integrity_changed")
        return {
            "binding_sha256": binding.fingerprint,
            "independent": True,
            "observed_at": self.clock(),
            "outcome": "observed_present",
            "capture_sha256": digest(capture),
            "transfers_sha256": digest(receipts),
            "objects_sha256": digest(objects),
            "application_ready": False,
            "activation_authorized": False,
        }
