"""Installed independent evidence checkpoint runner and mutation gate.

There is deliberately no file-backed deployed fallback. All production paths
require a separately administered Object Lock service and Vault Transit signer.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import stat
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping
from urllib.parse import urlsplit

import psycopg
from psycopg.conninfo import conninfo_to_dict

from provisioner.controlplane.persistence import TenantContext
from .audit import AuditCheckpointRepository
from .gate import EvidenceHold, EvidenceMutationGate
from .object_lock import S3ObjectLockArtifactStore, S3ObjectLockCheckpointStore
from .repository import EvidenceRepository
from .vault import VaultTransitClient, VaultTransitSigner, VaultTransitVerifier

_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$')


def _required(values: Mapping[str, str], name: str) -> str:
    value = values.get(name)
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f'{name} must be configured')
    return value


def _https_origin(value: str, label: str) -> str:
    parsed = urlsplit(value)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or
            parsed.password or parsed.path not in ('', '/') or parsed.query or
            parsed.fragment):
        raise ValueError(f'{label} must be a dedicated HTTPS origin')
    return value.rstrip('/')


def _private_file(path: Path) -> str:
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_CLOEXEC', 0)
    descriptor = os.open(path, flags)
    try:
        info = os.fstat(descriptor)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid not in (0, os.geteuid())
                or info.st_mode & 0o077 or info.st_size > 8192):
            raise ValueError('Evidence service credential file is not private')
        value = os.read(descriptor, 8193).decode('ascii').strip()
    finally:
        os.close(descriptor)
    if (not value or len(value) > 8192 or
            any(c.isspace() or ord(c) < 33 or ord(c) > 126 for c in value)):
        raise ValueError('Evidence service credential file is invalid')
    return value


@dataclass(frozen=True)
class EvidenceRuntimeConfig:
    postgres_dsn: str
    s3_endpoint: str
    s3_region: str
    s3_ca: Path
    s3_access_key_id: str
    s3_secret_file: Path
    artifact_bucket: str
    checkpoint_bucket: str
    retention_days: int
    vault_url: str
    vault_ca: Path
    vault_verify_token_file: Path
    vault_sign_token_file: Path | None
    vault_mount: str
    vault_key: str
    vault_key_id: str
    trusted_keys: Mapping[str, tuple[str, str]]
    max_unanchored_count: int
    s3_prefix: str = ''
    s3_kms_key_id: str | None = None
    scopes_file: Path | None = None

    @classmethod
    def from_environment(cls, values: Mapping[str, str] | None = None,
                         *, require_scopes: bool = False) -> 'EvidenceRuntimeConfig':
        env = os.environ if values is None else values
        try:
            trust = json.loads(_required(env, 'HOSTING_EVIDENCE_VAULT_TRUST_JSON'))
            if (not isinstance(trust, dict) or not trust or any(
                    not isinstance(label, str) or not isinstance(pair, list)
                    or len(pair) != 2 or not all(isinstance(item, str) and _NAME.fullmatch(item)
                                                   for item in pair)
                    for label, pair in trust.items())):
                raise ValueError('Vault trust list requires exact key labels and two path segments')
            trusted = {label: tuple(pair) for label, pair in trust.items()}
            retention_days = int(_required(env, 'HOSTING_EVIDENCE_RETENTION_DAYS'))
            max_lag = int(_required(env, 'HOSTING_EVIDENCE_MAX_UNANCHORED_COUNT'))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError('Evidence trust or retention configuration is invalid') from exc
        scope_path = env.get('HOSTING_EVIDENCE_SCOPES_FILE')
        if require_scopes and not scope_path:
            raise ValueError('HOSTING_EVIDENCE_SCOPES_FILE is required at API startup')
        return cls(
            postgres_dsn=_required(env, 'HOSTING_RUNTIME_DSN'),
            s3_endpoint=_required(env, 'HOSTING_EVIDENCE_S3_ENDPOINT'),
            s3_region=_required(env, 'HOSTING_EVIDENCE_S3_REGION'),
            s3_ca=Path(_required(env, 'HOSTING_EVIDENCE_S3_CA')),
            s3_access_key_id=_required(env, 'HOSTING_EVIDENCE_S3_ACCESS_KEY_ID'),
            s3_secret_file=Path(_required(env, 'HOSTING_EVIDENCE_S3_SECRET_FILE')),
            artifact_bucket=_required(env, 'HOSTING_EVIDENCE_ARTIFACT_BUCKET'),
            checkpoint_bucket=_required(env, 'HOSTING_EVIDENCE_CHECKPOINT_BUCKET'),
            retention_days=retention_days,
            vault_url=_required(env, 'HOSTING_EVIDENCE_VAULT_URL'),
            vault_ca=Path(_required(env, 'HOSTING_EVIDENCE_VAULT_CA')),
            vault_verify_token_file=Path(_required(
                env, 'HOSTING_EVIDENCE_VAULT_VERIFY_TOKEN_FILE')),
            vault_sign_token_file=Path(env['HOSTING_EVIDENCE_VAULT_SIGN_TOKEN_FILE'])
                if env.get('HOSTING_EVIDENCE_VAULT_SIGN_TOKEN_FILE') else None,
            vault_mount=_required(env, 'HOSTING_EVIDENCE_VAULT_MOUNT'),
            vault_key=_required(env, 'HOSTING_EVIDENCE_VAULT_KEY'),
            vault_key_id=_required(env, 'HOSTING_EVIDENCE_VAULT_KEY_ID'),
            trusted_keys=trusted,
            max_unanchored_count=max_lag,
            s3_prefix=env.get('HOSTING_EVIDENCE_S3_PREFIX', ''),
            s3_kms_key_id=env.get('HOSTING_EVIDENCE_S3_KMS_KEY_ID') or None,
            scopes_file=Path(scope_path) if scope_path else None,
        )

    def __post_init__(self) -> None:
        _https_origin(self.s3_endpoint, 'S3 endpoint')
        _https_origin(self.vault_url, 'Vault endpoint')
        settings = conninfo_to_dict(self.postgres_dsn)
        if (settings.get('sslmode') != 'verify-full' or not settings.get('host')
                or settings['host'].startswith('/') or ',' in settings['host']):
            raise ValueError('Evidence PostgreSQL connection requires verify-full TLS')
        if (self.artifact_bucket == self.checkpoint_bucket
                or type(self.retention_days) is not int or self.retention_days < 1
                or type(self.max_unanchored_count) is not int
                or self.max_unanchored_count < 0
                or not all(_NAME.fullmatch(name) for name in (
                    self.vault_mount, self.vault_key, self.vault_key_id))
                or self.vault_key_id not in self.trusted_keys
                or tuple(self.trusted_keys[self.vault_key_id]) != (
                    self.vault_mount, self.vault_key)):
            raise ValueError('Independent retention and Vault trust are required')

    def startup_scopes(self) -> tuple[TenantContext, ...]:
        if self.scopes_file is None:
            raise ValueError('Startup scope inventory is required')
        # This file carries scope names, not secrets, but may not be writable
        # by an unprivileged local user who could remove a startup check.
        descriptor = os.open(self.scopes_file, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
        try:
            info = os.fstat(descriptor)
            if (not stat.S_ISREG(info.st_mode) or info.st_mode & 0o022
                    or info.st_uid not in (0, os.geteuid())):
                raise ValueError('Startup scope inventory must be a protected file')
            if info.st_size > 1048576:
                raise ValueError('Startup scope inventory is too large')
            with os.fdopen(descriptor, 'rb', closefd=False) as source:
                raw = source.read(1048577)
        finally:
            os.close(descriptor)
        if len(raw) > 1048576:
            raise ValueError('Startup scope inventory is too large')
        scopes = json.loads(raw)
        if not isinstance(scopes, list) or len(scopes) > 10000:
            raise ValueError('Startup scope inventory must be a bounded list')
        result = []
        for scope in scopes:
            if not isinstance(scope, dict) or set(scope) != {'organizationId', 'tenantId'}:
                raise ValueError('Startup scope identity is invalid')
            result.append(TenantContext(scope['organizationId'], scope['tenantId']))
        if len(result) != len(set(result)):
            raise ValueError('Startup scope inventory contains duplicates')
        return tuple(result)


class _VerifyOnlySigner:
    key_id = 'verify-only'

    def sign(self, payload: bytes) -> bytes:
        raise EvidenceHold('Verification process has no signing credential')


def build_gate(config: EvidenceRuntimeConfig, *, s3_client=None,
               connection_factory: Callable | None = None,
               verifier_client: VaultTransitClient | None = None,
               signer_client: VaultTransitClient | None = None,
               allow_signing: bool = False) -> EvidenceMutationGate:
    if not isinstance(config, EvidenceRuntimeConfig):
        raise TypeError('Validated independent evidence configuration is required')
    if s3_client is None:
        import boto3
        from botocore.config import Config
        s3_client = boto3.client(
            's3', endpoint_url=config.s3_endpoint, region_name=config.s3_region,
            verify=str(config.s3_ca),
            aws_access_key_id=config.s3_access_key_id,
            aws_secret_access_key=_private_file(config.s3_secret_file),
            config=Config(signature_version='s3v4', connect_timeout=5,
                          read_timeout=10, retries={'max_attempts': 2}))
    if verifier_client is None:
        tls = ssl.create_default_context(cafile=str(config.vault_ca))
        tls.minimum_version = ssl.TLSVersion.TLSv1_2
        verifier_client = VaultTransitClient(
            config.vault_url,
            lambda: _private_file(config.vault_verify_token_file), tls_context=tls)
    if allow_signing:
        if config.vault_sign_token_file is None:
            raise ValueError('Independent signing identity must be configured for runner')
        if signer_client is None:
            tls = ssl.create_default_context(cafile=str(config.vault_ca))
            tls.minimum_version = ssl.TLSVersion.TLSv1_2
            signer_client = VaultTransitClient(
                config.vault_url,
                lambda: _private_file(config.vault_sign_token_file), tls_context=tls)
        signer = VaultTransitSigner(signer_client, key_id=config.vault_key_id,
                                    mount=config.vault_mount, key=config.vault_key)
    else:
        signer = _VerifyOnlySigner()
    verifier = VaultTransitVerifier(verifier_client, dict(config.trusted_keys))
    connect = connection_factory or (lambda: psycopg.connect(config.postgres_dsn,
                                                               connect_timeout=5))
    artifacts = S3ObjectLockArtifactStore(s3_client, config.artifact_bucket,
                                          retention_days=config.retention_days,
                                          prefix=config.s3_prefix,
                                          kms_key_id=config.s3_kms_key_id)
    checkpoints = S3ObjectLockCheckpointStore(
        s3_client, config.checkpoint_bucket, stream='evidence_entries',
        retention_days=config.retention_days, prefix=config.s3_prefix,
        kms_key_id=config.s3_kms_key_id)
    audits = S3ObjectLockCheckpointStore(
        s3_client, config.checkpoint_bucket, stream='audit_events',
        retention_days=config.retention_days, prefix=config.s3_prefix,
        kms_key_id=config.s3_kms_key_id)
    return EvidenceMutationGate(
        AuditCheckpointRepository(connect, audits, signer, verifier),
        EvidenceRepository(connect, artifacts, checkpoints, signer, verifier),
        max_unanchored_count=config.max_unanchored_count)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Independently retained evidence checkpoint')
    parser.add_argument('mode', choices=('inspect', 'enroll', 'verify', 'checkpoint', 'run'))
    parser.add_argument('--organization-id', required=True)
    parser.add_argument('--tenant-id', required=True)
    parser.add_argument('--expected-audit-sequence', type=int)
    parser.add_argument('--expected-audit-head')
    parser.add_argument('--interval-seconds', type=int, default=10)
    args = parser.parse_args(argv)
    if args.mode == 'run' and not 1 <= args.interval_seconds <= 60:
        parser.error('Checkpoint interval must be between 1 and 60 seconds')
    try:
        config = EvidenceRuntimeConfig.from_environment()
        gate = build_gate(config, allow_signing=args.mode in ('enroll', 'checkpoint', 'run'))
        context = TenantContext(args.organization_id, args.tenant_id)
        if args.mode == 'inspect':
            sequence, head = gate.audit.inspect_baseline(context)
            print(json.dumps({'auditSequence': sequence, 'auditHead': head}, sort_keys=True))
        elif args.mode == 'enroll':
            if args.expected_audit_sequence is None or args.expected_audit_head is None:
                raise ValueError('Enrollment requires independently attested audit sequence and head')
            gate.evidence.initialize(context)
            gate.audit.initialize(context, expected_sequence=args.expected_audit_sequence,
                                  expected_head_hash=args.expected_audit_head)
        elif args.mode == 'verify':
            gate.require(context)
        else:
            while True:
                gate.checkpoint(context)
                if args.mode == 'checkpoint':
                    break
                time.sleep(args.interval_seconds)
    except Exception:
        # Never echo DSNs, transport endpoints, tokens or artifact bytes.
        raise SystemExit('Independent evidence service is unavailable or held') from None
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
