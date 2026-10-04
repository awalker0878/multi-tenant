"""Actual Temporal histories for fixed Windows existing-service references.

Activity proof DTOs are synthetic. This tests durable no-repeat orchestration,
never native Windows acceptance or platform/method qualification.
"""
import asyncio
from dataclasses import replace
import unittest

from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker,Replayer

from provisioner.controlplane.jobs import AdmissionConflict
from provisioner.controlplane.jobs.repository import _digest
from provisioner.controlplane.workflow.admitted_job import AdmittedInput,VERIFY_ADMITTED_JOB_ACTIVITY
from provisioner.controlplane.workflow.approval_gate import ApprovalCheck
from provisioner.controlplane.workflow.temporal_adapter import TemporalConnection,TemporalWorkflowStarter
from provisioner.controlplane.workflow.windows_service_job import (WindowsServiceInput,WindowsServiceStageRequest,
    WindowsServiceStageResult,WindowsServiceResult,SelectedWindowsExistingServices,SERVICE_ACTIVITY,NATIVE_EXCLUSION_HOLD)

PAYLOAD=dict(format='hosting-workflow-start/1',job_id='windows-service-job',organization_id='org',
    tenant_id='tenant',plan_id='windows-plan',plan_revision=1,plan_digest='a'*64,revocation_epoch=0)
ADMITTED=AdmittedInput(PAYLOAD['job_id'],'org','tenant','windows-plan',1,'a'*64,0,_digest(PAYLOAD))
INPUT=WindowsServiceInput(ADMITTED,'b'*64,'c'*64,'CONFIGURE_AND_OBSERVE',('configure','observe'),'windows-vm')


class WindowsServiceWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def run_case(self,*,lost=None,revoke=False,false_read=False):
        calls=[]
        @activity.defn(name=VERIFY_ADMITTED_JOB_ACTIVITY)
        async def approve(request:AdmittedInput)->ApprovalCheck:
            calls.append('approval')
            return ApprovalCheck(not revoke,request.job_id,request.organization_id,request.tenant_id,
                request.plan_id,request.plan_revision,request.plan_digest,request.revocation_epoch,'approval','d'*64)
        @activity.defn(name=SERVICE_ACTIVITY)
        async def stage(request:WindowsServiceStageRequest)->WindowsServiceStageResult:
            calls.append(request.step_id)
            if request.step_id==lost: raise RuntimeError('Synthetic result lost after native dispatch')
            return WindowsServiceStageResult(request.input.admitted.job_id,request.step_id,'STAGE_COMPLETED','e'*64,
                service_postconditions_observed=request.step_id=='observe' and not false_read)
        async with await WorkflowEnvironment.start_local() as env:
            starter=TemporalWorkflowStarter(TemporalConnection(env.client.service_client.config.target_host,
                'default','windows-existing',insecure_loopback_for_tests=True),
                application_selector=lambda admitted:replace(INPUT,admitted=admitted))
            receipt=await asyncio.to_thread(starter.start,namespace='default',workflow_id=ADMITTED.job_id,payload=PAYLOAD)
            self.assertEqual(receipt,await asyncio.to_thread(starter.start,
                namespace='default',workflow_id=ADMITTED.job_id,payload=PAYLOAD))
            handle=env.client.get_workflow_handle(ADMITTED.job_id,run_id=receipt.run_id,result_type=WindowsServiceResult)
            async with Worker(env.client,task_queue='windows-existing',workflows=[SelectedWindowsExistingServices],
                              activities=[approve,stage]):
                result=await asyncio.wait_for(handle.result(),20)
                history=await handle.fetch_history()
            await Replayer(workflows=[SelectedWindowsExistingServices]).replay_workflow(history)
            self.assertEqual(result,await asyncio.to_thread(starter.completed_job,receipt))
            changed=TemporalWorkflowStarter(starter.connection,application_selector=lambda admitted:
                replace(INPUT,admitted=admitted,service_selection_digest='f'*64))
            with self.assertRaises(AdmissionConflict):
                await asyncio.to_thread(changed.start,namespace='default',workflow_id=ADMITTED.job_id,payload=PAYLOAD)
        return result,calls

    async def test_actual_fixed_history_observes_scm_but_never_projects_native_windows_acceptance(self):
        result,calls=await self.run_case()
        self.assertEqual(calls,['approval','configure','observe'])
        self.assertEqual((result.status,result.phase,result.completed,result.total),('HELD','VERIFY',3,3))
        self.assertTrue(result.service_postconditions_observed); self.assertFalse(result.native_acceptance)
        self.assertFalse(result.production_activation); self.assertEqual(result.hold_code,NATIVE_EXCLUSION_HOLD)

    async def test_lost_write_response_never_retries_or_dispatches_reader(self):
        result,calls=await self.run_case(lost='configure')
        self.assertEqual(calls,['approval','configure'])
        self.assertEqual((result.phase,result.reason_code),('PROVISION','NATIVE_UNCERTAIN'))
        self.assertFalse(result.service_postconditions_observed)

    async def test_revoked_initial_approval_prevents_every_service_request(self):
        result,calls=await self.run_case(revoke=True)
        self.assertEqual(calls,['approval']); self.assertEqual(result.reason_code,'AUTHORITY_REVOKED')

    async def test_matching_success_dto_without_independent_service_state_is_held(self):
        result,calls=await self.run_case(false_read=True)
        self.assertEqual(calls,['approval','configure','observe'])
        self.assertEqual(result.reason_code,'VALIDATION_FAILED'); self.assertFalse(result.service_postconditions_observed)


class WindowsServiceReferenceTests(unittest.TestCase):
    def test_history_is_fixed_bounded_nonsecret_references(self):
        self.assertEqual(replace(INPUT,service_steps=['configure','observe']),INPUT)
        for change in ({'action':'COLD_EXPORT_IMPORT'},{'service_steps':('curl https://example','observe')},
                       {'service_selection_digest':'/private/key'},{'machine_id':'arbitrary shell command'}):
            with self.subTest(change=change),self.assertRaises(ValueError): replace(INPUT,**change)
        with self.assertRaises(ValueError):
            WindowsServiceResult(ADMITTED.job_id,ADMITTED.plan_id,1,'a'*64,'b'*64,'c'*64,
                'SUCCEEDED','VERIFY','NATIVE_UNCERTAIN','d'*64,3,3,True,NATIVE_EXCLUSION_HOLD)


if __name__=='__main__': unittest.main()
