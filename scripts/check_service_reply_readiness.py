#!/usr/bin/env python3
"""Evaluate origin-specific shared-service reply readiness without changing routing."""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from scripts import check_service_reply_assurance as assurance

FORMAT='portable-hosting-service-reply-readiness-intent/1'
STATUS='PLANNING_ONLY_NOT_AUTHORIZED'
READY='SERVICE_REPLY_CURRENT_NO_ROUTING_MUTATION_AUTHORIZED'
HOLD_NONE='HOLD_NO_CURRENT_SERVICE_REPLY_ASSURANCE'
HOLD_REVIEW='HOLD_SERVICE_REPLY_REVIEW_DUE'
HOLD_PATH='HOLD_SERVICE_REPLY_PATH_TEST_DUE'
HOLD_BINDING='HOLD_SERVICE_REPLY_BINDING_DUE'
HOLD_GAPS='HOLD_SERVICE_REPLY_GAPS_OPEN'
HOLD_UNCERTAIN='HOLD_SERVICE_REPLY_UNCERTAIN'
HOLD_SCOPE='HOLD_SERVICE_REPLY_SCOPE_MISMATCH'
INTENT_KEYS={
    'format','status','request_id','reply_id','site_ref','service_class_ref',
    'service_binding_ref','origin_context_ref','service_endpoint_ref',
    'address_family','production_authority','source_refs'
}


def load(path):
    with Path(path).open('rb') as s:
        raw=s.read(1024*1024+1)
    if len(raw)>1024*1024:
        raise ValueError('Service-reply readiness intent exceeds bounded size')
    value=json.loads(raw)
    if not isinstance(value,dict):
        raise ValueError('Service-reply readiness intent must be an object')
    return value


def validate_intent(i):
    if set(i)!=INTENT_KEYS or i['format']!=FORMAT or i['status']!=STATUS:
        raise ValueError('Unsupported service-reply readiness intent')
    assurance.identifier(i['request_id'],'request_id')
    assurance.identifier(i['reply_id'],'reply_id')
    for k in ('site_ref','service_class_ref','service_binding_ref','origin_context_ref','service_endpoint_ref'):
        assurance.opaque_ref(i[k],k)
    if i['address_family'] not in assurance.FAMILIES:
        raise ValueError('Unknown service-reply address family')
    if i['production_authority']!='NOT_ASSESSED':
        raise ValueError('Service-reply readiness cannot carry production authority')
    for ref in assurance.unique_strings(i['source_refs'],'source_refs'):
        assurance.repository_ref(ref)


def evaluate(intent,index=None,as_of=None):
    if as_of is None:
        as_of=datetime.now(timezone.utc)
    if as_of.tzinfo is None:
        raise ValueError('Timezone-aware as_of required')
    as_of=as_of.astimezone(timezone.utc)
    validate_intent(intent)
    if index is None:
        index=assurance.load()
    summary=assurance.validate(index,as_of)
    records=[x for x in summary['records'] if x['reply_id']==intent['reply_id']]
    r=records[0] if records else None
    if r is None: result=HOLD_NONE
    elif r['state']=='UNCERTAIN': result=HOLD_UNCERTAIN
    elif r['state']=='REVIEW_DUE': result=HOLD_REVIEW
    elif r['state']=='PATH_TEST_DUE': result=HOLD_PATH
    elif r['state']=='BINDING_DUE': result=HOLD_BINDING
    elif r['state']=='GAPS_OPEN': result=HOLD_GAPS
    elif any([
        r['site_ref']!=intent['site_ref'],
        r['service_class_ref']!=intent['service_class_ref'],
        r['service_binding_ref']!=intent['service_binding_ref'],
        r['origin_context_ref']!=intent['origin_context_ref'],
        r['service_endpoint_ref']!=intent['service_endpoint_ref'],
        r['address_family']!=intent['address_family'],
    ]): result=HOLD_SCOPE
    else: result=READY

    return {
        'kind':'SERVICE_REPLY_READINESS_PREFLIGHT','status':result,
        'request_id':intent['request_id'],'reply_id':intent['reply_id'],
        'assurance_id':r['assurance_id'] if r else None,
        'address_family':intent['address_family'],
        'open_gap_ids':r['open_gap_ids'] if r else [],
        'may_create_route':False,'may_change_service_binding':False,
        'may_change_policy':False,'may_revoke_binding':False,
        'may_change_service':False,'may_apply':False,'may_activate':False,
        'next_owner_action':{
            READY:'Use this only as evidence that the exact service reply binding is current; native routing and service changes remain with their accountable owners.',
            HOLD_NONE:'Publish current binding, origin-specific forward/reply, alternate-path exclusion, failure and service-operations evidence for the exact binding.',
            HOLD_REVIEW:'Refresh the service-reply scope or residual-gap review.',
            HOLD_PATH:'Repeat native forward/reply, source-validation, alternate-path and failure/recovery observations.',
            HOLD_BINDING:'Refresh entitlement/authentication/management-separation/revocation and service availability/lifecycle evidence.',
            HOLD_GAPS:'Resolve or formally disposition every OPEN service-reply gap.',
            HOLD_UNCERTAIN:'Reconcile the authoritative service binding, route ownership and failure state.',
            HOLD_SCOPE:'Use evidence for the exact site/service binding/origin endpoint/address-family scope.'
        }[result],
        'limits':[
            'A ready result is not route, policy or service-binding authority.',
            'This preflight performs no route installation, binding change or revocation.',
            'CI never applies infrastructure or activates production.'
        ]
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('intent',type=Path)
    p.add_argument('--as-of')
    p.add_argument('--expected-status',choices=(READY,HOLD_NONE,HOLD_REVIEW,HOLD_PATH,HOLD_BINDING,HOLD_GAPS,HOLD_UNCERTAIN,HOLD_SCOPE))
    a=p.parse_args()
    try:
        as_of=assurance.instant(a.as_of,'as_of') if a.as_of else datetime.now(timezone.utc)
        result=evaluate(load(a.intent),as_of=as_of)
        print(json.dumps(result,indent=2))
        if a.expected_status is not None:
            return 0 if result['status']==a.expected_status else 2
        return 0 if result['status']==READY else 2
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({
            'kind':'SERVICE_REPLY_READINESS_PREFLIGHT',
            'status':'INVALID_SERVICE_REPLY_READINESS_INTENT','reason':str(exc),
            'may_create_route':False,'may_change_service_binding':False,
            'may_change_policy':False,'may_revoke_binding':False,
            'may_change_service':False,'may_apply':False,'may_activate':False
        },indent=2)); return 2


if __name__=='__main__':
    raise SystemExit(main())
