#!/usr/bin/env python3
"""Evaluate storage data-lifecycle readiness without mutating storage."""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from scripts import check_storage_data_lifecycle_assurance as assurance

FORMAT='portable-hosting-storage-data-lifecycle-readiness-intent/1'
STATUS='PLANNING_ONLY_NOT_AUTHORIZED'
READY='STORAGE_DATA_LIFECYCLE_CURRENT_NO_STORAGE_MUTATION_AUTHORIZED'
HOLD_NONE='HOLD_NO_CURRENT_STORAGE_LIFECYCLE_ASSURANCE'
HOLD_REVIEW='HOLD_STORAGE_LIFECYCLE_REVIEW_DUE'
HOLD_SERVICE='HOLD_STORAGE_SERVICE_TEST_DUE'
HOLD_LIFECYCLE='HOLD_STORAGE_COPY_SANITIZATION_DUE'
HOLD_GAPS='HOLD_STORAGE_LIFECYCLE_GAPS_OPEN'
HOLD_UNCERTAIN='HOLD_STORAGE_LIFECYCLE_UNCERTAIN'
HOLD_SCOPE='HOLD_STORAGE_LIFECYCLE_SCOPE_MISMATCH'
INTENT_KEYS={
    'format','status','request_id','storage_id','site_ref','service_class_ref',
    'platform_profile_ref','storage_profile_ref','production_authority','source_refs'
}


def load(path):
    with Path(path).open('rb') as s:
        raw=s.read(1024*1024+1)
    if len(raw)>1024*1024:
        raise ValueError('Storage readiness intent exceeds bounded size')
    value=json.loads(raw)
    if not isinstance(value,dict):
        raise ValueError('Storage readiness intent must be an object')
    return value


def validate_intent(i):
    if set(i)!=INTENT_KEYS or i['format']!=FORMAT or i['status']!=STATUS:
        raise ValueError('Unsupported storage readiness intent')
    assurance.identifier(i['request_id'],'request_id')
    assurance.identifier(i['storage_id'],'storage_id')
    for k in ('site_ref','service_class_ref','platform_profile_ref','storage_profile_ref'):
        assurance.opaque_ref(i[k],k)
    if i['production_authority']!='NOT_ASSESSED':
        raise ValueError('Storage readiness cannot carry production authority')
    for ref in assurance.unique_strings(i['source_refs'],'source_refs'):
        assurance.repository_ref(ref)


def evaluate(intent,index=None,as_of=None):
    if as_of is None:
        as_of=datetime.now(timezone.utc)
    if as_of.tzinfo is None:
        raise ValueError('Timezone-aware as_of required')
    as_of=as_of.astimezone(timezone.utc)
    validate_intent(intent)
    if index is None:
        index=assurance.load()
    summary=assurance.validate(index,as_of)
    records=[x for x in summary['records'] if x['storage_id']==intent['storage_id']]
    r=records[0] if records else None
    if r is None: result=HOLD_NONE
    elif r['state']=='UNCERTAIN': result=HOLD_UNCERTAIN
    elif r['state']=='REVIEW_DUE': result=HOLD_REVIEW
    elif r['state']=='SERVICE_TEST_DUE': result=HOLD_SERVICE
    elif r['state']=='LIFECYCLE_DUE': result=HOLD_LIFECYCLE
    elif r['state']=='GAPS_OPEN': result=HOLD_GAPS
    elif any([
        r['site_ref']!=intent['site_ref'],
        r['service_class_ref']!=intent['service_class_ref'],
        r['platform_profile_ref']!=intent['platform_profile_ref'],
        r['storage_profile_ref']!=intent['storage_profile_ref'],
    ]): result=HOLD_SCOPE
    else: result=READY

    return {
        'kind':'STORAGE_DATA_LIFECYCLE_READINESS_PREFLIGHT','status':result,
        'request_id':intent['request_id'],'storage_id':intent['storage_id'],
        'assurance_id':r['assurance_id'] if r else None,
        'protection_assurance_ref':r['protection_assurance_ref'] if r else None,
        'open_gap_ids':r['open_gap_ids'] if r else [],
        'may_provision_storage':False,'may_attach_storage':False,
        'may_snapshot_or_clone':False,'may_export_data':False,
        'may_delete_copy':False,'may_sanitize_media':False,
        'may_release_reuse':False,'may_apply':False,'may_activate':False,
        'next_owner_action':{
            READY:'Use this only as evidence that the exact storage service profile is current; native storage mutations remain with the storage authority.',
            HOLD_NONE:'Publish current ownership/lineage, service-semantics, copy/hold and sanitization-procedure evidence for the exact storage profile.',
            HOLD_REVIEW:'Refresh the storage-profile or residual-gap review.',
            HOLD_SERVICE:'Repeat ownership/cross-scope and capacity/performance/consistency/replication/snapshot/portability tests.',
            HOLD_LIFECYCLE:'Refresh copy catalogue/lineage/hold/key-version evidence and the qualified retirement/sanitization procedure.',
            HOLD_GAPS:'Resolve or formally disposition every OPEN storage lifecycle gap.',
            HOLD_UNCERTAIN:'Reconcile the authoritative storage, copy, hold and lifecycle state.',
            HOLD_SCOPE:'Use evidence for the exact site/service/platform/storage profile scope.'
        }[result],
        'limits':[
            'A ready result is not storage provisioning, export, deletion or sanitization authority.',
            'Actual resource retirement still requires current copy/hold reconciliation and a resource-specific sanitization receipt.',
            'CI never mutates storage or activates production.'
        ]
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('intent',type=Path)
    p.add_argument('--as-of')
    p.add_argument('--expected-status',choices=(READY,HOLD_NONE,HOLD_REVIEW,HOLD_SERVICE,HOLD_LIFECYCLE,HOLD_GAPS,HOLD_UNCERTAIN,HOLD_SCOPE))
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
            'kind':'STORAGE_DATA_LIFECYCLE_READINESS_PREFLIGHT',
            'status':'INVALID_STORAGE_DATA_LIFECYCLE_READINESS_INTENT','reason':str(exc),
            'may_provision_storage':False,'may_attach_storage':False,
            'may_snapshot_or_clone':False,'may_export_data':False,
            'may_delete_copy':False,'may_sanitize_media':False,
            'may_release_reuse':False,'may_apply':False,'may_activate':False
        },indent=2)); return 2


if __name__=='__main__':
    raise SystemExit(main())
