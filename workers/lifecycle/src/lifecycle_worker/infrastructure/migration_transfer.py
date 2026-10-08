"""Bounded artifact transfer under current authority, independent of a platform pair."""

import hashlib
import http.client
import os
import re
import time
from collections.abc import Callable
from typing import Any, BinaryIO, Protocol
from urllib.parse import urlsplit

from lifecycle_worker.application.native import NativeHeld
from lifecycle_worker.infrastructure.native_http import NativeEndpoint, PinnedConnection, credential


class BlobSink(Protocol):
    def write(self, data: bytes) -> int: ...
    def flush(self) -> None: ...


class NativeBlobDownload:
    """Read immutable native image bytes through a commissioned TLS origin."""

    def __init__(self, endpoint: NativeEndpoint, header: str) -> None:
        if header not in {"X-Auth-Token", "X-Ntnx-Api-Key"}:
            raise NativeHeld("invalid_native_authentication")
        self.endpoint, self.header = endpoint, header

    def download(
        self,
        path: str,
        sink: BlobSink,
        size: int,
        algorithm: str,
        checksum: str,
        current: Callable[[], None],
    ) -> dict[str, Any]:
        if (
            re.fullmatch(r"/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+", path) is None
            or any(p in {".", ".."} for p in path.split("/"))
            or type(size) is not int
            or not 0 < size <= 2**46
            or algorithm not in {"sha256", "sha512"}
            or not isinstance(checksum, str)
            or re.fullmatch(
                r"[a-f0-9]{" + str(64 if algorithm == "sha256" else 128) + "}", checksum
            )
            is None
        ):
            raise NativeHeld("invalid_native_blob_contract")
        token = credential(self.endpoint)
        hashes = {name: hashlib.new(name) for name in ("sha256", "sha512")}
        count = 0
        connection = PinnedConnection(self.endpoint)
        try:
            current()
            connection.request(
                "GET",
                urlsplit(self.endpoint.base_url).path.rstrip("/") + path,
                headers={
                    self.header: token,
                    "Accept": "application/octet-stream",
                    "Accept-Encoding": "identity",
                },
            )
            response = connection.getresponse()
            if (
                response.status != 200
                or response.getheader("Content-Encoding", "identity") != "identity"
                or response.getheader("Content-Type", "").split(";")[0].lower()
                not in {"application/octet-stream", "application/binary"}
                or (
                    response.getheader("Content-Length") is not None
                    and response.getheader("Content-Length") != str(size)
                )
            ):
                raise NativeHeld("native_blob_response_unconfirmed")
            while True:
                current()
                if credential(self.endpoint) != token:
                    raise NativeHeld("native_credential_changed")
                chunk = response.read1(min(1048576, size - count + 1))
                if not chunk:
                    break
                count += len(chunk)
                if count > size:
                    raise NativeHeld("native_blob_size_changed")
                if sink.write(chunk) != len(chunk):
                    raise NativeHeld("native_blob_short_write")
                for value in hashes.values():
                    value.update(chunk)
            if count != size or hashes[algorithm].hexdigest() != checksum:
                raise NativeHeld("native_blob_checksum_changed")
            sink.flush()
            return {"size": count, **{name: value.hexdigest() for name, value in hashes.items()}}
        except (OSError, http.client.HTTPException):
            raise NativeHeld("native_blob_transfer_interrupted") from None
        finally:
            connection.close()


class RateBound:
    """A cumulative byte limit and rate cap with authority checks during throttling."""

    def __init__(
        self, stream: BinaryIO, rate: int, limit: int, current: Callable[[], None]
    ) -> None:
        self.stream, self.rate, self.limit, self.current = stream, rate, limit, current
        self.size, self.started = 0, time.monotonic()

    def write(self, data: bytes) -> int:
        self.current()
        self.size += len(data)
        if self.size > self.limit:
            raise NativeHeld("migration_spool_bound")
        while (delay := self.size / self.rate - (time.monotonic() - self.started)) > 0:
            self.current()
            time.sleep(min(delay, 0.1))
        return self.stream.write(data)

    def flush(self) -> None:
        self.stream.flush()
        os.fsync(self.stream.fileno())

    def seek(self, offset: int, whence: int = 0) -> int:
        return self.stream.seek(offset, whence)
