#!/usr/bin/env python3
"""Validate origin-specific shared-service reply-path assurance evidence.

This repository is not a router, service controller, firewall, entitlement authority,
or production network authority. Records contain opaque references to externally owned
service-binding and forwarding evidence. The checker never installs routes, changes
policy, grants service access, revokes bindings, or activates production.
"""
from __future__ import annotations
import argparse, json, re
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'sources/capabilities/service_reply_assurance_index.json'
FORMAT='portable-hosting-service-reply-assurance-index/1'
STATUS='EXPORTED_SERVICE_REPLY_EVIDENCE_NOT_ROUTING_AUTHORITY'
STATES={'CURRENT_QUALIFIED','REVIEW_DUE','PATH_TEST_DUE','BINDING_DUE','GAPS_OPEN','UNCERTAIN'}
FAMILIES={'IPV4','IPV6'}
GAP_STATES={'OPEN','ACCEPTED'}
ID=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{1,191}$')

INDEX_KEYS={'format','status','reviewed_source_revision','records'}
RECORD_KEYS={
    'assurance_id','generation','state','reply_id','scope',
    'binding','routing','failure','operations','residual_gaps','source_refs'
}
SCOPE_KEYS={
    'site_ref','service_class_ref','service_binding_ref','origin_context_ref',
    'service_endpoint_ref','address_family','owner_ref','accepted_at','review_by'
}
BINDING_KEYS={
    'service_profile_ref','endpoint_identity_ref','authentication_ref',
    'entitlement_ref','allowed_operation_ref','management_separation_ref',
    'binding_expiry_ref','revocation_test_ref','observed_at','valid_until'
}
ROUTING_KEYS={
    'forward_path_ref','reply_path_ref','origin_specific_return_ref',
    'return_route_owner_ref','security_edge_assurance_ref','native_forwarding_ref',
    'source_validation_ref','connected_route_review_ref','summary_route_review_ref',
    'nat_pbr_review_ref','alternate_interface_review_ref','no_transit_ref',
    'observed_at','valid_until'
}
FAILURE_KEYS={
    'healthy_control_ref','missing_reply_route_ref','unavailable_next_hop_ref',
    'edge_failure_ref','no_borrowed_default_ref','reverse_initiation_deny_ref',
    'recovery_ref','observed_at','valid_until'
}
OPERATIONS_KEYS={
    'availability_ref','telemetry_ref','service_loss_ref','survivor_capacity_ref',
    'version_lifecycle_ref','observed_at','valid_until'
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
        raise ValueError('Service-reply assurance index exceeds bounded size')
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
        raise ValueError('Service-reply assurance index must be an object')
    return value


def evidence_block(value,keys,label,as_of):
    if not isinstance(value,dict) or set(value)!=keys:
        raise ValueError(f'{label}: evidence shape invalid')
    for key in keys-{'observed_at','valid_until'}:
        opaque_ref(value[key],f'{label}.{key}')
    observed=instant(value['observed_at'],f'{label}.observed_at')
    valid=instant(value['valid_until'],f'{label}.valid_until')
    if observed>as_of or valid<=observed:
        raise ValueError(f'{label}: chronology invalid')
    return observed,valid


def validate_record(record,as_of,root=ROOT):
    if not isinstance(record,dict) or set(record)!=RECORD_KEYS:
        raise ValueError('Service-reply assurance record has unexpected or missing fields')
    identifier(record['assurance_id'],'assurance_id')
    identifier(record['reply_id'],'reply_id')
    positive_int(record['generation'],'generation')
    if record['state'] not in STATES:
        raise ValueError('Unknown service-reply assurance state')

    scope=record['scope']
    if not isinstance(scope,dict) or set(scope)!=SCOPE_KEYS:
        raise ValueError('Service-reply scope shape invalid')
    for k in ('site_ref','service_class_ref','service_binding_ref','origin_context_ref','service_endpoint_ref','owner_ref'):
        opaque_ref(scope[k],f'scope.{k}')
    if scope['address_family'] not in FAMILIES:
        raise ValueError('Unknown service-reply address family')
    accepted=instant(scope['accepted_at'],'scope.accepted_at')
    review_by=instant(scope['review_by'],'scope.review_by')
    if accepted>as_of or review_by<=accepted:
        raise ValueError('Service-reply scope chronology invalid')

    _,binding_valid=evidence_block(record['binding'],BINDING_KEYS,'binding',as_of)
    _,routing_valid=evidence_block(record['routing'],ROUTING_KEYS,'routing',as_of)
    _,failure_valid=evidence_block(record['failure'],FAILURE_KEYS,'failure',as_of)
    _,operations_valid=evidence_block(record['operations'],OPERATIONS_KEYS,'operations',as_of)

    gaps=record['residual_gaps']
    if not isinstance(gaps,list) or len(gaps)>1024:
        raise ValueError('Residual service-reply gaps must be a bounded list')
    gap_ids=set(); open_gaps=[]; gap_reviews=[]
    for gap in gaps:
        if not isinstance(gap,dict) or set(gap)!=GAP_KEYS:
            raise ValueError('Residual service-reply gap shape invalid')
        gid=identifier(gap['gap_id'],'gap_id')
        if gid in gap_ids:
            raise ValueError('Duplicate residual service-reply gap ID')
        gap_ids.add(gid)
        if gap['status'] not in GAP_STATES:
            raise ValueError('Unknown residual service-reply gap state')
        opaque_ref(gap['owner_ref'],'gap.owner_ref')
        opaque_ref(gap['treatment_ref'],'gap.treatment_ref')
        gr=instant(gap['review_by'],'gap.review_by')
        gap_reviews.append(gr)
        if gap['status']=='OPEN':
            if gap['decision_ref'] is not None:
                raise ValueError('OPEN service-reply gap cannot carry acceptance decision')
            open_gaps.append(gid)
        else:
            opaque_ref(gap['decision_ref'],'gap.decision_ref')

    refs=unique_strings(record['source_refs'],'source_refs')
    for ref in refs:
        repository_ref(ref,root)

    review_due=as_of>=review_by or any(as_of>=x for x in gap_reviews)
    path_due=as_of>=min(routing_valid,failure_valid)
    binding_due=as_of>=min(binding_valid,operations_valid)

    state=record['state']
    if state=='CURRENT_QUALIFIED':
        if review_due or path_due or binding_due or open_gaps:
            raise ValueError('CURRENT_QUALIFIED service-reply evidence is stale or incomplete')
    elif state=='REVIEW_DUE':
        if not review_due:
            raise ValueError('REVIEW_DUE requires expired scope/gap review')
    elif state=='PATH_TEST_DUE':
        if review_due or not path_due:
            raise ValueError('PATH_TEST_DUE requires current review and stale routing/failure evidence')
    elif state=='BINDING_DUE':
        if review_due or path_due or not binding_due:
            raise ValueError('BINDING_DUE requires current path evidence and stale binding/operations evidence')
    elif state=='GAPS_OPEN':
        if review_due or path_due or binding_due or not open_gaps:
            raise ValueError('GAPS_OPEN requires current evidence and at least one OPEN residual gap')
    elif state=='UNCERTAIN':
        pass

    return {
        'assurance_id':record['assurance_id'],
        'generation':record['generation'],
        'state':state,
        'reply_id':record['reply_id'],
        'site_ref':scope['site_ref'],
        'service_class_ref':scope['service_class_ref'],
        'service_binding_ref':scope['service_binding_ref'],
        'origin_context_ref':scope['origin_context_ref'],
        'service_endpoint_ref':scope['service_endpoint_ref'],
        'address_family':scope['address_family'],
        'review_by':review_by.isoformat(),
        'open_gap_ids':sorted(open_gaps),
    }


def validate(index,as_of=None,root=ROOT):
    if as_of is None:
        as_of=datetime.now(timezone.utc)
    if not isinstance(as_of,datetime) or as_of.tzinfo is None:
        raise ValueError('Timezone-aware as_of required')
    as_of=as_of.astimezone(timezone.utc)
    if set(index)!=INDEX_KEYS:
        raise ValueError('Unexpected service-reply assurance-index fields')
    if index['format']!=FORMAT or index['status']!=STATUS:
        raise ValueError('Unsupported service-reply assurance format or authority boundary')
    revision=index['reviewed_source_revision']
    if not isinstance(revision,str) or not re.fullmatch(r'[0-9a-f]{40}',revision):
        raise ValueError('Reviewed source revision must be an exact Git SHA')
    records=index['records']
    if not isinstance(records,list) or len(records)>1024:
        raise ValueError('Service-reply assurance records must be a bounded list')
    ids=set(); reply_ids=set(); out=[]
    for raw in records:
        item=validate_record(raw,as_of,root)
        if item['assurance_id'] in ids:
            raise ValueError('Duplicate service-reply assurance ID')
        if item['reply_id'] in reply_ids:
            raise ValueError('Duplicate active assurance for one service-reply binding')
        ids.add(item['assurance_id']); reply_ids.add(item['reply_id']); out.append(item)
    return {
        'records':out,'record_count':len(out),
        'current_qualified_count':sum(x['state']=='CURRENT_QUALIFIED' for x in out),
        'review_due_count':sum(x['state']=='REVIEW_DUE' for x in out),
        'path_test_due_count':sum(x['state']=='PATH_TEST_DUE' for x in out),
        'binding_due_count':sum(x['state']=='BINDING_DUE' for x in out),
        'gaps_open_count':sum(x['state']=='GAPS_OPEN' for x in out),
        'uncertain_count':sum(x['state']=='UNCERTAIN' for x in out),
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
            'status':'PASSED_SERVICE_REPLY_ASSURANCE','as_of':as_of.isoformat(),
            **{k:v for k,v in summary.items() if k!='records'},
            'may_create_route':False,'may_change_service_binding':False,
            'may_change_policy':False,'may_revoke_binding':False,
            'may_change_service':False,'may_apply':False,'may_activate':False,
            'limits':[
                'A reachable shared service does not establish origin-specific reply ownership.',
                'A flow observed on the intended edge does not prove alternate paths are absent.',
                'Service reachability does not grant administrative or foreign-tenant entitlement.',
                'The repository validates exported evidence only and never changes service routing.'
            ]
        },indent=2)); return 0
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({
            'status':'FAILED_SERVICE_REPLY_ASSURANCE','reason':str(exc),
            'may_create_route':False,'may_change_service_binding':False,
            'may_change_policy':False,'may_revoke_binding':False,
            'may_change_service':False,'may_apply':False,'may_activate':False
        },indent=2)); return 2


if __name__=='__main__':
    raise SystemExit(main())
