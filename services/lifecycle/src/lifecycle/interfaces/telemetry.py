"""Redacted HTTP response timing with untrusted W3C v00 correlation only."""

import os
import re
import secrets
import time
from collections.abc import Callable

from uvicorn._types import (
    ASGI3Application,
    ASGIReceiveCallable,
    ASGISendCallable,
    ASGISendEvent,
    Scope,
)

TRACE = re.compile(r"00-([0-9a-f]{32})-([0-9a-f]{16})-0[01]\Z")
ROUTES = {"/health/live", "/health/ready", "/health/dependencies"}
METHODS = {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}


class RequestTelemetry:
    def __init__(self, app: ASGI3Application, append: Callable[[dict[str, object]], str]) -> None:
        self.app = app
        self.append = append

    async def __call__(
        self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = [v for k, v in scope["headers"] if k == b"traceparent"]
        match = (TRACE.fullmatch(incoming[0].decode("ascii", "replace"))
                 if len(incoming) == 1 else None)
        valid = match is not None and int(match[1], 16) != 0 and int(match[2], 16) != 0
        trace_id = match[1] if valid and match else secrets.token_hex(16)
        parent_id = match[2] if valid and match else None
        span_id = secrets.token_hex(8)
        started, timestamp = time.monotonic_ns(), time.time_ns() // 1000
        emitted = False

        def record(status: int) -> str:
            if os.environ.get("TELEMETRY_ENABLED") != "1":
                return "disabled"
            revision = os.environ.get("SOURCE_REVISION", "")
            environment = os.environ.get("TELEMETRY_ENVIRONMENT", "")
            if not re.fullmatch(r"[0-9a-f]{40}", revision) or environment not in {
                "development", "p01-compose", "p01-kubernetes"
            }:
                return "unavailable"
            return self.append({
                "schema_version": 1, "event": "http.response", "service": "lifecycle",
                "source_revision": revision, "environment": environment,
                "timestamp_unix_us": timestamp, "trace_id": trace_id,
                "span_id": span_id, "parent_span_id": parent_id,
                "route": scope["path"] if scope["path"] in ROUTES else "other",
                "method": scope["method"] if scope["method"] in METHODS else "OTHER",
                "status": status, "duration_us": (time.monotonic_ns() - started) // 1000,
            })

        async def observed_send(message: ASGISendEvent) -> None:
            nonlocal emitted
            if message["type"] == "http.response.start":
                state = record(message["status"])
                emitted = True
                message["headers"] = [*message["headers"],
                    (b"x-trace-id", trace_id.encode()), (b"x-span-id", span_id.encode()),
                    (b"x-telemetry-state", state.encode()),
                ]
            await send(message)

        try:
            await self.app(scope, receive, observed_send)
        except Exception:
            if not emitted:
                record(500)
            raise
