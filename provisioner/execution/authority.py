"""Execution authority.

This repository produces plans. It holds no authority to approve them, to mutate
a native platform or to activate a production service. Approval is a recorded
external fact bound to an exact plan digest — never a boolean in a request file.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from provisioner.domain.errors import ProvisioningError
from provisioner.domain.lifecycle import EXTERNAL_EVIDENCE_STAGES
from provisioner.domain.request import loads

APPROVAL_FORMAT = 'hosting-plan-approval/1'
EXECUTION_AUTHORITY = 'EXTERNAL_ONLY'
REPOSITORY_AUTHORITY = 'REPOSITORY_PLAN_ONLY'


@dataclass(frozen=True)
class Approval:
    """One recorded external approval of one immutable plan."""

    plan_digest: str
    approved_by: str
    authority_ref: str
    scope: str = 'plan'
    format: str = APPROVAL_FORMAT

    def to_dict(self) -> dict:
        return {'format': self.format, 'plan_digest': self.plan_digest,
                'approved_by': self.approved_by, 'authority_ref': self.authority_ref,
                'scope': self.scope}

APPROVAL_SET_FORMAT = 'hosting-plan-approval-set/1'


def load_approvals(path) -> tuple[Approval, ...]:
    """Read recorded approvals from a document produced outside this repository.

    The file is the record of an external decision. It is read, never written, and
    an approval that does not name an approver and an authority reference is refused.
    """

    target = Path(path)
    try:
        text = target.read_text(encoding='utf-8')
    except OSError as exc:
        raise ProvisioningError('AUTHORITY_REQUIRED', f'Unreadable approval record: {exc}',
                                path=str(target)) from exc
    document = loads(text, str(target))
    if not isinstance(document, dict):
        raise ProvisioningError('AUTHORITY_REQUIRED', 'An approval record must be a mapping',
                                path=str(target))
    rows = document.get('approvals')
    if not isinstance(rows, list) or not rows:
        raise ProvisioningError('AUTHORITY_REQUIRED',
                                'An approval record must list at least one approval',
                                path=str(target))
    allowed = {'plan_digest', 'approved_by', 'authority_ref', 'scope'}
    approvals: list[Approval] = []
    for row in rows:
        if not isinstance(row, dict) or set(row) - allowed:
            raise ProvisioningError('AUTHORITY_REQUIRED', 'Unknown approval field',
                                    path=str(target),
                                    details={'allowed': sorted(allowed)})
        if not {'plan_digest', 'approved_by', 'authority_ref'} <= set(row):
            raise ProvisioningError('AUTHORITY_REQUIRED',
                                    'An approval must cite a plan digest, an approver and an authority reference',
                                    path=str(target))
        approvals.append(Approval(plan_digest=row['plan_digest'],
                                  approved_by=row['approved_by'],
                                  authority_ref=row['authority_ref'],
                                  scope=row.get('scope', 'plan')))
    return tuple(approvals)

def require_approval(plan_digest: str, approvals) -> Approval:
    """Return the approval for this exact plan, or refuse execution."""
    for approval in approvals or ():
        if approval.plan_digest == plan_digest:
            if not approval.approved_by or not approval.authority_ref:
                raise ProvisioningError('AUTHORITY_REQUIRED',
                                        'An approval must name an approver and an authority reference',
                                        path='$.approval')
            return approval
    raise ProvisioningError(
        'AUTHORITY_REQUIRED',
        'No recorded approval cites this plan digest; execution is refused',
        path='$.approval',
        details={'plan_digest': plan_digest, 'authority': EXECUTION_AUTHORITY,
                 'approval_format': APPROVAL_FORMAT})

def require_stage(stage: str, produced: set[str]) -> None:
    """Refuse a stage whose external evidence has not been produced."""
    if stage not in EXTERNAL_EVIDENCE_STAGES:
        return
    if stage not in produced:
        raise ProvisioningError(
            'AUTHORITY_REQUIRED',
            f'Stage {stage!r} requires evidence produced outside this repository',
            path=f'$.stage.{stage}',
            details={'required_evidence': sorted(EXTERNAL_EVIDENCE_STAGES),
                     'produced': sorted(produced)})

def to_dict() -> dict:
    return {'format': APPROVAL_FORMAT, 'authority': EXECUTION_AUTHORITY,
            'repository_authority': REPOSITORY_AUTHORITY,
            'external_stages': sorted(EXTERNAL_EVIDENCE_STAGES),
            'limits': ['A plan is never an approval',
                       'Approval is bound to one immutable plan digest',
                       'Approval is not recorded in the request document']}