#!/usr/bin/env python3
"""Evaluate backup/recovery assurance readiness without invoking backup or restore.

The preflight checks that a WSD/request is backed by one current assurance record whose
policy/service/profile scope matches the reviewed requirement. It never contacts a
backup product, storage service, KMS, catalogue, or restored workload.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from scripts import check_backup_restore_assurance as assurance

FORMAT='portable-hosting-backup-readiness-intent/1'
STATUS='PLANNING_ONLY_NOT_AUTHORIZED'
READY='BACKUP_RESTORE_ASSURANCE_CURRENT_NO_OPERATION_AUTHORIZED'
HOLD_NONE='HOLD_NO_CURRENT_BACKUP_ASSURANCE'
HOLD_DUE='HOLD_ISOLATED_RESTORE_OR_POLICY_REVIEW_DUE'
HOLD_UNCERTAIN='HOLD_BACKUP_RESTORE_ASSURANCE_UNCERTAIN'
HOLD_SCOPE='HOLD_BACKUP_POLICY_OR_PROFILE_SCOPE_MISMATCH'
INTENT_KEYS={'format','status','request_id','wsd_engineering_ref','backup_policy_ref',
             'service_class_ref','required_profiles','production_authority','source_refs'}
REQUIRED_PROFILE_KEYS={'consistency','retention','location','key','protected_copy',
                       'restore_target','availability_recovery'}
ID=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{1,191}$')


def bounded(value,label,limit=512):
    if (not isinstance(value,str) or not value.strip() or len(value)>limit
            or any(ord(c)<32 or ord(c)==127 for c in value)):
        raise ValueError(f'{label}: bounded nonempty text required')
    return value


def identifier(value,label):
    bounded(value,label,192)
    if not ID.fullmatch(value):raise ValueError(f'{label}: invalid identifier')
    return value


def repository_ref(value):
    bounded(value,'repository reference')
    p=Path(value)
    if p.is_absolute() or '..' in p.parts or '\\' in value or ':' in value:
        raise ValueError('Repository reference must be normalized and relative')
    if not (ROOT/p).exists():raise ValueError(f'Repository reference does not exist: {value}')
    return value


def load(path:Path):
    with path.open('rb') as stream:raw=stream.read(1024*1024+1)
    if len(raw)>1024*1024:raise ValueError('Backup readiness intent exceeds bounded size')
    def pairs(items):
        out={}
        for k,v in items:
            if k in out:raise ValueError('Duplicate JSON property')
            out[k]=v
        return out
    def reject(_):raise ValueError('Non-finite JSON number')
    value=json.loads(raw,object_pairs_hook=pairs,parse_constant=reject)
    if not isinstance(value,dict):raise ValueError('Backup readiness intent must be an object')
    return value


def validate_intent(intent):
    if set(intent)!=INTENT_KEYS or intent['format']!=FORMAT or intent['status']!=STATUS:
        raise ValueError('Unsupported backup-readiness intent shape or authority boundary')
    identifier(intent['request_id'],'request_id')
    repository_ref(intent['wsd_engineering_ref'])
    assurance.opaque_ref(intent['backup_policy_ref'],'backup_policy_ref')
    assurance.opaque_ref(intent['service_class_ref'],'service_class_ref')
    profiles=intent['required_profiles']
    if not isinstance(profiles,dict) or set(profiles)!=REQUIRED_PROFILE_KEYS:
        raise ValueError('Exact required backup/recovery profile references are required')
    for key,value in profiles.items():assurance.opaque_ref(value,f'required_profiles.{key}')
    if intent['production_authority']!='NOT_ASSESSED':
        raise ValueError('Backup readiness preflight cannot carry production authority')
    refs=intent['source_refs']
    if not isinstance(refs,list) or not refs or len(refs)!=len(set(refs)):
        raise ValueError('Unique source_refs required')
    for ref in refs:repository_ref(ref)


def evaluate(intent,*,index=None,as_of=None):
    if as_of is None:as_of=datetime.now(timezone.utc)
    if not isinstance(as_of,datetime) or as_of.tzinfo is None:
        raise ValueError('Timezone-aware as_of required')
    as_of=as_of.astimezone(timezone.utc)
    validate_intent(intent)
    if index is None:index=assurance.load()
    summary=assurance.validate(index,as_of=as_of)
    records=[x for x in summary['records'] if x['request_id']==intent['request_id']]
    if not records:
        result=HOLD_NONE;record=None
    else:
        record=records[0]
        if record['state']=='UNCERTAIN':
            result=HOLD_UNCERTAIN
        elif record['state'] in ('RESTORE_DUE','RETIREMENT_PENDING'):
            result=HOLD_DUE
        elif record['backup_policy_ref']!=intent['backup_policy_ref'] or record['service_class_ref']!=intent['service_class_ref']:
            result=HOLD_SCOPE
        else:
            # The full profile map is validated in the source record. Re-read raw
            # record by immutable assurance ID to compare the requested subset.
            raw=next(x for x in index['records'] if x['assurance_id']==record['assurance_id'])
            if any(raw['profiles'][k]!=v for k,v in intent['required_profiles'].items()):
                result=HOLD_SCOPE
            else:
                result=READY

    return {
        'kind':'BACKUP_RESTORE_READINESS_PREFLIGHT','status':result,
        'request_id':intent['request_id'],
        'assurance_id':record['assurance_id'] if record else None,
        'backup_policy_ref':intent['backup_policy_ref'],
        'may_access_backup_management':False,'may_capture_backup':False,
        'may_delete_copy':False,'may_destroy_key':False,'may_restore':False,
        'may_reconnect_restored_service':False,'may_apply':False,'may_activate':False,
        'next_owner_action':{
            READY:'Use this current assurance only as a readiness prerequisite; any real backup/restore/reconnect action still requires its owning approved procedure.',
            HOLD_NONE:'Establish a current BackupPolicy, independent protected-copy evidence and isolated useful-data restore evidence.',
            HOLD_DUE:'Repeat/review the isolated restore or policy evidence at its accepted cadence before offering the service promise.',
            HOLD_UNCERTAIN:'Reconcile backup/copy/catalogue/key/restore state before relying on the assurance.',
            HOLD_SCOPE:'Align the BackupPolicy/service/profile scope with the reviewed WSD requirement; do not silently substitute a weaker service.'
        }[result],
        'limits':[
            'A ready result is not a backup job, restore authorization, reconnect approval or production authorization.',
            'The checker does not compare RTO/RPO against invented thresholds; those objectives live in the approved recovery profiles.',
            'Actual copy, catalogue, key, storage and application data remain in their authoritative systems.',
            'Backup consumption never grants access to backup management interfaces.'
        ]
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('intent',type=Path)
    p.add_argument('--as-of',help='ISO-8601 review instant; defaults to current UTC')
    p.add_argument('--expected-status',choices=(READY,HOLD_NONE,HOLD_DUE,HOLD_UNCERTAIN,HOLD_SCOPE))
    a=p.parse_args()
    try:
        as_of=assurance.instant(a.as_of,'as_of') if a.as_of else datetime.now(timezone.utc)
        result=evaluate(load(a.intent),as_of=as_of)
        print(json.dumps(result,indent=2))
        if a.expected_status is not None:return 0 if result['status']==a.expected_status else 2
        return 0 if result['status']==READY else 2
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({
            'kind':'BACKUP_RESTORE_READINESS_PREFLIGHT','status':'INVALID_BACKUP_READINESS_INTENT',
            'reason':str(exc),'may_access_backup_management':False,'may_capture_backup':False,
            'may_delete_copy':False,'may_destroy_key':False,'may_restore':False,
            'may_reconnect_restored_service':False,'may_apply':False,'may_activate':False
        },indent=2));return 2


if __name__=='__main__':raise SystemExit(main())
