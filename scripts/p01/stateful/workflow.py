"""Synthetic durable wait; never calls a native platform or product adapter."""
from temporalio import workflow


@workflow.defn
class RestartWitness:
    def __init__(self):
        self.released = False

    @workflow.run
    async def run(self, marker: str) -> str:
        await workflow.wait_condition(lambda: self.released)
        return marker

    @workflow.signal
    def release(self):
        self.released = True

    @workflow.query
    def waiting(self) -> bool:
        return not self.released
