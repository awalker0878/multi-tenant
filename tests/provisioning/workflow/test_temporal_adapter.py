"""Exact outbox binding on a real Temporal local test server."""
import asyncio
import unittest

from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Replayer, Worker

from provisioner.controlplane.jobs import AdmissionConflict
from provisioner.controlplane.workflow.admitted_job import (
    AdmittedInput, AdmittedMigrationJob, VERIFY_ADMITTED_JOB_ACTIVITY)
from provisioner.controlplane.workflow.approval_gate import ApprovalCheck, GateResult
from provisioner.controlplane.workflow.temporal_adapter import (
    TemporalConnection, TemporalWorkflowStarter)


PAYLOAD = {'format': 'hosting-workflow-start/1', 'job_id': 'job-1',
           'organization_id': 'org-1', 'tenant_id': 'tenant-1',
           'plan_id': 'plan-1', 'plan_revision': 3,
           'plan_digest': 'a' * 64, 'revocation_epoch': 0}


class TemporalAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_idempotent_start_verified_by_run_and_memo(self):
        async with await WorkflowEnvironment.start_local() as env:
            starter = TemporalWorkflowStarter(TemporalConnection(
                env.client.service_client.config.target_host, 'default', 'admitted',
                insecure_loopback_for_tests=True))
            first = await asyncio.to_thread(starter.start, namespace='default',
                                            workflow_id='job-1', payload=PAYLOAD)
            second = await asyncio.to_thread(starter.start, namespace='default',
                                             workflow_id='job-1', payload=PAYLOAD)
            self.assertEqual(first, second)
            self.assertTrue(first.run_id)
            altered = {**PAYLOAD, 'plan_digest': 'b' * 64}
            with self.assertRaises(AdmissionConflict):
                await asyncio.to_thread(starter.start, namespace='default',
                                        workflow_id='job-1', payload=altered)
            with self.assertRaises(AdmissionConflict):
                await asyncio.to_thread(starter.start, namespace='foreign',
                                        workflow_id='job-1', payload=PAYLOAD)
            with self.assertRaises(AdmissionConflict):
                await asyncio.to_thread(starter.start, namespace='default',
                                        workflow_id='job-2',
                                        payload={**PAYLOAD, 'job_id': 'job-2',
                                                 'credential': 'canary-do-not-persist'})
            with self.assertRaises(AdmissionConflict):
                await asyncio.to_thread(starter.start, namespace='default',
                                        workflow_id='AKIA1234567890ABCDEF',
                                        payload={**PAYLOAD,
                                                 'job_id': 'AKIA1234567890ABCDEF'})

    async def test_admitted_job_rechecks_authority_after_worker_replacement(self):
        calls = []

        @activity.defn(name=VERIFY_ADMITTED_JOB_ACTIVITY)
        async def verify(request: AdmittedInput) -> ApprovalCheck:
            calls.append(request)
            return ApprovalCheck(True, request.job_id, request.organization_id,
                                 request.tenant_id, request.plan_id,
                                 request.plan_revision, request.plan_digest,
                                 request.revocation_epoch, 'approval-1', 'b' * 64)

        async with await WorkflowEnvironment.start_local() as env:
            starter = TemporalWorkflowStarter(TemporalConnection(
                env.client.service_client.config.target_host, 'default', 'admitted-recovery',
                insecure_loopback_for_tests=True))
            # Start with no Worker; Temporal retains the task. A later Worker
            # processes it and a new Worker build can replay its history.
            receipt = await asyncio.to_thread(starter.start, namespace='default',
                                              workflow_id='job-1', payload=PAYLOAD)
            handle = env.client.get_workflow_handle('job-1', run_id=receipt.run_id,
                                                     result_type=GateResult)
            async with Worker(env.client, task_queue='admitted-recovery',
                              workflows=[AdmittedMigrationJob], activities=[verify]):
                result = await asyncio.wait_for(handle.result(), timeout=15)
            self.assertEqual(result.status, 'GATE_PASSED')
            self.assertEqual(len(calls), 1)
            self.assertEqual(result, await asyncio.to_thread(starter.completed_gate, receipt))
            history = await handle.fetch_history()
            await Replayer(workflows=[AdmittedMigrationJob]).replay_workflow(history)
            # Closed executions cannot be silently replaced under the same ID.
            self.assertEqual(receipt, await asyncio.to_thread(
                starter.start, namespace='default', workflow_id='job-1', payload=PAYLOAD))

    def test_tls_is_required_outside_loopback_test_mode(self):
        with self.assertRaises(ValueError):
            TemporalConnection('private.example:7233', 'namespace', 'queue')
        with self.assertRaises(ValueError):
            TemporalConnection('10.0.0.1:7233', 'namespace', 'queue',
                               insecure_loopback_for_tests=True)
        with self.assertRaises(ValueError):
            TemporalConnection('localhost:7233', 'namespace', 'queue')
