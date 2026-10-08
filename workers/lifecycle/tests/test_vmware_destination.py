"""Synthetic VI API with real pinned TLS disk uploads; no native qualification."""

import copy
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import uuid4
from xml.etree.ElementTree import fromstring

import pytest
from test_native import Journal
from test_native import binding as binding
from test_native_http import native_tls as native_tls

from lifecycle_worker.application.native import (
    NativeApiExecution,
    NativeBinding,
    NativeHeld,
    digest,
)
from lifecycle_worker.infrastructure.native_json import NativeJson
from lifecycle_worker.infrastructure.vmware_import import (
    NfcUpload,
    VmwareDestination,
    VmwareDestinationObserver,
)


class ImportJournal(Journal):
    def import_lease(self, binding: NativeBinding) -> str:
        return str(next(f["lease_id"] for e, f in self.events if e == "import_lease"))


class Api(NativeJson):
    def __init__(self, p: dict[str, Any], b: NativeBinding, upload_url: str, data: bytes) -> None:
        self.p, self.b, self.upload_url, self.data = p, b, upload_url, data
        self.calls: list[tuple[str, str, Any]] = []
        self.fault, self.state = "", "ready"
        self.hardware: dict[str, Any] = {
            "name": p["name"],
            "numCPUs": p["cpu"],
            "memoryMB": p["memory_mb"],
            "firmware": p["firmware"],
            "guestId": p["guest_id"],
            "version": p["hardware_version"],
            "deviceChange": [],
        }
        self.devices: list[dict[str, Any]] = [
            {
                "_typeName": "VirtualDisk",
                "key": 100 + i,
                "capacityInBytes": d["virtual_bytes"],
                "controllerKey": 1000,
                "unitNumber": i,
                "backing": {
                    "_typeName": "VirtualDiskFlatVer2BackingInfo",
                    "diskMode": "persistent",
                    "datastore": {"type": "Datastore", "value": p["datastore_id"]},
                },
            }
            for i, d in enumerate(p["disks"])
        ] + [
            {
                "_typeName": "VirtualVmxnet3",
                "key": 200 + i,
                "backing": {"network": {"type": "Network", "value": nic["quarantine_network_id"]}},
                "connectable": {"startConnected": False, "connected": False},
            }
            for i, nic in enumerate(p["nics"])
        ]
        self.devices.append({"_typeName": "VirtualLsiLogicController", "key": 1000, "busNumber": 0})
        self.hardware["deviceChange"] = [{"device": d, "operation": "add"} for d in self.devices]

    def request(
        self, method: str, path: str, boundary: Any, body: Any = None, expected: int = 200
    ) -> Any:
        boundary()
        self.calls.append((method, path, copy.deepcopy(body)))
        action = path.rsplit("/", 1)[1]
        if action == "childType":
            return ["VirtualMachine"]
        if action == "summary":
            return {"accessible": self.fault != "storage"}
        if action == "runtime":
            return (
                {"connectionState": "connected", "inMaintenanceMode": False}
                if "/HostSystem/" in path
                else {"powerState": "poweredOn" if self.fault == "running" else "poweredOff"}
            )
        if action == "CreateImportSpec":
            descriptor = fromstring(body["ovfDescriptor"])
            assert (
                len(descriptor.findall("{http://schemas.dmtf.org/ovf/envelope/1}References/*")) == 2
            )
            return {
                "importSpec": {
                    "_typeName": "VirtualMachineImportSpec",
                    "configSpec": copy.deepcopy(self.hardware),
                },
                "fileItem": [
                    {
                        "path": d["key"] + ".vmdk",
                        "deviceId": d["key"],
                        "size": len(self.data),
                        "create": False,
                        "cimType": 17,
                        **({"compressionMethod": "gzip"} if self.fault == "compressed" else {}),
                        **({"chunkSize": 512} if self.fault == "chunked" else {}),
                    }
                    for d in self.p["disks"]
                ],
            }
        if action == "ImportVApp":
            if self.fault == "lost_response":
                raise NativeHeld("response_lost")
            assert body["spec"]["configSpec"]["annotation"] == "migration:" + self.b.fingerprint
            return {"type": "HttpNfcLease", "value": "lease-1"}
        if action == "state":
            return self.state
        if action == "info":
            return {
                "entity": {"type": "VirtualMachine", "value": "vm-123"},
                "leaseTimeout": 60,
                "deviceUrl": [
                    {
                        "importKey": "wrong" if self.fault == "mapping" else d["key"],
                        "url": self.upload_url
                        + ("" if self.fault == "duplicate_url" else "/" + d["key"]),
                    }
                    for d in self.p["disks"]
                ],
            }
        if action == "HttpNfcLeaseProgress":
            assert expected == 204
            return None
        if action == "HttpNfcLeaseComplete":
            assert expected == 204
            self.state = "done"
            if self.fault == "completion_lost":
                raise NativeHeld("response_lost")
            return None
        if action == "config":
            return {
                "name": self.p["name"],
                "firmware": self.p["firmware"],
                "guestId": self.p["guest_id"],
                "version": self.hardware["version"],
                "annotation": "foreign"
                if self.fault == "foreign"
                else "migration:" + self.b.fingerprint,
                "hardware": {
                    "numCPU": self.p["cpu"],
                    "memoryMB": self.p["memory_mb"],
                    "device": self.devices,
                },
            }
        if action == "parent":
            if "/Folder/" in path:
                return {
                    "type": "Datacenter",
                    "value": "datacenter-99"
                    if self.fault == "folder_scope"
                    else self.p["project_id"],
                }
            if "/HostSystem/" in path:
                return {
                    "type": "ClusterComputeResource",
                    "value": "domain-c99" if self.fault == "host_pool" else "domain-c1",
                }
            if "/ClusterComputeResource/" in path:
                return {
                    "type": "Datacenter",
                    "value": "datacenter-99"
                    if self.fault == "compute_scope"
                    else self.p["project_id"],
                }
            return {"type": "Folder", "value": self.p["folder_id"]}
        if action == "owner":
            return {"type": "ClusterComputeResource", "value": "domain-c1"}
        if action == "datastore":
            if self.fault == "datastore_scope" and "/Datacenter/" in path:
                return []
            if self.fault == "datastore_host" and "/HostSystem/" in path:
                return []
            return [{"type": "Datastore", "value": self.p["datastore_id"]}]
        if action == "network":
            if self.fault == "network_scope" and "/Datacenter/" in path:
                return []
            if self.fault == "network_host" and "/HostSystem/" in path:
                return []
            return [
                {"type": "Network", "value": key}
                for key in {
                    n[field]
                    for n in self.p["nics"]
                    for field in ("quarantine_network_id", "production_network_id")
                }
            ]
        if action == "resourcePool":
            return {"type": "ResourcePool", "value": self.p["resource_pool_id"]}
        raise AssertionError((method, path))


@pytest.fixture
def destination(binding: NativeBinding, tmp_path: Path, native_tls: Any) -> dict[str, Any]:
    binding = replace(binding, project_id="datacenter-42")
    reads, wire = native_tls
    endpoint = reads.endpoints["compute"]
    origin = endpoint.base_url.split("/compute/")[0]
    p: dict[str, Any] = {
        "schema_version": 2,
        "kind": "vmware_destination",
        **{
            k: binding.document()[k]
            for k in ("custody_id", "custody_generation", "ownership_digest")
        },
        "api_version": "8.0.3.0",
        "destination_sha256": "d" * 64,
        "conversion_plan_sha256": "e" * 64,
        "project_id": binding.project_id,
        "folder_id": "group-v3",
        "resource_pool_id": "resgroup-4",
        "host_id": "host-5",
        "datastore_id": "datastore-6",
        "name": "migration-copy",
        "cpu": 2,
        "memory_mb": 1024,
        "guest_id": "ubuntu64Guest",
        "hardware_version": "vmx-20",
        "firmware": "efi",
        "disks": [{"key": "disk-" + str(i), "virtual_bytes": 1024} for i in range(2)],
        "nics": [
            {
                "source_key": i,
                "quarantine_network_id": "network-" + str(i + 1),
                "production_network_id": "network-10",
            }
            for i in range(2)
        ],
        "max_seconds": 10,
        "bytes_per_second": 2**30,
    }
    b = replace(binding, operation_plan_sha256=digest(p))
    file = tmp_path / "vmware.json"
    file.write_text(json.dumps(p))
    file.chmod(0o600)
    spool = tmp_path / "spool"
    spool.mkdir(mode=0o700)
    prior = str(uuid4())
    data = b"migration disk" * 64
    receipt = {
        "format": "vmdk",
        "sector_comparison": "passed",
        "virtual_bytes": 1024,
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "sha512": hashlib.sha512(data).hexdigest(),
    }
    for disk in p["disks"]:
        folder = spool / prior / disk["key"]
        folder.mkdir(parents=True)
        (folder / "disk.vmdk").write_bytes(data)

    class Custody:
        def artifact(self, b: NativeBinding, sha: str, kind: str) -> dict[str, Any]:
            assert sha == p["conversion_plan_sha256"] and kind == "conversion"
            return {"operation_id": prior, "disks": {d["key"]: receipt for d in p["disks"]}}

    class Authority:
        def require_current(self, supplied: NativeBinding, boundary: str) -> None:
            assert supplied == b

    journal = ImportJournal()
    api = Api(p, b, origin + "/nfc/upload", data)
    adapter = VmwareDestination(file, api, NfcUpload({origin: endpoint}), journal, Custody(), spool)
    observer = VmwareDestinationObserver(file, api, journal, lambda: 100, lambda: None)
    return {
        "binding": b,
        "plan": p,
        "api": api,
        "adapter": adapter,
        "observer": observer,
        "journal": journal,
        "wire": wire,
        "data": data,
        "receipt": receipt,
        "execution": NativeApiExecution(Authority(), journal, adapter, observer, lambda: 100),
    }


def test_native_import_uploads_every_disk_and_observes_isolated_vm(
    destination: dict[str, Any],
) -> None:
    c = destination
    result = c["execution"].execute(c["binding"])
    assert result["observation"]["outcome"] == "observed_present"
    assert result["application_ready"] is False
    assert len(c["wire"]["requests"]) == 2
    assert all(r["body"] == c["data"] and r["authorization"] is None for r in c["wire"]["requests"])
    with pytest.raises(NativeHeld, match="reconciliation"):
        c["execution"].execute(c["binding"])
    assert len(c["wire"]["requests"]) == 2


@pytest.mark.parametrize(
    "fault", ["storage", "mapping", "lost_response", "duplicate_url", "compressed", "chunked"]
)
def test_unavailable_or_unknown_destination_never_uploads_or_replays(
    destination: dict[str, Any], fault: str
) -> None:
    c = destination
    c["api"].fault = fault
    with pytest.raises(NativeHeld):
        c["execution"].execute(c["binding"])
    calls = len(c["api"].calls)
    with pytest.raises(NativeHeld):
        c["execution"].execute(c["binding"])
    assert len(c["api"].calls) == calls and not c["wire"]["requests"]


@pytest.mark.parametrize("fault", ["running", "foreign", "incomplete_lease"])
def test_imported_readback_rejects_activation_wrong_ownership_and_incomplete_lease(
    destination: dict[str, Any], fault: str
) -> None:
    c = destination
    assert c["journal"].claim(c["binding"])
    c["adapter"].execute(c["binding"], lambda: None)
    c["api"].fault = fault
    if fault == "incomplete_lease":
        c["api"].state = "ready"
    with pytest.raises(NativeHeld):
        c["observer"].observe(c["binding"], c["journal"].resources(c["binding"]))


@pytest.mark.parametrize(
    "fault", ["version", "raw_disk", "shared_disk", "parent", "connected", "device_operation"]
)
def test_import_spec_changed_or_unsafe_hardware_never_creates_vm(
    destination: dict[str, Any], fault: str
) -> None:
    c = destination
    config = c["api"].hardware
    if fault == "version":
        config["version"] = "vmx-19"
    elif fault == "raw_disk":
        c["api"].devices[0]["backing"]["_typeName"] = "VirtualDiskRawDiskMappingVer1BackingInfo"
    elif fault == "shared_disk":
        c["api"].devices[0]["backing"]["sharing"] = "sharingMultiWriter"
    elif fault == "parent":
        c["api"].devices[0]["backing"]["parent"] = {"fileName": "foreign.vmdk"}
    elif fault == "connected":
        c["api"].devices[2]["connectable"]["connected"] = True
    else:
        config["deviceChange"][0]["operation"] = "edit"
    with pytest.raises(NativeHeld):
        c["execution"].execute(c["binding"])
    assert not c["wire"]["requests"]
    assert not any(path.endswith("/ImportVApp") for _, path, _ in c["api"].calls)


def test_lost_completion_response_reconciles_without_import_or_upload_replay(
    destination: dict[str, Any],
) -> None:
    c = destination
    c["api"].fault = "completion_lost"
    with pytest.raises(NativeHeld):
        c["execution"].execute(c["binding"])
    assert len(c["wire"]["requests"]) == 2
    result = c["execution"].reconcile(c["binding"])
    assert result["outcome"] == "observed_present"
    assert len(c["wire"]["requests"]) == 2
    assert sum(path.endswith("/ImportVApp") for _, path, _ in c["api"].calls) == 1


@pytest.mark.parametrize("fault", ["", "uncommissioned", "credentials", "no_origin"])
def test_native_wildcard_upload_host_requires_exact_commissioned_origin(
    native_tls: Any, fault: str
) -> None:
    from urllib.parse import urlsplit

    reads, _ = native_tls
    endpoint = reads.endpoints["compute"]
    origin = "https://" + urlsplit(endpoint.base_url).netloc
    wildcard = "https://" + ("secret@" if fault == "credentials" else "")
    wildcard += "*:" + str(urlsplit(origin).port) + "/nfc/disk"
    uploader = NfcUpload(
        {} if fault == "uncommissioned" else {origin: endpoint},
        None if fault == "no_origin" else endpoint.base_url,
    )
    if fault:
        with pytest.raises(NativeHeld, match="uncommissioned"):
            uploader.destination(wildcard)
    else:
        assert uploader.destination(wildcard) == (origin + "/nfc/disk", endpoint)


@pytest.mark.parametrize(
    "fault",
    [
        "folder_scope",
        "compute_scope",
        "host_pool",
        "datastore_scope",
        "datastore_host",
        "network_scope",
        "network_host",
    ],
)
def test_native_scope_drift_prevents_import_and_independent_acceptance(
    destination: dict[str, Any], fault: str
) -> None:
    c = destination
    assert c["journal"].claim(c["binding"])
    c["api"].fault = fault
    with pytest.raises(NativeHeld):
        c["adapter"].execute(c["binding"], lambda: None)
    assert not any(method == "POST" for method, _, _ in c["api"].calls)
    c["api"].fault = ""
    c["adapter"].execute(c["binding"], lambda: None)
    c["api"].fault = fault
    with pytest.raises(NativeHeld):
        c["observer"].observe(c["binding"], c["journal"].resources(c["binding"]))


@pytest.mark.parametrize("platform,firmware", [("ahv", "efi"), ("vmware", "bios")])
def test_prepared_copy_must_match_vmware_guest_target(
    destination: dict[str, Any], platform: str, firmware: str
) -> None:
    c = destination
    c["receipt"].update(
        guest_transformation="prepared_offline",
        guest_target_platform=platform,
        guest_firmware=firmware,
    )
    with pytest.raises(NativeHeld, match="disk_changed"):
        c["adapter"].execute(c["binding"], lambda: None)
    assert not any(method == "POST" for method, _, _ in c["api"].calls)
