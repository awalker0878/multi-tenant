"""Native V1 history contains references and grants, never credentials or owner evidence."""

import asyncio
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, CancelledError, is_cancelled_exception


@workflow.defn(name="NativeJourneyV1")
class NativeJourney:
    def __init__(self) -> None:
        self.wake_revision = 0
        self.progress = "admitted"

    @workflow.signal
    def wake(self, revision: int) -> None:
        # Notifications carry no authority and cannot clear a durable hold or stop.
        if type(revision) is int:
            self.wake_revision = max(self.wake_revision, revision)

    @workflow.query
    def state(self) -> str:
        return self.progress

    async def call(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        effect = name == "native_effect_v1"
        result = await workflow.execute_activity(
            name,
            args,
            result_type=dict[str, Any],
            start_to_close_timeout=timedelta(seconds=600 if effect else 30),
            schedule_to_close_timeout=timedelta(seconds=660 if effect else 60),
            retry_policy=RetryPolicy(maximum_attempts=1),
        )
        return dict(result)

    async def hold(self, base: dict[str, Any]) -> None:
        self.progress = "held"
        try:
            await self.call("native_hold_v1", base)
        except (ActivityError, CancelledError, asyncio.CancelledError):
            # The prepared operation still excludes a second attempt if this write is unavailable.
            pass

    @workflow.run
    async def run(self, binding: dict[str, Any]) -> dict[str, Any]:
        base = {"tenant": binding["tenant"], "job": binding["job"]}
        while True:
            revision = self.wake_revision
            try:
                checkpoint = await self.call("native_checkpoint_v1", base)
                self.progress = checkpoint["state"]
                if self.progress in {"active", "retired", "stopped"}:
                    return {"state": self.progress, "native_qualification": "not_established"}
                if checkpoint["action"] == "prepare":
                    grant = await self.call(
                        "native_prepare_v1", base | {"stage": checkpoint["stage"]}
                    )
                    await self.call("native_effect_v1", base | {"grant": grant})
                    checkpoint = {"action": "reconcile", "grant": grant}
                if checkpoint["action"] == "reconcile":
                    observed = await self.call(
                        "native_reconcile_v1", base | {"grant": checkpoint["grant"]}
                    )
                    self.progress = observed["state"]
                    continue
            except ActivityError as error:
                await self.hold(base)
                if is_cancelled_exception(error):
                    raise CancelledError("native_workflow_cancelled") from None
            except (CancelledError, asyncio.CancelledError):
                # Temporal cancellation is not evidence of provider cancellation or quiescence.
                await self.hold(base)
                raise

            def awakened(current: int = revision) -> bool:
                return self.wake_revision > current

            try:
                await workflow.wait_condition(awakened, timeout=timedelta(seconds=15))
            except TimeoutError:
                pass
            if workflow.info().is_continue_as_new_suggested():
                # The committed journal remains authoritative across run and history boundaries.
                workflow.continue_as_new(binding)
