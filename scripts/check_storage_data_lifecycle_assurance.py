#!/usr/bin/env python3
"""Validate exported storage ownership, service-semantics and lifecycle assurance evidence.

This repository is not a storage controller, snapshot manager, copy catalogue, backup
system, sanitization executor or legal-hold authority. Records contain opaque references
to externally owned storage decisions and observations. The checker never provisions,
attaches, snapshots, exports, deletes, sanitizes or releases a storage resource.
"""
from __future__ import annotations
import argparse, json, re
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'sources/capabilities/storage_data_lifecycle_assurance_index.json'
FORMAT='portable-hosting-storage-data-lifecycle-assurance-index/1'
STATUS='EXPORTED_STORAGE_LIFECYCLE_EVIDENCE_NOT_STORAGE_AUTHORITY'
STATES={'CURRENT_QUALIFIED','REVIEW_DUE','SERVICE_TEST_DUE','LIFECYCLE_DUE','GAPS_OPEN','UNCERTAIN'}
GAP_STATES={'OPEN','ACCEPTED'}
ID=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{1,191}$')

INDEX_KEYS={'format','status','reviewed_source_revision','records'}
RECORD_KEYS={
    'assurance_id','generation','state','storage_id','scope',
    'ownership_lineage','service_semantics','copy_inventory',
    'release_sanitization','residual_gaps','source_refs'
}
SCOPE_KEYS={
    'site_ref','service_class_ref','platform_profile_ref','storage_profile_ref',
    'protection_assurance_ref','owner_ref','accepted_at','review_by'
}
OWNERSHIP_KEYS={
    'resource_owner_ref','categorization_ref','access_scope_ref','key_policy_ref',
    'placement_retention_ref','lineage_ref','cross_scope_authorization_ref',
    'cross_scope_deny_test_ref','observed_at','valid_until'
}
SEMANTIC_KEYS={
    'capacity_ref','performance_ref','consistency_ref','replication_ref',
    'snapshot_clone_ref','portability_ref','contention_test_ref',
    'accepted_failure_test_ref','observed_at','valid_until'
}
COPY_KEYS={
    'copy_catalogue_ref','derivative_lineage_ref','retained_copy_ref',
    'hold_register_ref','key_version_mapping_ref','copy_authority_ref',
    'observed_at','valid_until'
}
SANITIZE_KEYS={
    'withdrawal_procedure_ref','copy_hold_reconciliation_test_ref',
    'sanitization_method_ref','sanitization_verification_test_ref',
    'receipt_schema_ref','exception_process_ref','observed_at','valid_until'
}
GAP_KEYS={'gap_id','status','owner_ref','treatment_ref','decision_ref','review_by'}


def bounded(v,label,limit=1024):
    if not isinstance(v,str) or not v.strip() or len(v)>limit or any(ord(c)<32 or ord(c)==127 for c in v):
        raise ValueError(f'{label}: bounded nonempty text required')
    return v


def identifier(v,label):
    bounded(v,label,192)
    if not ID.fullmatch(v):
        raise ValueError(f'{label}: invalid identifier')
    return v


def positive_int(v,label):
    if type(v) is not int or v<1:
        raise ValueError(f'{label}: positive integer required')
    return v


def instant(v,label):
    bounded(v,label,64)
    dt=datetime.fromisoformat(v.replace('Z','+00:00'))
    if dt.tzinfo is None:
        raise ValueError(f'{label}: timezone required')
    return dt.astimezone(timezone.utc)


def opaque_ref(v,label):
    bounded(v,label,256)
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.:-]{1,255}',v):
        raise ValueError(f'{label}: opaque controlled reference required')
    return v


def repository_ref(v,root=ROOT):
    bounded(v,'repository reference')
    p=Path(v)
    if p.is_absolute() or '..' in p.parts or '\\' in v or ':' in v:
        raise ValueError('Repository reference must be normalized and relative')
    if not (root/p).exists():
        raise ValueError(f'Repository reference does not exist: {v}')
    return v


def unique_strings(v,label,allow_empty=False,maximum=128):
    if not isinstance(v,list) or len(v)>maximum or (not allow_empty and not v):
        raise ValueError(f'{label}: bounded list required')
    if any(not isinstance(x,str) or not x.strip() for x in v):
        raise ValueError(f'{label}: nonempty strings required')
    if len(v)!=len(set(v)):
        raise ValueError(f'{label}: duplicates not allowed')
    return v


def load(path:Path=INDEX):
    with path.open('rb') as s:
        raw=s.read(1024*1024+1)
    if len(raw)>1024*1024:
        raise ValueError('Storage lifecycle assurance index exceeds bounded size')
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
        raise ValueError('Storage lifecycle assurance index must be an object')
    return value


def evidence_block(value,keys,label,as_of):
    if not isinstance(value,dict) or set(value)!=keys:
        raise ValueError(f'{label}: evidence shape invalid')
    for key in keys-{'observed_at','valid_until'}:
        opaque_ref(value[key],f'{label}.{key}')
    observed=instant(value['observed_at'],f'{label}.observed_at')
    valid=instant(value['valid_until'],f'{label}.valid_until')
    if observed>as_of or valid<=observed:
        raise ValueError(f'{label}: chronology invalid')
    return observed,valid


def validate_record(record,as_of,root=ROOT):
    if not isinstance(record,dict) or set(record)!=RECORD_KEYS:
        raise ValueError('Storage lifecycle assurance record has unexpected or missing fields')
    identifier(record['assurance_id'],'assurance_id')
    identifier(record['storage_id'],'storage_id')
    positive_int(record['generation'],'generation')
    if record['state'] not in STATES:
        raise ValueError('Unknown storage lifecycle assurance state')

    scope=record['scope']
    if not isinstance(scope,dict) or set(scope)!=SCOPE_KEYS:
        raise ValueError('Storage assurance scope shape invalid')
    for k in ('site_ref','service_class_ref','platform_profile_ref','storage_profile_ref','protection_assurance_ref','owner_ref'):
        opaque_ref(scope[k],f'scope.{k}')
    accepted=instant(scope['accepted_at'],'scope.accepted_at')
    review_by=instant(scope['review_by'],'scope.review_by')
    if accepted>as_of or review_by<=accepted:
        raise ValueError('Storage assurance scope chronology invalid')

    _,ownership_valid=evidence_block(record['ownership_lineage'],OWNERSHIP_KEYS,'ownership_lineage',as_of)
    _,semantics_valid=evidence_block(record['service_semantics'],SEMANTIC_KEYS,'service_semantics',as_of)
    _,copy_valid=evidence_block(record['copy_inventory'],COPY_KEYS,'copy_inventory',as_of)
    _,sanitization_valid=evidence_block(record['release_sanitization'],SANITIZE_KEYS,'release_sanitization',as_of)

    gaps=record['residual_gaps']
    if not isinstance(gaps,list) or len(gaps)>1024:
        raise ValueError('Residual storage gaps must be a bounded list')
    gap_ids=set();open_gaps=[];gap_reviews=[]
    for gap in gaps:
        if not isinstance(gap,dict) or set(gap)!=GAP_KEYS:
            raise ValueError('Residual storage gap shape invalid')
        gid=identifier(gap['gap_id'],'gap_id')
        if gid in gap_ids:
            raise ValueError('Duplicate residual storage gap ID')
        gap_ids.add(gid)
        if gap['status'] not in GAP_STATES:
            raise ValueError('Unknown residual storage gap state')
        opaque_ref(gap['owner_ref'],'gap.owner_ref')
        opaque_ref(gap['treatment_ref'],'gap.treatment_ref')
        gr=instant(gap['review_by'],'gap.review_by')
        gap_reviews.append(gr)
        if gap['status']=='OPEN':
            if gap['decision_ref'] is not None:
                raise ValueError('OPEN storage gap cannot carry acceptance decision')
            open_gaps.append(gid)
        else:
            opaque_ref(gap['decision_ref'],'gap.decision_ref')

    refs=unique_strings(record['source_refs'],'source_refs')
    for ref in refs:
        repository_ref(ref,root)

    review_due=as_of>=review_by or any(as_of>=x for x in gap_reviews)
    service_due=as_of>=min(ownership_valid,semantics_valid)
    lifecycle_due=as_of>=min(copy_valid,sanitization_valid)

    state=record['state']
    if state=='CURRENT_QUALIFIED':
        if review_due or service_due or lifecycle_due or open_gaps:
            raise ValueError('CURRENT_QUALIFIED storage evidence is stale or incomplete')
    elif state=='REVIEW_DUE':
        if not review_due:
            raise ValueError('REVIEW_DUE requires expired scope/gap review')
    elif state=='SERVICE_TEST_DUE':
        if review_due or not service_due:
            raise ValueError('SERVICE_TEST_DUE requires current review and stale ownership/service-semantics evidence')
    elif state=='LIFECYCLE_DUE':
        if review_due or service_due or not lifecycle_due:
            raise ValueError('LIFECYCLE_DUE requires current service evidence and stale copy/sanitization evidence')
    elif state=='GAPS_OPEN':
        if review_due or service_due or lifecycle_due or not open_gaps:
            raise ValueError('GAPS_OPEN requires current evidence and at least one OPEN residual gap')
    elif state=='UNCERTAIN':
        pass

    return {
        'assurance_id':record['assurance_id'],
        'generation':record['generation'],
        'state':state,
        'storage_id':record['storage_id'],
        'site_ref':scope['site_ref'],
        'service_class_ref':scope['service_class_ref'],
        'platform_profile_ref':scope['platform_profile_ref'],
        'storage_profile_ref':scope['storage_profile_ref'],
        'protection_assurance_ref':scope['protection_assurance_ref'],
        'review_by':review_by.isoformat(),
        'open_gap_ids':sorted(open_gaps),
    }


def validate(index,as_of=None,root=ROOT):
    if as_of is None:
        as_of=datetime.now(timezone.utc)
    if not isinstance(as_of,datetime) or as_of.tzinfo is None:
        raise ValueError('Timezone-aware as_of required')
    as_of=as_of.astimezone(timezone.utc)
    if set(index)!=INDEX_KEYS:
        raise ValueError('Unexpected storage lifecycle assurance-index fields')
    if index['format']!=FORMAT or index['status']!=STATUS:
        raise ValueError('Unsupported storage lifecycle assurance format or authority boundary')
    revision=index['reviewed_source_revision']
    if not isinstance(revision,str) or not re.fullmatch(r'[0-9a-f]{40}',revision):
        raise ValueError('Reviewed source revision must be an exact Git SHA')
    records=index['records']
    if not isinstance(records,list) or len(records)>512:
        raise ValueError('Storage lifecycle assurance records must be a bounded list')
    ids=set(); storage_ids=set(); out=[]
    for raw in records:
        item=validate_record(raw,as_of,root)
        if item['assurance_id'] in ids:
            raise ValueError('Duplicate storage assurance ID')
        if item['storage_id'] in storage_ids:
            raise ValueError('Duplicate active assurance for one storage profile')
        ids.add(item['assurance_id']); storage_ids.add(item['storage_id']); out.append(item)
    return {
        'records':out,'record_count':len(out),
        'current_qualified_count':sum(x['state']=='CURRENT_QUALIFIED' for x in out),
        'review_due_count':sum(x['state']=='REVIEW_DUE' for x in out),
        'service_test_due_count':sum(x['state']=='SERVICE_TEST_DUE' for x in out),
        'lifecycle_due_count':sum(x['state']=='LIFECYCLE_DUE' for x in out),
        'gaps_open_count':sum(x['state']=='GAPS_OPEN' for x in out),
        'uncertain_count':sum(x['state']=='UNCERTAIN' for x in out),
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--index',type=Path,default=INDEX)
    p.add_argument('--as-of')
    a=p.parse_args()
    try:
        as_of=instant(a.as_of,'as_of') if a.as_of else datetime.now(timezone.utc)
        summary=validate(load(a.index),as_of)
        print(json.dumps({
            'status':'PASSED_STORAGE_DATA_LIFECYCLE_ASSURANCE','as_of':as_of.isoformat(),
            **{k:v for k,v in summary.items() if k!='records'},
            'may_provision_storage':False,'may_attach_storage':False,
            'may_snapshot_or_clone':False,'may_export_data':False,
            'may_delete_copy':False,'may_sanitize_media':False,
            'may_release_reuse':False,'may_apply':False,'may_activate':False,
            'limits':[
                'A VM/volume resource does not establish physical placement, copy lineage or sanitization assurance.',
                'Backup/restore assurance remains a separate protection dependency.',
                'A qualified sanitization procedure is not an actual resource-retirement receipt.',
                'The repository validates exported evidence only and never mutates storage.'
            ]
        },indent=2)); return 0
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({
            'status':'FAILED_STORAGE_DATA_LIFECYCLE_ASSURANCE','reason':str(exc),
            'may_provision_storage':False,'may_attach_storage':False,
            'may_snapshot_or_clone':False,'may_export_data':False,
            'may_delete_copy':False,'may_sanitize_media':False,
            'may_release_reuse':False,'may_apply':False,'may_activate':False
        },indent=2)); return 2


if __name__=='__main__':
    raise SystemExit(main())
