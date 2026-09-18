#!/usr/bin/env python3
"""Evaluate native IPv6/address-family readiness without enabling an address family."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from scripts import check_address_family_assurance as assurance

FORMAT='portable-hosting-address-family-readiness-intent/1'
STATUS='PLANNING_ONLY_NOT_AUTHORIZED'
READY='ADDRESS_FAMILY_CURRENT_NO_NETWORK_MUTATION_AUTHORIZED'
HOLD_NONE='HOLD_NO_CURRENT_ADDRESS_FAMILY_ASSURANCE'
HOLD_REVIEW='HOLD_ADDRESS_FAMILY_REVIEW_DUE'
HOLD_PACKET='HOLD_ADDRESS_FAMILY_PACKET_TEST_DUE'
HOLD_DEPENDENCY='HOLD_ADDRESS_FAMILY_DEPENDENCY_DUE'
HOLD_GAPS='HOLD_ADDRESS_FAMILY_GAPS_OPEN'
HOLD_UNCERTAIN='HOLD_ADDRESS_FAMILY_ASSURANCE_UNCERTAIN'
HOLD_SCOPE='HOLD_ADDRESS_FAMILY_SCOPE_MISMATCH'
INTENT_KEYS={
    'format','status','request_id','qualification_id','platform',
    'offered_mode','offered_families','service_class_ref',
    'platform_profile_ref','production_authority','source_refs'
}


def load(path:Path):
    with path.open('rb') as stream:
        raw=stream.read(1024*1024+1)
    if len(raw)>1024*1024: raise ValueError('Address-family readiness intent exceeds bounded size')
    def pairs(items):
        out={}
        for k,v in items:
            if k in out: raise ValueError('Duplicate JSON property')
            out[k]=v
        return out
    value=json.loads(raw,object_pairs_hook=pairs)
    if not isinstance(value,dict): raise ValueError('Address-family readiness intent must be an object')
    return value


def validate_intent(intent):
    if set(intent)!=INTENT_KEYS or intent['format']!=FORMAT or intent['status']!=STATUS:
        raise ValueError('Unsupported address-family readiness intent')
    assurance.identifier(intent['request_id'],'request_id')
    assurance.identifier(intent['qualification_id'],'qualification_id')
    if intent['platform'] not in assurance.PLATFORMS:
        raise ValueError('Unknown platform family')
    if intent['offered_mode'] not in assurance.MODES:
        raise ValueError('Unsupported address-family mode')
    families=assurance.unique_strings(intent['offered_families'],'offered_families')
    if tuple(families)!=assurance.MODES[intent['offered_mode']]:
        raise ValueError('Offered family list does not match declared mode')
    for key in ('service_class_ref','platform_profile_ref'):
        assurance.opaque_ref(intent[key],key)
    if intent['production_authority']!='NOT_ASSESSED':
        raise ValueError('Address-family readiness cannot carry production authority')
    refs=assurance.unique_strings(intent['source_refs'],'source_refs')
    for ref in refs: assurance.repository_ref(ref)


def evaluate(intent,*,index=None,as_of=None):
    if as_of is None: as_of=datetime.now(timezone.utc)
    if not isinstance(as_of,datetime) or as_of.tzinfo is None:
        raise ValueError('Timezone-aware as_of required')
    as_of=as_of.astimezone(timezone.utc)
    validate_intent(intent)
    if index is None: index=assurance.load()
    summary=assurance.validate(index,as_of=as_of)
    records=[x for x in summary['records'] if x['qualification_id']==intent['qualification_id']]
    record=records[0] if records else None
    if record is None: result=HOLD_NONE
    elif record['state']=='UNCERTAIN': result=HOLD_UNCERTAIN
    elif record['state']=='REVIEW_DUE': result=HOLD_REVIEW
    elif record['state']=='PACKET_TEST_DUE': result=HOLD_PACKET
    elif record['state']=='DEPENDENCY_DUE': result=HOLD_DEPENDENCY
    elif record['state']=='GAPS_OPEN': result=HOLD_GAPS
    elif (
        record['platform']!=intent['platform']
        or record['offered_mode']!=intent['offered_mode']
        or record['offered_families']!=intent['offered_families']
        or record['service_class_ref']!=intent['service_class_ref']
        or record['platform_profile_ref']!=intent['platform_profile_ref']
    ): result=HOLD_SCOPE
    else: result=READY

    return {
        'kind':'ADDRESS_FAMILY_READINESS_PREFLIGHT','status':result,
        'request_id':intent['request_id'],'qualification_id':intent['qualification_id'],
        'assurance_id':record['assurance_id'] if record else None,
        'platform':intent['platform'],'offered_mode':intent['offered_mode'],
        'offered_families':intent['offered_families'],
        'open_gap_ids':record['open_gap_ids'] if record else [],
        'may_allocate_address':False,'may_enable_ipv6':False,
        'may_change_route':False,'may_change_policy':False,
        'may_change_shared_service':False,'may_apply':False,'may_activate':False,
        'next_owner_action':{
            READY:'Use this only as evidence that the exact offered family mode is currently qualified; enabling or changing the service remains separately controlled.',
            HOLD_NONE:'Publish current native platform, ZIP, shared-service, PMTU, failure and operations evidence for the exact offered family mode.',
            HOLD_REVIEW:'Refresh the family/service qualification or residual-gap review.',
            HOLD_PACKET:'Repeat current native IPv6 path, security-equivalence, PMTU and failure tests.',
            HOLD_DEPENDENCY:'Refresh shared-service and operational/recovery dependency evidence before offering the family.',
            HOLD_GAPS:'Resolve or formally disposition every OPEN address-family gap.',
            HOLD_UNCERTAIN:'Reconcile the authoritative native family/path/dependency state before relying on the record.',
            HOLD_SCOPE:'Use evidence for the exact platform, family mode, service class and platform profile.'
        }[result],
        'limits':[
            'A ready result is not permission to enable IPv6 or change an address-family offer.',
            'This preflight allocates no address and changes no route, policy or shared service.',
            'A local Linux namespace campaign remains supporting laboratory evidence only.',
            'CI never applies infrastructure or activates production.'
        ]
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('intent',type=Path)
    p.add_argument('--as-of',help='ISO-8601 review instant; defaults to current UTC')
    p.add_argument('--expected-status',choices=(READY,HOLD_NONE,HOLD_REVIEW,HOLD_PACKET,HOLD_DEPENDENCY,HOLD_GAPS,HOLD_UNCERTAIN,HOLD_SCOPE))
    a=p.parse_args()
    try:
        as_of=assurance.instant(a.as_of,'as_of') if a.as_of else datetime.now(timezone.utc)
        result=evaluate(load(a.intent),as_of=as_of)
        print(json.dumps(result,indent=2))
        if a.expected_status is not None: return 0 if result['status']==a.expected_status else 2
        return 0 if result['status']==READY else 2
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({
            'kind':'ADDRESS_FAMILY_READINESS_PREFLIGHT',
            'status':'INVALID_ADDRESS_FAMILY_READINESS_INTENT','reason':str(exc),
            'may_allocate_address':False,'may_enable_ipv6':False,
            'may_change_route':False,'may_change_policy':False,
            'may_change_shared_service':False,'may_apply':False,'may_activate':False
        },indent=2)); return 2


if __name__=='__main__':
    raise SystemExit(main())
