"""Authenticated application-draft routes in the existing control application.

Draft authors are derived from the verified session; owner IDs and dependency
sources in the proposal remain assertions, not independently accepted identities.
"""
from __future__ import annotations

import re
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, Path, Query, Request
from starlette.concurrency import run_in_threadpool

from provisioner.controlplane.authority.service import EXECUTION_OPERATOR, JOB_READER, require_scoped_role
from provisioner.controlplane.discovery.application_reviews import ApplicationReviewService, REVIEW_STATUSES
from provisioner.controlplane.discovery.application_drafts import (
    ApplicationDraftConflict, ApplicationDraftRepository, MAX_DRAFT_BYTES)
from provisioner.controlplane.discovery.native_credentials import decode_json
from provisioner.controlplane.discovery.trust import _keys
from provisioner.controlplane.persistence.store import AuditContext

_ID = r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'
_REQUEST_SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'required': ['generation', 'resultDigest', 'expectedRevision', 'draft', 'dependencies'],
    'properties': {
        'generation': {'type': 'integer', 'minimum': 1, 'maximum': 2**63-1},
        'resultDigest': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'},
        'expectedRevision': {'type': 'integer', 'minimum': 0, 'maximum': 2**63-2},
        'draft': {'type': 'object', 'description': 'Closed GroupDraft fields; see application-drafts engineering contract.'},
        'dependencies': {'type': 'array', 'maxItems': 500, 'items': {'type': 'object'}},
    },
}


def install_routes(app, *, repository: ApplicationDraftRepository | None, authority,
                   session, environment, context, require_evidence, clock, error, reviews=None):
    """Reuse the enclosing API's authenticated session and exact-scope selectors."""
    if repository is not None and not isinstance(repository, ApplicationDraftRepository):
        raise TypeError('An actual application-draft repository is required')

    if reviews is not None and not isinstance(reviews, ApplicationReviewService):
        raise TypeError('An actual signed application review service is required')

    def authorizer(active, write=False):
        def check(scope, checked_at):
            principal = authority.authenticate(active.credential)
            if ((principal.subject, principal.organization_id, principal.tenant_id, principal.kind) !=
                    (active.principal.subject, active.principal.organization_id,
                     active.principal.tenant_id, 'HUMAN')):
                raise PermissionError('Authenticated draft actor changed')
            roles = (EXECUTION_OPERATOR,) if write else (JOB_READER, EXECUTION_OPERATOR)
            for role in roles:
                try:
                    require_scoped_role(principal, role, scope, checked_at)
                    break
                except PermissionError:
                    continue
            else:
                raise PermissionError('Exact-scope draft role is required')
            if write:
                require_evidence(active)
        return check

    def selected(active, environment_id, write=False):
        row = environment(active, environment_id)
        authorize = authorizer(active, write)
        authorize(row.scope, clock())
        if repository is None:
            raise error(503, 'APPLICATION_DRAFTS_UNAVAILABLE', 'Application drafts are unavailable')
        return row.scope, authorize

    def failure(exc):
        if isinstance(exc, error):
            raise exc
        if isinstance(exc, PermissionError):
            raise error(404, 'RESOURCE_NOT_FOUND', 'Resource not found') from None
        if isinstance(exc, ApplicationDraftConflict):
            raise error(409, 'APPLICATION_DRAFT_CONFLICT', 'Proposal revision or source generation changed') from None
        if isinstance(exc, (ValueError, TypeError, KeyError)):
            raise error(422, 'APPLICATION_DRAFT_INVALID', 'Invalid or inconsistent application proposal') from None
        raise error(503, 'APPLICATION_DRAFTS_UNAVAILABLE', 'Application draft operation is held') from None

    def checked_view(value, scope, environment_id, application_id, revision):
        if (not isinstance(value, dict) or value.get('scope') != vars(scope)
                or value.get('environmentId') != environment_id
                or value.get('applicationGroupId') != application_id
                or value.get('status') != 'UNREVIEWED'
                or value.get('ownershipAccepted') is not False
                or value.get('executionAuthorized') is not False
                or type(value.get('revision')) is not int or value['revision'] < 1
                or revision is not None and value['revision'] != revision):
            raise RuntimeError('Stored proposal response does not match the selected scope')
        return value

    @app.get('/v1/environments/{environment_id}/application-drafts',
             tags=['application-drafts'], summary='List current unreviewed application draft summaries')
    def list_drafts(environment_id: Annotated[str, Path(pattern=_ID)],
            after: Annotated[str | None, Query(pattern=_ID)] = None,
            limit: Annotated[int, Query(ge=1, le=100)] = 50, active=Depends(session)):
        try:
            scope, authorize = selected(active, environment_id)
            value = repository.list_current(context(active), scope, environment_id,
                                            after=after, limit=limit, authorize=authorize)
            if (not isinstance(value, dict) or value.get('format') != 'hosting-application-draft-list/1'
                    or value.get('scope') != vars(scope) or value.get('environmentId') != environment_id
                    or value.get('executionAuthorized') is not False or value.get('consistency') != 'LIVE_PAGE'
                    or not isinstance(value.get('items'), list) or len(value['items']) > limit):
                raise RuntimeError('Stored draft listing does not match the selected scope')
            latest = value.get('latestGeneration')
            if latest is not None and (type(latest) is not int or not 1 <= latest <= 2**63-1):
                raise RuntimeError('Stored draft listing has invalid source metadata')
            previous = after or ''
            for item in value['items']:
                identity = item.get('applicationGroupId') if isinstance(item, dict) else None
                if (not isinstance(identity, str) or not re.fullmatch(_ID, identity)
                        or identity <= previous or 'proposal' in item):
                    raise RuntimeError('Stored draft listing is not an advancing summary page')
                checked_view(item, scope, environment_id, identity, None)
                if (latest is None or type(item.get('generation')) is not int
                        or not 1 <= item['generation'] <= latest or item.get('latestGeneration') != latest
                        or type(item.get('sourceSuperseded')) is not bool
                        or item['sourceSuperseded'] != (item['generation'] != latest)):
                    raise RuntimeError('Stored draft summary has inconsistent source metadata')
                previous = identity
            if value.get('nextAfter') is not None and (len(value['items']) != limit
                    or value['nextAfter'] != previous):
                raise RuntimeError('Stored draft cursor is not the last selected application')
            return value
        except Exception as exc:
            failure(exc)

    @app.put('/v1/environments/{environment_id}/application-drafts/{application_id}',
             tags=['application-drafts'],
             summary='Append an unreviewed application proposal revision',
             openapi_extra={'requestBody': {'required': True, 'content': {
                 'application/json': {'schema': _REQUEST_SCHEMA}}}})
    async def save_draft(request: Request,
            environment_id: Annotated[str, Path(pattern=_ID)],
            application_id: Annotated[str, Path(pattern=_ID)], active=Depends(session)):
        try:
            scope, authorize = await run_in_threadpool(selected, active, environment_id, write=True)
            if request.headers.get('content-type', '').split(';', 1)[0].strip().lower() != 'application/json':
                raise ValueError('JSON is required')
            document = _keys(decode_json(await request.body(), MAX_DRAFT_BYTES),
                {'generation', 'resultDigest', 'expectedRevision', 'draft', 'dependencies'})
            if not isinstance(document['draft'], dict) or document['draft'].get('applicationGroupId') != application_id:
                raise ValueError('Path and proposal identity differ')
            if (type(document['generation']) is not int or not 1 <= document['generation'] <= 2**63-1
                    or type(document['expectedRevision']) is not int or not 0 <= document['expectedRevision'] < 2**63-1):
                raise ValueError('Bounded integer generation and revision are required')
            stored = await run_in_threadpool(repository.save, context(active), scope, environment_id,
                generation=document['generation'], result_digest=document['resultDigest'],
                expected_revision=document['expectedRevision'],
                content={'draft': document['draft'], 'dependencies': document['dependencies']},
                audit=AuditContext(active.principal.subject, uuid4().hex), authorize=authorize)
            # An identical retry may now refer to an older source generation.
            # Return history with a fresh supersession flag, never a false currency claim.
            value = await run_in_threadpool(repository.get, context(active), scope, environment_id,
                application_id, revision=stored.revision, authorize=authorizer(active))
            return checked_view(value, scope, environment_id, application_id, stored.revision)
        except Exception as exc:
            failure(exc)

    @app.get('/v1/environments/{environment_id}/application-drafts/{application_id}',
             tags=['application-drafts'], summary='Read an unreviewed proposal or exact historical revision')
    def get_draft(environment_id: Annotated[str, Path(pattern=_ID)],
            application_id: Annotated[str, Path(pattern=_ID)],
            revision: Annotated[int | None, Query(ge=1, le=2**63-1)] = None,
            active=Depends(session)):
        try:
            scope, authorize = selected(active, environment_id)
            value = repository.get(context(active), scope, environment_id, application_id,
                                   revision=revision, authorize=authorize)
            if value is None:
                raise error(404, 'RESOURCE_NOT_FOUND', 'Resource not found')
            return checked_view(value, scope, environment_id, application_id, revision)
        except Exception as exc:
            failure(exc)

    @app.get('/v1/environments/{environment_id}/application-drafts/{application_id}/review',
             tags=['application-drafts'], summary='Check independently signed owner review for an exact draft')
    def get_review(environment_id: Annotated[str, Path(pattern=_ID)],
            application_id: Annotated[str, Path(pattern=_ID)],
            revision: Annotated[int, Query(ge=1, le=2**63-1)], active=Depends(session)):
        try:
            scope, authorize = selected(active, environment_id)
            if reviews is None:
                raise error(503, 'APPLICATION_REVIEW_UNAVAILABLE', 'Signed application review service is unavailable')
            value = reviews.get(context(active), scope, environment_id, application_id,
                                revision=revision, authorize=authorize)
            if value is None:
                raise error(404, 'RESOURCE_NOT_FOUND', 'Resource not found')
            if (value.get('format') != 'hosting-application-review-status/1'
                    or value.get('scope') != vars(scope) or value.get('environmentId') != environment_id
                    or value.get('applicationGroupId') != application_id
                    or type(value.get('draftRevision')) is not int or value['draftRevision'] != revision
                    or not isinstance(value.get('status'), str) or value['status'] not in REVIEW_STATUSES
                    or value.get('dependencyEvidenceVerified') is not False
                    or value.get('ownershipAccepted') is not False
                    or value.get('executionAuthorized') is not False):
                raise RuntimeError('Signed review response differs from the selected draft')
            authorize(scope, clock())
            return value
        except Exception as exc:
            failure(exc)
