"""Destination selections use source-defined fields and API-observed IDs only."""

import pytest

from inventory.domain.ahv import destination_input as ahv_destination
from inventory.domain.discovery import Rejected
from inventory.domain.vmware import destination_input as vmware_destination


def vmware_source():
    return {
        "platform": "vmware", "schema_version": 1, "firmware": "efi",
        "guest_id": "rhel9_64Guest",
        "disks": [{"key": 2000}], "nics": [],
    }


def vmware_target():
    return {
        "platform": "vmware", "project_id": "dc-1", "vcenter_uuid": "vcenter-1",
        "folders": [{"folder": "group-v3", "type": "VIRTUAL_MACHINE"}],
        "resource_pools": [{"resource_pool": "resgroup-1"}],
        "hosts": [{"host": "host-1"}], "datastores": [{"datastore": "ds-1"}],
        "networks": [],
        "guest_options_by_host": [
            {"host": "host-1", "guest_ids": ["rhel9_64Guest"],
             "hardware_versions": ["vmx-21"]},
        ],
    }


def vmware_review():
    return {
        "destination": {
            "platform": "vmware", "project_id": "dc-1",
            "vcenter_uuid": "vcenter-1", "folder_id": "group-v3",
            "resource_pool_id": "resgroup-1", "host_id": "host-1",
            "datastore_id": "ds-1", "guest_id": "rhel9_64Guest",
            "hardware_version": "vmx-21", "firmware": "efi",
            "disks": [{"source_key": 2000, "index": 0}], "nics": [],
        },
    }


def test_vmware_guest_options_cannot_be_typed_or_extended_by_operator():
    vmware_destination(vmware_review(), vmware_source(), vmware_target())
    for field, invented in (
        ("guest_id", "madeup64Guest"),
        ("hardware_version", "vmx-99"),
        ("host_id", "host-not-observed"),
    ):
        review = vmware_review()
        review["destination"][field] = invented
        with pytest.raises(Rejected):
            vmware_destination(review, vmware_source(), vmware_target())
    unsupported = vmware_target()
    unsupported["guest_options_by_host"] = []
    with pytest.raises(Rejected, match="vmware_guest_mapping_unobserved"):
        vmware_destination(vmware_review(), vmware_source(), unsupported)


def test_vmware_unknown_source_firmware_or_guest_cannot_default_to_bios():
    unknown = vmware_source()
    unknown["firmware"] = None
    with pytest.raises(Rejected):
        vmware_destination(vmware_review(), unknown, vmware_target())
    unknown = vmware_source()
    unknown["guest_id"] = None
    with pytest.raises(Rejected):
        vmware_destination(vmware_review(), unknown, vmware_target())


def test_ahv_destination_enforced_policy_choices_follow_observed_source_groups():
    target = {
        "platform": "ahv",
        "project_id": "00000000-0000-4000-8000-000000000001",
        "prism_central_id": "00000000-0000-4000-8000-000000000002",
        "cluster_id": "00000000-0000-4000-8000-000000000003",
        "storage_containers": [{"extId": "00000000-0000-4000-8000-000000000004"}],
        "subnets": [
            {"extId": "00000000-0000-4000-8000-000000000005",
             "vpcReference": None, "clusterReference": "00000000-0000-4000-8000-000000000003"},
            {"extId": "00000000-0000-4000-8000-000000000006",
             "vpcReference": None, "clusterReference": "00000000-0000-4000-8000-000000000003"},
        ],
        "vpcs": [], "categories": [],
        "policies": [{"extId": "00000000-0000-4000-8000-000000000007",
                      "state": "ENFORCE"}],
    }
    source = {
        "platform": "openstack", "schema_version": 3,
        "native_scope": "source-project", "firmware": "efi",
        "nics": [{"key": 0}], "disks": [{"key": 0}],
        "native": {"metadata": {"ports": [
            {"id": "port-1", "project_id": "source-project", "port_security_enabled": True,
             "security_groups": ["source-rule"]},
        ]}},
    }
    chosen_id = "00000000-0000-4000-8000-000000000007"
    review = {
        "method": "VM_COLD_EXPORT",
        "destination": {
            "platform": "ahv", "project_id": target["project_id"],
            "prism_central_id": target["prism_central_id"],
            "cluster_id": target["cluster_id"], "vpc_id": None,
            "storage_container_id": "00000000-0000-4000-8000-000000000004",
            "category_ids": [], "policy_ids": [chosen_id],
            "security_mappings": [
                {"source_id": "source-rule", "destination_id": chosen_id},
            ],
            "firmware": "efi", "disks": [{"source_key": 0, "index": 0}],
            "nics": [{"source_key": 0,
                      "quarantine_subnet_id": "00000000-0000-4000-8000-000000000005",
                      "production_subnet_id": "00000000-0000-4000-8000-000000000006"}],
        },
    }
    # ENFORCE describes policy state; it is not rule-by-rule equivalence.
    with pytest.raises(Rejected, match="destination_security_rule_qualification_required"):
        ahv_destination(review, source, target)
    review["destination"]["security_mappings"] = []
    review["destination"]["policy_ids"] = []
    ahv_destination(review, source, target)  # incomplete security remains a hold
    review["destination"]["category_ids"] = [chosen_id]
    with pytest.raises(Rejected, match="unobserved_source_or_destination_category"):
        ahv_destination(review, source, target)
