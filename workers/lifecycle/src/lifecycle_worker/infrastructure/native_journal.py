"""Worker-owned PostgreSQL certainty ledger. No Lifecycle database access."""

import json
from collections.abc import Callable
from typing import Any

import psycopg

from lifecycle_worker.application.native import NativeBinding, NativeHeld


class PostgresNativeJournal:
    def __init__(self, connect: Callable[[], psycopg.Connection[dict[str, Any]]]) -> None:
        self.connect = connect

    def claim(self, binding: NativeBinding) -> bool:
        with self.connect() as connection:
            # Serialize competing first claims, including before either row exists.
            connection.execute("SELECT pg_advisory_xact_lock(7707001)")
            prior = connection.execute(
                "SELECT fingerprint FROM native.attempts WHERE operation_id=%s",
                (binding.operation_id,),
            ).fetchone()
            if prior:
                if prior["fingerprint"] != binding.fingerprint:
                    raise NativeHeld("native_operation_binding_conflict")
                return False
            held = connection.execute(
                "SELECT operation_id FROM native.workspace_holds WHERE state_lineage=%s",
                (binding.state_lineage,),
            ).fetchone()
            if held:
                raise NativeHeld("native_workspace_held")
            connection.execute(
                "INSERT INTO native.attempts(operation_id,attempt_id,tenant_id,"
                "fingerprint,binding) "
                "VALUES(%s,%s,%s,%s,%s::jsonb)",
                (
                    binding.operation_id,
                    binding.attempt_id,
                    binding.tenant_id,
                    binding.fingerprint,
                    json.dumps(binding.document()),
                ),
            )
            connection.execute(
                "INSERT INTO native.workspace_holds(state_lineage,operation_id) VALUES(%s,%s)",
                (binding.state_lineage, binding.operation_id),
            )
        return True

    def record(self, binding: NativeBinding, event: str, facts: dict[str, Any]) -> None:
        with self.connect() as connection:
            prior = connection.execute(
                "SELECT fingerprint FROM native.attempts WHERE operation_id=%s",
                (binding.operation_id,),
            ).fetchone()
            if prior is None or prior["fingerprint"] != binding.fingerprint:
                raise NativeHeld("native_attempt_not_bound")
            connection.execute(
                "INSERT INTO native.events(operation_id,kind,facts) VALUES(%s,%s,%s::jsonb)",
                (binding.operation_id, event, json.dumps(facts, allow_nan=False)),
            )
