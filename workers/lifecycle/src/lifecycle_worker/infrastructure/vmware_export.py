"""Vmware export; platform mechanisms retain native semantics."""



import hashlib
import http.client
import re
import time
from collections.abc import Callable
from typing import Any, Protocol
from urllib.parse import urlsplit

from lifecycle_worker.application.native import (
    NativeHeld,
    digest,
)
from lifecycle_worker.infrastructure.native_http import NativeEndpoint, PinnedConnection
from lifecycle_worker.infrastructure.native_json import NativeJson


MIGRATION_API_CAPABILITIES = frozenset({"vm.disk.export"})


class DownloadSink(Protocol):
    def write(self, data: bytes) -> int: ...
    def flush(self) -> None: ...
    def seek(self, offset: int, whence: int = 0) -> int: ...


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
            method,
            self.path(plan, "HttpNfcLease", lease, operation),
            boundary,
            body,
            expected=204 if operation in {"HttpNfcLeaseProgress", "HttpNfcLeaseComplete"} else 200,
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
        if not isinstance(url, str) or any(ord(c) < 33 or ord(c) > 126 for c in url):
            raise NativeHeld("uncommissioned_native_export_destination")
        try:
            parsed = urlsplit(url)
            if parsed.username or parsed.password:
                raise NativeHeld("uncommissioned_native_export_destination")
            if parsed.hostname == "*":
                api_origin = urlsplit(self.api.endpoint.base_url)
                if api_origin.scheme != "https" or not api_origin.hostname:
                    raise NativeHeld("uncommissioned_native_export_destination")
                host = api_origin.hostname
                if ":" in host:
                    host = "[" + host + "]"
                host += ":" + str(parsed.port) if parsed.port is not None else ""
                parsed = parsed._replace(netloc=host)
        except ValueError:
            raise NativeHeld("uncommissioned_native_export_destination") from None
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
