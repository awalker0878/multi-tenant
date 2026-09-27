"""Two-process, real Temporal/PostgreSQL crash and replay integration gate.

Run 'prepare', restart only the Temporal service (leave its PostgreSQL volume
intact), then run 'recover'. This intentionally does not contact the product DB.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from uuid import uuid4

from temporalio import activity
from temporalio.client import Client
from temporalio.worker import Replayer, Worker

from provisioner.controlplane.workflow.admitted_job import (
    AdmittedMigrationJob, VERIFY_ADMITTED_JOB_ACTIVITY)
from provisioner.controlplane.workflow.approval_gate import ApprovalCheck, GateInput, GateResult
from provisioner.controlplane.workflow.temporal_adapter import (
    TemporalConnection, TemporalWorkflowStarter)


async def _ready(address: str) -> None:
    for _ in range(60):
        try:
            await Client.connect(address, namespace='default')
            return
        except Exception:
            await asyncio.sleep(1)
    raise RuntimeError('Self-hosted Temporal did not become ready')


def _adapter(address: str) -> TemporalWorkflowStarter:
    return TemporalWorkflowStarter(TemporalConnection(
        address, 'default', 'mobility-recovery-gate',
        insecure_loopback_for_tests=True))


async def _prepare(address: str, state: Path) -> None:
    await _ready(address)
    job_id = 'recovery-' + uuid4().hex
    payload = {'format': 'hosting-workflow-start/1', 'job_id': job_id,
               'organization_id': 'org-recovery', 'tenant_id': 'tenant-recovery',
               'plan_id': 'plan-recovery', 'plan_revision': 1,
               'plan_digest': 'a' * 64, 'revocation_epoch': 0}
    receipt = await asyncio.to_thread(_adapter(address).start, namespace='default',
                                      workflow_id=job_id, payload=payload)
    state.write_text(json.dumps({'payload': payload, 'run_id': receipt.run_id}))


async def _recover(address: str, state: Path) -> None:
    await _ready(address)
    stored = json.loads(state.read_text())
    payload = stored['payload']
    starter = _adapter(address)
    receipt = await asyncio.to_thread(starter.start, namespace='default',
                                      workflow_id=payload['job_id'], payload=payload)
    if receipt.run_id != stored['run_id']:
        raise RuntimeError('Server restart created a second run')
    calls = []

    @activity.defn(name=VERIFY_ADMITTED_JOB_ACTIVITY)
    async def verify(job: GateInput) -> ApprovalCheck:
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
