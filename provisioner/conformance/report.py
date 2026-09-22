"""Conformance reporting.

The report is the artifact a reviewer reads before activation. It states the
outcome, the blocking checks and — explicitly — what it does not prove.
"""
from __future__ import annotations

from provisioner.conformance import checks as check_set

REPORT_FORMAT = 'hosting-conformance-report/1'

READY = 'CONFORMANT'
BLOCKED = 'BLOCKED_ON_EXTERNAL_EVIDENCE'
FAILED = 'FAILED'
STATUSES = (READY, BLOCKED, FAILED)


def build(plan, observations=(), authorization=None, subject: str | None = None) -> dict:
    """Summarise every check into one conformance report."""
    results = check_set.run(plan, observations, authorization)
    failed = sorted(c.name for c in results if c.status == check_set.FAIL)
    pending = sorted(c.name for c in results if c.status == check_set.PENDING)
    blocking = sorted(c.name for c in results if c.mandatory and not c.satisfied)

    if failed:
        status = FAILED
    elif pending:
        status = BLOCKED
    else:
        status = READY

    return {'format': REPORT_FORMAT, 'status': status,
            'subject': subject or f'{plan.request.tenant}/{plan.request.wsd}',
            'plan_digest': plan.digest,
            'request_digest': plan.request.digest,
            'checks': [c.to_dict() for c in results],
            'failed': failed, 'pending': pending, 'blocking': blocking,
            'ready': status == READY,
            'native_contact': False,
            'limits': ['This report is repository-side conformance evidence',
                       'A blocking check prevents activation, never planning',
                       'Unknown required evidence is never reported as PASS']}


def to_dict(plan, observations=(), authorization=None) -> dict:
    return build(plan, observations, authorization)