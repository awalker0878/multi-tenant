#!/usr/bin/env python3
"""Reserve, confirm, reconcile, retire, quarantine and release one NetBox 4.7 allocation.

No automatic free-address selection, deletion, retry or reuse. Retirement is
followed by a declared reuse quarantine over completed dependent cleanup, and a
released address is only re-reserved by a fresh explicit allocation decision.
The shared durable ledger and service-side VRF uniqueness are both required.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta
import fcntl
import ipaddress
import json
import os
from pathlib import Path
import re
from urllib.parse import urlencode, urlsplit

from provisioner.compiler.wsd import identity
from provisioner.execution.neutron_observe import strict_loads
from provisioner.execution.run_files import (current_window, digest, encoded, load_private, private_path,
                             read_private, replace_private, require, utcnow, write_new, OperatorError)
from provisioner.execution.service_http import JsonService

ACTIONS = {'reserve', 'confirm', 'reconcile', 'retire', 'quarantine', 'release'}
RELEASE_ACTIONS = {'quarantine', 'release'}
RETIREMENT_ACTIONS = RELEASE_ACTIONS | {'retire'}
# Release cleanup mirrors the exported allocation record so live and exported
# reuse evidence stay comparable; only the owner can accept external cleanup.
CLEANUP_CATEGORIES = {'routes', 'dhcp_leases', 'dns', 'policy', 'logging_attribution', 'incident_response'}
CLEANUP_STATES = {'NOT_STARTED', 'PENDING', 'COMPLETE', 'NOT_APPLICABLE'}
COMPLETE_STATES = {'COMPLETE', 'NOT_APPLICABLE'}
RELEASE_EVIDENCE = 'hosting-netbox-release-evidence/1'
QUARANTINE_RECEIPT = 'hosting-netbox-quarantine/1'
RELEASE_RECEIPT = 'hosting-netbox-release/1'
MAX_QUARANTINE_SECONDS = 31536000
REFERENCE = re.compile(r'[A-Za-z0-9:._/-]{3,200}')


def instant(value, message):
    require(isinstance(value, str) and value.strip(), message)
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise OperatorError(message) from None
    require(result.tzinfo is not None, message)
    return result


def validate_cleanup(cleanup):
    """Normalize the six dependent cleanup categories of the exported record.

    Routes, DHCP, DNS, policy, logging attribution and incident response stay
    under their own service owners. Only bounded references and observation
    times cross this boundary; this adapter never performs that cleanup.
    """
    require(isinstance(cleanup, dict) and set(cleanup) == CLEANUP_CATEGORIES,
            'Every dependent cleanup category must be declared')
    normalized = {}
    for key, item in cleanup.items():
        require(isinstance(item, dict) and set(item) == {'status', 'evidence_ref', 'observed_at'},
                'Dependent cleanup evidence shape invalid')
        require(item['status'] in CLEANUP_STATES, 'Unknown dependent cleanup status')
        if item['status'] == 'NOT_STARTED':
            require(item['evidence_ref'] is None and item['observed_at'] is None,
                    'NOT_STARTED cleanup cannot claim evidence')
            normalized[key] = {'status': 'NOT_STARTED', 'evidence_ref': None, 'observed_at': None}
            continue
        require(isinstance(item['evidence_ref'], str) and REFERENCE.fullmatch(item['evidence_ref']),
                'Started cleanup requires an accepted external evidence reference')
        normalized[key] = {'status': item['status'], 'evidence_ref': item['evidence_ref'],
                           'observed_at': instant(item['observed_at'],
                                                  'Dependent cleanup observation time required').isoformat()}
    return normalized


def cleanup_complete(cleanup):
    return all(item['status'] in COMPLETE_STATES for item in cleanup.values())


def validate_release_evidence(job, raw):
    """Bind one immutable reuse-quarantine declaration to this exact allocation."""
    require(isinstance(raw, (bytes, bytearray)) and len(raw) < 65536,
            'Bounded private reuse quarantine evidence required')
    value = strict_loads(bytes(raw))
    require(isinstance(value, dict) and set(value) == {'format', 'request_sha256', 'change_ref',
            'duration_seconds', 'cleanup', 'declared_at'}, 'Exact reuse quarantine declaration required')
    require(value['format'] == RELEASE_EVIDENCE and value['request_sha256'] == digest(encoded(job)),
            'Reuse quarantine declaration does not bind this exact allocation')
    require(isinstance(value['change_ref'], str) and REFERENCE.fullmatch(value['change_ref']),
            'Accepted reuse and cleanup procedure reference required')
    duration = value['duration_seconds']
    require(type(duration) is int and 0 < duration <= MAX_QUARANTINE_SECONDS,
            'Bounded reuse quarantine duration required')
    cleanup = validate_cleanup(value['cleanup'])
    require(cleanup_complete(cleanup),
            'Reuse quarantine requires every dependent cleanup completed or not applicable')
    declared = instant(value['declared_at'], 'Reuse quarantine declaration time required')
    return {'change_ref': value['change_ref'], 'declared_at': declared.isoformat(),
            'duration_seconds': duration,
            'reuse_not_before': (declared + timedelta(seconds=duration)).isoformat(),
            'cleanup': cleanup, 'evidence_sha256': digest(raw)}


def require_current_declaration(declaration, authority):
    """The declaration and every cleanup observation must be current, not replayed."""
    since = instant(authority['valid_from'], 'Authority start required')
    declared = instant(declaration['declared_at'], 'Reuse quarantine declaration time required')
    require(since <= declared <= utcnow(),
            'Declare the reuse quarantine and its cleanup inside the current authority window')
    for item in declaration['cleanup'].values():
        if item['observed_at'] is not None:
            require(since <= instant(item['observed_at'], 'Dependent cleanup observation time required') <= declared,
                    'Dependent cleanup evidence must be observed inside the current authority window')


SELECTION_FIELDS = frozenset({'format', 'origin', 'scope', 'member',
                             'tenant_id', 'vrf_id', 'prefix_id', 'prefix', 'address'})


def validate_selection(selected):
    """Parse pre-admission address intent without a runtime owner or authority.

    This pure parser performs no TLS, service contact, identity construction,
    reservation or enrollment. Effects still require the complete job parser
    and current allocation authority.
    """
    require(isinstance(selected,dict) and selected.keys()==SELECTION_FIELDS,
            'Invalid IPAM selection fields')
    require(selected['format'] == 'hosting-netbox-allocation/1', 'Unknown IPAM request')
    require(isinstance(selected['scope'],dict) and set(selected['scope']) ==
            {'environment_key', 'site_key', 'platform', 'tenant_key', 'wsd_key'},
            'Complete IPAM scope required')
    for value in [*selected['scope'].values(), selected['member']]:
        identity(value)
    require(selected['scope']['platform'] in {'nutanix', 'vmware', 'openstack'}, 'Unknown platform')
    for field in ('tenant_id', 'vrf_id', 'prefix_id'):
        require(type(selected[field]) is int and selected[field] > 0, 'Positive native ID/generation required')
    network = ipaddress.ip_network(selected['prefix'], strict=True)
    address = ipaddress.ip_interface(selected['address'])
    require(str(address) == selected['address'] and address.network == network and network.version == 4
            and network.prefixlen <= 30 and address.ip not in {network.network_address, network.broadcast_address}
            and not (address.ip.is_multicast or address.ip.is_loopback or address.ip.is_unspecified
                     or address.ip.is_link_local), 'Explicit usable IPv4 allocation in the accepted prefix required')
    origin=urlsplit(selected['origin'])
    require(origin.scheme=='https' and origin.hostname and origin.path in {'','/'}
            and not origin.username and not origin.password and not origin.query and not origin.fragment,
            'Explicit HTTPS service origin required')
    require(origin.port is None or 0<origin.port<=65535,'Explicit HTTPS service port required')
    return digest(encoded(selected))


def validate(job):
    require(isinstance(job,dict) and job.keys()==SELECTION_FIELDS|{'operation_id','generation','reservation_ref'},
            'Invalid IPAM request fields')
    validate_selection({key:job[key] for key in SELECTION_FIELDS})
    identity(job['operation_id'])
    require(type(job['generation']) is int and job['generation']>0,'Positive native ID/generation required')
    require(isinstance(job['reservation_ref'], str) and re.fullmatch(r'[A-Za-z0-9:._/-]{3,200}', job['reservation_ref']),
            'External capacity/address allocation authority required')
    return digest(encoded(job))


def validate_authority(job, action, authority, token_bytes, ca_bytes, evidence_bytes=None):
    require(action in ACTIONS and set(authority) == {'request_sha256', 'action', 'valid_from',
            'valid_until', 'change_ref', 'cleanup_ref', 'evidence_sha256', 'token_sha256',
            'ca_sha256'}, 'Invalid IPAM authority')
    require(authority['request_sha256'] == validate(job) and authority['action'] == action,
            'IPAM authority does not match the exact operation')
    require(authority['token_sha256'] == digest(token_bytes)
            and authority['ca_sha256'] == (digest(ca_bytes) if ca_bytes is not None else None)
            and authority['evidence_sha256'] == (digest(evidence_bytes) if evidence_bytes is not None else None),
            'IPAM credential, trust or reuse-quarantine evidence binding changed')
    require((evidence_bytes is not None) == (action in RELEASE_ACTIONS),
            'Reuse quarantine evidence is required exactly for quarantine and release')
    require(action in RETIREMENT_ACTIONS or authority['cleanup_ref'] is None,
            'Completed dependent cleanup reference is only valid for retirement or release')
    for value in [authority['change_ref']] + ([authority['cleanup_ref']] if action in RETIREMENT_ACTIONS else []):
        require(isinstance(value, str) and REFERENCE.fullmatch(value),
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


def require_dns_cleanup(directory, job, authority):
    """Gate retirement on current completed cleanup of every managed DNS slot.

    Caller holds the shared allocation lock. Native DNS permissions/fencing and
    cleanup outside this ledger remain the service owner's responsibility.
    """
    current_window(authority)
    since = datetime.fromisoformat(authority['valid_from'].replace('Z', '+00:00'))
    for slot in sorted(directory.glob('dns-*')):
        private_path(slot, directory=True)
        parent = load_private(slot / 'attempt.json')
        attempt = load_private(slot / 'withdrawal-attempt.json')
        latest = slot / 'withdrawal-reconciliation.json'
        reconciled = latest.exists() or latest.is_symlink()
        result = load_private(latest if reconciled else slot / 'withdrawal-transaction.json')
        require(isinstance(parent, dict) and isinstance(attempt, dict) and isinstance(result, dict),
                'Managed DNS cleanup records are invalid')
        for record, fields in [(parent, ('binding_sha256',)), (attempt, ('binding_sha256',
                'registration_binding_sha256', 'request_sha256', 'job_sha256', 'scope_sha256'))]:
            require(all(isinstance(record.get(key), str) and re.fullmatch(r'[0-9a-f]{64}', record[key])
                        for key in fields), 'Managed DNS cleanup binding is missing')
        native = result.get('dns')
        require(attempt['registration_binding_sha256'] == parent['binding_sha256']
                and attempt['request_sha256'] == digest(encoded(job))
                and result.get('format') == 'hosting-netbox-dns-receipt/1'
                and result.get('action') == ('reconcile-withdrawal' if reconciled else 'withdraw')
                and result.get('status') == 'AUTHORITATIVE_TOMBSTONE_OBSERVED'
                and result.get('binding_sha256') == attempt['binding_sha256']
                and result.get('registration_binding_sha256') == parent['binding_sha256']
                and result.get('reusable') is False and result.get('activation_authorized') is False
                and isinstance(native, dict) and native.get('activation_authorized') is False
                and native.get('status') in {'APPLIED_OBSERVED', 'ALREADY_APPLIED_OBSERVED', 'RECONCILED_APPLIED_OBSERVED'}
                and native.get('job_sha256') == attempt['job_sha256']
                and native.get('scope_sha256') == attempt['scope_sha256'],
                'Managed DNS cleanup is unresolved or belongs to another attempt')
        observed = datetime.fromisoformat(native.get('observed_at', native.get('finished_at', '')).replace('Z', '+00:00'))
        finished = datetime.fromisoformat(result.get('finished_at', '').replace('Z', '+00:00'))
        require(observed.tzinfo is not None and finished.tzinfo is not None
                and since <= observed <= finished <= utcnow(),
                'Reobserve DNS tombstones within the current IPAM retirement authority window')


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


def release(directory, job, action, authority, evidence, head, row, etag, native_status):
    """Declare, then elapse, the reuse quarantine over completed dependent cleanup.

    Caller holds the shared allocation lock and has already read the native
    allocation and its dependent cleanup. Retirement is never undone: the native
    row stays `deprecated`, this adapter never deletes or frees it, and later
    reuse remains a new explicit allocation decision by the address authority.
    """
    request_sha256 = digest(encoded(job))
    lifecycle = head.get('allocation_status') if isinstance(head, dict) else None
    require(native_status == 'deprecated' and lifecycle in {'deprecated', 'QUARANTINED', 'RELEASED'},
            'A completed retirement of this allocation is required before quarantine or release')
    quarantine_path, release_path = directory / 'quarantine.json', directory / 'release.json'
    # The declaration is re-presented and re-validated for both halves of the
    # procedure, so the elapsed reuse boundary is proved by the accepted evidence
    # and never by a mutable timestamp recorded beside it.
    declaration = validate_release_evidence(job, evidence)
    if action == 'quarantine':
        # Declaring the quarantine is a decision taken now, inside this authority window.
        require_current_declaration(declaration, authority)
        require(not release_path.exists(), 'A released address cannot be re-quarantined')
        if quarantine_path.exists():
            record = load_private(quarantine_path)
            require(isinstance(record, dict) and record.get('format') == QUARANTINE_RECEIPT
                    and record.get('request_sha256') == request_sha256
                    and record.get('evidence_sha256') == declaration['evidence_sha256']
                    and record.get('reuse_not_before') == declaration['reuse_not_before'],
                    'A different reuse quarantine is already declared for this address')
        else:
            record = {'format': QUARANTINE_RECEIPT, 'request_sha256': request_sha256, **declaration}
            write_new(quarantine_path, encoded(record))
        reusable, released_at = False, None
    else:
        require(quarantine_path.exists(), 'A declared reuse quarantine is required before release')
        record = load_private(quarantine_path)
        require(isinstance(record, dict) and record.get('format') == QUARANTINE_RECEIPT
                and record.get('request_sha256') == request_sha256
                and record.get('evidence_sha256') == declaration['evidence_sha256']
                and record.get('declared_at') == declaration['declared_at']
                and record.get('duration_seconds') == declaration['duration_seconds']
                and record.get('change_ref') == declaration['change_ref']
                and record.get('reuse_not_before') == declaration['reuse_not_before']
                and isinstance(record.get('cleanup'), dict)
                and cleanup_complete(validate_cleanup(record['cleanup'])),
                'The declared reuse quarantine does not bind this allocation')
        reusable, released_at = True, None
        if release_path.exists():
            released_at = instant(load_private(release_path).get('released_at'),
                                  'Recorded release time required')
            require(released_at >= instant(declaration['reuse_not_before'], 'Reuse boundary required'),
                    'The recorded release precedes the declared reuse boundary')
        else:
            released_at = utcnow()
            require(released_at >= instant(declaration['reuse_not_before'], 'Reuse boundary required'),
                    'The declared reuse quarantine has not elapsed')
            write_new(release_path, encoded({'format': RELEASE_RECEIPT, 'request_sha256': request_sha256,
                       'quarantine_sha256': digest(encoded(record)), 'change_ref': record['change_ref'],
                       'reuse_not_before': record['reuse_not_before'],
                       'released_at': released_at.isoformat(), 'cleanup': record['cleanup']}))
    receipt = {'format': RELEASE_RECEIPT if action == 'release' else QUARANTINE_RECEIPT, 'status': 'OBSERVED',
               'allocation_status': 'RELEASED' if action == 'release' else 'QUARANTINED',
               'action': action, 'request_sha256': request_sha256, 'scope': job['scope'],
               'member': job['member'], 'address': job['address'], 'native_id': row['id'], 'etag': etag,
               'observed_at': utcnow().isoformat(), 'reusable': reusable,
               'reuse_not_before': declaration['reuse_not_before'],
               'released_at': released_at.isoformat() if released_at else None,
               'cleanup': declaration['cleanup']}
    # head.json becomes the terminal lifecycle receipt; dependent services that
    # require the exact confirmed-allocation receipt fail closed from here on.
    replace_private(directory / 'head.json', encoded(receipt))
    return receipt


def operate(job, action, authority, client, ledger, evidence=None):
    reader = AllocationReader(job, authority, client)
    require(action in ACTIONS, 'Unknown IPAM action')
    require((evidence is not None) == (action in RELEASE_ACTIONS),
            'Reuse quarantine evidence is required exactly for quarantine and release')
    call, check, observed = reader.call, reader.check, reader.observed
    with allocation_lock(ledger, job) as directory:
        head_path = directory / 'head.json'
        head = load_private(head_path) if head_path.exists() else None
        if head and head['status'] == 'OUTCOME_UNKNOWN':
            require(action == 'reconcile', 'Uncertain IPAM mutation requires read-only reconciliation')
        if action in {'retire', 'quarantine'}:
            require_dns_cleanup(directory, job, authority)
        if action == 'retire':
            require(not (directory / 'quarantine.json').exists(),
                    'A declared reuse quarantine cannot be re-retired')
        reader.namespace()
        row, etag = observed()
        if action == 'reconcile':
            require(row is not None, 'No completed allocation observed; keep uncertainty hold')
            # Only the intended completed outcome clears an uncertainty hold.
            if head and head['status'] == 'OUTCOME_UNKNOWN':
                require(check(row) == head['desired_status'], 'Mutation completion remains uncertain')
        elif action in RELEASE_ACTIONS:
            return release(directory, job, action, authority, evidence, head, row, etag,
                           check(row) if row is not None else None)
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
    parser.add_argument('--release-evidence', type=Path)
    parser.add_argument('--token-file', type=Path)
    parser.add_argument('--ca-bundle', type=Path)
    parser.add_argument('--ledger', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    try:
        job = load_private(args.request)
        validate(job)
        evidence = read_private(args.release_evidence) if args.release_evidence else None
        require((evidence is not None) == (args.action in RELEASE_ACTIONS),
                'Reuse quarantine evidence is required exactly for quarantine and release')
        if evidence is not None:
            validate_release_evidence(job, evidence)
        if not args.execute:
            print('{"status":"VALIDATED_NO_CONTACT"}')
            return 0
        require(all([args.authority, args.token_file, args.ledger, args.output]), 'Private execution inputs required')
        require(not args.output.exists(), 'Receipt output already exists')
        private_path(args.output.parent, directory=True)
        token_bytes = read_private(args.token_file)
        ca_bytes = read_private(args.ca_bundle) if args.ca_bundle else None
        authority = load_private(args.authority)
        validate_authority(job, args.action, authority, token_bytes, ca_bytes, evidence)
        token = token_bytes.decode().strip()
        require(re.fullmatch(r'nbt_[A-Za-z0-9]+\.[A-Za-z0-9]+', token), 'Scoped NetBox v2 token required')
        client = JsonService(job['origin'], 'Bearer ' + token, args.ca_bundle)
        result = operate(job, args.action, authority, client, args.ledger, evidence)
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
