"""Concrete method dispatch, scoped dataset readback and denied unsafe data effects."""

import copy
import json
from dataclasses import replace
from itertools import product
from pathlib import Path
from typing import Any
from unittest.mock import Mock
from uuid import uuid4

import pytest
from test_migration_bootstrap import mounted, no_database, registry
from test_native import Journal
from test_native import binding as binding
from test_native_http import native_tls as native_tls

from lifecycle_worker.application.native import NativeBinding, NativeHeld, digest
from lifecycle_worker.infrastructure.migration_bootstrap import MountedMigrationRuntime
from lifecycle_worker.infrastructure.migration_method import (
    MECHANISMS,
    OPERATIONS,
    contract,
    measured,
)
from lifecycle_worker.infrastructure.native_http import NativeReads
from lifecycle_worker.infrastructure.native_journal import PostgresNativeJournal
from lifecycle_worker.infrastructure.owner_protocol import (
    OwnerProtocolClient,
    OwnerProtocolEffect,
    OwnerProtocolObserver,
)


def method_plan(
    method: str, stage: str, source: str = "ahv", target: str = "vmware"
) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "kind": "migration_owner_protocol",
        "stage": stage,
        "protocol_sha256": digest("synthetic-installed-owner-contract"),
        "parameters": {},
        "method_contract": {
            "method": method,
            "operation": OPERATIONS[method][stage],
            **{
                side: {
                    "platform": platform,
                    "installation_id": str(uuid4()),
                    "native_identity_sha256": digest([side, platform]),
                }
                for side, platform in (("source", source), ("target", target))
            },
            "datasets": {
                str(uuid4()): {
                    k: digest([i, k])
                    for k in ("source_sha256", "target_sha256", "consistency_sha256")
                }
                for i in range(2)
            },
            "mechanism": {
                "kind": MECHANISMS[method],
                "version": "synthetic-1",
                "artifact_sha256": digest("connector"),
                "qualification_sha256": digest("qualified-mechanism"),
            },
            "consistency_boundary_sha256": digest("application-consistency-point"),
            "writer_fence_sha256": digest("native-single-writer-fence"),
            "recovery_sha256": digest("retained-state-recovery"),
            "predecessor_receipt_sha256": digest("prior-stage"),
            "reverse_qualification_sha256": digest("reverse-qualified")
            if stage == "reverse_sync"
            else None,
            "limits": {"max_seconds": 120, "max_lag_seconds": 0, "max_data_loss_bytes": 0},
        },
    }


def measurement(c: dict[str, Any]) -> dict[str, Any]:
    return {
        "method_contract_sha256": digest(c),
        "consistency_boundary_sha256": c["consistency_boundary_sha256"],
        "recovery_sha256": c["recovery_sha256"],
        "source_writer_fenced": True,
        "target_writer_fenced": True,
        "elapsed_seconds": 10,
        "datasets": {
            key: {
                "dataset_sha256": digest(row),
                "observed_at": 100,
                "source_boundary_sha256": digest("source-boundary"),
                "target_boundary_sha256": digest("target-boundary"),
                "lag_seconds": 0,
                "data_loss_bytes": 0,
                "integrity_verified": True,
                "metadata_verified": True,
                "evidence_sha256": digest([key, "native-dataset-read"]),
            }
            for key, row in c["datasets"].items()
        },
    }


@pytest.mark.parametrize(
    ("source", "target"), list(product(("vmware", "openstack", "ahv"), repeat=2))
)
@pytest.mark.parametrize(
    ("method", "stage"),
    [(method, stage) for method, stages in OPERATIONS.items() for stage in stages],
)
def test_protected_runtime_dispatches_exact_data_mechanism_in_every_direction(
    tmp_path: Path, binding: NativeBinding, source: str, target: str, method: str, stage: str
) -> None:
    path, binding, row = registry(tmp_path, binding)
    plan = method_plan(method, stage, source, target)
    binding = replace(binding, operation_plan_sha256=digest(plan))
    row["binding"] = {k: binding.document()[k] for k in row["binding"]}
    mounted(Path(row["plan_file"]), plan)
    mounted(path, {"schema_version": 1, "entries": [row]})
    adapter, observer = MountedMigrationRuntime(
        path, PostgresNativeJournal(no_database), lambda: 100
    ).resolve(binding)
    assert adapter.inspect(binding)["native_write_authorized"] is False
    assert isinstance(observer, OwnerProtocolObserver) and observer.method_plan == plan
    # No fake claim or database was required merely to resolve the actual runtime.


@pytest.mark.parametrize(
    "fault",
    [
        "operation",
        "platform",
        "same_environment",
        "mechanism",
        "dataset",
        "predecessor",
        "reverse",
        "parameters",
    ],
)
def test_mismatched_data_method_is_held_before_native_submission(
    binding: NativeBinding, fault: str
) -> None:
    plan = method_plan("EXTERNAL_BLOCK_REPLICATION", "reverse_sync")
    c = plan["method_contract"]
    if fault == "operation":
        c["operation"] = "application_restore"
    elif fault == "platform":
        c["source"]["platform"] = "unknown"
    elif fault == "same_environment":
        c["target"]["installation_id"] = c["source"]["installation_id"]
    elif fault == "mechanism":
        c["mechanism"]["kind"] = "file_metadata_delta"
    elif fault == "dataset":
        c["datasets"] = {}
    elif fault == "predecessor":
        c["predecessor_receipt_sha256"] = None
    elif fault == "reverse":
        c["reverse_qualification_sha256"] = None
    elif fault == "parameters":
        plan["parameters"] = {"command": "untyped"}
    b = replace(binding, operation_plan_sha256=digest(plan))
    with pytest.raises(NativeHeld):
        OwnerProtocolEffect(plan, Mock(), Journal()).inspect(b)


@pytest.mark.parametrize(
    "fault",
    [
        "",
        "partial",
        "stale",
        "identity",
        "lag",
        "loss",
        "integrity",
        "metadata",
        "source_writer",
        "target_writer",
        "deadline",
        "boundary",
    ],
)
def test_independent_dataset_readback_enforces_every_limit(fault: str) -> None:
    c = contract(
        method_plan("VM_SNAPSHOT_BASELINE_FILE_DELTA", "final_sync")["method_contract"],
        "final_sync",
    )
    result = measurement(c)
    key = next(iter(result["datasets"]))
    row = result["datasets"][key]
    if fault == "partial":
        result["datasets"].pop(key)
    elif fault == "stale":
        row["observed_at"] = 94
    elif fault == "identity":
        row["dataset_sha256"] = digest("different-dataset")
    elif fault == "lag":
        row["lag_seconds"] = 1
    elif fault == "loss":
        row["data_loss_bytes"] = 1
    elif fault == "integrity":
        row["integrity_verified"] = False
    elif fault == "metadata":
        row["metadata_verified"] = False
    elif fault == "source_writer":
        result["source_writer_fenced"] = False
    elif fault == "target_writer":
        result["target_writer_fenced"] = False
    elif fault == "deadline":
        result["elapsed_seconds"] = 121
    elif fault == "boundary":
        result["consistency_boundary_sha256"] = digest("different-boundary")
    if fault:
        with pytest.raises(NativeHeld):
            measured(result, c, 100)
    else:
        assert measured(result, c, 100) == result


def test_data_method_tls_effect_and_independent_readback_are_separate(
    native_tls: tuple[NativeReads, dict[str, Any]], binding: NativeBinding, tmp_path: Path
) -> None:
    reads, peer = native_tls
    p = method_plan("APPLICATION_REBUILD_RESTORE", "import_target", "openstack", "ahv")
    b = replace(binding, operation_plan_sha256=digest(p))
    c = p["method_contract"]
    receipt = {
        "binding_sha256": b.fingerprint,
        "intent_sha256": digest(p),
        "receipt_sha256": digest("receipt"),
        "submitted": True,
        "retry_authorized": False,
        "method_contract_sha256": digest(c),
        "task_id": "restore-1",
    }
    peer["body"] = json.dumps(receipt).encode()
    journal = Journal()
    journal.claim(b)
    writer = OwnerProtocolClient(reads.endpoints["identity"])
    adapter = OwnerProtocolEffect(p, writer, journal)
    adapter.execute(b, lambda: None)
    assert peer["requests"][-1]["path"].endswith("/v2/migration/method-effects")
    assert journal.events[-1][0] == "poll_observed"
    observer_id = str(uuid4())
    token = tmp_path / "independent.token"
    token.write_text("independent-method-reader-token-value")
    reader = OwnerProtocolClient(
        replace(reads.endpoints["identity"], token_file=token), read_only=True
    )
    observer = OwnerProtocolObserver(reader, observer_id, str(uuid4()), lambda: 100, method_plan=p)
    result: dict[str, Any] = {
        "binding_sha256": b.fingerprint,
        "intent_sha256": digest(p),
        "observer_id": observer_id,
        "independent": True,
        "outcome": "observed_present",
        "observed_at": 100,
        "evidence_sha256": digest("observed"),
        "measurement": measurement(c),
    }
    peer["body"] = json.dumps(result).encode()
    assert observer.observe(b, {})["outcome"] == "observed_present"
    assert peer["requests"][-1]["path"].endswith("/v2/migration/method-observations")
    assert peer["requests"][-1]["authorization"] != peer["requests"][0]["authorization"]
    with pytest.raises(NativeHeld, match="observer_effect_denied"):
        reader.call("/v2/migration/method-effects", {}, lambda: None)
    stale = copy.deepcopy(result)
    next(iter(stale["measurement"]["datasets"].values()))["observed_at"] = 1
    peer["body"] = json.dumps(stale).encode()
    with pytest.raises(NativeHeld, match="dataset_not_verified"):
        observer.observe(b, {})
    peer["status"] = 503
    count = len(peer["requests"])
    with pytest.raises(NativeHeld, match="unconfirmed"):
        adapter.execute(b, lambda: None)
    assert len(peer["requests"]) == count + 1  # No automatic replay of uncertain data operations.


def test_data_loss_budget_applies_to_all_datasets_together() -> None:
    c = method_plan("APPLICATION_REBUILD_RESTORE", "final_sync")["method_contract"]
    c["limits"]["max_data_loss_bytes"] = 10
    result = measurement(c)
    for row in result["datasets"].values():
        row["data_loss_bytes"] = 6
    with pytest.raises(NativeHeld, match="total_data_loss_exceeded"):
        measured(result, c, 100)
