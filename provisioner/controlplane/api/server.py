"""Fail-closed PostgreSQL and OIDC composition for the control API.

The service refuses startup without a live database, distinct least-privilege
database roles, a pinned OIDC verifier, and a durable role directory. Migration
DDL and IAM synchronization run with separate credentials outside this service.
"""
from __future__ import annotations

import os
import base64
import binascii
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

import psycopg
import uvicorn
from fastapi import FastAPI
from psycopg.conninfo import conninfo_to_dict
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from provisioner.controlplane.authority.directory import PostgresRoleDirectory
from provisioner.controlplane.authority.oidc import OIDCIdentityProvider
from provisioner.controlplane.authority.postgres import PostgresAuthority
from provisioner.controlplane.authority.service import AuthorityService
from provisioner.controlplane.jobs.repository import JobRepository
from provisioner.controlplane.discovery.persistence import DiscoveryRepository
from provisioner.controlplane.evidence.runtime import (EvidenceHold,
    EvidenceRuntimeConfig, build_gate)
from provisioner.controlplane.persistence.store import EnterpriseRecordStore
from provisioner.controlplane.persistence.environments import EnvironmentRepository

from .http import create_app
from .portal import PortalConfig


def _required(environment: Mapping[str, str], name: str) -> str:
    value = environment.get(name)
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f'{name} must be configured')
    return value


def _secure_dsn(value: str, name: str) -> str:
    try:
        options = conninfo_to_dict(value)
    except psycopg.ProgrammingError:
        raise ValueError(f'{name} must be a valid PostgreSQL DSN') from None
    host = options.get('host', '')
    if (options.get('sslmode') != 'verify-full' or not host
            or host.startswith('/') or ',' in host
            or options.get('connect_timeout') not in (None, '5')):
        raise ValueError(f'{name} requires one TCP host, sslmode=verify-full and bounded timeout')
    return value


@dataclass(frozen=True)
class ServiceSettings:
    runtime_dsn: str
    authority_dsn: str
    directory_dsn: str
    oidc_issuer: str
    oidc_audience: str
    oidc_jwks_uri: str
    step_up_acr: frozenset[str]
    evidence_config: EvidenceRuntimeConfig | None = None
    portal: PortalConfig | None = None
    assessment_trust_path: str | None = None
    assessment_authority_public_key: str | None = None
    assessment_minimum_revision: int | None = None
    listen_host: str = '127.0.0.1'
    listen_port: int = 8080

    def __post_init__(self) -> None:
        assessment = (self.assessment_trust_path, self.assessment_authority_public_key,
                      self.assessment_minimum_revision)
        if any(value is not None for value in assessment):
            if (not all(value is not None for value in assessment)
                    or not isinstance(self.assessment_trust_path, str)
                    or not Path(self.assessment_trust_path).is_absolute()
                    or type(self.assessment_minimum_revision) is not int
                    or self.assessment_minimum_revision < 1):
                raise ValueError('Assessment trust requires an absolute path, pinned key and revision')
            try:
                Ed25519PublicKey.from_public_bytes(base64.b64decode(
                    self.assessment_authority_public_key, validate=True))
            except (ValueError, TypeError, binascii.Error):
                raise ValueError('Assessment authority key must be base64 raw Ed25519') from None
        for value, name in ((self.runtime_dsn, 'HOSTING_RUNTIME_DSN'),
                            (self.authority_dsn, 'HOSTING_AUTHORITY_DSN'),
                            (self.directory_dsn, 'HOSTING_DIRECTORY_DSN')):
            _secure_dsn(value, name)
        if len({self.runtime_dsn, self.authority_dsn, self.directory_dsn}) != 3:
            raise ValueError('Runtime, authority and directory credentials must be distinct')
        if self.evidence_config is not None and (
                not isinstance(self.evidence_config, EvidenceRuntimeConfig)
                or self.evidence_config.postgres_dsn != self.runtime_dsn):
            raise ValueError('Evidence verification must use this runtime database role')
        if not self.oidc_issuer or not self.oidc_audience or not self.oidc_jwks_uri:
            raise ValueError('Pinned OIDC issuer, audience and JWKS URI are required')
        if (not isinstance(self.step_up_acr, frozenset) or not self.step_up_acr
                or any(not isinstance(acr, str) or not acr for acr in self.step_up_acr)):
            raise ValueError('At least one verified step-up ACR is required')
        if self.portal is not None and (
                not isinstance(self.portal, PortalConfig)
                or (self.portal.issuer, self.portal.audience) !=
                   (self.oidc_issuer, self.oidc_audience)
                or (self.portal.step_up_acr is not None
                    and self.portal.step_up_acr not in self.step_up_acr)):
            raise ValueError('Portal issuer, audience and step-up ACR must match the API verifier')
        if (self.listen_host not in ('127.0.0.1', '::1')
                or type(self.listen_port) is not int or not 1 <= self.listen_port <= 65535):
            raise ValueError('Direct control API listener must bind loopback')

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> 'ServiceSettings':
        values = os.environ if environment is None else environment
        acr = frozenset(item.strip() for item in _required(values, 'HOSTING_STEP_UP_ACR').split(','))
        portal_keys = ('HOSTING_PORTAL_ORIGIN', 'HOSTING_PORTAL_AUTHORIZE_URL',
                       'HOSTING_PORTAL_TOKEN_URL', 'HOSTING_PORTAL_CLIENT_ID',
                       'HOSTING_PORTAL_SCOPE', 'HOSTING_PORTAL_STEP_UP_ACR')
        portal = None
        if any(values.get(key) for key in portal_keys):
            origin = _required(values, 'HOSTING_PORTAL_ORIGIN')
            portal = PortalConfig(
                origin=origin, issuer=_required(values, 'HOSTING_OIDC_ISSUER'),
                authorize_url=_required(values, 'HOSTING_PORTAL_AUTHORIZE_URL'),
                token_url=_required(values, 'HOSTING_PORTAL_TOKEN_URL'),
                client_id=_required(values, 'HOSTING_PORTAL_CLIENT_ID'),
                audience=_required(values, 'HOSTING_OIDC_AUDIENCE'),
                scope=_required(values, 'HOSTING_PORTAL_SCOPE'),
                redirect_uri=origin + '/portal/callback',
                step_up_acr=values.get('HOSTING_PORTAL_STEP_UP_ACR') or None,
            )
        try:
            port = int(values.get('HOSTING_LISTEN_PORT', '8080'))
        except ValueError:
            raise ValueError('HOSTING_LISTEN_PORT must be an integer') from None
        assessment = {}
        names = ('HOSTING_ASSESSMENT_TRUST_PATH',
                 'HOSTING_ASSESSMENT_AUTHORITY_PUBLIC_KEY',
                 'HOSTING_ASSESSMENT_MINIMUM_REVISION')
        if any(values.get(name) for name in names):
            try:
                revision = int(_required(values, names[2]))
            except ValueError:
                raise ValueError('HOSTING_ASSESSMENT_MINIMUM_REVISION must be a positive integer') from None
            assessment = dict(assessment_trust_path=_required(values, names[0]),
                              assessment_authority_public_key=_required(values, names[1]),
                              assessment_minimum_revision=revision)
        return cls(
            runtime_dsn=_required(values, 'HOSTING_RUNTIME_DSN'),
            authority_dsn=_required(values, 'HOSTING_AUTHORITY_DSN'),
            directory_dsn=_required(values, 'HOSTING_DIRECTORY_DSN'),
            oidc_issuer=_required(values, 'HOSTING_OIDC_ISSUER'),
            oidc_audience=_required(values, 'HOSTING_OIDC_AUDIENCE'),
            oidc_jwks_uri=_required(values, 'HOSTING_OIDC_JWKS_URI'),
            step_up_acr=acr,
            evidence_config=EvidenceRuntimeConfig.from_environment(
                values, require_scopes=True),
            portal=portal,
            listen_host=values.get('HOSTING_LISTEN_HOST', '127.0.0.1'),
            listen_port=port,
            **assessment,
        )


def _connect(dsn: str):
    return psycopg.connect(dsn, connect_timeout=5, autocommit=False)


def _role_name(connect) -> str:
    with connect() as connection:
        if connection.autocommit:
            raise RuntimeError('Control-plane role must use transactions')
        row = connection.execute(
            'SELECT current_user, rolsuper, rolbypassrls '
            'FROM pg_catalog.pg_roles WHERE rolname = current_user').fetchone()
        if row is None or row[1] or row[2]:
            raise RuntimeError('Control-plane database roles must enforce RLS')
        return row[0]


def create_postgres_app(settings: ServiceSettings, *,
                        evidence_gate=None) -> FastAPI:
    """Probe all three real DB roles, then wire the durable repositories."""
    if not isinstance(settings, ServiceSettings):
        raise TypeError('Validated service settings are required')
    runtime_connect = lambda: _connect(settings.runtime_dsn)
    authority_connect = lambda: _connect(settings.authority_dsn)
    directory_connect = lambda: _connect(settings.directory_dsn)
    roles = (_role_name(runtime_connect), _role_name(authority_connect),
             _role_name(directory_connect))
    if len(set(roles)) != 3:
        raise RuntimeError('Runtime, authority and directory roles must be distinct')
    directory = PostgresRoleDirectory(directory_connect)
    identities = OIDCIdentityProvider(
        issuer=settings.oidc_issuer, audience=settings.oidc_audience,
        jwks_uri=settings.oidc_jwks_uri, directory=directory,
        step_up_acr=settings.step_up_acr)
    ledger = PostgresAuthority(authority_connect)
    authority = AuthorityService(identities, ledger, ledger)
    records = EnterpriseRecordStore(runtime_connect)
    environments = EnvironmentRepository(runtime_connect)
    discovery = DiscoveryRepository(runtime_connect)
    assessment_inputs = None
    if settings.assessment_trust_path is not None:
        from provisioner.controlplane.discovery.assessment_inputs import (
            AssessmentInputRepository, DurableAssessmentInputs,
            SignedFileAssessmentTrustStore,
        )
        trust = SignedFileAssessmentTrustStore(
            settings.assessment_trust_path,
            authority_public_key=Ed25519PublicKey.from_public_bytes(base64.b64decode(
                settings.assessment_authority_public_key, validate=True)),
            minimum_revision=settings.assessment_minimum_revision)
        trust.current_policy(datetime.now(timezone.utc))
        assessment_inputs = DurableAssessmentInputs(
            AssessmentInputRepository(runtime_connect, trust), authority, environments)
    jobs = JobRepository(runtime_connect, ledger)
    if evidence_gate is None and settings.evidence_config is None:
        raise ValueError('Independent evidence configuration is required')
    gate = evidence_gate
    if gate is None:
        gate = build_gate(settings.evidence_config, connection_factory=runtime_connect)
        for tenant in settings.evidence_config.startup_scopes():
            gate.require(tenant)
    return create_app(records, authority, jobs, environments,
                      discovery=discovery,
                      assessment_inputs=assessment_inputs,
                      portal_config=settings.portal,
                      evidence_gate=gate)


def main() -> int:
    """Installed `hosting-api` entrypoint; secrets are read only from config."""
    try:
        settings = ServiceSettings.from_environment()
        app = create_postgres_app(settings)
    except (ValueError, RuntimeError, OSError, EvidenceHold, psycopg.Error):
        # DSNs and OIDC values must never be echoed in startup failures.
        raise SystemExit('Control API configuration or database authority is unavailable') from None
    uvicorn.run(app, host=settings.listen_host, port=settings.listen_port,
                proxy_headers=True, forwarded_allow_ips='127.0.0.1,::1',
                access_log=False)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
