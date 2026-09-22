"""Lifecycle vocabulary shared by the request model and the execution boundary."""
from __future__ import annotations

from provisioner.domain.errors import ProvisioningError

LIFECYCLES = ('development', 'test', 'qualification', 'production', 'recovery')
ENVIRONMENT_PROFILES = ('development', 'test', 'qualification', 'production', 'recovery')

# Ordered pipeline stages. A stage may only be reported when every earlier stage
# produced its artifact for the same request digest.
STAGES = ('request', 'normalized', 'validated', 'resolved', 'placed', 'allocated',
          'compiled', 'planned', 'approved', 'executed', 'observed', 'verified',
          'activated')

ACTIONS = ('create', 'update', 'contain', 'recover', 'retire')

# Stages this repository is permitted to reach without external evidence.
REPOSITORY_STAGES = ('request', 'normalized', 'validated', 'resolved', 'placed',
                     'allocated', 'compiled', 'planned')

# Stages that require evidence produced outside this repository.
EXTERNAL_EVIDENCE_STAGES = ('approved', 'executed', 'observed', 'verified', 'activated')


def require_lifecycle(value: str) -> str:
    if value not in LIFECYCLES:
        raise ProvisioningError('SCHEMA_VALIDATION_FAILED',
                                f'Unknown lifecycle: {value!r}',
                                path='$.spec.environment',
                                details={'allowed': list(LIFECYCLES)})
    return value


def stage_index(stage: str) -> int:
    if stage not in STAGES:
        raise ValueError(f'Unknown lifecycle stage: {stage}')
    return STAGES.index(stage)


def requires_external_evidence(stage: str) -> bool:
    return stage in EXTERNAL_EVIDENCE_STAGES