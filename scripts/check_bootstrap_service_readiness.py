#!/usr/bin/env python3
"""Evaluate bootstrap-service readiness without mutating bootstrap dependencies."""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from scripts import check_bootstrap_service_assurance as assurance

FORMAT='portable-hosting-bootstrap-service-readiness-intent/1'
STATUS='PLANNING_ONLY_NOT_AUTHORIZED'
READY='BOOTSTRAP_SERVICE_CURRENT_NO_BOOTSTRAP_MUTATION_AUTHORIZED'
HOLD_NONE='HOLD_NO_CURRENT_BOOTSTRAP_SERVICE_ASSURANCE'
HOLD_REVIEW='HOLD_BOOTSTRAP_REVIEW_DUE'
HOLD_DEPENDENCY='HOLD_BOOTSTRAP_DEPENDENCY_DUE'
HOLD_TRANSITION='HOLD_BOOTSTRAP_TRANSITION_DUE'
HOLD_GAPS='HOLD_BOOTSTRAP_GAPS_OPEN'
HOLD_UNCERTAIN='HOLD_BOOTSTRAP_ASSURANCE_UNCERTAIN'
HOLD_SCOPE='HOLD_BOOTSTRAP_SCOPE_MISMATCH'
INTENT_KEYS={
    'format','status','request_id','bootstrap_id','site_ref','service_class_ref',
    'platform_profile_ref','bootstrap_profile_ref','address_family_profile_ref',
    'production_authority','source_refs'
}

def load(path):
    with Path(path).open('rb') as s:
        raw=s.read(1024*1024+1)
    if len(raw)>1024*1024:
        raise ValueError('Bootstrap readiness intent exceeds bounded size')
    value=json.loads(raw)
    if not isinstance(value,dict):
        raise ValueError('Bootstrap readiness intent must be an object')
    return value

def validate_intent(i):
    if set(i)!=INTENT_KEYS or i['format']!=FORMAT or i['status']!=STATUS:
        raise ValueError('Unsupported bootstrap readiness intent')
    assurance.identifier(i['request_id'],'request_id')
    assurance.identifier(i['bootstrap_id'],'bootstrap_id')
    for k in ('site_ref','service_class_ref','platform_profile_ref','bootstrap_profile_ref','address_family_profile_ref'):
        assurance.opaque_ref(i[k],k)
    if i['production_authority']!='NOT_ASSESSED':
        raise ValueError('Bootstrap readiness cannot carry production authority')
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
    records=[x for x in summary['records'] if x['bootstrap_id']==intent['bootstrap_id']]
    r=records[0] if records else None
    if r is None: result=HOLD_NONE
    elif r['state']=='UNCERTAIN': result=HOLD_UNCERTAIN
    elif r['state']=='REVIEW_DUE': result=HOLD_REVIEW
    elif r['state']=='DEPENDENCY_DUE': result=HOLD_DEPENDENCY
    elif r['state']=='TRANSITION_DUE': result=HOLD_TRANSITION
    elif r['state']=='GAPS_OPEN': result=HOLD_GAPS
    elif any([
        r['site_ref']!=intent['site_ref'],
        r['service_class_ref']!=intent['service_class_ref'],
        r['platform_profile_ref']!=intent['platform_profile_ref'],
        r['bootstrap_profile_ref']!=intent['bootstrap_profile_ref'],
        r['address_family_profile_ref']!=intent['address_family_profile_ref']
    ]): result=HOLD_SCOPE
    else: result=READY
    return {
        'kind':'BOOTSTRAP_SERVICE_READINESS_PREFLIGHT','status':result,
        'request_id':intent['request_id'],'bootstrap_id':intent['bootstrap_id'],
        'assurance_id':r['assurance_id'] if r else None,
        'open_gap_ids':r['open_gap_ids'] if r else [],
        'may_allocate_address':False,'may_write_dns':False,
        'may_change_dhcp_metadata':False,'may_issue_credential':False,
        'may_change_service_binding':False,'may_retire_bootstrap_dependency':False,
        'may_apply':False,'may_activate':False,
        'next_owner_action':{
            READY:'Use this only as evidence that the exact bootstrap service profile is current; bootstrap mutations remain with their accountable service owners.',
            HOLD_NONE:'Publish current authoritative address/name, minimum dependency, restricted-management, failure and steady-state transition evidence for the exact bootstrap scope.',
            HOLD_REVIEW:'Refresh the bootstrap-profile or residual-gap review.',
            HOLD_DEPENDENCY:'Refresh authoritative IPAM/DNS/address-assignment and minimum name/time/trust/artifact/telemetry/service-reply dependency evidence.',
            HOLD_TRANSITION:'Refresh restricted management/execution, dependency-loss and temporary-to-steady-state transition evidence.',
            HOLD_GAPS:'Resolve or formally disposition every OPEN bootstrap gap.',
            HOLD_UNCERTAIN:'Reconcile the authoritative bootstrap dependency and handover state.',
            HOLD_SCOPE:'Use evidence for the exact site/service/platform/bootstrap/address-family profile scope.'
        }[result],
        'limits':[
            'A ready result is not permission to allocate, register names, issue credentials or change service bindings.',
            'This preflight performs no bootstrap mutation, apply or production activation.',
            'Temporary recovery material cannot be retired merely because steady-state services are reachable.'
        ]
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('intent',type=Path)
    p.add_argument('--as-of')
    p.add_argument('--expected-status',choices=(READY,HOLD_NONE,HOLD_REVIEW,HOLD_DEPENDENCY,HOLD_TRANSITION,HOLD_GAPS,HOLD_UNCERTAIN,HOLD_SCOPE))
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
            'kind':'BOOTSTRAP_SERVICE_READINESS_PREFLIGHT',
            'status':'INVALID_BOOTSTRAP_SERVICE_READINESS_INTENT','reason':str(exc),
            'may_allocate_address':False,'may_write_dns':False,
            'may_change_dhcp_metadata':False,'may_issue_credential':False,
            'may_change_service_binding':False,'may_retire_bootstrap_dependency':False,
            'may_apply':False,'may_activate':False
        },indent=2)); return 2

if __name__=='__main__':
    raise SystemExit(main())
