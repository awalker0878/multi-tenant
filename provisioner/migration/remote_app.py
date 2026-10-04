"""Concrete fixed application commands on the independently enrolled SSH owner."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

from provisioner.controlplane.worker.command_runtime import ApplicationWorkerCommandAuthority
from provisioner.controlplane.worker.guest_commands import GuestCommandRuntime
from provisioner.controlplane.reconciliation.read_enrollment import NativeReadEnrollment
from provisioner.execution.neutron_observe import strict_loads
from provisioner.execution.run_files import digest, encoded, private_path, require, sync_directory, utcnow
from .lifecycle import LifecycleCommandGuard, LifecycleWorkerRuntime

# Only standard-library code runs before the complete selected package closure
# and guest interpreter are checked. -I -S disables ambient paths and site hooks.
# The installed action then performs one fixed syscall/filesystem action; it
# launches no inner shell or native subprocess outside the per-command owner.
ACTION_BOOTSTRAP = r'''
import hashlib, json, os, pathlib, stat, sys
runtime = json.loads(sys.argv[1]); action = sys.argv[2]
root = pathlib.Path(runtime['root'])
for name, expected in runtime['source_files'].items():
    selected = root/name
    for parent in [selected, *selected.parents]:
        info = parent.lstat()
        if stat.S_ISLNK(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise SystemExit(125)
    fd = os.open(selected, os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        if hashlib.sha256(stream.read()).hexdigest() != expected:
            raise SystemExit(125)
if hashlib.sha256(pathlib.Path(sys.executable).read_bytes()).hexdigest() != runtime['python_sha256']:
    raise SystemExit(125)
sys.path.insert(0, str(root))
from provisioner.migration.guest_lifecycle import execute
raw = sys.stdin.buffer.read(1048577)
if len(raw)>1048576: raise SystemExit(125)
print(json.dumps(execute(action, json.loads(raw)),sort_keys=True,separators=(',',':')))
'''


@dataclass(frozen=True)
class ApplicationGuestRuntime:
    worker: LifecycleWorkerRuntime
    commands: GuestCommandRuntime
    target: dict
    ssh_runtime: dict
    key: Path
    certificate: Path
    output_directory: Path
    source_root: Path

    def __post_init__(self):
        require(isinstance(self.worker, LifecycleWorkerRuntime)
                and isinstance(self.commands, GuestCommandRuntime)
                and isinstance(self.target, dict) and isinstance(self.ssh_runtime, dict)
                and self.commands.command_runtime.authority is self.worker.execution_authority
                and self.commands.command_runtime.context == self.worker.context
                and self.commands.command_runtime.identity == self.worker.identity
                and self.commands.command_runtime.grant.grant_id == self.worker.grant_id,
                'The application guest must reuse its actual enrolled per-command worker owner')
        object.__setattr__(self, 'key', private_path(self.key))
        object.__setattr__(self, 'certificate', private_path(self.certificate))
        object.__setattr__(self, 'output_directory', private_path(self.output_directory, directory=True))
        object.__setattr__(self, 'source_root', Path(self.source_root))
        object.__setattr__(self, 'target', deepcopy(self.target))
        object.__setattr__(self, 'ssh_runtime', deepcopy(self.ssh_runtime))

    @property
    def registry(self):
        return self.worker.registry

    def select(self, guard):
        require(isinstance(guard, LifecycleCommandGuard) and guard.runtime is self.worker,
                'The exact original application phase guard is required')
        guest = guard.member['source' if guard.row['scope_side'] == 'source' else 'target']
        require((self.target['native_id'], self.target['machine_id']) ==
                (guest['native_id'], guest['machine_id']), 'The enrolled SSH handoff names another application guest')
        for name, expected in guest['action_runtime']['source_files'].items():
            selected = self.source_root / name
            require(selected.is_file() and not selected.is_symlink() and digest(selected.read_bytes()) == expected,
                    'The selected shipped guest action does not match this approved runtime')
        return self.commands.command_runtime.select_application(guard.admitted,
            strict_loads(guard.selection_bytes), guard.lifecycle, guard.phase, guard.member_id,
            self.source_root, intent_guard=guard)

    def command(self, authority, arguments, *, input_bytes=b'', timeout=60):
        require(isinstance(authority, ApplicationWorkerCommandAuthority)
                and authority.intent_guard.runtime is self.worker,
                'One concrete original application command authority is required')
        # Every exchange has separate retained stdout/stderr and fresh SSH
        # identity checks. Reusing a directory cannot hide a previous command.
        number = len(list(self.output_directory.glob('command-*'))) + 1
        output = self.output_directory / f'command-{number:05d}'
        output.mkdir(mode=0o700); sync_directory(self.output_directory)
        return self.commands.exchange(authority, target=self.target,
            binding=self.worker.lease.binding, runtime=self.ssh_runtime, key=self.key,
            certificate=self.certificate, remote_argv=tuple(arguments), input_bytes=input_bytes,
            output=output, timeout=timeout)

    def action(self, authority, action, parameters):
        guard = authority.intent_guard
        if action.startswith('FORWARD_RESTORE_'):
            require(guard.phase == 'FORWARD_REPAIR' and guard.recovery is not None
                and parameters.get('config') == guard.member['target_export']
                and parameters.get('target') == guard.member['forward_target_path'],
                'Same-guest restoration requires its independently approved committed-data recovery')
        guest = guard.member['source' if guard.row['scope_side'] == 'source' else 'target']
        packet = dict(format='hosting-application-guest-action/1', job_id=guard.admitted.job_id,
            operation_id=guard.row['operation_id'], selection_sha256=guard.lifecycle.sha256,
            guest=guest, parameters=parameters)
        raw = self.command(authority, ('/usr/bin/sudo', '-n', '--', '/usr/bin/python3', '-I', '-S', '-c',
            ACTION_BOOTSTRAP, encoded(guest['action_runtime']).decode(), action), input_bytes=encoded(packet))
        result = strict_loads(raw)
        require(isinstance(result, dict) and result.get('format') == 'hosting-application-guest-observation/1'
                and (result.get('action'), result.get('job_id'), result.get('operation_id'),
                     result.get('selection_sha256')) ==
                (action, guard.admitted.job_id, guard.row['operation_id'], guard.lifecycle.sha256)
                and result.get('identity') == {'machine_id': guest['machine_id'],
                    'native_uuid': guest['native_uuid'], 'image': 'ubuntu-24.04'},
                'The actual guest observation belongs to another application or operation')
        return result['observation']

    def systemctl(self, authority, verb, unit, *, properties=()):
        require(verb in {'stop', 'start', 'mask', 'unmask', 'show'}
                and isinstance(unit, str), 'One fixed selected service operation is required')
        guard = authority.intent_guard
        guest = guard.member['source' if guard.row['scope_side'] == 'source' else 'target']
        rehearsal = 'hosting-rehearsal-' + guard.row['operation_id'].replace(':', '-').replace('.', '-') + '.service'
        require(unit in {guest['unit'], rehearsal}, 'A service action escaped its exact selected application unit')
        argv = ['/usr/bin/sudo', '-n', '--', '/usr/bin/systemctl', verb, '--no-pager', unit]
        if properties:
            require(verb == 'show' and set(properties) <= {'ActiveState', 'SubState', 'UnitFileState',
                'MainPID', 'User', 'Group', 'PrivateNetwork', 'ProtectSystem', 'NoNewPrivileges',
                'BindPaths', 'ReadWritePaths', 'CapabilityBoundingSet', 'FragmentPath', 'ExecStart'},
                'Only fixed application service observation properties are supported')
            argv += ['--property=' + name for name in properties]
        raw = self.command(authority, tuple(argv)).decode('utf-8')
        if verb != 'show':
            return dict(verb=verb, unit=unit, response_sha256=digest(raw.encode()))
        values = {}
        for line in raw.splitlines():
            name, separator, value = line.partition('=')
            require(separator and name in properties and name not in values,
                    'Systemd returned an unselected or duplicated service property')
            values[name] = value
        require(set(values) == set(properties), 'Systemd did not return the exact selected service properties')
        return values

    def start_rehearsal(self, authority, guest, copy_path):
        guard = authority.intent_guard
        require(guest == guard.member['target'] and
                ((guard.phase == 'REHEARSAL' and copy_path == guard.member['rehearsal_path']) or
                 (guard.phase == 'FORWARD_REPAIR' and guard.recovery is not None
                  and copy_path == guard.member['rehearsal_path'])),
                'The isolated transient application can only use its exact selected copy')
        unit = 'hosting-rehearsal-' + guard.row['operation_id'].replace(':', '-').replace('.', '-') + '.service'
        argv = ('/usr/bin/sudo', '-n', '--', '/usr/bin/systemd-run', '--unit=' + unit,
            '--property=Type=exec', '--property=User=' + str(guest['uid']),
            '--property=Group=' + str(guest['gid']), '--property=PrivateNetwork=yes',
            '--property=PrivateTmp=yes', '--property=ProtectSystem=strict',
            '--property=ProtectHome=yes', '--property=NoNewPrivileges=yes',
            '--property=CapabilityBoundingSet=', '--property=DevicePolicy=closed',
            '--property=RestrictSUIDSGID=yes', '--property=RestrictNamespaces=yes',
            '--property=RestrictAddressFamilies=AF_INET AF_INET6',
            '--property=TemporaryFileSystem=/etc:ro /run:rw',
            '--property=ProtectKernelTunables=yes', '--property=ProtectKernelModules=yes',
            '--property=ProtectControlGroups=yes',
            '--property=BindPaths=' + copy_path + ':' + guest['data_path'],
            '--property=ReadWritePaths=' + guest['data_path'], '--',
            guest['executable']['path'], *guest['executable']['arguments'])
        self.command(authority, argv)
        state = self.systemctl(authority, 'show', unit, properties=('ActiveState', 'SubState', 'MainPID',
            'User', 'Group', 'PrivateNetwork', 'ProtectSystem', 'NoNewPrivileges', 'CapabilityBoundingSet'))
        require(state['ActiveState'] == 'active' and state['SubState'] == 'running'
                and state['User'] == str(guest['uid']) and state['Group'] == str(guest['gid'])
                and state['PrivateNetwork'] == 'yes' and state['ProtectSystem'] == 'strict'
                and state['NoNewPrivileges'] == 'yes' and state['CapabilityBoundingSet'] == ''
                and state['MainPID'].isdigit() and int(state['MainPID']) > 1,
                'The actual transient application lacks its selected isolation or useful running process')
        return unit, state


@dataclass(frozen=True)
class ApplicationHealthReadRuntime:
    """A separately enrolled real guest reader; it has no native write claim."""
    commands: GuestCommandRuntime
    enrollment: NativeReadEnrollment
    writer: LifecycleWorkerRuntime
    writer_guest: ApplicationGuestRuntime
    target: dict
    ssh_runtime: dict
    key: Path | None
    certificate: Path | None
    output_directory: Path
    source_root: Path
    side: str = 'destination'
    recovery: object = None

    def __post_init__(self):
        if self.recovery is not None:
            from .recovery import ApplicationRecoverySelection
            require(type(self.recovery) is ApplicationRecoverySelection and self.side == 'destination',
                'Only an exact independently approved retained-target recovery may select a repair reader')
        require(isinstance(self.commands, GuestCommandRuntime) and isinstance(self.enrollment, NativeReadEnrollment)
                and isinstance(self.writer, LifecycleWorkerRuntime) and self.side in {'source', 'destination'}
                and isinstance(self.writer_guest, ApplicationGuestRuntime) and self.writer_guest.worker is self.writer
                and self.commands.command_runtime is self.enrollment.command
                and self.commands.command_runtime.authority is self.writer.execution_authority,
                'The independent health reader must reuse the actual scoped B10/mTLS enrollment')
        for name in ('key', 'certificate'):
            if getattr(self, name) is not None:
                object.__setattr__(self, name, private_path(getattr(self, name)))
        object.__setattr__(self, 'output_directory', private_path(self.output_directory, directory=True))
        object.__setattr__(self, 'source_root', Path(self.source_root))
        object.__setattr__(self, 'target', deepcopy(self.target))
        object.__setattr__(self, 'ssh_runtime', deepcopy(self.ssh_runtime))

    @property
    def registry(self):
        return self.writer.registry

    def observe(self, admitted, selection, lifecycle, member_id):
        return self._observe(admitted, selection, lifecycle, member_id)

    def observe_initial(self, admitted, selection, lifecycle, member_id):
        require(self.side == 'destination', 'Only the selected target has an initial restore staging read')
        return self._observe(admitted, selection, lifecycle, member_id, initial=True)

    def observe_bootstrap(self, admitted, selection, lifecycle, member_id):
        require(self.side == 'destination' and self.recovery is None,
                'Only the original target has an isolated management bootstrap read')
        selected = lifecycle.member(member_id)['target_management']
        require(self.target['address'] == selected['ipv4_address'] and self.target['port'] == 22
                and self.writer_guest.target['address'] == self.target['address']
                and self.writer_guest.target['port'] == self.target['port']
                and digest(self.target['host_key'].encode()) == selected['ssh_host_key_sha256']
                and self.writer_guest.target['host_key'] == self.target['host_key']
                and self.commands.read_credentials.source_range == selected['worker_ipv4_address'] + '/32',
                'The independent pinned SSH read does not use the selected isolated management path')
        return self._observe(admitted, selection, lifecycle, member_id, bootstrap=True)

    def _observe(self, admitted, selection, lifecycle, member_id, *, initial=False, bootstrap=False):
        authority = self.commands.command_runtime.select_application_reader(admitted, selection, lifecycle,
            member_id, self.source_root, enrollment=self.enrollment, writer=self.writer, side=self.side,
            writer_native_user=self.writer_guest.target['user'], recovery=self.recovery)
        guest = authority.guest
        require((self.target['native_id'], self.target['machine_id']) == (guest['native_id'], guest['machine_id']),
                'The independent health reader names another actual guest')
        require(self.writer_guest.source_root == self.source_root
                and (self.writer_guest.target['native_id'], self.writer_guest.target['machine_id']) ==
                    (guest['native_id'], guest['machine_id']),
                'The separated native reader principal is not bound to this exact original writer guest and code')

        def exchange(arguments, packet=None):
            number = len(list(self.output_directory.glob('read-*'))) + 1
            output = self.output_directory / f'read-{number:05d}'
            output.mkdir(mode=0o700); sync_directory(self.output_directory)
            return self.commands.exchange(authority, target=self.target, binding=authority.binding,
                runtime=self.ssh_runtime, key=None, certificate=None,
                remote_argv=tuple(arguments), input_bytes=b'' if packet is None else encoded(packet), output=output, timeout=30)

        def action(name, parameters):
            packet = dict(format='hosting-application-guest-action/1', job_id=admitted.job_id,
                operation_id=authority.operation_id, selection_sha256=lifecycle.sha256, guest=guest, parameters=parameters)
            raw = exchange(('/usr/bin/sudo', '-n', '--', '/usr/bin/python3', '-I', '-S', '-c', ACTION_BOOTSTRAP,
                encoded(guest['action_runtime']).decode(), name), packet)
            result = strict_loads(raw)
            require(result.get('format') == 'hosting-application-guest-observation/1'
                    and (result.get('action'), result.get('job_id'), result.get('operation_id'), result.get('selection_sha256')) ==
                        (name, admitted.job_id, authority.operation_id, lifecycle.sha256)
                    and result.get('identity') == {'machine_id': guest['machine_id'], 'native_uuid': guest['native_uuid'],
                                                 'image': 'ubuntu-24.04'},
                    'The independent health observation changed its original guest or selected operation')
            return result['observation']

        image = action('IMAGE_OBSERVE', {})
        if bootstrap:
            properties = ('ActiveState', 'SubState', 'UnitFileState', 'MainPID')
            raw = exchange(('/usr/bin/sudo', '-n', '--', '/usr/bin/systemctl', 'show', '--no-pager', guest['unit'],
                            *('--property=' + name for name in properties))).decode('utf-8')
            state = {}
            for line in raw.splitlines():
                key, separator, value = line.partition('=')
                require(separator and key in properties and key not in state,
                        'The bootstrap reader returned a missing or repeated service state')
                state[key] = value
            require(set(state) == set(properties) and state['ActiveState'] == 'inactive'
                    and state['SubState'] == 'dead' and state['UnitFileState'] == 'masked'
                    and state['MainPID'] == '0',
                    'The isolated target already admits a production application writer')
            grant, _ = authority.require_current()
            return dict(format='hosting-independent-application-bootstrap/1', original_job_id=admitted.job_id,
                lifecycle_digest=lifecycle.sha256, member_id=member_id,
                reader_subject=self.commands.command_runtime.identity.subject,
                reader_certificate_digest=self.commands.command_runtime.identity.certificate_sha256,
                read_grant_id=grant.grant_id, read_operation_id=authority.operation_id,
                image=image, service=state, address=self.target['address'], port=self.target['port'],
                ssh_host_key_sha256=digest(self.target['host_key'].encode()), observed_at=utcnow().isoformat())
        if initial:
            data = action('DATA_OBSERVE', dict(path=authority.member['initial_target_path'],
                                              max_bytes=authority.member['max_bytes']))
            grant, _ = authority.require_current()
            return dict(format='hosting-independent-initial-application-data/1',
                original_job_id=admitted.job_id, lifecycle_digest=lifecycle.sha256, member_id=member_id,
                reader_subject=self.commands.command_runtime.identity.subject,
                reader_certificate_digest=self.commands.command_runtime.identity.certificate_sha256,
                read_grant_id=grant.grant_id, read_operation_id=authority.operation_id,
                image=image, data=data['data'], observed_at=utcnow().isoformat())
        properties = ('ActiveState', 'SubState', 'MainPID', 'User', 'Group', 'NoNewPrivileges', 'ProtectSystem')
        raw = exchange(('/usr/bin/sudo', '-n', '--', '/usr/bin/systemctl', 'show', '--no-pager', guest['unit'],
                        *('--property=' + name for name in properties))).decode('utf-8')
        state = {}
        for line in raw.splitlines():
            key, separator, value = line.partition('=')
            require(separator and key in properties and key not in state,
                    'The independent service reader returned an unknown or repeated property')
            state[key] = value
        require(set(state) == set(properties) and state['ActiveState'] == 'active' and state['SubState'] == 'running'
                and state['User'] == str(guest['uid']) and state['Group'] == str(guest['gid'])
                and state['NoNewPrivileges'] == 'yes' and state['ProtectSystem'] == 'strict'
                and state['MainPID'].isdigit() and int(state['MainPID']) > 1,
                'The actual independently read application is not usefully running as the selected unprivileged user')
        health = action('HEALTH_PRODUCTION', dict(main_pid=int(state['MainPID'])))
        grant, _ = authority.require_current()
        return dict(format='hosting-independent-application-health/1', original_job_id=admitted.job_id,
            lifecycle_digest=lifecycle.sha256, member_id=member_id, side=self.side,
            reader_subject=self.commands.command_runtime.identity.subject,
            reader_certificate_digest=self.commands.command_runtime.identity.certificate_sha256,
            read_grant_id=grant.grant_id, read_operation_id=authority.operation_id,
            original_writer_subject=self.writer.identity.subject, image=image, service=state, useful_health=health,
            observed_at=utcnow().isoformat())
