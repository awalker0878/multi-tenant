"""Destination review binds all observed resource and source-device identities."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from inventory.domain.discovery import Rejected
from inventory.domain.migration import destination_input
from inventory.domain.workload import profile_payload, review_input


def values() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    source = {"firmware": "efi", "disks": [{"key": 1}, {"key": 2}], "nics": [{"key": 3}]}
    target: dict[str, Any] = {
        "platform": "vmware",
        "project_id": "datacenter-1",
        "vcenter_uuid": "vc-1",
    }
    for plural, key in [
        ("folders", "folder"),
        ("resource_pools", "resource_pool"),
        ("hosts", "host"),
        ("datastores", "datastore"),
        ("networks", "network"),
    ]:
        target[plural] = [{key: key + "-1"}, {key: key + "-2"}]
    for row in target["folders"]:
        row["type"] = "VIRTUAL_MACHINE"
    selection = {
        "platform": "vmware",
        "project_id": "datacenter-1",
        "vcenter_uuid": "vc-1",
        "folder_id": "folder-1",
        "resource_pool_id": "resource_pool-1",
        "host_id": "host-1",
        "datastore_id": "datastore-1",
        "guest_id": "windows2022srv_64Guest",
        "hardware_version": "vmx-21",
        "firmware": "efi",
        "disks": [{"source_key": 1, "index": 0}, {"source_key": 2, "index": 1}],
        "nics": [
            {
                "source_key": 3,
                "quarantine_network_id": "network-1",
                "production_network_id": "network-2",
            }
        ],
    }
    return {"destination": selection, "method": "VM_COLD_EXPORT"}, source, target


def test_review_preserves_efi_and_all_disks() -> None:
    body, source, target = values()
    before = deepcopy((body, source, target))
    destination_input(body, source, target)
    assert (body, source, target) == before


@pytest.mark.parametrize(
    "fault",
    [
        "firmware",
        "foreign",
        "missing_disk",
        "duplicate_slot",
        "network",
        "host",
        "guest",
        "folder_type",
    ],
)
def test_rejects_incomplete_or_unobserved_vmware_mapping(fault: str) -> None:
    body, source, target = values()
    d = body["destination"]
    if fault == "firmware":
        d["firmware"] = "bios"
    if fault == "foreign":
        d["vcenter_uuid"] = "vc-2"
    if fault == "missing_disk":
        d["disks"].pop()
    if fault == "duplicate_slot":
        d["disks"][1]["index"] = 0
    if fault == "network":
        d["nics"][0]["production_network_id"] = "network-1"
    if fault == "host":
        d["host_id"] = "host-foreign"
    if fault == "guest":
        d["guest_id"] = "unknown"
    if fault == "folder_type":
        target["folders"][0]["type"] = "HOST"
    with pytest.raises(Rejected):
        destination_input(body, source, target)


def test_vmware_contract_fixture_is_valid_for_profile_intake_and_review() -> None:
    fixture = json.loads(
        (Path(__file__).with_name("fixtures") / "vmware-destination-v1.json").read_text()
    )
    source, target, review = (fixture[key] for key in ("source", "target", "review"))
    for p, stream in (
        (source, {"kind": "source_profile", "vm_ids": [source["vm_id"]]}),
        (target, {"kind": "target_profile"}),
    ):
        profile_payload(
            p, stream | {"api_version": p["api_version"]}, target["project_id"], "vmware"
        )
    review_input(review, source)
    destination_input(review, source, target)
