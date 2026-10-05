"""Compose the persistent synthetic diagnostic service without product operations."""

import argparse
from collections.abc import Sequence

import uvicorn

from inventory.infrastructure.foundation import database_ready
from inventory.infrastructure.telemetry import BoundedSignalBuffer
from inventory.interfaces.http import FoundationApp
from inventory.interfaces.telemetry import RequestTelemetry


def create_app() -> RequestTelemetry:
    return RequestTelemetry(FoundationApp(database_ready), BoundedSignalBuffer().append)


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
