"""Atomic admission, progress projection and a tenant-scoped PostgreSQL outbox.

The workflow history, not this table, owns workflow execution state. No method
here starts a workflow or contacts a native platform. Connection factories must
return a transaction-capable PostgreSQL connection configured with a non-
BYPASSRLS runtime role. The supplied authority checker must use the SAME cursor
and transaction to lock/recheck authoritative approval epochs and decisions.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Callable, Protocol
from uuid import uuid4

from provisioner.controlplane.authority.model import AuthorizedPlan, PlanScope
from provisioner.controlplane.persistence import TenantContext, canonical_record_digest
from provisioner.domain.enterprise_records import validate_record

_KEY = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$')


class AdmissionRefused(ValueError):
    """Current plan, scope or authority cannot be proven."""


class AdmissionConflict(ValueError):
    """Idempotency key or exact plan is already bound to another submission."""


class AdmissionAuthority(Protocol):
    def revalidate_admission(self, cursor, authorization: AuthorizedPlan,
                             at: datetime) -> None:
        """Check the authenticated actor and exact approval IDs/epoch under lock.

        Must raise on any mismatch or unavailable approval store. The caller's
        dataclass alone is NOT authority. Revocation writes must lock the same
        approval epoch row so admission and revocation serialize.
        """

    def revalidate_start(self, cursor, job: Job, at: datetime) -> None:
        """Fail closed when the exact plan, grant or epoch is no longer current."""


@dataclass(frozen=True)
class Job:
    organization_id: str
    tenant_id: str
    job_id: str
    idempotency_key: str
    plan_id: str
    plan_revision: int
    plan_digest: str
    source: PlanScope
    destination: PlanScope
    actor_subject: str
    approval_ids: tuple[str, ...]
    revocation_epoch: int
    status: str
    last_event_sequence: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class JobEvent:
    sequence: int
    event_key: str
    event_type: str
    status: str
    detail: dict
    recorded_at: datetime


@dataclass(frozen=True)
class OutboxMessage:
    outbox_id: str
    job_id: str
    payload: dict
    claim_token: str
    attempts: int


@dataclass(frozen=True)
class StartReceipt:
    """Acknowledged durable run returned by a trusted workflow adapter."""

    namespace: str
    workflow_id: str
    run_id: str
    job_id: str
    plan_id: str
    plan_revision: int
    plan_digest: str
    payload_digest: str


_JOB_COLUMNS = ('organization_id', 'tenant_id', 'job_id', 'idempotency_key',
                'plan_id', 'plan_revision', 'plan_digest', 'source_scope',
                'destination_scope', 'actor_subject',
                'approval_ids', 'revocation_epoch', 'status',
                'last_event_sequence', 'created_at', 'updated_at')
_JOB_SELECT = ', '.join(_JOB_COLUMNS)


def _json(value):
    return value if isinstance(value, (dict, list)) else json.loads(value)


def _digest(value: dict) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(',', ':'),
                           ensure_ascii=False, allow_nan=False).encode('utf-8')
    return hashlib.sha256(canonical).hexdigest()


def _job(row) -> Job:
    values = dict(zip(_JOB_COLUMNS, row))
    values['approval_ids'] = tuple(_json(values['approval_ids']))
    values['source'] = PlanScope(**_json(values.pop('source_scope')))
    values['destination'] = PlanScope(**_json(values.pop('destination_scope')))
    return Job(**values)


def _tenant(cursor, context) -> None:
    if not isinstance(context, TenantContext):
        raise TypeError('A trusted TenantContext is required')
    if cursor.connection.autocommit:
        raise RuntimeError('Job and outbox writes require a transaction')
    cursor.execute('SELECT rolsuper, rolbypassrls FROM pg_catalog.pg_roles '
                   'WHERE rolname = current_user')
    role = cursor.fetchone()
    if role is None or role[0] or role[1]:
        raise RuntimeError('Runtime role must enforce PostgreSQL row security')
    cursor.execute(
        "SELECT set_config('app.organization_id', %s, true), "
        "set_config('app.tenant_id', %s, true)",
        (context.organization_id, context.tenant_id))


def _ensure_plan(row, context, binding: AuthorizedPlan | Job) -> dict:
    if row is None:
        raise AdmissionRefused('The scoped plan does not exist')
    revision, record_digest, record = row
    record = _json(record)
    if not isinstance(record, dict) or validate_record(record):
        raise AdmissionRefused('The persisted plan is invalid')
    if canonical_record_digest(record) != record_digest:
        raise AdmissionRefused('The persisted plan digest is inconsistent')
    meta, spec = record['metadata'], record['spec']
    if (revision != binding.plan_revision
            or revision != meta['revision']
            or meta['planDigest'] != binding.plan_digest
            or meta['planId'] != binding.plan_id
            or meta['organizationId'] != context.organization_id
            or meta['tenantId'] != context.tenant_id
            or PlanScope.from_record(spec['source']) != binding.source
            or PlanScope.from_record(spec['destination']) != binding.destination):
        raise AdmissionRefused('The exact approved plan revision or scope changed')
    return record


def _ensure_workload(cursor, context, selected_plan: dict) -> None:
    """The approved plan must still describe the current observed workload."""
    workload_id = selected_plan['spec']['workloadId']
    cursor.execute(
        'SELECT revision, record_digest, record_json '
        'FROM hosting_controlplane.enterprise_records '
        'WHERE organization_id = %s AND tenant_id = %s '
        "AND record_kind = 'Workload' AND record_id = %s FOR SHARE",
        (context.organization_id, context.tenant_id, workload_id))
    row = cursor.fetchone()
    if row is None:
        raise AdmissionRefused('Current source workload is unavailable')
    revision, record_digest, raw = row
    workload = _json(raw)
    if (not isinstance(workload, dict) or revision != selected_plan['spec']['workloadRevision']
            or workload.get('kind') != 'Workload'
            or workload.get('metadata', {}).get('revision') != revision
            or workload.get('metadata', {}).get('workloadId') != workload_id
            or canonical_record_digest(workload) != record_digest
            or validate_record(workload)
            or validate_record(selected_plan, workload=workload)):
        raise AdmissionRefused('Workload revision or source binding changed; re-plan')


def _payload(authorization: AuthorizedPlan, job_id: str) -> dict:
    return {'format': 'hosting-workflow-start/1', 'job_id': job_id,
            'organization_id': authorization.organization_id,
            'tenant_id': authorization.tenant_id,
            'plan_id': authorization.plan_id,
            'plan_revision': authorization.plan_revision,
            'plan_digest': authorization.plan_digest,
            'revocation_epoch': authorization.revocation_epoch}


def _payload_from_job(job: Job) -> dict:
    return {'format': 'hosting-workflow-start/1', 'job_id': job.job_id,
            'organization_id': job.organization_id, 'tenant_id': job.tenant_id,
            'plan_id': job.plan_id, 'plan_revision': job.plan_revision,
            'plan_digest': job.plan_digest,
            'revocation_epoch': job.revocation_epoch}


class JobRepository:
    """PostgreSQL repository. Each public method owns one short transaction.

    The authentication service supplies AuthorizedPlan, and authority checks
    authoritative approval/revocation rows inside admission's transaction. A
    forged AuthorizedPlan must never be accepted from a transport.
    """

    def __init__(self, connect: Callable, authority: AdmissionAuthority):
        if not callable(connect) or authority is None or not callable(
                getattr(authority, 'revalidate_admission', None)) or not callable(
                getattr(authority, 'revalidate_start', None)):
            raise ValueError('A PostgreSQL connection and transactional authority are required')
        self._connect = connect
        self._authority = authority

    def submit(self, context, authorization: AuthorizedPlan, *,
               idempotency_key: str) -> Job:
        if not isinstance(authorization, AuthorizedPlan):
            raise AdmissionRefused('Trusted authorization is required')
        if (context.organization_id, context.tenant_id) != (
                authorization.organization_id, authorization.tenant_id):
            raise AdmissionRefused('Authorization does not match tenant scope')
        if not isinstance(idempotency_key, str) or not _KEY.fullmatch(idempotency_key):
            raise ValueError('Idempotency key must be a stable 1–128 character identifier')
        if not authorization.actor_subject or not authorization.approval_ids:
            raise AdmissionRefused('An authenticated actor and approvals are required')
        with self._connect() as connection:
            with connection.cursor() as cursor:
                _tenant(cursor, context)
                cursor.execute('SELECT clock_timestamp()')
                now = cursor.fetchone()[0]
                if authorization.expires_at.tzinfo is None or authorization.expires_at <= now:
                    raise AdmissionRefused('Authorization has expired')
                cursor.execute(
                    'SELECT revision, record_digest, record_json '
                    'FROM hosting_controlplane.enterprise_records '
                    'WHERE organization_id = %s AND tenant_id = %s '
                    "AND record_kind = 'MigrationPlan' AND record_id = %s FOR SHARE",
                    (context.organization_id, context.tenant_id, authorization.plan_id))
                selected_plan = _ensure_plan(cursor.fetchone(), context, authorization)
                _ensure_workload(cursor, context, selected_plan)
                # This check MUST lock the authoritative revocation/approval row.
                self._authority.revalidate_admission(cursor, authorization, now)
                job_id = uuid4().hex
                cursor.execute(
                    'INSERT INTO hosting_controlplane.operation_jobs '
                    '(organization_id, tenant_id, job_id, idempotency_key, plan_id, '
                    'plan_revision, plan_digest, source_scope, destination_scope, '
                    'actor_subject, approval_ids, revocation_epoch) '
                    'VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, '
                    '%s, %s::jsonb, %s) '
                    'ON CONFLICT DO NOTHING RETURNING job_id',
                    (context.organization_id, context.tenant_id, job_id,
                     idempotency_key, authorization.plan_id,
                     authorization.plan_revision, authorization.plan_digest,
                     json.dumps(asdict(authorization.source)),
                     json.dumps(asdict(authorization.destination)),
                     authorization.actor_subject,
                     json.dumps(authorization.approval_ids), authorization.revocation_epoch))
                inserted = cursor.fetchone()
                if inserted is None:
                    cursor.execute(
                        f'SELECT {_JOB_SELECT} FROM hosting_controlplane.operation_jobs '
                        'WHERE organization_id = %s AND tenant_id = %s '
                        'AND idempotency_key = %s FOR UPDATE',
                        (context.organization_id, context.tenant_id, idempotency_key))
                    existing = cursor.fetchone()
                    if existing is None:
                        raise AdmissionConflict('The exact plan has another idempotency key')
                    job = _job(existing)
                    if (job.plan_id, job.plan_revision, job.plan_digest,
                            job.source, job.destination, job.actor_subject,
                            job.approval_ids, job.revocation_epoch) != (
                            authorization.plan_id, authorization.plan_revision,
                            authorization.plan_digest, authorization.source,
                            authorization.destination, authorization.actor_subject,
                            authorization.approval_ids, authorization.revocation_epoch):
                        raise AdmissionConflict('Idempotency key was used for another submission')
                    return job
                cursor.execute(
                    'INSERT INTO hosting_controlplane.job_events '
                    '(organization_id, tenant_id, job_id, sequence, event_key, event_type, status) '
                    "VALUES (%s, %s, %s, 1, 'admitted', 'JOB_ADMITTED', 'QUEUED')",
                    (context.organization_id, context.tenant_id, job_id))
                cursor.execute(
                    'INSERT INTO hosting_controlplane.job_outbox '
                    '(organization_id, tenant_id, outbox_id, job_id, event_type, payload) '
                    "VALUES (%s, %s, %s, %s, 'START_WORKFLOW', %s::jsonb)",
                    (context.organization_id, context.tenant_id, uuid4().hex,
                     job_id, json.dumps(_payload(authorization, job_id))))
                cursor.execute(
                    f'SELECT {_JOB_SELECT} FROM hosting_controlplane.operation_jobs '
                    'WHERE organization_id = %s AND tenant_id = %s AND job_id = %s',
                    (context.organization_id, context.tenant_id, job_id))
                return _job(cursor.fetchone())

    def get(self, context, job_id: str) -> Job | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                _tenant(cursor, context)
                cursor.execute(
                    f'SELECT {_JOB_SELECT} FROM hosting_controlplane.operation_jobs '
                    'WHERE organization_id = %s AND tenant_id = %s AND job_id = %s',
                    (context.organization_id, context.tenant_id, job_id))
                row = cursor.fetchone()
                return _job(row) if row is not None else None

    def events(self, context, job_id: str, *, after_sequence: int = 0,
               limit: int = 100) -> tuple[JobEvent, ...]:
        if type(after_sequence) is not int or after_sequence < 0 or type(limit) is not int or not 1 <= limit <= 500:
            raise ValueError('Invalid progress cursor or page limit')
        with self._connect() as connection:
            with connection.cursor() as cursor:
                _tenant(cursor, context)
                cursor.execute(
                    'SELECT sequence, event_key, event_type, status, detail, recorded_at '
                    'FROM hosting_controlplane.job_events WHERE organization_id = %s '
                    'AND tenant_id = %s AND job_id = %s AND sequence > %s '
                    'ORDER BY sequence LIMIT %s',
                    (context.organization_id, context.tenant_id, job_id,
                     after_sequence, limit))
                return tuple(JobEvent(row[0], row[1], row[2], row[3],
                                      _json(row[4]), row[5]) for row in cursor.fetchall())

    def append_progress(self, context, job_id: str, *, event_key: str,
                        event_type: str, status: str, detail: dict) -> JobEvent:
        """Trusted workflow-event consumer only; event_key makes redelivery safe."""
        if (not isinstance(event_key, str) or not _KEY.fullmatch(event_key)
                or not isinstance(event_type, str) or not _KEY.fullmatch(event_type)
                or status not in ('WAITING_APPROVAL', 'RUNNING', 'HELD',
                                  'SUCCEEDED', 'FAILED', 'CANCELLED')
                or not isinstance(detail, dict)):
            raise ValueError('Invalid progress event')
        with self._connect() as connection:
            with connection.cursor() as cursor:
                _tenant(cursor, context)
                cursor.execute(
                    'SELECT status, last_event_sequence FROM hosting_controlplane.operation_jobs '
                    'WHERE organization_id = %s AND tenant_id = %s AND job_id = %s FOR UPDATE',
                    (context.organization_id, context.tenant_id, job_id))
                current = cursor.fetchone()
                if current is None:
                    raise KeyError('Unknown scoped job')
                cursor.execute(
                    'SELECT sequence, event_key, event_type, status, detail, recorded_at '
                    'FROM hosting_controlplane.job_events WHERE organization_id = %s '
                    'AND tenant_id = %s AND job_id = %s AND event_key = %s',
                    (context.organization_id, context.tenant_id, job_id, event_key))
                previous = cursor.fetchone()
                if previous is not None:
                    if (previous[2], previous[3], _json(previous[4])) != (event_type, status, detail):
                        raise AdmissionConflict('Progress event identity has different content')
                    return JobEvent(previous[0], previous[1], previous[2],
                                    previous[3], _json(previous[4]), previous[5])
                if current[0] in ('SUCCEEDED', 'FAILED', 'CANCELLED'):
                    raise AdmissionConflict('Terminal workflow projection cannot advance')
                if current[0] == 'HELD' and status not in ('HELD', 'CANCELLED'):
                    raise AdmissionConflict('Held workflow needs separate reviewed release')
                sequence = current[1] + 1
                cursor.execute(
                    'UPDATE hosting_controlplane.operation_jobs SET status = %s, '
                    'last_event_sequence = %s, updated_at = clock_timestamp() '
                    'WHERE organization_id = %s AND tenant_id = %s AND job_id = %s',
                    (status, sequence, context.organization_id, context.tenant_id, job_id))
                cursor.execute(
                    'INSERT INTO hosting_controlplane.job_events '
                    '(organization_id, tenant_id, job_id, sequence, event_key, '
                    'event_type, status, detail) VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb) '
                    'RETURNING recorded_at',
                    (context.organization_id, context.tenant_id, job_id,
                     sequence, event_key, event_type, status, json.dumps(detail)))
                return JobEvent(sequence, event_key, event_type, status, detail,
                                cursor.fetchone()[0])

    def claim_start(self, context, *, dispatcher_id: str,
                    lease_seconds: int = 30) -> OutboxMessage | None:
        if not isinstance(dispatcher_id, str) or not _KEY.fullmatch(dispatcher_id):
            raise ValueError('Dispatcher identity required')
        if type(lease_seconds) is not int or not 1 <= lease_seconds <= 3600:
            raise ValueError('Invalid claim duration')
        with self._connect() as connection:
            with connection.cursor() as cursor:
                _tenant(cursor, context)
                token = uuid4().hex
                cursor.execute(
                    'WITH due AS (SELECT o.organization_id, o.tenant_id, o.outbox_id '
                    'FROM hosting_controlplane.job_outbox o '
                    'JOIN hosting_controlplane.operation_jobs j ON '
                    'j.organization_id = o.organization_id AND j.tenant_id = o.tenant_id '
                    'AND j.job_id = o.job_id '
                    'WHERE o.organization_id = %s AND o.tenant_id = %s '
                    'AND o.delivered_at IS NULL '
                    'AND (o.claimed_until IS NULL OR o.claimed_until < clock_timestamp()) '
                    "AND j.status <> 'HELD' "
                    'ORDER BY o.created_at, o.outbox_id LIMIT 1 FOR UPDATE OF o SKIP LOCKED) '
                    'UPDATE hosting_controlplane.job_outbox o SET '
                    'claim_token = %s, claimed_by = %s, '
                    "claimed_until = clock_timestamp() + (%s * interval '1 second'), "
                    'attempts = o.attempts + 1 FROM due '
                    'WHERE o.organization_id = due.organization_id '
                    'AND o.tenant_id = due.tenant_id AND o.outbox_id = due.outbox_id '
                    'RETURNING o.outbox_id, o.job_id, o.payload, o.claim_token, o.attempts',
                    (context.organization_id, context.tenant_id,
                     token, dispatcher_id, lease_seconds))
                row = cursor.fetchone()
                if row is None:
                    return None
                return OutboxMessage(row[0], row[1], _json(row[2]), row[3], row[4])

    def revalidate_start(self, context, message: OutboxMessage) -> Job:
        """Check current plan and authority after claim, before external start.

        The worker must check again immediately before every native mutation:
        there is no atomic transaction with an external workflow service.
        """
        with self._connect() as connection:
            with connection.cursor() as cursor:
                _tenant(cursor, context)
                cursor.execute(
                    f'SELECT {_JOB_SELECT} FROM hosting_controlplane.operation_jobs '
                    'WHERE organization_id = %s AND tenant_id = %s AND job_id = %s FOR SHARE',
                    (context.organization_id, context.tenant_id, message.job_id))
                row = cursor.fetchone()
                if row is None:
                    raise AdmissionRefused('Unknown scoped job')
                job = _job(row)
                if job.status == 'HELD':
                    raise AdmissionRefused('Job is held')
                cursor.execute(
                    'SELECT payload, claim_token, claimed_until FROM '
                    'hosting_controlplane.job_outbox '
                    'WHERE organization_id = %s AND tenant_id = %s AND outbox_id = %s '
                    'AND job_id = %s AND delivered_at IS NULL FOR SHARE',
                    (context.organization_id, context.tenant_id,
                     message.outbox_id, message.job_id))
                claimed = cursor.fetchone()
                cursor.execute('SELECT clock_timestamp()')
                now = cursor.fetchone()[0]
                if (claimed is None or claimed[1] != message.claim_token
                        or claimed[2] <= now or _json(claimed[0]) != message.payload
                        or message.payload != _payload_from_job(job)):
                    raise AdmissionRefused('Outbox claim or immutable job binding changed')
                cursor.execute(
                    'SELECT revision, record_digest, record_json '
                    'FROM hosting_controlplane.enterprise_records '
                    'WHERE organization_id = %s AND tenant_id = %s '
                    "AND record_kind = 'MigrationPlan' AND record_id = %s FOR SHARE",
                    (context.organization_id, context.tenant_id, job.plan_id))
                selected_plan = _ensure_plan(cursor.fetchone(), context, job)
                _ensure_workload(cursor, context, selected_plan)
                self._authority.revalidate_start(cursor, job, now)
                return job

    def mark_started(self, context, message: OutboxMessage,
                     receipt: StartReceipt, *, namespace: str) -> bool:
        """Acknowledge only after workflow returned a matching durable receipt."""
        payload = message.payload
        if not isinstance(receipt, StartReceipt) or not namespace or (
                receipt.namespace, receipt.workflow_id, receipt.job_id,
                receipt.plan_id, receipt.plan_revision, receipt.plan_digest,
                receipt.payload_digest) != (
                namespace, message.job_id, message.job_id,
                payload['plan_id'], payload['plan_revision'],
                payload['plan_digest'], _digest(payload)) or not receipt.run_id:
            raise AdmissionConflict('Workflow receipt does not bind the exact outbox intent')
        with self._connect() as connection:
            with connection.cursor() as cursor:
                _tenant(cursor, context)
                cursor.execute(
                    'SELECT status, last_event_sequence FROM hosting_controlplane.operation_jobs '
                    'WHERE organization_id = %s AND tenant_id = %s AND job_id = %s FOR UPDATE',
                    (context.organization_id, context.tenant_id, message.job_id))
                current = cursor.fetchone()
                if current is None:
                    return False
                cursor.execute(
                    'UPDATE hosting_controlplane.job_outbox SET '
                    'delivered_at = clock_timestamp(), claim_token = NULL, '
                    'claimed_by = NULL, claimed_until = NULL '
                    'WHERE organization_id = %s AND tenant_id = %s AND outbox_id = %s '
                    'AND job_id = %s AND claim_token = %s AND delivered_at IS NULL '
                    'AND payload = %s::jsonb '
                    'AND claimed_until >= clock_timestamp() RETURNING job_id',
                    (context.organization_id, context.tenant_id,
                     message.outbox_id, message.job_id, message.claim_token,
                     json.dumps(message.payload)))
                if cursor.fetchone() is None:
                    return False
                status, sequence = current
                if status == 'HELD':
                    raise AdmissionConflict('Cannot acknowledge a held job')
                if status not in ('QUEUED', 'START_REQUESTED'):
                    # A workflow event may arrive before the start ACK is
                    # written. Its projection is authoritative for status;
                    # acknowledging the outbox must not append an event after
                    # a terminal result or rewind the observed status.
                    return True
                next_sequence = sequence + 1
                cursor.execute(
                    'UPDATE hosting_controlplane.operation_jobs SET status = %s, '
                    'last_event_sequence = %s, updated_at = clock_timestamp() '
                    'WHERE organization_id = %s AND tenant_id = %s AND job_id = %s',
                    ('STARTED', next_sequence, context.organization_id,
                     context.tenant_id, message.job_id))
                cursor.execute(
                    'INSERT INTO hosting_controlplane.job_events '
                    '(organization_id, tenant_id, job_id, sequence, event_key, event_type, status) '
                    "VALUES (%s, %s, %s, %s, 'workflow-start', 'WORKFLOW_START_ACCEPTED', %s)",
                    (context.organization_id, context.tenant_id,
                     message.job_id, next_sequence, 'STARTED'))
                return True

    def hold_start(self, context, message: OutboxMessage) -> bool:
        """Stop dispatch on failed authority recheck; no workflow is started."""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                _tenant(cursor, context)
                cursor.execute(
                    'SELECT status, last_event_sequence FROM hosting_controlplane.operation_jobs '
                    'WHERE organization_id = %s AND tenant_id = %s AND job_id = %s FOR UPDATE',
                    (context.organization_id, context.tenant_id, message.job_id))
                current = cursor.fetchone()
                if current is None or current[0] not in ('QUEUED', 'START_REQUESTED'):
                    return False
                cursor.execute(
                    'SELECT claim_token FROM hosting_controlplane.job_outbox '
                    'WHERE organization_id = %s AND tenant_id = %s AND outbox_id = %s '
                    'AND job_id = %s AND delivered_at IS NULL FOR UPDATE',
                    (context.organization_id, context.tenant_id,
                     message.outbox_id, message.job_id))
                row = cursor.fetchone()
                if row is None or row[0] != message.claim_token:
                    return False
                _, sequence = current
                cursor.execute(
                    "UPDATE hosting_controlplane.operation_jobs SET status = 'HELD', "
                    'last_event_sequence = %s, updated_at = clock_timestamp() '
                    'WHERE organization_id = %s AND tenant_id = %s AND job_id = %s',
                    (sequence + 1, context.organization_id, context.tenant_id, message.job_id))
                cursor.execute(
                    'INSERT INTO hosting_controlplane.job_events '
                    '(organization_id, tenant_id, job_id, sequence, event_key, event_type, status) '
                    "VALUES (%s, %s, %s, %s, 'start-authority-hold', 'AUTHORITY_HOLD', 'HELD')",
                    (context.organization_id, context.tenant_id,
                     message.job_id, sequence + 1))
                return True
