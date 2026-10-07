"""Durable native stage control, single redemption and independent reconciliation.

The owning ports must authenticate current records and fence provider requests.
This coordinator never obtains platform credentials or executes arbitrary commands.
"""

import json
from collections.abc import Callable
from typing import Any, Protocol
from uuid import uuid4

from lifecycle.application.campaigns import Campaigns, stage_admission, stage_complete
from lifecycle.application.reservations import Database, Transaction
from lifecycle.domain.admission import digest
from lifecycle.domain.execution import Rejected, identity
from lifecycle.domain.native_workflow import (
    api_stage,
    current_authority,
    observations,
    stages_for,
    terminal_for,
    validate_plan,
)


class NativeOwners(Protocol):
    def current(self, plan: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
        """Read Governance, confirmed Inventory revision and provider/state custody live."""
        ...

    def observe(
        self, plan: dict[str, Any], binding: dict[str, Any], phase: str
    ) -> list[dict[str, Any]]:
        """Read independently owned evidence through approved, scoped owner interfaces."""
        ...

    def epoch(self) -> str:
        """Read the independently administered current custody epoch."""
        ...


class NativeWorkflow:
    def __init__(self, database: Database, owners: NativeOwners, clock: Callable[[], int]) -> None:
        self.database, self.owners, self.clock = database, owners, clock

    def event(self, tx: Transaction, job: str, kind: str, facts: dict[str, Any]) -> None:
        tx.execute(
            "INSERT INTO app.native_events(job,kind,facts,occurred_at) VALUES(%s,%s,%s::jsonb,%s)",
            (job, kind, json.dumps(facts, allow_nan=False), self.clock()),
        )

    def lock(self, tx: Transaction) -> None:
        tx.execute("SELECT pg_advisory_xact_lock(7707002)")

    def load(self, tx: Transaction, tenant: str, job: str) -> dict[str, Any]:
        row = tx.one(
            "SELECT j.*,p.state,p.stopped,p.revision FROM app.native_jobs j "
            "JOIN app.native_projection p ON p.job=j.id WHERE j.id=%s AND j.tenant=%s",
            (identity(job), identity(tenant)),
        )
        if row is None:
            raise Rejected("not_found", 404)
        return row

    def custody(self, tx: Transaction, plan: dict[str, Any]) -> None:
        control = tx.one("SELECT epoch,quarantined FROM app.native_control WHERE id=1")
        epoch = identity(self.owners.epoch())
        if (
            control is None
            or control["quarantined"]
            or str(control["epoch"]) != epoch
            or epoch != plan["epoch"]
        ):
            raise Rejected("native_custody_held", 423)

    def require(self, tx: Transaction, row: dict[str, Any], binding: dict[str, Any]) -> None:
        if row["stopped"]:
            raise Rejected("native_stopped", 423)
        self.custody(tx, row["plan"])
        receipt = self.owners.current(row["plan"], binding)
        current_authority(row["plan"], binding, receipt, self.clock())
        # Owner reads can outlive a revocation/epoch change; never rely on a cached epoch.
        self.custody(tx, row["plan"])

    def project(self, tx: Transaction, job: str, state: str, reason: str | None = None) -> None:
        tx.execute(
            "UPDATE app.native_projection SET state=%s,reason=%s,revision=revision+1,"
            "updated_at=%s WHERE job=%s",
            (state, reason, self.clock(), job),
        )

    def admit(
        self,
        plan: dict[str, Any],
        command_key: str,
        campaign: tuple[str, str] | None = None,
    ) -> str:
        # Copy to exclude concurrent mutation of caller-owned objects during owner reads.
        plan = json.loads(json.dumps(plan, allow_nan=False))
        validate_plan(plan, self.clock())
        identity(command_key)
        tenant = plan["scope"]["tenant_id"]
        fingerprint = digest(plan)
        with self.database.transaction() as tx:
            self.lock(tx)
            prior = tx.one(
                "SELECT id,fingerprint FROM app.native_jobs WHERE tenant=%s AND command_key=%s",
                (tenant, command_key),
            )
            if prior:
                if prior["fingerprint"] != fingerprint:
                    raise Rejected("native_command_conflict", 409)
                if campaign is not None:
                    member = tx.one(
                        "SELECT id FROM app.migration_members WHERE campaign=%s AND id=%s "
                        "AND tenant=%s AND job=%s",
                        (*campaign, tenant, prior["id"]),
                    )
                    if member is None:
                        raise Rejected("campaign_native_job_conflict", 409)
                return str(prior["id"])
            job = str(uuid4())
            admission = {"job_id": job, "stage": "admission", "plan_sha256": fingerprint}
            self.require(tx, {"plan": plan, "stopped": False}, admission)
            key = digest({k: plan["scope"][k] for k in ("tenant_id", "resource_id")})
            held = tx.one(
                "SELECT job,custody_id FROM app.native_resource_holds "
                "WHERE resource_key=%s OR custody_id=%s",
                (key, plan["custody_id"]),
            )
            if plan["purpose"] == "migrate":
                self.migration_admission(tx, plan, held)
            elif plan["purpose"] == "provision":
                if held:
                    raise Rejected("native_resource_held", 423)
            else:
                source = self.load(tx, tenant, plan["source_job_id"])
                if (
                    held is None
                    or str(held["job"]) != plan["source_job_id"]
                    or source["state"] != "active"
                    or source["plan"]["scope"] != plan["scope"]
                    or source["plan"]["purpose"] != "provision"
                    or source["plan"]["epoch"] != plan["epoch"]
                    or str(held["custody_id"]) != plan["custody_id"]
                    or source["plan"]["approval_id"] == plan["approval_id"]
                    or source["plan"]["plan_digest"] == plan["plan_digest"]
                ):
                    raise Rejected("separate_native_retirement_required", 423)
            tx.execute(
                "INSERT INTO app.native_jobs VALUES(%s,%s,%s,%s,%s::jsonb,%s)",
                (job, tenant, command_key, fingerprint, json.dumps(plan), self.clock()),
            )
            if campaign is not None:
                Campaigns(self.database, self.clock).attach(
                    tx, tenant, campaign[0], campaign[1], plan, job
                )
            tx.execute(
                "INSERT INTO app.native_projection(job,state,updated_at) VALUES(%s,'prepared',%s)",
                (job, self.clock()),
            )
            if held:
                tx.execute(
                    "UPDATE app.native_resource_holds SET job=%s WHERE resource_key=%s", (job, key)
                )
            else:
                tx.execute(
                    "INSERT INTO app.native_resource_holds VALUES(%s,%s,%s)",
                    (key, plan["custody_id"], job),
                )
            self.event(
                tx, job, "admitted", {"plan_sha256": fingerprint, "purpose": plan["purpose"]}
            )
            tx.execute(
                "INSERT INTO app.native_dispatch(job,workflow_id) VALUES(%s,%s)",
                (job, "p07-native-v1-" + job),
            )
        return job

    def checkpoint(self, tenant: str, job: str) -> dict[str, Any]:
        """Read the journal; queue delivery and Temporal history confer no effect authority."""
        with self.database.transaction() as tx:
            self.lock(tx)
            row = self.load(tx, tenant, job)
            result = {"state": row["state"], "revision": row["revision"], "action": "wait"}
            if row["state"] in {
                "active",
                "retired",
                "stopped",
                "held",
                "rehearsed",
                "migrated",
                "recovered",
                "cleaned",
            }:
                return result
            operations = tx.all(
                "SELECT o.stage,o.binding,v.operation AS observed FROM app.native_operations o "
                "LEFT JOIN app.native_observations v ON v.operation=o.id WHERE o.job=%s",
                (job,),
            )
            pending = [o for o in operations if o["observed"] is None]
            if pending:
                # A worker might still be executing. Only independently observed drain can advance.
                return result | {"action": "reconcile", "grant": pending[0]["binding"]}
            stages = stages_for(row["plan"])
            completed = {o["stage"] for o in operations}
            for stage in stages:
                if stage not in completed:
                    try:
                        stage_admission(tx, job, stage, None, self.clock())
                    except Rejected as error:
                        if error.reason.startswith("campaign_"):
                            return result | {"action": "wait", "reason": error.reason}
                        raise
                    return result | {"action": "prepare", "stage": stage}
            raise Rejected("native_journal_inconsistent", 423)

    def prepare(self, tenant: str, job: str, stage: str) -> dict[str, Any]:
        with self.database.transaction() as tx:
            self.lock(tx)
            row = self.load(tx, tenant, job)
            plan = row["plan"]
            stages = stages_for(plan)
            if stage not in stages:
                raise Rejected("unsupported_native_stage", 422)
            if row["state"] not in {"prepared", "running"}:
                raise Rejected("native_journey_held", 423)
            existing = tx.one(
                "SELECT id FROM app.native_operations WHERE job=%s AND stage=%s", (job, stage)
            )
            if existing:
                raise Rejected("native_attempt_requires_reconciliation", 423)
            completed = tx.all(
                "SELECT o.stage FROM app.native_operations o JOIN app.native_observations r "
                "ON r.operation=o.id WHERE o.job=%s",
                (job,),
            )
            if {r["stage"] for r in completed} != set(stages[: stages.index(stage)]):
                raise Rejected("native_stage_order", 423)
            operation, attempt, grant = (str(uuid4()) for _ in range(3))
            binding = {
                "job_id": job,
                "operation_id": operation,
                "attempt_id": attempt,
                "grant_id": grant,
                "stage": stage,
                "plan_sha256": row["fingerprint"],
                "intent_digest": plan["intents"][stage],
                "epoch": plan["epoch"],
                "executor_id": plan["executor_id"],
                "expires_at": plan["expires_at"],
            }
            if api_stage(plan, stage):
                binding["native_binding"] = {
                    **{
                        k: plan["scope"][k]
                        for k in (
                            "tenant_id",
                            "site_id",
                            "project_id",
                            "resource_id",
                        )
                    },
                    **{
                        k: plan[k]
                        for k in (
                            "campaign_id",
                            "executor_id",
                            "epoch",
                            "plan_digest",
                            "operation_plan_sha256",
                            "ownership_digest",
                            "custody_id",
                            "custody_generation",
                            "expires_at",
                        )
                    },
                    "job_id": job,
                    "operation_id": operation,
                    "attempt_id": attempt,
                }
                if plan["purpose"] == "migrate":
                    binding["schema_version"] = 2
                    binding["native_binding"]["operation_plan_sha256"] = plan["intents"][stage]
            self.require(tx, row, binding)
            proof = self.owners.observe(plan, binding, "before")
            evidence_digest = observations(plan, binding, "before", proof, self.clock())
            self.require(tx, row, binding)
            tx.execute(
                "INSERT INTO app.native_operations VALUES(%s,%s,%s,%s::jsonb,%s,%s)",
                (operation, job, stage, json.dumps(binding), digest(binding), self.clock()),
            )
            stage_admission(tx, job, stage, operation, self.clock())
            self.project(tx, job, "running")
            self.event(
                tx,
                job,
                "stage_prepared",
                {"binding": binding, "prerequisites_sha256": evidence_digest},
            )
        return binding

    def bound(
        self, tx: Transaction, tenant: str, binding: dict[str, Any], worker: str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        row = self.load(tx, tenant, binding["job_id"])
        operation = tx.one(
            "SELECT * FROM app.native_operations WHERE id=%s AND job=%s",
            (identity(binding["operation_id"]), binding["job_id"]),
        )
        if (
            operation is None
            or operation["fingerprint"] != digest(binding)
            or identity(worker) != row["plan"]["executor_id"]
        ):
            raise Rejected("native_grant_binding_denied", 403)
        return row, operation

    def boundary(
        self, tenant: str, binding: dict[str, Any], worker: str, boundary: str
    ) -> dict[str, Any]:
        if boundary not in {
            "preflight",
            "before_api_sequence",
            "during_api_sequence",
            "before_effect",
            "during_effect",
        }:
            raise Rejected("invalid_native_boundary", 422)
        with self.database.transaction() as tx:
            self.lock(tx)
            row, operation = self.bound(tx, tenant, binding, worker)
            if row["state"] != "running" or binding["expires_at"] <= self.clock():
                raise Rejected("native_grant_held", 423)
            expected = (
                {"preflight", "before_api_sequence", "during_api_sequence"}
                if api_stage(row["plan"], binding["stage"])
                else {"preflight", "before_effect", "during_effect"}
            )
            if boundary not in expected:
                raise Rejected("native_stage_boundary_mismatch", 403)
            self.require(tx, row, binding)
            redemption = tx.one(
                "SELECT worker FROM app.native_redemptions WHERE operation=%s", (operation["id"],)
            )
            if boundary in {"before_api_sequence", "before_effect"}:
                if self.clock() - operation["created_at"] > 60:
                    raise Rejected("native_dispatch_expired", 423)
                if redemption:
                    raise Rejected("native_grant_already_redeemed", 423)
                # Re-read prerequisites at the last boundary, not only at preparation.
                proof = self.owners.observe(row["plan"], binding, "before")
                observations(row["plan"], binding, "before", proof, self.clock())
                self.require(tx, row, binding)
                tx.execute(
                    "INSERT INTO app.native_redemptions VALUES(%s,%s,%s)",
                    (operation["id"], worker, self.clock()),
                )
                if row["plan"]["purpose"] == "migrate" and binding["stage"] == "admit_writes":
                    tx.execute(
                        "INSERT INTO app.native_migration_writes VALUES(%s,%s,%s)",
                        (binding["job_id"], operation["id"], self.clock()),
                    )
                self.event(
                    tx,
                    binding["job_id"],
                    "grant_redeemed",
                    {"operation_id": str(operation["id"]), "worker": worker},
                )
            elif boundary.startswith("during"):
                if redemption is None or str(redemption["worker"]) != worker:
                    raise Rejected("native_grant_not_redeemed", 423)
            elif redemption:
                raise Rejected("native_grant_already_redeemed", 423)
            if binding["expires_at"] <= self.clock():
                raise Rejected("native_grant_expired", 423)
            return {
                "binding_sha256": digest(binding),
                "epoch": row["plan"]["epoch"],
                "boundary": boundary,
                "allowed": True,
                "authority_use": "native_boundary",
                "evaluated_at": self.clock(),
                "expires_at": binding["expires_at"],
            }

    def reconcile(self, tenant: str, binding: dict[str, Any]) -> str:
        # Reads remain useful after stop/expiry. A passing read cannot renew authority.
        binding = json.loads(json.dumps(binding, allow_nan=False))
        with self.database.transaction() as tx:
            row = self.load(tx, tenant, binding["job_id"])
            self.bound(tx, tenant, binding, row["plan"]["executor_id"])
        try:
            with self.database.transaction() as tx:
                self.lock(tx)
                row = self.load(tx, tenant, binding["job_id"])
                self.bound(tx, tenant, binding, row["plan"]["executor_id"])
                complete = tx.one(
                    "SELECT operation FROM app.native_observations WHERE operation=%s",
                    (binding["operation_id"],),
                )
                if complete:
                    return str(row["state"])
                self.custody(tx, row["plan"])
                redeemed = tx.one(
                    "SELECT operation,redeemed_at FROM app.native_redemptions WHERE operation=%s",
                    (binding["operation_id"],),
                )
                if redeemed is None:
                    raise Rejected("native_effect_not_redeemed", 423)
                records = self.owners.observe(row["plan"], binding, "after")
                checksum = observations(row["plan"], binding, "after", records, self.clock())
                if any(r["observed_at"] < redeemed["redeemed_at"] for r in records):
                    raise Rejected("native_observation_predates_effect", 423)
                self.custody(tx, row["plan"])
                tx.execute(
                    "INSERT INTO app.native_observations VALUES(%s,%s,%s::jsonb,%s) "
                    "ON CONFLICT DO NOTHING",
                    (binding["operation_id"], checksum, json.dumps(records), self.clock()),
                )
                self.event(
                    tx,
                    binding["job_id"],
                    "independently_observed",
                    {"operation_id": binding["operation_id"], "observations_sha256": checksum},
                )
                stages = stages_for(row["plan"])
                terminal = terminal_for(row["plan"])
                state = terminal if binding["stage"] == stages[-1] else "running"
                if row["stopped"]:
                    state = "stopped"
                stage_complete(
                    tx,
                    binding["job_id"],
                    binding["operation_id"],
                    state == terminal,
                    self.clock(),
                )
                self.project(tx, binding["job_id"], state)
                return state
        except Exception:
            self.hold(tenant, binding["job_id"], "native_readback_held")
            raise Rejected("native_attempt_requires_reconciliation", 423) from None

    def hold(self, tenant: str, job: str, reason: str = "native_outcome_unknown") -> None:
        if reason not in {
            "native_outcome_unknown",
            "native_readback_held",
            "native_authority_lost",
        }:
            raise Rejected("invalid_native_hold", 422)
        with self.database.transaction() as tx:
            self.lock(tx)
            row = self.load(tx, tenant, job)
            self.project(tx, job, "stopped" if row["stopped"] else "held", reason)
            tx.execute(
                "UPDATE app.migration_members SET state='held',reason=%s WHERE job=%s",
                (reason, job),
            )
            self.event(tx, job, "held", {"reason": reason})

    def stop(self, tenant: str, job: str) -> None:
        with self.database.transaction() as tx:
            self.lock(tx)
            self.load(tx, tenant, job)
            tx.execute("UPDATE app.native_projection SET stopped=true WHERE job=%s", (job,))
            self.project(tx, job, "stopped", "native_stop_requested")
            self.event(tx, job, "stop_requested", {"provider_drain_required": True})

    def read(self, tenant: str, job: str) -> dict[str, Any]:
        with self.database.transaction() as tx:
            row = self.load(tx, tenant, job)
            operations = tx.all(
                "SELECT o.stage,o.id, r.operation AS redeemed,v.digest AS observation_digest "
                "FROM app.native_operations o LEFT JOIN app.native_redemptions r "
                "ON r.operation=o.id "
                "LEFT JOIN app.native_observations v ON v.operation=o.id "
                "WHERE o.job=%s ORDER BY o.created_at,o.stage",
                (job,),
            )
            return {
                "job_id": job,
                "tenant_id": tenant,
                "state": row["state"],
                "revision": row["revision"],
                "stopped": row["stopped"],
                "plan_sha256": row["fingerprint"],
                "scope": row["plan"]["scope"],
                "operations": [
                    {
                        "stage": o["stage"],
                        "operation_id": str(o["id"]),
                        "redeemed": o["redeemed"] is not None,
                        "observation_digest": o["observation_digest"],
                    }
                    for o in operations
                ],
                "retry_authorized": False,
                "native_qualification": "not_established",
            }

    def migration_admission(
        self, tx: Transaction, plan: dict[str, Any], held: dict[str, Any] | None
    ) -> None:
        from lifecycle.domain.migration import RECOVERY, recovery_matches

        migration = plan["migration"]
        if migration["mode"] not in RECOVERY:
            if held:
                raise Rejected("native_resource_held", 423)
            return
        source = self.load(tx, plan["scope"]["tenant_id"], plan["source_job_id"])
        original = source["plan"]
        if (
            held is None
            or str(held["job"]) != plan["source_job_id"]
            or str(held["custody_id"]) != plan["custody_id"]
            or original["scope"] != plan["scope"]
            or original["purpose"] != "migrate"
            or source["fingerprint"] != migration["recovery_of_sha256"]
            or plan["custody_generation"] <= original["custody_generation"]
            or original["approval_id"] == plan["approval_id"]
            or original["plan_digest"] == plan["plan_digest"]
            or not recovery_matches(original["migration"], migration)
        ):
            raise Rejected("separate_migration_recovery_required", 423)
        # Follow ancestry so a recovery or cleanup cannot erase possible target writes.
        ancestor = source
        visited: set[str] = set()
        possible_writes = False
        while True:
            key = str(ancestor["id"])
            if key in visited or len(visited) >= 64:
                raise Rejected("migration_recovery_lineage_held", 423)
            visited.add(key)
            possible_writes |= (
                tx.one("SELECT job FROM app.native_migration_writes WHERE job=%s", (key,))
                is not None
            )
            parent = ancestor["plan"]["source_job_id"]
            if parent is None:
                break
            ancestor = self.load(tx, plan["scope"]["tenant_id"], parent)
        if migration["mode"] == "rollback" and possible_writes:
            raise Rejected("target_writes_require_reconciliation", 423)
        if migration["mode"] == "cleanup" and source["state"] not in {
            "rehearsed",
            "migrated",
            "recovered",
        }:
            raise Rejected("migration_cleanup_before_acceptance", 423)
        # New recovery authority revokes the old control path atomically. Native
        # provider exclusion/drain is independently required before recovery effects.
        tx.execute("UPDATE app.native_projection SET stopped=true WHERE job=%s", (source["id"],))
        self.project(tx, str(source["id"]), "stopped", "migration_authority_superseded")
        self.event(
            tx,
            str(source["id"]),
            "migration_authority_superseded",
            {"replacement_plan_sha256": digest(plan)},
        )
