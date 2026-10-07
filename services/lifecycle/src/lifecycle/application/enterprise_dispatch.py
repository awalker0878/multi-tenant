"""Durable enterprise dispatch; lost submit responses retain claims and cannot retry."""

from collections.abc import Callable
from typing import Any, Protocol

from lifecycle.application.enterprise import Enterprise


class EnterpriseEffects(Protocol):
    def execute(self, claim: dict[str, Any], boundary: Callable[[], None]) -> None: ...


class EnterpriseDispatcher:
    def __init__(self, enterprise: Enterprise, effects: EnterpriseEffects) -> None:
        self.enterprise, self.effects = enterprise, effects

    def tick(self) -> dict[str, Any] | None:
        claim = self.enterprise.claim()
        if claim is None:
            return None

        def boundary() -> None:
            self.enterprise.boundary(claim["tenant_id"], claim["operation_id"], claim["lease"])

        try:
            boundary()
            self.effects.execute(claim, boundary)
        except Exception:
            # The durable active claim retains all reservations. A restarted dispatcher
            # cannot resubmit it; only the independent observer may settle its outcome.
            return {"operation_id": claim["operation_id"], "state": "reconciliation_required"}
        return self.enterprise.reconcile(claim["tenant_id"], claim["operation_id"], claim["lease"])
