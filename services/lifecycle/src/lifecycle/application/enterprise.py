"""Global budget reservation, fair dispatch and explicit stop boundaries for P09.

An expired/failed worker retains allocations until independent reconciliation.
No method here performs a native effect or accepts owner evidence from a caller.
"""

import json
from collections.abc import Callable
from typing import Any, Protocol
from uuid import uuid4

from lifecycle.application.adoption import event
from lifecycle.application.reservations import Database, Transaction
from lifecycle.domain.admission import digest
from lifecycle.domain.execution import Rejected, identity
from lifecycle.domain.expansion import field_keys, operation, wave, window_open
from lifecycle.domain.native_workflow import checksum, exact, integer

LOCK = 7709002


class EnterpriseOwners(Protocol):
    def require_current(self, specification: dict[str, Any], boundary: str) -> None: ...
    def budgets(self, pools: list[str]) -> dict[str, Any]: ...
    def observe(self, specification: dict[str, Any], lease: str) -> dict[str, Any]: ...


class Enterprise:
    def __init__(
        self, database: Database, owners: EnterpriseOwners, clock: Callable[[], int]
    ) -> None:
        self.database, self.owners, self.clock = database, owners, clock

    def read(self, tenant: str, wave_id: str) -> dict[str, Any]:
        with self.database.transaction() as tx:
            return self.load(tx, tenant, wave_id)

    def specifications(self, tenant: str, wave_id: str) -> list[dict[str, Any]]:
        with self.database.transaction() as tx:
            self.load(tx, tenant, wave_id)
            return [
                dict(row["specification"])
                for row in tx.all(
                    "SELECT specification FROM app.enterprise_operations "
                    "WHERE wave=%s AND tenant=%s",
                    (wave_id, tenant),
                )
            ]

    def load(self, tx: Transaction, tenant: str, wave_id: str) -> dict[str, Any]:
        row = tx.one(
            "SELECT * FROM app.enterprise_waves WHERE id=%s AND tenant=%s",
            (identity(wave_id), identity(tenant)),
        )
        if row is None:
            raise Rejected("not_found", 404)
        return row

    def create(
        self, tenant: str, actor: str, key: str, specs: list[dict[str, Any]]
    ) -> dict[str, Any]:
        identity(tenant), identity(actor), identity(key)
        order = wave(specs)
        if any(s["tenant_id"] != tenant for s in specs):
            raise Rejected("enterprise_cross_tenant_wave", 403)
        fingerprint = digest(specs)
        with self.database.transaction() as tx:
            tx.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK,))
            prior = tx.one(
                "SELECT * FROM app.enterprise_waves WHERE tenant=%s AND actor=%s AND "
                "command_key=%s",
                (tenant, actor, key),
            )
            if prior:
                if prior["fingerprint"] != fingerprint:
                    raise Rejected("enterprise_command_conflict")
                return prior
            for spec in specs:
                self.owners.require_current(spec, "enqueue")
                if tx.one("SELECT id FROM app.enterprise_operations WHERE id=%s", (spec["id"],)):
                    raise Rejected("enterprise_operation_conflict")
            wave_id = str(uuid4())
            tx.execute(
                "INSERT INTO app.enterprise_waves(id,tenant,actor,command_key,fingerprint,state) "
                "VALUES(%s,%s,%s,%s,%s,'running')",
                (wave_id, tenant, actor, key, fingerprint),
            )
            by_id = {s["id"]: s for s in specs}
            for op in order:
                tx.execute(
                    "INSERT INTO app.enterprise_operations(id,wave,tenant,specification) "
                    "VALUES(%s,%s,%s,%s::jsonb)",
                    (op, wave_id, tenant, json.dumps(by_id[op])),
                )
            event(
                tx,
                wave_id,
                tenant,
                actor,
                "wave_created",
                {"specifications_sha256": fingerprint},
                self.clock(),
            )
            return self.load(tx, tenant, wave_id)

    def control(
        self, tenant: str, wave_id: str, actor: str, key: str, revision: int, action: str
    ) -> dict[str, Any]:
        identity(actor), identity(key)
        if action not in {"pause", "resume", "stop"}:
            raise Rejected("unsupported_enterprise_control", 422)
        fingerprint = digest([wave_id, revision, action])
        with self.database.transaction() as tx:
            tx.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK,))
            prior = tx.one(
                "SELECT * FROM app.expansion_commands WHERE tenant=%s AND actor=%s AND key=%s",
                (tenant, actor, key),
            )
            if prior:
                if prior["fingerprint"] != fingerprint:
                    raise Rejected("enterprise_command_conflict")
                return dict(prior["result"])
            row = self.load(tx, tenant, wave_id)
            if (
                type(revision) is not int
                or row["revision"] != revision
                or row["state"] == "stopped"
            ):
                raise Rejected("enterprise_revision_or_stop_conflict")
            state = {"pause": "paused", "resume": "running", "stop": "stopped"}[action]
            tx.execute(
                "UPDATE app.enterprise_waves SET state=%s,revision=revision+1 WHERE id=%s",
                (state, wave_id),
            )
            if state == "stopped":
                tx.execute(
                    "UPDATE app.enterprise_operations SET state='cancelled' WHERE wave=%s "
                    "AND state='queued'",
                    (wave_id,),
                )
            event(
                tx,
                wave_id,
                tenant,
                actor,
                action,
                {
                    "stop_boundary": "before_next_native_request",
                    "accepted_effects": "reconcile_and_retain_budgets",
                },
                self.clock(),
            )
            result = {"id": wave_id, "state": state, "revision": revision + 1}
            tx.execute(
                "INSERT INTO app.expansion_commands VALUES(%s,%s,%s,%s,%s::jsonb)",
                (tenant, actor, key, fingerprint, json.dumps(result)),
            )
            return result

    def available(self, tx: Transaction, spec: dict[str, Any]) -> bool:
        budgets = self.owners.budgets(sorted(spec["demands"]))
        exact(budgets, set(spec["demands"]))
        now = self.clock()
        for pool, amount in spec["demands"].items():
            budget = budgets[pool]
            exact(
                budget, {"limit", "external_usage", "observed_at", "expires_at", "evidence_sha256"}
            )
            integer(budget["limit"], 1)
            integer(budget["external_usage"])
            integer(budget["observed_at"])
            integer(budget["expires_at"], 1)
            checksum(budget["evidence_sha256"])
            if not 0 <= now - budget["observed_at"] <= 30 or budget["expires_at"] <= now:
                raise Rejected("enterprise_budget_stale", 423)
            reserved = tx.one(
                "SELECT COALESCE(SUM(amount),0) AS used FROM app.enterprise_allocations "
                "WHERE pool=%s",
                (pool,),
            )
            assert reserved is not None
            if budget["external_usage"] + int(reserved["used"]) + amount > budget["limit"]:
                return False
        return True

    def claim(self) -> dict[str, Any] | None:
        """Only a trusted dispatcher uses this method; every request rechecks the lease."""
        with self.database.transaction() as tx:
            tx.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK,))
            # A stale lease is uncertainty, never evidence that a write did not happen.
            tx.execute(
                "UPDATE app.enterprise_operations SET state='unknown' WHERE state='active' "
                "AND lease_until<=%s",
                (self.clock(),),
            )
            rows = tx.all(
                "SELECT o.*,w.actor FROM app.enterprise_operations o JOIN "
                "app.enterprise_waves w ON w.id=o.wave "
                "WHERE o.state='queued' AND w.state='running' ORDER BY "
                "(SELECT COALESCE(MAX(p.turn),0) FROM app.enterprise_operations p WHERE "
                "p.tenant=o.tenant),"
                "o.turn,(o.specification->>'priority')::integer DESC,o.id"
            )
            for row in rows:
                spec = operation(row["specification"])
                tx.execute(
                    "UPDATE app.enterprise_operations SET "
                    "turn=nextval('app.enterprise_dispatch_order') WHERE id=%s",
                    (row["id"],),
                )
                if not window_open(spec, self.clock()):
                    continue
                object_key = field_keys(spec["scope"], ["enterprise_writer"])[0]
                if tx.one(
                    "SELECT operation FROM app.enterprise_object_holds WHERE object_key=%s",
                    (object_key,),
                ):
                    continue
                if any(
                    tx.one(
                        "SELECT id FROM app.enterprise_operations WHERE id=%s AND wave=%s "
                        "AND state='succeeded'",
                        (dep, row["wave"]),
                    )
                    is None
                    for dep in spec["depends_on"]
                ):
                    continue
                try:
                    self.owners.require_current(spec, "dispatch")
                    if not self.available(tx, spec):
                        continue
                except Rejected:
                    continue
                now = self.clock()
                if not window_open(spec, now):
                    continue
                lease, expires = str(uuid4()), now + spec["maximum_seconds"]
                tx.execute(
                    "INSERT INTO app.enterprise_object_holds VALUES(%s,%s)", (object_key, row["id"])
                )
                for pool, amount in spec["demands"].items():
                    tx.execute(
                        "INSERT INTO app.enterprise_allocations VALUES(%s,%s,%s)",
                        (row["id"], pool, amount),
                    )
                tx.execute(
                    "UPDATE app.enterprise_operations SET "
                    "state='active',lease=%s,lease_until=%s,started_at=%s WHERE id=%s",
                    (lease, expires, now, row["id"]),
                )
                event(
                    tx,
                    str(row["id"]),
                    str(row["tenant"]),
                    str(row["actor"]),
                    "operation_claimed",
                    {"lease": lease, "expires_at": expires},
                    now,
                )
                return {
                    "operation_id": str(row["id"]),
                    "tenant_id": str(row["tenant"]),
                    "lease": lease,
                    "expires_at": expires,
                    "specification": spec,
                }
        return None

    def boundary(self, tenant: str, op: str, lease: str) -> dict[str, Any]:
        identity(tenant), identity(op), identity(lease)
        with self.database.transaction() as tx:
            tx.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK,))
            row = tx.one(
                "SELECT o.*,w.state AS wave_state FROM app.enterprise_operations o JOIN "
                "app.enterprise_waves w ON w.id=o.wave WHERE o.id=%s AND o.tenant=%s",
                (op, tenant),
            )
            if (
                row is None
                or str(row["lease"]) != lease
                or row["state"] != "active"
                or row["wave_state"] != "running"
                or row["lease_until"] <= self.clock()
            ):
                raise Rejected("enterprise_effect_boundary_held", 423)
            spec = operation(row["specification"])
            self.owners.require_current(spec, "before_native_request")
            if row["lease_until"] <= self.clock():
                raise Rejected("enterprise_effect_boundary_held", 423)
            return spec

    def reconcile(self, tenant: str, op: str, lease: str) -> dict[str, Any]:
        identity(tenant), identity(op), identity(lease)
        with self.database.transaction() as tx:
            tx.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK,))
            row = tx.one(
                "SELECT o.*,w.actor FROM app.enterprise_operations o JOIN "
                "app.enterprise_waves w ON w.id=o.wave WHERE o.id=%s AND o.tenant=%s",
                (op, tenant),
            )
            if (
                row is None
                or str(row["lease"]) != lease
                or row["state"] not in {"active", "unknown"}
            ):
                raise Rejected("enterprise_reconciliation_scope_held", 423)
            observed = self.owners.observe(row["specification"], lease)
            exact(
                observed,
                {
                    "operation_id",
                    "lease",
                    "specification_sha256",
                    "observer_id",
                    "executor_id",
                    "observed_at",
                    "outcome",
                    "writer_fenced",
                    "policy_sha256",
                    "services_sha256",
                    "recovery_sha256",
                    "evidence_sha256",
                },
            )
            integer(observed["observed_at"])
            identity(observed["observer_id"]), identity(observed["executor_id"])
            checksum(observed["evidence_sha256"])
            if (
                observed["operation_id"] != op
                or observed["lease"] != lease
                or observed["specification_sha256"] != digest(row["specification"])
                or observed["observer_id"] == observed["executor_id"]
                or not 0 <= self.clock() - observed["observed_at"] <= 30
                or observed["outcome"] not in {"succeeded", "failed", "unknown"}
            ):
                raise Rejected("enterprise_independent_observation_required", 423)
            state = observed["outcome"]
            if state != "unknown":
                if observed["writer_fenced"] is not True:
                    raise Rejected("enterprise_writer_must_be_fenced", 423)
                if state == "succeeded" and any(
                    observed[k + "_sha256"] != row["specification"]["prerequisites"][k]
                    for k in ("policy", "services", "recovery")
                ):
                    raise Rejected("enterprise_mandatory_outcome_changed", 423)
                tx.execute("DELETE FROM app.enterprise_allocations WHERE operation=%s", (op,))
                tx.execute("DELETE FROM app.enterprise_object_holds WHERE operation=%s", (op,))
            tx.execute(
                "UPDATE app.enterprise_operations SET state=%s,observation=%s::jsonb WHERE id=%s",
                (state, json.dumps(observed), op),
            )
            event(
                tx,
                op,
                tenant,
                str(row["actor"]),
                "operation_reconciled",
                {"outcome": state, "evidence_sha256": observed["evidence_sha256"]},
                self.clock(),
            )
            return {"operation_id": op, "state": state, "retry_authorized": False}
