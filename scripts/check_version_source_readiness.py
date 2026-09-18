#!/usr/bin/env python3
"""Evaluate exact-tuple version/source provenance readiness without qualifying a platform."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from scripts import check_version_source_provenance as provenance

FORMAT='portable-hosting-version-source-readiness-intent/1'
STATUS='PLANNING_ONLY_NOT_AUTHORIZED'
READY='VERSION_SOURCE_PROVENANCE_CURRENT_NO_QUALIFICATION_GRANTED'
HOLD_NONE='HOLD_NO_CURRENT_VERSION_SOURCE_PROVENANCE'
HOLD_REVIEW='HOLD_VERSION_SOURCE_REVIEW_DUE'
HOLD_UNSUPPORTED='HOLD_PLATFORM_TUPLE_UNSUPPORTED'
HOLD_UNCERTAIN='HOLD_VERSION_SOURCE_PROVENANCE_UNCERTAIN'
HOLD_TUPLE='HOLD_EXACT_TUPLE_MISMATCH'
INTENT_KEYS={
    'format','status','request_id','platform','product_tuple_id',
    'required_product_tuple','production_authority','source_refs'
}


def load(path:Path):
    with path.open('rb') as stream:
        raw=stream.read(1024*1024+1)
    if len(raw)>1024*1024:
        raise ValueError('Version/source readiness intent exceeds bounded size')
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
        raise ValueError('Version/source readiness intent must be an object')
    return value


def validate_intent(intent):
    if set(intent)!=INTENT_KEYS or intent['format']!=FORMAT or intent['status']!=STATUS:
        raise ValueError('Unsupported version/source readiness intent shape or authority boundary')
    provenance.identifier(intent['request_id'],'request_id')
    if intent['platform'] not in provenance.PLATFORMS:
        raise ValueError('Unknown platform family')
    provenance.identifier(intent['product_tuple_id'],'product_tuple_id')
    provenance.validate_product_tuple(intent['required_product_tuple'])
    if intent['production_authority']!='NOT_ASSESSED':
        raise ValueError('Version/source readiness cannot carry production authority')
    refs=provenance.unique_strings(intent['source_refs'],'source_refs')
    for ref in refs:
        provenance.repository_ref(ref)


def evaluate(intent,*,index=None,as_of=None):
    if as_of is None:
        as_of=datetime.now(timezone.utc)
    if not isinstance(as_of,datetime) or as_of.tzinfo is None:
        raise ValueError('Timezone-aware as_of required')
    as_of=as_of.astimezone(timezone.utc)
    validate_intent(intent)
    if index is None:
        index=provenance.load()
    summary=provenance.validate(index,as_of=as_of)
    records=[
        x for x in summary['records']
        if x['platform']==intent['platform']
        and x['product_tuple_id']==intent['product_tuple_id']
    ]
    record=records[0] if records else None
    if record is None:
        result=HOLD_NONE
    elif record['state']=='UNCERTAIN':
        result=HOLD_UNCERTAIN
    elif record['state']=='REVIEW_DUE':
        result=HOLD_REVIEW
    elif record['state']=='UNSUPPORTED':
        result=HOLD_UNSUPPORTED
    elif record['product_tuple']!=intent['required_product_tuple']:
        result=HOLD_TUPLE
    else:
        result=READY

    return {
        'kind':'VERSION_SOURCE_PROVENANCE_READINESS_PREFLIGHT',
        'status':result,
        'request_id':intent['request_id'],
        'platform':intent['platform'],
        'product_tuple_id':intent['product_tuple_id'],
        'provenance_id':record['provenance_id'] if record else None,
        'support_status':record['support_status'] if record else None,
        'may_claim_native_qualification':False,
        'may_select_site':False,
        'may_reserve_capacity':False,
        'may_allocate':False,
        'may_apply':False,
        'may_activate':False,
        'next_owner_action':{
            READY:'Use this current compatibility/provenance record only as a prerequisite for separately executed native qualification.',
            HOLD_NONE:'Select the exact installed tuple and publish current vendor/project support, API, provider, hardware and release evidence.',
            HOLD_REVIEW:'Refresh expired source, compatibility or lifecycle review evidence before using this tuple for qualification.',
            HOLD_UNSUPPORTED:'Do not use the unsupported tuple for new qualification; follow the accountable upgrade, exception or retirement decision.',
            HOLD_UNCERTAIN:'Reconcile the authoritative support/source/compatibility state before qualification.',
            HOLD_TUPLE:'Align the exact product/API/provider/hardware/licence tuple; documentation for a different tuple does not satisfy this request.'
        }[result],
        'limits':[
            'A ready result is not native qualification or production authorization.',
            'This check does not contact vendor support, package registries or platforms.',
            'Installed compatibility and lifecycle evidence must remain separately current from architecture/source review.',
            'CI never performs placement, allocation, apply or activation.'
        ]
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('intent',type=Path)
    p.add_argument('--as-of',help='ISO-8601 review instant; defaults to current UTC')
    p.add_argument('--expected-status',choices=(READY,HOLD_NONE,HOLD_REVIEW,HOLD_UNSUPPORTED,HOLD_UNCERTAIN,HOLD_TUPLE))
    a=p.parse_args()
    try:
        as_of=provenance.instant(a.as_of,'as_of') if a.as_of else datetime.now(timezone.utc)
        result=evaluate(load(a.intent),as_of=as_of)
        print(json.dumps(result,indent=2))
        if a.expected_status is not None:
            return 0 if result['status']==a.expected_status else 2
        return 0 if result['status']==READY else 2
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({
            'kind':'VERSION_SOURCE_PROVENANCE_READINESS_PREFLIGHT',
            'status':'INVALID_VERSION_SOURCE_READINESS_INTENT',
            'reason':str(exc),
            'may_claim_native_qualification':False,
            'may_select_site':False,'may_reserve_capacity':False,
            'may_allocate':False,'may_apply':False,'may_activate':False
        },indent=2))
        return 2


if __name__=='__main__':
    raise SystemExit(main())
