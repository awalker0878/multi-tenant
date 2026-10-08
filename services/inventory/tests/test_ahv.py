"""All-device mapping and enrolled project/cluster isolation for AHV destinations."""

from copy import deepcopy
from typing import Any
from uuid import uuid4

import pytest

from inventory.domain.discovery import Rejected
from inventory.domain.migration import destination_input


def mapping() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    project, pc, cluster, storage, quarantine, production, category, policy = [
        str(uuid4()) for _ in range(8)
    ]
    source = {
        "guest_id": "otherLinux64Guest",
        "firmware": "bios",
        "disks": [{"key": 2000}, {"key": 2001}],
        "nics": [{"key": 4000}],
    }
    target = {
        "platform": "ahv",
        "project_id": project,
        "prism_central_id": pc,
        "cluster_id": cluster,
        "storage_containers": [{"extId": storage}],
        "vpcs": [],
        "categories": [{"extId": category}],
        "policies": [{"extId": policy, "state": "ENFORCE"}],
        "subnets": [
            {"extId": key, "vpcReference": None, "clusterReference": cluster}
            for key in (quarantine, production)
        ],
    }
    body = {
        "method": "VM_COLD_EXPORT",
        "destination": {
            "platform": "ahv",
            "project_id": project,
            "prism_central_id": pc,
            "cluster_id": cluster,
            "firmware": "bios",
            "vpc_id": None,
            "storage_container_id": storage,
            "category_ids": [category],
            "policy_ids": [policy],
            "disks": [{"source_key": 2000, "index": 0}, {"source_key": 2001, "index": 1}],
            "nics": [
                {
                    "source_key": 4000,
                    "quarantine_subnet_id": quarantine,
                    "production_subnet_id": production,
                }
            ],
        },
    }
    return body, source, target


def test_ahv_selection_is_complete_and_does_not_rewrite_observations() -> None:
    body, source, target = mapping()
    original = deepcopy(target)
    destination_input(body, source, target)
    assert original == target


@pytest.mark.parametrize(
    "fault",
    [
        "project",
        "cluster",
        "pc",
        "storage",
        "nic",
        "disk",
        "order",
        "duplicate",
        "same_network",
        "category",
        "vpc",
        "warm",
        "uefi",
    ],
)
def test_ahv_mapping_rejects_gaps_or_unobserved_resources(fault: str) -> None:
    body, source, target = mapping()
    d = body["destination"]
    if fault in {"project", "cluster", "pc", "storage"}:
        d[
            {
                "project": "project_id",
                "cluster": "cluster_id",
                "pc": "prism_central_id",
                "storage": "storage_container_id",
            }[fault]
        ] = str(uuid4())
    if fault == "nic":
        d["nics"] = []
    if fault == "disk":
        d["disks"].pop()
    if fault == "order":
        d["disks"][1]["index"] = 0
    if fault == "duplicate":
        d["disks"][1]["source_key"] = 2000
    if fault == "same_network":
        d["nics"][0]["production_subnet_id"] = d["nics"][0]["quarantine_subnet_id"]
    if fault == "category":
        d["category_ids"] = [str(uuid4())]
    if fault == "vpc":
        d["vpc_id"] = str(uuid4())
    if fault == "warm":
        body["method"] = "VM_SNAPSHOT_BASELINE_APP_DELTA"
    if fault == "uefi":
        source["firmware"] = "efi"
    with pytest.raises(Rejected):
        destination_input(body, source, target)
