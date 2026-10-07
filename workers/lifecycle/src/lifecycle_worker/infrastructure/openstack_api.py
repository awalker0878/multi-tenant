"""Bounded native OpenStack creates; every uncertain submission retains its claim."""

import hashlib
import http.client
import json
import re
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlsplit

from lifecycle_worker.application.api_plan import native_payload, validate_api_plan
from lifecycle_worker.application.native import (
    NativeBinding,
    NativeHeld,
    NativeJournal,
    decode,
    digest,
    native_identity,
)
from lifecycle_worker.infrastructure.native_files import protected_read
from lifecycle_worker.infrastructure.native_http import (
    NativeEndpoint,
    NativeReads,
    PinnedConnection,
)


class NativeCreates(Protocol):
    def create(
        self,
        binding: NativeBinding,
        service: str,
        path: str,
        body: dict[str, Any],
        boundary: Callable[[], None],
    ) -> dict[str, Any]: ...
    def get(self, service: str, path: str, *, subject: bool = False) -> dict[str, Any]: ...


class NativeWrites(NativeReads):
    def __init__(
        self, endpoints: dict[str, NativeEndpoint], user_id: str, clock: Callable[[], int]
    ) -> None:
        super().__init__(endpoints)
        self.user_id, self.clock = native_identity(user_id), clock

    def authorize(self, binding: NativeBinding) -> None:
        token = self.get("identity", "/auth/tokens", subject=True).get("token", {})
        try:
            expiry = datetime.fromisoformat(token["expires_at"].replace("Z", "+00:00"))
            if (
                expiry.tzinfo is None
                or expiry.timestamp() <= self.clock()
                or token.get("project", {}).get("id") != binding.project_id
                or token.get("user", {}).get("id") != self.user_id
            ):
                raise ValueError
        except (KeyError, TypeError, ValueError):
            raise NativeHeld("native_writer_scope_denied") from None

    def create(
        self,
        binding: NativeBinding,
        service: str,
        path: str,
        body: dict[str, Any],
        boundary: Callable[[], None],
    ) -> dict[str, Any]:
        routes = {
            "compute": ("/servers", "server", 202),
            "network": ("/ports", "port", 201),
            "volume": ("/volumes", "volume", 202),
        }
        if service not in routes or path != routes[service][0] or set(body) != {routes[service][1]}:
            raise NativeHeld("unapproved_native_write_route")
        self.authorize(binding)
        endpoint = self.endpoints[service]
        token = protected_read(endpoint.token_file, 4096).rstrip(b"\r\n")
        if hashlib.sha256(token).hexdigest() != self.subject_token_sha256:
            raise NativeHeld("native_writer_credential_changed")
        payload = json.dumps(body, allow_nan=False, separators=(",", ":")).encode()
        if len(payload) > 262144:
            raise NativeHeld("native_request_bound")
        headers = {
            "X-Auth-Token": token.decode("ascii"),
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Encoding": "identity",
        }
        if service == "compute":
            headers["X-OpenStack-Nova-API-Version"] = "2.1"
        if service == "volume":
            headers["OpenStack-API-Version"] = "volume 3.0"
        connection = PinnedConnection(endpoint)
        try:
            boundary()
            connection.request(
                "POST",
                urlsplit(endpoint.base_url).path.rstrip("/") + path,
                body=payload,
                headers=headers,
            )
            response = connection.getresponse()
            request_id = response.getheader("x-openstack-request-id", "")
            if (
                response.status != routes[service][2]
                or response.getheader("Content-Type", "").split(";")[0] != "application/json"
                or response.getheader("Content-Encoding", "identity") != "identity"
                or re.fullmatch(r"req-[a-f0-9-]{36}", request_id) is None
            ):
                raise NativeHeld("native_create_unconfirmed")
            native_identity(request_id[4:])
            deadline = time.monotonic() + 5
            raw = bytearray()
            while True:
                if time.monotonic() >= deadline:
                    raise NativeHeld("native_create_response_deadline")
                data = response.read1(min(16384, 262145 - len(raw)))
                raw.extend(data)
                if len(raw) > 262144:
                    raise NativeHeld("native_create_response_bound")
                if not data:
                    return {"document": decode(bytes(raw), 262144), "request_id": request_id}
        except (OSError, http.client.HTTPException):
            raise NativeHeld("native_create_requires_reconciliation") from None
        finally:
            connection.close()


class OpenStackApi:
    def __init__(
        self,
        plan_file: Path,
        transport: NativeCreates,
        journal: NativeJournal,
        timeout: float = 600,
        interval: float = 1,
    ) -> None:
        if not 0 < timeout <= 600 or not 0 <= interval <= 5:
            raise NativeHeld("invalid_native_poll_bound")
        self.plan_file, self.transport, self.journal = plan_file, transport, journal
        self.timeout, self.interval = timeout, interval

    def resources(self, binding: NativeBinding) -> dict[str, dict[str, Any]]:
        return validate_api_plan(decode(protected_read(self.plan_file, 1_048_576)), binding)

    def inspect(self, binding: NativeBinding) -> dict[str, Any]:
        resources = self.resources(binding)
        return {
            "operation_plan_sha256": binding.operation_plan_sha256,
            "resource_count": len(resources),
            "native_write_authorized": False,
        }

    def execute(self, binding: NativeBinding, boundary: Callable[[], None]) -> None:
        resources = self.resources(binding)
        objects = self.journal.resources(binding)
        if objects:
            raise NativeHeld("native_attempt_requires_reconciliation")
        deadline = time.monotonic() + self.timeout
        for key, resource in resources.items():
            if time.monotonic() >= deadline:
                raise NativeHeld("native_sequence_deadline")
            kind = resource["kind"]
            service, path = {
                "port": ("network", "/ports"),
                "volume": ("volume", "/volumes"),
                "server": ("compute", "/servers"),
            }[kind]
            body = native_payload(binding, resource, objects)
            boundary()
            self.journal.record(
                binding,
                "request_started",
                {
                    "resource_key": key,
                    "kind": kind,
                    "method": "POST",
                    "path": path,
                    "payload_sha256": digest(body),
                },
            )
            reply = self.transport.create(binding, service, path, body, boundary)
            document = reply["document"].get(kind)
            if not isinstance(document, dict):
                raise NativeHeld("native_object_identity_missing")
            object_id = native_identity(document.get("id"))
            self.journal.record(
                binding,
                "request_accepted",
                {
                    "resource_key": key,
                    "kind": kind,
                    "native_id": object_id,
                    "request_id": reply["request_id"],
                    "response_sha256": digest(reply["document"]),
                },
            )
            objects[key] = {"kind": kind, "id": object_id}
            if kind == "port":
                continue
            expected_status = "available" if kind == "volume" else "ACTIVE"
            while True:
                if time.monotonic() >= deadline:
                    raise NativeHeld("native_poll_deadline")
                boundary()
                observation = self.transport.get(service, path + "/" + object_id)
                current = observation.get(kind, {})
                if current.get("id") != object_id:
                    raise NativeHeld("native_poll_identity_changed")
                status = current.get("status")
                if status == expected_status:
                    self.journal.record(
                        binding,
                        "poll_observed",
                        {
                            "resource_key": key,
                            "native_id": object_id,
                            "status": status,
                            "observation_sha256": digest(observation),
                        },
                    )
                    break
                if not isinstance(status, str) or status.lower().startswith(("error", "deleted")):
                    raise NativeHeld("native_asynchronous_operation_failed")
                time.sleep(min(self.interval, max(0, deadline - time.monotonic())))
