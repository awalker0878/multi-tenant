"""Separately deployed Temporal poller/dispatcher with verified workflow transport."""

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from temporalio.client import Client
from temporalio.service import TLSConfig
from temporalio.worker import Worker

from lifecycle.bootstrap.server import execution_service
from lifecycle.infrastructure.execution_owners import AlertReceiver
from lifecycle.infrastructure.foundation import mounted_secret
from lifecycle.infrastructure.store import Postgres
from lifecycle.infrastructure.temporal import Dispatcher, ExecutionActivities
from lifecycle.infrastructure.workflows import SimulationJourney


async def run() -> None:
    ca = Path(os.environ["TEMPORAL_CA_FILE"])
    if not ca.is_absolute():
        raise ValueError("verified_temporal_tls_required")
    client = await Client.connect(
        os.environ["TEMPORAL_TARGET"],
        namespace=os.environ["TEMPORAL_NAMESPACE"],
        tls=TLSConfig(
            server_root_ca_cert=ca.read_bytes(), domain=os.environ.get("TEMPORAL_SERVER_NAME")
        ),
        rpc_metadata={"authorization": "Bearer " + mounted_secret("TEMPORAL_CREDENTIAL_FILE")},
    )
    execution = execution_service()
    activities = ExecutionActivities(execution, "sim-worker")
    dispatcher = Dispatcher(Postgres(), client)
    with ThreadPoolExecutor(max_workers=8) as executor:
        async with Worker(
            client,
            task_queue="p06-simulation-v1",
            workflows=[SimulationJourney],
            activities=[activities.checkpoint, activities.effect, activities.hold],
            activity_executor=executor,
        ):
            while True:
                try:
                    await dispatcher.dispatch()
                    await asyncio.to_thread(execution.deliver_alerts, AlertReceiver())
                except Exception:
                    # Durable rows remain pending. Logs never include credentials or owner payloads.
                    print("execution_dependency_unavailable", flush=True)
                await asyncio.sleep(1)


def main() -> int:
    asyncio.run(run())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
