"""Actual Temporal history/replay for fixed no-repeat original resource recovery.

Activity results here are explicit synthetic evidence. Native protocol and real
PostgreSQL authorities have separate tests; these histories grant no acceptance.
"""
from dataclasses import replace
import asyncio
import unittest

from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker,Replayer

from provisioner.controlplane.workflow.admitted_job import AdmittedInput,VERIFY_ADMITTED_JOB_ACTIVITY
from provisioner.controlplane.workflow.approval_gate import ApprovalCheck
from provisioner.controlplane.workflow.resource_recovery_job import (ResourceRecoveryInput,
    ResourceRecoveryStageRequest,ResourceRecoveryStageResult,ResourceRecoveryResult,SelectedResourceRecovery)


ADMITTED=AdmittedInput('recovery-job','org','tenant','recovery-plan',1,'a'*64,0,'b'*64)
INPUT=ResourceRecoveryInput(ADMITTED,'c'*64,'d'*64,'original-job','e'*64,'f'*64,
    ('old-worker',),('cleanup-0-vm','cleanup-1-nic','cleanup-2-volume'),('cleanup','release'))


class ResourceRecoveryWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def run_case(self,*,input=INPUT,hold=None,lost=None):
        calls=[]
        @activity.defn(name=VERIFY_ADMITTED_JOB_ACTIVITY)
        async def approve(request: AdmittedInput)->ApprovalCheck:
            calls.append(('approval',''))
            return ApprovalCheck(True,request.job_id,request.organization_id,request.tenant_id,
                request.plan_id,request.plan_revision,request.plan_digest,request.revocation_epoch,'approval','1'*64)
        def fixed(name):
            @activity.defn(name=name)
            async def run(request: ResourceRecoveryStageRequest)->ResourceRecoveryStageResult:
                calls.append((name,request.member_id))
                if name==lost: raise RuntimeError('Synthetic lost original native response')
                if name==hold:
                    return ResourceRecoveryStageResult(request.input.admitted.job_id,request.member_id,
                        'HELD',reason_code='RECOVERY_REQUIRED')
                return ResourceRecoveryStageResult(request.input.admitted.job_id,request.member_id,
                    'STAGE_VERIFIED','2'*64)
            return run
        stages=[fixed(name) for name in ('resource_recovery_fence_original','resource_recovery_inspect_fence',
            'resource_recovery_require_original_resolution','resource_recovery_cleanup_native',
            'resource_recovery_inspect_native','resource_recovery_verify_resources','resource_recovery_release_observed')]
        async with await WorkflowEnvironment.start_local() as env:
            async with Worker(env.client,task_queue='recovery',workflows=[SelectedResourceRecovery],
                              activities=[approve,*stages]):
                handle=await env.client.start_workflow(SelectedResourceRecovery.run,input,
                    id=ADMITTED.job_id,task_queue='recovery')
                result=await asyncio.wait_for(handle.result(),20)
                history=await handle.fetch_history()
            await Replayer(workflows=[SelectedResourceRecovery]).replay_workflow(history)
        return result,calls

    async def test_selected_fences_native_dependency_order_and_refund_replay(self):
        result,calls=await self.run_case()
        self.assertEqual((result.status,result.completed,result.total),('SUCCEEDED',8,8))
        self.assertEqual(calls,[('approval',''),('resource_recovery_fence_original','old-worker'),
            ('resource_recovery_require_original_resolution',''),('resource_recovery_cleanup_native','cleanup-0-vm'),
            ('resource_recovery_cleanup_native','cleanup-1-nic'),('resource_recovery_cleanup_native','cleanup-2-volume'),
            ('resource_recovery_verify_resources',''),('resource_recovery_release_observed','')])

    async def test_unresolved_original_intent_never_reaches_delete_or_refund(self):
        result,calls=await self.run_case(hold='resource_recovery_require_original_resolution')
        self.assertEqual((result.status,result.phase,result.completed),('HELD','RECONCILE',2))
        self.assertFalse(any(name in {'resource_recovery_cleanup_native','resource_recovery_release_observed'}
                             for name,member in calls))

    async def test_lost_cleanup_result_is_not_retried_and_stops_the_other_children(self):
        result,calls=await self.run_case(lost='resource_recovery_cleanup_native')
        self.assertEqual((result.status,result.phase,result.reason_code),('HELD','CLEANUP','NATIVE_UNCERTAIN'))
        self.assertEqual([member for name,member in calls if name=='resource_recovery_cleanup_native'],['cleanup-0-vm'])
        self.assertNotIn(('resource_recovery_release_observed',''),calls)

    async def test_release_only_never_authorizes_vault_revocation_or_native_delete(self):
        result,calls=await self.run_case(input=replace(INPUT,actions=('release',)))
        self.assertEqual(result.status,'SUCCEEDED')
        self.assertIn(('resource_recovery_inspect_fence','old-worker'),calls)
        self.assertEqual(len([name for name,member in calls if name=='resource_recovery_inspect_native']),3)
        self.assertFalse(any(name in {'resource_recovery_fence_original','resource_recovery_cleanup_native'}
                             for name,member in calls))


class ResourceRecoveryReferenceTests(unittest.TestCase):
    def test_history_contains_only_sorted_bounded_exact_original_references(self):
        self.assertEqual(replace(INPUT,actions=['cleanup','release']),INPUT)
        for change in ({'original_job_id':ADMITTED.job_id},{'cleanup_binding_keys':('curl https://example',)},
                {'original_worker_ids':('worker','worker')},{'actions':('release','cleanup')},
                {'resource_bundle_digest':'/private/cloud.json'}):
            with self.subTest(change=change),self.assertRaises(ValueError): replace(INPUT,**change)
        with self.assertRaises(ValueError):
            ResourceRecoveryResult(ADMITTED.job_id,ADMITTED.plan_id,1,'a'*64,'b'*64,'c'*64,'old-job',
                'HELD','VERIFY',0,1,None,'/private/credential')
