"""Internal saved-plan worker use case with independently resolved caller and tooling."""

from collections.abc import Callable
from typing import Any, Protocol

from lifecycle_worker.application.native import (
    NativeBinding,
    NativeHeld,
    NativeJournal,
    NativeObserver,
    SavedPlanExecution,
    SavedPlanTool,
    digest,
    identity,
)
from lifecycle_worker.application.native_authority import (
    GrantedNativeAuthority,
    NativeBoundaryClient,
)


class NativeTooling(Protocol):
    def resolve(self, binding: NativeBinding) -> tuple[SavedPlanTool, NativeObserver]:
        """Resolve protected plan artifacts and observer from independently commissioned custody."""
        ...


class NativeSavedPlanEffect:
    def __init__(
        self,
        authority: NativeBoundaryClient,
        journal: NativeJournal,
        tooling: NativeTooling,
        clock: Callable[[], int],
    ) -> None:
        self.authority, self.journal, self.tooling, self.clock = authority, journal, tooling, clock

    def execute(self, tenant: str, worker: str, grant: dict[str, Any]) -> dict[str, Any]:
        authority = GrantedNativeAuthority(grant, self.authority, self.clock)
        binding = authority.binding
        if identity(tenant) != binding.tenant_id or identity(worker) != binding.executor_id:
            raise NativeHeld("native_worker_scope_denied")
        # Authorize before resolving protected artifacts as well as immediately before applying.
        authority.require_current(binding, "preflight")
        tool, observer = self.tooling.resolve(binding)
        SavedPlanExecution(authority, self.journal, tool, observer, self.clock).execute(binding)
        # Native process output and provider details do not cross the control/history boundary.
        return {
            "grant_sha256": digest(authority.grant),
            "submitted": True,
            "readiness_established": False,
            "retry_authorized": False,
        }
