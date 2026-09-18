#!/usr/bin/env python3
"""Validate production-activation and initial-readiness assurance evidence.

This repository is not an activation executor, authorizing authority, exposure controller,
incident authority, or production change system. Records contain opaque references to
externally owned decisions/evidence. The checker never releases quarantine, changes
exposure, applies infrastructure, withdraws sessions, or activates production.
"""
from __future__ import annotations
import argparse, json, re
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'sources/capabilities/production_activation_assurance_index.json'
FORMAT='portable-hosting-production-activation-assurance-index/1'
STATUS='EXPORTED_ACTIVATION_READINESS_EVIDENCE_NOT_ACTIVATION_AUTHORITY'
STATES={
    'READY_FOR_CONTROLLED_ACTIVATION','CURRENT_ACTIVATED','REVIEW_DUE',
    'INITIAL_READINESS_DUE','POST_ACTIVATION_DUE','WITHDRAWAL_REQUIRED',
    'GAPS_OPEN','UNCERTAIN'
}
AUTHORITY_STATES={'APPROVED','CONDITIONAL','SUSPENDED','REJECTED','NOT_ISSUED'}
POST_OUTCOMES={'NOT_RUN','PASSED','FAILED','UNKNOWN'}
WITHDRAWAL_STATES={'TESTED_READY','REQUIRED','COMPLETED'}
GAP_STATES={'OPEN','ACCEPTED'}
ID=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{1,191}$')
INDEX_KEYS={'format','status','reviewed_source_revision','records'}
RECORD_KEYS={
    'assurance_id','generation','state','activation_id','scope','prerequisites',
    'initial_readiness','activation','post_activation','withdrawal',
    'residual_gaps','source_refs'
}
SCOPE_KEYS={
    'site_ref','service_class_ref','platform_profile_ref','workload_scope_ref',
    'exposure_profile_ref','owner_ref','accepted_at','review_by'
}
PREREQ_KEYS={
    'g0_reference_adoption_ref','g1_site_design_ref','g2_platform_service_qualification_ref',
    'capacity_ref','reservation_ref','address_ipam_dns_ref','security_edge_ref',
    'control_inheritance_ref','backup_restore_ref','native_reconciliation_ref',
    'address_family_ref','operational_handover_ref','observed_at','valid_until'
}
INITIAL_KEYS={
    'recovery_readiness_ref','monitoring_alerting_ref','owner_oncall_ref',
    'credential_custody_ref','incident_containment_ref','observed_at','valid_until'
}
ACTIVATION_KEYS={
    'authority_status','operating_authority_ref','decision_ref','authority_valid_until',
    'change_record_ref','exposure_scope_ref','reversible_change_ref',
    'pre_activation_verification_ref','activation_receipt_ref','activated_at'
}
POST_KEYS={
    'outcome','live_entry_reply_ref','dependency_path_ref','monitoring_witness_ref',
    'observed_at','valid_until'
}
WITHDRAWAL_KEYS={
    'status','plan_ref','test_ref','preserve_data_ref','session_withdrawal_ref',
    'observed_at','valid_until'
}
GAP_KEYS={'gap_id','status','owner_ref','treatment_ref','decision_ref','review_by'}

def bounded(v,label,limit=1024):
    if not isinstance(v,str) or not v.strip() or len(v)>limit or any(ord(c)<32 or ord(c)==127 for c in v):
        raise ValueError(f'{label}: bounded nonempty text required')
    return v

def identifier(v,label):
    bounded(v,label,192)
    if not ID.fullmatch(v): raise ValueError(f'{label}: invalid identifier')
    return v

def positive_int(v,label):
    if type(v) is not int or v<1: raise ValueError(f'{label}: positive integer required')
    return v

def instant(v,label):
    bounded(v,label,64)
    dt=datetime.fromisoformat(v.replace('Z','+00:00'))
    if dt.tzinfo is None: raise ValueError(f'{label}: timezone required')
    return dt.astimezone(timezone.utc)

def opaque_ref(v,label):
    bounded(v,label,256)
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.:-]{1,255}',v):
        raise ValueError(f'{label}: opaque controlled reference required')
    return v

def repository_ref(v,root=ROOT):
    bounded(v,'repository reference')
    p=Path(v)
    if p.is_absolute() or '..' in p.parts or '\\' in v or ':' in v:
        raise ValueError('Repository reference must be normalized and relative')
    if not (root/p).exists(): raise ValueError(f'Repository reference does not exist: {v}')
    return v

def unique_strings(v,label,allow_empty=False,maximum=128):
    if not isinstance(v,list) or len(v)>maximum or (not allow_empty and not v):
        raise ValueError(f'{label}: bounded list required')
    if any(not isinstance(x,str) or not x.strip() for x in v): raise ValueError(f'{label}: nonempty strings required')
    if len(v)!=len(set(v)): raise ValueError(f'{label}: duplicates not allowed')
    return v

def load(path:Path=INDEX):
    with path.open('rb') as s: raw=s.read(1024*1024+1)
    if len(raw)>1024*1024: raise ValueError('Activation assurance index exceeds bounded size')
    def pairs(items):
        out={}
        for k,v in items:
            if k in out: raise ValueError('Duplicate JSON property')
            out[k]=v
        return out
    def reject(_): raise ValueError('Non-finite JSON number')
    val=json.loads(raw,object_pairs_hook=pairs,parse_constant=reject)
    if not isinstance(val,dict): raise ValueError('Activation assurance index must be an object')
    return val

def ref_time_block(value,keys,label,as_of):
    if not isinstance(value,dict) or set(value)!=keys: raise ValueError(f'{label}: evidence shape invalid')
    for key in keys-{'observed_at','valid_until'}: opaque_ref(value[key],f'{label}.{key}')
    observed=instant(value['observed_at'],f'{label}.observed_at')
    valid=instant(value['valid_until'],f'{label}.valid_until')
    if observed>as_of or valid<=observed: raise ValueError(f'{label}: chronology invalid')
    return observed,valid

def validate_record(record,as_of,root=ROOT):
    if not isinstance(record,dict) or set(record)!=RECORD_KEYS:
        raise ValueError('Activation assurance record has unexpected or missing fields')
    identifier(record['assurance_id'],'assurance_id'); identifier(record['activation_id'],'activation_id')
    positive_int(record['generation'],'generation')
    if record['state'] not in STATES: raise ValueError('Unknown activation assurance state')

    scope=record['scope']
    if not isinstance(scope,dict) or set(scope)!=SCOPE_KEYS: raise ValueError('Activation scope shape invalid')
    for k in ('site_ref','service_class_ref','platform_profile_ref','workload_scope_ref','exposure_profile_ref','owner_ref'):
        opaque_ref(scope[k],f'scope.{k}')
    accepted=instant(scope['accepted_at'],'scope.accepted_at'); review_by=instant(scope['review_by'],'scope.review_by')
    if accepted>as_of or review_by<=accepted: raise ValueError('Activation scope chronology invalid')

    _,prereq_valid=ref_time_block(record['prerequisites'],PREREQ_KEYS,'prerequisites',as_of)
    _,initial_valid=ref_time_block(record['initial_readiness'],INITIAL_KEYS,'initial_readiness',as_of)

    activation=record['activation']
    if not isinstance(activation,dict) or set(activation)!=ACTIVATION_KEYS: raise ValueError('Activation decision shape invalid')
    if activation['authority_status'] not in AUTHORITY_STATES: raise ValueError('Unknown operating authority status')
    for k in ('operating_authority_ref','decision_ref','change_record_ref','exposure_scope_ref','reversible_change_ref','pre_activation_verification_ref'):
        opaque_ref(activation[k],f'activation.{k}')
    authority_valid=instant(activation['authority_valid_until'],'activation.authority_valid_until')
    if activation['activation_receipt_ref'] is None:
        if activation['activated_at'] is not None: raise ValueError('Activation timestamp cannot exist without activation receipt')
        activated_at=None
    else:
        opaque_ref(activation['activation_receipt_ref'],'activation.activation_receipt_ref')
        activated_at=instant(activation['activated_at'],'activation.activated_at')
        if activated_at>as_of: raise ValueError('Activation timestamp is future-dated')

    post=record['post_activation']
    if not isinstance(post,dict) or set(post)!=POST_KEYS: raise ValueError('Post-activation evidence shape invalid')
    if post['outcome'] not in POST_OUTCOMES: raise ValueError('Unknown post-activation outcome')
    post_valid=None
    if post['outcome']=='NOT_RUN':
        if any(post[k] is not None for k in ('live_entry_reply_ref','dependency_path_ref','monitoring_witness_ref','observed_at','valid_until')):
            raise ValueError('NOT_RUN post-activation evidence cannot carry observations')
    else:
        for k in ('live_entry_reply_ref','dependency_path_ref','monitoring_witness_ref'):
            opaque_ref(post[k],f'post_activation.{k}')
        observed=instant(post['observed_at'],'post_activation.observed_at')
        post_valid=instant(post['valid_until'],'post_activation.valid_until')
        if observed>as_of or post_valid<=observed: raise ValueError('Post-activation chronology invalid')
        if activated_at is None or observed<activated_at: raise ValueError('Post-activation observation must follow activation')

    withdrawal=record['withdrawal']
    if not isinstance(withdrawal,dict) or set(withdrawal)!=WITHDRAWAL_KEYS: raise ValueError('Withdrawal evidence shape invalid')
    if withdrawal['status'] not in WITHDRAWAL_STATES: raise ValueError('Unknown withdrawal status')
    for k in ('plan_ref','test_ref','preserve_data_ref','session_withdrawal_ref'):
        opaque_ref(withdrawal[k],f'withdrawal.{k}')
    withdrawal_observed=instant(withdrawal['observed_at'],'withdrawal.observed_at')
    withdrawal_valid=instant(withdrawal['valid_until'],'withdrawal.valid_until')
    if withdrawal_observed>as_of or withdrawal_valid<=withdrawal_observed: raise ValueError('Withdrawal chronology invalid')

    gaps=record['residual_gaps']; open_gaps=[]; gap_ids=set(); gap_reviews=[]
    if not isinstance(gaps,list) or len(gaps)>1024: raise ValueError('Residual activation gaps must be a bounded list')
    for gap in gaps:
        if not isinstance(gap,dict) or set(gap)!=GAP_KEYS: raise ValueError('Residual activation gap shape invalid')
        gid=identifier(gap['gap_id'],'gap_id')
        if gid in gap_ids: raise ValueError('Duplicate residual activation gap ID')
        gap_ids.add(gid)
        if gap['status'] not in GAP_STATES: raise ValueError('Unknown residual activation gap state')
        opaque_ref(gap['owner_ref'],'gap.owner_ref'); opaque_ref(gap['treatment_ref'],'gap.treatment_ref')
        gr=instant(gap['review_by'],'gap.review_by'); gap_reviews.append(gr)
        if gap['status']=='OPEN':
            if gap['decision_ref'] is not None: raise ValueError('OPEN activation gap cannot carry acceptance decision')
            open_gaps.append(gid)
        else: opaque_ref(gap['decision_ref'],'gap.decision_ref')

    refs=unique_strings(record['source_refs'],'source_refs')
    for ref in refs: repository_ref(ref,root)

    review_due=as_of>=review_by or any(as_of>=x for x in gap_reviews)
    initial_due=as_of>=min(prereq_valid,initial_valid,withdrawal_valid) or as_of>=authority_valid
    authority_ok=activation['authority_status'] in {'APPROVED','CONDITIONAL'}
    post_due=activated_at is not None and (post['outcome']=='NOT_RUN' or (post_valid is not None and as_of>=post_valid))
    withdrawal_required=activated_at is not None and post['outcome'] in {'FAILED','UNKNOWN'}

    state=record['state']
    if state=='READY_FOR_CONTROLLED_ACTIVATION':
        if review_due or initial_due or not authority_ok or activated_at is not None or post['outcome']!='NOT_RUN' or withdrawal['status']!='TESTED_READY' or open_gaps:
            raise ValueError('READY_FOR_CONTROLLED_ACTIVATION prerequisites are not satisfied')
    elif state=='CURRENT_ACTIVATED':
        if review_due or initial_due or not authority_ok or activated_at is None or post['outcome']!='PASSED' or post_due or withdrawal['status']!='TESTED_READY' or open_gaps:
            raise ValueError('CURRENT_ACTIVATED evidence is incomplete or stale')
    elif state=='REVIEW_DUE':
        if not review_due: raise ValueError('REVIEW_DUE requires expired scope/gap review')
    elif state=='INITIAL_READINESS_DUE':
        if review_due or not initial_due: raise ValueError('INITIAL_READINESS_DUE requires current scope and stale prerequisite/readiness/authority evidence')
    elif state=='POST_ACTIVATION_DUE':
        if review_due or initial_due or not authority_ok or activated_at is None or not post_due or withdrawal_required:
            raise ValueError('POST_ACTIVATION_DUE requires activated scope and missing/stale nonfailed post-activation evidence')
    elif state=='WITHDRAWAL_REQUIRED':
        if review_due or initial_due or not authority_ok or not withdrawal_required or withdrawal['status']!='REQUIRED':
            raise ValueError('WITHDRAWAL_REQUIRED requires failed/unknown live verification and required withdrawal')
    elif state=='GAPS_OPEN':
        if review_due or initial_due or not authority_ok or activated_at is not None or post['outcome']!='NOT_RUN' or withdrawal['status']!='TESTED_READY' or not open_gaps:
            raise ValueError('GAPS_OPEN is reserved for pre-activation current evidence with unresolved gaps')
    elif state=='UNCERTAIN':
        pass

    return {
        'assurance_id':record['assurance_id'],'generation':record['generation'],'state':state,
        'activation_id':record['activation_id'],'site_ref':scope['site_ref'],
        'service_class_ref':scope['service_class_ref'],'platform_profile_ref':scope['platform_profile_ref'],
        'workload_scope_ref':scope['workload_scope_ref'],'exposure_profile_ref':scope['exposure_profile_ref'],
        'authority_status':activation['authority_status'],'activated_at':activated_at.isoformat() if activated_at else None,
        'post_activation_outcome':post['outcome'],'withdrawal_status':withdrawal['status'],
        'open_gap_ids':sorted(open_gaps)
    }

def validate(index,as_of=None,root=ROOT):
    if as_of is None: as_of=datetime.now(timezone.utc)
    if as_of.tzinfo is None: raise ValueError('Timezone-aware as_of required')
    as_of=as_of.astimezone(timezone.utc)
    if set(index)!=INDEX_KEYS: raise ValueError('Unexpected activation assurance-index fields')
    if index['format']!=FORMAT or index['status']!=STATUS: raise ValueError('Unsupported activation assurance format or authority boundary')
    rev=index['reviewed_source_revision']
    if not isinstance(rev,str) or not re.fullmatch(r'[0-9a-f]{40}',rev): raise ValueError('Reviewed source revision must be an exact Git SHA')
    recs=index['records']
    if not isinstance(recs,list) or len(recs)>512: raise ValueError('Activation assurance records must be a bounded list')
    ids=set(); acts=set(); out=[]
    for raw in recs:
        item=validate_record(raw,as_of,root)
        if item['assurance_id'] in ids: raise ValueError('Duplicate activation assurance ID')
        if item['activation_id'] in acts: raise ValueError('Duplicate active assurance for one activation ID')
        ids.add(item['assurance_id']); acts.add(item['activation_id']); out.append(item)
    return {
        'records':out,'record_count':len(out),
        'ready_for_controlled_activation_count':sum(x['state']=='READY_FOR_CONTROLLED_ACTIVATION' for x in out),
        'current_activated_count':sum(x['state']=='CURRENT_ACTIVATED' for x in out),
        'review_due_count':sum(x['state']=='REVIEW_DUE' for x in out),
        'initial_readiness_due_count':sum(x['state']=='INITIAL_READINESS_DUE' for x in out),
        'post_activation_due_count':sum(x['state']=='POST_ACTIVATION_DUE' for x in out),
        'withdrawal_required_count':sum(x['state']=='WITHDRAWAL_REQUIRED' for x in out),
        'gaps_open_count':sum(x['state']=='GAPS_OPEN' for x in out),
        'uncertain_count':sum(x['state']=='UNCERTAIN' for x in out)
    }

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--index',type=Path,default=INDEX); p.add_argument('--as-of')
    a=p.parse_args()
    try:
        as_of=instant(a.as_of,'as_of') if a.as_of else datetime.now(timezone.utc)
        s=validate(load(a.index),as_of)
        print(json.dumps({
            'status':'PASSED_PRODUCTION_ACTIVATION_ASSURANCE','as_of':as_of.isoformat(),
            **{k:v for k,v in s.items() if k!='records'},
            'may_release_quarantine':False,'may_change_exposure':False,'may_activate':False,
            'may_withdraw_sessions':False,'may_apply':False,'may_delete':False,
            'limits':[
                'A ready record is a prerequisite decision record, not permission to activate.',
                'G4 initial operating/recovery readiness must precede G3 production activation where applicable.',
                'Failed or unknown live verification requires controlled withdrawal rather than optimistic continuation.',
                'The repository validates exported evidence only and never changes production exposure.'
            ]
        },indent=2)); return 0
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({
            'status':'FAILED_PRODUCTION_ACTIVATION_ASSURANCE','reason':str(exc),
            'may_release_quarantine':False,'may_change_exposure':False,'may_activate':False,
            'may_withdraw_sessions':False,'may_apply':False,'may_delete':False
        },indent=2)); return 2

if __name__=='__main__': raise SystemExit(main())
