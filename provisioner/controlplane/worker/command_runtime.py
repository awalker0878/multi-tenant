"""Process-local current authority for one originally selected native command.

Nothing in this module reconstructs a worker, grant or issuer from queue JSON.
The enrollment owner supplies the real mTLS socket and the existing B10 and
execution-authority owners. Every use returns a freshly checked grant/window.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
import ssl

from provisioner.controlplane.authority.model import PlanScope, WorkerGrant
from provisioner.controlplane.jobs.repository import _digest
from provisioner.controlplane.persistence import TenantContext
from provisioner.controlplane.workflow.admitted_job import AdmittedInput
from provisioner.controlplane.workflow.execution_selection import (
    PostgresExecutionAuthority, _AUTHORITY_FILES)
from provisioner.execution.run_files import digest, read_private, require, utcnow
from provisioner.execution.source_integrity import verify, verify_runtime
from .grants import PostgresWorkerGrants, VerifiedWorkerIdentity
from .pki import MutualTlsWorkerVerifier


@dataclass(frozen=True)
class WorkerCommandRuntime:
    authority: PostgresExecutionAuthority
    grants: PostgresWorkerGrants
    verifier: MutualTlsWorkerVerifier
    transport_evidence: ssl.SSLSocket
    context: TenantContext
    identity: VerifiedWorkerIdentity
    grant: WorkerGrant

    def __post_init__(self):
        require(isinstance(self.authority, PostgresExecutionAuthority)
                and isinstance(self.grants, PostgresWorkerGrants)
                and isinstance(self.verifier, MutualTlsWorkerVerifier)
                and type(self.transport_evidence) is ssl.SSLSocket
                and isinstance(self.context, TenantContext)
                and isinstance(self.identity, VerifiedWorkerIdentity)
                and isinstance(self.grant, WorkerGrant),
                'Concrete enrolled command authority and actual mTLS transport required')
        require((self.context.organization_id, self.context.tenant_id, self.identity.subject) ==
                (self.grant.organization_id, self.grant.tenant_id, self.grant.worker_subject)
                and (self.identity.organization_id, self.identity.tenant_id, self.identity.site_id) ==
                (self.context.organization_id, self.context.tenant_id, self.grant.operation_scope.site_id),
                'Command enrollment differs from the exact worker tenant and native site')
        require(self.verifier.verify(self.transport_evidence) == self.identity,
                'The current real mTLS peer differs from the enrolled command worker')

    def grant_arguments(self, admitted):
        grant = self.grant
        return dict(job_id=admitted.job_id, step_id=grant.step_id,
                    operation_id=grant.operation_id, operation_kind=grant.operation_kind,
                    operation_scope=grant.operation_scope, lease_key=grant.lease_key,
                    lease_epoch=grant.lease_epoch)

    def select(self, admitted, selection, delivery, step, packet, root, *, intent_guard=None):
        return SelectedWorkerCommandAuthority(self, admitted, selection, delivery,
                                              step, packet, root, intent_guard=intent_guard)

    def select_application(self, admitted, selection, lifecycle, phase, member, root, *, intent_guard):
        return ApplicationWorkerCommandAuthority(self, admitted, selection, lifecycle,
                                                  phase, member, root, intent_guard=intent_guard)

    def select_application_reader(self, admitted, selection, lifecycle, member, root, *,
                                  enrollment, writer, writer_native_user, side='destination', recovery=None):
        return ApplicationGuestReadAuthority(self, admitted, selection, lifecycle, member,
            root, enrollment=enrollment, writer=writer, writer_native_user=writer_native_user, side=side,
            recovery=recovery)


class SelectedWorkerCommandAuthority:
    """An immutable process binding; caller dictionaries cannot switch its job.

    A typed original intent guard owns continuation after B11 claim. Without
    that guard this checks ordinary admission and exempts no unknown intent.
    """
    def __init__(self, runtime, admitted, selection, delivery, step, packet, root,
                 *, intent_guard=None):
        require(isinstance(runtime, WorkerCommandRuntime) and isinstance(admitted, AdmittedInput)
                and all(type(value) is dict for value in (selection, delivery, step, packet))
                and isinstance(root, Path), 'Exact admitted command documents and source root required')
        if intent_guard is not None:
            from provisioner.migration.provisioning import ObservedProvisioningGuard
            from provisioner.controlplane.reconciliation.service_runtime import PlannedServiceGuard
            from .windows_commands import WindowsGuestIntent
            require(isinstance(intent_guard, (ObservedProvisioningGuard, PlannedServiceGuard, WindowsGuestIntent))
                    and intent_guard.admitted == admitted
                    and intent_guard.selection_digest == _digest(selection)
                    and intent_guard.step == step
                    and intent_guard.operation_kind == runtime.grant.operation_kind,
                    'Only the exact original native intent may continue its command')
        self.runtime, self.admitted, self.root = runtime, admitted, root
        self.selection, self.delivery, self.step, self.packet = map(deepcopy,
            (selection, delivery, step, packet))
        self.selection_digest = _digest(self.selection)
        self.intent_guard = intent_guard
        self.document_digests = tuple(_digest(value) for value in
                                     (self.selection, self.delivery, self.step, self.packet))
        self.require_current()

    def _documents(self):
        require(tuple(_digest(value) for value in
                (self.selection, self.delivery, self.step, self.packet)) == self.document_digests,
                'Original command selection, purpose or packet changed')
        selection, delivery, step, packet = self.selection, self.delivery, self.step, self.packet
        require(_digest(delivery) == selection['deliveryPlanDigest']
                and delivery['source_commit'] == selection['sourceCommit']
                and delivery['scope'] == selection['executionScope']
                and step in delivery['steps'] and packet['step_id'] == step['id']
                and packet['plan_sha256'] == _digest(delivery),
                'The command changed its original selected delivery or source')
        binding = selection['stageBindings'].get(step['id'])
        require(binding is not None and binding['kind'] == step['kind']
                and binding['parametersDigest'] == _digest(packet['parameters'])
                and {name: asset['sha256'] for name, asset in packet['files'].items()
                     if name not in _AUTHORITY_FILES} == binding['inputDigests'],
                'Exact selected command parameters, inputs and purpose required')
        for asset in packet['files'].values():
            require(digest(read_private(asset['path'])) == asset['sha256'],
                    'An originally bound command input or current authority file changed')
        source = verify(self.root)
        require(source['status'] == 'HASHES_MATCH' and source['commit'] == selection['sourceCommit']
                and verify_runtime(self.root)['status'] == 'RUNTIME_SOURCES_MATCH',
                'The actual command runtime differs from its original selected source')

    def require_current(self):
        self._documents()
        runtime, original = self.runtime, self.runtime.grant
        require(runtime.verifier.verify(runtime.transport_evidence) == runtime.identity,
                'The current mTLS peer or independently enrolled certificate changed')
        def checked(_reference, current, deadline):
            require(current == original, 'The current B10 grant differs from the original command')
            return current, deadline
        grant, deadline = runtime.grants.with_authorized_reference(runtime.context, runtime.identity,
            original.grant_id, **runtime.grant_arguments(self.admitted), use=checked)
        require((grant.plan_id, grant.plan_revision, grant.plan_digest, grant.revocation_epoch,
                 grant.organization_id, grant.tenant_id, grant.step_id) ==
                (self.admitted.plan_id, self.admitted.plan_revision, self.admitted.plan_digest,
                 self.admitted.revocation_epoch, self.admitted.organization_id,
                 self.admitted.tenant_id, self.step['id']),
                'Grant differs from the immutable admitted job and selected stage')
        options = {}
        if self.intent_guard is not None:
            actual, guarded_deadline = self.intent_guard.require_current()
            require(actual == grant, 'The native continuation belongs to another original grant')
            deadline = min(deadline, guarded_deadline)
            if self.intent_guard.claimed:
                options = dict(continuation_grant=grant, continuation_identity=runtime.identity)
        plan, selection = runtime.authority.require_current(self.admitted,
            self.selection_digest, grant.operation_kind, **options)
        require(selection == self.selection and (grant.source, grant.destination) ==
                (PlanScope.from_record(plan['spec']['source']),
                 PlanScope.from_record(plan['spec']['destination']))
                and grant.operation_scope in (grant.source, grant.destination),
                'The original selected command or canonical native scope changed')
        deadline = min(deadline, runtime.identity.expires_at, grant.expires_at)
        require(deadline > utcnow(), 'The next command has no current original authority')
        return grant, deadline

    def timeout(self, requested):
        require(type(requested) in {int, float} and 0 < requested <= 3600,
                'Bounded command interval required')
        _grant, deadline = self.require_current()
        return min(requested, (deadline - utcnow()).total_seconds())


class ApplicationWorkerCommandAuthority(SelectedWorkerCommandAuthority):
    """The exact lifecycle descriptor supplies purpose; no invented packet.

    The application owner prepares/claims its original intent before any write.
    This owner adds live mTLS and database grant checks to every dispatched
    command and delegates only that typed original intent's continuation.
    """
    def __init__(self, runtime, admitted, selection, lifecycle, phase, member, root, *, intent_guard):
        from provisioner.migration.lifecycle import ApplicationLifecycleSelection, LifecycleCommandGuard, PHASES
        require(isinstance(runtime, WorkerCommandRuntime) and isinstance(admitted, AdmittedInput)
                and type(selection) is dict and isinstance(lifecycle, ApplicationLifecycleSelection)
                and isinstance(intent_guard, LifecycleCommandGuard) and phase in PHASES
                and PHASES[phase][1] != 'DISCOVER_READ'
                and type(member) is str and isinstance(root, Path)
                and intent_guard.admitted == admitted and intent_guard.lifecycle == lifecycle
                and (intent_guard.phase, intent_guard.member_id) == (phase, member)
                and intent_guard.runtime.execution_authority is runtime.authority
                and intent_guard.runtime.context == runtime.context
                and intent_guard.runtime.identity == runtime.identity
                and intent_guard.runtime.grant_id == runtime.grant.grant_id,
                'Concrete exact original application phase and actual worker enrollment required')
        self.runtime, self.admitted, self.root = runtime, admitted, root
        self.selection, self.lifecycle = deepcopy(selection), lifecycle
        self.selection_digest = _digest(self.selection)
        self.phase, self.member_id = phase, member
        self.member = lifecycle.member(member)
        self.guest = self.member['source' if intent_guard.row['scope_side'] == 'source' else 'target']
        self.descriptor_digest = lifecycle.sha256
        self.step, self.intent_guard = deepcopy(intent_guard.step), intent_guard
        self.require_current()

    def _documents(self):
        guard = self.intent_guard
        require(_digest(self.selection) == self.selection_digest
                and self.selection.get('applicationLifecycleSelectionDigest') == self.descriptor_digest
                and self.lifecycle.sha256 == self.descriptor_digest
                and self.lifecycle.member(self.member_id) == self.member
                and (guard.phase, guard.member_id, guard.descriptor_sha256, guard.selection_digest) ==
                (self.phase, self.member_id, self.descriptor_digest, self.selection_digest)
                and guard.step == self.step and guard.member == self.member
                and self.guest == self.member['source' if guard.row['scope_side'] == 'source' else 'target']
                and guard.row == self.member['phases'][self.phase]
                and self.runtime.grant.operation_scope == guard.scope
                and (self.runtime.grant.step_id, self.runtime.grant.operation_id, self.runtime.grant.operation_kind) ==
                (guard.row['step_id'], guard.row['operation_id'], guard.row['operation_kind']),
                'The original application descriptor, purpose, resource or current grant changed')
        source = verify(self.root)
        require(source['status'] == 'HASHES_MATCH' and source['commit'] == self.selection['sourceCommit']
                and verify_runtime(self.root)['status'] == 'RUNTIME_SOURCES_MATCH',
                'The application command runtime differs from its original selected source')


class ApplicationGuestReadAuthority(SelectedWorkerCommandAuthority):
    """An independent exact current application read; it claims no native write.

    The immutable lifecycle supplies a separately named read operation. The
    original writer remains a custody reference, including after uncertainty;
    only the independently enrolled reader's current permission authorizes a
    contact. This type never requests original write continuation.
    """
    def __init__(self, runtime, admitted, selection, lifecycle, member, root, *,
                 enrollment, writer, writer_native_user, side='destination', recovery=None):
        import re
        from provisioner.controlplane.persistence.store import NativeBinding
        from provisioner.controlplane.reconciliation.read_enrollment import NativeReadEnrollment
        from provisioner.migration.lifecycle import ApplicationLifecycleSelection, LifecycleWorkerRuntime
        require(isinstance(runtime, WorkerCommandRuntime) and isinstance(admitted, AdmittedInput)
                and type(selection) is dict and isinstance(lifecycle, ApplicationLifecycleSelection)
                and type(enrollment) is NativeReadEnrollment and enrollment.command is runtime
                and enrollment.admitted == admitted and enrollment.selection_digest == _digest(selection)
                and isinstance(writer, LifecycleWorkerRuntime) and type(member) is str
                and isinstance(root, Path) and side in {'source', 'destination'}
                and runtime.grant.operation_kind == 'DISCOVER_READ'
                and writer.execution_authority is runtime.authority and writer.context == runtime.context
                and writer.identity.subject != runtime.identity.subject
                and writer.identity.certificate_sha256 != runtime.identity.certificate_sha256
                and writer.grant_id != runtime.grant.grant_id
                and type(writer_native_user) is str and writer_native_user != 'root'
                and re.fullmatch('[a-z_][a-z0-9_-]{0,31}', writer_native_user),
                'An independently enrolled original application read worker is required')
        self.runtime, self.admitted, self.root = runtime, admitted, root
        self.selection, self.lifecycle = deepcopy(selection), lifecycle
        self.selection_digest, self.descriptor_digest = _digest(self.selection), lifecycle.sha256
        self.member_id, self.side = member, side
        self.member = lifecycle.member(member)
        self.guest = self.member['source' if side == 'source' else 'target']
        self.phase = 'SOURCE_VERIFY_READ' if side == 'source' else 'VERIFY_READ'
        self.row = deepcopy(self.member['phases'][self.phase])
        self.step = dict(id=self.row['step_id'], kind='application_' + self.phase.lower())
        self.operation_id, self.operation_kind = self.row['operation_id'], 'DISCOVER_READ'
        self.scope = PlanScope.from_record(lifecycle.to_dict()[side + '_scope'])
        self.binding = NativeBinding(self.scope.platform_family, self.scope.endpoint_id,
            self.scope.native_scope_id, 'vm', self.guest['native_id'])
        self.enrollment, self.writer, self.intent_guard = enrollment, writer, None
        self.writer_native_user = writer_native_user
        if recovery is not None:
            from provisioner.migration.recovery import ApplicationRecoverySelection
            require(type(recovery) is ApplicationRecoverySelection and side=='destination'
                    and selection.get('applicationRecoverySelectionDigest')==recovery.sha256
                    and recovery.to_dict()['mode']=='FORWARD_REPAIR'
                    and recovery.to_dict()['currentLifecycleDigest']==lifecycle.sha256,
                    'Only the exact independently approved retained-target repair reader is supported')
        self.recovery,self.recovery_digest=recovery,None if recovery is None else recovery.sha256
        self.writer_reference = (writer.identity, writer.grant_id, writer.lease.binding,
                                 writer.lease.workload_id, writer.scope, writer_native_user)
        self.require_current()

    def _documents(self):
        from provisioner.migration.lifecycle import PHASES
        require(_digest(self.selection) == self.selection_digest
                and self.selection.get('applicationLifecycleSelectionDigest') == self.descriptor_digest
                and self.lifecycle.sha256 == self.descriptor_digest
                and self.lifecycle.member(self.member_id) == self.member
                and self.guest == self.member['source' if self.side == 'source' else 'target']
                and self.row == self.member['phases'][self.phase]
                and PHASES[self.phase] == (self.side, 'DISCOVER_READ')
                and (self.row['scope_side'], self.row['operation_kind']) == (self.side, 'DISCOVER_READ')
                and self.step == dict(id=self.row['step_id'], kind='application_' + self.phase.lower())
                and self.operation_id == self.row['operation_id']
                and self.scope == PlanScope.from_record(self.lifecycle.to_dict()[self.side + '_scope'])
                and (self.binding.platform_family, self.binding.endpoint_id,
                     self.binding.native_scope_id, self.binding.resource_kind, self.binding.native_id) ==
                (self.scope.platform_family, self.scope.endpoint_id, self.scope.native_scope_id,
                 'vm', self.guest['native_id'])
                and self.writer_reference == (self.writer.identity, self.writer.grant_id,
                    self.writer.lease.binding, self.writer.lease.workload_id, self.writer.scope,
                    self.writer_native_user)
                and self.writer.scope == self.scope and self.writer.lease.binding == self.binding
                and self.writer.lease.workload_id == self.selection['workloadId'],
                'The original independent application read purpose or native member changed')
        source = verify(self.root)
        require((self.recovery is None and self.recovery_digest is None) or
                (self.recovery is not None and self.side=='destination'
                 and self.recovery.sha256==self.recovery_digest==self.selection.get('applicationRecoverySelectionDigest')
                 and self.recovery.to_dict()['currentLifecycleDigest']==self.descriptor_digest),
                'The independently approved retained-target repair read purpose changed')
        require(source['status'] == 'HASHES_MATCH' and source['commit'] == self.selection['sourceCommit']
                and verify_runtime(self.root)['status'] == 'RUNTIME_SOURCES_MATCH',
                'The application read runtime differs from its original selected source')
        for name, expected in self.guest['action_runtime']['source_files'].items():
            selected = self.root / name
            require(selected.is_file() and not selected.is_symlink()
                    and digest(selected.read_bytes()) == expected,
                    'The independently selected shipped guest read source changed')

    def require_current(self):
        self._documents()
        runtime = self.runtime
        require(self.enrollment.command is runtime and self.enrollment.admitted == self.admitted
                and self.enrollment.selection_digest == self.selection_digest,
                'The original independent read enrollment changed')
        grant, deadline = self.enrollment.require_current()
        plan, selection = runtime.authority.require_observation(self.admitted,
            self.selection_digest, 'DISCOVER_READ')
        if self.recovery is not None:
            require(plan['spec']['source']==plan['spec']['destination']==self.lifecycle.to_dict()['destination_scope'],
                    'Retained-target repair observation cannot borrow the original source scope')
            self.recovery.require_forward_plan(plan,selection,self.lifecycle)
        else:
            require(plan['spec']['source'] == self.lifecycle.to_dict()['source_scope']
                    and plan['spec']['destination'] == self.lifecycle.to_dict()['destination_scope'],
                    'The current reader differs from the original application native scopes')
        require(grant == runtime.grant and selection == self.selection
                and (grant.step_id, grant.operation_id, grant.operation_kind, grant.operation_scope) ==
                (self.step['id'], self.operation_id, 'DISCOVER_READ', self.scope)
                and (grant.source, grant.destination) ==
                (PlanScope.from_record(plan['spec']['source']), PlanScope.from_record(plan['spec']['destination'])),
                'The current reader differs from its exact original read grant or canonical native scopes')
        deadline = min(deadline, runtime.identity.expires_at, grant.expires_at)
        require(deadline > utcnow(), 'The next application read has no current original permission')
        return grant, deadline
