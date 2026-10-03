"""Operator-configured discovery-only mTLS ingestion process.

No default root keys, database identity, witness, evidence path or bind address
are supplied. The process owns a separate SQL writer role and never starts the
ordinary user API or a native platform execution adapter.
"""
from __future__ import annotations

import ipaddress
import os
import re
import signal
import stat
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping
from urllib.parse import parse_qs, unquote, urlsplit

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from provisioner.controlplane.worker.pki import MutualTlsWorkerVerifier

from .ingest import (DiscoveryIngestServer, DiscoveryIngestService,
                     PrivateDiscoveryEvidenceSink)
from .trust import SignedDiscoveryIngestVerifier, SignedFileDiscoveryTrustStore, _decode
from .witness import SignedFileDiscoveryCredentialAuthority

_ROLE = re.compile(r'^[a-z][a-z0-9_]{0,62}$')
_WRITE_TABLES = ('discovery_campaigns', 'discovery_generations',
                 'discovery_observations', 'discovery_absence_candidates', 'audit_events')


def _required(values: Mapping[str, str], key: str) -> str:
    value = values.get('HOSTING_DISCOVERY_' + key)
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError('Required discovery runtime configuration is absent')
    return value


@dataclass(frozen=True, slots=True)
class DiscoveryIngestSettings:
    postgres_dsn: str = field(repr=False)
    postgres_role: str
    bind_ip: str
    bind_port: int
    server_certificate: Path
    server_key: Path
    trust_bundle: Path
    crl_bundle: Path
    trust_domain: str
    trust_policy_file: Path
    trust_root_key: str
    trust_min_revision: int
    credential_witness_file: Path
    credential_witness_root_key: str
    credential_witness_min_revision: int
    evidence_root: Path
    max_connections: int = 16

    def __post_init__(self) -> None:
        try:
            parsed = urlsplit(self.postgres_dsn)
            options = parse_qs(parsed.query, strict_parsing=True,
                               keep_blank_values=True, max_num_fields=8)
            address = ipaddress.ip_address(self.bind_ip)
            port = parsed.port
            trust_key = _decode(self.trust_root_key, 32)
            witness_key = _decode(self.credential_witness_root_key, 32)
        except (ValueError, TypeError) as exc:
            raise ValueError('Verified PostgreSQL, exact management IP and independent roots required') from exc
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
                or not isinstance(self.postgres_role, str) or not _ROLE.fullmatch(self.postgres_role)
                or address.is_unspecified or type(self.bind_port) is not int
                or not 1 <= self.bind_port <= 65535
                or trust_key == witness_key
                or any(type(value) is not int or value < 1 for value in
                       (self.trust_min_revision, self.credential_witness_min_revision))
                or type(self.max_connections) is not int or not 1 <= self.max_connections <= 64
                or any(not isinstance(path, Path) or not path.is_absolute() for path in
                       (self.server_certificate, self.server_key, self.trust_bundle,
                        self.crl_bundle, self.trust_policy_file,
                        self.credential_witness_file, self.evidence_root))):
            raise ValueError('Dedicated discovery settings violate transport, root or bound requirements')

    @classmethod
    def from_environment(cls, values: Mapping[str, str] | None = None) -> DiscoveryIngestSettings:
        env = os.environ if values is None else values
        return cls(
            postgres_dsn=_required(env, 'POSTGRES_DSN'), postgres_role=_required(env, 'POSTGRES_ROLE'),
            bind_ip=_required(env, 'BIND_IP'), bind_port=int(_required(env, 'BIND_PORT')),
            server_certificate=Path(_required(env, 'TLS_CERT')), server_key=Path(_required(env, 'TLS_KEY')),
            trust_bundle=Path(_required(env, 'TLS_CA')), crl_bundle=Path(_required(env, 'TLS_CRL')),
            trust_domain=_required(env, 'TRUST_DOMAIN'), trust_policy_file=Path(_required(env, 'TRUST_POLICY_FILE')),
            trust_root_key=_required(env, 'TRUST_ROOT_KEY'),
            trust_min_revision=int(_required(env, 'TRUST_MIN_REVISION')),
            credential_witness_file=Path(_required(env, 'CREDENTIAL_WITNESS_FILE')),
            credential_witness_root_key=_required(env, 'CREDENTIAL_WITNESS_ROOT_KEY'),
            credential_witness_min_revision=int(_required(env, 'CREDENTIAL_WITNESS_MIN_REVISION')),
            evidence_root=Path(_required(env, 'EVIDENCE_ROOT')),
            max_connections=int(env.get('HOSTING_DISCOVERY_MAX_CONNECTIONS', '16')))


def _connect(dsn: str):
    import psycopg
    return psycopg.connect(dsn, connect_timeout=5, autocommit=False)


def require_ingest_role(connect: Callable, role: str) -> None:
    """Reject broad database writers, site workers, memberships and RLS bypass."""
    with connect() as connection:
        if connection.autocommit:
            raise RuntimeError('Discovery ingestion requires database transactions')
        record = connection.execute(
            'SELECT current_user, session_user, rolsuper, rolbypassrls, rolcreaterole, '
            'rolcreatedb, rolreplication FROM pg_catalog.pg_roles WHERE rolname = current_user'
        ).fetchone()
        if record != (role, role, False, False, False, False, False):
            raise RuntimeError('A dedicated unprivileged discovery SQL login is required')
        if connection.execute('SELECT hosting_controlplane.is_site_worker_role()').fetchone() != (False,):
            raise RuntimeError('A site worker cannot act as a discovery ingest writer')
        if connection.execute(
                'SELECT coalesce(bool_or(pg_has_role(session_user, r.oid, %s)), false) '
                'FROM pg_catalog.pg_roles r WHERE r.rolname <> session_user',
                ('member',)).fetchone() != (False,):
            raise RuntimeError('Discovery SQL login has another role membership')
        if connection.execute(
                "SELECT has_database_privilege(current_user, current_database(), 'CREATE'), "
                "coalesce(bool_or(has_schema_privilege(current_user, n.oid, 'CREATE')), false) "
                "FROM pg_catalog.pg_namespace n WHERE n.nspname NOT LIKE 'pg_%' "
                "AND n.nspname <> 'information_schema'").fetchone() != (False, False):
            raise RuntimeError('Discovery SQL login can create database objects')
        forbidden = connection.execute(
            "SELECT coalesce(bool_or(has_table_privilege(current_user, c.oid, 'UPDATE') "
            "OR has_table_privilege(current_user, c.oid, 'DELETE') "
            "OR has_table_privilege(current_user, c.oid, 'TRUNCATE') "
            "OR has_table_privilege(current_user, c.oid, 'TRIGGER') "
            "OR has_table_privilege(current_user, c.oid, 'REFERENCES') "
            "OR (has_table_privilege(current_user, c.oid, 'INSERT') AND "
            "NOT (n.nspname = 'hosting_controlplane' AND c.relname = ANY(%s)))), false) "
            'FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace '
            "WHERE c.relkind IN ('r', 'p') AND n.nspname NOT LIKE 'pg_%' "
            "AND n.nspname <> 'information_schema'", (list(_WRITE_TABLES),)).fetchone()
        if forbidden != (False,):
            raise RuntimeError('Discovery SQL login has unrelated or mutable table privileges')
        required = connection.execute(
            "SELECT bool_and(coalesce(has_table_privilege(current_user, "
            "to_regclass('hosting_controlplane.' || t.name), 'INSERT'), false) AND "
            "coalesce(has_table_privilege(current_user, "
            "to_regclass('hosting_controlplane.' || t.name), 'SELECT'), false)) "
            'FROM unnest(%s::text[]) AS t(name)', (list(_WRITE_TABLES),)).fetchone()
        if required != (True,):
            raise RuntimeError('Discovery SQL login lacks required append-only privileges')
        if connection.execute(
                "SELECT coalesce(has_table_privilege(current_user, "
                "to_regclass('hosting_controlplane.environment_registrations'), 'SELECT'), false), "
                "count(*) = 4 AND coalesce(bool_and(c.relrowsecurity AND c.relforcerowsecurity), false) "
                'FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace '
                "WHERE n.nspname = 'hosting_controlplane' AND c.relname = ANY(%s)",
                (list(_WRITE_TABLES[:-1]),)).fetchone() != (True, True):
            raise RuntimeError('Discovery registry or forced tenant RLS is unavailable')


def create_discovery_ingest_runtime(settings: DiscoveryIngestSettings, *,
                                    connection_factory: Callable | None = None) -> DiscoveryIngestServer:
    if not isinstance(settings, DiscoveryIngestSettings):
        raise TypeError('Validated discovery ingest settings are required')
    connect = connection_factory or (lambda: _connect(settings.postgres_dsn))
    require_ingest_role(connect, settings.postgres_role)
    key_info = settings.server_key.lstat()
    if (not stat.S_ISREG(key_info.st_mode) or key_info.st_uid not in (0, os.geteuid())
            or key_info.st_mode & 0o077):
        raise ValueError('Discovery TLS server key must be private')
    tls = MutualTlsWorkerVerifier(server_certificate=settings.server_certificate,
        server_key=settings.server_key, trust_bundle=settings.trust_bundle,
        crl_bundle=settings.crl_bundle, trust_domain=settings.trust_domain)
    trust = SignedFileDiscoveryTrustStore(settings.trust_policy_file,
        authority_public_key=Ed25519PublicKey.from_public_bytes(_decode(settings.trust_root_key, 32)),
        minimum_revision=settings.trust_min_revision)
    witness = SignedFileDiscoveryCredentialAuthority(settings.credential_witness_file,
        authority_public_key=Ed25519PublicKey.from_public_bytes(_decode(settings.credential_witness_root_key, 32)),
        minimum_revision=settings.credential_witness_min_revision)
    # Prove current configuration is usable before binding the management port.
    now = datetime.now(timezone.utc)
    trust.current_policy(now)
    witness.current_policy(now)
    service = DiscoveryIngestService(connect=connect, ingest_role=settings.postgres_role,
        tls_verifier=tls, signature_verifier=SignedDiscoveryIngestVerifier(trust, witness),
        evidence_sink=PrivateDiscoveryEvidenceSink(settings.evidence_root))
    return DiscoveryIngestServer((settings.bind_ip, settings.bind_port), service,
                                 max_connections=settings.max_connections)


def main() -> int:
    try:
        server = create_discovery_ingest_runtime(DiscoveryIngestSettings.from_environment())
    except Exception:
        raise SystemExit('Discovery ingestion configuration or authority is unavailable') from None
    if hasattr(signal, 'SIGHUP'):
        # Rotation replaces the pinned context. Existing sockets from the old
        # context are refused by MutualTlsWorkerVerifier on their next request.
        signal.signal(signal.SIGHUP, lambda *_: server.service.tls_verifier.reload_trust())
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
