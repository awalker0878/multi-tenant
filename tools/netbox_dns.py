#!/usr/bin/env python3
"""Register one scoped A or PTR record from a confirmed NetBox IPv4 allocation.

The existing RFC 2136/TSIG writer owns DNS. This adapter supplies current IPAM
preconditions and a shared write-once attempt; recovery only reads native state.
Default CLI use validates private inputs without contacting either service.
"""
import argparse
from datetime import datetime, timedelta
import ipaddress
import json
from pathlib import Path
import re
import sys

import dns.exception

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import dns_change as dns_writer
from tools.netbox_ipam import AllocationReader, allocation_lock, refs, validate as validate_allocation
from tools.run_files import (current_window, digest, encoded, load_private, private_path,
                             read_private, replace_private, require, sync_directory, utcnow, write_new)
from tools.service_http import JsonService


def resource_id(allocation):
    return 'ipam-' + refs(allocation)['hosting_owner'][:48]


def confirmed(allocation, receipt):
    require(isinstance(receipt, dict) and set(receipt) == {
        'format', 'status', 'allocation_status', 'request_sha256', 'scope', 'member',
        'address', 'native_id', 'etag', 'observed_at', 'reusable'}, 'Exact native IPAM receipt required')
    require(receipt['format'] == 'hosting-netbox-receipt/1' and receipt['status'] == 'OBSERVED'
            and receipt['allocation_status'] == 'active' and receipt['reusable'] is False
            and receipt['request_sha256'] == validate_allocation(allocation)
            and receipt['scope'] == allocation['scope'] and receipt['member'] == allocation['member']
            and receipt['address'] == allocation['address']
            and type(receipt['native_id']) is int and receipt['native_id'] > 0,
            'DNS requires the exact confirmed allocation and native identity')
    require(isinstance(receipt['etag'], str) and receipt['etag'] not in {'', '*'}
            and not any(c in receipt['etag'] for c in '\r\n'), 'Confirmed native revision required')
    when = datetime.fromisoformat(receipt['observed_at'].replace('Z', '+00:00'))
    require(when.tzinfo is not None and when <= utcnow(), 'Invalid IPAM observation time')
    # A later read-only IPAM reconciliation may refresh only the observation time.
    return {k: v for k, v in receipt.items() if k != 'observed_at'}


def validate(allocation, receipt, job, scope, *, action='register', fixture=False):
    confirmed(allocation, receipt)
    require(action in {'register', 'reconcile'}, 'Unknown DNS/IPAM action')
    validation_time = utcnow()
    if action == 'reconcile':
        # Historical deadlines constrain writes. A new, exact read authority may
        # inspect the original attempt after expiry without editing its inputs.
        deadlines = [datetime.fromisoformat(value['valid_until'].replace('Z', '+00:00'))
                     for value in (job, scope)]
        require(all(value.tzinfo is not None for value in deadlines), 'Timezone required')
        validation_time = min(validation_time, *deadlines) - timedelta(microseconds=1)
    dns_writer.validate(job, scope, now=validation_time, fixture=fixture)
    require(job['tenant_id'] == allocation['scope']['tenant_key']
            and job['resource_id'] == resource_id(allocation), 'DNS owner must bind the complete IPAM scope/member')
    require(job['previous_marker'] is None and len(job['records']) == 1,
            'This adapter supports one initial A or PTR registration only')
    record = job['records'][0]
    require(record['before'] is None and record['after'] is not None,
            'Updates, deletion and reuse need a separate DNS owner workflow')
    ip = ipaddress.ip_interface(allocation['address']).ip
    values = record['after']['values']
    require((record['type'] == 'A' and values == [str(ip)])
            or (record['type'] == 'PTR' and record['name'] == ip.reverse_pointer + '.' and len(values) == 1),
            'DNS record must describe the exact confirmed IPv4 address')
    require(scope['allowed_records'][0]['values'] == values, 'DNS authority must allow only the selected value')
    return digest(encoded({'allocation': allocation, 'confirmation': receipt, 'job': job, 'scope': scope}))


def validate_authority(binding, action, authority, token, ca, secret):
    require(isinstance(authority, dict) and set(authority) == {
        'format', 'binding_sha256', 'action', 'valid_from', 'valid_until', 'change_ref',
        'token_sha256', 'ca_sha256', 'tsig_sha256'}, 'Exact DNS/IPAM contact authority required')
    require(authority['format'] == 'hosting-netbox-dns-authority/1'
            and authority['binding_sha256'] == binding and authority['action'] == action
            and action in {'register', 'reconcile'}, 'DNS/IPAM authority changed')
    require(authority['token_sha256'] == digest(token)
            and authority['ca_sha256'] == (digest(ca) if ca is not None else None)
            and authority['tsig_sha256'] == digest(secret), 'DNS/IPAM credential or trust binding changed')
    require(isinstance(authority['change_ref'], str)
            and re.fullmatch(r'[A-Za-z0-9:._/-]{3,200}', authority['change_ref']), 'External change reference required')
    current_window(authority)


class AuthorizedDNSClient(dns_writer.Client):
    """Use the existing signed transport with a current window for every query."""
    def __init__(self, client, authority):
        self.client, self.authority = client, authority
        self.server, self.port, self.key_name = client.server, client.port, client.key_name

    def exchange(self, message):
        current_window(self.authority)
        return self.client.exchange(message)


def operate(allocation, receipt, job, scope, authority, ipam_client, dns_client, ledger,
            *, action, fixture=False):
    binding = validate(allocation, receipt, job, scope, action=action, fixture=fixture)
    require(action in {'register', 'reconcile'}, 'Unknown DNS/IPAM action')
    require(job['enabled'] and scope['enabled'], 'Disabled DNS inputs cannot contact services')
    require((dns_client.server, dns_client.port, dns_client.key_name)
            == (job['server'], job['port'], job['key_name']), 'DNS transport changed')
    current_window(authority)
    dns_client = AuthorizedDNSClient(dns_client, authority)
    reader = AllocationReader(allocation, authority, ipam_client)
    identity = confirmed(allocation, receipt)
    with allocation_lock(ledger, allocation) as directory:
        require(confirmed(allocation, load_private(directory / 'head.json')) == identity,
                'Current IPAM ledger no longer matches the confirmed allocation')
        # Endpoint, key, UUID, output path or intent changes cannot bypass a zone's
        # existing attempt for this allocation owner. Forward/reverse are separate.
        slot = directory / ('dns-' + digest(encoded([job['zone'], job['resource_id']])))
        if action == 'register':
            slot.mkdir(mode=0o700, exist_ok=True)
            private_path(slot, directory=True)
            sync_directory(directory)
            write_new(slot / 'attempt.json', encoded({'binding_sha256': binding, 'started_at': utcnow().isoformat()}))
        else:
            private_path(slot, directory=True)
            require(load_private(slot / 'attempt.json')['binding_sha256'] == binding,
                    'Reconciliation must retain the exact original DNS/IPAM inputs')
        head = {'format': 'hosting-netbox-dns-receipt/1', 'binding_sha256': binding,
                'action': action, 'status': 'DNS_REGISTRATION_HELD', 'dns': None,
                'activation_authorized': False, 'reusable': False}
        # Keep the last transaction journal on recovery; read-only observations
        # must not erase the original UPDATE_PENDING or lost-response evidence.
        output_path = slot / ('transaction.json' if action == 'register' else 'reconciliation.json')
        replace_private(output_path, encoded(head))

        def refresh():
            reader.namespace()
            row, etag = reader.observed()
            require(row is not None and reader.check(row) == 'active'
                    and row['id'] == receipt['native_id'] and etag == receipt['etag'],
                    'Current native IPAM confirmation or revision changed')
            current_window(authority)
            validate(allocation, receipt, job, scope, action=action, fixture=fixture)

        def record(report):
            head['dns'] = report
            replace_private(output_path, encoded(head))
            if report['status'] == 'UPDATE_PENDING' and report['events'][-1]['stage'] == 'UPDATE_PENDING':
                # Called after durable reservation and immediately before send.
                refresh()

        try:
            refresh()
            if action == 'register':
                result = dns_writer.change(job, scope, dns_client, execute=True, fixture=fixture, record=record)
            else:
                observed = dns_writer.snapshot(job, dns_client)
                result = {'kind': 'SCOPED_DNS_OBSERVATION', 'job_sha256': dns_writer.digest(job),
                          'scope_sha256': dns_writer.digest(scope), 'update_attempts': 0,
                          'status': 'ALREADY_APPLIED_OBSERVED' if dns_writer.matches(observed, job, 'after')
                                    else 'DNS_STATE_NOT_RECONCILED',
                          'observation_sha256': dns_writer.digest(observed), 'observed_at': utcnow().isoformat(),
                          'activation_authorized': False}
                record(result)
            refresh()
            if result['status'] in dns_writer.STATES:
                head['status'] = 'AUTHORITATIVE_REGISTRATION_OBSERVED'
            head['finished_at'] = utcnow().isoformat()
            replace_private(output_path, encoded(head))
            return head
        except (OSError, ValueError, TypeError, KeyError, AttributeError, dns.exception.DNSException) as exc:
            head['status'] = 'DNS_REGISTRATION_HELD'
            head['error_class'] = type(exc).__name__
            replace_private(output_path, encoded(head))
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('allocation', 'confirmation', 'job', 'scope'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--action', choices=['register', 'reconcile'], required=True)
    for name in ('authority', 'token-file', 'ca-bundle', 'tsig-file', 'ledger', 'output'):
        parser.add_argument('--' + name, type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    try:
        allocation, receipt, job, scope = [load_private(getattr(args, key))
                                          for key in ('allocation', 'confirmation', 'job', 'scope')]
        binding = validate(allocation, receipt, job, scope, action=args.action)
        if not args.execute:
            print(json.dumps({'status': 'VALIDATED_NO_CONTACT', 'binding_sha256': binding}))
            return 0
        require(all([args.authority, args.token_file, args.tsig_file, args.ledger, args.output]),
                'Private authority, credentials, shared ledger and new output required')
        private_path(args.output.parent, directory=True)
        require(not args.output.exists(), 'Output already exists')
        token, secret = read_private(args.token_file), read_private(args.tsig_file)
        ca = read_private(args.ca_bundle) if args.ca_bundle else None
        authority = load_private(args.authority)
        validate_authority(binding, args.action, authority, token, ca, secret)
        require(re.fullmatch(r'nbt_[A-Za-z0-9]+\.[A-Za-z0-9]+', token.decode().strip()),
                'Scoped NetBox v2 token required')
        ipam_client = JsonService(allocation['origin'], 'Bearer ' + token.decode().strip(), args.ca_bundle)
        dns_client = dns_writer.Client(job['server'], job['port'], job['key_name'], secret.decode().strip())
        result = operate(allocation, receipt, job, scope, authority, ipam_client, dns_client,
                         args.ledger, action=args.action)
        write_new(args.output, encoded(result))
        print(json.dumps({'status': result['status'], 'activation_authorized': False}))
        return 0 if result['status'] == 'AUTHORITATIVE_REGISTRATION_OBSERVED' else 2
    except (OSError, ValueError, TypeError, KeyError, AttributeError, dns.exception.DNSException):
        print('{"status":"STOPPED","reason":"Inspect private IPAM/DNS ledgers; do not retry registration"}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
