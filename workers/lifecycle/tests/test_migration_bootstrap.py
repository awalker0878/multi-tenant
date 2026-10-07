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
    row = {
        "binding": {k: binding.document()[k] for k in fields},
        "expires_at": 200,
        "plan_file": str(mounted(tmp_path / "plan.json", plan)),
        "adapter": "migration_owner_protocol",
        "configuration": {"endpoint": endpoint},
        "observer": {"endpoint": endpoint, "observer_id": str(uuid4()), "writer_id": str(uuid4())},
    }
    return (
        mounted(tmp_path / "registry.json", {"schema_version": 1, "entries": [row]}),
        binding,
        row,
    )


def no_database() -> Any:
    raise AssertionError("Composition must not claim an attempt or use a database")


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
