"""Atomic native admission outbox and single-attempt, independently reconciled activities."""

from datetime import timedelta
from typing import Any, Protocol

from temporalio import activity
from temporalio.client import Client
from temporalio.common import WorkflowIDConflictPolicy, WorkflowIDReusePolicy
from temporalio.exceptions import ApplicationError, WorkflowAlreadyStartedError

from lifecycle.application.native_workflow import NativeWorkflow
from lifecycle.application.reservations import Database
from lifecycle.domain.execution import identity, shape
from lifecycle.infrastructure.native_journey import NativeJourney


class NativeEffects(Protocol):
    def execute(self, grant: dict[str, Any]) -> None:
        """The selected worker authenticates and redeems this exact grant before every effect."""
        ...


class NativeDispatcher:
    def __init__(self, database: Database, client: Client) -> None:
        self.database, self.client = database, client

    async def dispatch(self) -> int:
        with self.database.transaction() as tx:
            pending = tx.all(
                "SELECT j.id,j.tenant,j.fingerprint,d.workflow_id FROM app.native_dispatch d "
                "JOIN app.native_jobs j ON j.id=d.job JOIN app.native_projection p ON p.job=j.id "
                "WHERE NOT d.dispatched AND NOT p.stopped ORDER BY j.created_at,j.id LIMIT 100"
            )
        for row in pending:
            job, tenant = str(row["id"]), str(row["tenant"])
            memo = {
                "job_id": job,
                "tenant_id": tenant,
                "plan_sha256": row["fingerprint"],
                "version": 1,
            }
            with self.database.transaction() as tx:
                tx.execute(
                    "UPDATE app.native_dispatch SET attempts=attempts+1 WHERE job=%s", (job,)
                )
            try:
                handle = await self.client.start_workflow(
                    NativeJourney.run,
                    {"job": job, "tenant": tenant, "version": 1},
                    id=row["workflow_id"],
                    task_queue="p07-native-v1",
                    id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE,
                    id_conflict_policy=WorkflowIDConflictPolicy.FAIL,
                    memo=memo,
                    rpc_timeout=timedelta(seconds=5),
                )
            except WorkflowAlreadyStartedError:
                handle = self.client.get_workflow_handle(row["workflow_id"])
            description = await handle.describe(rpc_timeout=timedelta(seconds=5))
            if (
                description.workflow_type != "NativeJourneyV1"
                or description.task_queue != "p07-native-v1"
            ):
                raise ValueError("native_workflow_identity_conflict")
            for key, value in memo.items():
                observed = await description.memo_value(key, None)
                if type(observed) is not type(value) or observed != value:
                    raise ValueError("native_workflow_identity_conflict")
            with self.database.transaction() as tx:
                tx.execute(
                    "UPDATE app.native_dispatch SET dispatched=true,run_id=%s WHERE job=%s",
                    (description.run_id, job),
                )
        return len(pending)


class NativeActivities:
    def __init__(self, control: NativeWorkflow, effects: NativeEffects) -> None:
        self.control, self.effects = control, effects

    def invoke(self, operation: str, args: dict[str, Any]) -> dict[str, Any]:
        try:
            extra = (
                {"stage"}
                if operation == "prepare"
                else {"grant"}
                if operation in {"effect", "reconcile"}
                else set()
            )
            shape(args, {"tenant", "job"} | extra)
            tenant, job = identity(args["tenant"]), identity(args["job"])
            if operation == "checkpoint":
                return self.control.checkpoint(tenant, job)
            if operation == "prepare":
                return self.control.prepare(tenant, job, args["stage"])
            if operation == "hold":
                self.control.hold(tenant, job)
                return {"state": "held"}
            grant = args["grant"]
            if not isinstance(grant, dict) or grant.get("job_id") != job:
                raise ValueError
            if operation == "effect":
                self.control.boundary(tenant, grant, grant["executor_id"], "preflight")
                self.effects.execute(grant)
                # Never forward worker output or treat it as independent readiness.
                return {"submitted": True}
            return {"state": self.control.reconcile(tenant, grant)}
        except Exception:
            # Keep provider/owner payloads and credentials out of Temporal history.
            raise ApplicationError("native_operation_held", non_retryable=True) from None

    @activity.defn(name="native_checkpoint_v1")
    def checkpoint(self, args: dict[str, Any]) -> dict[str, Any]:
        return self.invoke("checkpoint", args)

    @activity.defn(name="native_prepare_v1")
    def prepare(self, args: dict[str, Any]) -> dict[str, Any]:
        return self.invoke("prepare", args)

    @activity.defn(name="native_effect_v1")
    def effect(self, args: dict[str, Any]) -> dict[str, Any]:
        return self.invoke("effect", args)

    @activity.defn(name="native_reconcile_v1")
    def reconcile(self, args: dict[str, Any]) -> dict[str, Any]:
        return self.invoke("reconcile", args)

    @activity.defn(name="native_hold_v1")
    def hold(self, args: dict[str, Any]) -> dict[str, Any]:
        return self.invoke("hold", args)
