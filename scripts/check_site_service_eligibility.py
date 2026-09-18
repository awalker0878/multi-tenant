#!/usr/bin/env python3
"""Evaluate site/cell/service-class capacity envelopes without reserving anything.

This is the architecture's Step-2 engineering precheck after platform-family
qualification. It returns matching envelopes only. It never chooses a winner,
creates a reservation, allocates an address, contacts infrastructure, or authorizes
activation.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from scripts import check_site_service_capacity as capacity
from scripts import check_platform_qualification as qualification

FORMAT='portable-hosting-site-service-demand/1'
STATUS='PLANNING_ONLY_NOT_AUTHORIZED'
HOLD='HOLD_NO_ELIGIBLE_SITE_SERVICE_ENVELOPE'
MATCH='SITE_SERVICE_ENVELOPE_MATCH_RESERVATION_NOT_CREATED'
REQUEST_KEYS={
    'format','status','request_id','wsd_engineering_ref','candidate_platforms',
    'candidate_sites','candidate_cells','candidate_service_classes',
    'required_assurance_profile','required_profile_refs','capacity_demands',
    'production_authority','source_refs'
}
DEMAND_KEYS={'id','unit','quantity','quota_remaining'}
ID=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{1,191}$')


def bounded(value,label,limit=512):
    if (not isinstance(value,str) or not value.strip() or len(value)>limit
            or any(ord(c)<32 or ord(c)==127 for c in value)):
        raise ValueError(f'{label}: bounded nonempty text required')
    return value


def unique_strings(value,label,*,allow_empty=False,maximum=64):
    if not isinstance(value,list) or len(value)>maximum or (not allow_empty and not value):
        raise ValueError(f'{label}: bounded list required')
    if any(not isinstance(x,str) or not x.strip() for x in value):
        raise ValueError(f'{label}: nonempty strings required')
    if len(value)!=len(set(value)):
        raise ValueError(f'{label}: duplicate values not allowed')
    return value


def number(value,label):
    if not isinstance(value,str) or not value or len(value)>64:
        raise ValueError(f'{label}: decimal string required')
    try:
        n=Decimal(value)
    except InvalidOperation:
        raise ValueError(f'{label}: invalid decimal') from None
    if not n.is_finite() or n<0:
        raise ValueError(f'{label}: nonnegative finite decimal required')
    return n


def repository_ref(value):
    bounded(value,'repository reference')
    p=Path(value)
    if p.is_absolute() or '..' in p.parts or '\\' in value or ':' in value:
        raise ValueError('Repository reference must be normalized and relative')
    if not (ROOT/p).exists():
        raise ValueError(f'Repository reference does not exist: {value}')
    return value


def load_request(path:Path):
    with path.open('rb') as stream:
        raw=stream.read(1024*1024+1)
    if len(raw)>1024*1024:
        raise ValueError('Request exceeds bounded size')
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('Duplicate JSON property')
            result[key]=value
        return result
    def reject(_):raise ValueError('Non-finite JSON number')
    value=json.loads(raw,object_pairs_hook=pairs,parse_constant=reject)
    if not isinstance(value,dict):raise ValueError('Request must be a JSON object')
    return value


def validate_request(request,index_summary):
    if set(request)!=REQUEST_KEYS:
        raise ValueError('Unexpected or missing site-service demand fields')
    if request['format']!=FORMAT or request['status']!=STATUS:
        raise ValueError('Unsupported request format or authority boundary')
    if not isinstance(request['request_id'],str) or not ID.fullmatch(request['request_id']):
        raise ValueError('Invalid request identity')
    repository_ref(request['wsd_engineering_ref'])
    refs=unique_strings(request['source_refs'],'source_refs')
    for ref in refs:repository_ref(ref)
    if request['wsd_engineering_ref'] not in refs:
        raise ValueError('WSD engineering reference must be in source_refs')

    platforms=unique_strings(request['candidate_platforms'],'candidate_platforms')
    if any(x not in capacity.PLATFORMS for x in platforms):
        raise ValueError('Unknown candidate platform family')
    for key in ('candidate_sites','candidate_cells','candidate_service_classes'):
        values=unique_strings(request[key],key,allow_empty=True)
        for value in values:
            if not ID.fullmatch(value):raise ValueError(f'{key}: invalid identifier')

    assurance=request['required_assurance_profile']
    if assurance is not None:bounded(assurance,'required_assurance_profile',160)
    profiles=request['required_profile_refs']
    if not isinstance(profiles,dict) or set(profiles)!=capacity.PROFILE_KEYS:
        raise ValueError('Exact required profile references are required')
    for key,value in profiles.items():bounded(value,f'required_profile_refs.{key}')

    demands=request['capacity_demands']
    if not isinstance(demands,list) or not demands or len(demands)>128:
        raise ValueError('At least one bounded capacity demand is required')
    seen=set()
    for demand in demands:
        if not isinstance(demand,dict) or set(demand)!=DEMAND_KEYS:
            raise ValueError('Capacity demand shape invalid')
        if not isinstance(demand['id'],str) or not ID.fullmatch(demand['id']) or demand['id'] in seen:
            raise ValueError('Capacity demand IDs must be unique')
        seen.add(demand['id'])
        bounded(demand['unit'],'capacity demand unit',64)
        quantity=number(demand['quantity'],'capacity demand quantity')
        quota=number(demand['quota_remaining'],'quota_remaining')
        if quantity<=0:
            raise ValueError('Capacity demand must be greater than zero')
        if quota<quantity:
            # This is an engineering request conflict, not a malformed capacity
            # inventory. Keep it valid so evaluate() can report a quota blocker.
            pass
    if request['production_authority']!='NOT_ASSESSED':
        raise ValueError('This precheck cannot carry production authority')


def evaluate(request,index,*,qindex=None,provenance_index=None,as_of=None):
    if qindex is None:qindex=qualification.load()
    summary=capacity.validate(index,qindex=qindex,provenance_index=provenance_index,as_of=as_of)
    validate_request(request,summary)
    site_filter=set(request['candidate_sites'])
    cell_filter=set(request['candidate_cells'])
    class_filter=set(request['candidate_service_classes'])
    demand_by_id={x['id']:x for x in request['capacity_demands']}
    results=[];matches=[]

    for record in summary['records']:
        if record['platform'] not in request['candidate_platforms']:continue
        if site_filter and record['site_id'] not in site_filter:continue
        if cell_filter and record['cell_id'] not in cell_filter:continue
        if class_filter and record['service_class_id'] not in class_filter:continue

        blockers=[]
        if request['required_assurance_profile'] is not None and request['required_assurance_profile'] not in record['assurance_profiles']:
            blockers.append('assurance_profile:'+request['required_assurance_profile'])
        for key,value in request['required_profile_refs'].items():
            if record['profile_refs'][key]!=value:
                blockers.append('profile:'+key)

        dimensions={x['id']:x for x in record['dimensions']}
        capacity_view=[]
        for ident,demand in demand_by_id.items():
            if ident not in dimensions:
                blockers.append('capacity_dimension:'+ident+':missing')
                continue
            dim=dimensions[ident]
            if dim['unit']!=demand['unit']:
                blockers.append('capacity_dimension:'+ident+':unit')
                continue
            available=number(dim['available_after_failure_and_reserve'],'available_after_failure_and_reserve')
            requested=number(demand['quantity'],'quantity')
            quota=number(demand['quota_remaining'],'quota_remaining')
            if quota<requested:
                blockers.append('quota:'+ident)
            if available<requested:
                blockers.append('surviving_capacity:'+ident)
            capacity_view.append({
                'id':ident,'unit':dim['unit'],'requested':demand['quantity'],
                'quota_remaining':demand['quota_remaining'],
                'available_after_failure_and_reserve':dim['available_after_failure_and_reserve']
            })

        eligible=not blockers
        if eligible:matches.append(record['id'])
        results.append({
            'record_id':record['id'],'site_id':record['site_id'],'cell_id':record['cell_id'],
            'service_class_id':record['service_class_id'],'platform':record['platform'],
            'product_tuple_id':record['product_tuple_id'],
            'qualification_record_id':record['qualification_record_id'],
            'eligible':eligible,'blockers':sorted(set(blockers)),
            'capacity':sorted(capacity_view,key=lambda x:x['id'])
        })

    return {
        'kind':'SITE_SERVICE_CAPACITY_PRECHECK',
        'status':MATCH if matches else HOLD,
        'request_id':request['request_id'],
        'matching_envelopes':sorted(matches),
        'evaluations':results,
        'may_select_site':False,'may_reserve_capacity':False,'may_allocate':False,
        'may_allocate_address':False,'may_apply':False,'may_activate':False,
        'remaining_gates':[
            'requester authority and approved service parameters',
            'authoritative IPAM/address reservation',
            'transactional reservation under accountable owner and expiry',
            'current storage/key/recovery/shared-service dependency checks',
            'native scheduler placement within the approved pool',
            'realized-state verification and operating acceptance'
        ],
        'limits':[
            'This is a read-only comparison against commissioned envelopes, not a reservation.',
            'Matching capacity does not select a winner or create entitlement.',
            'Every required capacity dimension must fit; one bottleneck keeps the envelope ineligible.',
            'Quota remaining is a request input from an approved quota source, not discovered here.'
        ]
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('request',type=Path)
    parser.add_argument('--index',type=Path,default=capacity.INDEX)
    parser.add_argument('--expected-status',choices=(HOLD,MATCH))
    args=parser.parse_args()
    try:
        result=evaluate(load_request(args.request),capacity.load(args.index))
        print(json.dumps(result,indent=2))
        if args.expected_status is not None:
            return 0 if result['status']==args.expected_status else 2
        return 0 if result['status']==MATCH else 2
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({
            'kind':'SITE_SERVICE_CAPACITY_PRECHECK','status':'INVALID_SITE_SERVICE_REQUEST',
            'reason':str(exc),'may_select_site':False,'may_reserve_capacity':False,
            'may_allocate':False,'may_allocate_address':False,'may_apply':False,'may_activate':False
        },indent=2))
        return 2


if __name__=='__main__':
    raise SystemExit(main())
