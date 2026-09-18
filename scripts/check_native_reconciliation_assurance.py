#!/usr/bin/env python3
"""Validate native readback, writer-fencing and reconciliation assurance evidence.

This repository is not a native writer, lock manager, incident authority, state backend
or repair executor. Records bind externally owned native observations, writer-fencing
evidence and reconciliation decisions. The checker never lists/cancels native tasks,
imports state, releases containment, repairs resources, applies Terraform or activates
production.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'sources/capabilities/native_reconciliation_assurance_index.json'
FORMAT='portable-hosting-native-reconciliation-assurance-index/1'
STATUS='EXPORTED_NATIVE_RECONCILIATION_EVIDENCE_NOT_WRITER_AUTHORITY'
PLATFORMS={'VMWARE_NSX','NUTANIX','OPENSTACK_NEUTRON'}
STATES={
    'CURRENT_RECONCILED','REVIEW_DUE','OBSERVATION_DUE','FENCE_DUE',
    'CONTAINMENT_ACTIVE','RECONCILIATION_REQUIRED','GAPS_OPEN','UNCERTAIN'
}
OBSERVATION_OUTCOMES={
    'MATCHED_ACCEPTED_SCOPE','PENDING_NATIVE_TASK','PARTIAL_FAILURE',
    'DIVERGENCE_OBSERVED','UNKNOWN'
}
FENCE_STATES={'VERIFIED_FENCED','NOT_FENCED','UNKNOWN'}
CONTAINMENT_STATES={'NONE','ACTIVE','RELEASED'}
RECONCILIATION_STATES={
    'RECONCILED_NO_CHANGE','RECONCILED_ADOPTED_CURRENT_STATE',
    'RECONCILED_FORWARD_REPAIR_DECIDED','RECONCILED_COMPENSATION_DECIDED',
    'PENDING_DECISION'
}
GAP_STATES={'OPEN','ACCEPTED'}
ID=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{1,191}$')
SHA256=re.compile(r'^[0-9a-f]{64}$')

INDEX_KEYS={'format','status','reviewed_source_revision','records'}
RECORD_KEYS={
    'assurance_id','generation','state','operation_id','platform','scope',
    'native_interface','observation','writer_fence','containment',
    'reconciliation','residual_gaps','source_refs'
}
SCOPE_KEYS={
    'engineering_record_ref','operation_scope_ref','resource_set_ref',
    'change_record_ref','operation_owner_ref','operation_generation',
    'accepted_at','review_by'
}
INTERFACE_KEYS={
    'installed_tuple_ref','api_profile_ref','api_version_ref','rbac_evidence_ref',
    'default_omission_evidence_ref','version_token_evidence_ref',
    'task_entity_coverage_ref','coverage_state','observed_at','valid_until'
}
OBSERVATION_KEYS={
    'manifest_ref','report_ref','manifest_sha256','report_sha256','outcome',
    'stable_samples','observed_at','valid_until'
}
FENCE_KEYS={
    'state','mechanism_ref','scope_ref','owner_ref','competing_writer_review_ref',
    'observed_at','valid_until'
}
CONTAINMENT_KEYS={
    'state','authority_ref','scope_ref','state_evidence_ref','release_decision_ref'
}
RECONCILIATION_KEYS={
    'status','decision_ref','source_of_truth_reconciliation_ref','data_impact_ref',
    'shared_dependency_ref','repair_plan_ref','operation_generation','decided_at'
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
        raise ValueError('Native reconciliation assurance index exceeds bounded size')
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
        raise ValueError('Native reconciliation assurance index must be an object')
    return value


def validate_record(record,*,as_of,root=ROOT):
    if not isinstance(record,dict) or set(record)!=RECORD_KEYS:
        raise ValueError('Native reconciliation record has unexpected or missing fields')
    identifier(record['assurance_id'],'assurance_id')
    identifier(record['operation_id'],'operation_id')
    positive_int(record['generation'],'generation')
    if record['state'] not in STATES:
        raise ValueError('Unknown native reconciliation assurance state')
    if record['platform'] not in PLATFORMS:
        raise ValueError('Unknown native observation platform')

    scope=record['scope']
    if not isinstance(scope,dict) or set(scope)!=SCOPE_KEYS:
        raise ValueError('Operation scope shape invalid')
    repository_ref(scope['engineering_record_ref'],root)
    for key in ('operation_scope_ref','resource_set_ref','change_record_ref','operation_owner_ref'):
        opaque_ref(scope[key],f'scope.{key}')
    operation_generation=positive_int(scope['operation_generation'],'scope.operation_generation')
    accepted=instant(scope['accepted_at'],'scope.accepted_at')
    review_by=instant(scope['review_by'],'scope.review_by')
    if accepted>as_of or review_by<=accepted:
        raise ValueError('Operation scope chronology invalid')

    interface=record['native_interface']
    if not isinstance(interface,dict) or set(interface)!=INTERFACE_KEYS:
        raise ValueError('Native interface applicability shape invalid')
    for key in (
        'installed_tuple_ref','api_profile_ref','api_version_ref','rbac_evidence_ref',
        'default_omission_evidence_ref','version_token_evidence_ref',
        'task_entity_coverage_ref'
    ):
        opaque_ref(interface[key],f'native_interface.{key}')
    if interface['coverage_state']!='EXACT_ACCEPTED_SCOPE':
        raise ValueError('Native interface coverage must represent the exact accepted scope')
    interface_observed=instant(interface['observed_at'],'native_interface.observed_at')
    interface_valid=instant(interface['valid_until'],'native_interface.valid_until')
    if interface_observed>as_of or interface_valid<=interface_observed:
        raise ValueError('Native interface evidence chronology invalid')

    observation=record['observation']
    if not isinstance(observation,dict) or set(observation)!=OBSERVATION_KEYS:
        raise ValueError('Native observation shape invalid')
    for key in ('manifest_ref','report_ref'):
        opaque_ref(observation[key],f'observation.{key}')
    for key in ('manifest_sha256','report_sha256'):
        if not isinstance(observation[key],str) or not SHA256.fullmatch(observation[key]):
            raise ValueError(f'observation.{key}: exact SHA-256 required')
    if observation['outcome'] not in OBSERVATION_OUTCOMES:
        raise ValueError('Unknown native observation outcome')
    stable_samples=positive_int(observation['stable_samples'],'observation.stable_samples')
    if observation['outcome']=='MATCHED_ACCEPTED_SCOPE' and stable_samples<2:
        raise ValueError('Matched native observation requires at least two stable samples')
    observation_observed=instant(observation['observed_at'],'observation.observed_at')
    observation_valid=instant(observation['valid_until'],'observation.valid_until')
    if observation_observed>as_of or observation_valid<=observation_observed:
        raise ValueError('Native observation chronology invalid')

    fence=record['writer_fence']
    if not isinstance(fence,dict) or set(fence)!=FENCE_KEYS:
        raise ValueError('Writer-fence evidence shape invalid')
    if fence['state'] not in FENCE_STATES:
        raise ValueError('Unknown writer-fence state')
    for key in ('mechanism_ref','scope_ref','owner_ref','competing_writer_review_ref'):
        opaque_ref(fence[key],f'writer_fence.{key}')
    fence_observed=instant(fence['observed_at'],'writer_fence.observed_at')
    fence_valid=instant(fence['valid_until'],'writer_fence.valid_until')
    if fence_observed>as_of or fence_valid<=fence_observed:
        raise ValueError('Writer-fence chronology invalid')

    containment=record['containment']
    if not isinstance(containment,dict) or set(containment)!=CONTAINMENT_KEYS:
        raise ValueError('Containment evidence shape invalid')
    if containment['state'] not in CONTAINMENT_STATES:
        raise ValueError('Unknown containment state')
    for key in ('authority_ref','scope_ref','state_evidence_ref'):
        opaque_ref(containment[key],f'containment.{key}')
    if containment['state']=='RELEASED':
        opaque_ref(containment['release_decision_ref'],'containment.release_decision_ref')
    elif containment['release_decision_ref'] is not None:
        raise ValueError('Containment release decision is valid only for RELEASED state')

    reconciliation=record['reconciliation']
    if not isinstance(reconciliation,dict) or set(reconciliation)!=RECONCILIATION_KEYS:
        raise ValueError('Reconciliation decision shape invalid')
    if reconciliation['status'] not in RECONCILIATION_STATES:
        raise ValueError('Unknown reconciliation status')
    for key in ('source_of_truth_reconciliation_ref','data_impact_ref','shared_dependency_ref'):
        opaque_ref(reconciliation[key],f'reconciliation.{key}')
    if positive_int(reconciliation['operation_generation'],'reconciliation.operation_generation')!=operation_generation:
        raise ValueError('Reconciliation generation does not match the scoped operation generation')
    if reconciliation['status']=='PENDING_DECISION':
        if any(reconciliation[key] is not None for key in ('decision_ref','repair_plan_ref','decided_at')):
            raise ValueError('Pending reconciliation cannot carry a completed decision')
    else:
        opaque_ref(reconciliation['decision_ref'],'reconciliation.decision_ref')
        decided=instant(reconciliation['decided_at'],'reconciliation.decided_at')
        if decided>as_of:
            raise ValueError('Reconciliation decision is future-dated')
        if decided<max(interface_observed,observation_observed,fence_observed):
            raise ValueError('Reconciliation decision predates the native observation or writer-fence evidence')
        if reconciliation['status'] in (
            'RECONCILED_FORWARD_REPAIR_DECIDED','RECONCILED_COMPENSATION_DECIDED'
        ):
            opaque_ref(reconciliation['repair_plan_ref'],'reconciliation.repair_plan_ref')
        elif reconciliation['repair_plan_ref'] is not None:
            raise ValueError('Repair-plan reference belongs only to repair/compensation decisions')

    gaps=record['residual_gaps']
    if not isinstance(gaps,list) or len(gaps)>1024:
        raise ValueError('Residual reconciliation gaps must be a bounded list')
    gap_ids=set();open_gaps=[];gap_reviews=[]
    for gap in gaps:
        if not isinstance(gap,dict) or set(gap)!=GAP_KEYS:
            raise ValueError('Residual reconciliation gap shape invalid')
        gap_id=identifier(gap['gap_id'],'gap_id')
        if gap_id in gap_ids:
            raise ValueError('Duplicate residual reconciliation gap ID')
        gap_ids.add(gap_id)
        if gap['status'] not in GAP_STATES:
            raise ValueError('Unknown residual reconciliation gap state')
        opaque_ref(gap['owner_ref'],'gap.owner_ref')
        opaque_ref(gap['treatment_ref'],'gap.treatment_ref')
        gap_review=instant(gap['review_by'],'gap.review_by')
        gap_reviews.append(gap_review)
        if gap['status']=='OPEN':
            if gap['decision_ref'] is not None:
                raise ValueError('OPEN reconciliation gap cannot carry acceptance decision')
            open_gaps.append(gap_id)
        else:
            opaque_ref(gap['decision_ref'],'gap.decision_ref')

    refs=unique_strings(record['source_refs'],'source_refs')
    for ref in refs:
        repository_ref(ref,root)

    review_due=(as_of>=review_by or any(as_of>=x for x in gap_reviews))
    observation_due=(as_of>=interface_valid or as_of>=observation_valid)
    fence_due=(fence['state']!='VERIFIED_FENCED' or as_of>=fence_valid)
    containment_active=containment['state']=='ACTIVE'
    reconciliation_required=(
        observation['outcome']!='MATCHED_ACCEPTED_SCOPE'
        or reconciliation['status']=='PENDING_DECISION'
    )

    if record['state']=='CURRENT_RECONCILED':
        if review_due or observation_due or fence_due or containment_active or reconciliation_required:
            raise ValueError('CURRENT_RECONCILED requires current matched observation, verified fencing and reconciled containment state')
        if open_gaps:
            raise ValueError('CURRENT_RECONCILED cannot contain OPEN residual gaps')
    elif record['state']=='REVIEW_DUE':
        if not review_due:
            raise ValueError('REVIEW_DUE requires expired scope/gap review')
    elif record['state']=='OBSERVATION_DUE':
        if review_due or not observation_due:
            raise ValueError('OBSERVATION_DUE requires current review and stale interface/observation evidence')
    elif record['state']=='FENCE_DUE':
        if review_due or observation_due or not fence_due:
            raise ValueError('FENCE_DUE requires current observation and unverified/stale fencing')
    elif record['state']=='CONTAINMENT_ACTIVE':
        if review_due or observation_due or fence_due or not containment_active:
            raise ValueError('CONTAINMENT_ACTIVE requires current observation/fencing and active containment')
    elif record['state']=='RECONCILIATION_REQUIRED':
        if review_due or observation_due or fence_due or containment_active or not reconciliation_required:
            raise ValueError('RECONCILIATION_REQUIRED requires current prerequisites and unresolved native outcome')
    elif record['state']=='GAPS_OPEN':
        if review_due or observation_due or fence_due or containment_active or reconciliation_required or not open_gaps:
            raise ValueError('GAPS_OPEN requires current reconciled evidence and OPEN residual gaps')
    elif record['state']=='UNCERTAIN':
        pass

    return {
        'assurance_id':record['assurance_id'],
        'generation':record['generation'],
        'state':record['state'],
        'operation_id':record['operation_id'],
        'platform':record['platform'],
        'engineering_record_ref':scope['engineering_record_ref'],
        'operation_scope_ref':scope['operation_scope_ref'],
        'resource_set_ref':scope['resource_set_ref'],
        'operation_generation':operation_generation,
        'observation_outcome':observation['outcome'],
        'writer_fence_state':fence['state'],
        'containment_state':containment['state'],
        'reconciliation_status':reconciliation['status'],
        'open_gap_ids':sorted(open_gaps)
    }


def validate(index,*,as_of=None,root=ROOT):
    if as_of is None: as_of=datetime.now(timezone.utc)
    if not isinstance(as_of,datetime) or as_of.tzinfo is None:
        raise ValueError('Timezone-aware as_of required')
    as_of=as_of.astimezone(timezone.utc)
    if set(index)!=INDEX_KEYS:
        raise ValueError('Unexpected native reconciliation assurance-index fields')
    if index['format']!=FORMAT or index['status']!=STATUS:
        raise ValueError('Unsupported native reconciliation format or authority boundary')
    revision=index['reviewed_source_revision']
    if not isinstance(revision,str) or not re.fullmatch(r'[0-9a-f]{40}',revision):
        raise ValueError('Reviewed source revision must be an exact Git SHA')
    records=index['records']
    if not isinstance(records,list) or len(records)>1024:
        raise ValueError('Native reconciliation records must be a bounded list')
    ids=set();operations=set();out=[]
    for raw in records:
        item=validate_record(raw,as_of=as_of,root=root)
        if item['assurance_id'] in ids:
            raise ValueError('Duplicate native reconciliation assurance ID')
        if item['operation_id'] in operations:
            raise ValueError('Duplicate active reconciliation assurance for one operation')
        ids.add(item['assurance_id']);operations.add(item['operation_id']);out.append(item)
    return {
        'records':out,'record_count':len(out),
        'current_reconciled_count':sum(x['state']=='CURRENT_RECONCILED' for x in out),
        'review_due_count':sum(x['state']=='REVIEW_DUE' for x in out),
        'observation_due_count':sum(x['state']=='OBSERVATION_DUE' for x in out),
        'fence_due_count':sum(x['state']=='FENCE_DUE' for x in out),
        'containment_active_count':sum(x['state']=='CONTAINMENT_ACTIVE' for x in out),
        'reconciliation_required_count':sum(x['state']=='RECONCILIATION_REQUIRED' for x in out),
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
            'status':'PASSED_NATIVE_RECONCILIATION_ASSURANCE','as_of':as_of.isoformat(),
            **{k:v for k,v in summary.items() if k!='records'},
            'may_list_tasks':False,'may_cancel_task':False,'may_release_containment':False,
            'may_import_state':False,'may_repair':False,'may_apply':False,
            'may_delete':False,'may_activate':False,
            'limits':[
                'A matching readback does not establish writer fencing or permission to resume.',
                'A stopped runner or state lock is not proof that all native writers stopped.',
                'Containment remains above ordinary reconciliation until separately released.',
                'The repository validates exported evidence only and never executes a repair.'
            ]
        },indent=2)); return 0
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({
            'status':'FAILED_NATIVE_RECONCILIATION_ASSURANCE','reason':str(exc),
            'may_list_tasks':False,'may_cancel_task':False,'may_release_containment':False,
            'may_import_state':False,'may_repair':False,'may_apply':False,
            'may_delete':False,'may_activate':False
        },indent=2)); return 2


if __name__=='__main__':
    raise SystemExit(main())
