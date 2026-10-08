"""Strict TLS PostgreSQL and callback transport for the isolated simulation process."""

import http.client
import json
import os
import ssl
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import psycopg
from psycopg.rows import dict_row


def secret(name: str) -> str:
    path = Path(os.environ[name])
    if not path.is_absolute() or path.stat().st_size > 4096:
        raise ValueError("private_mount_required")
    value = path.read_text().strip()
    if not 32 <= len(value) <= 4096 or not value.isascii() or any(c.isspace() for c in value):
        raise ValueError("invalid_credential")
    return value


def custody() -> str:
    from uuid import UUID

    path = Path(os.environ["SIMULATION_CUSTODY_EPOCH_FILE"])
    if not path.is_absolute() or path.stat().st_size > 128:
        raise ValueError("invalid_epoch")
    value = path.read_text().strip()
    if str(UUID(value)) != value:
        raise ValueError("invalid_epoch")
    return value


def connect() -> psycopg.Connection[dict[str, Any]]:
    if os.environ["DB_SSLMODE"] != "verify-full" or not os.path.isabs(os.environ["DB_SSLROOTCERT"]):
        raise ValueError("verified_database_tls_required")
    return psycopg.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        dbname=os.environ["DB_DATABASE"],
        user=os.environ["DB_USERNAME"],
        password=secret("DB_PASSWORD_FILE"),
        sslmode="verify-full",
        sslrootcert=os.environ["DB_SSLROOTCERT"],
        row_factory=dict_row,
        connect_timeout=2,
        options="-c statement_timeout=10000 -c lock_timeout=6000",
    )


def redeem(grant: dict[str, Any]) -> dict[str, Any]:
    url = urlsplit(os.environ["LIFECYCLE_URL"])
    ca = os.environ["LIFECYCLE_CA_FILE"]
    if (
        url.scheme != "https"
        or not url.hostname
        or url.path
        or url.username
        or url.password
        or url.query
        or url.fragment
        or not os.path.isabs(ca)
    ):
        raise ValueError("verified_owner_tls_required")
    connection = http.client.HTTPSConnection(
        url.hostname, url.port or 443, timeout=5, context=ssl.create_default_context(cafile=ca)
    )
    try:
        connection.request(
            "POST",
            "/internal/simulation-grants/redemptions",
            json.dumps(grant),
            {
                "Authorization": "Bearer " + secret("SIMULATOR_LIFECYCLE_CREDENTIAL_FILE"),
                "Content-Type": "application/json",
            },
        )
        response = connection.getresponse()
        raw = response.read(16385)
        if response.status != 200 or len(raw) > 16384:
            raise ValueError("authority_denied")
        body = json.loads(raw)
        if not isinstance(body, dict):
            raise ValueError("invalid_authority")
        return body
    finally:
        connection.close()
