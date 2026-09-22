"""Evidence records produced by repository-side provisioning.

An evidence record binds an artifact to the request digest it came from, to the
generation it belongs to, and states what it does *not* prove. It is never a native
acceptance result.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from provisioner.domain.generation import require_generation
from provisioner.domain.request import digest

EVIDENCE_FORMAT = 'hosting-provisioning-evidence/1'

KINDS = ('request', 'validation', 'resolution', 'placement', 'allocation',
         'compilation', 'generation', 'plan', 'conformance', 'observation')


@dataclass(frozen=True)
class EvidenceRecord:
    kind: str
    subject: str
    request_digest: str
    artifact_digest: str
    stage: str
    status: str
    generation: int = 1
    authority: str = 'REPOSITORY_SIDE_ONLY'
    details: dict = field(default_factory=dict)
    limits: tuple[str, ...] = ()
    format: str = EVIDENCE_FORMAT
    digest: str = ''

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(f'Unknown evidence kind: {self.kind}')
        require_generation(self.generation)

    def to_dict(self) -> dict:
        return {'format': self.format, 'kind': self.kind, 'subject': self.subject,
                'generation': self.generation,
                'request_digest': self.request_digest, 'artifact_digest': self.artifact_digest,
                'stage': self.stage, 'status': self.status, 'authority': self.authority,
                'details': dict(self.details), 'limits': list(self.limits),
                'digest': self.digest}


def record(kind: str, subject: str, request_digest: str, artifact_digest: str, stage: str,
           status: str, details: dict | None = None, limits=(), generation: int = 1,
           authority='REPOSITORY_SIDE_ONLY'):
    row = EvidenceRecord(kind=kind, subject=subject, request_digest=request_digest,
                         artifact_digest=artifact_digest, stage=stage, status=status,
                         generation=require_generation(generation),
                         authority=authority, details=dict(details or {}),
                         limits=tuple(limits))
    body = row.to_dict()
    body.pop('digest')
    return EvidenceRecord(**{**row.__dict__, 'digest': digest(body)})