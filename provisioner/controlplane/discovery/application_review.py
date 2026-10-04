"""An independently signed application-definition decision, never write authority.

The existing assessment evidence owner verifies signatures and live enrollment.
This module owns only the exact immutable draft binding and its interpretation.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from provisioner.controlplane.authority.model import PlanScope
from .model import _digest, _id, _scope, _scope_json, _utc
from .trust import _keys, _time

APPLICATION_OWNER = 'APPLICATION_OWNER'
REVIEW_KIND = 'APPLICATION_REVIEW'
DECISIONS = frozenset({'ACCEPT_FOR_ASSESSMENT', 'REVOKE'})
MAX_REVIEW_AGE = timedelta(hours=1)

if TYPE_CHECKING:
    from .application_drafts import StoredApplicationDraft


def _sha(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


@dataclass(frozen=True, slots=True)
class ApplicationReviewDecision:
    environment_id: str
    scope: PlanScope
    application_group_id: str
    draft_revision: int
    draft_record_digest: str
    generation: int
    result_digest: str
    proposal_digest: str
    owner_id: str
    decision: str
    review_reference: str
    reviewed_at: datetime

    def binding_digest(self) -> str:
        return review_binding(self.environment_id, self.scope, self.application_group_id,
                              self.draft_revision, self.draft_record_digest)


def review_binding(environment_id: str, scope: PlanScope, application_group_id: str,
                   draft_revision: int, draft_record_digest: str) -> str:
    """One revision stream per immutable draft; revocations share that stream."""
    if (not _id(environment_id) or not _scope(scope) or not _id(application_group_id)
            or type(draft_revision) is not int or not 1 <= draft_revision <= 2**63-1
            or not _sha(draft_record_digest)):
        raise ValueError('An exact application draft binding is required')
    return _digest({'kind': REVIEW_KIND, 'environmentId': environment_id,
        'scope': _scope_json(scope), 'applicationGroupId': application_group_id,
        'draftRevision': draft_revision, 'draftRecordDigest': draft_record_digest})


def parse_review(payload: dict, *, issued_at: datetime, expires_at: datetime) -> ApplicationReviewDecision:
    body = _keys(payload, {'environmentId', 'scope', 'applicationGroupId', 'draftRevision',
        'draftRecordDigest', 'generation', 'resultDigest', 'proposalDigest', 'ownerId',
        'decision', 'reviewReference', 'reviewedAt'})
    raw_scope = _keys(body['scope'], {'organizationId', 'tenantId', 'locationId',
        'securityDomainId', 'endpointId', 'nativeScopeId', 'platformFamily'})
    scope = PlanScope.from_record(raw_scope)
    reviewed = _time(body['reviewedAt'])
    review_binding(body['environmentId'], scope, body['applicationGroupId'],
                   body['draftRevision'], body['draftRecordDigest'])
    if (type(body['generation']) is not int or not 1 <= body['generation'] <= 2**63-1
            or not _sha(body['resultDigest']) or not _sha(body['proposalDigest'])
            or not _id(body['ownerId']) or not _id(body['reviewReference'])
            or not isinstance(body['decision'], str) or body['decision'] not in DECISIONS
            or not _utc(issued_at) or not _utc(expires_at)
            or not reviewed <= issued_at < expires_at <= reviewed + MAX_REVIEW_AGE):
        raise ValueError('A bounded application review decision is required')
    return ApplicationReviewDecision(body['environmentId'], scope, body['applicationGroupId'],
        body['draftRevision'], body['draftRecordDigest'], body['generation'], body['resultDigest'],
        body['proposalDigest'], body['ownerId'], body['decision'], body['reviewReference'], reviewed)


def require_draft_binding(decision: ApplicationReviewDecision, stored: StoredApplicationDraft) -> None:
    """The enrolled signer must be the proposed owner, independent of the editor.

    A matching proposed owner does not itself enroll a signing key. Enrollment and
    signatures are checked independently by the existing evidence trust owner.
    """
    if (not isinstance(decision, ApplicationReviewDecision)
            or (decision.environment_id, decision.scope, decision.application_group_id,
                decision.draft_revision, decision.draft_record_digest, decision.generation,
                decision.result_digest, decision.proposal_digest) !=
               (stored.environment_id, stored.scope, stored.application_group_id,
                stored.revision, stored.record_digest, stored.generation,
                stored.result_digest, stored.proposal_digest)
            or decision.reviewed_at < stored.recorded_at
            or decision.owner_id != json.loads(stored.proposal_json)['draft']['ownerId']
            or decision.owner_id == stored.recorded_by):
        raise ValueError('Review does not bind an independently edited exact owner proposal')
