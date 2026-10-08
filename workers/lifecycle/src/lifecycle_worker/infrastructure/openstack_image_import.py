"""Explicit Glance-direct import from this job's completed conversion receipts.

Cinder/Nova consume the planned image UUIDs through the existing OpenStack create
adapter. This adapter does not change route when image staging/import fails.
"""

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

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
from lifecycle_worker.infrastructure.migration_budget import seconds
from lifecycle_worker.infrastructure.migration_custody import ArtifactCustody
from lifecycle_worker.infrastructure.native_files import protected_read
from lifecycle_worker.infrastructure.openstack_image_transport import GlanceImport


class OpenStackImageImport:
    def __init__(
        self,
        plan_file: Path,
        destination: GlanceImport,
        journal: NativeJournal,
        custody: ArtifactCustody,
        spool: Path,
    ) -> None:
        self.plan_file, self.destination, self.journal, self.custody, self.spool = (
            plan_file,
            destination,
            journal,
            custody,
            spool,
        )

    def plan(self, binding: NativeBinding) -> dict[str, Any]:
        p = decode(protected_read(self.plan_file, 1048576))
        shape(
            p, {"schema_version", "kind", "conversion_plan_sha256", "route", "disks", "max_seconds"}
        )
        if (
            type(p["schema_version"]) is not int
            or p["schema_version"] not in {1, 2}
            or p["kind"] != "migration_image_import"
            or p["route"] != "glance-direct"
            or not sha256(p["conversion_plan_sha256"])
            or digest(p) != binding.operation_plan_sha256
        ):
            raise NativeHeld("migration_import_plan_changed")
        if type(p["max_seconds"]) is not int or p["max_seconds"] != seconds(p):
            raise NativeHeld("migration_import_deadline_invalid")
        if not isinstance(p["disks"], list) or not 1 <= len(p["disks"]) <= 32:
            raise NativeHeld("migration_import_disks_invalid")
        keys, images = set(), set()
        import re

        for disk in p["disks"]:
            shape(
                disk,
                {
                    "key",
                    "image_id",
                    "name",
                    "disk_format",
                    "hw_firmware_type",
                    "hw_disk_bus",
                    "virtual_bytes",
                },
            )
            name(disk["name"])
            identity(disk["image_id"])
            if (
                not isinstance(disk["key"], str)
                or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", disk["key"])
                or disk["key"] in keys
                or disk["image_id"] in images
                or disk["disk_format"] not in {"raw", "qcow2"}
                or disk["hw_firmware_type"] not in {"bios", "uefi"}
                or disk["hw_disk_bus"] not in {"virtio", "scsi", "ide"}
                or type(disk["virtual_bytes"]) is not int
                or not 512 <= disk["virtual_bytes"] <= 2**46
            ):
                raise NativeHeld("migration_import_mapping_invalid")
            keys.add(disk["key"])
            images.add(disk["image_id"])
        if (
            not self.spool.is_absolute()
            or not self.spool.is_dir()
            or any(q.is_symlink() for q in (self.spool, *self.spool.parents))
            or self.spool.stat().st_mode & 0o077
        ):
            raise NativeHeld("private_native_spool_required")
        return p

    def inspect(self, binding: NativeBinding) -> dict[str, Any]:
        return {
            "operation_plan_sha256": digest(self.plan(binding)),
            "native_write_authorized": False,
        }

    def execute(self, binding: NativeBinding, boundary: Callable[[], None]) -> None:
        p = self.plan(binding)
        deadline = time.monotonic() + p["max_seconds"]

        def current() -> None:
            if time.monotonic() >= deadline:
                raise NativeHeld("migration_import_deadline")
            boundary()

        current()
        archive = self.custody.artifact(binding, p["conversion_plan_sha256"], "conversion")
        operation = identity(archive["operation_id"])
        if operation == binding.operation_id or set(archive["disks"]) != {
            d["key"] for d in p["disks"]
        }:
            raise NativeHeld("migration_import_inventory_changed")
        # Validate the complete dataset before submitting the first image.
        inputs = []
        for disk in p["disks"]:
            receipt = archive["disks"][disk["key"]]
            if (
                receipt.get("format") != disk["disk_format"]
                or receipt.get("virtual_bytes") != disk["virtual_bytes"]
                or receipt.get("sector_comparison") != "passed"
                or type(receipt.get("size")) is not int
                or not 0 < receipt["size"] <= 2**46
            ):
                raise NativeHeld("migration_import_artifact_changed")
            if receipt.get("guest_transformation") == "prepared_offline" and (
                receipt.get("guest_target_platform") != "openstack"
                or receipt.get("guest_firmware")
                != {"bios": "bios", "uefi": "efi"}[disk["hw_firmware_type"]]
            ):
                raise NativeHeld("migration_import_guest_profile_changed")
            path = self.spool / operation / disk["key"] / ("disk." + disk["disk_format"])
            observed = file_digest(path, receipt["size"], current)
            if any(observed[k] != receipt[k] for k in ("size", "sha256", "sha512")):
                raise NativeHeld("migration_import_artifact_changed")
            self.destination.preflight(binding, current, disk["disk_format"])
            inputs.append((disk, receipt, path))
        for disk, receipt, path in inputs:
            self.journal.record(
                binding,
                "disk_transferred",
                {
                    "resource_key": disk["key"],
                    **{k: receipt[k] for k in ("size", "sha256", "sha512")},
                },
            )
            self.journal.record(
                binding,
                "request_started",
                {"resource_key": disk["key"], "kind": "image", "payload_sha256": digest(disk)},
            )
            image = self.destination.create(binding, disk, current)
            self.journal.record(
                binding,
                "request_accepted",
                {
                    "resource_key": disk["key"],
                    "kind": "image",
                    "native_id": disk["image_id"],
                    "response_sha256": digest(image),
                },
            )
            # The download/import path is private custody; no payload enters Lifecycle or Console.
            import os

            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(fd, "rb") as stream:
                self.destination.stage(binding, disk, stream, receipt, current)
            self.destination.finish(binding, disk, receipt, current)
            self.journal.record(
                binding,
                "poll_observed",
                {"resource_key": disk["key"], "native_id": disk["image_id"], "status": "active"},
            )
