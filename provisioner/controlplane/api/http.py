"""Authenticated, tenant-scoped HTTP entrypoint for the first control-plane slice.

Every application instance requires the real B06/B07/B09 services. The only
client-supplied authority material is an opaque Bearer credential, which the
server's independently configured identity provider verifies on every call.
No endpoint starts native work or invents workflow progress.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated, Callable
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, Path, Query, Request, Response, Security
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.exceptions import HTTPException

from provisioner.controlplane.authority.model import PortfolioScope, VerifiedPrincipal
from provisioner.controlplane.authority.service import (
    EXECUTION_OPERATOR, JOB_READER, WORKLOAD_EDITOR, WORKLOAD_READER,
    AuthenticationFailed, AuthorityDenied, AuthorityService,
    require_scoped_role, require_workload_role,
)
from provisioner.controlplane.jobs.repository import (
    AdmissionConflict, AdmissionRefused, Job, JobEvent, JobRepository,
)
from provisioner.controlplane.persistence.store import (
    AuditContext, EnterpriseRecordStore, RecordNotFound,
    RecordValidationError, RevisionConflict, StoredRecord, TenantContext,
)

from .body_limit import BodyLimitMiddleware
from .models import (ErrorResponse, JobEventPage, JobEventView, JobView,
                     StoredWorkload, WorkloadCreate, WorkloadPage)

_ID_PATTERN = r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'
_BEARER = HTTPBearer(auto_error=False, description='Enterprise SSO bearer credential; verified by the server identity provider.')
_ERRORS = {code: {'model': ErrorResponse} for code in (400, 401, 403, 404, 409, 413, 422)}


@dataclass(frozen=True)
class _Session:
    principal: VerifiedPrincipal
    credential: str


class _ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, path: str | None = None):
        self.status = status
        self.code = code
        self.message = message
        self.path = path


def _error_response(status: int, code: str, message: str, path: str | None = None) -> JSONResponse:
    detail = {'code': code, 'message': message}
    if path:
        detail['path'] = path
    headers = {'Cache-Control': 'no-store'}
    if status == 401:
        headers['WWW-Authenticate'] = 'Bearer'
    return JSONResponse(status_code=status, content={'error': detail}, headers=headers)


def _stored(row: StoredRecord) -> StoredWorkload:
    return StoredWorkload(record=row.record, revision=row.revision, digest=row.digest)


def _job_view(job: Job) -> JobView:
    return JobView.model_validate({
        'jobId': job.job_id, 'planId': job.plan_id,
        'planRevision': job.plan_revision, 'planDigest': job.plan_digest,
        'status': job.status, 'lastEventSequence': job.last_event_sequence,
        'createdAt': job.created_at, 'updatedAt': job.updated_at,
    })


def _event_view(event: JobEvent) -> JobEventView:
    # JobEvent.detail is intentionally not exposed until B13 redaction is live.
    return JobEventView.model_validate({
        'sequence': event.sequence, 'eventType': event.event_type,
        'status': event.status, 'recordedAt': event.recorded_at,
    })


def _planned_only(record: dict) -> None:
    """A human draft cannot claim native discovery/ownership through this API."""
    for machine in record['spec']['machines']:
        if machine.get('bindings') != []:
            raise _ApiError(422, 'NATIVE_CLAIM_REFUSED', 'Planned workload cannot claim native bindings')
        for part in ('disks', 'nics'):
            if isinstance(machine.get(part), list) and any(
                    not isinstance(resource, dict) or resource.get('bindings') != []
                    for resource in machine[part]):
                raise _ApiError(422, 'NATIVE_CLAIM_REFUSED', 'Planned workload cannot claim native bindings')
    if any(dataset.get('sourceBindings') != [] for dataset in record['spec']['datasets']):
        raise _ApiError(422, 'NATIVE_CLAIM_REFUSED', 'Planned workload cannot claim native bindings')


def create_app(records: EnterpriseRecordStore, authority: AuthorityService,
               jobs: JobRepository, *, max_body_bytes: int = 1024 * 1024,
               clock: Callable[[], datetime] | None = None) -> FastAPI:
    """Compose supplied durable services; no development auth or in-memory fallback."""
    if (not isinstance(records, EnterpriseRecordStore)
            or not isinstance(authority, AuthorityService)
            or not isinstance(jobs, JobRepository)):
        raise TypeError('Real record, authority and job services are required')
    if type(max_body_bytes) is not int or max_body_bytes < 1:
        raise ValueError('max_body_bytes must be a positive integer')
    now = clock or (lambda: datetime.now(timezone.utc))
    app = FastAPI(title='Enterprise Workload Mobility Control API', version='1.0.0',
                  description='Scoped workload drafts, admitted jobs and recorded progress.',
                  docs_url=None, redoc_url=None)
    app.add_middleware(BodyLimitMiddleware, max_body_bytes=max_body_bytes)

    @app.exception_handler(_ApiError)
    async def api_error(_request: Request, exc: _ApiError) -> JSONResponse:
        return _error_response(exc.status, exc.code, exc.message, exc.path)

    @app.exception_handler(RequestValidationError)
    async def request_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        location = exc.errors()[0].get('loc', ()) if exc.errors() else ()
        path = '$.' + '.'.join(str(part) for part in location) if location else None
        return _error_response(422, 'REQUEST_INVALID', 'Invalid request shape', path)

    @app.exception_handler(HTTPException)
    async def http_error(_request: Request, exc: HTTPException) -> JSONResponse:
        return _error_response(exc.status_code, 'HTTP_ERROR', 'HTTP request failed')

    @app.middleware('http')
    async def no_store(request: Request, call_next):
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        return response

    def session(request: Request, credential: Annotated[
            HTTPAuthorizationCredentials | None, Security(_BEARER)]) -> _Session:
        if len(request.headers.getlist('authorization')) != 1 or credential is None:
            raise _ApiError(401, 'AUTHENTICATION_REQUIRED', 'Verified identity is required')
        try:
            principal = authority.authenticate(credential.credentials)
        except (AuthenticationFailed, AuthorityDenied):
            raise _ApiError(401, 'AUTHENTICATION_REQUIRED', 'Verified identity is required') from None
        if principal.kind != 'HUMAN':
            raise _ApiError(403, 'HUMAN_ROLE_REQUIRED', 'Human operator access is required')
        return _Session(principal, credential.credentials)

    def context(active: _Session) -> TenantContext:
        return TenantContext(active.principal.organization_id,
                             active.principal.tenant_id)

    def portfolio(active: _Session, wsd_id: str, role: str) -> PortfolioScope:
        scope = PortfolioScope(active.principal.organization_id,
                               active.principal.tenant_id, wsd_id)
        try:
            require_workload_role(active.principal, role, scope, now())
        except (AuthenticationFailed, AuthorityDenied):
            # An ungranted WSD looks exactly like an unknown WSD.
            raise _ApiError(404, 'RESOURCE_NOT_FOUND', 'Resource not found') from None
        return scope

    def visible_job(active: _Session, job_id: str) -> Job:
        job = jobs.get(context(active), job_id)
        if job is None:
            raise _ApiError(404, 'RESOURCE_NOT_FOUND', 'Resource not found')
        for role in (JOB_READER, EXECUTION_OPERATOR):
            try:
                require_scoped_role(active.principal, role, job.source, now())
                require_scoped_role(active.principal, role, job.destination, now())
                return job
            except (AuthenticationFailed, AuthorityDenied):
                pass
        raise _ApiError(404, 'RESOURCE_NOT_FOUND', 'Resource not found')

    @app.get('/v1/wsds/{wsd_id}/workloads', response_model=WorkloadPage,
             responses=_ERRORS, tags=['workloads'])
    def list_workloads(
            wsd_id: Annotated[str, Path(pattern=_ID_PATTERN)],
            limit: Annotated[int, Query(ge=1, le=100)] = 50,
            after: Annotated[str | None, Query(pattern=_ID_PATTERN)] = None,
            active: _Session = Depends(session)) -> WorkloadPage:
        portfolio(active, wsd_id, WORKLOAD_READER)
        rows = records.list(context(active), 'Workload', limit=limit + 1,
                            after=after, wsd_id=wsd_id)
        page = rows[:limit]
        next_after = page[-1].record['metadata']['workloadId'] if len(rows) > limit else None
        return WorkloadPage.model_validate({'items': [_stored(row) for row in page],
                                            'nextAfter': next_after})

    @app.get('/v1/wsds/{wsd_id}/workloads/{workload_id}', response_model=StoredWorkload,
             responses=_ERRORS, tags=['workloads'])
    def get_workload(
            wsd_id: Annotated[str, Path(pattern=_ID_PATTERN)],
            workload_id: Annotated[str, Path(pattern=_ID_PATTERN)],
            active: _Session = Depends(session)) -> StoredWorkload:
        portfolio(active, wsd_id, WORKLOAD_READER)
        row = records.get(context(active), 'Workload', workload_id, wsd_id=wsd_id)
        if row is None:
            raise _ApiError(404, 'RESOURCE_NOT_FOUND', 'Resource not found')
        return _stored(row)

    @app.post('/v1/wsds/{wsd_id}/workloads', status_code=201,
              response_model=StoredWorkload, responses=_ERRORS, tags=['workloads'])
    def create_workload(
            response: Response,
            wsd_id: Annotated[str, Path(pattern=_ID_PATTERN)],
            document: WorkloadCreate,
            active: _Session = Depends(session)) -> StoredWorkload:
        portfolio(active, wsd_id, WORKLOAD_EDITOR)
        record = document.canonical_document()
        meta = record['metadata']
        if (meta['organizationId'], meta['tenantId'], meta['wsdId']) != (
                active.principal.organization_id, active.principal.tenant_id, wsd_id):
            raise _ApiError(404, 'RESOURCE_NOT_FOUND', 'Resource not found')
        _planned_only(record)
        # Retain the exact independently verified subject. B07 plan-author
        # separation compares the same value to the durable audit provenance.
        audit = AuditContext(active.principal.subject, uuid4().hex)
        try:
            stored = records.create(context(active), record, audit)
        except RecordValidationError as exc:
            path = exc.problems[0].get('path') if exc.problems else None
            raise _ApiError(422, 'RECORD_INVALID', 'Canonical workload validation failed', path) from None
        except RecordNotFound:
            raise _ApiError(404, 'RESOURCE_NOT_FOUND', 'Resource not found') from None
        except RevisionConflict:
            raise _ApiError(409, 'REVISION_CONFLICT', 'Record identity or revision conflicts') from None
        response.headers['Location'] = f'/v1/wsds/{wsd_id}/workloads/{meta["workloadId"]}'
        return _stored(stored)

    @app.post('/v1/plans/{plan_id}/jobs', status_code=202,
              response_model=JobView, responses=_ERRORS, tags=['jobs'])
    def submit_job(
            response: Response,
            plan_id: Annotated[str, Path(pattern=_ID_PATTERN)],
            idempotency_key: Annotated[str, Header(alias='Idempotency-Key',
                                                   pattern=_ID_PATTERN)],
            active: _Session = Depends(session)) -> JobView:
        try:
            authorized = authority.authorize_submission(active.credential, plan_id)
        except (AuthenticationFailed, AuthorityDenied):
            raise _ApiError(403, 'ADMISSION_DENIED', 'Job admission denied') from None
        if (authorized.organization_id, authorized.tenant_id,
                authorized.actor_subject) != (
                active.principal.organization_id, active.principal.tenant_id,
                active.principal.subject):
            raise _ApiError(403, 'ADMISSION_DENIED', 'Job admission denied')
        try:
            job = jobs.submit(context(active), authorized,
                              idempotency_key=idempotency_key)
        except AdmissionRefused:
            raise _ApiError(409, 'ADMISSION_REFUSED', 'Current plan or approval cannot be admitted') from None
        except AdmissionConflict:
            raise _ApiError(409, 'IDEMPOTENCY_CONFLICT', 'Submission key conflicts with an existing job') from None
        response.headers['Location'] = f'/v1/jobs/{job.job_id}'
        return _job_view(job)

    @app.get('/v1/jobs/{job_id}', response_model=JobView,
             responses=_ERRORS, tags=['jobs'])
    def get_job(job_id: Annotated[str, Path(pattern=_ID_PATTERN)],
                active: _Session = Depends(session)) -> JobView:
        return _job_view(visible_job(active, job_id))

    @app.get('/v1/jobs/{job_id}/events', response_model=JobEventPage,
             responses=_ERRORS, tags=['jobs'])
    def get_job_events(
            job_id: Annotated[str, Path(pattern=_ID_PATTERN)],
            after: Annotated[int, Query(ge=0)] = 0,
            limit: Annotated[int, Query(ge=1, le=100)] = 50,
            active: _Session = Depends(session)) -> JobEventPage:
        visible_job(active, job_id)
        events = jobs.events(context(active), job_id, after_sequence=after, limit=limit + 1)
        page = events[:limit]
        next_after = page[-1].sequence if len(events) > limit else None
        return JobEventPage.model_validate({'items': [_event_view(event) for event in page],
                                            'nextAfter': next_after})

    return app
