"""Real Temporal retention/replay; native repair effects are explicitly synthetic."""
import asyncio
from dataclasses import replace
import unittest

from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Replayer, Worker

from provisioner.controlplane.jobs import AdmissionConflict
from provisioner.controlplane.workflow.admitted_job import AdmittedInput, VERIFY_ADMITTED_JOB_ACTIVITY
from provisioner.controlplane.workflow.approval_gate import ApprovalCheck
from provisioner.controlplane.workflow.application_recovery_job import (
    ApplicationRecoveryInput, ApplicationRecoveryResult, SelectedApplicationPostwriteRecovery)
from provisioner.controlplane.workflow.temporal_adapter import TemporalConnection, TemporalWorkflowStarter
from provisioner.migration.activities import MigrationActivityRequest, MigrationActivityResult
from tests.provisioning.workflow.test_application_split_workflows import ADMITTED, PAYLOAD, proof


SELECTED = ApplicationRecoveryInput(ADMITTED, 'b' * 64, 'c' * 64, 'd' * 64,
                                    'original-application', ('vm-alpha', 'vm-beta'))
NAMES = ('application_recovery_reattach', 'application_recovery_start',
         'application_recovery_restore', 'application_recovery_activate', 'application_recovery_verify')


class ApplicationRecoveryWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def campaign(self, *, lost=None, held=None):
        calls = []

        @activity.defn(name=VERIFY_ADMITTED_JOB_ACTIVITY)
        async def approve(admitted: AdmittedInput) -> ApprovalCheck:
            return ApprovalCheck(True, admitted.job_id, admitted.organization_id, admitted.tenant_id,
                admitted.plan_id, admitted.plan_revision, admitted.plan_digest, admitted.revocation_epoch,
                'new-recovery-approval', proof('recovery-approval'))

        def simulated(name):
            @activity.defn(name=name)
            async def perform(request: MigrationActivityRequest) -> MigrationActivityResult:
                calls.append((name, request.member_id))
                if name == lost:
                    raise RuntimeError('Synthetic completed native send lost its activity acknowledgement')
                if name == held:
                    return MigrationActivityResult('HELD', request.admitted.job_id, request.member_id,
                        'NATIVE_UNCERTAIN', 'ORIGINAL_APPLICATION_EFFECT_REQUIRES_RECONCILIATION')
                return MigrationActivityResult('STAGE_VERIFIED', request.admitted.job_id, request.member_id,
                    evidence_digest=proof(name + request.member_id))
            return perform

        async with await WorkflowEnvironment.start_local() as environment:
            starter = TemporalWorkflowStarter(TemporalConnection(
                environment.client.service_client.config.target_host, 'default', 'application-recovery-test',
                insecure_loopback_for_tests=True), application_selector=lambda admitted: replace(SELECTED, admitted=admitted))
            receipt = await asyncio.to_thread(starter.start, namespace='default',
                                             workflow_id=ADMITTED.job_id, payload=PAYLOAD)
            self.assertEqual(receipt, await asyncio.to_thread(starter.start, namespace='default',
                             workflow_id=ADMITTED.job_id, payload=PAYLOAD))
            handle = environment.client.get_workflow_handle(receipt.workflow_id, run_id=receipt.run_id,
                                                            result_type=ApplicationRecoveryResult)
            async with Worker(environment.client, task_queue='application-recovery-test',
                              workflows=[SelectedApplicationPostwriteRecovery],
                              activities=[approve, *(simulated(name) for name in NAMES)]):
                result = await asyncio.wait_for(handle.result(), 20)
            retained = tuple(calls)
            await Replayer(workflows=[SelectedApplicationPostwriteRecovery]).replay_workflow(await handle.fetch_history())
            self.assertEqual(tuple(calls), retained)
            self.assertEqual(await asyncio.to_thread(starter.completed_job, receipt), result)
            changed = TemporalWorkflowStarter(starter.connection,
                application_selector=lambda admitted: replace(SELECTED, admitted=admitted, recovery_selection_digest='f' * 64))
            with self.assertRaises(AdmissionConflict):
                await asyncio.to_thread(changed.start, namespace='default', workflow_id=ADMITTED.job_id, payload=PAYLOAD)
        return result, calls

    async def test_complete_repair_preserves_new_original_purpose_and_fixed_order(self):
        result, calls = await self.campaign()
        self.assertEqual((result.status, result.phase, result.completed, result.total), ('SUCCEEDED', 'VERIFY', 10, 10))
        self.assertEqual(result.original_job_id, SELECTED.original_job_id)
        self.assertEqual(calls, [(name, member) for member in SELECTED.machine_ids for name in NAMES[:-1]] + [(NAMES[-1], '')])

    async def test_lost_reattach_never_replays_restore_or_activation(self):
        result, calls = await self.campaign(lost=NAMES[0])
        self.assertEqual((result.status, result.reason_code), ('HELD', 'NATIVE_UNCERTAIN'))
        self.assertEqual(calls, [(NAMES[0], 'vm-alpha')])

    async def test_final_unresolved_acceptance_cannot_project_success(self):
        result, calls = await self.campaign(held=NAMES[-1])
        self.assertEqual((result.status, result.phase, result.completed), ('HELD', 'VERIFY', 9))
        self.assertEqual(len(calls), 9)

    def test_original_job_and_incomplete_success_are_rejected(self):
        with self.assertRaises(ValueError):
            replace(SELECTED, original_job_id=ADMITTED.job_id)
        with self.assertRaises(ValueError):
            ApplicationRecoveryResult(ADMITTED.job_id, ADMITTED.plan_id, 1, ADMITTED.plan_digest,
                SELECTED.selection_digest, SELECTED.lifecycle_selection_digest, SELECTED.recovery_selection_digest,
                SELECTED.original_job_id, 'SUCCEEDED', 'VERIFY', 9, 10, 'e' * 64, None)
