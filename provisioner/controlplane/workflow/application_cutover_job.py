"""New approval over actual staged targets; never reserve or create them again."""
from dataclasses import dataclass, replace
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError

with workflow.unsafe.imports_passed_through():
    from .admitted_job import AdmittedInput, VERIFY_ADMITTED_JOB_ACTIVITY
    from .approval_gate import ApprovalCheck, _valid_digest, _valid_id
    from .application_job import ApplicationJobResult, ApplicationStageRequest, ApplicationStageResult
    from provisioner.migration.activities import MigrationActivityRequest, MigrationActivityResult


@dataclass(frozen=True)
class ApplicationCutoverInput:
    admitted: AdmittedInput
    selection_digest: str
    provisioning_steps: tuple[str, ...]
    dataset_ids: tuple[str, ...]
    machine_ids: tuple[str, ...]
    lifecycle_selection_digest: str
    staging_selection_digest: str
    database_selection_digest: str | None = None
    database_member_id: str | None = None

    def __post_init__(self):
        if (not isinstance(self.admitted, AdmittedInput)
                or not all(_valid_digest(value) for value in (self.selection_digest,
                    self.lifecycle_selection_digest, self.staging_selection_digest))
                or not self.machine_ids
                or any(not isinstance(values, (tuple, list)) or len(values) > 100
                       or len(set(values)) != len(values) or any(not _valid_id(value) for value in values)
                       for values in (self.provisioning_steps, self.dataset_ids, self.machine_ids))
                or ((self.database_selection_digest is None) != (self.database_member_id is None))
                or (self.database_selection_digest is not None and
                    (not _valid_digest(self.database_selection_digest)
                     or self.database_member_id not in self.machine_ids))):
            raise ValueError('Cutover needs exact observed targets, lifecycle and selected data method')


@workflow.defn(name='OpenStackStagedApplicationCutover')
class OpenStackStagedApplicationCutover:
    @workflow.run
    async def run(self, input: ApplicationCutoverInput) -> ApplicationJobResult:
        admitted = input.admitted
        bootstrap = workflow.patched('isolated-management-bootstrap-v1')
        total = 7 + len(input.provisioning_steps) + len(input.dataset_ids) + 2 * len(input.machine_ids)
        if bootstrap:
            total += len(input.machine_ids)
        if input.database_selection_digest is not None:
            total += 4
        completed, evidence = 0, None

        def held(phase, reason='OPERATOR_HOLD', proof=None, code=None):
            return ApplicationJobResult(admitted.job_id, admitted.plan_id, admitted.plan_revision,
                admitted.plan_digest, input.selection_digest, 'HELD', phase, reason,
                proof or evidence, completed, total, code, input.lifecycle_selection_digest,
                input.staging_selection_digest, input.database_selection_digest)

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

        async def stage(name, member='', *, provisioning=False, phase='CUTOVER'):
            nonlocal completed, evidence
            request = (ApplicationStageRequest(admitted, input.selection_digest, member) if provisioning
                       else MigrationActivityRequest(admitted, input.selection_digest, member))
            try:
                result = await workflow.execute_activity(name, request,
                    result_type=ApplicationStageResult if provisioning else MigrationActivityResult,
                    start_to_close_timeout=timedelta(hours=2 if provisioning else 24),
                    retry_policy=RetryPolicy(maximum_attempts=1))
            except ActivityError:
                return held(phase, 'NATIVE_UNCERTAIN')
            returned_member = result.step_id if provisioning else result.member_id
            if result.job_id != admitted.job_id or returned_member != member:
                return held(phase, 'VALIDATION_FAILED')
            if result.status != 'STAGE_VERIFIED' or not _valid_digest(result.evidence_digest):
                return held(phase, result.reason_code or 'OPERATOR_HOLD', result.evidence_digest, result.hold_code)
            completed += 1
            evidence = result.evidence_digest
            return None

        result = await stage('application_verify_staged_data', phase='PREPARE')
        if result: return result
        for machine in input.machine_ids:
            result = await stage('application_target_prepare', machine, phase='PREPARE')
            if result: return result
        if bootstrap:
            for machine in input.machine_ids:
                result = await stage('application_target_bootstrap', machine, phase='PREPARE')
                if result: return result
        for step in input.provisioning_steps:
            result = await stage('application_provision_step', step, provisioning=True, phase='PROVISION')
            if result: return result
        if input.database_selection_digest is not None:
            for name in ('application_database_initialize', 'application_database_synchronize'):
                result = await stage(name, input.database_member_id, phase='TRANSFER')
                if result: return result
        for start in range(0, len(input.dataset_ids), 4):
            import asyncio
            results = await asyncio.gather(*(stage('application_transfer_dataset', member, phase='TRANSFER')
                                            for member in input.dataset_ids[start:start + 4]))
            for result in results:
                if result: return replace(result, completed=completed)
        result = await stage('application_join_datasets', phase='TRANSFER')
        if result: return result
        result = await stage('application_rehearsal', phase='VERIFY')
        if result: return result
        if input.database_selection_digest is not None:
            for name in ('application_database_source_fence', 'application_database_final'):
                result = await stage(name, input.database_member_id)
                if result: return result
        for machine in input.machine_ids:
            result = await stage('application_source_fence', machine)
            if result: return result
        for name in ('application_final_sync', 'application_cutover', 'application_verify_cutover'):
            result = await stage(name, phase='VERIFY' if name == 'application_verify_cutover' else 'CUTOVER')
            if result: return result
        return ApplicationJobResult(admitted.job_id, admitted.plan_id, admitted.plan_revision,
            admitted.plan_digest, input.selection_digest, 'SUCCEEDED', 'VERIFY', None,
            evidence, completed, total, None, input.lifecycle_selection_digest,
            input.staging_selection_digest, input.database_selection_digest)
