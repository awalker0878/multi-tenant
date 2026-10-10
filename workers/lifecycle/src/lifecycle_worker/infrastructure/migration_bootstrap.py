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
    NativeTransferContinuation,
    decode,
    digest,
    identity,
)
from lifecycle_worker.infrastructure.extension_trust import ExtensionTrust
from lifecycle_worker.infrastructure.image_conversion import CopyConverter, PinnedQemuSandbox
from lifecycle_worker.infrastructure.migration_conversion import MigrationConversion
from lifecycle_worker.infrastructure.native_files import protected_read
from lifecycle_worker.infrastructure.native_http import NativeEndpoint
from lifecycle_worker.infrastructure.native_image_archive import NativeImageArchive
from lifecycle_worker.infrastructure.native_image_observer import CapturedImageObserver
from lifecycle_worker.infrastructure.native_journal import PostgresNativeJournal
from lifecycle_worker.infrastructure.native_json import NativeJson
from lifecycle_worker.infrastructure.native_runtime import (
    MountedNativeRuntime,
    endpoints,
    independent_openstack,
)
from lifecycle_worker.infrastructure.openstack_api import NativeWrites
from lifecycle_worker.infrastructure.openstack_capture import OpenStackCapture
from lifecycle_worker.infrastructure.openstack_image_import import OpenStackImageImport
from lifecycle_worker.infrastructure.openstack_image_transport import GlanceImport, GlanceReadback
from lifecycle_worker.infrastructure.openstack_source_images import (
    OpenStackCapturedImages,
)
from lifecycle_worker.infrastructure.owner_protocol import (
    OwnerProtocolClient,
    OwnerProtocolEffect,
    OwnerProtocolObserver,
    distinct_owner_credentials,
)
from lifecycle_worker.infrastructure.platform_api import (
    PlatformApi,
    PlatformHttp,
    PlatformObserver,
    distinct_credentials,
)
from lifecycle_worker.infrastructure.vmware_capture import VmwareCapture
from lifecycle_worker.infrastructure.vmware_export import VmwareExport
from lifecycle_worker.infrastructure.vmware_export_archive import VmwareExportArchive


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

        if isinstance(adapter, NativeTransferContinuation):
            continuation = adapter

            class GuardedTransfer(GuardedAdapter):
                def resume_transfer(
                    self, supplied: NativeBinding, boundary: Callable[[], None]
                ) -> None:
                    if supplied.fingerprint != binding.fingerprint:
                        raise NativeHeld("migration_runtime_binding_changed")

                    def current() -> None:
                        self.current()
                        boundary()
                        self.current()

                    current()
                    continuation.resume_transfer(supplied, current)

            return GuardedTransfer()
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
        elif kind == "ahv_capture" or (
            kind == "native_image_archive" and plan.get("source_platform") == "ahv"
        ):
            from lifecycle_worker.infrastructure.ahv_accounts import probe, validate_account
            from lifecycle_worker.infrastructure.ahv_capture import AhvCapture
            from lifecycle_worker.infrastructure.ahv_http import AhvHttp
            from lifecycle_worker.infrastructure.ahv_source_images import AhvCapturedImages

            if set(config) != {"writer", "reader"} | (
                {"spool"} if kind == "native_image_archive" else set()
            ):
                raise NativeHeld("invalid_ahv_source_configuration")
            source_writer, source_reader = config["writer"], config["reader"]
            source_write_endpoint, source_read_endpoint = (
                endpoint(source_writer["endpoint"]),
                endpoint(source_reader["endpoint"]),
            )
            if (
                source_write_endpoint.base_url,
                source_write_endpoint.address,
                source_write_endpoint.ca_file,
            ) != (
                source_read_endpoint.base_url,
                source_read_endpoint.address,
                source_read_endpoint.ca_file,
            ):
                raise NativeHeld("ahv_observer_origin_changed")
            # A native stage without an exact operation-version manifest
            # cannot be executed even if a different API release was E3-rated.
            pinned = plan.get("api_versions")
            expected = dict.fromkeys(
                ("vmm", "prism", "clustermgmt", "networking", "microseg", "iam"),
                "v4.3",
            )
            if pinned != expected or (
                kind == "ahv_capture" and plan.get("schema_version") != 3
            ):
                raise NativeHeld("ahv_source_selected_version_not_pinned")
            source_write_api, source_read_api = (
                AhvHttp(source_write_endpoint, api_versions=pinned),
                AhvHttp(source_read_endpoint, read_only=True, api_versions=pinned),
            )

            def ahv_source_current() -> None:
                if digest(self.entry(binding)) != digest(entry):
                    raise NativeHeld("migration_commissioning_changed")
                distinct_credentials(source_write_endpoint, source_read_endpoint)
                if source_writer["user_id"] == source_reader["user_id"]:
                    raise NativeHeld("independent_ahv_observer_required")
                validate_account(source_writer, source_write_endpoint)
                validate_account(source_reader, source_read_endpoint)

            ahv_source_current()
            probe(
                source_write_api,
                source_writer,
                source_write_endpoint,
                self.clock,
                ahv_source_current,
            )
            probe(
                source_read_api, source_reader, source_read_endpoint, self.clock, ahv_source_current
            )
            ahv_source = AhvCapturedImages(source_write_api, source_write_endpoint)
            ahv_read_source = AhvCapturedImages(source_read_api, source_read_endpoint)
            adapter = (
                AhvCapture(path, source_write_api, self.journal)
                if kind == "ahv_capture"
                else NativeImageArchive(
                    path,
                    ahv_source,
                    self.journal,
                    self.journal,
                    Path(config["spool"]),
                    self.journal,
                )
            )
            source_observer = CapturedImageObserver(
                ahv_read_source,
                plan,
                self.journal,
                self.journal,
                source_writer["user_id"],
                source_reader["user_id"],
                self.clock,
                ahv_source_current,
                (
                    lambda supplied: ahv_read_source.reconcile_capture(
                        supplied, plan, self.journal, ahv_source_current
                    )
                )
                if kind == "ahv_capture"
                else None,
            )
            if entry["observer"] is not None:
                raise NativeHeld("unexpected_source_observer")
            adapter.inspect(binding)
            return self.bound(adapter, binding, entry, ahv_source_current), source_observer
        elif kind in {"openstack_capture", "native_image_archive"} and set(config) == (
            {"writer", "reader", "spool"}
            if kind == "native_image_archive"
            else {"writer", "reader"}
        ):
            if plan.get("source_platform", "openstack") != "openstack":
                raise NativeHeld("unsupported_native_image_source")
            writer, reader = config["writer"], config["reader"]
            for account in (writer, reader):
                if not isinstance(account, dict) or set(account) != {
                    "user_id",
                    "endpoints",
                    "image",
                }:
                    raise NativeHeld("invalid_source_connection")
            writer_endpoints, reader_endpoints = (
                endpoints(writer["endpoints"]),
                endpoints(reader["endpoints"]),
            )
            writer_image, reader_image = endpoint(writer["image"]), endpoint(reader["image"])

            def source_identity_check() -> None:
                if digest(self.entry(binding)) != digest(entry):
                    raise NativeHeld("migration_commissioning_changed")
                if writer["user_id"] == reader["user_id"]:
                    raise NativeHeld("independent_native_identity_required")
                independent_openstack(
                    writer_endpoints | {"image": writer_image},
                    reader_endpoints | {"image": reader_image},
                )

            source_identity_check()
            writer_auth = NativeWrites(
                writer_endpoints, writer["user_id"], self.clock, source_identity_check
            )
            reader_auth = NativeWrites(
                reader_endpoints, reader["user_id"], self.clock, source_identity_check
            )
            writer_source = OpenStackCapturedImages(
                NativeJson(writer_endpoints["compute"], "X-Auth-Token"),
                NativeJson(writer_image, "X-Auth-Token"),
                writer_auth,
            )
            reader_source = OpenStackCapturedImages(
                NativeJson(reader_endpoints["compute"], "X-Auth-Token"),
                NativeJson(reader_image, "X-Auth-Token"),
                reader_auth,
            )
            if kind == "openstack_capture":
                adapter = OpenStackCapture(
                    path,
                    writer_source.compute,
                    NativeJson(writer_endpoints["volume"], "X-Auth-Token"),
                    writer_source.api,
                    writer_auth,
                    self.journal,
                )
            else:
                adapter = NativeImageArchive(
                    path,
                    writer_source,
                    self.journal,
                    self.journal,
                    Path(config["spool"]),
                    self.journal,
                )
            capture_observer = CapturedImageObserver(
                reader_source,
                plan,
                self.journal,
                self.journal,
                writer["user_id"],
                reader["user_id"],
                self.clock,
            )
            if entry["observer"] is not None:
                raise NativeHeld("unexpected_source_observer")
            adapter.inspect(binding)
            return self.bound(adapter, binding, entry, source_identity_check), capture_observer
        elif kind == "vmware_export_archive" and set(config) == {"source", "nfc", "spool"}:
            if not isinstance(config["nfc"], dict) or not 1 <= len(config["nfc"]) <= 64:
                raise NativeHeld("invalid_nfc_registry")
            source = VmwareExport(
                NativeJson(endpoint(config["source"]), "vmware-api-session-id"),
                {k: endpoint(v) for k, v in config["nfc"].items()},
            )
            adapter = VmwareExportArchive(
                path, source, self.journal, self.journal, Path(config["spool"])
            )
        elif kind == "vmware_destination" and set(config) == {"writer", "reader", "nfc", "spool"}:
            from lifecycle_worker.infrastructure.vmware_import import (
                NfcUpload,
                VmwareDestination,
                VmwareDestinationObserver,
            )
            from lifecycle_worker.infrastructure.vmware_import import (
                path as vmware_path,
            )

            vm_writer, vm_reader = config["writer"], config["reader"]
            for account in (vm_writer, vm_reader):
                if not isinstance(account, dict) or set(account) != {"endpoint", "principal"}:
                    raise NativeHeld("invalid_vmware_import_account")
            vm_write_endpoint, vm_read_endpoint = (
                endpoint(vm_writer["endpoint"]),
                endpoint(vm_reader["endpoint"]),
            )
            if (
                vm_write_endpoint.base_url,
                vm_write_endpoint.address,
                vm_write_endpoint.ca_file,
            ) != (vm_read_endpoint.base_url, vm_read_endpoint.address, vm_read_endpoint.ca_file):
                raise NativeHeld("vmware_observer_origin_changed")
            vm_write_api, vm_read_api = (
                NativeJson(vm_write_endpoint, "vmware-api-session-id"),
                NativeJson(vm_read_endpoint, "vmware-api-session-id"),
            )

            def vmware_import_current() -> None:
                if digest(self.entry(binding)) != digest(entry):
                    raise NativeHeld("migration_commissioning_changed")
                distinct_credentials(vm_write_endpoint, vm_read_endpoint)
                if not vm_writer["principal"] or vm_writer["principal"] == vm_reader["principal"]:
                    raise NativeHeld("independent_vmware_observer_required")

            vmware_import_current()
            for api, account in ((vm_write_api, vm_writer), (vm_read_api, vm_reader)):
                session = api.request(
                    "GET",
                    vmware_path(plan, "SessionManager", "SessionManager", "currentSession"),
                    vmware_import_current,
                )
                if not isinstance(session, dict) or session.get("userName") != account["principal"]:
                    raise NativeHeld("vmware_import_principal_changed")
            if not isinstance(config["nfc"], dict) or not 1 <= len(config["nfc"]) <= 64:
                raise NativeHeld("invalid_nfc_registry")
            adapter = VmwareDestination(
                path,
                vm_write_api,
                NfcUpload(
                    {k: endpoint(v) for k, v in config["nfc"].items()},
                    api_origin=vm_write_endpoint.base_url,
                ),
                self.journal,
                self.journal,
                Path(config["spool"]),
            )
            vmware_observer = VmwareDestinationObserver(
                path, vm_read_api, self.journal, self.clock, vmware_import_current
            )
            if entry["observer"] is not None:
                raise NativeHeld("unexpected_vmware_observer")
            adapter.inspect(binding)
            return self.bound(adapter, binding, entry, vmware_import_current), vmware_observer
        elif kind == "migration_copy_conversion" and set(config) == {"converter", "spool"} | (
            {"guest_runtime"} if plan.get("schema_version") == 4 else set()
        ):
            # The read-only rootfs and executable digests are verified before claim.
            sandbox = PinnedQemuSandbox(Path(config["converter"]), lambda: None)
            from lifecycle_worker.infrastructure.guest_preparation import (
                GuestPreparation,
                PinnedGuestSandbox,
            )

            guest = (
                GuestPreparation(PinnedGuestSandbox(Path(config["guest_runtime"]), lambda: None))
                if "guest_runtime" in config
                else None
            )
            adapter = MigrationConversion(
                path,
                CopyConverter(sandbox),
                self.journal,
                self.journal,
                Path(config["spool"]),
                guest,
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
            adapter = OpenStackImageImport(
                path, destination, self.journal, self.journal, Path(config["spool"])
            )
            if entry["observer"] is not None:
                raise NativeHeld("unexpected_image_observer")
            adapter.inspect(binding)
            return self.bound(adapter, binding, entry, image_identity_check), observer
        elif kind == "ahv_destination" and set(config) == {"writer", "reader", "staging"}:
            from lifecycle_worker.infrastructure.ahv_accounts import probe, validate_account
            from lifecycle_worker.infrastructure.ahv_destination import (
                AhvDestination,
                AhvDestinationObserver,
            )
            from lifecycle_worker.infrastructure.ahv_http import AhvHttp
            from lifecycle_worker.infrastructure.ahv_staging import AhvStaging

            writer_account, reader_account = config["writer"], config["reader"]
            writer_endpoint, reader_endpoint = (
                endpoint(writer_account["endpoint"]),
                endpoint(reader_account["endpoint"]),
            )
            if (writer_endpoint.base_url, writer_endpoint.address, writer_endpoint.ca_file) != (
                reader_endpoint.base_url,
                reader_endpoint.address,
                reader_endpoint.ca_file,
            ):
                raise NativeHeld("ahv_observer_origin_changed")
            writer_api, reader_api = (
                AhvHttp(writer_endpoint, api_versions=plan.get("api_versions")),
                AhvHttp(reader_endpoint, read_only=True, api_versions=plan.get("api_versions")),
            )

            def ahv_identity_check() -> None:
                distinct_credentials(writer_endpoint, reader_endpoint)
                if writer_account["user_id"] == reader_account["user_id"]:
                    raise NativeHeld("independent_ahv_observer_required")
                validate_account(writer_account, writer_endpoint)
                validate_account(reader_account, reader_endpoint)

            ahv_identity_check()
            probe(writer_api, writer_account, writer_endpoint, self.clock, ahv_identity_check)
            probe(reader_api, reader_account, reader_endpoint, self.clock, ahv_identity_check)
            staged = config["staging"]
            if not isinstance(staged, dict) or set(staged) != {"root", "spool", "origin"}:
                raise NativeHeld("invalid_ahv_staging_configuration")
            staging = AhvStaging(
                Path(staged["root"]), Path(staged["spool"]), staged["origin"], self.clock
            )
            adapter = AhvDestination(path, writer_api, self.journal, self.journal, staging)
            ahv_observer = AhvDestinationObserver(
                path,
                reader_api,
                self.journal,
                self.clock,
                reader_account["user_id"],
                writer_account["user_id"],
                ahv_identity_check,
            )
            if entry["observer"] is not None:
                raise NativeHeld("unexpected_ahv_observer")
            adapter.inspect(binding)
            return self.bound(adapter, binding, entry, ahv_identity_check), ahv_observer
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
            method_plan=(
                plan
                if kind == "migration_owner_protocol" and plan.get("schema_version") == 2
                else None
            ),
        )
        adapter.inspect(binding)
        return self.bound(adapter, binding, entry, independent_credentials), independent_observer
