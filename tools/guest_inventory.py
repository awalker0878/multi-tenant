#!/usr/bin/env python3
"""Bind a private Linux access handoff to exact Terraform workload identities."""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import ipaddress
import json
import os
from pathlib import Path
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from provisioner.compiler.wsd import STATE, fields, identity, require
from tools.neutron_observe import strict_loads
from tools.guest_services import PROFILE, validate_services, verify_assets


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(parsed.tzinfo is not None, 'Timezone required')
    return parsed.astimezone(timezone.utc)


def build(outputs, access, known_hosts, now=None):
    now = now or datetime.now(timezone.utc)
    fields(access, {'format', 'scope', 'valid_until', 'change_ref', 'targets'}, 'guest access')
    require(access['format'] == 'hosting-guest-access/1', 'Unknown guest access format')
    fields(access['scope'], {'environment_key', 'site_key', 'platform', 'tenant_key', 'wsd_key', 'phase'}, 'guest scope')
    for key in ('environment_key', 'site_key', 'tenant_key', 'wsd_key'):
        identity(access['scope'][key])
    platform = access['scope']['platform']
    require(platform in {'nutanix', 'openstack', 'vmware'} and access['scope']['phase'] == 'workloads', 'Not a workload scope')
    require(outputs.get('scope', {}).get('value') == access['scope'], 'Workload output scope mismatch')
    require(outputs.get('delivery_state', {}).get('value') == STATE, 'Unexpected workload delivery state')
    require(isinstance(access['change_ref'], str) and re.fullmatch(r'[A-Za-z0-9:._/-]{3,200}', access['change_ref']), 'Change reference required')
    require(0 < (timestamp(access['valid_until']) - now).total_seconds() <= 86400, 'Access handoff expired or exceeds 24 hours')
    require(isinstance(known_hosts, str) and re.fullmatch(r'/[A-Za-z0-9_./-]+', known_hosts)
            and '..' not in Path(known_hosts).parts, 'Private absolute known-hosts path required')
    members = outputs.get('members', {}).get('value')
    require(isinstance(members, dict) and members and isinstance(access['targets'], dict)
            and set(members) == set(access['targets']), 'Exact workload target set required')
    hosts, key_lines, endpoints, native_ids, machine_ids = {}, [], set(), set(), set()
    for name, target in access['targets'].items():
        identity(name)
        require(name not in {'localhost', 'all', 'ungrouped', 'hosting_guests'}, 'Reserved Ansible inventory identity')
        keys = {'native_id', 'address', 'port', 'user', 'host_key', 'machine_id', 'hostname', 'profile', 'time_servers'}
        fields(target, keys | ({'services'} if target.get('profile') == PROFILE else set()), 'guest target')
        member = members[name]
        native_id = member.get('server_id' if platform == 'openstack' else 'vm_id')
        require(isinstance(native_id, str) and native_id and target['native_id'] == native_id
                and member.get('delivery_state') == STATE and native_id not in native_ids, 'Native workload identity mismatch or duplicate')
        native_ids.add(native_id)
        address = ipaddress.ip_address(target['address'])
        require(str(address) == target['address'] and not (address.is_loopback or address.is_multicast or address.is_unspecified), 'Invalid guest address')
        require(type(target['port']) is int and 1 <= target['port'] <= 65535, 'Invalid SSH port')
        endpoint = (target['address'], target['port'])
        require(endpoint not in endpoints, 'Duplicate SSH endpoint')
        endpoints.add(endpoint)
        require(re.fullmatch(r'[a-z_][a-z0-9_-]{0,31}', target['user']) and target['user'] != 'root', 'Non-root SSH account required')
        require(re.fullmatch(r'[0-9a-f]{32}', target['machine_id']) and target['machine_id'] not in machine_ids, 'Unique observed machine ID required')
        machine_ids.add(target['machine_id'])
        require(re.fullmatch(r'[a-z][a-z0-9-]{1,62}', target['hostname']), 'Invalid guest hostname')
        require(target['profile'] in {'ubuntu-24.04-chrony', PROFILE}, 'Unsupported guest image profile')
        if target['profile'] == PROFILE:
            validate_services(target, access['scope'])
        require(isinstance(target['time_servers'], list) and 1 <= len(target['time_servers']) <= 4, 'Explicit time servers required')
        for server in target['time_servers']:
            ip = ipaddress.ip_address(server)
            require(str(ip) == server and not (ip.is_loopback or ip.is_multicast or ip.is_unspecified), 'Invalid time server')
        require(len(set(target['time_servers'])) == len(target['time_servers']), 'Duplicate time server')
        require(isinstance(target['host_key'], str), 'Pinned SSH host key required')
        key = target['host_key'].split(' ')
        require(len(key) == 2 and key[0] == 'ssh-ed25519', 'Only exact Ed25519 public host keys are supported')
        decoded = base64.b64decode(key[1], validate=True)
        require(len(decoded) == 51 and decoded[:19] == struct.pack('>I', 11) + b'ssh-ed25519' + struct.pack('>I', 32), 'Malformed SSH host key')
        key_lines.append(f'[{address}]:{target["port"]} {target["host_key"]}')
        if target['port'] == 22:
            key_lines.append(f'{address} {target["host_key"]}')
        hosts[name] = {
            'ansible_host': str(address), 'ansible_port': target['port'], 'ansible_user': target['user'],
            'ansible_connection': 'ssh', 'ansible_python_interpreter': '/usr/bin/python3',
            'ansible_ssh_common_args': '-o BatchMode=yes -o StrictHostKeyChecking=yes -o UpdateHostKeys=no -o GlobalKnownHostsFile=/dev/null -o UserKnownHostsFile=' + known_hosts,
            'ansible_host_key_checking': True, 'ansible_ssh_host_key_checking': True,
            'hosting_target': target,
        }
        if target['profile'] == PROFILE:
            # The image must already trust the selected user CA. Requiring a
            # certificate on the initial connection proves access before keys
            # are withdrawn by the full owned server configuration.
            hosts[name]['ansible_ssh_common_args'] += ' -o PubkeyAcceptedAlgorithms=ssh-ed25519-cert-v01@openssh.com'
    variables = {'hosting_native_enabled': False, 'hosting_guest_access': access,
                 'hosting_workload_outputs': outputs, 'hosting_known_hosts': known_hosts}
    return {'all': {'vars': variables, 'children': {'hosting_guests': {'hosts': hosts}}}}, '\n'.join(key_lines) + '\n'


def gate(enabled, outputs, access, known_hosts, targets, hostvars):
    require(enabled is True, 'Native profile requires explicit Boolean opt-in')
    inventory, expected_keys = build(outputs, access, known_hosts)
    expected = inventory['all']['children']['hosting_guests']['hosts']
    require(set(targets) == set(expected), 'Native inventory target set changed')
    path = Path(known_hosts)
    require(path.is_file() and not path.is_symlink() and path.stat().st_mode & 0o077 == 0,
            'Private non-symlink known-hosts file required')
    require(path.read_text(encoding='utf-8') == expected_keys, 'Pinned SSH keys changed')
    for name, values in expected.items():
        if values['hosting_target']['profile'] == PROFILE:
            verify_assets(values['hosting_target'], access['scope'])
        forbidden = {'ansible_ssh_host', 'ansible_ssh_port', 'ansible_ssh_user', 'ansible_password',
                     'ansible_ssh_pass', 'ansible_ssh_args', 'ansible_ssh_extra_args',
                     'ansible_scp_extra_args', 'ansible_sftp_extra_args', 'ansible_ssh_executable',
                     'ansible_scp_executable', 'ansible_sftp_executable'}
        require(not forbidden.intersection(hostvars[name]), 'Unreviewed SSH connection override')
        require(all(hostvars[name].get(k) == v for k, v in values.items()), 'Inventory connection or target binding changed')
    return sorted(expected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workload_outputs', type=Path, nargs='?')
    parser.add_argument('access', type=Path)
    parser.add_argument('--workload-run', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        folder = args.output.resolve()
        require(not folder.is_relative_to(ROOT), 'Private inventory must be outside the repository')
        require((args.workload_outputs is None) != (args.workload_run is None), 'Choose raw outputs or one successful workload run')
        if args.workload_run:
            from tools.wsd_handoff import execution_outputs
            outputs, _, _ = execution_outputs(args.workload_run, 'workloads')
        else:
            outputs = strict_loads(args.workload_outputs.read_bytes())
        inventory, keys = build(outputs, strict_loads(args.access.read_bytes()), str(folder / 'known_hosts'))
        folder.mkdir(mode=0o700, exist_ok=False)
        for name, value in {'inventory.json': json.dumps(inventory, indent=2) + '\n', 'known_hosts': keys}.items():
            with open(os.open(folder / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as stream:
                stream.write(value)
        print('{"status":"INVENTORY_BOUND_NATIVE_PROFILE_DISABLED"}')
        return 0
    except (ValueError, TypeError, KeyError, OSError) as exc:
        print(json.dumps({'status': 'REJECTED', 'reason': str(exc)})); return 2


if __name__ == '__main__':
    raise SystemExit(main())
