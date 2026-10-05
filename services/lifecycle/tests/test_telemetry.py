"""Exercise real spool limits, acknowledgement races and redaction at transport."""

import asyncio
import fcntl
import hashlib
import json
import os
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from uvicorn._types import ASGISendEvent, HTTPScope

from lifecycle.infrastructure.telemetry import LIMIT, BoundedSignalBuffer
from lifecycle.interfaces.http import FoundationApp
from lifecycle.interfaces.telemetry import RequestTelemetry


def test_buffer_saturation_preserves_old_records_and_ack_cannot_delete_new(tmp_path: Path) -> None:
    buffer = BoundedSignalBuffer(tmp_path / "signals")
    assert buffer.append({"value": "a" * 900}) == "buffered"
    original = buffer.snapshot()
    assert buffer.append({"value": "later"}) == "buffered"
    with pytest.raises(ValueError, match="changed"):
        buffer.acknowledge(hashlib.sha256(original).hexdigest())
    for _ in range(100):
        state = buffer.append({"value": "a" * 900})
        if state == "full":
            break
    assert state == "full"
    raw = buffer.snapshot()
    assert raw.startswith(original) and len(raw) <= LIMIT
    assert buffer.append({"value": "a" * 900}) == "full"
    assert buffer.snapshot() == raw
    buffer.acknowledge(hashlib.sha256(raw).hexdigest())
    assert buffer.snapshot() == b""
    assert buffer.append({"value": "recovered"}) == "buffered"


def test_locked_unavailable_oversized_and_symlink_sinks_are_explicit(tmp_path: Path) -> None:
    buffer = BoundedSignalBuffer(tmp_path / "signals")
    buffer.append({"value": "first"})
    with (tmp_path / "signals/events.jsonl").open("rb") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert buffer.append({"value": "contended"}) == "contended"
    assert buffer.append({"value": "a" * 1024}) == "unavailable"
    (tmp_path / "file").touch()
    assert BoundedSignalBuffer(tmp_path / "file").append({}) == "unavailable"
    os.symlink(tmp_path / "signals", tmp_path / "link")
    assert BoundedSignalBuffer(tmp_path / "link").append({}) == "unavailable"
    raw = buffer.snapshot()
    assert b"contended" not in raw


@pytest.mark.parametrize(
    "trace",
    [
        "00-" + "b" * 32 + "-" + "c" * 16 + "-01",
        "00-" + "0" * 32 + "-" + "c" * 16 + "-01",
        "malformed",
        "00-" + "b" * 32 + "-" + "0" * 16 + "-01",
    ],
)
def test_transport_correlation_cannot_authorize_or_leak_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, trace: str
) -> None:
    monkeypatch.setenv("TELEMETRY_ENABLED", "1")
    monkeypatch.setenv("TELEMETRY_ENVIRONMENT", "development")
    monkeypatch.setenv("SOURCE_REVISION", "a" * 40)
    token = tmp_path / "token"
    token.write_text("real-synthetic-health-token" * 2)
    monkeypatch.setenv("HEALTH_TOKEN_FILE", str(token))
    buffer = BoundedSignalBuffer(tmp_path / "signals")
    probe = AsyncMock(return_value=True)
    app = RequestTelemetry(FoundationApp(probe), buffer.append)
    scope: HTTPScope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/health/dependencies",
        "raw_path": b"/health/dependencies",
        "query_string": b"password=CANARY_PRIVATE",
        "root_path": "",
        "headers": [
            (b"traceparent", trace.encode()),
            (b"authorization", b"Bearer CANARY_PRIVATE"),
            (b"cookie", b"CANARY_PRIVATE"),
            (b"x-tenant-id", b"CANARY_PRIVATE"),
            (b"baggage", b"CANARY_PRIVATE"),
        ],
        "client": ("127.0.0.1", 8000),
        "server": ("127.0.0.1", 8080),
    }
    messages: list[ASGISendEvent] = []

    async def send(message: ASGISendEvent) -> None:
        messages.append(message)

    asyncio.run(app(scope, AsyncMock(), send))
    first = messages[0]
    assert first["type"] == "http.response.start" and first["status"] == 401
    headers = dict(first["headers"])
    assert headers[b"x-telemetry-state"] == b"buffered"
    probe.assert_not_called()
    raw = buffer.snapshot()
    assert b"CANARY_PRIVATE" not in raw and token.read_bytes() not in raw
    row = json.loads(raw)
    assert row["trace_id"].encode() == headers[b"x-trace-id"]
    assert row["span_id"].encode() == headers[b"x-span-id"]
    assert row["status"] == 401 and row["source_revision"] == "a" * 40
    if trace == "00-" + "b" * 32 + "-" + "c" * 16 + "-01":
        assert row["trace_id"] == "b" * 32 and row["parent_span_id"] == "c" * 16
    else:
        assert row["parent_span_id"] is None and row["trace_id"] not in {"b" * 32, "0" * 32}
