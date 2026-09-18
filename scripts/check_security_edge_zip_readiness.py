#!/usr/bin/env python3
"""Evaluate security-edge/ZIP readiness without mutating routes, policy or attachments."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from scripts import check_security_edge_zip_assurance as assurance

FORMAT='portable-hosting-security-edge-zip-readiness-intent/1'
STATUS='PLANNING_ONLY_NOT_AUTHORIZED'
READY='SECURITY_EDGE_ZIP_CURRENT_NO_MUTATION_AUTHORIZED'
HOLD_NONE='HOLD_NO_CURRENT_SECURITY_EDGE_ZIP_ASSURANCE'
HOLD_REVIEW='HOLD_SECURITY_EDGE_REVIEW_DUE'
HOLD_FAILURE='HOLD_SECURITY_EDGE_FAILURE_TEST_DUE'
HOLD_GAPS='HOLD_SECURITY_EDGE_GAPS_OPEN'
HOLD_UNCERTAIN='HOLD_SECURITY_EDGE_ASSURANCE_UNCERTAIN'
HOLD_SCOPE='HOLD_SECURITY_EDGE_SCOPE_MISMATCH'
INTENT_KEYS={
    'format','status','request_id','boundary_id','source_endpoint_ref',
    'destination_endpoint_ref','service_class_ref','production_authority','source_refs'
}


def load(path:Path):
    with path.open('rb') as stream:
        raw=stream.read(1024*1024+1)
    if len(raw)>1024*1024:
        raise ValueError('Security-edge readiness intent exceeds bounded size')
    def pairs(items):
        out={}
        for k,v in items:
            if k in out: raise ValueError('Duplicate JSON property')
            out[k]=v
        return out
    value=json.loads(raw,object_pairs_hook=pairs)
    if not isinstance(value,dict):
        raise ValueError('Security-edge readiness intent must be an object')
    return value


def validate_intent(intent):
    if set(intent)!=INTENT_KEYS or intent['format']!=FORMAT or intent['status']!=STATUS:
        raise ValueError('Unsupported security-edge readiness intent')
    assurance.identifier(intent['request_id'],'request_id')
    assurance.identifier(intent['boundary_id'],'boundary_id')
    for key in ('source_endpoint_ref','destination_endpoint_ref','service_class_ref'):
        assurance.opaque_ref(intent[key],key)
    if intent['source_endpoint_ref']==intent['destination_endpoint_ref']:
        raise ValueError('Security-edge request requires two distinct adjacent endpoints')
    if intent['production_authority']!='NOT_ASSESSED':
        raise ValueError('Security-edge readiness cannot carry production authority')
    refs=assurance.unique_strings(intent['source_refs'],'source_refs')
    for ref in refs: assurance.repository_ref(ref)


def evaluate(intent,*,index=None,as_of=None):
    if as_of is None: as_of=datetime.now(timezone.utc)
    if not isinstance(as_of,datetime) or as_of.tzinfo is None:
        raise ValueError('Timezone-aware as_of required')
    as_of=as_of.astimezone(timezone.utc)
    validate_intent(intent)
    if index is None: index=assurance.load()
    summary=assurance.validate(index,as_of=as_of)
    records=[x for x in summary['records'] if x['boundary_id']==intent['boundary_id']]
    record=records[0] if records else None
    if record is None:
        result=HOLD_NONE
    elif record['state']=='UNCERTAIN':
        result=HOLD_UNCERTAIN
    elif record['state']=='REVIEW_DUE':
        result=HOLD_REVIEW
    elif record['state']=='FAILURE_TEST_DUE':
        result=HOLD_FAILURE
    elif record['state']=='GAPS_OPEN':
        result=HOLD_GAPS
    elif (
        record['source_endpoint_ref']!=intent['source_endpoint_ref']
        or record['destination_endpoint_ref']!=intent['destination_endpoint_ref']
        or record['service_class_ref']!=intent['service_class_ref']
    ):
        result=HOLD_SCOPE
    else:
        result=READY
    return {
        'kind':'SECURITY_EDGE_ZIP_READINESS_PREFLIGHT',
        'status':result,'request_id':intent['request_id'],'boundary_id':intent['boundary_id'],
        'assurance_id':record['assurance_id'] if record else None,
        'realization_type':record['realization_type'] if record else None,
        'open_gap_ids':record['open_gap_ids'] if record else [],
        'may_create_route':False,'may_change_policy':False,
        'may_attach_domain':False,'may_change_edge':False,
        'may_change_management_access':False,'may_apply':False,'may_activate':False,
        'next_owner_action':{
            READY:'Use this only as a readiness prerequisite for the exact accepted boundary; live route, policy, attachment and activation decisions remain separately controlled.',
            HOLD_NONE:'Publish current scoped ZIP assurance for the exact boundary, including pairwise authority, policy, path, inspection/logging, HA/failure and bypass evidence.',
            HOLD_REVIEW:'Refresh the boundary approval or residual-gap review before relying on this ZIP.',
            HOLD_FAILURE:'Repeat current path and failure tests, including member loss, manager loss, route withdrawal and no-uninspected-fallback behavior.',
            HOLD_GAPS:'Resolve or formally disposition every OPEN ZIP gap before treating the boundary as qualified.',
            HOLD_UNCERTAIN:'Reconcile the authoritative edge, routing, policy, management and evidence state.',
            HOLD_SCOPE:'Use the exact accepted source/destination/service-class scope; do not reuse assurance from another boundary.'
        }[result],
        'limits':[
            'A ready result is not permission to change firewall, routes, attachments or management access.',
            'A prepared native gateway or local packet fixture is not sufficient by itself.',
            'Distributed/shared realizations remain eligible only when equivalent mandatory ZIP outcomes are current.',
            'CI never performs native mutation or production activation.'
        ]
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('intent',type=Path)
    p.add_argument('--as-of',help='ISO-8601 review instant; defaults to current UTC')
    p.add_argument('--expected-status',choices=(READY,HOLD_NONE,HOLD_REVIEW,HOLD_FAILURE,HOLD_GAPS,HOLD_UNCERTAIN,HOLD_SCOPE))
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
            'kind':'SECURITY_EDGE_ZIP_READINESS_PREFLIGHT',
            'status':'INVALID_SECURITY_EDGE_ZIP_READINESS_INTENT','reason':str(exc),
            'may_create_route':False,'may_change_policy':False,
            'may_attach_domain':False,'may_change_edge':False,
            'may_change_management_access':False,'may_apply':False,'may_activate':False
        },indent=2))
        return 2


if __name__=='__main__':
    raise SystemExit(main())
