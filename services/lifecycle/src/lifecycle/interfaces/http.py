"""Minimal ASGI transport for process and authenticated foundation diagnostics."""

import hmac
import json
import os
from pathlib import Path

from uvicorn._types import ASGIReceiveCallable, ASGISendCallable, HTTPScope, Scope

from lifecycle.application.foundation import FoundationProbe


def health_token() -> bytes:
    path = Path(os.environ["HEALTH_TOKEN_FILE"])
    if not path.is_absolute():
        raise ValueError("Health token requires an absolute file path")
    with path.open("rb") as handle:
        raw = handle.read(4097)
    if len(raw) > 4096:
        raise ValueError("Oversized health token")
    value = raw.rstrip(b"\r\n")
    if not 32 <= len(value) <= 4096 or any(byte < 33 or byte > 126 for byte in value):
        raise ValueError("Invalid health token")
    return value


class FoundationApp:
    def __init__(self, check_dependencies: FoundationProbe) -> None:
        self.check_dependencies = check_dependencies

    async def __call__(
        self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        if scope["type"] != "http":
            return
        status = 404
        payload: dict[str, str | bool] = {"service": "lifecycle", "status": "not_found"}
        headers = [(b"content-type", b"application/json"), (b"cache-control", b"no-store")]
        if scope["path"] in {"/health/live", "/health/ready", "/health/dependencies"}:
            if scope["method"] != "GET":
                status = 405
                payload["status"] = "method_not_allowed"
                headers.append((b"allow", b"GET"))
            elif scope["path"] == "/health/live":
                status = 200
                payload.update(status="alive", scope="process")
            elif scope["path"] == "/health/ready":
                status = 503
                payload.update(status="not_ready", scope="service", reason="foundation_only")
            else:
                status, result = await self.dependencies(scope)
                payload.update(result)
        if status == 503:
            headers.append((b"retry-after", b"10"))
        if status == 401:
            headers.append((b"www-authenticate", b'Bearer realm="foundation"'))
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        headers.append((b"content-length", str(len(body)).encode()))
        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({"type": "http.response.body", "body": body})

    async def dependencies(self, scope: HTTPScope) -> tuple[int, dict[str, str | bool]]:
        payload: dict[str, str | bool] = {
            "scope": "foundation_dependencies",
            "native_operations_enabled": False,
        }
        try:
            expected = b"Bearer " + health_token()
        except (KeyError, ValueError, OSError):
            payload.update(status="not_ready", reason="health_authentication_unavailable")
            return 503, payload
        authorization = [value for name, value in scope["headers"] if name == b"authorization"]
        if len(authorization) != 1 or not hmac.compare_digest(authorization[0], expected):
            payload.update(status="unauthorized")
            return 401, payload
        if await self.check_dependencies():
            payload.update(status="ready")
            return 200, payload
        payload.update(status="not_ready", reason="dependencies_unavailable")
        return 503, payload
