#!/usr/bin/env python3
"""Validate exported operational handover and incident-readiness evidence.

This repository is not an ITSM system, incident command system, privileged-access
manager, monitoring service, or production authorization authority. Records contain
opaque external references and time-bounded evidence only. This checker never changes
access, starts containment, releases containment, performs recovery, changes
infrastructure, or activates production.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'sources/capabilities/operational_handover_assurance_index.json'
FORMAT='portable-hosting-operational-handover-assurance-index/1'
STATUS='EXPORTED_OPERATIONAL_HANDOVER_EVIDENCE_NOT_OPERATIONS_AUTHORITY'
STATES={'CURRENT_ACCEPTED','REVIEW_DUE','EXERCISE_DUE','GAPS_OPEN','UNCERTAIN'}
OBLIGATION_STATES={'OPEN','ACCEPTED'}
DECISION_KEYS={
    'service_change','incident_containment','containment_release',
    'recovery_acceptance','shared_foundation_change','privileged_access'
}
ID=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{1,191}$')
INDEX_KEYS={'format','status','reviewed_source_revision','records'}
RECORD_KEYS={
    'assurance_id','generation','state','request_id','wsd_engineering_ref',
    'scope','handover','decision_owners','credential_review','monitoring',
    'incident_exercise','residual_obligations','source_refs'
}
SCOPE_KEYS={
    'site_ref','service_class_ref','platform_profile_ref',
    'operating_model_ref','recovery_profile_ref'
}
HANDOVER_KEYS={
    'acceptance_ref','accepted_at','review_by','receiving_owner_ref',
    'support_owner_ref','escalation_ref','on_call_ref','as_built_ref',
    'dependency_ref','slo_recovery_ref','capacity_ref','runbook_ref',
    'evidence_package_ref'
}
DECISION_ITEM_KEYS={'owner_ref','evidence_ref'}
CREDENTIAL_KEYS={
    'review_ref','observed_at','valid_until','privileged_paths_ref',
    'custody_ref','break_glass_test_ref','stale_grants'
}
MONITORING_KEYS={
    'monitoring_ref','alerting_ref','evidence_loss_ref',
    'observed_at','valid_until'
}
EXERCISE_KEYS={
    'exercise_ref','test_set','incident_authority_ref','containment_scope_ref',
    'containment_evidence_ref','release_decision_ref','evidence_custody_ref',
    'coordination_ref','recovery_acceptance_ref','emergency_change_reconciliation_ref',
    'started_at','contained_at','released_at','reconciled_at',
    'evidence_valid_until','unrelated_service_impact','outcome'
}
OBLIGATION_KEYS={
    'obligation_id','status','owner_ref','treatment_ref','decision_ref','review_by'
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
        raise ValueError('Operational handover assurance index exceeds bounded size')
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
        raise ValueError('Operational handover assurance index must be an object')
    return value


def validate_record(record,*,as_of,root=ROOT):
    if not isinstance(record,dict) or set(record)!=RECORD_KEYS:
        raise ValueError('Operational handover assurance record has unexpected or missing fields')
    identifier(record['assurance_id'],'assurance_id')
    identifier(record['request_id'],'request_id')
    positive_int(record['generation'],'generation')
    if record['state'] not in STATES:
        raise ValueError('Unknown operational handover assurance state')
    repository_ref(record['wsd_engineering_ref'],root)

    scope=record['scope']
    if not isinstance(scope,dict) or set(scope)!=SCOPE_KEYS:
        raise ValueError('Exact operating scope is required')
    for key,value in scope.items():
        opaque_ref(value,f'scope.{key}')

    handover=record['handover']
    if not isinstance(handover,dict) or set(handover)!=HANDOVER_KEYS:
        raise ValueError('Operational handover shape invalid')
    for key in HANDOVER_KEYS-{'accepted_at','review_by'}:
        opaque_ref(handover[key],f'handover.{key}')
    accepted=instant(handover['accepted_at'],'handover.accepted_at')
    review_by=instant(handover['review_by'],'handover.review_by')
    if accepted>as_of or review_by<=accepted:
        raise ValueError('Operational handover chronology invalid')

    owners=record['decision_owners']
    if not isinstance(owners,dict) or set(owners)!=DECISION_KEYS:
        raise ValueError('All accountable operating decision owners are required')
    for decision,item in owners.items():
        if not isinstance(item,dict) or set(item)!=DECISION_ITEM_KEYS:
            raise ValueError(f'{decision}: decision-owner evidence shape invalid')
        opaque_ref(item['owner_ref'],f'{decision}.owner_ref')
        opaque_ref(item['evidence_ref'],f'{decision}.evidence_ref')

    credential=record['credential_review']
    if not isinstance(credential,dict) or set(credential)!=CREDENTIAL_KEYS:
        raise ValueError('Privileged credential review shape invalid')
    for key in ('review_ref','privileged_paths_ref','custody_ref','break_glass_test_ref'):
        opaque_ref(credential[key],f'credential_review.{key}')
    cred_observed=instant(credential['observed_at'],'credential_review.observed_at')
    cred_valid=instant(credential['valid_until'],'credential_review.valid_until')
    if cred_observed>as_of or cred_valid<=cred_observed:
        raise ValueError('Privileged credential review chronology invalid')
    if credential['stale_grants']!='NONE_UNRESOLVED':
        raise ValueError('Current operational readiness cannot carry unresolved stale privileged grants')

    monitoring=record['monitoring']
    if not isinstance(monitoring,dict) or set(monitoring)!=MONITORING_KEYS:
        raise ValueError('Monitoring/readiness evidence shape invalid')
    for key in ('monitoring_ref','alerting_ref','evidence_loss_ref'):
        opaque_ref(monitoring[key],f'monitoring.{key}')
    monitor_observed=instant(monitoring['observed_at'],'monitoring.observed_at')
    monitor_valid=instant(monitoring['valid_until'],'monitoring.valid_until')
    if monitor_observed>as_of or monitor_valid<=monitor_observed:
        raise ValueError('Monitoring evidence chronology invalid')

    exercise=record['incident_exercise']
    if not isinstance(exercise,dict) or set(exercise)!=EXERCISE_KEYS:
        raise ValueError('Scoped incident exercise shape invalid')
    for key in (
        'exercise_ref','test_set','incident_authority_ref','containment_scope_ref',
        'containment_evidence_ref','release_decision_ref','evidence_custody_ref',
        'coordination_ref','recovery_acceptance_ref','emergency_change_reconciliation_ref'
    ):
        opaque_ref(exercise[key],f'incident_exercise.{key}')
    started=instant(exercise['started_at'],'incident_exercise.started_at')
    contained=instant(exercise['contained_at'],'incident_exercise.contained_at')
    released=instant(exercise['released_at'],'incident_exercise.released_at')
    reconciled=instant(exercise['reconciled_at'],'incident_exercise.reconciled_at')
    exercise_valid=instant(exercise['evidence_valid_until'],'incident_exercise.evidence_valid_until')
    if not (started<=contained<=released<=reconciled<=as_of):
        raise ValueError('Incident exercise chronology invalid')
    if exercise_valid<=reconciled:
        raise ValueError('Incident exercise evidence validity must follow reconciliation')
    if exercise['unrelated_service_impact']!='WITHIN_APPROVED_SCOPE':
        raise ValueError('Incident exercise must demonstrate scoped rather than broad unrelated impact')
    if exercise['outcome']!='PASSED_SCOPED_EXERCISE':
        raise ValueError('Incident exercise outcome is not accepted for readiness evidence')

    obligations=record['residual_obligations']
    if not isinstance(obligations,list) or len(obligations)>1024:
        raise ValueError('Residual obligations must be a bounded list')
    obligation_ids=set()
    open_obligations=[]
    obligation_review_dates=[]
    for item in obligations:
        if not isinstance(item,dict) or set(item)!=OBLIGATION_KEYS:
            raise ValueError('Residual obligation has unexpected or missing fields')
        obligation_id=identifier(item['obligation_id'],'obligation_id')
        if obligation_id in obligation_ids:
            raise ValueError('Duplicate residual obligation ID')
        obligation_ids.add(obligation_id)
        if item['status'] not in OBLIGATION_STATES:
            raise ValueError('Unknown residual obligation state')
        opaque_ref(item['owner_ref'],'residual_obligation.owner_ref')
        opaque_ref(item['treatment_ref'],'residual_obligation.treatment_ref')
        review=instant(item['review_by'],'residual_obligation.review_by')
        obligation_review_dates.append(review)
        if item['status']=='OPEN':
            if item['decision_ref'] is not None:
                raise ValueError('OPEN residual obligation cannot carry an acceptance decision')
            open_obligations.append(obligation_id)
        else:
            opaque_ref(item['decision_ref'],'residual_obligation.decision_ref')

    refs=unique_strings(record['source_refs'],'source_refs')
    for ref in refs:
        repository_ref(ref,root)

    review_due=(as_of>=review_by or as_of>=cred_valid or as_of>=monitor_valid
                or any(as_of>=value for value in obligation_review_dates))
    exercise_due=as_of>=exercise_valid

    if record['state']=='CURRENT_ACCEPTED':
        if review_due or exercise_due:
            raise ValueError('CURRENT_ACCEPTED record has expired review or exercise evidence')
        if open_obligations:
            raise ValueError('CURRENT_ACCEPTED record cannot contain OPEN residual obligations')
    elif record['state']=='REVIEW_DUE':
        if not review_due:
            raise ValueError('REVIEW_DUE requires expired handover, credential, monitoring or obligation review evidence')
    elif record['state']=='EXERCISE_DUE':
        if review_due or not exercise_due:
            raise ValueError('EXERCISE_DUE requires current operating reviews and expired incident-exercise evidence')
    elif record['state']=='GAPS_OPEN':
        if review_due or exercise_due:
            raise ValueError('GAPS_OPEN is reserved for current evidence with unresolved obligations')
        if not open_obligations:
            raise ValueError('GAPS_OPEN requires at least one OPEN residual obligation')
    elif record['state']=='UNCERTAIN':
        pass

    return {
        'assurance_id':record['assurance_id'],
        'generation':record['generation'],
        'state':record['state'],
        'request_id':record['request_id'],
        'wsd_engineering_ref':record['wsd_engineering_ref'],
        'scope':dict(scope),
        'handover_acceptance_ref':handover['acceptance_ref'],
        'review_by':review_by.isoformat(),
        'incident_exercise_ref':exercise['exercise_ref'],
        'incident_exercise_valid_until':exercise_valid.isoformat(),
        'open_obligation_ids':sorted(open_obligations),
        'unresolved':record['state']=='UNCERTAIN',
    }


def validate(index,*,as_of=None,root=ROOT):
    if as_of is None:
        as_of=datetime.now(timezone.utc)
    if not isinstance(as_of,datetime) or as_of.tzinfo is None:
        raise ValueError('Timezone-aware as_of required')
    as_of=as_of.astimezone(timezone.utc)
    if set(index)!=INDEX_KEYS:
        raise ValueError('Unexpected operational handover assurance-index fields')
    if index['format']!=FORMAT or index['status']!=STATUS:
        raise ValueError('Unsupported operational handover assurance format or authority boundary')
    rev=index['reviewed_source_revision']
    if not isinstance(rev,str) or not re.fullmatch(r'[0-9a-f]{40}',rev):
        raise ValueError('Reviewed source revision must be an exact Git SHA')
    records=index['records']
    if not isinstance(records,list) or len(records)>1024:
        raise ValueError('Operational handover assurance records must be a bounded list')
    ids=set()
    request_ids=set()
    out=[]
    for raw in records:
        item=validate_record(raw,as_of=as_of,root=root)
        if item['assurance_id'] in ids:
            raise ValueError('Duplicate operational handover assurance ID')
        if item['request_id'] in request_ids:
            raise ValueError('Duplicate active operational handover assurance for one request')
        ids.add(item['assurance_id'])
        request_ids.add(item['request_id'])
        out.append(item)
    return {
        'records':out,
        'record_count':len(out),
        'current_accepted_count':sum(x['state']=='CURRENT_ACCEPTED' for x in out),
        'review_due_count':sum(x['state']=='REVIEW_DUE' for x in out),
        'exercise_due_count':sum(x['state']=='EXERCISE_DUE' for x in out),
        'gaps_open_count':sum(x['state']=='GAPS_OPEN' for x in out),
        'unresolved_count':sum(x['unresolved'] for x in out),
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
            'status':'PASSED_EXPORTED_OPERATIONAL_HANDOVER_ASSURANCE',
            'as_of':as_of.isoformat(),
            **{k:v for k,v in summary.items() if k!='records'},
            'may_change_privileged_access':False,
            'may_start_containment':False,
            'may_release_containment':False,
            'may_execute_recovery':False,
            'may_reconcile_emergency_change':False,
            'may_apply':False,
            'may_activate':False,
            'limits':[
                'Operational handover is acceptance of a specific service envelope, not receipt of generic documentation.',
                'Incident containment remains external authority and must take precedence over routine reconciliation until explicit attributable release.',
                'A synthetic or historical exercise does not establish current production readiness outside its accepted scope and validity interval.',
                'The repository validates exported evidence only and never changes access, infrastructure, containment or production state.'
            ]
        },indent=2))
        return 0
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({
            'status':'FAILED_EXPORTED_OPERATIONAL_HANDOVER_ASSURANCE',
            'reason':str(exc),
            'may_change_privileged_access':False,
            'may_start_containment':False,
            'may_release_containment':False,
            'may_execute_recovery':False,
            'may_reconcile_emergency_change':False,
            'may_apply':False,
            'may_activate':False
        },indent=2))
        return 2


if __name__=='__main__':
    raise SystemExit(main())
