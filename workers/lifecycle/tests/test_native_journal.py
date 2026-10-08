"""Real disposable PostgreSQL: durable holds, competing attempts and least privilege."""

import os
import shutil
import socket
import subprocess
import tempfile
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import psycopg
import pytest
from psycopg.rows import dict_row

from lifecycle_worker.application.native import NativeBinding, NativeHeld, digest
from lifecycle_worker.infrastructure.native_journal import PostgresNativeJournal


@pytest.mark.parametrize("native_id", ["vm-42", "fa7d15b1-a4d1-41b3-9cd2-f89acb50f188"])
def test_platform_lifecycle_receipts_use_native_vm_identities(native_id: str) -> None:
    request = binding()
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.execute.return_value.fetchone.return_value = {"fingerprint": request.fingerprint}
    connection.execute.return_value.fetchall.return_value = [
        {"facts": {"resource_key": "vm", "kind": "vm", "native_id": native_id}}
    ]
    ledger = PostgresNativeJournal(lambda: connection)
    assert ledger.resources(request) == {"vm": {"kind": "vm", "id": native_id}}


@pytest.mark.parametrize("native_id", ["foreign/vm-42", "vm-0", "unbound"])
def test_platform_lifecycle_receipts_reject_invalid_vm_identities(native_id: str) -> None:
    request = binding()
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.execute.return_value.fetchone.return_value = {"fingerprint": request.fingerprint}
    connection.execute.return_value.fetchall.return_value = [
        {"facts": {"resource_key": "vm", "kind": "vm", "native_id": native_id}}
    ]
    with pytest.raises(NativeHeld, match="invalid_native_identity"):
        PostgresNativeJournal(lambda: connection).resources(request)


@pytest.fixture(scope="module")
def postgres() -> Iterator[dict[str, Any]]:
    bindir = os.environ.get("P07_POSTGRES_BIN")
    if not bindir:
        pytest.skip("P07_POSTGRES_BIN is required for real journal qualification")
    private = Path(tempfile.mkdtemp(prefix="p07-native-postgres-"))
    private.chmod(0o755)
    root = os.getuid() == 0
    if root:
        os.chown(private, 65534, 65534)

    def unprivileged() -> None:
        if root:
            os.setgid(65534)
            os.setuid(65534)

    process = None
    try:
        subprocess.run(
            [
                str(Path(bindir) / "initdb"),
                "-D",
                str(private / "data"),
                "-A",
                "trust",
                "-U",
                "postgres",
                "--no-locale",
                "--encoding=UTF8",
            ],
            check=True,
            capture_output=True,
            preexec_fn=unprivileged,
        )
        subprocess.run(
            [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-nodes",
                "-keyout",
                str(private / "server.key"),
                "-out",
                str(private / "server.crt"),
                "-days",
                "1",
                "-subj",
                "/CN=localhost",
                "-addext",
                "subjectAltName=IP:127.0.0.1,DNS:localhost",
            ],
            check=True,
            capture_output=True,
        )
        for name in ("server.key", "server.crt"):
            if root:
                os.chown(private / name, 65534, 65534)
            (private / name).chmod(0o600 if name.endswith("key") else 0o644)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        config = private / "data/postgresql.conf"
        config.write_text(
            config.read_text()
            + f"\nlisten_addresses='127.0.0.1'\nport={port}\nunix_socket_directories=''\n"
            f"ssl=on\nssl_cert_file='{private}/server.crt'\nssl_key_file='{private}/server.key'\n"
        )
        with (private / "postgres.log").open("w") as log:
            process = subprocess.Popen(
                [str(Path(bindir) / "postgres"), "-D", str(private / "data")],
                preexec_fn=unprivileged,
                stdout=log,
                stderr=log,
            )
        settings = {
            "host": "127.0.0.1",
            "port": port,
            "user": "postgres",
            "dbname": "postgres",
            "sslmode": "verify-full",
            "sslrootcert": str(private / "server.crt"),
        }
        for _ in range(100):
            try:
                with psycopg.connect(**settings, autocommit=True) as c:
                    c.execute("CREATE ROLE native_owner NOLOGIN")
                    c.execute("CREATE ROLE native_runtime LOGIN")
                    c.execute("CREATE DATABASE native_test OWNER native_owner")
                break
            except psycopg.OperationalError:
                time.sleep(0.1)
        else:
            raise RuntimeError("disposable_postgres_unavailable")
        settings["dbname"] = "native_test"
        with psycopg.connect(**settings) as c:
            c.execute("SET LOCAL ROLE native_owner")
            migrations = sorted((Path(__file__).parents[1] / "migrations/native").glob("*.sql"))
            for migration in migrations:
                c.execute(migration.read_text())
        yield settings | {"user": "native_runtime"}
    finally:
        if process:
            process.terminate()
            process.wait(timeout=10)
        shutil.rmtree(private)


def binding() -> NativeBinding:
    return NativeBinding.parse(
        {
            k: str(uuid4())
            for k in (
                "tenant_id",
                "site_id",
                "project_id",
                "resource_id",
                "job_id",
                "operation_id",
                "attempt_id",
                "campaign_id",
                "executor_id",
                "epoch",
                "custody_id",
            )
        }
        | {
            "plan_digest": "a" * 64,
            "operation_plan_sha256": "b" * 64,
            "ownership_digest": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
            "custody_generation": 1,
            "expires_at": int(time.time()) + 60,
        }
    )


def journal(settings: dict[str, Any]) -> PostgresNativeJournal:
    return PostgresNativeJournal(lambda: psycopg.connect(**settings, row_factory=dict_row))


def test_concurrent_duplicate_deliveries_claim_once(postgres: dict[str, Any]) -> None:
    request = binding()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: journal(postgres).claim(request), range(16)))
    assert results.count(True) == 1 and results.count(False) == 15
    journal(postgres).record(request, "request_started", {})
    assert not journal(postgres).claim(request)  # a new adapter process cannot repeat it


def test_cross_tenant_ownership_digest_and_changed_attempt_denied(postgres: dict[str, Any]) -> None:
    request = binding()
    assert journal(postgres).claim(request)
    with pytest.raises(NativeHeld, match="binding_conflict"):
        journal(postgres).claim(replace(request, attempt_id=str(uuid4())))
    with pytest.raises(NativeHeld, match="custody_held"):
        journal(postgres).claim(
            replace(
                request, tenant_id=str(uuid4()), operation_id=str(uuid4()), attempt_id=str(uuid4())
            )
        )
    with pytest.raises(NativeHeld, match="not_bound"):
        journal(postgres).record(replace(request, tenant_id=str(uuid4())), "readback", {})


@pytest.mark.parametrize(
    "statement",
    [
        "DELETE FROM native.custody_holds",
        "DELETE FROM native.events",
        "UPDATE native.attempts SET fingerprint=repeat('a',64)",
        "TRUNCATE native.custody_holds",
        "ALTER TABLE native.attempts DROP COLUMN fingerprint",
    ],
)
def test_runtime_cannot_erase_uncertainty(postgres: dict[str, Any], statement: str) -> None:
    with psycopg.connect(**postgres) as connection:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            connection.execute(statement)


def test_unknown_effect_event_and_hold_survive_reconnect(postgres: dict[str, Any]) -> None:
    request = binding()
    original = journal(postgres)
    assert original.claim(request)
    original.record(request, "outcome_unknown", {"reason": "lost_reply"})
    with psycopg.connect(**postgres, row_factory=dict_row) as connection:
        row = connection.execute(
            "SELECT facts FROM native.events WHERE operation_id=%s", (request.operation_id,)
        ).fetchone()
        assert row and row["facts"] == {"reason": "lost_reply"}
    assert not journal(postgres).claim(request)


def test_accepted_ids_and_transfer_hashes_survive_new_journal_instance(
    postgres: dict[str, Any],
) -> None:
    request = binding()
    original = journal(postgres)
    assert original.claim(request)
    object_id = str(uuid4())
    original.record(request, "request_started", {"resource_key": "boot", "kind": "image"})
    original.record(
        request,
        "request_accepted",
        {
            "resource_key": "boot",
            "kind": "image",
            "native_id": object_id,
            "response_sha256": "a" * 64,
        },
    )
    original.record(
        request,
        "disk_transferred",
        {
            "resource_key": "boot",
            "size": 4096,
            "sha256": "b" * 64,
            "sha512": "c" * 128,
        },
    )
    recovered = journal(postgres)
    assert not recovered.claim(request)
    assert recovered.resources(request) == {"boot": {"kind": "image", "id": object_id}}
    assert recovered.transfers(request)["boot"]["sha256"] == "b" * 64
    with pytest.raises(NativeHeld, match="not_bound"):
        recovered.resources(replace(request, operation_plan_sha256="d" * 64))
    with pytest.raises(NativeHeld, match="not_bound"):
        recovered.transfers(replace(request, custody_generation=2))


def test_duplicate_native_receipts_never_guess_resource_identity(postgres: dict[str, Any]) -> None:
    request = binding()
    ledger = journal(postgres)
    assert ledger.claim(request)
    for _ in range(2):
        ledger.record(
            request,
            "request_accepted",
            {
                "resource_key": "vm",
                "kind": "server",
                "native_id": str(uuid4()),
            },
        )
    with pytest.raises(NativeHeld, match="ambiguous_native_receipt"):
        ledger.resources(request)


def test_migration_stage_custody_and_monotonic_recovery_generation(
    postgres: dict[str, Any],
) -> None:
    first = binding()
    j = journal(postgres)
    assert j.claim(first)
    second = replace(first, operation_id=str(uuid4()), attempt_id=str(uuid4()))
    assert j.claim(second)  # same admitted job; Lifecycle authorizes stage ordering
    with pytest.raises(NativeHeld, match="custody_held"):
        j.claim(
            replace(second, job_id=str(uuid4()), operation_id=str(uuid4()), attempt_id=str(uuid4()))
        )
    recovery = replace(
        second,
        job_id=str(uuid4()),
        operation_id=str(uuid4()),
        attempt_id=str(uuid4()),
        custody_generation=first.custody_generation + 1,
    )
    assert j.claim(recovery)
    with pytest.raises(NativeHeld, match="custody_held"):
        j.claim(replace(first, operation_id=str(uuid4()), attempt_id=str(uuid4())))
    with pytest.raises(NativeHeld, match="custody_held"):
        j.claim(
            replace(
                recovery,
                tenant_id=str(uuid4()),
                operation_id=str(uuid4()),
                attempt_id=str(uuid4()),
                custody_generation=recovery.custody_generation + 1,
            )
        )
    with psycopg.connect(**postgres) as c:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            c.execute("DELETE FROM native.custody_generations")


def test_capture_receipt_resolution_cannot_cross_job_or_approved_plan(
    postgres: dict[str, Any],
) -> None:
    capture = binding()
    j = journal(postgres)
    assert j.claim(capture)
    facts = {
        "source_vm_id": "vm-1",
        "clone_vm_id": "vm-2",
        "snapshot_id": "snapshot-1",
        "clone_config_sha256": "c" * 64,
        "disks_sha256": "d" * 64,
        "power_state": "poweredOff",
        "network_devices": 0,
    }
    j.record(capture, "clone_bound", facts)
    export = replace(
        capture, operation_id=str(uuid4()), attempt_id=str(uuid4()), operation_plan_sha256="e" * 64
    )
    assert j.capture(export, capture.operation_plan_sha256) == facts
    for changed in (
        replace(export, job_id=str(uuid4())),
        replace(export, tenant_id=str(uuid4())),
        replace(export, plan_digest="f" * 64),
    ):
        with pytest.raises(NativeHeld):
            j.capture(changed, capture.operation_plan_sha256)
    j.record(capture, "clone_bound", facts)
    with pytest.raises(NativeHeld, match="ambiguous"):
        j.capture(export, capture.operation_plan_sha256)


def test_partial_artifact_is_not_a_conversion_or_import_source(postgres: dict[str, Any]) -> None:
    export = binding()
    j = journal(postgres)
    assert j.claim(export)
    disk = {"resource_key": "disk-2000", "size": 512, "sha256": "a" * 64, "sha512": "b" * 128}
    j.record(export, "disk_transferred", disk)
    conversion = replace(
        export, operation_id=str(uuid4()), attempt_id=str(uuid4()), operation_plan_sha256="e" * 64
    )
    with pytest.raises(NativeHeld, match="incomplete"):
        j.artifact(conversion, export.operation_plan_sha256, "archive")
    j.record(
        export,
        "export_complete",
        {
            "descriptor_sha256": "c" * 64,
            "manifest_sha256": "d" * 64,
            "disks_sha256": digest(
                {"disk-2000": {k: v for k, v in disk.items() if k != "resource_key"}}
            ),
        },
    )
    result = j.artifact(conversion, export.operation_plan_sha256, "archive")
    assert result["operation_id"] == export.operation_id
    assert result["disks"] == {"disk-2000": disk}
    with pytest.raises(NativeHeld):
        j.artifact(
            replace(conversion, job_id=str(uuid4())), export.operation_plan_sha256, "archive"
        )
    with pytest.raises(NativeHeld):
        j.artifact(conversion, export.operation_plan_sha256, "conversion")


@pytest.mark.parametrize("fault", ["wrong_digest", "late_disk"])
def test_completed_artifact_cannot_gain_unbound_disks(postgres: dict[str, Any], fault: str) -> None:
    export = binding()
    j = journal(postgres)
    assert j.claim(export)
    receipt = {"size": 512, "sha256": "a" * 64, "sha512": "b" * 128}
    j.record(export, "disk_transferred", {"resource_key": "disk-2000", **receipt})
    j.record(
        export,
        "export_complete",
        {"disks_sha256": "c" * 64 if fault == "wrong_digest" else digest({"disk-2000": receipt})},
    )
    if fault == "late_disk":
        j.record(export, "disk_transferred", {"resource_key": "disk-2001", **receipt})
    with pytest.raises(NativeHeld):
        j.artifact(export, export.operation_plan_sha256, "archive")


def test_ahv_tasks_survive_reconnect_and_remain_bound_to_the_attempt(
    postgres: dict[str, Any],
) -> None:
    b = binding()
    j = journal(postgres)
    assert j.claim(b)
    task = {
        "resource_key": "disk-1",
        "kind": "image",
        "task_id": "ergon:" + str(uuid4()),
        "request_id": str(uuid4()),
    }
    j.record(b, "ahv_task_accepted", task)
    assert journal(postgres).ahv_tasks(b) == {"disk-1": task}
    assert j.resources(b) == {}  # Task acceptance is not native image completion.
    with pytest.raises(NativeHeld, match="not_bound"):
        j.ahv_tasks(replace(b, tenant_id=str(uuid4())))
    j.record(b, "ahv_task_accepted", task)
    with pytest.raises(NativeHeld, match="ambiguous"):
        j.ahv_tasks(b)


def test_archive_progress_retains_only_verified_disk_counts_and_bound_completion(
    postgres: dict[str, Any],
) -> None:
    request = binding()
    original = journal(postgres)
    assert original.claim(request)
    original.record(request, "transfer_started", {"resource_key": "root"})
    assert original.archive_progress(request) == {
        "bytes_completed": 0,
        "disks_completed": 0,
        "artifact_complete": False,
    }
    disk = {"size": 1024, "sha256": "a" * 64, "sha512": "b" * 128}
    original.record(request, "disk_transferred", {"resource_key": "root", **disk})
    assert journal(postgres).archive_progress(request) == {
        "bytes_completed": 1024,
        "disks_completed": 1,
        "artifact_complete": False,
    }
    original.record(request, "export_complete", {"disks_sha256": digest({"root": disk})})
    assert journal(postgres).archive_progress(request)["artifact_complete"] is True
    with pytest.raises(NativeHeld, match="not_bound"):
        original.archive_progress(replace(request, tenant_id=str(uuid4())))
    original.record(request, "disk_transferred", {"resource_key": "other", **disk})
    with pytest.raises(NativeHeld, match="ambiguous"):
        original.archive_progress(request)


@pytest.mark.parametrize(
    "event",
    [
        "source_request_started",
        "source_object_created",
        "source_capture_bound",
        "transfer_started",
        "transfer_continued",
        "continuation_held",
        "guest_copy_prepared",
        "import_lease",
    ],
)
def test_any_to_any_receipts_survive_postgres_constraint_and_reconnect(
    postgres: dict[str, Any],
    event: str,
) -> None:
    request = binding()
    j = journal(postgres)
    assert j.claim(request)
    j.record(request, event, {"evidence_sha256": "a" * 64})
    with psycopg.connect(**postgres, row_factory=dict_row) as connection:
        row = connection.execute(
            "SELECT kind,facts FROM native.events WHERE operation_id=%s",
            (request.operation_id,),
        ).fetchone()
    assert row == {"kind": event, "facts": {"evidence_sha256": "a" * 64}}


def test_vmware_datacenter_and_vm_ids_remain_native_and_tenant_scoped(
    postgres: dict[str, Any],
) -> None:
    request = replace(binding(), project_id="datacenter-42")
    assert NativeBinding.parse(request.document()) == request
    j = journal(postgres)
    assert j.claim(request)
    j.record(
        request, "request_accepted", {"kind": "server", "resource_key": "vm", "native_id": "vm-51"}
    )
    assert j.resources(request) == {"vm": {"kind": "server", "id": "vm-51"}}
    with pytest.raises(NativeHeld):
        j.resources(replace(request, project_id="datacenter-43"))


def test_concurrent_recovered_capture_receipts_are_idempotent_but_conflicts_hold(
    postgres: dict[str, Any],
) -> None:
    request = binding()
    ledger = journal(postgres)
    assert ledger.claim(request)
    facts: dict[str, Any] = {
        "source_platform": "ahv",
        "disks": {"root": {"image_id": str(uuid4())}},
    }
    accepted = {
        "resource_key": "root",
        "kind": "image",
        "native_id": facts["disks"]["root"]["image_id"],
        "task_id": "ZXJnb24=:" + str(uuid4()),
        "request_id": str(uuid4()),
    }

    def reconcile(_: int) -> None:
        fresh = journal(postgres)
        fresh.record(request, "request_accepted", accepted)
        fresh.record(request, "source_capture_bound", facts)

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(reconcile, range(8)))
    assert ledger.capture(request, request.operation_plan_sha256) == facts
    assert ledger.resources(request) == {"root": {"kind": "image", "id": accepted["native_id"]}}
    with pytest.raises(NativeHeld, match="conflict"):
        ledger.record(request, "request_accepted", accepted | {"native_id": str(uuid4())})
    with pytest.raises(NativeHeld, match="conflict"):
        ledger.record(request, "source_capture_bound", facts | {"unexpected": True})
