"""Typed commissioned application/file/block data operations and independent readback.

These protocols invoke an enrolled data-system owner, never a VM-disk adapter.
Installed backup/replication products and dataset mappings remain explicit; an API
submission does not establish synchronization or authorize destination writes.
"""

from typing import Any

from lifecycle_worker.application.api_plan import shape
from lifecycle_worker.application.native import NativeHeld, digest, identity, sha256

OPERATIONS = {
    "APPLICATION_REBUILD_RESTORE": {
        "export_copy": "application_backup",
        "import_target": "application_restore",
        "final_sync": "application_final_restore",
        "reverse_sync": "application_reverse_restore",
    },
    "VM_SNAPSHOT_BASELINE_APP_DELTA": {
        "restart_baseline_source": "application_tracking_start",
        "final_sync": "application_final_sync",
        "reverse_sync": "application_reverse_sync",
    },
    "VM_SNAPSHOT_BASELINE_FILE_DELTA": {
        "restart_baseline_source": "file_tracking_start",
        "final_sync": "file_metadata_final_sync",
        "reverse_sync": "file_metadata_reverse_sync",
    },
    "EXTERNAL_BLOCK_REPLICATION": {
        "capture": "block_replication_baseline",
        "import_target": "block_replica_attach",
        "final_sync": "block_replication_final_sync",
        "reverse_sync": "block_replication_reverse_sync",
    },
}
MECHANISMS = {
    "APPLICATION_REBUILD_RESTORE": "application_backup_restore",
    "VM_SNAPSHOT_BASELINE_APP_DELTA": "application_native_delta",
    "VM_SNAPSHOT_BASELINE_FILE_DELTA": "file_metadata_delta",
    "EXTERNAL_BLOCK_REPLICATION": "storage_block_replication",
}


def contract(value: Any, stage: str) -> dict[str, Any]:
    shape(
        value,
        {
            "method",
            "operation",
            "source",
            "target",
            "datasets",
            "mechanism",
            "consistency_boundary_sha256",
            "writer_fence_sha256",
            "recovery_sha256",
            "predecessor_receipt_sha256",
            "reverse_qualification_sha256",
            "limits",
        },
    )
    c: dict[str, Any] = value
    if (
        not isinstance(c["method"], str)
        or OPERATIONS.get(c["method"], {}).get(stage) != c["operation"]
    ):
        raise NativeHeld("migration_method_operation_mismatch")
    for side in ("source", "target"):
        row = c[side]
        shape(row, {"platform", "installation_id", "native_identity_sha256"})
        if row["platform"] not in {"vmware", "openstack", "ahv"}:
            raise NativeHeld("migration_method_platform_unsupported")
        identity(row["installation_id"])
        if not sha256(row["native_identity_sha256"]):
            raise NativeHeld("migration_method_identity_required")
    if c["source"]["installation_id"] == c["target"]["installation_id"] or (
        c["source"]["native_identity_sha256"] == c["target"]["native_identity_sha256"]
    ):
        raise NativeHeld("migration_method_distinct_environments_required")
    mechanism = c["mechanism"]
    shape(mechanism, {"kind", "version", "artifact_sha256", "qualification_sha256"})
    if (
        mechanism["kind"] != MECHANISMS[c["method"]]
        or not isinstance(mechanism["version"], str)
        or not 1 <= len(mechanism["version"]) <= 160
        or any(ord(char) < 32 for char in mechanism["version"])
        or not all(sha256(mechanism[k]) for k in ("artifact_sha256", "qualification_sha256"))
    ):
        raise NativeHeld("migration_method_mechanism_unqualified")
    rows = c["datasets"]
    if not isinstance(rows, dict) or not 1 <= len(rows) <= 256:
        raise NativeHeld("migration_method_datasets_required")
    for key, row in rows.items():
        identity(key)
        shape(row, {"source_sha256", "target_sha256", "consistency_sha256"})
        if not all(sha256(v) for v in row.values()):
            raise NativeHeld("migration_method_dataset_unbound")
    for key in ("consistency_boundary_sha256", "writer_fence_sha256", "recovery_sha256"):
        if not sha256(c[key]):
            raise NativeHeld("migration_method_safety_boundary_required")
    if c["predecessor_receipt_sha256"] is not None and not sha256(c["predecessor_receipt_sha256"]):
        raise NativeHeld("migration_method_predecessor_invalid")
    if stage not in {"capture", "export_copy"} and c["predecessor_receipt_sha256"] is None:
        raise NativeHeld("migration_method_predecessor_required")
    if c["reverse_qualification_sha256"] is not None and not sha256(
        c["reverse_qualification_sha256"]
    ):
        raise NativeHeld("migration_method_reverse_qualification_invalid")
    if stage == "reverse_sync" and c["reverse_qualification_sha256"] is None:
        raise NativeHeld("migration_method_reverse_unqualified")
    limits = c["limits"]
    shape(limits, {"max_seconds", "max_lag_seconds", "max_data_loss_bytes"})
    if (
        any(type(v) is not int or not 0 <= v < 2**63 for v in limits.values())
        or not limits["max_seconds"]
    ):
        raise NativeHeld("migration_method_limits_invalid")
    digest(c)
    return c


def measured(value: Any, c: dict[str, Any], now: int) -> dict[str, Any]:
    """An independent peer must read every selected dataset and the writer boundary."""
    shape(
        value,
        {
            "method_contract_sha256",
            "datasets",
            "source_writer_fenced",
            "target_writer_fenced",
            "elapsed_seconds",
            "consistency_boundary_sha256",
            "recovery_sha256",
        },
    )
    result: dict[str, Any] = value
    if (
        result["method_contract_sha256"] != digest(c)
        or result["consistency_boundary_sha256"] != c["consistency_boundary_sha256"]
        or result["recovery_sha256"] != c["recovery_sha256"]
        or result["target_writer_fenced"] is not True
        or type(result["source_writer_fenced"]) is not bool
        or type(result["elapsed_seconds"]) is not int
        or not 0 <= result["elapsed_seconds"] <= c["limits"]["max_seconds"]
    ):
        raise NativeHeld("migration_method_boundary_not_observed")
    tracking = c["operation"] in {"application_tracking_start", "file_tracking_start"}
    if not tracking and result["source_writer_fenced"] is not True:
        raise NativeHeld("migration_method_source_writer_not_fenced")
    datasets = result["datasets"]
    if not isinstance(datasets, dict) or set(datasets) != set(c["datasets"]):
        raise NativeHeld("migration_method_dataset_observations_incomplete")
    for key, row in datasets.items():
        shape(
            row,
            {
                "dataset_sha256",
                "observed_at",
                "source_boundary_sha256",
                "target_boundary_sha256",
                "lag_seconds",
                "data_loss_bytes",
                "integrity_verified",
                "metadata_verified",
                "evidence_sha256",
            },
        )
        if (
            row["dataset_sha256"] != digest(c["datasets"][key])
            or type(row["observed_at"]) is not int
            or not 0 <= now - row["observed_at"] <= 5
            or not all(
                sha256(row[k])
                for k in ("source_boundary_sha256", "target_boundary_sha256", "evidence_sha256")
            )
            or row["integrity_verified"] is not True
            or row["metadata_verified"] is not True
            or type(row["lag_seconds"]) is not int
            or not 0 <= row["lag_seconds"] <= c["limits"]["max_lag_seconds"]
            or type(row["data_loss_bytes"]) is not int
            or not 0 <= row["data_loss_bytes"] <= c["limits"]["max_data_loss_bytes"]
        ):
            raise NativeHeld("migration_method_dataset_not_verified")
    if (
        sum(row["data_loss_bytes"] for row in datasets.values())
        > c["limits"]["max_data_loss_bytes"]
    ):
        raise NativeHeld("migration_method_total_data_loss_exceeded")
    return result
