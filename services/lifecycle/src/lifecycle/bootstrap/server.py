"""Compose the persistent synthetic diagnostic service without product operations."""

import argparse
import os
import re
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


HTTP_OPERATIONS = (
    ("GET", "/internal/evidence-bindings/{tenant}/{job}"),
    ("POST", "/internal/simulation-grants/redemptions"),
    ("POST", "/internal/tenants/{tenant}/migration-observations/capacity"),
    ("POST", "/internal/tenants/{tenant}/migration-observations/performance"),
    ("POST", "/internal/tenants/{tenant}/migration-observations/release"),
    ("POST", "/internal/tenants/{tenant}/placement-reservations/checks"),
    ("POST", "/internal/tenants/{tenant}/placement-reservations/confirm"),
    ("POST", "/internal/tenants/{tenant}/placement-reservations/release"),
    ("POST", "/internal/tenants/{tenant}/placement-reservations/renew"),
    ("POST", "/internal/tenants/{tenant}/placement-reservations/reserve"),
    ("POST", "/v1/tenants/{tenant}/jobs"),
    ("GET", "/v1/tenants/{tenant}/jobs/{job}"),
    ("POST", "/v1/tenants/{tenant}/jobs/{job}/commands"),
    ("GET", "/v1/tenants/{tenant}/migration-campaigns"),
    ("POST", "/v1/tenants/{tenant}/migration-campaigns"),
    ("GET", "/v1/tenants/{tenant}/migration-campaigns/{campaign}"),
    ("POST", "/v1/tenants/{tenant}/migration-campaigns/{campaign}/commands"),
)


def _parameter_pattern(match: re.Match[str]) -> str:
    name = match.group()[1:-1]
    if name == "revision":
        return r"[1-9][0-9]{0,8}"
    if name == "digest":
        return r"[0-9a-f]{64}"
    return r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"


HTTP_ROUTE_PATTERNS = tuple(
    (verb, re.compile(re.sub(r"\{[a-z_]+\}", _parameter_pattern, path)))
    for verb, path in HTTP_OPERATIONS
)


async def reject_unpublished_route(scope: Scope, send: ASGISendCallable) -> bool:
    if scope["type"] != "http" or not scope["path"].startswith(("/v1/", "/internal/")):
        return False
    if any(
        verb == scope["method"] and pat.fullmatch(scope["path"])
        for verb, pat in HTTP_ROUTE_PATTERNS
    ):
        return False
    body = b'{"error":"not_found"}'
    await send(
        {
            "type": "http.response.start",
            "status": 404,
            "headers": [
                (b"content-type", b"application/json"),
                (b"cache-control", b"no-store"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
    return True


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
                NativePoolSnapshots(
                    Path(os.environ.get("LIFECYCLE_POOL_OWNERS_FILE", "/uncommissioned"))
                ),
                lambda: int(time.time()),
            ),
            capacity_caller,
        )
        self.foundation = FoundationApp(database_ready)

    async def __call__(
        self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        if await reject_unpublished_route(scope, send):
            return
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
