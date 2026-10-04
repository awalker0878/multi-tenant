"""Current real mTLS/B10/B11 authority for fixed cold lower-owner actions."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.jobs.repository import _digest
from provisioner.controlplane.persistence.store import OwnerLease
from provisioner.controlplane.reconciliation import NativeOperationRegistry, OwnerRecoveryEvidence
from provisioner.controlplane.worker.command_runtime import WorkerCommandRuntime
from provisioner.controlplane.worker.grants import CredentialBroker
from provisioner.controlplane.worker.vault_consumer import VaultCredentialConsumer
from provisioner.controlplane.workflow.admitted_job import AdmittedInput
from provisioner.execution.run_files import require, utcnow
from provisioner.execution.source_integrity import verify, verify_runtime
from .cold_selection import ColdVmSelection
from provisioner.allocations.transactions import ResourceTransactions


class _ColdAuthority:
    def _bind(self, command, admitted, artifact, cold, root):
        require(isinstance(command,WorkerCommandRuntime) and isinstance(admitted,AdmittedInput)
                and type(artifact) is dict and isinstance(cold,ColdVmSelection) and isinstance(root,Path),
                'Actual installed current worker and immutable cold selection required')
        self.command,self.admitted,self.cold,self.root = command,admitted,cold,root
        self.artifact = deepcopy(artifact); self.artifact_digest = _digest(artifact)
        self.cold_digest = cold.sha256; self.claimed = False; self.native_send_started = False

    def _current(self):
        command, grant = self.command,self.command.grant
        require(self.cold.sha256 == self.cold_digest and _digest(self.artifact) == self.artifact_digest
                and (grant.step_id,grant.operation_id,grant.lease_key) ==
                    (self.row['step_id'],self.row['operation_id'],self.row['lease_key'])
                and (grant.organization_id,grant.tenant_id,grant.plan_id,grant.plan_revision,
                     grant.plan_digest,grant.revocation_epoch) ==
                    (self.admitted.organization_id,self.admitted.tenant_id,self.admitted.plan_id,
                     self.admitted.plan_revision,self.admitted.plan_digest,self.admitted.revocation_epoch)
                and grant.operation_scope == self.scope and grant.operation_kind == self.operation_kind
                and grant.worker_subject == self.lease.worker_id and grant.lease_epoch == self.lease.epoch,
                'The original cold action, scope, plan, worker or owner epoch changed')
        source = verify(self.root)
        require(source['status'] == 'HASHES_MATCH' and source['commit'] == self.artifact['sourceCommit']
                and verify_runtime(self.root)['status'] == 'RUNTIME_SOURCES_MATCH',
                'The actual cold command runtime differs from approved installed source')
        require(command.verifier.verify(command.transport_evidence) == command.identity,
                'The actual mTLS identity changed before the next native exchange')
        def checked(_reference, actual, deadline):
            require(actual == grant, 'The cold action no longer has its original current B10 grant')
            return actual,deadline
        actual,deadline = command.grants.with_authorized_reference(command.context,command.identity,
            grant.grant_id,**command.grant_arguments(self.admitted),use=checked)
        options = dict(continuation_grant=actual,continuation_identity=command.identity) if self.claimed else {}
        plan,artifact = command.authority.require_current(self.admitted,self.artifact_digest,
            self.operation_kind,**options)
        require(artifact == self.artifact, 'The current protected cold execution artifact changed')
        self.cold.require_plan(plan,artifact)
        deadline = min(deadline,command.identity.expires_at,grant.expires_at,self.lease.expires_at)
        require(deadline > utcnow(), 'No current exact cold action interval remains')
        return actual,deadline

    def timeout(self, requested=10):
        require(type(requested) in {int,float} and 0 < requested <= 60,
                'A bounded native cold command interval required')
        _grant,deadline = self.require_current()
        return min(requested,(deadline-utcnow()).total_seconds())

    def acquire(self, broker, consumer):
        require(self.claimed and isinstance(broker,CredentialBroker) and isinstance(consumer,VaultCredentialConsumer)
                and broker._identities is self.command.verifier and broker._grants is self.command.grants
                and broker._issuer is consumer.issuer and consumer.issuer._lease_store is not None,
                'Original claimed action and actual revocable Vault credential custody required')
        grant,deadline = self.require_current()
        handle = broker.acquire(self.command.transport_evidence,self.command.context,
            grant.grant_id,**self.command.grant_arguments(self.admitted))
        material = consumer.unwrap(handle,grant)
        self.require_current()
        require(material.expires_at <= deadline, 'Native credential exceeds current original cold authority')
        return material

    def begin_native_send(self):
        self.require_current()
        require(self.claimed and not self.native_send_started,
                'Original cold native effect was already handed off; never resend an unknown attempt')
        # The durable original B11 claim precedes this process handoff. A new
        # process cannot reacquire that claim, and a new contact object cannot
        # resend it while this admitted command remains in memory.
        self.native_send_started = True


class ColdExportAuthority(_ColdAuthority):
    """One selected existing native snapshot; no implicit create/retry/export VM."""
    operation_kind = 'SNAPSHOT_EXPORT'

    def __init__(self,command,admitted,artifact,cold,root,*,registry,lease,
                 previous_lease,previous_exclusion,resources,resource_bundles):
        from provisioner.controlplane.workflow.provisioning_activity import FileResourceBundleStore
        self._bind(command,admitted,artifact,cold,root)
        require(isinstance(registry,NativeOperationRegistry) and isinstance(lease,OwnerLease)
                and isinstance(previous_lease,OwnerLease) and isinstance(previous_exclusion,OwnerRecoveryEvidence)
                and isinstance(resources,ResourceTransactions) and isinstance(resource_bundles,FileResourceBundleStore),
                'Actual original native registry and independently excluded prior owner required')
        self.registry,self.lease = registry,lease
        self.native_lease_id = None
        self.previous_lease,self.previous_exclusion = previous_lease,previous_exclusion
        self.resources,self.resource_bundles = resources,resource_bundles
        value = cold.to_dict(); self.scope = PlanScope.from_record(value['source_scope'])
        self.row = value['export']; self.binding = cold.binding()
        require(lease.binding == self.binding and lease.workload_id == value['workload_id']
                and (lease.organization_id,lease.tenant_id,lease.security_domain_id) ==
                    (self.scope.organization_id,self.scope.tenant_id,self.scope.security_domain_id)
                and command.identity.subject == lease.worker_id,
                'The cold export has another native VM, workload or tenant owner')
        self.require_current()

    def require_current(self):
        result = self._current()
        from .source_exclusion import require_excluded_native_owner
        require_excluded_native_owner(self.registry,self.command.context,self.lease,self.scope,
            self.previous_lease,self.previous_exclusion,self.cold.to_dict()['vm']['previous_owner'])
        bundle = self.resource_bundles(self.admitted,self.artifact)
        value = self.cold.to_dict()
        require(bundle.digest == value['resource_bundle_sha256'], 'The cold capture changed its counted resource bundle')
        selected = [pool for pool in bundle.pools if pool.scope == self.scope
                    and pool.catalog['pool_id'] == value['source_pool_id']]
        retained_bytes = sum(disk['capacityInBytes'] for disk in
            value['vm']['snapshot_config']['hardware']['device'] if disk['_typeName'] == 'VirtualDisk')
        require(len(selected) == 1 and 'cold-snapshot-export' in selected[0].capabilities
                and selected[0].staging.storage_gb*10**9 >= value['capture_resources']['limits']['expected_bytes']
                and selected[0].retained_source.storage_gb*10**9 >= retained_bytes
                and selected[0].snapshots.storage_gb*10**9 >= retained_bytes,
                'Original source, selected snapshot and additive protected capture staging must remain counted')
        self.resources._require_accounted(bundle)
        require(result[1] > utcnow(), 'Cold source exclusion/resource checks exhausted the current interval')
        return result

    def claim(self):
        require(not self.claimed, 'A native snapshot export can be claimed only once')
        grant,_deadline = self.require_current()
        from provisioner.execution import readback_core as c
        request = c.digest({'format':'hosting-cold-native-export-request/1',
                            'cold_selection':self.cold_digest,'native_binding':self.binding.key(),
                            'snapshot_moid':self.cold.to_dict()['vm']['snapshot_moid']})
        operation = self.registry.prepare(self.command.context,self.lease,self.scope,
            job_id=self.admitted.job_id,grant_id=grant.grant_id,step_id=grant.step_id,
            lease_key=grant.lease_key,worker_identity=self.command.identity,
            operation_id=grant.operation_id,operation_kind=self.operation_kind,request_digest=request)
        require(self.registry.claim_once(self.command.context,self.lease,self.scope,
            grant.operation_id,self.command.identity), 'Original export already started; observe it before any new action')
        self.claimed = True; self.require_current()
        return operation

    def accepted(self, native_lease_id):
        self.registry.task_accepted(self.command.context,self.row['operation_id'],
                                    self.command.identity.subject,native_lease_id)
        require(self.native_lease_id in {None,native_lease_id},
                'The original native export lease identity cannot be replaced')
        self.native_lease_id = native_lease_id

    def uncertain(self):
        if self.claimed:
            self.registry.mark_uncertain(self.command.context,self.row['operation_id'],self.command.identity.subject)


class ColdImageAuthority(_ColdAuthority):
    operation_kind = 'SNAPSHOT_IMPORT'

    def __init__(self,command,admitted,artifact,cold,root,*,registry,lease,disk_id,phase):
        from provisioner.controlplane.reconciliation.planned_image import PlannedImageRegistry, PlannedImageLease
        self._bind(command,admitted,artifact,cold,root)
        require(isinstance(registry,PlannedImageRegistry) and isinstance(lease,PlannedImageLease)
                and phase in {'CREATE','UPLOAD'} and lease.phase == phase and lease.disk_id == disk_id,
                'Exact original planned image action and existing B11 image registry required')
        self.registry,self.image_lease = registry,lease
        self.lease = lease.owner; self.phase,self.disk_id = phase,disk_id
        self.scope = self.lease.scope; self.row = cold.disk(disk_id)['phases'][phase]
        require(self.scope == PlanScope.from_record(cold.to_dict()['destination_scope'])
                and self.lease.resource_id == cold.disk(disk_id)['logical_image_id']
                and self.lease.job_id == admitted.job_id,
                'The planned image differs from the selected native destination and disk')
        self.require_current()

    def require_current(self):
        return self._current()

    def claim(self):
        require(not self.claimed, 'Each original image create/upload can be claimed only once')
        grant,_deadline = self.require_current()
        operation = self.registry.prepare(self.command.context,self.image_lease,grant=grant,
                                           identity=self.command.identity)
        require(self.registry.claim_once(self.command.context,self.image_lease,grant.operation_id,
            self.command.identity), 'Original image action already started; independently reconcile it')
        self.claimed = True; self.require_current()
        return operation

    def uncertain(self):
        if self.claimed:
            self.registry.mark_uncertain(self.command.context,self.row['operation_id'],self.command.identity.subject)
