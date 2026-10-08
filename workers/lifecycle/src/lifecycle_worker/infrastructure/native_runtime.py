"""Resolve native API connections and operation bytes from protected runtime custody."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from lifecycle_worker.application.api_plan import validate_api_plan
from lifecycle_worker.application.native import (
    NativeApiAdapter,
    NativeBinding,
    NativeHeld,
    NativeJournal,
    NativeObserver,
    decode,
    digest,
)
from lifecycle_worker.infrastructure.native_files import protected_read
from lifecycle_worker.infrastructure.native_http import NativeEndpoint, NativeReads, credential
from lifecycle_worker.infrastructure.openstack_api import NativeWrites, OpenStackApi
from lifecycle_worker.infrastructure.openstack_readback import OpenStackReadback


def endpoints(rows: dict[str, Any]) -> dict[str, NativeEndpoint]:
    if not isinstance(rows, dict) or set(rows) != {"identity", "compute", "network", "volume"}:
        raise NativeHeld("invalid_native_connections")
    result = {}
    for name, row in rows.items():
        if not isinstance(row, dict) or set(row) != {
            "base_url",
            "address",
            "ca_file",
            "token_file",
        }:
            raise NativeHeld("invalid_native_connection")
        result[name] = NativeEndpoint(
            row["base_url"], row["address"], Path(row["ca_file"]), Path(row["token_file"])
        )
    return result


def runtime(path: Path) -> dict[str, Any]:
    config = decode(protected_read(path, 65536))
    if set(config) != {"operation_plan", "writer", "observer"}:
        raise NativeHeld("invalid_native_runtime")
    for key in ("writer", "observer"):
        if set(config[key]) != {"endpoints", "user_id"}:
            raise NativeHeld("invalid_native_identity_connection")
    return config


def independent_openstack(
    writer: dict[str, NativeEndpoint], observer: dict[str, NativeEndpoint]
) -> None:
    if (
        not writer
        or set(writer) != set(observer)
        or any(
            (endpoint.base_url, endpoint.address)
            != (observer[service].base_url, observer[service].address)
            for service, endpoint in writer.items()
        )
    ):
        raise NativeHeld("independent_openstack_destination_mismatch")
    writer_tokens = {credential(endpoint) for endpoint in writer.values()}
    observer_tokens = {credential(endpoint) for endpoint in observer.values()}
    if len(writer_tokens) != 1 or len(observer_tokens) != 1 or writer_tokens & observer_tokens:
        raise NativeHeld("independent_openstack_credentials_required")


class MountedNativeRuntime:
    def __init__(
        self, runtime_file: Path, journal: NativeJournal, clock: Callable[[], int]
    ) -> None:
        self.runtime_file, self.journal, self.clock = runtime_file, journal, clock

    def resolve(self, binding: NativeBinding) -> tuple[NativeApiAdapter, NativeObserver]:
        config = runtime(self.runtime_file)
        plan_file = Path(config["operation_plan"])
        resources = validate_api_plan(decode(protected_read(plan_file, 1_048_576)), binding)
        writer, observer = config["writer"], config["observer"]
        writer_endpoints, observer_endpoints = (
            endpoints(writer["endpoints"]),
            endpoints(observer["endpoints"]),
        )

        def current() -> None:
            if digest(runtime(self.runtime_file)) != digest(config):
                raise NativeHeld("native_runtime_changed")
            independent_openstack(writer_endpoints, observer_endpoints)

        current()
        adapter = OpenStackApi(
            plan_file,
            NativeWrites(writer_endpoints, writer["user_id"], self.clock, current),
            self.journal,
            identity_check=current,
        )
        independent = OpenStackReadback(
            NativeReads(observer_endpoints, current),
            resources,
            observer["user_id"],
            writer["user_id"],
            self.clock,
        )
        return adapter, independent
