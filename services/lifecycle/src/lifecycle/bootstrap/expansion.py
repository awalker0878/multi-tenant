"""Explicit P09 control process; separate owner commissioning is mandatory."""

import argparse
import time
from collections.abc import Sequence
from pathlib import Path

import uvicorn

from lifecycle.application.adoption import Adoptions
from lifecycle.application.enterprise import Enterprise
from lifecycle.bootstrap.native_server import NativeRequestAuthority
from lifecycle.infrastructure.expansion_owners import AdoptionObservations, ExpansionOwners
from lifecycle.infrastructure.store import Postgres
from lifecycle.interfaces.expansion import ExpansionApp


def create_app(owners_file: Path) -> ExpansionApp:
    def clock() -> int:
        return int(time.time())

    owners = ExpansionOwners(owners_file, clock)
    owners.load()
    database = Postgres()
    return ExpansionApp(
        Adoptions(database, AdoptionObservations(owners), clock),
        Enterprise(database, owners, clock),
        NativeRequestAuthority(),
        owners.plan,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lifecycle-expansion", allow_abbrev=False)
    parser.add_argument("--owners", required=True, type=Path)
    parser.add_argument("--tls-cert", required=True, type=Path)
    parser.add_argument("--tls-key", required=True, type=Path)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8443)
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    try:
        from lifecycle.infrastructure.campaign_observers import protected

        protected(str(args.tls_cert), 1048576)
        protected(str(args.tls_key), 1048576)
        uvicorn.run(
            create_app(args.owners),
            host=args.host,
            port=args.port,
            ssl_certfile=str(args.tls_cert),
            ssl_keyfile=str(args.tls_key),
            lifespan="off",
            access_log=False,
            proxy_headers=False,
            server_header=False,
            limit_concurrency=32,
            timeout_keep_alive=5,
        )
        return 0
    except Exception:
        print('{"status":"expansion_control_unavailable"}')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
