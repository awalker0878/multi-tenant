"""Native worker composition requires commissioned owner and effect implementations.

This factory is intentionally separate from the simulation command and HTTP router.
Its caller supplies the verified Temporal client and independently trusted native ports.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor

from temporalio.client import Client
from temporalio.worker import Worker

from lifecycle.application.campaign_dispatch import CampaignDispatcher
from lifecycle.application.native_workflow import NativeWorkflow
from lifecycle.infrastructure.native_journey import NativeJourney
from lifecycle.infrastructure.native_temporal import (
    NativeActivities,
    NativeDispatcher,
    NativeEffects,
)


async def run_native(
    client: Client,
    control: NativeWorkflow,
    effects: NativeEffects,
    campaigns: CampaignDispatcher | None = None,
) -> None:
    activities = NativeActivities(control, effects)
    dispatcher = NativeDispatcher(control.database, client)
    with ThreadPoolExecutor(max_workers=8) as executor:
        async with Worker(
            client,
            task_queue="p07-native-v1",
            workflows=[NativeJourney],
            activities=[
                activities.checkpoint,
                activities.prepare,
                activities.effect,
                activities.reconcile,
                activities.hold,
            ],
            activity_executor=executor,
        ):
            while True:
                try:
                    if campaigns is not None:
                        await asyncio.to_thread(campaigns.tick)
                    await dispatcher.dispatch()
                except Exception:
                    # Lost replies leave the same workflow identity pending.
                    print("native_dispatch_dependency_unavailable", flush=True)
                await asyncio.sleep(1)
