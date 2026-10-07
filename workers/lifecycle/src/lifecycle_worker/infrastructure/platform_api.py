"""Pinned native lifecycle transport and durable VMware/AHV adapter components."""

import hashlib
import http.client
import json
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlsplit

from lifecycle_worker.application.native import (
    NativeBinding,
    NativeHeld,
    NativeJournal,
    decode,
    digest,
    identity,
)
from lifecycle_worker.application.platform_plan import achieved, request, validate
from lifecycle_worker.infrastructure.extension_trust import ExtensionTrust
from lifecycle_worker.infrastructure.native_files import protected_read
from lifecycle_worker.infrastructure.native_http import NativeEndpoint, PinnedConnection


class PlatformTransport(Protocol):
    def read(self, platform: str, object_id: str) -> tuple[dict[str, Any], str]: ...
    def send(
        self, platform: str, document: dict[str, Any], boundary: Callable[[], None]
    ) -> dict[str, Any]: ...


class PlatformHttp:
    def __init__(self, endpoint: NativeEndpoint, platform: str, read_only: bool = False) -> None:
        if platform not in {"vmware", "ahv"} or urlsplit(endpoint.base_url).path not in {"", "/"}:
            raise NativeHeld("invalid_platform_origin")
        self.endpoint, self.platform, self.read_only = endpoint, platform, read_only

    def call(
        self, method: str, path: str, body: Any, extra: dict[str, str], boundary: Callable[[], None]
    ) -> dict[str, Any]:
        patterns = {
            "vmware": (
                r"/api/vcenter/vm/vm-[1-9][0-9]{0,15}"
                r"(?:(?:/power\?action=(?:start|stop))|(?:/guest/power\?action=shutdown)"
                r"|(?:/hardware/(?:cpu|memory)))?"
            ),
            "ahv": (
                r"/api/vmm/v4\.0/ahv/config/vms/[a-f0-9-]{36}"
                r"(?:/\$actions/(?:power-on|power-off|shutdown))?"
            ),
        }
        if (
            re.fullmatch(patterns[self.platform], path) is None
            or method not in {"GET", "POST", "PATCH", "PUT"}
            or (self.read_only and method != "GET")
            or not set(extra).issubset({"If-Match", "Ntnx-Request-Id"})
        ):
            raise NativeHeld("unapproved_platform_request")
        token = protected_read(self.endpoint.token_file, 4096).rstrip(b"\r\n")
        if not token or any(c < 33 or c > 126 for c in token):
            raise NativeHeld("invalid_platform_credential")
        fingerprint = hashlib.sha256(token).digest()

        def current() -> None:
            boundary()
            now = protected_read(self.endpoint.token_file, 4096).rstrip(b"\r\n")
            if hashlib.sha256(now).digest() != fingerprint:
                raise NativeHeld("platform_credential_changed")

        auth = "vmware-api-session-id" if self.platform == "vmware" else "X-Ntnx-Api-Key"
        headers = {
            auth: token.decode("ascii"),
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            **extra,
        }
        payload = (
            None
            if body is None
            else json.dumps(body, allow_nan=False, separators=(",", ":")).encode()
        )
        if payload is not None:
            if len(payload) > 1048576:
                raise NativeHeld("platform_request_bound")
            headers["Content-Type"] = "application/json"
        connection = PinnedConnection(self.endpoint)
        try:
            current()
            connection.request(method, path, body=payload, headers=headers)
            response = connection.getresponse()
            expected = 200 if method == "GET" else (204 if self.platform == "vmware" else 202)
            if (
                response.status != expected
                or response.getheader("Content-Encoding", "identity") != "identity"
            ):
                raise NativeHeld("platform_response_requires_reconciliation")
            if (
                expected != 204
                and response.getheader("Content-Type", "").split(";")[0].lower()
                != "application/json"
            ):
                raise NativeHeld("invalid_platform_response")
            raw = bytearray()
            deadline = time.monotonic() + 10
            while True:
                current()
                if time.monotonic() >= deadline:
                    raise NativeHeld("platform_response_deadline")
                data = response.read1(min(65536, 2097153 - len(raw)))
                raw.extend(data)
                if len(raw) > 2097152:
                    raise NativeHeld("platform_response_bound")
                if not data:
                    current()
                    break
            return {
                "document": decode(bytes(raw)) if raw else {},
                "etag": response.getheader("ETag", ""),
                "status": response.status,
            }
        except (OSError, http.client.HTTPException):
            raise NativeHeld("platform_response_requires_reconciliation") from None
        finally:
            connection.close()

    def read(self, platform: str, object_id: str) -> tuple[dict[str, Any], str]:
        if platform != self.platform:
            raise NativeHeld("platform_transport_mismatch")
        base = "/api/vcenter/vm/" if platform == "vmware" else "/api/vmm/v4.0/ahv/config/vms/"
        reply = self.call("GET", base + object_id, None, {}, lambda: None)
        document = reply["document"] if platform == "vmware" else reply["document"].get("data")
        if not isinstance(document, dict):
            raise NativeHeld("platform_readback_missing")
        return document, reply["etag"]

    def send(
        self, platform: str, document: dict[str, Any], boundary: Callable[[], None]
    ) -> dict[str, Any]:
        if platform != self.platform or set(document) != {"method", "path", "body", "headers"}:
            raise NativeHeld("platform_transport_mismatch")
        return self.call(
            document["method"], document["path"], document["body"], document["headers"], boundary
        )


class PlatformApi:
    def __init__(
        self,
        plan_file: Path,
        envelope: Path,
        artifact: Path,
        trust: ExtensionTrust,
        transport: PlatformTransport,
        journal: NativeJournal,
    ) -> None:
        self.plan_file, self.envelope, self.artifact, self.trust = (
            plan_file,
            envelope,
            artifact,
            trust,
        )
        self.transport, self.journal = transport, journal

    def plan(self, binding: NativeBinding) -> dict[str, Any]:
        return validate(decode(protected_read(self.plan_file, 1048576)), binding)

    def inspect(self, binding: NativeBinding) -> dict[str, Any]:
        plan = self.plan(binding)
        manifest = self.trust.admit(
            self.envelope,
            self.artifact,
            plan["adapter_sha256"],
            {k: plan[k] for k in ("operation", "tuple_sha256", "route_sha256")},
        )
        if manifest["adapter_id"] != plan["platform"] + "-lifecycle-v1":
            raise NativeHeld("extension_platform_mismatch")
        return {
            "operation_plan_sha256": binding.operation_plan_sha256,
            "adapter_sha256": plan["adapter_sha256"],
            "native_write_authorized": False,
        }

    def execute(self, binding: NativeBinding, boundary: Callable[[], None]) -> None:
        self.inspect(binding)
        plan = self.plan(binding)
        current, etag = self.transport.read(plan["platform"], plan["object_id"])
        document = request(plan, current, etag, binding.operation_id)

        def current_boundary() -> None:
            self.inspect(binding)
            boundary()

        current_boundary()
        self.journal.record(
            binding,
            "request_started",
            {
                "resource_key": "vm",
                "kind": "vm",
                "method": document["method"],
                "path": document["path"],
                "payload_sha256": digest(document),
            },
        )
        reply = self.transport.send(plan["platform"], document, current_boundary)
        task_id = None
        if plan["platform"] == "ahv":
            task_id = reply["document"].get("data", {}).get("extId")
            if (
                not isinstance(task_id, str)
                or re.fullmatch(r"[A-Za-z0-9:_-]{1,160}", task_id) is None
            ):
                raise NativeHeld("ahv_task_identity_missing")
        self.journal.record(
            binding,
            "request_accepted",
            {
                "resource_key": "vm",
                "kind": "vm",
                "native_id": plan["object_id"],
                "request_id": task_id or binding.operation_id,
                "response_sha256": digest(reply),
            },
        )


class PlatformObserver:
    def __init__(
        self,
        plan_file: Path,
        transport: PlatformTransport,
        clock: Callable[[], int],
        observer_id: str,
        writer_id: str,
        require_independent_credentials: Callable[[], None],
    ) -> None:
        self.plan_file, self.transport, self.clock = plan_file, transport, clock
        self.observer_id, self.writer_id = identity(observer_id), identity(writer_id)
        if self.observer_id == self.writer_id:
            raise NativeHeld("independent_platform_principal_required")
        self.require_independent_credentials = require_independent_credentials

    def observe(self, binding: NativeBinding, objects: dict[str, Any]) -> dict[str, Any]:
        plan = validate(decode(protected_read(self.plan_file, 1048576)), binding)
        if objects and objects != {"vm": {"kind": "vm", "id": plan["object_id"]}}:
            raise NativeHeld("platform_receipt_identity_conflict")
        self.require_independent_credentials()
        current, _ = self.transport.read(plan["platform"], plan["object_id"])
        self.require_independent_credentials()
        return {
            "binding_sha256": binding.fingerprint,
            "independent": True,
            "observer_id": self.observer_id,
            "writer_id": self.writer_id,
            "outcome": "observed_present" if achieved(plan, current) else "held",
            "observed_at": self.clock(),
            "observation_sha256": digest(current),
            "application_ready": False,
        }


def distinct_credentials(writer: NativeEndpoint, reader: NativeEndpoint) -> None:
    if (
        writer.base_url != reader.base_url
        or writer.address != reader.address
        or hashlib.sha256(protected_read(writer.token_file, 4096).strip()).digest()
        == hashlib.sha256(protected_read(reader.token_file, 4096).strip()).digest()
    ):
        raise NativeHeld("independent_platform_read_identity_required")
