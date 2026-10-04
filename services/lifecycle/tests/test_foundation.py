"""Authentication, failure isolation and installed persistent HTTP regressions."""

import asyncio
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import psycopg
import pytest
from uvicorn._types import ASGIReceiveEvent, ASGISendEvent, HTTPScope

from lifecycle.infrastructure.foundation import database_ready
from lifecycle.interfaces.http import FoundationApp

TOKEN = "a" * 64


def request(
    probe: AsyncMock,
    path: str = "/health/dependencies",
    authorization: list[tuple[bytes, bytes]] | None = None,
    method: str = "GET",
) -> list[ASGISendEvent]:
    scope: HTTPScope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": authorization or [],
        "client": ("127.0.0.1", 8000),
        "server": ("127.0.0.1", 8080),
        "state": {},
    }
    events: list[ASGISendEvent] = []

    async def send(event: ASGISendEvent) -> None:
        events.append(event)

    async def receive() -> ASGIReceiveEvent:
        return {"type": "http.disconnect"}

    asyncio.run(FoundationApp(probe)(scope, receive, send))
    return events


def response(events: list[ASGISendEvent]) -> tuple[int, dict[str, str], dict[str, str | bool]]:
    start, body = events
    assert start["type"] == "http.response.start"
    assert body["type"] == "http.response.body"
    return (
        start["status"],
        {name.decode(): value.decode() for name, value in start["headers"]},
        json.loads(body["body"]),
    )


@pytest.fixture
def token_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "health-token"
    path.write_text(TOKEN + "\n")
    monkeypatch.setenv("HEALTH_TOKEN_FILE", str(path))
    return path


def test_authentication_precedes_database_and_rejects_duplicate_headers(token_file: Path) -> None:
    probe = AsyncMock(return_value=True)
    for headers in (
        [],
        [(b"authorization", b"Bearer " + b"b" * 64)],
        [(b"authorization", b"Bearer " + TOKEN.encode())] * 2,
    ):
        status, response_headers, payload = response(request(probe, authorization=headers))
        assert status == 401
        assert response_headers["cache-control"] == "no-store"
        assert "www-authenticate" in response_headers
        assert payload["status"] == "unauthorized"
        assert TOKEN not in str(payload)
    probe.assert_not_awaited()


def test_dependency_health_reads_rotated_token_and_keeps_product_unready(token_file: Path) -> None:
    probe = AsyncMock(return_value=True)
    header = [(b"authorization", b"Bearer " + TOKEN.encode())]
    status, _, payload = response(request(probe, authorization=header))
    assert status == 200
    assert payload == {
        "service": "lifecycle",
        "scope": "foundation_dependencies",
        "status": "ready",
        "native_operations_enabled": False,
    }
    token_file.write_text("b" * 64)
    assert response(request(probe, authorization=header))[0] == 401
    probe.assert_awaited_once()
    assert response(request(probe, path="/health/ready"))[0] == 503
    probe.assert_awaited_once()


def test_missing_or_invalid_auth_secret_fails_closed(token_file: Path) -> None:
    probe = AsyncMock(return_value=True)
    for value in ("short", TOKEN + "\n" * 5000, "a" * 4097):
        token_file.write_text(value)
        assert response(request(probe))[0] == 503
    token_file.unlink()
    assert response(request(probe))[0] == 503
    probe.assert_not_awaited()


def test_dependency_failure_is_generic_and_retryable(token_file: Path) -> None:
    probe = AsyncMock(return_value=False)
    status, headers, payload = response(
        request(probe, authorization=[(b"authorization", b"Bearer " + TOKEN.encode())])
    )
    assert status == 503
    assert headers["retry-after"] == "10"
    assert payload["reason"] == "dependencies_unavailable"
    assert payload["native_operations_enabled"] is False


@pytest.mark.parametrize(
    ("path", "method", "status"),
    [("/health/live", "GET", 200), ("/unknown", "GET", 404), ("/health/dependencies", "POST", 405)],
)
def test_unrelated_requests_do_not_access_dependencies(path: str, method: str, status: int) -> None:
    probe = AsyncMock(return_value=True)
    assert response(request(probe, path=path, method=method))[0] == status
    probe.assert_not_awaited()


@pytest.fixture
def database_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    password = tmp_path / "database-password"
    password.write_text("synthetic-test-password\n")
    root = tmp_path / "root.crt"
    root.write_text("placeholder only; these unit tests do not establish TLS")
    for name, value in {
        "DB_HOST": "postgres",
        "DB_PORT": "5432",
        "DB_DATABASE": "lifecycle",
        "DB_USERNAME": "lifecycle_app",
        "DB_PASSWORD_FILE": str(password),
        "DB_SSLMODE": "verify-full",
        "DB_SSLROOTCERT": str(root),
    }.items():
        monkeypatch.setenv(name, value)
    return password


@pytest.mark.parametrize(
    "rows",
    [
        [],
        [("lifecycle_app", "lifecycle", 2)],
        [("other", "lifecycle", 1)],
        [("lifecycle_app", "other", 1)],
        [("lifecycle_app", "lifecycle", 1)] * 2,
    ],
)
def test_schema_and_database_identity_must_match(
    database_settings: Path, rows: list[tuple[str, str, int]]
) -> None:
    connection = MagicMock()
    connection.__aenter__.return_value = connection
    cursor = MagicMock()
    connection.cursor.return_value.__aenter__.return_value = cursor
    cursor.execute = AsyncMock()
    cursor.fetchone = AsyncMock(return_value=(1,))
    cursor.fetchall = AsyncMock(return_value=rows)
    with patch(
        "lifecycle.infrastructure.foundation.psycopg.AsyncConnection.connect",
        new=AsyncMock(return_value=connection),
    ):
        assert asyncio.run(database_ready()) is False


def test_readonly_tls_probe_rereads_password(database_settings: Path) -> None:
    connection = MagicMock()
    connection.__aenter__.return_value = connection
    cursor = MagicMock()
    connection.cursor.return_value.__aenter__.return_value = cursor
    cursor.execute = AsyncMock()
    cursor.fetchone = AsyncMock(return_value=(1,))
    cursor.fetchall = AsyncMock(return_value=[("lifecycle_app", "lifecycle", 1)])
    connect = AsyncMock(return_value=connection)
    with patch("lifecycle.infrastructure.foundation.psycopg.AsyncConnection.connect", new=connect):
        assert asyncio.run(database_ready()) is True
        assert connect.call_args.kwargs["password"] == "synthetic-test-password"
        assert connect.call_args.kwargs["sslmode"] == "verify-full"
        assert connect.call_args.kwargs["connect_timeout"] == 2
        assert "default_transaction_read_only=on" in connect.call_args.kwargs["options"]
        assert "statement_timeout=2000" in connect.call_args.kwargs["options"]
        database_settings.write_text("rotated-test-password")
        assert asyncio.run(database_ready()) is True
        assert connect.call_args.kwargs["password"] == "rotated-test-password"


def test_postgres_errors_do_not_escape(database_settings: Path) -> None:
    with patch(
        "lifecycle.infrastructure.foundation.psycopg.AsyncConnection.connect",
        new=AsyncMock(side_effect=psycopg.OperationalError("secret connection details")),
    ):
        assert asyncio.run(database_ready()) is False


@pytest.mark.parametrize("mode", ["disable", "prefer", "require", "verify-ca", ""])
def test_tls_cannot_be_downgraded(
    database_settings: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    monkeypatch.setenv("DB_SSLMODE", mode)
    connect = AsyncMock()
    with patch("lifecycle.infrastructure.foundation.psycopg.AsyncConnection.connect", new=connect):
        assert asyncio.run(database_ready()) is False
    connect.assert_not_awaited()


@pytest.fixture(scope="module")
def http_server(tmp_path_factory: pytest.TempPathFactory) -> Iterator[tuple[str, Path]]:
    root = tmp_path_factory.mktemp("persistent-http")
    token = root / "health-token"
    token.write_text(TOKEN)
    with socket.socket() as socket_handle:
        socket_handle.bind(("127.0.0.1", 0))
        port = socket_handle.getsockname()[1]
    env = {
        name: value
        for name, value in os.environ.items()
        if name != "PYTHONPATH" and not name.startswith("DB_")
    }
    env["HEALTH_TOKEN_FILE"] = str(token)
    with subprocess.Popen(
        [
            sys.executable,
            "-I",
            "-m",
            "lifecycle.bootstrap.server",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    ) as process:
        try:
            url = f"http://127.0.0.1:{port}"
            deadline = time.monotonic() + 10
            while True:
                assert process.poll() is None, "Persistent HTTP process stopped during startup"
                try:
                    with urllib.request.urlopen(url + "/health/live", timeout=0.5) as result:
                        assert result.status == 200
                    break
                except (urllib.error.URLError, TimeoutError):
                    assert time.monotonic() < deadline, "Persistent HTTP startup timed out"
                    time.sleep(0.05)
            yield url, token
        finally:
            process.terminate()
            try:
                output, _ = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                output, _ = process.communicate(timeout=5)
            assert TOKEN not in output


def test_installed_server_handles_multiple_requests_and_auth_rotation(
    http_server: tuple[str, Path],
) -> None:
    url, token = http_server
    for route, status, credential in [
        ("/health/live", 200, None),
        ("/health/ready", 503, None),
        ("/health/dependencies", 401, None),
        ("/health/dependencies", 503, TOKEN),
    ]:
        headers = {} if credential is None else {"Authorization": "Bearer " + credential}
        req = urllib.request.Request(url + route, headers=headers)
        try:
            result = urllib.request.urlopen(req, timeout=5)
        except urllib.error.HTTPError as error:
            result = error
        with result:
            assert result.status == status
            assert result.headers["Cache-Control"] == "no-store"
            assert json.loads(result.read())["service"] == "lifecycle"
    token.write_text("b" * 64)
    req = urllib.request.Request(
        url + "/health/dependencies", headers={"Authorization": "Bearer " + TOKEN}
    )
    with pytest.raises(urllib.error.HTTPError) as rejected:
        urllib.request.urlopen(req, timeout=5)
    assert rejected.value.code == 401


@pytest.mark.parametrize(
    "host", ["/var/run/postgresql", "@socket", "postgres,/tmp", "postgres other", "host;user=x", ""]
)
def test_non_tcp_and_multihost_configuration_cannot_bypass_tls(
    database_settings: Path, monkeypatch: pytest.MonkeyPatch, host: str
) -> None:
    monkeypatch.setenv("DB_HOST", host)
    connect = AsyncMock()
    with patch("lifecycle.infrastructure.foundation.psycopg.AsyncConnection.connect", new=connect):
        assert asyncio.run(database_ready()) is False
    connect.assert_not_awaited()
