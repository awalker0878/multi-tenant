"""Native VI JSON import spec and NFC upload into a powered-off isolated VM.

MIGRATION_API_CAPABILITIES = frozenset({"vm.disk.import"})

No VDDK, production guest mutation, default network, automatic activation or
uncertain write replay. Every upload maps one retained disk to one lease device.
"""

import hashlib
import http.client
import os
import re
import stat
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlsplit, urlunsplit

from lifecycle_worker.application.api_plan import name, shape
from lifecycle_worker.application.native import (
    NativeBinding,
    NativeHeld,
    NativeJournal,
    decode,
    digest,
    identity,
    sha256,
)
from lifecycle_worker.infrastructure.image_conversion import file_digest
from lifecycle_worker.infrastructure.migration_custody import ArtifactCustody
from lifecycle_worker.infrastructure.native_files import protected_read
from lifecycle_worker.infrastructure.native_http import NativeEndpoint, PinnedConnection
from lifecycle_worker.infrastructure.native_json import NativeJson
from lifecycle_worker.infrastructure.vmware_capture import NICS, devices, moref, reference
from lifecycle_worker.infrastructure.vmware_ovf import descriptor


class ImportJournal(NativeJournal, Protocol):
    def import_lease(self, binding: NativeBinding) -> str: ...


def validate(p: dict[str, Any], b: NativeBinding) -> dict[str, Any]:
    shape(
        p,
        {
            "schema_version",
            "kind",
            "api_version",
            "destination_sha256",
            "conversion_plan_sha256",
            "project_id",
            "custody_id",
            "custody_generation",
            "ownership_digest",
            "folder_id",
            "resource_pool_id",
            "host_id",
            "datastore_id",
            "name",
            "cpu",
            "memory_mb",
            "guest_id",
            "hardware_version",
            "firmware",
            "disks",
            "nics",
            "max_seconds",
            "bytes_per_second",
        },
    )
    if (
        type(p["schema_version"]) is not int
        or p["schema_version"] != 2
        or p["kind"] != "vmware_destination"
        or digest(p) != b.operation_plan_sha256
        or p["project_id"] != b.project_id
        or not isinstance(p["project_id"], str)
        or re.fullmatch(r"datacenter-[1-9][0-9]{0,18}", p["project_id"]) is None
        or not sha256(p["destination_sha256"])
        or not sha256(p["conversion_plan_sha256"])
        or not isinstance(p["api_version"], str)
        or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+", p["api_version"])
    ):
        raise NativeHeld("vmware_import_plan_changed")
    if any(
        p[k] != b.document()[k] for k in ("custody_id", "custody_generation", "ownership_digest")
    ):
        raise NativeHeld("vmware_import_custody_changed")
    for key, kind in (
        ("folder_id", "Folder"),
        ("resource_pool_id", "ResourcePool"),
        ("host_id", "HostSystem"),
        ("datastore_id", "Datastore"),
    ):
        reference(kind, p[key])
    name(p["name"])
    for key, lower, upper in (
        ("cpu", 1, 256),
        ("memory_mb", 1, 2**24),
        ("max_seconds", 1, 86400),
        ("bytes_per_second", 65536, 2**34),
    ):
        if type(p[key]) is not int or not lower <= p[key] <= upper:
            raise NativeHeld("vmware_import_budget_invalid")
    if (
        p["firmware"] not in {"bios", "efi"}
        or not isinstance(p["guest_id"], str)
        or not re.fullmatch(r"[A-Za-z0-9_]{1,80}Guest", p["guest_id"])
        or not isinstance(p["hardware_version"], str)
        or not re.fullmatch(r"vmx-[0-9]{2}", p["hardware_version"])
    ):
        raise NativeHeld("vmware_import_guest_invalid")
    if (
        not isinstance(p["disks"], list)
        or not 1 <= len(p["disks"]) <= 32
        or not isinstance(p["nics"], list)
        or len(p["nics"]) > 32
    ):
        raise NativeHeld("vmware_import_mapping_invalid")
    keys = set()
    for disk in p["disks"]:
        shape(disk, {"key", "virtual_bytes"})
        if (
            not isinstance(disk["key"], str)
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", disk["key"])
            or disk["key"] in keys
            or type(disk["virtual_bytes"]) is not int
            or not 512 <= disk["virtual_bytes"] <= 2**46
        ):
            raise NativeHeld("vmware_import_mapping_invalid")
        keys.add(disk["key"])
    sources = set()
    for nic in p["nics"]:
        shape(nic, {"source_key", "quarantine_network_id", "production_network_id"})
        if (
            type(nic["source_key"]) is not int
            or nic["source_key"] < 0
            or nic["source_key"] in sources
            or nic["quarantine_network_id"] == nic["production_network_id"]
        ):
            raise NativeHeld("vmware_import_mapping_invalid")
        sources.add(nic["source_key"])
        for field in ("quarantine_network_id", "production_network_id"):
            reference("Network", nic[field])
    return p


def path(p: dict[str, Any], kind: str, key: str, operation: str) -> str:
    reference(kind, key)
    return f"/sdk/vim25/{p['api_version']}/{kind}/{key}/{operation}"


def destination_scope(api: NativeJson, p: dict[str, Any], current: Callable[[], None]) -> None:
    """Recheck native scope and host attachment instead of trusting cached inventory."""

    def read(kind: str, key: str, field: str) -> Any:
        return api.request("GET", path(p, kind, key, field), current)

    def ancestry(node: dict[str, Any]) -> None:
        visited: set[tuple[str, str]] = set()
        while isinstance(node, dict) and node.get("type") != "Datacenter":
            kind = node.get("type")
            if kind not in {"Folder", "ComputeResource", "ClusterComputeResource"}:
                raise NativeHeld("vmware_destination_scope_changed")
            key = moref(node, kind)
            if len(visited) >= 32 or (kind, key) in visited:
                raise NativeHeld("vmware_destination_scope_changed")
            visited.add((kind, key))
            node = read(kind, key, "parent")
        if moref(node, "Datacenter") != p["project_id"]:
            raise NativeHeld("vmware_destination_scope_changed")

    ancestry(reference("Folder", p["folder_id"]))
    owner = read("ResourcePool", p["resource_pool_id"], "owner")
    host_owner = read("HostSystem", p["host_id"], "parent")
    if not isinstance(owner, dict) or owner.get("type") not in {
        "ComputeResource",
        "ClusterComputeResource",
    }:
        raise NativeHeld("vmware_destination_scope_changed")
    if moref(owner, owner["type"]) != moref(host_owner, owner["type"]):
        raise NativeHeld("vmware_destination_host_pool_changed")
    ancestry(owner)
    for field, kind, wanted in (
        ("datastore", "Datastore", {p["datastore_id"]}),
        (
            "network",
            "Network",
            {
                n[key]
                for n in p["nics"]
                for key in ("quarantine_network_id", "production_network_id")
            },
        ),
    ):
        for parent_kind, parent_key in (
            ("Datacenter", p["project_id"]),
            ("HostSystem", p["host_id"]),
        ):
            rows = read(parent_kind, parent_key, field)
            if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                raise NativeHeld("vmware_destination_scope_changed")
            # Other network subclasses may coexist; only this qualified standard
            # Network mapping can satisfy the reviewed plan's exact references.
            observed = {moref(row, kind) for row in rows if row.get("type") == kind}
            if not wanted <= observed:
                raise NativeHeld("vmware_destination_scope_changed")


class NfcUpload:
    def __init__(self, endpoints: dict[str, NativeEndpoint], api_origin: str | None = None) -> None:
        self.endpoints, self.api_origin = endpoints, api_origin

    def destination(self, url: str) -> tuple[str, NativeEndpoint]:
        """Resolve VI's wildcard host only against the commissioned API origin."""
        if not isinstance(url, str) or any(ord(c) < 33 or ord(c) > 126 for c in url):
            raise NativeHeld("uncommissioned_native_import_destination")
        try:
            parsed = urlsplit(url)
            if parsed.username or parsed.password:
                raise NativeHeld("uncommissioned_native_import_destination")
            if parsed.hostname == "*" and self.api_origin is not None:
                origin = urlsplit(self.api_origin)
                if origin.scheme != "https" or not origin.hostname:
                    raise NativeHeld("uncommissioned_native_import_destination")
                host = origin.hostname
                if ":" in host:
                    host = "[" + host + "]"
                netloc = host + (":" + str(parsed.port) if parsed.port is not None else "")
                parsed = parsed._replace(netloc=netloc)
            endpoint = self.endpoints.get("https://" + parsed.netloc)
            if (
                endpoint is None
                or parsed.scheme != "https"
                or parsed.username
                or parsed.password
                or parsed.fragment
                or not parsed.path.startswith("/")
                or urlsplit(endpoint.base_url).netloc != parsed.netloc
            ):
                raise NativeHeld("uncommissioned_native_import_destination")
            return urlunsplit(parsed), endpoint
        except ValueError:
            raise NativeHeld("uncommissioned_native_import_destination") from None

    def upload(
        self,
        url: str,
        source: Path,
        receipt: dict[str, Any],
        create: bool,
        rate: int,
        current: Callable[[], None],
    ) -> None:
        url, endpoint = self.destination(url)
        parsed = urlsplit(url)
        connection = PinnedConnection(endpoint)
        try:
            current()
            connection.putrequest(
                "PUT" if create else "POST",
                parsed.path + ("?" + parsed.query if parsed.query else ""),
            )
            connection.putheader("Content-Type", "application/x-vnd.vmware-streamVmdk")
            connection.putheader("Content-Length", str(receipt["size"]))
            connection.endheaders()
            count, started = 0, time.monotonic()
            hashes = {key: hashlib.new(key) for key in ("sha256", "sha512")}
            # The caller verifies this exact private regular file before submission.
            fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(fd, "rb") as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                    raise NativeHeld("vmware_import_disk_changed")
                while chunk := stream.read(65536):
                    current()
                    count += len(chunk)
                    if count > receipt["size"]:
                        raise NativeHeld("vmware_import_disk_changed")
                    while (delay := count / rate - (time.monotonic() - started)) > 0:
                        current()
                        time.sleep(min(delay, 0.1))
                    connection.send(chunk)
                    for hasher in hashes.values():
                        hasher.update(chunk)
            response = connection.getresponse()
            if (
                response.status not in {200, 201}
                or count != receipt["size"]
                or any(hasher.hexdigest() != receipt[key] for key, hasher in hashes.items())
            ):
                raise NativeHeld("vmware_import_upload_unconfirmed")
            current()
        except (OSError, http.client.HTTPException):
            raise NativeHeld("vmware_import_upload_outcome_unknown") from None
        finally:
            connection.close()


def hardware(config: dict[str, Any], p: dict[str, Any], *, imported: bool) -> None:
    if not imported and any(d.get("operation") != "add" for d in config.get("deviceChange", [])):
        raise NativeHeld("vmware_import_device_mutation_unqualified")
    rows = (
        devices({"hardware": {"device": [d["device"] for d in config.get("deviceChange", [])]}})
        if not imported
        else devices(config)
    )
    disks = [d for d in rows if d.get("_typeName") == "VirtualDisk"]
    nics = sorted([d for d in rows if d.get("_typeName") in NICS], key=lambda d: d["key"])
    controllers = {d["key"]: d for d in rows if d.get("_typeName") == "VirtualLsiLogicController"}
    addresses = []
    for disk in disks:
        controller = controllers.get(disk.get("controllerKey"), {})
        if type(controller.get("busNumber")) is not int or type(disk.get("unitNumber")) is not int:
            raise NativeHeld("vmware_import_disk_address_unknown")
        addresses.append((controller["busNumber"], disk["unitNumber"], disk))
    addresses.sort(key=lambda r: (r[0], r[1]))
    if [(r[0], r[1]) for r in addresses] != [
        (i // 15, i % 15 + (1 if i % 15 >= 7 else 0)) for i in range(len(disks))
    ]:
        raise NativeHeld("vmware_import_disk_address_changed")
    disks = [r[2] for r in addresses]
    cpu, memory = (
        (config.get("hardware", {}).get("numCPU"), config.get("hardware", {}).get("memoryMB"))
        if imported
        else (config.get("numCPUs"), config.get("memoryMB"))
    )
    if (
        config.get("name") != p["name"]
        or cpu != p["cpu"]
        or memory != p["memory_mb"]
        or config.get("firmware", "bios") != p["firmware"]
        or config.get("guestId") != p["guest_id"]
        or config.get("version") != p["hardware_version"]
        or config.get("keyId") is not None
        or config.get("bootOptions", {}).get("efiSecureBootEnabled") is True
        or len(disks) != len(p["disks"])
        or len(nics) != len(p["nics"])
    ):
        raise NativeHeld("vmware_import_hardware_changed")
    for actual, expected in zip(disks, p["disks"], strict=True):
        backing = actual.get("backing", {})
        if (
            actual.get("capacityInBytes", actual.get("capacityInKB", 0) * 1024)
            != expected["virtual_bytes"]
            or backing.get("_typeName") != "VirtualDiskFlatVer2BackingInfo"
            or backing.get("diskMode") != "persistent"
            or backing.get("sharing", "sharingNone") != "sharingNone"
            or backing.get("keyId") is not None
            or backing.get("parent") is not None
            or imported
            and moref(actual.get("backing", {}).get("datastore"), "Datastore") != p["datastore_id"]
        ):
            raise NativeHeld("vmware_import_disk_changed")
    for actual, expected in zip(nics, p["nics"], strict=True):
        if (
            actual.get("_typeName") != "VirtualVmxnet3"
            or moref(actual.get("backing", {}).get("network"), "Network")
            != expected["quarantine_network_id"]
            or actual.get("connectable", {}).get("startConnected") is not False
            or actual.get("connectable", {}).get("connected", False) is not False
            or imported
            and actual.get("connectable", {}).get("connected") is not False
        ):
            raise NativeHeld("vmware_import_network_not_isolated")
    for device in rows:
        if device.get("_typeName") in {"VirtualCdrom", "VirtualFloppy"} and (
            device.get("connectable", {}).get("startConnected") is not False
            or device.get("connectable", {}).get("connected", False) is not False
        ):
            raise NativeHeld("vmware_import_media_not_isolated")


class VmwareDestination:
    def __init__(
        self,
        plan_file: Path,
        api: NativeJson,
        uploader: NfcUpload,
        journal: NativeJournal,
        custody: ArtifactCustody,
        spool: Path,
    ) -> None:
        self.plan_file, self.api, self.uploader, self.journal, self.custody, self.spool = (
            plan_file,
            api,
            uploader,
            journal,
            custody,
            spool,
        )

    def plan(self, b: NativeBinding) -> dict[str, Any]:
        return validate(decode(protected_read(self.plan_file, 1048576)), b)

    def inspect(self, b: NativeBinding) -> dict[str, Any]:
        return {"operation_plan_sha256": digest(self.plan(b)), "native_write_authorized": False}

    def execute(self, b: NativeBinding, boundary: Callable[[], None]) -> None:
        p = self.plan(b)
        deadline = time.monotonic() + p["max_seconds"]

        def current() -> None:
            boundary()
            if time.monotonic() >= deadline or digest(self.plan(b)) != b.operation_plan_sha256:
                raise NativeHeld("vmware_import_deadline_or_plan_changed")

        def call(kind: str, key: str, operation: str, body: Any = None) -> Any:
            return self.api.request(
                "GET" if body is None else "POST",
                path(p, kind, key, operation),
                current,
                body,
                expected=204
                if operation in {"HttpNfcLeaseProgress", "HttpNfcLeaseComplete"}
                else 200,
            )

        if self.journal.resources(b):
            raise NativeHeld("vmware_import_requires_reconciliation")
        destination_scope(self.api, p, current)
        if (
            "VirtualMachine" not in call("Folder", p["folder_id"], "childType")
            or call("Datastore", p["datastore_id"], "summary").get("accessible") is not True
        ):
            raise NativeHeld("vmware_destination_unavailable")
        host = call("HostSystem", p["host_id"], "runtime")
        if host.get("connectionState") != "connected" or host.get("inMaintenanceMode") is not False:
            raise NativeHeld("vmware_destination_unavailable")
        archive = self.custody.artifact(b, p["conversion_plan_sha256"], "conversion")
        operation = identity(archive["operation_id"])
        if operation == b.operation_id or set(archive["disks"]) != {d["key"] for d in p["disks"]}:
            raise NativeHeld("vmware_import_mapping_invalid")
        files = {}
        for disk in p["disks"]:
            receipt = archive["disks"][disk["key"]]
            file = self.spool / operation / disk["key"] / "disk.vmdk"
            actual = file_digest(file, receipt["size"], current)
            if (
                receipt.get("format") != "vmdk"
                or receipt.get("sector_comparison") != "passed"
                or receipt.get("virtual_bytes") != disk["virtual_bytes"]
                or receipt.get("guest_transformation") == "prepared_offline"
                and (
                    receipt.get("guest_target_platform") != "vmware"
                    or receipt.get("guest_firmware") != p["firmware"]
                )
                or any(actual[k] != receipt[k] for k in ("size", "sha256", "sha512"))
            ):
                raise NativeHeld("vmware_import_disk_changed")
            files[disk["key"] + ".vmdk"] = (file, receipt, disk["key"])
        result = call(
            "OvfManager",
            "OvfManager",
            "CreateImportSpec",
            {
                "ovfDescriptor": descriptor(p, archive["disks"]),
                "resourcePool": reference("ResourcePool", p["resource_pool_id"]),
                "datastore": reference("Datastore", p["datastore_id"]),
                "cisp": {
                    "entityName": p["name"],
                    "hostSystem": reference("HostSystem", p["host_id"]),
                    "diskProvisioning": "thin",
                    "networkMapping": [
                        {
                            "name": "quarantine-" + str(i),
                            "network": reference("Network", n["quarantine_network_id"]),
                        }
                        for i, n in enumerate(p["nics"])
                    ],
                },
            },
        )
        if (
            result.get("error")
            or result.get("warning")
            or result.get("importSpec", {}).get("_typeName") != "VirtualMachineImportSpec"
        ):
            raise NativeHeld("vmware_import_spec_unqualified")
        spec = result["importSpec"]
        hardware(spec["configSpec"], p, imported=False)
        spec["configSpec"]["annotation"] = "migration:" + b.fingerprint
        items = result.get("fileItem")
        if (
            not isinstance(items, list)
            or len(items) != len(files)
            or {i.get("path") for i in items} != set(files)
            or len({i.get("deviceId") for i in items}) != len(items)
            or any(
                type(i.get("create")) is not bool
                or i.get("size") != files[i["path"]][1]["size"]
                or i.get("cimType") != 17
                or i.get("compressionMethod") not in {None, ""}
                or i.get("chunkSize") not in {None, 0}
                for i in items
            )
        ):
            raise NativeHeld("vmware_import_file_map_changed")
        destination_scope(self.api, p, current)
        self.journal.record(
            b, "request_started", {"kind": "vmware_import", "payload_sha256": digest(spec)}
        )
        lease = moref(
            call(
                "ResourcePool",
                p["resource_pool_id"],
                "ImportVApp",
                {
                    "spec": spec,
                    "folder": reference("Folder", p["folder_id"]),
                    "host": reference("HostSystem", p["host_id"]),
                },
            ),
            "HttpNfcLease",
        )
        self.journal.record(b, "import_lease", {"lease_id": lease})
        while (state := call("HttpNfcLease", lease, "state")) == "initializing":
            time.sleep(0.1)
        if state != "ready":
            raise NativeHeld("vmware_import_lease_unconfirmed")
        info = call("HttpNfcLease", lease, "info")
        vm = moref(info.get("entity"), "VirtualMachine")
        self.journal.record(
            b,
            "request_accepted",
            {"kind": "server", "resource_key": "vm", "native_id": vm, "lease_id": lease},
        )
        urls = info.get("deviceUrl")
        if (
            not isinstance(urls, list)
            or len(urls) != len(items)
            or {u.get("importKey") for u in urls} != {i["deviceId"] for i in items}
            or type(info.get("leaseTimeout")) is not int
            or info["leaseTimeout"] < 15
        ):
            raise NativeHeld("vmware_import_lease_mapping_changed")
        targets = {u["importKey"]: self.uploader.destination(u.get("url"))[0] for u in urls}
        if len(set(targets.values())) != len(items):
            raise NativeHeld("vmware_import_lease_mapping_changed")
        heartbeat_at = 0.0

        def heartbeat() -> None:
            nonlocal heartbeat_at
            current()
            if time.monotonic() - heartbeat_at >= min(5, info["leaseTimeout"] / 3):
                call("HttpNfcLease", lease, "HttpNfcLeaseProgress", {"percent": 0})
                heartbeat_at = time.monotonic()

        for item in items:
            file, receipt, key = files[item["path"]]
            self.uploader.upload(
                targets[item["deviceId"]],
                file,
                receipt,
                item["create"],
                p["bytes_per_second"],
                heartbeat,
            )
            self.journal.record(b, "disk_transferred", {"resource_key": key, **receipt})
        call("HttpNfcLease", lease, "HttpNfcLeaseProgress", {"percent": 100})
        call("HttpNfcLease", lease, "HttpNfcLeaseComplete", {})
        if call("HttpNfcLease", lease, "state") != "done":
            raise NativeHeld("vmware_import_completion_unknown")


class VmwareDestinationObserver:
    def __init__(
        self,
        plan_file: Path,
        api: NativeJson,
        journal: ImportJournal,
        clock: Callable[[], int],
        current: Callable[[], None],
    ) -> None:
        self.plan_file, self.api, self.journal, self.clock, self.current = (
            plan_file,
            api,
            journal,
            clock,
            current,
        )

    def observe(self, b: NativeBinding, objects: dict[str, Any]) -> dict[str, Any]:
        self.current()
        p = validate(decode(protected_read(self.plan_file, 1048576)), b)
        destination_scope(self.api, p, self.current)
        if set(objects) != {"vm"} or objects["vm"].get("kind") != "server":
            raise NativeHeld("vmware_import_incomplete")
        vm = moref(reference("VirtualMachine", objects["vm"]["id"]), "VirtualMachine")
        lease = self.journal.import_lease(b)
        if self.api.request("GET", path(p, "HttpNfcLease", lease, "state"), self.current) != "done":
            raise NativeHeld("vmware_import_completion_unknown")
        config = self.api.request("GET", path(p, "VirtualMachine", vm, "config"), self.current)
        runtime = self.api.request("GET", path(p, "VirtualMachine", vm, "runtime"), self.current)
        parent = self.api.request("GET", path(p, "VirtualMachine", vm, "parent"), self.current)
        pool = self.api.request("GET", path(p, "VirtualMachine", vm, "resourcePool"), self.current)
        hardware(config, p, imported=True)
        if (
            runtime.get("powerState") != "poweredOff"
            or config.get("annotation") != "migration:" + b.fingerprint
            or moref(parent, "Folder") != p["folder_id"]
            or moref(pool, "ResourcePool") != p["resource_pool_id"]
            or set(self.journal.transfers(b)) != {d["key"] for d in p["disks"]}
        ):
            raise NativeHeld("vmware_import_scope_or_custody_changed")
        return {
            "binding_sha256": b.fingerprint,
            "observed_at": self.clock(),
            "independent": True,
            "outcome": "observed_present",
            "objects": objects,
            "observation_sha256": digest(config),
            "activation_authorized": False,
            "application_ready": False,
        }
