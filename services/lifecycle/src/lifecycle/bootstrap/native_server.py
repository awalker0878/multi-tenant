"""Explicit native control service and dispatcher; simulation is never mounted here."""

import argparse
import asyncio
import hmac
import os
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import uvicorn
from temporalio.client import Client
from temporalio.service import TLSConfig
from uvicorn._types import ASGIReceiveCallable, ASGISendCallable, Scope

from lifecycle.application.campaign_dispatch import CampaignDispatcher
from lifecycle.application.campaigns import Campaigns
from lifecycle.application.native_workflow import NativeWorkflow
from lifecycle.bootstrap.native_workflow import run_native
from lifecycle.domain.admission import digest
from lifecycle.domain.campaign_plan import plan_requirements
from lifecycle.domain.execution import Rejected, decode
from lifecycle.domain.native_workflow import exact
from lifecycle.infrastructure.campaign_observers import CampaignObservers, protected
from lifecycle.infrastructure.execution_owners import ExecutionOwners
from lifecycle.infrastructure.foundation import database_ready, mounted_secret
from lifecycle.infrastructure.native_effects import NativeWorkerEffects, credential
from lifecycle.infrastructure.native_owners import (
    NativeOwnerConfiguration,
    NativeOwners,
    NativeOwnerTransport,
    endpoint,
)
from lifecycle.infrastructure.store import Postgres
from lifecycle.interfaces.campaign_observations import CampaignObservationApp
from lifecycle.interfaces.campaigns import CampaignApp
from lifecycle.interfaces.http import FoundationApp
from lifecycle.interfaces.native import NativeBoundaryApp
from lifecycle.interfaces.native_jobs import NativeJobsApp


def configuration(path: Path) -> dict[str, Any]:
    value = decode(protected(str(path), 65536))
    exact(value, {"schema_version", "owners_file", "tls_cert_file", "tls_key_file"})
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise Rejected("invalid_native_service_configuration", 423)
    for key in ("owners_file", "tls_cert_file", "tls_key_file"):
        protected(value[key], 1048576)
    return value


class NativeRequestAuthority(ExecutionOwners):
    def caller(self, supplied: str, audience: str) -> None:
        if audience != "console":
            raise Rejected("invalid_workload", 401)
        incoming = mounted_secret("LIFECYCLE_CONSOLE_CALLER_FILE")
        outgoing = mounted_secret("LIFECYCLE_GOVERNANCE_CREDENTIAL_FILE")
        if incoming == outgoing or not hmac.compare_digest(incoming, supplied):
            raise Rejected("invalid_workload", 401)


class NativeControl:
    def __init__(self, path: Path) -> None:
        config = configuration(path)
        self.path, self.config_digest = path, digest(config)
        self.clock = lambda: int(time.time())
        self.configuration = NativeOwnerConfiguration(Path(config["owners_file"]), self.clock)
        self.configuration.load()
        self.owners = NativeOwners(
            self.configuration, NativeOwnerTransport(self.configuration), self.clock
        )
        database = Postgres()
        self.workflow = NativeWorkflow(database, self.owners, self.clock)
        self.campaigns = Campaigns(database, self.clock)
        self.dispatcher = CampaignDispatcher(self.campaigns, self.workflow, self.owners.resolve)
        self.boundary = NativeBoundaryApp(self.workflow, self.authorize_worker)
        self.native_jobs = NativeJobsApp(
            self.workflow,
            NativeRequestAuthority(),
            self.owners.resolve,
            self.continue_transfer,
            self.progress,
        )
        self.campaign_app = CampaignApp(
            self.campaigns,
            NativeRequestAuthority(),
            lambda tenant, ref: plan_requirements(self.owners.plan(tenant, ref), ref, tenant),
        )
        self.observation_app = CampaignObservationApp(self.campaigns, CampaignObservers().authorize)
        self.foundation = FoundationApp(database_ready)

    def authorize_worker(self, token: str) -> tuple[str, str]:
        if digest(configuration(self.path)) != self.config_digest:
            raise Rejected("native_service_configuration_changed", 423)
        return self.configuration.authorize_worker(token)

    def execute(self, grant: dict[str, Any]) -> None:
        self.effect(grant, continuation=False)

    def continue_transfer(self, grant: dict[str, Any]) -> None:
        self.effect(grant, continuation=True)

    def effect(self, grant: dict[str, Any], *, continuation: bool) -> None:
        effects = self.worker_effects(grant)
        if continuation:
            effects.continue_transfer(grant)
        else:
            effects.execute(grant)

    def progress(self, grant: dict[str, Any]) -> dict[str, Any]:
        return self.worker_effects(grant).progress(grant)

    def worker_effects(self, grant: dict[str, Any]) -> NativeWorkerEffects:
        if digest(configuration(self.path)) != self.config_digest:
            raise Rejected("native_service_configuration_changed", 423)
        config = self.configuration.load()
        workers = [
            w
            for w in config["workers"]
            if w["executor_id"] == grant.get("executor_id")
            and w["tenant_id"] == grant.get("native_binding", {}).get("tenant_id")
        ]
        if len(workers) != 1:
            raise Rejected("native_worker_scope_denied", 403)
        return NativeWorkerEffects({workers[0]["executor_id"]: endpoint(workers[0]["endpoint"])})

    async def __call__(
        self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        if scope["type"] == "http" and scope["path"] == "/internal/native-grants/checks":
            await self.boundary(scope, receive, send)
        elif scope["type"] == "http" and "/native-jobs" in scope["path"]:
            await self.native_jobs(scope, receive, send)
        elif scope["type"] == "http" and "/migration-observations/" in scope["path"]:
            await self.observation_app(scope, receive, send)
        elif scope["type"] == "http" and "/migration-campaigns" in scope["path"]:
            await self.campaign_app(scope, receive, send)
        else:
            await self.foundation(scope, receive, send)


async def dispatch(path: Path) -> None:
    control = NativeControl(path)
    client = await Client.connect(
        os.environ["TEMPORAL_TARGET"],
        namespace=os.environ["TEMPORAL_NAMESPACE"],
        tls=TLSConfig(
            server_root_ca_cert=protected(os.environ["TEMPORAL_CA_FILE"], 1048576),
            domain=os.environ.get("TEMPORAL_SERVER_NAME"),
        ),
        rpc_metadata={
            "authorization": "Bearer " + credential(Path(os.environ["TEMPORAL_CREDENTIAL_FILE"]))
        },
    )
    await run_native(client, control.workflow, control, control.dispatcher)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lifecycle-native", allow_abbrev=False)
    parser.add_argument("mode", choices=("serve", "dispatch"))
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8443)
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    try:
        config = configuration(args.config)
        if args.mode == "dispatch":
            asyncio.run(dispatch(args.config))
        else:
            uvicorn.run(
                NativeControl(args.config),
                host=args.host,
                port=args.port,
                ssl_certfile=config["tls_cert_file"],
                ssl_keyfile=config["tls_key_file"],
                lifespan="off",
                access_log=False,
                proxy_headers=False,
                server_header=False,
                limit_concurrency=64,
                timeout_keep_alive=5,
            )
        return 0
    except Exception:
        print('{"status":"native_control_unavailable"}')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
