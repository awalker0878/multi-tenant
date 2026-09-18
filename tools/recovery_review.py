#!/usr/bin/env python3
"""Offline interrupted-infrastructure-change triage; NEVER retries/applies/deletes.

The operator context comes from the existing change/incident system. References,
digests and asserted fence observations are not signatures or proof of authority.
A favorable result is permission to REVIEW the recovery plan, not to execute it.
"""
from __future__ import annotations
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
import sys
if __package__ in (None,''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools import readback_core as c
from tools import nsx_observe, nutanix_observe

ADAPTERS={'nsx':nsx_observe,'nutanix':nutanix_observe}


def check_report(m:dict,report:dict,current:datetime,max_age:int)->str:
    if type(max_age) is not int or not 1<=max_age<=900:
        raise ValueError('Evidence age bound must be 1-900 seconds')
    c.exact_keys(report,{'kind','platform','profile','origin','operation_id','tenant_id','scope_id',
        'target_binding_ref','manifest_sha256','started_at','completed_at','outcome','stable_rounds',
        'request_count','history','coverage','may_apply','may_delete','may_activate','content_sha256'})
    if report['kind']!='NATIVE_READBACK_V1' or report['content_sha256']!=c.digest({k:v for k,v in report.items() if k!='content_sha256'}):
        raise ValueError('Report integrity/format mismatch')
    for k in ('platform','profile','origin','operation_id','tenant_id','scope_id','target_binding_ref'):
        if type(report[k]) is not str or report[k]!=m[k]:
            raise ValueError('Readback and accepted target scope differ')
    if report['manifest_sha256']!=c.digest(m) or any(report[k] is not False for k in ('may_apply','may_delete','may_activate')):
        raise ValueError('Readback scope or authority flags invalid')
    start=c.timestamp(report['started_at']);end=c.timestamp(report['completed_at'])
    if start>end or end>current or (current-start).total_seconds()>max_age:
        raise ValueError('Evidence is future-dated, reversed or stale')
    if type(report['request_count']) is not int or not 1<=report['request_count']<=400:
        raise ValueError('Invalid request count')
    hist=report['history']
    if not isinstance(hist,list) or not 1<=len(hist)<=10:
        raise ValueError('Incomplete observation history')
    previous=None;stable=0;prior_time=start
    keys={r['path'] if m['platform']=='nsx' else r['ext_id'] for r in m['resources']}
    for index,row in enumerate(hist,1):
        c.exact_keys(row,{'round','observed_at','snapshot_sha256','states','outcome'})
        if type(row['round']) is not int or row['round']!=index:
            raise ValueError('Observation round sequence invalid')
        t=c.timestamp(row['observed_at'])
        if t<prior_time or t>end:raise ValueError('Invalid sample chronology')
        prior_time=t
        states=row['states']
        if not isinstance(states,list) or not states or any(not isinstance(s,dict) for s in states):
            raise ValueError('Missing actual selected-resource observations')
        actual=[s.get('resource_key') for s in states]
        transport_unknown=(len(states)==1 and states[0].get('resource_key')=='scope' and states[0].get('config_status')=='UNKNOWN' and states[0].get('progress')=='UNKNOWN')
        if not transport_unknown:
            if any(not isinstance(k,str) for k in actual) or len(actual)!=len(set(actual)) or set(actual)!=keys:
                raise ValueError('Resource observation coverage mismatch')
            for state in states:
                if state.get('identity_match') is not True and state.get('config_status')!='UNKNOWN':
                    raise ValueError('Unbound native identity')
                if state.get('config_status') not in ('MATCH','DIFFERENT','UNKNOWN') or state.get('progress') not in ('COMPLETE','PENDING','FAILED','UNKNOWN'):
                    raise ValueError('Unknown observation result')
                if not isinstance(state.get('config_sha256'),str) or not c.HEX.fullmatch(state['config_sha256']):
                    raise ValueError('Missing selected-configuration digest')
                if state['config_status']=='MATCH' and state.get('mismatch_fields')!=[]:
                    raise ValueError('Match contains contradictory mismatch information')
        sh=c.digest(states)
        if row['snapshot_sha256']!=sh:raise ValueError('Sample digest mismatch')
        stable=stable+1 if sh==previous else 1;previous=sh
        value=c.outcome(states,stable)
        if row['outcome']!=value:raise ValueError('Summary disagrees with observations')
    if report['outcome']!=value or type(report['stable_rounds']) is not int or report['stable_rounds']!=stable:
        raise ValueError('Final observation summary is inconsistent')
    return value


def valid_control(observation:dict,scope:str,start:datetime,current:datetime,max_age:int)->bool:
    c.exact_keys(observation,{'state','scope_id','observed_at','evidence_ref'})
    c.text(observation['evidence_ref'],'existing operational evidence reference')
    t=c.timestamp(observation['observed_at'])
    return observation['state']=='VERIFIED' and observation['scope_id']==scope and start<=t<=current and (current-t).total_seconds()<=max_age


def review(m:dict,report:dict,context:dict,*,current:datetime|None=None,max_age=300)->dict:
    current=current or datetime.now(timezone.utc)
    reasons=[];result='HOLD_INVALID_EVIDENCE'
    try:
        if m.get('platform') not in ADAPTERS:raise ValueError('Unsupported platform')
        ADAPTERS[m['platform']].validate(m)
        c.exact_keys(context,{'kind','operation_id','tenant_id','scope_id','manifest_sha256','report_sha256',
            'accepted_plan_sha256','change_record_ref','attempted_at','last_security_change_at',
            'attempted_generation','current_generation','executor_state','writer_fence','quarantine','containment','data_disposition'})
        c.reject_sensitive(context)
        if context['kind']!='INTERRUPTED_CHANGE_CONTEXT_V1':raise ValueError('Wrong context')
        for k in ('operation_id','tenant_id','scope_id'):
            if context[k]!=m[k]:raise ValueError('Context scope mismatch')
        for k in ('manifest_sha256','report_sha256','accepted_plan_sha256'):
            if not isinstance(context[k],str) or not c.HEX.fullmatch(context[k]) or set(context[k])=={'0'}:
                raise ValueError('Missing operation digest')
        if context['manifest_sha256']!=c.digest(m) or context['report_sha256']!=report.get('content_sha256'):
            raise ValueError('Unbound operation evidence')
        c.text(context['change_record_ref'],'existing change record')
        attempted=c.timestamp(context['attempted_at']);changed=c.timestamp(context['last_security_change_at'])
        if attempted>current or changed>current or c.timestamp(report['started_at'])<max(attempted,changed):
            raise ValueError('Observation predates operation or security change')
        result_native=check_report(m,report,current,max_age)
        if type(context['attempted_generation']) is not int or type(context['current_generation']) is not int or min(context['attempted_generation'],context['current_generation'])<0:
            raise ValueError('Invalid engineering generation')
        if context['executor_state'] not in ('STOPPED','RUNNING','UNKNOWN') or context['containment'] not in ('NONE','ACTIVE','UNKNOWN'):
            raise ValueError('Unknown writer/containment disposition')
        if context['data_disposition']!='PRESERVE':raise ValueError('This procedure never authorizes data destruction')
        fenced=valid_control(context['writer_fence'],m['scope_id'],max(attempted,changed),current,max_age)
        denied=valid_control(context['quarantine'],m['scope_id'],max(attempted,changed),current,max_age)
        if context['containment']=='ACTIVE':
            result='KEEP_INCIDENT_CONTAINMENT';reasons=['INCIDENT_AUTHORITY_REMAINS_IN_FORCE']
        elif context['containment']=='UNKNOWN':
            result='HOLD_CONTAINMENT_UNKNOWN';reasons=['DO_NOT_RESTORE_ORDINARY_ALLOW_POLICY']
        elif context['executor_state']!='STOPPED' or not fenced:
            result='HOLD_WRITER_NOT_FENCED';reasons=['OBSERVE_AND_FENCE_EXISTING_WRITERS_BEFORE_RECOVERY_REVIEW']
        elif context['attempted_generation']!=context['current_generation']:
            result='HOLD_SUPERSEDED_CHANGE';reasons=['REPLAN_AGAINST_CURRENT_APPROVED_ENGINEERING']
        elif not denied:
            result='HOLD_QUARANTINE_NOT_VERIFIED';reasons=['REESTABLISH_CONFIRMED_RESTRICTED_POSTURE_UNDER_ITS_OWNER']
        elif result_native=='HOLD_NATIVE_PENDING':
            result='WAIT_FOR_NATIVE_TASK';reasons=['DO_NOT_REPLAY_OR_CANCEL_FROM_THIS_TOOL']
        elif result_native=='HOLD_NATIVE_FAILURE':
            result='INSPECT_PARTIAL_FAILURE';reasons=['FAILED_OR_CANCELED_TASK_DOES_NOT_MEAN_NOTHING_CHANGED']
        elif result_native=='HOLD_DIFFERENCE':
            result='RECONCILE_DIVERGENCE';reasons=['NATIVE_CONFIG_DIFFERS_PRESERVE_DATA_AND_REVIEW_OWNERSHIP']
        elif result_native!='READBACK_MATCH_NOT_QUALIFIED':
            result='HOLD_NATIVE_UNCERTAINTY';reasons=['CURRENT_STABLE_NATIVE_COMPLETION_NOT_ESTABLISHED']
        else:
            result='READY_FOR_OPERATOR_RECOVERY_REVIEW';reasons=['NO_REPLAY_NEEDED_BY_OBSERVED_FIELDS','RECONCILE_STATE_AND_INDEPENDENT_VERIFICATION_BEFORE_ANY_NEW_CHANGE']
    except (ValueError,TypeError,KeyError,RecursionError):
        result='HOLD_INVALID_EVIDENCE';reasons=['MISSING_STALE_CONTRADICTORY_OR_UNBOUND_INPUT']
    return {'kind':'INTERRUPTED_CHANGE_TRIAGE_V1','result':result,'reasons':reasons,
        'evaluated_at':current.isoformat(),'may_apply':False,'may_delete':False,'may_activate':False,
        'proof_limit':'Record consistency only. Signatures, true writer fencing, native RBAC, data ownership and operational authorization require their respective authorities.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest',type=Path);p.add_argument('readback',type=Path);p.add_argument('context',type=Path)
    p.add_argument('--max-age-seconds',type=int,default=300);p.add_argument('--output',type=Path)
    a=p.parse_args()
    try:
        result=review(c.load(a.manifest),c.load(a.readback),c.load(a.context),max_age=a.max_age_seconds)
        if a.output:
            with c.PrivateJournal(a.output) as f:f.write(result)
        print(json.dumps(result,indent=2))
        return 0 if result['result']=='READY_FOR_OPERATOR_RECOVERY_REVIEW' else 2
    except (ValueError,OSError,TypeError,KeyError):
        print(json.dumps({'result':'HOLD_INVALID_EVIDENCE','may_apply':False,'may_delete':False,'may_activate':False}))
        return 2
if __name__=='__main__':raise SystemExit(main())
