"""Desired source logical IDs cannot silently remap to other native VMs."""

from copy import deepcopy

import pytest

from planning.domain.model import Rejected, digest
from planning.domain.source_intent_reconciliation import reconcile


def values() -> tuple[dict, list, list]:
    workload = {
        "id": "workload",
        "compute": {"vcpus": 2, "memory_mib": 4096},
        "guest": {"firmware": "uefi"},
        "disks": [{"order": 0, "size_gib": 10}],
        "nics": [{"order": 0}],
    }
    intent = {"workloads": [workload], "dependencies": []}
    link = {"workload_id": "workload", "catalogue_digest": digest(intent),
            "source_identity_sha256": digest("native"),
            "owner_confirmed": True, "native_generation_id": "generation",
            "native_profile_sha256": digest("profile"),
            "installation_id": "installation", "native_scope": "project",
            "evidence_sha256": digest("link"), "expires_at": 200}
    profile = {"source_identity_sha256": digest("native"),
               "generation_id": "generation", "profile_sha256": digest("profile"),
               "installation_id": "installation", "native_scope": "project",
               "current": True, "expires_at": 200, "holds": [],
               "facts": {"cpu": 2, "memory_mb": 4096, "firmware": "efi",
                         "disks": [{"key": 0, "capacity_bytes": 10 * 1024**3}],
                         "nics": [{"key": 0}], "native": {"identity": {}}}}
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
    for changed in ("generation", "disk", "nic", "compute", "firmware", "expired"):
        one, two = deepcopy(links), deepcopy(profiles)
        if changed == "generation": two[0]["generation_id"] = "new"
        if changed == "disk": two[0]["facts"]["disks"][0]["capacity_bytes"] -= 1024
        if changed == "nic": two[0]["facts"]["nics"] = []
        if changed == "compute": two[0]["facts"]["cpu"] = 4
        if changed == "firmware": two[0]["facts"]["firmware"] = None
        if changed == "expired": one[0]["expires_at"] = 90
        assert reconcile(intent, digest(intent), one, two, 100)["status"] == "held"


def test_native_identity_or_application_flow_cannot_be_inferred() -> None:
    intent, links, profiles = values()
    links[0]["source_identity_sha256"] = digest("different")
    with pytest.raises(Rejected, match="ambiguous"):
        reconcile(intent, digest(intent), links, profiles, 100)
    intent, links, profiles = values()
    intent["dependencies"] = [{"kind": "communication"}]
    assert "application_dependency_e4_validation_required" in reconcile(
        intent, digest(intent), links, profiles, 100
    )["holds"]
