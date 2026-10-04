"""Cold-purpose causality/no-retry contracts; no native qualification evidence."""
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from temporalio.exceptions import ActivityError

from provisioner.controlplane.workflow.admitted_job import AdmittedInput,VERIFY_ADMITTED_JOB_ACTIVITY
from provisioner.controlplane.workflow.approval_gate import ApprovalCheck
from provisioner.controlplane.workflow.cold_capture_job import (ColdCaptureInput,ColdCaptureStageRequest,
    ColdCaptureStageResult,SelectedColdCapture)
from provisioner.controlplane.workflow.cold_capture_selection import (PostgresColdCaptureSelector,
    SelectedColdPurpose,cold_input)
from provisioner.controlplane.workflow.execution_selection import FileExecutionSelectionStore
from provisioner.migration.cold_activities import ColdCaptureActivities,ColdCaptureRuntimeBindings
from provisioner.migration.cold_selection import FileColdSelectionStore
from tests.provisioning.mobility.cold_fixture import selection


ADMITTED=AdmittedInput('cold-job','org-01','tenant-01','cold-plan',1,'a'*64,0,'b'*64)


class ColdPurposeTests(unittest.IsolatedAsyncioTestCase):
    async def run_case(self,*,revoke=False,lose=None,changed=None):
        with tempfile.TemporaryDirectory() as temporary:
            cold=selection(Path(temporary)); selected=cold_input(ADMITTED,'c'*64,cold)
        calls=[]; requests=[]
        async def execute(name,request,**options):
            calls.append(name); requests.append(request)
            self.assertEqual(options['retry_policy'].maximum_attempts,1)
            if name==VERIFY_ADMITTED_JOB_ACTIVITY:
                return ApprovalCheck(not revoke,ADMITTED.job_id,ADMITTED.organization_id,ADMITTED.tenant_id,
                    ADMITTED.plan_id,1,ADMITTED.plan_digest,0,'approval','d'*64)
            if name==lose:
                raise ActivityError('Original response lost',scheduled_event_id=1,started_event_id=2,
                    identity='synthetic-worker',activity_type=name,activity_id='original',retry_state=None)
            status={'cold_capture_export':'CAPTURED','cold_capture_import':'IMPORTED','cold_capture_verify':'VERIFIED'}[name]
            digest=('f'*64 if name==changed else 'e'*64)
            return ColdCaptureStageResult(ADMITTED.job_id,request.step_id,status,'d'*64,digest)
        with patch('provisioner.controlplane.workflow.cold_capture_job.workflow.execute_activity',execute):
            result=await SelectedColdCapture().run(selected)
        return selected,result,calls,requests

    async def test_complete_graph_preserves_one_capture_and_stops_at_imported_bytes(self):
        selected,result,calls,requests=await self.run_case()
        self.assertEqual(calls,[VERIFY_ADMITTED_JOB_ACTIVITY,'cold_capture_export',
            *['cold_capture_import']*len(selected.image_steps),'cold_capture_verify'])
        self.assertEqual(result.status,'IMPORTED'); self.assertEqual(result.completed,result.total)
        self.assertFalse(result.guest_boot_qualified); self.assertFalse(result.production_activation)
        self.assertIsNone(requests[1].capture_digest)
        self.assertTrue(all(request.capture_digest=='e'*64 for request in requests[2:]))
        self.assertEqual(tuple(request.step_id for request in requests[2:-1]),selected.image_steps)

    async def test_revoked_approval_contacts_no_native_stage(self):
        _input,result,calls,_requests=await self.run_case(revoke=True)
        self.assertEqual((result.status,result.reason_code,result.completed),('HELD','AUTHORITY_REVOKED',0))
        self.assertEqual(calls,[VERIFY_ADMITTED_JOB_ACTIVITY])

    async def test_lost_original_export_or_import_response_never_repeats_or_continues(self):
        for name in ('cold_capture_export','cold_capture_import'):
            with self.subTest(stage=name):
                _input,result,calls,_requests=await self.run_case(lose=name)
                self.assertEqual(result.reason_code,'NATIVE_UNCERTAIN')
                self.assertEqual(calls.count(name),1); self.assertNotIn('cold_capture_verify',calls)

    async def test_valid_digest_from_another_capture_does_not_continue_graph(self):
        _input,result,calls,_requests=await self.run_case(changed='cold_capture_import')
        self.assertEqual(result.reason_code,'VALIDATION_FAILED')
        self.assertEqual(calls.count('cold_capture_import'),1); self.assertNotIn('cold_capture_verify',calls)

    async def test_missing_actual_enrollment_produces_explicit_hold_without_dispatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary); cold=selection(directory); input=cold_input(ADMITTED,'c'*64,cold)
            selector=PostgresColdCaptureSelector(lambda:None,FileExecutionSelectionStore(directory),
                                                 FileColdSelectionStore(directory))
            activities=ColdCaptureActivities(selector=selector,bindings=ColdCaptureRuntimeBindings(),directory=directory)
            purpose=SelectedColdPurpose(input,{}, {},cold)
            with patch.object(selector,'require_input',return_value=purpose):
                result=activities.export_snapshot(ColdCaptureStageRequest(input,input.export_step_id))
            self.assertEqual((result.status,result.reason_code),('HELD','RECOVERY_REQUIRED'))
            self.assertIsNone(result.evidence_digest); self.assertFalse(result.guest_boot_qualified)

    def test_history_cannot_contain_partial_disks_duplicate_operations_or_unknown_capture(self):
        input=ColdCaptureInput(ADMITTED,'c'*64,'d'*64,'export',('disk-create','disk-upload'))
        for changed in ({'image_steps':('only-create',)}, {'image_steps':('duplicate','duplicate')},
                        {'cold_selection_digest':True}, {'image_steps':('export','upload')}):
            with self.subTest(changed=changed),self.assertRaises(ValueError):replace(input,**changed)
        with self.assertRaises(ValueError):ColdCaptureStageRequest(input,'disk-upload')
        with self.assertRaises(ValueError):ColdCaptureStageRequest(input,'export','e'*64)
        with self.assertRaises(ValueError):ColdCaptureStageResult('cold-job','export','CAPTURED','e'*64,'f'*64,
                                                                 guest_boot_qualified=True)
