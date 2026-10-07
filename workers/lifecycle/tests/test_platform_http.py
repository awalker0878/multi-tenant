"""Verify actual TLS, native auth headers and denial behavior for both P09 transports."""

import json
import ssl
import subprocess
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from lifecycle_worker.application.native import NativeHeld
from lifecycle_worker.infrastructure.native_http import NativeEndpoint
from lifecycle_worker.infrastructure.platform_api import PlatformHttp, distinct_credentials


@pytest.fixture
def platform_peer(tmp_path: Path) -> Iterator[tuple[NativeEndpoint, dict[str, Any]]]:
    key, ca, token = tmp_path / "key.pem", tmp_path / "ca.pem", tmp_path / "token"
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
            "/CN=platform.invalid",
            "-addext",
            "subjectAltName=DNS:platform.invalid",
        ],
        capture_output=True,
        check=True,
    )
    token.write_text("synthetic-platform-credential")
    token.chmod(0o600)
    fixture: dict[str, Any] = {
        "status": 200,
        "body": b'{"power_state":"POWERED_OFF"}',
        "requests": [],
    }

    class Handler(BaseHTTPRequestHandler):
        def respond(self) -> None:
            fixture["requests"].append(
                {
                    "method": self.command,
                    "path": self.path,
                    "headers": dict(self.headers),
                    "body": self.rfile.read(int(self.headers.get("Content-Length", "0"))),
                }
            )
            self.send_response(fixture["status"])
            self.send_header("Content-Type", "application/json")
            self.send_header("Location", "https://foreign.invalid/never")
            self.send_header("ETag", '"version-7"')
            self.end_headers()
            self.wfile.write(fixture["body"])

        def do_GET(self) -> None:
            self.respond()

        def do_POST(self) -> None:
            self.respond()

        def do_PUT(self) -> None:
            self.respond()

        def do_PATCH(self) -> None:
            self.respond()

        def log_message(self, format: str, *args: Any) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(ca, key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield (
            NativeEndpoint(
                f"https://platform.invalid:{server.server_port}", "127.0.0.1", ca, token
            ),
            fixture,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_vmware_read_and_write_use_session_auth_and_204(
    platform_peer: tuple[NativeEndpoint, dict[str, Any]],
) -> None:
    endpoint, peer = platform_peer
    http = PlatformHttp(endpoint, "vmware")
    assert http.read("vmware", "vm-42")[0]["power_state"] == "POWERED_OFF"
    peer.update(status=204, body=b"")
    count = []
    http.send(
        "vmware",
        {
            "method": "POST",
            "path": "/api/vcenter/vm/vm-42/power?action=start",
            "body": None,
            "headers": {},
        },
        lambda: count.append(True),
    )
    assert count == [True]
    assert (
        peer["requests"][0]["headers"]["vmware-api-session-id"] == "synthetic-platform-credential"
    )
    assert peer["requests"][1]["method"] == "POST"


def test_ahv_put_preserves_etag_idempotency_and_api_key(
    platform_peer: tuple[NativeEndpoint, dict[str, Any]],
) -> None:
    endpoint, peer = platform_peer
    http = PlatformHttp(endpoint, "ahv")
    vm = "10000000-0000-4000-8000-000000000001"
    peer.update(body=json.dumps({"data": {"extId": vm}}).encode())
    assert http.read("ahv", vm) == ({"extId": vm}, '"version-7"')
    peer.update(status=202, body=json.dumps({"data": {"extId": "task-1"}}).encode())
    http.send(
        "ahv",
        {
            "method": "PUT",
            "path": "/api/vmm/v4.0/ahv/config/vms/" + vm,
            "body": {"extId": vm},
            "headers": {"If-Match": '"version-7"', "Ntnx-Request-Id": vm},
        },
        lambda: None,
    )
    headers = peer["requests"][1]["headers"]
    assert headers["X-Ntnx-Api-Key"] == "synthetic-platform-credential"
    assert headers["If-Match"] == '"version-7"' and headers["Ntnx-Request-Id"] == vm


@pytest.mark.parametrize("status", [301, 307, 401, 403, 404, 409, 412, 429, 500])
def test_platform_transport_never_follows_redirect_or_retries(
    platform_peer: tuple[NativeEndpoint, dict[str, Any]], status: int
) -> None:
    endpoint, peer = platform_peer
    peer["status"] = status
    with pytest.raises(NativeHeld):
        PlatformHttp(endpoint, "vmware").read("vmware", "vm-42")
    assert len(peer["requests"]) == 1


def test_observer_cannot_write_or_reuse_writer_secret(
    platform_peer: tuple[NativeEndpoint, dict[str, Any]],
) -> None:
    endpoint, peer = platform_peer
    with pytest.raises(NativeHeld, match="unapproved"):
        PlatformHttp(endpoint, "vmware", read_only=True).send(
            "vmware",
            {
                "method": "POST",
                "path": "/api/vcenter/vm/vm-42/power?action=start",
                "body": None,
                "headers": {},
            },
            lambda: None,
        )
    assert peer["requests"] == []
    with pytest.raises(NativeHeld, match="independent"):
        distinct_credentials(endpoint, endpoint)
