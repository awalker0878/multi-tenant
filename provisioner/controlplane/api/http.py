"""Authenticated, tenant-scoped HTTP entrypoint for the first control-plane slice.

Every application instance requires the real B06/B07/B09 services. The only
client-supplied authority material is an opaque Bearer credential, which the
server's independently configured identity provider verifies on every call.
No endpoint starts native work or invents workflow progress.
"""
from __future__ import annotations

import base64
import binascii
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Annotated, Callable
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, Path, Query, Request, Response, Security
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.exceptions import HTTPException

from provisioner.controlplane.authority.model import (PlanScope, PortfolioScope,
                                                     VerifiedPrincipal)
from provisioner.controlplane.authority.service import (
    DESTINATION_OWNER, DESTINATION_SECURITY, EXECUTION_OPERATOR, JOB_READER,
    SOURCE_OWNER, SOURCE_SECURITY, WORKLOAD_EDITOR, WORKLOAD_READER,
    AuthenticationFailed, AuthorityDenied, AuthorityService, PlanRevisionChanged,
    require_scoped_role, require_workload_role,
)
from provisioner.controlplane.jobs.repository import (
    AdmissionConflict, AdmissionRefused, Job, JobEvent, JobRepository,
)
from provisioner.controlplane.evidence.gate import EvidenceHold, EvidenceMutationGate
from provisioner.controlplane.persistence.store import (
    AuditContext, EnterpriseRecordStore, RecordNotFound,
    RecordValidationError, RevisionConflict, StoredRecord, TenantContext,
    canonical_record_digest,
)
from provisioner.controlplane.persistence.environments import (
    EnvironmentConflict, EnvironmentDeclaration, EnvironmentRepository,
    RegisteredEnvironment,
)
from provisioner.controlplane.discovery.persistence import (
    DiscoveryRepository, StoredGeneration, StoredObservation,
)
from provisioner.domain.enterprise_records import validate_record

from .body_limit import BodyLimitMiddleware
from .portal import PortalConfig, mount_portal
from .models import (AccessPage, ApprovalReceipt, ApprovalRequest,
                     DiscoveryGenerationPage, DiscoveryGenerationView,
                     EnvironmentCreate, EnvironmentPage, EnvironmentView,
                     ErrorResponse, JobEventPage, JobEventView, JobView,
                     ObservedObjectPage, ObservedObjectView, PlanReview,
                     RevocationReceipt, RevocationRequest, StoredWorkload,
                     WorkloadCreate, WorkloadPage)

_ID_PATTERN = r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'
_CURSOR = re.compile(r'^[A-Za-z0-9_-]{1,4096}$')
_BEARER = HTTPBearer(auto_error=False, description='Enterprise SSO bearer credential; verified by the server identity provider.')
_ERRORS = {code: {'model': ErrorResponse} for code in (400, 401, 403, 404, 409, 413, 422, 503)}


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


def _environment_view(row: RegisteredEnvironment) -> EnvironmentView:
    declaration, scope = row.declaration, row.scope
    return EnvironmentView.model_validate({
        'environmentId': declaration.environment_id,
        'displayName': declaration.display_name,
        'siteId': scope.site_id, 'securityDomainId': scope.security_domain_id,
        'endpointId': scope.endpoint_id, 'nativeScopeId': scope.native_scope_id,
        'platformFamily': scope.platform_family, 'status': row.status,
        'recordDigest': row.record_digest, 'registeredAt': row.registered_at,
    })


def _generation_view(row: StoredGeneration) -> DiscoveryGenerationView:
    return DiscoveryGenerationView.model_validate({
        'environmentId': row.environment_id, 'generation': row.generation,
        'campaignId': row.campaign_id, 'resultDigest': row.result_digest,
        'capturedAt': row.captured_at, 'completeness': row.completeness,
        'objectCount': row.object_count,
        'collectionErrorCount': len(row.collection_errors),
        'missingPrivilegeCount': len(row.missing_privileges),
    })


def _observation_view(row: StoredObservation) -> ObservedObjectView:
    display_name = None
    for fact in row.facts:
        if (fact.get('name') == 'name' and fact.get('state') == 'KNOWN'
                and isinstance(fact.get('value'), str)):
            candidate = fact['value']
            if (1 <= len(candidate) <= 256
                    and all(ord(char) >= 32 and ord(char) != 127
                            for char in candidate)):
                display_name = candidate
            break
    return ObservedObjectView.model_validate({
        'resourceKind': row.identity.resource_kind,
        'nativeId': row.identity.native_id,
        'displayName': display_name,
        'unknownCount': sum(fact.get('state') == 'UNKNOWN' for fact in row.facts),
        'objectDigest': row.object_digest,
    })


def _object_cursor(kind: str, native_id: str) -> str:
    raw = json.dumps([kind, native_id], separators=(',', ':'),
                     ensure_ascii=False).encode('utf-8')
    return base64.urlsafe_b64encode(raw).decode('ascii').rstrip('=')


def _read_object_cursor(value: str | None) -> tuple[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, str) or _CURSOR.fullmatch(value) is None:
        raise _ApiError(422, 'REQUEST_INVALID', 'Invalid inventory page cursor')
    try:
        raw = base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))
        pair = json.loads(raw)
    except (ValueError, UnicodeError, binascii.Error):
        raise _ApiError(422, 'REQUEST_INVALID', 'Invalid inventory page cursor') from None
    if (not isinstance(pair, list) or len(pair) != 2
            or not all(isinstance(item, str) for item in pair)
            or pair[0] not in {'vm', 'disk', 'nic', 'volume', 'image', 'network',
                              'pool', 'cluster', 'host', 'datastore', 'quota'}
            or not 1 <= len(pair[1]) <= 512
            or any(ord(char) < 32 or ord(char) == 127 for char in pair[1])
            or _object_cursor(pair[0], pair[1]) != value):
        raise _ApiError(422, 'REQUEST_INVALID', 'Invalid inventory page cursor')
    return pair[0], pair[1]


def _review_scope(scope: PlanScope) -> dict:
    return {'organizationId': scope.organization_id,
            'tenantId': scope.tenant_id, 'siteId': scope.site_id,
            'securityDomainId': scope.security_domain_id,
            'endpointId': scope.endpoint_id,
            'nativeScopeId': scope.native_scope_id,
            'platformFamily': scope.platform_family}


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
               jobs: JobRepository, environments: EnvironmentRepository, *,
               evidence_gate: EvidenceMutationGate,
               discovery: DiscoveryRepository | None = None,
               max_body_bytes: int = 1024 * 1024,
               clock: Callable[[], datetime] | None = None,
               portal_config: PortalConfig | None = None) -> FastAPI:
    """Compose supplied durable services; no development auth or in-memory fallback."""
    if (not isinstance(records, EnterpriseRecordStore)
            or not isinstance(authority, AuthorityService)
            or not isinstance(jobs, JobRepository)
            or not isinstance(environments, EnvironmentRepository)
            or discovery is not None and not isinstance(discovery, DiscoveryRepository)
            or evidence_gate is None
            or not callable(getattr(evidence_gate, 'require', None))):
        raise TypeError('Real record, authority, job and evidence services are required')
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

    def require_evidence(active: _Session) -> None:
        try:
            evidence_gate.require(context(active))
        except EvidenceHold:
            raise _ApiError(503, 'EVIDENCE_HOLD',
                            'Independent evidence checkpoint requires operator review') from None

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

    def environment_scopes(active: _Session, wsd_id: str) -> tuple[PlanScope, ...]:
        scopes = []
        seen = set()
        for grant in active.principal.grants:
            scope = grant.scope
            if (not isinstance(scope, PlanScope)
                    or scope.security_domain_id != wsd_id
                    or grant.role not in (JOB_READER, EXECUTION_OPERATOR)):
                continue
            try:
                require_scoped_role(active.principal, grant.role, scope, now())
            except (AuthenticationFailed, AuthorityDenied):
                continue
            key = (scope.site_id, scope.endpoint_id,
                   scope.native_scope_id, scope.platform_family)
            if key not in seen:
                scopes.append(scope)
                seen.add(key)
        if not scopes:
            raise _ApiError(404, 'RESOURCE_NOT_FOUND', 'Resource not found')
        return tuple(scopes)

    def visible_environment(active: _Session, environment_id: str) -> RegisteredEnvironment:
        row = environments.get(context(active), environment_id)
        if row is not None:
            for role in (JOB_READER, EXECUTION_OPERATOR):
                try:
                    require_scoped_role(active.principal, role, row.scope, now())
                    return row
                except (AuthenticationFailed, AuthorityDenied):
                    pass
        raise _ApiError(404, 'RESOURCE_NOT_FOUND', 'Resource not found')

    def discovery_repository() -> DiscoveryRepository:
        if discovery is None:
            raise _ApiError(503, 'DISCOVERY_UNAVAILABLE',
                            'Read-only discovery is unavailable')
        return discovery

    @app.get('/v1/access/scopes', response_model=AccessPage,
             responses=_ERRORS, tags=['access'])
    def access_scopes(active: _Session = Depends(session)) -> AccessPage:
        """List fresh role selectors; a grant does not prove an environment exists."""
        items = []
        at = now()
        principal = active.principal
        for grant in principal.grants:
            scope = grant.scope
            if (grant.expires_at <= at
                    or (scope.organization_id, scope.tenant_id) !=
                       (principal.organization_id, principal.tenant_id)):
                continue
            row = {'role': grant.role, 'organizationId': scope.organization_id,
                   'tenantId': scope.tenant_id,
                   'securityDomainId': scope.security_domain_id,
                   'expiresAt': grant.expires_at}
            if isinstance(scope, PortfolioScope):
                row['kind'] = 'PORTFOLIO'
            elif isinstance(scope, PlanScope):
                row.update({'kind': 'NATIVE', 'siteId': scope.site_id,
                            'endpointId': scope.endpoint_id,
                            'nativeScopeId': scope.native_scope_id,
                            'platformFamily': scope.platform_family})
            else:
                continue
            items.append(row)
        items.sort(key=lambda row: (row['kind'], row['securityDomainId'],
                                    row['role'], row.get('siteId', ''),
                                    row.get('endpointId', '')))
        return AccessPage.model_validate({'items': items})

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

    @app.get('/v1/environments', response_model=EnvironmentPage,
             responses=_ERRORS, tags=['environments'])
    def list_environments(
            wsd_id: Annotated[str, Query(alias='wsdId', pattern=_ID_PATTERN)],
            limit: Annotated[int, Query(ge=1, le=100)] = 50,
            after: Annotated[str | None, Query(pattern=_ID_PATTERN)] = None,
            active: _Session = Depends(session)) -> EnvironmentPage:
        scopes = environment_scopes(active, wsd_id)
        rows = environments.list(context(active), wsd_id, scopes,
                                 after=after, limit=limit + 1)
        page = rows[:limit]
        cursor = page[-1].declaration.environment_id if len(rows) > limit else None
        return EnvironmentPage.model_validate({
            'items': [_environment_view(row).model_dump(by_alias=True) for row in page],
            'nextAfter': cursor,
        })

    @app.get('/v1/environments/{environment_id}', response_model=EnvironmentView,
             responses=_ERRORS, tags=['environments'])
    def get_environment(
            environment_id: Annotated[str, Path(pattern=_ID_PATTERN)],
            active: _Session = Depends(session)) -> EnvironmentView:
        return _environment_view(visible_environment(active, environment_id))

    @app.get('/v1/environments/{environment_id}/discovery/generations',
             response_model=DiscoveryGenerationPage, responses=_ERRORS,
             tags=['discovery'])
    def list_discovery_generations(
            environment_id: Annotated[str, Path(pattern=_ID_PATTERN)],
            limit: Annotated[int, Query(ge=1, le=100)] = 50,
            after: Annotated[int, Query(ge=0)] = 0,
            active: _Session = Depends(session)) -> DiscoveryGenerationPage:
        environment = visible_environment(active, environment_id)
        rows = discovery_repository().list_generations(
            context(active), environment.scope, environment_id,
            after=after, limit=limit + 1)
        if any(row.environment_id != environment_id or row.scope != environment.scope
               for row in rows):
            raise _ApiError(503, 'DISCOVERY_UNAVAILABLE',
                            'Read-only discovery is unavailable')
        page = rows[:limit]
        cursor = page[-1].generation if len(rows) > limit else None
        return DiscoveryGenerationPage.model_validate({
            'items': [_generation_view(row).model_dump(by_alias=True) for row in page],
            'nextAfter': cursor,
        })

    @app.get('/v1/environments/{environment_id}/discovery/generations/{generation}/objects',
             response_model=ObservedObjectPage, responses=_ERRORS,
             tags=['discovery'])
    def list_observed_objects(
            environment_id: Annotated[str, Path(pattern=_ID_PATTERN)],
            generation: Annotated[int, Path(ge=1)],
            limit: Annotated[int, Query(ge=1, le=100)] = 50,
            after: Annotated[str | None, Query(max_length=4096)] = None,
            active: _Session = Depends(session)) -> ObservedObjectPage:
        environment = visible_environment(active, environment_id)
        repository = discovery_repository()
        generations = repository.list_generations(
            context(active), environment.scope, environment_id,
            after=generation - 1, limit=1)
        if not generations or generations[0].generation != generation:
            raise _ApiError(404, 'RESOURCE_NOT_FOUND', 'Resource not found')
        if (generations[0].environment_id != environment_id
                or generations[0].scope != environment.scope):
            raise _ApiError(503, 'DISCOVERY_UNAVAILABLE',
                            'Read-only discovery is unavailable')
        rows = repository.list_observations(
            context(active), environment.scope, environment_id, generation,
            after=_read_object_cursor(after), limit=limit + 1)
        if any(row.generation != generation
               or (row.identity.endpoint_id, row.identity.native_scope_id,
                   row.identity.platform_family) !=
                  (environment.scope.endpoint_id,
                   environment.scope.native_scope_id,
                   environment.scope.platform_family)
               for row in rows):
            raise _ApiError(503, 'DISCOVERY_UNAVAILABLE',
                            'Read-only discovery is unavailable')
        page = rows[:limit]
        cursor = (_object_cursor(page[-1].identity.resource_kind,
                                 page[-1].identity.native_id)
                  if len(rows) > limit else None)
        return ObservedObjectPage.model_validate({
            'environmentId': environment_id, 'generation': generation,
            'items': [_observation_view(row).model_dump(by_alias=True)
                      for row in page],
            'nextAfter': cursor,
        })

    @app.post('/v1/environments', status_code=201,
              response_model=EnvironmentView, responses=_ERRORS,
              tags=['environments'])
    def register_environment(
            response: Response, declaration: EnvironmentCreate,
            active: _Session = Depends(session)) -> EnvironmentView:
        require_evidence(active)
        scope = PlanScope(active.principal.organization_id,
                          active.principal.tenant_id, declaration.site_id,
                          declaration.security_domain_id, declaration.endpoint_id,
                          declaration.native_scope_id, declaration.platform_family)
        try:
            require_scoped_role(active.principal, EXECUTION_OPERATOR, scope, now())
        except (AuthenticationFailed, AuthorityDenied):
            raise _ApiError(404, 'RESOURCE_NOT_FOUND', 'Resource not found') from None
        row = EnvironmentDeclaration(declaration.environment_id,
                                     declaration.display_name, scope)
        try:
            stored = environments.create(context(active), row,
                                         AuditContext(active.principal.subject, uuid4().hex))
        except EnvironmentConflict:
            raise _ApiError(409, 'ENVIRONMENT_CONFLICT',
                            'Environment registration already exists') from None
        response.headers['Location'] = f'/v1/environments/{declaration.environment_id}'
        return _environment_view(stored)

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
        require_evidence(active)
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
        require_evidence(active)
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

    @app.get('/v1/plans/{plan_id}/review', response_model=PlanReview,
             responses=_ERRORS, tags=['approvals'])
    def review_plan(
            plan_id: Annotated[str, Path(pattern=_ID_PATTERN)],
            active: _Session = Depends(session)) -> PlanReview:
        """Show only approved decision facts, bound to current B07/B06 state.

        The plan may change immediately after this read. Approval POST must
        present this revision and digest, which B07 checks again on write.
        """
        try:
            frozen = authority.review_plan(active.credential, plan_id)
        except AuthenticationFailed:
            raise _ApiError(401, 'AUTHENTICATION_REQUIRED', 'Verified identity is required') from None
        except AuthorityDenied:
            raise _ApiError(404, 'RESOURCE_NOT_FOUND', 'Resource not found') from None
        if (frozen.organization_id, frozen.tenant_id) != (
                active.principal.organization_id, active.principal.tenant_id):
            raise _ApiError(404, 'RESOURCE_NOT_FOUND', 'Resource not found')
        row = records.get(context(active), 'MigrationPlan', plan_id)
        if row is None:
            raise _ApiError(404, 'RESOURCE_NOT_FOUND', 'Resource not found')
        record = row.record
        try:
            if (not isinstance(record, dict) or validate_record(record)
                    or canonical_record_digest(record) != row.digest
                    or row.revision != frozen.revision
                    or record['metadata']['planDigest'] != frozen.digest
                    or record['metadata']['planId'] != frozen.plan_id
                    or PlanScope.from_record(record['spec']['source']) != frozen.source
                    or PlanScope.from_record(record['spec']['destination']) != frozen.destination):
                raise ValueError('Plan is not the same validated record')
            spec, meta = record['spec'], record['metadata']
            frozen_at = datetime.fromisoformat(meta['frozenAt'].replace('Z', '+00:00'))
        except (KeyError, TypeError, ValueError):
            raise _ApiError(409, 'PLAN_REVIEW_STALE', 'Current plan cannot be reviewed') from None
        roles = ((SOURCE_OWNER, frozen.source),
                 (DESTINATION_OWNER, frozen.destination),
                 (SOURCE_SECURITY, frozen.source),
                 (DESTINATION_SECURITY, frozen.destination))
        eligible = []
        for role, scope in roles:
            try:
                require_scoped_role(active.principal, role, scope, now())
                if active.principal.subject != frozen.author_subject:
                    eligible.append(role)
            except (AuthenticationFailed, AuthorityDenied):
                pass
        return PlanReview.model_validate({
            'planId': frozen.plan_id, 'planRevision': frozen.revision,
            'planDigest': frozen.digest, 'frozenAt': frozen_at,
            'workloadId': spec['workloadId'],
            'workloadRevision': spec['workloadRevision'],
            'sourceSnapshotId': spec['sourceSnapshotId'],
            'destinationSnapshotId': spec['destinationSnapshotId'],
            'source': _review_scope(frozen.source),
            'destination': _review_scope(frozen.destination),
            'routeMethod': spec['route']['method'],
            'selectedMachineCount': len(spec['selectedMachineIds']),
            'selectedDatasetCount': len(spec['selectedDatasetIds']),
            'maxDowntimeSeconds': spec['maxDowntimeSeconds'],
            'maxDataLossSeconds': spec['maxDataLossSeconds'],
            'rollbackWindowSeconds': spec['rollbackWindowSeconds'],
            'eligibleRoles': eligible,
        })

    @app.post('/v1/plans/{plan_id}/approvals', status_code=201,
              response_model=ApprovalReceipt, responses=_ERRORS, tags=['approvals'])
    def record_approval(
            plan_id: Annotated[str, Path(pattern=_ID_PATTERN)],
            decision: ApprovalRequest,
            active: _Session = Depends(session)) -> ApprovalReceipt:
        """Record an independently verified, current step-up decision.

        This durable receipt does not claim that a workflow has advanced.
        """
        require_evidence(active)
        try:
            approval = authority.record_approval(
                active.credential, plan_id, decision.role,
                ttl=timedelta(seconds=decision.ttl_seconds),
                expected_revision=decision.expected_plan_revision,
                expected_digest=decision.expected_plan_digest)
        except AuthenticationFailed:
            raise _ApiError(401, 'AUTHENTICATION_REQUIRED', 'Verified identity is required') from None
        except PlanRevisionChanged:
            raise _ApiError(409, 'PLAN_REVIEW_STALE', 'Reviewed plan has changed') from None
        except AuthorityDenied:
            raise _ApiError(403, 'APPROVAL_DENIED', 'Approval was not recorded') from None
        return ApprovalReceipt.model_validate({
            'approvalId': approval.approval_id, 'planId': approval.plan_id,
            'planRevision': approval.plan_revision,
            'planDigest': approval.plan_digest, 'role': approval.role,
            'expiresAt': approval.expires_at,
        })

    @app.post('/v1/plans/{plan_id}/revoke', response_model=RevocationReceipt,
              responses=_ERRORS, tags=['approvals'])
    def revoke_approvals(
            plan_id: Annotated[str, Path(pattern=_ID_PATTERN)],
            decision: RevocationRequest,
            active: _Session = Depends(session)) -> RevocationReceipt:
        try:
            epoch = authority.revoke_approvals(
                active.credential, plan_id, decision.reason)
        except AuthenticationFailed:
            raise _ApiError(401, 'AUTHENTICATION_REQUIRED', 'Verified identity is required') from None
        except AuthorityDenied:
            raise _ApiError(403, 'REVOCATION_DENIED', 'Approval revocation was not recorded') from None
        return RevocationReceipt.model_validate({'planId': plan_id,
                                                 'revocationEpoch': epoch})

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

    mount_portal(app, portal_config)
    return app
