#!/usr/bin/env python3
"""Scoped RFC 2136 DNS change with TSIG, server-side prerequisites and read-back.

One owned record group, one explicitly named authoritative zone, one UPDATE at most.
This is a service-owner integration, not an IPAM allocator or authorization engine.
The default CLI performs input checks only. No resolver discovery or AXFR is used.
Forward and reverse zones are separate transactions; caller coordinates their gates.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import sys
import uuid
from typing import Any

import dns.exception
import dns.flags
import dns.message
import dns.name
import dns.query
import dns.rcode
import dns.rdataclass
import dns.rdatatype
import dns.rrset
import dns.tsig
import dns.tsigkeyring
import dns.update

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.neutron_observe import strict_loads, write_private

DOC_NETS = tuple(ipaddress.ip_network(x) for x in (
    '192.0.2.0/24', '198.51.100.0/24', '203.0.113.0/24', '2001:db8::/32'))
LABEL = re.compile(r'^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$')
OWNER = re.compile(r'^[a-z][a-z0-9-]{1,62}
JOB_KEYS = {'version', 'enabled', 'operation_id', 'tenant_id', 'resource_id',
            'zone', 'server', 'port', 'key_name', 'engineering_record_ref',
            'valid_until', 'previous_marker', 'allocation_binding_digest',
            'previous_allocation_binding_digest', 'records'}
SCOPE_KEYS = {'version', 'enabled', 'operation_id', 'tenant_id', 'resource_id',
              'zone', 'server', 'port', 'key_name', 'engineering_record_ref',
              'valid_until', 'transport_acceptance_ref', 'allowed_records'}
STATES = {'APPLIED_OBSERVED', 'ALREADY_APPLIED_OBSERVED', 'RECONCILED_APPLIED_OBSERVED'}


class DNSChangeError(ValueError):
    """Safe diagnostic; messages never include credentials or server response bodies."""


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def fqdn(value: Any) -> str:
    if not isinstance(value, str) or not value.endswith('.') or value != value.lower():
        raise DNSChangeError('Use a lower-case absolute DNS name with a trailing dot')
    labels = value[:-1].split('.')
    if len(labels) < 2 or len(value) > 253 or any(not LABEL.fullmatch(x) for x in labels):
        raise DNSChangeError('Unsupported DNS name; wildcards, escapes and empty labels are forbidden')
    return value


def deadline(value: Any, now: datetime) -> None:
    try:
        when = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if when.tzinfo is None or when <= now:
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        raise DNSChangeError('A current timezone-aware validity limit is required') from None


def address(value: Any, family: int, *, fixture: bool = False) -> str:
    try:
        parsed = ipaddress.ip_address(value)
    except (ValueError, TypeError):
        raise DNSChangeError('Invalid address') from None
    if parsed.version != family or str(parsed) != value or parsed.is_unspecified or parsed.is_multicast \
            or parsed.is_loopback or parsed.is_link_local:
        raise DNSChangeError('Address family, representation or scope is invalid')
    if not fixture and any(parsed.version == net.version and parsed in net for net in DOC_NETS):
        raise DNSChangeError('Documentation addresses are not actual allocations')
    return value


def payload(job: dict, side: str) -> list[dict]:
    return [{'name': r['name'], 'type': r['type'], 'value': r[side]}
            for r in sorted(job['records'], key=lambda x: (x['name'], x['type']))]


def opaque_ref(value: Any, label: str) -> str:
    if not isinstance(value, str) or not OPAQUE_REF.fullmatch(value):
        raise DNSChangeError(f'A bounded opaque {label} is required')
    if re.search(r'(?<![0-9])(?:[0-9]{1,3}\\.){3}[0-9]{1,3}(?![0-9])', value) or '::' in value:
        raise DNSChangeError(f'{label} must not embed an address value')
    if ':' in value:
        suffix = value.split(':', 1)[1]
        try:
            ipaddress.ip_address(suffix)
        except ValueError:
            pass
        else:
            raise DNSChangeError(f'{label} must not embed an address value')
    return value


def allocation_binding_digest(scope: dict) -> str:
    bindings = [{
        'name': item['name'],
        'type': item['type'],
        'allocation_binding_ref': item['allocation_binding_ref'],
        'allocation_generation': item['allocation_generation']
    } for item in sorted(scope['allowed_records'], key=lambda x: (x['name'], x['type']))]
    return digest(bindings)


def owner_token(job: dict) -> str:
    return digest([job['tenant_id'], job['resource_id']])[:24]


def marker_name(job: dict) -> str:
    # Opaque owner label is generated, not supplied as an arbitrary TXT record name.
    return f"_hosting-{owner_token(job)}.{job['zone']}"


def name_markers(job: dict) -> list[str]:
    # Name-scoped markers prevent A/AAAA split ownership and reuse after deletion.
    return sorted({'_hosting-owner.' + r['name'] for r in job['records']})


def marker_value(job: dict) -> str:
    return f"hosting-v2 {owner_token(job)} {job['operation_id']} {digest(payload(job, 'after'))} {job['allocation_binding_digest']}"


def marker_rr(value: str | None) -> dict | None:
    return None if value is None else {'ttl': 300, 'values': [value]}


def validate(job: dict, scope: dict, *, now: datetime | None = None,
             fixture: bool = False) -> None:
    now = now or datetime.now(timezone.utc)
    if not isinstance(job, dict) or set(job) != JOB_KEYS or not isinstance(scope, dict) or set(scope) != SCOPE_KEYS:
        raise DNSChangeError('Unexpected or missing job/scope fields')
    if type(job['version']) is not int or job['version'] != 2 or type(scope['version']) is not int or scope['version'] != 2:
        raise DNSChangeError('Unsupported integration version; allocation-bound DNS profile is version 2')
    if type(job['enabled']) is not bool or type(scope['enabled']) is not bool:
        raise DNSChangeError('Explicit enabled booleans are required')
    for key in ('operation_id', 'tenant_id', 'resource_id', 'zone', 'server', 'port',
                'key_name', 'engineering_record_ref'):
        if type(job[key]) is not type(scope[key]) or job[key] != scope[key]:
            raise DNSChangeError(f'Job differs from independently supplied scope: {key}')
    for key in ('tenant_id', 'resource_id'):
        if not isinstance(job[key], str) or not OWNER.fullmatch(job[key]):
            raise DNSChangeError('Invalid tenant or resource identifier')
    try:
        if str(uuid.UUID(job['operation_id'])) != job['operation_id']:
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        raise DNSChangeError('Canonical operation UUID required') from None
    for record in (job, scope):
        deadline(record['valid_until'], now)
    for key, value in [('engineering_record_ref', job['engineering_record_ref']),
                       ('transport_acceptance_ref', scope['transport_acceptance_ref'])]:
        if not isinstance(value, str) or not 1 <= len(value) <= 256 or any(ord(c) < 32 for c in value):
            raise DNSChangeError(f'A bounded non-secret {key} is required')
    if not isinstance(job['allocation_binding_digest'], str) or not HEX64.fullmatch(job['allocation_binding_digest']):
        raise DNSChangeError('Current allocation-binding SHA-256 is required')
    expected_binding = allocation_binding_digest(scope)
    if job['allocation_binding_digest'] != expected_binding:
        raise DNSChangeError('Job allocation binding differs from independently supplied DNS scope')
    zone = fqdn(job['zone'])
    fqdn(job['key_name'])
    try:
        server = ipaddress.ip_address(job['server'])
    except (ValueError, TypeError):
        raise DNSChangeError('An explicit authoritative server IP is required; discovery is disabled') from None
    if str(server) != job['server'] or server.is_unspecified or server.is_multicast or server.is_link_local:
        raise DNSChangeError('Invalid authoritative server scope')
    if fixture:
        if not server.is_loopback or not zone.endswith(('.invalid.', '.in-addr.arpa.', '.ip6.arpa.')):
            raise DNSChangeError('Test transport is restricted to loopback and reserved fixture/reverse zones')
    elif server.is_loopback or any(server.version == n.version and server in n for n in DOC_NETS) \
            or zone.endswith(('.invalid.', '.example.', '.test.')):
        raise DNSChangeError('Test names and addresses cannot select a native target')
    if type(job['port']) is not int or not 1 <= job['port'] <= 65535:
        raise DNSChangeError('Invalid DNS TCP port')
    records, allowed = job['records'], scope['allowed_records']
    if not isinstance(records, list) or not 1 <= len(records) <= 8 or not isinstance(allowed, list):
        raise DNSChangeError('Provide one to eight explicitly owned record sets')
    accepted = {}
    for item in allowed:
        if not isinstance(item, dict) or set(item) != {'name', 'type', 'values', 'maximum_ttl', 'allocation_binding_ref', 'allocation_generation'}:
            raise DNSChangeError('Invalid exact allocation-bound DNS record')
        if not isinstance(item['type'], str):
            raise DNSChangeError('Record type must be a string')
        pair = (fqdn(item['name']), item['type'])
        if pair in accepted or item['type'] not in ('A', 'AAAA', 'PTR'):
            raise DNSChangeError('Duplicate or unsupported scope record')
        if type(item['maximum_ttl']) is not int or not 1 <= item['maximum_ttl'] <= 2147483647:
            raise DNSChangeError('Invalid allowed TTL ceiling')
        opaque_ref(item['allocation_binding_ref'], 'allocation_binding_ref')
        if type(item['allocation_generation']) is not int or item['allocation_generation'] < 1:
            raise DNSChangeError('Positive allocation generation is required')
        if not isinstance(item['values'], list) or not 1 <= len(item['values']) <= 16 \
                or any(not isinstance(x, str) for x in item['values']) or len(set(item['values'])) != len(item['values']):
            raise DNSChangeError('Exact allocated addresses or PTR targets are required')
        accepted[pair] = item
    seen = set()
    for record in records:
        if not isinstance(record, dict) or set(record) != {'name', 'type', 'before', 'after'}:
            raise DNSChangeError('Each change requires explicit before and after values')
        name, rtype = fqdn(record['name']), record['type']
        if not isinstance(rtype, str):
            raise DNSChangeError('Record type must be a string')
        if not dns.name.from_text(name).is_subdomain(dns.name.from_text(zone)) or name == zone:
            raise DNSChangeError('Record must be strictly within the named zone, not at its apex')
        pair = (name, rtype)
        if pair in seen or pair not in accepted:
            raise DNSChangeError('Record is duplicate or outside the accepted scope')
        seen.add(pair)
        if rtype == 'PTR':
            try:
                # Exact reverse names only, no classless reverse alias invention.
                if name.endswith('.in-addr.arpa.'):
                    ipaddress.IPv4Address('.'.join(reversed(name.removesuffix('.in-addr.arpa.').split('.'))))
                elif name.endswith('.ip6.arpa.'):
                    nibbles = name.removesuffix('.ip6.arpa.').split('.')
                    if len(nibbles) != 32 or any(not re.fullmatch('[0-9a-f]', x) for x in nibbles):
                        raise ValueError
                else:
                    raise ValueError
            except ValueError:
                raise DNSChangeError('PTR requires an exact address reverse name') from None
        elif zone.endswith(('.in-addr.arpa.', '.ip6.arpa.')):
            raise DNSChangeError('Address records cannot be written into reverse zones')
        for side in ('before', 'after'):
            value = record[side]
            if value is None:
                continue
            if not isinstance(value, dict) or set(value) != {'ttl', 'values'} or type(value['ttl']) is not int \
                    or not 1 <= value['ttl'] <= accepted[pair]['maximum_ttl']:
                raise DNSChangeError('Invalid record-set TTL or structure')
            values = value['values']
            if not isinstance(values, list) or not 1 <= len(values) <= 8 or any(not isinstance(x, str) for x in values) \
                    or len(set(values)) != len(values) or values != sorted(values):
                raise DNSChangeError('Use a nonempty sorted unique record-value list')
            if not set(values) <= set(accepted[pair]['values']):
                raise DNSChangeError('DNS value is outside exact allocation/target acceptance')
            for item in values:
                if rtype in ('A', 'AAAA'):
                    address(item, 4 if rtype == 'A' else 6, fixture=fixture)
                else:
                    fqdn(item)
            if rtype == 'PTR' and len(values) != 1:
                raise DNSChangeError('The selected PTR profile has exactly one canonical target')
    if seen != set(accepted):
        raise DNSChangeError('Scope and change must identify the same immutable record group')
    prior = job['previous_marker']
    previous_binding = job['previous_allocation_binding_digest']
    if prior is None:
        if previous_binding is not None:
            raise DNSChangeError('First ownership claim cannot carry a previous allocation binding')
        if any(r['before'] is not None for r in records) or all(r['after'] is None for r in records):
            raise DNSChangeError('Unowned groups can only be created from entirely absent records')
    else:
        if not isinstance(previous_binding, str) or not HEX64.fullmatch(previous_binding):
            raise DNSChangeError('Owned update requires the previous allocation-binding SHA-256')
        expected = rf'hosting-v2 {owner_token(job)} [0-9a-f-]{{36}} {digest(payload(job, "before"))} {re.escape(previous_binding)}'
        if not isinstance(prior, str) or not re.fullmatch(expected, prior):
            raise DNSChangeError('Prior owner/generation/allocation marker does not match the expected before state')
    if len(marker_name(job)) > 253 or any(len(n) > 253 for n in name_markers(job)):
        raise DNSChangeError('Generated ownership name is too long')


class Client:
    """Fixed-IP TCP+TSIG transport. TSIG authenticates; it does not encrypt DNS data."""
    def __init__(self, server: str, port: int, key_name: str, secret: str, timeout: float = 3):
        ipaddress.ip_address(server)
        fqdn(key_name)
        try:
            decoded = base64.b64decode(secret, validate=True)
            if len(decoded) < 32:
                raise ValueError
        except (ValueError, TypeError):
            raise DNSChangeError('Inject a base64 TSIG secret of at least 32 bytes') from None
        if not 0.05 <= timeout <= 30 or type(port) is not int or not 1 <= port <= 65535:
            raise DNSChangeError('Invalid bounded DNS transport settings')
        self.server, self.port, self.key_name, self.timeout = server, port, key_name, timeout
        self.keyring = dns.tsigkeyring.from_text({key_name: secret})

    def exchange(self, message: dns.message.Message) -> dns.message.Message:
        message.use_tsig(self.keyring, keyname=self.key_name, algorithm=dns.tsig.HMAC_SHA256)
        response = dns.query.tcp(message, self.server, port=self.port, timeout=self.timeout)
        if not response.had_tsig or response.keyname != dns.name.from_text(self.key_name) \
                or response.keyalgorithm != dns.tsig.HMAC_SHA256 or not message.is_response(response):
            raise DNSChangeError('Missing or mismatched authenticated DNS response')
        if response.flags & dns.flags.TC:
            raise DNSChangeError('Truncated TCP response is inconclusive')
        return response

    def rrset(self, name: str, rtype: str, zone: str) -> dict | None:
        query = dns.message.make_query(name, rtype)
        query.flags &= ~dns.flags.RD
        response = self.exchange(query)
        if not response.flags & dns.flags.AA or response.rcode() not in (dns.rcode.NOERROR, dns.rcode.NXDOMAIN):
            raise DNSChangeError('Authoritative authenticated observation is unavailable')
        answer = [r for r in response.answer if r.name == dns.name.from_text(name)
                  and r.rdtype == dns.rdatatype.from_text(rtype) and r.rdclass == dns.rdataclass.IN]
        if response.rcode() == dns.rcode.NXDOMAIN and response.answer:
            raise DNSChangeError('Contradictory negative response')
        if len(answer) > 1 or len(response.answer) != len(answer):
            raise DNSChangeError('Aliases, referrals and unrelated answer records are not followed')
        if not answer:
            if not any(r.name == dns.name.from_text(zone) and r.rdtype == dns.rdatatype.SOA
                       for r in response.authority):
                raise DNSChangeError('Negative observation lacks the exact authoritative zone SOA')
            return None
        rr = answer[0]
        if rtype == 'TXT':
            values = sorted(b''.join(r.strings).decode('ascii') for r in rr)
        else:
            values = sorted(r.to_text().lower() for r in rr)
        return {'ttl': rr.ttl, 'values': values}


def snapshot(job: dict, client: Client) -> dict:
    # Validate the exact zone authority rather than infer it from a recursive answer.
    if client.rrset(job['zone'], 'SOA', job['zone']) is None:
        raise DNSChangeError('Named authoritative zone is unavailable')
    names = sorted({r['name'] for r in job['records']} | {marker_name(job)} | set(name_markers(job)))
    aliases = {name: client.rrset(name, 'CNAME', job['zone']) for name in names}
    if any(x is not None for x in aliases.values()):
        raise DNSChangeError('CNAME conflicts with the selected exact-record profile')
    marker = client.rrset(marker_name(job), 'TXT', job['zone'])
    owners = {name: client.rrset(name, 'TXT', job['zone']) for name in name_markers(job)}
    values = [{'name': r['name'], 'type': r['type'],
               'value': client.rrset(r['name'], r['type'], job['zone'])}
              for r in sorted(job['records'], key=lambda x: (x['name'], x['type']))]
    return {'marker': marker, 'name_owners': owners, 'records': values}


def matches(observed: dict, job: dict, side: str) -> bool:
    target = marker_value(job) if side == 'after' else job['previous_marker']
    return observed == {'marker': marker_rr(target), 'name_owners': {n: marker_rr(target) for n in name_markers(job)},
                        'records': payload(job, side)}


def build_update(job: dict) -> dns.update.UpdateMessage:
    update = dns.update.Update(job['zone'])
    mname = marker_name(job)
    if job['previous_marker'] is None:
        # Name-not-in-use, not merely TXT absence, protects the first ownership claim.
        update.absent(mname)
    else:
        update.present(mname, 'TXT', json.dumps(job['previous_marker']))
        update.absent(mname, 'CNAME')
    for name in name_markers(job):
        if job['previous_marker'] is None:
            update.absent(name)
        else:
            update.present(name, 'TXT', json.dumps(job['previous_marker']))
            update.absent(name, 'CNAME')
    if job['previous_marker'] is None:
        for name in sorted({r['name'] for r in job['records']}):
            update.absent(name)  # Never split a new owner across existing A/AAAA names.
    for record in job['records']:
        name, rtype = record['name'], record['type']
        update.absent(name, 'CNAME')
        before = record['before']
        if before is None:
            update.absent(name, rtype)
        else:
            update.present(name, rtype, *before['values'])
        update.delete(name, rtype)
        if record['after'] is not None:
            update.add(name, record['after']['ttl'], rtype, *record['after']['values'])
    # Retain a tombstone marker on delete: replay detection and ownership outlive records.
    update.replace(mname, 300, 'TXT', json.dumps(marker_value(job)))
    for name in name_markers(job):
        update.replace(name, 300, 'TXT', json.dumps(marker_value(job)))
    return update


def change(job: dict, scope: dict, client: Client, *, execute: bool = False,
           fixture: bool = False, record=None) -> dict:
    validate(job, scope, fixture=fixture)
    if execute and not fixture and record is None:
        raise DNSChangeError('A native mutation requires a journal writer')
    if not job['enabled'] or not scope['enabled']:
        raise DNSChangeError('Disabled examples cannot contact a target')
    if (client.server, client.port, client.key_name) != (job['server'], job['port'], job['key_name']):
        raise DNSChangeError('Transport differs from accepted endpoint and key scope')
    report = {'kind': 'SCOPED_DNS_TRANSACTION', 'operation_id': job['operation_id'],
              'job_sha256': digest(job), 'scope_sha256': digest(scope),
              'engineering_record_ref': job['engineering_record_ref'],
              'started_at': datetime.now(timezone.utc).isoformat(), 'update_attempts': 0,
              'status': 'OBSERVING', 'events': [], 'activation_authorized': False}

    def event(stage: str, **data):
        report['events'].append({'stage': stage, 'at': datetime.now(timezone.utc).isoformat(), **data})
        if record is not None:
            record(report)

    def finish(status: str):
        report['status'] = status
        report['finished_at'] = datetime.now(timezone.utc).isoformat()
        report['limitations'] = [
            'Authenticated authoritative reads are not cache/secondary propagation proof',
            'TSIG authentication is not confidentiality or independent approval verification',
            'One zone only; forward and reverse zones are not one transaction',
            'RFC 2136 compares RR data, not TTL; single-writer ownership remains required',
            'A DNS observation does not authorize network activation or address reuse',
            'Allocation binding references are engineering handoffs, not proof of IPAM service authenticity',
            'Deletion retains an ownership tombstone; releasing it needs separate governance']
        if record is not None:
            record(report)
        return report

    try:
        before = snapshot(job, client)
        event('BEFORE_OBSERVED', observation_sha256=digest(before))
    except (OSError, EOFError, dns.exception.DNSException, ValueError) as exc:
        event('OBSERVATION_ERROR', error_class=type(exc).__name__)
        return finish('INCONCLUSIVE_NO_UPDATE')
    if matches(before, job, 'after'):
        return finish('ALREADY_APPLIED_OBSERVED')
    if not matches(before, job, 'before'):
        return finish('CONFLICT_NO_UPDATE')
    if not execute:
        return finish('READY_FOR_INDEPENDENT_REVIEW_NO_UPDATE')
    # Validity is checked again after potentially slow observations.
    validate(job, scope, fixture=fixture)
    # Journal before sending. A failed journal write cannot be followed by a mutation.
    report['status'] = 'UPDATE_PENDING'
    report['update_attempts'] = 1  # Attempt reserved; after a crash its outcome is unknown.
    event('UPDATE_PENDING', update_digest=digest(payload(job, 'after')))
    ambiguous = False
    try:
        response = client.exchange(build_update(job))
        code = response.rcode()
        event('UPDATE_RESPONSE', rcode=dns.rcode.to_text(code))
        if code != dns.rcode.NOERROR:
            return finish('PREREQUISITE_CONFLICT' if code in (dns.rcode.NXRRSET, dns.rcode.YXRRSET,
                                                           dns.rcode.NXDOMAIN, dns.rcode.YXDOMAIN)
                          else 'UPDATE_REJECTED')
    except (OSError, EOFError, dns.exception.DNSException, ValueError) as exc:
        ambiguous = True
        event('UPDATE_OUTCOME_UNKNOWN', error_class=type(exc).__name__)
    try:
        after = snapshot(job, client)
        event('AFTER_OBSERVED', observation_sha256=digest(after))
        if matches(after, job, 'after'):
            return finish('RECONCILED_APPLIED_OBSERVED' if ambiguous else 'APPLIED_OBSERVED')
        return finish('UNKNOWN_OUTCOME_OPERATOR_RECONCILIATION' if ambiguous else 'APPLIED_BUT_READBACK_DIFFERS')
    except (OSError, EOFError, dns.exception.DNSException, ValueError) as exc:
        event('READBACK_ERROR', error_class=type(exc).__name__)
        return finish('UNKNOWN_OUTCOME_OPERATOR_RECONCILIATION' if ambiguous else 'APPLIED_READBACK_INCONCLUSIVE')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('job', type=Path)
    parser.add_argument('--scope', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--observe-authorized-target', action='store_true')
    parser.add_argument('--execute-approved-change', action='store_true')
    args = parser.parse_args()
    if args.execute_approved_change and not args.observe_authorized_target:
        parser.error('Execution requires explicit authorized-target contact too')
    try:
        job = strict_loads(args.job.read_bytes())
        scope = strict_loads(args.scope.read_bytes())
        validate(job, scope)
        if not args.observe_authorized_target:
            print(json.dumps({'status': 'INPUT_CHECKED_NO_TARGET_CONTACT', 'enabled': job['enabled'] and scope['enabled']}))
            return 0 if job['enabled'] and scope['enabled'] else 4
        if args.output is None:
            parser.error('A private --output journal is required before contact')
        # Existing journals are never overwritten to hide an uncertain prior attempt.
        if args.output.exists():
            raise DNSChangeError('Journal already exists; inspect and reconcile the prior operation before a new invocation')
        # Reserve this journal exclusively before contact; no concurrent run may reuse it.
        fd = os.open(args.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump({'status': 'RESERVED_NOT_SENT', 'operation_id': job['operation_id']}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        client = Client(job['server'], job['port'], job['key_name'], os.environ.get('DNS_TSIG_SECRET', ''))
        result = change(job, scope, client, execute=args.execute_approved_change,
                        record=lambda r: write_private(args.output, r))
        print(json.dumps({k: result[k] for k in ('status', 'operation_id', 'update_attempts', 'activation_authorized')}))
        return 0 if result['status'] in STATES or result['status'] == 'READY_FOR_INDEPENDENT_REVIEW_NO_UPDATE' else 2
    except (OSError, ValueError, dns.exception.DNSException) as exc:
        print(json.dumps({'status': 'BLOCKED_INPUT_OR_TRUST', 'error_class': type(exc).__name__,
                          'reason': str(exc) if isinstance(exc, DNSChangeError) else 'Invalid local input or trust material'}))
        return 4


if __name__ == '__main__':
    raise SystemExit(main())
)
OPAQUE_REF = re.compile(r'^[A-Za-z][A-Za-z0-9_.:-]{1,255}
JOB_KEYS = {'version', 'enabled', 'operation_id', 'tenant_id', 'resource_id',
            'zone', 'server', 'port', 'key_name', 'engineering_record_ref',
            'valid_until', 'previous_marker', 'records'}
SCOPE_KEYS = {'version', 'enabled', 'operation_id', 'tenant_id', 'resource_id',
              'zone', 'server', 'port', 'key_name', 'engineering_record_ref',
              'valid_until', 'transport_acceptance_ref', 'allowed_records'}
STATES = {'APPLIED_OBSERVED', 'ALREADY_APPLIED_OBSERVED', 'RECONCILED_APPLIED_OBSERVED'}


class DNSChangeError(ValueError):
    """Safe diagnostic; messages never include credentials or server response bodies."""


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def fqdn(value: Any) -> str:
    if not isinstance(value, str) or not value.endswith('.') or value != value.lower():
        raise DNSChangeError('Use a lower-case absolute DNS name with a trailing dot')
    labels = value[:-1].split('.')
    if len(labels) < 2 or len(value) > 253 or any(not LABEL.fullmatch(x) for x in labels):
        raise DNSChangeError('Unsupported DNS name; wildcards, escapes and empty labels are forbidden')
    return value


def deadline(value: Any, now: datetime) -> None:
    try:
        when = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if when.tzinfo is None or when <= now:
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        raise DNSChangeError('A current timezone-aware validity limit is required') from None


def address(value: Any, family: int, *, fixture: bool = False) -> str:
    try:
        parsed = ipaddress.ip_address(value)
    except (ValueError, TypeError):
        raise DNSChangeError('Invalid address') from None
    if parsed.version != family or str(parsed) != value or parsed.is_unspecified or parsed.is_multicast \
            or parsed.is_loopback or parsed.is_link_local:
        raise DNSChangeError('Address family, representation or scope is invalid')
    if not fixture and any(parsed.version == net.version and parsed in net for net in DOC_NETS):
        raise DNSChangeError('Documentation addresses are not actual allocations')
    return value


def payload(job: dict, side: str) -> list[dict]:
    return [{'name': r['name'], 'type': r['type'], 'value': r[side]}
            for r in sorted(job['records'], key=lambda x: (x['name'], x['type']))]


def owner_token(job: dict) -> str:
    return digest([job['tenant_id'], job['resource_id']])[:24]


def marker_name(job: dict) -> str:
    # Opaque owner label is generated, not supplied as an arbitrary TXT record name.
    return f"_hosting-{owner_token(job)}.{job['zone']}"


def name_markers(job: dict) -> list[str]:
    # Name-scoped markers prevent A/AAAA split ownership and reuse after deletion.
    return sorted({'_hosting-owner.' + r['name'] for r in job['records']})


def marker_value(job: dict) -> str:
    return f"hosting-v1 {owner_token(job)} {job['operation_id']} {digest(payload(job, 'after'))}"


def marker_rr(value: str | None) -> dict | None:
    return None if value is None else {'ttl': 300, 'values': [value]}


def validate(job: dict, scope: dict, *, now: datetime | None = None,
             fixture: bool = False) -> None:
    now = now or datetime.now(timezone.utc)
    if not isinstance(job, dict) or set(job) != JOB_KEYS or not isinstance(scope, dict) or set(scope) != SCOPE_KEYS:
        raise DNSChangeError('Unexpected or missing job/scope fields')
    if type(job['version']) is not int or job['version'] != 1 or type(scope['version']) is not int or scope['version'] != 1:
        raise DNSChangeError('Unsupported integration version')
    if type(job['enabled']) is not bool or type(scope['enabled']) is not bool:
        raise DNSChangeError('Explicit enabled booleans are required')
    for key in ('operation_id', 'tenant_id', 'resource_id', 'zone', 'server', 'port',
                'key_name', 'engineering_record_ref'):
        if type(job[key]) is not type(scope[key]) or job[key] != scope[key]:
            raise DNSChangeError(f'Job differs from independently supplied scope: {key}')
    for key in ('tenant_id', 'resource_id'):
        if not isinstance(job[key], str) or not OWNER.fullmatch(job[key]):
            raise DNSChangeError('Invalid tenant or resource identifier')
    try:
        if str(uuid.UUID(job['operation_id'])) != job['operation_id']:
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        raise DNSChangeError('Canonical operation UUID required') from None
    for record in (job, scope):
        deadline(record['valid_until'], now)
    for key, value in [('engineering_record_ref', job['engineering_record_ref']),
                       ('transport_acceptance_ref', scope['transport_acceptance_ref'])]:
        if not isinstance(value, str) or not 1 <= len(value) <= 256 or any(ord(c) < 32 for c in value):
            raise DNSChangeError(f'A bounded non-secret {key} is required')
    zone = fqdn(job['zone'])
    fqdn(job['key_name'])
    try:
        server = ipaddress.ip_address(job['server'])
    except (ValueError, TypeError):
        raise DNSChangeError('An explicit authoritative server IP is required; discovery is disabled') from None
    if str(server) != job['server'] or server.is_unspecified or server.is_multicast or server.is_link_local:
        raise DNSChangeError('Invalid authoritative server scope')
    if fixture:
        if not server.is_loopback or not zone.endswith(('.invalid.', '.in-addr.arpa.', '.ip6.arpa.')):
            raise DNSChangeError('Test transport is restricted to loopback and reserved fixture/reverse zones')
    elif server.is_loopback or any(server.version == n.version and server in n for n in DOC_NETS) \
            or zone.endswith(('.invalid.', '.example.', '.test.')):
        raise DNSChangeError('Test names and addresses cannot select a native target')
    if type(job['port']) is not int or not 1 <= job['port'] <= 65535:
        raise DNSChangeError('Invalid DNS TCP port')
    records, allowed = job['records'], scope['allowed_records']
    if not isinstance(records, list) or not 1 <= len(records) <= 8 or not isinstance(allowed, list):
        raise DNSChangeError('Provide one to eight explicitly owned record sets')
    accepted = {}
    for item in allowed:
        if not isinstance(item, dict) or set(item) != {'name', 'type', 'values', 'maximum_ttl'}:
            raise DNSChangeError('Invalid exact allocation record')
        if not isinstance(item['type'], str):
            raise DNSChangeError('Record type must be a string')
        pair = (fqdn(item['name']), item['type'])
        if pair in accepted or item['type'] not in ('A', 'AAAA', 'PTR'):
            raise DNSChangeError('Duplicate or unsupported scope record')
        if type(item['maximum_ttl']) is not int or not 1 <= item['maximum_ttl'] <= 2147483647:
            raise DNSChangeError('Invalid allowed TTL ceiling')
        if not isinstance(item['values'], list) or not 1 <= len(item['values']) <= 16 \
                or any(not isinstance(x, str) for x in item['values']) or len(set(item['values'])) != len(item['values']):
            raise DNSChangeError('Exact allocated addresses or PTR targets are required')
        accepted[pair] = item
    seen = set()
    for record in records:
        if not isinstance(record, dict) or set(record) != {'name', 'type', 'before', 'after'}:
            raise DNSChangeError('Each change requires explicit before and after values')
        name, rtype = fqdn(record['name']), record['type']
        if not isinstance(rtype, str):
            raise DNSChangeError('Record type must be a string')
        if not dns.name.from_text(name).is_subdomain(dns.name.from_text(zone)) or name == zone:
            raise DNSChangeError('Record must be strictly within the named zone, not at its apex')
        pair = (name, rtype)
        if pair in seen or pair not in accepted:
            raise DNSChangeError('Record is duplicate or outside the accepted scope')
        seen.add(pair)
        if rtype == 'PTR':
            try:
                # Exact reverse names only, no classless reverse alias invention.
                if name.endswith('.in-addr.arpa.'):
                    ipaddress.IPv4Address('.'.join(reversed(name.removesuffix('.in-addr.arpa.').split('.'))))
                elif name.endswith('.ip6.arpa.'):
                    nibbles = name.removesuffix('.ip6.arpa.').split('.')
                    if len(nibbles) != 32 or any(not re.fullmatch('[0-9a-f]', x) for x in nibbles):
                        raise ValueError
                else:
                    raise ValueError
            except ValueError:
                raise DNSChangeError('PTR requires an exact address reverse name') from None
        elif zone.endswith(('.in-addr.arpa.', '.ip6.arpa.')):
            raise DNSChangeError('Address records cannot be written into reverse zones')
        for side in ('before', 'after'):
            value = record[side]
            if value is None:
                continue
            if not isinstance(value, dict) or set(value) != {'ttl', 'values'} or type(value['ttl']) is not int \
                    or not 1 <= value['ttl'] <= accepted[pair]['maximum_ttl']:
                raise DNSChangeError('Invalid record-set TTL or structure')
            values = value['values']
            if not isinstance(values, list) or not 1 <= len(values) <= 8 or any(not isinstance(x, str) for x in values) \
                    or len(set(values)) != len(values) or values != sorted(values):
                raise DNSChangeError('Use a nonempty sorted unique record-value list')
            if not set(values) <= set(accepted[pair]['values']):
                raise DNSChangeError('DNS value is outside exact allocation/target acceptance')
            for item in values:
                if rtype in ('A', 'AAAA'):
                    address(item, 4 if rtype == 'A' else 6, fixture=fixture)
                else:
                    fqdn(item)
            if rtype == 'PTR' and len(values) != 1:
                raise DNSChangeError('The selected PTR profile has exactly one canonical target')
    if seen != set(accepted):
        raise DNSChangeError('Scope and change must identify the same immutable record group')
    prior = job['previous_marker']
    if prior is None:
        if any(r['before'] is not None for r in records) or all(r['after'] is None for r in records):
            raise DNSChangeError('Unowned groups can only be created from entirely absent records')
    else:
        expected = rf'hosting-v1 {owner_token(job)} [0-9a-f-]{{36}} {digest(payload(job, "before"))}'
        if not isinstance(prior, str) or not re.fullmatch(expected, prior):
            raise DNSChangeError('Prior owner/generation marker does not match the expected before state')
    if len(marker_name(job)) > 253 or any(len(n) > 253 for n in name_markers(job)):
        raise DNSChangeError('Generated ownership name is too long')


class Client:
    """Fixed-IP TCP+TSIG transport. TSIG authenticates; it does not encrypt DNS data."""
    def __init__(self, server: str, port: int, key_name: str, secret: str, timeout: float = 3):
        ipaddress.ip_address(server)
        fqdn(key_name)
        try:
            decoded = base64.b64decode(secret, validate=True)
            if len(decoded) < 32:
                raise ValueError
        except (ValueError, TypeError):
            raise DNSChangeError('Inject a base64 TSIG secret of at least 32 bytes') from None
        if not 0.05 <= timeout <= 30 or type(port) is not int or not 1 <= port <= 65535:
            raise DNSChangeError('Invalid bounded DNS transport settings')
        self.server, self.port, self.key_name, self.timeout = server, port, key_name, timeout
        self.keyring = dns.tsigkeyring.from_text({key_name: secret})

    def exchange(self, message: dns.message.Message) -> dns.message.Message:
        message.use_tsig(self.keyring, keyname=self.key_name, algorithm=dns.tsig.HMAC_SHA256)
        response = dns.query.tcp(message, self.server, port=self.port, timeout=self.timeout)
        if not response.had_tsig or response.keyname != dns.name.from_text(self.key_name) \
                or response.keyalgorithm != dns.tsig.HMAC_SHA256 or not message.is_response(response):
            raise DNSChangeError('Missing or mismatched authenticated DNS response')
        if response.flags & dns.flags.TC:
            raise DNSChangeError('Truncated TCP response is inconclusive')
        return response

    def rrset(self, name: str, rtype: str, zone: str) -> dict | None:
        query = dns.message.make_query(name, rtype)
        query.flags &= ~dns.flags.RD
        response = self.exchange(query)
        if not response.flags & dns.flags.AA or response.rcode() not in (dns.rcode.NOERROR, dns.rcode.NXDOMAIN):
            raise DNSChangeError('Authoritative authenticated observation is unavailable')
        answer = [r for r in response.answer if r.name == dns.name.from_text(name)
                  and r.rdtype == dns.rdatatype.from_text(rtype) and r.rdclass == dns.rdataclass.IN]
        if response.rcode() == dns.rcode.NXDOMAIN and response.answer:
            raise DNSChangeError('Contradictory negative response')
        if len(answer) > 1 or len(response.answer) != len(answer):
            raise DNSChangeError('Aliases, referrals and unrelated answer records are not followed')
        if not answer:
            if not any(r.name == dns.name.from_text(zone) and r.rdtype == dns.rdatatype.SOA
                       for r in response.authority):
                raise DNSChangeError('Negative observation lacks the exact authoritative zone SOA')
            return None
        rr = answer[0]
        if rtype == 'TXT':
            values = sorted(b''.join(r.strings).decode('ascii') for r in rr)
        else:
            values = sorted(r.to_text().lower() for r in rr)
        return {'ttl': rr.ttl, 'values': values}


def snapshot(job: dict, client: Client) -> dict:
    # Validate the exact zone authority rather than infer it from a recursive answer.
    if client.rrset(job['zone'], 'SOA', job['zone']) is None:
        raise DNSChangeError('Named authoritative zone is unavailable')
    names = sorted({r['name'] for r in job['records']} | {marker_name(job)} | set(name_markers(job)))
    aliases = {name: client.rrset(name, 'CNAME', job['zone']) for name in names}
    if any(x is not None for x in aliases.values()):
        raise DNSChangeError('CNAME conflicts with the selected exact-record profile')
    marker = client.rrset(marker_name(job), 'TXT', job['zone'])
    owners = {name: client.rrset(name, 'TXT', job['zone']) for name in name_markers(job)}
    values = [{'name': r['name'], 'type': r['type'],
               'value': client.rrset(r['name'], r['type'], job['zone'])}
              for r in sorted(job['records'], key=lambda x: (x['name'], x['type']))]
    return {'marker': marker, 'name_owners': owners, 'records': values}


def matches(observed: dict, job: dict, side: str) -> bool:
    target = marker_value(job) if side == 'after' else job['previous_marker']
    return observed == {'marker': marker_rr(target), 'name_owners': {n: marker_rr(target) for n in name_markers(job)},
                        'records': payload(job, side)}


def build_update(job: dict) -> dns.update.UpdateMessage:
    update = dns.update.Update(job['zone'])
    mname = marker_name(job)
    if job['previous_marker'] is None:
        # Name-not-in-use, not merely TXT absence, protects the first ownership claim.
        update.absent(mname)
    else:
        update.present(mname, 'TXT', json.dumps(job['previous_marker']))
        update.absent(mname, 'CNAME')
    for name in name_markers(job):
        if job['previous_marker'] is None:
            update.absent(name)
        else:
            update.present(name, 'TXT', json.dumps(job['previous_marker']))
            update.absent(name, 'CNAME')
    if job['previous_marker'] is None:
        for name in sorted({r['name'] for r in job['records']}):
            update.absent(name)  # Never split a new owner across existing A/AAAA names.
    for record in job['records']:
        name, rtype = record['name'], record['type']
        update.absent(name, 'CNAME')
        before = record['before']
        if before is None:
            update.absent(name, rtype)
        else:
            update.present(name, rtype, *before['values'])
        update.delete(name, rtype)
        if record['after'] is not None:
            update.add(name, record['after']['ttl'], rtype, *record['after']['values'])
    # Retain a tombstone marker on delete: replay detection and ownership outlive records.
    update.replace(mname, 300, 'TXT', json.dumps(marker_value(job)))
    for name in name_markers(job):
        update.replace(name, 300, 'TXT', json.dumps(marker_value(job)))
    return update


def change(job: dict, scope: dict, client: Client, *, execute: bool = False,
           fixture: bool = False, record=None) -> dict:
    validate(job, scope, fixture=fixture)
    if execute and not fixture and record is None:
        raise DNSChangeError('A native mutation requires a journal writer')
    if not job['enabled'] or not scope['enabled']:
        raise DNSChangeError('Disabled examples cannot contact a target')
    if (client.server, client.port, client.key_name) != (job['server'], job['port'], job['key_name']):
        raise DNSChangeError('Transport differs from accepted endpoint and key scope')
    report = {'kind': 'SCOPED_DNS_TRANSACTION', 'operation_id': job['operation_id'],
              'job_sha256': digest(job), 'scope_sha256': digest(scope),
              'engineering_record_ref': job['engineering_record_ref'],
              'started_at': datetime.now(timezone.utc).isoformat(), 'update_attempts': 0,
              'status': 'OBSERVING', 'events': [], 'activation_authorized': False}

    def event(stage: str, **data):
        report['events'].append({'stage': stage, 'at': datetime.now(timezone.utc).isoformat(), **data})
        if record is not None:
            record(report)

    def finish(status: str):
        report['status'] = status
        report['finished_at'] = datetime.now(timezone.utc).isoformat()
        report['limitations'] = [
            'Authenticated authoritative reads are not cache/secondary propagation proof',
            'TSIG authentication is not confidentiality or independent approval verification',
            'One zone only; forward and reverse zones are not one transaction',
            'RFC 2136 compares RR data, not TTL; single-writer ownership remains required',
            'A DNS observation does not authorize network activation or address reuse',
            'Deletion retains an ownership tombstone; releasing it needs separate governance']
        if record is not None:
            record(report)
        return report

    try:
        before = snapshot(job, client)
        event('BEFORE_OBSERVED', observation_sha256=digest(before))
    except (OSError, EOFError, dns.exception.DNSException, ValueError) as exc:
        event('OBSERVATION_ERROR', error_class=type(exc).__name__)
        return finish('INCONCLUSIVE_NO_UPDATE')
    if matches(before, job, 'after'):
        return finish('ALREADY_APPLIED_OBSERVED')
    if not matches(before, job, 'before'):
        return finish('CONFLICT_NO_UPDATE')
    if not execute:
        return finish('READY_FOR_INDEPENDENT_REVIEW_NO_UPDATE')
    # Validity is checked again after potentially slow observations.
    validate(job, scope, fixture=fixture)
    # Journal before sending. A failed journal write cannot be followed by a mutation.
    report['status'] = 'UPDATE_PENDING'
    report['update_attempts'] = 1  # Attempt reserved; after a crash its outcome is unknown.
    event('UPDATE_PENDING', update_digest=digest(payload(job, 'after')))
    ambiguous = False
    try:
        response = client.exchange(build_update(job))
        code = response.rcode()
        event('UPDATE_RESPONSE', rcode=dns.rcode.to_text(code))
        if code != dns.rcode.NOERROR:
            return finish('PREREQUISITE_CONFLICT' if code in (dns.rcode.NXRRSET, dns.rcode.YXRRSET,
                                                           dns.rcode.NXDOMAIN, dns.rcode.YXDOMAIN)
                          else 'UPDATE_REJECTED')
    except (OSError, EOFError, dns.exception.DNSException, ValueError) as exc:
        ambiguous = True
        event('UPDATE_OUTCOME_UNKNOWN', error_class=type(exc).__name__)
    try:
        after = snapshot(job, client)
        event('AFTER_OBSERVED', observation_sha256=digest(after))
        if matches(after, job, 'after'):
            return finish('RECONCILED_APPLIED_OBSERVED' if ambiguous else 'APPLIED_OBSERVED')
        return finish('UNKNOWN_OUTCOME_OPERATOR_RECONCILIATION' if ambiguous else 'APPLIED_BUT_READBACK_DIFFERS')
    except (OSError, EOFError, dns.exception.DNSException, ValueError) as exc:
        event('READBACK_ERROR', error_class=type(exc).__name__)
        return finish('UNKNOWN_OUTCOME_OPERATOR_RECONCILIATION' if ambiguous else 'APPLIED_READBACK_INCONCLUSIVE')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('job', type=Path)
    parser.add_argument('--scope', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--observe-authorized-target', action='store_true')
    parser.add_argument('--execute-approved-change', action='store_true')
    args = parser.parse_args()
    if args.execute_approved_change and not args.observe_authorized_target:
        parser.error('Execution requires explicit authorized-target contact too')
    try:
        job = strict_loads(args.job.read_bytes())
        scope = strict_loads(args.scope.read_bytes())
        validate(job, scope)
        if not args.observe_authorized_target:
            print(json.dumps({'status': 'INPUT_CHECKED_NO_TARGET_CONTACT', 'enabled': job['enabled'] and scope['enabled']}))
            return 0 if job['enabled'] and scope['enabled'] else 4
        if args.output is None:
            parser.error('A private --output journal is required before contact')
        # Existing journals are never overwritten to hide an uncertain prior attempt.
        if args.output.exists():
            raise DNSChangeError('Journal already exists; inspect and reconcile the prior operation before a new invocation')
        # Reserve this journal exclusively before contact; no concurrent run may reuse it.
        fd = os.open(args.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump({'status': 'RESERVED_NOT_SENT', 'operation_id': job['operation_id']}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        client = Client(job['server'], job['port'], job['key_name'], os.environ.get('DNS_TSIG_SECRET', ''))
        result = change(job, scope, client, execute=args.execute_approved_change,
                        record=lambda r: write_private(args.output, r))
        print(json.dumps({k: result[k] for k in ('status', 'operation_id', 'update_attempts', 'activation_authorized')}))
        return 0 if result['status'] in STATES or result['status'] == 'READY_FOR_INDEPENDENT_REVIEW_NO_UPDATE' else 2
    except (OSError, ValueError, dns.exception.DNSException) as exc:
        print(json.dumps({'status': 'BLOCKED_INPUT_OR_TRUST', 'error_class': type(exc).__name__,
                          'reason': str(exc) if isinstance(exc, DNSChangeError) else 'Invalid local input or trust material'}))
        return 4


if __name__ == '__main__':
    raise SystemExit(main())
)
HEX64 = re.compile(r'^[0-9a-f]{64}
JOB_KEYS = {'version', 'enabled', 'operation_id', 'tenant_id', 'resource_id',
            'zone', 'server', 'port', 'key_name', 'engineering_record_ref',
            'valid_until', 'previous_marker', 'records'}
SCOPE_KEYS = {'version', 'enabled', 'operation_id', 'tenant_id', 'resource_id',
              'zone', 'server', 'port', 'key_name', 'engineering_record_ref',
              'valid_until', 'transport_acceptance_ref', 'allowed_records'}
STATES = {'APPLIED_OBSERVED', 'ALREADY_APPLIED_OBSERVED', 'RECONCILED_APPLIED_OBSERVED'}


class DNSChangeError(ValueError):
    """Safe diagnostic; messages never include credentials or server response bodies."""


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def fqdn(value: Any) -> str:
    if not isinstance(value, str) or not value.endswith('.') or value != value.lower():
        raise DNSChangeError('Use a lower-case absolute DNS name with a trailing dot')
    labels = value[:-1].split('.')
    if len(labels) < 2 or len(value) > 253 or any(not LABEL.fullmatch(x) for x in labels):
        raise DNSChangeError('Unsupported DNS name; wildcards, escapes and empty labels are forbidden')
    return value


def deadline(value: Any, now: datetime) -> None:
    try:
        when = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if when.tzinfo is None or when <= now:
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        raise DNSChangeError('A current timezone-aware validity limit is required') from None


def address(value: Any, family: int, *, fixture: bool = False) -> str:
    try:
        parsed = ipaddress.ip_address(value)
    except (ValueError, TypeError):
        raise DNSChangeError('Invalid address') from None
    if parsed.version != family or str(parsed) != value or parsed.is_unspecified or parsed.is_multicast \
            or parsed.is_loopback or parsed.is_link_local:
        raise DNSChangeError('Address family, representation or scope is invalid')
    if not fixture and any(parsed.version == net.version and parsed in net for net in DOC_NETS):
        raise DNSChangeError('Documentation addresses are not actual allocations')
    return value


def payload(job: dict, side: str) -> list[dict]:
    return [{'name': r['name'], 'type': r['type'], 'value': r[side]}
            for r in sorted(job['records'], key=lambda x: (x['name'], x['type']))]


def owner_token(job: dict) -> str:
    return digest([job['tenant_id'], job['resource_id']])[:24]


def marker_name(job: dict) -> str:
    # Opaque owner label is generated, not supplied as an arbitrary TXT record name.
    return f"_hosting-{owner_token(job)}.{job['zone']}"


def name_markers(job: dict) -> list[str]:
    # Name-scoped markers prevent A/AAAA split ownership and reuse after deletion.
    return sorted({'_hosting-owner.' + r['name'] for r in job['records']})


def marker_value(job: dict) -> str:
    return f"hosting-v1 {owner_token(job)} {job['operation_id']} {digest(payload(job, 'after'))}"


def marker_rr(value: str | None) -> dict | None:
    return None if value is None else {'ttl': 300, 'values': [value]}


def validate(job: dict, scope: dict, *, now: datetime | None = None,
             fixture: bool = False) -> None:
    now = now or datetime.now(timezone.utc)
    if not isinstance(job, dict) or set(job) != JOB_KEYS or not isinstance(scope, dict) or set(scope) != SCOPE_KEYS:
        raise DNSChangeError('Unexpected or missing job/scope fields')
    if type(job['version']) is not int or job['version'] != 1 or type(scope['version']) is not int or scope['version'] != 1:
        raise DNSChangeError('Unsupported integration version')
    if type(job['enabled']) is not bool or type(scope['enabled']) is not bool:
        raise DNSChangeError('Explicit enabled booleans are required')
    for key in ('operation_id', 'tenant_id', 'resource_id', 'zone', 'server', 'port',
                'key_name', 'engineering_record_ref'):
        if type(job[key]) is not type(scope[key]) or job[key] != scope[key]:
            raise DNSChangeError(f'Job differs from independently supplied scope: {key}')
    for key in ('tenant_id', 'resource_id'):
        if not isinstance(job[key], str) or not OWNER.fullmatch(job[key]):
            raise DNSChangeError('Invalid tenant or resource identifier')
    try:
        if str(uuid.UUID(job['operation_id'])) != job['operation_id']:
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        raise DNSChangeError('Canonical operation UUID required') from None
    for record in (job, scope):
        deadline(record['valid_until'], now)
    for key, value in [('engineering_record_ref', job['engineering_record_ref']),
                       ('transport_acceptance_ref', scope['transport_acceptance_ref'])]:
        if not isinstance(value, str) or not 1 <= len(value) <= 256 or any(ord(c) < 32 for c in value):
            raise DNSChangeError(f'A bounded non-secret {key} is required')
    zone = fqdn(job['zone'])
    fqdn(job['key_name'])
    try:
        server = ipaddress.ip_address(job['server'])
    except (ValueError, TypeError):
        raise DNSChangeError('An explicit authoritative server IP is required; discovery is disabled') from None
    if str(server) != job['server'] or server.is_unspecified or server.is_multicast or server.is_link_local:
        raise DNSChangeError('Invalid authoritative server scope')
    if fixture:
        if not server.is_loopback or not zone.endswith(('.invalid.', '.in-addr.arpa.', '.ip6.arpa.')):
            raise DNSChangeError('Test transport is restricted to loopback and reserved fixture/reverse zones')
    elif server.is_loopback or any(server.version == n.version and server in n for n in DOC_NETS) \
            or zone.endswith(('.invalid.', '.example.', '.test.')):
        raise DNSChangeError('Test names and addresses cannot select a native target')
    if type(job['port']) is not int or not 1 <= job['port'] <= 65535:
        raise DNSChangeError('Invalid DNS TCP port')
    records, allowed = job['records'], scope['allowed_records']
    if not isinstance(records, list) or not 1 <= len(records) <= 8 or not isinstance(allowed, list):
        raise DNSChangeError('Provide one to eight explicitly owned record sets')
    accepted = {}
    for item in allowed:
        if not isinstance(item, dict) or set(item) != {'name', 'type', 'values', 'maximum_ttl'}:
            raise DNSChangeError('Invalid exact allocation record')
        if not isinstance(item['type'], str):
            raise DNSChangeError('Record type must be a string')
        pair = (fqdn(item['name']), item['type'])
        if pair in accepted or item['type'] not in ('A', 'AAAA', 'PTR'):
            raise DNSChangeError('Duplicate or unsupported scope record')
        if type(item['maximum_ttl']) is not int or not 1 <= item['maximum_ttl'] <= 2147483647:
            raise DNSChangeError('Invalid allowed TTL ceiling')
        if not isinstance(item['values'], list) or not 1 <= len(item['values']) <= 16 \
                or any(not isinstance(x, str) for x in item['values']) or len(set(item['values'])) != len(item['values']):
            raise DNSChangeError('Exact allocated addresses or PTR targets are required')
        accepted[pair] = item
    seen = set()
    for record in records:
        if not isinstance(record, dict) or set(record) != {'name', 'type', 'before', 'after'}:
            raise DNSChangeError('Each change requires explicit before and after values')
        name, rtype = fqdn(record['name']), record['type']
        if not isinstance(rtype, str):
            raise DNSChangeError('Record type must be a string')
        if not dns.name.from_text(name).is_subdomain(dns.name.from_text(zone)) or name == zone:
            raise DNSChangeError('Record must be strictly within the named zone, not at its apex')
        pair = (name, rtype)
        if pair in seen or pair not in accepted:
            raise DNSChangeError('Record is duplicate or outside the accepted scope')
        seen.add(pair)
        if rtype == 'PTR':
            try:
                # Exact reverse names only, no classless reverse alias invention.
                if name.endswith('.in-addr.arpa.'):
                    ipaddress.IPv4Address('.'.join(reversed(name.removesuffix('.in-addr.arpa.').split('.'))))
                elif name.endswith('.ip6.arpa.'):
                    nibbles = name.removesuffix('.ip6.arpa.').split('.')
                    if len(nibbles) != 32 or any(not re.fullmatch('[0-9a-f]', x) for x in nibbles):
                        raise ValueError
                else:
                    raise ValueError
            except ValueError:
                raise DNSChangeError('PTR requires an exact address reverse name') from None
        elif zone.endswith(('.in-addr.arpa.', '.ip6.arpa.')):
            raise DNSChangeError('Address records cannot be written into reverse zones')
        for side in ('before', 'after'):
            value = record[side]
            if value is None:
                continue
            if not isinstance(value, dict) or set(value) != {'ttl', 'values'} or type(value['ttl']) is not int \
                    or not 1 <= value['ttl'] <= accepted[pair]['maximum_ttl']:
                raise DNSChangeError('Invalid record-set TTL or structure')
            values = value['values']
            if not isinstance(values, list) or not 1 <= len(values) <= 8 or any(not isinstance(x, str) for x in values) \
                    or len(set(values)) != len(values) or values != sorted(values):
                raise DNSChangeError('Use a nonempty sorted unique record-value list')
            if not set(values) <= set(accepted[pair]['values']):
                raise DNSChangeError('DNS value is outside exact allocation/target acceptance')
            for item in values:
                if rtype in ('A', 'AAAA'):
                    address(item, 4 if rtype == 'A' else 6, fixture=fixture)
                else:
                    fqdn(item)
            if rtype == 'PTR' and len(values) != 1:
                raise DNSChangeError('The selected PTR profile has exactly one canonical target')
    if seen != set(accepted):
        raise DNSChangeError('Scope and change must identify the same immutable record group')
    prior = job['previous_marker']
    if prior is None:
        if any(r['before'] is not None for r in records) or all(r['after'] is None for r in records):
            raise DNSChangeError('Unowned groups can only be created from entirely absent records')
    else:
        expected = rf'hosting-v1 {owner_token(job)} [0-9a-f-]{{36}} {digest(payload(job, "before"))}'
        if not isinstance(prior, str) or not re.fullmatch(expected, prior):
            raise DNSChangeError('Prior owner/generation marker does not match the expected before state')
    if len(marker_name(job)) > 253 or any(len(n) > 253 for n in name_markers(job)):
        raise DNSChangeError('Generated ownership name is too long')


class Client:
    """Fixed-IP TCP+TSIG transport. TSIG authenticates; it does not encrypt DNS data."""
    def __init__(self, server: str, port: int, key_name: str, secret: str, timeout: float = 3):
        ipaddress.ip_address(server)
        fqdn(key_name)
        try:
            decoded = base64.b64decode(secret, validate=True)
            if len(decoded) < 32:
                raise ValueError
        except (ValueError, TypeError):
            raise DNSChangeError('Inject a base64 TSIG secret of at least 32 bytes') from None
        if not 0.05 <= timeout <= 30 or type(port) is not int or not 1 <= port <= 65535:
            raise DNSChangeError('Invalid bounded DNS transport settings')
        self.server, self.port, self.key_name, self.timeout = server, port, key_name, timeout
        self.keyring = dns.tsigkeyring.from_text({key_name: secret})

    def exchange(self, message: dns.message.Message) -> dns.message.Message:
        message.use_tsig(self.keyring, keyname=self.key_name, algorithm=dns.tsig.HMAC_SHA256)
        response = dns.query.tcp(message, self.server, port=self.port, timeout=self.timeout)
        if not response.had_tsig or response.keyname != dns.name.from_text(self.key_name) \
                or response.keyalgorithm != dns.tsig.HMAC_SHA256 or not message.is_response(response):
            raise DNSChangeError('Missing or mismatched authenticated DNS response')
        if response.flags & dns.flags.TC:
            raise DNSChangeError('Truncated TCP response is inconclusive')
        return response

    def rrset(self, name: str, rtype: str, zone: str) -> dict | None:
        query = dns.message.make_query(name, rtype)
        query.flags &= ~dns.flags.RD
        response = self.exchange(query)
        if not response.flags & dns.flags.AA or response.rcode() not in (dns.rcode.NOERROR, dns.rcode.NXDOMAIN):
            raise DNSChangeError('Authoritative authenticated observation is unavailable')
        answer = [r for r in response.answer if r.name == dns.name.from_text(name)
                  and r.rdtype == dns.rdatatype.from_text(rtype) and r.rdclass == dns.rdataclass.IN]
        if response.rcode() == dns.rcode.NXDOMAIN and response.answer:
            raise DNSChangeError('Contradictory negative response')
        if len(answer) > 1 or len(response.answer) != len(answer):
            raise DNSChangeError('Aliases, referrals and unrelated answer records are not followed')
        if not answer:
            if not any(r.name == dns.name.from_text(zone) and r.rdtype == dns.rdatatype.SOA
                       for r in response.authority):
                raise DNSChangeError('Negative observation lacks the exact authoritative zone SOA')
            return None
        rr = answer[0]
        if rtype == 'TXT':
            values = sorted(b''.join(r.strings).decode('ascii') for r in rr)
        else:
            values = sorted(r.to_text().lower() for r in rr)
        return {'ttl': rr.ttl, 'values': values}


def snapshot(job: dict, client: Client) -> dict:
    # Validate the exact zone authority rather than infer it from a recursive answer.
    if client.rrset(job['zone'], 'SOA', job['zone']) is None:
        raise DNSChangeError('Named authoritative zone is unavailable')
    names = sorted({r['name'] for r in job['records']} | {marker_name(job)} | set(name_markers(job)))
    aliases = {name: client.rrset(name, 'CNAME', job['zone']) for name in names}
    if any(x is not None for x in aliases.values()):
        raise DNSChangeError('CNAME conflicts with the selected exact-record profile')
    marker = client.rrset(marker_name(job), 'TXT', job['zone'])
    owners = {name: client.rrset(name, 'TXT', job['zone']) for name in name_markers(job)}
    values = [{'name': r['name'], 'type': r['type'],
               'value': client.rrset(r['name'], r['type'], job['zone'])}
              for r in sorted(job['records'], key=lambda x: (x['name'], x['type']))]
    return {'marker': marker, 'name_owners': owners, 'records': values}


def matches(observed: dict, job: dict, side: str) -> bool:
    target = marker_value(job) if side == 'after' else job['previous_marker']
    return observed == {'marker': marker_rr(target), 'name_owners': {n: marker_rr(target) for n in name_markers(job)},
                        'records': payload(job, side)}


def build_update(job: dict) -> dns.update.UpdateMessage:
    update = dns.update.Update(job['zone'])
    mname = marker_name(job)
    if job['previous_marker'] is None:
        # Name-not-in-use, not merely TXT absence, protects the first ownership claim.
        update.absent(mname)
    else:
        update.present(mname, 'TXT', json.dumps(job['previous_marker']))
        update.absent(mname, 'CNAME')
    for name in name_markers(job):
        if job['previous_marker'] is None:
            update.absent(name)
        else:
            update.present(name, 'TXT', json.dumps(job['previous_marker']))
            update.absent(name, 'CNAME')
    if job['previous_marker'] is None:
        for name in sorted({r['name'] for r in job['records']}):
            update.absent(name)  # Never split a new owner across existing A/AAAA names.
    for record in job['records']:
        name, rtype = record['name'], record['type']
        update.absent(name, 'CNAME')
        before = record['before']
        if before is None:
            update.absent(name, rtype)
        else:
            update.present(name, rtype, *before['values'])
        update.delete(name, rtype)
        if record['after'] is not None:
            update.add(name, record['after']['ttl'], rtype, *record['after']['values'])
    # Retain a tombstone marker on delete: replay detection and ownership outlive records.
    update.replace(mname, 300, 'TXT', json.dumps(marker_value(job)))
    for name in name_markers(job):
        update.replace(name, 300, 'TXT', json.dumps(marker_value(job)))
    return update


def change(job: dict, scope: dict, client: Client, *, execute: bool = False,
           fixture: bool = False, record=None) -> dict:
    validate(job, scope, fixture=fixture)
    if execute and not fixture and record is None:
        raise DNSChangeError('A native mutation requires a journal writer')
    if not job['enabled'] or not scope['enabled']:
        raise DNSChangeError('Disabled examples cannot contact a target')
    if (client.server, client.port, client.key_name) != (job['server'], job['port'], job['key_name']):
        raise DNSChangeError('Transport differs from accepted endpoint and key scope')
    report = {'kind': 'SCOPED_DNS_TRANSACTION', 'operation_id': job['operation_id'],
              'job_sha256': digest(job), 'scope_sha256': digest(scope),
              'engineering_record_ref': job['engineering_record_ref'],
              'started_at': datetime.now(timezone.utc).isoformat(), 'update_attempts': 0,
              'status': 'OBSERVING', 'events': [], 'activation_authorized': False}

    def event(stage: str, **data):
        report['events'].append({'stage': stage, 'at': datetime.now(timezone.utc).isoformat(), **data})
        if record is not None:
            record(report)

    def finish(status: str):
        report['status'] = status
        report['finished_at'] = datetime.now(timezone.utc).isoformat()
        report['limitations'] = [
            'Authenticated authoritative reads are not cache/secondary propagation proof',
            'TSIG authentication is not confidentiality or independent approval verification',
            'One zone only; forward and reverse zones are not one transaction',
            'RFC 2136 compares RR data, not TTL; single-writer ownership remains required',
            'A DNS observation does not authorize network activation or address reuse',
            'Deletion retains an ownership tombstone; releasing it needs separate governance']
        if record is not None:
            record(report)
        return report

    try:
        before = snapshot(job, client)
        event('BEFORE_OBSERVED', observation_sha256=digest(before))
    except (OSError, EOFError, dns.exception.DNSException, ValueError) as exc:
        event('OBSERVATION_ERROR', error_class=type(exc).__name__)
        return finish('INCONCLUSIVE_NO_UPDATE')
    if matches(before, job, 'after'):
        return finish('ALREADY_APPLIED_OBSERVED')
    if not matches(before, job, 'before'):
        return finish('CONFLICT_NO_UPDATE')
    if not execute:
        return finish('READY_FOR_INDEPENDENT_REVIEW_NO_UPDATE')
    # Validity is checked again after potentially slow observations.
    validate(job, scope, fixture=fixture)
    # Journal before sending. A failed journal write cannot be followed by a mutation.
    report['status'] = 'UPDATE_PENDING'
    report['update_attempts'] = 1  # Attempt reserved; after a crash its outcome is unknown.
    event('UPDATE_PENDING', update_digest=digest(payload(job, 'after')))
    ambiguous = False
    try:
        response = client.exchange(build_update(job))
        code = response.rcode()
        event('UPDATE_RESPONSE', rcode=dns.rcode.to_text(code))
        if code != dns.rcode.NOERROR:
            return finish('PREREQUISITE_CONFLICT' if code in (dns.rcode.NXRRSET, dns.rcode.YXRRSET,
                                                           dns.rcode.NXDOMAIN, dns.rcode.YXDOMAIN)
                          else 'UPDATE_REJECTED')
    except (OSError, EOFError, dns.exception.DNSException, ValueError) as exc:
        ambiguous = True
        event('UPDATE_OUTCOME_UNKNOWN', error_class=type(exc).__name__)
    try:
        after = snapshot(job, client)
        event('AFTER_OBSERVED', observation_sha256=digest(after))
        if matches(after, job, 'after'):
            return finish('RECONCILED_APPLIED_OBSERVED' if ambiguous else 'APPLIED_OBSERVED')
        return finish('UNKNOWN_OUTCOME_OPERATOR_RECONCILIATION' if ambiguous else 'APPLIED_BUT_READBACK_DIFFERS')
    except (OSError, EOFError, dns.exception.DNSException, ValueError) as exc:
        event('READBACK_ERROR', error_class=type(exc).__name__)
        return finish('UNKNOWN_OUTCOME_OPERATOR_RECONCILIATION' if ambiguous else 'APPLIED_READBACK_INCONCLUSIVE')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('job', type=Path)
    parser.add_argument('--scope', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--observe-authorized-target', action='store_true')
    parser.add_argument('--execute-approved-change', action='store_true')
    args = parser.parse_args()
    if args.execute_approved_change and not args.observe_authorized_target:
        parser.error('Execution requires explicit authorized-target contact too')
    try:
        job = strict_loads(args.job.read_bytes())
        scope = strict_loads(args.scope.read_bytes())
        validate(job, scope)
        if not args.observe_authorized_target:
            print(json.dumps({'status': 'INPUT_CHECKED_NO_TARGET_CONTACT', 'enabled': job['enabled'] and scope['enabled']}))
            return 0 if job['enabled'] and scope['enabled'] else 4
        if args.output is None:
            parser.error('A private --output journal is required before contact')
        # Existing journals are never overwritten to hide an uncertain prior attempt.
        if args.output.exists():
            raise DNSChangeError('Journal already exists; inspect and reconcile the prior operation before a new invocation')
        # Reserve this journal exclusively before contact; no concurrent run may reuse it.
        fd = os.open(args.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump({'status': 'RESERVED_NOT_SENT', 'operation_id': job['operation_id']}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        client = Client(job['server'], job['port'], job['key_name'], os.environ.get('DNS_TSIG_SECRET', ''))
        result = change(job, scope, client, execute=args.execute_approved_change,
                        record=lambda r: write_private(args.output, r))
        print(json.dumps({k: result[k] for k in ('status', 'operation_id', 'update_attempts', 'activation_authorized')}))
        return 0 if result['status'] in STATES or result['status'] == 'READY_FOR_INDEPENDENT_REVIEW_NO_UPDATE' else 2
    except (OSError, ValueError, dns.exception.DNSException) as exc:
        print(json.dumps({'status': 'BLOCKED_INPUT_OR_TRUST', 'error_class': type(exc).__name__,
                          'reason': str(exc) if isinstance(exc, DNSChangeError) else 'Invalid local input or trust material'}))
        return 4


if __name__ == '__main__':
    raise SystemExit(main())
)
JOB_KEYS = {'version', 'enabled', 'operation_id', 'tenant_id', 'resource_id',
            'zone', 'server', 'port', 'key_name', 'engineering_record_ref',
            'valid_until', 'previous_marker', 'records'}
SCOPE_KEYS = {'version', 'enabled', 'operation_id', 'tenant_id', 'resource_id',
              'zone', 'server', 'port', 'key_name', 'engineering_record_ref',
              'valid_until', 'transport_acceptance_ref', 'allowed_records'}
STATES = {'APPLIED_OBSERVED', 'ALREADY_APPLIED_OBSERVED', 'RECONCILED_APPLIED_OBSERVED'}


class DNSChangeError(ValueError):
    """Safe diagnostic; messages never include credentials or server response bodies."""


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def fqdn(value: Any) -> str:
    if not isinstance(value, str) or not value.endswith('.') or value != value.lower():
        raise DNSChangeError('Use a lower-case absolute DNS name with a trailing dot')
    labels = value[:-1].split('.')
    if len(labels) < 2 or len(value) > 253 or any(not LABEL.fullmatch(x) for x in labels):
        raise DNSChangeError('Unsupported DNS name; wildcards, escapes and empty labels are forbidden')
    return value


def deadline(value: Any, now: datetime) -> None:
    try:
        when = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if when.tzinfo is None or when <= now:
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        raise DNSChangeError('A current timezone-aware validity limit is required') from None


def address(value: Any, family: int, *, fixture: bool = False) -> str:
    try:
        parsed = ipaddress.ip_address(value)
    except (ValueError, TypeError):
        raise DNSChangeError('Invalid address') from None
    if parsed.version != family or str(parsed) != value or parsed.is_unspecified or parsed.is_multicast \
            or parsed.is_loopback or parsed.is_link_local:
        raise DNSChangeError('Address family, representation or scope is invalid')
    if not fixture and any(parsed.version == net.version and parsed in net for net in DOC_NETS):
        raise DNSChangeError('Documentation addresses are not actual allocations')
    return value


def payload(job: dict, side: str) -> list[dict]:
    return [{'name': r['name'], 'type': r['type'], 'value': r[side]}
            for r in sorted(job['records'], key=lambda x: (x['name'], x['type']))]


def owner_token(job: dict) -> str:
    return digest([job['tenant_id'], job['resource_id']])[:24]


def marker_name(job: dict) -> str:
    # Opaque owner label is generated, not supplied as an arbitrary TXT record name.
    return f"_hosting-{owner_token(job)}.{job['zone']}"


def name_markers(job: dict) -> list[str]:
    # Name-scoped markers prevent A/AAAA split ownership and reuse after deletion.
    return sorted({'_hosting-owner.' + r['name'] for r in job['records']})


def marker_value(job: dict) -> str:
    return f"hosting-v1 {owner_token(job)} {job['operation_id']} {digest(payload(job, 'after'))}"


def marker_rr(value: str | None) -> dict | None:
    return None if value is None else {'ttl': 300, 'values': [value]}


def validate(job: dict, scope: dict, *, now: datetime | None = None,
             fixture: bool = False) -> None:
    now = now or datetime.now(timezone.utc)
    if not isinstance(job, dict) or set(job) != JOB_KEYS or not isinstance(scope, dict) or set(scope) != SCOPE_KEYS:
        raise DNSChangeError('Unexpected or missing job/scope fields')
    if type(job['version']) is not int or job['version'] != 1 or type(scope['version']) is not int or scope['version'] != 1:
        raise DNSChangeError('Unsupported integration version')
    if type(job['enabled']) is not bool or type(scope['enabled']) is not bool:
        raise DNSChangeError('Explicit enabled booleans are required')
    for key in ('operation_id', 'tenant_id', 'resource_id', 'zone', 'server', 'port',
                'key_name', 'engineering_record_ref'):
        if type(job[key]) is not type(scope[key]) or job[key] != scope[key]:
            raise DNSChangeError(f'Job differs from independently supplied scope: {key}')
    for key in ('tenant_id', 'resource_id'):
        if not isinstance(job[key], str) or not OWNER.fullmatch(job[key]):
            raise DNSChangeError('Invalid tenant or resource identifier')
    try:
        if str(uuid.UUID(job['operation_id'])) != job['operation_id']:
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        raise DNSChangeError('Canonical operation UUID required') from None
    for record in (job, scope):
        deadline(record['valid_until'], now)
    for key, value in [('engineering_record_ref', job['engineering_record_ref']),
                       ('transport_acceptance_ref', scope['transport_acceptance_ref'])]:
        if not isinstance(value, str) or not 1 <= len(value) <= 256 or any(ord(c) < 32 for c in value):
            raise DNSChangeError(f'A bounded non-secret {key} is required')
    zone = fqdn(job['zone'])
    fqdn(job['key_name'])
    try:
        server = ipaddress.ip_address(job['server'])
    except (ValueError, TypeError):
        raise DNSChangeError('An explicit authoritative server IP is required; discovery is disabled') from None
    if str(server) != job['server'] or server.is_unspecified or server.is_multicast or server.is_link_local:
        raise DNSChangeError('Invalid authoritative server scope')
    if fixture:
        if not server.is_loopback or not zone.endswith(('.invalid.', '.in-addr.arpa.', '.ip6.arpa.')):
            raise DNSChangeError('Test transport is restricted to loopback and reserved fixture/reverse zones')
    elif server.is_loopback or any(server.version == n.version and server in n for n in DOC_NETS) \
            or zone.endswith(('.invalid.', '.example.', '.test.')):
        raise DNSChangeError('Test names and addresses cannot select a native target')
    if type(job['port']) is not int or not 1 <= job['port'] <= 65535:
        raise DNSChangeError('Invalid DNS TCP port')
    records, allowed = job['records'], scope['allowed_records']
    if not isinstance(records, list) or not 1 <= len(records) <= 8 or not isinstance(allowed, list):
        raise DNSChangeError('Provide one to eight explicitly owned record sets')
    accepted = {}
    for item in allowed:
        if not isinstance(item, dict) or set(item) != {'name', 'type', 'values', 'maximum_ttl'}:
            raise DNSChangeError('Invalid exact allocation record')
        if not isinstance(item['type'], str):
            raise DNSChangeError('Record type must be a string')
        pair = (fqdn(item['name']), item['type'])
        if pair in accepted or item['type'] not in ('A', 'AAAA', 'PTR'):
            raise DNSChangeError('Duplicate or unsupported scope record')
        if type(item['maximum_ttl']) is not int or not 1 <= item['maximum_ttl'] <= 2147483647:
            raise DNSChangeError('Invalid allowed TTL ceiling')
        if not isinstance(item['values'], list) or not 1 <= len(item['values']) <= 16 \
                or any(not isinstance(x, str) for x in item['values']) or len(set(item['values'])) != len(item['values']):
            raise DNSChangeError('Exact allocated addresses or PTR targets are required')
        accepted[pair] = item
    seen = set()
    for record in records:
        if not isinstance(record, dict) or set(record) != {'name', 'type', 'before', 'after'}:
            raise DNSChangeError('Each change requires explicit before and after values')
        name, rtype = fqdn(record['name']), record['type']
        if not isinstance(rtype, str):
            raise DNSChangeError('Record type must be a string')
        if not dns.name.from_text(name).is_subdomain(dns.name.from_text(zone)) or name == zone:
            raise DNSChangeError('Record must be strictly within the named zone, not at its apex')
        pair = (name, rtype)
        if pair in seen or pair not in accepted:
            raise DNSChangeError('Record is duplicate or outside the accepted scope')
        seen.add(pair)
        if rtype == 'PTR':
            try:
                # Exact reverse names only, no classless reverse alias invention.
                if name.endswith('.in-addr.arpa.'):
                    ipaddress.IPv4Address('.'.join(reversed(name.removesuffix('.in-addr.arpa.').split('.'))))
                elif name.endswith('.ip6.arpa.'):
                    nibbles = name.removesuffix('.ip6.arpa.').split('.')
                    if len(nibbles) != 32 or any(not re.fullmatch('[0-9a-f]', x) for x in nibbles):
                        raise ValueError
                else:
                    raise ValueError
            except ValueError:
                raise DNSChangeError('PTR requires an exact address reverse name') from None
        elif zone.endswith(('.in-addr.arpa.', '.ip6.arpa.')):
            raise DNSChangeError('Address records cannot be written into reverse zones')
        for side in ('before', 'after'):
            value = record[side]
            if value is None:
                continue
            if not isinstance(value, dict) or set(value) != {'ttl', 'values'} or type(value['ttl']) is not int \
                    or not 1 <= value['ttl'] <= accepted[pair]['maximum_ttl']:
                raise DNSChangeError('Invalid record-set TTL or structure')
            values = value['values']
            if not isinstance(values, list) or not 1 <= len(values) <= 8 or any(not isinstance(x, str) for x in values) \
                    or len(set(values)) != len(values) or values != sorted(values):
                raise DNSChangeError('Use a nonempty sorted unique record-value list')
            if not set(values) <= set(accepted[pair]['values']):
                raise DNSChangeError('DNS value is outside exact allocation/target acceptance')
            for item in values:
                if rtype in ('A', 'AAAA'):
                    address(item, 4 if rtype == 'A' else 6, fixture=fixture)
                else:
                    fqdn(item)
            if rtype == 'PTR' and len(values) != 1:
                raise DNSChangeError('The selected PTR profile has exactly one canonical target')
    if seen != set(accepted):
        raise DNSChangeError('Scope and change must identify the same immutable record group')
    prior = job['previous_marker']
    if prior is None:
        if any(r['before'] is not None for r in records) or all(r['after'] is None for r in records):
            raise DNSChangeError('Unowned groups can only be created from entirely absent records')
    else:
        expected = rf'hosting-v1 {owner_token(job)} [0-9a-f-]{{36}} {digest(payload(job, "before"))}'
        if not isinstance(prior, str) or not re.fullmatch(expected, prior):
            raise DNSChangeError('Prior owner/generation marker does not match the expected before state')
    if len(marker_name(job)) > 253 or any(len(n) > 253 for n in name_markers(job)):
        raise DNSChangeError('Generated ownership name is too long')


class Client:
    """Fixed-IP TCP+TSIG transport. TSIG authenticates; it does not encrypt DNS data."""
    def __init__(self, server: str, port: int, key_name: str, secret: str, timeout: float = 3):
        ipaddress.ip_address(server)
        fqdn(key_name)
        try:
            decoded = base64.b64decode(secret, validate=True)
            if len(decoded) < 32:
                raise ValueError
        except (ValueError, TypeError):
            raise DNSChangeError('Inject a base64 TSIG secret of at least 32 bytes') from None
        if not 0.05 <= timeout <= 30 or type(port) is not int or not 1 <= port <= 65535:
            raise DNSChangeError('Invalid bounded DNS transport settings')
        self.server, self.port, self.key_name, self.timeout = server, port, key_name, timeout
        self.keyring = dns.tsigkeyring.from_text({key_name: secret})

    def exchange(self, message: dns.message.Message) -> dns.message.Message:
        message.use_tsig(self.keyring, keyname=self.key_name, algorithm=dns.tsig.HMAC_SHA256)
        response = dns.query.tcp(message, self.server, port=self.port, timeout=self.timeout)
        if not response.had_tsig or response.keyname != dns.name.from_text(self.key_name) \
                or response.keyalgorithm != dns.tsig.HMAC_SHA256 or not message.is_response(response):
            raise DNSChangeError('Missing or mismatched authenticated DNS response')
        if response.flags & dns.flags.TC:
            raise DNSChangeError('Truncated TCP response is inconclusive')
        return response

    def rrset(self, name: str, rtype: str, zone: str) -> dict | None:
        query = dns.message.make_query(name, rtype)
        query.flags &= ~dns.flags.RD
        response = self.exchange(query)
        if not response.flags & dns.flags.AA or response.rcode() not in (dns.rcode.NOERROR, dns.rcode.NXDOMAIN):
            raise DNSChangeError('Authoritative authenticated observation is unavailable')
        answer = [r for r in response.answer if r.name == dns.name.from_text(name)
                  and r.rdtype == dns.rdatatype.from_text(rtype) and r.rdclass == dns.rdataclass.IN]
        if response.rcode() == dns.rcode.NXDOMAIN and response.answer:
            raise DNSChangeError('Contradictory negative response')
        if len(answer) > 1 or len(response.answer) != len(answer):
            raise DNSChangeError('Aliases, referrals and unrelated answer records are not followed')
        if not answer:
            if not any(r.name == dns.name.from_text(zone) and r.rdtype == dns.rdatatype.SOA
                       for r in response.authority):
                raise DNSChangeError('Negative observation lacks the exact authoritative zone SOA')
            return None
        rr = answer[0]
        if rtype == 'TXT':
            values = sorted(b''.join(r.strings).decode('ascii') for r in rr)
        else:
            values = sorted(r.to_text().lower() for r in rr)
        return {'ttl': rr.ttl, 'values': values}


def snapshot(job: dict, client: Client) -> dict:
    # Validate the exact zone authority rather than infer it from a recursive answer.
    if client.rrset(job['zone'], 'SOA', job['zone']) is None:
        raise DNSChangeError('Named authoritative zone is unavailable')
    names = sorted({r['name'] for r in job['records']} | {marker_name(job)} | set(name_markers(job)))
    aliases = {name: client.rrset(name, 'CNAME', job['zone']) for name in names}
    if any(x is not None for x in aliases.values()):
        raise DNSChangeError('CNAME conflicts with the selected exact-record profile')
    marker = client.rrset(marker_name(job), 'TXT', job['zone'])
    owners = {name: client.rrset(name, 'TXT', job['zone']) for name in name_markers(job)}
    values = [{'name': r['name'], 'type': r['type'],
               'value': client.rrset(r['name'], r['type'], job['zone'])}
              for r in sorted(job['records'], key=lambda x: (x['name'], x['type']))]
    return {'marker': marker, 'name_owners': owners, 'records': values}


def matches(observed: dict, job: dict, side: str) -> bool:
    target = marker_value(job) if side == 'after' else job['previous_marker']
    return observed == {'marker': marker_rr(target), 'name_owners': {n: marker_rr(target) for n in name_markers(job)},
                        'records': payload(job, side)}


def build_update(job: dict) -> dns.update.UpdateMessage:
    update = dns.update.Update(job['zone'])
    mname = marker_name(job)
    if job['previous_marker'] is None:
        # Name-not-in-use, not merely TXT absence, protects the first ownership claim.
        update.absent(mname)
    else:
        update.present(mname, 'TXT', json.dumps(job['previous_marker']))
        update.absent(mname, 'CNAME')
    for name in name_markers(job):
        if job['previous_marker'] is None:
            update.absent(name)
        else:
            update.present(name, 'TXT', json.dumps(job['previous_marker']))
            update.absent(name, 'CNAME')
    if job['previous_marker'] is None:
        for name in sorted({r['name'] for r in job['records']}):
            update.absent(name)  # Never split a new owner across existing A/AAAA names.
    for record in job['records']:
        name, rtype = record['name'], record['type']
        update.absent(name, 'CNAME')
        before = record['before']
        if before is None:
            update.absent(name, rtype)
        else:
            update.present(name, rtype, *before['values'])
        update.delete(name, rtype)
        if record['after'] is not None:
            update.add(name, record['after']['ttl'], rtype, *record['after']['values'])
    # Retain a tombstone marker on delete: replay detection and ownership outlive records.
    update.replace(mname, 300, 'TXT', json.dumps(marker_value(job)))
    for name in name_markers(job):
        update.replace(name, 300, 'TXT', json.dumps(marker_value(job)))
    return update


def change(job: dict, scope: dict, client: Client, *, execute: bool = False,
           fixture: bool = False, record=None) -> dict:
    validate(job, scope, fixture=fixture)
    if execute and not fixture and record is None:
        raise DNSChangeError('A native mutation requires a journal writer')
    if not job['enabled'] or not scope['enabled']:
        raise DNSChangeError('Disabled examples cannot contact a target')
    if (client.server, client.port, client.key_name) != (job['server'], job['port'], job['key_name']):
        raise DNSChangeError('Transport differs from accepted endpoint and key scope')
    report = {'kind': 'SCOPED_DNS_TRANSACTION', 'operation_id': job['operation_id'],
              'job_sha256': digest(job), 'scope_sha256': digest(scope),
              'engineering_record_ref': job['engineering_record_ref'],
              'started_at': datetime.now(timezone.utc).isoformat(), 'update_attempts': 0,
              'status': 'OBSERVING', 'events': [], 'activation_authorized': False}

    def event(stage: str, **data):
        report['events'].append({'stage': stage, 'at': datetime.now(timezone.utc).isoformat(), **data})
        if record is not None:
            record(report)

    def finish(status: str):
        report['status'] = status
        report['finished_at'] = datetime.now(timezone.utc).isoformat()
        report['limitations'] = [
            'Authenticated authoritative reads are not cache/secondary propagation proof',
            'TSIG authentication is not confidentiality or independent approval verification',
            'One zone only; forward and reverse zones are not one transaction',
            'RFC 2136 compares RR data, not TTL; single-writer ownership remains required',
            'A DNS observation does not authorize network activation or address reuse',
            'Deletion retains an ownership tombstone; releasing it needs separate governance']
        if record is not None:
            record(report)
        return report

    try:
        before = snapshot(job, client)
        event('BEFORE_OBSERVED', observation_sha256=digest(before))
    except (OSError, EOFError, dns.exception.DNSException, ValueError) as exc:
        event('OBSERVATION_ERROR', error_class=type(exc).__name__)
        return finish('INCONCLUSIVE_NO_UPDATE')
    if matches(before, job, 'after'):
        return finish('ALREADY_APPLIED_OBSERVED')
    if not matches(before, job, 'before'):
        return finish('CONFLICT_NO_UPDATE')
    if not execute:
        return finish('READY_FOR_INDEPENDENT_REVIEW_NO_UPDATE')
    # Validity is checked again after potentially slow observations.
    validate(job, scope, fixture=fixture)
    # Journal before sending. A failed journal write cannot be followed by a mutation.
    report['status'] = 'UPDATE_PENDING'
    report['update_attempts'] = 1  # Attempt reserved; after a crash its outcome is unknown.
    event('UPDATE_PENDING', update_digest=digest(payload(job, 'after')))
    ambiguous = False
    try:
        response = client.exchange(build_update(job))
        code = response.rcode()
        event('UPDATE_RESPONSE', rcode=dns.rcode.to_text(code))
        if code != dns.rcode.NOERROR:
            return finish('PREREQUISITE_CONFLICT' if code in (dns.rcode.NXRRSET, dns.rcode.YXRRSET,
                                                           dns.rcode.NXDOMAIN, dns.rcode.YXDOMAIN)
                          else 'UPDATE_REJECTED')
    except (OSError, EOFError, dns.exception.DNSException, ValueError) as exc:
        ambiguous = True
        event('UPDATE_OUTCOME_UNKNOWN', error_class=type(exc).__name__)
    try:
        after = snapshot(job, client)
        event('AFTER_OBSERVED', observation_sha256=digest(after))
        if matches(after, job, 'after'):
            return finish('RECONCILED_APPLIED_OBSERVED' if ambiguous else 'APPLIED_OBSERVED')
        return finish('UNKNOWN_OUTCOME_OPERATOR_RECONCILIATION' if ambiguous else 'APPLIED_BUT_READBACK_DIFFERS')
    except (OSError, EOFError, dns.exception.DNSException, ValueError) as exc:
        event('READBACK_ERROR', error_class=type(exc).__name__)
        return finish('UNKNOWN_OUTCOME_OPERATOR_RECONCILIATION' if ambiguous else 'APPLIED_READBACK_INCONCLUSIVE')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('job', type=Path)
    parser.add_argument('--scope', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--observe-authorized-target', action='store_true')
    parser.add_argument('--execute-approved-change', action='store_true')
    args = parser.parse_args()
    if args.execute_approved_change and not args.observe_authorized_target:
        parser.error('Execution requires explicit authorized-target contact too')
    try:
        job = strict_loads(args.job.read_bytes())
        scope = strict_loads(args.scope.read_bytes())
        validate(job, scope)
        if not args.observe_authorized_target:
            print(json.dumps({'status': 'INPUT_CHECKED_NO_TARGET_CONTACT', 'enabled': job['enabled'] and scope['enabled']}))
            return 0 if job['enabled'] and scope['enabled'] else 4
        if args.output is None:
            parser.error('A private --output journal is required before contact')
        # Existing journals are never overwritten to hide an uncertain prior attempt.
        if args.output.exists():
            raise DNSChangeError('Journal already exists; inspect and reconcile the prior operation before a new invocation')
        # Reserve this journal exclusively before contact; no concurrent run may reuse it.
        fd = os.open(args.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump({'status': 'RESERVED_NOT_SENT', 'operation_id': job['operation_id']}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        client = Client(job['server'], job['port'], job['key_name'], os.environ.get('DNS_TSIG_SECRET', ''))
        result = change(job, scope, client, execute=args.execute_approved_change,
                        record=lambda r: write_private(args.output, r))
        print(json.dumps({k: result[k] for k in ('status', 'operation_id', 'update_attempts', 'activation_authorized')}))
        return 0 if result['status'] in STATES or result['status'] == 'READY_FOR_INDEPENDENT_REVIEW_NO_UPDATE' else 2
    except (OSError, ValueError, dns.exception.DNSException) as exc:
        print(json.dumps({'status': 'BLOCKED_INPUT_OR_TRUST', 'error_class': type(exc).__name__,
                          'reason': str(exc) if isinstance(exc, DNSChangeError) else 'Invalid local input or trust material'}))
        return 4


if __name__ == '__main__':
    raise SystemExit(main())
