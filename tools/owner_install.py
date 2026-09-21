#!/usr/bin/env python3
"""Install a dedicated certificate-only worker endpoint on an accepted Ubuntu host.

Initial installation and exact interrupted-install resume only. Existing source,
account and credentials are selected private inputs; no package download, account
creation, SSH management rewrite or job dispatch is performed.
"""
import argparse
import base64
import fcntl
import ipaddress
import json
import os
from pathlib import Path
import pwd
import re
import stat
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ''): sys.path.insert(0, str(ROOT))
from tools import readback_core as c
from tools.check_release import verify
from tools.run_files import (current_window, digest, encoded, load_private, private_path,
                             read_private, require, sync_directory, utcnow, write_new)

SERVICE = 'hosting-owner.service'
CONFIG = Path('/etc/hosting-owner')
UNIT = Path('/etc/systemd/system') / SERVICE
STATE = Path('/var/lib/hosting-owner-install')
TMPFILES = Path('/etc/tmpfiles.d/hosting-owner.conf')


def installed_path(value):
    require(isinstance(value, str) and re.fullmatch(r'/[A-Za-z0-9_./-]+', value)
            and '..' not in Path(value).parts and str(Path(value)) == value, 'Simple absolute installed path required')
    return Path(value)


def public_key(value):
    require(isinstance(value, str) and len(value.split()) == 2 and value.split()[0] == 'ssh-ed25519'
            and value == ' '.join(value.split()), 'One exact Ed25519 public key required')
    raw = base64.b64decode(value.split()[1], validate=True)
    require(len(raw) == 51 and raw[:19] == b'\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20', 'Invalid Ed25519 key encoding')


def validate(config):
    c.exact_keys(config, {'format', 'source_commit', 'machine_id', 'account', 'uid', 'gid',
        'listen_address', 'port', 'principal', 'source', 'python', 'python_sha256', 'sshd', 'sshd_sha256',
        'systemctl', 'systemctl_sha256', 'ssh_keygen', 'ssh_keygen_sha256', 'host_private', 'host_public',
        'user_ca', 'data_directory', 'ledger_mode', 'custody_ref'})
    require(config['format'] == 'hosting-owner-install/1'
            and isinstance(config['source_commit'], str) and re.fullmatch('[0-9a-f]{40}', config['source_commit'])
            and isinstance(config['machine_id'], str) and re.fullmatch('[0-9a-f]{32}', config['machine_id']),
            'Exact worker source and machine required')
    require(isinstance(config['account'], str) and re.fullmatch('[a-z_][a-z0-9_-]{0,31}', config['account']),
            'Exact worker account required')
    require(all(type(config[key]) is int and config[key] >= 0 for key in ('uid', 'gid')), 'Exact worker UID/GID required')
    require(isinstance(config['principal'], str) and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', config['principal']),
            'One exact SSH certificate principal required')
    address = ipaddress.ip_address(config['listen_address'])
    require(address.version == 4 and str(address) == config['listen_address']
            and not address.is_unspecified and not address.is_multicast and not address.is_link_local,
            'One exact internal IPv4 listener required')
    require(type(config['port']) is int and 1024 <= config['port'] <= 65535, 'Dedicated non-management SSH port required')
    for key in ('source', 'python', 'sshd', 'systemctl', 'ssh_keygen', 'data_directory'): installed_path(config[key])
    require(Path(config['data_directory']).parent == Path('/var/lib')
            and Path(config['data_directory']).name.startswith('hosting-owner-')
            and Path(config['data_directory']) != STATE, 'Dedicated worker state directory required')
    for key in ('python', 'sshd', 'systemctl', 'ssh_keygen'):
        require(isinstance(config[key+'_sha256'], str) and re.fullmatch('[0-9a-f]{64}', config[key+'_sha256']),
                'Exact installed executable digest required')
    c.exact_keys(config['host_private'], {'path', 'sha256'}); installed_path(config['host_private']['path'])
    require(isinstance(config['host_private']['sha256'], str) and re.fullmatch('[0-9a-f]{64}', config['host_private']['sha256']),
            'Exact private host-key binding required')
    public_key(config['host_public']); public_key(config['user_ca'])
    require(config['host_public'] != config['user_ca'], 'Host and user-signing keys must be separate')
    require(config['ledger_mode'] in {'new', 'retained'}, 'Explicit new or retained ledger selection required')
    c.text(config['custody_ref'])


def authorize(config, authority):
    c.exact_keys(authority, {'format', 'config_sha256', 'valid_from', 'valid_until', 'change_ref', 'recovery_access_ref'})
    require(authority['format'] == 'hosting-owner-install-authority/1' and authority['config_sha256'] == c.digest(config),
            'Exact worker installation authority required')
    current_window(authority)
    for name in ('change_ref', 'recovery_access_ref'): c.text(authority[name])


def service_files(config, *, config_directory=CONFIG, data_directory=None, runtime_directory=Path('/run/hosting-owner')):
    """Render the same fixed daemon profile for installation and real SSH labs."""
    validate(config); directory = installed_path(str(config_directory))
    data = installed_path(str(data_directory or config['data_directory']))
    runtime = installed_path(str(runtime_directory))
    forced = f"{config['python']} -I {config['source']}/tools/owner_worker.py --spool {data}/spool --ledger {data}/ledger"
    daemon = '\n'.join([f"Port {config['port']}", f"ListenAddress {config['listen_address']}", 'AddressFamily inet',
        f'HostKey {directory}/host-key', 'HostKeyAlgorithms ssh-ed25519', f'PidFile {runtime}/sshd.pid',
        'UsePAM yes', 'AuthenticationMethods publickey', 'PubkeyAuthentication yes', 'PasswordAuthentication no',
        'KbdInteractiveAuthentication no', 'PermitEmptyPasswords no', 'HostbasedAuthentication no', 'GSSAPIAuthentication no',
        'PermitRootLogin '+('prohibit-password' if config['uid'] == 0 else 'no'), 'AuthorizedKeysFile none',
        'AuthorizedKeysCommand none', 'AuthorizedPrincipalsCommand none', f'TrustedUserCAKeys {directory}/user-ca.pub',
        f'AuthorizedPrincipalsFile {directory}/principals', 'CASignatureAlgorithms ssh-ed25519',
        'PubkeyAcceptedAlgorithms ssh-ed25519-cert-v01@openssh.com', f"AllowUsers {config['account']}",
        'AllowAgentForwarding no', 'AllowTcpForwarding no', 'AllowStreamLocalForwarding no', 'DisableForwarding yes',
        'PermitTunnel no', 'X11Forwarding no', 'PermitTTY no', 'PermitUserRC no', 'PermitUserEnvironment no',
        'MaxAuthTries 3', 'MaxSessions 1', 'LoginGraceTime 30', 'StrictModes yes', 'LogLevel VERBOSE',
        'SetEnv GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0='+config['source'],
        'ForceCommand '+forced, ''])
    service = '\n'.join(['[Unit]', 'Description=Scoped hosting owner certificate SSH endpoint',
        'Wants=network-online.target', 'After=network-online.target systemd-tmpfiles-setup.service',
        'ConditionPathExists='+str(directory/'sshd_config'), '', '[Service]',
        'Type=exec', 'UMask=0077', 'RuntimeDirectory=hosting-owner', 'RuntimeDirectoryMode=0755',
        f"ExecStartPre={config['sshd']} -t -f {directory}/sshd_config",
        f"ExecStart={config['sshd']} -D -e -f {directory}/sshd_config", 'Restart=no',
        # A management service stop is not native job cancellation/fencing.
        'KillMode=process', 'TimeoutStopSec=15', 'ProtectSystem=full', 'ProtectHome=read-only',
        '', '[Install]', 'WantedBy=multi-user.target', ''])
    return {'sshd_config': daemon.encode(), 'user-ca.pub': (config['user_ca']+'\n').encode(),
            'principals': (config['principal']+'\n').encode(), SERVICE: service.encode(),
            'hosting-owner.tmpfiles': b'd /run/sshd 0755 root root -\n'}


class Host:
    """Fixed host operations; a filesystem prefix is used only by local tests."""
    def __init__(self, prefix=Path('/'), *, custodian_uid=0, custodian_gid=0):
        self.prefix, self.custodian_uid, self.custodian_gid = Path(prefix), custodian_uid, custodian_gid
    def path(self, path): return self.prefix / Path(path).relative_to('/')

    def command(self, argv):
        result = subprocess.run(list(map(str, argv)), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C.UTF-8'}, timeout=60)
        require(result.returncode == 0, 'Host command failed; installation remains held')
        require(len(result.stdout) <= 1024*1024, 'Unexpected host command output')
        return result.stdout.decode().strip()

    def identity(self, config, root):
        require(os.geteuid() == 0, 'Worker endpoint installation requires the accepted local root operator')
        release = dict(line.split('=',1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)
        require(release.get('ID','').strip('"') == 'ubuntu' and release.get('VERSION_ID','').strip('"') == '24.04'
                and Path('/run/systemd/system').is_dir(), 'Accepted Ubuntu 24.04 systemd host required')
        require(Path('/etc/machine-id').read_text().strip() == config['machine_id'], 'Wrong worker host')
        account = pwd.getpwnam(config['account'])
        require((account.pw_uid,account.pw_gid) == (config['uid'],config['gid'])
                and account.pw_shell in {'/bin/bash','/bin/sh','/usr/bin/bash','/usr/bin/sh'}, 'Worker account identity or shell differs')
        require(Path(config['source']) == root, 'Installation source differs from executing checkout')
        source = verify(root)
        require(source['status'] == 'HASHES_MATCH' and source['commit'] == config['source_commit'], 'Worker source changed')
        # The privileged forced command must not execute another account's mutable source.
        for path in [root, *root.parents, *root.rglob('*')]:
            require(not path.is_symlink(), 'Installed source symlinks are unsupported')
            info = path.stat()
            require(info.st_uid == 0 and not stat.S_IMODE(info.st_mode) & 0o022, 'Worker source must be root-controlled')
        for key in ('python', 'sshd', 'systemctl', 'ssh_keygen'):
            path = Path(config[key]); info = path.stat()
            require(path.is_file() and os.access(path,os.X_OK) and info.st_uid == 0
                    and not stat.S_IMODE(info.st_mode) & 0o022 and digest(path.read_bytes()) == config[key+'_sha256'],
                    'Worker executable changed or is not root-controlled')
            for parent in {*path.parents,*path.resolve(strict=True).parents}:
                info = parent.stat()
                require(info.st_uid == 0 and not stat.S_IMODE(info.st_mode) & 0o022,
                        'Worker executable location is not root-controlled')

    def directory(self, path, uid=None, gid=None, mode=0o700, *, create=True):
        uid = self.custodian_uid if uid is None else uid
        gid = self.custodian_gid if gid is None else gid
        path = self.path(path)
        require(not any(p.is_symlink() for p in (path,*path.parents)), 'Symlink in worker installation path')
        if not path.exists():
            require(create, 'Retained worker state is missing; recover custody before installation')
            path.mkdir(mode=mode); os.chown(path,uid,gid); sync_directory(path.parent)
        info = path.stat()
        require(path.is_dir() and (info.st_uid,info.st_gid,stat.S_IMODE(info.st_mode)) == (uid,gid,mode),
                'Worker directory ownership or mode differs')
        return path

    def file(self, path, data, mode):
        path = self.path(path)
        require(not any(p.is_symlink() for p in (path,*path.parents)), 'Symlink in worker installation file')
        if path.exists():
            info = path.stat()
            require(path.is_file() and info.st_uid == self.custodian_uid and info.st_gid == self.custodian_gid
                    and stat.S_IMODE(info.st_mode) == mode
                    and path.read_bytes() == data, 'Existing worker file changed; maintenance reconciliation required')
            return
        # Atomic publication leaves either the exact complete file or no destination.
        fd, name = tempfile.mkstemp(prefix='.install-', dir=path.parent)
        try:
            with os.fdopen(fd,'wb') as stream:
                stream.write(data); stream.flush(); os.fchmod(stream.fileno(),mode); os.fsync(stream.fileno())
            os.link(name,path,follow_symlinks=False); sync_directory(path.parent)
        finally: Path(name).unlink(missing_ok=True)


def install(config, authority, *, host=None, root=ROOT):
    validate(config); authorize(config,authority); host = host or Host(); host.identity(config,root)
    key = read_private(config['host_private']['path'])
    require(digest(key) == config['host_private']['sha256'], 'Private worker host key changed')
    # OpenSSH may retain the key's trailing comment in -y output. Compare only
    # the exact public algorithm/material; comments do not define host identity.
    observed_key = ' '.join(host.command([config['ssh_keygen'],'-y','-f',config['host_private']['path']]).split()[:2])
    require(observed_key == config['host_public'], 'Private worker host key does not match its accepted public identity')
    files = service_files(config); files['host-key'] = key
    state = host.directory(STATE)
    fd = os.open(state/'writer.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        private_path(state/'writer.lock'); fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        intent = state/'intent.json'; binding = {'format':'hosting-owner-install-intent/1','config':config,
            'files':{name:digest(raw) for name,raw in files.items()}}
        if intent.exists(): require(load_private(intent) == binding, 'Another installation owns this endpoint')
        else:
            require(not any(host.path(path).exists() for path in (CONFIG,UNIT,TMPFILES)), 'Unmanaged endpoint cannot be adopted implicitly')
            if config['ledger_mode'] == 'new':
                require(not host.path(config['data_directory']).exists(), 'New worker state already exists; choose retained custody explicitly')
            write_new(intent,encoded(binding))
        # A malformed daemon candidate cannot partially install a live endpoint.
        candidate = state/'candidate'
        host.directory(STATE/'candidate', mode=0o755)
        staged = service_files(config,config_directory=candidate); staged['host-key'] = key
        for name,raw in staged.items(): host.file(STATE/'candidate'/name,raw,0o600 if name in {'sshd_config','host-key'} else 0o644)
        host.directory(Path('/run/sshd'),mode=0o755)
        host.command([config['sshd'],'-t','-f',candidate/'sshd_config'])
        current_window(authority)
        host.directory(CONFIG,mode=0o755)
        data = Path(config['data_directory'])
        for path in (data,data/'spool',data/'ledger'):
            host.directory(path,config['uid'],config['gid'],create=config['ledger_mode'] == 'new')
        for name,raw in files.items():
            host.file(UNIT if name == SERVICE else TMPFILES if name == 'hosting-owner.tmpfiles' else CONFIG/name,raw,
                      0o600 if name in {'host-key','sshd_config'} else 0o644)
        host.command([config['sshd'],'-t','-f',host.path(CONFIG/'sshd_config')])
        current_window(authority)
        host.command([config['systemctl'],'daemon-reload'])
        fragment = host.command([config['systemctl'],'show',SERVICE,'--property=FragmentPath','--value'])
        dropins = host.command([config['systemctl'],'show',SERVICE,'--property=DropInPaths','--value'])
        require(fragment == str(host.path(UNIT)) and not dropins, 'Loaded worker service differs from the exact installed unit')
        host.command([config['systemctl'],'enable',SERVICE]); current_window(authority)
        host.command([config['systemctl'],'start',SERVICE])
        require(host.command([config['systemctl'],'is-active',SERVICE]) == 'active'
                and host.command([config['systemctl'],'is-enabled',SERVICE]) == 'enabled', 'Worker service did not become active and enabled')
        current_window(authority)
        result = {'format':'hosting-owner-install-receipt/1','status':'WORKER_INSTALLED_REQUIRES_ENDPOINT_ACCEPTANCE',
            'config_sha256':c.digest(config),'authority_sha256':c.digest(authority),'machine_id':config['machine_id'],
            'host_public':config['host_public'],'observed_at':utcnow().isoformat(),
            'native_acceptance':False,'production_activation':False}
        # Keep every installation observation; restart/resume never clears the owner ledger.
        write_new(state/('receipt-'+digest(encoded(result))+'.json'),encoded(result)); return result
    finally: os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True); parser.add_argument('--authority',type=Path)
    parser.add_argument('--execute',action='store_true'); args = parser.parse_args()
    try:
        config = load_private(args.config); validate(config)
        if not args.execute: print('{"status":"VALIDATED_NO_HOST_CHANGE"}'); return 0
        require(args.authority is not None,'Exact worker installation authority required')
        result = install(config,load_private(args.authority)); print(json.dumps({'status':result['status']})); return 0
    except Exception:
        print('{"status":"WORKER_INSTALLATION_HELD","reason":"Inspect private installation and owner records; preserve existing management and native jobs"}')
        return 2


if __name__ == '__main__': raise SystemExit(main())
