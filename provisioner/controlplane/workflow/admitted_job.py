"""First real B09 workflow: recheck admitted authority and stop safely.

The admitted job already has all four approvals. It must not wait for a second
signal that can be lost between B07's commit and an RPC. This workflow checks
the live ledger in an Activity and returns a gate result. A later provisioning
or migration graph needs fresh per-effect authority, ownership and native
reconciliation; this workflow cannot start one implicitly.
"""
from __future__ import annotations

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError

from .approval_gate import (ApprovalCheck, GateInput, GateResult,
                            _valid_digest, _valid_id)

VERIFY_ADMITTED_JOB_ACTIVITY = 'verify_admitted_migration_job'


@workflow.defn(name='AdmittedMigrationJob')
class AdmittedMigrationJob:
    @workflow.run
    async def run(self, input: GateInput) -> GateResult:
        try:
            check = await workflow.execute_activity(
                VERIFY_ADMITTED_JOB_ACTIVITY, input, result_type=ApprovalCheck,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=1))
        except ActivityError:
            return GateResult('HELD', input.job_id, input.plan_id,
                              input.plan_revision, input.plan_digest)
        if (check.authorized is not True or (check.job_id, check.organization_id,
                check.tenant_id, check.plan_id, check.plan_revision,
                check.plan_digest, check.revocation_epoch) !=
                (input.job_id, input.organization_id, input.tenant_id,
                 input.plan_id, input.plan_revision, input.plan_digest,
                 input.revocation_epoch)):
            return GateResult('HELD', input.job_id, input.plan_id,
                              input.plan_revision, input.plan_digest)
        # The verifier's typed result still needs a nonempty approval ID and a
        # content digest before the check can be reported as passed.
        if not _valid_id(check.approval_id) or not _valid_digest(check.evidence_digest):
            return GateResult('HELD', input.job_id, input.plan_id,
                              input.plan_revision, input.plan_digest)
        return GateResult('GATE_PASSED', input.job_id, input.plan_id,
                          input.plan_revision, input.plan_digest,
                          check.approval_id, check.evidence_digest)
