"""The native worker transport pins its destination and sends each grant at most once."""

import json
import ssl
import subprocess
import threading
from collections.abc import Iterator
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from lifecycle.domain.admission import digest
from lifecycle.domain.execution import Rejected
from lifecycle.infrastructure.native_effects import NativeWorkerEffects, NativeWorkerEndpoint


@pytest.fixture
def peer(tmp_path: Path) -> Iterator[tuple[NativeWorkerEndpoint, dict[str, Any]]]:
    key, ca, token = tmp_path / "key.pem", tmp_path / "ca.pem", tmp_path / "worker.token"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(key),
            "-out",
            str(ca),
            "-days",
            "1",
            "-subj",
            "/CN=worker.invalid",
            "-addext",
            "subjectAltName=DNS:worker.invalid",
        ],
        capture_output=True,
        check=True,
    )
    token.write_text("a" * 32)
    token.chmod(0o600)
    fixture: dict[str, Any] = {
        "status": 200,
        "requests": [],
        "body": None,
        "content_type": "application/json",
    }

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            data = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            fixture["requests"].append(
                (self.path, self.headers.get("Authorization"), json.loads(data))
            )
            body = fixture["body"]
            if body is None:
                body = json.dumps(
                    {
                        "grant_sha256": digest(json.loads(data)["grant"]),
                        "submitted": True,
                        "readiness_established": False,
                        "retry_authorized": False,
                    }
                ).encode()
            self.send_response(fixture["status"])
            self.send_header("Content-Type", fixture["content_type"])
            if fixture.get("length") != "absent":
                self.send_header("Content-Length", fixture.get("length", str(len(body))))
            self.send_header("Location", "https://foreign.invalid/never")
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError, ssl.SSLEOFError):
                pass

        def log_message(self, format: str, *args: Any) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.load_cert_chain(ca, key)
    server.socket = tls.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield (
            NativeWorkerEndpoint(
                f"https://worker.invalid:{server.server_port}", "127.0.0.1", ca, token
            ),
            fixture,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_exact_effect_submission_and_credential_rotation(peer: Any) -> None:
    endpoint, fixture = peer
    worker = str(uuid4())
    grant = {"executor_id": worker, "grant_id": str(uuid4())}
    transport = NativeWorkerEffects({worker: endpoint})
    transport.execute(grant)
    assert fixture["requests"] == [
        ("/internal/native-effects", "Bearer " + "a" * 32, {"grant": grant})
    ]
    endpoint.credential_file.write_text("b" * 32)
    transport.execute(grant | {"grant_id": str(uuid4())})
    assert fixture["requests"][1][1] == "Bearer " + "b" * 32


@pytest.mark.parametrize("status", [301, 307, 401, 403, 404, 423, 429, 500])
def test_redirect_denial_and_failure_never_retry(peer: Any, status: int) -> None:
    endpoint, fixture = peer
    fixture["status"] = status
    worker = str(uuid4())
    with pytest.raises(Rejected, match="native_effect_requires_reconciliation"):
        NativeWorkerEffects({worker: endpoint}).execute({"executor_id": worker})
    assert len(fixture["requests"]) == 1


@pytest.mark.parametrize(
    "body",
    [
        b"[]",
        b'{"a":1,"a":2}',
        b'{"a":NaN}',
        b"x" * 4097,
        b'{"submitted":true,"readiness_established":true}',
    ],
)
def test_uncertain_or_forged_receipt_is_held(peer: Any, body: bytes) -> None:
    endpoint, fixture = peer
    fixture["body"] = body
    worker = str(uuid4())
    with pytest.raises(Rejected):
        NativeWorkerEffects({worker: endpoint}).execute({"executor_id": worker})
    assert len(fixture["requests"]) == 1


def test_unregistered_worker_wrong_hostname_and_bad_credential_never_submit(peer: Any) -> None:
    endpoint, fixture = peer
    worker = str(uuid4())
    for endpoints in (
        {},
        {
            worker: replace(
                endpoint, origin=endpoint.origin.replace("worker.invalid", "wrong.invalid")
            )
        },
    ):
        with pytest.raises(Rejected):
            NativeWorkerEffects(endpoints).execute({"executor_id": worker})
    endpoint.credential_file.chmod(0o666)
    with pytest.raises(Rejected):
        NativeWorkerEffects({worker: endpoint}).execute({"executor_id": worker})
    assert not fixture["requests"]


def test_boolean_coercion_cannot_forge_effect_receipt(peer: Any) -> None:
    endpoint, fixture = peer
    worker = str(uuid4())
    grant = {"executor_id": worker}
    fixture["body"] = json.dumps(
        {
            "grant_sha256": digest(grant),
            "submitted": 1,
            "readiness_established": False,
            "retry_authorized": False,
        }
    ).encode()
    with pytest.raises(Rejected):
        NativeWorkerEffects({worker: endpoint}).execute(grant)
    assert len(fixture["requests"]) == 1


@pytest.mark.parametrize("length", ["absent", "4097", "-1", "1, 1", "4096"])
def test_missing_ambiguous_or_truncated_framing_is_held(peer: Any, length: str) -> None:
    endpoint, fixture = peer
    fixture["length"] = length
    worker = str(uuid4())
    with pytest.raises(Rejected):
        NativeWorkerEffects({worker: endpoint}).execute({"executor_id": worker})
    assert len(fixture["requests"]) == 1
