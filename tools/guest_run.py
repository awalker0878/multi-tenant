#!/usr/bin/env python3
"""Prepare a private, source-bound guest configuration bundle without SSH contact."""
from copy import deepcopy
import argparse
import base64
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ''): sys.path.insert(0, str(ROOT))
from provisioner.repository import ASSET_ROOT, asset_path
from tools.check_release import verify
from tools.compile_wsd import identity
from tools.guest_inventory import build, gate
from tools.guest_services import PROFILE, verify_assets
from tools.run_files import (digest, encoded, file_map, load_private, new_directory,
    private_path, read_private, require, utcnow, write_new)
from tools.wsd_handoff import execution_outputs

PLAYBOOK = 'ansible/playbooks/native/configure_linux.yml'
REFERENCES = {'target_binding_ref', 'bootstrap_ref', 'writer_coordination_ref', 'runtime_ref', 'recovery_ref'}
RUNTIME_INSPECT = r'''
import hashlib, importlib, importlib.metadata, json, pathlib, sys
packages = {}
for name, distribution in [('ansible', 'ansible-core'), ('jinja2', 'Jinja2'), ('yaml', 'PyYAML'), ('markupsafe', 'MarkupSafe')]:
    module = importlib.import_module(name)
    root = pathlib.Path(module.__file__).resolve().parent
    files = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    packages[name] = dict(version=importlib.metadata.version(distribution), path=str(root),
        files_sha256=hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest())
print(json.dumps(dict(python=sys.version, prefix=sys.prefix, packages=packages)))
'''


def safe_path(value):
    path = Path(value).absolute()
    require(re.fullmatch(r'/[A-Za-z0-9_./-]+', str(path)) and '..' not in path.parts,
            'Use an absolute operator path without shell metacharacters')
    return path


def runtime_environment(directory):
    # No caller ANSIBLE_*, Python paths, SSH agents, shell startup or proxy settings.
    return {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8',
            'HOME': str(directory / 'runtime/home'), 'TMPDIR': str(directory / 'runtime/tmp'),
            'ANSIBLE_CONFIG': str(directory / 'ansible.cfg'),
            'ANSIBLE_LOCAL_TEMP': str(directory / 'runtime/tmp'),
            'ANSIBLE_COLLECTIONS_PATH': str(directory / 'runtime/collections'),
            'ANSIBLE_COLLECTIONS_SCAN_SYS_PATH': 'False', 'ANSIBLE_NOCOLOR': '1',
            'HOSTING_GUEST_RESULT': str(directory / 'runtime/stats.json')}


def runtime_record(python, ssh):
    python, ssh = safe_path(python), safe_path(ssh)
    require(all(p.is_file() and os.access(p, os.X_OK) for p in (python, ssh)), 'Executable Python and SSH required')
    result = subprocess.run([str(python), '-I', '-c', RUNTIME_INSPECT], stdin=subprocess.DEVNULL,
        capture_output=True, text=True, timeout=30, env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
    require(result.returncode == 0, 'Pinned Ansible runtime is unavailable')
    data = json.loads(result.stdout)
    for name, version in [('ansible', '2.19.7'), ('jinja2', '3.1.6'), ('yaml', '6.0.2')]:
        require(data['packages'][name]['version'] == version, 'Install the repository-pinned Ansible dependencies')
    return data | {'python_path': str(python), 'python_sha256': digest(python.read_bytes()),
                   'ssh_path': str(ssh), 'ssh_sha256': digest(ssh.read_bytes())}


def source_paths(root):
    def reviewed(name):
        return asset_path(name) if root == ROOT else root / name

    paths = [reviewed(PLAYBOOK), root / 'scripts/__init__.py', root / 'scripts/build_wsd_compositions.py',
             reviewed('ansible/filter_plugins/guest_filters.py'),
             reviewed('ansible/callback_plugins/hosting_guest_result.py')]
    paths += list((root / 'tools').glob('*.py'))
    for role in ('linux_guest_baseline', 'linux_guest_services', 'linux_guest_backup'):
        tasks = reviewed(f'ansible/roles/{role}/tasks/main.yml')
        paths += [p for p in tasks.parents[1].rglob('*') if p.is_file()]
    return sorted(paths)


def configuration(directory, ssh):
    source = directory / 'source/ansible'
    return f'''[defaults]
roles_path = {source}/roles
filter_plugins = {source}/filter_plugins
callback_plugins = {source}/callback_plugins
callbacks_enabled = hosting_guest_result
stdout_callback = default
retry_files_enabled = False
host_key_checking = True
display_args_to_stdout = False
fact_caching = memory
forks = 1
timeout = 10
nocows = True
[inventory]
enable_plugins = yaml
[ssh_connection]
ssh_executable = {ssh}
ssh_args = -F /dev/null -o BatchMode=yes -o IdentitiesOnly=yes -o IdentityAgent=none -o CertificateFile={directory}/ssh_key-cert.pub -o PubkeyAcceptedAlgorithms=ssh-ed25519-cert-v01@openssh.com -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no -o ProxyCommand=none -o ProxyJump=none -o ControlMaster=no -o ControlPersist=no -o ControlPath=none -o ForwardAgent=no -o ClearAllForwardings=yes
transfer_method = piped
password_mechanism = disable
pipelining = False
usetty = False
retries = 0
'''.encode()


def assets(target):
    if target['profile'] != PROFILE: return []
    values = list(target['services']['files'].values())
    if 'backup' in target['services']:
        values += [target['services']['backup'][key] for key in ('credentials', 'ca')]
    return values


def snapshot_access(access, directory):
    rewritten = deepcopy(access)
    for name, target in rewritten['targets'].items():
        if target['profile'] == PROFILE: verify_assets(target, access['scope'])
        for index, asset in enumerate(assets(target)):
            raw = read_private(asset['path'])
            require(digest(raw) == asset['sha256'], 'Service asset changed during preparation')
            destination = directory / 'assets' / (name + '-' + str(index))
            write_new(destination, raw); asset['path'] = str(destination)
        if target['profile'] == PROFILE: verify_assets(target, access['scope'])
    return rewritten


def prepare(args, root=ROOT):
    identity(args.operation_id)
    require(type(args.generation) is int and args.generation > 0, 'Positive operation generation required')
    require(args.mode in {'check', 'configure'}, 'Explicit supported guest mode required')
    require(type(args.max_seconds) is int and 30 <= args.max_seconds <= 3600, 'Bound execution to 30-3600 seconds')
    require((args.workload_run is None) != (args.workload_outputs is None), 'Choose one workload receipt or raw output')
    source = verify(root)
    require(source['status'] == 'HASHES_MATCH', 'Prepare from an exact clean source revision')
    references = load_private(args.references)
    require(isinstance(references, dict) and set(references) == REFERENCES, 'Complete external guest handoffs required')
    require(all(isinstance(v, str) and re.fullmatch(r'[A-Za-z0-9:._/-]{3,200}', v) for v in references.values()),
            'Invalid guest handoff reference')
    if args.workload_run:
        outputs, _, provenance = execution_outputs(args.workload_run, 'workloads')
    else:
        outputs, provenance = load_private(args.workload_outputs), None
    access = load_private(args.access)
    destination = safe_path(args.output)
    build(outputs, access, str(destination / 'known_hosts'))
    key = read_private(args.ssh_key); certificate = read_private(args.ssh_certificate)
    require(0 < len(key) <= 65536 and key.startswith(b'-----BEGIN OPENSSH PRIVATE KEY-----'), 'OpenSSH private key required')
    parts = certificate.decode('ascii').strip().split()
    require(2 <= len(parts) <= 3 and parts[0] == 'ssh-ed25519-cert-v01@openssh.com'
            and len(certificate) <= 16384 and base64.b64decode(parts[1], validate=True), 'Ed25519 user certificate required')
    runtime = runtime_record(args.python, args.ssh)
    directory = new_directory(destination, root)
    for name in ('source', 'assets', 'runtime', 'runtime/home', 'runtime/tmp', 'runtime/collections'):
        (directory / name).mkdir(mode=0o700)
    for path in source_paths(root):
        require(not path.is_symlink(), 'Execution source symlink is unsupported')
        relative = path.relative_to(ASSET_ROOT) if path.is_relative_to(ASSET_ROOT) else path.relative_to(root)
        copied = directory / 'source' / relative
        copied.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        for parent in copied.parents:
            if parent == directory: break
            parent.chmod(0o700)
        write_new(copied, path.read_bytes())
    rewritten = snapshot_access(access, directory)
    inventory, pins = build(outputs, rewritten, str(directory / 'known_hosts'))
    inventory['all']['vars']['hosting_native_enabled'] = True
    documents = {'outputs.json': outputs, 'access.json': rewritten, 'original-access.json': access,
        'references.json': references, 'inventory.json': inventory,
        'credentials.json': {'ssh_key': {'path': str(private_path(args.ssh_key)), 'sha256': digest(key)}},
        'runtime.json': runtime, 'handoff.json': provenance}
    for name, data in documents.items(): write_new(directory / name, encoded(data))
    write_new(directory / 'known_hosts', pins.encode())
    write_new(directory / 'ssh_key-cert.pub', certificate)
    write_new(directory / 'ansible.cfg', configuration(directory, runtime['ssh_path']))
    hosts = inventory['all']['children']['hosting_guests']['hosts']
    gate(True, outputs, rewritten, str(directory / 'known_hosts'), list(hosts), hosts)
    require(verify(root) == source, 'Source changed during preparation')
    artifacts = {p.name: digest(read_private(p)) for p in directory.iterdir() if p.is_file()}
    bundle = {'format': 'hosting-guest-bundle/1', 'status': 'AWAITING_EXACT_GUEST_REVIEW',
        'operation_id': args.operation_id, 'generation': args.generation, 'source_commit': source['commit'],
        'scope': access['scope'], 'mode': args.mode, 'max_seconds': args.max_seconds,
        'created_at': utcnow().isoformat(), 'directory': str(directory),
        'artifacts': artifacts, 'source_files': file_map(directory / 'source'), 'service_assets': file_map(directory / 'assets')}
    write_new(directory / 'bundle.json', encoded(bundle))
    return {'status': bundle['status'], 'bundle_sha256': digest(encoded(bundle)), 'target_contacted': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--workload-run', type=Path); choice.add_argument('--workload-outputs', type=Path)
    for name in ('access', 'references', 'ssh-key', 'ssh-certificate', 'python', 'ssh', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--operation-id', required=True); parser.add_argument('--generation', type=int, required=True)
    parser.add_argument('--mode', choices=('check', 'configure'), default='check')
    parser.add_argument('--max-seconds', type=int, default=600)
    try:
        print(json.dumps(prepare(parser.parse_args()))); return 0
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
        print(json.dumps({'status': 'REJECTED', 'target_contacted': False,
                         'reason': 'Guest preparation failed; inspect private inputs and runtime'})); return 2


if __name__ == '__main__': raise SystemExit(main())
