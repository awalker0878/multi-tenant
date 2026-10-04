"""Read-only PostgreSQL diagnostic using verified TLS and mounted credentials."""

import asyncio
import ipaddress
import os
import re
from pathlib import Path

import psycopg


def required(name: str) -> str:
    value = os.environ[name]
    if not value:
        raise ValueError("Empty foundation setting")
    return value


def mounted_secret(name: str) -> str:
    path = Path(required(name))
    if not path.is_absolute():
        raise ValueError("Foundation secrets require absolute file paths")
    with path.open("rb") as handle:
        raw = handle.read(4097)
    if len(raw) > 4096:
        raise ValueError("Oversized foundation secret")
    value = raw.decode("utf-8").rstrip("\r\n")
    if not value or "\n" in value or "\r" in value or "\0" in value:
        raise ValueError("Invalid foundation secret")
    return value


def database_host() -> str:
    host = required("DB_HOST")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        # libpq ignores sslmode for Unix sockets. Only a single DNS/IP endpoint
        # is allowed, including rejecting multi-host lists with socket fallbacks.
        labels = host.removesuffix(".").split(".")
        if len(host) > 253 or any(
            re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label) is None
            for label in labels
        ):
            raise ValueError("Foundation database requires a single TCP host") from None
    return host


async def database_ready() -> bool:
    """Re-open credentials per request; disclose neither settings nor driver errors."""
    try:
        if required("DB_SSLMODE") != "verify-full":
            return False
        root = Path(required("DB_SSLROOTCERT"))
        if not root.is_absolute() or not root.is_file():
            return False
        user = required("DB_USERNAME")
        database = required("DB_DATABASE")
        port = int(required("DB_PORT"))
        if not 1 <= port <= 65535:
            return False
        # The outer deadline also bounds DNS/connection setup and all statements.
        async with asyncio.timeout(5):
            async with await psycopg.AsyncConnection.connect(
                host=database_host(),
                port=port,
                dbname=database,
                user=user,
                password=mounted_secret("DB_PASSWORD_FILE"),
                sslmode="verify-full",
                sslrootcert=str(root),
                connect_timeout=2,
                options=(
                    "-c default_transaction_read_only=on "
                    "-c statement_timeout=2000 -c search_path=pg_catalog"
                ),
            ) as connection:
                async with connection.cursor() as cursor:
                    await cursor.execute("SELECT 1")
                    if await cursor.fetchone() != (1,):
                        return False
                    await cursor.execute(
                        "SELECT current_user, current_database(), version "
                        "FROM app.foundation_schema ORDER BY version LIMIT 2"
                    )
                    return await cursor.fetchall() == [(user, database, 1)]
    except (KeyError, ValueError, OSError, psycopg.Error, TimeoutError):
        return False
