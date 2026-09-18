#!/usr/bin/env python3
"""Validate exported control-allocation, inheritance and external-interface evidence.

This repository is not a control-assessment system, authorizing authority, personnel
system, facility authority, maintenance system, or risk register. Records contain
opaque references to externally owned decisions and evidence. This checker never
selects controls, accepts inheritance, closes residual risk, applies infrastructure,
or authorizes production.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'sources/capabilities/control_inheritance_assurance_index.json'
FORMAT='portable-hosting-control-inheritance-assurance-index/1'
STATUS='EXPORTED_CONTROL_ALLOCATION_EVIDENCE_NOT_AUTHORIZATION_AUTHORITY'
STATES={'CURRENT_REVIEWED','REVIEW_DUE','GAPS_OPEN','UNCERTAIN'}
DISPOSITIONS={'PROVIDER','TENANT','SHARED','INHERITED'}
GAP_STATES={'OPEN','ACCEPTED'}
INTERFACES={
    'PHYSICAL_ENVIRONMENTAL',
    'PERSONNEL_PRIVILEGED_ROLES',
    'MAINTENANCE_SUPPORT',
    'TRAINING_OPERATIONS',
    'DATA_PRIVACY_LOCATION',
    'ASSESSMENT_AUTHORIZATION',
}
ID=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{1,191}$')
INDEX_KEYS={'format','status','reviewed_source_revision','records'}
RECORD_KEYS={
    'assurance_id','generation','state','request_id','wsd_engineering_ref',
    'scope','review','controls','external_interfaces','residual_gaps','source_refs'
}
SCOPE_KEYS={
    'site_ref','service_class_ref','platform_profile_ref',
    'control_catalogue_ref','control_selection_ref'
}
REVIEW_KEYS={'allocation_decision_ref','accepted_at','review_by','accountable_role'}
CONTROL_KEYS={
    'control_id','parameter_decision_ref','disposition','implementation_ref',
    'evidence_ref','evidence_scope_ref','owner_refs','inherited_service_ref',
    'observed_at','evidence_valid_until'
}
EXTERNAL_KEYS={
    'interface','owner_ref','evidence_ref','applicability_ref',
    'observed_at','evidence_valid_until'
}
GAP_KEYS={
    'gap_id','related_control_ids','status','owner_role','treatment_ref','decision_ref'
}


def bounded(value,label,limit=512):
    if (not isinstance(value,str) or not value.strip() or len(value)>limit
            or any(ord(c)<32 or ord(c)==127 for c in value)):
        raise ValueError(f'{label}: bounded nonempty text required')
    return value


def identifier(value,label):
    bounded(value,label,192)
    if not ID.fullmatch(value):
        raise ValueError(f'{label}: invalid identifier')
    return value


def positive_int(value,label):
    if type(value) is not int or value<1:
        raise ValueError(f'{label}: positive integer required')
    return value


def instant(value,label):
    bounded(value,label,64)
    dt=datetime.fromisoformat(value.replace('Z','+00:00'))
    if dt.tzinfo is None:
        raise ValueError(f'{label}: timezone required')
    return dt.astimezone(timezone.utc)


def repository_ref(value,root=ROOT):
    bounded(value,'repository reference')
    p=Path(value)
    if p.is_absolute() or '..' in p.parts or '\\' in value or ':' in value:
        raise ValueError('Repository reference must be normalized and relative')
    if not (root/p).exists():
        raise ValueError(f'Repository reference does not exist: {value}')
    return value


def opaque_ref(value,label):
    bounded(value,label,256)
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.:-]{1,255}',value):
        raise ValueError(f'{label}: opaque external reference required')
    return value


def unique_strings(value,label,*,allow_empty=False,maximum=128):
    if not isinstance(value,list) or len(value)>maximum or (not allow_empty and not value):
        raise ValueError(f'{label}: bounded list required')
    if any(not isinstance(x,str) or not x.strip() for x in value):
        raise ValueError(f'{label}: nonempty strings required')
    if len(value)!=len(set(value)):
        raise ValueError(f'{label}: duplicates not allowed')
    return value


def load(path:Path=INDEX):
    with path.open('rb') as stream:
        raw=stream.read(1024*1024+1)
    if len(raw)>1024*1024:
        raise ValueError('Control-inheritance assurance index exceeds bounded size')
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
        raise ValueError('Control-inheritance assurance index must be an object')
    return value


def validate_record(record,*,as_of,root=ROOT):
    if not isinstance(record,dict) or set(record)!=RECORD_KEYS:
        raise ValueError('Control-inheritance assurance record has unexpected or missing fields')
    identifier(record['assurance_id'],'assurance_id')
    identifier(record['request_id'],'request_id')
    positive_int(record['generation'],'generation')
    if record['state'] not in STATES:
        raise ValueError('Unknown control-inheritance assurance state')
    repository_ref(record['wsd_engineering_ref'],root)

    scope=record['scope']
    if not isinstance(scope,dict) or set(scope)!=SCOPE_KEYS:
        raise ValueError('Exact site/service/platform/control scope is required')
    for key,value in scope.items():
        opaque_ref(value,f'scope.{key}')

    review=record['review']
    if not isinstance(review,dict) or set(review)!=REVIEW_KEYS:
        raise ValueError('Control-allocation review shape invalid')
    opaque_ref(review['allocation_decision_ref'],'allocation_decision_ref')
    accepted=instant(review['accepted_at'],'accepted_at')
    review_by=instant(review['review_by'],'review_by')
    bounded(review['accountable_role'],'accountable_role')
    if accepted>as_of or review_by<=accepted:
        raise ValueError('Control-allocation review chronology invalid')

    controls=record['controls']
    if not isinstance(controls,list) or not controls or len(controls)>2048:
        raise ValueError('At least one bounded control allocation is required')
    control_ids=set()
    normalized_controls=[]
    control_valid_until=[]
    for item in controls:
        if not isinstance(item,dict) or set(item)!=CONTROL_KEYS:
            raise ValueError('Control allocation has unexpected or missing fields')
        control_id=identifier(item['control_id'],'control_id')
        if control_id in control_ids:
            raise ValueError('Duplicate control allocation ID')
        control_ids.add(control_id)
        opaque_ref(item['parameter_decision_ref'],'parameter_decision_ref')
        if item['disposition'] not in DISPOSITIONS:
            raise ValueError('Unknown control responsibility disposition')
        for key in ('implementation_ref','evidence_ref','evidence_scope_ref'):
            opaque_ref(item[key],key)
        owners=unique_strings(item['owner_refs'],'owner_refs',maximum=8)
        for ref in owners:
            opaque_ref(ref,'owner_ref')
        inherited=item['inherited_service_ref']
        if item['disposition']=='INHERITED':
            opaque_ref(inherited,'inherited_service_ref')
        elif inherited is not None:
            raise ValueError('Only INHERITED controls may carry inherited_service_ref')
        observed=instant(item['observed_at'],'control.observed_at')
        valid_until=instant(item['evidence_valid_until'],'control.evidence_valid_until')
        if observed>as_of or valid_until<=observed:
            raise ValueError('Control evidence chronology invalid')
        control_valid_until.append(valid_until)
        normalized_controls.append({
            'control_id':control_id,
            'disposition':item['disposition'],
            'evidence_valid_until':valid_until.isoformat(),
        })

    external=record['external_interfaces']
    if not isinstance(external,list) or len(external)!=len(INTERFACES):
        raise ValueError('All required organizational/external interfaces must be represented exactly once')
    seen_interfaces=set()
    external_valid_until=[]
    for item in external:
        if not isinstance(item,dict) or set(item)!=EXTERNAL_KEYS:
            raise ValueError('External-interface evidence shape invalid')
        interface=item['interface']
        if interface not in INTERFACES or interface in seen_interfaces:
            raise ValueError('External-interface set is missing, duplicated or unknown')
        seen_interfaces.add(interface)
        for key in ('owner_ref','evidence_ref','applicability_ref'):
            opaque_ref(item[key],f'{interface}.{key}')
        observed=instant(item['observed_at'],f'{interface}.observed_at')
        valid_until=instant(item['evidence_valid_until'],f'{interface}.evidence_valid_until')
        if observed>as_of or valid_until<=observed:
            raise ValueError('External-interface evidence chronology invalid')
        external_valid_until.append(valid_until)
    if seen_interfaces!=INTERFACES:
        raise ValueError('All required organizational/external interfaces must be represented')

    gaps=record['residual_gaps']
    if not isinstance(gaps,list) or len(gaps)>1024:
        raise ValueError('Residual gaps must be a bounded list')
    gap_ids=set()
    open_gaps=[]
    for gap in gaps:
        if not isinstance(gap,dict) or set(gap)!=GAP_KEYS:
            raise ValueError('Residual-gap record has unexpected or missing fields')
        gap_id=identifier(gap['gap_id'],'gap_id')
        if gap_id in gap_ids:
            raise ValueError('Duplicate residual-gap ID')
        gap_ids.add(gap_id)
        related=unique_strings(gap['related_control_ids'],'related_control_ids')
        for control_id in related:
            identifier(control_id,'related_control_id')
            if control_id not in control_ids:
                raise ValueError('Residual gap references an unallocated control')
        if gap['status'] not in GAP_STATES:
            raise ValueError('Unknown residual-gap state')
        bounded(gap['owner_role'],'residual_gap.owner_role')
        opaque_ref(gap['treatment_ref'],'residual_gap.treatment_ref')
        if gap['status']=='OPEN':
            if gap['decision_ref'] is not None:
                raise ValueError('OPEN residual gap cannot carry an acceptance decision')
            open_gaps.append(gap_id)
        else:
            opaque_ref(gap['decision_ref'],'residual_gap.decision_ref')

    refs=unique_strings(record['source_refs'],'source_refs')
    for ref in refs:
        repository_ref(ref,root)

    stale=(as_of>=review_by or
           any(as_of>=value for value in control_valid_until) or
           any(as_of>=value for value in external_valid_until))
    if record['state']=='CURRENT_REVIEWED':
        if stale:
            raise ValueError('CURRENT_REVIEWED record has expired review or evidence')
        if open_gaps:
            raise ValueError('CURRENT_REVIEWED record cannot contain OPEN residual gaps')
    elif record['state']=='REVIEW_DUE':
        if not stale:
            raise ValueError('REVIEW_DUE requires expired review or evidence')
    elif record['state']=='GAPS_OPEN':
        if stale:
            raise ValueError('GAPS_OPEN is reserved for current evidence with unresolved residual gaps')
        if not open_gaps:
            raise ValueError('GAPS_OPEN requires at least one OPEN residual gap')
    elif record['state']=='UNCERTAIN':
        pass

    return {
        'assurance_id':record['assurance_id'],
        'generation':record['generation'],
        'state':record['state'],
        'request_id':record['request_id'],
        'wsd_engineering_ref':record['wsd_engineering_ref'],
        'scope':dict(scope),
        'control_ids':sorted(control_ids),
        'control_count':len(control_ids),
        'open_gap_ids':sorted(open_gaps),
        'review_by':review_by.isoformat(),
        'unresolved':record['state']=='UNCERTAIN',
    }


def validate(index,*,as_of=None,root=ROOT):
    if as_of is None:
        as_of=datetime.now(timezone.utc)
    if not isinstance(as_of,datetime) or as_of.tzinfo is None:
        raise ValueError('Timezone-aware as_of required')
    as_of=as_of.astimezone(timezone.utc)
    if set(index)!=INDEX_KEYS:
        raise ValueError('Unexpected control-inheritance assurance-index fields')
    if index['format']!=FORMAT or index['status']!=STATUS:
        raise ValueError('Unsupported control-inheritance assurance format or authority boundary')
    rev=index['reviewed_source_revision']
    if not isinstance(rev,str) or not re.fullmatch(r'[0-9a-f]{40}',rev):
        raise ValueError('Reviewed source revision must be an exact Git SHA')
    records=index['records']
    if not isinstance(records,list) or len(records)>1024:
        raise ValueError('Control-inheritance assurance records must be a bounded list')
    ids=set()
    request_ids=set()
    out=[]
    for raw in records:
        item=validate_record(raw,as_of=as_of,root=root)
        if item['assurance_id'] in ids:
            raise ValueError('Duplicate control-inheritance assurance ID')
        if item['request_id'] in request_ids:
            raise ValueError('Duplicate active control-inheritance assurance for one request')
        ids.add(item['assurance_id'])
        request_ids.add(item['request_id'])
        out.append(item)
    return {
        'records':out,
        'record_count':len(out),
        'current_reviewed_count':sum(x['state']=='CURRENT_REVIEWED' for x in out),
        'review_due_count':sum(x['state']=='REVIEW_DUE' for x in out),
        'gaps_open_count':sum(x['state']=='GAPS_OPEN' for x in out),
        'unresolved_count':sum(x['unresolved'] for x in out),
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--index',type=Path,default=INDEX)
    p.add_argument('--as-of',help='ISO-8601 review instant; defaults to current UTC')
    a=p.parse_args()
    try:
        as_of=instant(a.as_of,'as_of') if a.as_of else datetime.now(timezone.utc)
        summary=validate(load(a.index),as_of=as_of)
        print(json.dumps({
            'status':'PASSED_EXPORTED_CONTROL_INHERITANCE_ASSURANCE',
            'as_of':as_of.isoformat(),
            **{k:v for k,v in summary.items() if k!='records'},
            'may_select_controls':False,
            'may_accept_inheritance':False,
            'may_close_residual_gap':False,
            'may_issue_authorization':False,
            'may_apply':False,
            'may_activate':False,
            'limits':[
                'A control-family crosswalk is not a completed control assessment.',
                'Inherited evidence must remain scoped to the actual service, site, version, tenant scope and review interval.',
                'Residual-gap acceptance and formal authorization remain attributable external decisions.',
                'The repository validates exported evidence only and never changes infrastructure or authoritative control records.'
            ]
        },indent=2))
        return 0
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({
            'status':'FAILED_EXPORTED_CONTROL_INHERITANCE_ASSURANCE',
            'reason':str(exc),
            'may_select_controls':False,
            'may_accept_inheritance':False,
            'may_close_residual_gap':False,
            'may_issue_authorization':False,
            'may_apply':False,
            'may_activate':False
        },indent=2))
        return 2


if __name__=='__main__':
    raise SystemExit(main())
