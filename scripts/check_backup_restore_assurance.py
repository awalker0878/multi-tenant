#!/usr/bin/env python3
"""Validate exported backup protection and isolated-restore assurance evidence.

This repository is not a backup product, storage service, KMS, catalogue, or recovery
orchestrator. Records contain opaque external references and current assurance evidence.
No backup/restore operation, copy deletion, key operation, reconnect, or activation is
performed by this checker.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'sources/capabilities/backup_restore_assurance_index.json'
FORMAT='portable-hosting-backup-restore-assurance-index/1'
STATUS='EXPORTED_BACKUP_RESTORE_ASSURANCE_NOT_BACKUP_AUTHORITY'
STATES={'CURRENT_ASSURED','RESTORE_DUE','RETIREMENT_PENDING','UNCERTAIN'}
ID=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{1,191}$')
SHA=re.compile(r'^[0-9a-f]{64}$')
INDEX_KEYS={'format','status','reviewed_source_revision','records'}
RECORD_KEYS={
    'assurance_id','generation','state','request_id','wsd_engineering_ref',
    'backup_policy_ref','service_class_ref','policy_effective_at','policy_review_by',
    'profiles','management_separation','protected_copy','isolated_restore',
    'owners','exclusions','source_refs'
}
PROFILE_KEYS={
    'consistency','retention','location','key','protected_copy','capture',
    'data_path','restore_target','availability_recovery'
}
SEPARATION_KEYS={
    'consumer_management_access','production_copy_delete','production_retention_reduce',
    'production_required_key_destroy'
}
SEPARATION_ITEM_KEYS={'decision','evidence_ref','observed_at'}
PROTECTED_COPY_KEYS={
    'copy_ref','repository_ref','catalogue_ref','key_dependency_ref','captured_at',
    'retention_until','integrity_evidence_ref','catalogue_access_evidence_ref',
    'key_access_evidence_ref','lineage_evidence_ref'
}
RESTORE_KEYS={
    'restore_ref','test_set','copy_ref','isolated_target_ref','started_at',
    'recovered_point_at','service_accepted_at','evidence_valid_until',
    'consistency_evidence_ref','isolation_evidence_ref','useful_data_acceptance_ref',
    'identity_key_evidence_ref','rto_observed_seconds','rpo_observed_seconds',
    'rto_profile_ref','rpo_profile_ref','production_connection_during_restore'
}
OWNER_KEYS={'backup_owner_role','data_owner_role','recovery_owner_role','key_owner_role'}


def bounded(value,label,limit=512):
    if (not isinstance(value,str) or not value.strip() or len(value)>limit
            or any(ord(c)<32 or ord(c)==127 for c in value)):
        raise ValueError(f'{label}: bounded nonempty text required')
    return value


def identifier(value,label):
    bounded(value,label,192)
    if not ID.fullmatch(value):raise ValueError(f'{label}: invalid identifier')
    return value


def positive_int(value,label):
    if type(value) is not int or value<1:raise ValueError(f'{label}: positive integer required')
    return value


def instant(value,label):
    bounded(value,label,64)
    dt=datetime.fromisoformat(value.replace('Z','+00:00'))
    if dt.tzinfo is None:raise ValueError(f'{label}: timezone required')
    return dt.astimezone(timezone.utc)


def decimal_nonnegative(value,label):
    if not isinstance(value,str) or not value or len(value)>64:
        raise ValueError(f'{label}: decimal string required')
    try:n=Decimal(value)
    except InvalidOperation:raise ValueError(f'{label}: invalid decimal') from None
    if not n.is_finite() or n<0:raise ValueError(f'{label}: nonnegative finite decimal required')
    return n


def repository_ref(value,root=ROOT):
    bounded(value,'repository reference')
    p=Path(value)
    if p.is_absolute() or '..' in p.parts or '\\' in value or ':' in value:
        raise ValueError('Repository reference must be normalized and relative')
    if not (root/p).exists():raise ValueError(f'Repository reference does not exist: {value}')
    return value


def opaque_ref(value,label):
    bounded(value,label,256)
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.:-]{1,255}',value):
        raise ValueError(f'{label}: opaque external reference required')
    return value


def unique_strings(value,label,*,allow_empty=False,maximum=128):
    if not isinstance(value,list) or len(value)>maximum or (not allow_empty and not value):
        raise ValueError(f'{label}: bounded list required')
    if any(not isinstance(x,str) or not x.strip() for x in value):
        raise ValueError(f'{label}: nonempty strings required')
    if len(value)!=len(set(value)):raise ValueError(f'{label}: duplicates not allowed')
    return value


def load(path:Path=INDEX):
    with path.open('rb') as stream:raw=stream.read(1024*1024+1)
    if len(raw)>1024*1024:raise ValueError('Backup assurance index exceeds bounded size')
    def pairs(items):
        out={}
        for k,v in items:
            if k in out:raise ValueError('Duplicate JSON property')
            out[k]=v
        return out
    def reject(_):raise ValueError('Non-finite JSON number')
    value=json.loads(raw,object_pairs_hook=pairs,parse_constant=reject)
    if not isinstance(value,dict):raise ValueError('Backup assurance index must be an object')
    return value


def validate_record(record,*,as_of,root=ROOT):
    if not isinstance(record,dict) or set(record)!=RECORD_KEYS:
        raise ValueError('Backup assurance record has unexpected or missing fields')
    identifier(record['assurance_id'],'assurance_id')
    identifier(record['request_id'],'request_id')
    positive_int(record['generation'],'generation')
    if record['state'] not in STATES:raise ValueError('Unknown backup assurance state')
    repository_ref(record['wsd_engineering_ref'],root)
    opaque_ref(record['backup_policy_ref'],'backup_policy_ref')
    opaque_ref(record['service_class_ref'],'service_class_ref')
    effective=instant(record['policy_effective_at'],'policy_effective_at')
    review_by=instant(record['policy_review_by'],'policy_review_by')
    if effective>as_of or review_by<=effective:
        raise ValueError('Backup-policy chronology invalid')

    profiles=record['profiles']
    if not isinstance(profiles,dict) or set(profiles)!=PROFILE_KEYS:
        raise ValueError('Exact backup/recovery profile references required')
    for key,value in profiles.items():opaque_ref(value,f'profiles.{key}')

    separation=record['management_separation']
    if not isinstance(separation,dict) or set(separation)!=SEPARATION_KEYS:
        raise ValueError('Exact backup management/protection separation evidence required')
    normalized_sep={}
    for key,item in separation.items():
        if not isinstance(item,dict) or set(item)!=SEPARATION_ITEM_KEYS:
            raise ValueError('Backup separation item shape invalid')
        if item['decision']!='DENIED':
            raise ValueError(f'{key}: destructive/management authority must be denied to the disallowed role')
        opaque_ref(item['evidence_ref'],f'{key}.evidence_ref')
        observed=instant(item['observed_at'],f'{key}.observed_at')
        if observed>as_of:raise ValueError('Backup separation evidence is future-dated')
        normalized_sep[key]={'decision':'DENIED','evidence_ref':item['evidence_ref'],
                             'observed_at':observed.isoformat()}

    copy=record['protected_copy']
    if not isinstance(copy,dict) or set(copy)!=PROTECTED_COPY_KEYS:
        raise ValueError('Protected-copy evidence shape invalid')
    for key in ('copy_ref','repository_ref','catalogue_ref','key_dependency_ref',
                'integrity_evidence_ref','catalogue_access_evidence_ref',
                'key_access_evidence_ref','lineage_evidence_ref'):
        opaque_ref(copy[key],f'protected_copy.{key}')
    captured=instant(copy['captured_at'],'protected_copy.captured_at')
    retention_until=instant(copy['retention_until'],'protected_copy.retention_until')
    if captured>as_of or retention_until<=captured:
        raise ValueError('Protected-copy chronology invalid')

    restore=record['isolated_restore']
    if not isinstance(restore,dict) or set(restore)!=RESTORE_KEYS:
        raise ValueError('Isolated-restore evidence shape invalid')
    for key in ('restore_ref','test_set','copy_ref','isolated_target_ref',
                'consistency_evidence_ref','isolation_evidence_ref',
                'useful_data_acceptance_ref','identity_key_evidence_ref',
                'rto_profile_ref','rpo_profile_ref'):
        opaque_ref(restore[key],f'isolated_restore.{key}')
    if restore['copy_ref']!=copy['copy_ref']:
        raise ValueError('Isolated restore must use the protected copy recorded by this assurance')
    started=instant(restore['started_at'],'isolated_restore.started_at')
    recovered=instant(restore['recovered_point_at'],'isolated_restore.recovered_point_at')
    accepted=instant(restore['service_accepted_at'],'isolated_restore.service_accepted_at')
    evidence_valid_until=instant(restore['evidence_valid_until'],'isolated_restore.evidence_valid_until')
    if recovered>started or started>accepted or accepted>as_of or evidence_valid_until<=accepted:
        raise ValueError('Isolated-restore chronology invalid')
    decimal_nonnegative(restore['rto_observed_seconds'],'rto_observed_seconds')
    decimal_nonnegative(restore['rpo_observed_seconds'],'rpo_observed_seconds')
    if restore['production_connection_during_restore']!='DENIED':
        raise ValueError('Isolated restore cannot claim production connectivity before authorized reconnect')

    owners=record['owners']
    if not isinstance(owners,dict) or set(owners)!=OWNER_KEYS:
        raise ValueError('Backup/data/recovery/key owner roles required')
    for key in OWNER_KEYS:bounded(owners[key],key)
    exclusions=unique_strings(record['exclusions'],'exclusions',allow_empty=True)
    sources=unique_strings(record['source_refs'],'source_refs')
    for ref in sources:repository_ref(ref,root)

    stale=as_of>=evidence_valid_until or as_of>=review_by
    if record['state']=='CURRENT_ASSURED':
        if stale:raise ValueError('CURRENT_ASSURED record has expired policy or restore evidence')
        if retention_until<=as_of:
            raise ValueError('CURRENT_ASSURED record has no currently retained protected copy')
    elif record['state']=='RESTORE_DUE':
        if not stale:raise ValueError('RESTORE_DUE requires expired policy review or restore evidence')
    elif record['state']=='RETIREMENT_PENDING':
        if retention_until<=captured:raise ValueError('Retirement record lost retained-copy obligation')
    elif record['state']=='UNCERTAIN':
        pass

    return {
        'assurance_id':record['assurance_id'],'generation':record['generation'],
        'state':record['state'],'request_id':record['request_id'],
        'wsd_engineering_ref':record['wsd_engineering_ref'],
        'backup_policy_ref':record['backup_policy_ref'],'service_class_ref':record['service_class_ref'],
        'policy_review_by':review_by.isoformat(),'protected_copy_ref':copy['copy_ref'],
        'retention_until':retention_until.isoformat(),
        'restore_ref':restore['restore_ref'],'restore_evidence_valid_until':evidence_valid_until.isoformat(),
        'rto_observed_seconds':restore['rto_observed_seconds'],
        'rpo_observed_seconds':restore['rpo_observed_seconds'],
        'management_separation':normalized_sep,'unresolved':record['state']=='UNCERTAIN',
        'exclusions':sorted(exclusions)
    }


def validate(index,*,as_of=None,root=ROOT):
    if as_of is None:as_of=datetime.now(timezone.utc)
    if not isinstance(as_of,datetime) or as_of.tzinfo is None:raise ValueError('Timezone-aware as_of required')
    as_of=as_of.astimezone(timezone.utc)
    if set(index)!=INDEX_KEYS:raise ValueError('Unexpected backup assurance-index fields')
    if index['format']!=FORMAT or index['status']!=STATUS:
        raise ValueError('Unsupported backup assurance-index format or authority boundary')
    rev=index['reviewed_source_revision']
    if not isinstance(rev,str) or not re.fullmatch(r'[0-9a-f]{40}',rev):
        raise ValueError('Reviewed source revision must be an exact Git SHA')
    if not isinstance(index['records'],list) or len(index['records'])>1024:
        raise ValueError('Backup assurance records must be a bounded list')
    ids=set();request_ids=set();out=[]
    for raw in index['records']:
        item=validate_record(raw,as_of=as_of,root=root)
        if item['assurance_id'] in ids:raise ValueError('Duplicate backup assurance ID')
        if item['request_id'] in request_ids:raise ValueError('Duplicate active backup assurance for one request')
        ids.add(item['assurance_id']);request_ids.add(item['request_id']);out.append(item)
    return {
        'records':out,'record_count':len(out),
        'current_assured_count':sum(x['state']=='CURRENT_ASSURED' for x in out),
        'restore_due_count':sum(x['state']=='RESTORE_DUE' for x in out),
        'retirement_pending_count':sum(x['state']=='RETIREMENT_PENDING' for x in out),
        'unresolved_count':sum(x['unresolved'] for x in out)
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--index',type=Path,default=INDEX)
    p.add_argument('--as-of',help='ISO-8601 review instant; defaults to current UTC')
    a=p.parse_args()
    try:
        as_of=instant(a.as_of,'as_of') if a.as_of else datetime.now(timezone.utc)
        summary=validate(load(a.index),as_of=as_of)
        print(json.dumps({
            'status':'PASSED_EXPORTED_BACKUP_RESTORE_ASSURANCE','as_of':as_of.isoformat(),
            **{k:v for k,v in summary.items() if k!='records'},
            'may_access_backup_management':False,'may_capture_backup':False,
            'may_delete_copy':False,'may_destroy_key':False,'may_restore':False,
            'may_reconnect_restored_service':False,'may_apply':False,'may_activate':False,
            'limits':[
                'A successful backup job alone is not recovery assurance.',
                'CURRENT_ASSURED requires independent-protection evidence plus a current isolated useful-data restore witness.',
                'Observed RTO/RPO values are evidence; this checker does not invent or approve service objectives.',
                'The repository validates exported evidence only and never contacts a backup, storage, KMS, or recovery service.'
            ]
        },indent=2));return 0
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({
            'status':'FAILED_EXPORTED_BACKUP_RESTORE_ASSURANCE','reason':str(exc),
            'may_access_backup_management':False,'may_capture_backup':False,
            'may_delete_copy':False,'may_destroy_key':False,'may_restore':False,
            'may_reconnect_restored_service':False,'may_apply':False,'may_activate':False
        },indent=2));return 2


if __name__=='__main__':raise SystemExit(main())
