"""Append-only human environment declarations with tenant and exact-scope reads.

Registration never establishes native ownership, discovery, connectivity or
qualification. Those independent facts belong to the site workers and later
observations. The HTTP boundary supplies an already verified actor and scope.
"""
from __future__ import annotations

import hashlib
import json
import re
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Iterator

from provisioner.controlplane.authority.model import PlanScope

from .store import AuditContext, TenantContext

_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$')
_COLUMNS = ('environment_id, display_name, site_id, security_domain_id, '
            'endpoint_id, native_scope_id, platform_family, status, '
            'registered_by, record_digest, registered_at')


class EnvironmentConflict(RuntimeError):
    """A declaration ID or exact native selector was registered already."""


@dataclass(frozen=True)
class EnvironmentDeclaration:
    environment_id: str
    display_name: str
    scope: PlanScope

    def __post_init__(self) -> None:
        if (not isinstance(self.scope, PlanScope)
                or not _ID.fullmatch(self.environment_id)
                or not 1 <= len(self.display_name) <= 256
                or any(ord(c) < 32 or ord(c) == 127 for c in self.display_name)
                or not all(_ID.fullmatch(value) for value in
                            (self.scope.organization_id, self.scope.tenant_id,
                             self.scope.site_id, self.scope.security_domain_id,
                             self.scope.endpoint_id))
                or not 1 <= len(self.scope.native_scope_id) <= 512
                or not self.scope.native_scope_id.strip()
                or any(ord(c) < 32 or ord(c) == 127 for c in self.scope.native_scope_id)
                or self.scope.platform_family not in ('vmware', 'nutanix', 'openstack')):
            raise ValueError('Invalid unverified environment declaration')

    def digest(self) -> str:
        raw = json.dumps({
            'environmentId': self.environment_id, 'displayName': self.display_name,
            'organizationId': self.scope.organization_id,
            'tenantId': self.scope.tenant_id, 'siteId': self.scope.site_id,
            'securityDomainId': self.scope.security_domain_id,
            'endpointId': self.scope.endpoint_id,
            'nativeScopeId': self.scope.native_scope_id,
            'platformFamily': self.scope.platform_family,
            'status': 'DECLARED_UNVERIFIED',
        }, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
        return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class RegisteredEnvironment:
    declaration: EnvironmentDeclaration
    registered_by: str
    record_digest: str
    registered_at: datetime
    status: str = 'DECLARED_UNVERIFIED'

    @property
    def scope(self) -> PlanScope:
        return self.declaration.scope


class EnvironmentRepository:
    def __init__(self, connection_factory: Callable):
        if not callable(connection_factory):
            raise TypeError('A PostgreSQL connection factory is required')
        self._connect = connection_factory

    @contextmanager
    def _session(self, ctx: TenantContext) -> Iterator:
        if not isinstance(ctx, TenantContext):
            raise TypeError('A trusted tenant context is required')
        with self._connect() as connection:
            if connection.autocommit:
                raise RuntimeError('Environment access requires a transaction')
            row = connection.execute(
                'SELECT rolsuper, rolbypassrls FROM pg_catalog.pg_roles '
                'WHERE rolname = current_user').fetchone()
            if row is None or row[0] or row[1]:
                raise RuntimeError('Environment role must enforce RLS')
            connection.execute(
                "SELECT set_config('app.organization_id', %s, true), "
                "set_config('app.tenant_id', %s, true)",
                (ctx.organization_id, ctx.tenant_id))
            yield connection

    @staticmethod
    def _row(ctx: TenantContext, row) -> RegisteredEnvironment:
        (environment_id, name, site_id, wsd_id, endpoint_id, native_scope_id,
         family, status, actor, digest, registered_at) = row
        if status != 'DECLARED_UNVERIFIED':
            raise RuntimeError('An unqualified registration has an invalid status')
        declaration = EnvironmentDeclaration(environment_id, name, PlanScope(
            ctx.organization_id, ctx.tenant_id, site_id, wsd_id,
            endpoint_id, native_scope_id, family))
        if declaration.digest() != digest:
            raise RuntimeError('Environment registration has changed since audit')
        return RegisteredEnvironment(declaration, actor, digest, registered_at)

    def create(self, ctx: TenantContext, declaration: EnvironmentDeclaration,
               audit: AuditContext) -> RegisteredEnvironment:
        if (not isinstance(ctx, TenantContext)
                or not isinstance(declaration, EnvironmentDeclaration)
                or not isinstance(audit, AuditContext)):
            raise TypeError('Trusted context, declaration and audit identity are required')
        if (ctx.organization_id, ctx.tenant_id) != (
                declaration.scope.organization_id, declaration.scope.tenant_id):
            raise ValueError('Declaration is outside the trusted tenant')
        scope = declaration.scope
        digest = declaration.digest()
        with self._session(ctx) as connection:
            try:
                row = connection.execute(
                    'INSERT INTO hosting_controlplane.environment_registrations '
                    '(organization_id, tenant_id, environment_id, display_name, '
                    'site_id, security_domain_id, endpoint_id, native_scope_id, '
                    'platform_family, registered_by, record_digest) VALUES '
                    '(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) '
                    f'RETURNING {_COLUMNS}',
                    (ctx.organization_id, ctx.tenant_id, declaration.environment_id,
                     declaration.display_name, scope.site_id, scope.security_domain_id,
                     scope.endpoint_id, scope.native_scope_id, scope.platform_family,
                     audit.actor_id, digest)).fetchone()
            except Exception as exc:
                if getattr(exc, 'sqlstate', None) == '23505':
                    raise EnvironmentConflict('Environment declaration already exists') from exc
                raise
            connection.execute(
                'INSERT INTO hosting_controlplane.audit_events '
                '(organization_id, tenant_id, actor_id, correlation_id, action, '
                'record_kind, record_id, revision, record_digest, details) VALUES '
                "(%s, %s, %s, %s, 'RECORD_CREATE', 'EnvironmentRegistration', "
                "%s, 1, %s, '{}'::jsonb)",
                (ctx.organization_id, ctx.tenant_id, audit.actor_id,
                 audit.correlation_id, declaration.environment_id, digest))
            return self._row(ctx, row)

    def get(self, ctx: TenantContext, environment_id: str) -> RegisteredEnvironment | None:
        if not isinstance(environment_id, str) or not _ID.fullmatch(environment_id):
            raise ValueError('Invalid environment ID')
        with self._session(ctx) as connection:
            row = connection.execute(
                f'SELECT {_COLUMNS} FROM hosting_controlplane.environment_registrations '
                'WHERE organization_id = %s AND tenant_id = %s AND environment_id = %s',
                (ctx.organization_id, ctx.tenant_id, environment_id)).fetchone()
        return self._row(ctx, row) if row else None

    def list(self, ctx: TenantContext, wsd_id: str,
             scopes: tuple[PlanScope, ...], *, after: str | None = None,
             limit: int = 51) -> list[RegisteredEnvironment]:
        if (not isinstance(wsd_id, str) or not _ID.fullmatch(wsd_id)
                or after is not None and (not isinstance(after, str) or not _ID.fullmatch(after))
                or type(limit) is not int or not 1 <= limit <= 101
                or not isinstance(scopes, tuple) or not 1 <= len(scopes) <= 100):
            raise ValueError('Invalid bounded environment read')
        if any(not isinstance(scope, PlanScope)
               or (scope.organization_id, scope.tenant_id, scope.security_domain_id) !=
                  (ctx.organization_id, ctx.tenant_id, wsd_id)
               for scope in scopes):
            raise ValueError('Native scope does not match tenant and WSD')
        # Apply exact native-scope authorization in SQL before LIMIT/cursor.
        predicates = ' OR '.join(
            '(site_id = %s AND endpoint_id = %s AND native_scope_id = %s '
            'AND platform_family = %s)' for _ in scopes)
        args = [ctx.organization_id, ctx.tenant_id, wsd_id, after or '']
        for scope in scopes:
            args.extend((scope.site_id, scope.endpoint_id,
                         scope.native_scope_id, scope.platform_family))
        args.append(limit)
        with self._session(ctx) as connection:
            rows = connection.execute(
                f'SELECT {_COLUMNS} FROM hosting_controlplane.environment_registrations '
                'WHERE organization_id = %s AND tenant_id = %s '
                'AND security_domain_id = %s AND environment_id > %s '
                f'AND ({predicates}) ORDER BY environment_id LIMIT %s',
                args).fetchall()
        return [self._row(ctx, row) for row in rows]
