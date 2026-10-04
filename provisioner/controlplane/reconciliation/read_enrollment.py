"""Concrete independently enrolled B10 read contact, including revoked-job recovery.

An observer uses its own current admitted read/recovery job and an existing
commissioned native binding. It never borrows a creation writer's identity or
fabricates a pre-creation VM lease. All native clients are fixed product owners.
"""
from __future__ import annotations

from dataclasses import dataclass

from provisioner.controlplane.jobs.repository import _digest
from provisioner.controlplane.worker.command_runtime import WorkerCommandRuntime
from provisioner.controlplane.worker.grants import CredentialBroker
from provisioner.controlplane.worker.vault_consumer import VaultCredentialConsumer
from provisioner.controlplane.workflow.admitted_job import AdmittedInput
from provisioner.execution.run_files import require, utcnow


@dataclass(frozen=True)
class NativeReadEnrollment:
    command: WorkerCommandRuntime
    admitted: AdmittedInput
    selection_digest: str
    broker: CredentialBroker
    consumer: VaultCredentialConsumer

    def __post_init__(self):
        require(isinstance(self.command, WorkerCommandRuntime)
                and isinstance(self.admitted, AdmittedInput)
                and isinstance(self.broker, CredentialBroker)
                and isinstance(self.consumer, VaultCredentialConsumer)
                and self.broker._identities is self.command.verifier
                and self.broker._grants is self.command.grants
                and self.broker._issuer is self.consumer.issuer
                and self.command.grant.operation_kind == 'DISCOVER_READ',
                'Actual independent read enrollment and native credential owners required')
        self.require_current()

    @property
    def scope(self):
        return self.command.grant.operation_scope

    @property
    def subject(self):
        return self.command.identity.subject

    def require_current(self, *, cursor=None):
        runtime, original = self.command, self.command.grant
        require(runtime.verifier.verify(runtime.transport_evidence) == runtime.identity,
                'The independent reader mTLS identity changed')
        arguments = runtime.grant_arguments(self.admitted)
        if cursor is None:
            def checked(_reference, grant, deadline):
                require(grant == original, 'Independent read grant changed')
                return grant, deadline
            grant, deadline = runtime.grants.with_authorized_reference(runtime.context,
                runtime.identity, original.grant_id, **arguments, use=checked)
        else:
            arguments.pop('lease_epoch')
            grant = runtime.grants.verify_intent(cursor, runtime.context,
                grant_id=original.grant_id, worker_identity=runtime.identity,
                lease_epoch=original.lease_epoch, **arguments)
            deadline = min(grant.expires_at, runtime.identity.expires_at)
            require(grant == original, 'Independent read grant changed')
        options={'cursor':cursor} if cursor is not None else {}
        plan, artifact = runtime.authority.require_observation(self.admitted,
            self.selection_digest, 'DISCOVER_READ',**options)
        require(_digest(artifact) == self.selection_digest and
                (grant.organization_id, grant.tenant_id, grant.plan_id, grant.plan_revision,
                 grant.plan_digest, grant.revocation_epoch) ==
                (self.admitted.organization_id,self.admitted.tenant_id,self.admitted.plan_id,
                 self.admitted.plan_revision,self.admitted.plan_digest,self.admitted.revocation_epoch)
                and deadline > utcnow(), 'Independent observer no longer has current native read authority')
        return grant, deadline

    def acquire(self,*,cursor=None):
        grant, deadline = self.require_current(cursor=cursor)
        binding=self.command.grant_arguments(self.admitted)
        if cursor is None:
            handle=self.broker.acquire(self.command.transport_evidence,self.command.context,
                                       grant.grant_id,**binding)
        else:
            handle=self.broker.acquire_observation(cursor,self.command.transport_evidence,
                        self.command.context,grant.grant_id,**binding)
        material = self.consumer.unwrap(handle, grant)
        self.require_current(cursor=cursor)
        require(material.expires_at <= deadline, 'Read credential exceeds its independently current grant')
        return material
