"""Native VMware ExportVm/NFC to Glance import. No converter or alternate route."""

import hashlib
import http.client
import json
import re
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, BinaryIO, Protocol
from urllib.parse import urlsplit

from lifecycle_worker.application.api_plan import name, shape
from lifecycle_worker.application.native import (
    NativeBinding,
    NativeHeld,
    NativeJournal,
    decode,
    digest,
    identity,
    sha256,
)
from lifecycle_worker.infrastructure.native_files import protected_read
from lifecycle_worker.infrastructure.native_http import NativeEndpoint, PinnedConnection, credential
from lifecycle_worker.infrastructure.native_response import response_bytes
from lifecycle_worker.infrastructure.openstack_api import NativeWrites


class DownloadSink(Protocol):
    def write(self, data: bytes) -> int: ...
    def flush(self) -> None: ...
    def seek(self, offset: int, whence: int = 0) -> int: ...


def copy_plan(document: dict[str, Any], binding: NativeBinding) -> dict[str, Any]:
    shape(
        document,
        {
            "schema_version",
            "method",
            "project_id",
            "ownership_digest",
            "custody_id",
            "custody_generation",
            "source",
            "disks",
            "max_seconds",
        },
    )
    if (
        type(document["schema_version"]) is not int
        or document["schema_version"] != 1
        or document["method"] != "native_api_export_import"
        or digest(document) != binding.operation_plan_sha256
    ):
        raise NativeHeld("invalid_native_copy_plan")
    for key in ("project_id", "ownership_digest", "custody_id", "custody_generation"):
        if digest(document[key]) != digest(binding.document()[key]):
            raise NativeHeld("native_copy_scope_changed")
    source = document["source"]
    shape(source, {"vm_id", "api_version", "config_sha256"})
    if (
        not isinstance(source["vm_id"], str)
        or re.fullmatch(r"vm-[1-9][0-9]*", source["vm_id"]) is None
        or not isinstance(source["api_version"], str)
        or re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+", source["api_version"]) is None
        or not sha256(source["config_sha256"])
    ):
        raise NativeHeld("invalid_native_copy_source")
    if type(document["max_seconds"]) is not int or not 1 <= document["max_seconds"] <= 86400:
        raise NativeHeld("invalid_native_copy_deadline")
    disks = document["disks"]
    if not isinstance(disks, list) or not 1 <= len(disks) <= 32:
        raise NativeHeld("invalid_native_copy_disks")
    keys: set[str] = set()
    images: set[str] = set()
    for disk in disks:
        shape(
            disk,
            {"key", "capacity", "max_bytes", "image_id", "name", "hw_firmware_type", "hw_disk_bus"},
        )
        name(disk["key"])
        name(disk["name"])
        identity(disk["image_id"])
        if (
            disk["key"] in keys
            or disk["image_id"] in images
            or type(disk["capacity"]) is not int
            or not 1 <= disk["capacity"] <= 2**46
            or type(disk["max_bytes"]) is not int
            or not 1 <= disk["max_bytes"] <= 2**46
            or disk["hw_firmware_type"] not in {"bios", "uefi"}
            or disk["hw_disk_bus"] not in {"scsi", "virtio", "ide"}
        ):
            raise NativeHeld("invalid_native_copy_disk_mapping")
        keys.add(disk["key"])
        images.add(disk["image_id"])
    return document


class NativeJson:
    """Fixed commissioned origin. Every request is single submission and bounded."""

    def __init__(self, endpoint: NativeEndpoint, header: str) -> None:
        if header not in {"vmware-api-session-id", "X-Auth-Token"}:
            raise NativeHeld("invalid_native_authentication")
        self.endpoint, self.header = endpoint, header
        self.expected_token_sha256: str | None = None

    def credential(self) -> str:
        return credential(self.endpoint)

    def request(
        self,
        method: str,
        path: str,
        boundary: Callable[[], None],
        body: dict[str, Any] | None = None,
        expected: int = 200,
    ) -> Any:
        if (
            method not in {"GET", "POST"}
            or re.fullmatch(r"/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+", path) is None
            or any(part in {".", ".."} for part in path.split("/"))
        ):
            raise NativeHeld("invalid_native_api_route")
        token = self.credential()
        token_sha256 = hashlib.sha256(token.encode()).hexdigest()

        def current() -> None:
            boundary()
            if self.credential() != token or (
                self.expected_token_sha256 is not None
                and token_sha256 != self.expected_token_sha256
            ):
                raise NativeHeld("native_credential_changed")

        headers = {
            self.header: token,
            "Accept": "application/json",
            "Accept-Encoding": "identity",
        }
        data = None if body is None else json.dumps(body, allow_nan=False).encode()
        if data is not None:
            headers["Content-Type"] = "application/json"
            if len(data) > 65536:
                raise NativeHeld("native_request_bound")
        connection = PinnedConnection(self.endpoint)
        try:
            current()
            connection.request(
                method, urlsplit(self.endpoint.base_url).path.rstrip("/") + path, data, headers
            )
            response = connection.getresponse()
            if (
                response.status != expected
                or response.getheader("Content-Encoding", "identity") != "identity"
            ):
                raise NativeHeld("native_api_response_unconfirmed")
            raw = response_bytes(response, 0 if expected == 204 else 2097152, 10, current)
            if not raw:
                return None
            if response.getheader("Content-Type", "").split(";")[0].lower() != "application/json":
                raise NativeHeld("native_api_response_type")
            # Strict duplicate/nonfinite checking also covers arrays and scalar replies.
            return decode(b'{"value":' + raw + b"}", 2097164)["value"]
        except (OSError, http.client.HTTPException):
            raise NativeHeld("native_api_outcome_unknown") from None
        finally:
            connection.close()


class VmwareExport:
    def __init__(self, api: NativeJson, nfc_endpoints: dict[str, NativeEndpoint]) -> None:
        self.api, self.nfc_endpoints = api, nfc_endpoints

    def path(self, plan: dict[str, Any], kind: str, object_id: str, operation: str) -> str:
        return f"/sdk/vim25/{plan['source']['api_version']}/{kind}/{object_id}/{operation}"

    def preflight(self, plan: dict[str, Any], boundary: Callable[[], None]) -> None:
        vm = plan["source"]["vm_id"]
        runtime = self.api.request(
            "GET", self.path(plan, "VirtualMachine", vm, "runtime"), boundary
        )
        config = self.api.request("GET", self.path(plan, "VirtualMachine", vm, "config"), boundary)
        if (
            not isinstance(runtime, dict)
            or runtime.get("powerState") != "poweredOff"
            or not isinstance(config, dict)
            or digest(config) != plan["source"]["config_sha256"]
        ):
            raise NativeHeld("source_vm_not_fenced_or_config_changed")

    def start(self, plan: dict[str, Any], boundary: Callable[[], None]) -> str:
        self.preflight(plan, boundary)
        lease = self.api.request(
            "POST", self.path(plan, "VirtualMachine", plan["source"]["vm_id"], "ExportVm"), boundary
        )
        if (
            not isinstance(lease, dict)
            or lease.get("type") != "HttpNfcLease"
            or not isinstance(lease.get("value"), str)
            or re.fullmatch(r"[A-Za-z0-9_-]{1,128}", lease["value"]) is None
        ):
            raise NativeHeld("export_lease_identity_unconfirmed")
        return str(lease["value"])

    def call(
        self,
        plan: dict[str, Any],
        lease: str,
        operation: str,
        boundary: Callable[[], None],
        body: dict[str, Any] | None = None,
    ) -> Any:
        method = "GET" if operation in {"state", "info"} else "POST"
        return self.api.request(
            method, self.path(plan, "HttpNfcLease", lease, operation), boundary, body
        )

    def ready(
        self, plan: dict[str, Any], lease: str, boundary: Callable[[], None]
    ) -> dict[str, Any]:
        while True:
            state = self.call(plan, lease, "state", boundary)
            if state == "ready":
                info = self.call(plan, lease, "info", boundary)
                if (
                    not isinstance(info, dict)
                    or info.get("entity", {}).get("type") != "VirtualMachine"
                    or info["entity"].get("value") != plan["source"]["vm_id"]
                    or type(info.get("leaseTimeout")) is not int
                    or info["leaseTimeout"] < 15
                ):
                    raise NativeHeld("export_lease_scope_or_timeout_changed")
                return info
            if state != "initializing":
                raise NativeHeld("export_lease_not_ready")
            time.sleep(0.1)

    def download(
        self,
        url: str,
        limit: int,
        target: DownloadSink,
        heartbeat: Callable[[], None],
        *,
        allow_range_continuation: bool = False,
        on_continuation: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        parsed = urlsplit(url)
        origin = f"https://{parsed.netloc}"
        endpoint = self.nfc_endpoints.get(origin)
        if (
            endpoint is None
            or parsed.scheme != "https"
            or parsed.username
            or parsed.password
            or parsed.fragment
            or not parsed.path.startswith("/")
            or any(ord(c) < 33 or ord(c) > 126 for c in url)
            or urlsplit(endpoint.base_url).netloc != parsed.netloc
        ):
            raise NativeHeld("uncommissioned_native_export_destination")
        size, total = 0, None
        etag: str | None = None
        hashes = {algorithm: hashlib.new(algorithm) for algorithm in ("sha256", "sha512")}
        for attempt in range(3 if allow_range_continuation else 1):
            connection = PinnedConnection(endpoint)
            try:
                heartbeat()
                headers = {"Accept-Encoding": "identity"}
                if attempt:
                    if not size or total is None or size >= total or etag is None:
                        raise NativeHeld("native_export_continuation_unconfirmed")
                    try:
                        target.flush()
                    except OSError:
                        raise NativeHeld("native_export_local_io") from None
                    if on_continuation:
                        try:
                            on_continuation(
                                {
                                    "bytes": size,
                                    "total": total,
                                    "prefix_sha256": hashes["sha256"].hexdigest(),
                                    "validator_sha256": hashlib.sha256(etag.encode()).hexdigest(),
                                }
                            )
                        except OSError:
                            raise NativeHeld("native_export_journal_unavailable") from None
                    headers.update({"Range": f"bytes={size}-", "If-Match": etag})
                # The lease URL is already scoped. Never forward platform API credentials.
                connection.request(
                    "GET",
                    parsed.path + ("?" + parsed.query if parsed.query else ""),
                    headers=headers,
                )
                response = connection.getresponse()
                if response.getheader("Content-Encoding", "identity") != "identity":
                    raise NativeHeld("native_export_stream_unconfirmed")
                length = response.getheader("Content-Length")
                if length is not None and (not length.isdigit() or not 0 < int(length) <= limit):
                    raise NativeHeld("native_export_size_bound")
                if not attempt:
                    if response.status != 200:
                        raise NativeHeld("native_export_stream_unconfirmed")
                    total = int(length) if length is not None else None
                    candidate = response.getheader("ETag", "")
                    if response.getheader("Accept-Ranges") == "bytes" and re.fullmatch(
                        r'"[!#-~]{1,254}"', candidate
                    ):
                        etag = candidate
                else:
                    assert total is not None
                    if (
                        response.status != 206
                        or response.getheader("ETag") != etag
                        or response.getheader("Content-Range")
                        != f"bytes {size}-{total - 1}/{total}"
                        or length is None
                        or int(length) != total - size
                    ):
                        raise NativeHeld("native_export_range_changed")
                while True:
                    heartbeat()
                    chunk = response.read1(min(65536, limit + 1 - size))
                    if not chunk:
                        break
                    if size + len(chunk) > limit or (
                        total is not None and size + len(chunk) > total
                    ):
                        raise NativeHeld("native_export_size_bound")
                    try:
                        written = target.write(chunk)
                    except OSError:
                        raise NativeHeld("native_export_local_io") from None
                    if written != len(chunk):
                        raise NativeHeld("native_export_short_write")
                    size += len(chunk)
                    for hasher in hashes.values():
                        hasher.update(chunk)
                if not size or (total is not None and total != size):
                    raise http.client.IncompleteRead(b"")
                heartbeat()
                try:
                    target.flush()
                    target.seek(0)
                except OSError:
                    raise NativeHeld("native_export_local_io") from None
                return {
                    "size": size,
                    **{algorithm: hasher.hexdigest() for algorithm, hasher in hashes.items()},
                }
            except (OSError, http.client.HTTPException):
                if (
                    not allow_range_continuation
                    or attempt == 2
                    or not size
                    or total is None
                    or etag is None
                ):
                    raise NativeHeld("native_export_outcome_unknown") from None
                # Only a read is continued, in the same live lease and authority window.
                # Process restart, expired authority or unknown native writes still hold.
            finally:
                connection.close()
        raise NativeHeld("native_export_outcome_unknown")


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


class NativeVmCopy:
    def __init__(
        self,
        plan_file: Path,
        source: VmwareExport,
        destination: GlanceImport,
        journal: NativeJournal,
        spool: Path,
    ) -> None:
        self.plan_file, self.source, self.destination, self.journal, self.spool = (
            plan_file,
            source,
            destination,
            journal,
            spool,
        )

    def inspect(self, binding: NativeBinding) -> dict[str, Any]:
        plan = copy_plan(decode(protected_read(self.plan_file, 1048576)), binding)
        if (
            not self.spool.is_absolute()
            or self.spool.is_symlink()
            or not self.spool.is_dir()
            or self.spool.stat().st_mode & 0o077
        ):
            raise NativeHeld("private_native_spool_required")
        return {
            "operation_plan_sha256": digest(plan),
            "disk_count": len(plan["disks"]),
            "native_write_authorized": False,
        }

    def execute(self, binding: NativeBinding, boundary: Callable[[], None]) -> None:
        plan = copy_plan(decode(protected_read(self.plan_file, 1048576)), binding)
        deadline = time.monotonic() + plan["max_seconds"]

        def current() -> None:
            if time.monotonic() >= deadline:
                raise NativeHeld("native_copy_deadline")
            boundary()

        self.destination.preflight(binding, current)
        self.journal.record(
            binding, "request_started", {"kind": "export", "source_sha256": digest(plan["source"])}
        )
        lease = self.source.start(plan, current)
        self.journal.record(
            binding, "export_lease", {"lease_id": lease, "source_sha256": digest(plan["source"])}
        )
        info = self.source.ready(plan, lease, current)
        devices = {row["key"]: row for row in info.get("deviceUrl", []) if row.get("disk") is True}
        if set(devices) != {disk["key"] for disk in plan["disks"]} or len(devices) != sum(
            row.get("disk") is True for row in info.get("deviceUrl", [])
        ):
            raise NativeHeld("export_disk_inventory_changed")
        renewed = 0.0

        def heartbeat() -> None:
            nonlocal renewed
            current()
            if time.monotonic() - renewed >= min(5, info["leaseTimeout"] / 3):
                self.source.call(plan, lease, "HttpNfcLeaseProgress", current, {"percent": 0})
                renewed = time.monotonic()

        streams: dict[str, BinaryIO] = {}
        receipts: dict[str, dict[str, Any]] = {}
        try:
            for disk in plan["disks"]:
                stream = tempfile.TemporaryFile(mode="w+b", dir=self.spool)
                streams[disk["key"]] = stream
                receipts[disk["key"]] = self.source.download(
                    devices[disk["key"]]["url"], disk["max_bytes"], stream, heartbeat
                )
            manifest = self.source.call(plan, lease, "HttpNfcLeaseGetManifest", current)
            if not isinstance(manifest, list):
                raise NativeHeld("export_manifest_missing")
            entries = {row["key"]: row for row in manifest if row.get("disk") is True}
            if len(entries) != len(manifest) or set(entries) != set(receipts):
                raise NativeHeld("export_manifest_inventory_changed")
            for disk in plan["disks"]:
                entry, receipt = entries[disk["key"]], receipts[disk["key"]]
                algorithm = entry.get("checksumType")
                if (
                    algorithm not in {"sha256", "sha512"}
                    or entry.get("checksum") != receipt[algorithm]
                    or entry.get("size") != receipt["size"]
                    or entry.get("capacity") != disk["capacity"]
                ):
                    raise NativeHeld("export_manifest_integrity_failed")
                self.journal.record(
                    binding, "disk_transferred", {"resource_key": disk["key"], **receipt}
                )
            self.source.call(plan, lease, "HttpNfcLeaseComplete", current)
            self.journal.record(
                binding, "export_complete", {"lease_id": lease, "manifest_sha256": digest(manifest)}
            )
            for disk in plan["disks"]:
                current()
                self.journal.record(
                    binding,
                    "request_started",
                    {"resource_key": disk["key"], "kind": "image", "payload_sha256": digest(disk)},
                )
                image = self.destination.create(binding, disk, current)
                self.journal.record(
                    binding,
                    "request_accepted",
                    {
                        "resource_key": disk["key"],
                        "kind": "image",
                        "native_id": disk["image_id"],
                        "response_sha256": digest(image),
                    },
                )
                self.destination.stage(
                    binding, disk, streams[disk["key"]], receipts[disk["key"]], current
                )
                self.destination.finish(binding, disk, receipts[disk["key"]], current)
                self.journal.record(
                    binding,
                    "poll_observed",
                    {
                        "resource_key": disk["key"],
                        "native_id": disk["image_id"],
                        "status": "active",
                        **receipts[disk["key"]],
                    },
                )
        finally:
            for opened in streams.values():
                opened.close()
            # An incomplete lease expires natively. Never issue cleanup under expired authority,
            # acquire a second lease, repeat imports or restart the source automatically.


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
