#!/usr/bin/env python3
"""Validate bootstrap service-initialization assurance evidence.

This repository is not IPAM, DNS, DHCP/metadata, NTP, identity, artifact, telemetry,
or bootstrap execution authority. Records contain opaque references to externally owned
dependency and test evidence. The checker never allocates addresses, registers names,
issues credentials, changes time sources, downloads images, changes telemetry, or
performs production activation.
"""
from __future__ import annotations
import argparse, json, re
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'sources/capabilities/bootstrap_service_assurance_index.json'
FORMAT='portable-hosting-bootstrap-service-assurance-index/1'
STATUS='EXPORTED_BOOTSTRAP_SERVICE_EVIDENCE_NOT_INITIALIZATION_AUTHORITY'
STATES={
    'CURRENT_READY','REVIEW_DUE','DEPENDENCY_DUE',
    'FAILURE_TEST_DUE','TRANSITION_DUE','GAPS_OPEN','UNCERTAIN'
}
GAP_STATES={'OPEN','ACCEPTED'}
ID=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{1,191}$')

INDEX_KEYS={'format','status','reviewed_source_revision','records'}
RECORD_KEYS={
    'assurance_id','generation','state','bootstrap_id','scope',
    'prerequisites','initialization','artifact_baseline','telemetry',
    'failure_tests','transition','residual_gaps','source_refs'
}
SCOPE_KEYS={
    'site_ref','service_class_ref','platform_profile_ref','bootstrap_profile_ref',
    'owner_ref','accepted_at','review_by'
}
PREREQ_KEYS={
    'ipam_allocation_ref','dns_registration_ref','trust_assurance_ref',
    'address_family_assurance_ref','service_reply_set_ref',
    'recovery_bootstrap_ref','observed_at','valid_until'
}
INITIALIZATION_KEYS={
    'address_assignment_mode_ref','dhcp_metadata_scope_ref',
    'resolver_profile_ref','time_profile_ref',
    'artifact_repository_profile_ref','trust_bootstrap_ref',
    'key_access_ref','initialization_network_scope_ref',
    'observed_at','valid_until'
}
ARTIFACT_KEYS={
    'image_baseline_ref','provenance_digest_ref','support_status_ref',
    'hardening_ref','vulnerability_disposition_ref',
    'runtime_baseline_verification_ref','retirement_rebuild_ref',
    'observed_at','valid_until'
}
TELEMETRY_KEYS={
    'stable_identity_ref','event_coverage_ref','time_integrity_ref',
    'buffering_loss_alert_ref','collection_failure_behavior_ref',
    'observed_at','valid_until'
}
FAILURE_KEYS={
    'ipam_unavailable_no_guess_ref','resolver_unavailable_ref',
    'time_loss_ref','repository_unavailable_ref','collector_unavailable_ref',
    'no_unrestricted_fallback_ref','observed_at','valid_until'
}
TRANSITION_KEYS={
    'temporary_dependency_register_ref','temporary_credential_ref',
    'temporary_route_ref','exception_register_ref',
    'steady_state_replacement_ref','post_transfer_verification_ref',
    'revocation_cleanup_ref','recovery_dependency_retention_ref',
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
        raise ValueError('Bootstrap service assurance index exceeds bounded size')
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
        raise ValueError('Bootstrap service assurance index must be an object')
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
        raise ValueError('Bootstrap service assurance record has unexpected or missing fields')
    identifier(record['assurance_id'],'assurance_id')
    identifier(record['bootstrap_id'],'bootstrap_id')
    positive_int(record['generation'],'generation')
    if record['state'] not in STATES:
        raise ValueError('Unknown bootstrap service assurance state')

    scope=record['scope']
    if not isinstance(scope,dict) or set(scope)!=SCOPE_KEYS:
        raise ValueError('Bootstrap scope shape invalid')
    for k in ('site_ref','service_class_ref','platform_profile_ref','bootstrap_profile_ref','owner_ref'):
        opaque_ref(scope[k],f'scope.{k}')
    accepted=instant(scope['accepted_at'],'scope.accepted_at')
    review_by=instant(scope['review_by'],'scope.review_by')
    if accepted>as_of or review_by<=accepted:
        raise ValueError('Bootstrap scope chronology invalid')

    _,prereq_valid=evidence_block(record['prerequisites'],PREREQ_KEYS,'prerequisites',as_of)
    _,initialization_valid=evidence_block(record['initialization'],INITIALIZATION_KEYS,'initialization',as_of)
    _,artifact_valid=evidence_block(record['artifact_baseline'],ARTIFACT_KEYS,'artifact_baseline',as_of)
    _,telemetry_valid=evidence_block(record['telemetry'],TELEMETRY_KEYS,'telemetry',as_of)
    _,failure_valid=evidence_block(record['failure_tests'],FAILURE_KEYS,'failure_tests',as_of)
    _,transition_valid=evidence_block(record['transition'],TRANSITION_KEYS,'transition',as_of)

    gaps=record['residual_gaps']
    if not isinstance(gaps,list) or len(gaps)>1024:
        raise ValueError('Residual bootstrap gaps must be a bounded list')
    gap_ids=set(); open_gaps=[]; gap_reviews=[]
    for gap in gaps:
        if not isinstance(gap,dict) or set(gap)!=GAP_KEYS:
            raise ValueError('Residual bootstrap gap shape invalid')
        gid=identifier(gap['gap_id'],'gap_id')
        if gid in gap_ids:
            raise ValueError('Duplicate residual bootstrap gap ID')
        gap_ids.add(gid)
        if gap['status'] not in GAP_STATES:
            raise ValueError('Unknown residual bootstrap gap state')
        opaque_ref(gap['owner_ref'],'gap.owner_ref')
        opaque_ref(gap['treatment_ref'],'gap.treatment_ref')
        gr=instant(gap['review_by'],'gap.review_by')
        gap_reviews.append(gr)
        if gap['status']=='OPEN':
            if gap['decision_ref'] is not None:
                raise ValueError('OPEN bootstrap gap cannot carry acceptance decision')
            open_gaps.append(gid)
        else:
            opaque_ref(gap['decision_ref'],'gap.decision_ref')

    refs=unique_strings(record['source_refs'],'source_refs')
    for ref in refs:
        repository_ref(ref,root)

    review_due=as_of>=review_by or any(as_of>=x for x in gap_reviews)
    dependency_due=as_of>=min(prereq_valid,initialization_valid,artifact_valid,telemetry_valid)
    failure_due=as_of>=failure_valid
    transition_due=as_of>=transition_valid

    state=record['state']
    if state=='CURRENT_READY':
        if review_due or dependency_due or failure_due or transition_due or open_gaps:
            raise ValueError('CURRENT_READY bootstrap evidence is stale or incomplete')
    elif state=='REVIEW_DUE':
        if not review_due:
            raise ValueError('REVIEW_DUE requires expired scope/gap review')
    elif state=='DEPENDENCY_DUE':
        if review_due or not dependency_due:
            raise ValueError('DEPENDENCY_DUE requires current review and stale prerequisite/initialization/artifact/telemetry evidence')
    elif state=='FAILURE_TEST_DUE':
        if review_due or dependency_due or not failure_due:
            raise ValueError('FAILURE_TEST_DUE requires current dependencies and stale failure evidence')
    elif state=='TRANSITION_DUE':
        if review_due or dependency_due or failure_due or not transition_due:
            raise ValueError('TRANSITION_DUE requires current dependency/failure evidence and stale transition evidence')
    elif state=='GAPS_OPEN':
        if review_due or dependency_due or failure_due or transition_due or not open_gaps:
            raise ValueError('GAPS_OPEN requires current evidence and at least one OPEN residual gap')
    elif state=='UNCERTAIN':
        pass

    return {
        'assurance_id':record['assurance_id'],
        'generation':record['generation'],
        'state':state,
        'bootstrap_id':record['bootstrap_id'],
        'site_ref':scope['site_ref'],
        'service_class_ref':scope['service_class_ref'],
        'platform_profile_ref':scope['platform_profile_ref'],
        'bootstrap_profile_ref':scope['bootstrap_profile_ref'],
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
        raise ValueError('Unexpected bootstrap assurance-index fields')
    if index['format']!=FORMAT or index['status']!=STATUS:
        raise ValueError('Unsupported bootstrap assurance format or authority boundary')
    revision=index['reviewed_source_revision']
    if not isinstance(revision,str) or not re.fullmatch(r'[0-9a-f]{40}',revision):
        raise ValueError('Reviewed source revision must be an exact Git SHA')
    records=index['records']
    if not isinstance(records,list) or len(records)>512:
        raise ValueError('Bootstrap assurance records must be a bounded list')
    ids=set(); bootstrap_ids=set(); out=[]
    for raw in records:
        item=validate_record(raw,as_of,root)
        if item['assurance_id'] in ids:
            raise ValueError('Duplicate bootstrap assurance ID')
        if item['bootstrap_id'] in bootstrap_ids:
            raise ValueError('Duplicate active assurance for one bootstrap ID')
        ids.add(item['assurance_id']); bootstrap_ids.add(item['bootstrap_id']); out.append(item)
    return {
        'records':out,'record_count':len(out),
        'current_ready_count':sum(x['state']=='CURRENT_READY' for x in out),
        'review_due_count':sum(x['state']=='REVIEW_DUE' for x in out),
        'dependency_due_count':sum(x['state']=='DEPENDENCY_DUE' for x in out),
        'failure_test_due_count':sum(x['state']=='FAILURE_TEST_DUE' for x in out),
        'transition_due_count':sum(x['state']=='TRANSITION_DUE' for x in out),
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
            'status':'PASSED_BOOTSTRAP_SERVICE_ASSURANCE','as_of':as_of.isoformat(),
            **{k:v for k,v in summary.items() if k!='records'},
            'may_allocate_address':False,'may_register_name':False,
            'may_change_dhcp_metadata':False,'may_change_time_source':False,
            'may_issue_bootstrap_credential':False,'may_fetch_artifact':False,
            'may_change_telemetry':False,'may_retire_temporary_dependency':False,
            'may_apply':False,'may_activate':False,
            'limits':[
                'Current IPAM and DNS evidence remain separate authoritative dependencies.',
                'Bootstrap reachability does not authorize provider administration or unrestricted external access.',
                'Failure recovery may use only preapproved dependency paths; guessed addresses, arbitrary time or unverified images are prohibited.',
                'The repository validates exported evidence only and never initializes a workload or platform.'
            ]
        },indent=2)); return 0
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({
            'status':'FAILED_BOOTSTRAP_SERVICE_ASSURANCE','reason':str(exc),
            'may_allocate_address':False,'may_register_name':False,
            'may_change_dhcp_metadata':False,'may_change_time_source':False,
            'may_issue_bootstrap_credential':False,'may_fetch_artifact':False,
            'may_change_telemetry':False,'may_retire_temporary_dependency':False,
            'may_apply':False,'may_activate':False
        },indent=2)); return 2


if __name__=='__main__':
    raise SystemExit(main())
