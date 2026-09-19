#!/usr/bin/env python3
"""Validate exported identity, certificate and key-management assurance evidence.

This repository is not an identity provider, PAM system, CA, KMS, HSM, secret store,
or recovery authority. Records contain opaque references to externally owned decisions
and observations. The checker never issues/revokes credentials, enrolls certificates,
rotates/destroys keys, changes privileged access, or executes recovery.
"""
from __future__ import annotations
import argparse, json, re
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'sources/capabilities/identity_crypto_assurance_index.json'
FORMAT='portable-hosting-identity-crypto-assurance-index/1'
STATUS='EXPORTED_IDENTITY_CRYPTO_EVIDENCE_NOT_TRUST_AUTHORITY'
STATES={'CURRENT_QUALIFIED','REVIEW_DUE','TRUST_EVIDENCE_DUE','OUTAGE_TEST_DUE','GAPS_OPEN','UNCERTAIN'}
GAP_STATES={'OPEN','ACCEPTED'}
ID=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{1,191}$')

INDEX_KEYS={'format','status','reviewed_source_revision','records'}
RECORD_KEYS={
    'assurance_id','generation','state','trust_id','scope','identity',
    'certificates','keys','outage_recovery','agility','residual_gaps','source_refs'
}
SCOPE_KEYS={
    'site_ref','service_class_ref','trust_profile_ref','key_profile_ref',
    'owner_ref','accepted_at','review_by'
}
IDENTITY_KEYS={
    'human_scope_ref','workload_scope_ref','automation_scope_ref',
    'provider_authority_separation_ref','privileged_path_ref','strong_auth_ref',
    'time_bound_delegation_ref','emergency_access_ref','supplier_access_ref',
    'revocation_propagation_ref','cached_token_test_ref','observed_at','valid_until'
}
CERT_KEYS={
    'issuer_ref','relying_party_trust_ref','endpoint_identity_validation_ref',
    'issuance_scope_ref','renewal_ref','revocation_ref','tls_profile_ref',
    'crypto_module_evidence_ref','observed_at','valid_until'
}
KEY_KEYS={
    'use_authority_ref','administration_authority_ref','recovery_authority_ref',
    'destruction_authority_ref','retained_data_dependency_ref',
    'destruction_disposition_ref','custody_ref','key_version_inventory_ref',
    'rotation_ref','observed_at','valid_until'
}
OUTAGE_KEYS={
    'kms_outage_test_ref','no_plaintext_fallback_ref','trust_service_outage_ref',
    'independent_recovery_path_ref','emergency_identity_ref','recovery_audit_ref',
    'observed_at','valid_until'
}
AGILITY_KEYS={
    'cryptographic_inventory_ref','certificate_rotation_plan_ref',
    'algorithm_transition_plan_ref','exception_register_ref',
    'observed_at','valid_until'
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
        raise ValueError('Identity/crypto assurance index exceeds bounded size')
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
        raise ValueError('Identity/crypto assurance index must be an object')
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
        raise ValueError('Identity/crypto assurance record has unexpected or missing fields')
    identifier(record['assurance_id'],'assurance_id')
    identifier(record['trust_id'],'trust_id')
    positive_int(record['generation'],'generation')
    if record['state'] not in STATES:
        raise ValueError('Unknown identity/crypto assurance state')

    scope=record['scope']
    if not isinstance(scope,dict) or set(scope)!=SCOPE_KEYS:
        raise ValueError('Identity/crypto scope shape invalid')
    for k in ('site_ref','service_class_ref','trust_profile_ref','key_profile_ref','owner_ref'):
        opaque_ref(scope[k],f'scope.{k}')
    accepted=instant(scope['accepted_at'],'scope.accepted_at')
    review_by=instant(scope['review_by'],'scope.review_by')
    if accepted>as_of or review_by<=accepted:
        raise ValueError('Identity/crypto scope chronology invalid')

    _,identity_valid=evidence_block(record['identity'],IDENTITY_KEYS,'identity',as_of)
    _,cert_valid=evidence_block(record['certificates'],CERT_KEYS,'certificates',as_of)
    _,key_valid=evidence_block(record['keys'],KEY_KEYS,'keys',as_of)
    _,outage_valid=evidence_block(record['outage_recovery'],OUTAGE_KEYS,'outage_recovery',as_of)
    _,agility_valid=evidence_block(record['agility'],AGILITY_KEYS,'agility',as_of)

    key_authorities=[
        record['keys']['use_authority_ref'],
        record['keys']['administration_authority_ref'],
        record['keys']['recovery_authority_ref'],
        record['keys']['destruction_authority_ref'],
    ]
    if len(set(key_authorities))!=4:
        raise ValueError('Key use, administration, recovery and destruction authorities must be explicitly separated')

    gaps=record['residual_gaps']
    if not isinstance(gaps,list) or len(gaps)>1024:
        raise ValueError('Residual identity/crypto gaps must be a bounded list')
    gap_ids=set(); open_gaps=[]; gap_reviews=[]
    for gap in gaps:
        if not isinstance(gap,dict) or set(gap)!=GAP_KEYS:
            raise ValueError('Residual identity/crypto gap shape invalid')
        gid=identifier(gap['gap_id'],'gap_id')
        if gid in gap_ids:
            raise ValueError('Duplicate residual identity/crypto gap ID')
        gap_ids.add(gid)
        if gap['status'] not in GAP_STATES:
            raise ValueError('Unknown residual identity/crypto gap state')
        opaque_ref(gap['owner_ref'],'gap.owner_ref')
        opaque_ref(gap['treatment_ref'],'gap.treatment_ref')
        gr=instant(gap['review_by'],'gap.review_by')
        gap_reviews.append(gr)
        if gap['status']=='OPEN':
            if gap['decision_ref'] is not None:
                raise ValueError('OPEN identity/crypto gap cannot carry acceptance decision')
            open_gaps.append(gid)
        else:
            opaque_ref(gap['decision_ref'],'gap.decision_ref')

    refs=unique_strings(record['source_refs'],'source_refs')
    for ref in refs:
        repository_ref(ref,root)

    review_due=as_of>=review_by or any(as_of>=x for x in gap_reviews)
    trust_due=as_of>=min(identity_valid,cert_valid,key_valid,agility_valid)
    outage_due=as_of>=outage_valid

    state=record['state']
    if state=='CURRENT_QUALIFIED':
        if review_due or trust_due or outage_due or open_gaps:
            raise ValueError('CURRENT_QUALIFIED identity/crypto evidence is stale or incomplete')
    elif state=='REVIEW_DUE':
        if not review_due:
            raise ValueError('REVIEW_DUE requires expired scope/gap review')
    elif state=='TRUST_EVIDENCE_DUE':
        if review_due or not trust_due:
            raise ValueError('TRUST_EVIDENCE_DUE requires current review and stale identity/certificate/key/agility evidence')
    elif state=='OUTAGE_TEST_DUE':
        if review_due or trust_due or not outage_due:
            raise ValueError('OUTAGE_TEST_DUE requires current trust evidence and stale outage/recovery evidence')
    elif state=='GAPS_OPEN':
        if review_due or trust_due or outage_due or not open_gaps:
            raise ValueError('GAPS_OPEN requires current evidence and at least one OPEN residual gap')
    elif state=='UNCERTAIN':
        pass

    return {
        'assurance_id':record['assurance_id'],
        'generation':record['generation'],
        'state':state,
        'trust_id':record['trust_id'],
        'site_ref':scope['site_ref'],
        'service_class_ref':scope['service_class_ref'],
        'trust_profile_ref':scope['trust_profile_ref'],
        'key_profile_ref':scope['key_profile_ref'],
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
        raise ValueError('Unexpected identity/crypto assurance-index fields')
    if index['format']!=FORMAT or index['status']!=STATUS:
        raise ValueError('Unsupported identity/crypto assurance format or authority boundary')
    revision=index['reviewed_source_revision']
    if not isinstance(revision,str) or not re.fullmatch(r'[0-9a-f]{40}',revision):
        raise ValueError('Reviewed source revision must be an exact Git SHA')
    records=index['records']
    if not isinstance(records,list) or len(records)>512:
        raise ValueError('Identity/crypto assurance records must be a bounded list')
    ids=set(); trusts=set(); out=[]
    for raw in records:
        item=validate_record(raw,as_of,root)
        if item['assurance_id'] in ids:
            raise ValueError('Duplicate identity/crypto assurance ID')
        if item['trust_id'] in trusts:
            raise ValueError('Duplicate active assurance for one trust ID')
        ids.add(item['assurance_id']); trusts.add(item['trust_id']); out.append(item)
    return {
        'records':out,'record_count':len(out),
        'current_qualified_count':sum(x['state']=='CURRENT_QUALIFIED' for x in out),
        'review_due_count':sum(x['state']=='REVIEW_DUE' for x in out),
        'trust_evidence_due_count':sum(x['state']=='TRUST_EVIDENCE_DUE' for x in out),
        'outage_test_due_count':sum(x['state']=='OUTAGE_TEST_DUE' for x in out),
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
            'status':'PASSED_IDENTITY_CRYPTO_ASSURANCE','as_of':as_of.isoformat(),
            **{k:v for k,v in summary.items() if k!='records'},
            'may_issue_credential':False,'may_revoke_credential':False,
            'may_enroll_certificate':False,'may_rotate_key':False,
            'may_destroy_key':False,'may_change_privileged_access':False,
            'may_execute_recovery':False,'may_apply':False,'may_activate':False,
            'limits':[
                'A TLS fixture or successful login is not enterprise identity/PKI/KMS qualification.',
                'Network reachability does not grant identity, key or administrative entitlement.',
                'Key destruction remains dependent on retained-data disposition and copy/key lineage.',
                'The repository validates exported evidence only and never mutates trust services.'
            ]
        },indent=2)); return 0
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({
            'status':'FAILED_IDENTITY_CRYPTO_ASSURANCE','reason':str(exc),
            'may_issue_credential':False,'may_revoke_credential':False,
            'may_enroll_certificate':False,'may_rotate_key':False,
            'may_destroy_key':False,'may_change_privileged_access':False,
            'may_execute_recovery':False,'may_apply':False,'may_activate':False
        },indent=2)); return 2


if __name__=='__main__':
    raise SystemExit(main())
