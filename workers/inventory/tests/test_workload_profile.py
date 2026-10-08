"""Native facts remain observed, incomplete application facts remain owner inputs."""

from copy import deepcopy
from typing import Any
from uuid import uuid4

import pytest

from inventory_worker.infrastructure.native import CollectionFailure
from inventory_worker.infrastructure.profile_digest import fingerprint
from inventory_worker.infrastructure.vmware_workload import VmwareWorkloadDiscovery, normalize


def records() -> dict[str, Any]:
    return {
        "config": {
            "instanceUuid": str(uuid4()),
            "uuid": str(uuid4()),
            "guestId": "otherLinux64Guest",
            "firmware": "efi",
            "hardware": {
                "numCPU": 2,
                "memoryMB": 4096,
                "device": [
                    {"_typeName": "VirtualLsiLogicController", "key": 1000, "busNumber": 0},
                    {
                        "_typeName": "VirtualDisk",
                        "key": 2000,
                        "controllerKey": 1000,
                        "unitNumber": 0,
                        "capacityInBytes": 1048576,
                        "backing": {
                            "_typeName": "VirtualDiskFlatVer2BackingInfo",
                            "diskMode": "persistent",
                            "fileName": "sensitive-native-path",
                        },
                    },
                    {
                        "_typeName": "VirtualVmxnet3",
                        "key": 4000,
                        "macAddress": "00:50:56:00:00:01",
                        "backing": {"port": {"switchUuid": "switch-1", "portgroupKey": "dvpg-1"}},
                    },
                ],
            },
        },
        "runtime": {"powerState": "poweredOn", "host": {"type": "HostSystem", "value": "host-1"}},
        "guest": {"toolsRunningStatus": "guestToolsRunning", "toolsVersion": "123"},
        "content": {
            "about": {"instanceUuid": str(uuid4()), "version": "9.1.1", "apiVersion": "9.1.1.0"}
        },
        "capability": {"snapshotConfigSupported": True},
        "host_capability": {"cloneFromSnapshotSupported": True},
        "snapshot": None,
    }


def test_all_disks_and_native_facts_are_normalized_without_credential_data() -> None:
    r = records()
    p = normalize("vm-1", "9.1.1.0", r, 1000)
    assert not p["holds"]
    assert p["disks"][0]["native_sha256"] == fingerprint(r["config"]["hardware"]["device"][1])
    assert p["cpu"] == 2 and p["firmware"] == "efi"
    assert p["required_owner_inputs"]
    assert p["native_qualification"] == "not_established"
    assert "sensitive-native-path" not in str(p)


@pytest.mark.parametrize(
    "fault",
    ["unknown_capacity", "rdm", "encrypted", "controller", "capability", "vcenter", "firmware"],
)
def test_unknown_native_facts_remain_held(fault: str) -> None:
    r = records()
    d = r["config"]["hardware"]["device"][1]
    if fault == "unknown_capacity":
        d.pop("capacityInBytes")
    if fault == "rdm":
        d["backing"]["_typeName"] = "VirtualDiskRawDiskMappingVer1BackingInfo"
    if fault == "encrypted":
        d["backing"]["keyId"] = {"keyId": "sensitive-key"}
    if fault == "controller":
        d["controllerKey"] = 9999
    if fault == "capability":
        r["host_capability"] = {}
    if fault == "vcenter":
        r["content"]["about"].pop("instanceUuid")
    if fault == "firmware":
        r["config"]["firmware"] = None
    p = normalize("vm-1", "9.1.1.0", r, 1000)
    assert p["holds"]
    assert "sensitive-key" not in str(p)


def test_source_scope_and_configuration_change_are_denied() -> None:
    class Reader(VmwareWorkloadDiscovery):
        def __init__(self) -> None:
            super().__init__({}, {"vm-1"}, "9.1.1.0", lambda: 1000, lambda: None)
            self.responses = records()
            self.calls: list[str] = []

        def read(self, kind: str, native_id: str, field: str) -> Any:
            self.calls.append(field)
            value = deepcopy(self.responses["host_capability" if kind == "HostSystem" else field])
            if field == "config" and self.calls.count("config") == 2:
                value["hardware"]["numCPU"] = 4
            return value

    reader = Reader()
    with pytest.raises(CollectionFailure, match="permission_denied"):
        reader.collect("vm-2")
    assert reader.calls == []
    with pytest.raises(CollectionFailure, match="source_changed"):
        reader.collect("vm-1")


@pytest.mark.parametrize(
    "path",
    [
        ("config",),
        ("runtime",),
        ("guest",),
        ("content",),
        ("capability",),
        ("host_capability",),
        ("config", "hardware"),
        ("config", "bootOptions"),
        ("content", "about"),
    ],
)
def test_malformed_vmware_objects_are_reported_as_invalid_native_responses(
    path: tuple[str, ...],
) -> None:
    r = records()
    parent = r
    for key in path[:-1]:
        parent = parent[key]
    parent[path[-1]] = None
    with pytest.raises(CollectionFailure, match="invalid_response"):
        normalize("vm-1", "9.1.1.0", r, 1000)


def test_malformed_vmware_nic_connectivity_is_rejected() -> None:
    r = records()
    r["config"]["hardware"]["device"][2]["connectable"] = []
    with pytest.raises(CollectionFailure, match="invalid_response"):
        normalize("vm-1", "9.1.1.0", r, 1000)


def target_records() -> dict[str, Any]:
    return {
        "image_schema": {"properties": {"disk_format": {"enum": ["raw", "qcow2"]}}},
        "image_import": {"import-methods": {"value": ["glance-direct"]}},
        "flavors": {"flavors": [{"id": "small", "vcpus": 2, "ram": 4096, "disk": 0}]},
        "volume_types": {"volume_types": [{"id": "type-1", "is_public": False}]},
        "network_extensions": {"extensions": [{"alias": "security-group"}]},
        "compute_version": {"min_version": "2.1", "version": "2.100"},
        "volume_version": {"min_version": "3.0", "version": "3.75"},
    }


def test_target_formats_and_import_routes_are_observed_not_inferred() -> None:
    from inventory_worker.infrastructure.openstack_capabilities import target_profile

    r = target_records()
    p = target_profile("project-1", r, 1000)
    assert p["disk_formats"] == ["qcow2", "raw"]
    assert "vmdk" not in p["disk_formats"]
    assert p["native_qualification"] == "not_established"
    assert "guest_driver_profile" in p["required_capability_evidence"]
    r["image_schema"] = {}
    assert target_profile("project-1", r, 1000)["holds"] == ["image_formats_unobserved"]
    r["flavors"]["flavors_links"] = [{"rel": "next", "href": "https://untrusted.invalid"}]
    with pytest.raises(CollectionFailure):
        target_profile("project-1", r, 1000)


@pytest.mark.parametrize(
    "path",
    [
        ("image_schema",),
        ("image_schema", "properties"),
        ("image_schema", "properties", "disk_format"),
        ("image_import", "import-methods"),
    ],
)
def test_malformed_openstack_capability_objects_are_rejected(path: tuple[str, ...]) -> None:
    from inventory_worker.infrastructure.openstack_capabilities import target_profile

    r = target_records()
    parent = r
    for key in path[:-1]:
        parent = parent[key]
    parent[path[-1]] = None
    with pytest.raises(CollectionFailure, match="invalid_response"):
        target_profile("project-1", r, 1000)


@pytest.mark.parametrize(
    ("field", "collection", "identity"),
    [
        ("flavors", "flavors", "id"),
        ("volume_types", "volume_types", "id"),
        ("network_extensions", "extensions", "alias"),
    ],
)
@pytest.mark.parametrize("fault", ["duplicate", "missing", "malformed"])
def test_ambiguous_openstack_capability_identities_are_rejected(
    field: str,
    collection: str,
    identity: str,
    fault: str,
) -> None:
    from inventory_worker.infrastructure.openstack_capabilities import target_profile

    r = target_records()
    rows = r[field][collection]
    if fault == "duplicate":
        rows *= 2
    elif fault == "missing":
        rows[0].pop(identity)
    else:
        rows[0][identity] = []
    with pytest.raises(CollectionFailure, match="invalid_response"):
        target_profile("project-1", r, 1000)
