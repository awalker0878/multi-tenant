"""A new approval repairs committed target data without replaying an old write."""
from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError

with workflow.unsafe.imports_passed_through():
    from .admitted_job import AdmittedInput, VERIFY_ADMITTED_JOB_ACTIVITY
    from .approval_gate import ApprovalCheck, _valid_digest, _valid_id
    from provisioner.migration.activities import MigrationActivityRequest, MigrationActivityResult


@dataclass(frozen=True)
class ApplicationRecoveryInput:
    admitted: AdmittedInput
    selection_digest: str
    lifecycle_selection_digest: str
    recovery_selection_digest: str
    original_job_id: str
    machine_ids: tuple[str, ...]

    def __post_init__(self):
        if (not isinstance(self.admitted, AdmittedInput)
                or not all(_valid_digest(value) for value in (self.selection_digest,
                    self.lifecycle_selection_digest, self.recovery_selection_digest))
                or not _valid_id(self.original_job_id) or self.original_job_id == self.admitted.job_id
                or not isinstance(self.machine_ids, (tuple, list)) or not 1 <= len(self.machine_ids) <= 100
                or len(set(self.machine_ids)) != len(self.machine_ids)
                or any(not _valid_id(value) for value in self.machine_ids)):
            raise ValueError('A new exact original-application recovery approval is required')
        object.__setattr__(self, 'machine_ids', tuple(self.machine_ids))


@dataclass(frozen=True)
class ApplicationRecoveryResult:
    job_id: str
    plan_id: str
    plan_revision: int
    plan_digest: str
    selection_digest: str
    lifecycle_selection_digest: str
    recovery_selection_digest: str
    original_job_id: str
    status: str
    phase: str
    completed: int
    total: int
    evidence_digest: str | None
    reason_code: str | None
    hold_code: str | None = None

    def __post_init__(self):
        if (not all(_valid_id(value) for value in (self.job_id, self.plan_id, self.original_job_id))
                or self.job_id == self.original_job_id or type(self.plan_revision) is not int or self.plan_revision < 1
                or not all(_valid_digest(value) for value in (self.plan_digest, self.selection_digest,
                    self.lifecycle_selection_digest, self.recovery_selection_digest))
                or self.status not in {'HELD', 'SUCCEEDED'} or self.phase not in {
                    'RECONCILE', 'TRANSFER', 'CUTOVER', 'VERIFY'}
                or type(self.completed) is not int or type(self.total) is not int
                or not 0 <= self.completed <= self.total <= 402
                or self.reason_code not in {None, 'AUTHORITY_REVOKED', 'NATIVE_UNCERTAIN',
                    'RECOVERY_REQUIRED', 'VALIDATION_FAILED', 'OPERATOR_HOLD', 'WORKFLOW_FAILED'}
                or (self.evidence_digest is not None and not _valid_digest(self.evidence_digest))
                or (self.hold_code is not None and not _valid_id(self.hold_code))
                or (self.status == 'HELD' and self.reason_code is None)
                or (self.status == 'SUCCEEDED' and (self.phase != 'VERIFY' or self.completed != self.total
                    or self.reason_code is not None or self.hold_code is not None or self.evidence_digest is None))):
            raise ValueError('Exact original-application recovery result required')


@workflow.defn(name='SelectedApplicationPostwriteRecovery')
class SelectedApplicationPostwriteRecovery:
    @workflow.run
    async def run(self, input: ApplicationRecoveryInput) -> ApplicationRecoveryResult:
        admitted = input.admitted
        total, completed, evidence = 2 + 4 * len(input.machine_ids), 0, None

        def result(status, phase, reason=None, code=None):
            return ApplicationRecoveryResult(admitted.job_id, admitted.plan_id, admitted.plan_revision,
                admitted.plan_digest, input.selection_digest, input.lifecycle_selection_digest,
                input.recovery_selection_digest, input.original_job_id, status, phase, completed, total,
                evidence, reason, code)

        try:
            check = await workflow.execute_activity(VERIFY_ADMITTED_JOB_ACTIVITY, admitted,
                result_type=ApprovalCheck, start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=1))
            if (check.authorized is not True or
                    (check.job_id, check.organization_id, check.tenant_id, check.plan_id,
                     check.plan_revision, check.plan_digest, check.revocation_epoch) !=
                    (admitted.job_id, admitted.organization_id, admitted.tenant_id, admitted.plan_id,
                     admitted.plan_revision, admitted.plan_digest, admitted.revocation_epoch)
                    or not _valid_id(check.approval_id) or not _valid_digest(check.evidence_digest)):
                return result('HELD', 'RECONCILE', 'AUTHORITY_REVOKED')
            completed += 1
        except ActivityError:
            return result('HELD', 'RECONCILE', 'AUTHORITY_REVOKED')

        async def stage(name, member, phase):
            nonlocal completed, evidence
            try:
                checked = await workflow.execute_activity(name,
                    MigrationActivityRequest(admitted, input.selection_digest, member),
                    result_type=MigrationActivityResult, start_to_close_timeout=timedelta(hours=24),
                    retry_policy=RetryPolicy(maximum_attempts=1))
            except ActivityError:
                return result('HELD', phase, 'NATIVE_UNCERTAIN')
            if checked.job_id != admitted.job_id or checked.member_id != member:
                return result('HELD', phase, 'VALIDATION_FAILED')
            if checked.evidence_digest is not None:
                evidence = checked.evidence_digest
            if checked.status != 'STAGE_VERIFIED' or not _valid_digest(checked.evidence_digest):
                return result('HELD', phase, checked.reason_code or 'OPERATOR_HOLD', checked.hold_code)
            completed += 1
            return None

        for member in input.machine_ids:
            for name, phase in (
                    ('application_recovery_reattach', 'RECONCILE'),
                    ('application_recovery_start', 'RECONCILE'),
                    ('application_recovery_restore', 'TRANSFER'),
                    ('application_recovery_activate', 'CUTOVER')):
                held = await stage(name, member, phase)
                if held is not None:
                    return held
        held = await stage('application_recovery_verify', '', 'VERIFY')
        return held if held is not None else result('SUCCEEDED', 'VERIFY')
