#!/usr/bin/env python3
"""Evaluate restricted native-target selection readiness without contacting the target."""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from scripts import check_target_selection_assurance as assurance

FORMAT='portable-hosting-target-selection-readiness-intent/1'
STATUS='PLANNING_ONLY_NOT_AUTHORIZED'
READY='TARGET_SELECTION_CURRENT_NO_TARGET_CONTACT_AUTHORIZED'
HOLD_NONE='HOLD_NO_CURRENT_TARGET_SELECTION'
HOLD_REVIEW='HOLD_TARGET_SELECTION_REVIEW_DUE'
HOLD_CONTACT='HOLD_TARGET_CONTACT_AUTHORITY_DUE'
HOLD_GAPS='HOLD_TARGET_SELECTION_GAPS_OPEN'
HOLD_UNCERTAIN='HOLD_TARGET_SELECTION_UNCERTAIN'
HOLD_SCOPE='HOLD_TARGET_SELECTION_SCOPE_MISMATCH'
INTENT_KEYS={
    'format','status','request_id','selection_id','site_ref','cell_ref',
    'campaign_scope_ref','platform_family','product_tuple_id',
    'production_authority','source_refs'
}

def load(path):
    with Path(path).open('rb') as s:
        raw=s.read(1024*1024+1)
    if len(raw)>1024*1024:
        raise ValueError('Target-selection readiness intent exceeds bounded size')
    value=json.loads(raw)
    if not isinstance(value,dict):
        raise ValueError('Target-selection readiness intent must be an object')
    return value

def validate_intent(i):
    if set(i)!=INTENT_KEYS or i['format']!=FORMAT or i['status']!=STATUS:
        raise ValueError('Unsupported target-selection readiness intent')
    assurance.identifier(i['request_id'],'request_id')
    assurance.identifier(i['selection_id'],'selection_id')
    for k in ('site_ref','cell_ref','campaign_scope_ref'):
        assurance.opaque_ref(i[k],k)
    if i['platform_family'] not in assurance.PLATFORMS:
        raise ValueError('Unknown platform family')
    assurance.identifier(i['product_tuple_id'],'product_tuple_id')
    if i['production_authority']!='NOT_ASSESSED':
        raise ValueError('Target-selection readiness cannot carry production authority')
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
    records=[x for x in summary['records'] if x['selection_id']==intent['selection_id']]
    r=records[0] if records else None
    if r is None: result=HOLD_NONE
    elif r['state']=='UNCERTAIN': result=HOLD_UNCERTAIN
    elif r['state']=='REVIEW_DUE': result=HOLD_REVIEW
    elif r['state']=='CONTACT_AUTHORITY_DUE': result=HOLD_CONTACT
    elif r['state']=='GAPS_OPEN': result=HOLD_GAPS
    elif any([
        r['site_ref']!=intent['site_ref'],
        r['cell_ref']!=intent['cell_ref'],
        r['campaign_scope_ref']!=intent['campaign_scope_ref'],
        r['platform_family']!=intent['platform_family'],
        r['product_tuple_id']!=intent['product_tuple_id'],
    ]): result=HOLD_SCOPE
    else: result=READY

    return {
        'kind':'TARGET_SELECTION_READINESS_PREFLIGHT','status':result,
        'request_id':intent['request_id'],'selection_id':intent['selection_id'],
        'assurance_id':r['assurance_id'] if r else None,
        'platform_family':intent['platform_family'],
        'product_tuple_id':intent['product_tuple_id'],
        'security_edge_realization_ref':r['security_edge_realization_ref'] if r else None,
        'open_gap_ids':r['open_gap_ids'] if r else [],
        'may_select_target':False,'may_contact_target':False,
        'may_retrieve_credentials':False,'may_run_native_tests':False,
        'may_apply':False,'may_activate':False,
        'next_owner_action':{
            READY:'Use this only as evidence that the externally selected target/campaign scope is current; target contact and native execution remain separately authorized actions.',
            HOLD_NONE:'Record the actual site/cell, installed tuple, edge realization, restricted campaign scope, owners, stop authority and current target-contact authority.',
            HOLD_REVIEW:'Refresh the target-selection or residual-gap review.',
            HOLD_CONTACT:'Refresh the external target-contact authority/window before any target interaction.',
            HOLD_GAPS:'Resolve or formally disposition every OPEN target-selection gap.',
            HOLD_UNCERTAIN:'Reconcile the authoritative target, campaign scope, owner or contact-authority state.',
            HOLD_SCOPE:'Use evidence for the exact site/cell/campaign/platform/tuple selection.'
        }[result],
        'limits':[
            'A ready result is not permission to contact the target or retrieve credentials.',
            'Native execution still requires separately controlled campaign procedures and owners.',
            'CI never runs native tests, applies infrastructure or activates production.'
        ]
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('intent',type=Path)
    p.add_argument('--as-of')
    p.add_argument('--expected-status',choices=(READY,HOLD_NONE,HOLD_REVIEW,HOLD_CONTACT,HOLD_GAPS,HOLD_UNCERTAIN,HOLD_SCOPE))
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
            'kind':'TARGET_SELECTION_READINESS_PREFLIGHT',
            'status':'INVALID_TARGET_SELECTION_READINESS_INTENT','reason':str(exc),
            'may_select_target':False,'may_contact_target':False,
            'may_retrieve_credentials':False,'may_run_native_tests':False,
            'may_apply':False,'may_activate':False
        },indent=2)); return 2

if __name__=='__main__':
    raise SystemExit(main())
