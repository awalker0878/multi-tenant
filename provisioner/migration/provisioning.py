"""Observed resource owners for the selected OpenStack application stages.

Enrolled planning and guest command owners recheck the exact live grant for
each provider subprocess and SSH command. Local nft transactions and observation
commands reuse the existing owners under their exact current operation grants.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import fcntl
import ipaddress
import os
from pathlib import Path
import socket
import struct
import subprocess
from uuid import UUID

from provisioner.controlplane.authority import AuthorityService, PlanScope
from provisioner.controlplane.persistence import TenantContext, canonical_record_digest
from provisioner.controlplane.persistence.store import NativeBinding, OwnerLease
from provisioner.controlplane.reconciliation import NativeOperationRegistry
from provisioner.controlplane.worker.grants import VerifiedWorkerIdentity
from provisioner.controlplane.workflow.admitted_job import AdmittedInput
from provisioner.controlplane.workflow.approval_gate import _valid_id
from provisioner.controlplane.workflow.execution_selection import PostgresExecutionAuthority
from provisioner.execution import delivery_steps, guest_apply, nft_edge, qualify_target
from provisioner.execution.run_files import (
    current_window, digest, encoded, load_private, new_directory, private_path,
    read_private, require, utcnow, write_new)

_OPERATIONS = {'guest_apply': 'GUEST_CONFIG', 'edge_policy': 'POLICY_APPLY',
               'terraform_plan': 'DISCOVER_READ', 'target_campaign': 'DISCOVER_READ'}
_LOCAL_TARGETS = frozenset({('openstack', 'vm')})


class ProvisioningHeld(RuntimeError):
    """A missing native owner is not replaced by an operator assertion."""
    def __init__(self, hold_code):
        require(hold_code in {'GUEST_PER_COMMAND_AUTHORITY_UNAVAILABLE',
                             'SCOPED_PLANNING_CREDENTIAL_OWNER_UNAVAILABLE'},
                'A fixed supported provisioning hold is required')
        self.hold_code = hold_code
        super().__init__(hold_code)


@dataclass(frozen=True)
class GuestCommandExclusion:
    """The current route has no commissioned per-command SSH authority owner.

    A controller timeout, certificate expiry, sealed inventory or pre-start
    approval cannot exclude an already dispatched remote write. This concrete
    boundary always holds; it exposes no success boolean or callback adapter.
    A future implementation must compose the actual server/connection owner.
    """
    def require_current(self, guard, prepared, target):
        require(isinstance(guard, ObservedProvisioningGuard)
                and isinstance(prepared, Path) and isinstance(target, dict),
                'Exact original guest command binding is required')
        guard.require_current()
        raise ProvisioningHeld('GUEST_PER_COMMAND_AUTHORITY_UNAVAILABLE')


@dataclass(frozen=True)
class LocalOpenStackTarget:
    """Fresh Linux facts on the very VM adopted by the native owner lease.

    This only supports a commissioned in-guest writer and a system network
    namespace with one primary connected IPv4 network per selected interface.
    Provider UUID, machine, namespace or network mismatch holds before nft.
    These facts do not qualify the application or prove inter-VM isolation.
    """
    binding: NativeBinding

    def __post_init__(self):
        require(isinstance(self.binding, NativeBinding)
                and (self.binding.platform_family, self.binding.resource_kind) in _LOCAL_TARGETS,
                'An observed OpenStack VM binding is required')
        UUID(self.binding.native_id)

    def require_current(self, spec):
        require(UUID(Path('/sys/class/dmi/id/product_uuid').read_text().strip()) ==
                UUID(self.binding.native_id), 'The local guest differs from the adopted native VM')
        release = dict(line.split('=', 1) for line in Path('/etc/os-release').read_text().splitlines()
                       if '=' in line)
        require(os.getuid() == os.geteuid() == 0
                and (release.get('ID', '').strip('"'), release.get('VERSION_ID', '').strip('"')) ==
                    ('ubuntu', '24.04'), 'The local owner requires the selected Ubuntu 24.04 root guest')
        require(Path('/etc/machine-id').read_text().strip() == spec['machine_id']
                and os.stat('/proc/self/ns/net').st_ino == os.stat('/proc/1/ns/net').st_ino ==
                    spec['network_namespace_inode'], 'The original guest or system namespace changed')
        present = {name for _number, name in socket.if_nameindex()}
        require(set(spec['interfaces']) <= present, 'A selected native interface is absent')
        # Linux SIOCGIFADDR/SIOCGIFNETMASK read the current primary IPv4 identity.
        # Secondary-address and unnumbered boundaries need a separate observer.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as handle:
            for name, networks in spec['interfaces'].items():
                request = struct.pack('256s', name.encode('ascii'))
                address = socket.inet_ntoa(fcntl.ioctl(handle.fileno(), 0x8915, request)[20:24])
                mask = socket.inet_ntoa(fcntl.ioctl(handle.fileno(), 0x891B, request)[20:24])
                observed = str(ipaddress.IPv4Network(address + '/' + mask, strict=False))
                require(networks == [observed], 'The selected connected interface network changed')
        return {'native_id': self.binding.native_id, 'machine_id': spec['machine_id'],
                'network_namespace_inode': spec['network_namespace_inode'],
                'interfaces': spec['interfaces']}


class ObservedProvisioningGuard:
    """Actual current B10/B11 authority, including the original claimed intent."""
    def __init__(self, runtime, admitted, selection, step, operation_kind, *, local_spec=None):
        require(isinstance(runtime, ObservedProvisioningRuntime)
                and isinstance(admitted, AdmittedInput) and step['kind'] in _OPERATIONS
                and _OPERATIONS[step['kind']] == operation_kind,
                'Concrete original observed-resource command authority required')
        self.runtime, self.admitted, self.selection = runtime, admitted, selection
        self.step, self.operation_kind, self.local_spec = step, operation_kind, local_spec
        self.selection_digest = canonical_record_digest(selection)
        self.claimed = False
        self.binary_binding = None

    def require_current(self):
        runtime = self.runtime
        grant, deadline = runtime.worker_authority.require_worker_step_window(
            runtime.credential, runtime.grant_id, step_id=self.step['id'],
            operation_id=runtime.operation_id, operation_kind=self.operation_kind,
            operation_scope=runtime.scope)
        require((grant.organization_id, grant.tenant_id, grant.plan_id, grant.plan_revision,
                 grant.plan_digest, grant.revocation_epoch, grant.worker_subject,
                 grant.lease_key, grant.lease_epoch) ==
                (self.admitted.organization_id, self.admitted.tenant_id, self.admitted.plan_id,
                 self.admitted.plan_revision, self.admitted.plan_digest, self.admitted.revocation_epoch,
                 runtime.identity.subject, runtime.lease_key, runtime.lease.epoch),
                'The current native command grant differs from the original admitted operation')
        options = {'continuation_grant': grant, 'continuation_identity': runtime.identity} \
                  if self.claimed else {}
        plan, selected = runtime.execution_authority.require_current(
            self.admitted, self.selection_digest, self.operation_kind, **options)
        require(selected == self.selection and
                (grant.source, grant.destination) ==
                    (PlanScope.from_record(plan['spec']['source']),
                     PlanScope.from_record(plan['spec']['destination'])),
                'The complete selected operation or current canonical native scopes changed')
        if self.binary_binding is not None:
            binary, expected = self.binary_binding
            require(binary.is_file() and not binary.is_symlink() and os.access(binary, os.X_OK)
                    and digest(binary.read_bytes()) == expected,
                    'The exact approved native executable changed between commands')
        if self.local_spec is not None:
            require(type(runtime.local_target) is LocalOpenStackTarget,
                    'A commissioned local native identity owner is required')
            runtime.local_target.require_current(self.local_spec)
        deadline = min(deadline, runtime.lease.expires_at, runtime.identity.expires_at)
        require(deadline > utcnow(), 'The next command has no remaining original authority')
        return grant, deadline

    def timeout(self, requested):
        require(type(requested) in {int, float} and requested > 0,
                'A bounded native command interval is required')
        _grant, deadline = self.require_current()
        return min(requested, (deadline - utcnow()).total_seconds())


class _GuardedKernel(nft_edge.Kernel):
    def __init__(self, binary, operation, guard):
        require(isinstance(guard, ObservedProvisioningGuard)
                and guard.operation_kind == 'POLICY_APPLY', 'Exact current policy authority required')
        super().__init__(binary, operation)
        self.guard = guard

    def command(self, arguments):
        self.counter += 1
        output = self.operation / f'kernel-{self.counter:02d}.json'
        error = self.operation / f'kernel-{self.counter:02d}.log'
        timeout = self.guard.timeout(10)
        with os.fdopen(os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'wb') as out, \
             os.fdopen(os.open(error, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'wb') as err:
            result = subprocess.run([self.binary, *arguments], stdin=subprocess.DEVNULL,
                stdout=out, stderr=err, env={'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C'},
                timeout=timeout, umask=0o077)
        self.guard.require_current()
        require(result.returncode == 0, 'Native policy command failed; retain original uncertainty')
        return output.read_text()


@dataclass(frozen=True)
class ObservedProvisioningRuntime:
    """Server-only bindings for one observed resource and exact native operation."""
    execution_authority: PostgresExecutionAuthority
    worker_authority: AuthorityService
    registry: NativeOperationRegistry
    context: TenantContext
    lease: OwnerLease
    identity: VerifiedWorkerIdentity
    credential: object
    grant_id: str
    lease_key: str
    operation_id: str
    scope: PlanScope
    local_target: LocalOpenStackTarget | None = None
    guest_commands: object | None = None
    planning_credentials: object | None = None

    def __post_init__(self):
        from provisioner.controlplane.worker.guest_commands import GuestCommandRuntime
        from provisioner.controlplane.worker.adapters.openstack_planning import ScopedOpenStackPlanningRuntime
        require(isinstance(self.execution_authority, PostgresExecutionAuthority)
                and isinstance(self.worker_authority, AuthorityService)
                and isinstance(self.registry, NativeOperationRegistry)
                and isinstance(self.context, TenantContext) and isinstance(self.lease, OwnerLease)
                and isinstance(self.identity, VerifiedWorkerIdentity) and isinstance(self.scope, PlanScope)
                and all(_valid_id(value) for value in (self.grant_id, self.lease_key, self.operation_id))
                and (self.local_target is None or type(self.local_target) is LocalOpenStackTarget)
                and (self.guest_commands is None or type(self.guest_commands) in
                     {GuestCommandExclusion, GuestCommandRuntime})
                and (self.planning_credentials is None or type(self.planning_credentials) is
                     ScopedOpenStackPlanningRuntime),
                'Concrete enrolled observed-native worker dependencies are required')
        binding = self.lease.binding
        require((self.context.organization_id, self.context.tenant_id, self.scope.site_id,
                 self.scope.security_domain_id, self.identity.subject) ==
                (self.scope.organization_id, self.scope.tenant_id, self.identity.site_id,
                 self.lease.security_domain_id, self.lease.worker_id)
                and (self.lease.organization_id, self.lease.tenant_id) ==
                    (self.context.organization_id, self.context.tenant_id)
                and (self.identity.organization_id, self.identity.tenant_id) ==
                    (self.context.organization_id, self.context.tenant_id)
                and (binding.platform_family, binding.endpoint_id, binding.native_scope_id) ==
                    (self.scope.platform_family, self.scope.endpoint_id, self.scope.native_scope_id),
                'The resource lease and verified worker must name the exact selected native scope')
        if self.local_target is not None:
            require(self.local_target.binding == binding, 'Local guest observer names another native resource')
        for owner in (self.guest_commands, self.planning_credentials):
            if hasattr(owner, 'command_runtime'):
                command = owner.command_runtime
                require(command.authority is self.execution_authority
                        and command.context == self.context and command.identity == self.identity
                        and command.grant.grant_id == self.grant_id
                        and command.grant.operation_id == self.operation_id
                        and command.grant.lease_key == self.lease_key
                        and command.grant.lease_epoch == self.lease.epoch
                        and command.grant.operation_scope == self.scope,
                        'The native command owner differs from the exact original resource enrollment')

    def _claim(self, guard, request):
        guard.require_current()
        self.registry.prepare(self.context, self.lease, self.scope,
            job_id=guard.admitted.job_id, grant_id=self.grant_id, step_id=guard.step['id'],
            lease_key=self.lease_key, worker_identity=self.identity, operation_id=self.operation_id,
            operation_kind=guard.operation_kind, request_digest=canonical_record_digest(request))
        require(self.registry.claim_once(self.context, self.lease, self.scope,
                    self.operation_id, self.identity), 'Original native operation was already claimed')
        guard.claimed = True
        guard.require_current()

    def run_step(self, admitted, selection, plan, step, packet, directory, base, root):
        require(isinstance(admitted, AdmittedInput) and step['kind'] in _OPERATIONS,
                'This observed native owner has no implementation for the selected step')
        kind = _OPERATIONS[step['kind']]
        original_plan = self.execution_authority.require_packet(admitted,
            canonical_record_digest(selection), plan, step, packet, kind)
        require(self.scope == PlanScope.from_record(original_plan['spec']['destination'])
                and self.lease.workload_id == selection['workloadId'],
                'Observed provisioning must use the approved destination and workload')
        delivery_steps.validate_packet(step, packet, plan, base, root=root)
        files = delivery_steps.file_paths(packet)
        values = packet['parameters']
        guard = ObservedProvisioningGuard(self, admitted, selection, step, kind)
        for binary in ('terraform', 'ssh', 'nft'):
            if binary in values:
                guard.binary_binding = (Path(values[binary]), values[binary + '_sha256'])
        guard.require_current()
        directory, base = private_path(directory, directory=True), private_path(base, directory=True)
        if step['kind'] == 'guest_apply':
            require((self.lease.binding.platform_family, self.lease.binding.resource_kind) in _LOCAL_TARGETS,
                    'Guest configuration requires one observed target VM')
            prepared = delivery_steps.prepared_directory(step, packet, plan, base)
            bundle, access, _runtime = guest_apply.validate_bundle(prepared, load_private(files['approval']), root)
            require(len(access['targets']) == 1, 'One VM grant cannot configure a multi-VM prepared inventory')
            target = next(iter(access['targets'].values()))
            require(target['native_id'] == self.lease.binding.native_id
                    and bundle['operation_id'] == self.operation_id,
                    'The prepared guest target differs from the exact adopted native operation')
            from provisioner.controlplane.worker.guest_commands import GuestCommandRuntime
            if type(self.guest_commands) is not GuestCommandRuntime:
                if type(self.guest_commands) is GuestCommandExclusion:
                    self.guest_commands.require_current(guard, prepared, target)
                raise ProvisioningHeld('GUEST_PER_COMMAND_AUTHORITY_UNAVAILABLE')
            command = self.guest_commands.command_runtime.select(admitted, selection, plan,
                step, packet, root, intent_guard=guard)
            self._claim(guard, {'kind': 'guest_apply', 'bundle': bundle,
                               'target': target, 'approval_sha256': digest(read_private(files['approval']))})
            try:
                result = self.guest_commands.execute_prepared(command, prepared, self.lease.binding,
                    files['approval'], delivery_steps.owner_ledger(base, 'guest'), root)
                guard.require_current()
                write_new(directory/'result.json', encoded(result))
                return delivery_steps.complete(step, packet, directory, plan, result, ['result.json'])
            except Exception:
                self.registry.mark_uncertain(self.context, self.operation_id, self.identity.subject)
                raise
        if step['kind'] == 'edge_policy':
            return self._policy(guard, plan, step, packet, values, files, directory, base, root)
        if step['kind'] == 'terraform_plan':
            from provisioner.controlplane.worker.adapters.openstack_planning import ScopedOpenStackPlanningRuntime
            if type(self.planning_credentials) is not ScopedOpenStackPlanningRuntime:
                raise ProvisioningHeld('SCOPED_PLANNING_CREDENTIAL_OWNER_UNAVAILABLE')
            return self.planning_credentials.run_step(admitted, selection, plan, step, packet,
                directory, base, root, guard=guard)
        else:
            campaign = load_private(files['plan'])
            require(campaign['scope'] == selection['executionScope']
                    and campaign['format'] == 'hosting-target-campaign/2',
                    'The selected route requires its exact OpenStack workload observation campaign')
            # Scope labels in the inventory cannot grant another native project.
            # Check physical manifest selectors against the current native scope
            # before the existing campaign owner opens any API connection.
            for name in ('native_manifest', 'workload_manifest'):
                asset = campaign['assets'][name]
                raw = read_private(asset['path'])
                require(digest(raw) == asset['sha256'] and
                        qualify_target.c.strict_loads(raw)['project_id'] == self.scope.native_scope_id,
                        'Native observation manifest belongs to another granted project')
            result = qualify_target.execute(files['plan'], authority_path=files['authority'],
                ssh=Path(values['ssh']), output=directory / 'execution', root=root, command_guard=guard)
            require(result['status'] == 'COLLECTED_REQUIRES_INDEPENDENT_ACCEPTANCE',
                    'The actual native or service observation remains held')
            write_new(directory / 'result.json', read_private(directory / 'execution/result.json'))
            names = ['result.json']
        guard.require_current()
        return delivery_steps.complete(step, packet, directory, plan, result, names)

    def _policy(self, guard, plan, step, packet, values, files, directory, base, root):
        from provisioner.execution.source_integrity import verify, verify_runtime
        source = verify(root)
        require(source['status'] == 'HASHES_MATCH' and source['commit'] == guard.selection['sourceCommit'] and
                verify_runtime(root)['status'] == 'RUNTIME_SOURCES_MATCH',
                'The local policy runtime must match the selected clean source')
        spec, authority = load_private(files['spec']), load_private(files['authority'])
        nft_edge.validate(spec)
        require(spec['scope'] == plan['scope'] and spec['operation_id'] == self.operation_id
                and (self.lease.binding.platform_family, self.lease.binding.resource_kind) in _LOCAL_TARGETS
                and type(self.local_target) is LocalOpenStackTarget,
                'The exact observed VM, native operation and local policy owner are required')
        require(digest(Path(values['nft']).read_bytes()) == spec['nft_sha256'] == values['nft_sha256'],
                'The approved native policy executable changed')
        current_window(authority)
        guard.local_spec = spec
        _grant, deadline = guard.require_current()
        native_until = datetime.fromisoformat(authority['valid_until'].replace('Z', '+00:00'))
        # Preserve the original authority bytes and receipt. Native allow leases
        # must expire inside the real worker window, not only the wider packet.
        require(native_until <= deadline, 'Reissue native policy authority inside the current worker grant window')
        execution = new_directory(directory / 'execution', root)
        kernel = _GuardedKernel(Path(values['nft']).resolve(strict=True), execution, guard)
        try:
            self._claim(guard, {'selected_artifact': guard.selection_digest,
                               'packet': packet, 'native_binding': self.lease.binding.key()})
            result = nft_edge.apply(spec, values['mode'], authority, kernel,
                delivery_steps.owner_ledger(base, 'edge_policy'), execution)
            guard.require_current()
            write_new(directory / 'result.json', read_private(execution / 'receipt.json'))
            return delivery_steps.complete(step, packet, directory, plan, result, ['result.json'])
        except BaseException:
            if guard.claimed:
                try:
                    self.registry.mark_uncertain(self.context, self.operation_id,
                        self.identity.subject)
                except BaseException:
                    pass
            raise
