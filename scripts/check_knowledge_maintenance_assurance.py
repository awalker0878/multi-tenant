#!/usr/bin/env python3
"""Validate primary knowledge homes and release-maintenance assurance evidence.

This is a publishing/knowledge-integrity check, not an architecture approval service,
security authorization authority, Git merge controller, or infrastructure controller.
Static link/requirement checks do not create a maintained-release decision.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
REGISTRY=ROOT/'sources/documentation/knowledge_home_registry.json'
INDEX=ROOT/'sources/documentation/release_maintenance_assurance_index.json'
REGISTRY_FORMAT='portable-hosting-knowledge-home-registry/1'
REGISTRY_STATUS='SOURCE_DERIVED_PRIMARY_HOMES_NOT_MAINTENANCE_AUTHORITY'
FORMAT='portable-hosting-release-maintenance-assurance-index/1'
STATUS='EXPORTED_RELEASE_MAINTENANCE_EVIDENCE_NOT_PUBLICATION_AUTHORITY'
TOPIC_IDS={
    'SITE_CELL_FAILURE','FABRIC_ROUTING_ATTACHMENTS','PRIVILEGED_ACCESS',
    'TENANCY_NATIVE_PLATFORMS','SERVICE_DATA_TRUST_RECOVERY',
    'PROVISIONING_CHANGE','CAPACITY_OPERATIONS_ASSURANCE',
    'EXCEPTIONS_FUTURE_SERVICES'
}
VERSION_ROLES={
    'architecture','engineering','requirements','tests','gap_register',
    'source_reviews','knowledge_homes','generator'
}
STATES={'CURRENT_MAINTAINED','REVIEW_DUE','VALIDATION_DUE','CONFLICTS_OPEN','UNCERTAIN'}
REGISTRY_KEYS={'format','status','reviewed_source_revision','topics'}
TOPIC_KEYS={'id','parent_refs','primary_home_ref','related_home_refs','change_ripple'}
INDEX_KEYS={'format','status','reviewed_source_revision','records'}
RECORD_KEYS={
    'assurance_id','generation','state','release_id','reviewed_revision',
    'version_set','maintenance','validation','change_control',
    'unresolved_conflicts','source_refs'
}
MAINTENANCE_KEYS={'owner_ref','cadence_ref','reviewed_at','review_by'}
VALIDATION_KEYS={
    'documentation_check_ref','repository_check_ref','link_validation_ref',
    'requirement_mapping_ref','primary_home_review_ref',
    'duplicate_policy_review_ref','drift_review_ref',
    'scenario_consistency_ref','observed_at','valid_until','status'
}
CHANGE_KEYS={
    'change_record_ref','approval_ref','approved_at','owner_ref',
    'affected_topic_ids','ripple_review_ref'
}
ID=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{1,191}$')
SHA40=re.compile(r'^[0-9a-f]{40}$')


def bounded(value,label,limit=1024):
    if (not isinstance(value,str) or not value.strip() or len(value)>limit
            or any(ord(c)<32 or ord(c)==127 for c in value)):
        raise ValueError(f'{label}: bounded nonempty text required')
    return value


def identifier(value,label):
    bounded(value,label,192)
    if not ID.fullmatch(value):
        raise ValueError(f'{label}: invalid identifier')
    return value


def positive_int(value,label):
    if type(value) is not int or value<1:
        raise ValueError(f'{label}: positive integer required')
    return value


def instant(value,label):
    bounded(value,label,64)
    dt=datetime.fromisoformat(value.replace('Z','+00:00'))
    if dt.tzinfo is None:
        raise ValueError(f'{label}: timezone required')
    return dt.astimezone(timezone.utc)


def opaque_ref(value,label):
    bounded(value,label,256)
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.:-]{1,255}',value):
        raise ValueError(f'{label}: opaque controlled reference required')
    return value


def unique_strings(value,label,*,allow_empty=False,maximum=128):
    if not isinstance(value,list) or len(value)>maximum or (not allow_empty and not value):
        raise ValueError(f'{label}: bounded list required')
    if any(not isinstance(x,str) or not x.strip() for x in value):
        raise ValueError(f'{label}: nonempty strings required')
    if len(value)!=len(set(value)):
        raise ValueError(f'{label}: duplicates not allowed')
    return value


def repository_ref(value,root=ROOT):
    bounded(value,'repository reference')
    p=Path(value)
    if p.is_absolute() or '..' in p.parts or '\\' in value or ':' in value or '#' in value:
        raise ValueError('Repository reference must be a normalized relative file path')
    if not (root/p).is_file():
        raise ValueError(f'Repository file reference does not exist: {value}')
    return value


def anchored_ref(value,root=ROOT):
    bounded(value,'anchored repository reference')
    if value.count('#')!=1:
        raise ValueError('Anchored repository reference must contain one fragment')
    path,fragment=value.split('#',1)
    repository_ref(path,root)
    bounded(fragment,'fragment',192)
    text=(root/path).read_text(errors='replace')
    if f'id="{fragment}"' not in text and f"id='{fragment}'" not in text:
        raise ValueError(f'Anchored repository fragment does not exist: {value}')
    return value


def load_json(path:Path,limit=1024*1024):
    with path.open('rb') as stream:
        raw=stream.read(limit+1)
    if len(raw)>limit:
        raise ValueError(f'{path.name} exceeds bounded size')
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
        raise ValueError(f'{path.name} must be an object')
    return value


def load_registry(path:Path=REGISTRY):
    return load_json(path)


def load(path:Path=INDEX):
    return load_json(path)


def validate_registry(registry,*,root=ROOT):
    if set(registry)!=REGISTRY_KEYS:
        raise ValueError('Unexpected knowledge-home registry fields')
    if registry['format']!=REGISTRY_FORMAT or registry['status']!=REGISTRY_STATUS:
        raise ValueError('Unsupported knowledge-home registry format or authority boundary')
    if not isinstance(registry['reviewed_source_revision'],str) or not SHA40.fullmatch(registry['reviewed_source_revision']):
        raise ValueError('Knowledge-home reviewed source revision must be an exact Git SHA')
    topics=registry['topics']
    if not isinstance(topics,list) or len(topics)!=len(TOPIC_IDS):
        raise ValueError('Knowledge-home registry must represent the complete reviewed topic set')
    ids=set()
    primary=set()
    normalized=[]
    for item in topics:
        if not isinstance(item,dict) or set(item)!=TOPIC_KEYS:
            raise ValueError('Knowledge-home topic shape invalid')
        if item['id'] not in TOPIC_IDS or item['id'] in ids:
            raise ValueError('Knowledge-home topic ID is unknown or duplicated')
        ids.add(item['id'])
        parents=unique_strings(item['parent_refs'],'parent_refs')
        related=unique_strings(item['related_home_refs'],'related_home_refs',allow_empty=True)
        for ref in parents+related:
            anchored_ref(ref,root)
        primary_ref=anchored_ref(item['primary_home_ref'],root)
        if primary_ref in primary:
            raise ValueError('Two topics cannot silently share one primary knowledge home')
        primary.add(primary_ref)
        bounded(item['change_ripple'],'change_ripple')
        normalized.append({
            'id':item['id'],
            'primary_home_ref':primary_ref,
            'parent_refs':sorted(parents),
            'related_home_refs':sorted(related),
            'change_ripple':item['change_ripple']
        })
    if ids!=TOPIC_IDS:
        raise ValueError('Knowledge-home topic set is incomplete')
    return {'topics':sorted(normalized,key=lambda x:x['id']),'topic_count':len(normalized)}


def validate_record(record,*,as_of,registry_summary,root=ROOT):
    if not isinstance(record,dict) or set(record)!=RECORD_KEYS:
        raise ValueError('Release-maintenance record has unexpected or missing fields')
    identifier(record['assurance_id'],'assurance_id')
    identifier(record['release_id'],'release_id')
    positive_int(record['generation'],'generation')
    if record['state'] not in STATES:
        raise ValueError('Unknown release-maintenance state')
    if not isinstance(record['reviewed_revision'],str) or not SHA40.fullmatch(record['reviewed_revision']):
        raise ValueError('Release-maintenance reviewed_revision must be an exact Git SHA')

    version_set=record['version_set']
    if not isinstance(version_set,dict) or set(version_set)!=VERSION_ROLES:
        raise ValueError('Complete version-set role map required')
    seen_paths=set()
    for role,path in version_set.items():
        repository_ref(path,root)
        if path in seen_paths:
            raise ValueError('Version-set roles must not alias the same file')
        seen_paths.add(path)

    maintenance=record['maintenance']
    if not isinstance(maintenance,dict) or set(maintenance)!=MAINTENANCE_KEYS:
        raise ValueError('Maintenance owner/cadence shape invalid')
    opaque_ref(maintenance['owner_ref'],'maintenance.owner_ref')
    opaque_ref(maintenance['cadence_ref'],'maintenance.cadence_ref')
    reviewed=instant(maintenance['reviewed_at'],'maintenance.reviewed_at')
    review_by=instant(maintenance['review_by'],'maintenance.review_by')
    if reviewed>as_of or review_by<=reviewed:
        raise ValueError('Maintenance review chronology invalid')

    validation=record['validation']
    if not isinstance(validation,dict) or set(validation)!=VALIDATION_KEYS:
        raise ValueError('Release validation evidence shape invalid')
    for key in VALIDATION_KEYS-{'observed_at','valid_until','status'}:
        opaque_ref(validation[key],f'validation.{key}')
    observed=instant(validation['observed_at'],'validation.observed_at')
    valid_until=instant(validation['valid_until'],'validation.valid_until')
    if observed>as_of or valid_until<=observed:
        raise ValueError('Release validation chronology invalid')
    if validation['status']!='PASSED_RELEASE_INTEGRITY':
        raise ValueError('Release validation status is not a passing integrity review')

    change=record['change_control']
    if not isinstance(change,dict) or set(change)!=CHANGE_KEYS:
        raise ValueError('Change-control evidence shape invalid')
    for key in ('change_record_ref','approval_ref','owner_ref','ripple_review_ref'):
        opaque_ref(change[key],f'change_control.{key}')
    approved=instant(change['approved_at'],'change_control.approved_at')
    if approved<observed or approved>as_of:
        raise ValueError('Approved change record must follow the recorded release validation')
    topics=unique_strings(change['affected_topic_ids'],'change_control.affected_topic_ids')
    if not set(topics)<=TOPIC_IDS:
        raise ValueError('Change-control ripple review references an unknown knowledge topic')

    conflicts=unique_strings(record['unresolved_conflicts'],'unresolved_conflicts',allow_empty=True)
    refs=unique_strings(record['source_refs'],'source_refs')
    for ref in refs:
        repository_ref(ref,root)

    review_due=as_of>=review_by
    validation_due=as_of>=valid_until
    if record['state']=='CURRENT_MAINTAINED':
        if review_due or validation_due:
            raise ValueError('CURRENT_MAINTAINED has expired maintenance or validation evidence')
        if conflicts:
            raise ValueError('CURRENT_MAINTAINED cannot carry unresolved policy/drift conflicts')
    elif record['state']=='REVIEW_DUE':
        if not review_due:
            raise ValueError('REVIEW_DUE requires expired maintenance review')
    elif record['state']=='VALIDATION_DUE':
        if review_due or not validation_due:
            raise ValueError('VALIDATION_DUE requires current maintenance review and expired validation')
    elif record['state']=='CONFLICTS_OPEN':
        if review_due or validation_due or not conflicts:
            raise ValueError('CONFLICTS_OPEN requires current evidence and unresolved conflicts')
    elif record['state']=='UNCERTAIN':
        pass

    return {
        'assurance_id':record['assurance_id'],
        'generation':record['generation'],
        'state':record['state'],
        'release_id':record['release_id'],
        'reviewed_revision':record['reviewed_revision'],
        'review_by':review_by.isoformat(),
        'validation_valid_until':valid_until.isoformat(),
        'affected_topic_ids':sorted(topics),
        'unresolved_conflicts':sorted(conflicts),
        'knowledge_topic_count':registry_summary['topic_count']
    }


def validate(index,*,as_of=None,root=ROOT,registry=None):
    if as_of is None:
        as_of=datetime.now(timezone.utc)
    if not isinstance(as_of,datetime) or as_of.tzinfo is None:
        raise ValueError('Timezone-aware as_of required')
    as_of=as_of.astimezone(timezone.utc)
    registry_summary=validate_registry(registry or load_registry(),root=root)
    if set(index)!=INDEX_KEYS:
        raise ValueError('Unexpected release-maintenance assurance-index fields')
    if index['format']!=FORMAT or index['status']!=STATUS:
        raise ValueError('Unsupported release-maintenance format or authority boundary')
    if not isinstance(index['reviewed_source_revision'],str) or not SHA40.fullmatch(index['reviewed_source_revision']):
        raise ValueError('Release-maintenance reviewed source revision must be an exact Git SHA')
    records=index['records']
    if not isinstance(records,list) or len(records)>128:
        raise ValueError('Release-maintenance records must be a bounded list')
    ids=set(); releases=set(); out=[]
    for raw in records:
        item=validate_record(raw,as_of=as_of,registry_summary=registry_summary,root=root)
        if item['assurance_id'] in ids:
            raise ValueError('Duplicate release-maintenance assurance ID')
        if item['release_id'] in releases:
            raise ValueError('Duplicate active maintenance record for one release')
        ids.add(item['assurance_id']);releases.add(item['release_id']);out.append(item)
    return {
        'records':out,
        'knowledge_topic_count':registry_summary['topic_count'],
        'record_count':len(out),
        'current_maintained_count':sum(x['state']=='CURRENT_MAINTAINED' for x in out),
        'review_due_count':sum(x['state']=='REVIEW_DUE' for x in out),
        'validation_due_count':sum(x['state']=='VALIDATION_DUE' for x in out),
        'conflicts_open_count':sum(x['state']=='CONFLICTS_OPEN' for x in out),
        'uncertain_count':sum(x['state']=='UNCERTAIN' for x in out)
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--index',type=Path,default=INDEX)
    p.add_argument('--registry',type=Path,default=REGISTRY)
    p.add_argument('--as-of',help='ISO-8601 review instant; defaults to current UTC')
    a=p.parse_args()
    try:
        as_of=instant(a.as_of,'as_of') if a.as_of else datetime.now(timezone.utc)
        summary=validate(load(a.index),as_of=as_of,registry=load_registry(a.registry))
        print(json.dumps({
            'status':'PASSED_KNOWLEDGE_MAINTENANCE_ASSURANCE',
            'as_of':as_of.isoformat(),
            **{k:v for k,v in summary.items() if k!='records'},
            'may_publish_release':False,
            'may_approve_change':False,
            'may_reassign_primary_home':False,
            'may_accept_conflict':False,
            'may_authorize_architecture':False,
            'may_apply':False,
            'may_activate':False,
            'limits':[
                'Static link and requirement checks do not create a maintained-release decision.',
                'Primary homes are source-derived routing for knowledge, not authority to overwrite parent architecture.',
                'Duplicate-policy and drift review remain attributable release evidence, not inferred from matching words.',
                'The repository validates exported maintenance evidence only and never approves or publishes a release.'
            ]
        },indent=2))
        return 0
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({
            'status':'FAILED_KNOWLEDGE_MAINTENANCE_ASSURANCE',
            'reason':str(exc),
            'may_publish_release':False,
            'may_approve_change':False,
            'may_reassign_primary_home':False,
            'may_accept_conflict':False,
            'may_authorize_architecture':False,
            'may_apply':False,
            'may_activate':False
        },indent=2))
        return 2


if __name__=='__main__':
    raise SystemExit(main())
