#!/usr/bin/env python3
"""Evaluate native IPv6/address-family readiness without changing or offering service."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from scripts import check_native_ipv6_assurance as assurance

FORMAT='portable-hosting-native-ipv6-readiness-intent/1'
STATUS='PLANNING_ONLY_NOT_AUTHORIZED'
READY='NATIVE_IPV6_QUALIFICATION_CURRENT_NO_SERVICE_OFFER_AUTHORIZED'
HOLD_NONE='HOLD_NO_CURRENT_NATIVE_IPV6_ASSURANCE'
HOLD_REVIEW='HOLD_NATIVE_IPV6_REVIEW_DUE'
HOLD_QUALIFICATION='HOLD_NATIVE_IPV6_QUALIFICATION_DUE'
HOLD_GAPS='HOLD_NATIVE_IPV6_GAPS_OPEN'
HOLD_UNCERTAIN='HOLD_NATIVE_IPV6_ASSURANCE_UNCERTAIN'
HOLD_SCOPE='HOLD_NATIVE_IPV6_SCOPE_MISMATCH'
INTENT_KEYS={
    'format','status','request_id','site_ref','service_class_ref','platform',
    'platform_profile_ref','security_edge_profile_ref','family_mode',
    'production_authority','source_refs'
}


def load(path:Path):
    with path.open('rb') as stream:
        raw=stream.read(1024*1024+1)
    if len(raw)>1024*1024: raise ValueError('Native IPv6 readiness intent exceeds bounded size')
    def pairs(items):
        out={}
        for k,v in items:
            if k in out: raise ValueError('Duplicate JSON property')
            out[k]=v
        return out
    value=json.loads(raw,object_pairs_hook=pairs)
    if not isinstance(value,dict): raise ValueError('Native IPv6 readiness intent must be an object')
    return value


def validate_intent(intent):
    if set(intent)!=INTENT_KEYS or intent['format']!=FORMAT or intent['status']!=STATUS:
        raise ValueError('Unsupported native IPv6 readiness intent')
    assurance.identifier(intent['request_id'],'request_id')
    for key in ('site_ref','service_class_ref','platform_profile_ref','security_edge_profile_ref'):
        assurance.opaque_ref(intent[key],key)
    if intent['platform'] not in assurance.PLATFORMS:
        raise ValueError('Unknown native platform family')
    if intent['family_mode'] not in assurance.FAMILY_MODES:
        raise ValueError('Unknown address-family service mode')
    if intent['production_authority']!='NOT_ASSESSED':
        raise ValueError('Native IPv6 readiness cannot carry production authority')
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
    records=[
        x for x in summary['records']
        if x['site_ref']==intent['site_ref']
        and x['service_class_ref']==intent['service_class_ref']
        and x['platform']==intent['platform']
        and x['family_mode']==intent['family_mode']
    ]
    record=records[0] if records else None
    if record is None: result=HOLD_NONE
    elif record['state']=='UNCERTAIN': result=HOLD_UNCERTAIN
    elif record['state']=='REVIEW_DUE': result=HOLD_REVIEW
    elif record['state']=='QUALIFICATION_DUE': result=HOLD_QUALIFICATION
    elif record['state']=='GAPS_OPEN': result=HOLD_GAPS
    elif (
        record['platform_profile_ref']!=intent['platform_profile_ref']
        or record['security_edge_profile_ref']!=intent['security_edge_profile_ref']
    ): result=HOLD_SCOPE
    else: result=READY
    return {
        'kind':'NATIVE_IPV6_READINESS_PREFLIGHT','status':result,
        'request_id':intent['request_id'],'site_ref':intent['site_ref'],
        'service_class_ref':intent['service_class_ref'],'platform':intent['platform'],
        'family_mode':intent['family_mode'],
        'assurance_id':record['assurance_id'] if record else None,
        'addressing_mode':record['addressing_mode'] if record else None,
        'open_gap_ids':record['open_gap_ids'] if record else [],
        'may_offer_ipv6':False,'may_change_addressing':False,'may_change_routes':False,
        'may_change_security_policy':False,'may_change_mtu':False,
        'may_apply':False,'may_activate':False,
        'next_owner_action':{
            READY:'Use this only as evidence that the exact native address-family service scope is currently qualified; service offering and production activation remain separate decisions.',
            HOLD_NONE:'Qualify the exact site/service/platform/security-edge family mode across addressing, local protocols, routing/security, PMTU, shared services, failure/recovery and operations.',
            HOLD_REVIEW:'Refresh the address-family scope or residual-gap review before relying on this service mode.',
            HOLD_QUALIFICATION:'Repeat the native address-family campaign and operational acceptance before continuing to offer this family mode.',
            HOLD_GAPS:'Resolve or formally disposition every OPEN native IPv6 gap.',
            HOLD_UNCERTAIN:'Reconcile the authoritative native address-family, dependency and qualification state.',
            HOLD_SCOPE:'Use the exact qualified platform/security-edge profiles for this site/service/family scope.'
        }[result],
        'limits':[
            'A ready result is not service-offer, addressing, routing, policy, MTU, apply or activation authority.',
            'Local Linux packet evidence remains supporting laboratory evidence only.',
            'IPv6-only must prove absence of hidden IPv4 fallback; dual-stack must retain independent IPv4 evidence.',
            'CI never contacts or mutates a native platform.'
        ]
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('intent',type=Path)
    p.add_argument('--as-of',help='ISO-8601 review instant; defaults to current UTC')
    p.add_argument('--expected-status',choices=(READY,HOLD_NONE,HOLD_REVIEW,HOLD_QUALIFICATION,HOLD_GAPS,HOLD_UNCERTAIN,HOLD_SCOPE))
    a=p.parse_args()
    try:
        as_of=assurance.instant(a.as_of,'as_of') if a.as_of else datetime.now(timezone.utc)
        result=evaluate(load(a.intent),as_of=as_of)
        print(json.dumps(result,indent=2))
        if a.expected_status is not None: return 0 if result['status']==a.expected_status else 2
        return 0 if result['status']==READY else 2
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({
            'kind':'NATIVE_IPV6_READINESS_PREFLIGHT',
            'status':'INVALID_NATIVE_IPV6_READINESS_INTENT','reason':str(exc),
            'may_offer_ipv6':False,'may_change_addressing':False,'may_change_routes':False,
            'may_change_security_policy':False,'may_change_mtu':False,
            'may_apply':False,'may_activate':False
        },indent=2)); return 2


if __name__=='__main__':
    raise SystemExit(main())
