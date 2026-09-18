#!/usr/bin/env python3
"""Validate exact-tuple version, source-provenance, compatibility and lifecycle evidence.

This repository is not a vendor support portal, package registry, vulnerability scanner,
licensing system or native qualification authority. Records contain opaque references
to externally controlled source/support evidence. A current record is a prerequisite
for native qualification; it is not native qualification by itself.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'sources/capabilities/version_source_provenance_index.json'
FORMAT='portable-hosting-version-source-provenance-index/1'
STATUS='EXPORTED_VERSION_SOURCE_PROVENANCE_NOT_NATIVE_QUALIFICATION'
STATES={'CURRENT_SUPPORTED','REVIEW_DUE','UNSUPPORTED','UNCERTAIN'}
PLATFORMS={'nutanix','vmware-nsx','openstack'}
SOURCE_KINDS={
    'PRODUCT_SUPPORT','API_REFERENCE','AUTOMATION_PROVIDER',
    'HARDWARE_COMPATIBILITY','RELEASE_NOTES','FEATURE_ENTITLEMENT'
}
BASE_REQUIRED_KINDS={
    'PRODUCT_SUPPORT','API_REFERENCE','AUTOMATION_PROVIDER',
    'HARDWARE_COMPATIBILITY','RELEASE_NOTES'
}
REVIEW_STATES={'CURRENT_REVIEWED','PARTIAL_ACCESS','INHERITED_NOT_REVERIFIED'}
SUPPORT_STATES={'SUPPORTED','SUPPORT_END_SCHEDULED','UNSUPPORTED','UNKNOWN'}
ID=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{1,191}$')
INDEX_KEYS={'format','status','reviewed_source_revision','records'}
RECORD_KEYS={
    'provenance_id','generation','state','platform','product_tuple_id',
    'product_tuple','source_reviews','compatibility','lifecycle',
    'owners','exclusions','source_refs'
}
TUPLE_KEYS={
    'product','product_version','api','api_version','automation_providers',
    'hardware_profile_ref','feature_licenses'
}
SOURCE_KEYS={
    'source_id','kind','edition','review_state','reviewed_at','valid_until',
    'evidence_ref','limitation'
}
COMPAT_KEYS={
    'compatibility_record_ref','assessed_at','valid_until',
    'product_api_evidence_ref','provider_evidence_refs','hardware_evidence_ref',
    'operation_coverage_ref','feature_entitlement_evidence_refs','exceptions'
}
LIFECYCLE_KEYS={
    'support_status','support_evidence_ref','reviewed_at','review_by',
    'support_end_at','vulnerability_owner_ref','lifecycle_decision_ref'
}
OWNER_KEYS={
    'platform_engineering_role','architecture_role','vulnerability_management_role'
}


def bounded(value,label,limit=512):
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


def repository_ref(value,root=ROOT):
    bounded(value,'repository reference')
    p=Path(value)
    if p.is_absolute() or '..' in p.parts or '\\' in value or ':' in value:
        raise ValueError('Repository reference must be normalized and relative')
    if not (root/p).exists():
        raise ValueError(f'Repository reference does not exist: {value}')
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
    if len(value)!=len(set(value)):
        raise ValueError(f'{label}: duplicates not allowed')
    return value


def load(path:Path=INDEX):
    with path.open('rb') as stream:
        raw=stream.read(1024*1024+1)
    if len(raw)>1024*1024:
        raise ValueError('Version/source provenance index exceeds bounded size')
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
        raise ValueError('Version/source provenance index must be an object')
    return value


def validate_product_tuple(value):
    if not isinstance(value,dict) or set(value)!=TUPLE_KEYS:
        raise ValueError('Exact product/API/provider/hardware tuple fields required')
    for key in ('product','product_version','api','api_version','hardware_profile_ref'):
        bounded(value[key],f'product_tuple.{key}')
    providers=unique_strings(value['automation_providers'],'automation_providers')
    licenses=unique_strings(value['feature_licenses'],'feature_licenses',allow_empty=True)
    return providers,licenses


def validate_record(record,*,as_of,root=ROOT):
    if not isinstance(record,dict) or set(record)!=RECORD_KEYS:
        raise ValueError('Version/source provenance record has unexpected or missing fields')
    identifier(record['provenance_id'],'provenance_id')
    positive_int(record['generation'],'generation')
    if record['state'] not in STATES:
        raise ValueError('Unknown version/source provenance state')
    if record['platform'] not in PLATFORMS:
        raise ValueError('Unknown platform family')
    identifier(record['product_tuple_id'],'product_tuple_id')
    providers,licenses=validate_product_tuple(record['product_tuple'])

    reviews=record['source_reviews']
    if not isinstance(reviews,list) or not reviews or len(reviews)>128:
        raise ValueError('Bounded source-review evidence is required')
    source_ids=set()
    current_kinds=set()
    expired_current_kinds=set()
    normalized_reviews=[]
    for item in reviews:
        if not isinstance(item,dict) or set(item)!=SOURCE_KEYS:
            raise ValueError('Source-review evidence shape invalid')
        source_id=identifier(item['source_id'],'source_id')
        if source_id in source_ids:
            raise ValueError('Duplicate source-review ID')
        source_ids.add(source_id)
        if item['kind'] not in SOURCE_KINDS:
            raise ValueError('Unknown source-review kind')
        bounded(item['edition'],'source_review.edition')
        if item['review_state'] not in REVIEW_STATES:
            raise ValueError('Unknown source-review state')
        reviewed=instant(item['reviewed_at'],'source_review.reviewed_at')
        valid_until=instant(item['valid_until'],'source_review.valid_until')
        if reviewed>as_of or valid_until<=reviewed:
            raise ValueError('Source-review chronology invalid')
        opaque_ref(item['evidence_ref'],'source_review.evidence_ref')
        bounded(item['limitation'],'source_review.limitation',1024)
        if item['review_state']=='CURRENT_REVIEWED':
            if as_of<valid_until:
                current_kinds.add(item['kind'])
            else:
                expired_current_kinds.add(item['kind'])
        normalized_reviews.append({
            'source_id':source_id,'kind':item['kind'],'edition':item['edition'],
            'review_state':item['review_state'],'valid_until':valid_until.isoformat()
        })

    required_kinds=set(BASE_REQUIRED_KINDS)
    if licenses:
        required_kinds.add('FEATURE_ENTITLEMENT')
    missing_current_kinds=required_kinds-current_kinds

    compat=record['compatibility']
    if not isinstance(compat,dict) or set(compat)!=COMPAT_KEYS:
        raise ValueError('Compatibility record shape invalid')
    for key in ('compatibility_record_ref','product_api_evidence_ref',
                'hardware_evidence_ref','operation_coverage_ref'):
        opaque_ref(compat[key],f'compatibility.{key}')
    provider_refs=unique_strings(
        compat['provider_evidence_refs'],'compatibility.provider_evidence_refs')
    for ref in provider_refs:
        opaque_ref(ref,'compatibility.provider_evidence_ref')
    feature_refs=unique_strings(
        compat['feature_entitlement_evidence_refs'],
        'compatibility.feature_entitlement_evidence_refs',allow_empty=True)
    for ref in feature_refs:
        opaque_ref(ref,'compatibility.feature_entitlement_evidence_ref')
    if licenses and not feature_refs:
        raise ValueError('Licensed feature tuple requires entitlement evidence')
    exceptions=unique_strings(compat['exceptions'],'compatibility.exceptions',allow_empty=True)
    assessed=instant(compat['assessed_at'],'compatibility.assessed_at')
    compat_valid=instant(compat['valid_until'],'compatibility.valid_until')
    if assessed>as_of or compat_valid<=assessed:
        raise ValueError('Compatibility chronology invalid')

    lifecycle=record['lifecycle']
    if not isinstance(lifecycle,dict) or set(lifecycle)!=LIFECYCLE_KEYS:
        raise ValueError('Lifecycle record shape invalid')
    if lifecycle['support_status'] not in SUPPORT_STATES:
        raise ValueError('Unknown support status')
    for key in ('support_evidence_ref','vulnerability_owner_ref','lifecycle_decision_ref'):
        opaque_ref(lifecycle[key],f'lifecycle.{key}')
    lifecycle_reviewed=instant(lifecycle['reviewed_at'],'lifecycle.reviewed_at')
    lifecycle_review_by=instant(lifecycle['review_by'],'lifecycle.review_by')
    if lifecycle_reviewed>as_of or lifecycle_review_by<=lifecycle_reviewed:
        raise ValueError('Lifecycle review chronology invalid')
    support_end=None
    if lifecycle['support_end_at'] is not None:
        support_end=instant(lifecycle['support_end_at'],'lifecycle.support_end_at')
        if support_end<=lifecycle_reviewed:
            raise ValueError('Support end must follow lifecycle review')

    owners=record['owners']
    if not isinstance(owners,dict) or set(owners)!=OWNER_KEYS:
        raise ValueError('Platform/architecture/vulnerability owners are required')
    for key in OWNER_KEYS:
        bounded(owners[key],key)

    unique_strings(record['exclusions'],'exclusions',allow_empty=True)
    refs=unique_strings(record['source_refs'],'source_refs')
    for ref in refs:
        repository_ref(ref,root)

    review_due=(bool(expired_current_kinds) or as_of>=compat_valid or as_of>=lifecycle_review_by)
    unsupported=(lifecycle['support_status']=='UNSUPPORTED'
                 or (support_end is not None and as_of>=support_end))
    source_incomplete=bool(missing_current_kinds)

    if record['state']=='CURRENT_SUPPORTED':
        if source_incomplete:
            raise ValueError('CURRENT_SUPPORTED lacks current reviewed mandatory source kinds')
        if review_due:
            raise ValueError('CURRENT_SUPPORTED has expired source, compatibility or lifecycle review')
        if unsupported or lifecycle['support_status']=='UNKNOWN':
            raise ValueError('CURRENT_SUPPORTED requires current vendor/project support evidence')
        if lifecycle['support_status']=='SUPPORT_END_SCHEDULED' and support_end is None:
            raise ValueError('SUPPORT_END_SCHEDULED requires support_end_at')
    elif record['state']=='REVIEW_DUE':
        if not review_due:
            raise ValueError('REVIEW_DUE requires expired source, compatibility or lifecycle evidence')
        if unsupported:
            raise ValueError('Unsupported tuple must use UNSUPPORTED state')
    elif record['state']=='UNSUPPORTED':
        if not unsupported:
            raise ValueError('UNSUPPORTED requires explicit support end or unsupported status')
    elif record['state']=='UNCERTAIN':
        pass

    return {
        'provenance_id':record['provenance_id'],
        'generation':record['generation'],
        'state':record['state'],
        'platform':record['platform'],
        'product_tuple_id':record['product_tuple_id'],
        'product_tuple':dict(record['product_tuple']),
        'required_source_kinds':sorted(required_kinds),
        'missing_current_source_kinds':sorted(missing_current_kinds),
        'compatibility_valid_until':compat_valid.isoformat(),
        'lifecycle_review_by':lifecycle_review_by.isoformat(),
        'support_status':lifecycle['support_status'],
        'support_end_at':support_end.isoformat() if support_end else None,
        'exceptions':sorted(exceptions),
        'source_reviews':normalized_reviews,
    }


def validate(index,*,as_of=None,root=ROOT):
    if as_of is None:
        as_of=datetime.now(timezone.utc)
    if not isinstance(as_of,datetime) or as_of.tzinfo is None:
        raise ValueError('Timezone-aware as_of required')
    as_of=as_of.astimezone(timezone.utc)
    if set(index)!=INDEX_KEYS:
        raise ValueError('Unexpected version/source provenance-index fields')
    if index['format']!=FORMAT or index['status']!=STATUS:
        raise ValueError('Unsupported provenance-index format or authority boundary')
    rev=index['reviewed_source_revision']
    if not isinstance(rev,str) or not re.fullmatch(r'[0-9a-f]{40}',rev):
        raise ValueError('Reviewed source revision must be an exact Git SHA')
    records=index['records']
    if not isinstance(records,list) or len(records)>128:
        raise ValueError('Provenance records must be a bounded list')
    ids=set()
    tuples=set()
    out=[]
    for raw in records:
        item=validate_record(raw,as_of=as_of,root=root)
        if item['provenance_id'] in ids:
            raise ValueError('Duplicate provenance record ID')
        key=(item['platform'],item['product_tuple_id'])
        if key in tuples:
            raise ValueError('Duplicate active provenance record for exact tuple')
        ids.add(item['provenance_id'])
        tuples.add(key)
        out.append(item)
    return {
        'records':out,
        'record_count':len(out),
        'current_supported_count':sum(x['state']=='CURRENT_SUPPORTED' for x in out),
        'review_due_count':sum(x['state']=='REVIEW_DUE' for x in out),
        'unsupported_count':sum(x['state']=='UNSUPPORTED' for x in out),
        'uncertain_count':sum(x['state']=='UNCERTAIN' for x in out),
    }


def records_for(index,platform,product_tuple_id,*,as_of=None,root=ROOT):
    summary=validate(index,as_of=as_of,root=root)
    return [
        r for r in summary['records']
        if r['platform']==platform and r['product_tuple_id']==product_tuple_id
    ]


def current_supported_for(index,platform,product_tuple_id,*,as_of=None,root=ROOT):
    return [
        r for r in records_for(index,platform,product_tuple_id,as_of=as_of,root=root)
        if r['state']=='CURRENT_SUPPORTED'
    ]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--index',type=Path,default=INDEX)
    p.add_argument('--as-of',help='ISO-8601 review instant; defaults to current UTC')
    a=p.parse_args()
    try:
        as_of=instant(a.as_of,'as_of') if a.as_of else datetime.now(timezone.utc)
        summary=validate(load(a.index),as_of=as_of)
        print(json.dumps({
            'status':'PASSED_VERSION_SOURCE_PROVENANCE_INDEX',
            'as_of':as_of.isoformat(),
            **{k:v for k,v in summary.items() if k!='records'},
            'may_claim_native_qualification':False,
            'may_select_site':False,
            'may_reserve_capacity':False,
            'may_allocate':False,
            'may_apply':False,
            'may_activate':False,
            'limits':[
                'Source edition and source review state are separate facts.',
                'A documentation review or provider-repository version is not proof that an installed tuple is supported.',
                'CURRENT_SUPPORTED is only a prerequisite for exact-tuple native qualification.',
                'The repository never contacts vendor support systems or changes infrastructure.'
            ]
        },indent=2))
        return 0
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({
            'status':'FAILED_VERSION_SOURCE_PROVENANCE_INDEX',
            'reason':str(exc),
            'may_claim_native_qualification':False,
            'may_select_site':False,
            'may_reserve_capacity':False,
            'may_allocate':False,
            'may_apply':False,
            'may_activate':False
        },indent=2))
        return 2


if __name__=='__main__':
    raise SystemExit(main())
