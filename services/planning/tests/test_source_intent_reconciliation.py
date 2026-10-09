"""Desired source logical IDs cannot silently remap to other native VMs."""

from copy import deepcopy
import hashlib
import json

import pytest

from planning.domain.model import Rejected, digest
from planning.domain.source_intent_reconciliation import reconcile


def values() -> tuple[dict, list, list]:
    workload = {
        "id": "workload",
        "compute": {"vcpus": 2, "memory_mib": 4096},
        "guest": {"firmware": "uefi", "secure_boot": True},
        "disks": [{"id": "disk-0", "order": 0, "size_gib": 10}],
        "nics": [{"id": "nic-0", "order": 0}],
    }
    intent = {"workloads": [workload], "dependencies": []}
    link = {"workload_id": "workload", "catalogue_digest": digest(intent),
            "source_identity_sha256": digest("native"),
            "owner_confirmed": True, "native_generation_id": "generation",
            "native_profile_sha256": digest("profile"),
            "installation_id": "installation", "native_scope": "project",
            "evidence_sha256": digest("link"), "expires_at": 200,
            "disk_mappings": [{"logical_device_id": "disk-0", "native_key": 0}],
            "nic_mappings": [{"logical_device_id": "nic-0", "native_key": 0}]}
    profile = {"source_identity_sha256": digest("native"),
               "generation_id": "generation", "profile_sha256": digest("profile"),
               "installation_id": "installation", "native_scope": "project",
               "current": True, "expires_at": 200, "holds": [],
               "owner_dataset_coverage_sha256": digest([]),
               "owner_dataset_coverage_current": True,
               "network_semantics_sha256": digest(workload["nics"]),
               "network_semantics_independently_verified": True,
               "facts": {"cpu": 2, "memory_mb": 4096, "firmware": "efi",
                         "secure_boot": True,
                         "disks": [{"key": 0, "capacity_bytes": 10 * 1024**3}],
                         "nics": [{"key": 0}],
                         "native": {"identity": {
                             "vm_id": "vm-01", "generation_uuid": "gen-01",
                         }}}}
    return intent, [link], [profile]


def test_exact_current_catalogue_to_native_join() -> None:
    intent, links, profiles = values()
    result = reconcile(intent, digest(intent), links, profiles, 100)
    assert result["status"] == "matched"
    assert result["native_write_authorized"] is False
    assert result["reconciliation_sha256"] == digest({
        k: v for k, v in result.items() if k != "reconciliation_sha256"
    })


def test_mutation_missing_link_and_storage_or_nic_drift_are_held() -> None:
    intent, links, profiles = values()
    assert reconcile(intent, digest(intent), [], [], 100)["status"] == "held"
    for changed in ("generation", "disk", "nic", "compute", "firmware", "secure_boot",
                    "datasets", "network", "incarnation", "expired"):
        one, two = deepcopy(links), deepcopy(profiles)
        if changed == "generation": two[0]["generation_id"] = "new"
        if changed == "disk": two[0]["facts"]["disks"][0]["capacity_bytes"] -= 1024
        if changed == "nic": two[0]["facts"]["nics"] = []
        if changed == "compute": two[0]["facts"]["cpu"] = 4
        if changed == "firmware": two[0]["facts"]["firmware"] = None
        if changed == "secure_boot": two[0]["facts"]["secure_boot"] = False
        if changed == "datasets": two[0]["owner_dataset_coverage_current"] = False
        if changed == "network": two[0]["network_semantics_independently_verified"] = False
        if changed == "incarnation": two[0]["facts"]["native"]["identity"].pop(
            "generation_uuid"
        )
        if changed == "expired": one[0]["expires_at"] = 90
        assert reconcile(intent, digest(intent), one, two, 100)["status"] == "held"


def test_native_identity_or_application_flow_cannot_be_inferred() -> None:
    intent, links, profiles = values()
    links[0]["source_identity_sha256"] = digest("different")
    with pytest.raises(Rejected, match="ambiguous"):
        reconcile(intent, digest(intent), links, profiles, 100)
    intent, links, profiles = values()
    intent["dependencies"] = [{"kind": "communication"}]
    links[0]["catalogue_digest"] = digest(intent)
    assert "application_dependency_e4_validation_required" in reconcile(
        intent, digest(intent), links, profiles, 100
    )["holds"]


def test_catalogue_document_cannot_be_substituted_behind_receipt_digest() -> None:
    intent, links, profiles = values()
    intent["workloads"][0]["compute"]["vcpus"] = 8
    with pytest.raises(Rejected, match="catalogue_document_changed"):
        reconcile(intent, links[0]["catalogue_digest"], links, profiles, 100)


def test_unicode_catalogue_canonicalization_matches_published_digest() -> None:
    intent, links, profiles = values()
    intent["workloads"][0]["name"] = "Café de Montréal"
    catalogue_sha = hashlib.sha256(json.dumps(
        intent, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode()).hexdigest()
    links[0]["catalogue_digest"] = catalogue_sha
    assert reconcile(intent, catalogue_sha, links, profiles, 100)["status"] == "matched"


def test_native_keys_need_not_equal_catalogue_display_order() -> None:
    intent, links, profiles = values()
    links[0]["disk_mappings"][0]["native_key"] = 2000
    links[0]["nic_mappings"][0]["native_key"] = 4000
    profiles[0]["facts"]["disks"][0]["key"] = 2000
    profiles[0]["facts"]["nics"][0]["key"] = 4000
    assert reconcile(intent, digest(intent), links, profiles, 100)["status"] == "matched"
    links[0]["disk_mappings"][0]["native_key"] = 9999
    assert "source_disk_identity_ambiguous" in reconcile(
        intent, digest(intent), links, profiles, 100
    )["holds"][0]


def test_missing_or_reused_device_mapping_never_reconciles() -> None:
    intent, links, profiles = values()
    links[0]["disk_mappings"] = []
    assert reconcile(intent, digest(intent), links, profiles, 100)["status"] == "held"
    links[0]["disk_mappings"] = [
        {"logical_device_id": "unknown", "native_key": 0}
    ]
    assert reconcile(intent, digest(intent), links, profiles, 100)["status"] == "held"


def test_full_catalogue_requires_semantic_dispositions_beyond_vm_sizing() -> None:
    for field, path in [
        ("architecture", "compute.architecture"),
        ("os", "guest.os"),
        ("hardening_profile", "guest.hardening_profile"),
        ("boot", "disks.disk-0.boot"),
        ("encryption", "disks.disk-0.encryption"),
        ("failure_domain", "failure_domain"),
    ]:
        intent, links, profiles = values()
        workload = intent["workloads"][0]
        if field == "architecture":
            workload["compute"]["architecture"] = "x86_64"
        elif field in {"os", "hardening_profile"}:
            workload["guest"][field] = "RHEL-9"
        elif field in {"boot", "encryption"}:
            workload["disks"][0][field] = True if field == "boot" else "required"
        else:
            workload["failure_domain"] = {
                "group": "zone-a", "mode": "anti_affinity", "strength": "required",
            }
        links[0]["catalogue_digest"] = digest(intent)
        result = reconcile(intent, digest(intent), links, profiles, 100)
        assert result["status"] == "held"
        row = result["workloads"][0]
        assert any(d["field"] == path and d["disposition"] == "unobserved"
                   for d in row["field_dispositions"])
        assert any(path in hold for hold in row["holds"])


def test_optional_placement_does_not_falsely_block_required_sizing() -> None:
    intent, links, profiles = values()
    intent["workloads"][0]["failure_domain"] = {
        "group": "zone", "mode": "independent", "strength": "preferred",
    }
    links[0]["catalogue_digest"] = digest(intent)
    result = reconcile(intent, digest(intent), links, profiles, 100)
    assert result["status"] == "matched"
    assert result["workloads"][0]["field_dispositions"][0]["disposition"] == "unobserved"
