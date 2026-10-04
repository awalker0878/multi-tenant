"""Independent Windows service readback and separately admitted fixed repair.

Service state is a current postcondition, not proof of old WinRM shell or
credential exclusion. This owner records that distinction explicitly. Only a
new current mutation with an actually resolved predecessor may remediate an
existing selected service; an uncertain predecessor never becomes a retry.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from provisioner.controlplane.jobs.repository import _digest, _tenant
from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.persistence.store import NativeBinding
from provisioner.controlplane.reconciliation.read_enrollment import NativeReadEnrollment
from provisioner.controlplane.reconciliation.registry import NativeOperationRegistry, RecoveryHeld
from provisioner.execution import delivery_steps
from provisioner.execution.run_files import digest, encoded, private_path, read_private, require, utcnow, write_new
from provisioner.execution.windows_guest import WindowsGuestSelection
from .command_runtime import SelectedWorkerCommandAuthority
from .windows_commands import _WinRM

def original_operation(registry, admitted, selection, operation_id, original, *, authority=None, retained=None):
    """Read the actual original B11 row; queue metadata does not hydrate it."""
    require(isinstance(registry, NativeOperationRegistry) and type(original) is WindowsGuestSelection,
            'Actual native registry and original Windows descriptor required')
    from provisioner.controlplane.persistence import TenantContext
    original_admitted,original_selection=admitted,selection
    reference=None
    if retained is not None:
        from provisioner.controlplane.workflow.execution_selection import PostgresExecutionAuthority
        from provisioner.controlplane.workflow.windows_service_selection import (
            DRIVER, WindowsOriginalServiceIntent, validate_artifact)
        require(type(retained) is WindowsOriginalServiceIntent and isinstance(authority,PostgresExecutionAuthority),
                'Actual current root and exact retained Windows intent references required')
        reference=retained.to_dict(); original_admitted=retained.admitted
        require((original_admitted.organization_id,original_admitted.tenant_id)==
                (admitted.organization_id,admitted.tenant_id) and original_admitted.job_id!=admitted.job_id
                and operation_id==reference['operationId']
                and original.sha256==reference['windowsSelectionDigest']
                and original.to_dict()['native_binding']==reference['nativeBinding'],
                'Separately admitted Windows follow-up changed its original intent, input or tenant')
        _plan,original_selection=authority.require_observation(original_admitted,reference['artifactDigest'],'DISCOVER_READ')
        validate_artifact(original_selection)
        require(original_selection['driver']==selection['driver']==DRIVER
                and original_selection['workloadId']==selection['workloadId']
                and original_selection['destination']==selection['destination'],
                'Retained Windows service intent cannot authorize another workload, native scope or purpose')
    context = TenantContext(admitted.organization_id, admitted.tenant_id)
    with registry._connect() as connection, connection.cursor() as cursor:
        _tenant(cursor, context)
        operation = registry._get(cursor, context, operation_id)
    binding = original_selection['stageBindings'].get(operation.step_id)
    require(operation.operation_id == operation_id and operation.job_id == original_admitted.job_id
            and operation.operation_kind == 'GUEST_CONFIG' and operation.native_task_id is None
            and operation.binding == NativeBinding.from_record(original.to_dict()['native_binding'])
            and (operation.workload_id, operation.security_domain_id) ==
                (selection['workloadId'], selection['destination']['securityDomainId'])
            and binding is not None and binding['kind'] in {'windows_guest_apply', 'windows_guest_remediate'}
            and binding['inputDigests'].get('windows_selection') == original.sha256,
            'The actual original intent does not bind this selected Windows guest or descriptor')
    if reference is not None:
        require((operation.operation_id,operation.step_id,operation.request_digest,operation.lease_key,
                 operation.worker_id,operation.owner_epoch)==
                tuple(reference[name] for name in ('operationId','stepId','requestDigest','leaseKey','workerSubject','ownerEpoch')),
                'The retained Windows native intent custody differs from its actual original registry row')
    return operation


def require_remediation(runtime, admitted, selection, step, packet):
    """Recheck the predecessor before every new repair command or request."""
    require(step['kind'] == 'windows_guest_remediate'
            and set(packet['parameters']) == {'original_operation_id'},
            'A separately selected fixed Windows remediation purpose is required')
    paths = delivery_steps.file_paths(packet)
    original = WindowsGuestSelection(read_private(paths['original_windows_selection']))
    current = WindowsGuestSelection(read_private(paths['windows_selection']))
    original.require_same_services(current)
    operation = original_operation(runtime.registry, admitted, selection,
        packet['parameters']['original_operation_id'], original,
        authority=runtime.command_runtime.authority,retained=runtime.original_intent)
    require(operation.operation_id != runtime.command_runtime.grant.operation_id
            and operation.binding == runtime.lease.binding,
            'Windows remediation must have its own new native intent on the exact original VM')
    if operation.state != 'RESOLVED' or operation.outcome != 'EFFECT_PRESENT':
        raise RecoveryHeld('Original Windows uncertainty requires independent fenced recovery before remediation')
    return operation


class WindowsServiceReadAuthority(SelectedWorkerCommandAuthority):
    """An independently enrolled read stage; no native mutation continuation."""
    def __init__(self, owner, admitted, selection, delivery, step, packet, root):
        require(type(owner) is ScopedWindowsServiceReadRuntime
                and owner.enrollment.admitted == admitted
                and owner.enrollment.selection_digest == _digest(selection)
                and step['kind'] == 'windows_guest_observe'
                and set(packet['parameters']) == {'original_operation_id'},
                'The exact independent Windows service observation stage is required')
        self.owner = owner
        super().__init__(owner.command_runtime, admitted, selection, delivery, step, packet, root)
        self.original_reference = self._original()

    def _original(self):
        paths = delivery_steps.file_paths(self.packet)
        original = WindowsGuestSelection(read_private(paths['original_windows_selection']))
        current = WindowsGuestSelection(read_private(paths['windows_selection']))
        original.require_same_services(current)
        return original_operation(self.owner.registry, self.admitted, self.selection,
                                  self.packet['parameters']['original_operation_id'], original,
                                  authority=self.runtime.authority,retained=self.owner.original_intent)

    def require_current(self):
        self._documents()
        runtime = self.runtime
        require(self.owner.enrollment.command is runtime,
                'The independent Windows read worker enrollment changed')
        grant, deadline = self.owner.enrollment.require_current()
        plan, selected = runtime.authority.require_observation(self.admitted,
            self.selection_digest, 'DISCOVER_READ')
        paths = delivery_steps.file_paths(self.packet)
        original = WindowsGuestSelection(read_private(paths['original_windows_selection']))
        current = WindowsGuestSelection(read_private(paths['windows_selection']))
        original.require_same_services(current)
        operation = self._original()
        from provisioner.controlplane.workflow.windows_service_selection import DRIVER,WindowsServiceSelection
        if selected.get('driver')==DRIVER:
            purpose=WindowsServiceSelection.from_record(selected['windowsServices'])
            purpose.require_guest(current,reader=True)
            require(purpose.to_dict()['read']=={'stepId':self.step['id'],'kind':self.step['kind'],
                'operationId':grant.operation_id}, 'Windows read differs from its exact selected independent operation')
        body = current.to_dict()
        mappings = [row for row in plan['spec']['machineMappings'] if row['targetMachineId'] == body['machine_id']]
        require(grant == runtime.grant and selected == self.selection
                and (grant.source, grant.destination) ==
                (PlanScope.from_record(plan['spec']['source']), PlanScope.from_record(plan['spec']['destination']))
                and grant.operation_kind == 'DISCOVER_READ' and grant.step_id == self.step['id']
                and grant.operation_scope == grant.destination
                and grant.operation_id != operation.operation_id and grant.worker_subject != operation.worker_id
                and self.selection['guestProfile'] == plan['spec']['route']['guestProfile'] == 'windows-server-2022'
                and len(mappings) == 1 and mappings[0]['machineId'] in plan['spec']['selectedMachineIds']
                and (operation.binding.platform_family, operation.binding.endpoint_id, operation.binding.native_scope_id) ==
                (grant.operation_scope.platform_family, grant.operation_scope.endpoint_id, grant.operation_scope.native_scope_id)
                and current.to_dict()['mapped_user'].lower() != original.to_dict()['mapped_user'].lower()
                and current.to_dict()['certificate_upn'].lower() != original.to_dict()['certificate_upn'].lower()
                and digest(read_private(paths['winrm_ca'])) == body['ca_sha256'],
                'Current Windows read grant, independent identity, original native guest or trust changed')
        if hasattr(self, 'original_reference'):
            reference = self.original_reference
            require(tuple(getattr(operation, name) for name in ('operation_id', 'job_id', 'grant_id', 'step_id',
                'lease_key', 'binding', 'workload_id', 'security_domain_id', 'worker_id', 'owner_epoch',
                'operation_kind', 'request_digest')) == tuple(getattr(reference, name) for name in
                ('operation_id', 'job_id', 'grant_id', 'step_id', 'lease_key', 'binding', 'workload_id',
                 'security_domain_id', 'worker_id', 'owner_epoch', 'operation_kind', 'request_digest')),
                'The original Windows intent custody changed during independent readback')
        require(deadline > utcnow(), 'The next independent Windows read has no current original permission')
        return grant, deadline


@dataclass(frozen=True)
class ScopedWindowsServiceReadRuntime:
    enrollment: NativeReadEnrollment
    registry: NativeOperationRegistry
    original_intent: object | None = None

    def __post_init__(self):
        from provisioner.controlplane.workflow.windows_service_selection import WindowsOriginalServiceIntent
        require(self.original_intent is None or type(self.original_intent) is WindowsOriginalServiceIntent,
                'Windows read may retain exact original references, never hydrated native authority')
        require(type(self.enrollment) is NativeReadEnrollment
                and isinstance(self.registry, NativeOperationRegistry)
                and self.registry._grants is self.enrollment.command.grants
                and self.enrollment.command.grant.operation_kind == 'DISCOVER_READ',
                'Actual independently enrolled Windows read authority and original native registry required')
        matching = [role for role in self.consumer.issuer._roles.values()
            if role.scope == self.command_runtime.grant.operation_scope and role.operation_kind == 'DISCOVER_READ']
        require(len(matching) == 1, 'One actual scoped native Windows read certificate role required')

    @property
    def command_runtime(self): return self.enrollment.command

    @property
    def broker(self): return self.enrollment.broker

    @property
    def consumer(self): return self.enrollment.consumer

    def run_step(self, admitted, selection, plan, step, packet, directory, base, root):
        delivery_steps.validate_packet(step, packet, plan, base, root=root)
        authority = WindowsServiceReadAuthority(self, admitted, selection, plan, step, packet, root)
        paths = delivery_steps.file_paths(packet)
        output = private_path(directory, directory=True)
        descriptor = WindowsGuestSelection(read_private(paths['windows_selection']))
        result = self.observe_selected(authority, descriptor, paths['winrm_ca'], output)
        write_new(output/'result.json', encoded(result))
        return delivery_steps.complete(step, packet, output, plan, result, ['result.json'])

    def observe_selected(self, authority, descriptor, ca, output):
        require(type(authority) is WindowsServiceReadAuthority and authority.owner is self
                and authority.runtime is self.command_runtime and type(descriptor) is WindowsGuestSelection,
                'One actual independently selected Windows service read authority required')
        paths = delivery_steps.file_paths(authority.packet)
        require(descriptor.canonical == read_private(paths['windows_selection'])
                and Path(ca) == paths['winrm_ca'], 'Original independent Windows inputs changed')
        output = private_path(output, directory=True)
        channel = _WinRM(self, authority, descriptor, paths['winrm_ca'], output)
        observations = [channel.action('IDENTITY')]
        for service in descriptor.to_dict()['services']:
            current = channel.action('OBSERVE_SERVICE', service)
            row = current['observation']['service']
            require(row['state'] == service['state'] and row['startup'] ==
                    {'Automatic':'Auto', 'Manual':'Manual', 'Disabled':'Disabled'}[service['startup']],
                    'Independent Windows readback differs from the selected service postconditions')
            observations.append(current)
        authority.require_current()
        original = authority._original()
        result = dict(format='hosting-independent-windows-services/1',
            status='SERVICE_POSTCONDITIONS_VERIFIED_REQUIRES_NATIVE_EXCLUSION',
            native_acceptance=False, production_activation=False, native_quiesced=False,
            job_id=authority.admitted.job_id, read_operation_id=self.command_runtime.grant.operation_id,
            original_operation_id=original.operation_id, original_request_digest=original.request_digest,
            original_selection_sha256=WindowsGuestSelection(read_private(paths['original_windows_selection'])).sha256,
            original_native_state=original.state, original_native_outcome=original.outcome,
            original_worker_subject=original.worker_id, original_owner_epoch=original.owner_epoch,
            reader_subject=self.command_runtime.identity.subject,
            reader_certificate_digest=self.command_runtime.identity.certificate_sha256,
            native_binding=descriptor.to_dict()['native_binding'], selection_sha256=descriptor.sha256,
            source_commit=authority.selection['sourceCommit'], scope=authority.selection['executionScope'],
            observations=observations, exchanges=channel.receipts)
        return result
