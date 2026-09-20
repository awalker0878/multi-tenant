#!/usr/bin/env python3
"""Reserve, confirm, reconcile and tombstone an exact NetBox 4.7 IP allocation.

No automatic free-address selection, deletion, retry or reuse after retirement.
The shared durable ledger and service-side VRF uniqueness are both required.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime
import fcntl
import ipaddress
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.compile_wsd import identity
from tools.run_files import (current_window, digest, encoded, load_private, private_path,
                             read_private, replace_private, require, utcnow, write_new, OperatorError)
from tools.service_http import JsonService

ACTIONS = {'reserve', 'confirm', 'reconcile', 'retire'}


def validate(job):
    require(set(job) == {'format', 'origin', 'scope', 'member', 'operation_id', 'generation',
                        'tenant_id', 'vrf_id', 'prefix_id', 'prefix', 'address', 'reservation_ref'},
            'Invalid IPAM request fields')
    require(job['format'] == 'hosting-netbox-allocation/1', 'Unknown IPAM request')
    require(set(job['scope']) == {'environment_key', 'site_key', 'platform', 'tenant_key', 'wsd_key'},
            'Complete IPAM scope required')
    for value in [*job['scope'].values(), job['member'], job['operation_id']]:
        identity(value)
    require(job['scope']['platform'] in {'nutanix', 'vmware', 'openstack'}, 'Unknown platform')
    for field in ('tenant_id', 'vrf_id', 'prefix_id', 'generation'):
        require(type(job[field]) is int and job[field] > 0, 'Positive native ID/generation required')
    network = ipaddress.ip_network(job['prefix'], strict=True)
    address = ipaddress.ip_interface(job['address'])
    require(str(address) == job['address'] and address.network == network and network.version == 4
            and network.prefixlen <= 30 and address.ip not in {network.network_address, network.broadcast_address}
            and not (address.ip.is_multicast or address.ip.is_loopback or address.ip.is_unspecified
                     or address.ip.is_link_local), 'Explicit usable IPv4 allocation in the accepted prefix required')
    require(isinstance(job['reservation_ref'], str) and re.fullmatch(r'[A-Za-z0-9:._/-]{3,200}', job['reservation_ref']),
            'External capacity/address allocation authority required')
    # Construction validates the URL without opening a connection.
    JsonService(job['origin'], 'not-used')
    return digest(encoded(job))


def validate_authority(job, action, authority, token_bytes, ca_bytes):
    require(action in ACTIONS and set(authority) == {'request_sha256', 'action', 'valid_from',
            'valid_until', 'change_ref', 'cleanup_ref', 'token_sha256', 'ca_sha256'}, 'Invalid IPAM authority')
    require(authority['request_sha256'] == validate(job) and authority['action'] == action,
            'IPAM authority does not match the exact operation')
    require(authority['token_sha256'] == digest(token_bytes)
            and authority['ca_sha256'] == (digest(ca_bytes) if ca_bytes is not None else None),
            'IPAM credential/trust binding changed')
    for value in [authority['change_ref']] + ([authority['cleanup_ref']] if action == 'retire' else []):
        require(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9:._/-]{3,200}', value),
                'Current change and completed cleanup references required')
    current_window(authority)


def refs(job):
    return {'hosting_owner': digest(encoded({'scope': job['scope'], 'member': job['member']})),
            'hosting_request': digest(encoded(job)), 'hosting_operation': job['operation_id']}


@contextmanager
def allocation_lock(ledger, job):
    private_path(ledger, directory=True)
    key = digest(encoded([job['origin'].rstrip('/'), job['vrf_id'], str(ipaddress.ip_interface(job['address']).ip)]))
    directory = Path(ledger) / key
    directory.mkdir(mode=0o700, exist_ok=True)
    private_path(directory, directory=True)
    fd = os.open(directory / 'writer.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        private_path(directory / 'writer.lock')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (directory / 'request.json').exists():
            require(load_private(directory / 'request.json') == job, 'Address ledger is owned by another request')
        else:
            write_new(directory / 'request.json', encoded(job))
        yield directory
    finally:
        os.close(fd)


def relation(row, key):
    return row.get(key, {}).get('id') if isinstance(row.get(key), dict) else row.get(key)


class AllocationReader:
    """Exact native allocation/namespace readback shared by dependent services."""

    def __init__(self, job, authority, client):
        validate(job)
        require(client.origin == job['origin'].rstrip('/'), 'IPAM client origin changed')
        self.job, self.authority, self.client = job, authority, client

    def call(self, method, path, body=None, **kwargs):
        current_window(self.authority)
        seconds = (datetime.fromisoformat(self.authority['valid_until'].replace('Z', '+00:00')) - utcnow()).total_seconds()
        result, headers = self.client.request(method, path, body, timeout=seconds, **kwargs)
        headers = {k.lower(): v for k, v in headers.items()}
        require(headers.get('api-version') == '4.7', 'The selected NetBox 4.7 API is required')
        return result, headers

    def check(self, row):
        job = self.job
        require(isinstance(row, dict) and row.get('address') == job['address']
                and type(relation(row, 'tenant')) is int and relation(row, 'tenant') == job['tenant_id']
                and type(relation(row, 'vrf')) is int and relation(row, 'vrf') == job['vrf_id']
                and isinstance(row.get('custom_fields'), dict)
                and all(row.get('custom_fields', {}).get(k) == v for k, v in refs(job).items()),
                'IPAM object ownership or allocation changed')
        require(type(row.get('id')) is int and row['id'] > 0, 'Missing native IPAM identity')
        require(isinstance(row.get('status'), dict)
                and row['status'].get('value') in {'reserved', 'active', 'deprecated'},
                'Unsupported native allocation status')
        return row['status']['value']

    def observed(self):
        job = self.job
        query = urlencode({'address': str(ipaddress.ip_interface(job['address']).ip), 'vrf_id': job['vrf_id'], 'limit': 2})
        result, _ = self.call('GET', '/api/ipam/ip-addresses/?' + query)
        require(isinstance(result, dict) and isinstance(result.get('results'), list)
                and type(result.get('count')) is int and result.get('next') is None
                and result['count'] == len(result['results']) and result['count'] <= 1,
                'Ambiguous or paginated IP allocation')
        if not result['results']:
            return None, None
        selected = result['results'][0]
        status = self.check(selected)
        row, headers = self.call('GET', f"/api/ipam/ip-addresses/{selected['id']}/")
        require(self.check(row) == status and row['id'] == selected['id'],
                'Allocation identity or status changed between list and detail reads')
        return row, headers.get('etag')

    def namespace(self):
        job = self.job
        prefix, _ = self.call('GET', f"/api/ipam/prefixes/{job['prefix_id']}/")
        vrf, _ = self.call('GET', f"/api/ipam/vrfs/{job['vrf_id']}/")
        require(isinstance(prefix, dict) and isinstance(vrf, dict)
                and all(type(value) is int for value in [prefix.get('id'), relation(prefix, 'tenant'),
                        relation(prefix, 'vrf'), vrf.get('id'), relation(vrf, 'tenant')])
                and prefix.get('id') == job['prefix_id'] and prefix.get('prefix') == job['prefix']
                and relation(prefix, 'tenant') == job['tenant_id'] and relation(prefix, 'vrf') == job['vrf_id']
                and vrf.get('id') == job['vrf_id'] and relation(vrf, 'tenant') == job['tenant_id']
                and vrf.get('enforce_unique') is True, 'Prefix/tenant/VRF binding or server uniqueness changed')


def operate(job, action, authority, client, ledger):
    reader = AllocationReader(job, authority, client)
    require(action in ACTIONS, 'Unknown IPAM action')
    call, check, observed = reader.call, reader.check, reader.observed
    with allocation_lock(ledger, job) as directory:
        head_path = directory / 'head.json'
        head = load_private(head_path) if head_path.exists() else None
        if head and head['status'] == 'OUTCOME_UNKNOWN':
            require(action == 'reconcile', 'Uncertain IPAM mutation requires read-only reconciliation')
        reader.namespace()
        row, etag = observed()
        if action == 'reconcile':
            require(row is not None, 'No completed allocation observed; keep uncertainty hold')
            # Only the intended completed outcome clears an uncertainty hold.
            if head and head['status'] == 'OUTCOME_UNKNOWN':
                require(check(row) == head['desired_status'], 'Mutation completion remains uncertain')
        elif action == 'reserve' and row is not None:
            require(check(row) in {'reserved', 'active'}, 'Retired addresses cannot be reused')
        else:
            desired = {'reserve': 'reserved', 'confirm': 'active', 'retire': 'deprecated'}[action]
            require(action == 'reserve' or row is not None, 'Existing owned allocation required')
            if row is None or check(row) != desired:
                if row is not None:
                    require(check(row) in {'reserved', 'active'} and etag, 'Conditional update of live allocation required')
                attempt = {'status': 'OUTCOME_UNKNOWN', 'action': action, 'desired_status': desired,
                           'request_sha256': digest(encoded(job)), 'started_at': utcnow().isoformat()}
                # Immutable attempt first; even a lost successful POST cannot be retried.
                write_new(directory / (action + '.started.json'), encoded(attempt))
                replace_private(head_path, encoded(attempt))
                if row is None:
                    call('POST', '/api/ipam/ip-addresses/', dict(address=job['address'], vrf=job['vrf_id'],
                         tenant=job['tenant_id'], status='reserved', custom_fields=refs(job)))
                else:
                    call('PATCH', f"/api/ipam/ip-addresses/{row['id']}/", {'status': desired}, etag=etag)
                row, etag = observed()
                require(row is not None and check(row) == desired, 'IPAM mutation not observed complete')
        result = {'format': 'hosting-netbox-receipt/1', 'status': 'OBSERVED', 'allocation_status': check(row),
                  'request_sha256': digest(encoded(job)), 'scope': job['scope'], 'member': job['member'],
                  'address': job['address'], 'native_id': row['id'], 'etag': etag,
                  'observed_at': utcnow().isoformat(), 'reusable': False}
        replace_private(head_path, encoded(result))
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('request', type=Path)
    parser.add_argument('--action', choices=sorted(ACTIONS), required=True)
    parser.add_argument('--authority', type=Path)
    parser.add_argument('--token-file', type=Path)
    parser.add_argument('--ca-bundle', type=Path)
    parser.add_argument('--ledger', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    try:
        job = load_private(args.request)
        validate(job)
        if not args.execute:
            print('{"status":"VALIDATED_NO_CONTACT"}')
            return 0
        require(all([args.authority, args.token_file, args.ledger, args.output]), 'Private execution inputs required')
        require(not args.output.exists(), 'Receipt output already exists')
        private_path(args.output.parent, directory=True)
        token_bytes = read_private(args.token_file)
        ca_bytes = read_private(args.ca_bundle) if args.ca_bundle else None
        authority = load_private(args.authority)
        validate_authority(job, args.action, authority, token_bytes, ca_bytes)
        token = token_bytes.decode().strip()
        require(re.fullmatch(r'nbt_[A-Za-z0-9]+\.[A-Za-z0-9]+', token), 'Scoped NetBox v2 token required')
        client = JsonService(job['origin'], 'Bearer ' + token, args.ca_bundle)
        result = operate(job, args.action, authority, client, args.ledger)
        write_new(args.output, encoded(result))
        print(json.dumps({'status': result['status'], 'allocation_status': result['allocation_status']}))
        return 0
    except OperatorError as exc:
        print(json.dumps({'status': 'STOPPED', 'reason': str(exc)}))
        return 2
    except (OSError, ValueError, TypeError, KeyError):
        print('{"status":"STOPPED","reason":"Inspect the private IPAM ledger; do not retry uncertain writes"}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
