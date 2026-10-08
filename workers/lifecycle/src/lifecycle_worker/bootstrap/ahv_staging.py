"""TLS-only image staging listener inside the Lifecycle worker deployment."""

import argparse
from pathlib import Path

import uvicorn

from lifecycle_worker.application.api_plan import shape
from lifecycle_worker.application.native import decode
from lifecycle_worker.infrastructure.ahv_staging import AhvArtifactApp, AhvStaging
from lifecycle_worker.infrastructure.native_files import protected_read


def main() -> None:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8444)
    args = parser.parse_args()
    config = decode(protected_read(args.config, 16384))
    shape(config, {"root", "spool", "origin", "addresses", "tls_cert_file", "tls_key_file"})
    for key in ("tls_cert_file", "tls_key_file"):
        protected_read(Path(config[key]), 1048576)
    app = AhvArtifactApp(
        AhvStaging(Path(config["root"]), Path(config["spool"]), config["origin"]),
        config["addresses"],
    )
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        ssl_certfile=config["tls_cert_file"],
        ssl_keyfile=config["tls_key_file"],
        access_log=False,
        proxy_headers=False,
        server_header=False,
        lifespan="off",
        limit_concurrency=4,
        timeout_keep_alive=5,
    )


if __name__ == "__main__":
    main()
