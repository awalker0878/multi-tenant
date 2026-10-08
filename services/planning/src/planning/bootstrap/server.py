"""Compose the persistent synthetic diagnostic service without product operations."""

import argparse
import time
from collections.abc import Sequence

import uvicorn
from uvicorn._types import ASGIReceiveCallable, ASGISendCallable, Scope

from planning.application.migration_plans import MigrationPlans
from planning.application.migration_support import MigrationSupport
from planning.application.native_plans import NativePlans
from planning.application.planning import Planning
from planning.infrastructure.foundation import database_ready
from planning.infrastructure.migration import prepare_migration
from planning.infrastructure.migration_recipes import recipe_for, visible_recipes
from planning.infrastructure.migration_support import qualification_records, selected_tranche
from planning.infrastructure.owners import GovernanceAuthority, OwnerSources
from planning.infrastructure.store import Postgres
from planning.infrastructure.telemetry import BoundedSignalBuffer
from planning.interfaces.http import FoundationApp
from planning.interfaces.migration import MigrationPreparationApp
from planning.interfaces.native_plans import NativePlansApp
from planning.interfaces.planning import PlanningApp
from planning.interfaces.telemetry import RequestTelemetry


class PlanningRouter:
    def __init__(self) -> None:
        self.planning = PlanningApp(
            Planning(Postgres(), OwnerSources(), lambda: int(time.time())), GovernanceAuthority()
        )
        self.foundation = FoundationApp(database_ready)
        self.support = MigrationSupport(
            selected_tranche, qualification_records, lambda: int(time.time())
        )
        migrations = MigrationPlans(
            self.planning.planning,
            prepare_migration,
            recipe_for,
            visible_recipes,
            self.support.require,
        )
        self.planning.planning.migration_current = migrations.current
        self.planning.planning.migration_execution_current = migrations.execution_current
        self.migration = MigrationPreparationApp(
            self.planning.authority, prepare_migration, migrations, self.support
        )
        native = NativePlans(
            self.planning.planning,
            lambda actor, site, recipe: recipe_for(
                actor, site, recipe, file_variable="PLANNING_NATIVE_RECIPES_FILE"
            ),
        )
        self.planning.planning.native_execution_current = native.current
        self.native = NativePlansApp(self.planning.authority, native)

    async def __call__(
        self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        if scope["type"] == "http" and scope["path"].endswith("/native-plans"):
            await self.native(scope, receive, send)
        elif scope["type"] == "http" and scope["path"].endswith(
            (
                "/migration-preparations",
                "/migration-plans",
                "/migration-plan-options",
                "/migration-support",
            )
        ):
            await self.migration(scope, receive, send)
        elif scope["type"] == "http" and scope["path"].startswith("/v1/"):
            await self.planning(scope, receive, send)
        else:
            await self.foundation(scope, receive, send)


def create_app() -> RequestTelemetry:
    return RequestTelemetry(PlanningRouter(), BoundedSignalBuffer().append)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="planning-serve", allow_abbrev=False)
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
