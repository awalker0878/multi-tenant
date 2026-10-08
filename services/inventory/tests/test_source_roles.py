"""Profile intake and source identity never borrow another platform's fields."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any
from unittest.mock import Mock
from uuid import uuid4

import pytest
from test_discovery import policy_document

from inventory.application.workload import WorkloadProfiles
from inventory.domain.discovery import Rejected, digest
from inventory.domain.workload import profile_payload
from inventory.infrastructure.policies import parse_policy


def profiles() -> list[dict[str, Any]]:
    return list(
        json.loads(
            (
                Path(__file__).resolve().parents[3]
                / "contracts/fixtures/inventory/source-roles-v3.json"
            ).read_text()
        )["profiles"]
    )


@pytest.mark.parametrize("p", profiles())
def test_role_profiles_preserve_native_identity_and_detect_changed_disk_mapping(
    p: dict[str, Any],
) -> None:
    stream = {"kind": "source_profile", "vm_ids": [p["vm_id"]], "api_version": p["api_version"]}
    assert profile_payload(p, stream, p["native_scope"], p["platform"]) == p
    profile: dict[str, Any] = {
        "facts": p,
        "digest": digest(p),
        "endpoint_id": str(uuid4()),
        "collected_at": 100,
        "expires_at": 200,
    }
    app = WorkloadProfiles(Mock())
    original = app.binding(profile)
    moved = deepcopy(profile)
    moved["facts"]["installation_id"] = str(uuid4())
    assert app.binding(moved)["native_identity_sha256"] != original["native_identity_sha256"]
    with pytest.raises(Rejected):
        profile_payload(p, stream, "foreign", p["platform"])
    with pytest.raises(Rejected):
        profile_payload(p, stream, p["native_scope"], "vmware")
    changed = deepcopy(p)
    changed["native"]["disk_records"][0]["native_id"] = str(uuid4())
    with pytest.raises(Rejected, match="mapping_changed"):
        profile_payload(changed, stream, p["native_scope"], p["platform"])
    changed = deepcopy(p)
    changed["native_qualification"] = "qualified"
    with pytest.raises(Rejected):
        profile_payload(changed, stream, p["native_scope"], p["platform"])


def test_openstack_profile_enrollment_requires_the_existing_compute_scope() -> None:
    p = policy_document()
    p["streams"].append(p["streams"][0] | {"kind": "source_profile", "vm_ids": [str(uuid4())]})
    assert parse_policy(p).platform == "openstack"
    for change in (
        {"api_version": "latest"},
        {"base_url": "https://foreign.example/v2.1"},
        {"vm_ids": ["vm-1"]},
    ):
        bad = deepcopy(p)
        bad["streams"][-1].update(change)
        with pytest.raises(Rejected):
            parse_policy(bad)


def test_ahv_source_enrollment_requires_server_inventory_before_profiles() -> None:
    p = policy_document()
    cluster, pc, project = (str(uuid4()) for _ in range(3))
    p.update(platform="ahv", native_scope=project)
    connection = p["streams"][0] | {
        "base_url": "https://native.example",
        "api_version": "v4.3",
        "cluster_id": cluster,
        "prism_central_id": pc,
        "shared_resource_ids": [],
    }
    p["streams"] = [connection, connection | {"kind": "source_profile", "vm_ids": [str(uuid4())]}]
    assert parse_policy(p).platform == "ahv"
    p["streams"].reverse()
    with pytest.raises(Rejected, match="profile_scope_not_ready"):
        parse_policy(p)


@pytest.mark.parametrize("source", [True, False])
def test_legacy_profiles_cannot_cross_the_enrolled_platform(source: bool) -> None:
    from test_workload_profiles import profile

    p = profile(100, source)
    stream = {
        "kind": "source_profile" if source else "target_profile",
        "vm_ids": ["vm-1"],
        "api_version": "9.1.1.0",
    }
    with pytest.raises(Rejected, match="invalid_workload_profile"):
        profile_payload(p, stream, "project-a", "ahv")


@pytest.mark.parametrize(
    "fault", ["duplicate_nic", "duplicate_disk", "malformed_disk", "nic_state"]
)
def test_source_profiles_reject_ambiguous_device_inventory(fault: str) -> None:
    p = profiles()[0]
    if fault == "duplicate_nic":
        p["nics"].append(deepcopy(p["nics"][0]))
    elif fault == "duplicate_disk":
        record = p["native"]["disk_records"][1]
        record["native_id"] = p["native"]["disk_records"][0]["native_id"]
        p["disks"][1]["native_sha256"] = digest(record)
    elif fault == "malformed_disk":
        p["native"]["disk_records"][0]["key"] = []
    else:
        p["nics"][0]["connectable"]["connected"] = "false"
    stream = {"kind": "source_profile", "vm_ids": [p["vm_id"]], "api_version": p["api_version"]}
    with pytest.raises(Rejected):
        profile_payload(p, stream, p["native_scope"], p["platform"])


def test_ahv_observed_installed_version_is_part_of_exact_tuple() -> None:
    p = profiles()[1]
    profile: dict[str, Any] = {
        "facts": p,
        "digest": digest(p),
        "endpoint_id": str(uuid4()),
        "collected_at": 100,
        "expires_at": 200,
    }
    app = WorkloadProfiles(Mock())
    original = app.binding(profile)
    p["native"]["metadata"]["installed"] = {"cluster": {"buildInfo": {"version": "changed"}}}
    assert app.binding(profile)["tuple_sha256"] != original["tuple_sha256"]
