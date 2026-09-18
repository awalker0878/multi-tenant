#!/usr/bin/env python3
"""Evaluate operational handover readiness without exercising operations authority.

The preflight checks that one current exported assurance record covers the reviewed
WSD/request and exact operating scope. It never changes privileged access, starts or
releases containment, performs recovery, reconciles emergency changes, applies
infrastructure, or activates production.
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

from scripts import check_operational_handover_assurance as assurance

FORMAT='portable-hosting-operational-handover-readiness-intent/1'
STATUS='PLANNING_ONLY_NOT_AUTHORIZED'
READY='OPERATIONAL_HANDOVER_CURRENT_NO_OPERATION_AUTHORIZED'
HOLD_NONE='HOLD_NO_CURRENT_OPERATIONAL_HANDOVER'
HOLD_REVIEW='HOLD_OPERATIONAL_HANDOVER_REVIEW_DUE'
HOLD_EXERCISE='HOLD_SCOPED_INCIDENT_EXERCISE_DUE'
HOLD_GAPS='HOLD_OPERATIONAL_OBLIGATIONS_OPEN'
HOLD_UNCERTAIN='HOLD_OPERATIONAL_HANDOVER_UNCERTAIN'
HOLD_SCOPE='HOLD_OPERATIONAL_SCOPE_MISMATCH'
INTENT_KEYS={
    'format','status','request_id','wsd_engineering_ref',
    'required_scope','production_authority','source_refs'
}


def load(path:Path):
    with path.open('rb') as stream:
        raw=stream.read(1024*1024+1)
    if len(raw)>1024*1024:
        raise ValueError('Operational handover readiness intent exceeds bounded size')
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
        raise ValueError('Operational handover readiness intent must be an object')
    return value


def validate_intent(intent):
    if set(intent)!=INTENT_KEYS or intent['format']!=FORMAT or intent['status']!=STATUS:
        raise ValueError('Unsupported operational handover readiness intent shape or authority boundary')
    assurance.identifier(intent['request_id'],'request_id')
    assurance.repository_ref(intent['wsd_engineering_ref'])
    scope=intent['required_scope']
    if not isinstance(scope,dict) or set(scope)!=assurance.SCOPE_KEYS:
        raise ValueError('Exact required operating scope is required')
    for key,value in scope.items():
        assurance.opaque_ref(value,f'required_scope.{key}')
    if intent['production_authority']!='NOT_ASSESSED':
        raise ValueError('Operational handover preflight cannot carry production authority')
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
    elif record['state']=='EXERCISE_DUE':
        result=HOLD_EXERCISE
    elif record['state']=='GAPS_OPEN':
        result=HOLD_GAPS
    elif record['wsd_engineering_ref']!=intent['wsd_engineering_ref'] or record['scope']!=intent['required_scope']:
        result=HOLD_SCOPE
    else:
        result=READY

    return {
        'kind':'OPERATIONAL_HANDOVER_READINESS_PREFLIGHT',
        'status':result,
        'request_id':intent['request_id'],
        'assurance_id':record['assurance_id'] if record else None,
        'handover_acceptance_ref':record['handover_acceptance_ref'] if record else None,
        'incident_exercise_ref':record['incident_exercise_ref'] if record else None,
        'open_obligation_ids':record['open_obligation_ids'] if record else [],
        'may_change_privileged_access':False,
        'may_start_containment':False,
        'may_release_containment':False,
        'may_execute_recovery':False,
        'may_reconcile_emergency_change':False,
        'may_apply':False,
        'may_activate':False,
        'next_owner_action':{
            READY:'Use this evidence only as an operational-readiness prerequisite; every live operating action remains under its separately accountable authority.',
            HOLD_NONE:'Complete an attributable operational handover with named owners, privileged-access review, monitoring evidence and a current scoped incident exercise.',
            HOLD_REVIEW:'Refresh expired handover, credential, monitoring or residual-obligation review evidence before relying on the operating envelope.',
            HOLD_EXERCISE:'Repeat the accepted scoped incident/containment/release/reconciliation exercise before relying on continuing operational readiness.',
            HOLD_GAPS:'Resolve or formally disposition every OPEN operational obligation before treating handover as current.',
            HOLD_UNCERTAIN:'Reconcile the authoritative operating, credential, monitoring, incident and handover state before relying on this record.',
            HOLD_SCOPE:'Align the WSD/site/service/platform/operating/recovery scope; do not reuse a handover from a different service envelope.'
        }[result],
        'limits':[
            'A ready result does not grant incident command, privileged access, recovery, change or production authority.',
            'Containment release must remain explicit and attributable outside this repository.',
            'Emergency changes remain external and require deliberate reconciliation after the incident or maintenance action.',
            'CI never changes live infrastructure or production state.'
        ]
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('intent',type=Path)
    p.add_argument('--as-of',help='ISO-8601 review instant; defaults to current UTC')
    p.add_argument('--expected-status',choices=(READY,HOLD_NONE,HOLD_REVIEW,HOLD_EXERCISE,HOLD_GAPS,HOLD_UNCERTAIN,HOLD_SCOPE))
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
            'kind':'OPERATIONAL_HANDOVER_READINESS_PREFLIGHT',
            'status':'INVALID_OPERATIONAL_HANDOVER_READINESS_INTENT',
            'reason':str(exc),
            'may_change_privileged_access':False,
            'may_start_containment':False,
            'may_release_containment':False,
            'may_execute_recovery':False,
            'may_reconcile_emergency_change':False,
            'may_apply':False,
            'may_activate':False
        },indent=2))
        return 2


if __name__=='__main__':
    raise SystemExit(main())
