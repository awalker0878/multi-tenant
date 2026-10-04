"""Actual Temporal starts/histories/replay; explicitly simulated native activities.

No site, staged target, database commit or migration is qualified by these tests.
The fixed synthetic activities isolate workflow ordering, no-repeat boundaries,
typed retained results and original start/result binding from native owners.
"""
import asyncio
from contextlib import nullcontext
from dataclasses import replace
import hashlib
import unittest
from unittest.mock import patch

from temporalio import activity
from temporalio import workflow as workflow_api
from temporalio.api.enums.v1 import EventType
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Replayer, Worker

from provisioner.controlplane.jobs import AdmissionConflict, StartReceipt
from provisioner.controlplane.jobs.repository import _digest
from provisioner.controlplane.workflow.admitted_job import AdmittedInput, VERIFY_ADMITTED_JOB_ACTIVITY
from provisioner.controlplane.workflow.approval_gate import ApprovalCheck
from provisioner.controlplane.workflow.application_job import (
    ApplicationJobResult, ApplicationStageRequest, ApplicationStageResult)
from provisioner.controlplane.workflow.application_staging_job import (
    ApplicationStagingInput, ApplicationStagingResult, OpenStackApplicationStaging)
from provisioner.controlplane.workflow.application_cutover_job import (
    ApplicationCutoverInput, OpenStackStagedApplicationCutover)
from provisioner.controlplane.workflow.temporal_adapter import (
    TemporalConnection, TemporalWorkflowStarter, _application_input_digest)
from provisioner.migration.activities import MigrationActivityRequest, MigrationActivityResult


PAYLOAD = dict(format='hosting-workflow-start/1', job_id='split-application-job',
    organization_id='org-split', tenant_id='tenant-split', plan_id='plan-split',
    plan_revision=1, plan_digest='a' * 64, revocation_epoch=0)
ADMITTED = AdmittedInput(PAYLOAD['job_id'], PAYLOAD['organization_id'], PAYLOAD['tenant_id'],
    PAYLOAD['plan_id'], 1, 'a' * 64, 0, _digest(PAYLOAD))
STAGING = ApplicationStagingInput(ADMITTED, 'b' * 64,
                                 ('initial-create', 'associate-targets'), ('vm-alpha', 'vm-beta'))
CUTOVER = ApplicationCutoverInput(ADMITTED, 'c' * 64,
    ('guest-config', 'policy-apply'), ('files', 'static'), ('vm-alpha', 'vm-beta'), 'd' * 64, 'e' * 64)
DATABASE = replace(CUTOVER, database_selection_digest='f' * 64, database_member_id='vm-alpha')


def proof(name):
    return hashlib.sha256(('synthetic-temporal-only:' + name).encode()).hexdigest()


class SplitWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def test_interrupted_cutover_requires_both_original_staged_purpose_digests(self):
        async with await WorkflowEnvironment.start_local() as environment:
            starter = TemporalWorkflowStarter(TemporalConnection(
                environment.client.service_client.config.target_host, 'default', 'malformed-no-worker',
                insecure_loopback_for_tests=True))
            for omitted in ('staging_selection_digest', 'lifecycle_selection_digest'):
                with self.subTest(missing=omitted):
                    payload = {**PAYLOAD, 'job_id': 'interrupted-' + omitted.replace('_', '-')}
                    admitted = replace(ADMITTED, job_id=payload['job_id'], payload_digest=_digest(payload))
                    selected = replace(CUTOVER, admitted=admitted)
                    memo = dict(job_id=admitted.job_id, organization_id=admitted.organization_id,
                        tenant_id=admitted.tenant_id, plan_id=admitted.plan_id, plan_revision=admitted.plan_revision,
                        plan_digest=admitted.plan_digest, revocation_epoch=admitted.revocation_epoch,
                        payload_digest=admitted.payload_digest, selection_digest=selected.selection_digest,
                        application_input_digest=_application_input_digest(selected),
                        lifecycle_selection_digest=selected.lifecycle_selection_digest,
                        staging_selection_digest=selected.staging_selection_digest)
                    del memo[omitted]
                    # No Worker: neither authority nor a simulated/native effect
                    # can run. This is a real retained interrupted Temporal run.
                    handle = await environment.client.start_workflow(OpenStackStagedApplicationCutover.run,
                        selected, id=admitted.job_id, task_queue='malformed-no-worker',
                        memo={'hosting_job_binding_v1': memo})
                    await handle.terminate(reason='Synthetic exact memo-custody negative; no native Worker')
                    receipt = StartReceipt('default', admitted.job_id, handle.result_run_id, admitted.job_id,
                        admitted.plan_id, admitted.plan_revision, admitted.plan_digest, admitted.payload_digest)
                    with self.assertRaises(AdmissionConflict):
                        await asyncio.to_thread(starter.completed_job, receipt)

    async def run_case(self, selected, *, held=None, lose_result=None, foreign_member=None,
                       invalid_evidence=None, revoke_approval=False, lose_start_response=False,
                       historical_markers=None):
        calls, requests, simulated_effects = [], [], []

        @activity.defn(name=VERIFY_ADMITTED_JOB_ACTIVITY)
        async def approve(request: AdmittedInput) -> ApprovalCheck:
            calls.append('approval'); requests.append(request)
            return ApprovalCheck(not revoke_approval, request.job_id, request.organization_id, request.tenant_id,
                request.plan_id, request.plan_revision, request.plan_digest, request.revocation_epoch,
                'synthetic-approval', proof('approval'))

        @activity.defn(name='application_reserve_resources')
        async def reserve(request: ApplicationStageRequest) -> ApplicationStageResult:
            calls.append('reserve'); requests.append(request)
            # Register this even for cutover: an accidental reserve is an
            # immediate observable test failure, not an unregistered task wait.
            if isinstance(selected, ApplicationCutoverInput):
                raise AssertionError('Staged cutover cannot reserve a second resource graph')
            if held == 'reserve':
                return ApplicationStageResult('HELD', request.admitted.job_id, '',
                    'OPERATOR_HOLD', hold_code='CURRENT_AUTHORITY_UNAVAILABLE')
            return ApplicationStageResult('STAGE_VERIFIED', request.admitted.job_id, '', evidence_digest=proof('reserve'))

        @activity.defn(name='application_provision_step')
        async def provision(request: ApplicationStageRequest) -> ApplicationStageResult:
            name = 'provision:' + request.step_id
            calls.append(name); requests.append(request); simulated_effects.append(name)
            if name == lose_result:
                raise RuntimeError('Synthetic native handoff completed; its activity response was lost')
            return ApplicationStageResult('STAGE_VERIFIED', request.admitted.job_id,
                'foreign-step' if name == foreign_member else request.step_id,
                evidence_digest=True if name == invalid_evidence else proof(name))

        # This factory exists only in this test module. Names below are fixed;
        # there is no production callback or native endpoint behind it.
        def synthetic_migration(name):
            @activity.defn(name=name)
            async def perform(request: MigrationActivityRequest) -> MigrationActivityResult:
                call = name + (':' + request.member_id if request.member_id else '')
                calls.append(call); requests.append(request)
                if name == held:
                    return MigrationActivityResult('HELD', request.admitted.job_id, request.member_id,
                        'OPERATOR_HOLD', 'CURRENT_STAGED_APPLICATION_TARGET_REQUIRED'
                            if name == 'application_verify_staged_data' else 'CURRENT_APPLICATION_TRAFFIC_REQUIRED')
                simulated_effects.append(call)
                if name == lose_result:
                    raise RuntimeError('Synthetic original activity outcome lost; replay must not repeat it')
                return MigrationActivityResult('STAGE_VERIFIED', request.admitted.job_id,
                    'foreign-member' if name == foreign_member else request.member_id,
                    evidence_digest=True if name == invalid_evidence else proof(name))
            return perform

        names = (
            'application_stage_targets', 'application_verify_staged_data', 'application_target_prepare',
            'application_target_bootstrap', 'application_target_policy',
            'application_transfer_dataset',
            'application_join_datasets', 'application_rehearsal', 'application_database_initialize',
            'application_database_synchronize', 'application_database_source_fence', 'application_database_final',
            'application_source_fence', 'application_final_sync', 'application_cutover', 'application_verify_cutover')
        activities = [approve, reserve, provision, *(synthetic_migration(name) for name in names)]
        staging = isinstance(selected, ApplicationStagingInput)
        workflow = OpenStackApplicationStaging if staging else OpenStackStagedApplicationCutover
        result_type = ApplicationStagingResult if staging else ApplicationJobResult
        async with await WorkflowEnvironment.start_local() as environment:
            selector = lambda admitted: replace(selected, admitted=admitted)
            starter = TemporalWorkflowStarter(TemporalConnection(
                environment.client.service_client.config.target_host, 'default', 'split-application',
                insecure_loopback_for_tests=True), application_selector=selector)
            lost_receipts = []
            if lose_start_response:
                def original_start_with_lost_acknowledgement():
                    lost_receipts.append(starter.start(namespace='default',
                        workflow_id=ADMITTED.job_id, payload=PAYLOAD))
                    raise ConnectionError('Actual Temporal start persisted; its synthetic delivery acknowledgement was lost')
                with self.assertRaises(ConnectionError):
                    await asyncio.to_thread(original_start_with_lost_acknowledgement)
            receipt = await asyncio.to_thread(starter.start, namespace='default',
                workflow_id=ADMITTED.job_id, payload=PAYLOAD)
            if lost_receipts:
                self.assertEqual(lost_receipts, [receipt])
            self.assertEqual(receipt, await asyncio.to_thread(starter.start, namespace='default',
                workflow_id=ADMITTED.job_id, payload=PAYLOAD))
            handle = environment.client.get_workflow_handle(receipt.workflow_id, run_id=receipt.run_id,
                                                              result_type=result_type)
            original_patch = workflow_api.patched
            marker_context = patch.object(workflow_api, 'patched',
                side_effect=lambda name: original_patch(name) if name in historical_markers else False) \
                if historical_markers is not None else nullcontext()
            with marker_context:
                async with Worker(environment.client, task_queue='split-application',
                                  workflows=[workflow], activities=activities):
                    result = await asyncio.wait_for(handle.result(), 20)
            history = await handle.fetch_history()
            self.assertEqual(sum(event.event_type == EventType.EVENT_TYPE_WORKFLOW_EXECUTION_STARTED
                                 for event in history.events), 1)
            effects_before_replay = tuple(simulated_effects)
            await Replayer(workflows=[workflow]).replay_workflow(history)
            self.assertEqual(tuple(simulated_effects), effects_before_replay)
            self.assertEqual(result, await asyncio.to_thread(starter.completed_job, receipt))
            self.assertEqual(receipt, await asyncio.to_thread(starter.start, namespace='default',
                workflow_id=ADMITTED.job_id, payload=PAYLOAD))
            changed = TemporalWorkflowStarter(starter.connection,
                application_selector=lambda admitted: replace(selector(admitted), selection_digest='9' * 64))
            with self.assertRaises(AdmissionConflict):
                await asyncio.to_thread(changed.start, namespace='default', workflow_id=ADMITTED.job_id, payload=PAYLOAD)
            with self.assertRaises(AdmissionConflict):
                await asyncio.to_thread(starter.completed_job, replace(receipt, plan_digest='9' * 64))
        for request in requests:
            if isinstance(request, AdmittedInput):
                self.assertEqual(request, ADMITTED)
            else:
                self.assertEqual(request.admitted, ADMITTED)
                self.assertEqual(request.selection_digest, selected.selection_digest)
        return result, calls, simulated_effects

    async def test_lost_original_start_acknowledgement_rejoins_each_exact_retained_workflow(self):
        for selected in (STAGING, CUTOVER):
            with self.subTest(workflow=type(selected).__name__):
                result, calls, effects = await self.run_case(selected, lose_start_response=True)
                self.assertEqual(calls.count('approval'), 1)
                self.assertEqual(len(effects), len(set(effects)))
                self.assertIn(result.status, ('STAGED', 'SUCCEEDED'))

    async def test_initial_staging_creates_associates_and_stops_with_original_handover(self):
        result, calls, _ = await self.run_case(STAGING)
        self.assertEqual(calls, ['approval', 'reserve', 'provision:initial-create',
                                 'provision:associate-targets', 'application_stage_targets'])
        self.assertEqual((result.status, result.phase, result.completed, result.total), ('STAGED', 'VERIFY', 5, 5))
        self.assertEqual(result.evidence_digest, proof('application_stage_targets'))
        self.assertNotIn('application_source_fence', calls)
        self.assertNotIn('application_cutover', calls)

    async def test_staging_lost_create_or_handover_result_is_held_without_repeating_effects(self):
        for name, completed in (('provision:initial-create', 2), ('application_stage_targets', 4)):
            with self.subTest(activity=name):
                result, calls, effects = await self.run_case(STAGING, lose_result=name)
                self.assertEqual((result.status, result.reason_code, result.completed, result.total),
                                 ('HELD', 'NATIVE_UNCERTAIN', completed, 5))
                self.assertEqual(calls.count(name), 1); self.assertEqual(effects.count(name), 1)
                self.assertFalse(any('dataset' in call or 'source_fence' in call or 'cutover' in call for call in calls))

    async def test_revoked_approval_or_operating_reservation_hold_precedes_staging_effects(self):
        result, calls, effects = await self.run_case(STAGING, revoke_approval=True)
        self.assertEqual((result.phase, result.completed), ('APPROVAL', 0))
        self.assertEqual(calls, ['approval']); self.assertEqual(effects, [])
        result, calls, effects = await self.run_case(STAGING, held='reserve')
        self.assertEqual((result.phase, result.completed, result.total), ('PREPARE', 1, 5))
        self.assertEqual(calls, ['approval', 'reserve']); self.assertEqual(effects, [])

    async def test_staged_cutover_never_reserves_or_creates_and_has_separate_final_proof(self):
        result, calls, _ = await self.run_case(CUTOVER)
        self.assertEqual((result.status, result.completed, result.total), ('SUCCEEDED', 19, 19))
        self.assertEqual(calls[:8], ['approval', 'application_verify_staged_data',
                                    'application_target_prepare:vm-alpha', 'application_target_prepare:vm-beta',
                                    'application_target_bootstrap:vm-alpha', 'application_target_bootstrap:vm-beta',
                                    'provision:guest-config', 'provision:policy-apply'])
        self.assertEqual(set(calls[8:10]), {'application_transfer_dataset:files', 'application_transfer_dataset:static'})
        self.assertEqual(calls[10:], ['application_join_datasets', 'application_rehearsal',
            'application_source_fence:vm-alpha', 'application_source_fence:vm-beta',
            'application_final_sync', 'application_target_policy:vm-alpha', 'application_target_policy:vm-beta',
            'application_cutover', 'application_verify_cutover'])
        self.assertNotIn('reserve', calls); self.assertNotIn('provision:initial-create', calls)
        self.assertEqual(result.lifecycle_selection_digest, CUTOVER.lifecycle_selection_digest)
        self.assertEqual(result.staging_selection_digest, CUTOVER.staging_selection_digest)
        self.assertEqual(result.evidence_digest, proof('application_verify_cutover'))
        self.assertNotEqual(result.evidence_digest, proof('application_cutover'))

    async def test_current_staged_handover_hold_stops_every_data_or_native_cutover_effect(self):
        result, calls, effects = await self.run_case(DATABASE, held='application_verify_staged_data')
        self.assertEqual((result.status, result.phase, result.completed, result.total), ('HELD', 'PREPARE', 1, 23))
        self.assertEqual(result.hold_code, 'CURRENT_STAGED_APPLICATION_TARGET_REQUIRED')
        self.assertEqual(calls, ['approval', 'application_verify_staged_data']); self.assertEqual(effects, [])

    async def test_target_prepare_hold_or_lost_result_stops_before_guest_and_source_effects(self):
        for option in ({'held': 'application_target_prepare'}, {'lose_result': 'application_target_prepare'}):
            with self.subTest(option=option):
                result, calls, effects = await self.run_case(CUTOVER, **option)
                self.assertEqual((result.status, result.phase, result.completed, result.total),
                                 ('HELD', 'PREPARE', 2, 19))
                self.assertEqual(calls, ['approval', 'application_verify_staged_data',
                                        'application_target_prepare:vm-alpha'])
                self.assertLessEqual(effects.count('application_target_prepare:vm-alpha'), 1)
                self.assertFalse(any(call.startswith('provision:') or 'source_fence' in call
                                     or 'transfer_dataset' in call or call == 'application_cutover'
                                     for call in calls))

    async def test_database_copy_sync_and_final_native_position_precede_vm_fence_and_activation(self):
        result, calls, _ = await self.run_case(DATABASE)
        self.assertEqual((result.status, result.completed, result.total), ('SUCCEEDED', 23, 23))
        self.assertEqual(calls[8:10], ['application_database_initialize:vm-alpha', 'application_database_synchronize:vm-alpha'])
        db_fence = calls.index('application_database_source_fence:vm-alpha')
        self.assertEqual(calls[db_fence:db_fence + 4], ['application_database_source_fence:vm-alpha',
            'application_database_final:vm-alpha', 'application_source_fence:vm-alpha', 'application_source_fence:vm-beta'])
        self.assertLess(calls.index('application_database_final:vm-alpha'), calls.index('application_cutover'))
        self.assertEqual(result.database_selection_digest, DATABASE.database_selection_digest)

    async def test_bootstrap_hold_or_lost_result_cannot_contact_guests_copy_data_or_fence_sources(self):
        for option in ({'held': 'application_target_bootstrap'}, {'lose_result': 'application_target_bootstrap'}):
            with self.subTest(option=option):
                result, calls, effects = await self.run_case(CUTOVER, **option)
                self.assertEqual((result.status, result.phase, result.completed, result.total),
                                 ('HELD', 'PREPARE', 4, 19))
                self.assertEqual(calls, ['approval', 'application_verify_staged_data',
                    'application_target_prepare:vm-alpha', 'application_target_prepare:vm-beta',
                    'application_target_bootstrap:vm-alpha'])
                self.assertLessEqual(effects.count('application_target_bootstrap:vm-alpha'), 1)
                self.assertFalse(any(call.startswith('provision:') or 'source_fence' in call
                    or 'transfer_dataset' in call or call == 'application_cutover' for call in calls))

    async def test_lost_database_final_result_never_fences_vms_or_activates_target(self):
        result, calls, effects = await self.run_case(DATABASE, lose_result='application_database_final')
        self.assertEqual((result.status, result.phase, result.reason_code, result.completed, result.total),
                         ('HELD', 'CUTOVER', 'NATIVE_UNCERTAIN', 15, 23))
        self.assertEqual(effects.count('application_database_final:vm-alpha'), 1)
        self.assertFalse(any(call.startswith('application_source_fence:') for call in calls))
        self.assertNotIn('application_cutover', calls)

    async def test_policy_hold_or_lost_reply_stops_before_activation_and_is_not_repeated(self):
        for option in ({'held': 'application_target_policy'}, {'lose_result': 'application_target_policy'}):
            with self.subTest(option=option):
                result, calls, effects = await self.run_case(CUTOVER, **option)
                self.assertEqual((result.status, result.phase, result.completed, result.total),
                                 ('HELD', 'CUTOVER', 15, 19))
                self.assertEqual(calls[-1], 'application_target_policy:vm-alpha')
                self.assertNotIn('application_target_policy:vm-beta', calls)
                self.assertNotIn('application_cutover', calls)
                self.assertLessEqual(effects.count('application_target_policy:vm-alpha'), 1)

    async def test_historical_ordering_replays_under_new_code_without_inventing_policy_or_bootstrap(self):
        for markers, total in ((set(), 15), ({'isolated-management-bootstrap-v1'}, 17)):
            with self.subTest(markers=markers):
                result, calls, _ = await self.run_case(CUTOVER, historical_markers=markers)
                self.assertEqual((result.status, result.completed, result.total), ('SUCCEEDED', total, total))
                self.assertFalse(any(call.startswith('application_target_policy') for call in calls))
                self.assertEqual(any(call.startswith('application_target_bootstrap') for call in calls), bool(markers))

    async def test_final_acceptance_hold_or_lost_result_cannot_close_or_repeat_cutover(self):
        for option in ({'held': 'application_verify_cutover'}, {'lose_result': 'application_verify_cutover'}):
            with self.subTest(option=option):
                result, calls, effects = await self.run_case(DATABASE, **option)
                self.assertEqual((result.status, result.phase, result.completed, result.total), ('HELD', 'VERIFY', 22, 23))
                self.assertEqual(calls.count('application_cutover'), 1)
                self.assertEqual(calls.count('application_verify_cutover'), 1)
                self.assertEqual(effects.count('application_cutover'), 1)

    async def test_wrong_staging_member_or_boolean_cutover_evidence_cannot_advance(self):
        result, calls, _ = await self.run_case(STAGING, foreign_member='provision:initial-create')
        self.assertEqual((result.reason_code, result.completed), ('VALIDATION_FAILED', 2))
        self.assertNotIn('provision:associate-targets', calls)
        result, calls, _ = await self.run_case(CUTOVER, invalid_evidence='application_verify_staged_data')
        self.assertEqual((result.status, result.reason_code, result.completed), ('HELD', 'NATIVE_UNCERTAIN', 1))
        self.assertEqual(calls, ['approval', 'application_verify_staged_data'])


class SplitWorkflowValueTests(unittest.TestCase):
    def test_native_uncertainty_cannot_be_encoded_as_a_verified_provisioning_stage(self):
        verified = ApplicationStageResult('STAGE_VERIFIED', ADMITTED.job_id, 'initial-create',
                                          evidence_digest='1' * 64)
        for reason in ('NATIVE_UNCERTAIN', 'OPERATOR_HOLD', 'VALIDATION_FAILED'):
            with self.subTest(reason=reason), self.assertRaises(ValueError):
                replace(verified, reason_code=reason)

    def test_input_graphs_are_bounded_unique_and_digest_bound(self):
        for change in ({'provisioning_steps': ()}, {'machine_ids': ()}, {'machine_ids': ('vm', 'vm')},
                       {'selection_digest': True}, {'provisioning_steps': ('create;curl secret',)}):
            with self.subTest(staging=change), self.assertRaises(ValueError): replace(STAGING, **change)
        for change in ({'machine_ids': ()}, {'dataset_ids': ('data', 'data')},
                       {'staging_selection_digest': '/private/credential'},
                       {'database_selection_digest': 'f' * 64}, {'database_member_id': 'foreign-machine'},
                       {'database_selection_digest': True, 'database_member_id': 'vm-alpha'}):
            with self.subTest(cutover=change), self.assertRaises(ValueError): replace(CUTOVER, **change)

    def test_staging_success_and_cutover_success_require_their_exact_complete_proofs(self):
        staged = ApplicationStagingResult(ADMITTED.job_id, ADMITTED.plan_id, 1, ADMITTED.plan_digest,
            STAGING.selection_digest, 'STAGED', 'VERIFY', None, '1' * 64, 5, 5)
        for change in ({'evidence_digest': None}, {'evidence_digest': True}, {'completed': 4},
                       {'completed': True}, {'total': 104}, {'reason_code': 'OPERATOR_HOLD'}, {'phase': 'PROVISION'}):
            with self.subTest(staging=change), self.assertRaises(ValueError): replace(staged, **change)
        final = ApplicationJobResult(ADMITTED.job_id, ADMITTED.plan_id, 1, ADMITTED.plan_digest,
            CUTOVER.selection_digest, 'SUCCEEDED', 'VERIFY', None, '2' * 64, 13, 13,
            lifecycle_selection_digest=CUTOVER.lifecycle_selection_digest,
            staging_selection_digest=CUTOVER.staging_selection_digest)
        for change in ({'evidence_digest': None}, {'evidence_digest': True}, {'completed': 12},
                       {'lifecycle_selection_digest': None}, {'reason_code': 'OPERATOR_HOLD'}):
            with self.subTest(cutover=change), self.assertRaises(ValueError): replace(final, **change)


if __name__ == '__main__':
    unittest.main()
