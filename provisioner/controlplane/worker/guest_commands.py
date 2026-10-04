"""Current authority at every actual pinned SSH command and Ansible retry.

The local socket carries digests, not identity, native credentials or authority
claims. Its sole server retains the real original selected command owner. A
dispatched remote effect may still finish after revocation; it never becomes
accepted from the controller's exit code and remains original uncertainty.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
import ipaddress
import json
import os
from pathlib import Path
import re
import shlex
import socket
import stat
import struct
import subprocess
import threading
from uuid import UUID, uuid4

from provisioner.controlplane.persistence.store import NativeBinding
from provisioner.execution import guest_apply, guest_run
from provisioner.execution.guest_command_client import authorize, machine_command as _machine_command
from provisioner.execution.guest_native_profiles import NATIVE_GUEST_PROFILES
from provisioner.execution.run_files import (
    digest, encoded, load_private, private_path, read_private, require,
    sync_directory, utcnow, write_new)
from .command_runtime import (WorkerCommandRuntime, SelectedWorkerCommandAuthority,
    ApplicationWorkerCommandAuthority, ApplicationGuestReadAuthority)

_GUEST_MODULE_FILES = (
    'provisioner/__init__.py', 'provisioner/domain/__init__.py', 'provisioner/domain/errors.py',
    'provisioner/execution/__init__.py', 'provisioner/execution/neutron_observe.py',
    'provisioner/execution/run_files.py',
    'provisioner/execution/restic_run.py',
    'provisioner/migration/resources.py',
    'provisioner/migration/__init__.py', 'provisioner/migration/guest_lifecycle.py')
_MODULE_BOOTSTRAP = '''
import hashlib,importlib.metadata,json,os,pathlib,runpy,stat,sys
manifest=json.loads(sys.argv.pop(1)); module=sys.argv.pop(1)
distribution=importlib.metadata.distribution('hosting-provisioner')
base=pathlib.Path(distribution.locate_file('')).resolve(strict=True)
for name,expected in manifest.items():
    path=base/name
    for parent in (path,*path.parents):
        info=parent.lstat()
        if stat.S_ISLNK(info.st_mode) or info.st_uid!=0 or info.st_mode&0o022:
            raise PermissionError('Deployed guest package custody differs')
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
        raise PermissionError('Deployed guest action source differs')
sys.path.insert(0,str(base)); sys.argv[0]=module
runpy.run_module(module,run_name='__main__',alter_sys=True)
'''


def machine_command(command, target, binding):
    """Check machine identity in the same SSH command before its owned action."""
    return _machine_command(command, target, binding.key())


@dataclass(frozen=True)
class GuestReadCredentialProfile:
    """Commissioned native read CA/principal, supplied by the real enrollment."""
    ssh_ca_public: bytes
    principal: str
    source_range: str

    def __post_init__(self):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        require(type(self.ssh_ca_public) is bytes and len(self.ssh_ca_public) <= 4096
                and isinstance(serialization.load_ssh_public_key(self.ssh_ca_public), Ed25519PublicKey)
                and type(self.principal) is str and self.principal != 'root'
                and re.fullmatch('[a-z_][a-z0-9_-]{0,31}', self.principal)
                and type(self.source_range) is str
                and str(ipaddress.ip_network(self.source_range, strict=True)) == self.source_range,
                'A fixed trusted native read CA, account and exact source network are required')


@dataclass(frozen=True)
class GuestCommandRuntime:
    command_runtime: WorkerCommandRuntime
    read_credentials: GuestReadCredentialProfile | None = None
    _read_serials: set = field(default_factory=set, repr=False, compare=False)
    _read_lock: object = field(default_factory=threading.Lock, repr=False, compare=False)

    def __post_init__(self):
        require(isinstance(self.command_runtime, WorkerCommandRuntime),
                'The actual enrolled per-command worker runtime is required')
        require(self.read_credentials is None or type(self.read_credentials) is GuestReadCredentialProfile,
                'Only a commissioned native guest read credential profile is available')

    def execute_prepared(self, authority, prepared, binding, approval, ledger, root):
        context = GuestExecutionContext(self, authority, prepared, binding, approval, root)
        from argparse import Namespace
        return guest_apply.apply(Namespace(execute=True, bundle=prepared, approval=approval, ledger=ledger),
                                 root=root, guest_context=context)

    def exchange(self, authority, *, target, binding, runtime, key, certificate,
                 remote_argv, input_bytes, output, timeout=60):
        """Owned callers construct fixed argv; no queue JSON chooses a command.

        Output is bounded readback material, never an accepted postcondition.
        The caller owns retained intent, independent observations and recovery.
        """
        require(type(authority) in {SelectedWorkerCommandAuthority,
                    ApplicationWorkerCommandAuthority, ApplicationGuestReadAuthority}
                and authority.runtime is self.command_runtime
                and isinstance(binding, NativeBinding) and type(target) is dict
                and type(remote_argv) is tuple and remote_argv
                and all(type(arg) is str and arg and '\x00' not in arg and len(arg) <= 65536 for arg in remote_argv)
                and type(input_bytes) is bytes and len(input_bytes) <= 16*2**20,
                'One actual selected authority and fixed owned guest argv required')
        if isinstance(authority, ApplicationWorkerCommandAuthority):
            require(authority.intent_guard.claimed is True,
                    'Original application intent must be claimed before any guest contact')
        elif not isinstance(authority, ApplicationGuestReadAuthority):
            from provisioner.migration.provisioning import ObservedProvisioningGuard
            require(authority.runtime.grant.operation_kind == 'GUEST_CONFIG'
                    and authority.step['kind'] == 'guest_apply'
                    and isinstance(authority.intent_guard,ObservedProvisioningGuard)
                    and authority.intent_guard.claimed is True
                    and authority.intent_guard.runtime.lease.binding == binding,
                    'Original guest native mutation must be claimed before remote contact')
        sudo = remote_argv[:3] == ('/usr/bin/sudo','-n','--')
        native_argv = remote_argv[3:] if sudo else remote_argv
        require(native_argv and native_argv[0] in {'/usr/bin/systemctl', '/usr/bin/systemd-run',
            '/usr/bin/nsenter', '/usr/bin/python3', '/usr/bin/restic'},
            'Only the fixed owned guest command families are available')
        if isinstance(authority, ApplicationGuestReadAuthority):
            self._application_read(authority, native_argv, input_bytes, binding)
        if native_argv[0] == '/usr/bin/python3':
            if native_argv[:4] == ('/usr/bin/python3','-I','-S','-c'):
                from provisioner.migration.remote_app import ACTION_BOOTSTRAP
                from provisioner.execution.neutron_observe import strict_loads
                require(isinstance(authority, (ApplicationWorkerCommandAuthority, ApplicationGuestReadAuthority))
                        and len(native_argv) == 7 and native_argv[4] == ACTION_BOOTSTRAP,
                        'Only the concrete original application action bootstrap is available')
                guest = authority.guest
                packet = strict_loads(input_bytes)
                operation_id = (authority.operation_id if isinstance(authority, ApplicationGuestReadAuthority)
                                else authority.intent_guard.row['operation_id'])
                require(strict_loads(native_argv[5].encode()) == guest['action_runtime']
                        and packet['guest'] == guest and packet['job_id'] == authority.admitted.job_id
                        and packet['operation_id'] == operation_id
                        and packet['selection_sha256'] == authority.lifecycle.sha256,
                        'The command changed its original deployed source, interpreter or application inputs')
            else:
                require(native_argv[:5] == ('/usr/bin/python3','-I','-B','-m','provisioner.migration.guest_lifecycle'),
                        'Only the installed source-bound guest lifecycle module may execute Python')
                require(all((authority.root/name).is_file() and not (authority.root/name).is_symlink()
                            for name in _GUEST_MODULE_FILES), 'Actual owned guest lifecycle source required')
                manifest = {name:digest((authority.root/name).read_bytes()) for name in _GUEST_MODULE_FILES}
                native_argv = ('/usr/bin/python3','-I','-B','-c',_MODULE_BOOTSTRAP,
                               json.dumps(manifest,sort_keys=True,separators=(',',':')),
                               'provisioner.migration.guest_lifecycle',*native_argv[5:])
                remote_argv = ('/usr/bin/sudo','-n','--',*native_argv) if sudo else native_argv
        self._target(authority, target, binding)
        directory = private_path(output, directory=True)
        require(guest_run.runtime_record(runtime['python_path'], runtime['ssh_path']) == runtime,
                'The original pinned guest command runtime changed')
        ssh = Path(runtime['ssh_path'])
        require(digest(ssh.read_bytes()) == runtime['ssh_sha256'], 'The actual approved SSH executable changed')
        options = ['BatchMode=yes', 'StrictHostKeyChecking=yes', 'UpdateHostKeys=no',
            'GlobalKnownHostsFile=/dev/null', 'UserKnownHostsFile='+str(directory/'known_hosts'),
            'IdentitiesOnly=yes', 'IdentityAgent=none', 'PasswordAuthentication=no',
            'KbdInteractiveAuthentication=no', 'PubkeyAcceptedAlgorithms=ssh-ed25519-cert-v01@openssh.com',
            'CertificateFile='+str(directory/'ssh_key-cert.pub'), 'ControlMaster=no',
            'ControlPersist=no', 'ControlPath=none', 'ForwardAgent=no', 'ClearAllForwardings=yes',
            'ProxyCommand=none', 'ProxyJump=none', 'ConnectionAttempts=1', 'ConnectTimeout=5', 'RequestTTY=no']
        host, port = target['address'], target['port']
        pins = f'[{host}]:{port} {target["host_key"]}\n'
        if port == 22: pins += f'{host} {target["host_key"]}\n'
        native = binding.key()
        if hasattr(authority,'lifecycle'):
            selected_guest = authority.guest
            require(target['machine_id'] == selected_guest['machine_id'],
                    'Guest transport changed the original application machine')
            native = (*native, selected_guest['native_uuid'])
        command = _machine_command(shlex.join(remote_argv), target, native)
        argv = [str(ssh), '-F', '/dev/null', '-T', '-i', str(directory/'ssh_key'),
                '-p', str(port), '-l', target['user']]
        for option in options: argv += ['-o', option]
        argv += [host, command]
        native_deadline = None
        try:
            if isinstance(authority, ApplicationGuestReadAuthority):
                private_key, public_certificate, native_deadline = self._read_material(authority, target)
                write_new(directory/'ssh_key', private_key)
                write_new(directory/'ssh_key-cert.pub', public_certificate)
            else:
                for name, path in [('ssh_key', key), ('ssh_key-cert.pub', certificate)]:
                    write_new(directory/name, read_private(path))
            write_new(directory/'known_hosts', pins.encode())
            interval = authority.timeout(timeout)
            if native_deadline is not None:
                interval = min(interval, (native_deadline - utcnow()).total_seconds())
                require(interval > 0, 'The fresh native read certificate expired before contact')
            result = _bounded_process(argv, input_bytes, directory, interval)
            authority.require_current()
            require(native_deadline is None or native_deadline > utcnow(),
                    'The native read certificate expired before bounded observation completed')
            require(result == 0,
                    'Remote command has no bounded successful transport result; retain original uncertainty')
            with (directory/'stdout').open('rb') as stream:
                return stream.read(16*2**20 + 1)
        finally:
            (directory/'ssh_key').unlink(missing_ok=True)
            (directory/'ssh_key-cert.pub').unlink(missing_ok=True)
            sync_directory(directory)

    def _read_material(self, authority, target):
        """Consume and verify one fresh native read certificate per contact."""
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        profile = self.read_credentials
        require(type(profile) is GuestReadCredentialProfile
                and target['user'] == profile.principal
                and profile.principal != authority.writer_native_user,
                'A genuinely separate commissioned native guest read account is required')
        material = authority.enrollment.acquire()
        data = material.data
        require(type(data) is dict and set(data) == {'format', 'grant_id', 'lifecycle_sha256',
                'native_binding', 'machine_id', 'user', 'host_key', 'private_key', 'certificate'}
                and data['format'] == 'hosting-application-ssh-read/1'
                and (data['grant_id'], data['lifecycle_sha256'], data['native_binding'],
                     data['machine_id'], data['user'], data['host_key']) ==
                (authority.runtime.grant.grant_id, authority.lifecycle.sha256, list(authority.binding.key()),
                 authority.guest['machine_id'], profile.principal, target['host_key'])
                and all(type(data[name]) is str and 1 <= len(data[name]) <= 16384
                        for name in ('private_key', 'certificate')),
                'The fresh read credential changed its original grant, host, native guest or descriptor')
        private_key = data['private_key'].encode('ascii')
        public_certificate = data['certificate'].encode('ascii')
        native_key = serialization.load_ssh_private_key(private_key, password=None)
        certificate = serialization.load_ssh_public_identity(public_certificate)
        public = lambda value: value.public_bytes(serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH)
        require(isinstance(native_key, Ed25519PrivateKey)
                and isinstance(certificate, serialization.SSHCertificate)
                and public(certificate.public_key()) == public(native_key.public_key())
                and public(certificate.signature_key()) == public(serialization.load_ssh_public_key(profile.ssh_ca_public))
                and certificate.type == serialization.SSHCertificateType.USER
                and certificate.key_id == ('hosting-read:' + authority.runtime.grant.grant_id + ':'
                    + authority.admitted.job_id + ':' + authority.lifecycle.sha256).encode('ascii')
                and certificate.valid_principals == [profile.principal.encode('ascii')]
                and certificate.critical_options == {b'source-address': profile.source_range.encode('ascii')}
                and certificate.extensions == {}
                and certificate.valid_after <= utcnow().timestamp() < certificate.valid_before
                and certificate.valid_before <= material.expires_at.timestamp(),
                'The native read certificate trust, identity, scope or lifetime differs')
        certificate.verify_cert_signature()
        with self._read_lock:
            require(certificate.serial not in self._read_serials and len(self._read_serials) < 4096,
                    'The native read certificate replay state differs')
            self._read_serials.add(certificate.serial)
        authority.require_current()
        from datetime import datetime, timezone
        return private_key, public_certificate, datetime.fromtimestamp(certificate.valid_before, timezone.utc)

    @staticmethod
    def _application_read(authority, argv, input_bytes, binding):
        """A read enrollment never dispatches a write-capable command family."""
        require(binding == authority.binding, 'Independent read changed its original native guest binding')
        if argv[0] == '/usr/bin/systemctl':
            properties = {'ActiveState', 'SubState', 'UnitFileState', 'MainPID', 'User', 'Group',
                'FragmentPath', 'ExecStart', 'NoNewPrivileges', 'ProtectSystem'}
            require(argv[:4] == ('/usr/bin/systemctl', 'show', '--no-pager', authority.guest['unit'])
                    and 5 <= len(argv) <= 4 + len(properties) and input_bytes == b''
                    and len(set(argv[4:])) == len(argv[4:])
                    and all(value.startswith('--property=') and value[11:] in properties for value in argv[4:]),
                    'Independent application reader may only show selected production service properties')
            return
        from provisioner.migration.remote_app import ACTION_BOOTSTRAP
        from provisioner.execution.neutron_observe import strict_loads
        require(argv[:4] == ('/usr/bin/python3', '-I', '-S', '-c') and len(argv) == 7
                and argv[4] == ACTION_BOOTSTRAP and argv[6] in {'IMAGE_OBSERVE', 'HEALTH_PRODUCTION', 'DATA_OBSERVE'}
                and len(input_bytes) <= 2**20,
                'Independent application reader may only run fixed image and useful health observations')
        packet = strict_loads(input_bytes)
        require(type(packet) is dict and set(packet) ==
                {'format', 'job_id', 'operation_id', 'selection_sha256', 'guest', 'parameters'}
                and packet['format'] == 'hosting-application-guest-action/1'
                and (packet['job_id'], packet['operation_id'], packet['selection_sha256']) ==
                (authority.admitted.job_id, authority.operation_id, authority.lifecycle.sha256)
                and packet['guest'] == authority.guest,
                'Independent application read changed its original operation, resource or input')
        parameters = packet['parameters']
        require((argv[6] == 'IMAGE_OBSERVE' and parameters == {}) or
                (argv[6] == 'DATA_OBSERVE' and authority.side == 'destination'
                 and parameters == {'path':authority.member['initial_target_path'],
                                    'max_bytes':authority.member['max_bytes']}) or
                (argv[6] == 'HEALTH_PRODUCTION' and type(parameters) is dict
                 and set(parameters) == {'main_pid'} and type(parameters['main_pid']) is int
                 and 1 < parameters['main_pid'] < 2**31),
                'Only the actual bounded production process observation is permitted')


    @staticmethod
    def _target(authority, target, binding):
        grant, _deadline = authority.require_current()
        require((binding.platform_family, binding.endpoint_id, binding.native_scope_id) ==
                (grant.operation_scope.platform_family, grant.operation_scope.endpoint_id,
                 grant.operation_scope.native_scope_id)
                and binding.resource_kind == 'vm' and target['native_id'] == binding.native_id,
                'Guest command changed its actual native resource or granted scope')
        # Reuse the existing exact handoff validator, including pinned host keys,
        # machine identity, native resource identity and non-root SSH account.
        from provisioner.execution.guest_inventory import build
        scope = authority.selection['executionScope'] | {'phase': 'workloads'}
        if grant.operation_scope != grant.destination:
            scope |= {'platform': grant.operation_scope.platform_family,
                      'site_key': grant.operation_scope.site_id,
                      'tenant_key': grant.operation_scope.tenant_id,
                      'wsd_key': grant.operation_scope.security_domain_id}
        access = {'format': 'hosting-guest-access/1', 'scope': scope,
                  'valid_until': (grant.expires_at).isoformat(), 'change_ref': 'original-command',
                  'targets': {'owned-guest': target}}
        member = {NATIVE_GUEST_PROFILES[binding.platform_family]['member_identity']: binding.native_id}
        from provisioner.compiler.wsd import STATE
        member['delivery_state'] = STATE
        build({'scope': {'value': scope}, 'delivery_state': {'value': STATE},
               'members': {'value': {'owned-guest': member}}}, access, '/owned-command/known_hosts')


def _bounded_process(argv, input_bytes, directory, timeout):
    """Bound memory and stop the original SSH process on output overflow."""
    exceeded = threading.Event()
    stop = threading.Event()
    with os.fdopen(os.open(directory/'stdout', os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'wb') as out, \
         os.fdopen(os.open(directory/'stderr', os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'wb') as err:
        with subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=out, stderr=err,
                env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'}, umask=0o077) as process:
            def monitor():
                while not stop.wait(.01):
                    if ((directory/'stdout').stat().st_size > 16*2**20
                            or (directory/'stderr').stat().st_size > 65536):
                        exceeded.set()
                        try: process.kill()
                        except ProcessLookupError: pass
                        return
            watcher = threading.Thread(target=monitor, name='bounded-guest-output', daemon=True)
            watcher.start()
            try:
                process.communicate(input=input_bytes, timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill(); process.communicate()
                raise
            finally:
                stop.set(); watcher.join(timeout=1)
            require(not exceeded.is_set() and os.fstat(out.fileno()).st_size <= 16*2**20
                    and os.fstat(err.fileno()).st_size <= 65536,
                    'Remote output exceeded its bound; retain original uncertainty')
            return process.returncode



class GuestExecutionContext:
    """One prepared Linux bundle and one private live per-command listener."""
    def __init__(self, runtime, authority, prepared, binding, approval, root):
        from provisioner.migration.provisioning import ObservedProvisioningGuard
        require(isinstance(runtime, GuestCommandRuntime)
                and isinstance(authority, SelectedWorkerCommandAuthority)
                and authority.runtime is runtime.command_runtime
                and authority.runtime.grant.operation_kind == 'GUEST_CONFIG'
                and authority.step['kind'] == 'guest_apply'
                and isinstance(authority.intent_guard,ObservedProvisioningGuard)
                and authority.intent_guard.claimed is True
                and authority.intent_guard.runtime.lease.binding == binding,
                'Concrete original selected guest configuration authority required')
        self.runtime, self.authority = runtime, authority
        self.prepared, self.approval, self.root = private_path(prepared, directory=True), Path(approval), root
        self.binding = binding
        self.bundle_digest = digest(read_private(self.prepared/'bundle.json'))
        self.require_current()

    def require_current(self):
        self.authority.require_current()
        require(digest(read_private(self.prepared/'bundle.json')) == self.bundle_digest,
                'The originally selected guest bundle changed')
        bundle, access, runtime = guest_apply.validate_bundle(self.prepared, load_private(self.approval), self.root)
        require(len(access['targets']) == 1 and bundle['operation_id'] == self.authority.runtime.grant.operation_id,
                'One original VM operation cannot configure another guest bundle')
        require(bundle['scope'] == self.authority.selection['executionScope'] | {'phase':'workloads'}
                and bundle['source_commit'] == self.authority.selection['sourceCommit'],
                'The guest bundle differs from its original selected application scope or source')
        self.target = next(iter(access['targets'].values()))
        self.runtime._target(self.authority, self.target, self.binding)
        return bundle, access, runtime

    @contextmanager
    def controller(self, runtime):
        self.require_current()
        folder = self.prepared/'runtime'/('command-'+uuid4().hex)
        folder.mkdir(mode=0o700); sync_directory(folder.parent)
        path = folder/'authority.sock'
        require(len(str(path).encode()) <= 107, 'Choose a shorter private guest bundle path for its Unix socket')
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(path)); path.chmod(0o600); server.listen(2); server.settimeout(.2)
        stop = threading.Event(); seen = set()
        binding = {'bundle': self.bundle_digest, 'selection': self.authority.selection_digest,
                   'job': self.authority.admitted.job_id, 'step': self.authority.step['id'],
                   'grant': self.authority.runtime.grant.grant_id, 'target': self.target,
                   'native': self.binding.key()}
        session = {'socket': str(path), 'binding_digest': digest(encoded(binding)),
                   'target': self.target, 'native': self.binding.key(), 'ssh': runtime['ssh_path']}
        session_path = folder/'session.json'; write_new(session_path, encoded(session))
        session_digest = digest(read_private(session_path))
        def listen():
            while not stop.is_set():
                try: peer, _address = server.accept()
                except TimeoutError: continue
                except OSError: break
                with peer:
                    peer.settimeout(2)
                    try:
                        _pid, uid, _gid = struct.unpack('3i', peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                        require(uid == os.geteuid(), 'Guest command client belongs to another actual UID')
                        raw = bytearray()
                        while True:
                            chunk = peer.recv(1024)
                            if not chunk: break
                            raw.extend(chunk); require(len(raw) <= 2048, 'Guest command check exceeds its bound')
                        require(raw.endswith(b'\n'), 'A complete bounded command request is required')
                        request = json.loads(raw)
                        require(type(request) is dict and request.keys() == {'format', 'request_id',
                            'binding_digest', 'command_digest', 'input_digest'}
                            and request['format'] == 'hosting-guest-command-check/1'
                            and request['binding_digest'] == session['binding_digest']
                            and re.fullmatch('[0-9a-f]{32}', request['request_id'])
                            and request['request_id'] not in seen and len(seen) < 4096
                            and all(re.fullmatch('[0-9a-f]{64}', request[name]) for name in ('command_digest', 'input_digest')),
                            'Guest command changed or replayed its original bound request')
                        require(digest(read_private(session_path)) == session_digest,
                                'The original process-local guest session was replaced')
                        seen.add(request['request_id']); self.require_current()
                        require(not stop.is_set(), 'The original guest controller has stopped')
                        response = {'status': 'CURRENT_ORIGINAL_COMMAND', 'request_digest': digest(bytes(raw).rstrip(b'\n'))}
                    except Exception:
                        response = {'status': 'HELD', 'request_digest': ''}
                    try: peer.sendall(encoded(response))
                    except OSError: pass
        thread = threading.Thread(target=listen, name='original-guest-command-authority', daemon=True)
        thread.start()
        inventory = load_private(self.prepared/'inventory.json')
        for host in inventory['all']['children']['hosting_guests']['hosts'].values():
            host['ansible_connection'] = 'hosting_guarded_ssh'
        write_new(folder/'inventory.json', encoded(inventory))
        config = guest_run.configuration(self.prepared, runtime['ssh_path'])
        config = config.replace(b'[defaults]\n', b'[defaults]\nconnection_plugins = '+
            str(self.prepared/'source/ansible/connection_plugins').encode()+b'\n')
        write_new(folder/'ansible.cfg', config)
        try:
            yield {'inventory': folder/'inventory.json', 'configuration': folder/'ansible.cfg',
                   'session': session_path}
            self.require_current()
        finally:
            stop.set(); server.close(); thread.join(timeout=3)
            path.unlink(missing_ok=True); sync_directory(folder)
