"""Version-pinned application graph for an explicitly selected execution artifact.

This is a distinct workflow type. Existing gate-only histories remain unchanged.
All effects run once; a lost activity result requires original-operation
inspection, never an automatic native replay. Histories contain references only.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError

with workflow.unsafe.imports_passed_through():
    from .admitted_job import AdmittedInput, VERIFY_ADMITTED_JOB_ACTIVITY
    from .approval_gate import ApprovalCheck, _valid_digest, _valid_id
    from provisioner.controlplane.jobs.progress import APPLICATION_HOLD_CODES
    from provisioner.migration.activities import MigrationActivityRequest, MigrationActivityResult


@dataclass(frozen=True)
class ApplicationJobInput:
    admitted: AdmittedInput
    selection_digest: str
    provisioning_steps: tuple[str, ...]
    dataset_ids: tuple[str, ...]
    machine_ids: tuple[str, ...]
    lifecycle_selection_digest: str | None = None


    def __post_init__(self):
        if (not isinstance(self.admitted, AdmittedInput) or not _valid_digest(self.selection_digest)
                or not self.provisioning_steps or not self.machine_ids
                or (self.lifecycle_selection_digest is not None
                    and not _valid_digest(self.lifecycle_selection_digest))
                or any(not isinstance(values, (tuple, list)) or len(values) > 100
                       or len(set(values)) != len(values)
                       or any(not _valid_id(value) for value in values)
                       for values in (self.provisioning_steps, self.dataset_ids, self.machine_ids))):
            raise ValueError('Bounded immutable approved application references required')


@dataclass(frozen=True)
class ApplicationStageRequest:
    admitted: AdmittedInput
    selection_digest: str
    step_id: str = ''

    def __post_init__(self):
        if (not isinstance(self.admitted, AdmittedInput) or not _valid_digest(self.selection_digest)
                or (self.step_id and not _valid_id(self.step_id))):
            raise ValueError('Exact application stage reference required')


@dataclass(frozen=True)
class ApplicationStageResult:
    status: str
    job_id: str
    step_id: str
    reason_code: str | None = None
    evidence_digest: str | None = None
    hold_code: str | None = None

    def __post_init__(self):
        if (self.status not in {'STAGE_VERIFIED', 'HELD'} or not _valid_id(self.job_id)
                or (self.step_id and not _valid_id(self.step_id))
                or self.reason_code not in {None, 'AUTHORITY_REVOKED', 'NATIVE_UNCERTAIN',
                    'CAPACITY_UNAVAILABLE', 'VALIDATION_FAILED', 'OPERATOR_HOLD',
                    'RECOVERY_REQUIRED', 'POLICY_DENIED', 'TIMEOUT', 'WORKFLOW_FAILED'}
                or (self.evidence_digest is not None and not _valid_digest(self.evidence_digest))
                or (self.hold_code is not None and self.hold_code not in APPLICATION_HOLD_CODES)
                or (self.status == 'STAGE_VERIFIED' and self.hold_code is not None)
                or (self.status == 'STAGE_VERIFIED' and self.evidence_digest is None)
                or (self.status == 'STAGE_VERIFIED' and self.reason_code is not None)
                or (self.status == 'HELD' and self.reason_code is None)):
            raise ValueError('Only bounded verified-stage metadata may enter history')


@dataclass(frozen=True)
class ApplicationJobResult:
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
    lifecycle_selection_digest: str | None = None
    staging_selection_digest: str | None = None
    database_selection_digest: str | None = None

    def __post_init__(self):
        if (not _valid_id(self.job_id) or not _valid_id(self.plan_id)
                or type(self.plan_revision) is not int or self.plan_revision < 1
                or not _valid_digest(self.plan_digest) or not _valid_digest(self.selection_digest)
                or self.status not in {'HELD', 'SUCCEEDED'}
                or self.phase not in {'APPROVAL', 'PREPARE', 'PROVISION', 'TRANSFER',
                                     'CUTOVER', 'VERIFY'}
                or self.reason_code not in {None, 'AUTHORITY_REVOKED', 'NATIVE_UNCERTAIN',
                    'CAPACITY_UNAVAILABLE', 'VALIDATION_FAILED', 'OPERATOR_HOLD',
                    'RECOVERY_REQUIRED', 'POLICY_DENIED', 'TIMEOUT', 'WORKFLOW_FAILED'}
                or (self.evidence_digest is not None and not _valid_digest(self.evidence_digest))
                or (self.hold_code is not None and self.hold_code not in APPLICATION_HOLD_CODES)
                or (self.lifecycle_selection_digest is not None
                    and not _valid_digest(self.lifecycle_selection_digest))
                or any(value is not None and not _valid_digest(value)
                       for value in (self.staging_selection_digest, self.database_selection_digest))
                or type(self.completed) is not int or type(self.total) is not int
                or not 0 <= self.completed <= self.total <= 1000
                or (self.status == 'HELD' and self.reason_code is None)
                or (self.status == 'SUCCEEDED' and (self.phase != 'VERIFY'
                    or self.reason_code is not None or self.hold_code is not None
                    or self.evidence_digest is None or self.lifecycle_selection_digest is None
                    or self.completed != self.total or self.total == 0))):
            raise ValueError('Application projection requires exact stage and acceptance evidence')


@workflow.defn(name='OpenStackApplicationMigration')
class OpenStackApplicationMigration:
    @workflow.run
    async def run(self, input: ApplicationJobInput) -> ApplicationJobResult:
        admitted = input.admitted
        total = 6 + len(input.provisioning_steps) + len(input.dataset_ids) + len(input.machine_ids)
        if input.lifecycle_selection_digest is not None:
            total += 1
        completed, evidence = 0, None

        def held(phase, reason='OPERATOR_HOLD', proof=None, hold_code=None):
            return ApplicationJobResult(admitted.job_id, admitted.plan_id, admitted.plan_revision,
                admitted.plan_digest, input.selection_digest, 'HELD', phase, reason,
                proof or evidence, completed, total, hold_code, input.lifecycle_selection_digest)

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
                return held('APPROVAL', 'AUTHORITY_REVOKED')
            completed += 1
        except ActivityError:
            return held('APPROVAL', 'AUTHORITY_REVOKED')

        async def stage(name, member='', *, migration=False, phase='PROVISION'):
            nonlocal completed, evidence
            request = (MigrationActivityRequest(admitted, input.selection_digest, member)
                       if migration else ApplicationStageRequest(admitted, input.selection_digest, member))
            try:
                result = await workflow.execute_activity(name, request,
                    result_type=MigrationActivityResult if migration else ApplicationStageResult,
                    start_to_close_timeout=timedelta(hours=24) if migration else timedelta(hours=2),
                    retry_policy=RetryPolicy(maximum_attempts=1))
            except ActivityError:
                return held(phase, 'NATIVE_UNCERTAIN')
            returned_member = result.member_id if migration else result.step_id
            if result.job_id != admitted.job_id or returned_member != member:
                return held(phase, 'VALIDATION_FAILED')
            if result.status != 'STAGE_VERIFIED' or not _valid_digest(result.evidence_digest):
                return held(phase, result.reason_code or 'OPERATOR_HOLD', result.evidence_digest,
                            result.hold_code)
            completed += 1
            evidence = result.evidence_digest
            return None

        result = await stage('application_reserve_resources', phase='PREPARE')
        if result: return result
        for step in input.provisioning_steps:
            result = await stage('application_provision_step', step)
            if result: return result
        # Bounded children make independently journalled datasets resumable.
        # A child's uncertain result never causes a sibling to be reissued.
        for start in range(0, len(input.dataset_ids), 4):
            import asyncio
            results = await asyncio.gather(*(stage('application_transfer_dataset', member,
                migration=True, phase='TRANSFER') for member in input.dataset_ids[start:start + 4]))
            for result in results:
                if result: return replace(result, completed=completed)
        result = await stage('application_join_datasets', migration=True, phase='TRANSFER')
        if result: return result
        result = await stage('application_rehearsal', migration=True, phase='VERIFY')
        if result: return result
        for machine in input.machine_ids:
            result = await stage('application_source_fence', machine, migration=True, phase='CUTOVER')
            if result: return result
        result = await stage('application_final_sync', migration=True, phase='CUTOVER')
        if result: return result
        result = await stage('application_cutover', migration=True, phase='CUTOVER')
        if result: return result
        # Histories selected before the lifecycle owner retain their original
        # final hold. New selections close only after the independent whole
        # application proof joins original fencing, useful data and traffic.
        if input.lifecycle_selection_digest is None:
            return held('VERIFY', 'OPERATOR_HOLD', hold_code='FINAL_APPLICATION_ACCEPTANCE_UNAVAILABLE')
        result = await stage('application_verify_cutover', migration=True, phase='VERIFY')
        if result: return result
        return ApplicationJobResult(admitted.job_id, admitted.plan_id, admitted.plan_revision,
            admitted.plan_digest, input.selection_digest, 'SUCCEEDED', 'VERIFY', None,
            evidence, completed, total, None, input.lifecycle_selection_digest)
