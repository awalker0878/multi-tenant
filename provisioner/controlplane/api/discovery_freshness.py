"""Inventory freshness reads using the existing API identity and scope boundary."""
from __future__ import annotations

from copy import deepcopy
from typing import Annotated
from fastapi import Depends, Path, Request

from provisioner.controlplane.authority.service import (
    EXECUTION_OPERATOR, JOB_READER, require_scoped_role)
from provisioner.controlplane.discovery.freshness import (
    DiscoveryFreshnessService, FreshnessChanged, FreshnessUnavailable)
from provisioner.controlplane.discovery.model import _utc

_ID = r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'


def install_routes(app, *, repository, authority, session, environment, context, clock, error):
    """Mount the read projection; reuse identity verification, never issue authority."""
    service = None if repository is None else DiscoveryFreshnessService(repository, clock=clock)

    @app.get('/v1/environments/{environment_id}/discovery/freshness', tags=['discovery'],
             summary='Inspect latest inventory age and collection-health metadata',
             responses={code: {'description': description} for code, description in (
                 (401, 'Authentication required'), (403, 'Human role required'),
                 (404, 'Resource not found'), (409, 'Inventory changed during inspection'),
                 (422, 'Invalid request'), (503, 'Freshness metadata unavailable'))})
    def inspect_freshness(request: Request, environment_id: Annotated[str, Path(pattern=_ID)],
                          active=Depends(session)) -> dict:
        if request.query_params:
            raise error(422, 'REQUEST_INVALID', 'Freshness policy is server-owned; no query parameters are accepted')
        try:
            selected = deepcopy(environment(active, environment_id))
        except error:
            raise
        except Exception:
            raise error(503, 'DISCOVERY_FRESHNESS_UNAVAILABLE', 'Freshness metadata is unavailable') from None
        if service is None:
            raise error(503, 'DISCOVERY_UNAVAILABLE', 'Read-only discovery is unavailable')

        def authorize(scope, checked_at):
            principal = authority.authenticate(active.credential)
            if ((principal.subject, principal.organization_id, principal.tenant_id, principal.kind) !=
                    (active.principal.subject, active.principal.organization_id,
                     active.principal.tenant_id, 'HUMAN')):
                raise PermissionError('Freshness reader changed')
            at = clock()
            if not _utc(at) or at < checked_at:
                raise FreshnessUnavailable('Freshness reauthorization clock regressed')
            for role in (JOB_READER, EXECUTION_OPERATOR):
                try:
                    require_scoped_role(principal, role, scope, at)
                    break
                except PermissionError:
                    continue
            else:
                raise PermissionError('Current exact-scope read role is required')
            current = type(active)(principal, active.credential)
            if environment(current, environment_id) != selected:
                raise PermissionError('Environment selection changed')

        try:
            return service.inspect(context(active), selected.scope, environment_id, authorize=authorize)
        except error:
            raise
        except PermissionError:
            raise error(404, 'RESOURCE_NOT_FOUND', 'Resource not found') from None
        except FreshnessChanged:
            raise error(409, 'DISCOVERY_FRESHNESS_CHANGED', 'Inventory changed; explicitly inspect again') from None
        except Exception:
            # Database, metadata and clock errors are not evidence of missing inventory.
            raise error(503, 'DISCOVERY_FRESHNESS_UNAVAILABLE', 'Freshness metadata is unavailable') from None
