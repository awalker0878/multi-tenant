"""Resolve only this job's retained archive and convert each explicitly mapped disk."""

import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from lifecycle_worker.application.api_plan import shape
from lifecycle_worker.application.native import (
    NativeBinding,
    NativeHeld,
    NativeJournal,
    decode,
    digest,
    sha256,
)
from lifecycle_worker.infrastructure.image_conversion import CopyConverter
from lifecycle_worker.infrastructure.native_files import protected_read


class ArtifactCustody(Protocol):
    def artifact(self, binding: NativeBinding, plan_sha256: str, kind: str) -> dict[str, Any]: ...


class MigrationConversion:
    def __init__(
        self,
        plan_file: Path,
        converter: CopyConverter,
        journal: NativeJournal,
        custody: ArtifactCustody,
        spool: Path,
    ) -> None:
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
            },
        )
        if (
            type(p["schema_version"]) is not int
            or p["schema_version"] != 1
            or p["kind"] != "migration_copy_conversion"
            or digest(p) != binding.operation_plan_sha256
            or not sha256(p["export_plan_sha256"])
            or not sha256(p["artifact_sha256"])
        ):
            raise NativeHeld("conversion_plan_changed")
        if (
            type(p["max_seconds"]) is not int
            or not 1 <= p["max_seconds"] <= 600
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
                or d["target_format"] not in {"raw", "qcow2"}
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
        receipts = {}
        for d in p["disks"]:
            prior = archive["disks"][d["key"]]
            intent = {
                "source_sha256": prior["sha256"],
                "source_bytes": prior["size"],
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
                self.spool / operation_id / (d["key"] + ".vmdk"), output / d["key"], intent, current
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
