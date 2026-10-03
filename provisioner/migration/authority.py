"""Locked admitted selection checks for the actual native command owners."""
from dataclasses import dataclass

from provisioner.controlplane.authority import PlanScope, WorkerGrant
from provisioner.controlplane.worker.grants import VerifiedWorkerIdentity
from provisioner.controlplane.workflow.admitted_job import AdmittedInput
from provisioner.controlplane.workflow.approval_gate import _valid_digest
from provisioner.controlplane.workflow.execution_selection import PostgresExecutionAuthority
from provisioner.execution.run_files import require


@dataclass(frozen=True)
class ApplicationCommandAuthority:
    """Server-only continuation of one exact admitted, currently claimed intent.

    The worker owner checks its real grant immediately before this call. The
    root owner then locks the actual PostgreSQL job, original selection, current
    qualifications, operating controls, native intent, lease and worker epoch.
    It excludes only that original intent from uncertainty admission checks.
    """
    authority: PostgresExecutionAuthority
    admitted: AdmittedInput
    selection_digest: str
    identity: VerifiedWorkerIdentity
    operation_kind: str

    def __post_init__(self):
        require(isinstance(self.authority, PostgresExecutionAuthority)
                and isinstance(self.admitted, AdmittedInput) and _valid_digest(self.selection_digest)
                and isinstance(self.identity, VerifiedWorkerIdentity)
                and self.operation_kind in {'RESTORE_DATA', 'SOURCE_FENCE'}
                and (self.identity.organization_id, self.identity.tenant_id) ==
                    (self.admitted.organization_id, self.admitted.tenant_id),
                'The actual admitted continuation authority and enrolled identity are required')

    def _bound(self, grant):
        require(isinstance(grant, WorkerGrant) and grant.operation_kind == self.operation_kind
                and (grant.organization_id, grant.tenant_id, grant.plan_id, grant.plan_revision,
                     grant.plan_digest, grant.revocation_epoch, grant.worker_subject) ==
                    (self.admitted.organization_id, self.admitted.tenant_id, self.admitted.plan_id,
                     self.admitted.plan_revision, self.admitted.plan_digest,
                     self.admitted.revocation_epoch, self.identity.subject),
                'The native command differs from the admitted original worker operation')

    @staticmethod
    def _scopes(grant, plan):
        require((grant.source, grant.destination) ==
                (PlanScope.from_record(plan['spec']['source']),
                 PlanScope.from_record(plan['spec']['destination'])),
                'The exact current approved command scopes changed')

    def require_admission(self, grant):
        """Preclaim checking never exempts an existing unresolved native intent."""
        self._bound(grant)
        plan, _selection = self.authority.require_current(self.admitted, self.selection_digest,
                                                        self.operation_kind)
        self._scopes(grant, plan)

    def require_current(self, grant):
        self._bound(grant)
        plan, _selection = self.authority.require_current(self.admitted, self.selection_digest,
            self.operation_kind, continuation_grant=grant, continuation_identity=self.identity)
        self._scopes(grant, plan)
