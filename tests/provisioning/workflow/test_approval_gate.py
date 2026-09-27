"""Real Temporal test server checks for B08 orchestration semantics."""
import asyncio
import unittest

from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Replayer, Worker

from provisioner.controlplane.workflow.approval_gate import (
    ApprovalCheck,
    ApprovalNotice,
    GateInput,
    MigrationApprovalGate,
    VERIFY_APPROVAL_ACTIVITY,
)


PLAN = GateInput('job-1', 'org-1', 'tenant-1', 'plan-1', 3,
                 'a' * 64, 0, 'c' * 64, 3600)


def notice(approval_id='approval-1', *, tenant_id='tenant-1'):
    return ApprovalNotice(PLAN.job_id, PLAN.organization_id, tenant_id, PLAN.plan_id,
                          PLAN.plan_revision, PLAN.plan_digest, approval_id)


def decision(request, *, authorized=True, digest='b' * 64):
    return ApprovalCheck(authorized, request.job_id, request.organization_id,
                         request.tenant_id, request.plan_id, request.plan_revision,
                         request.plan_digest, PLAN.revocation_epoch,
                         request.approval_id, digest)


class ApprovalGateTests(unittest.IsolatedAsyncioTestCase):
    async def test_timer_expires_without_approval_or_activity(self):
        calls = []

        @activity.defn(name=VERIFY_APPROVAL_ACTIVITY)
        async def verify(request: ApprovalNotice) -> ApprovalCheck:
            calls.append(request)
            return decision(request)

        async with await WorkflowEnvironment.start_time_skipping() as env:
            async with Worker(env.client, task_queue='gate-expiry',
                              workflows=[MigrationApprovalGate], activities=[verify]):
                handle = await env.client.start_workflow(
                    MigrationApprovalGate.run, PLAN, id='gate-expiry', task_queue='gate-expiry')
                result = await handle.result()
                self.assertEqual(result.status, 'EXPIRED')
                self.assertEqual(result.plan_digest, PLAN.plan_digest)
                self.assertFalse(calls)

    async def test_worker_restart_replays_wait_and_validates_untrusted_notice(self):
        calls = []

        @activity.defn(name=VERIFY_APPROVAL_ACTIVITY)
        async def verify(request: ApprovalNotice) -> ApprovalCheck:
            calls.append(request)
            return decision(request)

        async with await WorkflowEnvironment.start_local() as env:
            async with Worker(env.client, task_queue='gate-restart',
                              workflows=[MigrationApprovalGate], activities=[verify]):
                handle = await env.client.start_workflow(
                    MigrationApprovalGate.run, PLAN, id='gate-restart', task_queue='gate-restart')
                self.assertEqual(await handle.query(MigrationApprovalGate.gate_status),
                                 'WAITING_FOR_APPROVAL')
            # The Signal is recorded by the server while there is no Worker.
            await handle.signal(MigrationApprovalGate.offer_approval, notice())
            async with Worker(env.client, task_queue='gate-restart',
                              workflows=[MigrationApprovalGate], activities=[verify]):
                result = await asyncio.wait_for(handle.result(), timeout=15)
                self.assertEqual(result.status, 'GATE_PASSED')
                self.assertEqual(result.approval_id, 'approval-1')
                self.assertEqual(result.evidence_digest, 'b' * 64)
            self.assertEqual(calls, [notice()])
            history = await handle.fetch_history()
            await Replayer(workflows=[MigrationApprovalGate]).replay_workflow(history)

    async def test_wrong_scope_never_calls_authority(self):
        calls = []

        @activity.defn(name=VERIFY_APPROVAL_ACTIVITY)
        async def verify(request: ApprovalNotice) -> ApprovalCheck:
            calls.append(request)
            return decision(request)

        async with await WorkflowEnvironment.start_time_skipping() as env:
            async with Worker(env.client, task_queue='gate-scope',
                              workflows=[MigrationApprovalGate], activities=[verify]):
                handle = await env.client.start_workflow(
                    MigrationApprovalGate.run, PLAN, id='gate-scope', task_queue='gate-scope')
                await handle.signal(MigrationApprovalGate.offer_approval,
                                    notice(tenant_id='foreign'))
                result = await handle.result()
                self.assertEqual(result.status, 'HELD')
                self.assertIsNone(result.evidence_digest)
                self.assertFalse(calls)

    async def test_authority_must_bind_exact_revision_and_evidence(self):
        @activity.defn(name=VERIFY_APPROVAL_ACTIVITY)
        async def verify(request: ApprovalNotice) -> ApprovalCheck:
            return decision(request, digest='malformed')

        async with await WorkflowEnvironment.start_time_skipping() as env:
            async with Worker(env.client, task_queue='gate-proof',
                              workflows=[MigrationApprovalGate], activities=[verify]):
                handle = await env.client.start_workflow(
                    MigrationApprovalGate.run, PLAN, id='gate-proof', task_queue='gate-proof')
                await handle.signal(MigrationApprovalGate.offer_approval, notice())
                self.assertEqual((await handle.result()).status, 'HELD')

    def test_rejects_unbounded_or_unbound_input(self):
        with self.assertRaises(ValueError):
            GateInput('job', 'org', 'tenant', 'plan', 0, 'a' * 64, 0, 'c' * 64, 3600)
        with self.assertRaises(ValueError):
            GateInput('job', 'org', 'tenant', 'plan', 1, 'x' * 64, 0, 'c' * 64, 3600)
        with self.assertRaises(ValueError):
            GateInput('job', 'org', 'tenant', 'plan', 1, 'a' * 64, 0, 'c' * 64,
                      3600 * 24 * 31)
