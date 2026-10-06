"""Versioned deterministic Temporal orchestration, with bounded activity retries."""

from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError


@workflow.defn(name="SimulationJourneyV1")
class SimulationJourney:
    def __init__(self) -> None:
        self.wake_revision = 0
        self.progress = "admitted"

    @workflow.signal
    def wake(self, revision: int) -> None:
        # A signal carries no authority; every action is read back from Lifecycle.
        self.wake_revision = max(self.wake_revision, revision)

    @workflow.query
    def state(self) -> str:
        return self.progress

    async def call(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        result = await workflow.execute_activity(
            name,
            args,
            result_type=dict[str, Any],
            start_to_close_timeout=timedelta(seconds=30),
            schedule_to_close_timeout=timedelta(minutes=2),
            retry_policy=RetryPolicy(maximum_attempts=1),
        )

        return dict(result)

    @workflow.run
    async def run(self, binding: dict[str, Any]) -> dict[str, Any]:
        # Workflow type and queue are versioned. V1 histories retain V1 code until drained.
        base = {"tenant": binding["tenant"], "job": binding["job"]}
        while True:
            revision = self.wake_revision
            try:
                checkpoint = await self.call("execution_checkpoint_v1", base)
                self.progress = checkpoint["state"]
                if self.progress in {"completed", "cancelled"}:
                    return {"state": self.progress, "simulation": True}
                if self.progress == "ready":
                    for step in checkpoint["steps"]:
                        self.progress = "running"
                        result = await self.call("execution_effect_v1", base | {"step": step})
                        if result["state"] != "confirmed_succeeded":
                            self.progress = "held"
                            break
                    else:
                        continue
            except ActivityError:
                # An activity timeout cannot tell whether acceptance occurred.
                self.progress = "held"
                try:
                    await self.call(
                        "execution_hold_v1", base | {"reason": "activity_outcome_unknown"}
                    )
                except ActivityError:
                    pass

            # Bounded polling observes committed requests even if a wake notification is lost.
            def awakened(current: int = revision) -> bool:
                return self.wake_revision > current

            try:
                await workflow.wait_condition(
                    awakened,
                    timeout=timedelta(seconds=15),
                )
            except TimeoutError:
                pass
