"""Reconciliation receives only factual native observations, not invented approvals."""

from copy import deepcopy

import pytest

from inventory.domain.discovery import Rejected, digest
from inventory.domain.source_profile import source_observation


def profile(platform: str) -> dict:
    native = {
        "identity": {"vm_id": "vm-1", "scope": "project", "generation_uuid": "g"},
        "metadata": {"vm": {"bootConfig": {"isSecureBootEnabled": True}}},
    }
    return {
        "generation_id": "generation", "current": True, "expires_at": 200,
        "facts": {
            "platform": platform, "profile_type": "SourceWorkloadProfile",
            "vm_id": "vm-1", "vcenter_uuid": "vcenter-1",
            "installation_id": "installation", "native_scope": "project",
            "cpu": 2, "memory_mb": 4096, "firmware": "efi",
            "disks": [{"key": 0, "capacity_bytes": 2**30}],
            "nics": [{"key": 0}], "native": native, "holds": [],
        },
    }


BINDING = {
    "native_identity_sha256": digest("identity"),
    "profile_sha256": digest("profile"),
    "tuple_sha256": digest("installed"),
}


def test_ahv_native_secure_boot_is_observed_without_inventing_qualification() -> None:
    result = source_observation(profile("ahv"), BINDING)
    assert result["facts"]["secure_boot"] is True
    assert result["native_write_authorized"] is False
    assert result["owner_dataset_coverage_current"] is False
    assert result["network_semantics_independently_verified"] is False
    assert result["observation_sha256"] == digest({
        k: v for k, v in result.items() if k != "observation_sha256"
    })


def test_vmware_and_openstack_do_not_infer_boot_settings_from_guest_metadata() -> None:
    for platform in ("vmware", "openstack"):
        value = profile(platform)
        value["facts"]["native"]["metadata"]["server"] = {"metadata": {"secure_boot": "true"}}
        result = source_observation(value, BINDING)
        assert result["facts"]["secure_boot"] is None
        assert result["native_write_authorized"] is False


def test_target_profile_cannot_masquerade_as_source() -> None:
    value = deepcopy(profile("ahv"))
    value["facts"]["profile_type"] = "TargetCapabilityProfile"
    with pytest.raises(Rejected, match="source_observation_profile_required"):
        source_observation(value, BINDING)


def test_vmware_native_boot_option_is_retained_when_observed() -> None:
    value = profile("vmware")
    value["facts"]["secure_boot"] = False
    result = source_observation(value, BINDING)
    assert result["facts"]["secure_boot"] is False
