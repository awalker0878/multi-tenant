"""Fixed Windows service purpose on the existing admitted-job Temporal queue.

No resource creation, guest image deployment, data transfer or cutover occurs.
SCM postconditions remain separate from old native command/credential exclusion.
"""
from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError

with workflow.unsafe.imports_passed_through():
    from .admitted_job import AdmittedInput, VERIFY_ADMITTED_JOB_ACTIVITY
    from .approval_gate import ApprovalCheck, _valid_digest, _valid_id

SERVICE_ACTIVITY = 'windows_existing_service_step'
NATIVE_EXCLUSION_HOLD = 'WINDOWS_SERVICE_NATIVE_EXCLUSION_REQUIRED'
_ACTIONS = frozenset({'CONFIGURE_AND_OBSERVE','OBSERVE_ORIGINAL','REMEDIATE_AND_OBSERVE'})


@dataclass(frozen=True)
class WindowsServiceInput:
    admitted: AdmittedInput
    selection_digest: str
    service_selection_digest: str
    action: str
    service_steps: tuple[str,...]
    machine_id: str

    def __post_init__(self):
        if (type(self.admitted) is not AdmittedInput or not _valid_digest(self.selection_digest)
                or not _valid_digest(self.service_selection_digest) or self.action not in _ACTIONS
                or not _valid_id(self.machine_id) or not isinstance(self.service_steps,(tuple,list))
                or len(self.service_steps)!=(1 if self.action=='OBSERVE_ORIGINAL' else 2)
                or len(set(self.service_steps))!=len(self.service_steps)
                or any(not _valid_id(value) for value in self.service_steps)):
            raise ValueError('Exact admitted existing-target Windows service references required')
        object.__setattr__(self,'service_steps',tuple(self.service_steps))


@dataclass(frozen=True)
class WindowsServiceStageRequest:
    input: WindowsServiceInput
    step_id: str

    def __post_init__(self):
        if type(self.input) is not WindowsServiceInput or self.step_id not in self.input.service_steps:
            raise ValueError('The exact selected existing Windows service stage is required')


@dataclass(frozen=True)
class WindowsServiceStageResult:
    job_id: str
    step_id: str
    status: str
    evidence_digest: str | None
    reason_code: str | None = None
    service_postconditions_observed: bool = False

    def __post_init__(self):
        if (not _valid_id(self.job_id) or not _valid_id(self.step_id)
                or self.status not in {'STAGE_COMPLETED','HELD'}
                or (self.evidence_digest is not None and not _valid_digest(self.evidence_digest))
                or self.reason_code not in {None,'AUTHORITY_REVOKED','NATIVE_UNCERTAIN',
                    'VALIDATION_FAILED','OPERATOR_HOLD','RECOVERY_REQUIRED'}
                or type(self.service_postconditions_observed) is not bool
                or (self.status=='STAGE_COMPLETED' and (self.evidence_digest is None or self.reason_code is not None))
                or (self.status=='HELD' and (self.reason_code is None or self.service_postconditions_observed))):
            raise ValueError('Fixed Windows stage evidence cannot imply native acceptance')


@dataclass(frozen=True)
class WindowsServiceResult:
    job_id: str
    plan_id: str
    plan_revision: int
    plan_digest: str
    selection_digest: str
    service_selection_digest: str
    status: str
    phase: str
    reason_code: str
    evidence_digest: str | None
    completed: int
    total: int
    service_postconditions_observed: bool = False
    hold_code: str | None = None
    native_acceptance: bool = False
    production_activation: bool = False

    def __post_init__(self):
        if (not _valid_id(self.job_id) or not _valid_id(self.plan_id) or type(self.plan_revision) is not int
                or self.plan_revision<1 or not _valid_digest(self.plan_digest)
                or not _valid_digest(self.selection_digest) or not _valid_digest(self.service_selection_digest)
                or self.status!='HELD' or self.phase not in {'APPROVAL','PROVISION','VERIFY'}
                or self.reason_code not in {'AUTHORITY_REVOKED','NATIVE_UNCERTAIN',
                    'VALIDATION_FAILED','OPERATOR_HOLD','RECOVERY_REQUIRED'}
                or (self.evidence_digest is not None and not _valid_digest(self.evidence_digest))
                or type(self.completed) is not int or type(self.total) is not int
                or not 0<=self.completed<=self.total<=3
                or type(self.service_postconditions_observed) is not bool
                or self.native_acceptance is not False or self.production_activation is not False
                or self.hold_code not in {None,NATIVE_EXCLUSION_HOLD}
                or (self.service_postconditions_observed and (self.completed!=self.total or self.phase!='VERIFY'
                    or self.evidence_digest is None or self.hold_code!=NATIVE_EXCLUSION_HOLD))):
            raise ValueError('Existing service postconditions cannot claim Windows native migration or old writer exclusion')


@workflow.defn(name='SelectedWindowsExistingServices')
class SelectedWindowsExistingServices:
    @workflow.run
    async def run(self,input:WindowsServiceInput)->WindowsServiceResult:
        admitted=input.admitted; completed=0; total=1+len(input.service_steps); evidence=None

        def held(phase,reason='OPERATOR_HOLD',*,observed=False):
            return WindowsServiceResult(admitted.job_id,admitted.plan_id,admitted.plan_revision,
                admitted.plan_digest,input.selection_digest,input.service_selection_digest,'HELD',phase,
                reason,evidence,completed,total,observed,NATIVE_EXCLUSION_HOLD if observed else None)

        try:
            checked=await workflow.execute_activity(VERIFY_ADMITTED_JOB_ACTIVITY,admitted,result_type=ApprovalCheck,
                start_to_close_timeout=timedelta(seconds=30),retry_policy=RetryPolicy(maximum_attempts=1))
            if (checked.authorized is not True or
                    (checked.job_id,checked.organization_id,checked.tenant_id,checked.plan_id,
                     checked.plan_revision,checked.plan_digest,checked.revocation_epoch)!=
                    (admitted.job_id,admitted.organization_id,admitted.tenant_id,admitted.plan_id,
                     admitted.plan_revision,admitted.plan_digest,admitted.revocation_epoch)
                    or not _valid_id(checked.approval_id) or not _valid_digest(checked.evidence_digest)):
                return held('APPROVAL','AUTHORITY_REVOKED')
            completed+=1
        except ActivityError:
            return held('APPROVAL','AUTHORITY_REVOKED')
        for index,step_id in enumerate(input.service_steps):
            final=index==len(input.service_steps)-1
            phase='VERIFY' if final else 'PROVISION'
            try:
                result=await workflow.execute_activity(SERVICE_ACTIVITY,WindowsServiceStageRequest(input,step_id),
                    result_type=WindowsServiceStageResult,start_to_close_timeout=timedelta(minutes=10),
                    retry_policy=RetryPolicy(maximum_attempts=1))
            except ActivityError:
                return held(phase,'NATIVE_UNCERTAIN')
            if result.job_id!=admitted.job_id or result.step_id!=step_id:
                return held(phase,'VALIDATION_FAILED')
            if result.status!='STAGE_COMPLETED' or not _valid_digest(result.evidence_digest):
                return held(phase,result.reason_code or 'OPERATOR_HOLD')
            if result.service_postconditions_observed is not final:
                return held(phase,'VALIDATION_FAILED')
            completed+=1; evidence=result.evidence_digest
        return held('VERIFY','NATIVE_UNCERTAIN',observed=True)
