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
