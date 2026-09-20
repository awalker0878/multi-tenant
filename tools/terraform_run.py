#!/usr/bin/env python3
"""Prepare an exact, private saved-plan bundle for an authorized restricted WSD.

This operator command contacts the selected backend and native provider during
planning only with --read-authorized-target. It never approves an operation.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.check_release import verify
from tools.compile_wsd import identity
from tools.neutron_observe import strict_loads
from tools.plan_review import review
from tools.run_files import (current_window, digest, encoded, file_map, load_private,
                             new_directory, private_path, read_private, require,
                             utcnow, write_new)
from tools.terraform_catalog import entries

SCOPE_KEYS = ('environment_key', 'site_key', 'platform', 'tenant_key', 'wsd_key', 'phase')
ENV_KEYS = {'TF_VAR_platform_password', 'TF_HTTP_USERNAME', 'TF_HTTP_PASSWORD'}
BACKEND_KEYS = {'state_key', 'address', 'lock_address', 'unlock_address', 'lock_method', 'unlock_method'}


def select_scope(root, catalog_id, inputs):
    selected = [e for e in entries(root) if e['id'] == catalog_id and e['kind'] == 'composition']
    require(len(selected) == 1, 'Select one registered WSD composition')
    entry = selected[0]
    config = json.loads((root / entry['root'] / 'main.tf.json').read_text())
    require(config['terraform'].get('backend') == {'http': {}}, 'Only the owned HTTP backend is supported')
    require(isinstance(inputs, dict) and not set(inputs) - set(config['variable']), 'Unknown Terraform inputs')
    require(not any(k in inputs for k, v in config['variable'].items() if v.get('sensitive')),
            'Inject provider credentials through the private environment')
    require(inputs.get('allow_restricted_build') is True and bool(inputs.get('test_authorization_ref')),
            'Restricted build requires current external authority')
    require(isinstance(inputs.get('members'), dict) and inputs['members'], 'WSD members required')
    scope = {k: identity(inputs[k]) for k in ('environment_key', 'site_key', 'tenant_key', 'wsd_key')}
    scope.update(platform=entry['platform'], phase=entry['root'].split('/')[-1])
    state_key = '/'.join(scope[k] for k in SCOPE_KEYS)
    return entry, scope, state_key


def backend_settings(backend, state_key):
    require(isinstance(backend, dict) and set(backend) == BACKEND_KEYS, 'Invalid backend fields')
    require(backend['state_key'] == state_key, 'Backend belongs to another state scope')
    origins = set()
    for key in ('address', 'lock_address', 'unlock_address'):
        value = backend[key]
        require(isinstance(value, str), 'Backend endpoint required')
        url = urlsplit(value)
        require(url.scheme == 'https' and url.hostname and not url.username and not url.password
                and not url.query and not url.fragment and url.path.startswith('/')
                and not url.hostname.endswith('.invalid'), 'Authenticated TLS backend endpoints required')
        origins.add((url.hostname, url.port or 443))
    require(len(origins) == 1, 'State and lock endpoints must share the reviewed authority')
    require(backend['lock_method'] in {'LOCK', 'POST'} and backend['unlock_method'] in {'UNLOCK', 'DELETE'},
            'Unsupported backend lock methods')
    return {k: v for k, v in backend.items() if k != 'state_key'}


def authority_matches(authority, source, scope, input_bytes, backend_bytes):
    require(set(authority) == {'format', 'source_commit', 'scope', 'operation_id', 'generation',
            'input_sha256', 'backend_sha256', 'valid_from', 'valid_until', 'change_ref'},
            'Invalid contact authority fields')
    require(authority['format'] == 'hosting-terraform-contact/1', 'Unknown contact authority')
    require(authority['source_commit'] == source and authority['scope'] == scope, 'Contact authority scope mismatch')
    require(authority['input_sha256'] == digest(input_bytes) and authority['backend_sha256'] == digest(backend_bytes),
            'Contact authority input/backend mismatch')
    identity(authority['operation_id'])
    require(type(authority['generation']) is int and authority['generation'] > 0, 'Positive operation generation required')
    require(isinstance(authority['change_ref'], str) and re.fullmatch(r'[A-Za-z0-9:._/-]{3,200}', authority['change_ref']),
            'External change reference required')
    current_window(authority)


def process_environment(environment):
    require(isinstance(environment, dict) and not set(environment) - ENV_KEYS
            and all(isinstance(v, str) and v for v in environment.values()), 'Unsupported credential environment')
    # No inherited TF_CLI_ARGS, TF_WORKSPACE, endpoint overrides, provider debug logs
    # or plugin cache/mirror settings. Backend endpoints come from the bound file.
    clean = {k: os.environ[k] for k in ('PATH', 'LANG', 'LC_ALL', 'SSL_CERT_FILE', 'SSL_CERT_DIR') if k in os.environ}
    clean.update(environment)
    clean.update(TF_IN_AUTOMATION='1', TF_INPUT='0', CHECKPOINT_DISABLE='1')
    return clean


def snapshot(root, destination):
    destination.mkdir(mode=0o700)
    listing = subprocess.check_output(['git', '-C', str(root), 'ls-tree', '-rz', 'HEAD', 'terraform'], timeout=60)
    for item in listing.split(b'\0'):
        if not item:
            continue
        metadata, name = item.split(b'\t', 1)
        mode, kind, blob = metadata.split()
        require(mode in {b'100644', b'100755'} and kind == b'blob', 'Unsupported Terraform source object')
        path = destination / name.decode()
        require(path.resolve().is_relative_to(destination.resolve()), 'Unsafe Terraform source path')
        path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        # mkdir(parents=True) intermediate directories are subsequently restricted.
        for parent in path.parents:
            if parent == destination:
                break
            parent.chmod(0o700)
        data = subprocess.check_output(['git', '-C', str(root), 'cat-file', 'blob', blob.decode()], timeout=60)
        write_new(path, data)


def command(binary, directory, argv, environment, output, *, timeout=900, ok=(0,)):
    require(not output.exists(), 'Command output already exists')
    # stdout/stderr can contain credentials and plans: never copy them to the console.
    with os.fdopen(os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as stream:
        result = subprocess.run([str(binary), f'-chdir={directory}', *argv], env=environment,
                                stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT,
                                timeout=timeout, check=False, umask=0o077)
        stream.flush()
        os.fsync(stream.fileno())
    require(result.returncode in ok, 'Terraform command failed; inspect the private operation log')
    return result.returncode


def prepare(args, root=ROOT):
    require(args.read_authorized_target is True, 'Explicit native read/contact opt-in required')
    source = verify(root)
    require(source['status'] == 'HASHES_MATCH', 'A clean committed checkout is required')
    input_bytes, backend_bytes = read_private(args.inputs), read_private(args.backend)
    inputs, backend = strict_loads(input_bytes), strict_loads(backend_bytes)
    entry, scope, state_key = select_scope(root, args.catalog_id, inputs)
    settings = backend_settings(backend, state_key)
    authority = load_private(args.authority)
    authority_matches(authority, source['commit'], scope, input_bytes, backend_bytes)
    credentials = load_private(args.environment)
    env = process_environment(credentials)
    require(entry['platform'] != 'openstack', 'OpenStack cloud-file custody is not yet supported by this executor')
    binary = Path(args.terraform).resolve(strict=True)
    require(binary.is_file() and os.access(binary, os.X_OK), 'An explicit Terraform executable is required')
    operation = new_directory(args.output, root)
    (operation / 'tmp').mkdir(mode=0o700)
    env['TMPDIR'] = str(operation / 'tmp')
    # An explicit empty CLI config prevents ambient provider development overrides.
    write_new(operation / 'terraform.rc', b'disable_checkpoint = true\n')
    env['TF_CLI_CONFIG_FILE'] = str(operation / 'terraform.rc')
    snapshot(root, operation / 'source')
    directory = operation / 'source' / entry['root']
    for name, data in {'inputs.json': input_bytes, 'backend.json': backend_bytes,
                       'contact.json': encoded(authority), 'environment.json': encoded(credentials)}.items():
        write_new(operation / name, data)
    references = load_private(args.references) if args.references else {}
    write_new(operation / 'references.json', encoded(references))
    write_new(operation / 'backend.hcl', ''.join(f'{k} = {json.dumps(v)}\n' for k, v in sorted(settings.items())).encode())
    command(binary, directory, ['version', '-json'], env, operation / 'version.json')
    version = strict_loads(read_private(operation / 'version.json'))['terraform_version']
    require(version == json.loads((root / 'config/toolchain.json').read_text())['terraform'], 'Terraform version differs from the pinned toolchain')
    current_window(authority)
    command(binary, directory, ['init', '-input=false', '-no-color', '-lockfile=readonly',
            '-reconfigure', f'-backend-config={operation / "backend.hcl"}'], env, operation / 'init.log')
    current_window(authority)
    command(binary, directory, ['plan', '-input=false', '-no-color', '-lock=true', '-lock-timeout=60s',
            '-detailed-exitcode', f'-var-file={operation / "inputs.json"}', f'-out={operation / "saved.tfplan"}'],
            env, operation / 'plan.log', ok=(0, 2))
    command(binary, directory, ['show', '-json', str(operation / 'saved.tfplan')], env, operation / 'plan.json')
    result = review(strict_loads(read_private(operation / 'plan.json')), references)
    write_new(operation / 'review.json', encoded(result))
    require(result['status'] != 'BLOCKED', 'Restricted plan has blocked changes; no execution bundle issued')
    current_window(authority)
    protected = ['inputs.json', 'backend.json', 'backend.hcl', 'environment.json', 'contact.json',
                 'references.json', 'terraform.rc', 'version.json', 'saved.tfplan', 'plan.json', 'review.json']
    manifest = {'format': 'hosting-terraform-bundle/1', 'source_commit': source['commit'],
                'catalog_id': entry['id'], 'root': entry['root'], 'scope': scope, 'state_key': state_key,
                'operation_id': authority['operation_id'], 'generation': authority['generation'],
                'created_at': utcnow().isoformat(), 'terraform_version': version,
                'terraform_sha256': digest(binary.read_bytes()), 'source_files': file_map(operation / 'source'),
                'artifacts': {name: digest(read_private(operation / name)) for name in protected},
                'review_status': result['status'], 'status': 'AWAITING_EXACT_PLAN_REVIEW'}
    write_new(operation / 'bundle.json', encoded(manifest))
    return {'status': manifest['status'], 'bundle_sha256': digest(encoded(manifest)), 'native_apply': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog-id', required=True)
    for name in ('inputs', 'backend', 'authority', 'environment', 'output', 'terraform'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--references', type=Path)
    parser.add_argument('--read-authorized-target', action='store_true')
    args = parser.parse_args()
    try:
        result = prepare(args)
        print(json.dumps(result))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        # Exception values and native diagnostics can contain secrets or endpoints.
        print(json.dumps({'status': 'STOPPED', 'native_acceptance': False,
                          'reason': 'Operator precondition or Terraform command failed; inspect private artifacts'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
