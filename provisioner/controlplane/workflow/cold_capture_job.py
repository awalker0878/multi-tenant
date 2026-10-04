"""Fixed snapshot export and image import on the existing admitted-job queue.

History contains approved references and retained evidence digests. These
effects run once; an interrupted native attempt remains held for the original
registry's independent reconciliation. IMPORTED is a bytes-only purpose.
"""
from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError

with workflow.unsafe.imports_passed_through():
    from .admitted_job import AdmittedInput, VERIFY_ADMITTED_JOB_ACTIVITY
    from .approval_gate import ApprovalCheck, _valid_digest, _valid_id

_REASONS = frozenset({'AUTHORITY_REVOKED','NATIVE_UNCERTAIN','VALIDATION_FAILED',
                     'OPERATOR_HOLD','RECOVERY_REQUIRED','CAPACITY_UNAVAILABLE'})


@dataclass(frozen=True)
class ColdCaptureInput:
    admitted: AdmittedInput
    selection_digest: str
    cold_selection_digest: str
    export_step_id: str
    image_steps: tuple[str,...]

    def __post_init__(self):
        if (type(self.admitted) is not AdmittedInput or not _valid_digest(self.selection_digest)
                or not _valid_digest(self.cold_selection_digest) or not _valid_id(self.export_step_id)
                or not isinstance(self.image_steps,(tuple,list)) or not 2<=len(self.image_steps)<=32
                or len(self.image_steps)%2 or len(set(self.image_steps))!=len(self.image_steps)
                or self.export_step_id in self.image_steps
                or any(not _valid_id(value) for value in self.image_steps)):
            raise ValueError('Exact admitted complete cold capture and original image phase references required')
        object.__setattr__(self,'image_steps',tuple(self.image_steps))


@dataclass(frozen=True)
class ColdCaptureStageRequest:
    input: ColdCaptureInput
    step_id: str = ''
    capture_digest: str | None = None

    def __post_init__(self):
        if (type(self.input) is not ColdCaptureInput
                or self.step_id not in ('',self.input.export_step_id,*self.input.image_steps)
                or (self.capture_digest is not None and not _valid_digest(self.capture_digest))
                or (self.step_id==self.input.export_step_id and self.capture_digest is not None)
                or (self.step_id!=self.input.export_step_id and self.capture_digest is None)):
            raise ValueError('Exact cold stage and actual original captured bytes reference required')


@dataclass(frozen=True)
class ColdCaptureStageResult:
    job_id: str
    step_id: str
    status: str
    evidence_digest: str | None = None
    capture_digest: str | None = None
    reason_code: str | None = None
    guest_boot_qualified: bool = False
    production_activation: bool = False

    def __post_init__(self):
        if (not _valid_id(self.job_id) or (self.step_id and not _valid_id(self.step_id))
                or self.status not in {'CAPTURED','IMPORTED','VERIFIED','HELD'}
                or any(value is not None and not _valid_digest(value)
                    for value in (self.evidence_digest,self.capture_digest))
                or self.reason_code not in {None,*_REASONS}
                or self.guest_boot_qualified is not False or self.production_activation is not False
                or (self.status=='HELD' and self.reason_code is None)
                or (self.status!='HELD' and (self.reason_code is not None
                    or self.evidence_digest is None or self.capture_digest is None))
                or (self.status=='VERIFIED' and self.step_id)):
            raise ValueError('Original capture/import evidence cannot authorize guest boot or activation')


@dataclass(frozen=True)
class ColdCaptureResult:
    job_id: str
    plan_id: str
    plan_revision: int
    plan_digest: str
    selection_digest: str
    cold_selection_digest: str
    status: str
    phase: str
    completed: int
    total: int
    evidence_digest: str | None
    capture_digest: str | None
    reason_code: str | None
    guest_boot_qualified: bool = False
    production_activation: bool = False

    def __post_init__(self):
        if (not _valid_id(self.job_id) or not _valid_id(self.plan_id)
                or type(self.plan_revision) is not int or self.plan_revision<1
                or any(not _valid_digest(value) for value in
                    (self.plan_digest,self.selection_digest,self.cold_selection_digest))
                or self.status not in {'HELD','IMPORTED'} or self.phase not in {'APPROVAL','CAPTURE','IMPORT','VERIFY'}
                or type(self.completed) is not int or type(self.total) is not int
                or not 0<=self.completed<=self.total<=35
                or any(value is not None and not _valid_digest(value)
                    for value in (self.evidence_digest,self.capture_digest))
                or self.reason_code not in {None,*_REASONS}
                or self.guest_boot_qualified is not False or self.production_activation is not False
                or (self.status=='HELD' and self.reason_code is None)
                or (self.status=='IMPORTED' and (self.phase!='VERIFY' or self.completed!=self.total
                    or self.reason_code is not None or self.evidence_digest is None or self.capture_digest is None))):
            raise ValueError('Complete imported-byte purpose must retain original evidence and its boot hold')


@workflow.defn(name='SelectedColdCapture')
class SelectedColdCapture:
    @workflow.run
    async def run(self,input:ColdCaptureInput)->ColdCaptureResult:
        admitted=input.admitted; completed=0; total=3+len(input.image_steps)
        evidence=None; captured=None

        def result(status,phase,reason=None):
            return ColdCaptureResult(admitted.job_id,admitted.plan_id,admitted.plan_revision,
                admitted.plan_digest,input.selection_digest,input.cold_selection_digest,status,phase,
                completed,total,evidence,captured,reason)

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
                return result('HELD','APPROVAL','AUTHORITY_REVOKED')
            completed+=1
        except ActivityError:
            return result('HELD','APPROVAL','AUTHORITY_REVOKED')

        for name,step,phase,expected in (
                ('cold_capture_export',input.export_step_id,'CAPTURE','CAPTURED'),
                *(('cold_capture_import',step,'IMPORT','IMPORTED') for step in input.image_steps),
                ('cold_capture_verify','','VERIFY','VERIFIED')):
            try:
                stage=await workflow.execute_activity(name,ColdCaptureStageRequest(input,step,captured),
                    result_type=ColdCaptureStageResult,start_to_close_timeout=timedelta(hours=4),
                    retry_policy=RetryPolicy(maximum_attempts=1))
            except ActivityError:
                return result('HELD',phase,'NATIVE_UNCERTAIN')
            if (stage.job_id,stage.step_id)!=(admitted.job_id,step):
                return result('HELD',phase,'VALIDATION_FAILED')
            if stage.status!=expected:
                return result('HELD',phase,stage.reason_code or 'OPERATOR_HOLD')
            if (not _valid_digest(stage.evidence_digest) or not _valid_digest(stage.capture_digest)
                    or (captured is not None and captured!=stage.capture_digest)):
                return result('HELD',phase,'VALIDATION_FAILED')
            captured=stage.capture_digest; evidence=stage.evidence_digest; completed+=1
        return result('IMPORTED','VERIFY')
