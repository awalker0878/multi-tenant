"""Real disposable PostgreSQL: durable holds, competing attempts and least privilege."""

import os
import shutil
import socket
import subprocess
import tempfile
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import uuid4

import psycopg
import pytest
from psycopg.rows import dict_row

from lifecycle_worker.application.native import NativeBinding, NativeHeld
from lifecycle_worker.infrastructure.native_journal import PostgresNativeJournal


@pytest.fixture(scope="module")
def postgres() -> Iterator[dict[str, Any]]:
    bindir = os.environ.get("P07_POSTGRES_BIN")
    if not bindir:
        pytest.skip("P07_POSTGRES_BIN is required for real journal qualification")
    private = Path(tempfile.mkdtemp(prefix="p07-native-postgres-"))
    private.chmod(0o755)
    root = os.getuid() == 0
    if root:
        os.chown(private, 65534, 65534)

    def unprivileged() -> None:
        if root:
            os.setgid(65534)
            os.setuid(65534)

    process = None
    try:
        subprocess.run(
            [
                str(Path(bindir) / "initdb"),
                "-D",
                str(private / "data"),
                "-A",
                "trust",
                "-U",
                "postgres",
                "--no-locale",
                "--encoding=UTF8",
            ],
            check=True,
            capture_output=True,
            preexec_fn=unprivileged,
        )
        subprocess.run(
            [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-nodes",
                "-keyout",
                str(private / "server.key"),
                "-out",
                str(private / "server.crt"),
                "-days",
                "1",
                "-subj",
                "/CN=localhost",
                "-addext",
                "subjectAltName=IP:127.0.0.1,DNS:localhost",
            ],
            check=True,
            capture_output=True,
        )
        for name in ("server.key", "server.crt"):
            if root:
                os.chown(private / name, 65534, 65534)
            (private / name).chmod(0o600 if name.endswith("key") else 0o644)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        config = private / "data/postgresql.conf"
        config.write_text(
            config.read_text()
            + f"\nlisten_addresses='127.0.0.1'\nport={port}\nunix_socket_directories=''\n"
            f"ssl=on\nssl_cert_file='{private}/server.crt'\nssl_key_file='{private}/server.key'\n"
        )
        with (private / "postgres.log").open("w") as log:
            process = subprocess.Popen(
                [str(Path(bindir) / "postgres"), "-D", str(private / "data")],
                preexec_fn=unprivileged,
                stdout=log,
                stderr=log,
            )
        settings = {
            "host": "127.0.0.1",
            "port": port,
            "user": "postgres",
            "dbname": "postgres",
            "sslmode": "verify-full",
            "sslrootcert": str(private / "server.crt"),
        }
        for _ in range(100):
            try:
                with psycopg.connect(**settings, autocommit=True) as c:
                    c.execute("CREATE ROLE native_owner NOLOGIN")
                    c.execute("CREATE ROLE native_runtime LOGIN")
                    c.execute("CREATE DATABASE native_test OWNER native_owner")
                break
            except psycopg.OperationalError:
                time.sleep(0.1)
        else:
            raise RuntimeError("disposable_postgres_unavailable")
        settings["dbname"] = "native_test"
        with psycopg.connect(**settings) as c:
            c.execute("SET LOCAL ROLE native_owner")
            migration = Path(__file__).parents[1] / "migrations/002_native_attempts.sql"
            c.execute(migration.read_text())
        yield settings | {"user": "native_runtime"}
    finally:
        if process:
            process.terminate()
            process.wait(timeout=10)
        shutil.rmtree(private)


def binding() -> NativeBinding:
    return NativeBinding.parse(
        {
            k: str(uuid4())
            for k in (
                "tenant_id",
                "site_id",
                "project_id",
                "resource_id",
                "job_id",
                "operation_id",
                "attempt_id",
                "campaign_id",
                "executor_id",
                "epoch",
                "state_lineage",
            )
        }
        | {
            "plan_digest": "a" * 64,
            "bundle_sha256": "b" * 64,
            "workspace": "default",
            "state_serial": 1,
            "expires_at": int(time.time()) + 60,
        }
    )


def journal(settings: dict[str, Any]) -> PostgresNativeJournal:
    return PostgresNativeJournal(lambda: psycopg.connect(**settings, row_factory=dict_row))


def test_concurrent_duplicate_deliveries_claim_once(postgres: dict[str, Any]) -> None:
    request = binding()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: journal(postgres).claim(request), range(16)))
    assert results.count(True) == 1 and results.count(False) == 15
    journal(postgres).record(request, "apply_started", {})
    assert not journal(postgres).claim(request)  # a new adapter process cannot repeat it


def test_cross_tenant_workspace_and_changed_attempt_denied(postgres: dict[str, Any]) -> None:
    request = binding()
    assert journal(postgres).claim(request)
    with pytest.raises(NativeHeld, match="binding_conflict"):
        journal(postgres).claim(replace(request, attempt_id=str(uuid4())))
    with pytest.raises(NativeHeld, match="workspace_held"):
        journal(postgres).claim(
            replace(
                request, tenant_id=str(uuid4()), operation_id=str(uuid4()), attempt_id=str(uuid4())
            )
        )
    with pytest.raises(NativeHeld, match="not_bound"):
        journal(postgres).record(replace(request, tenant_id=str(uuid4())), "readback", {})


@pytest.mark.parametrize(
    "statement",
    [
        "DELETE FROM native.workspace_holds",
        "DELETE FROM native.events",
        "UPDATE native.attempts SET fingerprint=repeat('a',64)",
        "TRUNCATE native.workspace_holds",
        "ALTER TABLE native.attempts DROP COLUMN fingerprint",
    ],
)
def test_runtime_cannot_erase_uncertainty(postgres: dict[str, Any], statement: str) -> None:
    with psycopg.connect(**postgres) as connection:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            connection.execute(statement)


def test_unknown_effect_event_and_hold_survive_reconnect(postgres: dict[str, Any]) -> None:
    request = binding()
    original = journal(postgres)
    assert original.claim(request)
    original.record(request, "outcome_unknown", {"reason": "lost_reply"})
    with psycopg.connect(**postgres, row_factory=dict_row) as connection:
        row = connection.execute(
            "SELECT facts FROM native.events WHERE operation_id=%s", (request.operation_id,)
        ).fetchone()
        assert row and row["facts"] == {"reason": "lost_reply"}
    assert not journal(postgres).claim(request)
