"""P08 exact migration selection and ordered effect prerequisites.

Profiles are read from Inventory custody, not accepted as assertions of native
qualification. These contracts select effects; commissioned owners still authorize
and independently observe every effect through NativeWorkflow.
"""

from typing import Any

from lifecycle.domain.admission import digest
from lifecycle.domain.execution import Rejected, identity
from lifecycle.domain.native_workflow import checksum, exact, integer

METHODS = {
    "APPLICATION_REBUILD_RESTORE",
    "VM_SNAPSHOT_BASELINE_APP_DELTA",
    "VM_SNAPSHOT_BASELINE_FILE_DELTA",
    "VM_COLD_EXPORT",
    "EXTERNAL_BLOCK_REPLICATION",
}
DELTA = {"VM_SNAPSHOT_BASELINE_APP_DELTA", "VM_SNAPSHOT_BASELINE_FILE_DELTA"}
MODES = {"rehearsal", "cutover", "rollback", "forward_recovery", "reverse_recovery", "cleanup"}
CAPTURE = (
    "source_prepare",
    "capture",
    "export_copy",
    "convert_copy",
    "import_target",
    "transform_copy",
)
RECOVERY = {
    "rollback": ("fence_target", "verify_no_divergence", "restore_source", "verify_source"),
    "forward_recovery": ("fence_target", "preserve_target", "recover_target", "verify_recovery"),
    "reverse_recovery": (
        "fence_target",
        "preserve_target",
        "reverse_sync",
        "verify_source_data",
        "restore_source",
        "verify_source",
    ),
    "cleanup": (
        "remove_copy",
        "remove_snapshot",
        "verify_consolidation",
        "revoke_migration_access",
    ),
}
TERMINALS = {
    "rehearsal": "rehearsed",
    "cutover": "migrated",
    "rollback": "recovered",
    "forward_recovery": "recovered",
    "reverse_recovery": "recovered",
    "cleanup": "cleaned",
}
BEFORE = {
    "source_prepare": (
        "source_profile_current",
        "target_profile_current",
        "datasets_complete",
        "application_capture_authorized",
        "capacity_reserved",
        "recoverability",
    ),
    "capture": ("application_stopped", "source_powered_off", "all_source_writers_fenced"),
    "restart_baseline_source": ("snapshot_bound", "delta_qualified", "source_restart_authorized"),
    "export_copy": ("copy_isolated", "copy_powered_off", "snapshot_bound"),
    "convert_copy": ("export_integrity", "copy_custody", "conversion_artifact_current"),
    "import_target": ("converted_integrity", "target_quarantine", "capacity_reserved"),
    "transform_copy": ("target_quarantine", "copy_custody", "guest_profile_qualified"),
    "rehearsal_validate": ("target_quarantine", "business_effects_suppressed", "guest_ready"),
    "retain_rehearsal": ("rehearsal_integrity", "business_effects_suppressed"),
    "fence_source": ("rehearsal_accepted", "change_window_current", "source_profile_current"),
    "final_sync": ("all_source_writers_fenced", "application_stopped", "delta_access_ready"),
    "shutdown_source": ("final_integrity", "all_source_writers_fenced"),
    "validate_target": ("source_powered_off", "all_source_writers_fenced", "target_quarantine"),
    "admit_writes": (
        "source_powered_off",
        "all_source_writers_fenced",
        "final_integrity",
        "guest_ready",
        "application_health",
        "policy_paths",
        "required_services",
        "backup_restore",
        "change_window_current",
    ),
    "verify_activation": (
        "source_powered_off",
        "all_source_writers_fenced",
        "target_writer_admitted",
    ),
    "fence_target": ("recovery_decision_current", "source_writer_fenced"),
    "verify_no_divergence": ("target_writer_fenced", "target_requests_quiescent"),
    "preserve_target": (
        "target_writer_fenced",
        "target_requests_quiescent",
        "target_keys_readable",
    ),
    "recover_target": ("accepted_target_changes_retained", "source_writer_fenced"),
    "reverse_sync": (
        "accepted_target_changes_retained",
        "source_writer_fenced",
        "reverse_adapter_qualified",
    ),
    "verify_source_data": (
        "reverse_sync_integrity",
        "source_writer_fenced",
        "target_writer_fenced",
    ),
    "restore_source": (
        "source_return_integrity",
        "target_writer_fenced",
        "target_requests_quiescent",
    ),
    "verify_source": ("source_writer_admitted", "target_writer_fenced"),
    "verify_recovery": (
        "recovered_integrity",
        "accepted_target_changes_retained",
        "source_writer_fenced",
    ),
    "remove_copy": (
        "separate_cleanup_authority",
        "copy_owned",
        "copy_powered_off",
        "retained_evidence",
    ),
    "remove_snapshot": (
        "separate_cleanup_authority",
        "copy_absent",
        "snapshot_owned",
        "retained_evidence",
    ),
    "verify_consolidation": ("snapshot_absent", "source_retained"),
    "revoke_migration_access": ("snapshot_consolidated", "retained_evidence", "source_retained"),
}
AFTER = {
    "source_prepare": ("application_stopped", "source_powered_off", "all_source_writers_fenced"),
    "capture": ("snapshot_bound", "copy_isolated", "copy_powered_off"),
    "restart_baseline_source": ("source_application_healthy", "delta_tracking_active"),
    "export_copy": ("export_integrity", "copy_custody", "ovf_bound"),
    "convert_copy": ("converted_integrity", "copy_custody"),
    "import_target": ("target_quarantine", "target_disk_mapping", "import_integrity"),
    "transform_copy": ("guest_ready", "target_quarantine", "business_effects_suppressed"),
    "rehearsal_validate": (
        "rehearsal_integrity",
        "application_health",
        "policy_paths",
        "required_services",
    ),
    "retain_rehearsal": ("rehearsal_dossier", "target_writer_fenced", "retained_evidence"),
    "fence_source": ("all_source_writers_fenced", "application_stopped"),
    "final_sync": ("final_integrity", "last_source_write_bound", "all_source_writers_fenced"),
    "shutdown_source": ("source_powered_off", "all_source_writers_fenced"),
    "validate_target": (
        "final_integrity",
        "guest_ready",
        "application_health",
        "policy_paths",
        "required_services",
        "backup_restore",
        "target_quarantine",
    ),
    "admit_writes": ("target_writer_admitted", "source_writer_fenced", "traffic_active"),
    "verify_activation": (
        "application_health",
        "policy_paths",
        "required_services",
        "outage_objective_met",
        "data_objective_met",
        "one_writer",
        "source_retained",
    ),
    "fence_target": ("target_writer_fenced", "target_requests_quiescent"),
    "verify_no_divergence": ("source_return_integrity", "no_target_divergence"),
    "preserve_target": ("accepted_target_changes_retained", "target_keys_readable"),
    "recover_target": ("recovered_integrity", "accepted_target_changes_retained"),
    "reverse_sync": ("reverse_sync_integrity", "accepted_target_changes_retained"),
    "verify_source_data": ("source_return_integrity", "accepted_target_changes_retained"),
    "restore_source": ("source_writer_admitted", "target_writer_fenced"),
    "verify_source": (
        "application_health",
        "one_writer",
        "data_objective_met",
        "outage_objective_met",
    ),
    "verify_recovery": (
        "application_health",
        "one_writer",
        "data_objective_met",
        "outage_objective_met",
    ),
    "remove_copy": ("copy_absent", "source_retained"),
    "remove_snapshot": ("snapshot_absent", "source_retained"),
    "verify_consolidation": ("snapshot_consolidated", "source_retained"),
    "revoke_migration_access": (
        "migration_access_revoked",
        "buffers_removed",
        "retained_evidence",
        "source_retained",
    ),
}


def stages(migration: dict[str, Any]) -> tuple[str, ...]:
    mode, method = migration["mode"], migration["method"]
    if mode in RECOVERY:
        return RECOVERY[mode]
    capture: tuple[str, ...] = CAPTURE
    if method in DELTA:
        capture = CAPTURE[:2] + ("restart_baseline_source",) + CAPTURE[2:]
    elif method == "APPLICATION_REBUILD_RESTORE":
        capture = ("source_prepare", "export_copy", "import_target", "transform_copy")
    elif method == "EXTERNAL_BLOCK_REPLICATION":
        capture = ("source_prepare", "capture", "import_target", "transform_copy")
    if mode == "rehearsal":
        return capture + ("rehearsal_validate", "retain_rehearsal")
    return capture + (
        "fence_source",
        "final_sync",
        "shutdown_source",
        "validate_target",
        "admit_writes",
        "verify_activation",
    )


def cases(plan: dict[str, Any], stage: str, phase: str) -> tuple[str, ...]:
    required = BEFORE[stage] if phase == "before" else AFTER[stage]
    if (
        stage == "final_sync"
        and phase == "before"
        and plan["migration"]["method"] == "VM_COLD_EXPORT"
    ):
        required = ("all_source_writers_fenced", "source_powered_off", "export_integrity")
    if stage == "fence_target" and phase == "before":
        required += ("prior_provider_requests_excluded",)
    if phase == "after":
        required += ("provider_requests_quiescent",)
    if plan["migration"]["method"] == "VM_COLD_EXPORT" and stage in {
        "export_copy",
        "convert_copy",
        "import_target",
        "transform_copy",
        "final_sync",
    }:
        required += ("source_powered_off", "all_source_writers_fenced")
    if plan["migration"]["mode"] == "rollback" and stage == "restore_source":
        required += ("no_target_divergence",)
    if plan["migration"]["mode"] == "reverse_recovery" and stage == "restore_source":
        required += ("accepted_target_changes_retained",)
    return tuple(dict.fromkeys(required))


def validate(m: dict[str, Any], now: int) -> None:
    exact(
        m,
        {
            "schema_version",
            "mode",
            "method",
            "source",
            "target",
            "datasets",
            "disks",
            "delta",
            "artifacts",
            "objectives",
            "rehearsal_sha256",
            "recovery_of_sha256",
        },
    )
    if type(m["schema_version"]) is not int or m["schema_version"] != 1:
        raise Rejected("invalid_migration_version", 422)
    if m["method"] not in METHODS or m["mode"] not in MODES:
        raise Rejected("migration_method_or_mode_not_selected", 422)
    for side in ("source", "target"):
        p = exact(
            m[side],
            {
                "profile_sha256",
                "native_identity_sha256",
                "tuple_sha256",
                "observed_at",
                "expires_at",
            },
        )
        for key in ("profile_sha256", "native_identity_sha256", "tuple_sha256"):
            checksum(p[key])
        if not 0 <= now - integer(p["observed_at"]) <= 3600 or integer(p["expires_at"]) <= now:
            raise Rejected("migration_profile_stale", 423)
    if m["source"]["native_identity_sha256"] == m["target"]["native_identity_sha256"]:
        raise Rejected("migration_copy_required", 422)
    datasets = m["datasets"]
    if (
        not isinstance(datasets, list)
        or not 1 <= len(datasets) <= 256
        or len({identity(d) for d in datasets}) != len(datasets)
    ):
        raise Rejected("migration_datasets_incomplete", 422)
    disks = m["disks"]
    if not isinstance(disks, list) or not 1 <= len(disks) <= 32:
        raise Rejected("migration_disk_inventory_required", 422)
    seen: set[str] = set()
    targets: set[str] = set()
    covered: set[str] = set()
    for d in disks:
        exact(d, {"source_disk_sha256", "target_key", "capacity_bytes", "format", "datasets"})
        checksum(d["source_disk_sha256"])
        identity(d["target_key"])
        integer(d["capacity_bytes"], 1)
        if (
            d["source_disk_sha256"] in seen
            or d["target_key"] in targets
            or d["format"] not in {"vmdk", "raw", "qcow2"}
        ):
            raise Rejected("migration_disk_mapping_ambiguous", 422)
        seen.add(d["source_disk_sha256"])
        targets.add(d["target_key"])
        if not isinstance(d["datasets"], list) or len(set(d["datasets"])) != len(d["datasets"]):
            raise Rejected("migration_dataset_mapping_invalid", 422)
        covered.update(identity(i) for i in d["datasets"])
    if covered != set(datasets):
        raise Rejected("migration_datasets_incomplete", 422)
    artifacts = exact(
        m["artifacts"], {"capture", "transfer", "conversion", "guest", "delta", "recovery"}
    )
    for value in artifacts.values():
        checksum(value)
    delta = exact(m["delta"], {"kind", "requires_running_guest", "qualification_sha256"})
    expected = {
        "VM_SNAPSHOT_BASELINE_APP_DELTA": "application",
        "VM_SNAPSHOT_BASELINE_FILE_DELTA": "file",
        "APPLICATION_REBUILD_RESTORE": "restore",
        "VM_COLD_EXPORT": "none",
        "EXTERNAL_BLOCK_REPLICATION": "block",
    }[m["method"]]
    if delta["kind"] != expected or type(delta["requires_running_guest"]) is not bool:
        raise Rejected("migration_delta_method_mismatch", 422)
    checksum(delta["qualification_sha256"])
    if expected == "none" and delta["requires_running_guest"]:
        raise Rejected("cold_source_cannot_supply_guest_delta", 422)
    objectives = exact(
        m["objectives"],
        {"owner_id", "acceptance_sha256", "max_outage_seconds", "max_data_loss_bytes"},
    )
    identity(objectives["owner_id"])
    checksum(objectives["acceptance_sha256"])
    integer(objectives["max_outage_seconds"], 1)
    integer(objectives["max_data_loss_bytes"])
    if m["mode"] == "cutover":
        checksum(m["rehearsal_sha256"])
    elif m["rehearsal_sha256"] is not None:
        raise Rejected("unexpected_migration_rehearsal", 422)
    if m["mode"] in RECOVERY:
        checksum(m["recovery_of_sha256"])
    elif m["recovery_of_sha256"] is not None:
        raise Rejected("unexpected_migration_recovery", 422)


def recovery_matches(original: dict[str, Any], replacement: dict[str, Any]) -> bool:
    """Recovery can change authority/artifacts, but cannot switch datasets or migration method."""
    keys = ("method", "datasets", "disks")
    return all(digest(original[k]) == digest(replacement[k]) for k in keys) and all(
        original[side][key] == replacement[side][key]
        for side in ("source", "target")
        for key in ("native_identity_sha256", "tuple_sha256")
    )
