"""Controlled TLS endpoint observations; these are not native platform qualification."""

import json
import ssl
import subprocess
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest

from inventory_worker.infrastructure.native import CollectionFailure, collect, exchange


class Endpoint(BaseHTTPRequestHandler):
    calls: list[tuple[str, str]] = []
    mode = "normal"

    def log_message(self, format: str, *args: Any) -> None:
        pass

    def do_GET(self) -> None:
        type(self).calls.append(("GET", self.path))
        mode = type(self).mode
        if mode == "redirect":
            self.send_response(302)
            self.send_header("Location", "https://169.254.169.254/latest/meta-data")
            self.end_headers()
            return
        code = {"forbidden": 403, "throttle": 429}.get(mode, 200)
        path = urlsplit(self.path)
        query = parse_qs(path.query)
        if path.path.startswith("/api/vcenter"):
            key = path.path.split("/")[-1]
            data: Any = [{key: key + "-1", "name": "<script>inert</script>"}]
            if mode == "too_many":
                data *= 101
        else:
            key = (
                "networks"
                if path.path.endswith("/networks")
                else "volumes"
                if path.path.endswith("/volumes/detail")
                else "servers"
            )
            rows = (
                []
                if query.get("marker")
                else [
                    {
                        "id": "id-a",
                        "name": "Observed",
                        "tenant_id": "foreign" if mode == "foreign" else "project-a",
                        "created": "2026-10-06T00:00:00Z",
                        "status": "ACTIVE",
                        "adminPass": "never-copy-this",
                    }
                ]
            )
            data = {
                key: rows,
                key + "_links": [{"rel": "next", "href": "https://169.254.169.254/hostile"}],
            }
        raw = (
            b'{"servers":[],"servers":[{}]}'
            if mode == "duplicate_json"
            else json.dumps(data).encode()
        )
        if mode == "oversize":
            raw = b" " * 2097153
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        if mode == "compressed":
            self.send_header("Content-Encoding", "gzip")
        self.end_headers()
        try:
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError, ssl.SSLError):
            pass


@pytest.fixture
def endpoint(tmp_path: Path) -> Iterator[dict[str, Any]]:
    cert, key = tmp_path / "cert.pem", tmp_path / "key.pem"
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
            str(cert),
            "-days",
            "1",
            "-subj",
            "/CN=native.example",
            "-addext",
            "subjectAltName=DNS:native.example",
        ],
        check=True,
        capture_output=True,
    )
    token = tmp_path / "token"
    token.write_text("native-test-token-" + "a" * 32)
    Endpoint.calls = []
    Endpoint.mode = "normal"
    server = ThreadingHTTPServer(("127.0.0.1", 0), Endpoint)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield {
            "base_url": f"https://native.example:{server.server_port}",
            "addresses": ["127.0.0.1"],
            "ca_file": str(cert),
            "credential_file": str(token),
            "kind": "server",
            "api_version": "2.1",
        }
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def policy(stream: dict[str, Any], platform: str = "openstack") -> dict[str, Any]:
    return {
        "platform": platform,
        "native_scope": "project-a",
        "streams": [stream],
        "coverage_reference": "synthetic-observer",
    }


def test_verified_tls_pinned_address_pagination_and_response_redaction(
    endpoint: dict[str, Any],
) -> None:
    first = collect(policy(endpoint), 0, None)
    assert first["next_cursor"] == "id-a" and first["terminal"] is False
    assert "never-copy-this" not in json.dumps(first)
    last = collect(policy(endpoint), 0, first["next_cursor"])
    assert last["observations"] == [] and last["terminal"] is True
    assert all(method == "GET" for method, _ in Endpoint.calls)
    assert len(Endpoint.calls) == 2 and "marker=id-a" in Endpoint.calls[-1][1]
    assert all("169.254" not in path for _, path in Endpoint.calls)


@pytest.mark.parametrize(
    "mode,reason",
    [
        ("redirect", "unsafe_destination"),
        ("forbidden", "permission_denied"),
        ("throttle", "throttled"),
        ("foreign", "permission_denied"),
        ("duplicate_json", "invalid_response"),
        ("compressed", "invalid_response"),
        ("oversize", "invalid_response"),
    ],
)
def test_native_faults_are_explicit_and_never_follow_links(
    endpoint: dict[str, Any], mode: str, reason: str
) -> None:
    Endpoint.mode = mode
    with pytest.raises(CollectionFailure, match=reason):
        collect(policy(endpoint), 0, None)
    assert len(Endpoint.calls) == 1


def test_unapproved_address_and_hostname_mismatch_do_not_disclose_credentials(
    endpoint: dict[str, Any],
) -> None:
    with pytest.raises(CollectionFailure, match="unsafe_destination"):
        collect(policy(endpoint | {"addresses": ["169.254.169.254"]}), 0, None)
    assert Endpoint.calls == []
    port = urlsplit(endpoint["base_url"]).port
    with pytest.raises(CollectionFailure, match="transport_unavailable"):
        collect(policy(endpoint | {"base_url": f"https://wrong.example:{port}"}), 0, None)
    assert Endpoint.calls == []


@pytest.mark.parametrize("kind", ["server", "network", "datastore"])
def test_vmware_scope_and_missing_incarnation_stay_explicit(
    endpoint: dict[str, Any], kind: str
) -> None:
    result = collect(
        policy(endpoint | {"kind": kind, "api_version": "vcenter-api"}, "vmware"), 0, None
    )
    assert result["terminal"] is True
    assert result["observations"][0]["incarnation"] is None
    assert "datacenters=project-a" in Endpoint.calls[0][1]


def test_vmware_does_not_truncate_lists_or_infer_ahv_support(endpoint: dict[str, Any]) -> None:
    Endpoint.mode = "too_many"
    with pytest.raises(CollectionFailure, match="invalid_response"):
        collect(policy(endpoint | {"api_version": "vcenter-api"}, "vmware"), 0, None)
    with pytest.raises(CollectionFailure, match="unsupported_api"):
        collect(policy(endpoint, "ahv"), 0, None)


def test_native_transport_rejects_supplied_url_paths(endpoint: dict[str, Any]) -> None:
    with pytest.raises(CollectionFailure, match="unsafe_destination"):
        exchange(endpoint, "https://metadata.example/", {})
    with pytest.raises(CollectionFailure, match="unsafe_destination"):
        collect(policy(endpoint), 0, "a&all_tenants=1")
    assert Endpoint.calls == []
