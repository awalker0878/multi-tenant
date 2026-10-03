#!/usr/bin/env python3
"""Prepare an exact, private saved-plan bundle for an authorized restricted WSD.

This operator command contacts the selected backend and native provider during
planning only with --read-authorized-target. It never approves an operation.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit

from hosting_resources import SOURCE_ROOT
ROOT = SOURCE_ROOT

from provisioner.execution.source_integrity import verify, verify_runtime
from provisioner.compiler.wsd import identity
from provisioner.execution.neutron_observe import strict_loads
from provisioner.execution.plan_review import review
from provisioner.execution.run_files import (current_window, digest, encoded, file_map, load_private,
                             new_directory, private_path, read_private, require,
                             utcnow, write_new, OperatorError)
from provisioner.execution.terraform_catalog import entries

SCOPE_KEYS = ('environment_key', 'site_key', 'platform', 'tenant_key', 'wsd_key', 'phase')
ENV_KEYS = {'TF_VAR_platform_password', 'TF_HTTP_USERNAME', 'TF_HTTP_PASSWORD'}
BACKEND_KEYS = {'state_key', 'address', 'lock_address', 'unlock_address', 'lock_method', 'unlock_method'}


def select_scope(root, catalog_id, inputs):
    require(isinstance(root, Path), 'An explicit current source checkout is required')
    selected = [e for e in entries(root) if e['id'] == catalog_id and e['kind'] == 'composition']
    require(len(selected) == 1, 'Select one registered WSD composition')
    entry = selected[0]
    config = json.loads((root / entry['root'] / 'main.tf.json').read_text(encoding='utf-8'))
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


def authority_matches(authority, source, scope, input_bytes, backend_bytes, environment_bytes, cloud_bytes, ca_bytes):
    require(set(authority) == {'format', 'source_commit', 'scope', 'operation_id', 'generation',
            'input_sha256', 'backend_sha256', 'environment_sha256', 'cloud_sha256', 'ca_sha256',
            'valid_from', 'valid_until', 'change_ref'},
            'Invalid contact authority fields')
    require(authority['format'] == 'hosting-terraform-contact/2', 'Unknown contact authority')
    require(authority['source_commit'] == source and authority['scope'] == scope, 'Contact authority scope mismatch')
    require(authority['input_sha256'] == digest(input_bytes) and authority['backend_sha256'] == digest(backend_bytes),
            'Contact authority input/backend mismatch')
    for key, content in [('environment', environment_bytes), ('cloud', cloud_bytes), ('ca', ca_bytes)]:
        require(authority[key + '_sha256'] == (digest(content) if content is not None else None),
                'Credential, cloud or trust material differs from contact authority')
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
    clean = {k: os.environ[k] for k in ('PATH', 'LANG', 'LC_ALL') if k in os.environ}
    clean.update(environment)
    clean.update(TF_IN_AUTOMATION='1', TF_INPUT='0', CHECKPOINT_DISABLE='1')
    return clean


def cloud_config(content, name):
    """A bounded, self-contained application-credential profile; no YAML merging."""
    doc = strict_loads(content)
    require(set(doc) == {'clouds'} and isinstance(doc['clouds'], dict) and set(doc['clouds']) == {name},
            'Exactly the selected cloud profile is required')
    cloud = doc['clouds'][name]
    require(isinstance(cloud, dict) and set(cloud) == {'auth_type', 'auth', 'region_name', 'interface', 'verify'},
            'A self-contained cloud without imported profiles or file references is required')
    require(cloud['auth_type'] == 'v3applicationcredential' and cloud['verify'] is True
            and cloud['interface'] in {'internal', 'public'}, 'Scoped application credentials and TLS required')
    require(isinstance(cloud['region_name'], str) and bool(cloud['region_name'].strip()), 'Explicit cloud region required')
    auth = cloud['auth']
    require(isinstance(auth, dict) and set(auth) == {'auth_url', 'application_credential_id', 'application_credential_secret'}
            and all(isinstance(v, str) and v.strip() for v in auth.values()), 'Complete application credential required')
    url = urlsplit(auth['auth_url'])
    require(url.scheme == 'https' and url.hostname and not url.username and not url.password
            and not url.query and not url.fragment and not url.hostname.endswith('.invalid'),
            'TLS identity endpoint required')
    return doc


def runtime_environment(operation, credentials, platform, directory):
    env = process_environment(credentials)
    env.update(TMPDIR=str(operation / 'tmp'), TF_CLI_CONFIG_FILE=str(operation / 'terraform.rc'))
    if (operation / 'ca.pem').exists():
        env['SSL_CERT_FILE'] = str(operation / 'ca.pem')
    if platform == 'openstack':
        env['OS_CLIENT_CONFIG_FILE'] = str(directory / 'clouds.yaml')
    return env


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


def authorized_command(authority, *args, **kwargs):
    current_window(authority)
    remaining = (datetime.fromisoformat(authority['valid_until'].replace('Z', '+00:00')) - utcnow()).total_seconds()
    require(remaining > 0, 'Native contact window expired')
    kwargs['timeout'] = min(kwargs.get('timeout', 900), remaining)
    return command(*args, **kwargs)


def prepare(args, root=ROOT):
    require(isinstance(root, Path), 'An explicit current source checkout is required')
    require(args.read_authorized_target is True, 'Explicit native read/contact opt-in required')
    source = verify(root)
    require(source['status'] == 'HASHES_MATCH', 'A clean committed checkout is required')
    require(verify_runtime(root)['status'] == 'RUNTIME_SOURCES_MATCH',
            'Running package differs from the selected source checkout')
    input_bytes, backend_bytes = read_private(args.inputs), read_private(args.backend)
    inputs, backend = strict_loads(input_bytes), strict_loads(backend_bytes)
    entry, scope, state_key = select_scope(root, args.catalog_id, inputs)
    transition = load_private(args.transition) if getattr(args, 'transition', None) else None
    if transition is not None:
        from provisioner.execution.lifecycle_transition import validate as validate_transition
        validate_transition(transition, scope, input_bytes)
    settings = backend_settings(backend, state_key)
    environment_bytes = read_private(args.environment)
    cloud_bytes = read_private(args.cloud) if args.cloud else None
    ca_bytes = read_private(args.ca_bundle) if args.ca_bundle else None
    authority = load_private(args.authority)
    authority_matches(authority, source['commit'], scope, input_bytes, backend_bytes, environment_bytes, cloud_bytes, ca_bytes)
    credentials = strict_loads(environment_bytes)
    env = process_environment(credentials)
    require((entry['platform'] == 'openstack') == (cloud_bytes is not None), 'Cloud profile required only for OpenStack')
    cloud = cloud_config(cloud_bytes, inputs['openstack_cloud']) if cloud_bytes else None
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
    if ca_bytes is not None:
        write_new(operation / 'ca.pem', ca_bytes)
    if cloud is not None:
        if ca_bytes is not None:
            cloud['clouds'][inputs['openstack_cloud']]['cacert'] = str(operation / 'ca.pem')
        # Gophercloud searches secure.yaml separately. Explicit empty files prevent
        # ambient home or /etc profiles from changing the selected project/account.
        write_new(directory / 'clouds.yaml', encoded(cloud))
        write_new(directory / 'secure.yaml', b'{"clouds": {}}\n')
        write_new(directory / 'clouds-public.yaml', b'{"public-clouds": {}}\n')
    env = runtime_environment(operation, credentials, entry['platform'], directory)
    for name, data in {'inputs.json': input_bytes, 'backend.json': backend_bytes,
                       'contact.json': encoded(authority), 'environment.json': encoded(credentials)}.items():
        write_new(operation / name, data)
    references = load_private(args.references) if args.references else {}
    write_new(operation / 'references.json', encoded(references))
    if transition is not None:
        write_new(operation / 'transition.json', encoded(transition))
    write_new(operation / 'backend.hcl', ''.join(f'{k} = {json.dumps(v)}\n' for k, v in sorted(settings.items())).encode())
    authorized_command(authority, binary, directory, ['version', '-json'], env, operation / 'version.json')
    version = strict_loads(read_private(operation / 'version.json'))['terraform_version']
    toolchain = root / 'config/toolchain.json'
    require(version == json.loads(toolchain.read_text(encoding='utf-8'))['terraform'], 'Terraform version differs from the pinned toolchain')
    current_window(authority)
    authorized_command(authority, binary, directory, ['init', '-input=false', '-no-color', '-lockfile=readonly',
            '-reconfigure', f'-backend-config={operation / "backend.hcl"}'], env, operation / 'init.log')
    current_window(authority)
    authorized_command(authority, binary, directory, ['plan', '-input=false', '-no-color', '-lock=true', '-lock-timeout=60s',
            '-detailed-exitcode', f'-var-file={operation / "inputs.json"}', f'-out={operation / "saved.tfplan"}'],
            env, operation / 'plan.log', ok=(0, 2))
    authorized_command(authority, binary, directory, ['show', '-json', str(operation / 'saved.tfplan')], env, operation / 'plan.json')
    result = review(strict_loads(read_private(operation / 'plan.json')), references, transition)
    write_new(operation / 'review.json', encoded(result))
    require(result['status'] != 'BLOCKED', 'Restricted plan has blocked changes; no execution bundle issued')
    current_window(authority)
    protected = ['inputs.json', 'backend.json', 'backend.hcl', 'environment.json', 'contact.json',
                 'references.json', 'terraform.rc', 'version.json', 'saved.tfplan', 'plan.json', 'review.json']
    if ca_bytes is not None:
        protected.append('ca.pem')
    if transition is not None:
        protected.append('transition.json')
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
    parser.add_argument('--transition', type=Path)
    parser.add_argument('--cloud', type=Path)
    parser.add_argument('--ca-bundle', type=Path)
    parser.add_argument('--read-authorized-target', action='store_true')
    parser.add_argument('--source-root', type=Path, default=ROOT,
                        help='Exact clean source checkout; required outside source development')
    args = parser.parse_args()
    try:
        result = prepare(args, root=args.source_root)
        print(json.dumps(result))
        return 0
    except OperatorError as exc:
        print(json.dumps({'status': 'STOPPED', 'reason': str(exc), 'native_acceptance': False}))
        return 2
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        # Exception values and native diagnostics can contain secrets or endpoints.
        print(json.dumps({'status': 'STOPPED', 'native_acceptance': False,
                          'reason': 'Operator precondition or Terraform command failed; inspect private artifacts'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
