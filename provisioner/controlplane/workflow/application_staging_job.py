"""Create actual targets before a later approval can bind their observed IDs."""
from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError

with workflow.unsafe.imports_passed_through():
    from .admitted_job import AdmittedInput, VERIFY_ADMITTED_JOB_ACTIVITY
    from .approval_gate import ApprovalCheck, _valid_digest, _valid_id
    from .application_job import ApplicationStageRequest, ApplicationStageResult
    from provisioner.controlplane.jobs.progress import APPLICATION_HOLD_CODES
    from provisioner.migration.activities import MigrationActivityRequest, MigrationActivityResult


@dataclass(frozen=True)
class ApplicationStagingInput:
    admitted: AdmittedInput
    selection_digest: str
    provisioning_steps: tuple[str, ...]
    machine_ids: tuple[str, ...]

    def __post_init__(self):
        if (not isinstance(self.admitted, AdmittedInput) or not _valid_digest(self.selection_digest)
                or any(not isinstance(values, (tuple, list)) or not 1 <= len(values) <= 100
                       or len(set(values)) != len(values) or any(not _valid_id(value) for value in values)
                       for values in (self.provisioning_steps, self.machine_ids))):
            raise ValueError('Exact admitted target creation graph required')


@dataclass(frozen=True)
class ApplicationStagingResult:
    job_id: str
    plan_id: str
    plan_revision: int
    plan_digest: str
    selection_digest: str
    status: str
    phase: str
    reason_code: str | None
    evidence_digest: str | None
    completed: int
    total: int
    hold_code: str | None = None

    def __post_init__(self):
        if (not _valid_id(self.job_id) or not _valid_id(self.plan_id)
                or type(self.plan_revision) is not int or self.plan_revision < 1
                or not _valid_digest(self.plan_digest) or not _valid_digest(self.selection_digest)
                or self.status not in {'HELD', 'STAGED'} or self.phase not in {'APPROVAL', 'PREPARE', 'PROVISION', 'VERIFY'}
                or self.reason_code not in {None, 'AUTHORITY_REVOKED', 'NATIVE_UNCERTAIN', 'CAPACITY_UNAVAILABLE',
                    'VALIDATION_FAILED', 'OPERATOR_HOLD', 'RECOVERY_REQUIRED', 'POLICY_DENIED', 'TIMEOUT', 'WORKFLOW_FAILED'}
                or (self.evidence_digest is not None and not _valid_digest(self.evidence_digest))
                or (self.hold_code is not None and self.hold_code not in APPLICATION_HOLD_CODES)
                or type(self.completed) is not int or type(self.total) is not int
                or not 0 <= self.completed <= self.total <= 103
                or (self.status == 'HELD' and self.reason_code is None)
                or (self.status == 'STAGED' and (self.phase != 'VERIFY' or self.reason_code is not None
                    or self.hold_code is not None or self.evidence_digest is None or self.completed != self.total))):
            raise ValueError('Target staging must retain the actual complete observed handover')


@workflow.defn(name='OpenStackApplicationStaging')
class OpenStackApplicationStaging:
    @workflow.run
    async def run(self, input: ApplicationStagingInput) -> ApplicationStagingResult:
        admitted = input.admitted
        completed, evidence, total = 0, None, 3 + len(input.provisioning_steps)

        def held(phase, reason='OPERATOR_HOLD', proof=None, code=None):
            return ApplicationStagingResult(admitted.job_id, admitted.plan_id, admitted.plan_revision,
                admitted.plan_digest, input.selection_digest, 'HELD', phase, reason,
                proof or evidence, completed, total, code)

        try:
            checked = await workflow.execute_activity(VERIFY_ADMITTED_JOB_ACTIVITY, admitted,
                result_type=ApprovalCheck, start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=1))
            if (checked.authorized is not True or
                    (checked.job_id, checked.organization_id, checked.tenant_id, checked.plan_id,
                     checked.plan_revision, checked.plan_digest, checked.revocation_epoch) !=
                    (admitted.job_id, admitted.organization_id, admitted.tenant_id, admitted.plan_id,
                     admitted.plan_revision, admitted.plan_digest, admitted.revocation_epoch)
                    or not _valid_id(checked.approval_id) or not _valid_digest(checked.evidence_digest)):
                return held('APPROVAL', 'AUTHORITY_REVOKED')
            completed += 1
        except ActivityError:
            return held('APPROVAL', 'AUTHORITY_REVOKED')

        for name, member, phase in (
                ('application_reserve_resources', '', 'PREPARE'),
                *(('application_provision_step', step, 'PROVISION') for step in input.provisioning_steps),
                ('application_stage_targets', '', 'VERIFY')):
            staging = name == 'application_stage_targets'
            request = (MigrationActivityRequest(admitted, input.selection_digest) if staging
                       else ApplicationStageRequest(admitted, input.selection_digest, member))
            try:
                result = await workflow.execute_activity(name, request,
                    result_type=MigrationActivityResult if staging else ApplicationStageResult,
                    start_to_close_timeout=timedelta(hours=2), retry_policy=RetryPolicy(maximum_attempts=1))
            except ActivityError:
                return held(phase, 'NATIVE_UNCERTAIN')
            returned_member = result.member_id if staging else result.step_id
            if result.job_id != admitted.job_id or returned_member != member:
                return held(phase, 'VALIDATION_FAILED')
            if result.status != 'STAGE_VERIFIED' or not _valid_digest(result.evidence_digest):
                return held(phase, result.reason_code or 'OPERATOR_HOLD', result.evidence_digest, result.hold_code)
            completed += 1
            evidence = result.evidence_digest
        return ApplicationStagingResult(admitted.job_id, admitted.plan_id, admitted.plan_revision,
            admitted.plan_digest, input.selection_digest, 'STAGED', 'VERIFY', None, evidence, completed, total)
