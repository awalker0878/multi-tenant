"""Native json; platform mechanisms retain native semantics."""

import hashlib
import http.client
import json
import re
from collections.abc import Callable
from typing import Any
from urllib.parse import urlsplit

from lifecycle_worker.application.native import (
    NativeHeld,
    decode,
)
from lifecycle_worker.infrastructure.native_http import NativeEndpoint, PinnedConnection, credential
from lifecycle_worker.infrastructure.native_response import response_bytes


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
