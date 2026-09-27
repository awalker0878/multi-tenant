"""Two-process, real Temporal/PostgreSQL crash and replay integration gate.

Run 'prepare', restart only the Temporal service (leave its PostgreSQL volume
intact), then run 'recover'. This intentionally does not contact the product DB.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from temporalio import activity
from temporalio.api.enums.v1 import NamespaceState
from temporalio.api.workflowservice.v1 import DescribeNamespaceRequest
from temporalio.client import Client
from temporalio.service import RPCError, RPCStatusCode
from temporalio.worker import Replayer, Worker

from provisioner.controlplane.workflow.admitted_job import (
    AdmittedInput, AdmittedMigrationJob, VERIFY_ADMITTED_JOB_ACTIVITY)
from provisioner.controlplane.workflow.approval_gate import ApprovalCheck, GateResult
from provisioner.controlplane.workflow.temporal_adapter import (
    TemporalConnection, TemporalWorkflowStarter)


async def _ready(address: str) -> None:
    last_failure = 'no connection attempt'
    for _ in range(90):
        try:
            client = await Client.connect(address, namespace='default')
            description = await client.workflow_service.describe_namespace(
                DescribeNamespaceRequest(namespace='default'),
                timeout=timedelta(seconds=2))
            if (description.namespace_info.name == 'default'
                    and description.namespace_info.state ==
                    NamespaceState.NAMESPACE_STATE_REGISTERED):
                return
            last_failure = 'namespace is not registered'
        except Exception as exc:
            last_failure = type(exc).__name__
        await asyncio.sleep(1)
    raise RuntimeError(f'Self-hosted Temporal did not become ready ({last_failure})')


def _adapter(address: str) -> TemporalWorkflowStarter:
    return TemporalWorkflowStarter(TemporalConnection(
        address, 'default', 'mobility-recovery-gate',
        insecure_loopback_for_tests=True))


async def _start_after_namespace_cache(starter: TemporalWorkflowStarter,
                                       payload: dict):
    """Auto-setup registration precedes propagation to the frontend cache."""
    for _ in range(60):
        try:
            return await asyncio.to_thread(
                starter.start, namespace='default',
                workflow_id=payload['job_id'], payload=payload)
        except RPCError as exc:
            if (exc.status != RPCStatusCode.NOT_FOUND
                    or 'Namespace default is not found' not in exc.message):
                raise
        await asyncio.sleep(1)
    raise RuntimeError('Temporal default namespace did not reach the workflow frontend cache')


async def _prepare(address: str, state: Path) -> None:
    await _ready(address)
    job_id = 'recovery-' + uuid4().hex
    payload = {'format': 'hosting-workflow-start/1', 'job_id': job_id,
               'organization_id': 'org-recovery', 'tenant_id': 'tenant-recovery',
               'plan_id': 'plan-recovery', 'plan_revision': 1,
               'plan_digest': 'a' * 64, 'revocation_epoch': 0}
    receipt = await _start_after_namespace_cache(_adapter(address), payload)
    state.write_text(json.dumps({'payload': payload, 'run_id': receipt.run_id}))


async def _recover(address: str, state: Path) -> None:
    await _ready(address)
    stored = json.loads(state.read_text())
    payload = stored['payload']
    starter = _adapter(address)
    receipt = await _start_after_namespace_cache(starter, payload)
    if receipt.run_id != stored['run_id']:
        raise RuntimeError('Server restart created a second run')
    calls = []

    @activity.defn(name=VERIFY_ADMITTED_JOB_ACTIVITY)
    async def verify(job: AdmittedInput) -> ApprovalCheck:
        calls.append(job.job_id)
        return ApprovalCheck(True, job.job_id, job.organization_id, job.tenant_id,
                             job.plan_id, job.plan_revision, job.plan_digest,
                             job.revocation_epoch, 'approval-recovery', 'b' * 64)

    client = await Client.connect(address, namespace='default')
    handle = client.get_workflow_handle(payload['job_id'], run_id=receipt.run_id,
                                        result_type=GateResult)
    async with Worker(client, task_queue='mobility-recovery-gate',
                      workflows=[AdmittedMigrationJob], activities=[verify]):
        result = await asyncio.wait_for(handle.result(), timeout=30)
    if result.status != 'GATE_PASSED' or calls != [payload['job_id']]:
        raise RuntimeError('Persisted task did not resume with one authority check')
    history = await handle.fetch_history()
    await Replayer(workflows=[AdmittedMigrationJob]).replay_workflow(history)
    if await asyncio.to_thread(starter.completed_gate, receipt) != result:
        raise RuntimeError('Pinned result differs from workflow history')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('prepare', 'recover'))
    parser.add_argument('--address', default='127.0.0.1:7233')
    parser.add_argument('--state', type=Path, required=True)
    args = parser.parse_args()
    if args.phase == 'prepare':
        asyncio.run(_prepare(args.address, args.state))
    else:
        asyncio.run(_recover(args.address, args.state))


if __name__ == '__main__':
    main()
