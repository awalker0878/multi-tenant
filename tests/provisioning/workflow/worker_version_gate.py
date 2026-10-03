"""Exercise pinned Temporal Worker routing through upgrade and rollback.

This is a disposable engine gate. Both releases process read-only approval
checks; no workload driver or product credential is available here.
"""
from __future__ import annotations

import argparse
import asyncio
from uuid import uuid4

from temporalio import activity
from temporalio.api.workflowservice.v1 import (
    DescribeWorkerDeploymentRequest, SetWorkerDeploymentCurrentVersionRequest)
from temporalio.client import Client
from temporalio.common import VersioningBehavior, WorkerDeploymentVersion
from temporalio.service import RPCError, RPCStatusCode
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker, WorkerDeploymentConfig

from provisioner.controlplane.workflow.approval_gate import (
    ApprovalCheck, ApprovalNotice, GateInput, MigrationApprovalGate,
    VERIFY_APPROVAL_ACTIVITY)
from tests.provisioning.workflow.temporal_recovery_gate import _ready


_REGISTRATION_ATTEMPTS = 30
_RPC_TIMEOUT_SECONDS = 5


async def _set_current(client: Client, deployment: str, build_id: str) -> None:
    """Wait for this exact release; never select another or unversioned worker.

    A successful Describe may contain only the previously registered release.
    That is pending registration, not a permanent error. Bound both the poll
    count and each RPC, and refresh the conflict token after every retry.
    """
    service = client.service_client.workflow_service
    for attempt in range(_REGISTRATION_ATTEMPTS):
        try:
            description = await asyncio.wait_for(
                service.describe_worker_deployment(
                    DescribeWorkerDeploymentRequest(namespace=client.namespace,
                                                    deployment_name=deployment)),
                timeout=_RPC_TIMEOUT_SECONDS)
            registered = any(
                v.deployment_version.deployment_name == deployment
                and v.deployment_version.build_id == build_id
                for v in description.worker_deployment_info.version_summaries)
            if registered:
                await asyncio.wait_for(
                    service.set_worker_deployment_current_version(
                        SetWorkerDeploymentCurrentVersionRequest(
                            namespace=client.namespace, deployment_name=deployment,
                            build_id=build_id, conflict_token=description.conflict_token,
                            identity='mobility-ci-release-gate')),
                    timeout=_RPC_TIMEOUT_SECONDS)
                return
        except RPCError as exc:
            if exc.status not in (RPCStatusCode.NOT_FOUND, RPCStatusCode.FAILED_PRECONDITION):
                raise
        if attempt + 1 < _REGISTRATION_ATTEMPTS:
            await asyncio.sleep(1)
    raise RuntimeError(f'Versioned Worker failed to register or activate: {deployment}/{build_id}')


def _verifier(release: str, calls: list[tuple[str, str]]):
    @activity.defn(name=VERIFY_APPROVAL_ACTIVITY)
    async def verify(request: ApprovalNotice) -> ApprovalCheck:
        calls.append((request.job_id, release))
        return ApprovalCheck(True, request.job_id, request.organization_id,
                             request.tenant_id, request.plan_id,
                             request.plan_revision, request.plan_digest, 0,
                             request.approval_id, 'b' * 64)
    return verify


async def _start_waiting(client: Client, queue: str, job_id: str):
    plan = GateInput(job_id, 'org-version-gate', 'tenant-version-gate',
                     'plan-version-gate', 1, 'a' * 64, 0, 'c' * 64, 60)
    handle = await client.start_workflow(
        MigrationApprovalGate.run, plan, id=job_id, task_queue=queue)
    for _ in range(30):
        try:
            if await handle.query(MigrationApprovalGate.gate_status) == 'WAITING_FOR_APPROVAL':
                return handle, plan
        except RPCError as exc:
            if exc.status != RPCStatusCode.FAILED_PRECONDITION:
                raise
        await asyncio.sleep(.25)
    raise RuntimeError('Pinned approval wait did not start')


async def _finish(handle, plan: GateInput) -> None:
    notice = ApprovalNotice(plan.job_id, plan.organization_id, plan.tenant_id,
                            plan.plan_id, plan.plan_revision, plan.plan_digest,
                            'approval-' + plan.job_id)
    await handle.signal(MigrationApprovalGate.offer_approval, notice)
    result = await asyncio.wait_for(handle.result(), timeout=30)
    if result.status != 'GATE_PASSED' or result.approval_id != notice.approval_id:
        raise RuntimeError('A pinned approval wait did not pass its authority check')


async def _gate(client: Client) -> None:
    suffix = uuid4().hex[:12]
    deployment, queue = 'mobility-gate-' + suffix, 'mobility-versions-' + suffix
    older, newer = 'a' * 40, 'b' * 40
    calls: list[tuple[str, str]] = []

    def worker(build_id: str, release: str) -> Worker:
        return Worker(
            client, task_queue=queue, workflows=[MigrationApprovalGate],
            activities=[_verifier(release, calls)],
            deployment_config=WorkerDeploymentConfig(
                version=WorkerDeploymentVersion(deployment_name=deployment,
                                                build_id=build_id),
                use_worker_versioning=True,
                default_versioning_behavior=VersioningBehavior.PINNED))

    async with worker(older, 'old'):
        await _set_current(client, deployment, older)
        old, old_plan = await _start_waiting(client, queue, 'old-' + suffix)
        async with worker(newer, 'new'):
            await _set_current(client, deployment, newer)
            new, new_plan = await _start_waiting(client, queue, 'new-' + suffix)
            await _finish(new, new_plan)
            await _finish(old, old_plan)
            # Rolling back the Current version changes only subsequent starts.
            await _set_current(client, deployment, older)
            rollback, rollback_plan = await _start_waiting(
                client, queue, 'rollback-' + suffix)
            await _finish(rollback, rollback_plan)
    if sorted(calls) != sorted((
            (old_plan.job_id, 'old'),
            (new_plan.job_id, 'new'),
            (rollback_plan.job_id, 'old'))):
        raise RuntimeError('Upgrade/rollback crossed pinned Worker versions')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--address', default='127.0.0.1:7233')
    parser.add_argument('--local', action='store_true',
                        help='use a disposable in-memory development server')
    args = parser.parse_args()

    async def run() -> None:
        if args.local:
            async with await WorkflowEnvironment.start_local() as env:
                await _gate(env.client)
        else:
            await _ready(args.address)
            await _gate(await Client.connect(args.address, namespace='default'))

    asyncio.run(run())


if __name__ == '__main__':
    main()
