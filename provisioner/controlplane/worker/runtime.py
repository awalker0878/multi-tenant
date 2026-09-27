"""Installed, fail-closed site worker credential listener.

An operator supplies exact read routes, a dedicated read-only PostgreSQL role,
enterprise worker PKI, and reviewed dynamic Vault roles. No native mutation
route or platform API adapter is started by this process.
"""
from __future__ import annotations

import ipaddress
import json
import os
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Callable, Mapping
from urllib.parse import parse_qs, unquote, urlsplit

from provisioner.controlplane.authority.model import PlanScope

from .grants import _ID
from .pki import MutualTlsWorkerVerifier
from .site_service import SiteWorkerServer, create_site_worker_server
from .vault import VaultDynamicCredentialIssuer, VaultDynamicRole

_SCOPE_KEYS = frozenset({'organizationId', 'tenantId', 'locationId',
                         'securityDomainId', 'endpointId', 'nativeScopeId',
                         'platformFamily'})
_ROUTE_KEYS = frozenset({'scope', 'reference', 'apiPath', 'maxCredentialTtlSeconds'})


def _required(values: Mapping[str, str], key: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f'{key} must be configured')
    return value


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate site route fields are forbidden')
        result[key] = value
    return result


def _nonfinite(_value):
    raise ValueError('Nonfinite site route values are forbidden')


@dataclass(frozen=True)
class SiteWorkerSettings:
    postgres_dsn: str
    postgres_role: str
    site_id: str
    bind_ip: str
    bind_port: int
    server_certificate: Path
    server_key: Path
    trust_bundle: Path
    crl_bundle: Path
    trust_domain: str
    vault_url: str
    vault_ca: Path
    vault_token_file: Path
    roles: tuple[VaultDynamicRole, ...]
    vault_namespace: str | None = None
    vault_client_certificate: Path | None = None
    vault_client_key: Path | None = None

    def __post_init__(self) -> None:
        try:
            parsed = urlsplit(self.postgres_dsn)
            options = parse_qs(parsed.query, strict_parsing=True,
                               keep_blank_values=True, max_num_fields=8)
            bind = ipaddress.ip_address(self.bind_ip)
            port = parsed.port
        except (ValueError, TypeError) as exc:
            raise ValueError('A verified PostgreSQL DSN and exact management IP are required') from exc
        if (parsed.scheme != 'postgresql' or not parsed.hostname
                or port is not None and not 1 <= port <= 65535
                or not parsed.path or parsed.path == '/' or parsed.fragment
                or ',' in parsed.hostname or unquote(parsed.username or '') != self.postgres_role
                or not set(options) <= {'sslmode', 'connect_timeout', 'sslrootcert',
                                       'sslcert', 'sslkey', 'channel_binding'}
                or any(len(value) != 1 for value in options.values())
                or options.get('sslmode') != ['verify-full']
                or options.get('connect_timeout') != ['5']
                or not options.get('sslrootcert', [''])[0].startswith('/')
                or not isinstance(self.postgres_role, str)
                or not _ID.fullmatch(self.postgres_role)
                or not isinstance(self.site_id, str) or not _ID.fullmatch(self.site_id)
                or bind.is_unspecified or type(self.bind_port) is not int
                or not 1 <= self.bind_port <= 65535
                or not isinstance(self.roles, tuple) or not self.roles
                or any(not isinstance(role, VaultDynamicRole)
                       or role.operation_kind != 'DISCOVER_READ'
                       or role.scope.site_id != self.site_id for role in self.roles)
                or len({role.reference for role in self.roles}) != len(self.roles)
                or len({role.scope for role in self.roles}) != len(self.roles)
                or (self.vault_client_certificate is None) !=
                   (self.vault_client_key is None)):
            raise ValueError('A dedicated read-only site role and exact routes are required')

    @classmethod
    def from_environment(cls, values: Mapping[str, str] | None = None) -> 'SiteWorkerSettings':
        env = os.environ if values is None else values
        try:
            routes = json.loads(_required(env, 'HOSTING_SITE_READ_ROUTES_JSON'),
                                object_pairs_hook=_unique_pairs, parse_constant=_nonfinite)
            if not isinstance(routes, list) or not routes:
                raise ValueError('At least one explicit site read route is required')
            parsed_roles = []
            for route in routes:
                if (not isinstance(route, dict) or route.keys() != _ROUTE_KEYS
                        or not isinstance(route['scope'], dict)
                        or route['scope'].keys() != _SCOPE_KEYS
                        or type(route['maxCredentialTtlSeconds']) is not int):
                    raise ValueError('An exact read route is required')
                parsed_roles.append(VaultDynamicRole(
                    route['reference'], route['apiPath'],
                    PlanScope.from_record(route['scope']), 'DISCOVER_READ',
                    timedelta(seconds=route['maxCredentialTtlSeconds'])))
            port = int(_required(env, 'HOSTING_SITE_BIND_PORT'))
        except (json.JSONDecodeError, TypeError, OverflowError) as exc:
            raise ValueError('Invalid site worker route or port configuration') from exc
        return cls(
            postgres_dsn=_required(env, 'HOSTING_SITE_POSTGRES_DSN'),
            postgres_role=_required(env, 'HOSTING_SITE_POSTGRES_ROLE'),
            site_id=_required(env, 'HOSTING_SITE_ID'),
            bind_ip=_required(env, 'HOSTING_SITE_BIND_IP'), bind_port=port,
            server_certificate=Path(_required(env, 'HOSTING_SITE_TLS_CERT')),
            server_key=Path(_required(env, 'HOSTING_SITE_TLS_KEY')),
            trust_bundle=Path(_required(env, 'HOSTING_SITE_TLS_CA')),
            crl_bundle=Path(_required(env, 'HOSTING_SITE_TLS_CRL')),
            trust_domain=_required(env, 'HOSTING_SITE_TRUST_DOMAIN'),
            vault_url=_required(env, 'HOSTING_SITE_VAULT_URL'),
            vault_ca=Path(_required(env, 'HOSTING_SITE_VAULT_CA')),
            vault_token_file=Path(_required(env, 'HOSTING_SITE_VAULT_TOKEN_FILE')),
            roles=tuple(parsed_roles),
            vault_namespace=env.get('HOSTING_SITE_VAULT_NAMESPACE') or None,
            vault_client_certificate=Path(env['HOSTING_SITE_VAULT_CLIENT_CERT'])
                if env.get('HOSTING_SITE_VAULT_CLIENT_CERT') else None,
            vault_client_key=Path(env['HOSTING_SITE_VAULT_CLIENT_KEY'])
                if env.get('HOSTING_SITE_VAULT_CLIENT_KEY') else None)


def _connect(dsn: str):
    import psycopg
    return psycopg.connect(dsn, connect_timeout=5, autocommit=False)


def _require_read_only_role(connect: Callable, expected_role: str) -> None:
    """Refuse privileged, grant-writing or mutable site database identities."""
    with connect() as connection:
        if connection.autocommit:
            raise RuntimeError('Site database transactions are required')
        role = connection.execute(
            'SELECT current_user, rolsuper, rolbypassrls FROM pg_catalog.pg_roles '
            'WHERE rolname = current_user').fetchone()
        if role != (expected_role, False, False):
            raise RuntimeError('The dedicated site PostgreSQL role is unavailable')
        if connection.execute(
            "SELECT has_schema_privilege(current_user, 'hosting_controlplane', 'CREATE'), "
            "has_database_privilege(current_user, current_database(), 'CREATE')"
        ).fetchone() != (False, False):
            raise RuntimeError('Site database role can create database objects')
        privilege = connection.execute(
            "SELECT coalesce(bool_or(has_table_privilege(current_user, c.oid, 'INSERT') "
            "OR has_table_privilege(current_user, c.oid, 'UPDATE') "
            "OR has_table_privilege(current_user, c.oid, 'DELETE') "
            "OR has_table_privilege(current_user, c.oid, 'TRUNCATE') "
            "OR has_table_privilege(current_user, c.oid, 'TRIGGER')), false) "
            'FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n '
            'ON n.oid = c.relnamespace WHERE n.nspname = %s '
            "AND c.relkind IN ('r', 'p')",
            ('hosting_controlplane',)).fetchone()
        if privilege != (False,):
            raise RuntimeError('Site database role has table write privileges')
        readable = connection.execute(
            "SELECT bool_and(coalesce(has_table_privilege(current_user, "
            "to_regclass('hosting_controlplane.' || t.name), 'SELECT'), false)) "
            "FROM (VALUES ('operation_jobs'), ('worker_grants'), "
            "('enterprise_records'), ('audit_events'), ('plan_approvals'), "
            "('native_containment_holds')) AS t(name)"
        ).fetchone()
        if readable != (True,):
            raise RuntimeError('Site database role cannot read required authority')
        required = connection.execute(
            "SELECT has_function_privilege(current_user, "
            "'hosting_controlplane.lock_job_scope(text,text,text)', 'EXECUTE'), "
            "has_function_privilege(current_user, "
            "'hosting_controlplane.lock_authority_scope(text,text,text)', 'EXECUTE'), "
            "has_function_privilege(current_user, "
            "'hosting_controlplane.lock_worker_scope(text,text,text,text,text,text,text,text,text,text)', 'EXECUTE'), "
            "has_function_privilege(current_user, "
            "'hosting_controlplane.lock_native_worker_scope(text,text,text)', 'EXECUTE')"
        ).fetchone()
        if required != (True, True, True, True):
            raise RuntimeError('Site database role cannot lock required authority')


def create_site_worker_runtime(settings: SiteWorkerSettings, *,
                               connection_factory: Callable | None = None) -> SiteWorkerServer:
    if not isinstance(settings, SiteWorkerSettings):
        raise TypeError('Validated site worker settings are required')
    connect = connection_factory or (lambda: _connect(settings.postgres_dsn))
    _require_read_only_role(connect, settings.postgres_role)
    verifier = MutualTlsWorkerVerifier(
        server_certificate=settings.server_certificate, server_key=settings.server_key,
        trust_bundle=settings.trust_bundle, crl_bundle=settings.crl_bundle,
        trust_domain=settings.trust_domain)
    issuer = VaultDynamicCredentialIssuer(
        vault_url=settings.vault_url, ca_bundle=settings.vault_ca,
        agent_token_file=settings.vault_token_file, roles=settings.roles,
        namespace=settings.vault_namespace,
        client_certificate=settings.vault_client_certificate,
        client_key=settings.vault_client_key)
    return create_site_worker_server(
        (settings.bind_ip, settings.bind_port), site_id=settings.site_id,
        allowed_read_scopes=frozenset(role.scope for role in settings.roles),
        verifier=verifier, connect=connect, issuer=issuer)


def main() -> int:
    try:
        settings = SiteWorkerSettings.from_environment()
        server = create_site_worker_runtime(settings)
    except Exception:
        # Never echo DSNs, certificate paths, tokens, or Vault configuration.
        raise SystemExit('Site worker configuration or authority is unavailable') from None
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
