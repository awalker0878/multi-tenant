"""Fixed-origin native readback with verified TLS, address pins and protected tokens."""

import hashlib
import http.client
import ipaddress
import re
import socket
import ssl
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from lifecycle_worker.application.native import NativeHeld, decode
from lifecycle_worker.infrastructure.native_files import protected_read
from lifecycle_worker.infrastructure.native_response import response_bytes


@dataclass(frozen=True)
class NativeEndpoint:
    base_url: str
    address: str
    ca_file: Path
    token_file: Path


def credential(endpoint: NativeEndpoint) -> str:
    raw = protected_read(endpoint.token_file, 4096).rstrip(b"\r\n")
    if not raw or any(c < 33 or c > 126 for c in raw):
        raise NativeHeld("invalid_native_credential")
    return raw.decode("ascii")


class PinnedConnection(http.client.HTTPSConnection):
    def __init__(self, endpoint: NativeEndpoint) -> None:
        url = urlsplit(endpoint.base_url)
        address = ipaddress.ip_address(endpoint.address)
        if (
            url.scheme != "https"
            or not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
            or not endpoint.ca_file.is_absolute()
            or address.is_link_local
            or address.is_multicast
            or address.is_unspecified
            or re.fullmatch(r"(?:/[A-Za-z0-9._~-]+)*/?", url.path) is None
            or any(p in {".", ".."} for p in url.path.split("/"))
        ):
            raise NativeHeld("unsafe_native_destination")
        self.verified_context = ssl.create_default_context(cafile=endpoint.ca_file)
        super().__init__(url.hostname, url.port or 443, timeout=3, context=self.verified_context)
        self.address = endpoint.address

    def connect(self) -> None:
        raw = socket.create_connection((self.address, self.port), timeout=3)
        try:
            self.sock = self.verified_context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise


class NativeReads:
    def __init__(
        self,
        endpoints: dict[str, NativeEndpoint],
        identity_check: Callable[[], None] = lambda: None,
    ) -> None:
        if (
            set(endpoints) != {"identity", "compute", "network", "volume"}
            or len({e.token_file for e in endpoints.values()}) != 1
        ):
            raise NativeHeld("one_project_scoped_observer_token_required")
        self.endpoints = endpoints
        self.identity_check = identity_check
        self.subject_token_sha256: str | None = None

    def get(self, service: str, path: str, *, subject: bool = False) -> dict[str, Any]:
        if (
            service not in self.endpoints
            or re.fullmatch(r"/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+", path) is None
            or ".." in path
        ):
            raise NativeHeld("unsafe_native_read")
        endpoint = self.endpoints[service]
        token = credential(endpoint)
        token_sha256 = hashlib.sha256(token.encode()).hexdigest()
        if subject:
            if service != "identity" or path != "/auth/tokens":
                raise NativeHeld("invalid_native_subject_read")
        elif self.subject_token_sha256 is not None and token_sha256 != self.subject_token_sha256:
            raise NativeHeld("observer_token_changed_requires_scope_recheck")

        def current() -> None:
            self.identity_check()
            if credential(endpoint) != token:
                raise NativeHeld("native_read_credential_changed")

        headers = {
            "X-Auth-Token": token,
            "Accept": "application/json",
            "Accept-Encoding": "identity",
        }
        if subject:
            headers["X-Subject-Token"] = token
        if service == "compute":
            headers["X-OpenStack-Nova-API-Version"] = "2.1"
        if service == "volume":
            headers["OpenStack-API-Version"] = "volume 3.0"
        connection = PinnedConnection(endpoint)
        try:
            current()
            connection.request(
                "GET", urlsplit(endpoint.base_url).path.rstrip("/") + path, headers=headers
            )
            response = connection.getresponse()
            if (
                response.status != 200
                or response.getheader("Content-Encoding", "identity") != "identity"
                or not response.getheader("Content-Type", "").lower().startswith("application/json")
            ):
                # A 404 or empty listing never establishes sealed absence after an uncertain create.
                raise NativeHeld("native_read_not_observed")
            result = decode(response_bytes(response, 2_097_152, 10, current))
            if subject:
                self.subject_token_sha256 = token_sha256
            return result
        except (OSError, http.client.HTTPException):
            raise NativeHeld("native_read_unavailable") from None
        finally:
            connection.close()
