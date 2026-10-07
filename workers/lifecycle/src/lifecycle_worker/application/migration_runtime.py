"""Explicit commissioned stage composition; no default adapter or automatic fallback.

The bootstrap owner supplies immutable operation artifacts and independent reader
implementations. Missing site integrations fail closed before an attempt is claimed.
"""

from lifecycle_worker.application.native import (
    NativeApiAdapter,
    NativeBinding,
    NativeHeld,
    NativeObserver,
    sha256,
)

MIGRATION_STAGES = frozenset(
    {
        "source_prepare",
        "capture",
        "restart_baseline_source",
        "export_copy",
        "convert_copy",
        "import_target",
        "transform_copy",
        "rehearsal_validate",
        "retain_rehearsal",
        "fence_source",
        "final_sync",
        "shutdown_source",
        "validate_target",
        "admit_writes",
        "verify_activation",
        "fence_target",
        "verify_no_divergence",
        "restore_source",
        "verify_source",
        "preserve_target",
        "recover_target",
        "verify_recovery",
        "reverse_sync",
        "verify_source_data",
        "remove_copy",
        "remove_snapshot",
        "verify_consolidation",
        "revoke_migration_access",
    }
)


class CommissionedMigrationRuntime:
    def __init__(self, artifacts: dict[str, tuple[NativeApiAdapter, NativeObserver]]) -> None:
        if not artifacts or not all(sha256(k) for k in artifacts):
            raise NativeHeld("invalid_migration_artifact_registry")
        self.artifacts = dict(artifacts)

    def resolve(self, binding: NativeBinding) -> tuple[NativeApiAdapter, NativeObserver]:
        try:
            return self.artifacts[binding.operation_plan_sha256]
        except KeyError:
            raise NativeHeld("migration_stage_not_commissioned") from None
