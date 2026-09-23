"""Activation gating.

Activation is refused unless conformance is complete and separate production
authorization exists. The refusal is the feature: a repository that can activate
its own work has no separation of duties.
"""
from __future__ import annotations

from provisioner.conformance import report as conformance_report
from provisioner.domain.errors import ProvisioningError
from provisioner.execution import authority

ACTIVATION_FORMAT = 'hosting-activation-decision/1'


def require_conformant(plan, observations=(), authorization=None, capacity=None,
                       addresses=None) -> dict:
    """Refuse activation unless every mandatory check is satisfied.

    `capacity` and `addresses` are the reconciled owner readings the transport holds,
    if any. They are passed through so a caller that has the owners' answers is judged
    on them rather than on their absence; a caller that has none is refused by the
    checks that stay PENDING, which is the point.
    """
    report = conformance_report.build(plan, observations, authorization,
                                      capacity=capacity, addresses=addresses)
    if not report['ready']:
        raise ProvisioningError(
            'ACTIVATION_REFUSED',
            f'Conformance is {report["status"]}; activation is refused',
            path='$.conformance',
            details={'failed': report['failed'], 'pending': report['pending'],
                     'blocking': report['blocking']})
    if authorization is None:
        raise ProvisioningError(
            'ACTIVATION_REFUSED',
            'No separate production authorization was supplied',
            path='$.authorization',
            details={'authority': authority.EXECUTION_AUTHORITY})
    return {'format': ACTIVATION_FORMAT, 'status': 'AUTHORIZED_BY_EXTERNAL_RECORD',
            'subject': report['subject'], 'authorization': authorization.to_dict(),
            'conformance': report['status'],
            'limits': ['Activation is performed by the owning authority, not by this repository']}


def to_dict(plan, observations=(), authorization=None, capacity=None,
            addresses=None) -> dict:
    report = conformance_report.build(plan, observations, authorization,
                                      capacity=capacity, addresses=addresses)
    return {'format': ACTIVATION_FORMAT,
            'status': 'ELIGIBLE' if report['ready'] and authorization else 'HELD',
            'conformance': report['status'], 'blocking': report['blocking'],
            'authorization': authorization.to_dict() if authorization else None,
            'native_contact': False,
            'limits': ['Activation requires complete conformance and separate authorization']}