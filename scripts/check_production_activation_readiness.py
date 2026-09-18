#!/usr/bin/env python3
"""Evaluate production-activation readiness without authorizing activation."""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from scripts import check_production_activation_assurance as assurance

FORMAT='portable-hosting-production-activation-readiness-intent/1'
STATUS='PLANNING_ONLY_NOT_AUTHORIZED'
READY='PRODUCTION_ACTIVATION_PREREQUISITES_CURRENT_NO_ACTIVATION_AUTHORIZED'
CURRENT='PRODUCTION_SERVICE_ALREADY_ACTIVATED_CURRENT_NO_CHANGE_AUTHORIZED'
HOLD_NONE='HOLD_NO_CURRENT_PRODUCTION_ACTIVATION_ASSURANCE'
HOLD_REVIEW='HOLD_PRODUCTION_ACTIVATION_REVIEW_DUE'
HOLD_INITIAL='HOLD_INITIAL_OPERATIONAL_RECOVERY_READINESS_DUE'
HOLD_POST='HOLD_POST_ACTIVATION_VERIFICATION_DUE'
HOLD_WITHDRAWAL='HOLD_PRODUCTION_WITHDRAWAL_REQUIRED'
HOLD_GAPS='HOLD_PRODUCTION_ACTIVATION_GAPS_OPEN'
HOLD_UNCERTAIN='HOLD_PRODUCTION_ACTIVATION_UNCERTAIN'
HOLD_SCOPE='HOLD_PRODUCTION_ACTIVATION_SCOPE_MISMATCH'
INTENT_KEYS={'format','status','request_id','activation_id','site_ref','service_class_ref','platform_profile_ref','workload_scope_ref','exposure_profile_ref','production_authority','source_refs'}

def load(path):
    with Path(path).open('rb') as s: raw=s.read(1024*1024+1)
    if len(raw)>1024*1024: raise ValueError('Activation readiness intent exceeds bounded size')
    val=json.loads(raw)
    if not isinstance(val,dict): raise ValueError('Activation readiness intent must be an object')
    return val

def validate_intent(i):
    if set(i)!=INTENT_KEYS or i['format']!=FORMAT or i['status']!=STATUS: raise ValueError('Unsupported activation readiness intent')
    assurance.identifier(i['request_id'],'request_id'); assurance.identifier(i['activation_id'],'activation_id')
    for k in ('site_ref','service_class_ref','platform_profile_ref','workload_scope_ref','exposure_profile_ref'): assurance.opaque_ref(i[k],k)
    if i['production_authority']!='NOT_ASSESSED': raise ValueError('Readiness intent cannot carry production authority')
    for ref in assurance.unique_strings(i['source_refs'],'source_refs'): assurance.repository_ref(ref)

def evaluate(intent,index=None,as_of=None):
    if as_of is None: as_of=datetime.now(timezone.utc)
    if as_of.tzinfo is None: raise ValueError('Timezone-aware as_of required')
    as_of=as_of.astimezone(timezone.utc); validate_intent(intent)
    if index is None: index=assurance.load()
    summary=assurance.validate(index,as_of)
    records=[x for x in summary['records'] if x['activation_id']==intent['activation_id']]
    r=records[0] if records else None
    if r is None: result=HOLD_NONE
    elif r['state']=='UNCERTAIN': result=HOLD_UNCERTAIN
    elif r['state']=='REVIEW_DUE': result=HOLD_REVIEW
    elif r['state']=='INITIAL_READINESS_DUE': result=HOLD_INITIAL
    elif r['state']=='POST_ACTIVATION_DUE': result=HOLD_POST
    elif r['state']=='WITHDRAWAL_REQUIRED': result=HOLD_WITHDRAWAL
    elif r['state']=='GAPS_OPEN': result=HOLD_GAPS
    elif any([
        r['site_ref']!=intent['site_ref'],r['service_class_ref']!=intent['service_class_ref'],
        r['platform_profile_ref']!=intent['platform_profile_ref'],r['workload_scope_ref']!=intent['workload_scope_ref'],
        r['exposure_profile_ref']!=intent['exposure_profile_ref']
    ]): result=HOLD_SCOPE
    elif r['state']=='CURRENT_ACTIVATED': result=CURRENT
    else: result=READY
    return {
        'kind':'PRODUCTION_ACTIVATION_READINESS_PREFLIGHT','status':result,
        'request_id':intent['request_id'],'activation_id':intent['activation_id'],
        'assurance_id':r['assurance_id'] if r else None,
        'authority_status':r['authority_status'] if r else None,
        'activated_at':r['activated_at'] if r else None,
        'post_activation_outcome':r['post_activation_outcome'] if r else None,
        'withdrawal_status':r['withdrawal_status'] if r else None,
        'open_gap_ids':r['open_gap_ids'] if r else [],
        'may_release_quarantine':False,'may_change_exposure':False,'may_activate':False,
        'may_withdraw_sessions':False,'may_apply':False,'may_delete':False,
        'next_owner_action':{
            READY:'Use this only as prerequisite evidence; the accountable activation authority must still execute/authorize the controlled exposure change.',
            CURRENT:'The recorded service is already activated and current; any further exposure/change requires a separate current change decision.',
            HOLD_NONE:'Publish an exact activation record with current G0/G1/G2, applicable initial G4, operating authority, reversible G3 plan and withdrawal readiness.',
            HOLD_REVIEW:'Refresh scope or residual-gap review.',
            HOLD_INITIAL:'Refresh prerequisite, initial operating/recovery, withdrawal-readiness or operating-authority evidence before activation.',
            HOLD_POST:'Complete/refresh post-activation live entry/reply, dependency and telemetry verification.',
            HOLD_WITHDRAWAL:'Withdraw the failed/unknown exposure using the approved data-preserving withdrawal procedure and record the outcome.',
            HOLD_GAPS:'Resolve or formally disposition every OPEN activation gap.',
            HOLD_UNCERTAIN:'Reconcile the authoritative activation, authority, exposure and live-verification state.',
            HOLD_SCOPE:'Use evidence for the exact site/service/platform/workload/exposure scope.'
        }[result],
        'limits':[
            'A ready result never authorizes quarantine release, exposure change or production activation.',
            'Post-activation failure is a withdrawal condition, not permission to continue.',
            'CI performs no apply, deletion, session withdrawal or production mutation.'
        ]
    }

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('intent',type=Path); p.add_argument('--as-of'); p.add_argument('--expected-status',choices=(READY,CURRENT,HOLD_NONE,HOLD_REVIEW,HOLD_INITIAL,HOLD_POST,HOLD_WITHDRAWAL,HOLD_GAPS,HOLD_UNCERTAIN,HOLD_SCOPE))
    a=p.parse_args()
    try:
        as_of=assurance.instant(a.as_of,'as_of') if a.as_of else datetime.now(timezone.utc)
        result=evaluate(load(a.intent),as_of=as_of); print(json.dumps(result,indent=2))
        if a.expected_status is not None: return 0 if result['status']==a.expected_status else 2
        return 0 if result['status'] in (READY,CURRENT) else 2
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({'kind':'PRODUCTION_ACTIVATION_READINESS_PREFLIGHT','status':'INVALID_PRODUCTION_ACTIVATION_READINESS_INTENT','reason':str(exc),'may_release_quarantine':False,'may_change_exposure':False,'may_activate':False,'may_withdraw_sessions':False,'may_apply':False,'may_delete':False},indent=2)); return 2

if __name__=='__main__': raise SystemExit(main())
