"""Planning must reconcile every workload from current independent owners."""

from copy import deepcopy

import pytest

from planning.domain.model import Rejected, digest
from planning.domain.workload_reconciliation import evaluate


def specimen() -> tuple[dict, dict, dict, dict, dict, dict]:
    scope = {"tenant_id": "tenant", "application_id": "app",
             "environment_id": "environment", "site_id": "site"}
    disk, nic, workload, dataset = "disk-id", "nic-id", "workload-id", "dataset-id"
    intent = {
        "environment": {"id": "environment"},
        "workloads": [{
            "id": workload, "compute": {"vcpus": 2, "memory_mib": 4096},
            "guest": {"firmware": "uefi", "secure_boot": True},
            "disks": [{"id": disk, "order": 0, "size_gib": 10, "dataset_id": dataset}],
            "nics": [{"id": nic, "order": 0}],
        }],
        "datasets": [{"id": dataset, "owner_id": workload}],
        "dependencies": [],
    }
    source = digest("source")
    dest = digest("target")
    review = digest("review")
    catalogue = {
        "revision_id": "revision", "intent_sha256": digest(intent), "intent": intent,
    }
    link = {
        "application_id": "app", "environment_id": "environment",
        "revision_id": "revision", "intent_sha256": digest(intent),
        "workload_id": workload,
        "disk_mappings": [{"logical_device_id": disk, "native_key": 2000}],
        "nic_mappings": [{"logical_device_id": nic, "native_key": 4000}],
    }
    native = {
        "source_identity_sha256": digest("native"), "generation_id": "generation",
        "profile_sha256": source, "installed_tuple_sha256": digest("installed"),
        "installation_id": "installation", "native_scope": "project",
        "current": True, "expires_at": 200, "holds": [],
        "facts": {
            "cpu": 2, "memory_mb": 4096, "firmware": "efi",
            "secure_boot": True,
            "disks": [{"key": 2000, "capacity_bytes": 10 * 1024**3}],
            "nics": [{"key": 4000}],
            "native": {"identity": {"vm_id": "vm", "generation_uuid": "gen"}},
        },
        "owner_dataset_coverage_current": False,
        "network_semantics_independently_verified": False,
        "native_write_authorized": False,
    }
    native["observation_sha256"] = digest(native)
    association = {
        "catalogue_binding": link, "source_observation": native,
        "source_binding": {
            "native_identity_sha256": native["source_identity_sha256"],
            "profile_sha256": source, "tuple_sha256": native["installed_tuple_sha256"],
        },
        "datasets": [{"id": dataset, "disk_keys": [2000]}],
        "revision": 1, "digest": review, "confirmed_by": "owner", "current": True,
    }
    inventory = {
        "tenant_id": "tenant", "site_id": "site", "revision": 1, "digest": review,
        "current": True, "confirmed_by": "owner", "catalogue_binding": link,
        "source": {**association["source_binding"]},
        "target": {"profile_sha256": dest},
        "source_observation": native, "source_associations": [association],
    }
    selected = {"review": {"revision": 1, "digest": review},
                "source": {"profile_sha256": source},
                "target": {"profile_sha256": dest}}
    flow = {
        "level": "E4", "decision": "accepted", "revoked": False,
        "intent_sha256": digest(intent), "source_profile_sha256": source,
        "target_profile_sha256": dest, "expires_at": 160,
        "evidence_sha256": digest("E4"),
        "workload_interface_cases": [{
            "workload_id": workload, "source_profile_sha256": source,
            "target_profile_sha256": dest, "logical_nics_sha256": digest(intent["workloads"][0]["nics"]),
            "native_path_set_sha256": digest("paths"),
            "allowed_probe_sha256": digest("allowed"), "denied_probe_sha256": digest("denied"),
            "return_probe_sha256": digest("return"), "isolation_probe_sha256": digest("isolation"),
            "evidence_sha256": digest("nic-e4"), "observed_at": 99, "expires_at": 150,
            "level": "E4", "decision": "accepted", "revoked": False,
        }],
    }
    return scope, catalogue, inventory, selected, flow, native


def test_qualified_single_vm_reconciles_all_owned_devices_and_datasets() -> None:
    scope, catalogue, inventory, selected, flow, _ = specimen()
    result = evaluate(scope, catalogue, inventory, selected, flow, 100)
    assert result["status"] == "matched"
    assert result["holds"] == []
    assert result["workloads"][0]["status"] == "matched"
    assert result["native_write_authorized"] is False
    assert result["reconciliation_sha256"] == digest({
        k: v for k, v in result.items() if k != "reconciliation_sha256"
    })


def test_unmapped_second_vm_never_inherits_first_vms_assurance() -> None:
    scope, catalogue, inventory, selected, flow, _ = specimen()
    extra = deepcopy(catalogue["intent"]["workloads"][0])
    extra["id"] = "second-workload"
    catalogue["intent"]["workloads"].append(extra)
    catalogue["intent_sha256"] = digest(catalogue["intent"])
    inventory["catalogue_binding"]["intent_sha256"] = catalogue["intent_sha256"]
    inventory["source_associations"][0]["catalogue_binding"]["intent_sha256"] = (
        catalogue["intent_sha256"]
    )
    flow["intent_sha256"] = catalogue["intent_sha256"]
    result = evaluate(scope, catalogue, inventory, selected, flow, 100)
    assert result["status"] == "held"
    assert any("second-workload" in hold for hold in result["holds"])


def test_missing_e4_or_dataset_equivalence_remains_held() -> None:
    scope, catalogue, inventory, selected, flow, _ = specimen()
    assert evaluate(scope, catalogue, inventory, selected, None, 100)["status"] == "held"
    changed = deepcopy(inventory)
    changed["source_associations"][0]["datasets"][0]["disk_keys"] = [999]
    result = evaluate(scope, catalogue, changed, selected, flow, 100)
    assert "source_dataset_mapping_not_independently_confirmed" in str(result["holds"])


def test_changed_profile_review_and_untrusted_observation_are_rejected() -> None:
    scope, catalogue, inventory, selected, flow, _ = specimen()
    altered = deepcopy(inventory)
    altered["source_associations"][0]["source_observation"]["facts"]["cpu"] = 4
    with pytest.raises(Rejected, match="source_observation_changed"):
        evaluate(scope, catalogue, altered, selected, flow, 100)
    altered = deepcopy(inventory)
    altered["digest"] = digest("changed")
    with pytest.raises(Rejected, match="review_not_current"):
        evaluate(scope, catalogue, altered, selected, flow, 100)



def test_application_flow_receipt_without_per_vm_interface_probes_never_passes() -> None:
    scope, catalogue, inventory, selected, flow, _ = specimen()
    flow["workload_interface_cases"] = []
    result = evaluate(scope, catalogue, inventory, selected, flow, 100)
    assert result["status"] == "held"
    assert any("source_network_semantics_not_verified" in hold for hold in result["holds"])
    flow["workload_interface_cases"] = [{
        "workload_id": catalogue["intent"]["workloads"][0]["id"],
        "source_profile_sha256": digest("wrong-source"),
    }]
    assert evaluate(scope, catalogue, inventory, selected, flow, 100)["status"] == "held"
