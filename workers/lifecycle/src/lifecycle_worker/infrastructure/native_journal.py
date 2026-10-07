"""Worker-owned PostgreSQL certainty ledger. No Lifecycle database access."""

import json
from collections.abc import Callable
from typing import Any

import psycopg

from lifecycle_worker.application.native import NativeBinding, NativeHeld, digest, native_identity


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
            scope = {
                k: binding.document()[k]
                for k in ("tenant_id", "site_id", "project_id", "resource_id", "ownership_digest")
            }
            held = connection.execute(
                "SELECT generation,job_id,scope FROM native.custody_generations "
                "WHERE custody_id=%s ORDER BY generation DESC LIMIT 1",
                (binding.custody_id,),
            ).fetchone()
            if held and (
                digest(held["scope"]) != digest(scope)
                or held["generation"] > binding.custody_generation
                or (
                    held["generation"] == binding.custody_generation
                    and str(held["job_id"]) != binding.job_id
                )
            ):
                raise NativeHeld("native_custody_held")
            # The caller has checked the commissioned Lifecycle grant immediately
            # before claim. A new generation needs independently renewed custody.
            connection.execute(
                "INSERT INTO native.custody_generations VALUES(%s,%s,%s,%s::jsonb) "
                "ON CONFLICT DO NOTHING",
                (binding.custody_id, binding.custody_generation, binding.job_id, json.dumps(scope)),
            )
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
                "INSERT INTO native.custody_holds(custody_id,operation_id) VALUES(%s,%s) "
                "ON CONFLICT DO NOTHING",
                (binding.custody_id, binding.operation_id),
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

    def resources(self, binding: NativeBinding) -> dict[str, dict[str, str]]:
        with self.connect() as connection:
            prior = connection.execute(
                "SELECT fingerprint FROM native.attempts WHERE operation_id=%s",
                (binding.operation_id,),
            ).fetchone()
            if prior is None or prior["fingerprint"] != binding.fingerprint:
                raise NativeHeld("native_attempt_not_bound")
            rows = connection.execute(
                "SELECT facts FROM native.events WHERE operation_id=%s "
                "AND kind='request_accepted' ORDER BY sequence",
                (binding.operation_id,),
            ).fetchall()
        result: dict[str, dict[str, str]] = {}
        for row in rows:
            facts = row["facts"]
            key = facts["resource_key"]
            if key in result or facts["kind"] not in {"server", "port", "volume", "image"}:
                raise NativeHeld("ambiguous_native_receipt")
            result[key] = {"kind": facts["kind"], "id": native_identity(facts["native_id"])}
        return result

    def transfers(self, binding: NativeBinding) -> dict[str, dict[str, Any]]:
        with self.connect() as connection:
            prior = connection.execute(
                "SELECT fingerprint FROM native.attempts WHERE operation_id=%s",
                (binding.operation_id,),
            ).fetchone()
            if prior is None or prior["fingerprint"] != binding.fingerprint:
                raise NativeHeld("native_attempt_not_bound")
            rows = connection.execute(
                "SELECT facts FROM native.events WHERE operation_id=%s "
                "AND kind='disk_transferred' ORDER BY sequence",
                (binding.operation_id,),
            ).fetchall()
        result: dict[str, dict[str, Any]] = {}
        for row in rows:
            key = row["facts"]["resource_key"]
            if key in result:
                raise NativeHeld("ambiguous_native_transfer_receipt")
            result[key] = row["facts"]
        return result

    def capture(self, binding: NativeBinding, plan_sha256: str) -> dict[str, Any]:
        """Resolve a prior immutable capture intent only inside the same tenant/job/plan."""
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT a.binding,e.facts FROM native.attempts a JOIN native.events e "
                "ON e.operation_id=a.operation_id WHERE a.tenant_id=%s "
                "AND a.binding->>'job_id'=%s AND a.binding->>'operation_plan_sha256'=%s "
                "AND e.kind='clone_bound'",
                (binding.tenant_id, binding.job_id, plan_sha256),
            ).fetchall()
        if len(rows) != 1:
            raise NativeHeld("migration_capture_receipt_ambiguous")
        prior = rows[0]["binding"]
        fields = (
            "tenant_id",
            "site_id",
            "project_id",
            "resource_id",
            "job_id",
            "plan_digest",
            "ownership_digest",
            "custody_id",
            "custody_generation",
            "epoch",
        )
        if any(digest(prior.get(k)) != digest(binding.document()[k]) for k in fields):
            raise NativeHeld("migration_capture_receipt_scope_changed")
        return dict(rows[0]["facts"])

    def artifact(self, binding: NativeBinding, plan_sha256: str, kind: str) -> dict[str, Any]:
        if kind not in {"archive", "conversion"}:
            raise NativeHeld("invalid_migration_artifact_kind")
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT operation_id,binding FROM native.attempts WHERE tenant_id=%s "
                "AND binding->>'job_id'=%s AND binding->>'operation_plan_sha256'=%s",
                (binding.tenant_id, binding.job_id, plan_sha256),
            ).fetchall()
            if len(rows) != 1:
                raise NativeHeld("migration_artifact_ambiguous")
            prior = rows[0]["binding"]
            fields = (
                "tenant_id",
                "site_id",
                "project_id",
                "resource_id",
                "job_id",
                "plan_digest",
                "ownership_digest",
                "custody_id",
                "custody_generation",
                "epoch",
            )
            if any(digest(prior.get(k)) != digest(binding.document()[k]) for k in fields):
                raise NativeHeld("migration_artifact_scope_changed")
            events = connection.execute(
                "SELECT kind,facts FROM native.events WHERE operation_id=%s ORDER BY sequence",
                (rows[0]["operation_id"],),
            ).fetchall()
        terminal = "export_complete" if kind == "archive" else "conversion_complete"
        completed = [e["facts"] for e in events if e["kind"] == terminal]
        if len(completed) != 1:
            raise NativeHeld("migration_artifact_incomplete")
        disk_event = "disk_transferred" if kind == "archive" else "conversion_observed"
        disks: dict[str, dict[str, Any]] = {}
        for event in events:
            if event["kind"] != disk_event:
                continue
            key = event["facts"]["resource_key"]
            if key in disks:
                raise NativeHeld("migration_artifact_ambiguous")
            disks[key] = event["facts"]
        if not disks:
            raise NativeHeld("migration_artifact_incomplete")
        return {
            "operation_id": str(rows[0]["operation_id"]),
            "disks": disks,
            "completion": completed[0],
        }
