"""Two-process PostgreSQL outbox + self-hosted Temporal restart gate.

Prepare commits an admitted job, records the external start attempt, starts a
Temporal run, then deliberately exits before its database ACK. CI restarts the
Temporal service without deleting either database. Recover retries from a new
dispatcher, pins the original run, executes the read-only authority gate and
projects its result without a native platform action.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import psycopg
from temporalio.client import Client
from temporalio.service import RPCError, RPCStatusCode
from temporalio.worker import Worker

from provisioner.controlplane.authority.model import AuthorizedPlan, FrozenPlan, PlanApproval
from provisioner.controlplane.authority.postgres import PostgresAuthority
from provisioner.controlplane.authority import postgres as authority_postgres
from provisioner.controlplane.jobs import JobRepository, OutboxDispatcher
from provisioner.controlplane.jobs.repository import _tenant
from provisioner.controlplane.persistence import AuditContext, EnterpriseRecordStore, TenantContext
from provisioner.controlplane.workflow.admitted_job import AdmittedMigrationJob
from provisioner.controlplane.workflow.approval_activity import PostgresApprovalVerifier
from provisioner.controlplane.workflow.approval_gate import GateResult
from provisioner.controlplane.workflow.runtime import project_one
from provisioner.controlplane.workflow.temporal_adapter import (
    TemporalConnection, TemporalWorkflowStarter)
from tests.provisioning.schema.test_enterprise_records import plan, workload
from tests.provisioning.workflow.temporal_recovery_gate import (
    _ready, _start_after_namespace_cache)
from provisioner.domain.enterprise_records import plan_digest


def _connect():
    return psycopg.connect(os.environ['HOSTING_TEST_POSTGRES_RUNTIME_DSN'])


def _authority_connect():
    return psycopg.connect(os.environ['HOSTING_TEST_POSTGRES_AUTHORITY_DSN'])


def _starter(address: str, queue: str) -> TemporalWorkflowStarter:
    return TemporalWorkflowStarter(TemporalConnection(
        address, 'default', queue, insecure_loopback_for_tests=True))


def _admit() -> tuple[TenantContext, JobRepository, str]:
    suffix = uuid4().hex
    ctx = TenantContext('org-' + suffix, 'tenant-' + suffix)
    audit = AuditContext('plan-author', 'temporal-gate-' + suffix)
    observed, selected = deepcopy(workload()), deepcopy(plan())
    for item in (observed, selected):
        item['metadata'].update(organizationId=ctx.organization_id,
                                tenantId=ctx.tenant_id)
    observed['metadata']['workloadId'] = 'workload-' + suffix
    selected['metadata']['planId'] = 'plan-' + suffix
    selected['spec']['workloadId'] = observed['metadata']['workloadId']
    for scope in (selected['spec']['source'], selected['spec']['destination']):
        scope.update(organizationId=ctx.organization_id, tenantId=ctx.tenant_id)
    selected['metadata']['planDigest'] = plan_digest(selected)
    store = EnterpriseRecordStore(_connect)
    store.create(ctx, observed, audit)
    store.create(ctx, selected, audit)
    frozen = FrozenPlan.from_record(selected, author_subject=audit.actor_id)
    authority = PostgresAuthority(_authority_connect)
    now = datetime.now(timezone.utc)
    approvals = []
    for index, (role, scope) in enumerate((
            ('SOURCE_OWNER', frozen.source),
            ('DESTINATION_OWNER', frozen.destination),
            ('SOURCE_SECURITY', frozen.source),
            ('DESTINATION_SECURITY', frozen.destination))):
        approval = PlanApproval(
            'gate-approval-' + uuid4().hex, ctx.organization_id, ctx.tenant_id,
            frozen.plan_id, frozen.revision, frozen.digest, role, scope,
            f'gate-reviewer-{index}', now - timedelta(minutes=1),
            now + timedelta(hours=2), 0)
        authority.append_if_current(frozen, approval, 0)
        approvals.append(approval.approval_id)
    authorized = AuthorizedPlan(
        ctx.organization_id, ctx.tenant_id, frozen.plan_id,
        frozen.revision, frozen.digest, frozen.source, frozen.destination,
        tuple(approvals), 0, now + timedelta(seconds=30), 'gate-operator')
    jobs = JobRepository(_connect, authority_postgres)
    job = jobs.submit(ctx, authorized, idempotency_key='gate-' + suffix)
    if len(jobs.events(ctx, job.job_id)) != 1:
        raise RuntimeError('Admission failed to atomically create the first event')
    return ctx, jobs, job.job_id


def _prepare(address: str, state: Path) -> None:
    asyncio.run(_ready(address))
    ctx, jobs, job_id = _admit()
    queue = 'gate-' + uuid4().hex
    starter = _starter(address, queue)
    message = jobs.claim_start(ctx, dispatcher_id='gate-before-crash',
                               lease_seconds=300)
    if message is None or message.job_id != job_id:
        raise RuntimeError('Committed outbox intent was not claimable')
    jobs.revalidate_start(ctx, message)
    jobs.record_start_attempt(ctx, message, namespace='default',
                              retention_seconds=86400)
    receipt = asyncio.run(_start_after_namespace_cache(starter, message.payload))
    if jobs.start_run(ctx, job_id) is not None:
        raise RuntimeError('Run was acknowledged before the simulated crash')
    # The process ends here: no mark_started call, no Worker, no native action.
    state.write_text(json.dumps({
        'organization_id': ctx.organization_id, 'tenant_id': ctx.tenant_id,
        'job_id': job_id, 'outbox_id': message.outbox_id,
        'task_queue': queue, 'run_id': receipt.run_id,
    }, sort_keys=True))


async def _complete(address: str, queue: str, job_id: str, run_id: str) -> GateResult:
    client = await Client.connect(address, namespace='default')
    handle = client.get_workflow_handle(job_id, run_id=run_id, result_type=GateResult)
    verifier = PostgresApprovalVerifier(_connect, authority_postgres)
    with ThreadPoolExecutor(max_workers=2) as pool:
        async with Worker(client, task_queue=queue, workflows=[AdmittedMigrationJob],
                          activities=[verifier.verify_job], activity_executor=pool):
            return await asyncio.wait_for(handle.result(), timeout=45)


def _recover(address: str, state: Path) -> None:
    asyncio.run(_ready(address))
    saved = json.loads(state.read_text())
    ctx = TenantContext(saved['organization_id'], saved['tenant_id'])
    jobs = JobRepository(_connect, authority_postgres)
    starter = _starter(address, saved['task_queue'])
    def expire_claim() -> None:
        with _connect() as connection, connection.cursor() as cursor:
            _tenant(cursor, ctx)
            cursor.execute(
                'UPDATE hosting_controlplane.job_outbox SET '
                "claimed_until = clock_timestamp() - interval '1 second' "
                'WHERE organization_id = %s AND tenant_id = %s AND outbox_id = %s '
                'AND delivered_at IS NULL',
                (ctx.organization_id, ctx.tenant_id, saved['outbox_id']))
            if cursor.rowcount != 1:
                raise RuntimeError('The unacknowledged outbox attempt was lost')
    expire_claim()
    # A fresh dispatcher process repeats the exact durable start after the
    # service restart. Temporal describes the retained run and validates memo.
    dispatcher = OutboxDispatcher(
        jobs, starter, dispatcher_id='gate-after-restart', namespace='default',
        start_history_retention_seconds=86400)
    for _ in range(60):
        try:
            result = dispatcher.run_one(ctx)
            break
        except RPCError as exc:
            if (exc.status != RPCStatusCode.NOT_FOUND or
                    'Namespace default is not found' not in exc.message):
                raise
            # Only the observed namespace-cache delay is retried. Expire the
            # claim explicitly, retaining the same first-attempt binding.
            time.sleep(1)
            expire_claim()
    else:
        raise RuntimeError('Temporal namespace was not ready after restart')
    if result is None or result.disposition != 'STARTED':
        raise RuntimeError('Uncertain outbox start was not reconciled')
    bound = jobs.start_run(ctx, saved['job_id'])
    if bound is None or bound.run_id != saved['run_id']:
        raise RuntimeError('Duplicate dispatch changed the pinned Temporal run')
    repeated = starter.start(namespace='default', workflow_id=saved['job_id'],
                             payload={'format': 'hosting-workflow-start/1',
                                      'job_id': saved['job_id'],
                                      'organization_id': ctx.organization_id,
                                      'tenant_id': ctx.tenant_id,
                                      'plan_id': bound.plan_id,
                                      'plan_revision': bound.plan_revision,
                                      'plan_digest': bound.plan_digest,
                                      'revocation_epoch': 0})
    if repeated != bound:
        raise RuntimeError('A duplicate workflow start created a different run')
    with _connect() as connection, connection.cursor() as cursor:
        _tenant(cursor, ctx)
        cursor.execute(
            'SELECT attempts, start_run_id, start_namespace, delivered_at '
            'FROM hosting_controlplane.job_outbox WHERE organization_id = %s '
            'AND tenant_id = %s AND outbox_id = %s',
            (ctx.organization_id, ctx.tenant_id, saved['outbox_id']))
        attempts, run_id, namespace, delivered = cursor.fetchone()
    if attempts < 2 or (run_id, namespace) != (saved['run_id'], 'default') or delivered is None:
        raise RuntimeError('Run receipt was not durably bound to the one outbox row')
    gate = asyncio.run(_complete(address, saved['task_queue'],
                                 saved['job_id'], saved['run_id']))
    if gate.status != 'GATE_PASSED':
        raise RuntimeError('Replayed admitted job did not revalidate PostgreSQL authority')
    if not project_one(jobs, starter, ctx, saved['job_id']):
        raise RuntimeError('Completed Temporal gate was not projected')
    events = jobs.events(ctx, saved['job_id'])
    if (jobs.get(ctx, saved['job_id']).status != 'HELD'
            or [event.event_type for event in events] !=
            ['JOB_ADMITTED', 'WORKFLOW_START_ACCEPTED',
             'GATE_PASSED_EXECUTION_HELD']):
        raise RuntimeError('Workflow projection rewound or skipped progress')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('prepare', 'recover'))
    parser.add_argument('--address', default='127.0.0.1:7233')
    parser.add_argument('--state', type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get('HOSTING_TEST_POSTGRES_ISOLATED') != '1':
        raise RuntimeError('The combined gate requires a disposable PostgreSQL database')
    if args.phase == 'prepare':
        _prepare(args.address, args.state)
    else:
        _recover(args.address, args.state)


if __name__ == '__main__':
    main()
