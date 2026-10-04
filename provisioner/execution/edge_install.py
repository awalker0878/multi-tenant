#!/usr/bin/env python3
"""Install exact startup denial during accepted offline network maintenance."""
import argparse
from contextlib import ExitStack
from copy import deepcopy
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import sys

from hosting_resources import SOURCE_ROOT
ROOT = SOURCE_ROOT
from provisioner.execution import readback_core as c
from provisioner.execution import edge_boot as boot
from provisioner.execution import edge_contain
from provisioner.execution import nft_edge as edge
from provisioner.execution import owner_install as files
from provisioner.execution.source_integrity import verify, verify_runtime
from provisioner.execution.run_files import (current_window, digest, encoded, load_private, new_directory,
    private_path, require, utcnow, write_new)

SERVICE = 'hosting-edge-boot.service'
CONFIG = Path('/etc/hosting-edge-boot')
STATE = Path('/var/lib/hosting-edge-boot-install')
OUTPUT = Path('/var/lib/hosting-edge-boot')
UNIT = Path('/etc/systemd/system')/SERVICE


def dropin(config):
    return Path('/etc/systemd/system')/(config['manager']+'.d')/'hosting-edge-boot.conf'


def binding(value):
    c.exact_keys(value, {'path', 'sha256'}); files.installed_path(value['path'])
    require(isinstance(value['sha256'], str) and c.HEX.fullmatch(value['sha256']), 'Exact installed artifact digest required')


def validate(config):
    c.exact_keys(config, {'format', 'source', 'python', 'python_sha256',
        'systemctl', 'systemctl_sha256', 'systemd_analyze', 'systemd_analyze_sha256',
        'manager', 'manager_unit', 'manager_dropins', 'boot', 'custody_ref'})
    require(config['format'] == 'hosting-edge-install/1', 'Exact edge installation profile required')
    for name in ('source', 'python', 'systemctl', 'systemd_analyze'): files.installed_path(config[name])
    for name in ('python', 'systemctl', 'systemd_analyze'):
        require(isinstance(config[name+'_sha256'], str) and c.HEX.fullmatch(config[name+'_sha256']), 'Exact host executable required')
    require(config['manager'] in {'systemd-networkd.service', 'NetworkManager.service'}, 'Select actual network manager')
    binding(config['manager_unit'])
    require(Path(config['manager_unit']['path']).name == config['manager'], 'Exact manager unit filename required')
    require(isinstance(config['manager_dropins'], list) and len(config['manager_dropins']) <= 32, 'Bounded accepted manager overrides required')
    for value in config['manager_dropins']: binding(value)
    paths = [value['path'] for value in config['manager_dropins']]
    require(paths == sorted(set(paths)) and str(dropin(config)) not in paths, 'Unique preexisting manager drop-ins required')
    c.text(config['custody_ref'])
    specs = boot.validate(config['boot'])
    for value in (config['source'], config['python'], config['boot']['ledger'], config['boot']['nft']):
        path = files.installed_path(value)
        require(not any(path.is_relative_to(parent) for parent in (Path('/home'), Path('/root'), Path('/tmp'), Path('/run'))),
                'Boot dependencies must survive without home, temporary or runtime storage')
    require(not any(Path(config['boot']['ledger']).is_relative_to(parent) for parent in (CONFIG, STATE, OUTPUT)),
            'Retain the separately owned native edge ledger')
    return specs


def authorize(config, authority):
    c.exact_keys(authority, {'format', 'config_sha256', 'valid_from', 'valid_until', 'change_ref', 'maintenance_ref', 'recovery_access_ref'})
    require(authority['format'] == 'hosting-edge-install-authority/1' and authority['config_sha256'] == c.digest(config),
            'Exact edge installation authority required')
    current_window(authority)
    for name in ('change_ref', 'maintenance_ref', 'recovery_access_ref'): c.text(authority[name])


def installed_files(config):
    """Copy accepted boundaries into durable startup custody; keep native ledger."""
    specs = validate(config); installed = deepcopy(config['boot']); installed['specs'] = []; result = {}
    for number, spec in enumerate(specs):
        path = CONFIG/f'boundary-{number:03d}.json'; raw = encoded(spec); result[path] = (raw, 0o600)
        installed['specs'].append({'path': str(path), 'sha256': digest(raw)})
    result[CONFIG/'boot.json'] = (encoded(installed), 0o600)
    units = boot.service_files(config['python'], config['source'], str(CONFIG/'boot.json'), str(OUTPUT),
                              installed['ledger'], config['manager'])
    result[UNIT] = (units[SERVICE].encode(), 0o644)
    result[dropin(config)] = (units['network-manager.conf'].encode(), 0o644)
    return installed, result


class Host(files.Host):
    def controlled(self, path, sha):
        path = Path(path)
        require(path.is_file() and digest(path.read_bytes()) == sha, 'Accepted host artifact changed')
        for value in {path, path.resolve(strict=True), *path.parents, *path.resolve(strict=True).parents}:
            info = value.stat()
            require(info.st_uid == 0 and not stat.S_IMODE(info.st_mode) & 0o022, 'Host artifact location must be root-controlled')

    def identity(self, config, root):
        require(os.getuid() == os.geteuid() == 0 and Path('/run/systemd/system').is_dir(), 'Accepted root systemd installer required')
        release = dict(line.split('=',1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)
        require(release.get('ID','').strip('"') == 'ubuntu' and release.get('VERSION_ID','').strip('"') == '24.04',
                'Accepted Ubuntu 24.04 edge host required')
        require(Path('/etc/machine-id').read_text().strip() == config['boot']['machine_id']
                and os.stat('/proc/self/ns/net').st_ino == os.stat('/proc/1/ns/net').st_ino == config['boot']['network_namespace_inode'],
                'Wrong edge machine or system network namespace')
        require(root == Path(config['source']), 'Installed guard source differs')
        require(isinstance(root,Path) and verify_runtime(root)['status']=='RUNTIME_SOURCES_MATCH',
                'Exact runtime and explicitly selected source checkout required')
        source = verify(root)
        require(source['status'] == 'HASHES_MATCH' and source['commit'] == config['boot']['source_commit'], 'Installed guard source changed')
        for path in [root, *root.parents, *root.rglob('*')]:
            require(not path.is_symlink(), 'Installed guard source symlinks unsupported')
            info = path.stat()
            require(info.st_uid == 0 and not stat.S_IMODE(info.st_mode) & 0o022, 'Installed source must remain root-controlled')
        for name in ('python', 'systemctl', 'systemd_analyze'):
            self.controlled(config[name], config[name+'_sha256']); require(os.access(config[name], os.X_OK), 'Host executable required')
        self.controlled(config['boot']['nft'], config['boot']['nft_sha256'])
        for value in [config['manager_unit'], *config['manager_dropins']]: self.controlled(value['path'], value['sha256'])
        from provisioner.execution.runtime_build import verify_application
        verify_application(config['python'],root,self.command)

    def property(self, config, service, name):
        return self.command([config['systemctl'], 'show', service, '--property='+name, '--value'])

    def manager(self, config, *, installed=False):
        unit = config['manager']
        require(self.property(config, unit, 'LoadState') == 'loaded'
                and self.property(config, unit, 'FragmentPath') == config['manager_unit']['path'], 'Loaded network manager differs')
        expected = [row['path'] for row in config['manager_dropins']]
        if installed: expected.append(str(dropin(config)))
        require(sorted(self.property(config, unit, 'DropInPaths').split()) == sorted(expected), 'Network manager overrides differ')
        require(self.property(config, unit, 'ActiveState') == 'inactive'
                and self.property(config, unit, 'SubState') == 'dead', 'Keep the network manager stopped under accepted console maintenance')
        if installed:
            require(all(SERVICE in self.property(config, unit, key).split() for key in ('Requires', 'After')),
                    'Network manager lacks the hard startup guard dependency')

    def denial(self, config, directory):
        kernel = edge.Kernel(config['nft'], directory); observations = {}; specs = boot.validate(config)
        with ExitStack() as locks:
            for spec in specs: locks.enter_context(boot.boundary_lock(Path(config['ledger']), edge.validate(spec)[1]))
            for spec in specs:
                state, _ = kernel.inspect(spec)
                observations[edge.validate(spec)[1]] = edge_contain.observed_withdrawal(spec, state)
        return observations


def install(config, authority, *, host=None, root=ROOT):
    installed, rendered = installed_files(config); authorize(config, authority)
    host = host or Host(); host.identity(config, root)
    state = host.directory(STATE)
    fd = os.open(state/'writer.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        private_path(state/'writer.lock'); fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        intent = state/'intent.json'; identity = {'format':'hosting-edge-install-intent/1', 'config':config,
            'files':{str(path):digest(raw) for path,(raw,_) in rendered.items()}}
        if intent.exists(): require(load_private(intent) == identity, 'Another installation owns the startup guard')
        else:
            require(not any(host.path(path).exists() for path in (CONFIG, UNIT, dropin(config), OUTPUT)),
                    'Unmanaged startup guard cannot be adopted implicitly')
            host.manager(config)
            require(host.property(config, SERVICE, 'LoadState') == 'not-found'
                    and not host.property(config, SERVICE, 'FragmentPath')
                    and not host.property(config, SERVICE, 'DropInPaths'), 'Unmanaged loaded startup guard cannot be replaced')
            write_new(intent, encoded(identity))
        for path,(raw,mode) in rendered.items():
            if host.path(path).exists(): host.verify_file(path, raw, mode)
        authorize(config, authority)
        loaded = str(dropin(config)) in host.property(config, config['manager'], 'DropInPaths').split()
        host.manager(config, installed=loaded)
        host.directory(CONFIG); host.directory(OUTPUT); host.directory(dropin(config).parent, mode=0o755)
        for path,(raw,mode) in rendered.items(): host.file(path, raw, mode)
        host.command([config['systemd_analyze'], 'verify', '--man=no', host.path(UNIT), config['manager_unit']['path']])
        authorize(config, authority); host.command([config['systemctl'], 'daemon-reload'])
        require(host.property(config, SERVICE, 'LoadState') == 'loaded'
                and host.property(config, SERVICE, 'FragmentPath') == str(host.path(UNIT))
                and not host.property(config, SERVICE, 'DropInPaths'), 'Loaded startup guard differs from the installed unit')
        host.manager(config, installed=True)
        authorize(config, authority); host.command([config['systemctl'], 'enable', SERVICE])
        authorize(config, authority); host.command([config['systemctl'], 'start', SERVICE])
        require(host.property(config, SERVICE, 'ActiveState') == 'active'
                and host.property(config, SERVICE, 'SubState') == 'exited'
                and host.command([config['systemctl'], 'is-enabled', SERVICE]) == 'enabled', 'Startup guard did not become active and enabled')
        import uuid
        observation = new_directory(host.path(OUTPUT)/('installation-observe-'+uuid.uuid4().hex), root)
        observed = host.denial(installed, observation)
        host.manager(config, installed=True); authorize(config, authority)
        result = {'format':'hosting-edge-install-receipt/1', 'status':'EDGE_GUARD_INSTALLED_REQUIRES_STARTUP_QUALIFICATION',
            'config_sha256':c.digest(config), 'authority_sha256':c.digest(authority), 'boot_config_sha256':c.digest(installed),
            'observations':observed, 'observed_at':utcnow().isoformat(), 'network_manager_started':False,
            'actual_reboot_tested':False, 'native_acceptance':False, 'production_activation':False}
        write_new(state/('receipt-'+digest(encoded(result))+'.json'), encoded(result)); return result
    finally: os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True); parser.add_argument('--authority', type=Path)
    parser.add_argument('--source-root',type=Path,default=ROOT)
    parser.add_argument('--execute', action='store_true'); args = parser.parse_args()
    try:
        config = load_private(args.config); validate(config)
        if not args.execute: print('{"status":"VALIDATED_NO_HOST_CHANGE"}'); return 0
        require(args.authority is not None, 'Current exact installation authority required')
        result = install(config, load_private(args.authority),root=args.source_root); print(json.dumps({'status':result['status']})); return 0
    except Exception:
        print('{"status":"EDGE_INSTALLATION_HELD","reason":"Keep attachment held; preserve denial and native ledgers and use accepted console recovery"}')
        return 2


if __name__ == '__main__': raise SystemExit(main())
