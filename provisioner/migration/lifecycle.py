"""Immutable selected Linux application contract and real command authority."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from provisioner.controlplane.authority import AuthorityService, PlanScope
from provisioner.controlplane.persistence import TenantContext, canonical_record_digest
from provisioner.controlplane.persistence.store import NativeBinding, OwnerLease
from provisioner.controlplane.reconciliation import NativeOperationRegistry
from provisioner.controlplane.worker.grants import VerifiedWorkerIdentity
from provisioner.controlplane.workflow.admitted_job import AdmittedInput
from provisioner.controlplane.workflow.execution_selection import PostgresExecutionAuthority
from provisioner.execution import restic_run, vsphere_power
from provisioner.execution.neutron_observe import strict_loads
from provisioner.execution.run_files import encoded, private_path, require, utcnow
from .guest_lifecycle import ACTION_SOURCE_FILES
from .resources import LinuxApplicationIO, LinuxTransferResources, TransferLimits

FORMAT = 'hosting-application-lifecycle-selection/1'
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}')
_HASH = re.compile(r'[0-9a-f]{64}')
PHASES = {
    'TARGET_PREPARE': ('destination', 'VM_POWER'),
    'TARGET_BOOTSTRAP': ('destination', 'NETWORK_ATTACH'),
    'TARGET_POLICY': ('destination', 'POLICY_APPLY'),
    'TARGET_ISOLATE': ('destination', 'POLICY_APPLY'),
    'REHEARSAL': ('destination', 'DESTINATION_ACTIVATE'),
    'SOURCE_FENCE': ('source', 'SOURCE_FENCE'),
    'FINAL_SYNC': ('destination', 'RESTORE_DATA'),
    'ACTIVATE': ('destination', 'DESTINATION_ACTIVATE'),
    'VERIFY_READ': ('destination', 'DISCOVER_READ'),
    'SOURCE_VERIFY_READ': ('source', 'DISCOVER_READ'),
    'TARGET_FENCE': ('destination', 'SOURCE_FENCE'),
    'SOURCE_REATTACH': ('source', 'DISK_ATTACH'),
    'SOURCE_START': ('source', 'VM_POWER'),
    'PREWRITE_RETURN': ('source', 'DESTINATION_ACTIVATE'),
    'POSTWRITE_CAPTURE': ('destination', 'SOURCE_FENCE'),
    'POSTWRITE_RESTORE': ('source', 'RESTORE_DATA'),
    'POSTWRITE_RETURN': ('source', 'DESTINATION_ACTIVATE'),
    'FORWARD_REPAIR': ('destination', 'RESTORE_DATA'),
    'TARGET_REATTACH': ('destination', 'DISK_ATTACH'),
    'TARGET_START': ('destination', 'VM_POWER'),
    'FORWARD_ACTIVATE': ('destination', 'DESTINATION_ACTIVATE'),
}
_DIRECTIONS = frozenset({('vmware', 'openstack')})


def _path(value):
    require(isinstance(value, str) and re.fullmatch(r'/[A-Za-z0-9_./-]+', value)
            and value != '/' and '..' not in Path(value).parts and str(Path(value)) == value,
            'An exact bounded application path is required')


def _guest(value):
    require(isinstance(value, dict) and set(value) == {'native_id', 'native_uuid', 'machine_id',
            'unit', 'unit_sha256', 'uid', 'gid', 'mount_path', 'filesystem_uuid',
            'data_path', 'executable', 'health', 'action_runtime', 'block_serial'},
            'An exact enrolled application guest is required')
    require(_ID.fullmatch(value['native_id']) and re.fullmatch(r'[0-9a-f-]{36}', value['native_uuid'])
            and re.fullmatch(r'[0-9a-f]{32}', value['machine_id'])
            and re.fullmatch(r'hosting-[a-z0-9][a-z0-9-]{0,60}\.service', value['unit'])
            and _HASH.fullmatch(value['unit_sha256'])
            and all(type(value[key]) is int and 100 <= value[key] <= 60000 for key in ('uid', 'gid')),
            'The exact native guest and unprivileged application unit are required')
    _path(value['mount_path']); _path(value['data_path'])
    require(Path(value['data_path']).is_relative_to(Path(value['mount_path']))
            and Path(value['data_path']) != Path(value['mount_path'])
            and re.fullmatch(r'[0-9a-f-]{36}', value['filesystem_uuid']),
            'Application data must stay on its one enrolled filesystem')
    require(re.fullmatch(r'[0-9a-f]{32,64}', value['block_serial']),
            'The application filesystem must bind its real exclusive native block-disk serial')
    executable = value['executable']
    require(isinstance(executable, dict) and set(executable) == {'path', 'sha256', 'arguments'}
            and _HASH.fullmatch(executable['sha256'])
            and isinstance(executable['arguments'], list) and len(executable['arguments']) <= 32
            and all(isinstance(argument, str) and len(argument) <= 1024 and '\x00' not in argument
                    and '\n' not in argument for argument in executable['arguments']),
            'The immutable application image executable and arguments are required')
    _path(executable['path'])
    action_runtime = value['action_runtime']
    require(isinstance(action_runtime, dict) and set(action_runtime) == {'root', 'python_sha256', 'source_files'}
            and _HASH.fullmatch(action_runtime['python_sha256'])
            and isinstance(action_runtime['source_files'], dict)
            and set(action_runtime['source_files']) == ACTION_SOURCE_FILES
            and all(_HASH.fullmatch(digest) for digest in action_runtime['source_files'].values()),
            'The shipped application action needs its complete content-bound guest source closure')
    _path(action_runtime['root'])
    health = value['health']
    require(isinstance(health, dict) and set(health) == {'port', 'path', 'response_sha256'}
            and type(health['port']) is int and 1024 <= health['port'] <= 65535
            and isinstance(health['path'], str) and re.fullmatch(r'/[A-Za-z0-9_/-]{0,128}', health['path'])
            and _HASH.fullmatch(health['response_sha256']),
            'One harmless useful application health response is required')


@dataclass(frozen=True)
class ApplicationLifecycleSelection:
    canonical: bytes

    def __post_init__(self):
        require(isinstance(self.canonical, bytes) and len(self.canonical) <= 16 * 1024 * 1024,
                'A bounded canonical application lifecycle selection is required')
        body = strict_loads(self.canonical)
        require(isinstance(body, dict) and encoded(body) == self.canonical and set(body) ==
                {'format', 'guest_profile', 'source_scope', 'destination_scope', 'members'}
                and body['format'] == FORMAT and body['guest_profile'] == 'linux-ubuntu-2404',
                'The exact selected Linux application lifecycle is required')
        source, target = (PlanScope.from_record(body[key]) for key in ('source_scope', 'destination_scope'))
        require((source.platform_family, target.platform_family) in _DIRECTIONS
                and (source.organization_id, source.tenant_id) == (target.organization_id, target.tenant_id),
                'No concrete application lifecycle owner exists for this direction')
        require(isinstance(body['members'], list) and 1 <= len(body['members']) <= 32,
                'The complete bounded application member set is required')
        members, datasets, operations, steps, paths = set(), set(), set(), set(), set()
        for member in body['members']:
            required = {'machine_id', 'dataset_id',
                    'source', 'target', 'initial_target_path', 'rehearsal_path', 'final_target_path',
                    'recovery_target_path', 'forward_target_path', 'max_bytes', 'source_export', 'target_export', 'phases',
                    'native_fence', 'target_native_fence', 'traffic_steps', 'source_io', 'target_io',
                    'source_resources', 'target_resources'}
            require(isinstance(member, dict) and required <= set(member)
                    and set(member) - required <= {'source_database_directory', 'target_database_directory',
                                                   'target_management', 'target_policy'}
                    and ('source_database_directory' in member) == ('target_database_directory' in member),
                    'The exact selected application member is required')
            if 'source_database_directory' in member:
                for side in ('source', 'target'):
                    _path(member[side + '_database_directory'])
                    require(not Path(member[side + '_database_directory']).is_relative_to(Path(member[side]['mount_path'])),
                        'The PostgreSQL engine data cannot live on the selected application file disk')
            for key, known in (('machine_id', members), ('dataset_id', datasets)):
                require(_ID.fullmatch(member[key]) and member[key] not in known,
                        'Application members and datasets cannot be duplicated')
                known.add(member[key])
            _guest(member['source']); _guest(member['target'])
            require((member['source']['uid'], member['source']['gid']) ==
                    (member['target']['uid'], member['target']['gid']),
                    'This concrete Linux application owner requires unchanged unprivileged data ownership')
            for key in ('initial_target_path', 'rehearsal_path', 'final_target_path', 'recovery_target_path', 'forward_target_path'):
                _path(member[key])
                selected = Path(member[key])
                require(selected not in paths and not any(selected.is_relative_to(previous)
                        or previous.is_relative_to(selected) for previous in paths),
                        'Application staging and rehearsal paths must be distinct')
                paths.add(selected)
            require(type(member['max_bytes']) is int and 1 <= member['max_bytes'] <= 2**40,
                    'An approved useful-byte ceiling is required')
            for side in ('source', 'target'):
                require(isinstance(member[side + '_io'], dict)
                        and set(member[side + '_io']) == {'cgroup', 'block_device', 'bandwidth_kib_per_second', 'block_iops'},
                        'Both final export directions require exact finite source-I/O ownership')
                LinuxApplicationIO(**member[side + '_io'])
            for side, stage in (('target', 'final_target_path'), ('source', 'recovery_target_path')):
                resources = member[side + '_resources']
                require(isinstance(resources, dict) and set(resources) == {'stage_parent', 'cgroup', 'block_device', 'limits'}
                        and isinstance(resources['limits'], dict), 'A transfer requires its exact reserved staging controls')
                controls = LinuxTransferResources(Path(resources['stage_parent']), resources['cgroup'],
                                                  resources['block_device'], TransferLimits(**resources['limits']))
                require(controls.limits.expected_bytes == member['max_bytes']
                        and Path(member[stage]).parent == controls.stage_parent,
                        'A dynamic final or recovery export cannot exceed its approved staging useful-byte ceiling')
            require(Path(member['forward_target_path']).parent == Path(member['target_resources']['stage_parent']),
                    'Forward repair needs a new reserved target staging root')
            require(Path(member['rehearsal_path']).parent == Path(member['target_resources']['stage_parent'])
                    and Path(member['initial_target_path']).is_relative_to(Path(member['target_resources']['stage_parent'])),
                    'The original restored dataset and rehearsal copy must remain in the reserved finite staging filesystem')
            for key, guest in (('source_export', member['source']), ('target_export', member['target'])):
                config = member[key]
                restic_run.validate(config, allow_expired=True)
                require(config['machine_id'] == guest['machine_id'] and config['source'] == guest['data_path'],
                        'A final export must bind its exact original application guest and path')
            base_phases = set(PHASES) - {'TARGET_PREPARE', 'TARGET_BOOTSTRAP', 'TARGET_POLICY', 'TARGET_ISOLATE'}
            require(isinstance(member['phases'], dict) and set(member['phases']) in
                    (base_phases, base_phases | {'TARGET_PREPARE'},
                     base_phases | {'TARGET_PREPARE', 'TARGET_BOOTSTRAP'}, set(PHASES))
                    and ('TARGET_BOOTSTRAP' in member['phases']) == ('target_management' in member)
                    and ('TARGET_POLICY' in member['phases']) == ('target_policy' in member),
                    'Every application phase needs its own immutable original operation')
            if 'target_management' in member:
                from .bootstrap_selection import validate_management_selection
                validate_management_selection(member['target_management'], target)
            if 'target_policy' in member:
                from .bootstrap_selection import validate_policy_selection
                validate_policy_selection(member['target_policy'], target, member['target_management'],
                                          member['target']['health']['port'])
            for phase, expected in PHASES.items():
                if phase not in member['phases']:
                    continue
                row = member['phases'][phase]
                require(isinstance(row, dict) and set(row) == {'step_id', 'operation_id', 'scope_side', 'operation_kind'}
                        and (row['scope_side'], row['operation_kind']) == expected,
                        'An application phase cannot borrow another native action capability')
                for key, known in (('step_id', steps), ('operation_id', operations)):
                    require(_ID.fullmatch(row[key]) and row[key] not in known,
                            'Application phase identities cannot be reused')
                    known.add(row[key])
            fence = member['native_fence']
            require(isinstance(fence, dict) and set(fence) == {'power_request', 'disk_keys', 'previous_owner'}
                    and vsphere_power.validate(fence['power_request'])['moid'] == member['source']['native_id']
                    and fence['power_request']['desired_power'] == 'poweredOff'
                    and isinstance(fence['disk_keys'], list) and 1 <= len(fence['disk_keys']) <= 16
                    and len(set(fence['disk_keys'])) == len(fence['disk_keys'])
                    and all(type(key) is int and key > 0 for key in fence['disk_keys']),
                    'The selected source fence requires exact retained data disks and shutdown')
            disks = [device for device in fence['power_request']['snapshot']['resources'][0]['expected']['config']['hardware']['device']
                     if device['key'] in fence['disk_keys']]
            require(len(disks) == len(fence['disk_keys']) == 1 and disks[0]['_typeName'] == 'VirtualDisk'
                    and re.sub('[^0-9a-f]', '', disks[0]['backing']['uuid'].lower()) == member['source']['block_serial']
                    and fence['power_request']['snapshot']['resources'][0]['expected']['config']['uuid'] ==
                        member['source']['native_uuid'],
                    'The selected filesystem must bind its one actual exclusive source data disk and BIOS UUID')
            previous = fence['previous_owner']
            require(isinstance(previous, dict) and set(previous) == {'worker_id', 'owner_epoch', 'incident_id'}
                    and _ID.fullmatch(previous['worker_id']) and _ID.fullmatch(previous['incident_id'])
                    and type(previous['owner_epoch']) is int and previous['owner_epoch'] > 0,
                    'The source fence needs its exact previously excluded writer epoch')
            target_fence = member['target_native_fence']
            require(isinstance(target_fence, dict) and set(target_fence) ==
                    {'volume_id', 'device', 'previous_owner', 'identity_url', 'compute_endpoint', 'volume_endpoint',
                     'region', 'interface', 'cloud_alias', 'ca_sha256'}
                    and re.fullmatch(r'[0-9a-f-]{36}', target_fence['volume_id'])
                    and target_fence['volume_id'].replace('-', '') == member['target']['block_serial']
                    and re.fullmatch(r'/dev/[a-z]+[a-z0-9]*', target_fence['device'])
                    and _HASH.fullmatch(target_fence['ca_sha256'])
                    and target_fence['interface'] in {'internal', 'public'}
                    and all(isinstance(target_fence[key], str) and target_fence[key]
                            for key in ('identity_url', 'compute_endpoint', 'volume_endpoint', 'region', 'cloud_alias')),
                    'The target native fence requires one exact retained Nova/Cinder data volume and commissioned endpoints')
            previous = target_fence['previous_owner']
            require(isinstance(previous, dict) and set(previous) == {'worker_id', 'owner_epoch', 'incident_id'}
                    and _ID.fullmatch(previous['worker_id']) and _ID.fullmatch(previous['incident_id'])
                    and type(previous['owner_epoch']) is int and previous['owner_epoch'] > 0,
                    'The target fence needs its exact independently excluded previous owner')
            require(isinstance(member['traffic_steps'], dict)
                    and set(member['traffic_steps']) == {'cutover_dns', 'cutover_propagation',
                                                        'return_dns', 'return_propagation'}
                    and all(_ID.fullmatch(value) for value in member['traffic_steps'].values()),
                    'Cutover and return require separately selected authoritative traffic operations')

    @classmethod
    def from_record(cls, body):
        return cls(encoded(body))

    @property
    def sha256(self):
        return canonical_record_digest(self.to_dict())

    def to_dict(self):
        return strict_loads(self.canonical)

    def member(self, machine_id):
        found = [member for member in self.to_dict()['members'] if member['machine_id'] == machine_id]
        require(len(found) == 1, 'The original selected application member is unavailable')
        return found[0]


@dataclass(frozen=True)
class LifecycleWorkerRuntime:
    """Actual server-side B10/B11 owners for one enrolled existing VM operation."""
    execution_authority: PostgresExecutionAuthority
    worker_authority: AuthorityService
    registry: NativeOperationRegistry
    context: TenantContext
    lease: OwnerLease
    identity: VerifiedWorkerIdentity
    credential: object
    grant_id: str
    lease_key: str
    scope: PlanScope

    def __post_init__(self):
        require(isinstance(self.execution_authority, PostgresExecutionAuthority)
                and isinstance(self.worker_authority, AuthorityService)
                and isinstance(self.registry, NativeOperationRegistry)
                and isinstance(self.context, TenantContext) and isinstance(self.lease, OwnerLease)
                and isinstance(self.identity, VerifiedWorkerIdentity) and isinstance(self.scope, PlanScope)
                and _ID.fullmatch(self.grant_id) and _ID.fullmatch(self.lease_key),
                'Actual enrolled application worker and native registry owners are required')
        require((self.context.organization_id, self.context.tenant_id, self.identity.site_id,
                 self.identity.subject, self.lease.security_domain_id) ==
                (self.scope.organization_id, self.scope.tenant_id, self.scope.site_id,
                 self.lease.worker_id, self.scope.security_domain_id)
                and (self.lease.organization_id, self.lease.tenant_id) ==
                    (self.context.organization_id, self.context.tenant_id)
                and (self.identity.organization_id, self.identity.tenant_id) ==
                    (self.context.organization_id, self.context.tenant_id)
                and (self.lease.binding.platform_family, self.lease.binding.endpoint_id,
                     self.lease.binding.native_scope_id, self.lease.binding.resource_kind) ==
                    (self.scope.platform_family, self.scope.endpoint_id, self.scope.native_scope_id, 'vm'),
                'The application worker lease differs from the exact native VM and site')


class LifecycleCommandGuard:
    """One concrete immutable lifecycle phase; claims no arbitrary callback."""
    def __init__(self, runtime, admitted, selection, lifecycle, phase, member_id, *, recovery=None, network_gate=None):
        require(isinstance(runtime, LifecycleWorkerRuntime) and isinstance(admitted, AdmittedInput)
                and isinstance(selection, dict) and isinstance(lifecycle, ApplicationLifecycleSelection)
                and selection.get('applicationLifecycleSelectionDigest') == lifecycle.sha256
                and phase in PHASES, 'An approved concrete application phase is required')
        self.runtime, self.admitted, self.lifecycle, self.phase = runtime, admitted, lifecycle, phase
        self.member_id, self.selection_bytes = member_id, encoded(selection)
        self.selection_digest = canonical_record_digest(selection)
        self.member = lifecycle.member(member_id)
        if recovery is not None:
            from .recovery import ApplicationRecoverySelection
            require(type(recovery) is ApplicationRecoverySelection
                and selection.get('applicationRecoverySelectionDigest') == recovery.sha256
                and recovery.to_dict()['currentLifecycleDigest'] == lifecycle.sha256
                and recovery.to_dict()['mode'] == 'FORWARD_REPAIR'
                and phase in {'TARGET_REATTACH', 'TARGET_START', 'FORWARD_REPAIR', 'FORWARD_ACTIVATE'},
                'Recovery admits only the exact separately approved retained-target effect')
        self.recovery = recovery
        if network_gate is not None:
            from .application_network import OpenStackBootstrapRuntime
            require(type(network_gate) is OpenStackBootstrapRuntime and network_gate.registry is runtime.registry,
                    'The guest network gate must use the same original native registry')
        self.network_gate = network_gate
        self.row = self.member['phases'][phase]
        self.step = dict(id=self.row['step_id'], kind='application_' + phase.lower())
        self.operation_kind = self.row['operation_kind']
        self.descriptor_sha256 = lifecycle.sha256
        body = lifecycle.to_dict()
        self.scope = PlanScope.from_record(body[self.row['scope_side'] + '_scope'])
        self.binding = NativeBinding(self.scope.platform_family, self.scope.endpoint_id,
            self.scope.native_scope_id, 'vm', self.member[
                'source' if self.row['scope_side'] == 'source' else 'target']['native_id'])
        require(runtime.scope == self.scope and runtime.lease.binding == self.binding
                and runtime.lease.workload_id == selection['workloadId'],
                'The lifecycle phase is not enrolled on its exact selected original VM')
        self.claimed = False

    def require_guest_network(self):
        if self.row['scope_side'] != 'destination' or 'applicationStagingSelectionDigest' not in \
                strict_loads(self.selection_bytes):
            return
        require(self.network_gate is not None and self.phase != 'TARGET_BOOTSTRAP',
                'Current independently enrolled management policy is required before a guest effect')
        policy = True if self.phase in {'ACTIVATE', 'FORWARD_REPAIR', 'FORWARD_ACTIVATE'} else \
            (None if self.phase in {'TARGET_FENCE', 'POSTWRITE_CAPTURE'} else False)
        self.network_gate.observe(self.admitted, strict_loads(self.selection_bytes), self.lifecycle, self.member_id,
                                  policy_enabled=policy if 'target_policy' in self.member else False)

    def require_current(self):
        require(self.lifecycle.sha256 == self.descriptor_sha256
                and self.lifecycle.member(self.member_id) == self.member
                and self.member['phases'][self.phase] == self.row,
                'The original selected application phase was replaced')
        runtime = self.runtime
        grant, deadline = runtime.worker_authority.require_worker_step_window(
            runtime.credential, runtime.grant_id, step_id=self.row['step_id'],
            operation_id=self.row['operation_id'], operation_kind=self.operation_kind,
            operation_scope=self.scope)
        require((grant.organization_id, grant.tenant_id, grant.plan_id, grant.plan_revision,
                 grant.plan_digest, grant.revocation_epoch, grant.worker_subject,
                 grant.lease_key, grant.lease_epoch) ==
                (self.admitted.organization_id, self.admitted.tenant_id, self.admitted.plan_id,
                 self.admitted.plan_revision, self.admitted.plan_digest, self.admitted.revocation_epoch,
                 runtime.identity.subject, runtime.lease_key, runtime.lease.epoch),
                'The application phase differs from its current original admitted worker grant')
        options = dict(continuation_grant=grant, continuation_identity=runtime.identity) if self.claimed else {}
        plan, selected = runtime.execution_authority.require_current(
            self.admitted, self.selection_digest, self.operation_kind, **options)
        require(encoded(selected) == self.selection_bytes and
                (grant.source, grant.destination) ==
                (PlanScope.from_record(plan['spec']['source']), PlanScope.from_record(plan['spec']['destination'])),
                'The complete selected application or exact canonical native scopes changed')
        if self.recovery is None:
            require(plan['spec']['source'] == self.lifecycle.to_dict()['source_scope']
                and plan['spec']['destination'] == self.lifecycle.to_dict()['destination_scope'],
                'The complete selected application or exact canonical native scopes changed')
        else:
            self.recovery.require_forward_plan(plan, selected, self.lifecycle)
        deadline = min(deadline, runtime.lease.expires_at, runtime.identity.expires_at)
        require(deadline > utcnow(), 'The original application command authority has expired')
        return grant, deadline

    def claim(self, request_digest):
        require(_HASH.fullmatch(request_digest) and not self.claimed,
                'One exact original application intent must be claimed only once')
        self.require_current()
        runtime = self.runtime
        operation = runtime.registry.prepare(runtime.context, runtime.lease, self.scope,
            job_id=self.admitted.job_id, grant_id=runtime.grant_id, step_id=self.row['step_id'],
            lease_key=runtime.lease_key, worker_identity=runtime.identity,
            operation_id=self.row['operation_id'], operation_kind=self.operation_kind,
            request_digest=request_digest)
        require(runtime.registry.claim_once(runtime.context, runtime.lease, self.scope,
                    self.row['operation_id'], runtime.identity),
                'The original application operation was already claimed; independently observe it')
        self.claimed = True
        self.require_current()
        return operation

    def uncertain(self):
        if self.claimed:
            self.runtime.registry.mark_uncertain(self.runtime.context, self.row['operation_id'],
                                                 self.runtime.identity.subject)

    def timeout(self, requested):
        require(type(requested) in {int, float} and 0 < requested <= 3600,
                'A bounded application command interval is required')
        _grant, deadline = self.require_current()
        return min(requested, (deadline - utcnow()).total_seconds())
