"""Durable admission, effect certainty and fencing; Temporal alone advances the journey."""

import json
from collections.abc import Callable
from typing import Any
from uuid import uuid4

from lifecycle.application.execution_ports import Alerts, Authority, Effects, Evidence
from lifecycle.application.reservations import Database, Transaction
from lifecycle.domain.admission import digest, evaluate
from lifecycle.domain.execution import Rejected, execution_plan, hold_keys, identity, recovery_mode

LOCK = "SELECT pg_advisory_xact_lock(7601001)"


class Execution:
    def __init__(
        self,
        database: Database,
        authority: Authority,
        effects: Effects,
        evidence: Evidence,
        clock: Callable[[], int],
    ) -> None:
        self.database, self.authority, self.effects = database, authority, effects
        self.evidence, self.clock = evidence, clock

    def control(self, tx: Transaction, epoch: str | None = None) -> str:
        control = tx.one("SELECT * FROM app.execution_control WHERE id=1")
        external = self.authority.custody()
        if (
            control is None
            or control["quarantined"]
            or str(control["epoch"]) != external
            or (epoch is not None and epoch != external)
        ):
            raise Rejected("restore_quarantine", 423)
        return external

    def current(self, job: dict[str, Any]) -> dict[str, Any]:
        snapshot = self.authority.current(job)
        decision = evaluate(job["plan"], job["binding"], snapshot, self.clock())
        if not decision["admissible"]:
            raise Rejected("authority_held:" + ",".join(decision["holds"]), 403)
        campaign = snapshot["campaign"]
        if (
            snapshot.get("simulation") is not True
            or campaign.get("id") != job["campaign_id"]
            or campaign.get("adapter") != "p06-simulator-v1"
            or campaign.get("custody_epoch") != self.authority.custody()
        ):
            raise Rejected("simulation_campaign_required", 403)
        return snapshot

    def admit(
        self,
        tenant: str,
        actor: str,
        key: str,
        plan: dict[str, Any],
        binding: dict[str, Any],
        approval: str,
        campaign: str,
    ) -> dict[str, Any]:
        for value in (tenant, actor, key, approval, campaign):
            identity(value)
        steps = execution_plan(plan, binding)
        if binding["tenant_id"] != tenant or actor not in binding["executor_ids"]:
            raise Rejected("scope_denied", 403)
        fingerprint = digest(
            {
                "actor": actor,
                "binding": binding,
                "approval": approval,
                "campaign": campaign,
                "content": plan,
            }
        )
        with self.database.transaction() as tx:
            prior = tx.one(
                "SELECT id,fingerprint FROM app.execution_jobs WHERE tenant=%s AND command_key=%s",
                (tenant, key),
            )
            if prior:
                if prior["fingerprint"] != fingerprint:
                    raise Rejected("command_key_conflict")
                return self.read(tenant, str(prior["id"]))
        job: dict[str, Any] = {
            "id": str(uuid4()),
            "tenant": tenant,
            "actor": actor,
            "plan": plan,
            "binding": binding,
            "approval_id": approval,
            "campaign_id": campaign,
        }
        snapshot = self.current(job)
        with self.database.transaction() as tx:
            tx.execute(LOCK)
            epoch = self.control(tx)
            # Recheck freshness after waiting for the transaction lock.
            if self.clock() - snapshot["evaluated_at"] > 5:
                raise Rejected("authority_snapshot_stale", 403)
            prior = tx.one(
                "SELECT id,fingerprint FROM app.execution_jobs WHERE tenant=%s AND command_key=%s",
                (tenant, key),
            )
            if prior:
                if prior["fingerprint"] != fingerprint:
                    raise Rejected("command_key_conflict")
                job["id"] = str(prior["id"])
            else:
                for resource in hold_keys(plan):
                    held = tx.one(
                        "SELECT job,retained FROM app.execution_holds WHERE resource_key=%s",
                        (resource,),
                    )
                    if held and held["retained"]:
                        raise Rejected("resource_held")
                workflow = "p06/" + tenant + "/" + job["id"]
                tx.execute(
                    "INSERT INTO app.execution_jobs(id,tenant,actor,command_"
                    "key,fingerprint,plan,binding,approval_id,campaign_id,cu"
                    "stody_epoch,workflow_id,admitted_at,admission) VALUES(%"
                    "s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s,%s,%s,%s,%s::js"
                    "onb)",
                    (
                        job["id"],
                        tenant,
                        actor,
                        key,
                        fingerprint,
                        json.dumps(plan),
                        json.dumps(binding),
                        approval,
                        campaign,
                        epoch,
                        workflow,
                        self.clock(),
                        json.dumps(snapshot),
                    ),
                )
                tx.execute(
                    "INSERT INTO app.execution_projection(job,updated_at) VALUES(%s,%s)",
                    (job["id"], self.clock()),
                )
                tx.execute("INSERT INTO app.execution_dispatch(job) VALUES(%s)", (job["id"],))
                for resource in hold_keys(plan):
                    tx.execute(
                        "INSERT INTO app.execution_holds(resource_key,job) VALUE"
                        "S(%s,%s) ON CONFLICT(resource_key) DO UPDATE SET job=EX"
                        "CLUDED.job,retained=true",
                        (resource, job["id"]),
                    )
                for ordinal, step in enumerate(steps):
                    tx.execute(
                        "INSERT INTO app.execution_operations(id,job,step,ordina"
                        "l) VALUES(%s,%s,%s,%s)",
                        (str(uuid4()), job["id"], step, ordinal),
                    )
                self.event(
                    tx,
                    job["id"],
                    "admitted",
                    {
                        "plan_digest": binding["digest"],
                        "workflow_id": workflow,
                        "reservation_bindings": snapshot["reservations"],
                        "simulation": True,
                    },
                )
        return self.read(tenant, job["id"])

    def job(self, tx: Transaction, tenant: str, job: str) -> dict[str, Any]:
        row = tx.one(
            "SELECT j.*,p.state,p.reason,p.revision,p.updated_at,p.c"
            "ancel_requested,p.pause_requested,p.stop_requested,p.ev"
            "idence,p.workflow_run_id FROM app.execution_jobs j JOIN"
            " app.execution_projection p ON p.job=j.id WHERE j.id=%s"
            " AND j.tenant=%s",
            (identity(job), identity(tenant)),
        )
        if row is None:
            raise Rejected("not_found", 404)
        for key in (
            "id",
            "tenant",
            "actor",
            "approval_id",
            "campaign_id",
            "custody_epoch",
            "command_key",
        ):
            row[key] = str(row[key])
        return row

    def read(self, tenant: str, job: str) -> dict[str, Any]:
        with self.database.transaction() as tx:
            row = self.job(tx, tenant, job)
            operations = tx.all(
                "SELECT id,step,ordinal,outcome,revision,observation FRO"
                "M app.execution_operations WHERE job=%s ORDER BY ordina"
                "l",
                (job,),
            )
            events = tx.all(
                "SELECT id,kind,facts,occurred_at FROM app.execution_eve"
                "nts WHERE job=%s ORDER BY sequence LIMIT 300",
                (job,),
            )
            for op in operations:
                op["id"] = str(op["id"])
            for event in events:
                event["id"] = str(event["id"])
            return {
                "id": row["id"],
                "tenant_id": tenant,
                "actor_id": row["actor"],
                "requested_by": row["binding"]["requested_by"],
                "source_revision": row["admission"].get("source_revision"),
                "scope": row["plan"]["scope"],
                "plan_id": row["binding"]["plan_id"],
                "plan_digest": row["binding"]["digest"],
                "approval_id": row["approval_id"],
                "workflow_id": row["workflow_id"],
                "workflow_run_id": row["workflow_run_id"],
                "state": row["state"],
                "reason": row["reason"],
                "revision": row["revision"],
                "observed_at": self.clock(),
                "updated_at": row["updated_at"],
                "simulation": True,
                "evidence_level": "E2",
                "native_write_authorized": False,
                "cancel_requested": row["cancel_requested"],
                "pause_requested": row["pause_requested"],
                "stop_requested": row["stop_requested"],
                "evidence": row["evidence"],
                "recovery_mode": recovery_mode(row["plan"], operations),
                "operations": operations,
                "events": events,
                "resources_retained": True,
            }

    def project(self, tx: Transaction, job: str, state: str, reason: str | None = None) -> None:
        prior = tx.one("SELECT state,reason FROM app.execution_projection WHERE job=%s", (job,))
        if prior and (prior["state"], prior["reason"]) == (state, reason):
            return
        tx.execute(
            "UPDATE app.execution_projection SET state=%s,reason=%s,"
            "updated_at=%s,revision=revision+1 WHERE job=%s",
            (state, reason, self.clock(), job),
        )
        self.event(tx, job, state, {"reason": reason})
        if state == "held":
            p = tx.one("SELECT revision FROM app.execution_projection WHERE job=%s", (job,))
            assert p
            alert = {"id": str(uuid4()), "job_id": job, "reason": reason, "simulation": True}
            tx.execute(
                "INSERT INTO app.execution_alerts(id,job,projection_revi"
                "sion,payload) VALUES(%s,%s,%s,%s::jsonb)",
                (alert["id"], job, p["revision"], json.dumps(alert)),
            )

    def hold(self, tenant: str, job: str, reason: str) -> dict[str, Any]:
        with self.database.transaction() as tx:
            tx.execute(LOCK)
            self.job(tx, tenant, job)
            if reason != "evidence_pending":
                tx.execute(
                    "UPDATE app.execution_projection SET pause_requested=true WHERE job=%s", (job,)
                )
            self.project(tx, job, "held", reason)
        return {"state": "held", "reason": reason}

    def acquire(self, tenant: str, job_id: str, step: str, worker: str) -> dict[str, Any]:
        with self.database.transaction() as tx:
            job = self.job(tx, tenant, job_id)
        snapshot = self.current(job)
        if worker not in snapshot["campaign"].get("worker_ids", []):
            raise Rejected("worker_scope_denied", 403)
        with self.database.transaction() as tx:
            tx.execute(LOCK)
            job = self.job(tx, tenant, job_id)
            epoch = self.control(tx, job["custody_epoch"])
            if job["cancel_requested"] or job["pause_requested"] or job["stop_requested"]:
                raise Rejected("operator_hold", 423)
            if self.clock() - snapshot["evaluated_at"] > 5:
                raise Rejected("authority_snapshot_stale", 403)
            op = tx.one(
                "SELECT * FROM app.execution_operations WHERE job=%s AND step=%s", (job_id, step)
            )
            if not op:
                raise Rejected("unknown_step", 422)
            if op["outcome"] == "confirmed_succeeded":
                return {"completed": True, "operation_id": str(op["id"])}
            if op["outcome"] != "not_started":
                raise Rejected("reconciliation_required", 423)
            if tx.one(
                "SELECT id FROM app.execution_operations WHERE job=%s AN"
                "D ordinal<%s AND outcome<>'confirmed_succeeded' LIMIT 1",
                (job_id, op["ordinal"]),
            ):
                raise Rejected("precondition_not_confirmed", 423)
            for resource in hold_keys(job["plan"]):
                held = tx.one(
                    "SELECT job,retained FROM app.execution_holds WHERE resource_key=%s",
                    (resource,),
                )
                if not held or str(held["job"]) != job_id or not held["retained"]:
                    raise Rejected("ownership_lost", 423)
            attempt, grant = str(uuid4()), str(uuid4())
            expiry = min(
                self.clock() + 15, snapshot["campaign"]["expires_at"], job["plan"]["valid_until"]
            )
            tx.execute(
                "UPDATE app.execution_operations SET outcome='attempting"
                "',attempt_id=%s,grant_id=%s,worker=%s,epoch=%s,expires_"
                "at=%s,redeemed=false,revision=revision+1 WHERE id=%s",
                (attempt, grant, worker, epoch, expiry, op["id"]),
            )
            self.project(tx, job_id, "running")
            self.event(
                tx,
                job_id,
                "attempt_committed",
                {
                    "operation_id": str(op["id"]),
                    "attempt_id": attempt,
                    "step": step,
                    "epoch": epoch,
                    "worker": worker,
                },
            )
            return {
                "completed": False,
                "id": grant,
                "operation_id": str(op["id"]),
                "attempt_id": attempt,
                "job_id": job_id,
                "tenant_id": tenant,
                "step": step,
                "worker_id": worker,
                "epoch": epoch,
                "expires_at": expiry,
                "plan_digest": job["binding"]["digest"],
                "campaign_id": job["campaign_id"],
                "scope": job["plan"]["scope"],
                "simulation": True,
                "adapter": "p06-simulator-v1",
            }

    def redeem(self, grant: dict[str, Any], worker: str) -> dict[str, Any]:
        with self.database.transaction() as tx:
            job = self.job(tx, grant["tenant_id"], grant["job_id"])
        snapshot = self.current(job)
        with self.database.transaction() as tx:
            tx.execute(LOCK)
            job = self.job(tx, grant["tenant_id"], grant["job_id"])
            self.control(tx, job["custody_epoch"])
            op = tx.one(
                "SELECT * FROM app.execution_operations WHERE id=%s AND job=%s",
                (identity(grant["operation_id"]), job["id"]),
            )
            if (
                not op
                or str(op["grant_id"]) != grant["id"]
                or str(op["attempt_id"]) != grant["attempt_id"]
                or str(op["epoch"]) != grant["epoch"]
                or op["worker"] != worker
                or grant["worker_id"] != worker
                or worker not in snapshot["campaign"]["worker_ids"]
                or op["step"] != grant["step"]
                or op["expires_at"] != grant["expires_at"]
                or op["expires_at"] <= self.clock()
                or op["outcome"] != "attempting"
                or op["redeemed"]
                or grant["scope"] != job["plan"]["scope"]
                or grant["plan_digest"] != job["binding"]["digest"]
                or grant["campaign_id"] != job["campaign_id"]
                or grant["simulation"] is not True
                or grant["adapter"] != "p06-simulator-v1"
                or job["cancel_requested"]
                or job["pause_requested"]
                or job["stop_requested"]
                or self.clock() - snapshot["evaluated_at"] > 5
            ):
                raise Rejected("grant_not_current", 403)
            tx.execute(
                "UPDATE app.execution_operations SET redeemed=true,revision=revision+1 WHERE id=%s",
                (op["id"],),
            )
            self.event(
                tx,
                job["id"],
                "grant_redeemed",
                {
                    "operation_id": str(op["id"]),
                    "attempt_id": str(op["attempt_id"]),
                    "epoch": grant["epoch"],
                },
            )
        return {
            "allowed": True,
            "grant_id": grant["id"],
            "simulation": True,
            "expires_at": grant["expires_at"],
        }

    def record(self, tenant: str, job: str, step: str, observation: dict[str, Any]) -> None:
        with self.database.transaction() as tx:
            tx.execute(LOCK)
            row = self.job(tx, tenant, job)
            op = tx.one(
                "SELECT * FROM app.execution_operations WHERE job=%s AND step=%s", (job, step)
            )
            if not op:
                raise Rejected("not_found", 404)
            expected = {
                "tenant_id": tenant,
                "job_id": job,
                "operation_id": str(op["id"]),
                "attempt_id": str(op["attempt_id"]),
                "plan_digest": row["binding"]["digest"],
                "simulation": True,
                "epoch": str(op["epoch"]),
            }
            valid = (
                all(observation.get(k) == v for k, v in expected.items())
                and observation.get("sealed") is True
                and observation.get("outcome") in {"confirmed_succeeded", "confirmed_failed"}
                and type(observation.get("observed_at")) is int
                and 0 <= self.clock() - observation["observed_at"] <= 5
                and observation.get("effect_count")
                == (1 if observation.get("outcome") == "confirmed_succeeded" else 0)
            )
            if op["outcome"] in {"confirmed_succeeded", "confirmed_failed"}:
                return
            result = (
                observation
                if valid
                else {"outcome": "outcome_unknown", "reason": "independent_readback_required"}
            )
            tx.execute(
                "UPDATE app.execution_operations SET outcome=%s,observat"
                "ion=%s::jsonb,revision=revision+1 WHERE id=%s",
                (result["outcome"], json.dumps(result), op["id"]),
            )
            tx.execute(
                "UPDATE app.execution_projection SET revision=revision+1"
                ",updated_at=%s WHERE job=%s",
                (self.clock(), job),
            )
            self.event(
                tx, job, "outcome_recorded", {"operation_id": str(op["id"]), "observation": result}
            )
            if result["outcome"] != "confirmed_succeeded":
                tx.execute(
                    "UPDATE app.execution_projection SET pause_requested=true WHERE job=%s", (job,)
                )
                self.project(tx, job, "held", result["outcome"])

    def activity(self, tenant: str, job: str, step: str, worker: str) -> dict[str, Any]:
        try:
            grant = self.acquire(tenant, job, step, worker)
        except Rejected as error:
            return self.hold(tenant, job, error.reason)
        if grant["completed"]:
            return {"state": "confirmed_succeeded"}
        try:
            # Acknowledgement is only a hint. Independent sealed readback decides certainty.
            self.effects.execute({k: v for k, v in grant.items() if k != "completed"})
            with self.database.transaction() as tx:
                op = tx.one(
                    "SELECT * FROM app.execution_operations WHERE job=%s AND step=%s", (job, step)
                )
            assert op
            observation = self.effects.reconcile(
                self.observation_request(tenant, job, op, grant["plan_digest"])
            )
        except Exception:
            observation = {"outcome": "outcome_unknown"}
        self.record(tenant, job, step, observation)
        public = self.read(tenant, job)
        actual = next(o for o in public["operations"] if o["step"] == step)
        return {"state": actual["outcome"]}

    @staticmethod
    def observation_request(
        tenant: str, job: str, op: dict[str, Any], plan_digest: str
    ) -> dict[str, Any]:
        return {
            "tenant_id": tenant,
            "job_id": job,
            "operation_id": str(op["id"]),
            "attempt_id": str(op["attempt_id"]),
            "epoch": str(op["epoch"]),
            "plan_digest": plan_digest,
            "simulation": True,
        }

    def reconcile(self, tenant: str, job: str) -> dict[str, Any]:
        # Committed-fact observation continues after initiating authority expires/revokes.
        with self.database.transaction() as tx:
            row = self.job(tx, tenant, job)
            ops = tx.all(
                "SELECT * FROM app.execution_operations WHERE job=%s AND"
                " outcome IN ('attempting','outcome_unknown') ORDER BY o"
                "rdinal",
                (job,),
            )
        for op in ops:
            try:
                observation = self.effects.reconcile(
                    self.observation_request(tenant, job, op, row["binding"]["digest"])
                )
            except Exception:
                observation = {"outcome": "outcome_unknown"}
            self.record(tenant, job, op["step"], observation)
        return self.read(tenant, job)

    def command(
        self, tenant: str, job: str, actor: str, key: str, action: str, expected: int
    ) -> dict[str, Any]:
        identity(actor)
        identity(key)
        if action not in {"pause", "cancel", "stop", "reconcile", "resume", "retry_unstarted"}:
            raise Rejected("invalid_action", 422)
        fingerprint = digest({"job": job, "actor": actor, "action": action, "revision": expected})
        with self.database.transaction() as tx:
            row = self.job(tx, tenant, job)
        if action in {"resume", "retry_unstarted"}:
            self.current(row)
        with self.database.transaction() as tx:
            tx.execute(LOCK)
            row = self.job(tx, tenant, job)
            prior = tx.one(
                "SELECT fingerprint,receipt FROM app.execution_commands "
                "WHERE tenant=%s AND command_key=%s",
                (tenant, key),
            )
            if prior:
                if prior["fingerprint"] != fingerprint:
                    raise Rejected("command_key_conflict")
                return dict(prior["receipt"])
            if type(expected) is not int or row["revision"] != expected:
                raise Rejected("stale_revision")
            if row["state"] in {"completed", "cancelled"}:
                raise Rejected("terminal_job")
            ops = tx.all(
                "SELECT * FROM app.execution_operations WHERE job=%s ORDER BY ordinal", (job,)
            )
            if action in {"resume", "retry_unstarted"}:
                self.control(tx, row["custody_epoch"])
                if row["cancel_requested"] or any(
                    o["outcome"] in {"attempting", "outcome_unknown"} for o in ops
                ):
                    raise Rejected("reconciliation_required")
                if action == "retry_unstarted":
                    if recovery_mode(row["plan"], ops) == "forward_recovery_required":
                        raise Rejected("new_forward_recovery_plan_required")
                    failed = [o for o in ops if o["outcome"] == "confirmed_failed"]
                    if not failed or any(
                        not o["observation"]
                        or o["observation"].get("sealed") is not True
                        or o["observation"].get("effect_count") != 0
                        for o in failed
                    ):
                        raise Rejected("sealed_absence_required")
                    tx.execute(
                        "UPDATE app.execution_operations SET outcome='not_starte"
                        "d',revision=revision+1 WHERE job=%s AND outcome='confir"
                        "med_failed'",
                        (job,),
                    )
                tx.execute(
                    "UPDATE app.execution_projection SET pause_requested=fal"
                    "se,stop_requested=false WHERE job=%s",
                    (job,),
                )
            if action in {"pause", "cancel", "stop"}:
                column = {
                    "pause": "pause_requested",
                    "cancel": "cancel_requested",
                    "stop": "stop_requested",
                }[action]
                tx.execute(
                    "UPDATE app.execution_projection SET " + column + "=true WHERE job=%s", (job,)
                )
            tx.execute(
                "UPDATE app.execution_projection SET revision=revision+1"
                ",updated_at=%s WHERE job=%s",
                (self.clock(), job),
            )
            receipt = {
                "command_id": key,
                "job_id": job,
                "action": action,
                "accepted": True,
                "effect_undone": False,
            }
            tx.execute(
                "INSERT INTO app.execution_commands(tenant,command_key,f"
                "ingerprint,job,receipt) VALUES(%s,%s,%s,%s,%s::jsonb)",
                (tenant, key, fingerprint, job, json.dumps(receipt)),
            )
            self.event(tx, job, "operator_request", {**receipt, "actor_id": actor})
        return receipt

    def checkpoint(self, tenant: str, job: str) -> dict[str, Any]:
        self.reconcile(tenant, job)
        with self.database.transaction() as tx:
            tx.execute(LOCK)
            row = self.job(tx, tenant, job)
            ops = tx.all(
                "SELECT step,outcome,observation FROM app.execution_oper"
                "ations WHERE job=%s ORDER BY ordinal",
                (job,),
            )
            unknown = any(o["outcome"] in {"attempting", "outcome_unknown"} for o in ops)
            if unknown:
                self.project(tx, job, "held", "outcome_unknown")
                return {"state": "held"}
            if row["cancel_requested"]:
                self.project(tx, job, "cancelled", "effects_and_allocations_retained")
                return {"state": "cancelled"}
            if row["pause_requested"] or row["stop_requested"]:
                self.project(tx, job, "held", "operator_hold")
                return {"state": "held"}
            if any(o["outcome"] == "confirmed_failed" for o in ops):
                self.project(tx, job, "held", "operator_recovery_required")
                return {"state": "held"}
            if not all(o["outcome"] == "confirmed_succeeded" for o in ops):
                return {"state": "ready", "steps": [o["step"] for o in ops]}
        # Audit finalization is allowed for committed facts after actor revocation.
        try:
            receipt = self.evidence.finalize(row, [o["observation"] for o in ops])
            if (
                receipt.get("tenant_id") != tenant
                or receipt.get("job_id") != job
                or receipt.get("plan_digest") != row["binding"]["digest"]
                or receipt.get("digest") != digest([o["observation"] for o in ops])
                or receipt.get("state") != "finalized"
                or receipt.get("evidence_level") != "E2"
                or receipt.get("native_support") is not False
            ):
                raise ValueError("evidence_binding")
        except Exception:
            return self.hold(tenant, job, "evidence_pending")
        with self.database.transaction() as tx:
            tx.execute(LOCK)
            current = self.job(tx, tenant, job)
            if (
                current["cancel_requested"]
                or current["pause_requested"]
                or current["stop_requested"]
            ):
                return {"state": "held"}
            tx.execute(
                "UPDATE app.execution_projection SET evidence=%s::jsonb WHERE job=%s",
                (json.dumps(receipt), job),
            )
            self.project(tx, job, "completed")
        return {"state": "completed"}

    def deliver_alerts(self, alerts: Alerts) -> int:
        with self.database.transaction() as tx:
            pending = tx.all(
                "SELECT * FROM app.execution_alerts WHERE receipt IS NULL ORDER BY id LIMIT 100"
            )
        for row in pending:
            receipt = alerts.deliver(row["payload"])
            if not receipt or len(receipt) > 256:
                raise Rejected("alert_acknowledgement_required", 503)
            with self.database.transaction() as tx:
                tx.execute(
                    "UPDATE app.execution_alerts SET receipt=%s WHERE id=%s AND receipt IS NULL",
                    (receipt, row["id"]),
                )
        return len(pending)

    def event(self, tx: Transaction, job: str, kind: str, facts: dict[str, Any]) -> None:
        tx.execute(
            "INSERT INTO app.execution_events(id,job,kind,facts,occu"
            "rred_at) VALUES(%s,%s,%s,%s::jsonb,%s)",
            (str(uuid4()), job, kind, json.dumps(facts), self.clock()),
        )
