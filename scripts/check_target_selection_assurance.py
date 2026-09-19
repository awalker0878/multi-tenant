#!/usr/bin/env python3
"""Validate exported actual-target selection evidence for a restricted native campaign.

This repository is not a site selector, platform owner, credential broker, change
authority, or native target controller. Records contain opaque references to an
externally selected site/cell, installed implementation tuple and permitted disposable
campaign scope. The checker never selects a target, grants target contact, retrieves
credentials, changes infrastructure, or authorizes production.
"""
from __future__ import annotations
import argparse, json, re
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'sources/capabilities/target_selection_assurance_index.json'
FORMAT='portable-hosting-target-selection-assurance-index/1'
STATUS='EXPORTED_TARGET_SELECTION_EVIDENCE_NOT_TARGET_CONTACT_AUTHORITY'
STATES={'CURRENT_SELECTED','REVIEW_DUE','CONTACT_AUTHORITY_DUE','GAPS_OPEN','UNCERTAIN'}
PLATFORMS={'NUTANIX','VMWARE_NSX','OPENSTACK'}
GAP_STATES={'OPEN','ACCEPTED'}
ID=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{1,191}$')

INDEX_KEYS={'format','status','reviewed_source_revision','records'}
RECORD_KEYS={
    'assurance_id','generation','state','selection_id','scope',
    'implementation_tuple','campaign','residual_gaps','source_refs'
}
SCOPE_KEYS={
    'site_ref','cell_ref','campaign_scope_ref','change_authority_ref',
    'target_contact_authority_ref','target_contact_valid_until',
    'stop_authority_ref','owner_ref','selected_at','review_by'
}
TUPLE_KEYS={
    'platform_family','product_tuple_id','hardware_inventory_ref',
    'product_api_provider_ref','feature_entitlement_ref',
    'version_source_provenance_ref','security_edge_realization_ref',
    'management_oob_ref','network_backend_ref','storage_backend_ref'
}
CAMPAIGN_KEYS={
    'qualification_campaign_ref','native_api_scope_ref','observer_scope_ref',
    'writer_scope_ref','credential_custody_ref','evidence_workspace_ref',
    'data_restriction_ref','permitted_operations_ref','prohibited_operations_ref',
    'cleanup_ref','contact_window_ref','production_authority_status'
}
GAP_KEYS={'gap_id','status','owner_ref','treatment_ref','decision_ref','review_by'}

def bounded(v,label,limit=1024):
    if not isinstance(v,str) or not v.strip() or len(v)>limit or any(ord(c)<32 or ord(c)==127 for c in v):
        raise ValueError(f'{label}: bounded nonempty text required')
    return v

def identifier(v,label):
    bounded(v,label,192)
    if not ID.fullmatch(v):
        raise ValueError(f'{label}: invalid identifier')
    return v

def positive_int(v,label):
    if type(v) is not int or v<1:
        raise ValueError(f'{label}: positive integer required')
    return v

def instant(v,label):
    bounded(v,label,64)
    dt=datetime.fromisoformat(v.replace('Z','+00:00'))
    if dt.tzinfo is None:
        raise ValueError(f'{label}: timezone required')
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
    if not (root/p).exists():
        raise ValueError(f'Repository reference does not exist: {v}')
    return v

def unique_strings(v,label,allow_empty=False,maximum=128):
    if not isinstance(v,list) or len(v)>maximum or (not allow_empty and not v):
        raise ValueError(f'{label}: bounded list required')
    if any(not isinstance(x,str) or not x.strip() for x in v):
        raise ValueError(f'{label}: nonempty strings required')
    if len(v)!=len(set(v)):
        raise ValueError(f'{label}: duplicates not allowed')
    return v

def load(path:Path=INDEX):
    with path.open('rb') as s:
        raw=s.read(1024*1024+1)
    if len(raw)>1024*1024:
        raise ValueError('Target-selection assurance index exceeds bounded size')
    def pairs(items):
        out={}
        for k,v in items:
            if k in out:
                raise ValueError('Duplicate JSON property')
            out[k]=v
        return out
    def reject(_):
        raise ValueError('Non-finite JSON number')
    value=json.loads(raw,object_pairs_hook=pairs,parse_constant=reject)
    if not isinstance(value,dict):
        raise ValueError('Target-selection assurance index must be an object')
    return value

def validate_record(record,as_of,root=ROOT):
    if not isinstance(record,dict) or set(record)!=RECORD_KEYS:
        raise ValueError('Target-selection assurance record has unexpected or missing fields')
    identifier(record['assurance_id'],'assurance_id')
    identifier(record['selection_id'],'selection_id')
    positive_int(record['generation'],'generation')
    if record['state'] not in STATES:
        raise ValueError('Unknown target-selection assurance state')

    scope=record['scope']
    if not isinstance(scope,dict) or set(scope)!=SCOPE_KEYS:
        raise ValueError('Target-selection scope shape invalid')
    for key in ('site_ref','cell_ref','campaign_scope_ref','change_authority_ref',
                'target_contact_authority_ref','stop_authority_ref','owner_ref'):
        opaque_ref(scope[key],f'scope.{key}')
    selected=instant(scope['selected_at'],'scope.selected_at')
    review_by=instant(scope['review_by'],'scope.review_by')
    contact_valid=instant(scope['target_contact_valid_until'],'scope.target_contact_valid_until')
    if selected>as_of or review_by<=selected or contact_valid<=selected:
        raise ValueError('Target-selection chronology invalid')

    target=record['implementation_tuple']
    if not isinstance(target,dict) or set(target)!=TUPLE_KEYS:
        raise ValueError('Exact implementation tuple selection shape invalid')
    if target['platform_family'] not in PLATFORMS:
        raise ValueError('Unknown selected platform family')
    identifier(target['product_tuple_id'],'product_tuple_id')
    for key in TUPLE_KEYS-{'platform_family','product_tuple_id'}:
        opaque_ref(target[key],f'implementation_tuple.{key}')

    campaign=record['campaign']
    if not isinstance(campaign,dict) or set(campaign)!=CAMPAIGN_KEYS:
        raise ValueError('Restricted native campaign shape invalid')
    for key in CAMPAIGN_KEYS-{'production_authority_status'}:
        opaque_ref(campaign[key],f'campaign.{key}')
    if campaign['production_authority_status']!='NOT_ISSUED':
        raise ValueError('Restricted native target selection cannot carry production authority')

    gaps=record['residual_gaps']
    if not isinstance(gaps,list) or len(gaps)>1024:
        raise ValueError('Residual target-selection gaps must be a bounded list')
    gap_ids=set(); open_gaps=[]; gap_reviews=[]
    for gap in gaps:
        if not isinstance(gap,dict) or set(gap)!=GAP_KEYS:
            raise ValueError('Residual target-selection gap shape invalid')
        gid=identifier(gap['gap_id'],'gap_id')
        if gid in gap_ids:
            raise ValueError('Duplicate residual target-selection gap ID')
        gap_ids.add(gid)
        if gap['status'] not in GAP_STATES:
            raise ValueError('Unknown residual target-selection gap state')
        opaque_ref(gap['owner_ref'],'gap.owner_ref')
        opaque_ref(gap['treatment_ref'],'gap.treatment_ref')
        gr=instant(gap['review_by'],'gap.review_by')
        gap_reviews.append(gr)
        if gap['status']=='OPEN':
            if gap['decision_ref'] is not None:
                raise ValueError('OPEN target-selection gap cannot carry acceptance decision')
            open_gaps.append(gid)
        else:
            opaque_ref(gap['decision_ref'],'gap.decision_ref')

    refs=unique_strings(record['source_refs'],'source_refs')
    for ref in refs:
        repository_ref(ref,root)

    review_due=as_of>=review_by or any(as_of>=x for x in gap_reviews)
    contact_due=as_of>=contact_valid

    state=record['state']
    if state=='CURRENT_SELECTED':
        if review_due or contact_due or open_gaps:
            raise ValueError('CURRENT_SELECTED target evidence is stale or incomplete')
    elif state=='REVIEW_DUE':
        if not review_due:
            raise ValueError('REVIEW_DUE requires expired selection/gap review')
    elif state=='CONTACT_AUTHORITY_DUE':
        if review_due or not contact_due:
            raise ValueError('CONTACT_AUTHORITY_DUE requires current selection review and expired target-contact authority')
    elif state=='GAPS_OPEN':
        if review_due or contact_due or not open_gaps:
            raise ValueError('GAPS_OPEN requires current selection/contact evidence and at least one OPEN residual gap')
    elif state=='UNCERTAIN':
        pass

    return {
        'assurance_id':record['assurance_id'],
        'generation':record['generation'],
        'state':state,
        'selection_id':record['selection_id'],
        'site_ref':scope['site_ref'],
        'cell_ref':scope['cell_ref'],
        'campaign_scope_ref':scope['campaign_scope_ref'],
        'platform_family':target['platform_family'],
        'product_tuple_id':target['product_tuple_id'],
        'security_edge_realization_ref':target['security_edge_realization_ref'],
        'review_by':review_by.isoformat(),
        'target_contact_valid_until':contact_valid.isoformat(),
        'open_gap_ids':sorted(open_gaps),
    }

def validate(index,as_of=None,root=ROOT):
    if as_of is None:
        as_of=datetime.now(timezone.utc)
    if not isinstance(as_of,datetime) or as_of.tzinfo is None:
        raise ValueError('Timezone-aware as_of required')
    as_of=as_of.astimezone(timezone.utc)
    if set(index)!=INDEX_KEYS:
        raise ValueError('Unexpected target-selection assurance-index fields')
    if index['format']!=FORMAT or index['status']!=STATUS:
        raise ValueError('Unsupported target-selection assurance format or authority boundary')
    revision=index['reviewed_source_revision']
    if not isinstance(revision,str) or not re.fullmatch(r'[0-9a-f]{40}',revision):
        raise ValueError('Reviewed source revision must be an exact Git SHA')
    records=index['records']
    if not isinstance(records,list) or len(records)>128:
        raise ValueError('Target-selection assurance records must be a bounded list')
    ids=set(); selections=set(); out=[]
    for raw in records:
        item=validate_record(raw,as_of,root)
        if item['assurance_id'] in ids:
            raise ValueError('Duplicate target-selection assurance ID')
        if item['selection_id'] in selections:
            raise ValueError('Duplicate active assurance for one target selection')
        ids.add(item['assurance_id']); selections.add(item['selection_id']); out.append(item)
    return {
        'records':out,'record_count':len(out),
        'current_selected_count':sum(x['state']=='CURRENT_SELECTED' for x in out),
        'review_due_count':sum(x['state']=='REVIEW_DUE' for x in out),
        'contact_authority_due_count':sum(x['state']=='CONTACT_AUTHORITY_DUE' for x in out),
        'gaps_open_count':sum(x['state']=='GAPS_OPEN' for x in out),
        'uncertain_count':sum(x['state']=='UNCERTAIN' for x in out)
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--index',type=Path,default=INDEX)
    p.add_argument('--as-of')
    a=p.parse_args()
    try:
        as_of=instant(a.as_of,'as_of') if a.as_of else datetime.now(timezone.utc)
        summary=validate(load(a.index),as_of)
        print(json.dumps({
            'status':'PASSED_TARGET_SELECTION_ASSURANCE','as_of':as_of.isoformat(),
            **{k:v for k,v in summary.items() if k!='records'},
            'may_select_target':False,'may_contact_target':False,
            'may_retrieve_credentials':False,'may_run_native_tests':False,
            'may_apply':False,'may_activate':False,
            'limits':[
                'A current record captures an externally selected target; it does not select one.',
                'Target-contact authority is evidence owned outside this repository and is not executed by CI.',
                'Production authority remains NOT_ISSUED for the restricted qualification campaign.',
                'The repository stores opaque scope/tuple references rather than credentials or target endpoint secrets.'
            ]
        },indent=2)); return 0
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({
            'status':'FAILED_TARGET_SELECTION_ASSURANCE','reason':str(exc),
            'may_select_target':False,'may_contact_target':False,
            'may_retrieve_credentials':False,'may_run_native_tests':False,
            'may_apply':False,'may_activate':False
        },indent=2)); return 2

if __name__=='__main__':
    raise SystemExit(main())
