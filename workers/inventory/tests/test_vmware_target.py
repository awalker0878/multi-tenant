"""Bounded destination discovery retains native identity and rechecks authority."""

from typing import Any

import pytest

from inventory_worker.infrastructure import vmware_profile
from inventory_worker.infrastructure.native import CollectionFailure
from inventory_worker.infrastructure.profile_collection import collect_profile


def test_vmware_target_uses_datacenter_scope_and_per_request_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[str] = []
    permits: list[bool] = []

    def exchange(stream: Any, path: str, headers: Any, **kwargs: Any) -> Any:
        requests.append(path)
        assert len(permits) == len(requests)
        if path.endswith("/content"):
            return {
                "about": {
                    "instanceUuid": "vcenter-a",
                    "version": "9.1",
                    "apiVersion": "9.1",
                    "build": "123",
                }
            }
        if path.endswith("/HostSystem/host-1/parent"):
            return {"type": "ComputeResource", "value": "resgroup-1"}
        if path.endswith("/ComputeResource/resgroup-1/environmentBrowser"):
            return {"type": "EnvironmentBrowser", "value": "env-1"}
        if path.endswith("/EnvironmentBrowser/env-1/QueryConfigOption"):
            assert kwargs == {"method": "POST", "body": {
                "host": {"_typeName": "ManagedObjectReference",
                         "type": "HostSystem", "value": "host-1"},
            }}
            return {"version": "vmx-21", "guestOSDescriptor": [
                {"id": "otherLinux64Guest"}, {"id": "rhel9_64Guest"}
            ]}
        assert path.endswith("?datacenters=datacenter-1")
        key = path.split("/")[-1].split("?")[0].replace("-", "_")
        rows = [
            {
                key: key + "-1",
                "name": key,
                "type": "VIRTUAL_MACHINE" if key == "folder" else "NETWORK",
            }
        ]
        if key == "folder":
            rows.append({"folder": "group-h1", "name": "Hosts", "type": "HOST"})
        return rows

    monkeypatch.setattr(vmware_profile, "exchange", exchange)
    monkeypatch.setattr(vmware_profile, "secret", lambda _: "fixture")
    result = collect_profile(
        {"platform": "vmware", "native_scope": "datacenter-1", "coverage_reference": "ref"},
        {"kind": "target_profile", "api_version": "9.1.1.0", "credential_file": "/fixture"},
        None,
        lambda: permits.append(True),
    )
    assert len(requests) == 9
    p = result["profile"]
    assert p["project_id"] == "datacenter-1" and p["holds"] == []
    assert p["native_qualification"] == "not_established"
    assert p["disk_formats"] == ["vmdk"] and p["networks"][0]["network"] == "network-1"
    assert p["guest_options_by_host"] == [{
        "host": "host-1", "guest_ids": ["otherLinux64Guest", "rhel9_64Guest"],
        "hardware_versions": ["vmx-21"],
        "native_sha256": p["guest_options_by_host"][0]["native_sha256"],
    }]
    assert [row["folder"] for row in p["folders"]] == ["folder-1"]
    with pytest.raises(CollectionFailure):
        collect_profile({"platform": "vmware"}, {"kind": "target_profile"}, "cursor", lambda: None)


def test_destination_read_revocation_stops_before_first_get(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(vmware_profile, "secret", lambda _: "fixture")

    def revoked() -> None:
        raise CollectionFailure("permission_denied")

    with pytest.raises(CollectionFailure, match="permission_denied"):
        vmware_profile.collect_vmware({}, {"credential_file": "/fixture"}, 1, revoked)
