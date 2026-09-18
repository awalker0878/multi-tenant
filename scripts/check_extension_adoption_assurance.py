#!/usr/bin/env python3
"""Validate bounded extension-adoption and qualification evidence.

This repository is not a bare-metal installer, Kubernetes controller, device manager,
fabric controller, extension scheduler, or production authorization authority. Records
describe externally approved extension scope and evidence only. An extension never
becomes part of the base offered service merely because this checker accepts its record.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'sources/capabilities/extension_adoption_assurance_index.json'
FORMAT='portable-hosting-extension-adoption-assurance-index/1'
STATUS='EXPORTED_EXTENSION_ADOPTION_EVIDENCE_NOT_BASE_SERVICE_AUTHORITY'
STATES={'CURRENT_ADOPTED','REVIEW_DUE','QUALIFICATION_DUE','GAPS_OPEN','UNCERTAIN'}
KINDS={
    'BARE_METAL','CONTAINER_HOSTING','SPECIAL_DEVICE_ACCELERATOR',
    'L2_STRETCH_OR_CROSS_STACK','HIGHER_ASSURANCE','FUTURE_PLATFORM'
}
QUAL_DIMENSIONS={
    'topology','management','host_control_plane','network',
    'storage','lifecycle','recovery'
}
KIND_REQUIREMENTS={
    'BARE_METAL':{
        'bmc_boot_firmware','port_gateway_authority',
        'data_attachment','media_sanitization'
    },
    'CONTAINER_HOSTING':{
        'control_plane_node_sharing','workload_admission',
        'network_policy_enforcement','privileged_workload_restrictions',
        'secrets_and_storage','cluster_recovery'
    },
    'SPECIAL_DEVICE_ACCELERATOR':{
        'device_tenancy','host_compatibility',
        'reset_and_data_handling','mobility_limits'
    },
    'L2_STRETCH_OR_CROSS_STACK':{
        'gateway_and_partition_behavior','writer_fencing',
        'latency_failure_coupling','cross_scope_ownership'
    },
    'HIGHER_ASSURANCE':{
        'source_applicability','dedication_scope',
        'infrastructure_control_scope','explicit_approval'
    },
    'FUTURE_PLATFORM':{
        'supported_stack','interface_equivalence',
        'conformance_scope','exit_and_recovery'
    },
}
GAP_STATES={'OPEN','ACCEPTED'}
ID=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{1,191}$')
INDEX_KEYS={'format','status','reviewed_source_revision','records'}
RECORD_KEYS={
    'assurance_id','generation','state','extension_kind','extension_id',
    'scope','design','specific_evidence','qualification',
    'unsupported_capabilities','mandatory_control_weakening',
    'residual_gaps','source_refs'
}
SCOPE_KEYS={
    'extension_profile_ref','service_class_ref','adoption_decision_ref',
    'accepted_at','review_by','extension_owner_ref','base_service_status',
    'portability_impact_ref'
}
DESIGN_KEYS={
    'topology_ref','trust_boundaries_ref','failure_model_ref','management_ref',
    'network_ref','storage_ref','identity_ref','provisioning_ref',
    'recovery_ref','retirement_ref'
}
QUAL_KEYS={
    'applicable_test_sets','dimension_evidence','qualified_at','valid_until',
    'decision_ref','authority_role'
}
GAP_KEYS={
    'gap_id','status','owner_ref','treatment_ref','decision_ref','review_by'
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
        raise ValueError('Extension assurance index exceeds bounded size')
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
        raise ValueError('Extension assurance index must be an object')
    return value


def validate_record(record,*,as_of,root=ROOT):
    if not isinstance(record,dict) or set(record)!=RECORD_KEYS:
        raise ValueError('Extension assurance record has unexpected or missing fields')
    identifier(record['assurance_id'],'assurance_id')
    identifier(record['extension_id'],'extension_id')
    positive_int(record['generation'],'generation')
    if record['state'] not in STATES:
        raise ValueError('Unknown extension assurance state')
    if record['extension_kind'] not in KINDS:
        raise ValueError('Unknown extension kind')

    scope=record['scope']
    if not isinstance(scope,dict) or set(scope)!=SCOPE_KEYS:
        raise ValueError('Extension scope shape invalid')
    for key in (
        'extension_profile_ref','service_class_ref','adoption_decision_ref',
        'extension_owner_ref','portability_impact_ref'
    ):
        opaque_ref(scope[key],f'scope.{key}')
    accepted=instant(scope['accepted_at'],'scope.accepted_at')
    review_by=instant(scope['review_by'],'scope.review_by')
    if accepted>as_of or review_by<=accepted:
        raise ValueError('Extension scope chronology invalid')
    if scope['base_service_status']!='EXTENSION_ONLY':
        raise ValueError('Bounded extension cannot be represented as part of the base offered service')

    design=record['design']
    if not isinstance(design,dict) or set(design)!=DESIGN_KEYS:
        raise ValueError('Complete extension topology/lifecycle design references are required')
    for key,value in design.items():
        opaque_ref(value,f'design.{key}')

    specific=record['specific_evidence']
    required_specific=KIND_REQUIREMENTS[record['extension_kind']]
    if not isinstance(specific,dict) or set(specific)!=required_specific:
        raise ValueError('Extension-kind-specific evidence is incomplete or contains unexpected fields')
    for key,value in specific.items():
        opaque_ref(value,f'specific_evidence.{key}')

    qualification=record['qualification']
    if not isinstance(qualification,dict) or set(qualification)!=QUAL_KEYS:
        raise ValueError('Extension qualification shape invalid')
    tests=unique_strings(
        qualification['applicable_test_sets'],'qualification.applicable_test_sets')
    if any(len(x)>128 for x in tests):
        raise ValueError('Extension test-set reference too long')
    dimensions=qualification['dimension_evidence']
    if not isinstance(dimensions,dict) or set(dimensions)!=QUAL_DIMENSIONS:
        raise ValueError('All extension qualification dimensions require evidence')
    for key,value in dimensions.items():
        opaque_ref(value,f'qualification.dimension_evidence.{key}')
    qualified=instant(qualification['qualified_at'],'qualification.qualified_at')
    valid_until=instant(qualification['valid_until'],'qualification.valid_until')
    if qualified>as_of or valid_until<=qualified:
        raise ValueError('Extension qualification chronology invalid')
    opaque_ref(qualification['decision_ref'],'qualification.decision_ref')
    bounded(qualification['authority_role'],'qualification.authority_role')

    unsupported=unique_strings(
        record['unsupported_capabilities'],'unsupported_capabilities',allow_empty=True)
    if record['mandatory_control_weakening']!='DENIED':
        raise ValueError('Unsupported extension capability cannot be emulated by weakening a mandatory control')

    gaps=record['residual_gaps']
    if not isinstance(gaps,list) or len(gaps)>1024:
        raise ValueError('Residual extension gaps must be a bounded list')
    gap_ids=set()
    open_gaps=[]
    gap_review_dates=[]
    for gap in gaps:
        if not isinstance(gap,dict) or set(gap)!=GAP_KEYS:
            raise ValueError('Residual extension gap shape invalid')
        gap_id=identifier(gap['gap_id'],'gap_id')
        if gap_id in gap_ids:
            raise ValueError('Duplicate residual extension gap ID')
        gap_ids.add(gap_id)
        if gap['status'] not in GAP_STATES:
            raise ValueError('Unknown residual extension gap state')
        opaque_ref(gap['owner_ref'],'gap.owner_ref')
        opaque_ref(gap['treatment_ref'],'gap.treatment_ref')
        gap_review=instant(gap['review_by'],'gap.review_by')
        gap_review_dates.append(gap_review)
        if gap['status']=='OPEN':
            if gap['decision_ref'] is not None:
                raise ValueError('OPEN extension gap cannot carry an acceptance decision')
            open_gaps.append(gap_id)
        else:
            opaque_ref(gap['decision_ref'],'gap.decision_ref')

    refs=unique_strings(record['source_refs'],'source_refs')
    for ref in refs:
        repository_ref(ref,root)

    review_due=(as_of>=review_by or any(as_of>=x for x in gap_review_dates))
    qualification_due=as_of>=valid_until

    if record['state']=='CURRENT_ADOPTED':
        if review_due:
            raise ValueError('CURRENT_ADOPTED record has expired scope/gap review')
        if qualification_due:
            raise ValueError('CURRENT_ADOPTED record has expired qualification evidence')
        if open_gaps:
            raise ValueError('CURRENT_ADOPTED record cannot contain OPEN residual gaps')
    elif record['state']=='REVIEW_DUE':
        if not review_due:
            raise ValueError('REVIEW_DUE requires expired scope or residual-gap review')
    elif record['state']=='QUALIFICATION_DUE':
        if review_due or not qualification_due:
            raise ValueError('QUALIFICATION_DUE requires current scope review and expired qualification')
    elif record['state']=='GAPS_OPEN':
        if review_due or qualification_due:
            raise ValueError('GAPS_OPEN is reserved for current evidence with unresolved gaps')
        if not open_gaps:
            raise ValueError('GAPS_OPEN requires at least one OPEN residual gap')
    elif record['state']=='UNCERTAIN':
        pass

    return {
        'assurance_id':record['assurance_id'],
        'generation':record['generation'],
        'state':record['state'],
        'extension_kind':record['extension_kind'],
        'extension_id':record['extension_id'],
        'extension_profile_ref':scope['extension_profile_ref'],
        'service_class_ref':scope['service_class_ref'],
        'base_service_status':scope['base_service_status'],
        'portability_impact_ref':scope['portability_impact_ref'],
        'qualification_valid_until':valid_until.isoformat(),
        'unsupported_capabilities':sorted(unsupported),
        'open_gap_ids':sorted(open_gaps),
    }


def validate(index,*,as_of=None,root=ROOT):
    if as_of is None:
        as_of=datetime.now(timezone.utc)
    if not isinstance(as_of,datetime) or as_of.tzinfo is None:
        raise ValueError('Timezone-aware as_of required')
    as_of=as_of.astimezone(timezone.utc)
    if set(index)!=INDEX_KEYS:
        raise ValueError('Unexpected extension assurance-index fields')
    if index['format']!=FORMAT or index['status']!=STATUS:
        raise ValueError('Unsupported extension assurance format or authority boundary')
    revision=index['reviewed_source_revision']
    if not isinstance(revision,str) or not re.fullmatch(r'[0-9a-f]{40}',revision):
        raise ValueError('Reviewed source revision must be an exact Git SHA')
    records=index['records']
    if not isinstance(records,list) or len(records)>256:
        raise ValueError('Extension assurance records must be a bounded list')
    ids=set()
    extension_ids=set()
    out=[]
    for raw in records:
        checked=validate_record(raw,as_of=as_of,root=root)
        if checked['assurance_id'] in ids:
            raise ValueError('Duplicate extension assurance ID')
        if checked['extension_id'] in extension_ids:
            raise ValueError('Duplicate active extension assurance for one extension ID')
        ids.add(checked['assurance_id'])
        extension_ids.add(checked['extension_id'])
        out.append(checked)
    return {
        'records':out,
        'record_count':len(out),
        'current_adopted_count':sum(x['state']=='CURRENT_ADOPTED' for x in out),
        'review_due_count':sum(x['state']=='REVIEW_DUE' for x in out),
        'qualification_due_count':sum(x['state']=='QUALIFICATION_DUE' for x in out),
        'gaps_open_count':sum(x['state']=='GAPS_OPEN' for x in out),
        'uncertain_count':sum(x['state']=='UNCERTAIN' for x in out),
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
            'status':'PASSED_EXPORTED_EXTENSION_ADOPTION_ASSURANCE',
            'as_of':as_of.isoformat(),
            **{k:v for k,v in summary.items() if k!='records'},
            'may_add_to_base_service':False,
            'may_provision_extension':False,
            'may_change_physical_fabric':False,
            'may_create_cluster':False,
            'may_assign_device':False,
            'may_apply':False,
            'may_activate':False,
            'limits':[
                'All accepted records remain EXTENSION_ONLY; this checker cannot expand the base service.',
                'Namespaces, projects and physical VRFs are not sufficient evidence of a complete tenancy/security boundary.',
                'Unsupported capabilities must stay explicit; mandatory controls cannot be weakened to imitate support.',
                'The repository validates exported adoption evidence only and never provisions an extension.'
            ]
        },indent=2))
        return 0
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({
            'status':'FAILED_EXPORTED_EXTENSION_ADOPTION_ASSURANCE',
            'reason':str(exc),
            'may_add_to_base_service':False,
            'may_provision_extension':False,
            'may_change_physical_fabric':False,
            'may_create_cluster':False,
            'may_assign_device':False,
            'may_apply':False,
            'may_activate':False
        },indent=2))
        return 2


if __name__=='__main__':
    raise SystemExit(main())
