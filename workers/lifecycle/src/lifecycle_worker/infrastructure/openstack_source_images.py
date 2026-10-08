"""Read captured Nova/Cinder images, independently of the destination platform."""

import hashlib
from collections.abc import Callable
from dataclasses import replace
from typing import Any, BinaryIO

from lifecycle_worker.application.native import (
    NativeBinding,
    NativeHeld,
    digest,
    identity,
)
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
        self,
        image: dict[str, Any],
        sink: BlobSink,
        boundary: Callable[[], None],
        prefix: BinaryIO | None = None,
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
            prefix,
        )

    def download_remaining(
        self, image: dict[str, Any], sink: BlobSink, prefix: BinaryIO, boundary: Callable[[], None]
    ) -> dict[str, Any]:
        return self.download(image, sink, boundary, prefix)
