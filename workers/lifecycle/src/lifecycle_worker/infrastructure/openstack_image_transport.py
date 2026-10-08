"""Openstack image transport; platform mechanisms retain native semantics."""

import hashlib
import http.client
import time
from collections.abc import Callable
from typing import Any, BinaryIO
from urllib.parse import urlsplit

from lifecycle_worker.application.native import (
    NativeBinding,
    NativeHeld,
    NativeJournal,
    digest,
)
from lifecycle_worker.infrastructure.native_http import PinnedConnection
from lifecycle_worker.infrastructure.native_json import NativeJson
from lifecycle_worker.infrastructure.native_response import response_bytes
from lifecycle_worker.infrastructure.openstack_api import NativeWrites


class GlanceImport:
    def __init__(self, api: NativeJson, scope: NativeWrites) -> None:
        if api.endpoint.token_file != scope.endpoints["identity"].token_file:
            raise NativeHeld("image_project_credential_mismatch")
        self.api, self.scope = api, scope

    def current(self, binding: NativeBinding, boundary: Callable[[], None]) -> None:
        boundary()
        self.scope.authorize(binding)
        if (
            hashlib.sha256(self.api.credential().encode()).hexdigest()
            != self.scope.subject_token_sha256
        ):
            raise NativeHeld("image_credential_changed")
        self.api.expected_token_sha256 = self.scope.subject_token_sha256
        boundary()

    def preflight(
        self, binding: NativeBinding, boundary: Callable[[], None], disk_format: str = "vmdk"
    ) -> None:
        def current() -> None:
            self.current(binding, boundary)

        schema = self.api.request("GET", "/v2/schemas/image", current)
        methods = self.api.request("GET", "/v2/info/import", current)
        if (
            disk_format not in {"vmdk", "raw", "qcow2"}
            or disk_format
            not in schema.get("properties", {}).get("disk_format", {}).get("enum", [])
            or "bare"
            not in schema.get("properties", {}).get("container_format", {}).get("enum", [])
            or "glance-direct" not in methods.get("import-methods", {}).get("value", [])
        ):
            raise NativeHeld("native_disk_import_not_supported")

    def create(
        self, binding: NativeBinding, disk: dict[str, Any], boundary: Callable[[], None]
    ) -> dict[str, Any]:
        payload = {key: disk[key] for key in ("name", "hw_firmware_type", "hw_disk_bus")}
        payload.update(
            id=disk["image_id"],
            disk_format=disk.get("disk_format", "vmdk"),
            container_format="bare",
            visibility="private",
            product_tenant_id=binding.tenant_id,
            product_operation_id=binding.operation_id,
            product_resource_id=binding.resource_id,
            product_object_key=disk["key"],
        )
        result = self.api.request(
            "POST", "/v2/images", lambda: self.current(binding, boundary), payload, 201
        )
        if (
            not isinstance(result, dict)
            or result.get("id") != disk["image_id"]
            or result.get("owner") != binding.project_id
            or result.get("status") != "queued"
        ):
            raise NativeHeld("native_image_create_unconfirmed")
        return result

    def stage(
        self,
        binding: NativeBinding,
        disk: dict[str, Any],
        stream: BinaryIO,
        receipt: dict[str, Any],
        boundary: Callable[[], None],
    ) -> None:
        self.current(binding, boundary)
        token = self.api.credential()
        token_sha256 = hashlib.sha256(token.encode()).hexdigest()

        def current() -> None:
            boundary()
            self.scope.identity_check()
            if (
                self.api.credential() != token
                or token_sha256 != self.scope.subject_token_sha256
                or token_sha256 != self.api.expected_token_sha256
            ):
                raise NativeHeld("image_credential_changed")
            if self.scope.clock() >= self.scope.credential_expires_at:
                raise NativeHeld("image_credential_expired")

        headers = {
            "X-Auth-Token": token,
            "Content-Type": "application/octet-stream",
            "Content-Length": str(receipt["size"]),
        }
        connection = PinnedConnection(self.api.endpoint)
        try:
            current()
            path = (
                urlsplit(self.api.endpoint.base_url).path.rstrip("/")
                + "/v2/images/"
                + disk["image_id"]
                + "/stage"
            )
            connection.putrequest("PUT", path)
            for key, value in headers.items():
                connection.putheader(key, value)
            connection.endheaders()
            size, checksum = 0, hashlib.sha256()
            stream.seek(0)
            while chunk := stream.read(65536):
                current()
                size += len(chunk)
                if size > receipt["size"]:
                    raise NativeHeld("native_export_artifact_changed")
                checksum.update(chunk)
                connection.send(chunk)
            if size != receipt["size"] or checksum.hexdigest() != receipt["sha256"]:
                raise NativeHeld("native_export_artifact_changed")
            current()
            response = connection.getresponse()
            if response.status != 204:
                raise NativeHeld("native_image_stage_unconfirmed")
            response_bytes(response, 0, 10, current)
        except (OSError, http.client.HTTPException):
            raise NativeHeld("native_image_stage_outcome_unknown") from None
        finally:
            connection.close()

    def finish(
        self,
        binding: NativeBinding,
        disk: dict[str, Any],
        receipt: dict[str, Any],
        boundary: Callable[[], None],
    ) -> None:
        def current() -> None:
            self.current(binding, boundary)

        path = "/v2/images/" + disk["image_id"]
        self.api.request(
            "POST", path + "/import", current, {"method": {"name": "glance-direct"}}, 202
        )
        while True:
            image = self.api.request("GET", path, current)
            if image.get("id") != disk["image_id"] or image.get("owner") != binding.project_id:
                raise NativeHeld("native_image_scope_changed")
            if image.get("status") == "active":
                algorithm = image.get("os_hash_algo")
                if (
                    algorithm not in {"sha256", "sha512"}
                    or image.get("os_hash_value") != receipt[algorithm]
                    or image.get("size") != receipt["size"]
                    or image.get("disk_format") != disk.get("disk_format", "vmdk")
                ):
                    raise NativeHeld("native_image_integrity_changed")
                return
            if image.get("status") not in {"uploading", "importing"}:
                raise NativeHeld("native_image_import_failed")
            time.sleep(0.1)


class GlanceReadback:
    """Separate credential verifies copied images against durable transfer receipts."""

    def __init__(
        self,
        reader: GlanceImport,
        plan: dict[str, Any],
        journal: NativeJournal,
        writer_user_id: str,
        clock: Callable[[], int],
    ) -> None:
        if reader.scope.user_id == writer_user_id:
            raise NativeHeld("independent_native_identity_required")
        self.reader, self.plan, self.journal, self.clock = reader, plan, journal, clock

    def observe(self, binding: NativeBinding, objects: dict[str, Any]) -> dict[str, Any]:
        receipts = self.journal.transfers(binding)
        if set(objects) != {disk["key"] for disk in self.plan["disks"]}:
            raise NativeHeld("native_image_receipts_incomplete")
        for disk in self.plan["disks"]:
            if objects[disk["key"]] != {"kind": "image", "id": disk["image_id"]}:
                raise NativeHeld("native_image_receipt_changed")
            image = self.reader.api.request(
                "GET",
                "/v2/images/" + disk["image_id"],
                lambda: self.reader.current(binding, lambda: None),
            )
            receipt = receipts[disk["key"]]
            algorithm = image.get("os_hash_algo")
            expected = {
                "id": disk["image_id"],
                "owner": binding.project_id,
                "status": "active",
                "disk_format": disk.get("disk_format", "vmdk"),
                "container_format": "bare",
                "visibility": "private",
                "product_tenant_id": binding.tenant_id,
                "product_operation_id": binding.operation_id,
                "product_resource_id": binding.resource_id,
                "product_object_key": disk["key"],
                **{key: disk[key] for key in ("name", "hw_firmware_type", "hw_disk_bus")},
            }
            if (
                any(image.get(key) != value for key, value in expected.items())
                or algorithm not in {"sha256", "sha512"}
                or image.get("os_hash_value") != receipt[algorithm]
                or type(image.get("size")) is not int
                or image["size"] != receipt["size"]
            ):
                raise NativeHeld("native_image_readback_changed")
        return {
            "binding_sha256": binding.fingerprint,
            "independent": True,
            "observed_at": self.clock(),
            "outcome": "observed_present",
            "objects_sha256": digest(objects),
            "transfers_sha256": digest(receipts),
            "application_ready": False,
            "activation_authorized": False,
        }
