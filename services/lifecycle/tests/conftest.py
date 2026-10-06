"""Optional real PostgreSQL/TLS campaign; core unit tests remain independently runnable."""

import os
import shutil
import socket
import subprocess
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import psycopg
import pytest


@pytest.fixture(scope="session")
def postgres() -> Iterator[dict[str, Any]]:
    bindir = os.environ.get("P05_POSTGRES_BIN")
    if not bindir:
        pytest.skip("P05_POSTGRES_BIN is required for real PostgreSQL qualification")
    private = Path(tempfile.mkdtemp(prefix="p05-lifecycle-postgres-"))
    private.chmod(0o755)
    root = os.getuid() == 0
    if root:
        os.chown(private, 65534, 65534)

    def unprivileged() -> None:
        if root:
            os.setgid(65534)
            os.setuid(65534)

    pg = Path(bindir)
    process = None
    try:
        subprocess.run(
            [
                str(pg / "initdb"),
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
            preexec_fn=unprivileged,
            capture_output=True,
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
                [str(pg / "postgres"), "-D", str(private / "data")],
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
            for _ in range(60):
                try:
                    with psycopg.connect(**settings, autocommit=True) as connection:
                        connection.execute("CREATE ROLE lifecycle_owner NOLOGIN")
                        connection.execute("CREATE ROLE lifecycle_runtime LOGIN")
                        connection.execute("CREATE DATABASE p05_lifecycle OWNER lifecycle_owner")
                    break
                except psycopg.OperationalError:
                    time.sleep(0.1)
            else:
                raise RuntimeError("Disposable PostgreSQL did not start")
            yield settings | {"dbname": "p05_lifecycle"}
    finally:
        if process:
            process.terminate()
            process.wait(timeout=10)
        shutil.rmtree(private)


@pytest.fixture()
def database(postgres: dict[str, Any]) -> Any:
    from lifecycle.infrastructure.store import Postgres

    with psycopg.connect(**postgres, autocommit=True) as c:
        c.execute("DROP SCHEMA IF EXISTS app CASCADE")
        c.execute("CREATE SCHEMA app AUTHORIZATION lifecycle_owner")
        c.execute("GRANT USAGE ON SCHEMA app TO lifecycle_runtime")
        migration = (
            Path(__file__).resolve().parents[1] / "migrations/001_reservations.sql"
        ).read_text()
        c.execute("\n".join(line for line in migration.splitlines() if not line.startswith("\\")))
    return Postgres(postgres | {"user": "lifecycle_runtime"})
