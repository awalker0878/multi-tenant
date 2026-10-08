"""Compose the persistent synthetic diagnostic service without product operations."""

import argparse
import os
import time
from collections.abc import Sequence
from pathlib import Path

import uvicorn
from uvicorn._types import ASGIReceiveCallable, ASGISendCallable, Scope

from lifecycle.application.campaigns import Campaigns
from lifecycle.application.execution import Execution
from lifecycle.application.placement_reservations import PlacementReservations
from lifecycle.domain.campaign_plan import plan_requirements
from lifecycle.infrastructure.campaign_observers import CampaignObservers
from lifecycle.infrastructure.execution_owners import (
    EvidenceCustody,
    ExecutionOwners,
    SimulatedEffects,
)
from lifecycle.infrastructure.foundation import database_ready
from lifecycle.infrastructure.pool_snapshots import NativePoolSnapshots, capacity_caller
from lifecycle.infrastructure.store import Postgres
from lifecycle.infrastructure.telemetry import BoundedSignalBuffer
from lifecycle.interfaces.campaign_observations import CampaignObservationApp
from lifecycle.interfaces.campaigns import CampaignApp
from lifecycle.interfaces.execution import ExecutionApp
from lifecycle.interfaces.http import FoundationApp
from lifecycle.interfaces.placement_reservations import PlacementReservationApp
from lifecycle.interfaces.telemetry import RequestTelemetry


def execution_service() -> Execution:
    return Execution(
        Postgres(),
        ExecutionOwners(),
        SimulatedEffects(),
        EvidenceCustody(),
        lambda: int(time.time()),
    )


class Router:
    def __init__(self) -> None:
        self.execution = ExecutionApp(execution_service(), ExecutionOwners())
        owners = ExecutionOwners()
        self.campaigns = CampaignApp(
            Campaigns(Postgres(), lambda: int(time.time())),
            owners,
            lambda tenant, ref: plan_requirements(
                owners.plan(tenant, ref["plan_id"], ref["plan_revision"]), ref, tenant
            ),
        )
        self.campaign_observations = CampaignObservationApp(
            Campaigns(Postgres(), lambda: int(time.time())), CampaignObservers().authorize
        )
        self.placement = PlacementReservationApp(
            PlacementReservations(
                Postgres(),
                NativePoolSnapshots(Path(os.environ.get("LIFECYCLE_POOL_OWNERS_FILE", "/uncommissioned"))),
                lambda: int(time.time()),
            ),
            capacity_caller,
        )
        self.foundation = FoundationApp(database_ready)

    async def __call__(
        self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        if scope["type"] == "http" and "/placement-reservations/" in scope["path"]:
            await self.placement(scope, receive, send)
        elif scope["type"] == "http" and "/migration-observations/" in scope["path"]:
            await self.campaign_observations(scope, receive, send)
        elif scope["type"] == "http" and "/migration-campaigns" in scope["path"]:
            await self.campaigns(scope, receive, send)
        elif scope["type"] == "http" and scope["path"].startswith(("/v1/", "/internal/")):
            await self.execution(scope, receive, send)
        else:
            await self.foundation(scope, receive, send)


def create_app() -> RequestTelemetry:
    return RequestTelemetry(Router(), BoundedSignalBuffer().append)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lifecycle-serve", allow_abbrev=False)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    uvicorn.run(
        create_app(),
        host=args.host,
        port=args.port,
        lifespan="off",
        access_log=False,
        proxy_headers=False,
        server_header=False,
        limit_concurrency=32,
        timeout_keep_alive=5,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
