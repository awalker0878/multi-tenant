"""Production bootstrap composition with real protected files and TLS synthetic peers."""

import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any
from unittest.mock import Mock
from uuid import uuid4

import pytest
from test_native import Journal
from test_native import binding as binding
from test_native_http import native_tls as native_tls
from test_platform_expansion import plan_for, signed
from test_vmware_capture import Api
from test_vmware_capture import capture as capture

from lifecycle_worker.application.native import NativeBinding, NativeHeld, digest
from lifecycle_worker.infrastructure.migration_bootstrap import (
    MountedMigrationRuntime,
    MountedNativeCallers,
)
from lifecycle_worker.infrastructure.migration_protocol import (
    OwnerProtocolClient,
    OwnerProtocolEffect,
    OwnerProtocolObserver,
)
from lifecycle_worker.infrastructure.native_http import NativeReads
from lifecycle_worker.infrastructure.native_journal import PostgresNativeJournal
from lifecycle_worker.infrastructure.vmware_capture import VmwareCapture


def mounted(path: Path, data: Any) -> Path:
    path.write_text(json.dumps(data))
    path.chmod(0o600)
    return path


def test_caller_rotation_revocation_and_shared_tokens_are_checked_on_every_request(
    tmp_path: Path, binding: NativeBinding
) -> None:
    token = tmp_path / "caller.token"
    token.write_text("a" * 32)
    row = {
        "tenant_id": binding.tenant_id,
        "executor_id": binding.executor_id,
        "expires_at": 200,
        "token_file": str(token),
    }
    path = mounted(tmp_path / "callers.json", {"schema_version": 1, "callers": [row]})
    callers = MountedNativeCallers(path, lambda: 100)
    assert callers.authorize("a" * 32) == (binding.tenant_id, binding.executor_id)
    token.write_text("b" * 32)
    with pytest.raises(NativeHeld):
        callers.authorize("a" * 32)
    assert callers.authorize("b" * 32)[0] == binding.tenant_id
    mounted(path, {"schema_version": 1, "callers": [row, row | {"tenant_id": str(uuid4())}]})
    with pytest.raises(NativeHeld):
        callers.authorize("b" * 32)
    mounted(path, {"schema_version": 1, "callers": [row | {"expires_at": 100}]})
    with pytest.raises(NativeHeld):
        callers.authorize("b" * 32)


def registry(tmp_path: Path, binding: NativeBinding) -> tuple[Path, NativeBinding, dict[str, Any]]:
    plan = {
        "schema_version": 1,
        "kind": "migration_owner_protocol",
        "stage": "transform_copy",
        "protocol_sha256": "d" * 64,
        "parameters": {"guest": "qualified-profile"},
    }
    binding = replace(binding, operation_plan_sha256=digest(plan))
    fields = set(NativeBinding.__dataclass_fields__) - {
        "job_id",
        "operation_id",
        "attempt_id",
        "campaign_id",
        "expires_at",
    }
    endpoint = {
        "base_url": "https://owner.invalid",
        "address": "192.0.2.1",
        "ca_file": str(tmp_path / "ca.pem"),
        "token_file": str(tmp_path / "owner.token"),
    }
    reader_endpoint = endpoint | {"token_file": str(tmp_path / "observer.token")}
    for connection, value in ((endpoint, "w" * 64), (reader_endpoint, "r" * 64)):
        token = Path(connection["token_file"])
        token.write_text(value)
        token.chmod(0o600)
    row = {
        "binding": {k: binding.document()[k] for k in fields},
        "expires_at": 200,
        "plan_file": str(mounted(tmp_path / "plan.json", plan)),
        "adapter": "migration_owner_protocol",
        "configuration": {"endpoint": endpoint},
        "observer": {
            "endpoint": reader_endpoint,
            "observer_id": str(uuid4()),
            "writer_id": str(uuid4()),
        },
    }
    return (
        mounted(tmp_path / "registry.json", {"schema_version": 1, "entries": [row]}),
        binding,
        row,
    )


def no_database() -> Any:
    raise AssertionError("Composition must not claim an attempt or use a database")


def test_signed_platform_registry_composes_and_rejects_shared_observer(
    tmp_path: Path, binding: NativeBinding
) -> None:
    path, binding, row = registry(tmp_path, binding)
    plan, _ = plan_for(binding)
    trust, envelope, artifact, manifest, _ = signed(tmp_path, plan)
    plan["adapter_sha256"] = digest(manifest)
    binding = replace(binding, operation_plan_sha256=digest(plan))
    writer = row["configuration"]["endpoint"]
    reader = writer | {"token_file": str(tmp_path / "reader.token")}
    for connection, value in ((writer, "synthetic-writer"), (reader, "synthetic-reader")):
        token = Path(connection["token_file"])
        token.write_text(value)
        token.chmod(0o600)
    row.update(
        binding={k: binding.document()[k] for k in row["binding"]},
        adapter="platform_lifecycle",
        observer=None,
        configuration={
            "writer": writer,
            "reader": reader,
            "trust_file": str(trust.trust_file),
            "envelope_file": str(envelope),
            "artifact_file": str(artifact),
            "observer_id": str(uuid4()),
            "writer_id": str(uuid4()),
        },
    )
    mounted(Path(row["plan_file"]), plan)
    mounted(path, {"schema_version": 1, "entries": [row]})
    runtime = MountedMigrationRuntime(path, PostgresNativeJournal(no_database), lambda: 100)
    adapter, _ = runtime.resolve(binding)
    assert adapter.inspect(binding)["native_write_authorized"] is False
    row["configuration"]["observer_id"] = row["configuration"]["writer_id"]
    mounted(path, {"schema_version": 1, "entries": [row]})
    with pytest.raises(NativeHeld, match="independent_platform_principal_required"):
        runtime.resolve(binding)


@pytest.mark.parametrize(
    "field",
    [
        "tenant_id",
        "site_id",
        "project_id",
        "resource_id",
        "executor_id",
        "epoch",
        "custody_id",
        "plan_digest",
        "ownership_digest",
        "custody_generation",
    ],
)
def test_registry_binds_every_authority_dimension(
    tmp_path: Path, binding: NativeBinding, field: str
) -> None:
    path, binding, _ = registry(tmp_path, binding)
    runtime = MountedMigrationRuntime(path, PostgresNativeJournal(no_database), lambda: 100)
    assert (
        runtime.resolve(binding)[0].inspect(binding)["operation_plan_sha256"]
        == binding.operation_plan_sha256
    )
    changes = binding.document()
    changes[field] = (
        2
        if field == "custody_generation"
        else "f" * 64
        if field.endswith("digest")
        else str(uuid4())
    )
    with pytest.raises(NativeHeld, match="not_commissioned"):
        runtime.resolve(NativeBinding.parse(changes))


@pytest.mark.parametrize(
    "fault", ["expiry", "duplicate", "mutation", "adapter", "observer", "symlink"]
)
def test_bad_commissioning_is_held_before_claim(
    tmp_path: Path, binding: NativeBinding, fault: str
) -> None:
    path, binding, row = registry(tmp_path, binding)
    runtime = MountedMigrationRuntime(path, PostgresNativeJournal(no_database), lambda: 100)
    if fault == "expiry":
        row["expires_at"] = 199
    elif fault == "adapter":
        row["adapter"] = "python:simulation"
    elif fault == "observer":
        row["observer"]["observer_id"] = row["observer"]["writer_id"]
    elif fault == "mutation":
        mounted(Path(row["plan_file"]), {"changed": True})
    elif fault == "symlink":
        link = tmp_path / "link.json"
        link.symlink_to(row["plan_file"])
        row["plan_file"] = str(link)
    mounted(path, {"schema_version": 1, "entries": [row, row] if fault == "duplicate" else [row]})
    with pytest.raises(NativeHeld):
        runtime.resolve(binding)


def test_inflight_registry_revocation_stops_the_next_effect_boundary(
    tmp_path: Path, binding: NativeBinding
) -> None:
    path, binding, row = registry(tmp_path, binding)
    runtime = MountedMigrationRuntime(path, PostgresNativeJournal(no_database), lambda: 100)
    adapter = Mock()
    observed: list[str] = []

    def execute(supplied: NativeBinding, boundary: Callable[[], None]) -> None:
        assert supplied == binding
        boundary()
        observed.append("first-boundary")
        mounted(path, {"schema_version": 1, "entries": [row | {"expires_at": 100}]})
        boundary()
        observed.append("revoked-boundary")

    adapter.execute.side_effect = execute
    guarded = runtime.bound(adapter, binding, runtime.entry(binding))
    with pytest.raises(NativeHeld, match="expired"):
        guarded.execute(binding, lambda: None)
    assert observed == ["first-boundary"]


def test_owner_protocol_real_tls_binds_receipt_and_keeps_observer_independent(
    native_tls: tuple[NativeReads, dict[str, Any]], binding: NativeBinding
) -> None:
    reads, peer = native_tls
    client = OwnerProtocolClient(reads.endpoints["identity"])
    plan = {
        "schema_version": 1,
        "kind": "migration_owner_protocol",
        "stage": "final_sync",
        "protocol_sha256": "d" * 64,
        "parameters": {"datasets": ["application-owned"]},
    }
    binding = replace(binding, operation_plan_sha256=digest(plan))
    peer["body"] = json.dumps(
        {
            "binding_sha256": binding.fingerprint,
            "intent_sha256": digest(plan),
            "receipt_sha256": "a" * 64,
            "submitted": True,
            "retry_authorized": False,
        }
    ).encode()
    journal = Journal()
    journal.claim(binding)
    adapter = OwnerProtocolEffect(plan, client, journal)
    adapter.execute(binding, lambda: None)
    assert peer["requests"][0]["authorization"].startswith("Bearer ")
    assert json.loads(peer["requests"][0]["body"])["binding"] == binding.document()
    peer["status"] = 302
    with pytest.raises(NativeHeld):
        adapter.execute(binding, lambda: None)
    assert len(peer["requests"]) == 2  # No redirect or retry.
    peer["status"] = 200
    reader = str(uuid4())
    observer = OwnerProtocolObserver(client, reader, str(uuid4()), lambda: 100)
    peer["body"] = json.dumps(
        {
            "binding_sha256": binding.fingerprint,
            "intent_sha256": digest(plan),
            "observer_id": reader,
            "independent": True,
            "outcome": "observed_present",
            "observed_at": 100,
            "evidence_sha256": "e" * 64,
        }
    ).encode()
    assert observer.observe(binding, {})["outcome"] == "observed_present"
    observer.clock = lambda: 106
    with pytest.raises(NativeHeld):
        observer.observe(binding, {})


def test_owner_rotation_and_readonly_identity_cannot_cross_effect_boundary(
    native_tls: tuple[NativeReads, dict[str, Any]], binding: NativeBinding
) -> None:
    reads, peer = native_tls
    endpoint = reads.endpoints["identity"]
    reader = OwnerProtocolClient(endpoint, read_only=True)
    with pytest.raises(NativeHeld, match="observer_effect_denied"):
        reader.call("/v1/native/effects", {}, lambda: None)
    writer = OwnerProtocolClient(endpoint)

    def rotate() -> None:
        endpoint.token_file.write_text("z" * 64)

    with pytest.raises(NativeHeld, match="credential_changed"):
        writer.call("/v1/native/effects", {}, rotate)
    assert peer["requests"] == []


def test_native_owner_stage_registry_and_independent_credentials_are_enforced(
    tmp_path: Path, binding: NativeBinding
) -> None:
    path, binding, row = registry(tmp_path, binding)
    plan = json.loads(Path(row["plan_file"]).read_text())
    plan.update(kind="native_owner_protocol", stage="enroll_services")
    binding = replace(binding, operation_plan_sha256=digest(plan))
    row.update(
        adapter="native_owner_protocol", binding={k: binding.document()[k] for k in row["binding"]}
    )
    mounted(Path(row["plan_file"]), plan)
    mounted(path, {"schema_version": 1, "entries": [row]})
    runtime = MountedMigrationRuntime(path, PostgresNativeJournal(no_database), lambda: 100)
    adapter, observer = runtime.resolve(binding)
    assert adapter.inspect(binding)["native_write_authorized"] is False
    assert isinstance(observer, OwnerProtocolObserver) and observer.family == "native"
    Path(row["observer"]["endpoint"]["token_file"]).write_text("w" * 64)
    with pytest.raises(NativeHeld, match="independent_owner_read_identity_required"):
        runtime.resolve(binding)


@pytest.mark.parametrize("when", ["before_inspection", "before_execution", "at_boundary"])
@pytest.mark.parametrize("family", ["migration_owner_protocol", "native_owner_protocol"])
def test_owner_identity_rotation_is_rejected_before_any_effect(
    tmp_path: Path, binding: NativeBinding, when: str, family: str
) -> None:
    path, binding, row = registry(tmp_path, binding)
    plan = json.loads(Path(row["plan_file"]).read_text())
    plan.update(
        kind=family, stage="enroll_services" if family == "native_owner_protocol" else "final_sync"
    )
    binding = replace(binding, operation_plan_sha256=digest(plan))
    row.update(adapter=family, binding={k: binding.document()[k] for k in row["binding"]})
    mounted(Path(row["plan_file"]), plan)
    mounted(path, {"schema_version": 1, "entries": [row]})
    runtime = MountedMigrationRuntime(path, PostgresNativeJournal(no_database), lambda: 100)
    adapter, _ = runtime.resolve(binding)

    def collide() -> None:
        Path(row["observer"]["endpoint"]["token_file"]).write_text("w" * 64)

    if when != "at_boundary":
        collide()
    with pytest.raises(NativeHeld, match="independent_owner_read_identity_required"):
        if when == "before_inspection":
            adapter.inspect(binding)
        else:
            adapter.execute(binding, collide if when == "at_boundary" else lambda: None)


def test_capture_accepts_separately_enrolled_observer_origin_but_not_shared_credentials(
    tmp_path: Path, capture: tuple[NativeBinding, VmwareCapture, Api, Journal]
) -> None:
    original, capture_adapter, _, _ = capture
    path, _, row = registry(tmp_path, original)
    row.update(
        binding={k: original.document()[k] for k in row["binding"]},
        adapter="vmware_capture",
        plan_file=str(capture_adapter.plan_file),
        configuration={
            "source": row["configuration"]["endpoint"] | {"base_url": "https://vcenter.invalid"}
        },
    )
    mounted(path, {"schema_version": 1, "entries": [row]})
    runtime = MountedMigrationRuntime(path, PostgresNativeJournal(no_database), lambda: 100)
    adapter, _ = runtime.resolve(original)
    assert adapter.inspect(original)["native_write_authorized"] is False
    Path(row["observer"]["endpoint"]["token_file"]).write_text("w" * 64)
    with pytest.raises(NativeHeld, match="independent_owner_read_identity_required"):
        adapter.execute(original, lambda: None)


@pytest.mark.parametrize("when", ["resolve", "boundary"])
def test_image_import_requires_independent_credentials_before_native_effects(
    tmp_path: Path, binding: NativeBinding, when: str
) -> None:
    path, binding, row = registry(tmp_path, binding)
    plan = {
        "schema_version": 1,
        "kind": "migration_image_import",
        "conversion_plan_sha256": "a" * 64,
        "route": "glance-direct",
        "max_seconds": 600,
        "disks": [
            {
                "key": "boot",
                "image_id": str(uuid4()),
                "name": "copied-boot",
                "disk_format": "raw",
                "hw_firmware_type": "bios",
                "hw_disk_bus": "virtio",
                "virtual_bytes": 1048576,
            }
        ],
    }
    binding = replace(binding, operation_plan_sha256=digest(plan))
    spool = tmp_path / "spool"
    spool.mkdir(mode=0o700)
    connections = {}
    for role, endpoint_row in (
        ("writer", row["configuration"]["endpoint"]),
        ("reader", row["observer"]["endpoint"]),
    ):
        connections[role] = {
            "user_id": str(uuid4()),
            "image": endpoint_row,
            "endpoints": {
                service: endpoint_row for service in ("identity", "compute", "network", "volume")
            },
        }
    reader_token = Path(connections["reader"]["image"]["token_file"])
    row.update(
        binding={k: binding.document()[k] for k in row["binding"]},
        adapter="migration_image_import",
        observer=None,
        configuration={**connections, "spool": str(spool)},
    )
    mounted(Path(row["plan_file"]), plan)
    mounted(path, {"schema_version": 1, "entries": [row]})
    runtime = MountedMigrationRuntime(path, PostgresNativeJournal(no_database), lambda: 100)
    if when == "resolve":
        reader_token.write_text("w" * 64)
        with pytest.raises(NativeHeld, match="independent_openstack_credentials_required"):
            runtime.resolve(binding)
    else:
        adapter, _ = runtime.resolve(binding)

        def collide() -> None:
            reader_token.write_text("w" * 64)

        with pytest.raises(NativeHeld, match="independent_openstack_credentials_required"):
            adapter.execute(binding, collide)
