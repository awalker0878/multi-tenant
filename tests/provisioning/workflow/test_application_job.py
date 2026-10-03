"""Real Temporal persistence/replay and no-repeat effect boundaries for the slice."""
import asyncio
from dataclasses import replace
import unittest

from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker, Replayer

from provisioner.controlplane.jobs import AdmissionConflict
from provisioner.controlplane.jobs.repository import _digest
from provisioner.controlplane.workflow.admitted_job import AdmittedInput, VERIFY_ADMITTED_JOB_ACTIVITY
from provisioner.controlplane.workflow.approval_gate import ApprovalCheck
from provisioner.controlplane.workflow.application_job import (ApplicationJobInput,
    ApplicationJobResult, ApplicationStageRequest, ApplicationStageResult, OpenStackApplicationMigration)
from provisioner.controlplane.workflow.temporal_adapter import TemporalConnection, TemporalWorkflowStarter
from provisioner.migration.activities import MigrationActivityRequest, MigrationActivityResult

PAYLOAD = {'format': 'hosting-workflow-start/1', 'job_id': 'application-job',
    'organization_id': 'org', 'tenant_id': 'tenant', 'plan_id': 'plan',
    'plan_revision': 1, 'plan_digest': 'a'*64, 'revocation_epoch': 0}
ADMITTED = AdmittedInput('application-job', 'org', 'tenant', 'plan', 1, 'a'*64, 0, _digest(PAYLOAD))
INPUT = ApplicationJobInput(ADMITTED, 'b'*64, ('compile', 'apply'), ('files', 'database'), ('vm',))


class ApplicationWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def run_case(self, *, fail_apply=False, hold_resources=False):
        calls = []
        @activity.defn(name=VERIFY_ADMITTED_JOB_ACTIVITY)
        async def approve(request: AdmittedInput) -> ApprovalCheck:
            calls.append('approval')
            return ApprovalCheck(True, request.job_id, request.organization_id, request.tenant_id,
                request.plan_id, request.plan_revision, request.plan_digest, request.revocation_epoch,
                'approval', 'c'*64)
        @activity.defn(name='application_reserve_resources')
        async def reserve(request: ApplicationStageRequest) -> ApplicationStageResult:
            calls.append('resources')
            return ApplicationStageResult('HELD' if hold_resources else 'STAGE_VERIFIED',
                request.admitted.job_id, '', 'OPERATOR_HOLD' if hold_resources else None,
                None if hold_resources else 'd'*64)
        @activity.defn(name='application_provision_step')
        async def provision(request: ApplicationStageRequest) -> ApplicationStageResult:
            calls.append(request.step_id)
            if fail_apply and request.step_id == 'apply':
                raise RuntimeError('lost result after simulated native handoff')
            return ApplicationStageResult('STAGE_VERIFIED', request.admitted.job_id, request.step_id,
                                           evidence_digest='e'*64)
        @activity.defn(name='application_transfer_dataset')
        async def transfer(request: MigrationActivityRequest) -> MigrationActivityResult:
            calls.append('dataset-' + request.member_id)
            return MigrationActivityResult('STAGE_VERIFIED', request.admitted.job_id,
                                           request.member_id, evidence_digest='f'*64)
        @activity.defn(name='application_join_datasets')
        async def join(request: MigrationActivityRequest) -> MigrationActivityResult:
            calls.append('join')
            return MigrationActivityResult('STAGE_VERIFIED', request.admitted.job_id, '',
                                           evidence_digest='1'*64)
        @activity.defn(name='application_rehearsal')
        async def rehearse(request: MigrationActivityRequest) -> MigrationActivityResult:
            calls.append('rehearsal')
            return MigrationActivityResult('HELD', request.admitted.job_id, '',
                'OPERATOR_HOLD', 'ISOLATED_REHEARSAL_OWNER_UNAVAILABLE')
        async with await WorkflowEnvironment.start_local() as env:
            selector = lambda admitted: replace(INPUT, admitted=admitted)
            starter = TemporalWorkflowStarter(TemporalConnection(
                env.client.service_client.config.target_host, 'default', 'application',
                insecure_loopback_for_tests=True), application_selector=selector)
            receipt = await asyncio.to_thread(starter.start, namespace='default',
                workflow_id=ADMITTED.job_id, payload=PAYLOAD)
            self.assertEqual(receipt, await asyncio.to_thread(starter.start, namespace='default',
                workflow_id=ADMITTED.job_id, payload=PAYLOAD))
            handle = env.client.get_workflow_handle(ADMITTED.job_id, run_id=receipt.run_id,
                                                     result_type=ApplicationJobResult)
            async with Worker(env.client, task_queue='application',
                    workflows=[OpenStackApplicationMigration],
                    activities=[approve, reserve, provision, transfer, join, rehearse]):
                result = await asyncio.wait_for(handle.result(), 20)
            history = await handle.fetch_history()
            await Replayer(workflows=[OpenStackApplicationMigration]).replay_workflow(history)
            self.assertEqual(result, await asyncio.to_thread(starter.completed_job, receipt))
            # An altered artifact cannot reuse this original native-capable run.
            changed = TemporalWorkflowStarter(starter.connection, application_selector=
                lambda admitted: replace(INPUT, admitted=admitted, selection_digest='2'*64))
            with self.assertRaises(AdmissionConflict):
                await asyncio.to_thread(changed.start, namespace='default',
                    workflow_id=ADMITTED.job_id, payload=PAYLOAD)
        return result, calls

    async def test_children_join_and_rehearsal_hold_survive_original_history_replay(self):
        result, calls = await self.run_case()
        self.assertEqual(result.phase, 'VERIFY')
        self.assertEqual(result.completed, 7)
        self.assertEqual(calls[:4], ['approval', 'resources', 'compile', 'apply'])
        self.assertEqual(set(calls[4:6]), {'dataset-files', 'dataset-database'})
        self.assertEqual(calls[6:], ['join', 'rehearsal'])
        self.assertEqual(result.status, 'HELD')
        self.assertEqual(result.hold_code, 'ISOLATED_REHEARSAL_OWNER_UNAVAILABLE')

    async def test_lost_native_activity_response_does_not_retry_or_start_data_transfer(self):
        result, calls = await self.run_case(fail_apply=True)
        self.assertEqual(calls, ['approval', 'resources', 'compile', 'apply'])
        self.assertEqual(result.reason_code, 'NATIVE_UNCERTAIN')
        self.assertEqual(result.phase, 'PROVISION')

    async def test_minimum_operating_or_resource_hold_prevents_every_provisioning_effect(self):
        result, calls = await self.run_case(hold_resources=True)
        self.assertEqual(calls, ['approval', 'resources'])
        self.assertEqual(result.phase, 'PREPARE')


class ApplicationReferenceTests(unittest.TestCase):
    def test_unbounded_or_credential_shaped_identifiers_cannot_enter_history(self):
        for change in ({'provisioning_steps': ()}, {'dataset_ids': ('data', 'data')},
                {'machine_ids': ()}, {'selection_digest': '/private/credential'},
                {'provisioning_steps': ('curl https://example.test',)}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(INPUT, **change)
        with self.assertRaises(ValueError):
            ApplicationStageResult('STAGE_VERIFIED', 'application-job', 'apply')
        with self.assertRaises(ValueError):
            ApplicationStageResult('HELD', 'application-job', 'apply', 'OPERATOR_HOLD',
                hold_code='/private/credential-or-unreviewed-error')
        with self.assertRaises(ValueError):
            ApplicationJobResult('application-job', 'plan', 1, 'a'*64, 'b'*64,
                'SUCCEEDED', 'VERIFY', 'OPERATOR_HOLD', 'c'*64, 1, 1)
