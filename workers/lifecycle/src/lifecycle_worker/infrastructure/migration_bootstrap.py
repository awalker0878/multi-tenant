"""Protected native migration composition. No dynamic imports, simulation or fallback.

The registry is re-read for each operation. Every entry is bound to the complete
reviewed scope and custody; editing an entry invalidates its immutable intent.
"""

import hmac
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from lifecycle_worker.application.native import (
    NativeApiAdapter,
    NativeBinding,
    NativeHeld,
    NativeObserver,
    decode,
    digest,
    identity,
)
from lifecycle_worker.infrastructure.extension_trust import ExtensionTrust
from lifecycle_worker.infrastructure.image_conversion import CopyConverter, PinnedQemuSandbox
from lifecycle_worker.infrastructure.migration_archive import MigrationArchive
from lifecycle_worker.infrastructure.migration_conversion import MigrationConversion
from lifecycle_worker.infrastructure.migration_import import MigrationImport
from lifecycle_worker.infrastructure.migration_protocol import (
    OwnerProtocolClient,
    OwnerProtocolEffect,
    OwnerProtocolObserver,
    distinct_owner_credentials,
)
from lifecycle_worker.infrastructure.native_copy import (
    GlanceImport,
    GlanceReadback,
    NativeJson,
    VmwareExport,
)
from lifecycle_worker.infrastructure.native_files import protected_read
from lifecycle_worker.infrastructure.native_http import NativeEndpoint
from lifecycle_worker.infrastructure.native_journal import PostgresNativeJournal
from lifecycle_worker.infrastructure.native_runtime import (
    MountedNativeRuntime,
    endpoints,
    independent_openstack,
)
from lifecycle_worker.infrastructure.openstack_api import NativeWrites
from lifecycle_worker.infrastructure.platform_api import (
    PlatformApi,
    PlatformHttp,
    PlatformObserver,
    distinct_credentials,
)
from lifecycle_worker.infrastructure.vmware_capture import VmwareCapture


def endpoint(value: Any) -> NativeEndpoint:
    if (
        not isinstance(value, dict)
        or set(value) != {"base_url", "address", "ca_file", "token_file"}
        or not all(isinstance(v, str) for v in value.values())
    ):
        raise NativeHeld("invalid_migration_connection")
    return NativeEndpoint(
        value["base_url"], value["address"], Path(value["ca_file"]), Path(value["token_file"])
    )


class MountedNativeCallers:
    def __init__(self, path: Path, clock: Callable[[], int]) -> None:
        self.path, self.clock = path, clock

    def authorize(self, token: str) -> tuple[str, str]:
        data = decode(protected_read(self.path, 262144))
        if (
            set(data) != {"schema_version", "callers"}
            or type(data["schema_version"]) is not int
            or data["schema_version"] != 1
        ):
            raise NativeHeld("invalid_native_callers")
        rows = data["callers"]
        if not isinstance(rows, list) or not 1 <= len(rows) <= 256:
            raise NativeHeld("invalid_native_callers")
        matches = []
        credentials = set()
        for row in rows:
            if not isinstance(row, dict) or set(row) != {
                "tenant_id",
                "executor_id",
                "token_file",
                "expires_at",
            }:
                raise NativeHeld("invalid_native_caller")
            tenant, worker = identity(row["tenant_id"]), identity(row["executor_id"])
            secret = protected_read(Path(row["token_file"]), 4096).decode("ascii").rstrip("\r\n")
            if (
                not re.fullmatch(r"[A-Za-z0-9_-]{32,4096}", secret)
                or secret in credentials
                or type(row["expires_at"]) is not int
            ):
                raise NativeHeld("invalid_native_caller_credential")
            credentials.add(secret)
            if hmac.compare_digest(secret, token) and self.clock() < row["expires_at"]:
                matches.append((tenant, worker))
        if len(matches) != 1:
            raise NativeHeld("native_caller_denied")
        return matches[0]


class MountedMigrationRuntime:
    def __init__(
        self, path: Path, journal: PostgresNativeJournal, clock: Callable[[], int]
    ) -> None:
        self.path, self.journal, self.clock = path, journal, clock

    def entry(self, binding: NativeBinding) -> dict[str, Any]:
        document = decode(protected_read(self.path, 1048576))
        if (
            set(document) != {"schema_version", "entries"}
            or type(document["schema_version"]) is not int
            or document["schema_version"] != 1
        ):
            raise NativeHeld("invalid_migration_registry")
        entries = document["entries"]
        if not isinstance(entries, list) or not 1 <= len(entries) <= 1000:
            raise NativeHeld("migration_registry_bound")
        matches = []
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) != {
                "binding",
                "expires_at",
                "plan_file",
                "adapter",
                "configuration",
                "observer",
            }:
                raise NativeHeld("invalid_migration_registry_entry")
            fields = set(NativeBinding.__dataclass_fields__) - {
                "job_id",
                "operation_id",
                "attempt_id",
                "campaign_id",
                "expires_at",
            }
            if not isinstance(entry["binding"], dict) or set(entry["binding"]) != fields:
                raise NativeHeld("migration_registry_scope_incomplete")
            if digest(entry["binding"]) == digest({k: binding.document()[k] for k in fields}):
                matches.append(entry)
        if len(matches) != 1:
            raise NativeHeld("migration_stage_not_commissioned")
        row: dict[str, Any] = matches[0]
        if (
            type(row["expires_at"]) is not int
            or self.clock() >= row["expires_at"]
            or binding.expires_at > row["expires_at"]
        ):
            raise NativeHeld("migration_commissioning_expired")
        plan = decode(protected_read(Path(row["plan_file"]), 1048576))
        if digest(plan) != binding.operation_plan_sha256:
            raise NativeHeld("migration_stage_artifact_changed")
        return row | {"plan": plan}

    def bound(
        self,
        adapter: NativeApiAdapter,
        binding: NativeBinding,
        entry: dict[str, Any],
        identity_check: Callable[[], None] = lambda: None,
    ) -> NativeApiAdapter:
        registry = self
        fingerprint = digest(entry)

        class GuardedAdapter:
            def current(self) -> None:
                if digest(registry.entry(binding)) != fingerprint:
                    raise NativeHeld("migration_commissioning_changed")
                identity_check()

            def inspect(self, supplied: NativeBinding) -> dict[str, Any]:
                if supplied.fingerprint != binding.fingerprint:
                    raise NativeHeld("migration_runtime_binding_changed")
                self.current()
                return adapter.inspect(supplied)

            def execute(self, supplied: NativeBinding, boundary: Callable[[], None]) -> None:
                if supplied.fingerprint != binding.fingerprint:
                    raise NativeHeld("migration_runtime_binding_changed")

                def current() -> None:
                    self.current()
                    boundary()
                    self.current()

                current()
                adapter.execute(supplied, current)

        return GuardedAdapter()

    def resolve(self, binding: NativeBinding) -> tuple[NativeApiAdapter, NativeObserver]:
        entry = self.entry(binding)
        kind, config, plan = entry["adapter"], entry["configuration"], entry["plan"]
        path = Path(entry["plan_file"])
        if not isinstance(config, dict):
            raise NativeHeld("invalid_migration_adapter_configuration")
        adapter: NativeApiAdapter
        if kind == "vmware_capture" and set(config) == {"source"}:
            adapter = VmwareCapture(
                path, NativeJson(endpoint(config["source"]), "vmware-api-session-id"), self.journal
            )
        elif kind == "vmware_export_archive" and set(config) == {"source", "nfc", "spool"}:
            if not isinstance(config["nfc"], dict) or not 1 <= len(config["nfc"]) <= 64:
                raise NativeHeld("invalid_nfc_registry")
            source = VmwareExport(
                NativeJson(endpoint(config["source"]), "vmware-api-session-id"),
                {k: endpoint(v) for k, v in config["nfc"].items()},
            )
            adapter = MigrationArchive(
                path, source, self.journal, self.journal, Path(config["spool"])
            )
        elif kind == "migration_copy_conversion" and set(config) == {"converter", "spool"}:
            # The read-only rootfs and executable digests are verified before claim.
            sandbox = PinnedQemuSandbox(Path(config["converter"]), lambda: None)
            adapter = MigrationConversion(
                path, CopyConverter(sandbox), self.journal, self.journal, Path(config["spool"])
            )
        elif kind == "migration_image_import" and set(config) == {"writer", "reader", "spool"}:
            writer, reader = config["writer"], config["reader"]
            for connection in (writer, reader):
                if not isinstance(connection, dict) or set(connection) != {
                    "user_id",
                    "endpoints",
                    "image",
                }:
                    raise NativeHeld("invalid_image_connection")
            image_writer_endpoints, image_reader_endpoints = (
                endpoints(writer["endpoints"]),
                endpoints(reader["endpoints"]),
            )
            image_writer, image_reader = endpoint(writer["image"]), endpoint(reader["image"])

            def image_identity_check() -> None:
                independent_openstack(
                    image_writer_endpoints | {"image": image_writer},
                    image_reader_endpoints | {"image": image_reader},
                )

            image_identity_check()
            destination = GlanceImport(
                NativeJson(image_writer, "X-Auth-Token"),
                NativeWrites(
                    image_writer_endpoints, writer["user_id"], self.clock, image_identity_check
                ),
            )
            independent = GlanceImport(
                NativeJson(image_reader, "X-Auth-Token"),
                NativeWrites(
                    image_reader_endpoints, reader["user_id"], self.clock, image_identity_check
                ),
            )
            observer = GlanceReadback(
                independent, plan, self.journal, writer["user_id"], self.clock
            )
            adapter = MigrationImport(
                path, destination, self.journal, self.journal, Path(config["spool"])
            )
            if entry["observer"] is not None:
                raise NativeHeld("unexpected_image_observer")
            adapter.inspect(binding)
            return self.bound(adapter, binding, entry, image_identity_check), observer
        elif kind == "platform_lifecycle" and set(config) == {
            "writer",
            "reader",
            "trust_file",
            "envelope_file",
            "artifact_file",
            "observer_id",
            "writer_id",
        }:
            writer_endpoint, reader_endpoint = (
                endpoint(config["writer"]),
                endpoint(config["reader"]),
            )
            distinct_credentials(writer_endpoint, reader_endpoint)
            adapter = PlatformApi(
                path,
                Path(config["envelope_file"]),
                Path(config["artifact_file"]),
                ExtensionTrust(Path(config["trust_file"]), self.clock),
                PlatformHttp(writer_endpoint, plan["platform"]),
                self.journal,
            )
            platform_observer = PlatformObserver(
                path,
                PlatformHttp(reader_endpoint, plan["platform"], read_only=True),
                self.clock,
                config["observer_id"],
                config["writer_id"],
                lambda: distinct_credentials(writer_endpoint, reader_endpoint),
            )
            if entry["observer"] is not None:
                raise NativeHeld("unexpected_platform_observer")
            adapter.inspect(binding)
            return (
                self.bound(
                    adapter,
                    binding,
                    entry,
                    lambda: distinct_credentials(writer_endpoint, reader_endpoint),
                ),
                platform_observer,
            )
        elif kind == "openstack_resources" and set(config) == {"runtime_file"}:
            adapter, native_observer = MountedNativeRuntime(
                Path(config["runtime_file"]), self.journal, self.clock
            ).resolve(binding)
            if entry["observer"] is not None:
                raise NativeHeld("unexpected_resource_observer")
            return self.bound(adapter, binding, entry), native_observer
        elif kind in {"migration_owner_protocol", "native_owner_protocol"} and set(config) == {
            "endpoint"
        }:
            if plan.get("kind") != kind:
                raise NativeHeld("owner_protocol_kind_changed")
            adapter = OwnerProtocolEffect(
                plan, OwnerProtocolClient(endpoint(config["endpoint"])), self.journal
            )
        else:
            raise NativeHeld("migration_adapter_not_supported")
        observed = entry["observer"]
        if not isinstance(observed, dict) or set(observed) != {
            "endpoint",
            "observer_id",
            "writer_id",
        }:
            raise NativeHeld("migration_independent_observer_required")
        reader_endpoint = endpoint(observed["endpoint"])
        owner_writer_endpoint = (
            endpoint(config["endpoint"])
            if "endpoint" in config
            else endpoint(config["source"])
            if "source" in config
            else None
        )

        def independent_credentials() -> None:
            if owner_writer_endpoint is not None:
                distinct_owner_credentials(owner_writer_endpoint, reader_endpoint)

        independent_credentials()
        independent_observer = OwnerProtocolObserver(
            OwnerProtocolClient(reader_endpoint, read_only=True),
            observed["observer_id"],
            observed["writer_id"],
            self.clock,
            family="native" if kind == "native_owner_protocol" else "migration",
            identity_check=independent_credentials,
        )
        adapter.inspect(binding)
        return self.bound(adapter, binding, entry, independent_credentials), independent_observer
