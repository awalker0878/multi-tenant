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
    async def run_case(self, *, fail_apply=False, hold_resources=False,
                       lifecycle=False, complete_stages=False, hold_acceptance=False,
                       lose_acceptance=False):
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
            if complete_stages:
                return MigrationActivityResult('STAGE_VERIFIED', request.admitted.job_id, '',
                                               evidence_digest='3'*64)
            return MigrationActivityResult('HELD', request.admitted.job_id, '',
                'OPERATOR_HOLD', 'ISOLATED_REHEARSAL_OWNER_UNAVAILABLE')
        @activity.defn(name='application_source_fence')
        async def source_fence(request: MigrationActivityRequest) -> MigrationActivityResult:
            calls.append('source-fence-' + request.member_id)
            return MigrationActivityResult('STAGE_VERIFIED', request.admitted.job_id,
                                           request.member_id, evidence_digest='4'*64)
        @activity.defn(name='application_final_sync')
        async def final_sync(request: MigrationActivityRequest) -> MigrationActivityResult:
            calls.append('final-sync')
            return MigrationActivityResult('STAGE_VERIFIED', request.admitted.job_id, '',
                                           evidence_digest='5'*64)
        @activity.defn(name='application_cutover')
        async def cutover(request: MigrationActivityRequest) -> MigrationActivityResult:
            calls.append('cutover')
            return MigrationActivityResult('STAGE_VERIFIED', request.admitted.job_id, '',
                                           evidence_digest='6'*64)
        @activity.defn(name='application_verify_cutover')
        async def verify(request: MigrationActivityRequest) -> MigrationActivityResult:
            calls.append('independent-acceptance')
            if lose_acceptance:
                raise RuntimeError('lost independent acceptance result')
            if hold_acceptance:
                return MigrationActivityResult('HELD', request.admitted.job_id, '',
                    'OPERATOR_HOLD', 'CURRENT_APPLICATION_TRAFFIC_REQUIRED')
            return MigrationActivityResult('STAGE_VERIFIED', request.admitted.job_id, '',
                                           evidence_digest='7'*64)
        async with await WorkflowEnvironment.start_local() as env:
            selector = lambda admitted: replace(INPUT, admitted=admitted,
                lifecycle_selection_digest='8'*64 if lifecycle else None)
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
                    activities=[approve, reserve, provision, transfer, join, rehearse,
                                source_fence, final_sync, cutover, verify]):
                result = await asyncio.wait_for(handle.result(), 20)
            history = await handle.fetch_history()
            await Replayer(workflows=[OpenStackApplicationMigration]).replay_workflow(history)
            self.assertEqual(result, await asyncio.to_thread(starter.completed_job, receipt))
            # An altered artifact cannot reuse this original native-capable run.
            changed = TemporalWorkflowStarter(starter.connection, application_selector=
                lambda admitted: replace(selector(admitted), selection_digest='2'*64))
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

    async def test_lifecycle_requires_final_acceptance_before_success_and_replays(self):
        result, calls = await self.run_case(lifecycle=True, complete_stages=True)
        self.assertEqual(result.status, 'SUCCEEDED')
        self.assertEqual((result.completed, result.total), (12, 12))
        self.assertEqual(result.evidence_digest, '7'*64)
        self.assertEqual(result.lifecycle_selection_digest, '8'*64)
        self.assertEqual(calls[-4:], ['source-fence-vm', 'final-sync', 'cutover', 'independent-acceptance'])

    async def test_old_selected_history_remains_held_after_every_modeled_stage(self):
        result, calls = await self.run_case(complete_stages=True)
        self.assertEqual(result.hold_code, 'FINAL_APPLICATION_ACCEPTANCE_UNAVAILABLE')
        self.assertNotIn('independent-acceptance', calls)
        self.assertEqual((result.completed, result.total), (11, 11))

    async def test_missing_or_lost_acceptance_cannot_close_or_retry_the_application(self):
        for options in ({'hold_acceptance': True}, {'lose_acceptance': True}):
            with self.subTest(options=options):
                result, calls = await self.run_case(lifecycle=True, complete_stages=True, **options)
                self.assertEqual(result.status, 'HELD')
                self.assertEqual((result.completed, result.total), (11, 12))
                self.assertEqual(calls.count('independent-acceptance'), 1)
                if options.get('hold_acceptance'):
                    self.assertEqual(result.hold_code, 'CURRENT_APPLICATION_TRAFFIC_REQUIRED')
                else:
                    self.assertEqual(result.reason_code, 'NATIVE_UNCERTAIN')

    def test_original_application_memo_digest_survives_new_optional_input_field(self):
        from dataclasses import asdict
        from provisioner.controlplane.workflow.temporal_adapter import _application_input_digest
        original = asdict(INPUT)
        original.pop('lifecycle_selection_digest')
        self.assertEqual(_application_input_digest(INPUT), _digest(original))
        self.assertNotEqual(_application_input_digest(replace(INPUT,
            lifecycle_selection_digest='8'*64)), _digest(original))


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
