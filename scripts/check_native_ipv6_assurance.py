#!/usr/bin/env python3
"""Validate native IPv6/address-family qualification evidence.

This repository is not a native network controller, IPAM/DHCPv6 service, security edge,
routing system or production authorization authority. Records contain externally owned
evidence for an offered IPv6-only or dual-stack service class. The checker never changes
addresses, routes, neighbour controls, MTU, firewall policy, shared services or activation.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'sources/capabilities/native_ipv6_assurance_index.json'
FORMAT='portable-hosting-native-ipv6-assurance-index/1'
STATUS='EXPORTED_NATIVE_IPV6_EVIDENCE_NOT_ADDRESS_FAMILY_AUTHORITY'
STATES={'CURRENT_QUALIFIED','REVIEW_DUE','QUALIFICATION_DUE','GAPS_OPEN','UNCERTAIN'}
PLATFORMS={'NUTANIX','VMWARE_NSX','OPENSTACK'}
FAMILY_MODES={'IPV6_ONLY','DUAL_STACK'}
ADDRESSING_MODES={'STATIC','SLAAC','DHCPV6','SLAAC_DHCPV6'}
GAP_STATES={'OPEN','ACCEPTED'}
QUAL_OUTCOMES={'PASSED_NATIVE_ADDRESS_FAMILY_QUALIFICATION','FAILED_NATIVE_ADDRESS_FAMILY_QUALIFICATION','UNKNOWN_OR_INCOMPLETE'}
ID=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{1,191}$')

INDEX_KEYS={'format','status','reviewed_source_revision','records'}
RECORD_KEYS={
    'assurance_id','generation','state','platform','scope','platform_support',
    'addressing','local_protocols','routing_security','mtu_pmtu',
    'shared_services','failure_recovery','qualification','residual_gaps','source_refs'
}
SCOPE_KEYS={
    'site_ref','service_class_ref','platform_profile_ref','security_edge_profile_ref',
    'family_mode','accepted_at','review_by','owner_ref'
}
PLATFORM_KEYS={
    'installed_tuple_ref','api_profile_ref','network_backend_ref',
    'supported_address_mode_ref','endpoint_profile_ref','management_exclusion_ref'
}
ADDRESSING_KEYS={
    'mode','prefix_scope_ref','allocation_authority_ref','dad_ref',
    'source_address_validation_ref','neighbor_discovery_ref','router_advertisement_ref',
    'dhcpv6_ref','redirect_policy_ref','transition_mechanism_ref'
}
LOCAL_KEYS={
    'neighbor_solicitation_advertisement_ref','icmpv6_error_ref','packet_too_big_ref',
    'mld_ref','fragment_policy_ref','extension_header_policy_ref','hop_limit_validation_ref'
}
ROUTING_KEYS={
    'route_authority_ref','forward_reply_path_ref','same_host_distributed_ref',
    'security_outcome_parity_ref','security_edge_ref','management_exclusion_ref',
    'origin_specific_reply_ref','bypass_review_ref'
}
MTU_KEYS={
    'packet_frame_convention_ref','workload_mtu_ref','overlay_encapsulation_budget_ref',
    'handoff_mtu_ref','pmtud_ref','ptb_blackhole_negative_ref'
}
SERVICE_KEYS={
    'required_service_matrix_ref','dns_aaaa_udp_tcp_ref','identity_tls_ref',
    'time_service_ref','telemetry_ref','artifact_repository_ref','protection_recovery_ref'
}
FAILURE_KEYS={
    'route_withdrawal_ref','edge_or_link_failure_ref','address_dad_recovery_ref',
    'survivor_capacity_ref','recovery_service_path_ref','no_ipv4_fallback_ref',
    'independent_ipv4_campaign_ref'
}
QUAL_KEYS={
    'native_test_campaign_ref','target_version_ref','healthy_controls_ref',
    'negative_tests_ref','operational_acceptance_ref','observed_at','valid_until','outcome'
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
        raise ValueError('Native IPv6 assurance index exceeds bounded size')
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
        raise ValueError('Native IPv6 assurance index must be an object')
    return value


def ref_fields(obj,keys,label):
    if not isinstance(obj,dict) or set(obj)!=keys:
        raise ValueError(f'{label} shape invalid')
    for key,value in obj.items():
        opaque_ref(value,f'{label}.{key}')


def validate_record(record,*,as_of,root=ROOT):
    if not isinstance(record,dict) or set(record)!=RECORD_KEYS:
        raise ValueError('Native IPv6 assurance record has unexpected or missing fields')
    identifier(record['assurance_id'],'assurance_id')
    positive_int(record['generation'],'generation')
    if record['state'] not in STATES:
        raise ValueError('Unknown native IPv6 assurance state')
    if record['platform'] not in PLATFORMS:
        raise ValueError('Unknown native platform family')

    scope=record['scope']
    if not isinstance(scope,dict) or set(scope)!=SCOPE_KEYS:
        raise ValueError('Address-family scope shape invalid')
    for key in ('site_ref','service_class_ref','platform_profile_ref','security_edge_profile_ref','owner_ref'):
        opaque_ref(scope[key],f'scope.{key}')
    if scope['family_mode'] not in FAMILY_MODES:
        raise ValueError('Unknown address-family service mode')
    accepted=instant(scope['accepted_at'],'scope.accepted_at')
    review_by=instant(scope['review_by'],'scope.review_by')
    if accepted>as_of or review_by<=accepted:
        raise ValueError('Address-family scope chronology invalid')

    ref_fields(record['platform_support'],PLATFORM_KEYS,'platform_support')

    addressing=record['addressing']
    if not isinstance(addressing,dict) or set(addressing)!=ADDRESSING_KEYS:
        raise ValueError('IPv6 addressing evidence shape invalid')
    if addressing['mode'] not in ADDRESSING_MODES:
        raise ValueError('Unknown IPv6 addressing mode')
    for key in ADDRESSING_KEYS-{'mode'}:
        opaque_ref(addressing[key],f'addressing.{key}')

    ref_fields(record['local_protocols'],LOCAL_KEYS,'local_protocols')
    ref_fields(record['routing_security'],ROUTING_KEYS,'routing_security')
    ref_fields(record['mtu_pmtu'],MTU_KEYS,'mtu_pmtu')
    ref_fields(record['shared_services'],SERVICE_KEYS,'shared_services')

    failure=record['failure_recovery']
    if not isinstance(failure,dict) or set(failure)!=FAILURE_KEYS:
        raise ValueError('IPv6 failure/recovery evidence shape invalid')
    for key in FAILURE_KEYS-{'no_ipv4_fallback_ref','independent_ipv4_campaign_ref'}:
        opaque_ref(failure[key],f'failure_recovery.{key}')
    if scope['family_mode']=='IPV6_ONLY':
        opaque_ref(failure['no_ipv4_fallback_ref'],'failure_recovery.no_ipv4_fallback_ref')
        if failure['independent_ipv4_campaign_ref'] is not None:
            raise ValueError('IPv6-only service must not carry dual-stack IPv4 campaign evidence')
    else:
        opaque_ref(failure['independent_ipv4_campaign_ref'],'failure_recovery.independent_ipv4_campaign_ref')
        if failure['no_ipv4_fallback_ref'] is not None:
            raise ValueError('Dual-stack service uses independent-family evidence rather than IPv6-only fallback field')

    qualification=record['qualification']
    if not isinstance(qualification,dict) or set(qualification)!=QUAL_KEYS:
        raise ValueError('Native IPv6 qualification evidence shape invalid')
    for key in (
        'native_test_campaign_ref','target_version_ref','healthy_controls_ref',
        'negative_tests_ref','operational_acceptance_ref'
    ):
        opaque_ref(qualification[key],f'qualification.{key}')
    if qualification['outcome'] not in QUAL_OUTCOMES:
        raise ValueError('Unknown native IPv6 qualification outcome')
    observed=instant(qualification['observed_at'],'qualification.observed_at')
    valid_until=instant(qualification['valid_until'],'qualification.valid_until')
    if observed>as_of or valid_until<=observed or observed<accepted:
        raise ValueError('Native IPv6 qualification chronology invalid')

    gaps=record['residual_gaps']
    if not isinstance(gaps,list) or len(gaps)>1024:
        raise ValueError('Residual IPv6 gaps must be a bounded list')
    gap_ids=set();open_gaps=[];gap_reviews=[]
    for gap in gaps:
        if not isinstance(gap,dict) or set(gap)!=GAP_KEYS:
            raise ValueError('Residual IPv6 gap shape invalid')
        gap_id=identifier(gap['gap_id'],'gap_id')
        if gap_id in gap_ids:
            raise ValueError('Duplicate residual IPv6 gap ID')
        gap_ids.add(gap_id)
        if gap['status'] not in GAP_STATES:
            raise ValueError('Unknown residual IPv6 gap state')
        opaque_ref(gap['owner_ref'],'gap.owner_ref')
        opaque_ref(gap['treatment_ref'],'gap.treatment_ref')
        gap_review=instant(gap['review_by'],'gap.review_by')
        gap_reviews.append(gap_review)
        if gap['status']=='OPEN':
            if gap['decision_ref'] is not None:
                raise ValueError('OPEN IPv6 gap cannot carry acceptance decision')
            open_gaps.append(gap_id)
        else:
            opaque_ref(gap['decision_ref'],'gap.decision_ref')

    refs=unique_strings(record['source_refs'],'source_refs')
    for ref in refs:
        repository_ref(ref,root)

    review_due=(as_of>=review_by or any(as_of>=x for x in gap_reviews))
    qualification_due=as_of>=valid_until

    passed=qualification['outcome']=='PASSED_NATIVE_ADDRESS_FAMILY_QUALIFICATION'
    if record['state']=='CURRENT_QUALIFIED':
        if not passed:
            raise ValueError('CURRENT_QUALIFIED requires a passing native address-family qualification')
        if review_due:
            raise ValueError('CURRENT_QUALIFIED IPv6 record has expired review evidence')
        if qualification_due:
            raise ValueError('CURRENT_QUALIFIED IPv6 record has expired qualification evidence')
        if open_gaps:
            raise ValueError('CURRENT_QUALIFIED IPv6 record cannot contain OPEN residual gaps')
    elif record['state']=='REVIEW_DUE':
        if not passed:
            raise ValueError('REVIEW_DUE requires a previously passing native qualification')
        if not review_due:
            raise ValueError('REVIEW_DUE requires expired scope or gap review')
    elif record['state']=='QUALIFICATION_DUE':
        if not passed:
            raise ValueError('QUALIFICATION_DUE requires a previously passing native qualification')
        if review_due or not qualification_due:
            raise ValueError('QUALIFICATION_DUE requires current review and expired native qualification')
    elif record['state']=='GAPS_OPEN':
        if not passed:
            raise ValueError('GAPS_OPEN requires a passing native qualification with residual gaps')
        if review_due or qualification_due or not open_gaps:
            raise ValueError('GAPS_OPEN requires current qualification and at least one OPEN gap')
    elif record['state']=='UNCERTAIN':
        pass

    return {
        'assurance_id':record['assurance_id'],
        'generation':record['generation'],
        'state':record['state'],
        'platform':record['platform'],
        'site_ref':scope['site_ref'],
        'service_class_ref':scope['service_class_ref'],
        'platform_profile_ref':scope['platform_profile_ref'],
        'security_edge_profile_ref':scope['security_edge_profile_ref'],
        'family_mode':scope['family_mode'],
        'addressing_mode':addressing['mode'],
        'review_by':review_by.isoformat(),
        'qualification_valid_until':valid_until.isoformat(),
        'open_gap_ids':sorted(open_gaps)
    }


def validate(index,*,as_of=None,root=ROOT):
    if as_of is None: as_of=datetime.now(timezone.utc)
    if not isinstance(as_of,datetime) or as_of.tzinfo is None:
        raise ValueError('Timezone-aware as_of required')
    as_of=as_of.astimezone(timezone.utc)
    if set(index)!=INDEX_KEYS:
        raise ValueError('Unexpected native IPv6 assurance-index fields')
    if index['format']!=FORMAT or index['status']!=STATUS:
        raise ValueError('Unsupported native IPv6 assurance format or authority boundary')
    revision=index['reviewed_source_revision']
    if not isinstance(revision,str) or not re.fullmatch(r'[0-9a-f]{40}',revision):
        raise ValueError('Reviewed source revision must be an exact Git SHA')
    records=index['records']
    if not isinstance(records,list) or len(records)>256:
        raise ValueError('Native IPv6 assurance records must be a bounded list')
    ids=set();scopes=set();out=[]
    for raw in records:
        item=validate_record(raw,as_of=as_of,root=root)
        if item['assurance_id'] in ids:
            raise ValueError('Duplicate native IPv6 assurance ID')
        key=(item['site_ref'],item['service_class_ref'],item['platform'],item['family_mode'])
        if key in scopes:
            raise ValueError('Duplicate active IPv6 assurance for one site/service/platform/family scope')
        ids.add(item['assurance_id']);scopes.add(key);out.append(item)
    return {
        'records':out,'record_count':len(out),
        'current_qualified_count':sum(x['state']=='CURRENT_QUALIFIED' for x in out),
        'review_due_count':sum(x['state']=='REVIEW_DUE' for x in out),
        'qualification_due_count':sum(x['state']=='QUALIFICATION_DUE' for x in out),
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
            'status':'PASSED_NATIVE_IPV6_ASSURANCE','as_of':as_of.isoformat(),
            **{k:v for k,v in summary.items() if k!='records'},
            'may_offer_ipv6':False,'may_change_addressing':False,'may_change_routes':False,
            'may_change_security_policy':False,'may_change_mtu':False,
            'may_apply':False,'may_activate':False,
            'limits':[
                'Passing routed Linux fixtures are not native platform or service qualification.',
                'IPv6-only and dual-stack are distinct offered service modes with different evidence.',
                'Security outcomes and required dependencies must remain equivalent across offered families.',
                'The repository validates exported evidence only and never changes native address-family configuration.'
            ]
        },indent=2)); return 0
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({
            'status':'FAILED_NATIVE_IPV6_ASSURANCE','reason':str(exc),
            'may_offer_ipv6':False,'may_change_addressing':False,'may_change_routes':False,
            'may_change_security_policy':False,'may_change_mtu':False,
            'may_apply':False,'may_activate':False
        },indent=2)); return 2


if __name__=='__main__':
    raise SystemExit(main())
