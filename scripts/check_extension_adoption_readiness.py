#!/usr/bin/env python3
"""Evaluate bounded extension-adoption readiness without provisioning an extension."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from scripts import check_extension_adoption_assurance as assurance

FORMAT='portable-hosting-extension-adoption-readiness-intent/1'
STATUS='PLANNING_ONLY_NOT_AUTHORIZED'
READY='EXTENSION_ADOPTION_CURRENT_EXTENSION_ONLY_NO_PROVISIONING_AUTHORIZED'
HOLD_NONE='HOLD_NO_CURRENT_EXTENSION_ADOPTION'
HOLD_REVIEW='HOLD_EXTENSION_SCOPE_REVIEW_DUE'
HOLD_QUALIFICATION='HOLD_EXTENSION_QUALIFICATION_DUE'
HOLD_GAPS='HOLD_EXTENSION_GAPS_OPEN'
HOLD_UNCERTAIN='HOLD_EXTENSION_ADOPTION_UNCERTAIN'
HOLD_SCOPE='HOLD_EXTENSION_SCOPE_MISMATCH'
INTENT_KEYS={
    'format','status','request_id','extension_kind','extension_id',
    'extension_profile_ref','service_class_ref','production_authority','source_refs'
}


def load(path:Path):
    with path.open('rb') as stream:
        raw=stream.read(1024*1024+1)
    if len(raw)>1024*1024:
        raise ValueError('Extension readiness intent exceeds bounded size')
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
        raise ValueError('Extension readiness intent must be an object')
    return value


def validate_intent(intent):
    if set(intent)!=INTENT_KEYS or intent['format']!=FORMAT or intent['status']!=STATUS:
        raise ValueError('Unsupported extension readiness intent shape or authority boundary')
    assurance.identifier(intent['request_id'],'request_id')
    assurance.identifier(intent['extension_id'],'extension_id')
    if intent['extension_kind'] not in assurance.KINDS:
        raise ValueError('Unknown extension kind')
    assurance.opaque_ref(intent['extension_profile_ref'],'extension_profile_ref')
    assurance.opaque_ref(intent['service_class_ref'],'service_class_ref')
    if intent['production_authority']!='NOT_ASSESSED':
        raise ValueError('Extension readiness cannot carry production authority')
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
    records=[x for x in summary['records'] if x['extension_id']==intent['extension_id']]
    record=records[0] if records else None
    if record is None:
        result=HOLD_NONE
    elif record['state']=='UNCERTAIN':
        result=HOLD_UNCERTAIN
    elif record['state']=='REVIEW_DUE':
        result=HOLD_REVIEW
    elif record['state']=='QUALIFICATION_DUE':
        result=HOLD_QUALIFICATION
    elif record['state']=='GAPS_OPEN':
        result=HOLD_GAPS
    elif (
        record['extension_kind']!=intent['extension_kind']
        or record['extension_profile_ref']!=intent['extension_profile_ref']
        or record['service_class_ref']!=intent['service_class_ref']
    ):
        result=HOLD_SCOPE
    else:
        result=READY

    return {
        'kind':'EXTENSION_ADOPTION_READINESS_PREFLIGHT',
        'status':result,
        'request_id':intent['request_id'],
        'extension_id':intent['extension_id'],
        'extension_kind':intent['extension_kind'],
        'assurance_id':record['assurance_id'] if record else None,
        'base_service_status':record['base_service_status'] if record else 'EXTENSION_ONLY',
        'unsupported_capabilities':record['unsupported_capabilities'] if record else [],
        'open_gap_ids':record['open_gap_ids'] if record else [],
        'may_add_to_base_service':False,
        'may_provision_extension':False,
        'may_change_physical_fabric':False,
        'may_create_cluster':False,
        'may_assign_device':False,
        'may_apply':False,
        'may_activate':False,
        'next_owner_action':{
            READY:'Use this only as evidence that the separately scoped extension is currently adopted; provision and activate it only through its approved extension-specific procedures.',
            HOLD_NONE:'Develop and approve an extension-specific scope, design, ownership, recovery/retirement model and applicable qualification evidence.',
            HOLD_REVIEW:'Refresh the extension adoption scope or residual-gap review before continuing to offer the extension.',
            HOLD_QUALIFICATION:'Repeat the applicable extension qualification before continuing to offer the extension.',
            HOLD_GAPS:'Resolve or formally disposition every OPEN extension gap before treating adoption as current.',
            HOLD_UNCERTAIN:'Reconcile the authoritative extension scope, topology, ownership and qualification state before relying on this record.',
            HOLD_SCOPE:'Use the exact adopted extension kind/profile/service-class scope; do not substitute another extension or base-service profile.'
        }[result],
        'limits':[
            'A ready result does not make the extension part of the portable base service.',
            'This preflight grants no cluster, device, physical-fabric, provisioning, apply or activation authority.',
            'Extension-specific unsupported capabilities and portability impacts remain explicit.',
            'Actual extension implementation and production authorization remain external accountable work.'
        ]
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('intent',type=Path)
    p.add_argument('--as-of',help='ISO-8601 review instant; defaults to current UTC')
    p.add_argument('--expected-status',choices=(READY,HOLD_NONE,HOLD_REVIEW,HOLD_QUALIFICATION,HOLD_GAPS,HOLD_UNCERTAIN,HOLD_SCOPE))
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
            'kind':'EXTENSION_ADOPTION_READINESS_PREFLIGHT',
            'status':'INVALID_EXTENSION_ADOPTION_READINESS_INTENT',
            'reason':str(exc),
            'may_add_to_base_service':False,
            'may_provision_extension':False,
            'may_change_physical_fabric':False,
            'may_create_cluster':False,
            'may_assign_device':False,
            'may_apply':False,
            'may_activate':False
        },indent=2))
        return 2


if __name__=='__main__':
    raise SystemExit(main())
