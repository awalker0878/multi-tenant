"""Actual TLS create requests, scope checks, redirects and ambiguous replies."""

import json
from typing import Any
from uuid import uuid4

import pytest
from test_native import binding as binding
from test_native_http import native_tls as native_tls

from lifecycle_worker.application.native import NativeBinding, NativeHeld
from lifecycle_worker.infrastructure.openstack_api import NativeWrites


@pytest.mark.parametrize(
    "service,path,kind,status",
    [
        ("compute", "/servers", "server", 202),
        ("network", "/ports", "port", 201),
        ("volume", "/volumes", "volume", 202),
    ],
)
def test_native_post_has_exact_route_and_native_receipt(
    binding: NativeBinding, native_tls: Any, service: str, path: str, kind: str, status: int
) -> None:
    reads, fixture = native_tls
    user, object_id, request_id = str(uuid4()), str(uuid4()), "req-" + str(uuid4())
    fixture["routes"] = {
        "/identity/v3/auth/tokens": {
            "status": 200,
            "body": json.dumps(
                {
                    "token": {
                        "project": {"id": binding.project_id},
                        "user": {"id": user},
                        "expires_at": "2099-01-01T00:00:00Z",
                    }
                }
            ).encode(),
        }
    }
    fixture.update(
        status=status, body=json.dumps({kind: {"id": object_id}}).encode(), request_id=request_id
    )
    boundaries: list[str] = []
    reply = NativeWrites(reads.endpoints, user, lambda: 100).create(
        binding, service, path, {kind: {"name": "approved"}}, lambda: boundaries.append("current")
    )
    assert reply == {"document": {kind: {"id": object_id}}, "request_id": request_id}
    assert len(boundaries) >= 3  # Submission, streamed response and completion remain authorized.
    assert len(fixture["requests"]) == 2
    assert fixture["requests"][0]["subject"] == "synthetic-read-only-observer-token"
    assert json.loads(fixture["requests"][1]["body"]) == {kind: {"name": "approved"}}


@pytest.mark.parametrize(
    "fault", ["project", "expired", "redirect", "wrong_status", "missing_request_id", "denied"]
)
def test_native_post_failure_is_never_repeated(
    binding: NativeBinding, native_tls: Any, fault: str
) -> None:
    reads, fixture = native_tls
    user = str(uuid4())
    fixture["routes"] = {
        "/identity/v3/auth/tokens": {
            "status": 200,
            "body": json.dumps(
                {
                    "token": {
                        "project": {
                            "id": str(uuid4()) if fault == "project" else binding.project_id
                        },
                        "user": {"id": user},
                        "expires_at": "1970-01-01T00:00:00Z"
                        if fault == "expired"
                        else "2099-01-01T00:00:00Z",
                    }
                }
            ).encode(),
        }
    }
    fixture.update(
        status=302 if fault == "redirect" else (500 if fault == "wrong_status" else 202),
        body=json.dumps({"server": {"id": str(uuid4())}}).encode(),
    )
    if fault != "missing_request_id":
        fixture["request_id"] = "req-" + str(uuid4())

    def boundary() -> None:
        if fault == "denied":
            raise NativeHeld("revoked")

    with pytest.raises(NativeHeld):
        NativeWrites(reads.endpoints, user, lambda: 100).create(
            binding, "compute", "/servers", {"server": {"name": "approved"}}, boundary
        )
    assert sum(row["method"] == "POST" for row in fixture["requests"]) == (
        0 if fault in {"project", "expired", "denied"} else 1
    )


@pytest.mark.parametrize(
    "fault", ["before_send", "during_response", "revoked", "expired", "truncated"]
)
def test_openstack_create_holds_credential_and_authority_changes_without_replay(
    binding: NativeBinding, native_tls: Any, fault: str
) -> None:
    reads, fixture = native_tls
    user = str(uuid4())
    fixture["routes"] = {
        "/identity/v3/auth/tokens": {
            "status": 200,
            "body": json.dumps(
                {
                    "token": {
                        "project": {"id": binding.project_id},
                        "user": {"id": user},
                        "expires_at": "1970-01-01T00:03:20Z",
                    }
                }
            ).encode(),
        }
    }
    fixture.update(status=202, body=b'{"server":{}}', request_id="req-" + str(uuid4()))
    if fault == "during_response":
        fixture["before_response"] = lambda: reads.endpoints["compute"].token_file.write_text(
            "rotated"
        )
    if fault == "truncated":
        fixture["headers"] = {"Content-Length": ["100"]}
    clock = [100]

    def boundary() -> None:
        submitted = any(row["method"] == "POST" for row in fixture["requests"])
        if fault == "before_send":
            reads.endpoints["compute"].token_file.write_text("rotated")
        elif fault == "revoked" and submitted:
            raise NativeHeld("revoked")
        elif fault == "expired" and submitted:
            clock[0] = 200

    with pytest.raises(NativeHeld):
        NativeWrites(reads.endpoints, user, lambda: clock[0]).create(
            binding, "compute", "/servers", {"server": {}}, boundary
        )
    assert sum(row["method"] == "POST" for row in fixture["requests"]) == (fault != "before_send")
