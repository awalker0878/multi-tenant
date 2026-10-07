"""Resolve the existing protected tooling packet; it supplies no effect authority."""

from collections.abc import Callable
from pathlib import Path

from lifecycle_worker.application.native import (
    NativeBinding,
    NativeHeld,
    NativeObserver,
    SavedPlanTool,
    decode,
)
from lifecycle_worker.infrastructure.native_files import protected_read
from lifecycle_worker.infrastructure.native_http import NativeEndpoint, NativeReads
from lifecycle_worker.infrastructure.openstack_readback import OpenStackReadback
from lifecycle_worker.infrastructure.terraform import TerraformSavedPlan


class MountedNativeTooling:
    def __init__(self, runtime_file: Path, clock: Callable[[], int]) -> None:
        self.runtime_file, self.clock = runtime_file, clock

    def resolve(self, binding: NativeBinding) -> tuple[SavedPlanTool, NativeObserver]:
        config = decode(protected_read(self.runtime_file, 65536))
        if set(config) != {
            "terraform_executable",
            "bundle_root",
            "environment",
            "credential_files",
            "observer",
        }:
            raise NativeHeld("invalid_native_runtime")
        tool = TerraformSavedPlan(
            Path(config["terraform_executable"]),
            Path(config["bundle_root"]),
            config["environment"],
            {k: Path(v) for k, v in config["credential_files"].items()},
        )
        observer = config["observer"]
        if set(observer) != {"endpoints", "user_id", "writer_user_id"}:
            raise NativeHeld("invalid_native_observer")
        reads = NativeReads(
            {
                name: NativeEndpoint(
                    row["base_url"], row["address"], Path(row["ca_file"]), Path(row["token_file"])
                )
                for name, row in observer["endpoints"].items()
            }
        )
        independent = OpenStackReadback(
            reads,
            tool.verified(binding)["resources"],
            observer["user_id"],
            observer["writer_user_id"],
            self.clock,
        )
        return tool, independent
