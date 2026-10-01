"""Inventory freshness reads and audited checks under the existing API authority."""
from __future__ import annotations

from copy import deepcopy
import re
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, Path, Request
from starlette.concurrency import run_in_threadpool

from provisioner.controlplane.authority.service import (
    EXECUTION_OPERATOR, JOB_READER, require_scoped_role)
from provisioner.controlplane.discovery.freshness import (
    DiscoveryFreshnessService, FreshnessChanged, FreshnessUnavailable)
from provisioner.controlplane.discovery.freshness_history import (
    FreshnessHistoryRepository, FreshnessCheckConflict)
from provisioner.controlplane.discovery.model import _utc
from provisioner.controlplane.discovery.native_credentials import decode_json
from provisioner.controlplane.discovery.trust import _keys
from provisioner.controlplane.persistence.store import AuditContext

_ID = r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'
_BASE = '/v1/environments/{environment_id}/discovery/freshness'
_RESPONSES = {code: {'description': description} for code, description in (
    (401, 'Authentication required'), (403, 'Human role required'),
    (404, 'Resource not found'), (409, 'Check conflict or changed inventory'),
    (413, 'Request exceeds its bound'), (422, 'Invalid request'),
    (503, 'Freshness metadata or evidence custody unavailable'))}


def install_routes(app, *, repository, authority, session, environment, context,
                   require_evidence, clock, error):
    """The server computes checks; clients never supply a report or actor."""
    service = None if repository is None else DiscoveryFreshnessService(repository, clock=clock)
    history = None if repository is None else FreshnessHistoryRepository(repository)

    def selected(active, environment_id, *, write=False):
        record = deepcopy(environment(active, environment_id))
        if service is None:
            raise error(503, 'DISCOVERY_UNAVAILABLE', 'Read-only discovery is unavailable')

        def authorize(scope, checked_at):
            principal = authority.authenticate(active.credential)
            if ((principal.subject, principal.organization_id, principal.tenant_id, principal.kind) !=
                    (active.principal.subject, active.principal.organization_id,
                     active.principal.tenant_id, 'HUMAN') or scope != record.scope):
                raise PermissionError('Freshness reader or selected scope changed')
            at = clock()
            if not _utc(at) or not _utc(checked_at) or at < checked_at:
                raise FreshnessUnavailable('Freshness reauthorization clock regressed')
            for role in ((EXECUTION_OPERATOR,) if write else (JOB_READER, EXECUTION_OPERATOR)):
                try:
                    require_scoped_role(principal, role, scope, at)
                    break
                except PermissionError:
                    continue
            else:
                raise PermissionError('Current exact-scope role is required')
            current = type(active)(principal, active.credential)
            if environment(current, environment_id) != record:
                raise PermissionError('Environment selection changed')
            if write:
                require_evidence(current)

        authorize(record.scope, clock())
        return record.scope, authorize

    def failure(exc):
        if isinstance(exc, error):
            raise exc
        if isinstance(exc, PermissionError):
            raise error(404, 'RESOURCE_NOT_FOUND', 'Resource not found') from None
        if isinstance(exc, FreshnessChanged):
            raise error(409, 'DISCOVERY_FRESHNESS_CHANGED', 'Inventory changed; explicitly inspect again') from None
        if isinstance(exc, FreshnessCheckConflict):
            raise error(409, 'DISCOVERY_FRESHNESS_CHECK_CONFLICT', 'Check ID is already in use') from None
        # Corrupt retained records and database failures are not client errors or missing inventory.
        raise error(503, 'DISCOVERY_FRESHNESS_UNAVAILABLE', 'Freshness metadata is unavailable') from None

    def no_query(request):
        if request.query_params:
            raise error(422, 'REQUEST_INVALID', 'No query parameters are accepted')

    def page_query(request):
        pairs = list(request.query_params.multi_items())
        if (any(key not in ('after', 'limit') for key, _ in pairs)
                or len({key for key, _ in pairs}) != len(pairs)):
            raise error(422, 'REQUEST_INVALID', 'Invalid history page selection')
        values = {'after': 0, 'limit': 20}
        for key, raw in pairs:
            if len(raw) > 19 or not re.fullmatch(r'0|[1-9][0-9]*', raw):
                raise error(422, 'REQUEST_INVALID', 'Invalid history page selection')
            value = int(raw)
            if not (0 <= value <= 2**63-1 if key == 'after' else 1 <= value <= 50):
                raise error(422, 'REQUEST_INVALID', 'Invalid history page selection')
            values[key] = value
        return values

    def checked_history(value, scope, environment_id, *, check_id=None):
        if (not isinstance(value, dict) or value.get('scope') != vars(scope)
                or value.get('environmentId') != environment_id or value.get('historicalOnly') is not True
                or any(value.get(k) is not False for k in (
                    'notificationAttempted', 'collectionRequested', 'executionAuthorized'))
                or value.get('format') != ('hosting-discovery-freshness-history/1' if check_id is None
                                           else 'hosting-discovery-freshness-check/1')
                or check_id is not None and value.get('checkId') != check_id):
            raise FreshnessUnavailable('History response differs from selected identity')
        return value

    @app.get(_BASE, tags=['discovery'], responses=_RESPONSES,
             summary='Inspect latest inventory age and collection-health metadata')
    def inspect_freshness(request: Request, environment_id: Annotated[str, Path(pattern=_ID)],
                          active=Depends(session)) -> dict:
        no_query(request)
        try:
            scope, authorize = selected(active, environment_id)
            return service.inspect(context(active), scope, environment_id, authorize=authorize)
        except Exception as exc:
            failure(exc)

    @app.put(_BASE + '/checks/{check_id}', tags=['discovery'], responses=_RESPONSES,
             summary='Record one server-computed historical freshness check',
             openapi_extra={'requestBody': {'required': True, 'content': {'application/json': {
                 'schema': {'type': 'object', 'properties': {}, 'additionalProperties': False}}}}})
    async def capture_freshness(request: Request, environment_id: Annotated[str, Path(pattern=_ID)],
                                check_id: Annotated[str, Path(pattern=_ID)], active=Depends(session)) -> dict:
        no_query(request)
        try:
            scope, authorize = await run_in_threadpool(selected, active, environment_id, write=True)
            if request.headers.get('content-type', '').split(';', 1)[0].strip().lower() != 'application/json':
                raise error(422, 'REQUEST_INVALID', 'An empty JSON object is required')
            raw = bytearray()
            async for chunk in request.stream():
                raw.extend(chunk)
                if len(raw) > 1024:
                    raise error(413, 'REQUEST_TOO_LARGE', 'Freshness check body exceeds its bound')
            try:
                _keys(decode_json(bytes(raw), 1024), set())
            except (ValueError, TypeError):
                raise error(422, 'REQUEST_INVALID', 'An empty JSON object is required') from None
            value = await run_in_threadpool(history.capture, context(active), scope, environment_id, check_id,
                audit=AuditContext(active.principal.subject, uuid4().hex), authorize=authorize)
            # Repository context exit has rechecked current authority and committed the audit atomically.
            return checked_history(value, scope, environment_id, check_id=check_id)
        except Exception as exc:
            failure(exc)

    @app.get(_BASE + '/checks', tags=['discovery'], responses=_RESPONSES, summary='Read one page of historical freshness checks')
    def list_freshness(request: Request, environment_id: Annotated[str, Path(pattern=_ID)],
                       active=Depends(session)) -> dict:
        values = page_query(request)
        try:
            scope, authorize = selected(active, environment_id)
            return checked_history(history.list_checks(context(active), scope, environment_id,
                authorize=authorize, **values), scope, environment_id)
        except Exception as exc:
            failure(exc)

    @app.get(_BASE + '/checks/{check_id}', tags=['discovery'], responses=_RESPONSES, summary='Read an exact retained freshness check')
    def get_freshness(request: Request, environment_id: Annotated[str, Path(pattern=_ID)],
                      check_id: Annotated[str, Path(pattern=_ID)], active=Depends(session)) -> dict:
        no_query(request)
        try:
            scope, authorize = selected(active, environment_id)
            value = history.get(context(active), scope, environment_id, check_id, authorize=authorize)
            if value is None:
                raise error(404, 'RESOURCE_NOT_FOUND', 'Resource not found')
            return checked_history(value, scope, environment_id, check_id=check_id)
        except Exception as exc:
            failure(exc)
