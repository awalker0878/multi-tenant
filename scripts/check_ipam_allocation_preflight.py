#!/usr/bin/env python3
"""Evaluate an authoritative-IPAM allocation intent without allocating an address.

The intent is bound to the parent reservation's IPAM dependency operation identity.
Actual values are returned only by the external authoritative IPAM and are never
invented or stored in this repository.
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

from scripts import check_ipam_allocation_records as ipam
from scripts import check_reservation_preflight as reservation_preflight
from scripts import check_reservation_records as reservation_records
from scripts import check_site_service_eligibility as sitecheck

FORMAT='portable-hosting-ipam-allocation-intent/1'
STATUS='PLANNING_ONLY_NOT_AUTHORIZED'
READY='IPAM_INTENT_READY_EXTERNAL_RESERVE_NOT_EXECUTED'
HOLD_PARENT='HOLD_PARENT_RESERVATION_NOT_HELD'
HOLD_CONFLICT='HOLD_IPAM_IDENTITY_OR_INTENT_CONFLICT'
HOLD_UNCERTAIN='HOLD_DISCOVER_IPAM_OUTCOME'
HOLD_RELEASE='HOLD_IPAM_RELEASE_LIFECYCLE'
HOLD_TERMINAL='HOLD_TERMINAL_IPAM_ALLOCATION_NEW_OPERATION_REQUIRED'
EXISTING_RESERVED='EXISTING_RESERVED_IPAM_ALLOCATION_IDEMPOTENT'
EXISTING_CONFIRMED='EXISTING_CONFIRMED_IPAM_ALLOCATION'
INTENT_KEYS={'format','status','spec','production_authority','source_refs'}
SPEC_KEYS={
    'allocation_id','operation_id','generation','reservation_id','request_id',
    'wsd_engineering_ref','reservation_intent_ref','allocation_policy',
    'overlap_exception_ref','family','allocation_kind','requested_prefix_length',
    'delegated_scope_ref','hold_expires_at','owners'
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
    if len(raw)>1024*1024:raise ValueError('IPAM allocation intent exceeds bounded size')
    def pairs(items):
        out={}
        for k,v in items:
            if k in out:raise ValueError('Duplicate JSON property')
            out[k]=v
        return out
    def reject(_):raise ValueError('Non-finite JSON number')
    value=json.loads(raw,object_pairs_hook=pairs,parse_constant=reject)
    if not isinstance(value,dict):raise ValueError('IPAM allocation intent must be an object')
    return value


def normalized_spec(intent,*,as_of):
    if set(intent)!=INTENT_KEYS or intent['format']!=FORMAT or intent['status']!=STATUS:
        raise ValueError('Unsupported IPAM intent shape or authority boundary')
    if intent['production_authority']!='NOT_ASSESSED':
        raise ValueError('IPAM preflight cannot carry production authority')
    if not isinstance(intent['source_refs'],list) or not intent['source_refs']:
        raise ValueError('source_refs required')
    if len(intent['source_refs'])!=len(set(intent['source_refs'])):
        raise ValueError('source_refs duplicates not allowed')
    for ref in intent['source_refs']:repository_ref(ref)

    spec=intent['spec']
    if not isinstance(spec,dict) or set(spec)!=SPEC_KEYS:
        raise ValueError('IPAM intent fields are incomplete or unexpected')
    for key in ('allocation_id','operation_id','reservation_id','request_id'):
        identifier(spec[key],key)
    if type(spec['generation']) is not int or spec['generation']<1:
        raise ValueError('generation must be a positive integer')
    repository_ref(spec['wsd_engineering_ref'])
    repository_ref(spec['reservation_intent_ref'])
    if spec['allocation_policy'] not in ipam.POLICIES:raise ValueError('Unknown allocation policy')
    if spec['allocation_policy']=='UNIQUE_DEFAULT':
        if spec['overlap_exception_ref'] is not None:
            raise ValueError('Unique-default intent cannot carry overlap exception')
    else:
        if spec['overlap_exception_ref'] is None:
            raise ValueError('Overlap allocation intent requires an explicit exception reference')
        bounded(spec['overlap_exception_ref'],'overlap_exception_ref')

    if spec['family'] not in ipam.FAMILIES or spec['allocation_kind'] not in ipam.KINDS:
        raise ValueError('Unknown family or allocation kind')
    ipam.validate_prefix_shape(spec['family'],spec['allocation_kind'],spec['requested_prefix_length'])
    bounded(spec['delegated_scope_ref'],'delegated_scope_ref')
    expires=ipam.instant(spec['hold_expires_at'],'hold_expires_at')
    if expires<=as_of:raise ValueError('Requested IPAM hold expiry must be future-dated')

    owners=spec['owners']
    if not isinstance(owners,dict) or set(owners)!=ipam.OWNER_KEYS:
        raise ValueError('Exact IPAM owner roles required')
    for key in ipam.OWNER_KEYS:bounded(owners[key],key)

    parent=reservation_preflight.load(ROOT/spec['reservation_intent_ref'])
    capacity_request_ref=parent.get('spec',{}).get('capacity_request_ref')
    if not isinstance(capacity_request_ref,str):raise ValueError('Parent reservation intent lacks capacity request')
    repository_ref(capacity_request_ref)
    capacity_request=sitecheck.load_request(ROOT/capacity_request_ref)
    parent_spec=reservation_preflight.normalized_spec(parent,capacity_request,as_of=as_of)

    if spec['reservation_id']!=parent_spec['reservation_id']:
        raise ValueError('IPAM intent reservation_id differs from parent reservation')
    if spec['request_id']!=parent_spec['request_id']:
        raise ValueError('IPAM intent request_id differs from parent reservation')
    if spec['wsd_engineering_ref']!=parent_spec['wsd_engineering_ref']:
        raise ValueError('IPAM intent WSD differs from parent reservation')
    matches=[x for x in parent_spec['dependency_handoffs']
             if x['kind'].lower()=='ipam' and x['operation_id']==spec['operation_id']]
    if len(matches)!=1:
        raise ValueError('IPAM operation_id must match exactly one parent IPAM dependency handoff')

    return {
        'allocation_id':spec['allocation_id'],'operation_id':spec['operation_id'],
        'generation':spec['generation'],'reservation_id':spec['reservation_id'],
        'request_id':spec['request_id'],'wsd_engineering_ref':spec['wsd_engineering_ref'],
        'reservation_intent_ref':spec['reservation_intent_ref'],
        'parent_reservation_spec_sha256':reservation_records.canonical_digest(parent_spec),
        'allocation_policy':spec['allocation_policy'],
        'overlap_exception_ref':spec['overlap_exception_ref'],
        'family':spec['family'],'allocation_kind':spec['allocation_kind'],
        'requested_prefix_length':spec['requested_prefix_length'],
        'delegated_scope_ref':spec['delegated_scope_ref'],
        'hold_expires_at':expires.isoformat(),'owners':dict(owners)
    }


def evaluate(intent,*,reservation_index=None,allocation_index=None,as_of=None):
    if as_of is None:as_of=datetime.now(timezone.utc)
    if not isinstance(as_of,datetime) or as_of.tzinfo is None:
        raise ValueError('Timezone-aware as_of required')
    as_of=as_of.astimezone(timezone.utc)
    if reservation_index is None:reservation_index=reservation_records.load()
    if allocation_index is None:allocation_index=ipam.load()

    spec=normalized_spec(intent,as_of=as_of)
    intent_sha=reservation_records.canonical_digest(spec)
    parent=reservation_records.validate(reservation_index,as_of=as_of)
    parent_record=next((x for x in parent['records']
                        if x['reservation_id']==spec['reservation_id']),None)
    parent_held=(parent_record is not None and parent_record['state']=='HELD'
                 and not parent_record['unresolved'])

    allocations=ipam.validate(allocation_index,as_of=as_of)
    by_op={x['operation_id']:x for x in allocations['records']}
    by_id={x['allocation_id']:x for x in allocations['records']}
    current=by_op.get(spec['operation_id'])
    same_id=by_id.get(spec['allocation_id'])

    if current is not None or same_id is not None:
        record=current or same_id
        same_identity=(record['allocation_id']==spec['allocation_id']
                       and record['operation_id']==spec['operation_id'])
        same_spec=(record['intent_sha256']==intent_sha
                   and record['generation']==spec['generation']
                   and record['reservation_id']==spec['reservation_id']
                   and record['request_id']==spec['request_id']
                   and record['allocation_policy']==spec['allocation_policy']
                   and record['family']==spec['family']
                   and record['allocation_kind']==spec['allocation_kind']
                   and record['requested_prefix_length']==spec['requested_prefix_length']
                   and record['delegated_scope_ref']==spec['delegated_scope_ref'])
        if not (same_identity and same_spec):
            result=HOLD_CONFLICT
        elif record['unresolved']:
            result=HOLD_UNCERTAIN
        elif record['state']=='RESERVED':
            result=EXISTING_RESERVED
        elif record['state']=='CONFIRMED':
            result=EXISTING_CONFIRMED
        elif record['state'] in ('RELEASE_PENDING','QUARANTINED'):
            result=HOLD_RELEASE
        else:
            result=HOLD_TERMINAL
    elif not parent_held:
        result=HOLD_PARENT
    else:
        result=READY

    return {
        'kind':'AUTHORITATIVE_IPAM_ALLOCATION_PREFLIGHT','status':result,
        'allocation_id':spec['allocation_id'],'operation_id':spec['operation_id'],
        'generation':spec['generation'],'reservation_id':spec['reservation_id'],
        'intent_sha256':intent_sha,'family':spec['family'],
        'allocation_kind':spec['allocation_kind'],
        'delegated_scope_ref':spec['delegated_scope_ref'],
        'actual_allocation_value':None,
        'actual_allocation_value_source':'AUTHORITATIVE_IPAM_ONLY',
        'may_reserve_address':False,'may_confirm_address':False,'may_release_address':False,
        'may_reuse_address':False,'may_write_dns':False,'may_apply':False,'may_activate':False,
        'next_owner_action':{
            READY:'Submit the immutable intent to the authoritative IPAM owner; do not supply or guess an allocation value.',
            HOLD_PARENT:'Establish/reconcile the parent HELD reservation before asking IPAM to reserve.',
            HOLD_CONFLICT:'Stop and reconcile the existing IPAM operation/allocation identity before retry.',
            HOLD_UNCERTAIN:'Discover the authoritative IPAM outcome before retry; never allocate another value blindly.',
            HOLD_RELEASE:'Complete/reconcile release cleanup and reuse quarantine under the IPAM owner.',
            HOLD_TERMINAL:'Use a new approved operation identity for a new allocation; do not revive released allocation state.',
            EXISTING_RESERVED:'Reuse the authoritative RESERVED allocation reference; do not reserve another value.',
            EXISTING_CONFIRMED:'Consume the authoritative CONFIRMED allocation reference; do not reserve another value.'
        }[result],
        'limits':[
            'No actual address or prefix is accepted as an input or returned by this repository preflight.',
            'The authoritative IPAM service is the only source of allocation values.',
            'IPAM service failure or missing evidence causes a hold, never a guessed allocation.',
            'DNS/network owners consume the authoritative allocation reference through their approved service handoff.'
        ]
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('intent',type=Path)
    p.add_argument('--as-of',help='ISO-8601 review instant; defaults to current UTC')
    p.add_argument('--expected-status',choices=(READY,HOLD_PARENT,HOLD_CONFLICT,HOLD_UNCERTAIN,HOLD_RELEASE,HOLD_TERMINAL,EXISTING_RESERVED,EXISTING_CONFIRMED))
    a=p.parse_args()
    try:
        as_of=ipam.instant(a.as_of,'as_of') if a.as_of else datetime.now(timezone.utc)
        result=evaluate(load(a.intent),as_of=as_of)
        print(json.dumps(result,indent=2))
        if a.expected_status is not None:return 0 if result['status']==a.expected_status else 2
        return 0 if result['status'] in (READY,EXISTING_RESERVED,EXISTING_CONFIRMED) else 2
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({
            'kind':'AUTHORITATIVE_IPAM_ALLOCATION_PREFLIGHT','status':'INVALID_IPAM_ALLOCATION_INTENT',
            'reason':str(exc),'actual_allocation_value':None,
            'may_reserve_address':False,'may_confirm_address':False,'may_release_address':False,
            'may_reuse_address':False,'may_write_dns':False,'may_apply':False,'may_activate':False
        },indent=2));return 2


if __name__=='__main__':raise SystemExit(main())
