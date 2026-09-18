#!/usr/bin/env python3
"""Validate exported authoritative DNS registration lifecycle evidence.

This repository is not authoritative DNS and does not store assigned A/AAAA/PTR
values or internal DNS names. Records bind opaque name-assignment and zone-scope
references to a CONFIRMED authoritative IPAM allocation, operation identity,
observations, ownership, and retirement/tombstone evidence.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import ipaddress
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from scripts import check_ipam_allocation_records as ipam

INDEX=ROOT/'sources/capabilities/dns_registration_index.json'
FORMAT='portable-hosting-dns-registration-index/1'
STATUS='EXPORTED_AUTHORITATIVE_DNS_EVIDENCE_NOT_DNS_AUTHORITY'
STATES={'REGISTERED','RELEASE_PENDING','TOMBSTONED','RELEASED','UNCERTAIN'}
RECORD_TYPES={'A','AAAA','PTR'}
OBSERVATIONS={'AUTHORITATIVE','RECURSIVE','SECONDARY'}
OBS_STATES={'COMPLETE','PENDING','FAILED','UNKNOWN','NOT_APPLICABLE'}
ID=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{1,191}$')
INDEX_KEYS={'format','status','reviewed_source_revision','records'}
RECORD_KEYS={
    'registration_id','operation_id','generation','state','reservation_id','request_id',
    'wsd_engineering_ref','ipam_allocation_id','name_assignment_ref','record_types',
    'forward_zone_ref','reverse_zone_ref','ttl_profile_ref','required_observations',
    'authoritative_system','created_at','last_observed_at','registered_at',
    'release_requested_at','tombstone_until','released_at','observations','owners',
    'evidence_refs','source_refs'
}
SYSTEM_KEYS={'system_ref','record_ref','record_version'}
OWNER_KEYS={'dns_owner_role','ipam_owner_role','service_owner_role'}
OBS_KEYS={'status','evidence_ref','observed_at'}


def bounded(value,label,limit=512):
    if (not isinstance(value,str) or not value.strip() or len(value)>limit
            or any(ord(c)<32 or ord(c)==127 for c in value)):
        raise ValueError(f'{label}: bounded nonempty text required')
    return value


def identifier(value,label):
    bounded(value,label,192)
    if not ID.fullmatch(value):raise ValueError(f'{label}: invalid identifier')
    return value


def positive_int(value,label):
    if type(value) is not int or value<1:raise ValueError(f'{label}: positive integer required')
    return value


def instant(value,label):
    bounded(value,label,64)
    dt=datetime.fromisoformat(value.replace('Z','+00:00'))
    if dt.tzinfo is None:raise ValueError(f'{label}: timezone required')
    return dt.astimezone(timezone.utc)


def nullable_instant(value,label):
    return None if value is None else instant(value,label)


def repository_ref(value,root=ROOT):
    bounded(value,'repository reference')
    p=Path(value)
    if p.is_absolute() or '..' in p.parts or '\\' in value or ':' in value:
        raise ValueError('Repository reference must be normalized and relative')
    if not (root/p).exists():raise ValueError(f'Repository reference does not exist: {value}')
    return value


def opaque_ref(value,label):
    bounded(value,label,256)
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.:-]{1,255}',value):
        raise ValueError(f'{label}: opaque external reference required')
    # Public repository evidence must not smuggle actual allocation values or FQDNs.
    if re.search(r'(?<![0-9])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9])',value) or '::' in value:
        raise ValueError(f'{label}: literal IP values are not allowed')
    candidates={value}
    if ':' in value:candidates.add(value.split(':',1)[1])
    for candidate in candidates:
        try:ipaddress.ip_address(candidate)
        except ValueError:pass
        else:raise ValueError(f'{label}: literal IP values are not allowed')
    # A DNS owner may use an external record handle, but the repository must not
    # expose an internal absolute name through that handle.
    if value.endswith('.') and value.count('.')>=2:
        raise ValueError(f'{label}: literal DNS names are not allowed')
    return value


def unique_strings(value,label,*,allow_empty=False,maximum=64):
    if not isinstance(value,list) or len(value)>maximum or (not allow_empty and not value):
        raise ValueError(f'{label}: bounded list required')
    if any(not isinstance(x,str) or not x.strip() for x in value):
        raise ValueError(f'{label}: nonempty strings required')
    if len(value)!=len(set(value)):raise ValueError(f'{label}: duplicates not allowed')
    return value


def load(path:Path=INDEX):
    with path.open('rb') as stream:raw=stream.read(1024*1024+1)
    if len(raw)>1024*1024:raise ValueError('DNS registration index exceeds bounded size')
    def pairs(items):
        out={}
        for k,v in items:
            if k in out:raise ValueError('Duplicate JSON property')
            out[k]=v
        return out
    def reject(_):raise ValueError('Non-finite JSON number')
    value=json.loads(raw,object_pairs_hook=pairs,parse_constant=reject)
    if not isinstance(value,dict):raise ValueError('DNS registration index must be an object')
    return value


def validate_observations(value,required,*,observed_through):
    if not isinstance(value,dict) or set(value)!=OBSERVATIONS:
        raise ValueError('Exact DNS observation classes are required')
    normalized={}
    for key,item in value.items():
        if not isinstance(item,dict) or set(item)!=OBS_KEYS:
            raise ValueError('DNS observation item shape invalid')
        if item['status'] not in OBS_STATES:raise ValueError('Unknown DNS observation state')
        ref=item['evidence_ref'];when=nullable_instant(item['observed_at'],f'observations.{key}.observed_at')
        if item['status'] in ('PENDING','UNKNOWN'):
            if ref is not None or when is not None:
                raise ValueError('Pending/unknown observation cannot claim evidence')
        else:
            if ref is None or when is None:raise ValueError('Completed/failed/not-applicable observation requires evidence')
            bounded(ref,f'observations.{key}.evidence_ref')
            if when>observed_through:raise ValueError('DNS observation occurs after record observation time')
        if key in required and item['status']!='COMPLETE':
            raise ValueError(f'Required DNS observation is not complete: {key}')
        normalized[key]={'status':item['status'],'evidence_ref':ref,
                         'observed_at':when.isoformat() if when else None}
    return normalized


def validate_record(record,*,ipam_index,as_of,root=ROOT):
    if not isinstance(record,dict) or set(record)!=RECORD_KEYS:
        raise ValueError('DNS registration record has unexpected or missing fields')
    for key in ('registration_id','operation_id','reservation_id','request_id'):
        identifier(record[key],key)
    positive_int(record['generation'],'generation')
    if record['state'] not in STATES:raise ValueError('Unknown DNS registration state')
    repository_ref(record['wsd_engineering_ref'],root)
    identifier(record['ipam_allocation_id'],'ipam_allocation_id')
    opaque_ref(record['name_assignment_ref'],'name_assignment_ref')
    types=unique_strings(record['record_types'],'record_types')
    if not set(types)<=RECORD_TYPES:raise ValueError('Unsupported DNS record type')
    if 'A' in types and 'AAAA' in types:
        raise ValueError('One registration record binds one confirmed IPAM family; split A and AAAA registrations')
    forward=record['forward_zone_ref'];reverse=record['reverse_zone_ref']
    if any(t in types for t in ('A','AAAA')):
        if forward is None:raise ValueError('Forward record type requires forward-zone scope reference')
        opaque_ref(forward,'forward_zone_ref')
    elif forward is not None:
        raise ValueError('Forward-zone scope requires A or AAAA')
    if 'PTR' in types:
        if reverse is None:raise ValueError('PTR requires reverse-zone scope reference')
        opaque_ref(reverse,'reverse_zone_ref')
    elif reverse is not None:
        raise ValueError('Reverse-zone scope requires PTR')
    opaque_ref(record['ttl_profile_ref'],'ttl_profile_ref')
    required=unique_strings(record['required_observations'],'required_observations')
    if not set(required)<=OBSERVATIONS:raise ValueError('Unknown required DNS observation class')
    if 'AUTHORITATIVE' not in required:raise ValueError('Authoritative readback is always required')

    system=record['authoritative_system']
    if not isinstance(system,dict) or set(system)!=SYSTEM_KEYS:
        raise ValueError('Authoritative DNS system record required')
    for key in ('system_ref','record_ref'):opaque_ref(system[key],f'authoritative_system.{key}')
    positive_int(system['record_version'],'authoritative_system.record_version')

    created=instant(record['created_at'],'created_at')
    observed=instant(record['last_observed_at'],'last_observed_at')
    if created>observed or observed>as_of:raise ValueError('DNS observation chronology invalid')
    registered=nullable_instant(record['registered_at'],'registered_at')
    release_requested=nullable_instant(record['release_requested_at'],'release_requested_at')
    tombstone_until=nullable_instant(record['tombstone_until'],'tombstone_until')
    released=nullable_instant(record['released_at'],'released_at')
    if any(t is not None and (t<created or t>observed) for t in (registered,release_requested,released)):
        raise ValueError('DNS lifecycle timestamp outside observed chronology')

    ipam_summary=ipam.validate(ipam_index,as_of=as_of,root=root)
    allocation=next((x for x in ipam_summary['records']
                     if x['allocation_id']==record['ipam_allocation_id']),None)
    if allocation is None:raise ValueError('DNS registration lacks matching authoritative IPAM allocation evidence')
    if allocation['reservation_id']!=record['reservation_id'] or allocation['request_id']!=record['request_id']:
        raise ValueError('DNS registration and IPAM allocation parent scope differ')
    expected_family='IPV4' if 'A' in types else ('IPV6' if 'AAAA' in types else allocation['family'])
    if allocation['family']!=expected_family:raise ValueError('DNS record type conflicts with confirmed IPAM family')

    observations=validate_observations(record['observations'],set(required),observed_through=observed)

    if record['state']=='REGISTERED':
        if allocation['state']!='CONFIRMED':
            raise ValueError('REGISTERED DNS requires a CONFIRMED authoritative IPAM allocation')
        if registered is None or any(x is not None for x in (release_requested,tombstone_until,released)):
            raise ValueError('REGISTERED DNS lifecycle fields are inconsistent')
    elif record['state']=='RELEASE_PENDING':
        if registered is None or release_requested is None or tombstone_until is not None or released is not None:
            raise ValueError('RELEASE_PENDING DNS lifecycle fields are inconsistent')
    elif record['state']=='TOMBSTONED':
        if registered is None or release_requested is None or tombstone_until is None or released is not None:
            raise ValueError('TOMBSTONED DNS requires release request and tombstone boundary')
        if tombstone_until<release_requested:raise ValueError('DNS tombstone cannot predate release request')
    elif record['state']=='RELEASED':
        if registered is None or release_requested is None or tombstone_until is None or released is None:
            raise ValueError('RELEASED DNS requires registration, release request, tombstone and release receipt')
        if released<tombstone_until:raise ValueError('DNS name released before tombstone period ended')
    else: # UNCERTAIN
        if released is not None:raise ValueError('UNCERTAIN DNS cannot claim final release')

    owners=record['owners']
    if not isinstance(owners,dict) or set(owners)!=OWNER_KEYS:raise ValueError('DNS owner roles required')
    for key in OWNER_KEYS:bounded(owners[key],key)
    evidence=unique_strings(record['evidence_refs'],'evidence_refs')
    sources=unique_strings(record['source_refs'],'source_refs')
    for ref in sources:repository_ref(ref,root)
    return {
        'registration_id':record['registration_id'],'operation_id':record['operation_id'],
        'generation':record['generation'],'state':record['state'],
        'reservation_id':record['reservation_id'],'request_id':record['request_id'],
        'ipam_allocation_id':record['ipam_allocation_id'],
        'name_assignment_ref':record['name_assignment_ref'],'record_types':sorted(types),
        'required_observations':sorted(required),'observations':observations,
        'unresolved':record['state']=='UNCERTAIN','evidence_refs':sorted(evidence)
    }


def validate(index,*,ipam_index=None,as_of=None,root=ROOT):
    if as_of is None:as_of=datetime.now(timezone.utc)
    if not isinstance(as_of,datetime) or as_of.tzinfo is None:raise ValueError('Timezone-aware as_of required')
    as_of=as_of.astimezone(timezone.utc)
    if ipam_index is None:ipam_index=ipam.load()
    if set(index)!=INDEX_KEYS:raise ValueError('Unexpected DNS registration-index fields')
    if index['format']!=FORMAT or index['status']!=STATUS:
        raise ValueError('Unsupported DNS registration-index format or authority boundary')
    rev=index['reviewed_source_revision']
    if not isinstance(rev,str) or not re.fullmatch(r'[0-9a-f]{40}',rev):
        raise ValueError('Reviewed source revision must be an exact Git SHA')
    if not isinstance(index['records'],list) or len(index['records'])>2048:
        raise ValueError('DNS registration records must be a bounded list')
    ids=set();ops=set();out=[]
    for raw in index['records']:
        item=validate_record(raw,ipam_index=ipam_index,as_of=as_of,root=root)
        if item['registration_id'] in ids:raise ValueError('Duplicate DNS registration ID')
        if item['operation_id'] in ops:raise ValueError('Duplicate DNS operation identity')
        ids.add(item['registration_id']);ops.add(item['operation_id']);out.append(item)
    return {
        'records':out,'record_count':len(out),
        'registered_count':sum(x['state']=='REGISTERED' for x in out),
        'release_lifecycle_count':sum(x['state'] in ('RELEASE_PENDING','TOMBSTONED','RELEASED') for x in out),
        'unresolved_count':sum(x['unresolved'] for x in out)
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--index',type=Path,default=INDEX)
    p.add_argument('--as-of',help='ISO-8601 review instant; defaults to current UTC')
    a=p.parse_args()
    try:
        as_of=instant(a.as_of,'as_of') if a.as_of else datetime.now(timezone.utc)
        summary=validate(load(a.index),as_of=as_of)
        print(json.dumps({
            'status':'PASSED_EXPORTED_AUTHORITATIVE_DNS_RECORDS','as_of':as_of.isoformat(),
            **{k:v for k,v in summary.items() if k!='records'},
            'literal_dns_names_in_repository':False,'literal_allocation_values_in_repository':False,
            'may_write_dns':False,'may_delete_dns':False,'may_release_name':False,
            'may_apply':False,'may_activate':False,
            'limits':[
                'Actual DNS names and A/AAAA/PTR values remain in authoritative owner systems.',
                'REGISTERED requires CONFIRMED authoritative IPAM evidence and all declared required observations.',
                'Recursive/secondary propagation is separate from authoritative write/readback and is required only when the profile declares it.',
                'The repository validates exported evidence only; it never performs DNS mutation.'
            ]
        },indent=2));return 0
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({
            'status':'FAILED_EXPORTED_AUTHORITATIVE_DNS_RECORDS','reason':str(exc),
            'literal_dns_names_in_repository':False,'literal_allocation_values_in_repository':False,
            'may_write_dns':False,'may_delete_dns':False,'may_release_name':False,
            'may_apply':False,'may_activate':False
        },indent=2));return 2


if __name__=='__main__':raise SystemExit(main())
