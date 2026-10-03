"""Installed-package Temporal worker, outbox dispatcher and result projector.

Each dispatcher/projector instance is bound to one verified tenant context.
Existing gate histories keep their original workflow type. The separately
selected application graph requires explicit installed runtime composition.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import psycopg
from temporalio.client import Client
from temporalio.common import VersioningBehavior, WorkerDeploymentVersion
from temporalio.worker import Worker, WorkerDeploymentConfig

from provisioner.controlplane.authority import postgres as authority_postgres
from provisioner.controlplane.jobs import JobRepository, OutboxDispatcher
from provisioner.controlplane.evidence.runtime import (EvidenceRuntimeConfig,
                                                      build_gate)
from provisioner.controlplane.evidence.gate import EvidenceHold
from provisioner.controlplane.jobs.repository import _tenant
from provisioner.controlplane.persistence import TenantContext

from .admitted_job import AdmittedMigrationJob
from .application_job import ApplicationJobResult, OpenStackApplicationMigration
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
    return psycopg.connect(_required('HOSTING_WORKFLOW_POSTGRES_DSN'),
                           connect_timeout=5)


def _worker_deployment_config() -> WorkerDeploymentConfig:
    """Pin executions to one immutable release until that version drains."""
    name = _required('HOSTING_TEMPORAL_WORKER_DEPLOYMENT')
    build_id = _required('HOSTING_TEMPORAL_WORKER_BUILD_ID')
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9._-]{0,63}', name):
        raise ValueError('Temporal Worker deployment name must be a bounded identifier')
    if not re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', build_id):
        raise ValueError('Temporal Worker build ID must be a full immutable commit or digest')
    return WorkerDeploymentConfig(
        version=WorkerDeploymentVersion(deployment_name=name, build_id=build_id),
        use_worker_versioning=True,
        default_versioning_behavior=VersioningBehavior.PINNED)


async def _worker(settings: TemporalConnection, *, application_components=None) -> None:
    deployment = _worker_deployment_config()
    verifier = PostgresApprovalVerifier(_connect, authority_postgres)
    from .application_runtime import application_execution_enabled, build_application_worker_components
    if application_components is None and application_execution_enabled():
        evidence_config = EvidenceRuntimeConfig.from_environment()
        if evidence_config.postgres_dsn != _required('HOSTING_WORKFLOW_POSTGRES_DSN'):
            raise ValueError('Application workflow and evidence database roles must match')
        application_components = build_application_worker_components(_connect, build_gate(evidence_config))
    workflows, activities = [AdmittedMigrationJob], [verifier.verify_job]
    if application_components is not None:
        from .application_runtime import ApplicationWorkerComponents
        if not isinstance(application_components, ApplicationWorkerComponents):
            raise TypeError('Actual installed application worker components required')
        application_components.settings.require_current()
        workflows.append(OpenStackApplicationMigration)
        activities.extend(application_components.activities)
    client = await Client.connect(settings.target_host, namespace=settings.namespace,
                                  tls=settings.tls())
    with ThreadPoolExecutor(max_workers=8) as executor:
        worker = Worker(client, task_queue=settings.task_queue,
                        workflows=workflows,
                        activities=activities, activity_executor=executor,
                        deployment_config=deployment)
        await worker.run()


@dataclass(frozen=True)
class ProjectionCursor:
    """Immutable job ordering key; status changes never move the scan boundary."""
    created_at: datetime
    job_id: str

    def __post_init__(self):
        if (not isinstance(self.created_at, datetime)
                or self.created_at.tzinfo is None
                or not isinstance(self.job_id, str) or not self.job_id):
            raise ValueError('Projection cursor requires an exact timestamp and job ID')


@dataclass(frozen=True)
class ProjectionBatch:
    checked: int
    progressed: bool
    next_cursor: ProjectionCursor | None


def _pending_jobs(context: TenantContext, *, limit: int = 32,
                  after: ProjectionCursor | None = None) -> tuple[ProjectionCursor, ...]:
    if type(limit) is not int or not 1 <= limit <= 128:
        raise ValueError('Projection page size must be between 1 and 128')
    if after is not None and not isinstance(after, ProjectionCursor):
        raise TypeError('An immutable projection cursor is required')
    query = (
        'SELECT j.job_id, j.created_at FROM hosting_controlplane.operation_jobs j '
        'JOIN hosting_controlplane.job_outbox o '
        'ON (j.organization_id, j.tenant_id, j.job_id) = '
        '(o.organization_id, o.tenant_id, o.job_id) '
        'WHERE j.organization_id = %s AND j.tenant_id = %s '
        "AND j.status = 'STARTED' AND o.delivered_at IS NOT NULL "
        'AND o.start_run_id IS NOT NULL ')
    parameters = [context.organization_id, context.tenant_id]
    if after is not None:
        query += 'AND (j.created_at, j.job_id) > (%s, %s) '
        parameters.extend((after.created_at, after.job_id))
    query += 'ORDER BY j.created_at, j.job_id LIMIT %s'
    parameters.append(limit)
    with _connect() as connection, connection.cursor() as cursor:
        _tenant(cursor, context)
        cursor.execute(query, tuple(parameters))
        return tuple(ProjectionCursor(row[1], row[0]) for row in cursor.fetchall())


def project_one(jobs: JobRepository, workflow: TemporalWorkflowStarter,
                context: TenantContext, job_id: str) -> bool:
    """Idempotently project a pinned gate result; leave pending runs alone.

    Even a passed gate is HELD while there is no implemented native execution
    graph. A gate result does not mean a workload was moved or provisioned.
    """
    receipt = jobs.start_run(context, job_id)
    if receipt is None:
        return False
    result = workflow.completed_job(receipt)
    if result is None:
        return False
    if isinstance(result, ApplicationJobResult):
        detail = {'stepId': {'APPROVAL': 'approval-gate', 'PREPARE': 'prepare',
            'PROVISION': 'provision', 'TRANSFER': 'transfer', 'CUTOVER': 'cutover',
            'VERIFY': 'verify'}[result.phase], 'phase': result.phase,
            'reasonCode': result.reason_code, 'completed': result.completed, 'total': result.total}
        if result.evidence_digest is not None:
            detail['evidenceDigest'] = result.evidence_digest
        if result.hold_code is not None:
            detail['holdCode'] = result.hold_code
        jobs.append_progress(context, job_id, event_key=f'temporal-application:{receipt.run_id}',
            event_type='APPLICATION_EXECUTION_HELD', status='HELD', detail=detail)
        return True
    passed = result.status == 'GATE_PASSED'
    jobs.append_progress(
        context, job_id, event_key=f'temporal-gate:{receipt.run_id}',
        event_type='GATE_PASSED_EXECUTION_HELD' if passed else 'GATE_HELD',
        status='HELD',
        detail={'stepId': 'approval-gate', 'phase': 'APPROVAL',
                'reasonCode': 'OPERATOR_HOLD' if passed else 'UNKNOWN'})
    return True


def project_batch(jobs: JobRepository, workflow: TemporalWorkflowStarter,
                  context: TenantContext, *, after: ProjectionCursor | None = None,
                  limit: int = 32) -> ProjectionBatch:
    """Check every job in one bounded, fair keyset page.

    An unfinished workflow is not a progress result and cannot monopolize the
    oldest page. After the final page the next scan wraps, so earlier pending jobs
    remain observable. The cursor only schedules readback; it carries no workflow
    completion or native execution authority and can safely reset on restart.
    """
    pending = _pending_jobs(context, limit=limit, after=after)
    if not pending and after is not None:
        pending = _pending_jobs(context, limit=limit)
    progressed = False
    for candidate in pending:
        # Evaluate every row even when an earlier projection made progress.
        if project_one(jobs, workflow, context, candidate.job_id):
            progressed = True
    return ProjectionBatch(len(pending), progressed,
                           pending[-1] if len(pending) == limit else None)


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
    try:
        evidence_config = EvidenceRuntimeConfig.from_environment()
        if evidence_config.postgres_dsn != _required('HOSTING_WORKFLOW_POSTGRES_DSN'):
            raise ValueError('Workflow and evidence database roles must match')
        gate = build_gate(evidence_config)
        gate.require(context)
    except Exception:
        raise SystemExit('Workflow signed evidence configuration is unavailable') from None
    selector = None
    if args.mode == 'dispatch':
        from .application_runtime import (application_execution_enabled, build_application_worker_components,
                                          selected_application_runtime_required)
        if application_execution_enabled():
            selector = build_application_worker_components(_connect, gate).selector
        else:
            selector = lambda admitted: selected_application_runtime_required(_connect, admitted)
    workflow = TemporalWorkflowStarter(settings, application_selector=selector)
    if args.mode == 'dispatch':
        if not args.dispatcher_id:
            parser.error('dispatch requires a stable dispatcher ID')
        dispatcher = OutboxDispatcher(
            jobs, workflow, dispatcher_id=args.dispatcher_id,
            namespace=settings.namespace,
            start_history_retention_seconds=int(_required('HOSTING_TEMPORAL_START_RETENTION_SECONDS')),
            evidence_guard=gate.require)
    projection_cursor = None
    try:
        while True:
            if args.mode == 'dispatch':
                result = dispatcher.run_one(context)
                busy = result is not None
            else:
                gate.require(context)
                batch = project_batch(jobs, workflow, context, after=projection_cursor)
                busy = batch.progressed
                projection_cursor = batch.next_cursor
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
