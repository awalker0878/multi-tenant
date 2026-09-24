"""Shared clean-source binding for delivery handoffs."""
from __future__ import annotations

from provisioner import repository
from provisioner.domain.errors import ProvisioningError
from provisioner.execution import handoff

NO_CHECKOUT = 'BLOCKED_NO_CURRENT_CHECKOUT'


def bind(requested: str | None, *, instruction: str) -> tuple[str, dict]:
    """Bind one exact clean source commit before a delivery graph is emitted."""
    source = repository.source_commit()
    commit = source['commit']
    if requested is not None:
        if not handoff.SOURCE_COMMIT.match(requested):
            raise ProvisioningError(
                'SCHEMA_VALIDATION_FAILED',
                'A delivery handoff binds one exact clean source commit',
                path='$.apply', details={'source_commit': requested})
        if source['status'] != NO_CHECKOUT and requested != commit:
            raise ProvisioningError(
                'ARTIFACT_INTEGRITY_FAILED',
                'The declared source commit is not the commit under review',
                path='$.apply',
                details={'source_commit': requested, 'checkout_commit': commit})
        return requested, source
    if source['status'] != 'HASHES_MATCH':
        raise ProvisioningError(
            'ARTIFACT_INTEGRITY_FAILED',
            'A delivery handoff binds one exact clean source commit',
            path='$.apply',
            details={'status': source['status'], 'issues': source['issues'],
                     'instruction': instruction})
    return commit, source
