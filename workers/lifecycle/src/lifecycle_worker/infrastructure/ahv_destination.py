"""Native image URL import and powered-off AHV VM creation with durable task receipts."""

MIGRATION_API_CAPABILITIES = frozenset({"vm.disk.import"})

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from lifecycle_worker.application.ahv_plan import image_body, marker, validate, vm_body
from lifecycle_worker.application.native import (
    NativeBinding,
    NativeHeld,
    decode,
    digest,
    identity,
)
from lifecycle_worker.infrastructure.ahv_http import COLLECTIONS, AhvTransport, read
from lifecycle_worker.infrastructure.ahv_staging import AhvStaging
from lifecycle_worker.infrastructure.ahv_tasks import AhvJournal, completed, submit
from lifecycle_worker.infrastructure.image_conversion import file_digest
from lifecycle_worker.infrastructure.migration_custody import ArtifactCustody
from lifecycle_worker.infrastructure.native_files import protected_read


def owned(document: dict[str, Any], key: str, p: dict[str, Any], b: NativeBinding) -> None:
    project = document.get("projectExtId", document.get("project", {}).get("extId"))
    if document.get("project", {}).get("extId", project) != project:
        raise NativeHeld("ahv_object_scope_changed")
    if project != b.project_id or document.get("description") != marker(b):
        raise NativeHeld("ahv_object_scope_changed")
    if key == "vm" and document.get("cluster", {}).get("extId") != p["cluster_id"]:
        raise NativeHeld("ahv_object_cluster_changed")


def infrastructure(api: AhvTransport, p: dict[str, Any], boundary: Callable[[], None]) -> None:
    pc = read(api, "/api/prism/v4.3/config/domain-managers/" + p["prism_central_id"], boundary)
    cluster = read(api, "/api/clustermgmt/v4.3/config/clusters/" + p["cluster_id"], boundary)
    if (
        pc.get("extId") != p["prism_central_id"]
        or cluster.get("extId") != p["cluster_id"]
        or cluster.get("config", {}).get("isAvailable") is not True
        or "AHV" not in cluster.get("config", {}).get("hypervisorTypes", [])
    ):
        raise NativeHeld("ahv_cluster_unavailable")
    for key in {d["storage_container_id"] for d in p["disks"]}:
        row = read(api, "/api/clustermgmt/v4.3/config/storage-containers/" + key, boundary)
        if (
            row.get("extId") != key
            or row.get("clusterExtId") != p["cluster_id"]
            or row.get("isMarkedForRemoval") is not False
            or row.get("isInternal") is not False
        ):
            raise NativeHeld("ahv_container_changed")
    for key in {n[f] for n in p["nics"] for f in ("quarantine_subnet_id", "production_subnet_id")}:
        row = read(api, "/api/networking/v4.3/config/subnets/" + key, boundary)
        if row.get("extId") != key or (
            row.get("projectExtId") != p["project_id"] and key not in p["shared_resource_ids"]
        ):
            raise NativeHeld("ahv_subnet_changed")
    for key in p["category_ids"]:
        if read(api, "/api/prism/v4.3/config/categories/" + key, boundary).get("extId") != key:
            raise NativeHeld("ahv_category_changed")
    for key in p["policy_ids"]:
        row = read(api, "/api/microseg/v4.3/config/policies/" + key, boundary)
        if (
            row.get("extId") != key
            or row.get("state") != "ENFORCE"
            or (row.get("projectExtId") != p["project_id"] and key not in p["shared_resource_ids"])
        ):
            raise NativeHeld("ahv_policy_not_enforced")


class AhvDestination:
    def __init__(
        self,
        plan_file: Path,
        api: AhvTransport,
        journal: AhvJournal,
        custody: ArtifactCustody,
        staging: AhvStaging,
        interval: float = 1,
    ) -> None:
        if not 0 <= interval <= 5:
            raise NativeHeld("invalid_ahv_poll_interval")
        self.plan_file, self.api, self.journal = plan_file, api, journal
        self.custody, self.staging, self.interval = custody, staging, interval

    def plan(self, binding: NativeBinding) -> dict[str, Any]:
        return validate(decode(protected_read(self.plan_file, 1048576)), binding)

    def inspect(self, binding: NativeBinding) -> dict[str, Any]:
        return {
            "operation_plan_sha256": digest(self.plan(binding)),
            "native_write_authorized": False,
        }

    def execute(self, b: NativeBinding, boundary: Callable[[], None]) -> None:
        p = self.plan(b)
        deadline = time.monotonic() + p["max_seconds"]

        def current() -> None:
            boundary()
            if time.monotonic() >= deadline or digest(self.plan(b)) != b.operation_plan_sha256:
                raise NativeHeld("ahv_destination_deadline_or_plan_changed")

        if self.journal.resources(b) or self.journal.ahv_tasks(b):
            raise NativeHeld("ahv_attempt_requires_reconciliation")
        current()
        infrastructure(self.api, p, current)
        archive = self.custody.artifact(b, p["conversion_plan_sha256"], "conversion")
        operation = identity(archive["operation_id"])
        if operation == b.operation_id or set(archive["disks"]) != {d["key"] for d in p["disks"]}:
            raise NativeHeld("ahv_conversion_inventory_changed")
        inputs = []
        for disk in p["disks"]:
            receipt = archive["disks"][disk["key"]]
            if (
                receipt.get("format") != "raw"
                or receipt.get("sector_comparison") != "passed"
                or receipt.get("virtual_bytes") != disk["virtual_bytes"]
                or receipt.get("size") != disk["virtual_bytes"]
                or receipt.get("guest_transformation") == "prepared_offline"
                and (
                    receipt.get("guest_target_platform") != "ahv"
                    or receipt.get("guest_firmware") != p.get("firmware", "bios")
                )
            ):
                raise NativeHeld("ahv_converted_disk_changed")
            path = self.staging.spool / operation / disk["key"] / "disk.raw"
            hashes = file_digest(path, receipt["size"], current)
            if any(hashes[k] != receipt[k] for k in ("size", "sha256", "sha512")):
                raise NativeHeld("ahv_converted_disk_changed")
            inputs.append((disk, receipt, path))
        images = {}
        for disk, receipt, path in inputs:
            current()
            url, token = self.staging.grant(b, path, receipt)
            self.journal.record(
                b,
                "disk_transferred",
                {
                    "resource_key": disk["key"],
                    **{k: receipt[k] for k in ("size", "sha256", "sha512")},
                },
            )
            image_id = submit(
                self.api,
                self.journal,
                b,
                disk["key"],
                "image",
                image_body(p, disk, receipt, url, b),
                current,
                self.interval,
            )
            image = read(self.api, COLLECTIONS["image"] + "/" + image_id, current)
            verify_image(image, disk, receipt, p, b)
            images[disk["key"]] = image_id
            self.staging.revoke(token)
        submit(
            self.api, self.journal, b, "vm", "server", vm_body(p, images, b), current, self.interval
        )


def verify_image(
    row: dict[str, Any],
    disk: dict[str, Any],
    receipt: dict[str, Any],
    p: dict[str, Any],
    b: NativeBinding,
) -> None:
    owned(row, disk["key"], p, b)
    if (
        row.get("name") != p["name"] + "-" + disk["key"]
        or row.get("type") != "DISK_IMAGE"
        or row.get("isSharedWithAllProjects") is not False
        or row.get("sizeBytes") != receipt["size"]
        or row.get("checksum", {}).get("hexDigest") != receipt["sha256"]
        or set(row.get("clusterLocationExtIds", [])) != {p["cluster_id"]}
        or set(row.get("categoryExtIds", [])) != set(p["category_ids"])
    ):
        raise NativeHeld("ahv_image_readback_mismatch")


class AhvDestinationObserver:
    def __init__(
        self,
        plan_file: Path,
        api: AhvTransport,
        journal: AhvJournal,
        clock: Callable[[], int],
        observer_id: str,
        writer_id: str,
        current: Callable[[], None],
    ) -> None:
        if identity(observer_id) == identity(writer_id):
            raise NativeHeld("independent_ahv_observer_required")
        self.plan_file, self.api, self.journal, self.clock = plan_file, api, journal, clock
        self.current = current

    def observe(self, b: NativeBinding, objects: dict[str, Any]) -> dict[str, Any]:
        self.current()
        p = validate(decode(protected_read(self.plan_file, 1048576)), b)
        objects = dict(objects)
        tasks = self.journal.ahv_tasks(b)
        for key, task in tasks.items():
            native_id = completed(self.api, task, self.current)
            if native_id is None:
                raise NativeHeld("ahv_task_incomplete")
            if key in objects and objects[key]["id"] != native_id:
                raise NativeHeld("ahv_task_object_changed")
            objects[key] = {"kind": task["kind"], "id": native_id}
        if set(objects) != {"vm", *(d["key"] for d in p["disks"])}:
            raise NativeHeld("ahv_destination_incomplete")
        transfers = self.journal.transfers(b)
        if set(transfers) != {d["key"] for d in p["disks"]}:
            raise NativeHeld("ahv_image_custody_incomplete")
        images = {}
        for disk in p["disks"]:
            key = disk["key"]
            image_id = identity(objects[key]["id"])
            row = read(self.api, COLLECTIONS["image"] + "/" + image_id, self.current)
            if row.get("extId") != image_id:
                raise NativeHeld("ahv_image_identity_changed")
            verify_image(row, disk, transfers[key], p, b)
            images[key] = image_id
        vm_id = identity(objects["vm"]["id"])
        vm = read(self.api, COLLECTIONS["server"] + "/" + vm_id, self.current)
        owned(vm, "vm", p, b)
        expected = vm_body(p, images, b)
        if (
            vm.get("extId") != vm_id
            or any(
                vm.get(k) != expected[k]
                for k in (
                    "name",
                    "numSockets",
                    "numCoresPerSocket",
                    "numThreadsPerCore",
                    "memorySizeBytes",
                    "powerState",
                )
            )
            or any(vm.get("bootConfig", {}).get(k) != v for k, v in expected["bootConfig"].items())
            or {c.get("extId") for c in vm.get("categories", [])} != set(p["category_ids"])
            or len(vm.get("disks", [])) != len(p["disks"])
            or len(vm.get("nics", [])) != len(p["nics"])
        ):
            raise NativeHeld("ahv_vm_readback_mismatch")
        for actual, wanted in zip(vm["disks"], expected["disks"], strict=True):
            backing = actual.get("backingInfo", {})
            if (
                {k: actual.get("diskAddress", {}).get(k) for k in ("busType", "index")}
                != wanted["diskAddress"]
                or backing.get("diskSizeBytes") != wanted["backingInfo"]["diskSizeBytes"]
                or backing.get("dataSource", {}).get("reference", {}).get("imageExtId")
                != wanted["backingInfo"]["dataSource"]["reference"]["imageExtId"]
                or backing.get("storageContainer", {}).get("extId")
                != wanted["backingInfo"]["storageContainer"]["extId"]
            ):
                raise NativeHeld("ahv_disk_readback_mismatch")
        for actual, wanted in zip(vm["nics"], expected["nics"], strict=True):
            if (
                actual.get("backingInfo", {}).get("isConnected") is not False
                or actual.get("backingInfo", {}).get("model") != "VIRTIO"
                or actual.get("networkInfo", {}).get("subnet", {}).get("extId")
                != wanted["networkInfo"]["subnet"]["extId"]
            ):
                raise NativeHeld("ahv_nic_readback_mismatch")
        infrastructure(self.api, p, self.current)
        return {
            "binding_sha256": b.fingerprint,
            "observed_at": self.clock(),
            "independent": True,
            "outcome": "observed_present",
            "objects": objects,
            "observation_sha256": digest(vm),
            "disk_identities": [
                {"resource_key": disk["key"], "native_id": identity(actual.get("extId"))}
                for disk, actual in zip(p["disks"], vm["disks"], strict=True)
            ],
            "nic_identities": [
                {**nic, "native_id": identity(actual.get("extId"))}
                for nic, actual in zip(p["nics"], vm["nics"], strict=True)
            ],
            "activation_authorized": False,
            "application_ready": False,
        }
