"""Cold Nova/Cinder capture into owned images, with no guest changes.

Image-backed root and Cinder disks have distinct native capture paths. A stopped
server and exact complete disk mapping are mandatory. Native submissions are
never replayed by this adapter; partial resource receipts remain in custody.
"""



import re
import time
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from lifecycle_worker.application.api_plan import shape
from lifecycle_worker.application.native import (
    NativeBinding,
    NativeHeld,
    NativeJournal,
    decode,
    digest,
    identity,
    native_identity,
    sha256,
)
from lifecycle_worker.infrastructure.migration_budget import seconds
from lifecycle_worker.infrastructure.native_files import protected_read
from lifecycle_worker.infrastructure.native_json import NativeJson
from lifecycle_worker.infrastructure.openstack_api import NativeWrites
from lifecycle_worker.infrastructure.openstack_source_contract import configuration


MIGRATION_API_CAPABILITIES = frozenset({"vm.disk.export"})


def validate_capture(p: dict[str, Any], binding: NativeBinding) -> dict[str, Any]:
    shape(
        p,
        {
            "schema_version",
            "kind",
            "method",
            "source_project_id",
            "source_vm_id",
            "source_profile_sha256",
            "server_sha256",
            "disks",
            "max_seconds",
        },
    )
    if (
        p["schema_version"] != 2
        or type(p["schema_version"]) is not int
        or p["kind"] != "openstack_capture"
        or p["method"] != "VM_COLD_EXPORT"
        or digest(p) != binding.operation_plan_sha256
        or not sha256(p["source_profile_sha256"])
        or not sha256(p["server_sha256"])
    ):
        raise NativeHeld("openstack_capture_plan_changed")
    identity(p["source_vm_id"])
    native_identity(p["source_project_id"])
    seconds(p)
    if not isinstance(p["disks"], list) or not 1 <= len(p["disks"]) <= 32:
        raise NativeHeld("openstack_capture_disks_invalid")
    keys, ids = set(), set()
    for disk in p["disks"]:
        shape(disk, {"key", "volume_id", "source_sha256", "virtual_bytes"})
        key = disk["key"]
        if (
            not isinstance(key, str)
            or re.fullmatch(r"[A-Za-z0-9_-]{1,80}", key) is None
            or key in keys
        ):
            raise NativeHeld("openstack_capture_disks_invalid")
        keys.add(key)
        if disk["volume_id"] in ids or not sha256(disk["source_sha256"]):
            raise NativeHeld("openstack_capture_disks_invalid")
        ids.add(disk["volume_id"])
        if disk["volume_id"] is not None:
            identity(disk["volume_id"])
        if type(disk["virtual_bytes"]) is not int or not 512 <= disk["virtual_bytes"] <= 2**46:
            raise NativeHeld("openstack_capture_disks_invalid")
    return p


def image_facts(document: Any, project: str, name: str) -> dict[str, Any]:
    if (
        not isinstance(document, dict)
        or document.get("owner") != project
        or document.get("name") != name
        or document.get("visibility") != "private"
        or document.get("status") != "active"
        or document.get("disk_format") not in {"raw", "qcow2", "vmdk"}
        or document.get("container_format") != "bare"
    ):
        raise NativeHeld("source_image_not_ready_or_owned")
    identity(document.get("id"))
    size, algorithm, checksum = (document.get(k) for k in ("size", "os_hash_algo", "os_hash_value"))
    if (
        type(size) is not int
        or not 0 < size <= 2**46
        or algorithm not in {"sha256", "sha512"}
        or not isinstance(checksum, str)
        or re.fullmatch(r"[a-f0-9]{" + str(64 if algorithm == "sha256" else 128) + "}", checksum)
        is None
    ):
        raise NativeHeld("source_image_checksum_required")
    return {
        "image_id": document["id"],
        "name": name,
        "format": document["disk_format"],
        "size": size,
        "checksum_algorithm": algorithm,
        "checksum": checksum,
    }


class OpenStackCapture:
    def __init__(
        self,
        plan_file: Path,
        compute: NativeJson,
        volume: NativeJson,
        image: NativeJson,
        authorization: NativeWrites,
        journal: NativeJournal,
        interval: float = 1,
    ) -> None:
        if not 0 <= interval <= 5:
            raise NativeHeld("invalid_native_poll_bound")
        self.plan_file, self.compute, self.volume, self.image = plan_file, compute, volume, image
        self.authorization, self.journal, self.interval = authorization, journal, interval

    def plan(self, binding: NativeBinding) -> dict[str, Any]:
        return validate_capture(decode(protected_read(self.plan_file, 1048576)), binding)

    def inspect(self, binding: NativeBinding) -> dict[str, Any]:
        return {
            "operation_plan_sha256": digest(self.plan(binding)),
            "native_write_authorized": False,
        }

    def execute(self, binding: NativeBinding, boundary: Callable[[], None]) -> None:
        p = self.plan(binding)
        deadline = time.monotonic() + seconds(p)
        self.authorization.authorize(replace(binding, project_id=p["source_project_id"]))
        for api in (self.compute, self.volume, self.image):
            api.expected_token_sha256 = self.authorization.subject_token_sha256

        def current() -> None:
            boundary()
            self.authorization.identity_check()
            if (
                time.monotonic() >= deadline
                or self.authorization.clock() >= self.authorization.credential_expires_at
            ):
                raise NativeHeld("openstack_capture_authority_expired")

        def server() -> dict[str, Any]:
            value = self.compute.request("GET", "/servers/" + p["source_vm_id"], current).get(
                "server", {}
            )
            if (
                value.get("id") != p["source_vm_id"]
                or value.get("tenant_id") != p["source_project_id"]
                or value.get("status") != "SHUTOFF"
                or digest(configuration("server", value)) != p["server_sha256"]
            ):
                raise NativeHeld("openstack_source_not_stopped_or_changed")
            attached = value.get("os-extended-volumes:volumes_attached", [])
            expected = {d["volume_id"] for d in p["disks"] if d["volume_id"] is not None}
            if (
                not isinstance(attached, list)
                or len(attached) != len(expected)
                or {a.get("id") for a in attached if isinstance(a, dict)} != expected
                or bool(value.get("image")) != any(d["volume_id"] is None for d in p["disks"])
            ):
                raise NativeHeld("openstack_source_disk_inventory_changed")
            return dict(value)

        def wait(
            api: NativeJson, path: str, field: str | None, allowed: set[str], ready: str
        ) -> dict[str, Any]:
            while True:
                current()
                result = api.request("GET", path, current)
                value = result.get(field, {}) if field else result
                if not isinstance(value, dict) or value.get("status") not in allowed | {ready}:
                    raise NativeHeld("openstack_capture_resource_failed")
                if value["status"] == ready:
                    return dict(value)
                time.sleep(self.interval)

        owned: list[dict[str, str]] = []
        captured = {}
        source = server()
        for disk in p["disks"]:
            current()
            key = disk["key"]
            name = "migration-" + binding.operation_id + "-" + key
            metadata = {
                "product_tenant_id": binding.tenant_id,
                "product_operation_id": binding.operation_id,
                "product_resource_id": binding.resource_id,
                "product_object_key": key,
            }
            if disk["volume_id"] is None:
                if (
                    digest({"image_id": source["image"]["id"], "flavor_id": source["flavor"]["id"]})
                    != disk["source_sha256"]
                ):
                    raise NativeHeld("openstack_source_root_changed")
                self.journal.record(
                    binding, "source_request_started", {"kind": "server_image", "resource_key": key}
                )
                document, headers = self.compute.request_with_headers(
                    "POST",
                    "/servers/" + p["source_vm_id"] + "/action",
                    current,
                    {"createImage": {"name": name, "metadata": metadata}},
                    202,
                )
                location = headers.get("location")
                if not isinstance(location, str):
                    raise NativeHeld("source_image_identity_unknown")
                returned = urlsplit(location)
                if returned.query or returned.fragment or returned.username or returned.password:
                    raise NativeHeld("source_image_identity_unknown")
                image_id = identity(returned.path.rstrip("/").rsplit("/", 1)[-1])
                # Only the identity is consumed. The response URL is never followed.
            else:
                original = self.volume.request("GET", "/volumes/" + disk["volume_id"], current).get(
                    "volume", {}
                )
                if (
                    original.get("id") != disk["volume_id"]
                    or original.get("encrypted") is not False
                    or original.get("multiattach") is not False
                    or digest(configuration("volume", original)) != disk["source_sha256"]
                    or original.get("status") != "in-use"
                    or len(original.get("attachments", [])) != 1
                    or original["attachments"][0].get("server_id") != p["source_vm_id"]
                    or type(original.get("size")) is not int
                    or original["size"] * 1024**3 != disk["virtual_bytes"]
                ):
                    raise NativeHeld("openstack_source_volume_changed")
                self.journal.record(
                    binding,
                    "source_request_started",
                    {"kind": "volume_snapshot", "resource_key": key},
                )
                snap = self.volume.request(
                    "POST",
                    "/snapshots",
                    current,
                    {
                        "snapshot": {
                            "volume_id": disk["volume_id"],
                            "force": True,
                            "name": name,
                            "metadata": metadata,
                        }
                    },
                    202,
                )
                snapshot_id = identity(snap.get("snapshot", {}).get("id"))
                owned.append({"kind": "snapshot", "id": snapshot_id, "resource_key": key})
                self.journal.record(binding, "source_object_created", owned[-1])
                ready = wait(
                    self.volume, "/snapshots/" + snapshot_id, "snapshot", {"creating"}, "available"
                )
                if ready.get("volume_id") != disk["volume_id"] or ready.get("metadata") != metadata:
                    raise NativeHeld("openstack_snapshot_ownership_changed")
                self.journal.record(
                    binding, "source_request_started", {"kind": "volume_copy", "resource_key": key}
                )
                copied = self.volume.request(
                    "POST",
                    "/volumes",
                    current,
                    {
                        "volume": {
                            "snapshot_id": snapshot_id,
                            "size": original["size"],
                            "name": name,
                            "metadata": metadata,
                        }
                    },
                    202,
                )
                copy_id = identity(copied.get("volume", {}).get("id"))
                if copy_id == disk["volume_id"]:
                    raise NativeHeld("openstack_copy_not_isolated")
                owned.append({"kind": "volume", "id": copy_id, "resource_key": key})
                self.journal.record(binding, "source_object_created", owned[-1])
                ready = wait(
                    self.volume,
                    "/volumes/" + copy_id,
                    "volume",
                    {"creating", "downloading"},
                    "available",
                )
                if (
                    ready.get("id") != copy_id
                    or ready.get("snapshot_id") != snapshot_id
                    or ready.get("metadata") != metadata
                    or ready.get("attachments") != []
                    or ready.get("encrypted") is not False
                ):
                    raise NativeHeld("openstack_copy_not_isolated")
                self.journal.record(
                    binding, "source_request_started", {"kind": "volume_image", "resource_key": key}
                )
                uploaded = self.volume.request(
                    "POST",
                    "/volumes/" + copy_id + "/action",
                    current,
                    {
                        "os-volume_upload_image": {
                            "image_name": name,
                            "force": False,
                            "disk_format": "raw",
                            "container_format": "bare",
                        }
                    },
                    202,
                )
                image_id = identity(uploaded.get("os-volume_upload_image", {}).get("image_id"))
            if any(o["kind"] == "image" and o["id"] == image_id for o in owned):
                raise NativeHeld("source_image_identity_reused")
            owned.append({"kind": "image", "id": image_id, "resource_key": key})
            self.journal.record(binding, "source_object_created", owned[-1])
            image = wait(
                self.image,
                "/images/" + image_id,
                None,
                {"queued", "saving", "uploading", "importing"},
                "active",
            )
            if image.get("id") != image_id:
                raise NativeHeld("source_image_identity_changed")
            captured[key] = image_facts(image, p["source_project_id"], name) | {
                "virtual_bytes": disk["virtual_bytes"]
            }
        server()
        self.journal.record(
            binding,
            "source_capture_bound",
            {
                "source_platform": "openstack",
                "source_vm_id": p["source_vm_id"],
                "source_project_id": p["source_project_id"],
                "source_profile_sha256": p["source_profile_sha256"],
                "server_sha256": p["server_sha256"],
                "consistency": "cold_powered_off",
                "disks": captured,
                "owned_objects": owned,
            },
        )
