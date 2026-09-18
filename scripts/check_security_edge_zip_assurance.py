#!/usr/bin/env python3
"""Validate exported security-edge/ZIP assurance evidence.

This repository is not a firewall manager, routing controller, security-policy authority,
or production authorization system. Records contain opaque references to externally
owned boundary decisions and observations. The checker never creates routes, policies,
attachments, sessions, inspection rules, or management access.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'sources/capabilities/security_edge_zip_assurance_index.json'
FORMAT='portable-hosting-security-edge-zip-assurance-index/1'
STATUS='EXPORTED_ZIP_ASSURANCE_EVIDENCE_NOT_SECURITY_EDGE_AUTHORITY'
STATES={'CURRENT_QUALIFIED','REVIEW_DUE','FAILURE_TEST_DUE','GAPS_OPEN','UNCERTAIN'}
REALIZATIONS={'DEDICATED_EDGE','DISTRIBUTED_SHARED'}
FUNCTION_KEYS={
    'route_control','stateful_policy','inspection','logging',
    'session_revocation','management_separation',
    'source_identity_preservation','fail_secure'
}
GAP_STATES={'OPEN','ACCEPTED'}
ID=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{1,191}$')
INDEX_KEYS={'format','status','reviewed_source_revision','records'}
RECORD_KEYS={
    'assurance_id','generation','state','boundary_id','scope','realization',
    'security_functions','topology','policy','failure_tests','capacity',
    'path_tests','residual_gaps','source_refs'
}
SCOPE_KEYS={
    'source_endpoint_ref','destination_endpoint_ref',
    'source_authority_ref','destination_authority_ref',
    'joint_approval_ref','service_class_ref','management_authority_ref',
    'accepted_at','review_by'
}
REALIZATION_KEYS={
    'type','sharing_assurance_ref','equivalent_outcomes_ref',
    'unsupported_mandatory_functions'
}
TOPOLOGY_KEYS={
    'forward_path_ref','reply_path_ref','attachment_pair_ref',
    'native_route_review_ref','bypass_review_ref','management_path_ref',
    'translation_behavior_ref','return_symmetry_ref'
}
POLICY_KEYS={
    'deny_baseline_ref','approved_flow_set_ref','policy_precedence_ref',
    'inspection_profile_ref','logging_profile_ref','session_revocation_ref'
}
FAILURE_KEYS={
    'ha_mode_ref','state_sync_ref','edge_member_loss_ref',
    'manager_unavailable_ref','route_withdrawal_ref',
    'no_uninspected_fallback_ref','observed_at','valid_until'
}
CAPACITY_KEYS={
    'session_capacity_ref','throughput_ref','inspection_capacity_ref',
    'log_export_capacity_ref','survivor_capacity_ref'
}
PATH_TEST_KEYS={
    'allowed_flow_ref','cross_tenant_deny_ref',
    'unsolicited_reverse_deny_ref','management_transit_deny_ref',
    'same_host_or_distributed_bypass_ref','observed_at','valid_until'
}
GAP_KEYS={'gap_id','status','owner_ref','treatment_ref','decision_ref','review_by'}


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
    if p.is_absolute() or '..' in p.parts or '\\' in value or ':' in value:
        raise ValueError('Repository reference must be normalized and relative')
    if not (root/p).exists():
        raise ValueError(f'Repository reference does not exist: {value}')
    return value


def load(path:Path=INDEX):
    with path.open('rb') as stream:
        raw=stream.read(1024*1024+1)
    if len(raw)>1024*1024:
        raise ValueError('Security-edge assurance index exceeds bounded size')
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
        raise ValueError('Security-edge assurance index must be an object')
    return value


def validate_record(record,*,as_of,root=ROOT):
    if not isinstance(record,dict) or set(record)!=RECORD_KEYS:
        raise ValueError('Security-edge assurance record has unexpected or missing fields')
    identifier(record['assurance_id'],'assurance_id')
    identifier(record['boundary_id'],'boundary_id')
    positive_int(record['generation'],'generation')
    if record['state'] not in STATES:
        raise ValueError('Unknown security-edge assurance state')

    scope=record['scope']
    if not isinstance(scope,dict) or set(scope)!=SCOPE_KEYS:
        raise ValueError('ZIP scope shape invalid')
    for key in (
        'source_endpoint_ref','destination_endpoint_ref',
        'source_authority_ref','destination_authority_ref',
        'joint_approval_ref','service_class_ref','management_authority_ref'
    ):
        opaque_ref(scope[key],f'scope.{key}')
    if scope['source_endpoint_ref']==scope['destination_endpoint_ref']:
        raise ValueError('ZIP requires exactly two distinct adjacent endpoints')
    accepted=instant(scope['accepted_at'],'scope.accepted_at')
    review_by=instant(scope['review_by'],'scope.review_by')
    if accepted>as_of or review_by<=accepted:
        raise ValueError('ZIP scope chronology invalid')

    realization=record['realization']
    if not isinstance(realization,dict) or set(realization)!=REALIZATION_KEYS:
        raise ValueError('ZIP realization shape invalid')
    if realization['type'] not in REALIZATIONS:
        raise ValueError('Unknown ZIP realization type')
    unsupported=unique_strings(
        realization['unsupported_mandatory_functions'],
        'unsupported_mandatory_functions',allow_empty=True)
    if realization['type']=='DEDICATED_EDGE':
        if realization['sharing_assurance_ref'] is not None or realization['equivalent_outcomes_ref'] is not None:
            raise ValueError('Dedicated edge cannot claim distributed/shared equivalence fields')
    else:
        opaque_ref(realization['sharing_assurance_ref'],'sharing_assurance_ref')
        opaque_ref(realization['equivalent_outcomes_ref'],'equivalent_outcomes_ref')
    if unsupported:
        raise ValueError('A ZIP with unsupported mandatory functions is ineligible')

    functions=record['security_functions']
    if not isinstance(functions,dict) or set(functions)!=FUNCTION_KEYS:
        raise ValueError('Complete mandatory ZIP security-function evidence is required')
    for key,value in functions.items():
        opaque_ref(value,f'security_functions.{key}')

    topology=record['topology']
    if not isinstance(topology,dict) or set(topology)!=TOPOLOGY_KEYS:
        raise ValueError('ZIP topology evidence shape invalid')
    for key,value in topology.items():
        opaque_ref(value,f'topology.{key}')

    policy=record['policy']
    if not isinstance(policy,dict) or set(policy)!=POLICY_KEYS:
        raise ValueError('ZIP policy evidence shape invalid')
    for key,value in policy.items():
        opaque_ref(value,f'policy.{key}')

    failure=record['failure_tests']
    if not isinstance(failure,dict) or set(failure)!=FAILURE_KEYS:
        raise ValueError('ZIP failure-test evidence shape invalid')
    for key in FAILURE_KEYS-{'observed_at','valid_until'}:
        opaque_ref(failure[key],f'failure_tests.{key}')
    failure_observed=instant(failure['observed_at'],'failure_tests.observed_at')
    failure_valid=instant(failure['valid_until'],'failure_tests.valid_until')
    if failure_observed>as_of or failure_valid<=failure_observed:
        raise ValueError('ZIP failure-test chronology invalid')

    capacity=record['capacity']
    if not isinstance(capacity,dict) or set(capacity)!=CAPACITY_KEYS:
        raise ValueError('ZIP capacity evidence shape invalid')
    for key,value in capacity.items():
        opaque_ref(value,f'capacity.{key}')

    path_tests=record['path_tests']
    if not isinstance(path_tests,dict) or set(path_tests)!=PATH_TEST_KEYS:
        raise ValueError('ZIP path-test evidence shape invalid')
    for key in PATH_TEST_KEYS-{'observed_at','valid_until'}:
        opaque_ref(path_tests[key],f'path_tests.{key}')
    path_observed=instant(path_tests['observed_at'],'path_tests.observed_at')
    path_valid=instant(path_tests['valid_until'],'path_tests.valid_until')
    if path_observed>as_of or path_valid<=path_observed:
        raise ValueError('ZIP path-test chronology invalid')

    gaps=record['residual_gaps']
    if not isinstance(gaps,list) or len(gaps)>1024:
        raise ValueError('Residual ZIP gaps must be a bounded list')
    gap_ids=set(); open_gaps=[]; gap_reviews=[]
    for gap in gaps:
        if not isinstance(gap,dict) or set(gap)!=GAP_KEYS:
            raise ValueError('Residual ZIP gap shape invalid')
        gap_id=identifier(gap['gap_id'],'gap_id')
        if gap_id in gap_ids:
            raise ValueError('Duplicate residual ZIP gap ID')
        gap_ids.add(gap_id)
        if gap['status'] not in GAP_STATES:
            raise ValueError('Unknown residual ZIP gap state')
        opaque_ref(gap['owner_ref'],'gap.owner_ref')
        opaque_ref(gap['treatment_ref'],'gap.treatment_ref')
        gap_review=instant(gap['review_by'],'gap.review_by')
        gap_reviews.append(gap_review)
        if gap['status']=='OPEN':
            if gap['decision_ref'] is not None:
                raise ValueError('OPEN ZIP gap cannot carry an acceptance decision')
            open_gaps.append(gap_id)
        else:
            opaque_ref(gap['decision_ref'],'gap.decision_ref')

    refs=unique_strings(record['source_refs'],'source_refs')
    for ref in refs:
        repository_ref(ref,root)

    review_due=(as_of>=review_by or any(as_of>=x for x in gap_reviews))
    failure_due=as_of>=failure_valid or as_of>=path_valid
    if record['state']=='CURRENT_QUALIFIED':
        if review_due:
            raise ValueError('CURRENT_QUALIFIED ZIP has expired review evidence')
        if failure_due:
            raise ValueError('CURRENT_QUALIFIED ZIP has expired path/failure evidence')
        if open_gaps:
            raise ValueError('CURRENT_QUALIFIED ZIP cannot contain OPEN residual gaps')
    elif record['state']=='REVIEW_DUE':
        if not review_due:
            raise ValueError('REVIEW_DUE requires expired scope or gap review')
    elif record['state']=='FAILURE_TEST_DUE':
        if review_due or not failure_due:
            raise ValueError('FAILURE_TEST_DUE requires current review and expired path/failure evidence')
    elif record['state']=='GAPS_OPEN':
        if review_due or failure_due or not open_gaps:
            raise ValueError('GAPS_OPEN requires current evidence and at least one OPEN residual gap')
    elif record['state']=='UNCERTAIN':
        pass

    return {
        'assurance_id':record['assurance_id'],
        'generation':record['generation'],
        'state':record['state'],
        'boundary_id':record['boundary_id'],
        'realization_type':realization['type'],
        'source_endpoint_ref':scope['source_endpoint_ref'],
        'destination_endpoint_ref':scope['destination_endpoint_ref'],
        'service_class_ref':scope['service_class_ref'],
        'review_by':review_by.isoformat(),
        'failure_valid_until':failure_valid.isoformat(),
        'path_valid_until':path_valid.isoformat(),
        'open_gap_ids':sorted(open_gaps)
    }


def validate(index,*,as_of=None,root=ROOT):
    if as_of is None:
        as_of=datetime.now(timezone.utc)
    if not isinstance(as_of,datetime) or as_of.tzinfo is None:
        raise ValueError('Timezone-aware as_of required')
    as_of=as_of.astimezone(timezone.utc)
    if set(index)!=INDEX_KEYS:
        raise ValueError('Unexpected security-edge assurance-index fields')
    if index['format']!=FORMAT or index['status']!=STATUS:
        raise ValueError('Unsupported security-edge assurance format or authority boundary')
    revision=index['reviewed_source_revision']
    if not isinstance(revision,str) or not re.fullmatch(r'[0-9a-f]{40}',revision):
        raise ValueError('Reviewed source revision must be an exact Git SHA')
    records=index['records']
    if not isinstance(records,list) or len(records)>512:
        raise ValueError('Security-edge assurance records must be a bounded list')
    ids=set(); boundaries=set(); out=[]
    for raw in records:
        item=validate_record(raw,as_of=as_of,root=root)
        if item['assurance_id'] in ids:
            raise ValueError('Duplicate security-edge assurance ID')
        if item['boundary_id'] in boundaries:
            raise ValueError('Duplicate active assurance record for one ZIP boundary')
        ids.add(item['assurance_id']);boundaries.add(item['boundary_id']);out.append(item)
    return {
        'records':out,
        'record_count':len(out),
        'current_qualified_count':sum(x['state']=='CURRENT_QUALIFIED' for x in out),
        'review_due_count':sum(x['state']=='REVIEW_DUE' for x in out),
        'failure_test_due_count':sum(x['state']=='FAILURE_TEST_DUE' for x in out),
        'gaps_open_count':sum(x['state']=='GAPS_OPEN' for x in out),
        'uncertain_count':sum(x['state']=='UNCERTAIN' for x in out)
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
            'status':'PASSED_SECURITY_EDGE_ZIP_ASSURANCE',
            'as_of':as_of.isoformat(),
            **{k:v for k,v in summary.items() if k!='records'},
            'may_create_route':False,'may_change_policy':False,
            'may_attach_domain':False,'may_change_edge':False,
            'may_change_management_access':False,'may_apply':False,'may_activate':False,
            'limits':[
                'A route or quarantine resource alone is not a qualified ZIP.',
                'Distributed/shared ZIPs must prove the same required security outcomes as a dedicated edge.',
                'Negative path observations require healthy controls and current native forwarding/policy evidence.',
                'The repository validates exported evidence only and never changes a security edge.'
            ]
        },indent=2))
        return 0
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({
            'status':'FAILED_SECURITY_EDGE_ZIP_ASSURANCE','reason':str(exc),
            'may_create_route':False,'may_change_policy':False,
            'may_attach_domain':False,'may_change_edge':False,
            'may_change_management_access':False,'may_apply':False,'may_activate':False
        },indent=2))
        return 2


if __name__=='__main__':
    raise SystemExit(main())
