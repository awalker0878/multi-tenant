#!/usr/bin/env python3
"""Evaluate reservation intent without creating or mutating a reservation.

The preflight re-evaluates the referenced site/service-capacity request, binds a
stable reservation/operation identity to that exact demand, and reconciles any
exported authoritative reservation record. All writes remain external.
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

from scripts import check_reservation_records as records
from scripts import check_site_service_capacity as capacity
from scripts import check_site_service_eligibility as sitecheck
from scripts import check_platform_qualification as qualification

FORMAT='portable-hosting-reservation-intent/1'
STATUS='PLANNING_ONLY_NOT_AUTHORIZED'
READY='RESERVATION_INTENT_READY_EXTERNAL_CREATE_NOT_EXECUTED'
HOLD_ENVELOPE='HOLD_ENVELOPE_NOT_CURRENTLY_ELIGIBLE'
HOLD_CONFLICT='HOLD_RESERVATION_IDENTITY_OR_INTENT_CONFLICT'
HOLD_UNCERTAIN='HOLD_DISCOVER_RESERVATION_OUTCOME'
HOLD_TERMINAL='HOLD_TERMINAL_RESERVATION_NEW_OPERATION_REQUIRED'
EXISTING_HELD='EXISTING_HELD_RESERVATION_IDEMPOTENT'
EXISTING_CONSUMED='EXISTING_CONSUMED_RESERVATION'
INTENT_KEYS={'format','status','spec','production_authority','source_refs'}
SPEC_KEYS={
    'reservation_id','operation_id','generation','request_id','wsd_engineering_ref',
    'envelope_id','capacity_request_ref','expires_at','owners','resources',
    'dependency_handoffs'
}
OWNER_KEYS=records.OWNER_KEYS
RESOURCE_KEYS=records.RESOURCE_KEYS
DEPENDENCY_KEYS={'kind','owner_role','operation_id'}
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
    if len(raw)>1024*1024:raise ValueError('Reservation intent exceeds bounded size')
    def pairs(items):
        out={}
        for k,v in items:
            if k in out:raise ValueError('Duplicate JSON property')
            out[k]=v
        return out
    def reject(_):raise ValueError('Non-finite JSON number')
    value=json.loads(raw,object_pairs_hook=pairs,parse_constant=reject)
    if not isinstance(value,dict):raise ValueError('Reservation intent must be an object')
    return value


def normalized_spec(intent,capacity_request,*,as_of):
    if set(intent)!=INTENT_KEYS or intent['format']!=FORMAT or intent['status']!=STATUS:
        raise ValueError('Unsupported reservation intent shape or authority boundary')
    if intent['production_authority']!='NOT_ASSESSED':
        raise ValueError('Reservation preflight cannot carry production authority')
    if not isinstance(intent['source_refs'],list) or not intent['source_refs']:
        raise ValueError('source_refs required')
    if len(intent['source_refs'])!=len(set(intent['source_refs'])):
        raise ValueError('source_refs duplicates not allowed')
    for ref in intent['source_refs']:repository_ref(ref)

    spec=intent['spec']
    if not isinstance(spec,dict) or set(spec)!=SPEC_KEYS:
        raise ValueError('Reservation spec fields are incomplete or unexpected')
    for key in ('reservation_id','operation_id','request_id','envelope_id'):
        identifier(spec[key],key)
    if type(spec['generation']) is not int or spec['generation']<1:
        raise ValueError('generation must be a positive integer')
    repository_ref(spec['wsd_engineering_ref'])
    repository_ref(spec['capacity_request_ref'])
    if spec['request_id']!=capacity_request['request_id']:
        raise ValueError('Reservation request_id differs from capacity request')
    if spec['wsd_engineering_ref']!=capacity_request['wsd_engineering_ref']:
        raise ValueError('Reservation WSD differs from capacity request')
    expires=records.instant(spec['expires_at'],'expires_at')
    if expires<=as_of:raise ValueError('Reservation intent expiry must be future-dated')

    owners=spec['owners']
    if not isinstance(owners,dict) or set(owners)!=OWNER_KEYS:
        raise ValueError('Exact reservation owners required')
    for key in OWNER_KEYS:bounded(owners[key],key)

    resources=spec['resources']
    if not isinstance(resources,list) or not resources:
        raise ValueError('Reservation resources required')
    seen=set();normalized_resources=[]
    for item in resources:
        if not isinstance(item,dict) or set(item)!=RESOURCE_KEYS:
            raise ValueError('Reservation resource shape invalid')
        identifier(item['id'],'resource.id')
        if item['id'] in seen:raise ValueError('Duplicate reservation resource')
        seen.add(item['id'])
        bounded(item['unit'],'resource.unit',64)
        records.number(item['quantity'],'resource.quantity')
        bounded(item['owner_role'],'resource.owner_role')
        normalized_resources.append(dict(item))

    demands={x['id']:(x['unit'],x['quantity']) for x in capacity_request['capacity_demands']}
    resources_map={x['id']:(x['unit'],x['quantity']) for x in normalized_resources}
    if resources_map!=demands:
        raise ValueError('Reservation resource dimensions/units/quantities must exactly match the capacity request')

    deps=spec['dependency_handoffs']
    if not isinstance(deps,list) or len(deps)>128:
        raise ValueError('dependency_handoffs must be bounded')
    dep_ids=set();normalized_deps=[]
    for item in deps:
        if not isinstance(item,dict) or set(item)!=DEPENDENCY_KEYS:
            raise ValueError('Dependency intent shape invalid')
        bounded(item['kind'],'dependency.kind',64)
        bounded(item['owner_role'],'dependency.owner_role')
        identifier(item['operation_id'],'dependency.operation_id')
        if item['operation_id'] in dep_ids:raise ValueError('Duplicate dependency operation identity')
        dep_ids.add(item['operation_id']);normalized_deps.append(dict(item))

    return {
        'reservation_id':spec['reservation_id'],
        'operation_id':spec['operation_id'],
        'generation':spec['generation'],
        'request_id':spec['request_id'],
        'wsd_engineering_ref':spec['wsd_engineering_ref'],
        'envelope_id':spec['envelope_id'],
        'capacity_request_ref':spec['capacity_request_ref'],
        'capacity_request_sha256':records.canonical_digest(capacity_request),
        'expires_at':expires.isoformat(),
        'owners':dict(owners),
        'resources':sorted(normalized_resources,key=lambda x:x['id']),
        'dependency_handoffs':sorted(normalized_deps,key=lambda x:x['operation_id'])
    }


def evaluate(intent,*,capacity_index=None,reservation_index=None,qindex=None,provenance_index=None,as_of=None):
    if as_of is None:as_of=datetime.now(timezone.utc)
    if not isinstance(as_of,datetime) or as_of.tzinfo is None:
        raise ValueError('Timezone-aware as_of required')
    as_of=as_of.astimezone(timezone.utc)
    if capacity_index is None:capacity_index=capacity.load()
    if reservation_index is None:reservation_index=records.load()
    if qindex is None:qindex=qualification.load()

    capacity_request_ref=intent.get('spec',{}).get('capacity_request_ref')
    if not isinstance(capacity_request_ref,str):raise ValueError('capacity_request_ref required')
    repository_ref(capacity_request_ref)
    capacity_request=sitecheck.load_request(ROOT/capacity_request_ref)
    spec=normalized_spec(intent,capacity_request,as_of=as_of)
    spec_sha=records.canonical_digest(spec)

    cap_result=sitecheck.evaluate(
        capacity_request,capacity_index,qindex=qindex,provenance_index=provenance_index,as_of=as_of)
    journal=records.validate(reservation_index,as_of=as_of)
    existing_by_op={x['operation_id']:x for x in journal['records']}
    existing_by_id={x['reservation_id']:x for x in journal['records']}
    current=existing_by_op.get(spec['operation_id'])
    same_id=existing_by_id.get(spec['reservation_id'])

    if current is not None or same_id is not None:
        record=current or same_id
        same_identity=(record['reservation_id']==spec['reservation_id']
                       and record['operation_id']==spec['operation_id'])
        same_spec=(record['spec_sha256']==spec_sha
                   and record['generation']==spec['generation']
                   and record['request_id']==spec['request_id']
                   and record['envelope_id']==spec['envelope_id'])
        if not (same_identity and same_spec):
            status=HOLD_CONFLICT
        elif record['unresolved']:
            status=HOLD_UNCERTAIN
        elif record['state']=='HELD':
            status=EXISTING_HELD
        elif record['state']=='CONSUMED':
            status=EXISTING_CONSUMED
        else:
            status=HOLD_TERMINAL
    elif spec['envelope_id'] not in cap_result['matching_envelopes']:
        status=HOLD_ENVELOPE
    else:
        status=READY

    return {
        'kind':'RESERVATION_PREFLIGHT',
        'status':status,
        'reservation_id':spec['reservation_id'],
        'operation_id':spec['operation_id'],
        'generation':spec['generation'],
        'spec_sha256':spec_sha,
        'envelope_id':spec['envelope_id'],
        'capacity_status':cap_result['status'],
        'may_create_reservation':False,'may_extend_reservation':False,
        'may_consume_reservation':False,'may_release_reservation':False,
        'may_allocate_address':False,'may_apply':False,'may_activate':False,
        'next_owner_action':{
            READY:'Submit the exact immutable spec to the authoritative reservation owner under its approved interface.',
            HOLD_ENVELOPE:'Re-evaluate site/cell/service-class eligibility; do not reserve or choose another unqualified target.',
            HOLD_CONFLICT:'Stop and reconcile the existing operation/reservation identity before any retry.',
            HOLD_UNCERTAIN:'Discover authoritative reservation/dependency outcome before any retry.',
            HOLD_TERMINAL:'Use a newly approved operation identity for a new reservation attempt; do not revive terminal state.',
            EXISTING_HELD:'Reuse the authoritative held reservation; do not create a duplicate.',
            EXISTING_CONSUMED:'Treat the reservation as already consumed and continue only under the owning workflow.'
        }[status],
        'limits':[
            'No reservation-system write occurs.',
            'No site is chosen by this check; envelope_id is supplied by the accepted workflow.',
            'No address or external dependency value is guessed.',
            'Spec identity is stable across retries; a changed spec with the same operation identity is a conflict.'
        ]
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('intent',type=Path)
    p.add_argument('--expected-status',choices=(READY,HOLD_ENVELOPE,HOLD_CONFLICT,HOLD_UNCERTAIN,HOLD_TERMINAL,EXISTING_HELD,EXISTING_CONSUMED))
    p.add_argument('--as-of',help='ISO-8601 review instant; defaults to current UTC')
    a=p.parse_args()
    try:
        as_of=records.instant(a.as_of,'as_of') if a.as_of else datetime.now(timezone.utc)
        result=evaluate(load(a.intent),as_of=as_of)
        print(json.dumps(result,indent=2))
        if a.expected_status is not None:return 0 if result['status']==a.expected_status else 2
        return 0 if result['status'] in (READY,EXISTING_HELD,EXISTING_CONSUMED) else 2
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({
            'kind':'RESERVATION_PREFLIGHT','status':'INVALID_RESERVATION_INTENT','reason':str(exc),
            'may_create_reservation':False,'may_extend_reservation':False,
            'may_consume_reservation':False,'may_release_reservation':False,
            'may_allocate_address':False,'may_apply':False,'may_activate':False
        },indent=2));return 2


if __name__=='__main__':raise SystemExit(main())
