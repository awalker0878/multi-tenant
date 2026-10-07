"""One authenticated native worker submission; uncertain replies are never retried."""

import http.client
import ipaddress
import json
import os
import re
import socket
import ssl
import stat
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from lifecycle.domain.admission import digest
from lifecycle.domain.execution import Rejected, decode, identity


@dataclass(frozen=True)
class NativeWorkerEndpoint:
    origin: str
    address: str
    ca_file: Path
    credential_file: Path


class NativeEffectConnection(http.client.HTTPSConnection):
    def __init__(self, endpoint: NativeWorkerEndpoint) -> None:
        url = urlsplit(endpoint.origin)
        address = ipaddress.ip_address(endpoint.address)
        if (
            url.scheme != "https"
            or not url.hostname
            or url.path
            or url.username
            or url.password
            or url.query
            or url.fragment
            or not endpoint.ca_file.is_absolute()
            or address.is_link_local
            or address.is_multicast
            or address.is_unspecified
        ):
            raise Rejected("unsafe_native_worker", 423)
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


def credential(path: Path) -> str:
    if not path.is_absolute() or any(part.is_symlink() for part in (path, *path.parents)):
        raise Rejected("protected_native_credential_required", 423)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o022 or info.st_size > 4098:
            raise Rejected("protected_native_credential_required", 423)
        value = handle.read(4099).rstrip(b"\r\n").decode("ascii")
    if not re.fullmatch(r"[A-Za-z0-9_-]{32,4096}", value):
        raise Rejected("invalid_native_workload_credential", 423)
    return value


class NativeWorkerEffects:
    def __init__(self, workers: dict[str, NativeWorkerEndpoint]) -> None:
        self.workers = {identity(worker): endpoint for worker, endpoint in workers.items()}

    def execute(self, grant: dict[str, Any]) -> None:
        connection = None
        try:
            endpoint = self.workers[identity(grant["executor_id"])]
            data = json.dumps({"grant": grant}, allow_nan=False, separators=(",", ":")).encode()
            if len(data) > 16384:
                raise Rejected("native_effect_request_bound", 423)
            token = credential(endpoint.credential_file)
            connection = NativeEffectConnection(endpoint)
            connection.request(
                "POST",
                "/internal/native-effects",
                data,
                {
                    "Authorization": "Bearer " + token,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Accept-Encoding": "identity",
                },
            )
            if connection.sock is None:
                raise Rejected("native_effect_connection_lost", 423)
            # Native API execution is bounded independently. Timeout leaves the prepared grant held.
            deadline = time.monotonic() + 620
            stream = connection.sock
            stream.settimeout(620)
            response = connection.getresponse()
            if (
                response.status != 200
                or response.getheader("Content-Encoding", "identity") != "identity"
                or response.getheader("Content-Type", "").split(";")[0] != "application/json"
                or response.getheader("Transfer-Encoding") is not None
            ):
                raise Rejected("native_effect_unconfirmed", 423)
            length = response.getheader("Content-Length", "")
            if not re.fullmatch(r"[0-9]{1,4}", length) or not 0 < int(length) <= 4096:
                raise Rejected("native_effect_response_bound", 423)
            expected_length = int(length)
            raw = bytearray()
            while len(raw) < expected_length:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise Rejected("native_effect_response_deadline", 423)
                stream.settimeout(min(5, remaining))
                part = response.read1(expected_length - len(raw))
                if not part:
                    raise Rejected("native_effect_response_incomplete", 423)
                raw.extend(part)
            expected = {
                "grant_sha256": digest(grant),
                "submitted": True,
                "readiness_established": False,
                "retry_authorized": False,
            }
            if digest(decode(bytes(raw))) != digest(expected):
                raise Rejected("native_effect_receipt_mismatch", 423)
        except Exception:
            raise Rejected("native_effect_requires_reconciliation", 423) from None
        finally:
            if connection is not None:
                connection.close()
