#!/usr/bin/env python3
"""Evaluate release knowledge-maintenance readiness without approving publication."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from scripts import check_knowledge_maintenance_assurance as assurance

FORMAT='portable-hosting-knowledge-maintenance-readiness-intent/1'
STATUS='PLANNING_ONLY_NOT_AUTHORIZED'
READY='KNOWLEDGE_MAINTENANCE_CURRENT_NO_PUBLICATION_AUTHORIZED'
HOLD_NONE='HOLD_NO_CURRENT_RELEASE_MAINTENANCE'
HOLD_REVIEW='HOLD_MAINTENANCE_REVIEW_DUE'
HOLD_VALIDATION='HOLD_RELEASE_VALIDATION_DUE'
HOLD_CONFLICTS='HOLD_KNOWLEDGE_CONFLICTS_OPEN'
HOLD_UNCERTAIN='HOLD_KNOWLEDGE_MAINTENANCE_UNCERTAIN'
HOLD_REVISION='HOLD_RELEASE_REVISION_MISMATCH'
INTENT_KEYS={
    'format','status','request_id','release_id','reviewed_revision',
    'required_topic_ids','publication_authority','source_refs'
}


def load(path:Path):
    return assurance.load_json(path)


def validate_intent(intent):
    if set(intent)!=INTENT_KEYS or intent['format']!=FORMAT or intent['status']!=STATUS:
        raise ValueError('Unsupported knowledge-maintenance readiness intent')
    assurance.identifier(intent['request_id'],'request_id')
    assurance.identifier(intent['release_id'],'release_id')
    if not isinstance(intent['reviewed_revision'],str) or not assurance.SHA40.fullmatch(intent['reviewed_revision']):
        raise ValueError('Readiness reviewed_revision must be an exact Git SHA')
    topics=assurance.unique_strings(intent['required_topic_ids'],'required_topic_ids')
    if set(topics)!=assurance.TOPIC_IDS:
        raise ValueError('Readiness intent must cover the complete primary knowledge-home topic set')
    if intent['publication_authority']!='NOT_ASSESSED':
        raise ValueError('Knowledge-maintenance readiness cannot carry publication authority')
    refs=assurance.unique_strings(intent['source_refs'],'source_refs')
    for ref in refs:
        assurance.repository_ref(ref)


def evaluate(intent,*,index=None,registry=None,as_of=None):
    if as_of is None:
        as_of=datetime.now(timezone.utc)
    if not isinstance(as_of,datetime) or as_of.tzinfo is None:
        raise ValueError('Timezone-aware as_of required')
    as_of=as_of.astimezone(timezone.utc)
    validate_intent(intent)
    if index is None:index=assurance.load()
    if registry is None:registry=assurance.load_registry()
    summary=assurance.validate(index,as_of=as_of,registry=registry)
    records=[x for x in summary['records'] if x['release_id']==intent['release_id']]
    record=records[0] if records else None
    if record is None:
        result=HOLD_NONE
    elif record['state']=='UNCERTAIN':
        result=HOLD_UNCERTAIN
    elif record['state']=='REVIEW_DUE':
        result=HOLD_REVIEW
    elif record['state']=='VALIDATION_DUE':
        result=HOLD_VALIDATION
    elif record['state']=='CONFLICTS_OPEN':
        result=HOLD_CONFLICTS
    elif record['reviewed_revision']!=intent['reviewed_revision']:
        result=HOLD_REVISION
    else:
        result=READY
    return {
        'kind':'KNOWLEDGE_MAINTENANCE_READINESS_PREFLIGHT',
        'status':result,
        'request_id':intent['request_id'],
        'release_id':intent['release_id'],
        'assurance_id':record['assurance_id'] if record else None,
        'reviewed_revision':record['reviewed_revision'] if record else None,
        'knowledge_topic_count':summary['knowledge_topic_count'],
        'unresolved_conflicts':record['unresolved_conflicts'] if record else [],
        'may_publish_release':False,
        'may_approve_change':False,
        'may_reassign_primary_home':False,
        'may_accept_conflict':False,
        'may_authorize_architecture':False,
        'may_apply':False,
        'may_activate':False,
        'next_owner_action':{
            READY:'Use this only as evidence that the named release has current maintenance records; publication and architecture approval remain separate attributable decisions.',
            HOLD_NONE:'Assign the maintaining owner/cadence and publish a release record with validated links/mappings, drift/duplicate review, consistent version set and approved change record.',
            HOLD_REVIEW:'Perform the scheduled maintenance review and refresh owner/cadence evidence.',
            HOLD_VALIDATION:'Rerun release-wide documentation/repository/link/requirement/primary-home/drift/scenario validation and refresh its evidence.',
            HOLD_CONFLICTS:'Resolve the recorded duplicate-policy or supplement/parent drift conflicts before treating the release as maintained.',
            HOLD_UNCERTAIN:'Reconcile the authoritative release, ownership, validation and change-control state.',
            HOLD_REVISION:'Review the exact requested Git revision; evidence for another release revision cannot be reused.'
        }[result],
        'limits':[
            'A ready result is not publication approval, architecture adoption or security authorization.',
            'The primary-home map routes maintenance; it does not permit a supplement to weaken its parent.',
            'Release maintenance evidence is revision-specific and cannot silently carry forward after changes.',
            'CI never publishes, approves, applies or activates production.'
        ]
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('intent',type=Path)
    p.add_argument('--as-of',help='ISO-8601 review instant; defaults to current UTC')
    p.add_argument('--expected-status',choices=(READY,HOLD_NONE,HOLD_REVIEW,HOLD_VALIDATION,HOLD_CONFLICTS,HOLD_UNCERTAIN,HOLD_REVISION))
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
            'kind':'KNOWLEDGE_MAINTENANCE_READINESS_PREFLIGHT',
            'status':'INVALID_KNOWLEDGE_MAINTENANCE_READINESS_INTENT',
            'reason':str(exc),
            'may_publish_release':False,'may_approve_change':False,
            'may_reassign_primary_home':False,'may_accept_conflict':False,
            'may_authorize_architecture':False,'may_apply':False,'may_activate':False
        },indent=2))
        return 2


if __name__=='__main__':
    raise SystemExit(main())
