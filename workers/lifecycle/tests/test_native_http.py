"""Real TLS transport against synthetic OpenStack responses; no external environment."""

import ssl
import subprocess
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from lifecycle_worker.application.native import NativeHeld
from lifecycle_worker.infrastructure.native_http import NativeEndpoint, NativeReads


@pytest.fixture
def native_tls(tmp_path: Path) -> Iterator[tuple[NativeReads, dict[str, Any]]]:
    key, ca = tmp_path / "server.key", tmp_path / "ca.pem"
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
            "/CN=observer.invalid",
            "-addext",
            "subjectAltName=DNS:observer.invalid",
        ],
        capture_output=True,
        check=True,
    )
    token = tmp_path / "observer.token"
    token.write_text("synthetic-read-only-observer-token")
    fixture: dict[str, Any] = {
        "status": 200,
        "body": b'{"server":{"id":"observed"}}',
        "requests": [],
    }

    class Handler(BaseHTTPRequestHandler):
        def answer(self, reply: dict[str, Any]) -> None:
            if callback := reply.get("before_response"):
                callback()
            self.send_response(reply["status"])
            self.send_header("Content-Type", reply.get("content_type", "application/json"))
            for key in ("Content-Length", "Transfer-Encoding"):
                for value in reply.get("headers", {}).get(key, []):
                    self.send_header(key, value)
            if reply.get("location"):
                self.send_header("Location", reply["location"])
            if reply.get("request_id"):
                self.send_header("x-openstack-request-id", reply["request_id"])
            self.end_headers()
            try:
                self.wfile.write(reply["body"])
            except (BrokenPipeError, ConnectionResetError, ssl.SSLEOFError):
                pass

        def do_POST(self) -> None:
            fixture["requests"].append(
                {
                    "path": self.path,
                    "method": "POST",
                    "authorization": self.headers.get("Authorization"),
                    "body": self.rfile.read(int(self.headers.get("Content-Length", "0"))),
                }
            )
            self.answer(fixture.get("routes", {}).get(self.path, fixture))

        def do_GET(self) -> None:
            fixture["requests"].append(
                {
                    "path": self.path,
                    "method": "GET",
                    "token": self.headers.get("X-Auth-Token"),
                    "subject": self.headers.get("X-Subject-Token"),
                    "nova_version": self.headers.get("X-OpenStack-Nova-API-Version"),
                    "volume_version": self.headers.get("OpenStack-API-Version"),
                }
            )
            self.answer(fixture.get("routes", {}).get(self.path, fixture))

        def log_message(self, format: str, *args: Any) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(ca, key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"https://observer.invalid:{server.server_port}"
    reads = NativeReads(
        {
            name: NativeEndpoint(base + prefix, "127.0.0.1", ca, token)
            for name, prefix in {
                "identity": "/identity/v3",
                "compute": "/compute/v2.1",
                "network": "/network/v2.0",
                "volume": "/volume/v3/project",
            }.items()
        }
    )
    try:
        yield reads, fixture
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_pinned_tls_keeps_catalog_prefix_and_explicit_microversions(
    native_tls: tuple[NativeReads, dict[str, Any]],
) -> None:
    reads, fixture = native_tls
    assert reads.get("compute", "/servers/known")["server"]["id"] == "observed"
    reads.get("volume", "/volumes/known")
    reads.get("identity", "/auth/tokens", subject=True)
    assert fixture["requests"][0]["path"] == "/compute/v2.1/servers/known"
    assert fixture["requests"][0]["nova_version"] == "2.1"
    assert fixture["requests"][1]["volume_version"] == "volume 3.0"
    assert fixture["requests"][2]["subject"] == fixture["requests"][2]["token"]


@pytest.mark.parametrize("status", [301, 307, 401, 403, 404, 429, 500])
def test_native_reads_never_follow_redirect_or_turn_404_into_absence(
    native_tls: tuple[NativeReads, dict[str, Any]], status: int
) -> None:
    reads, fixture = native_tls
    fixture.update(status=status, location="https://foreign.invalid/private")
    with pytest.raises(NativeHeld):
        reads.get("compute", "/servers/known")
    assert len(fixture["requests"]) == 1


@pytest.mark.parametrize(
    "body",
    [b'{"a":1,"a":2}', b'{"value":NaN}', b'{"value":Infinity}', b"x" * 2_097_153],
    ids=["duplicate", "nan", "infinity", "oversized"],
)
def test_tls_response_bounds_and_strict_json(
    native_tls: tuple[NativeReads, dict[str, Any]], body: bytes
) -> None:
    reads, fixture = native_tls
    fixture["body"] = body
    with pytest.raises(NativeHeld):
        reads.get("network", "/ports/known")


def test_hostname_verification_and_credential_rotation(
    native_tls: tuple[NativeReads, dict[str, Any]],
) -> None:
    reads, fixture = native_tls
    endpoint = reads.endpoints["compute"]
    endpoint.token_file.write_text("rotated-synthetic-observer-token")
    reads.get("compute", "/servers/known")
    assert fixture["requests"][0]["token"] == "rotated-synthetic-observer-token"
    reads.endpoints["compute"] = NativeEndpoint(
        endpoint.base_url.replace("observer.invalid", "wrong.invalid"),
        endpoint.address,
        endpoint.ca_file,
        endpoint.token_file,
    )
    with pytest.raises(NativeHeld):
        reads.get("compute", "/servers/known")
    assert len(fixture["requests"]) == 1


@pytest.mark.parametrize(
    "path",
    [
        "//foreign/servers",
        "/servers/../secrets",
        "/servers/x?all_tenants=1",
        "/servers/x%2fother",
        "https://foreign.invalid/x",
    ],
)
def test_arbitrary_paths_denied_before_transport(
    native_tls: tuple[NativeReads, dict[str, Any]], path: str
) -> None:
    reads, fixture = native_tls
    with pytest.raises(NativeHeld):
        reads.get("compute", path)
    assert fixture["requests"] == []


def test_token_rotation_requires_new_scope_read(
    native_tls: tuple[NativeReads, dict[str, Any]],
) -> None:
    reads, fixture = native_tls
    reads.get("identity", "/auth/tokens", subject=True)
    reads.endpoints["identity"].token_file.write_text("different-project-credential")
    with pytest.raises(NativeHeld, match="scope_recheck"):
        reads.get("compute", "/servers/known")
    assert len(fixture["requests"]) == 1


def test_lifecycle_native_boundary_uses_pinned_authenticated_post(
    native_tls: tuple[NativeReads, dict[str, Any]],
) -> None:
    import json

    from lifecycle_worker.infrastructure.native_authority import LifecycleNativeBoundary

    reads, fixture = native_tls
    endpoint = reads.endpoints["compute"]
    endpoint.token_file.write_text("synthetic-distinct-native-worker-token")
    fixture["body"] = b'{"allowed":true}'
    client = LifecycleNativeBoundary(endpoint)
    assert client.check({"binding": "synthetic"}, "preflight") == {"allowed": True}
    request = fixture["requests"][0]
    assert request["path"] == "/compute/v2.1/internal/native-grants/checks"
    assert request["authorization"] == "Bearer synthetic-distinct-native-worker-token"
    assert json.loads(request["body"]) == {
        "grant": {"binding": "synthetic"},
        "boundary": "preflight",
    }


@pytest.mark.parametrize("status", [301, 307, 401, 403, 409, 423, 429, 500])
def test_lifecycle_native_boundary_denials_are_never_retried(
    native_tls: tuple[NativeReads, dict[str, Any]], status: int
) -> None:
    from lifecycle_worker.infrastructure.native_authority import LifecycleNativeBoundary

    reads, fixture = native_tls
    endpoint = reads.endpoints["compute"]
    endpoint.token_file.write_text("synthetic-distinct-native-worker-token")
    fixture.update(status=status, location="https://foreign.invalid/authority")
    with pytest.raises(NativeHeld):
        LifecycleNativeBoundary(endpoint).check({}, "before_api_sequence")
    assert len(fixture["requests"]) == 1


@pytest.mark.parametrize("body", [b'{"a":1,"a":2}', b'{"a":NaN}', b"x" * 16385])
def test_lifecycle_native_boundary_enforces_small_strict_responses(
    native_tls: tuple[NativeReads, dict[str, Any]], body: bytes
) -> None:
    from lifecycle_worker.infrastructure.native_authority import LifecycleNativeBoundary

    reads, fixture = native_tls
    endpoint = reads.endpoints["compute"]
    endpoint.token_file.write_text("synthetic-distinct-native-worker-token")
    fixture["body"] = body
    with pytest.raises(NativeHeld):
        LifecycleNativeBoundary(endpoint).check({}, "preflight")


@pytest.mark.parametrize("client", ["read", "authority", "migration", "owner", "platform"])
@pytest.mark.parametrize(
    "headers,body",
    [
        ({"Content-Length": ["100"]}, b'{"allowed":true}'),
        ({"Content-Length": ["-1"]}, b"{}"),
        ({"Content-Length": ["2", "3"]}, b"{}"),
        ({"Content-Length": ["2"], "Transfer-Encoding": ["chunked"]}, b"0\r\n\r\n"),
        ({"Transfer-Encoding": ["gzip"]}, b"{}"),
        ({"Transfer-Encoding": ["chunked"]}, b"2\r\n{}\r\n"),
    ],
    ids=[
        "truncated_json",
        "negative_length",
        "duplicate_length",
        "ambiguous",
        "encoding",
        "chunk_eof",
    ],
)
def test_native_json_clients_reject_incomplete_or_ambiguous_replies(
    native_tls: tuple[NativeReads, dict[str, Any]],
    client: str,
    headers: dict[str, list[str]],
    body: bytes,
) -> None:
    from dataclasses import replace

    from lifecycle_worker.infrastructure.migration_protocol import OwnerProtocolClient
    from lifecycle_worker.infrastructure.native_authority import LifecycleNativeBoundary
    from lifecycle_worker.infrastructure.native_copy import NativeJson
    from lifecycle_worker.infrastructure.platform_api import PlatformHttp

    reads, fixture = native_tls
    fixture.update(headers=headers, body=body)
    endpoint = reads.endpoints["compute"]
    with pytest.raises(NativeHeld):
        if client == "read":
            reads.get("compute", "/servers/known")
        elif client == "authority":
            LifecycleNativeBoundary(endpoint).check({}, "preflight")
        elif client == "owner":
            OwnerProtocolClient(endpoint).call("/v1/native/effects", {}, lambda: None)
        elif client == "platform":
            PlatformHttp(
                replace(endpoint, base_url=endpoint.base_url.removesuffix("/compute/v2.1")),
                "vmware",
            ).read("vmware", "vm-1")
        else:
            NativeJson(endpoint, "vmware-api-session-id").request("POST", "/export", lambda: None)
    assert len(fixture["requests"]) == 1


@pytest.mark.parametrize("subject", [False, True])
def test_read_rotation_during_response_does_not_establish_scope(
    native_tls: tuple[NativeReads, dict[str, Any]], subject: bool
) -> None:
    reads, fixture = native_tls
    fixture["before_response"] = lambda: reads.endpoints["identity"].token_file.write_text(
        "changed-while-request-in-flight"
    )
    with pytest.raises(NativeHeld, match="credential_changed"):
        reads.get("identity", "/auth/tokens", subject=subject)
    assert reads.subject_token_sha256 is None
    assert len(fixture["requests"]) == 1


def test_complete_chunked_and_length_delimited_json_are_accepted(
    native_tls: tuple[NativeReads, dict[str, Any]],
) -> None:
    reads, fixture = native_tls
    fixture.update(headers={"Transfer-Encoding": ["chunked"]}, body=b"2\r\n{}\r\n0\r\n\r\n")
    assert reads.get("compute", "/servers/known") == {}
    fixture.update(headers={"Content-Length": ["2"]}, body=b"{}")
    assert reads.get("compute", "/servers/known") == {}
