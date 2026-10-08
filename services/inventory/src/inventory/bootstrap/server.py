"Compose the persistent synthetic diagnostic service without product operations."

import argparse
from collections.abc import Sequence

import uvicorn
from uvicorn._types import ASGIReceiveCallable, ASGISendCallable, Scope

from inventory.application.discovery import Discovery
from inventory.infrastructure.capability_observations import MountedCapabilityObservations
from inventory.infrastructure.authority import GovernanceAuthority, planning_actor
from inventory.infrastructure.foundation import database_ready
from inventory.infrastructure.generated_configuration_streams import configuration_streams
from inventory.infrastructure.native_readers import native_reader
from inventory.infrastructure.policies import MountedPolicies
from inventory.infrastructure.readiness_evidence import read_evidence
from inventory.infrastructure.store import Postgres
from inventory.infrastructure.telemetry import BoundedSignalBuffer
from inventory.interfaces.discovery import InventoryApp
from inventory.interfaces.http import FoundationApp
from inventory.interfaces.planning import PlanningInputApp
from inventory.interfaces.telemetry import RequestTelemetry


class InventoryRouter:
    def __init__(self) -> None:
        policies = MountedPolicies()
        authority = GovernanceAuthority(policies)
        self.inventory = InventoryApp(
            Discovery(
                Postgres(),
                policies,
                authority.collection,
                configuration_streams=configuration_streams,
            ),
            authority,
            read_evidence,
        )
        self.planning = PlanningInputApp(
            self.inventory.discovery,
            planning_actor,
            native_reader,
            MountedCapabilityObservations(),
        )
        self.foundation = FoundationApp(database_ready)

    async def __call__(
        self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        if scope["type"] == "http" and any(
            p in scope["path"] for p in ("/planning-inputs/", "/planning-capability-inputs/", "/migration-inputs/")
        ):
            await self.planning(scope, receive, send)
        elif scope["type"] == "http" and (
            scope["path"].startswith("/v1/") or scope["path"].startswith("/internal/")
        ):
            await self.inventory(scope, receive, send)
        else:
            await self.foundation(scope, receive, send)


def create_app() -> RequestTelemetry:
    return RequestTelemetry(InventoryRouter(), BoundedSignalBuffer().append)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="inventory-serve", allow_abbrev=False)
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
