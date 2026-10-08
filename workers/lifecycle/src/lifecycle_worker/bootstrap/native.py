"""Native worker process: verified TLS, protected commissioning, durable native journal."""

import argparse
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import uvicorn

from lifecycle_worker.application.native import NativeHeld, decode
from lifecycle_worker.application.native_effect import NativeApiEffect
from lifecycle_worker.infrastructure.migration_bootstrap import (
    MountedMigrationRuntime,
    MountedNativeCallers,
    endpoint,
)
from lifecycle_worker.infrastructure.native_authority import LifecycleNativeBoundary
from lifecycle_worker.infrastructure.native_files import protected_read
from lifecycle_worker.infrastructure.native_journal import PostgresNativeJournal
from lifecycle_worker.infrastructure.runtime import connect
from lifecycle_worker.interfaces.native import NativeEffectApp


def configuration(path: Path) -> dict[str, Any]:
    value = decode(protected_read(path, 65536))
    if (
        set(value)
        != {
            "schema_version",
            "callers_file",
            "registry_file",
            "authority",
            "tls_cert_file",
            "tls_key_file",
        }
        or type(value["schema_version"]) is not int
        or value["schema_version"] != 1
    ):
        raise NativeHeld("invalid_native_worker_configuration")
    for key in ("callers_file", "registry_file", "tls_cert_file", "tls_key_file"):
        protected_read(Path(value[key]), 1048576)
    return value


def create_app(path: Path) -> NativeEffectApp:
    config = configuration(path)

    def clock() -> int:
        return int(time.time())

    journal = PostgresNativeJournal(connect)
    callers = MountedNativeCallers(Path(config["callers_file"]), clock)
    effects = NativeApiEffect(
        LifecycleNativeBoundary(endpoint(config["authority"])),
        journal,
        MountedMigrationRuntime(Path(config["registry_file"]), journal, clock),
        clock,
    )
    return NativeEffectApp(effects, callers.authorize)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lifecycle-worker-native", allow_abbrev=False)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8443)
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    try:
        config = configuration(args.config)
        uvicorn.run(
            create_app(args.config),
            host=args.host,
            port=args.port,
            ssl_certfile=config["tls_cert_file"],
            ssl_keyfile=config["tls_key_file"],
            lifespan="off",
            access_log=False,
            proxy_headers=False,
            server_header=False,
            limit_concurrency=16,
            timeout_keep_alive=5,
        )
        return 0
    except Exception:
        print('{"status":"native_worker_unavailable"}')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
