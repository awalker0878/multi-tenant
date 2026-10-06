"""Explicit simulation-only process; no platform SDK or generic native endpoint exists."""

import argparse
import os
import time

import uvicorn

from lifecycle_worker.application.simulation import Simulation
from lifecycle_worker.infrastructure.runtime import connect, custody, redeem, secret
from lifecycle_worker.interfaces.simulation import SimulationApp


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8449)
    args = parser.parse_args()
    app = SimulationApp(Simulation(connect, redeem, lambda: int(time.time()), custody), secret)
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=args.port,
        ssl_certfile=os.environ["SIMULATION_TLS_CERT_FILE"],
        ssl_keyfile=os.environ["SIMULATION_TLS_KEY_FILE"],
        lifespan="off",
        access_log=False,
        proxy_headers=False,
        server_header=False,
        limit_concurrency=16,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
