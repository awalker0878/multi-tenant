"""Fixed newly admitted resource recovery on the existing B09 workflow queue.

Histories contain approved references only. This workflow has no reserve,
creation, application cutover or replay stage. Every effect activity runs once.
"""
from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError

with workflow.unsafe.imports_passed_through():
    from .admitted_job import AdmittedInput,VERIFY_ADMITTED_JOB_ACTIVITY
    from .approval_gate import ApprovalCheck,_valid_digest,_valid_id


@dataclass(frozen=True)
class ResourceRecoveryInput:
    admitted: AdmittedInput
    selection_digest: str
    recovery_selection_digest: str
    original_job_id: str
    original_selection_digest: str
    resource_bundle_digest: str
    original_worker_ids: tuple[str,...]
    cleanup_binding_keys: tuple[str,...]
    actions: tuple[str,...]

    def __post_init__(self):
        if (not isinstance(self.admitted,AdmittedInput) or not _valid_id(self.original_job_id)
                or self.original_job_id==self.admitted.job_id
                or any(not _valid_digest(value) for value in (self.selection_digest,
                    self.recovery_selection_digest,self.original_selection_digest,self.resource_bundle_digest))
                or any(not isinstance(values,(tuple,list)) or len(values)>1000
                    or list(values)!=sorted(set(values)) or any(not _valid_id(value) for value in values)
                    for values in (self.original_worker_ids,self.cleanup_binding_keys))
                or not isinstance(self.actions,(tuple,list)) or not self.actions
                or list(self.actions)!=sorted(set(self.actions)) or not set(self.actions)<={'cleanup','release'}):
            raise ValueError('Exact newly admitted original-resource recovery references required')
        for field in ('original_worker_ids','cleanup_binding_keys','actions'):
            object.__setattr__(self,field,tuple(getattr(self,field)))


@dataclass(frozen=True)
class ResourceRecoveryStageRequest:
    input: ResourceRecoveryInput
    member_id: str=''

    def __post_init__(self):
        if not isinstance(self.input,ResourceRecoveryInput) or (self.member_id and not _valid_id(self.member_id)):
            raise ValueError('Exact original recovery stage reference required')


@dataclass(frozen=True)
class ResourceRecoveryStageResult:
    job_id: str
    member_id: str
    status: str
    evidence_digest: str|None=None
    reason_code: str|None=None

    def __post_init__(self):
        if (not _valid_id(self.job_id) or (self.member_id and not _valid_id(self.member_id))
                or self.status not in {'STAGE_VERIFIED','HELD'}
                or (self.evidence_digest is not None and not _valid_digest(self.evidence_digest))
                or self.reason_code not in {None,'AUTHORITY_REVOKED','NATIVE_UNCERTAIN',
                    'RECOVERY_REQUIRED','VALIDATION_FAILED','OPERATOR_HOLD','WORKFLOW_FAILED'}
                or (self.status=='STAGE_VERIFIED' and (self.evidence_digest is None or self.reason_code is not None))
                or (self.status=='HELD' and self.reason_code is None)):
            raise ValueError('Bounded actual recovery stage metadata required')


@dataclass(frozen=True)
class ResourceRecoveryResult:
    job_id: str
    plan_id: str
    plan_revision: int
    plan_digest: str
    selection_digest: str
    recovery_selection_digest: str
    original_job_id: str
    status: str
    phase: str
    completed: int
    total: int
    evidence_digest: str|None
    reason_code: str|None

    def __post_init__(self):
        if (not all(_valid_id(value) for value in (self.job_id,self.plan_id,self.original_job_id))
                or self.job_id==self.original_job_id or type(self.plan_revision) is not int or self.plan_revision<1
                or not all(_valid_digest(value) for value in
                    (self.plan_digest,self.selection_digest,self.recovery_selection_digest))
                or self.status not in {'HELD','SUCCEEDED'} or self.phase not in {'RECONCILE','CLEANUP','VERIFY'}
                or type(self.completed) is not int or type(self.total) is not int
                or not 0<=self.completed<=self.total<=3000
                or (self.evidence_digest is not None and not _valid_digest(self.evidence_digest))
                or self.reason_code not in {None,'AUTHORITY_REVOKED','NATIVE_UNCERTAIN',
                    'RECOVERY_REQUIRED','VALIDATION_FAILED','OPERATOR_HOLD','WORKFLOW_FAILED'}
                or (self.status=='HELD' and self.reason_code is None)
                or (self.status=='SUCCEEDED' and (self.phase!='VERIFY' or self.completed!=self.total
                    or self.reason_code is not None or self.evidence_digest is None))):
            raise ValueError('Exact recovery projection required')


@workflow.defn(name='SelectedResourceRecovery')
class SelectedResourceRecovery:
    @workflow.run
    async def run(self,input: ResourceRecoveryInput)->ResourceRecoveryResult:
        admitted=input.admitted
        total=3+len(input.original_worker_ids)+len(input.cleanup_binding_keys)
        if 'release' in input.actions: total+=1
        completed=0; evidence=None

        def result(status,phase,reason=None):
            return ResourceRecoveryResult(admitted.job_id,admitted.plan_id,admitted.plan_revision,
                admitted.plan_digest,input.selection_digest,input.recovery_selection_digest,
                input.original_job_id,status,phase,completed,total,evidence,reason)

        try:
            checked=await workflow.execute_activity(VERIFY_ADMITTED_JOB_ACTIVITY,admitted,
                result_type=ApprovalCheck,start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=1))
            if (checked.authorized is not True or
                    (checked.job_id,checked.organization_id,checked.tenant_id,checked.plan_id,
                     checked.plan_revision,checked.plan_digest,checked.revocation_epoch)!=
                    (admitted.job_id,admitted.organization_id,admitted.tenant_id,admitted.plan_id,
                     admitted.plan_revision,admitted.plan_digest,admitted.revocation_epoch)
                    or not _valid_id(checked.approval_id) or not _valid_digest(checked.evidence_digest)):
                return result('HELD','RECONCILE','AUTHORITY_REVOKED')
            completed+=1
        except ActivityError:
            return result('HELD','RECONCILE','AUTHORITY_REVOKED')

        async def stage(name,member='',phase='RECONCILE'):
            nonlocal completed,evidence
            try:
                stage_result=await workflow.execute_activity(name,ResourceRecoveryStageRequest(input,member),
                    result_type=ResourceRecoveryStageResult,start_to_close_timeout=timedelta(minutes=10),
                    retry_policy=RetryPolicy(maximum_attempts=1))
            except ActivityError:
                return result('HELD',phase,'NATIVE_UNCERTAIN')
            if (stage_result.job_id,stage_result.member_id)!=(admitted.job_id,member):
                return result('HELD',phase,'VALIDATION_FAILED')
            if stage_result.status!='STAGE_VERIFIED':
                return result('HELD',phase,stage_result.reason_code or 'RECOVERY_REQUIRED')
            completed+=1; evidence=stage_result.evidence_digest
            return None

        for worker in input.original_worker_ids:
            name='resource_recovery_fence_original' if 'cleanup' in input.actions else 'resource_recovery_inspect_fence'
            held=await stage(name,worker)
            if held: return held
        held=await stage('resource_recovery_require_original_resolution')
        if held: return held
        if 'cleanup' in input.actions:
            for binding in input.cleanup_binding_keys:
                held=await stage('resource_recovery_cleanup_native',binding,'CLEANUP')
                if held: return held
        elif input.cleanup_binding_keys:
            # Release-only approval may inspect cleanup already performed but
            # cannot authorize another native DELETE.
            for binding in input.cleanup_binding_keys:
                held=await stage('resource_recovery_inspect_native',binding,'CLEANUP')
                if held: return held
        held=await stage('resource_recovery_verify_resources',phase='VERIFY')
        if held: return held
        if 'release' in input.actions:
            held=await stage('resource_recovery_release_observed',phase='VERIFY')
            if held: return held
        return result('SUCCEEDED','VERIFY')
