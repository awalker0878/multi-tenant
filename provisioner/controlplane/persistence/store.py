"""Tenant-scoped PostgreSQL records and cooperative native-owner leases.

Only trusted server code may construct ``TenantContext`` and ``AuditContext``:
derive both from authenticated B07 principal evidence, never client JSON. The
connection factory must return a psycopg 3 connection using a dedicated runtime
role with no SUPERUSER/BYPASSRLS permission. Every method owns one transaction.
No native operation is authorized by possession of a database lease alone.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Iterator

from provisioner.domain.enterprise_records import (VerifiedBindingCutover,
                                                   VerifiedWsdTransition,
                                                   validate_record,
                                                   validate_workload_successor)


_IDS = {
    'Workload': 'workloadId', 'ApplicationGroup': 'applicationGroupId',
    'ObservationSnapshot': 'snapshotId', 'MigrationPlan': 'planId',
    'TransferManifest': 'transferId', 'ActivityResult': 'activityId',
}
_VERSIONED = {'Workload', 'ApplicationGroup', 'MigrationPlan'}
_ID_PATTERN = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$')


class RecordValidationError(ValueError):
    def __init__(self, problems: list[dict]):
        self.problems = problems
        super().__init__('Enterprise record validation failed')


class RecordNotFound(LookupError):
    """No record is visible within the verified tenant context."""


class RevisionConflict(RuntimeError):
    """The selected tenant record has advanced or already exists."""


class OwnershipConflict(RuntimeError):
    """A native identity is owned, or its lease is held, elsewhere."""


class LeaseConflict(RuntimeError):
    """The worker no longer holds the current lease epoch."""


@dataclass(frozen=True)
class TenantContext:
    organization_id: str
    tenant_id: str

    def __post_init__(self):
        if not _ID_PATTERN.fullmatch(self.organization_id) or not _ID_PATTERN.fullmatch(self.tenant_id):
            raise ValueError('Invalid trusted tenant context')


@dataclass(frozen=True)
class AuditContext:
    actor_id: str
    correlation_id: str

    def __post_init__(self):
        if (not isinstance(self.actor_id, str) or not 1 <= len(self.actor_id) <= 512
                or any(unicodedata.category(char) in {'Cc', 'Cf'} for char in self.actor_id)
                or not _ID_PATTERN.fullmatch(self.correlation_id)):
            raise ValueError('Invalid trusted audit context')


@dataclass(frozen=True)
class StoredRecord:
    record: dict
    revision: int
    digest: str


@dataclass(frozen=True)
class NativeBinding:
    platform_family: str
    endpoint_id: str
    native_scope_id: str
    resource_kind: str
    native_id: str

    @classmethod
    def from_record(cls, binding: dict) -> 'NativeBinding':
        if set(binding) != {'platformFamily', 'endpointId', 'nativeScopeId', 'resourceKind', 'nativeId'}:
            raise ValueError('Invalid native binding fields')
        return cls(binding['platformFamily'], binding['endpointId'],
                   binding['nativeScopeId'], binding['resourceKind'], binding['nativeId'])

    def __post_init__(self):
        if (self.platform_family not in {'vmware', 'nutanix', 'openstack'}
                or self.resource_kind not in {'vm', 'disk', 'nic', 'volume', 'dataset', 'network'}
                or not _ID_PATTERN.fullmatch(self.endpoint_id)
                or not self.native_scope_id or len(self.native_scope_id) > 512
                or not self.native_id or len(self.native_id) > 512):
            raise ValueError('Invalid native binding')

    def key(self) -> tuple[str, str, str, str, str]:
        return (self.platform_family, self.endpoint_id, self.native_scope_id,
                self.resource_kind, self.native_id)


@dataclass(frozen=True)
class OwnerLease:
    binding: NativeBinding
    organization_id: str
    tenant_id: str
    security_domain_id: str
    workload_id: str
    worker_id: str
    epoch: int
    expires_at: datetime


def _binding_seen_in_workload(record: dict, binding: NativeBinding) -> bool:
    def matches(candidate: dict) -> bool:
        return NativeBinding.from_record(candidate).key() == binding.key()

    for machine in record['spec']['machines']:
        for resource in (machine, *machine['disks'], *machine['nics']):
            if any(matches(history['binding']) for history in resource['bindings']):
                return True
    return any(matches(source) for dataset in record['spec']['datasets']
               for source in dataset['sourceBindings'])


def _encode(record: dict) -> tuple[str, str]:
    raw = json.dumps(record, sort_keys=True, separators=(',', ':'),
                     ensure_ascii=False, allow_nan=False)
    return raw, hashlib.sha256(raw.encode('utf-8')).hexdigest()


def canonical_record_digest(record: dict) -> str:
    """Digest of a complete canonical record, distinct from planDigest."""
    return _encode(record)[1]


def _decode(value) -> dict:
    return json.loads(value) if isinstance(value, str) else value


class EnterpriseRecordStore:
    """Run SQL as a non-bypass PostgreSQL runtime role, with local RLS context.

    ``connection_factory`` returns a fresh psycopg 3 connection. Connections
    are committed or rolled back and closed by their context manager. This API
    does not run migration DDL with the privileged runtime role.
    """

    def __init__(self, connection_factory: Callable):
        if not callable(connection_factory):
            raise TypeError('A PostgreSQL connection factory is required')
        self._connect = connection_factory

    @contextmanager
    def _session(self, ctx: TenantContext) -> Iterator:
        if not isinstance(ctx, TenantContext):
            raise TypeError('A trusted TenantContext is required')
        with self._connect() as connection:
            if connection.autocommit:
                raise RuntimeError('Control-plane transactions cannot use autocommit')
            role = connection.execute(
                'SELECT rolsuper, rolbypassrls FROM pg_catalog.pg_roles '
                'WHERE rolname = current_user').fetchone()
            if role is None or role[0] or role[1]:
                raise RuntimeError('Runtime role must enforce PostgreSQL row security')
            connection.execute(
                "SELECT set_config('app.organization_id', %s, true), "
                "set_config('app.tenant_id', %s, true)",
                (ctx.organization_id, ctx.tenant_id))
            yield connection

    @staticmethod
    def _identity(ctx: TenantContext, record: dict) -> tuple[str, str]:
        problems = validate_record(record)
        if problems:
            raise RecordValidationError(problems)
        metadata = record['metadata']
        if (metadata['organizationId'], metadata['tenantId']) != (ctx.organization_id, ctx.tenant_id):
            raise RecordNotFound('No record is visible in this tenant')
        kind = record['kind']
        return kind, metadata[_IDS[kind]]

    @staticmethod
    def _load(connection, ctx: TenantContext, kind: str, record_id: str,
              wsd_id: str | None = None, *, lock: bool = False) -> StoredRecord | None:
        query = (
            'SELECT revision, record_json, record_digest '
            'FROM hosting_controlplane.enterprise_records '
            'WHERE organization_id = %s AND tenant_id = %s '
            'AND record_kind = %s AND record_id = %s')
        args = [ctx.organization_id, ctx.tenant_id, kind, record_id]
        if wsd_id is not None:
            query += ' AND security_domain_id = %s'
            args.append(wsd_id)
        if lock:
            query += ' FOR SHARE'
        row = connection.execute(query, args).fetchone()
        return StoredRecord(_decode(row[1]), row[0], row[2]) if row else None

    @staticmethod
    def _audit(connection, ctx: TenantContext, audit: AuditContext, action: str,
               kind: str, record_id: str, revision: int, digest: str,
               details: dict | None = None) -> None:
        if not isinstance(audit, AuditContext):
            raise TypeError('A trusted AuditContext is required')
        connection.execute(
            'INSERT INTO hosting_controlplane.audit_events '
            '(organization_id, tenant_id, actor_id, correlation_id, action, '
            'record_kind, record_id, revision, record_digest, details) '
            'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)',
            (ctx.organization_id, ctx.tenant_id, audit.actor_id,
             audit.correlation_id, action, kind, record_id, revision,
             digest, json.dumps(details or {}, sort_keys=True)))

    @staticmethod
    def _check_links(connection, ctx: TenantContext, record: dict) -> None:
        kind = record['kind']
        if kind == 'MigrationPlan':
            workload = EnterpriseRecordStore._load(connection, ctx, 'Workload',
                                                   record['spec']['workloadId'], lock=True)
            if workload is None or workload.revision != record['spec']['workloadRevision']:
                raise RecordValidationError([{'path': '$.spec.workloadRevision',
                                              'message': 'Selected workload revision is unavailable'}])
            problems = validate_record(record, workload=workload.record)
        elif kind in {'TransferManifest', 'ActivityResult'}:
            metadata = record['metadata']
            plan = EnterpriseRecordStore._load(connection, ctx, 'MigrationPlan',
                                              metadata['planId'], lock=True)
            if (plan is None or plan.revision != metadata['planRevision']
                    or plan.record['metadata']['planDigest'] != metadata['planDigest']):
                raise RecordValidationError([{'path': '$.metadata.planId',
                                              'message': 'Bound plan revision is unavailable'}])
            problems = validate_record(record, plan=plan.record)
        else:
            problems = []
        if problems:
            raise RecordValidationError(problems)

    def create(self, ctx: TenantContext, record: dict, audit: AuditContext) -> StoredRecord:
        kind, record_id = self._identity(ctx, record)
        if not isinstance(audit, AuditContext):
            raise TypeError('A trusted AuditContext is required')
        if kind in _VERSIONED and record['metadata']['revision'] != 1:
            raise RevisionConflict('A new record must start at revision 1')
        raw, digest = _encode(record)
        with self._session(ctx) as connection:
            self._check_links(connection, ctx, record)
            try:
                connection.execute(
                    'INSERT INTO hosting_controlplane.enterprise_records '
                    '(organization_id, tenant_id, record_kind, record_id, revision, '
                    'record_json, record_digest) VALUES '
                    '(%s, %s, %s, %s, 1, %s::jsonb, %s)',
                    (ctx.organization_id, ctx.tenant_id, kind, record_id, raw, digest))
            except Exception as exc:
                if getattr(exc, 'sqlstate', None) == '23505':
                    raise RevisionConflict('Record already exists') from exc
                raise
            self._append_history(connection, ctx, kind, record_id, 1, raw, digest)
            self._audit(connection, ctx, audit, 'RECORD_CREATE', kind, record_id, 1, digest)
        return StoredRecord(record, 1, digest)

    @staticmethod
    def _append_history(connection, ctx: TenantContext, kind: str, record_id: str,
                        revision: int, raw: str, digest: str) -> None:
        connection.execute(
            'INSERT INTO hosting_controlplane.enterprise_record_history '
            '(organization_id, tenant_id, record_kind, record_id, revision, '
            'record_json, record_digest) VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)',
            (ctx.organization_id, ctx.tenant_id, kind, record_id, revision, raw, digest))

    def get(self, ctx: TenantContext, kind: str, record_id: str,
            *, wsd_id: str | None = None) -> StoredRecord | None:
        self._check_key(kind, record_id)
        self._check_wsd_filter(kind, wsd_id)
        with self._session(ctx) as connection:
            return self._load(connection, ctx, kind, record_id, wsd_id)

    @staticmethod
    def _check_key(kind: str, record_id: str) -> None:
        if kind not in _IDS or not isinstance(record_id, str) or not _ID_PATTERN.fullmatch(record_id):
            raise ValueError('Invalid enterprise record key')

    @staticmethod
    def _check_wsd_filter(kind: str, wsd_id: str | None) -> None:
        if wsd_id is not None and (kind != 'Workload' or not isinstance(wsd_id, str)
                                   or not _ID_PATTERN.fullmatch(wsd_id)):
            raise ValueError('WSD filter requires a valid Workload security domain')

    def list(self, ctx: TenantContext, kind: str, *, limit: int = 100,
             after: str | None = None,
             wsd_id: str | None = None) -> list[StoredRecord]:
        self._check_key(kind, after or 'first')
        self._check_wsd_filter(kind, wsd_id)
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 500:
            raise ValueError('Invalid page size')
        with self._session(ctx) as connection:
            query = (
                'SELECT revision, record_json, record_digest '
                'FROM hosting_controlplane.enterprise_records '
                'WHERE organization_id = %s AND tenant_id = %s AND record_kind = %s '
                'AND record_id > %s')
            args = [ctx.organization_id, ctx.tenant_id, kind, after or '']
            if wsd_id is not None:
                query += ' AND security_domain_id = %s'
                args.append(wsd_id)
            rows = connection.execute(query + ' ORDER BY record_id LIMIT %s',
                                      (*args, limit)).fetchall()
        return [StoredRecord(_decode(raw), revision, digest)
                for revision, raw, digest in rows]

    def update(self, ctx: TenantContext, record: dict, expected_revision: int,
               audit: AuditContext, *,
               verified_transition: VerifiedWsdTransition | None = None,
               verified_cutover: VerifiedBindingCutover | None = None,
               plan: dict | None = None) -> StoredRecord:
        with self._session(ctx) as connection:
            return self.update_in_transaction(connection, ctx, record, expected_revision,
                audit, verified_transition=verified_transition,
                verified_cutover=verified_cutover, plan=plan)

    def update_in_transaction(self, connection, ctx: TenantContext, record: dict,
               expected_revision: int, audit: AuditContext, *,
               verified_transition: VerifiedWsdTransition | None = None,
               verified_cutover: VerifiedBindingCutover | None = None,
               plan: dict | None = None) -> StoredRecord:
        """Use the existing owner in an already scoped, live atomic transaction.

        The caller must establish independent approval/evidence in this same
        transaction. Record identity, optimistic revision, history and audit
        checks are exactly those used by ``update``.
        """
        import psycopg
        if (not isinstance(connection, psycopg.Connection) or connection.autocommit
                or connection.info.transaction_status != psycopg.pq.TransactionStatus.INTRANS
                or not isinstance(ctx, TenantContext)):
            raise ValueError('A live trusted PostgreSQL record-owner transaction is required')
        role = connection.execute('SELECT rolsuper, rolbypassrls FROM pg_catalog.pg_roles '
                                 'WHERE rolname = current_user').fetchone()
        scoped = connection.execute("SELECT current_setting('app.organization_id', true), "
                                    "current_setting('app.tenant_id', true)").fetchone()
        if role is None or role[0] or role[1] or scoped != (ctx.organization_id, ctx.tenant_id):
            raise ValueError('The record-owner transaction must enforce its exact tenant row security')
        kind, record_id = self._identity(ctx, record)
        if kind not in _VERSIONED:
            raise ValueError('This record kind is immutable')
        if (not isinstance(expected_revision, int) or isinstance(expected_revision, bool)
                or expected_revision < 1):
            raise RevisionConflict('Expected revision must be positive')
        if record['metadata']['revision'] != expected_revision + 1:
            raise RevisionConflict('Revision must advance by one')
        raw, digest = _encode(record)
        previous = self._load(connection, ctx, kind, record_id)
        if previous is None:
            raise RecordNotFound('No record is visible in this tenant')
        if previous.revision != expected_revision:
            raise RevisionConflict('Record revision has changed')
        if kind == 'Workload':
            problems = validate_workload_successor(
                previous.record, record, verified_transition=verified_transition,
                verified_cutover=verified_cutover, plan=plan)
            if problems:
                raise RecordValidationError(problems)
        else:
            self._check_links(connection, ctx, record)
        row = connection.execute(
            'UPDATE hosting_controlplane.enterprise_records '
            'SET revision = %s, record_json = %s::jsonb, record_digest = %s, '
            'updated_at = clock_timestamp() '
            'WHERE organization_id = %s AND tenant_id = %s '
            'AND record_kind = %s AND record_id = %s AND revision = %s '
            'RETURNING revision',
            (expected_revision + 1, raw, digest, ctx.organization_id, ctx.tenant_id,
             kind, record_id, expected_revision)).fetchone()
        if row is None:
            raise RevisionConflict('Record revision changed during update')
        self._append_history(connection, ctx, kind, record_id, row[0], raw, digest)
        self._audit(connection, ctx, audit, 'RECORD_UPDATE', kind, record_id,
                    row[0], digest)
        return StoredRecord(record, row[0], digest)

    @staticmethod
    def _lease_scope(ctx: TenantContext, scope: dict, binding: NativeBinding) -> str:
        required = {'organizationId', 'tenantId', 'securityDomainId', 'endpointId',
                    'nativeScopeId', 'locationId', 'platformFamily'}
        if (not isinstance(scope, dict) or set(scope) != required
                or (scope['organizationId'], scope['tenantId']) !=
                (ctx.organization_id, ctx.tenant_id)
                or (scope['platformFamily'], scope['endpointId'], scope['nativeScopeId']) !=
                (binding.platform_family, binding.endpoint_id, binding.native_scope_id)
                or not _ID_PATTERN.fullmatch(scope['securityDomainId'])):
            raise OwnershipConflict('Native scope is not valid for this tenant')
        return scope['securityDomainId']

    @staticmethod
    def _ttl(ttl_seconds: int) -> None:
        if (not isinstance(ttl_seconds, int) or isinstance(ttl_seconds, bool)
                or not 1 <= ttl_seconds <= 3600):
            raise ValueError('Lease duration must be between 1 and 3600 seconds')

    def acquire_owner_lease(self, ctx: TenantContext, scope: dict,
                            binding: NativeBinding, workload_id: str,
                            worker_id: str, ttl_seconds: int,
                            audit: AuditContext) -> OwnerLease:
        self._ttl(ttl_seconds)
        if not isinstance(binding, NativeBinding):
            raise TypeError('NativeBinding is required')
        security_domain_id = self._lease_scope(ctx, scope, binding)
        if not _ID_PATTERN.fullmatch(workload_id) or not _ID_PATTERN.fullmatch(worker_id):
            raise ValueError('Invalid workload or worker identity')
        with self._session(ctx) as connection:
            from provisioner.controlplane.conversion.handover import require_write_admission
            with connection.cursor() as cursor:
                require_write_admission(cursor,ctx,security_domain_id=security_domain_id,workload_id=workload_id)
            workload = self._load(connection, ctx, 'Workload', workload_id, lock=True)
            if workload is None:
                raise RecordNotFound('No workload is visible in this tenant')
            if workload.record['metadata']['wsdId'] != security_domain_id:
                raise OwnershipConflict('Native scope differs from accepted workload security domain')
            if not _binding_seen_in_workload(workload.record, binding):
                raise OwnershipConflict('Native binding has not been observed on this workload')
            key = binding.key()
            row = connection.execute(
                'INSERT INTO hosting_controlplane.native_ownership '
                '(platform_family, endpoint_id, native_scope_id, resource_kind, native_id, '
                'organization_id, tenant_id, security_domain_id, workload_id, worker_id, '
                'lease_epoch, lease_expires_at) VALUES '
                '(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1, '
                "clock_timestamp() + make_interval(secs => %s)) "
                'ON CONFLICT DO NOTHING RETURNING lease_epoch, lease_expires_at',
                (*key, ctx.organization_id, ctx.tenant_id, security_domain_id,
                 workload_id, worker_id, ttl_seconds)).fetchone()
            if row is None:
                # An expired worker may still be mutating a native target. It
                # remains held until a separate reconciliation path proves
                # exclusion; only an explicit release can clear the lease.
                row = connection.execute(
                    'UPDATE hosting_controlplane.native_ownership '
                    'SET worker_id = %s, lease_epoch = lease_epoch + 1, '
                    'lease_expires_at = clock_timestamp() + make_interval(secs => %s), '
                    'updated_at = clock_timestamp() '
                    'WHERE platform_family = %s AND endpoint_id = %s AND native_scope_id = %s '
                    'AND resource_kind = %s AND native_id = %s '
                    'AND organization_id = %s AND tenant_id = %s '
                    'AND security_domain_id = %s AND workload_id = %s '
                    'AND lease_expires_at IS NULL '
                    'RETURNING lease_epoch, lease_expires_at',
                    (worker_id, ttl_seconds, *key, ctx.organization_id, ctx.tenant_id,
                     security_domain_id, workload_id)).fetchone()
            if row is None:
                raise OwnershipConflict('Native binding is owned or leased elsewhere')
            lease = OwnerLease(binding, ctx.organization_id, ctx.tenant_id,
                               security_domain_id, workload_id, worker_id, row[0], row[1])
            self._audit(connection, ctx, audit, 'LEASE_ACQUIRE', 'Workload', workload_id,
                        workload.revision, workload.digest,
                        {'epoch': lease.epoch, 'bindingDigest':
                         hashlib.sha256(repr(key).encode('utf-8')).hexdigest()})
            return lease

    def renew_owner_lease(self, ctx: TenantContext, lease: OwnerLease,
                          ttl_seconds: int, audit: AuditContext) -> OwnerLease:
        self._ttl(ttl_seconds)
        with self._session(ctx) as connection:
            from provisioner.controlplane.conversion.handover import require_write_admission
            with connection.cursor() as cursor:
                require_write_admission(cursor,ctx,security_domain_id=lease.security_domain_id,workload_id=lease.workload_id)
            workload = self._load(connection, ctx, 'Workload', lease.workload_id)
            if workload is None or (lease.organization_id, lease.tenant_id) != (
                    ctx.organization_id, ctx.tenant_id):
                raise LeaseConflict('Lease is not current in this tenant')
            row = connection.execute(
                'UPDATE hosting_controlplane.native_ownership '
                'SET lease_expires_at = clock_timestamp() + make_interval(secs => %s), '
                'updated_at = clock_timestamp() '
                'WHERE platform_family = %s AND endpoint_id = %s AND native_scope_id = %s '
                'AND resource_kind = %s AND native_id = %s '
                'AND organization_id = %s AND tenant_id = %s '
                'AND security_domain_id = %s AND workload_id = %s '
                'AND worker_id = %s AND lease_epoch = %s '
                'AND lease_expires_at > clock_timestamp() '
                'RETURNING lease_expires_at',
                (ttl_seconds, *lease.binding.key(), ctx.organization_id, ctx.tenant_id,
                 lease.security_domain_id, lease.workload_id, lease.worker_id,
                 lease.epoch)).fetchone()
            if row is None:
                raise LeaseConflict('Lease expired or its epoch changed')
            self._audit(connection, ctx, audit, 'LEASE_RENEW', 'Workload', lease.workload_id,
                        workload.revision, workload.digest, {'epoch': lease.epoch})
            return OwnerLease(lease.binding, lease.organization_id, lease.tenant_id,
                              lease.security_domain_id, lease.workload_id, lease.worker_id,
                              lease.epoch, row[0])

    def release_owner_lease(self, ctx: TenantContext, lease: OwnerLease,
                            audit: AuditContext) -> int:
        with self._session(ctx) as connection:
            workload = self._load(connection, ctx, 'Workload', lease.workload_id)
            if workload is None or (lease.organization_id, lease.tenant_id) != (
                    ctx.organization_id, ctx.tenant_id):
                raise LeaseConflict('Lease is not current in this tenant')
            row = connection.execute(
                'UPDATE hosting_controlplane.native_ownership '
                'SET worker_id = NULL, lease_expires_at = NULL, '
                'lease_epoch = lease_epoch + 1, updated_at = clock_timestamp() '
                'WHERE platform_family = %s AND endpoint_id = %s AND native_scope_id = %s '
                'AND resource_kind = %s AND native_id = %s '
                'AND organization_id = %s AND tenant_id = %s '
                'AND security_domain_id = %s AND workload_id = %s '
                'AND worker_id = %s AND lease_epoch = %s '
                'AND lease_expires_at > clock_timestamp() '
                'RETURNING lease_epoch',
                (*lease.binding.key(), ctx.organization_id, ctx.tenant_id,
                 lease.security_domain_id, lease.workload_id, lease.worker_id,
                 lease.epoch)).fetchone()
            if row is None:
                raise LeaseConflict('Lease expired or its epoch changed')
            self._audit(connection, ctx, audit, 'LEASE_RELEASE', 'Workload', lease.workload_id,
                        workload.revision, workload.digest, {'releasedEpoch': lease.epoch})
            return row[0]

    def has_current_owner_lease(self, ctx: TenantContext, lease: OwnerLease) -> bool:
        if (lease.organization_id, lease.tenant_id) != (ctx.organization_id, ctx.tenant_id):
            return False
        with self._session(ctx) as connection:
            row = connection.execute(
                'SELECT 1 FROM hosting_controlplane.native_ownership '
                'WHERE platform_family = %s AND endpoint_id = %s AND native_scope_id = %s '
                'AND resource_kind = %s AND native_id = %s '
                'AND organization_id = %s AND tenant_id = %s '
                'AND security_domain_id = %s AND workload_id = %s '
                'AND worker_id = %s AND lease_epoch = %s '
                'AND lease_expires_at > clock_timestamp()',
                (*lease.binding.key(), ctx.organization_id, ctx.tenant_id,
                 lease.security_domain_id, lease.workload_id, lease.worker_id,
                 lease.epoch)).fetchone()
            return row is not None
