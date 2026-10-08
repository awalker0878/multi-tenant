"""Resolve only this job's retained archive and convert each explicitly mapped disk."""

import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from lifecycle_worker.application.api_plan import shape
from lifecycle_worker.application.native import (
    NativeBinding,
    NativeHeld,
    NativeJournal,
    decode,
    digest,
    sha256,
)
from lifecycle_worker.infrastructure.guest_preparation import GuestPreparation
from lifecycle_worker.infrastructure.image_conversion import CopyConverter
from lifecycle_worker.infrastructure.migration_budget import seconds
from lifecycle_worker.infrastructure.migration_custody import ArtifactCustody
from lifecycle_worker.infrastructure.native_files import protected_read, sync_directory


class MigrationConversion:
    def __init__(
        self,
        plan_file: Path,
        converter: CopyConverter,
        journal: NativeJournal,
        custody: ArtifactCustody,
        spool: Path,
        guest: GuestPreparation | None = None,
    ) -> None:
        self.guest = guest
        self.plan_file, self.converter, self.journal, self.custody, self.spool = (
            plan_file,
            converter,
            journal,
            custody,
            spool,
        )

    def plan(self, binding: NativeBinding) -> dict[str, Any]:
        p = decode(protected_read(self.plan_file, 1048576))
        shape(
            p,
            {
                "schema_version",
                "kind",
                "export_plan_sha256",
                "artifact_sha256",
                "disks",
                "max_seconds",
                "bytes_per_second",
            }
            | ({"guest_profile"} if p.get("schema_version") == 4 else set()),
        )
        if (
            type(p["schema_version"]) is not int
            or p["schema_version"] not in {1, 2, 3, 4}
            or p["kind"] != "migration_copy_conversion"
            or digest(p) != binding.operation_plan_sha256
            or not sha256(p["export_plan_sha256"])
            or not sha256(p["artifact_sha256"])
        ):
            raise NativeHeld("conversion_plan_changed")
        if (
            type(p["max_seconds"]) is not int
            or p["max_seconds"] != seconds(p)
            or type(p["bytes_per_second"]) is not int
            or not 65536 <= p["bytes_per_second"] <= 2**34
        ):
            raise NativeHeld("conversion_budget_invalid")
        if not isinstance(p["disks"], list) or not 1 <= len(p["disks"]) <= 32:
            raise NativeHeld("conversion_inventory_invalid")
        keys = set()
        for d in p["disks"]:
            shape(d, {"key", "virtual_bytes", "target_format", "max_output_bytes"})
            if (
                not isinstance(d["key"], str)
                or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", d["key"])
                or d["key"] in keys
                or d["target_format"]
                not in ({"raw", "qcow2", "vmdk"} if p["schema_version"] >= 3 else {"raw", "qcow2"})
            ):
                raise NativeHeld("conversion_mapping_invalid")
            keys.add(d["key"])
            for k in ("virtual_bytes", "max_output_bytes"):
                if type(d[k]) is not int or not 512 <= d[k] <= 2**46:
                    raise NativeHeld("conversion_budget_invalid")
        if (
            not self.spool.is_absolute()
            or not self.spool.is_dir()
            or any(q.is_symlink() for q in (self.spool, *self.spool.parents))
            or self.spool.stat().st_mode & 0o077
        ):
            raise NativeHeld("private_native_spool_required")
        if p["schema_version"] == 4:
            if self.guest is None:
                raise NativeHeld("guest_preparation_runtime_required")
            self.guest.validate(p["guest_profile"])
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
                raise NativeHeld("conversion_deadline")
            boundary()

        current()
        archive = self.custody.artifact(binding, p["export_plan_sha256"], "archive")
        from lifecycle_worker.application.native import identity

        operation_id = identity(archive["operation_id"])
        if operation_id == binding.operation_id or set(archive["disks"]) != {
            d["key"] for d in p["disks"]
        }:
            raise NativeHeld("conversion_source_mapping_changed")
        output = self.spool / binding.operation_id
        output.mkdir(mode=0o700)
        sync_directory(self.spool)
        prepared: dict[str, dict[str, Any]] = {}
        preparation: dict[str, Any] = {}
        if p["schema_version"] == 4:
            assert self.guest is not None
            directory = output / "preparation"
            directory.mkdir(mode=0o700)
            for d in p["disks"]:
                prior = archive["disks"][d["key"]]
                fmt = prior.get("format", "vmdk")
                prepared[d["key"]] = self.converter.convert(
                    self.spool / operation_id / (d["key"] + "." + fmt),
                    directory / d["key"],
                    {
                        "source_sha256": prior["sha256"],
                        "source_bytes": prior["size"],
                        "source_format": fmt,
                        "virtual_bytes": d["virtual_bytes"],
                        "target_format": "raw",
                        "max_output_bytes": d["virtual_bytes"],
                        **{k: p[k] for k in ("max_seconds", "bytes_per_second", "artifact_sha256")},
                    },
                    current,
                )
            preparation = self.guest.prepare(
                directory, prepared, p["guest_profile"], deadline, current
            )
            self.journal.record(binding, "guest_copy_prepared", preparation)
        receipts = {}
        for d in p["disks"]:
            prior = archive["disks"][d["key"]]
            source = self.spool / operation_id / (d["key"] + "." + prior.get("format", "vmdk"))
            if preparation:
                prior = preparation["disks"][d["key"]] | {"format": "raw"}
                source = output / "preparation" / d["key"] / "disk.raw"
            source_format = prior.get("format", "vmdk")
            if source_format not in {"vmdk", "qcow2", "raw"} or (
                source_format != "vmdk" and p["schema_version"] < 3
            ):
                raise NativeHeld("conversion_source_format_unqualified")
            intent = {
                "source_sha256": prior["sha256"],
                "source_bytes": prior["size"],
                **({"source_format": source_format} if p["schema_version"] >= 3 else {}),
                **{k: d[k] for k in ("virtual_bytes", "target_format", "max_output_bytes")},
                **{k: p[k] for k in ("max_seconds", "bytes_per_second", "artifact_sha256")},
            }
            self.journal.record(
                binding,
                "conversion_started",
                {
                    "resource_key": d["key"],
                    "intent_sha256": digest(intent),
                    "source_operation_id": operation_id,
                },
            )
            result = self.converter.convert(
                source,
                output / d["key"],
                intent,
                current,
            )
            if preparation:
                result.update(
                    guest_transformation="prepared_offline",
                    guest_profile_sha256=digest(p["guest_profile"]),
                    guest_target_platform=p["guest_profile"]["target_platform"],
                    guest_firmware=p["guest_profile"]["firmware"],
                    preparation_sha256=digest(preparation),
                    original_source_sha256=archive["disks"][d["key"]]["sha256"],
                )
            receipts[d["key"]] = result
            self.journal.record(
                binding, "conversion_observed", {"resource_key": d["key"], **result}
            )
        self.journal.record(
            binding,
            "conversion_complete",
            {"disks_sha256": digest(receipts), "source_operation_id": operation_id},
        )
