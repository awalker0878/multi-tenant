"Lifecycle-owned PostgreSQL transactions; runtime credentials never run migrations."

import os
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg.rows import dict_row

from lifecycle.application.reservations import Transaction
from lifecycle.infrastructure.foundation import database_host, mounted_secret, required


class PgTransaction:
    def __init__(self, connection: psycopg.Connection[dict[str, Any]]) -> None:
        self.connection = connection

    def execute(self, sql: str, parameters: Sequence[Any] = ()) -> None:
        self.connection.execute(sql, parameters)

    def one(self, sql: str, parameters: Sequence[Any] = ()) -> dict[str, Any] | None:
        return self.connection.execute(sql, parameters).fetchone()

    def all(self, sql: str, parameters: Sequence[Any] = ()) -> list[dict[str, Any]]:
        return self.connection.execute(sql, parameters).fetchall()


class Postgres:
    def __init__(self, parameters: dict[str, Any] | None = None) -> None:
        self.parameters = parameters

    @contextmanager
    def transaction(self) -> Iterator[Transaction]:
        parameters = self.parameters
        if parameters is None:
            if required("DB_SSLMODE") != "verify-full":
                raise ValueError("Lifecycle requires verified database TLS")
            root = required("DB_SSLROOTCERT")
            if not os.path.isabs(root):
                raise ValueError("Lifecycle requires an absolute CA path")
            parameters = {
                "host": database_host(),
                "port": int(required("DB_PORT")),
                "dbname": required("DB_DATABASE"),
                "user": required("DB_USERNAME"),
                "password": mounted_secret("DB_PASSWORD_FILE"),
                "sslmode": "verify-full",
                "sslrootcert": root,
            }
        with psycopg.connect(
            **parameters,
            row_factory=dict_row,
            connect_timeout=2,
            options=(
                "-c statement_timeout=5000 -c lock_timeout=3000 -c "
                "idle_in_transaction_session_timeout=15000"
            ),
        ) as connection:
            yield PgTransaction(connection)
