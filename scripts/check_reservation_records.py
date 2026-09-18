#!/usr/bin/env python3
"""Validate exported reservation records without becoming the reservation authority.

The authoritative reservation system remains external. This checker enforces the
repository contract for immutable identity, owner/expiry, generation/spec binding,
record version, and fail-closed uncertain/conflict evidence. It never creates,
extends, consumes, releases, or deletes a reservation.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'sources/capabilities/reservation_record_index.json'
FORMAT='portable-hosting-reservation-record-index/1'
STATUS='EXPORTED_RESERVATION_EVIDENCE_NOT_RESERVATION_AUTHORITY'
STATES={'HELD','CONSUMED','RELEASED','EXPIRED','UNCERTAIN'}
ID=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{1,191}$')
SHA=re.compile(r'^[0-9a-f]{64}$')
INDEX_KEYS={'format','status','reviewed_source_revision','records'}
RECORD_KEYS={
    'reservation_id','operation_id','generation','state','request_id',
    'wsd_engineering_ref','envelope_id','spec_sha256','authoritative_system',
    'created_at','expires_at','last_observed_at','owners','resources',
    'dependency_handoffs','evidence_refs','source_refs'
}
SYSTEM_KEYS={'system_ref','record_ref','record_version'}
OWNER_KEYS={'reservation_owner_role','capacity_owner_role','service_owner_role'}
RESOURCE_KEYS={'id','unit','quantity','owner_role'}
DEPENDENCY_KEYS={'kind','owner_role','operation_id','reservation_ref','state'}
DEPENDENCY_STATES={'NOT_STARTED','RESERVED','CONSUMED','RELEASED','UNCERTAIN'}


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


def number(value,label):
    if not isinstance(value,str) or not value or len(value)>64:
        raise ValueError(f'{label}: decimal string required')
    try:n=Decimal(value)
    except InvalidOperation:raise ValueError(f'{label}: invalid decimal') from None
    if not n.is_finite() or n<=0:raise ValueError(f'{label}: positive finite decimal required')
    return n


def instant(value,label):
    bounded(value,label,64)
    dt=datetime.fromisoformat(value.replace('Z','+00:00'))
    if dt.tzinfo is None:raise ValueError(f'{label}: timezone required')
    return dt.astimezone(timezone.utc)


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


def canonical_digest(value):
    return hashlib.sha256(json.dumps(
        value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def load(path:Path=INDEX):
    with path.open('rb') as stream:raw=stream.read(1024*1024+1)
    if len(raw)>1024*1024:raise ValueError('Reservation index exceeds bounded size')
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('Duplicate JSON property')
            result[key]=value
        return result
    def reject(_):raise ValueError('Non-finite JSON number')
    value=json.loads(raw,object_pairs_hook=pairs,parse_constant=reject)
    if not isinstance(value,dict):raise ValueError('Reservation index must be a JSON object')
    return value


def validate_record(record,*,as_of,root=ROOT):
    if not isinstance(record,dict) or set(record)!=RECORD_KEYS:
        raise ValueError('Reservation record has unexpected or missing fields')
    for key in ('reservation_id','operation_id','request_id','envelope_id'):
        identifier(record[key],key)
    if record['state'] not in STATES:raise ValueError('Unknown reservation state')
    positive_int(record['generation'],'generation')
    repository_ref(record['wsd_engineering_ref'],root)
    if not isinstance(record['spec_sha256'],str) or not SHA.fullmatch(record['spec_sha256']):
        raise ValueError('Reservation spec SHA-256 required')

    system=record['authoritative_system']
    if not isinstance(system,dict) or set(system)!=SYSTEM_KEYS:
        raise ValueError('Authoritative reservation-system record required')
    bounded(system['system_ref'],'authoritative_system.system_ref')
    bounded(system['record_ref'],'authoritative_system.record_ref')
    positive_int(system['record_version'],'authoritative_system.record_version')

    created=instant(record['created_at'],'created_at')
    expires=instant(record['expires_at'],'expires_at')
    observed=instant(record['last_observed_at'],'last_observed_at')
    if created>observed or observed>as_of or expires<=created:
        raise ValueError('Reservation chronology is invalid')
    if record['state']=='HELD' and as_of>=expires:
        raise ValueError('Expired HELD reservation requires explicit reconciliation; it is not silently reusable')
    if record['state']=='EXPIRED' and observed<expires:
        raise ValueError('EXPIRED state cannot be observed before its expiry')
    if record['state'] in ('RELEASED','EXPIRED') and observed<created:
        raise ValueError('Terminal reservation observation predates creation')

    owners=record['owners']
    if not isinstance(owners,dict) or set(owners)!=OWNER_KEYS:
        raise ValueError('Reservation owner fields required')
    for key in OWNER_KEYS:bounded(owners[key],key)

    resources=record['resources']
    if not isinstance(resources,list) or not resources or len(resources)>128:
        raise ValueError('At least one reserved resource quantity is required')
    seen=set()
    normalized=[]
    for item in resources:
        if not isinstance(item,dict) or set(item)!=RESOURCE_KEYS:
            raise ValueError('Reservation resource shape invalid')
        identifier(item['id'],'resource.id')
        if item['id'] in seen:raise ValueError('Duplicate reservation resource dimension')
        seen.add(item['id'])
        bounded(item['unit'],'resource.unit',64)
        number(item['quantity'],'resource.quantity')
        bounded(item['owner_role'],'resource.owner_role')
        normalized.append(dict(item))

    deps=record['dependency_handoffs']
    if not isinstance(deps,list) or len(deps)>128:
        raise ValueError('dependency_handoffs must be a bounded list')
    dep_ops=set()
    normalized_deps=[]
    for item in deps:
        if not isinstance(item,dict) or set(item)!=DEPENDENCY_KEYS:
            raise ValueError('Dependency handoff shape invalid')
        bounded(item['kind'],'dependency.kind',64)
        bounded(item['owner_role'],'dependency.owner_role')
        identifier(item['operation_id'],'dependency.operation_id')
        if item['operation_id'] in dep_ops:raise ValueError('Duplicate dependency operation identity')
        dep_ops.add(item['operation_id'])
        if item['reservation_ref'] is not None:
            bounded(item['reservation_ref'],'dependency.reservation_ref')
        if item['state'] not in DEPENDENCY_STATES:raise ValueError('Unknown dependency handoff state')
        if item['state'] in ('RESERVED','CONSUMED') and item['reservation_ref'] is None:
            raise ValueError('Reserved/consumed dependency requires authoritative reservation reference')
        normalized_deps.append(dict(item))

    evidence=unique_strings(record['evidence_refs'],'evidence_refs')
    sources=unique_strings(record['source_refs'],'source_refs')
    for ref in sources:repository_ref(ref,root)

    unresolved=(record['state']=='UNCERTAIN'
                or any(x['state']=='UNCERTAIN' for x in normalized_deps))
    return {
        'reservation_id':record['reservation_id'],
        'operation_id':record['operation_id'],
        'generation':record['generation'],
        'state':record['state'],
        'request_id':record['request_id'],
        'envelope_id':record['envelope_id'],
        'spec_sha256':record['spec_sha256'],
        'authoritative_system':dict(system),
        'created_at':created.isoformat(),
        'expires_at':expires.isoformat(),
        'last_observed_at':observed.isoformat(),
        'resources':normalized,
        'dependency_handoffs':normalized_deps,
        'unresolved':unresolved,
        'evidence_refs':sorted(evidence)
    }


def validate(index,*,as_of=None,root=ROOT):
    if as_of is None:as_of=datetime.now(timezone.utc)
    if not isinstance(as_of,datetime) or as_of.tzinfo is None:
        raise ValueError('Timezone-aware as_of required')
    as_of=as_of.astimezone(timezone.utc)
    if set(index)!=INDEX_KEYS:raise ValueError('Unexpected reservation-index fields')
    if index['format']!=FORMAT or index['status']!=STATUS:
        raise ValueError('Unsupported reservation-index format or authority boundary')
    revision=index['reviewed_source_revision']
    if not isinstance(revision,str) or not re.fullmatch(r'[0-9a-f]{40}',revision):
        raise ValueError('Reviewed source revision must be an exact Git SHA')
    if not isinstance(index['records'],list) or len(index['records'])>512:
        raise ValueError('Reservation records must be a bounded list')

    reservation_ids=set();operation_ids={}
    records=[]
    for raw in index['records']:
        record=validate_record(raw,as_of=as_of,root=root)
        if record['reservation_id'] in reservation_ids:
            raise ValueError('Duplicate immutable reservation ID')
        reservation_ids.add(record['reservation_id'])
        prior=operation_ids.get(record['operation_id'])
        if prior is not None:
            raise ValueError('One idempotent operation ID cannot identify multiple reservation records')
        operation_ids[record['operation_id']]=record
        records.append(record)

    return {
        'records':records,
        'record_count':len(records),
        'held_count':sum(x['state']=='HELD' for x in records),
        'consumed_count':sum(x['state']=='CONSUMED' for x in records),
        'terminal_count':sum(x['state'] in ('RELEASED','EXPIRED') for x in records),
        'unresolved_count':sum(x['unresolved'] for x in records)
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index',type=Path,default=INDEX)
    parser.add_argument('--as-of',help='ISO-8601 review instant; defaults to current UTC')
    args=parser.parse_args()
    try:
        as_of=instant(args.as_of,'as_of') if args.as_of else datetime.now(timezone.utc)
        summary=validate(load(args.index),as_of=as_of)
        result={
            'status':'PASSED_EXPORTED_RESERVATION_RECORDS',
            'as_of':as_of.isoformat(),
            **{k:v for k,v in summary.items() if k!='records'},
            'may_create_reservation':False,'may_extend_reservation':False,
            'may_consume_reservation':False,'may_release_reservation':False,
            'may_allocate_address':False,'may_apply':False,'may_activate':False,
            'limits':[
                'The authoritative reservation system is external to this repository.',
                'UNCERTAIN outcomes require owner discovery/reconciliation; retries do not invent a second identity.',
                'Expired holds are not silently treated as reusable capacity.',
                'Dependency handoffs such as IPAM remain under their authoritative service owners.'
            ]
        }
        print(json.dumps(result,indent=2));return 0
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({
            'status':'FAILED_EXPORTED_RESERVATION_RECORDS','reason':str(exc),
            'may_create_reservation':False,'may_extend_reservation':False,
            'may_consume_reservation':False,'may_release_reservation':False,
            'may_allocate_address':False,'may_apply':False,'may_activate':False
        },indent=2));return 2


if __name__=='__main__':raise SystemExit(main())
