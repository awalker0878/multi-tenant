#!/usr/bin/env python3
"""Read exact DNS generations from selected authenticated authority/resolver views.

No UPDATE, cache flush, discovery, address release or ownership change is issued.
"""
import argparse
from datetime import timedelta
import ipaddress
import json
from pathlib import Path
import sys
import time

import dns.exception
import dns.flags
import dns.message
import dns.name
import dns.rcode
import dns.rdataclass
import dns.rdatatype

from hosting_resources import SOURCE_ROOT
ROOT = SOURCE_ROOT
from provisioner.execution import readback_core as c
from provisioner.execution import dns_change as writer
from provisioner.execution.run_files import (current_window, digest, encoded, load_private, require,
                             utcnow, write_new)

STATUS = 'SELECTED_DNS_VIEWS_OBSERVED_REQUIRES_ACCEPTANCE'


def validate(config, job, scope, receipt, secrets, *, fixture=False, current=True):
    c.exact_keys(config, {'format', 'job_sha256', 'scope_sha256', 'receipt_sha256',
        'observer_machine_id', 'network_namespace_inode', 'valid_from', 'valid_until',
        'observation_ref', 'max_seconds', 'targets'})
    require(config['format'] == 'hosting-dns-propagation/1'
            and config['job_sha256'] == c.digest(job) and config['scope_sha256'] == c.digest(scope)
            and config['receipt_sha256'] == c.digest(receipt), 'Exact original DNS handoff required')
    current_window(config, now=None if current else c.timestamp(config['valid_from']))
    c.text(config['observation_ref'])
    require(isinstance(config['observer_machine_id'], str) and len(config['observer_machine_id']) == 32
            and all(x in '0123456789abcdef' for x in config['observer_machine_id']), 'Exact observer machine required')
    require(type(config['network_namespace_inode']) is int and config['network_namespace_inode'] > 0,
            'Exact observer network namespace required')
    require(type(config['max_seconds']) is int and 1 <= config['max_seconds'] <= 300,
            'Bounded observation duration required')
    # A read can inspect a historical write without renewing permission to UPDATE.
    validation_time = min(utcnow(), c.timestamp(job['valid_until']), c.timestamp(scope['valid_until'])) - timedelta(microseconds=1)
    writer.validate(job, scope, now=validation_time, fixture=fixture)
    require(job['enabled'] and scope['enabled'], 'Disabled DNS handoff cannot contact services')
    native = receipt.get('dns', {})
    deleted = all(r['after'] is None for r in job['records'])
    require(receipt.get('format') == 'hosting-netbox-dns-receipt/1'
            and receipt.get('status') == ('AUTHORITATIVE_TOMBSTONE_OBSERVED' if deleted else 'AUTHORITATIVE_REGISTRATION_OBSERVED')
            and receipt.get('activation_authorized') is False and receipt.get('reusable') is False
            and isinstance(native, dict) and native.get('status') in writer.STATES
            and native.get('job_sha256') == c.digest(job) and native.get('scope_sha256') == c.digest(scope),
            'Completed exact primary DNS observation required')
    targets = config['targets']
    require(isinstance(targets, list) and 3 <= len(targets) <= 16, 'Primary, secondary and recursive targets required')
    ids, transports, roles = set(), set(), []
    for target in targets:
        c.exact_keys(target, {'id', 'role', 'server', 'port', 'key_name', 'tsig_sha256',
                             'view_ref', 'control_name', 'control_value'})
        c.identifier(target['id']); c.text(target['view_ref'])
        require(target['role'] in {'primary', 'secondary', 'recursive'}, 'Unknown DNS observer role')
        address = ipaddress.ip_address(target['server'])
        require(str(address) == target['server'] and not address.is_unspecified and not address.is_multicast
                and not address.is_link_local, 'Explicit DNS observer address required')
        if fixture:
            require(address.is_loopback, 'Fixture DNS observation is loopback only')
        else:
            writer.address(target['server'], address.version)
        require(type(target['port']) is int and 1 <= target['port'] <= 65535, 'Exact DNS observer port required')
        writer.fqdn(target['key_name']); writer.fqdn(target['control_name'])
        require(dns.name.from_text(target['control_name']).is_subdomain(dns.name.from_text(job['zone']))
                and target['control_name'] != job['zone']
                and target['control_name'] not in {r['name'] for r in job['records']},
                'Independent positive control must belong to the exact zone')
        require(isinstance(target['control_value'], str) and 1 <= len(target['control_value']) <= 200
                and all(32 <= ord(x) <= 126 for x in target['control_value']), 'Bounded positive TXT control required')
        endpoint = (target['server'], target['port'], target['key_name'])
        require(target['id'] not in ids and endpoint not in transports, 'Duplicate DNS observation target')
        is_primary = (target['server'], target['port']) == (job['server'], job['port'])
        require(is_primary if target['role'] == 'primary' else not is_primary,
                'Primary and propagated views must be independently addressed')
        ids.add(target['id']); transports.add(endpoint); roles.append(target['role'])
    require(roles.count('primary') == 1 and {'secondary', 'recursive'} <= set(roles),
            'One primary and all selected secondary/recursive views are required')
    c.exact_keys(secrets, ids)
    for target in targets:
        secret = secrets[target['id']]
        require(isinstance(secret, str) and digest(secret.encode()) == target['tsig_sha256'],
                'DNS observation key changed')
        # Validate every key before opening any connection.
        writer.Client(target['server'], target['port'], target['key_name'], secret)


class Client(writer.Client):
    def __init__(self, target, secret, config, end):
        super().__init__(target['server'], target['port'], target['key_name'], secret)
        self.target, self.config, self.end = target, config, end

    def exchange(self, message):
        current_window(self.config)
        remaining = min(self.end - time.monotonic(), (c.timestamp(self.config['valid_until']) - utcnow()).total_seconds())
        require(remaining > 0, 'DNS observation budget exhausted')
        self.timeout = min(5, remaining)
        response = super().exchange(message)
        current_window(self.config)
        require(time.monotonic() <= self.end, 'DNS observation budget exhausted')
        return response

    def rrset(self, name, rtype, zone):
        recursive = self.target['role'] == 'recursive'
        query = dns.message.make_query(name, rtype)
        if not recursive: query.flags &= ~dns.flags.RD
        response = self.exchange(query)
        require(response.rcode() in (dns.rcode.NOERROR, dns.rcode.NXDOMAIN),
                'DNS failure is not an absence observation')
        if recursive:
            require(response.flags & dns.flags.RA and response.flags & dns.flags.RD
                    and not response.flags & dns.flags.AA, 'Selected recursive view did not return a recursive answer')
        else:
            require(response.flags & dns.flags.AA, 'Selected authority is not authoritative')
        answer = [rr for rr in response.answer if rr.name == dns.name.from_text(name)
                  and rr.rdtype == dns.rdatatype.from_text(rtype) and rr.rdclass == dns.rdataclass.IN]
        require(len(answer) <= 1 and len(answer) == len(response.answer),
                'DNS aliases and unrelated answers are not followed')
        require(response.rcode() != dns.rcode.NXDOMAIN or not response.answer, 'Contradictory negative DNS response')
        if not answer:
            soa = [rr for rr in response.authority if rr.rdtype == dns.rdatatype.SOA]
            require(len(soa) == 1 and soa[0].name == dns.name.from_text(zone)
                    and soa[0].rdclass == dns.rdataclass.IN and len(soa[0]) == 1,
                    'Negative DNS observation requires the exact zone SOA')
            return None
        rr = answer[0]
        values = sorted(b''.join(r.strings).decode('ascii') if rtype == 'TXT' else r.to_text().lower() for r in rr)
        return {'ttl': rr.ttl, 'values': values}


def matches(observed, job, *, recursive):
    expected = {'marker': writer.marker_rr(writer.marker_value(job)),
                'name_owners': {name: writer.marker_rr(writer.marker_value(job)) for name in writer.name_markers(job)},
                'records': writer.payload(job, 'after')}
    if not recursive: return observed == expected
    # Cache TTLs decay. Values and exact ownership generations may not differ.
    def rr(actual, wanted):
        if wanted is None: return actual is None
        return isinstance(actual, dict) and set(actual) == {'ttl', 'values'} and actual['values'] == wanted['values'] \
            and type(actual['ttl']) is int and 0 <= actual['ttl'] <= wanted['ttl']
    return (set(observed) == set(expected) and rr(observed['marker'], expected['marker'])
        and set(observed['name_owners']) == set(expected['name_owners'])
        and all(rr(observed['name_owners'][n], v) for n, v in expected['name_owners'].items())
        and len(observed['records']) == len(expected['records'])
        and all(set(a) == set(b) and a['name'] == b['name'] and a['type'] == b['type'] and rr(a['value'], b['value'])
                for a, b in zip(observed['records'], expected['records'])))


def observe(config, job, scope, receipt, secrets, *, fixture=False,enrolled_context=None):
    if enrolled_context is not None:
        from provisioner.controlplane.reconciliation.service_propagation import EnrolledDnsPropagationContext
        require(type(enrolled_context) is EnrolledDnsPropagationContext and not fixture
                and config==enrolled_context.effective and secrets==enrolled_context.secrets,
                'Only the actual enrolled read owner may refresh DNS authentication')
        enrolled_context.require_current()
    validate(config, job, scope, receipt, secrets, fixture=fixture)
    require(Path('/etc/machine-id').read_text().strip() == config['observer_machine_id']
            and Path('/proc/self/ns/net').stat().st_ino == config['network_namespace_inode'],
            'DNS observation must originate from the accepted machine and network namespace')
    started = utcnow().isoformat(); end = time.monotonic() + config['max_seconds']; observations = []
    # Two full sweeps detect a view reverting or changing while other views are read.
    # They are finite observations, never a claim of universal cache expiry.
    for sweep in (1, 2):
        for target in config['targets']:
            client = (enrolled_context.client(target,config,end) if enrolled_context is not None
                      else Client(target,secrets[target['id']],config,end))
            control = client.rrset(target['control_name'], 'TXT', job['zone'])
            require(control is not None and control['values'] == [target['control_value']],
                    'DNS view positive control differs')
            observed = writer.snapshot(job, client)
            require(matches(observed, job, recursive=target['role'] == 'recursive'),
                    'DNS propagation is stale, incomplete or belongs to another generation')
            control_after = client.rrset(target['control_name'], 'TXT', job['zone'])
            require(control_after is not None and control_after['values'] == [target['control_value']],
                    'DNS view positive control changed')
            observations.append({'target_id': target['id'], 'sweep': sweep, 'observed_at': utcnow().isoformat(),
                                 'snapshot': observed, 'control': control_after})
    return {'format': 'hosting-dns-propagation-receipt/1', 'status': STATUS,
            'config_sha256': c.digest(config), 'job_sha256': c.digest(job), 'scope_sha256': c.digest(scope),
            'primary_receipt_sha256': c.digest(receipt), 'started_at': started, 'finished_at': utcnow().isoformat(),
            'observations': observations, 'activation_authorized': False, 'reusable': False}


def validate_result(result, config, job, scope, receipt):
    """Check a durable observation before recovering its interrupted publication."""
    c.exact_keys(result, {'format', 'status', 'config_sha256', 'job_sha256', 'scope_sha256',
        'primary_receipt_sha256', 'started_at', 'finished_at', 'observations', 'activation_authorized', 'reusable'})
    require(result['format'] == 'hosting-dns-propagation-receipt/1' and result['status'] == STATUS
            and result['config_sha256'] == c.digest(config) and result['job_sha256'] == c.digest(job)
            and result['scope_sha256'] == c.digest(scope) and result['primary_receipt_sha256'] == c.digest(receipt)
            and result['activation_authorized'] is False and result['reusable'] is False,
            'Retained DNS observation handoff changed')
    start, finish = c.timestamp(result['started_at']), c.timestamp(result['finished_at'])
    require(c.timestamp(config['valid_from']) <= start <= finish < c.timestamp(config['valid_until'])
            and finish <= utcnow() and (finish-start).total_seconds() <= config['max_seconds'],
            'Retained DNS observation time is outside its authority')
    expected = [(sweep, target) for sweep in (1, 2) for target in config['targets']]
    require(isinstance(result['observations'], list) and len(result['observations']) == len(expected),
            'Incomplete retained DNS observations')
    prior = start
    for observed, (sweep, target) in zip(result['observations'], expected):
        c.exact_keys(observed, {'target_id', 'sweep', 'observed_at', 'snapshot', 'control'})
        when = c.timestamp(observed['observed_at'])
        require(type(observed['sweep']) is int and observed['sweep'] == sweep and observed['target_id'] == target['id']
                and prior <= when <= finish and isinstance(observed['control'], dict)
                and observed['control'].get('values') == [target['control_value']]
                and matches(observed['snapshot'], job, recursive=target['role'] == 'recursive'),
                'Retained DNS view observations are incomplete or changed')
        prior = when


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('config', 'job', 'scope', 'receipt', 'secrets'): parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--output', type=Path); parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    try:
        values = [load_private(getattr(args, name)) for name in ('config', 'job', 'scope', 'receipt', 'secrets')]
        validate(*values)
        if not args.execute:
            print(json.dumps({'status': 'VALIDATED_NO_CONTACT'})); return 0
        require(args.output is not None, 'New private observation output required')
        result = observe(*values); write_new(args.output, encoded(result))
        print(json.dumps({'status': result['status']})); return 0
    except (OSError, ValueError, TypeError, KeyError, AttributeError, dns.exception.DNSException) as exc:
        print(json.dumps({'status': 'DNS_PROPAGATION_HELD', 'error_class': type(exc).__name__})); return 1


if __name__ == '__main__': raise SystemExit(main())
