"""Confirmed outbox-to-Temporal dispatch. Ambiguous starts keep the same workflow identity."""

from datetime import timedelta
from typing import Any

from temporalio import activity
from temporalio.client import Client
from temporalio.common import WorkflowIDConflictPolicy, WorkflowIDReusePolicy
from temporalio.exceptions import WorkflowAlreadyStartedError

from lifecycle.application.execution import Execution
from lifecycle.application.reservations import Database
from lifecycle.infrastructure.workflows import SimulationJourney


class Dispatcher:
    def __init__(self, database: Database, client: Client) -> None:
        self.database, self.client = database, client

    async def dispatch(self) -> int:
        with self.database.transaction() as tx:
            pending = tx.all(
                "SELECT j.id,j.tenant,j.workflow_id FROM app.execution_d"
                "ispatch d JOIN app.execution_jobs j ON j.id=d.job WHERE"
                " NOT d.dispatched ORDER BY j.admitted_at LIMIT 100"
            )
        for row in pending:
            job, tenant = str(row["id"]), str(row["tenant"])
            with self.database.transaction() as tx:
                tx.execute(
                    "UPDATE app.execution_dispatch SET attempts=attempts+1 WHERE job=%s", (job,)
                )
            try:
                handle = await self.client.start_workflow(
                    SimulationJourney.run,
                    {"job": job, "tenant": tenant, "version": 1},
                    id=row["workflow_id"],
                    task_queue="p06-simulation-v1",
                    id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE,
                    id_conflict_policy=WorkflowIDConflictPolicy.FAIL,
                    memo={"job_id": job, "tenant_id": tenant, "version": 1},
                    rpc_timeout=timedelta(seconds=5),
                )
            except WorkflowAlreadyStartedError:
                handle = self.client.get_workflow_handle(row["workflow_id"])
            # Unavailable describe leaves dispatch pending. Never invent a replacement ID.
            description = await handle.describe(rpc_timeout=timedelta(seconds=5))
            if (
                description.workflow_type != "SimulationJourneyV1"
                or await description.memo_value("job_id", None) != job
                or await description.memo_value("tenant_id", None) != tenant
                or await description.memo_value("version", None) != 1
            ):
                raise ValueError("workflow_identity_conflict")
            with self.database.transaction() as tx:
                tx.execute(
                    "UPDATE app.execution_dispatch SET dispatched=true,run_id=%s WHERE job=%s",
                    (description.run_id, job),
                )
                tx.execute(
                    "UPDATE app.execution_projection SET workflow_run_id=%s WHERE job=%s",
                    (description.run_id, job),
                )
        return len(pending)


class ExecutionActivities:
    def __init__(self, execution: Execution, worker: str) -> None:
        self.execution, self.worker = execution, worker

    @activity.defn(name="execution_checkpoint_v1")
    def checkpoint(self, args: dict[str, Any]) -> dict[str, Any]:
        return self.execution.checkpoint(args["tenant"], args["job"])

    @activity.defn(name="execution_effect_v1")
    def effect(self, args: dict[str, Any]) -> dict[str, Any]:
        return self.execution.activity(args["tenant"], args["job"], args["step"], self.worker)

    @activity.defn(name="execution_hold_v1")
    def hold(self, args: dict[str, Any]) -> dict[str, Any]:
        return self.execution.hold(args["tenant"], args["job"], args["reason"])
