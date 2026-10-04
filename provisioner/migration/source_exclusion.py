"""Retain source disks while removing their persistent VM writer attachment.

Only the selected VMware application data disks can be detached. A new current
source owner must first recheck the actual B11 old-owner reviews and independent
native/credential/late-task exclusion. Device removal is journaled before its
native call, with optimistic changeVersion and exact task/VM readback. The
result still needs the original independent outcome owner before cutover.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import timedelta
import time

from provisioner.controlplane.jobs.repository import _tenant
from provisioner.controlplane.persistence.store import OwnerLease
from provisioner.controlplane.reconciliation import OwnerRecoveryEvidence
from provisioner.execution import readback_core as c, vsphere_observe as vm, vsphere_power, vsphere_task_observe as task
from provisioner.execution.run_files import require
from .cutover import SourceWorkerRuntime
from .lifecycle import LifecycleCommandGuard
from provisioner.controlplane.worker.command_runtime import ApplicationWorkerCommandAuthority


@dataclass(frozen=True)
class SourceDiskFenceRuntime:
    source: SourceWorkerRuntime
    previous_lease: OwnerLease
    previous_exclusion: OwnerRecoveryEvidence
    credentials: object

    @property
    def registry(self):
        return self.source.registry

    def __post_init__(self):
        from .vsphere_credentials import VsphereNativeCredentialOwner
        require(isinstance(self.source, SourceWorkerRuntime)
                and isinstance(self.previous_lease, OwnerLease)
                and isinstance(self.previous_exclusion, OwnerRecoveryEvidence)
                and type(self.credentials) is VsphereNativeCredentialOwner
                and self.credentials.commands.identity == self.source.identity
                and self.credentials.commands.context == self.source.context
                and self.credentials.commands.grant.grant_id == self.source.grant_id
                and self.previous_lease.binding == self.source.lease.binding
                and self.previous_lease.epoch < self.source.lease.epoch
                and self.previous_lease.worker_id != self.source.lease.worker_id
                and (self.previous_lease.organization_id, self.previous_lease.tenant_id,
                     self.previous_lease.security_domain_id, self.previous_lease.workload_id) ==
                (self.source.lease.organization_id, self.source.lease.tenant_id,
                 self.source.lease.security_domain_id, self.source.lease.workload_id),
                'A new enrolled source owner and exact independently excluded prior writer are required')

    def require_previous_exclusion(self, guard):
        require(isinstance(guard, LifecycleCommandGuard) and guard.phase in
                {'SOURCE_FENCE', 'SOURCE_REATTACH', 'SOURCE_START'}
                and guard.runtime.registry is self.source.registry
                and guard.runtime.lease == self.source.lease
                and guard.runtime.identity == self.source.identity,
                'The native source fence differs from the exact application intent owner')
        return require_previous_writer(guard, self.previous_lease, self.previous_exclusion,
                                       guard.member['native_fence']['previous_owner'])


def require_previous_writer(guard, lease, evidence, selected):
    """Actual retained B11 owner exclusion, reverified for every native exchange."""
    require(isinstance(guard, LifecycleCommandGuard) and isinstance(lease, OwnerLease)
            and isinstance(evidence, OwnerRecoveryEvidence) and lease.binding == guard.binding
            and lease.epoch < guard.runtime.lease.epoch
            and lease.worker_id != guard.runtime.lease.worker_id
            and (lease.organization_id, lease.tenant_id, lease.security_domain_id, lease.workload_id) ==
                (guard.runtime.lease.organization_id, guard.runtime.lease.tenant_id,
                 guard.runtime.lease.security_domain_id, guard.runtime.lease.workload_id),
            'The exact original native writer and a separately enrolled newer owner are required')
    guard.require_current()
    return require_excluded_native_owner(guard.runtime.registry, guard.runtime.context,
        guard.runtime.lease, guard.scope, lease, evidence, selected)


def require_excluded_native_owner(registry, context, current_lease, scope, lease, evidence, selected):
    """One actual B11 exclusion owner shared by fixed native command owners."""
    from provisioner.controlplane.persistence import TenantContext
    from provisioner.controlplane.authority.model import PlanScope
    from provisioner.controlplane.reconciliation import NativeOperationRegistry
    require(isinstance(registry, NativeOperationRegistry) and isinstance(context, TenantContext)
            and isinstance(scope, PlanScope) and isinstance(current_lease, OwnerLease)
            and isinstance(lease, OwnerLease) and isinstance(evidence, OwnerRecoveryEvidence)
            and lease.binding == current_lease.binding and lease.epoch < current_lease.epoch
            and lease.worker_id != current_lease.worker_id
            and (lease.organization_id,lease.tenant_id,lease.security_domain_id,lease.workload_id) ==
                (current_lease.organization_id,current_lease.tenant_id,current_lease.security_domain_id,
                 current_lease.workload_id)
            and (scope.organization_id,scope.tenant_id,scope.security_domain_id) ==
                (context.organization_id,context.tenant_id,current_lease.security_domain_id)
            and (scope.platform_family,scope.endpoint_id,scope.native_scope_id) ==
                (lease.binding.platform_family,lease.binding.endpoint_id,lease.binding.native_scope_id),
            'Exact current native owner and separately excluded original writer required')
    require((lease.worker_id, lease.epoch, evidence.incident_id) ==
            (selected['worker_id'], selected['owner_epoch'], selected['incident_id']),
            'The excluded original source writer differs from the approved lifecycle')
    with registry._connect() as connection, connection.cursor() as cursor:
        _tenant(cursor, context)
        now = registry._clock(cursor)
        require(now - timedelta(minutes=5) <= evidence.observed_at <= now,
                'The original source native/credential exclusion has expired')
        cursor.execute('SELECT reviewer_subject,native_evidence_digest,worker_fence_digest,observed_at,incident_id '
            'FROM hosting_controlplane.native_owner_recovery_reviews WHERE organization_id=%s AND tenant_id=%s '
            'AND platform_family=%s AND endpoint_id=%s AND native_scope_id=%s AND resource_kind=%s '
            'AND native_id=%s AND owner_epoch=%s FOR SHARE',
            (context.organization_id, context.tenant_id, *lease.binding.key(), lease.epoch))
        reviews = cursor.fetchall()
        require(len(reviews) == 2 and len({review[0] for review in reviews}) == 2
                and all(review[0] != lease.worker_id and review[1:] ==
                        (evidence.native_evidence_digest, evidence.worker_fence_digest,
                         evidence.observed_at, evidence.incident_id) for review in reviews),
                'The old source writer has no two matching independently retained exclusion reviews')
        cursor.execute('SELECT 1 FROM hosting_controlplane.native_operation_intents '
            'WHERE organization_id=%s AND tenant_id=%s AND platform_family=%s AND endpoint_id=%s '
            'AND native_scope_id=%s AND resource_kind=%s AND native_id=%s AND owner_epoch<=%s '
            "AND state!='RESOLVED' LIMIT 1",
            (context.organization_id, context.tenant_id, *lease.binding.key(), lease.epoch))
        require(cursor.fetchone() is None, 'An earlier source request remains unresolved')
        registry._owner(cursor, context, current_lease)
        registry._containment(cursor, lease.binding)
        registry._evidence.verify_owner_exclusion(cursor, lease, scope, evidence)
    return dict(old_worker_id=lease.worker_id, old_owner_epoch=lease.epoch,
                native_evidence_digest=evidence.native_evidence_digest,
                worker_fence_digest=evidence.worker_fence_digest,
                observed_at=evidence.observed_at.isoformat())


class _ApplicationVsphereClient(vsphere_power.Client):
    def __init__(self, request, runtime, guard, authority, exclusions=None, database_final_proof=None):
        from .lifecycle_evidence import CurrentWriterExclusions
        require(isinstance(runtime, SourceDiskFenceRuntime) and isinstance(guard, LifecycleCommandGuard)
                and isinstance(authority, ApplicationWorkerCommandAuthority) and authority.intent_guard is guard
                and (guard.phase == 'SOURCE_FENCE' or isinstance(exclusions, CurrentWriterExclusions)),
                'The concrete enrolled native source fence is required')
        self.fence_runtime, self.guard, self.authority, self.exclusions = runtime, guard, authority, exclusions
        if database_final_proof is not None:
            from .postgresql_activities import DatabaseFinalProofOwner
            require(type(database_final_proof) is DatabaseFinalProofOwner
                and guard.phase == 'SOURCE_FENCE'
                and database_final_proof.activities.authority is guard.runtime.execution_authority,
                'Only the actual current SQL final owner may retain the running database source')
        self.database_final_proof = database_final_proof
        super().__init__(request, runtime.source.session, runtime.source.ca_file)

    def _request(self, *args, **kwargs):
        self.fence_runtime.require_previous_exclusion(self.guard)
        self.authority.require_current()
        if self.exclusions is not None:
            self.exclusions.require_current()
        if self.database_final_proof is not None:
            self.database_final_proof.require_final(self.guard.admitted,
                c.strict_loads(self.guard.selection_bytes), self.guard.lifecycle, self.guard.member_id)
        session = self.fence_runtime.credentials.acquire_session(self.authority,
            native_id=self.resource['moid'], origin=self.origin, ca_file=self.fence_runtime.source.ca_file)
        self._auth_headers = {'vmware-api-session-id': session.token}
        from provisioner.execution.run_files import utcnow
        timeout = min(self.authority.timeout(30), (session.expires_at - utcnow()).total_seconds())
        require(timeout > 0, 'The native source credential expired before its exchange')
        self.timeout = min(self.timeout, timeout)
        self.deadline = min(self.deadline, time.monotonic() + timeout)
        result = super()._request(*args, **kwargs)
        self.guard.require_current()
        self.authority.require_current()
        return result

    def detach(self, current, selected_disks):
        require(current['runtime']['powerState'] == ('poweredOn' if self.database_final_proof is not None else 'poweredOff'),
            'Source disk removal requires shutdown or its actual independently fenced separate running SQL engine')
        payload = {'spec': {'changeVersion': current['config']['changeVersion'],
            'deviceChange': [{'operation': 'remove', 'device': deepcopy(disk)} for disk in selected_disks]}}
        # No fileOperation is sent: the VMDK and its committed data are retained.
        result, _ = self._request('POST', vm.resource_target(self.resource, 'ReconfigVM_Task'), payload)
        vm.reference(result, 'Task', 'task')
        return result['value']

    def attach(self, current, disks):
        require(self.guard.phase == 'SOURCE_REATTACH' and self.guard.operation_kind == 'DISK_ATTACH'
                and current['runtime']['powerState'] == 'poweredOff',
                'Retained disk reattachment requires its own exact capability and a stopped VM')
        require(not any(device['key'] in {disk['key'] for disk in disks}
                        for device in current['config']['hardware']['device']),
                'A retained data disk is already attached')
        payload = {'spec': {'changeVersion': current['config']['changeVersion'],
            'deviceChange': [{'operation': 'add', 'device': deepcopy(disk)} for disk in disks]}}
        result, _ = self._request('POST', vm.resource_target(self.resource, 'ReconfigVM_Task'), payload)
        vm.reference(result, 'Task', 'task')
        return result['value']


def selected_disks(request, keys):
    resource = vsphere_power.validate(request)
    devices = resource['expected']['config']['hardware']['device']
    found = [disk for disk in devices if disk['key'] in keys]
    require(len(found) == len(keys) and all(disk['_typeName'] == 'VirtualDisk'
            and disk['backing'].get('sharing', 'sharingNone') == 'sharingNone'
            and disk['backing']['diskMode'] == 'persistent'
            and not disk['backing'].get('parent') for disk in found),
            'Only exclusive persistent application data disks may be fenced')
    # At least one boot disk stays attached. Removing the source OS would hide
    # service/fstab state and make approved prewrite return impossible.
    require(any(disk['_typeName'] == 'VirtualDisk' and disk['key'] not in keys for disk in devices),
            'The original source boot disk must remain retained and attached')
    return found


def observe_removed(request, disks, task_id, started_at, client):
    witness = client.task_info(task_id)
    record = dict(moid=task_id, vm_moid=vsphere_power.validate(request)['moid'],
        description_id='VirtualMachine.reconfigure', queued_at=witness.get('queueTime'),
        event_chain_id=witness.get('eventChainId'))
    require(c.timestamp(started_at) <= c.timestamp(record['queued_at'])
            and task.evaluate_task(record, witness)['task_completion_observed'],
            'The exact original disk-removal task has no completed native outcome')
    resource = vsphere_power.validate(request)
    snapshots = [vm.snapshot(resource, client) for _ in range(2)]
    if client.database_final_proof is None:
        expected = vsphere_power.normalize_after(request, snapshots[-1][0])
    else:
        # The running PostgreSQL engine and every retained device must remain
        # unchanged. Only the selected file disk and optimistic revision move.
        client.database_final_proof.require_final(client.guard.admitted,
            c.strict_loads(client.guard.selection_bytes), client.guard.lifecycle, client.guard.member_id)
        expected = deepcopy(resource['expected'])
        expected['config']['changeVersion'] = snapshots[-1][0]['config']['changeVersion']
    expected['config']['hardware']['device'] = [disk for disk in expected['config']['hardware']['device']
                                               if disk['key'] not in {item['key'] for item in disks}]
    require(snapshots[0][0] == snapshots[1][0]
            and not any('/runtime/question:execution_blocked' in mismatch for _, mismatch in snapshots)
            and not c.differences(snapshots[-1][0], expected),
            'The source restarted, retained hardware changed, or a data disk remains attached')
    pending = [row for row in client.activity(started_at) if row.get('state') in {'queued', 'running'}]
    require(not pending and client.task_info(task_id) == witness,
            'A late source native task is pending or the disk-removal task changed')
    return dict(native_task_id=task_id, task_witness=witness,
                vm_snapshot=snapshots[-1][0], removed_device_keys=[disk['key'] for disk in disks],
                retained_backing_digests=[c.digest(disk['backing']) for disk in disks],
                state='SOURCE_DATA_DISKS_DETACHED_PERSISTENTLY',
                running_separate_database=client.database_final_proof is not None, observed_at=c.now())


def observe_added(request, disks, task_id, started_at, client):
    witness = client.task_info(task_id)
    record = dict(moid=task_id, vm_moid=vsphere_power.validate(request)['moid'],
        description_id='VirtualMachine.reconfigure', queued_at=witness.get('queueTime'),
        event_chain_id=witness.get('eventChainId'))
    require(c.timestamp(started_at) <= c.timestamp(record['queued_at'])
            and task.evaluate_task(record, witness)['task_completion_observed'],
            'The exact original retained disk-attachment task has no completed native outcome')
    resource = vsphere_power.validate(request)
    snapshots = [vm.snapshot(resource, client) for _ in range(2)]
    expected = vsphere_power.normalize_after(request, snapshots[-1][0])
    require(snapshots[0][0] == snapshots[1][0]
            and not any('/runtime/question:execution_blocked' in mismatch for _, mismatch in snapshots)
            and not c.differences(snapshots[-1][0], expected),
            'The retained data disks, stopped source VM or original complete hardware changed')
    pending = [row for row in client.activity(started_at) if row.get('state') in {'queued', 'running'}]
    require(not pending and client.task_info(task_id) == witness,
            'A late native source request remains pending during retained-disk attachment')
    return dict(native_task_id=task_id, task_witness=witness, vm_snapshot=snapshots[-1][0],
        attached_device_keys=[disk['key'] for disk in disks], retained_backing_digests=[c.digest(disk['backing']) for disk in disks],
        state='RETAINED_SOURCE_DATA_DISKS_REATTACHED_STOPPED', observed_at=c.now())
