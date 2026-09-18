#!/usr/bin/env python3
"""Validate exported authoritative IPAM allocation evidence.

This repository is not IPAM. Records contain stable owner/system references and
lifecycle evidence but intentionally omit the allocated address/prefix value.
Actual values stay in the authoritative IPAM and are handed to dependent owners
through its accepted interface.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import ipaddress
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'sources/capabilities/ipam_allocation_index.json'
FORMAT='portable-hosting-ipam-allocation-index/1'
STATUS='EXPORTED_AUTHORITATIVE_IPAM_EVIDENCE_NOT_IPAM_AUTHORITY'
STATES={'RESERVED','CONFIRMED','RELEASE_PENDING','QUARANTINED','RELEASED','UNCERTAIN'}
POLICIES={'UNIQUE_DEFAULT','OVERLAP_EXCEPTION'}
KINDS={'ADDRESS','PREFIX'}
FAMILIES={'IPV4','IPV6'}
ID=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{1,191}$')
SHA=re.compile(r'^[0-9a-f]{64}$')
INDEX_KEYS={'format','status','reviewed_source_revision','records'}
RECORD_KEYS={
    'allocation_id','operation_id','generation','state','reservation_id','request_id',
    'wsd_engineering_ref','intent_sha256','allocation_policy','overlap_exception_ref',
    'family','allocation_kind','requested_prefix_length','delegated_scope_ref',
    'authoritative_system','allocation_ref','created_at','last_observed_at',
    'hold_expires_at','confirmed_at','realization_ref','release_requested_at',
    'cleanup','reuse_not_before','released_at','owners','evidence_refs','source_refs'
}
SYSTEM_KEYS={'system_ref','record_ref','record_version'}
OWNER_KEYS={'ipam_owner_role','network_owner_role','service_owner_role'}
CLEANUP_KEYS={'routes','dhcp_leases','dns','policy','logging_attribution','incident_response'}
CLEANUP_ITEM_KEYS={'status','evidence_ref','observed_at'}
CLEANUP_STATES={'NOT_STARTED','PENDING','COMPLETE','NOT_APPLICABLE'}


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


def unique_strings(value,label,*,allow_empty=False,maximum=128):
    if not isinstance(value,list) or len(value)>maximum or (not allow_empty and not value):
        raise ValueError(f'{label}: bounded list required')
    if any(not isinstance(x,str) or not x.strip() for x in value):
        raise ValueError(f'{label}: nonempty strings required')
    if len(value)!=len(set(value)):raise ValueError(f'{label}: duplicates not allowed')
    return value


def load(path:Path=INDEX):
    with path.open('rb') as stream:raw=stream.read(1024*1024+1)
    if len(raw)>1024*1024:raise ValueError('IPAM allocation index exceeds bounded size')
    def pairs(items):
        out={}
        for k,v in items:
            if k in out:raise ValueError('Duplicate JSON property')
            out[k]=v
        return out
    def reject(_):raise ValueError('Non-finite JSON number')
    value=json.loads(raw,object_pairs_hook=pairs,parse_constant=reject)
    if not isinstance(value,dict):raise ValueError('IPAM allocation index must be an object')
    return value


def validate_prefix_shape(family,kind,prefix_length):
    bits=32 if family=='IPV4' else 128
    if kind=='ADDRESS':
        if prefix_length is not None:raise ValueError('ADDRESS allocation cannot request a prefix length')
    else:
        if type(prefix_length) is not int or not 0<=prefix_length<=bits:
            raise ValueError('PREFIX allocation requires a family-valid prefix length')


def validate_cleanup(cleanup,*,as_of):
    if not isinstance(cleanup,dict) or set(cleanup)!=CLEANUP_KEYS:
        raise ValueError('Exact release-cleanup categories are required')
    normalized={}
    for key,item in cleanup.items():
        if not isinstance(item,dict) or set(item)!=CLEANUP_ITEM_KEYS:
            raise ValueError('Cleanup evidence item shape invalid')
        if item['status'] not in CLEANUP_STATES:raise ValueError('Unknown cleanup status')
        observed=nullable_instant(item['observed_at'],f'cleanup.{key}.observed_at')
        ref=item['evidence_ref']
        if item['status']=='NOT_STARTED':
            if ref is not None or observed is not None:
                raise ValueError('NOT_STARTED cleanup cannot claim evidence')
        else:
            if ref is None:raise ValueError('Started cleanup requires an evidence/authority reference')
            bounded(ref,f'cleanup.{key}.evidence_ref')
            if observed is None or observed>as_of:
                raise ValueError('Started cleanup requires a non-future observation')
        normalized[key]={'status':item['status'],'evidence_ref':ref,
                         'observed_at':observed.isoformat() if observed else None}
    return normalized


def cleanup_complete(cleanup):
    return all(item['status'] in ('COMPLETE','NOT_APPLICABLE') for item in cleanup.values())


def validate_record(record,*,as_of,root=ROOT):
    if not isinstance(record,dict) or set(record)!=RECORD_KEYS:
        raise ValueError('IPAM allocation record has unexpected or missing fields')
    for key in ('allocation_id','operation_id','reservation_id','request_id'):
        identifier(record[key],key)
    positive_int(record['generation'],'generation')
    if record['state'] not in STATES:raise ValueError('Unknown IPAM allocation state')
    repository_ref(record['wsd_engineering_ref'],root)
    if not isinstance(record['intent_sha256'],str) or not SHA.fullmatch(record['intent_sha256']):
        raise ValueError('Intent SHA-256 required')

    if record['allocation_policy'] not in POLICIES:raise ValueError('Unknown allocation policy')
    overlap=record['overlap_exception_ref']
    if record['allocation_policy']=='UNIQUE_DEFAULT':
        if overlap is not None:raise ValueError('Unique-default allocation cannot carry overlap exception')
    else:
        if overlap is None:raise ValueError('Overlap allocation requires explicit exception reference')
        bounded(overlap,'overlap_exception_ref')

    family=record['family'];kind=record['allocation_kind']
    if family not in FAMILIES or kind not in KINDS:raise ValueError('Unknown address family or allocation kind')
    validate_prefix_shape(family,kind,record['requested_prefix_length'])
    bounded(record['delegated_scope_ref'],'delegated_scope_ref')

    system=record['authoritative_system']
    if not isinstance(system,dict) or set(system)!=SYSTEM_KEYS:
        raise ValueError('Authoritative IPAM system record required')
    bounded(system['system_ref'],'authoritative_system.system_ref')
    bounded(system['record_ref'],'authoritative_system.record_ref')
    positive_int(system['record_version'],'authoritative_system.record_version')
    bounded(record['allocation_ref'],'allocation_ref')

    created=instant(record['created_at'],'created_at')
    observed=instant(record['last_observed_at'],'last_observed_at')
    if created>observed or observed>as_of:raise ValueError('IPAM observation chronology invalid')
    hold_expires=nullable_instant(record['hold_expires_at'],'hold_expires_at')
    confirmed=nullable_instant(record['confirmed_at'],'confirmed_at')
    release_requested=nullable_instant(record['release_requested_at'],'release_requested_at')
    reuse_not_before=nullable_instant(record['reuse_not_before'],'reuse_not_before')
    released=nullable_instant(record['released_at'],'released_at')
    if any(t is not None and (t<created or t>as_of) for t in (confirmed,release_requested,released)):
        raise ValueError('IPAM lifecycle timestamp outside observed chronology')

    if record['state']=='RESERVED':
        if hold_expires is None or as_of>=hold_expires:
            raise ValueError('RESERVED allocation requires an unexpired authoritative hold')
        if any(x is not None for x in (confirmed,release_requested,reuse_not_before,released)):
            raise ValueError('RESERVED allocation has later lifecycle fields')
        if record['realization_ref'] is not None:raise ValueError('RESERVED allocation cannot claim realization')
    else:
        if hold_expires is not None:
            raise ValueError('Only RESERVED allocations carry a hold expiry')

    if confirmed is not None:
        if record['realization_ref'] is None:raise ValueError('Confirmed allocation requires realization reference')
        bounded(record['realization_ref'],'realization_ref')
    elif record['realization_ref'] is not None:
        raise ValueError('Realization reference requires confirmed_at')
    if record['state']=='CONFIRMED' and confirmed is None:
        raise ValueError('CONFIRMED allocation requires post-realization confirmation')
    if record['state'] in ('RELEASE_PENDING','QUARANTINED','RELEASED') and release_requested is None:
        raise ValueError('Release lifecycle requires release_requested_at')
    if release_requested is not None and confirmed is not None and release_requested<confirmed:
        raise ValueError('Release cannot predate confirmation')

    cleanup=validate_cleanup(record['cleanup'],as_of=as_of)
    if record['state'] in ('RESERVED','CONFIRMED','UNCERTAIN'):
        if any(item['status']!='NOT_STARTED' for item in cleanup.values()):
            raise ValueError('Release cleanup cannot be asserted before release lifecycle')
    if record['state']=='RELEASE_PENDING':
        if cleanup_complete(cleanup):
            raise ValueError('Complete release cleanup should advance to QUARANTINED')
        if reuse_not_before is not None or released is not None:
            raise ValueError('RELEASE_PENDING cannot claim quarantine completion/release')
    if record['state']=='QUARANTINED':
        if not cleanup_complete(cleanup) or reuse_not_before is None or released is not None:
            raise ValueError('QUARANTINED requires complete cleanup and reuse-not-before, but not release')
        if release_requested is not None and reuse_not_before<release_requested:
            raise ValueError('Reuse quarantine cannot begin before release request')
    if record['state']=='RELEASED':
        if not cleanup_complete(cleanup) or reuse_not_before is None or released is None:
            raise ValueError('RELEASED requires cleanup, quarantine and release receipt')
        if released<reuse_not_before:
            raise ValueError('Allocation released before reuse quarantine expired')
    if record['state'] not in ('QUARANTINED','RELEASED') and reuse_not_before is not None:
        raise ValueError('reuse_not_before only belongs to quarantine/released state')
    if record['state']!='RELEASED' and released is not None:
        raise ValueError('released_at only belongs to RELEASED state')

    owners=record['owners']
    if not isinstance(owners,dict) or set(owners)!=OWNER_KEYS:raise ValueError('IPAM owner fields required')
    for key in OWNER_KEYS:bounded(owners[key],key)
    evidence=unique_strings(record['evidence_refs'],'evidence_refs')
    sources=unique_strings(record['source_refs'],'source_refs')
    for ref in sources:repository_ref(ref,root)

    return {
        'allocation_id':record['allocation_id'],'operation_id':record['operation_id'],
        'generation':record['generation'],'state':record['state'],
        'reservation_id':record['reservation_id'],'request_id':record['request_id'],
        'intent_sha256':record['intent_sha256'],'allocation_policy':record['allocation_policy'],
        'family':family,'allocation_kind':kind,'requested_prefix_length':record['requested_prefix_length'],
        'delegated_scope_ref':record['delegated_scope_ref'],
        'authoritative_system':dict(system),'allocation_ref':record['allocation_ref'],
        'created_at':created.isoformat(),'last_observed_at':observed.isoformat(),
        'cleanup':cleanup,'unresolved':record['state']=='UNCERTAIN',
        'evidence_refs':sorted(evidence)
    }


def validate(index,*,as_of=None,root=ROOT):
    if as_of is None:as_of=datetime.now(timezone.utc)
    if not isinstance(as_of,datetime) or as_of.tzinfo is None:raise ValueError('Timezone-aware as_of required')
    as_of=as_of.astimezone(timezone.utc)
    if set(index)!=INDEX_KEYS:raise ValueError('Unexpected IPAM allocation-index fields')
    if index['format']!=FORMAT or index['status']!=STATUS:
        raise ValueError('Unsupported IPAM allocation-index format or authority boundary')
    rev=index['reviewed_source_revision']
    if not isinstance(rev,str) or not re.fullmatch(r'[0-9a-f]{40}',rev):
        raise ValueError('Reviewed source revision must be an exact Git SHA')
    if not isinstance(index['records'],list) or len(index['records'])>1024:
        raise ValueError('IPAM records must be a bounded list')
    allocation_ids=set();operation_ids=set();records_out=[]
    for raw in index['records']:
        item=validate_record(raw,as_of=as_of,root=root)
        if item['allocation_id'] in allocation_ids:raise ValueError('Duplicate immutable allocation ID')
        if item['operation_id'] in operation_ids:raise ValueError('Duplicate idempotent IPAM operation ID')
        allocation_ids.add(item['allocation_id']);operation_ids.add(item['operation_id']);records_out.append(item)
    return {
        'records':records_out,'record_count':len(records_out),
        'reserved_count':sum(x['state']=='RESERVED' for x in records_out),
        'confirmed_count':sum(x['state']=='CONFIRMED' for x in records_out),
        'release_lifecycle_count':sum(x['state'] in ('RELEASE_PENDING','QUARANTINED','RELEASED') for x in records_out),
        'unresolved_count':sum(x['unresolved'] for x in records_out)
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
            'status':'PASSED_EXPORTED_AUTHORITATIVE_IPAM_RECORDS','as_of':as_of.isoformat(),
            **{k:v for k,v in summary.items() if k!='records'},
            'actual_allocation_values_in_repository':False,
            'may_reserve_address':False,'may_confirm_address':False,'may_release_address':False,
            'may_reuse_address':False,'may_write_dns':False,'may_apply':False,'may_activate':False,
            'limits':[
                'Actual addresses/prefixes remain in authoritative IPAM and are not stored by this index.',
                'Service failure never authorizes guessed allocation values.',
                'Release is not reusable until dependent cleanup and quarantine evidence are complete.',
                'The repository validates exported evidence only; it does not mutate IPAM.'
            ]
        },indent=2));return 0
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({
            'status':'FAILED_EXPORTED_AUTHORITATIVE_IPAM_RECORDS','reason':str(exc),
            'actual_allocation_values_in_repository':False,
            'may_reserve_address':False,'may_confirm_address':False,'may_release_address':False,
            'may_reuse_address':False,'may_write_dns':False,'may_apply':False,'may_activate':False
        },indent=2));return 2


if __name__=='__main__':raise SystemExit(main())
