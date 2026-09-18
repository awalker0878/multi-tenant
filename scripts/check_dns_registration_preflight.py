#!/usr/bin/env python3
"""Evaluate authoritative DNS registration intent without writing DNS.

The preflight binds a stable DNS operation/name-assignment scope to a CONFIRMED
authoritative IPAM allocation and exported DNS lifecycle evidence. Actual names,
addresses and authoritative server details remain in the DNS/IPAM owner systems.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from scripts import check_dns_registration_records as dnsrecords
from scripts import check_ipam_allocation_records as ipam

FORMAT='portable-hosting-dns-registration-intent/1'
STATUS='PLANNING_ONLY_NOT_AUTHORIZED'
READY='DNS_INTENT_READY_EXTERNAL_CHANGE_NOT_EXECUTED'
HOLD_IPAM='HOLD_IPAM_ALLOCATION_NOT_CONFIRMED'
HOLD_CONFLICT='HOLD_DNS_IDENTITY_OR_INTENT_CONFLICT'
HOLD_UNCERTAIN='HOLD_DISCOVER_DNS_OUTCOME'
HOLD_RELEASE='HOLD_DNS_RELEASE_LIFECYCLE'
HOLD_TERMINAL='HOLD_TERMINAL_DNS_REGISTRATION_NEW_OPERATION_REQUIRED'
EXISTING_REGISTERED='EXISTING_REGISTERED_DNS_IDEMPOTENT'
INTENT_KEYS={'format','status','spec','production_authority','source_refs'}
SPEC_KEYS={
    'registration_id','operation_id','generation','reservation_id','request_id',
    'wsd_engineering_ref','ipam_allocation_id','name_assignment_ref','record_types',
    'forward_zone_ref','reverse_zone_ref','ttl_profile_ref','required_observations',
    'valid_until','owners'
}
ID=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{1,191}$')


def bounded(value,label,limit=512):
    if (not isinstance(value,str) or not value.strip() or len(value)>limit
            or any(ord(c)<32 or ord(c)==127 for c in value)):
        raise ValueError(f'{label}: bounded nonempty text required')
    return value


def identifier(value,label):
    bounded(value,label,192)
    if not ID.fullmatch(value):raise ValueError(f'{label}: invalid identifier')
    return value


def repository_ref(value):
    bounded(value,'repository reference')
    p=Path(value)
    if p.is_absolute() or '..' in p.parts or '\\' in value or ':' in value:
        raise ValueError('Repository reference must be normalized and relative')
    if not (ROOT/p).exists():raise ValueError(f'Repository reference does not exist: {value}')
    return value


def load(path:Path):
    with path.open('rb') as stream:raw=stream.read(1024*1024+1)
    if len(raw)>1024*1024:raise ValueError('DNS registration intent exceeds bounded size')
    def pairs(items):
        out={}
        for k,v in items:
            if k in out:raise ValueError('Duplicate JSON property')
            out[k]=v
        return out
    def reject(_):raise ValueError('Non-finite JSON number')
    value=json.loads(raw,object_pairs_hook=pairs,parse_constant=reject)
    if not isinstance(value,dict):raise ValueError('DNS registration intent must be an object')
    return value


def canonical_digest(value):
    import hashlib
    return hashlib.sha256(json.dumps(
        value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False
    ).encode()).hexdigest()


def normalized_spec(intent,*,as_of):
    if set(intent)!=INTENT_KEYS or intent['format']!=FORMAT or intent['status']!=STATUS:
        raise ValueError('Unsupported DNS intent shape or authority boundary')
    if intent['production_authority']!='NOT_ASSESSED':
        raise ValueError('DNS preflight cannot carry production authority')
    if not isinstance(intent['source_refs'],list) or not intent['source_refs']:
        raise ValueError('source_refs required')
    if len(intent['source_refs'])!=len(set(intent['source_refs'])):
        raise ValueError('source_refs duplicates not allowed')
    for ref in intent['source_refs']:repository_ref(ref)

    spec=intent['spec']
    if not isinstance(spec,dict) or set(spec)!=SPEC_KEYS:
        raise ValueError('DNS intent fields are incomplete or unexpected')
    for key in ('registration_id','operation_id','reservation_id','request_id','ipam_allocation_id'):
        identifier(spec[key],key)
    if type(spec['generation']) is not int or spec['generation']<1:
        raise ValueError('generation must be a positive integer')
    repository_ref(spec['wsd_engineering_ref'])
    dnsrecords.opaque_ref(spec['name_assignment_ref'],'name_assignment_ref')
    types=dnsrecords.unique_strings(spec['record_types'],'record_types')
    if not set(types)<=dnsrecords.RECORD_TYPES:raise ValueError('Unsupported DNS record type')
    if 'A' in types and 'AAAA' in types:
        raise ValueError('One DNS intent binds one confirmed IPAM family; split A and AAAA registrations')
    forward=spec['forward_zone_ref'];reverse=spec['reverse_zone_ref']
    if any(t in types for t in ('A','AAAA')):
        if forward is None:raise ValueError('Forward record type requires forward-zone scope')
        dnsrecords.opaque_ref(forward,'forward_zone_ref')
    elif forward is not None:raise ValueError('Forward-zone scope requires A or AAAA')
    if 'PTR' in types:
        if reverse is None:raise ValueError('PTR requires reverse-zone scope')
        dnsrecords.opaque_ref(reverse,'reverse_zone_ref')
    elif reverse is not None:raise ValueError('Reverse-zone scope requires PTR')
    dnsrecords.opaque_ref(spec['ttl_profile_ref'],'ttl_profile_ref')
    required=dnsrecords.unique_strings(spec['required_observations'],'required_observations')
    if not set(required)<=dnsrecords.OBSERVATIONS:raise ValueError('Unknown DNS observation class')
    if 'AUTHORITATIVE' not in required:raise ValueError('Authoritative readback is always required')
    expires=dnsrecords.instant(spec['valid_until'],'valid_until')
    if expires<=as_of:raise ValueError('DNS intent validity must be future-dated')
    owners=spec['owners']
    if not isinstance(owners,dict) or set(owners)!=dnsrecords.OWNER_KEYS:
        raise ValueError('Exact DNS/IPAM/service owner roles required')
    for key in dnsrecords.OWNER_KEYS:bounded(owners[key],key)
    return {
        'registration_id':spec['registration_id'],'operation_id':spec['operation_id'],
        'generation':spec['generation'],'reservation_id':spec['reservation_id'],
        'request_id':spec['request_id'],'wsd_engineering_ref':spec['wsd_engineering_ref'],
        'ipam_allocation_id':spec['ipam_allocation_id'],
        'name_assignment_ref':spec['name_assignment_ref'],'record_types':sorted(types),
        'forward_zone_ref':forward,'reverse_zone_ref':reverse,
        'ttl_profile_ref':spec['ttl_profile_ref'],
        'required_observations':sorted(required),'valid_until':expires.isoformat(),
        'owners':dict(owners)
    }


def evaluate(intent,*,ipam_index=None,dns_index=None,as_of=None):
    if as_of is None:as_of=datetime.now(timezone.utc)
    if not isinstance(as_of,datetime) or as_of.tzinfo is None:
        raise ValueError('Timezone-aware as_of required')
    as_of=as_of.astimezone(timezone.utc)
    if ipam_index is None:ipam_index=ipam.load()
    if dns_index is None:dns_index=dnsrecords.load()

    spec=normalized_spec(intent,as_of=as_of)
    intent_sha=canonical_digest(spec)
    ipam_summary=ipam.validate(ipam_index,as_of=as_of)
    allocation=next((x for x in ipam_summary['records']
                     if x['allocation_id']==spec['ipam_allocation_id']),None)
    dns_summary=dnsrecords.validate(dns_index,ipam_index=ipam_index,as_of=as_of)
    by_op={x['operation_id']:x for x in dns_summary['records']}
    by_id={x['registration_id']:x for x in dns_summary['records']}
    current=by_op.get(spec['operation_id'])
    same_id=by_id.get(spec['registration_id'])

    if current is not None or same_id is not None:
        record=current or same_id
        same_identity=(record['registration_id']==spec['registration_id']
                       and record['operation_id']==spec['operation_id'])
        same_scope=(record['generation']==spec['generation']
                    and record['reservation_id']==spec['reservation_id']
                    and record['request_id']==spec['request_id']
                    and record['ipam_allocation_id']==spec['ipam_allocation_id']
                    and record['name_assignment_ref']==spec['name_assignment_ref']
                    and record['record_types']==spec['record_types']
                    and record['required_observations']==spec['required_observations'])
        if not (same_identity and same_scope):
            result=HOLD_CONFLICT
        elif record['unresolved']:
            result=HOLD_UNCERTAIN
        elif record['state']=='REGISTERED':
            result=EXISTING_REGISTERED
        elif record['state'] in ('RELEASE_PENDING','TOMBSTONED'):
            result=HOLD_RELEASE
        else:
            result=HOLD_TERMINAL
    elif allocation is None or allocation['state']!='CONFIRMED':
        result=HOLD_IPAM
    elif allocation['reservation_id']!=spec['reservation_id'] or allocation['request_id']!=spec['request_id']:
        result=HOLD_CONFLICT
    elif ('A' in spec['record_types'] and allocation['family']!='IPV4') or (
          'AAAA' in spec['record_types'] and allocation['family']!='IPV6'):
        result=HOLD_CONFLICT
    else:
        result=READY

    return {
        'kind':'AUTHORITATIVE_DNS_REGISTRATION_PREFLIGHT','status':result,
        'registration_id':spec['registration_id'],'operation_id':spec['operation_id'],
        'generation':spec['generation'],'reservation_id':spec['reservation_id'],
        'ipam_allocation_id':spec['ipam_allocation_id'],'intent_sha256':intent_sha,
        'record_types':spec['record_types'],'required_observations':spec['required_observations'],
        'actual_dns_name':None,'actual_record_values':None,
        'actual_name_value_source':'AUTHORITATIVE_IPAM_AND_DNS_NAME_AUTHORITY_ONLY',
        'may_write_dns':False,'may_delete_dns':False,'may_release_name':False,
        'may_apply':False,'may_activate':False,
        'next_owner_action':{
            READY:'DNS owner resolves the approved name and confirmed allocation through authoritative systems, builds an independently scoped RFC2136 job/scope, and submits it under the approved DNS change process.',
            HOLD_IPAM:'Confirm/reconcile the authoritative IPAM allocation before any DNS change; do not guess A/AAAA/PTR values.',
            HOLD_CONFLICT:'Stop and reconcile the existing DNS operation/registration or parent allocation identity.',
            HOLD_UNCERTAIN:'Discover authoritative DNS state before retry; do not send a second blind update.',
            HOLD_RELEASE:'Complete/reconcile DNS retirement and tombstone obligations before reusing the name.',
            HOLD_TERMINAL:'Use a new approved operation identity and name-assignment decision; do not revive released registration state.',
            EXISTING_REGISTERED:'Reuse the existing authoritative registration evidence; do not create a duplicate DNS update.'
        }[result],
        'limits':[
            'No literal DNS name or A/AAAA/PTR value is accepted or returned by this repository preflight.',
            'The existing tools/dns_change.py remains the separately scoped mutation mechanism and is never invoked by this check.',
            'Authoritative readback does not prove recursive/secondary propagation unless those observations are explicitly required and evidenced.',
            'DNS failure never authorizes guessed address values, alternate names, broader key ACLs, or production activation.'
        ]
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('intent',type=Path)
    p.add_argument('--as-of',help='ISO-8601 review instant; defaults to current UTC')
    p.add_argument('--expected-status',choices=(READY,HOLD_IPAM,HOLD_CONFLICT,HOLD_UNCERTAIN,HOLD_RELEASE,HOLD_TERMINAL,EXISTING_REGISTERED))
    a=p.parse_args()
    try:
        as_of=dnsrecords.instant(a.as_of,'as_of') if a.as_of else datetime.now(timezone.utc)
        result=evaluate(load(a.intent),as_of=as_of)
        print(json.dumps(result,indent=2))
        if a.expected_status is not None:return 0 if result['status']==a.expected_status else 2
        return 0 if result['status'] in (READY,EXISTING_REGISTERED) else 2
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({
            'kind':'AUTHORITATIVE_DNS_REGISTRATION_PREFLIGHT','status':'INVALID_DNS_REGISTRATION_INTENT',
            'reason':str(exc),'actual_dns_name':None,'actual_record_values':None,
            'may_write_dns':False,'may_delete_dns':False,'may_release_name':False,
            'may_apply':False,'may_activate':False
        },indent=2));return 2


if __name__=='__main__':raise SystemExit(main())
