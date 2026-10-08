"""One fixed, authenticated Lifecycle authority call. No redirects or retries."""

import http.client
import json
from typing import Any
from urllib.parse import urlsplit

from lifecycle_worker.application.native import NativeHeld, decode
from lifecycle_worker.infrastructure.native_files import protected_read
from lifecycle_worker.infrastructure.native_http import NativeEndpoint, PinnedConnection, credential
from lifecycle_worker.infrastructure.native_response import response_bytes


class LifecycleNativeBoundary:
    def __init__(self, endpoint: NativeEndpoint) -> None:
        self.endpoint = endpoint

    def check(self, stage_grant: dict[str, Any], boundary: str) -> dict[str, Any]:
        endpoint = self.endpoint
        raw = protected_read(endpoint.token_file, 4096).rstrip(b"\r\n")
        if not 32 <= len(raw) <= 4096 or any(c < 33 or c > 126 for c in raw):
            raise NativeHeld("invalid_native_workload_credential")
        payload = json.dumps({"grant": stage_grant, "boundary": boundary}, allow_nan=False).encode()
        if len(payload) > 16384:
            raise NativeHeld("native_boundary_request_bound")

        def current() -> None:
            if credential(endpoint).encode() != raw:
                raise NativeHeld("native_boundary_credential_changed")

        connection = PinnedConnection(endpoint)
        try:
            current()
            connection.request(
                "POST",
                urlsplit(endpoint.base_url).path.rstrip("/") + "/internal/native-grants/checks",
                body=payload,
                headers={
                    "Authorization": "Bearer " + raw.decode("ascii"),
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Accept-Encoding": "identity",
                },
            )
            response = connection.getresponse()
            if (
                response.status != 200
                or response.getheader("Content-Encoding", "identity") != "identity"
                or response.getheader("Content-Type", "").split(";")[0] != "application/json"
            ):
                raise NativeHeld("native_boundary_not_authorized")
            return decode(response_bytes(response, 16384, 5, current), limit=16384)
        except (OSError, http.client.HTTPException):
            raise NativeHeld("native_boundary_unavailable") from None
        finally:
            connection.close()
