"""Read current independently signed decisions against immutable application drafts.

This composes the existing draft, discovery and signed-evidence owners. It is not
an approval writer, owner-enrollment service or native migration admission path.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Callable

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.persistence.store import TenantContext

from .application_drafts import ApplicationDraftRepository, StoredApplicationDraft, _COLUMNS, _SCOPE_SQL, parse_content
from .application_review import REVIEW_KIND, MAX_REVIEW_AGE, require_draft_binding, review_binding
from .assessment_inputs import AssessmentEvidence, AssessmentInputDenied, AssessmentInputRepository
from .grouping import OwnerReview, reviewed_candidate
from .model import DiscoveryResult, _id, _json
from .persistence import DiscoveryRepository


REVIEW_STATUSES = frozenset({'UNREVIEWED', 'REVOKED', 'HELD_SUPERSEDED_DRAFT',
    'HELD_SUPERSEDED_INVENTORY', 'HELD_INCOMPLETE_INVENTORY', 'HELD_STALE_INVENTORY',
    'REVIEWED_ASSESSMENT_ONLY', 'REVIEWED_WITH_UNKNOWNS'})


class ApplicationReviewUnavailable(RuntimeError):
    """Retained/current signed review authority could not be established."""


def _view(stored: StoredApplicationDraft, result: DiscoveryResult | None,
          evidence: AssessmentEvidence | None, latest_generation: int,
          latest_revision: int, checked_at: datetime) -> dict:
    body = {'format': 'hosting-application-review-status/1',
        'environmentId': stored.environment_id, 'scope': vars(stored.scope),
        'applicationGroupId': stored.application_group_id, 'draftRevision': stored.revision,
        'draftRecordDigest': stored.record_digest, 'proposalDigest': stored.proposal_digest,
        'generation': stored.generation, 'resultDigest': stored.result_digest,
        'latestGeneration': latest_generation, 'latestDraftRevision': latest_revision,
        'checkedAt': checked_at.isoformat(), 'status': 'UNREVIEWED',
        'ownerDecision': None, 'ownerId': None, 'reviewReference': None,
        'evidenceId': None, 'evidenceRevision': None, 'evidenceDigest': None,
        'reviewedAt': None, 'expiresAt': None, 'candidateDigest': None,
        'unknownDependencyCount': None, 'dependencyEvidenceVerified': False,
        'ownershipAccepted': False, 'executionAuthorized': False}
    if evidence is not None:
        if evidence.kind != REVIEW_KIND:
            raise ApplicationReviewUnavailable('Invalid signed application review kind')
        decision = evidence.value
        require_draft_binding(decision, stored)
        if not decision.reviewed_at <= evidence.issued_at <= checked_at < evidence.expires_at:
            raise ApplicationReviewUnavailable('Application review is not current')
        body.update(ownerDecision=decision.decision, ownerId=decision.owner_id,
            reviewReference=decision.review_reference, evidenceId=evidence.evidence_id,
            evidenceRevision=evidence.revision, evidenceDigest=evidence.digest,
            reviewedAt=decision.reviewed_at.isoformat(), expiresAt=evidence.expires_at.isoformat())
    if evidence is not None and evidence.value.decision == 'REVOKE':
        body['status'] = 'REVOKED'
    elif stored.revision != latest_revision:
        body['status'] = 'HELD_SUPERSEDED_DRAFT'
    elif stored.generation != latest_generation:
        body['status'] = 'HELD_SUPERSEDED_INVENTORY'
    elif evidence is None:
        pass
    elif result is None or result.digest != stored.result_digest or result.scope != stored.scope:
        raise ApplicationReviewUnavailable('Source observation cannot be reconstructed')
    elif result.completeness != 'COMPLETE':
        body['status'] = 'HELD_INCOMPLETE_INVENTORY'
    elif not result.captured_at <= checked_at <= result.captured_at + MAX_REVIEW_AGE:
        body['status'] = 'HELD_STALE_INVENTORY'
    else:
        proposal = json.loads(stored.proposal_json)
        draft, edges = parse_content({'draft': proposal['draft'], 'dependencies': proposal['dependencies']})
        decision = evidence.value
        candidate = reviewed_candidate(result, draft, edges, OwnerReview(decision.owner_id,
            decision.scope, decision.review_reference, decision.reviewed_at, decision.proposal_digest),
            checked_at=checked_at, max_age=MAX_REVIEW_AGE)
        body.update(status=candidate.status, candidateDigest=candidate.digest,
                    unknownDependencyCount=len(candidate.unknown_edges))
    return body


class ApplicationReviewService:
    def __init__(self, drafts: ApplicationDraftRepository, evidence: AssessmentInputRepository):
        if not isinstance(drafts, ApplicationDraftRepository) or not isinstance(evidence, AssessmentInputRepository):
            raise TypeError('Actual draft and signed assessment repositories are required')
        self._drafts, self._evidence = drafts, evidence

    def get(self, ctx: TenantContext, scope: PlanScope, environment_id: str,
            application_group_id: str, *, revision: int,
            authorize: Callable[[PlanScope, datetime], None]) -> dict | None:
        if not _id(application_group_id) or type(revision) is not int or not 1 <= revision <= 2**63-1:
            raise ValueError('An exact immutable draft revision is required')
        DiscoveryRepository._require_scope(ctx, scope, environment_id)
        args = DiscoveryRepository._scope_args(ctx, scope, environment_id)
        with self._drafts._session(ctx, scope, environment_id, authorize) as connection:
            # Writers of generations, drafts and review evidence take the same
            # exclusive source lock. Multiple assessments may hold shared reads.
            key = int.from_bytes(hashlib.sha256(_json(args).encode('utf-8')).digest()[:8], 'big', signed=True)
            connection.execute('SELECT pg_advisory_xact_lock_shared(%s::bigint)', (key,))
            authorize(scope, connection.execute('SELECT clock_timestamp()').fetchone()[0])
            row = connection.execute('SELECT '+_COLUMNS+
                ' FROM hosting_controlplane.application_draft_revisions WHERE '+_SCOPE_SQL+
                ' AND application_group_id=%s AND revision=%s',
                (*args, application_group_id, revision)).fetchone()
            if row is None:
                authorize(scope, connection.execute('SELECT clock_timestamp()').fetchone()[0])
                return None
            stored = self._drafts._row(environment_id, scope, row)
            latest_revision = connection.execute('SELECT max(revision) FROM '
                'hosting_controlplane.application_draft_revisions WHERE '+_SCOPE_SQL+
                ' AND application_group_id=%s', (*args, application_group_id)).fetchone()[0]
            latest_generation = connection.execute('SELECT max(generation) FROM '
                'hosting_controlplane.discovery_generations WHERE '+_SCOPE_SQL, args).fetchone()[0]
            if latest_generation is None or latest_generation < stored.generation:
                raise ApplicationReviewUnavailable('Original source generation is unavailable')
            binding = review_binding(environment_id, scope, application_group_id, revision, stored.record_digest)
            try:
                at = connection.execute('SELECT clock_timestamp()').fetchone()[0]
                evidence = self._evidence.latest(ctx, REVIEW_KIND, binding, at)
                result = (self._drafts._snapshot(connection, args, stored.generation, stored.result_digest)
                          if evidence is not None and stored.revision == latest_revision
                          and stored.generation == latest_generation else None)
                at = connection.execute('SELECT clock_timestamp()').fetchone()[0]
                value = _view(stored, result, evidence, latest_generation, latest_revision, at)
                # Reverify original signatures and current enrollment/revocation
                # after reconstruction; never fall back to an older acceptance.
                if self._evidence.latest(ctx, REVIEW_KIND, binding,
                        connection.execute('SELECT clock_timestamp()').fetchone()[0]) != evidence:
                    raise ApplicationReviewUnavailable('Application review changed during evaluation')
            except (AssessmentInputDenied, ValueError):
                raise ApplicationReviewUnavailable('Current signed application review unavailable') from None
            authorize(scope, connection.execute('SELECT clock_timestamp()').fetchone()[0])
            return value
