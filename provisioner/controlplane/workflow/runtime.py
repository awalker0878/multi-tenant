"""Installed-package Temporal worker, outbox dispatcher and result projector.

Each dispatcher/projector instance is bound to one verified tenant context.
The worker handles a read-only approval gate and has no native platform API.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg
from temporalio.client import Client
from temporalio.worker import Worker

from provisioner.controlplane.authority import postgres as authority_postgres
from provisioner.controlplane.jobs import JobRepository, OutboxDispatcher
from provisioner.controlplane.evidence.runtime import (EvidenceRuntimeConfig,
                                                      build_gate)
from provisioner.controlplane.evidence.gate import EvidenceHold
from provisioner.controlplane.jobs.repository import _tenant
from provisioner.controlplane.persistence import TenantContext

from .admitted_job import AdmittedMigrationJob
from .approval_activity import PostgresApprovalVerifier
from .temporal_adapter import TemporalConnection, TemporalWorkflowStarter


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f'{name} must be configured')
    return value


def _settings() -> TemporalConnection:
    testing = os.environ.get('HOSTING_TEMPORAL_INSECURE_LOOPBACK_TEST') == '1'
    return TemporalConnection(
        _required('HOSTING_TEMPORAL_ADDRESS'), _required('HOSTING_TEMPORAL_NAMESPACE'),
        _required('HOSTING_TEMPORAL_TASK_QUEUE'),
        server_ca=Path(os.environ['HOSTING_TEMPORAL_CA']) if not testing else None,
        client_cert=Path(os.environ['HOSTING_TEMPORAL_CLIENT_CERT']) if not testing else None,
        client_key=Path(os.environ['HOSTING_TEMPORAL_CLIENT_KEY']) if not testing else None,
        server_name=os.environ.get('HOSTING_TEMPORAL_SERVER_NAME'),
        insecure_loopback_for_tests=testing,
        rpc_timeout_seconds=int(os.environ.get('HOSTING_TEMPORAL_RPC_TIMEOUT_SECONDS', '10')))


def _connect():
    return psycopg.connect(_required('HOSTING_WORKFLOW_POSTGRES_DSN'))


async def _worker(settings: TemporalConnection) -> None:
    verifier = PostgresApprovalVerifier(_connect, authority_postgres)
    client = await Client.connect(settings.target_host, namespace=settings.namespace,
                                  tls=settings.tls())
    with ThreadPoolExecutor(max_workers=8) as executor:
        worker = Worker(client, task_queue=settings.task_queue,
                        workflows=[AdmittedMigrationJob],
                        activities=[verifier.verify_job], activity_executor=executor)
        await worker.run()


def _pending_jobs(context: TenantContext, *, limit: int = 32) -> tuple[str, ...]:
    with _connect() as connection, connection.cursor() as cursor:
        _tenant(cursor, context)
        cursor.execute(
            'SELECT j.job_id FROM hosting_controlplane.operation_jobs j '
            'JOIN hosting_controlplane.job_outbox o '
            'ON (j.organization_id, j.tenant_id, j.job_id) = '
            '(o.organization_id, o.tenant_id, o.job_id) '
            'WHERE j.organization_id = %s AND j.tenant_id = %s '
            "AND j.status = 'STARTED' AND o.delivered_at IS NOT NULL "
            'AND o.start_run_id IS NOT NULL ORDER BY j.created_at LIMIT %s',
            (context.organization_id, context.tenant_id, limit))
        return tuple(row[0] for row in cursor.fetchall())


def project_one(jobs: JobRepository, workflow: TemporalWorkflowStarter,
                context: TenantContext, job_id: str) -> bool:
    """Idempotently project a pinned gate result; leave pending runs alone.

    Even a passed gate is HELD while there is no implemented native execution
    graph. A gate result does not mean a workload was moved or provisioned.
    """
    receipt = jobs.start_run(context, job_id)
    if receipt is None:
        return False
    result = workflow.completed_gate(receipt)
    if result is None:
        return False
    passed = result.status == 'GATE_PASSED'
    jobs.append_progress(
        context, job_id, event_key=f'temporal-gate:{receipt.run_id}',
        event_type='GATE_PASSED_EXECUTION_HELD' if passed else 'GATE_HELD',
        status='HELD',
        detail={'stepId': 'approval-gate', 'phase': 'APPROVAL',
                'reasonCode': 'OPERATOR_HOLD' if passed else 'UNKNOWN'})
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Scoped Temporal control-plane runtime')
    parser.add_argument('mode', choices=('worker', 'dispatch', 'project'))
    parser.add_argument('--organization-id')
    parser.add_argument('--tenant-id')
    parser.add_argument('--dispatcher-id')
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args(argv)
    settings = _settings()
    if args.mode == 'worker':
        asyncio.run(_worker(settings))
        return 0
    if not args.organization_id or not args.tenant_id:
        parser.error('dispatch and project require exact organization and tenant IDs')
    context = TenantContext(args.organization_id, args.tenant_id)
    jobs = JobRepository(_connect, authority_postgres)
    workflow = TemporalWorkflowStarter(settings)
    try:
        evidence_config = EvidenceRuntimeConfig.from_environment()
        if evidence_config.postgres_dsn != _required('HOSTING_WORKFLOW_POSTGRES_DSN'):
            raise ValueError('Workflow and evidence database roles must match')
        gate = build_gate(evidence_config)
        gate.require(context)
    except Exception:
        raise SystemExit('Workflow signed evidence configuration is unavailable') from None
    if args.mode == 'dispatch':
        if not args.dispatcher_id:
            parser.error('dispatch requires a stable dispatcher ID')
        dispatcher = OutboxDispatcher(
            jobs, workflow, dispatcher_id=args.dispatcher_id,
            namespace=settings.namespace,
            start_history_retention_seconds=int(_required('HOSTING_TEMPORAL_START_RETENTION_SECONDS')),
            evidence_guard=gate.require)
    try:
        while True:
            if args.mode == 'dispatch':
                result = dispatcher.run_one(context)
                busy = result is not None
            else:
                gate.require(context)
                busy = any(project_one(jobs, workflow, context, job_id)
                           for job_id in _pending_jobs(context))
            if args.once:
                return 0
            if not busy:
                time.sleep(1)
    except KeyboardInterrupt:
        return 0
    except EvidenceHold:
        raise SystemExit('Workflow mutations held by independent evidence') from None


if __name__ == '__main__':
    raise SystemExit(main())
