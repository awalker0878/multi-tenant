"""Native source parsing and authority failure cases, using synthetic API responses."""

from copy import deepcopy
from typing import Any
from uuid import uuid4

import pytest

from inventory_worker.infrastructure import ahv_workload, openstack_workload
from inventory_worker.infrastructure.native import CollectionFailure
from inventory_worker.infrastructure.profile_collection import collect_profile


def openstack_fixture() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    vm, volume, image, port = (str(uuid4()) for _ in range(4))
    streams = [
        {"kind": k, "credential_file": "/synthetic", "base_url": "https://native.example"}
        for k in ("server", "network", "volume")
    ]
    stream = streams[0] | {"kind": "source_profile", "api_version": "2.1", "vm_ids": [vm]}
    policy = {
        "platform": "openstack",
        "authority": "cloud-a",
        "native_scope": "project-a",
        "installed": {"product": "synthetic"},
        "streams": streams,
        "coverage_reference": None,
    }
    server = {
        "id": vm,
        "tenant_id": "project-a",
        "created": "2026-01-01T00:00:00Z",
        "status": "SHUTOFF",
        "flavor": {"id": "small"},
        "image": {"id": image},
        "metadata": {"os_distro": "debian", "hw_firmware_type": "bios"},
    }
    responses = {
        f"/servers/{vm}": {"server": server},
        "/flavors/small": {"flavor": {"vcpus": 2, "ram": 4096, "disk": 20}},
        f"/servers/{vm}/os-volume_attachments": {"volumeAttachments": [{"volumeId": volume}]},
        f"/ports?device_id={vm}&project_id=project-a&limit=33": {
            "ports": [
                {
                    "id": port,
                    "project_id": "project-a",
                    "device_id": vm,
                    "status": "ACTIVE",
                    "admin_state_up": True,
                }
            ]
        },
        f"/volumes/{volume}": {
            "volume": {
                "id": volume,
                "size": 10,
                "encrypted": False,
                "multiattach": False,
                "bootable": "false",
                "attachments": [{"server_id": vm}],
            }
        },
    }
    return policy, stream, responses


def test_openstack_source_includes_attached_bytes_and_native_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    policy, stream, responses = openstack_fixture()
    requests: list[str] = []
    permits: list[bool] = []

    def read(connection: Any, path: str, headers: Any) -> Any:
        requests.append(path)
        assert len(permits) == len(requests)
        return deepcopy(responses[path])

    monkeypatch.setattr(openstack_workload, "exchange", read)
    monkeypatch.setattr(openstack_workload, "secret", lambda _: "synthetic")
    result = collect_profile(policy, stream, None, lambda: permits.append(True))
    p = result["profile"]
    assert p["platform"] == "openstack" and p["schema_version"] == 3
    assert len(p["disks"]) == 2 and sum(d["capacity_bytes"] for d in p["disks"]) == 30 * 1024**3
    assert [d["role"] for d in p["native"]["disk_records"]] == ["root", "data_volume"]
    assert p["holds"] == [] and len(requests) == 6
    assert p["native_qualification"] == "not_established"
    assert requests[0] == requests[-1]


@pytest.mark.parametrize(
    "fault",
    [
        "foreign_vm",
        "foreign_port",
        "duplicate_volume",
        "duplicate_port",
        "changed",
        "revoked",
        "truncated",
    ],
)
def test_openstack_source_rejects_scope_loss_or_incomplete_collection(
    monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    policy, stream, responses = openstack_fixture()
    vm = stream["vm_ids"][0]
    paths = list(responses)
    if fault == "foreign_vm":
        responses[paths[0]]["server"]["tenant_id"] = "foreign"
    if fault == "foreign_port":
        responses[paths[3]]["ports"][0]["project_id"] = "foreign"
    if fault == "duplicate_volume":
        responses[paths[2]]["volumeAttachments"] *= 2
    if fault == "duplicate_port":
        responses[paths[3]]["ports"] *= 2
    if fault == "truncated":
        responses[paths[3]]["ports_links"] = [{"rel": "next", "href": "https://foreign"}]
    requests: list[str] = []

    def read(connection: Any, path: str, headers: Any) -> Any:
        requests.append(path)
        value = deepcopy(responses[path])
        if fault == "changed" and path == f"/servers/{vm}" and len(requests) > 1:
            value["server"]["status"] = "ACTIVE"
        return value

    def permit() -> None:
        if fault == "revoked" and len(requests) == 2:
            raise CollectionFailure("permission_denied")

    monkeypatch.setattr(openstack_workload, "exchange", read)
    monkeypatch.setattr(openstack_workload, "secret", lambda _: "synthetic")
    with pytest.raises(CollectionFailure):
        collect_profile(policy, stream, None, permit)
    if fault == "revoked":
        assert len(requests) == 2


def ahv_fixture() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    vm, project, cluster, pc = (str(uuid4()) for _ in range(4))
    stream = {
        "kind": "source_profile",
        "credential_file": "/synthetic",
        "api_version": "v4.3",
        "vm_ids": [vm],
        "cluster_id": cluster,
        "prism_central_id": pc,
    }
    policy = {
        "platform": "ahv",
        "native_scope": project,
        "installed": {"product": "synthetic"},
        "coverage_reference": None,
    }
    row = {
        "extId": vm,
        "name": "vm",
        "projectExtId": project,
        "cluster": {"extId": cluster},
        "generationUuid": str(uuid4()),
        "biosUuid": str(uuid4()),
        "numSockets": 2,
        "numCoresPerSocket": 2,
        "numThreadsPerCore": 1,
        "memorySizeBytes": 4 * 1024**3,
        "powerState": "OFF",
        "bootConfig": {"$objectType": "vmm.v4.ahv.config.LegacyBoot"},
        "disks": [
            {
                "extId": str(uuid4()),
                "diskAddress": {"busType": "SCSI", "index": 0},
                "backingInfo": {
                    "$objectType": "vmm.v4.ahv.config.VmDisk",
                    "diskSizeBytes": 1024**3,
                },
            }
        ],
        "nics": [],
        "guestCustomization": {"password": "must-not-persist"},
    }
    return policy, stream, row


def test_ahv_source_preserves_native_identity_without_guest_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    policy, stream, row = ahv_fixture()

    def read(connection: Any, path: str, headers: Any) -> Any:
        if "/vms/" in path:
            return {"data": deepcopy(row)}
        return {
            "data": {
                "extId": path.rsplit("/", 1)[-1],
                "config": {
                    "buildInfo": {"version": "synthetic"},
                    "clusterSoftwareMap": [{"softwareType": "NOS", "version": "synthetic"}],
                    "hypervisorTypes": ["AHV"],
                },
            }
        }

    permits: list[bool] = []
    monkeypatch.setattr(ahv_workload, "exchange", read)
    monkeypatch.setattr(ahv_workload, "secret", lambda _: "synthetic")
    p = collect_profile(policy, stream, None, lambda: permits.append(True))["profile"]
    assert p["cpu"] == 4 and p["firmware"] == "bios" and p["guest_id"] is None
    assert p["holds"] == []
    assert p["native"]["identity"]["generation_uuid"] == row["generationUuid"]
    assert "guestCustomization" not in p["native"]["metadata"]["vm"] and len(permits) == 4
    row["projectExtId"] = str(uuid4())
    with pytest.raises(CollectionFailure, match="permission_denied"):
        collect_profile(policy, stream, None, lambda: None)


@pytest.mark.parametrize("fault", ["duplicate_disk", "malformed_disk", "malformed_scope", "memory"])
def test_ahv_source_rejects_ambiguous_or_malformed_native_inventory(
    monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    policy, stream, row = ahv_fixture()
    if fault == "duplicate_disk":
        row["disks"] *= 2
    elif fault == "malformed_disk":
        row["disks"] = [None]
    elif fault == "malformed_scope":
        row["cluster"] = None
    else:
        row["memorySizeBytes"] = 0

    def read(connection: Any, path: str, headers: Any) -> Any:
        if "/vms/" in path:
            return {"data": deepcopy(row)}
        return {"data": {"extId": path.rsplit("/", 1)[-1], "config": {}}}

    monkeypatch.setattr(ahv_workload, "exchange", read)
    monkeypatch.setattr(ahv_workload, "secret", lambda _: "synthetic")
    with pytest.raises(CollectionFailure):
        collect_profile(policy, stream, None, lambda: None)


@pytest.mark.parametrize("firmware", [None, "uefi", "unrecognized"])
def test_openstack_firmware_is_normalized_without_inventing_native_support(
    monkeypatch: pytest.MonkeyPatch, firmware: str | None
) -> None:
    policy, stream, responses = openstack_fixture()
    vm = stream["vm_ids"][0]
    responses[f"/servers/{vm}"]["server"]["metadata"]["hw_firmware_type"] = firmware
    monkeypatch.setattr(
        openstack_workload, "exchange", lambda connection, path, headers: deepcopy(responses[path])
    )
    monkeypatch.setattr(openstack_workload, "secret", lambda _: "synthetic")
    p = collect_profile(policy, stream, None, lambda: None)["profile"]
    assert p["firmware"] == ("efi" if firmware == "uefi" else None)
    assert ("firmware_unknown" in p["holds"]) is (firmware != "uefi")
