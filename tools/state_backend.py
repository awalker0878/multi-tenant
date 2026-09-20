#!/usr/bin/env python3
"""Compile the existing locked HTTP backend contract for a GitLab state project."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.compile_wsd import identity
from tools.run_files import encoded, new_directory, require, write_new
from tools.terraform_run import SCOPE_KEYS, backend_settings


def compile_backend(origin, project_id, scope):
    url = urlsplit(origin)
    require(url.scheme == 'https' and url.hostname and not url.username and not url.password
            and not url.query and not url.fragment and url.path in {'', '/'}
            and not url.hostname.endswith('.invalid'), 'Verified HTTPS GitLab origin required')
    require(type(project_id) is int and project_id > 0, 'Explicit state project ID required')
    require(set(scope) == set(SCOPE_KEYS), 'Complete state scope required')
    for value in scope.values():
        identity(value)
    require(scope['platform'] in {'nutanix', 'vmware', 'openstack'}
            and scope['phase'] in {'domains', 'workloads'}, 'Unsupported state scope')
    key = '/'.join(scope[k] for k in SCOPE_KEYS)
    # GitLab state names cannot contain slashes. Preserve the full scope in the
    # contract and derive a stable collision-resistant service name from it.
    name = 'wsd-' + hashlib.sha256(key.encode()).hexdigest()
    address = origin.rstrip('/') + f'/api/v4/projects/{project_id}/terraform/state/{name}'
    result = dict(state_key=key, address=address, lock_address=address + '/lock',
                  unlock_address=address + '/lock', lock_method='POST', unlock_method='DELETE')
    backend_settings(result, key)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--origin', required=True)
    parser.add_argument('--project-id', type=int, required=True)
    for key in SCOPE_KEYS:
        parser.add_argument('--' + key.replace('_', '-'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = compile_backend(args.origin, args.project_id, {k: getattr(args, k) for k in SCOPE_KEYS})
        folder = new_directory(args.output, ROOT)
        write_new(folder / 'backend.json', encoded(result))
        print(json.dumps({'status': 'BACKEND_CONFIGURATION_COMPILED', 'native_contact': False}))
        return 0
    except (ValueError, OSError, TypeError, KeyError):
        print('{"status":"REJECTED","native_contact":false}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
