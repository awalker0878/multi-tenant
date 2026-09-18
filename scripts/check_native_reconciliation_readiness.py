#!/usr/bin/env python3
"""Evaluate native reconciliation readiness without authorizing any native mutation."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from scripts import check_native_reconciliation_assurance as assurance

FORMAT='portable-hosting-native-reconciliation-readiness-intent/1'
STATUS='PLANNING_ONLY_NOT_AUTHORIZED'
READY='NATIVE_RECONCILIATION_CURRENT_NO_MUTATION_AUTHORIZED'
HOLD_NONE='HOLD_NO_CURRENT_NATIVE_RECONCILIATION'
HOLD_REVIEW='HOLD_NATIVE_RECONCILIATION_REVIEW_DUE'
HOLD_OBSERVATION='HOLD_NATIVE_OBSERVATION_DUE'
HOLD_FENCE='HOLD_WRITER_FENCE_DUE'
HOLD_CONTAINMENT='HOLD_INCIDENT_CONTAINMENT_ACTIVE'
HOLD_RECONCILIATION='HOLD_NATIVE_RECONCILIATION_REQUIRED'
HOLD_GAPS='HOLD_NATIVE_RECONCILIATION_GAPS_OPEN'
HOLD_UNCERTAIN='HOLD_NATIVE_RECONCILIATION_UNCERTAIN'
HOLD_SCOPE='HOLD_NATIVE_RECONCILIATION_SCOPE_MISMATCH'
INTENT_KEYS={
    'format','status','request_id','operation_id','platform',
    'engineering_record_ref','operation_scope_ref','resource_set_ref',
    'operation_generation','production_authority','source_refs'
}


def load(path:Path):
    with path.open('rb') as stream:
        raw=stream.read(1024*1024+1)
    if len(raw)>1024*1024: raise ValueError('Native reconciliation readiness intent exceeds bounded size')
    def pairs(items):
        out={}
        for k,v in items:
            if k in out: raise ValueError('Duplicate JSON property')
            out[k]=v
        return out
    value=json.loads(raw,object_pairs_hook=pairs)
    if not isinstance(value,dict): raise ValueError('Native reconciliation readiness intent must be an object')
    return value


def validate_intent(intent):
    if set(intent)!=INTENT_KEYS or intent['format']!=FORMAT or intent['status']!=STATUS:
        raise ValueError('Unsupported native reconciliation readiness intent')
    assurance.identifier(intent['request_id'],'request_id')
    assurance.identifier(intent['operation_id'],'operation_id')
    if intent['platform'] not in assurance.PLATFORMS: raise ValueError('Unknown native observation platform')
    assurance.repository_ref(intent['engineering_record_ref'])
    for key in ('operation_scope_ref','resource_set_ref'):
        assurance.opaque_ref(intent[key],key)
    assurance.positive_int(intent['operation_generation'],'operation_generation')
    if intent['production_authority']!='NOT_ASSESSED':
        raise ValueError('Native reconciliation readiness cannot carry production authority')
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
    records=[x for x in summary['records'] if x['operation_id']==intent['operation_id']]
    record=records[0] if records else None
    if record is None: result=HOLD_NONE
    elif record['state']=='UNCERTAIN': result=HOLD_UNCERTAIN
    elif record['state']=='REVIEW_DUE': result=HOLD_REVIEW
    elif record['state']=='OBSERVATION_DUE': result=HOLD_OBSERVATION
    elif record['state']=='FENCE_DUE': result=HOLD_FENCE
    elif record['state']=='CONTAINMENT_ACTIVE': result=HOLD_CONTAINMENT
    elif record['state']=='RECONCILIATION_REQUIRED': result=HOLD_RECONCILIATION
    elif record['state']=='GAPS_OPEN': result=HOLD_GAPS
    elif (
        record['platform']!=intent['platform']
        or record['engineering_record_ref']!=intent['engineering_record_ref']
        or record['operation_scope_ref']!=intent['operation_scope_ref']
        or record['resource_set_ref']!=intent['resource_set_ref']
        or record['operation_generation']!=intent['operation_generation']
    ): result=HOLD_SCOPE
    else: result=READY

    return {
        'kind':'NATIVE_RECONCILIATION_READINESS_PREFLIGHT','status':result,
        'request_id':intent['request_id'],'operation_id':intent['operation_id'],
        'assurance_id':record['assurance_id'] if record else None,
        'observation_outcome':record['observation_outcome'] if record else None,
        'writer_fence_state':record['writer_fence_state'] if record else None,
        'containment_state':record['containment_state'] if record else None,
        'reconciliation_status':record['reconciliation_status'] if record else None,
        'open_gap_ids':record['open_gap_ids'] if record else [],
        'may_list_tasks':False,'may_cancel_task':False,'may_release_containment':False,
        'may_import_state':False,'may_repair':False,'may_apply':False,
        'may_delete':False,'may_activate':False,
        'next_owner_action':{
            READY:'Use this only as evidence that the exact operation scope is reconciled; any subsequent mutation needs a separate current plan and authorization.',
            HOLD_NONE:'Publish current native interface/readback, true writer-fence, containment and reconciliation evidence for the exact operation/resource scope.',
            HOLD_REVIEW:'Refresh the operation-scope or residual-gap review before relying on this reconciliation record.',
            HOLD_OBSERVATION:'Refresh exact API/RBAC/version-token/task-entity applicability and bounded native observation evidence.',
            HOLD_FENCE:'Establish and verify the real scoped native writer fence; a stopped runner or state lock alone is insufficient.',
            HOLD_CONTAINMENT:'Preserve incident containment until the designated authority records an explicit release.',
            HOLD_RECONCILIATION:'Resolve pending/failed/divergent/unknown native outcome and record the accountable data-safe reconciliation decision.',
            HOLD_GAPS:'Resolve or formally disposition every OPEN reconciliation gap.',
            HOLD_UNCERTAIN:'Reconcile the authoritative native task/resource/writer/containment state before continuing.',
            HOLD_SCOPE:'Use evidence for the exact platform, engineering record, resource set and operation generation.'
        }[result],
        'limits':[
            'A ready result is not mutation or recovery authorization.',
            'This preflight never lists/cancels tasks, releases containment, imports state, repairs or deletes resources.',
            'Old Terraform state is never treated as infrastructure rollback.',
            'CI never contacts a native target or activates production.'
        ]
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('intent',type=Path)
    p.add_argument('--as-of',help='ISO-8601 review instant; defaults to current UTC')
    p.add_argument('--expected-status',choices=(
        READY,HOLD_NONE,HOLD_REVIEW,HOLD_OBSERVATION,HOLD_FENCE,HOLD_CONTAINMENT,
        HOLD_RECONCILIATION,HOLD_GAPS,HOLD_UNCERTAIN,HOLD_SCOPE))
    a=p.parse_args()
    try:
        as_of=assurance.instant(a.as_of,'as_of') if a.as_of else datetime.now(timezone.utc)
        result=evaluate(load(a.intent),as_of=as_of)
        print(json.dumps(result,indent=2))
        if a.expected_status is not None: return 0 if result['status']==a.expected_status else 2
        return 0 if result['status']==READY else 2
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({
            'kind':'NATIVE_RECONCILIATION_READINESS_PREFLIGHT',
            'status':'INVALID_NATIVE_RECONCILIATION_READINESS_INTENT','reason':str(exc),
            'may_list_tasks':False,'may_cancel_task':False,'may_release_containment':False,
            'may_import_state':False,'may_repair':False,'may_apply':False,
            'may_delete':False,'may_activate':False
        },indent=2)); return 2


if __name__=='__main__':
    raise SystemExit(main())
