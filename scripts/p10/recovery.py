"""Offline coordinated-restore checklist; this never re-enables a writer."""

from evidence import reference, require

DEPENDENCIES = {
    "databases",
    "workflows",
    "broker_outbox_inbox",
    "evidence",
    "automation_state",
    "identities",
    "keys",
    "configuration",
}


def assess_restore(root, packet):
    require(
        set(packet)
        == {
            "candidate_sha256",
            "recovery_point",
            "dependencies",
            "isolation",
            "old_epoch",
            "new_epoch",
            "native_effects",
            "native_inventory",
            "upgrade",
        },
        "invalid_restore_packet",
    )
    dependencies = packet["dependencies"]
    require(
        isinstance(dependencies, dict) and set(dependencies) == DEPENDENCIES,
        "incomplete_restore_dependencies",
    )
    for name, ref in dependencies.items():
        observed = reference(root, ref)
        require(
            observed["component"] == name
            and observed["candidate_sha256"] == packet["candidate_sha256"]
            and observed["recovery_point"] == packet["recovery_point"]
            and observed["integrity"] == "VERIFIED"
            and observed["mode"] == "read_only",
            "restore_identity_or_integrity_changed:" + name,
        )
    isolation = reference(root, packet["isolation"])
    require(
        isolation["old_writers_fenced"] is True
        and isolation["restore_network_isolated"] is True
        and isolation["candidate_sha256"] == packet["candidate_sha256"]
        and isolation["old_epoch"] == packet["old_epoch"]
        and isolation["new_epoch"] == packet["new_epoch"]
        and packet["old_epoch"] != packet["new_epoch"],
        "restore_fence_or_epoch_unreconciled",
    )
    require(
        isinstance(packet["native_effects"], list), "native_effect_inventory_missing"
    )
    seen = set()
    for ref in packet["native_effects"]:
        effect = reference(root, ref)
        require(effect["operation_id"] not in seen, "duplicate_native_effect")
        seen.add(effect["operation_id"])
        require(
            effect["candidate_sha256"] == packet["candidate_sha256"]
            and effect["provider_requests_quiescent"] is True
            and effect["outcome"] in {"succeeded", "failed", "not_accepted"}
            and effect["observer_id"] != effect["executor_id"]
            and effect["reconciled_epoch"] == packet["new_epoch"],
            "native_outcome_unreconciled",
        )
    inventory = reference(root, packet["native_inventory"])
    require(
        inventory["candidate_sha256"] == packet["candidate_sha256"]
        and inventory["reconciled_epoch"] == packet["new_epoch"]
        and inventory["inventory_complete"] is True
        and isinstance(inventory["operation_ids"], list)
        and len(inventory["operation_ids"]) == len(set(inventory["operation_ids"]))
        and set(inventory["operation_ids"]) == seen,
        "native_effect_inventory_incomplete",
    )
    upgrade = reference(root, packet["upgrade"])
    require(
        upgrade["candidate_sha256"] == packet["candidate_sha256"]
        and upgrade["migration_state_verified"] is True
        and upgrade["old_workers_drained"] is True
        and upgrade["mixed_contracts"] == "PASSED"
        and upgrade["workflow_replay"] == "PASSED"
        and upgrade["backfill_restart"] == "PASSED"
        and upgrade["retained_key_decryption"] == "PASSED"
        and upgrade["recovery_path"]
        in {"compatible_rollback", "reviewed_forward_recovery"},
        "upgrade_recovery_unproven",
    )
    return {
        "status": "PACKET_COMPLETE_REQUIRES_INDEPENDENT_REVIEW",
        "native_effects": len(seen),
        "write_reenable_authorized": False,
        "evidence_authenticity_established": False,
    }
