"""Read-only Prism image byte export; all source disk receipts remain in custody."""

from collections.abc import Callable
from typing import Any, BinaryIO

from lifecycle_worker.application.native import NativeBinding, NativeHeld, identity
from lifecycle_worker.infrastructure.ahv_capture import image_facts, reconcile_capture, source_vm
from lifecycle_worker.infrastructure.ahv_http import COLLECTIONS, AhvTransport, read
from lifecycle_worker.infrastructure.ahv_tasks import AhvJournal
from lifecycle_worker.infrastructure.migration_transfer import BlobSink, NativeBlobDownload
from lifecycle_worker.infrastructure.native_http import NativeEndpoint


class AhvCapturedImages:
    def __init__(self, api: AhvTransport, endpoint: NativeEndpoint) -> None:
        self.api, self.blobs = api, NativeBlobDownload(endpoint, "X-Ntnx-Api-Key")

    def reconcile_capture(
        self,
        binding: NativeBinding,
        plan: dict[str, Any],
        journal: AhvJournal,
        boundary: Callable[[], None],
    ) -> dict[str, Any]:
        return reconcile_capture(plan, binding, self.api, journal, boundary)

    def current(
        self, binding: NativeBinding, capture: dict[str, Any], boundary: Callable[[], None]
    ) -> None:
        if (
            capture.get("source_platform") != "ahv"
            or capture.get("consistency") != "cold_powered_off"
        ):
            raise NativeHeld("ahv_capture_receipt_invalid")
        source_vm(self.api, capture | {"disks": capture["source_disks"]}, boundary)

    def image(
        self,
        binding: NativeBinding,
        capture: dict[str, Any],
        key: str,
        boundary: Callable[[], None],
    ) -> dict[str, Any]:
        expected = capture["disks"][key]
        row = read(self.api, COLLECTIONS["image"] + "/" + identity(expected["image_id"]), boundary)
        observed = image_facts(row, capture, key)
        if observed != {k: v for k, v in expected.items() if k != "virtual_bytes"}:
            raise NativeHeld("ahv_capture_image_changed")
        return observed

    def download(
        self,
        image: dict[str, Any],
        sink: BlobSink,
        boundary: Callable[[], None],
        prefix: BinaryIO | None = None,
    ) -> dict[str, Any]:
        return self.blobs.download(
            COLLECTIONS["image"] + "/" + identity(image["image_id"]) + "/file",
            sink,
            image["size"],
            image["checksum_algorithm"],
            image["checksum"],
            boundary,
            prefix,
        )

    def download_remaining(
        self, image: dict[str, Any], sink: BlobSink, prefix: BinaryIO, boundary: Callable[[], None]
    ) -> dict[str, Any]:
        return self.download(image, sink, boundary, prefix)
