"""Internal native API worker use case with independently resolved caller and tooling."""

from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

from lifecycle_worker.application.native import (
    NativeApiAdapter,
    NativeApiExecution,
    NativeBinding,
    NativeHeld,
    NativeJournal,
    NativeObserver,
    digest,
    identity,
)
from lifecycle_worker.application.native_authority import (
    GrantedNativeAuthority,
    NativeBoundaryClient,
)


class NativeRuntime(Protocol):
    def resolve(self, binding: NativeBinding) -> tuple[NativeApiAdapter, NativeObserver]:
        """Resolve protected plan artifacts and observer from independently commissioned custody."""
        ...


@runtime_checkable
class NativeArchiveProgress(Protocol):
    def archive_progress(self, binding: NativeBinding) -> dict[str, Any]: ...


class NativeApiEffect:
    def __init__(
        self,
        authority: NativeBoundaryClient,
        journal: NativeJournal,
        tooling: NativeRuntime,
        clock: Callable[[], int],
    ) -> None:
        self.authority, self.journal, self.tooling, self.clock = authority, journal, tooling, clock

    def execute(self, tenant: str, worker: str, grant: dict[str, Any]) -> dict[str, Any]:
        return self.run(tenant, worker, grant, continuation=False)

    def continue_transfer(self, tenant: str, worker: str, grant: dict[str, Any]) -> dict[str, Any]:
        return self.run(tenant, worker, grant, continuation=True)

    def progress(self, tenant: str, worker: str, grant: dict[str, Any]) -> dict[str, Any]:
        authority = GrantedNativeAuthority(grant, self.authority, self.clock)
        binding = authority.binding
        if (
            identity(tenant) != binding.tenant_id
            or identity(worker) != binding.executor_id
            or grant["stage"] != "export_copy"
            or not isinstance(self.journal, NativeArchiveProgress)
        ):
            raise NativeHeld("native_progress_scope_denied")
        authority.require_current(binding, "during_api_sequence")
        counters = self.journal.archive_progress(binding)
        authority.require_current(binding, "during_api_sequence")
        return {
            "grant_sha256": digest(grant),
            "binding_sha256": binding.fingerprint,
            "measured_at": self.clock(),
            "evidence_source": "worker_custody_journal",
            **counters,
        }

    def run(
        self, tenant: str, worker: str, grant: dict[str, Any], *, continuation: bool
    ) -> dict[str, Any]:
        authority = GrantedNativeAuthority(grant, self.authority, self.clock)
        binding = authority.binding
        if identity(tenant) != binding.tenant_id or identity(worker) != binding.executor_id:
            raise NativeHeld("native_worker_scope_denied")
        # Authorize before resolving protected artifacts as well as immediately before applying.
        authority.require_current(binding, "during_api_sequence" if continuation else "preflight")
        tool, observer = self.tooling.resolve(binding)
        execution = NativeApiExecution(authority, self.journal, tool, observer, self.clock)
        if continuation:
            execution.continue_transfer(binding)
        else:
            execution.execute(binding)
        # Native process output and provider details do not cross the control/history boundary.
        return {
            "grant_sha256": digest(authority.grant),
            "submitted": True,
            "readiness_established": False,
            "retry_authorized": False,
        }
