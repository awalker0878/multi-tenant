#!/usr/bin/env python3
"""Validate native IPv6/address-family qualification evidence.

This repository is not an address manager, router, firewall, DHCPv6/RA controller,
DNS authority, PMTU controller, or production authorization service. Records contain
opaque evidence references for an offered family mode. The checker never allocates
addresses, changes routing/policy, enables IPv6, mutates shared services, or activates
production.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'sources/capabilities/address_family_assurance_index.json'
FORMAT='portable-hosting-address-family-assurance-index/1'
STATUS='EXPORTED_ADDRESS_FAMILY_EVIDENCE_NOT_NETWORK_AUTHORITY'
STATES={'CURRENT_QUALIFIED','REVIEW_DUE','PACKET_TEST_DUE','DEPENDENCY_DUE','GAPS_OPEN','UNCERTAIN'}
MODES={
    'IPV6_ONLY':('IPV6',),
    'DUAL_STACK':('IPV4','IPV6'),
}
PLATFORMS={'NUTANIX','VMWARE_NSX','OPENSTACK'}
GAP_STATES={'OPEN','ACCEPTED'}

INDEX_KEYS={'format','status','reviewed_source_revision','records'}
RECORD_KEYS={
    'assurance_id','generation','state','qualification_id','platform','scope',
    'native_path','security_equivalence','shared_services','pmtu',
    'failure_recovery','operations','residual_gaps','source_refs'
}
SCOPE_KEYS={
    'offered_mode','offered_families','service_class_ref','platform_profile_ref',
    'platform_qualification_ref','security_edge_assurance_refs',
    'accepted_at','review_by','owner_ref'
}
NATIVE_PATH_KEYS={
    'routing_ref','same_host_enforcement_ref','source_neighbor_control_ref',
    'address_assignment_ref','local_protocol_control_ref','transition_restriction_ref',
    'management_exclusion_ref','observed_at','valid_until'
}
SECURITY_KEYS={
    'ipv4_baseline_ref','policy_equivalence_ref','negative_path_ref',
    'inspection_equivalence_ref','logging_attribution_ref','fail_secure_ref',
    'observed_at','valid_until'
}
SERVICE_KEYS={
    'dns_aaaa_ref','dns_udp_tcp_ref','time_service_ref','trust_identity_ref',
    'telemetry_ref','image_repository_ref','protection_recovery_ref',
    'origin_specific_reply_ref','observed_at','valid_until'
}
PMTU_KEYS={
    'effective_workload_mtu_ref','encapsulation_budget_ref','icmpv6_error_policy_ref',
    'packet_too_big_ref','large_small_control_ref','fragment_extension_policy_ref',
    'observed_at','valid_until'
}
FAILURE_KEYS={
    'route_withdrawal_ref','edge_failure_ref','service_reply_loss_ref',
    'address_dad_recovery_ref','no_ipv4_fallback_ref','survivor_capacity_ref',
    'observed_at','valid_until'
}
OPERATIONS_KEYS={
    'monitoring_ref','runbook_ref','recovery_reexposure_ref',
    'operational_acceptance_ref','observed_at','valid_until'
}
GAP_KEYS={'gap_id','status','owner_ref','treatment_ref','decision_ref','review_by'}
ID=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{1,191}$')


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


def repository_ref(value,root=ROOT):
    bounded(value,'repository reference')
    p=Path(value)
    if p.is_absolute() or '..' in p.parts or '\\' in value or ':' in value:
        raise ValueError('Repository reference must be normalized and relative')
    if not (root/p).exists():
        raise ValueError(f'Repository reference does not exist: {value}')
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
        raise ValueError('Address-family assurance index exceeds bounded size')
    def pairs(items):
        out={}
        for k,v in items:
            if k in out: raise ValueError('Duplicate JSON property')
            out[k]=v
        return out
    def reject(_):
        raise ValueError('Non-finite JSON number')
    value=json.loads(raw,object_pairs_hook=pairs,parse_constant=reject)
    if not isinstance(value,dict):
        raise ValueError('Address-family assurance index must be an object')
    return value


def evidence_block(value,expected_keys,label,*,as_of):
    if not isinstance(value,dict) or set(value)!=expected_keys:
        raise ValueError(f'{label}: evidence shape invalid')
    for key in expected_keys-{'observed_at','valid_until'}:
        opaque_ref(value[key],f'{label}.{key}')
    observed=instant(value['observed_at'],f'{label}.observed_at')
    valid=instant(value['valid_until'],f'{label}.valid_until')
    if observed>as_of or valid<=observed:
        raise ValueError(f'{label}: evidence chronology invalid')
    return observed,valid


def validate_record(record,*,as_of,root=ROOT):
    if not isinstance(record,dict) or set(record)!=RECORD_KEYS:
        raise ValueError('Address-family assurance record has unexpected or missing fields')
    identifier(record['assurance_id'],'assurance_id')
    identifier(record['qualification_id'],'qualification_id')
    positive_int(record['generation'],'generation')
    if record['state'] not in STATES:
        raise ValueError('Unknown address-family assurance state')
    if record['platform'] not in PLATFORMS:
        raise ValueError('Unknown platform family')

    scope=record['scope']
    if not isinstance(scope,dict) or set(scope)!=SCOPE_KEYS:
        raise ValueError('Address-family qualification scope shape invalid')
    mode=scope['offered_mode']
    if mode not in MODES:
        raise ValueError('Unsupported offered address-family mode')
    families=unique_strings(scope['offered_families'],'offered_families')
    if tuple(families)!=MODES[mode]:
        raise ValueError('Offered family list does not exactly match the declared mode')
    for key in ('service_class_ref','platform_profile_ref','platform_qualification_ref','owner_ref'):
        opaque_ref(scope[key],f'scope.{key}')
    edges=unique_strings(scope['security_edge_assurance_refs'],'security_edge_assurance_refs')
    for ref in edges:
        opaque_ref(ref,'security_edge_assurance_ref')
    accepted=instant(scope['accepted_at'],'scope.accepted_at')
    review_by=instant(scope['review_by'],'scope.review_by')
    if accepted>as_of or review_by<=accepted:
        raise ValueError('Address-family scope chronology invalid')

    _,native_valid=evidence_block(record['native_path'],NATIVE_PATH_KEYS,'native_path',as_of=as_of)
    _,security_valid=evidence_block(record['security_equivalence'],SECURITY_KEYS,'security_equivalence',as_of=as_of)
    _,service_valid=evidence_block(record['shared_services'],SERVICE_KEYS,'shared_services',as_of=as_of)
    _,pmtu_valid=evidence_block(record['pmtu'],PMTU_KEYS,'pmtu',as_of=as_of)
    _,failure_valid=evidence_block(record['failure_recovery'],FAILURE_KEYS,'failure_recovery',as_of=as_of)
    _,operations_valid=evidence_block(record['operations'],OPERATIONS_KEYS,'operations',as_of=as_of)

    gaps=record['residual_gaps']
    if not isinstance(gaps,list) or len(gaps)>1024:
        raise ValueError('Residual address-family gaps must be a bounded list')
    gap_ids=set();open_gaps=[];gap_reviews=[]
    for gap in gaps:
        if not isinstance(gap,dict) or set(gap)!=GAP_KEYS:
            raise ValueError('Residual address-family gap shape invalid')
        gap_id=identifier(gap['gap_id'],'gap_id')
        if gap_id in gap_ids:
            raise ValueError('Duplicate residual address-family gap ID')
        gap_ids.add(gap_id)
        if gap['status'] not in GAP_STATES:
            raise ValueError('Unknown residual address-family gap state')
        opaque_ref(gap['owner_ref'],'gap.owner_ref')
        opaque_ref(gap['treatment_ref'],'gap.treatment_ref')
        review=instant(gap['review_by'],'gap.review_by')
        gap_reviews.append(review)
        if gap['status']=='OPEN':
            if gap['decision_ref'] is not None:
                raise ValueError('OPEN address-family gap cannot carry an acceptance decision')
            open_gaps.append(gap_id)
        else:
            opaque_ref(gap['decision_ref'],'gap.decision_ref')

    refs=unique_strings(record['source_refs'],'source_refs')
    for ref in refs:
        repository_ref(ref,root)

    review_due=as_of>=review_by or any(as_of>=x for x in gap_reviews)
    packet_due=as_of>=min(native_valid,security_valid,pmtu_valid,failure_valid)
    dependency_due=as_of>=min(service_valid,operations_valid)

    if record['state']=='CURRENT_QUALIFIED':
        if review_due or packet_due or dependency_due:
            raise ValueError('CURRENT_QUALIFIED address-family record has expired review/evidence')
        if open_gaps:
            raise ValueError('CURRENT_QUALIFIED address-family record cannot contain OPEN residual gaps')
    elif record['state']=='REVIEW_DUE':
        if not review_due:
            raise ValueError('REVIEW_DUE requires expired scope or gap review')
    elif record['state']=='PACKET_TEST_DUE':
        if review_due or not packet_due:
            raise ValueError('PACKET_TEST_DUE requires current review and expired native/security/PMTU/failure evidence')
    elif record['state']=='DEPENDENCY_DUE':
        if review_due or packet_due or not dependency_due:
            raise ValueError('DEPENDENCY_DUE requires current packet evidence and expired service/operations evidence')
    elif record['state']=='GAPS_OPEN':
        if review_due or packet_due or dependency_due or not open_gaps:
            raise ValueError('GAPS_OPEN requires current evidence and at least one OPEN residual gap')
    elif record['state']=='UNCERTAIN':
        pass

    return {
        'assurance_id':record['assurance_id'],
        'generation':record['generation'],
        'state':record['state'],
        'qualification_id':record['qualification_id'],
        'platform':record['platform'],
        'offered_mode':mode,
        'offered_families':families,
        'service_class_ref':scope['service_class_ref'],
        'platform_profile_ref':scope['platform_profile_ref'],
        'platform_qualification_ref':scope['platform_qualification_ref'],
        'security_edge_assurance_refs':sorted(edges),
        'review_by':review_by.isoformat(),
        'open_gap_ids':sorted(open_gaps)
    }


def validate(index,*,as_of=None,root=ROOT):
    if as_of is None: as_of=datetime.now(timezone.utc)
    if not isinstance(as_of,datetime) or as_of.tzinfo is None:
        raise ValueError('Timezone-aware as_of required')
    as_of=as_of.astimezone(timezone.utc)
    if set(index)!=INDEX_KEYS:
        raise ValueError('Unexpected address-family assurance-index fields')
    if index['format']!=FORMAT or index['status']!=STATUS:
        raise ValueError('Unsupported address-family assurance format or authority boundary')
    revision=index['reviewed_source_revision']
    if not isinstance(revision,str) or not re.fullmatch(r'[0-9a-f]{40}',revision):
        raise ValueError('Reviewed source revision must be an exact Git SHA')
    records=index['records']
    if not isinstance(records,list) or len(records)>256:
        raise ValueError('Address-family assurance records must be a bounded list')
    ids=set();qualifications=set();out=[]
    for raw in records:
        item=validate_record(raw,as_of=as_of,root=root)
        if item['assurance_id'] in ids:
            raise ValueError('Duplicate address-family assurance ID')
        if item['qualification_id'] in qualifications:
            raise ValueError('Duplicate active address-family assurance for one qualification ID')
        ids.add(item['assurance_id']);qualifications.add(item['qualification_id']);out.append(item)
    return {
        'records':out,'record_count':len(out),
        'current_qualified_count':sum(x['state']=='CURRENT_QUALIFIED' for x in out),
        'review_due_count':sum(x['state']=='REVIEW_DUE' for x in out),
        'packet_test_due_count':sum(x['state']=='PACKET_TEST_DUE' for x in out),
        'dependency_due_count':sum(x['state']=='DEPENDENCY_DUE' for x in out),
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
            'status':'PASSED_ADDRESS_FAMILY_ASSURANCE','as_of':as_of.isoformat(),
            **{k:v for k,v in summary.items() if k!='records'},
            'may_allocate_address':False,'may_enable_ipv6':False,
            'may_change_route':False,'may_change_policy':False,
            'may_change_shared_service':False,'may_apply':False,'may_activate':False,
            'limits':[
                'A successful local IPv6 laboratory is not native offered-family qualification.',
                'Ping or address assignment alone does not establish security equivalence or complete dependencies.',
                'ICMPv6/PMTU and local-protocol controls are part of the offered service, not optional diagnostics.',
                'The repository validates exported evidence only and never enables an address family.'
            ]
        },indent=2)); return 0
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({
            'status':'FAILED_ADDRESS_FAMILY_ASSURANCE','reason':str(exc),
            'may_allocate_address':False,'may_enable_ipv6':False,
            'may_change_route':False,'may_change_policy':False,
            'may_change_shared_service':False,'may_apply':False,'may_activate':False
        },indent=2)); return 2


if __name__=='__main__':
    raise SystemExit(main())
