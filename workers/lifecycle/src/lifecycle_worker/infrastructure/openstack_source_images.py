"""Read captured Nova/Cinder images, independently of the destination platform."""

import hashlib
from collections.abc import Callable
from dataclasses import replace
from typing import Any

from lifecycle_worker.application.native import (
    NativeBinding,
    NativeHeld,
    NativeJournal,
    digest,
    identity,
)
from lifecycle_worker.infrastructure.migration_custody import CaptureCustody
from lifecycle_worker.infrastructure.migration_transfer import BlobSink, NativeBlobDownload
from lifecycle_worker.infrastructure.native_http import credential
from lifecycle_worker.infrastructure.native_json import NativeJson
from lifecycle_worker.infrastructure.openstack_api import NativeWrites
from lifecycle_worker.infrastructure.openstack_capture import image_facts
from lifecycle_worker.infrastructure.openstack_source_contract import configuration


class OpenStackCapturedImages:
    def __init__(self, compute: NativeJson, image: NativeJson, authorization: NativeWrites) -> None:
        self.compute, self.api, self.authorization = compute, image, authorization
        self.blobs = NativeBlobDownload(image.endpoint, "X-Auth-Token")

    def current(
        self, binding: NativeBinding, capture: dict[str, Any], boundary: Callable[[], None]
    ) -> None:
        boundary()
        if (
            capture.get("source_platform") != "openstack"
            or capture.get("consistency") != "cold_powered_off"
        ):
            raise NativeHeld("openstack_capture_receipt_invalid")
        self.authorization.authorize(replace(binding, project_id=capture["source_project_id"]))
        for api in (self.compute, self.api):
            api.expected_token_sha256 = self.authorization.subject_token_sha256
        server = self.compute.request(
            "GET", "/servers/" + identity(capture["source_vm_id"]), boundary
        ).get("server", {})
        if (
            server.get("id") != capture["source_vm_id"]
            or server.get("tenant_id") != capture["source_project_id"]
            or server.get("status") != "SHUTOFF"
            or digest(configuration("server", server)) != capture.get("server_sha256")
        ):
            raise NativeHeld("openstack_source_not_stopped_or_changed")

    def image(
        self,
        binding: NativeBinding,
        capture: dict[str, Any],
        key: str,
        boundary: Callable[[], None],
    ) -> dict[str, Any]:
        expected = capture["disks"][key]
        document = self.api.request("GET", "/images/" + identity(expected["image_id"]), boundary)
        observed = image_facts(document, capture["source_project_id"], expected["name"])
        if observed != {k: v for k, v in expected.items() if k != "virtual_bytes"}:
            raise NativeHeld("openstack_capture_image_changed")
        return observed

    def download(
        self, image: dict[str, Any], sink: BlobSink, boundary: Callable[[], None]
    ) -> dict[str, Any]:
        def current() -> None:
            boundary()
            self.authorization.identity_check()
            token = credential(self.api.endpoint)
            if (
                hashlib.sha256(token.encode()).hexdigest()
                != self.authorization.subject_token_sha256
                or self.authorization.clock() >= self.authorization.credential_expires_at
            ):
                raise NativeHeld("openstack_source_credential_changed_or_expired")

        return self.blobs.download(
            "/images/" + identity(image["image_id"]) + "/file",
            sink,
            image["size"],
            image["checksum_algorithm"],
            image["checksum"],
            current,
        )


class CapturedImageObserver:
    """Separate native identity checks image metadata and durable transfer hashes.

    This proves copy custody only. It never claims guest or application health.
    """

    def __init__(
        self,
        source: OpenStackCapturedImages,
        plan: dict[str, Any],
        custody: CaptureCustody,
        journal: NativeJournal,
        writer_id: str,
        clock: Callable[[], int],
    ) -> None:
        if source.authorization.user_id == writer_id:
            raise NativeHeld("independent_native_identity_required")
        self.source, self.plan, self.custody, self.journal, self.clock = (
            source,
            plan,
            custody,
            journal,
            clock,
        )

    def observe(self, binding: NativeBinding, objects: dict[str, Any]) -> dict[str, Any]:
        is_archive = self.plan["kind"] == "native_image_archive"
        capture = self.custody.capture(
            binding,
            self.plan["capture_plan_sha256"] if is_archive else binding.operation_plan_sha256,
        )
        self.source.current(binding, capture, lambda: None)
        expected = {d["key"] for d in self.plan["disks"]}
        if set(capture["disks"]) != expected or objects:
            raise NativeHeld("source_capture_inventory_changed")
        receipts = self.journal.transfers(binding) if is_archive else {}
        if is_archive and set(receipts) != expected:
            raise NativeHeld("source_transfer_receipts_incomplete")
        for key in sorted(expected):
            image = self.source.image(binding, capture, key, lambda: None)
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
