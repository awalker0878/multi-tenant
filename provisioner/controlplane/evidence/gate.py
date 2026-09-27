"""Fail-closed signed evidence and audit lag guard for product mutations."""
from __future__ import annotations

from provisioner.controlplane.persistence import TenantContext
from .audit import AuditCheckpointRepository
from .repository import EvidenceRepository


class EvidenceHold(RuntimeError):
    """Signed evidence, retention or allowed checkpoint lag cannot be proven."""


class EvidenceMutationGate:
    def __init__(self, audit: AuditCheckpointRepository, evidence: EvidenceRepository,
                 *, max_unanchored_count: int):
        if type(max_unanchored_count) is not int or max_unanchored_count < 0:
            raise ValueError('Maximum unanchored suffix must be nonnegative')
        self.audit = audit
        self.evidence = evidence
        self.max_unanchored_count = max_unanchored_count

    def require(self, context: TenantContext) -> None:
        try:
            audit = self.audit.verify(context)
            evidence = self.evidence.verify(context)
            if (audit.unanchored_count > self.max_unanchored_count or
                    evidence.unanchored_count > self.max_unanchored_count):
                raise EvidenceHold('Independent checkpoint lag exceeds site policy')
        except EvidenceHold:
            raise
        except Exception as exc:
            raise EvidenceHold('Signed evidence is unavailable or inconsistent') from exc

    def checkpoint(self, context: TenantContext) -> None:
        try:
            self.evidence.checkpoint(context)
            self.audit.checkpoint(context)
            self.require(context)
        except EvidenceHold:
            raise
        except Exception as exc:
            raise EvidenceHold('Independent checkpoint could not advance') from exc
