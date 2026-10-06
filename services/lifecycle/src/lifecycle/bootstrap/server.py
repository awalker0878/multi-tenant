"""Compose the persistent synthetic diagnostic service without product operations."""

import argparse
import time
from collections.abc import Sequence

import uvicorn
from uvicorn._types import ASGIReceiveCallable, ASGISendCallable, Scope

from lifecycle.application.execution import Execution
from lifecycle.infrastructure.execution_owners import (
    EvidenceCustody,
    ExecutionOwners,
    SimulatedEffects,
)
from lifecycle.infrastructure.foundation import database_ready
from lifecycle.infrastructure.store import Postgres
from lifecycle.infrastructure.telemetry import BoundedSignalBuffer
from lifecycle.interfaces.execution import ExecutionApp
from lifecycle.interfaces.http import FoundationApp
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
        self.foundation = FoundationApp(database_ready)

    async def __call__(
        self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        if scope["type"] == "http" and scope["path"].startswith(("/v1/", "/internal/")):
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
