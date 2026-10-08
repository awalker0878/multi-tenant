"""Private Assurance invalidation request authentication and bounded transport."""

import asyncio
import json
from pathlib import Path
from typing import Any, cast
from unittest.mock import Mock

import pytest

from planning.application.qualification_invalidations import QualificationInvalidations
from planning.interfaces.qualification_invalidations import QualificationInvalidationApp

CREDENTIAL = "q" * 64


def exchange(
    app: QualificationInvalidationApp,
    body: bytes,
    *,
    method: str = "POST",
    credential: str | None = CREDENTIAL,
    content_type: bytes = b"application/json",
) -> tuple[int, dict[str, Any]]:
    sent: list[dict[str, Any]] = []
    headers: list[tuple[bytes, bytes]] = [(b"content-type", content_type)]
    if credential is not None:
        headers.append((b"authorization", ("Bearer " + credential).encode()))

    async def run() -> None:
        scope: Any = {
            "type": "http",
            "path": "/internal/qualification-events",
            "method": method,
            "query_string": b"",
            "headers": headers,
        }

        async def receive() -> Any:
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message: Any) -> None:
            sent.append(message)

        await app(scope, receive, send)

    asyncio.run(run())
    assert (b"cache-control", b"no-store, private") in sent[0]["headers"]
    return sent[0]["status"], json.loads(sent[1]["body"])


@pytest.fixture
def receiver(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[QualificationInvalidationApp, Mock]:
    token = tmp_path / "credential"
    token.write_text(CREDENTIAL)
    monkeypatch.setenv("PLANNING_ASSURANCE_INVALIDATION_CREDENTIAL_FILE", str(token))
    inbox = Mock()
    inbox.accept.return_value = {
        "persisted": True,
        "event_id": "10000000-0000-4000-8000-000000000001",
        "scope_sha256": "a" * 64,
        "authority_epoch": 1,
        "event_sha256": "b" * 64,
    }
    return QualificationInvalidationApp(cast(QualificationInvalidations, inbox)), inbox


def test_exact_authenticated_held_event_is_acked_after_receiver_persistence(
    receiver: tuple[QualificationInvalidationApp, Mock],
) -> None:
    app, inbox = receiver
    body = b'{"event_id":"10000000-0000-4000-8000-000000000001"}'
    status, reply = exchange(app, body)
    assert status == 200 and reply["persisted"] is True
    inbox.accept.assert_called_once_with({"event_id": "10000000-0000-4000-8000-000000000001"})


@pytest.mark.parametrize(
    ("credential", "status"),
    [(None, 401), ("different", 401), ("q" * 63, 401)],
)
def test_wrong_or_missing_authority_denied_without_touching_inbox(
    receiver: tuple[QualificationInvalidationApp, Mock], credential: str | None, status: int
) -> None:
    app, inbox = receiver
    assert exchange(app, b"{}", credential=credential)[0] == status
    inbox.accept.assert_not_called()


@pytest.mark.parametrize(
    ("body", "method", "content_type", "status"),
    [
        (b"{}", "GET", b"application/json", 405),
        (b"{}", "POST", b"text/plain", 415),
        (b'{"event_id":1,"event_id":2}', "POST", b"application/json", 422),
        (b"x" * 8193, "POST", b"application/json", 413),
    ],
)
def test_untrusted_payload_fails_before_mutation(
    receiver: tuple[QualificationInvalidationApp, Mock],
    body: bytes,
    method: str,
    content_type: bytes,
    status: int,
) -> None:
    app, inbox = receiver
    assert exchange(app, body, method=method, content_type=content_type)[0] == status
    inbox.accept.assert_not_called()
