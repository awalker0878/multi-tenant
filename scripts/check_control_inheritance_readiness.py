#!/usr/bin/env python3
"""Evaluate control-inheritance readiness without selecting controls or authorizing service.

The preflight checks that one current exported assurance record covers the reviewed
WSD/request, exact service/site/platform/control-selection scope, and required control
IDs. It never accepts inherited evidence, closes residual gaps, or issues authorization.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from scripts import check_control_inheritance_assurance as assurance

FORMAT='portable-hosting-control-inheritance-readiness-intent/1'
STATUS='PLANNING_ONLY_NOT_AUTHORIZED'
READY='CONTROL_INHERITANCE_EVIDENCE_CURRENT_NO_AUTHORIZATION_ISSUED'
HOLD_NONE='HOLD_NO_CURRENT_CONTROL_ALLOCATION'
HOLD_REVIEW='HOLD_CONTROL_EVIDENCE_REVIEW_DUE'
HOLD_GAPS='HOLD_RESIDUAL_CONTROL_GAPS'
HOLD_UNCERTAIN='HOLD_CONTROL_ALLOCATION_UNCERTAIN'
HOLD_SCOPE='HOLD_CONTROL_SCOPE_MISMATCH'
HOLD_CONTROL='HOLD_REQUIRED_CONTROL_NOT_ALLOCATED'
INTENT_KEYS={
    'format','status','request_id','wsd_engineering_ref','required_scope',
    'required_control_ids','production_authority','source_refs'
}


def load(path:Path):
    with path.open('rb') as stream:
        raw=stream.read(1024*1024+1)
    if len(raw)>1024*1024:
        raise ValueError('Control-inheritance readiness intent exceeds bounded size')
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
        raise ValueError('Control-inheritance readiness intent must be an object')
    return value


def validate_intent(intent):
    if set(intent)!=INTENT_KEYS or intent['format']!=FORMAT or intent['status']!=STATUS:
        raise ValueError('Unsupported control-inheritance readiness intent shape or authority boundary')
    assurance.identifier(intent['request_id'],'request_id')
    assurance.repository_ref(intent['wsd_engineering_ref'])
    scope=intent['required_scope']
    if not isinstance(scope,dict) or set(scope)!=assurance.SCOPE_KEYS:
        raise ValueError('Exact required control-inheritance scope is required')
    for key,value in scope.items():
        assurance.opaque_ref(value,f'required_scope.{key}')
    control_ids=assurance.unique_strings(intent['required_control_ids'],'required_control_ids')
    for control_id in control_ids:
        assurance.identifier(control_id,'required_control_id')
    if intent['production_authority']!='NOT_ASSESSED':
        raise ValueError('Control-inheritance preflight cannot carry production authority')
    refs=assurance.unique_strings(intent['source_refs'],'source_refs')
    for ref in refs:
        assurance.repository_ref(ref)


def evaluate(intent,*,index=None,as_of=None):
    if as_of is None:
        as_of=datetime.now(timezone.utc)
    if not isinstance(as_of,datetime) or as_of.tzinfo is None:
        raise ValueError('Timezone-aware as_of required')
    as_of=as_of.astimezone(timezone.utc)
    validate_intent(intent)
    if index is None:
        index=assurance.load()
    summary=assurance.validate(index,as_of=as_of)
    records=[x for x in summary['records'] if x['request_id']==intent['request_id']]
    record=records[0] if records else None
    if record is None:
        result=HOLD_NONE
    elif record['state']=='UNCERTAIN':
        result=HOLD_UNCERTAIN
    elif record['state']=='REVIEW_DUE':
        result=HOLD_REVIEW
    elif record['state']=='GAPS_OPEN':
        result=HOLD_GAPS
    elif record['wsd_engineering_ref']!=intent['wsd_engineering_ref'] or record['scope']!=intent['required_scope']:
        result=HOLD_SCOPE
    elif not set(intent['required_control_ids']).issubset(record['control_ids']):
        result=HOLD_CONTROL
    else:
        result=READY

    return {
        'kind':'CONTROL_INHERITANCE_READINESS_PREFLIGHT',
        'status':result,
        'request_id':intent['request_id'],
        'assurance_id':record['assurance_id'] if record else None,
        'control_count':record['control_count'] if record else 0,
        'open_gap_ids':record['open_gap_ids'] if record else [],
        'may_select_controls':False,
        'may_accept_inheritance':False,
        'may_close_residual_gap':False,
        'may_issue_authorization':False,
        'may_apply':False,
        'may_activate':False,
        'next_owner_action':{
            READY:'Use this evidence only as a readiness prerequisite; formal authorization and any infrastructure change remain separate attributable decisions.',
            HOLD_NONE:'Publish a reviewed control allocation with scoped evidence for the actual service/site/platform selection and all required external interfaces.',
            HOLD_REVIEW:'Refresh the expired control, inherited-service or external-interface evidence and obtain the required review decision.',
            HOLD_GAPS:'Resolve or formally disposition every OPEN residual control gap under the accountable external authority.',
            HOLD_UNCERTAIN:'Reconcile the authoritative control, inheritance, evidence and decision state before relying on this record.',
            HOLD_SCOPE:'Align the reviewed WSD/site/service/platform/catalogue/selection scope; do not reuse evidence from a different scope.',
            HOLD_CONTROL:'Allocate and evidence every required control ID before treating the dependency as ready.'
        }[result],
        'limits':[
            'A ready result is not a control assessment report, risk acceptance or formal authorization.',
            'This preflight does not choose catalogue controls or parameters.',
            'Inherited evidence remains external and must apply to the exact reviewed scope and time interval.',
            'CI never applies infrastructure or activates production.'
        ]
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('intent',type=Path)
    p.add_argument('--as-of',help='ISO-8601 review instant; defaults to current UTC')
    p.add_argument('--expected-status',choices=(READY,HOLD_NONE,HOLD_REVIEW,HOLD_GAPS,HOLD_UNCERTAIN,HOLD_SCOPE,HOLD_CONTROL))
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
            'kind':'CONTROL_INHERITANCE_READINESS_PREFLIGHT',
            'status':'INVALID_CONTROL_INHERITANCE_READINESS_INTENT',
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
