#!/usr/bin/env python3
"""Evaluate identity/PKI/KMS trust readiness without mutating trust services."""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from scripts import check_identity_crypto_assurance as assurance

FORMAT='portable-hosting-identity-crypto-readiness-intent/1'
STATUS='PLANNING_ONLY_NOT_AUTHORIZED'
READY='IDENTITY_CRYPTO_CURRENT_NO_TRUST_MUTATION_AUTHORIZED'
HOLD_NONE='HOLD_NO_CURRENT_IDENTITY_CRYPTO_ASSURANCE'
HOLD_REVIEW='HOLD_IDENTITY_CRYPTO_REVIEW_DUE'
HOLD_TRUST='HOLD_IDENTITY_CRYPTO_EVIDENCE_DUE'
HOLD_OUTAGE='HOLD_IDENTITY_CRYPTO_OUTAGE_TEST_DUE'
HOLD_GAPS='HOLD_IDENTITY_CRYPTO_GAPS_OPEN'
HOLD_UNCERTAIN='HOLD_IDENTITY_CRYPTO_UNCERTAIN'
HOLD_SCOPE='HOLD_IDENTITY_CRYPTO_SCOPE_MISMATCH'
INTENT_KEYS={
    'format','status','request_id','trust_id','site_ref','service_class_ref',
    'trust_profile_ref','key_profile_ref','production_authority','source_refs'
}


def load(path):
    with Path(path).open('rb') as s:
        raw=s.read(1024*1024+1)
    if len(raw)>1024*1024:
        raise ValueError('Identity/crypto readiness intent exceeds bounded size')
    value=json.loads(raw)
    if not isinstance(value,dict):
        raise ValueError('Identity/crypto readiness intent must be an object')
    return value


def validate_intent(i):
    if set(i)!=INTENT_KEYS or i['format']!=FORMAT or i['status']!=STATUS:
        raise ValueError('Unsupported identity/crypto readiness intent')
    assurance.identifier(i['request_id'],'request_id')
    assurance.identifier(i['trust_id'],'trust_id')
    for k in ('site_ref','service_class_ref','trust_profile_ref','key_profile_ref'):
        assurance.opaque_ref(i[k],k)
    if i['production_authority']!='NOT_ASSESSED':
        raise ValueError('Identity/crypto readiness cannot carry production authority')
    for ref in assurance.unique_strings(i['source_refs'],'source_refs'):
        assurance.repository_ref(ref)


def evaluate(intent,index=None,as_of=None):
    if as_of is None:
        as_of=datetime.now(timezone.utc)
    if as_of.tzinfo is None:
        raise ValueError('Timezone-aware as_of required')
    as_of=as_of.astimezone(timezone.utc)
    validate_intent(intent)
    if index is None:
        index=assurance.load()
    summary=assurance.validate(index,as_of)
    records=[x for x in summary['records'] if x['trust_id']==intent['trust_id']]
    r=records[0] if records else None
    if r is None: result=HOLD_NONE
    elif r['state']=='UNCERTAIN': result=HOLD_UNCERTAIN
    elif r['state']=='REVIEW_DUE': result=HOLD_REVIEW
    elif r['state']=='TRUST_EVIDENCE_DUE': result=HOLD_TRUST
    elif r['state']=='OUTAGE_TEST_DUE': result=HOLD_OUTAGE
    elif r['state']=='GAPS_OPEN': result=HOLD_GAPS
    elif any([
        r['site_ref']!=intent['site_ref'],
        r['service_class_ref']!=intent['service_class_ref'],
        r['trust_profile_ref']!=intent['trust_profile_ref'],
        r['key_profile_ref']!=intent['key_profile_ref'],
    ]): result=HOLD_SCOPE
    else: result=READY
    return {
        'kind':'IDENTITY_CRYPTO_READINESS_PREFLIGHT','status':result,
        'request_id':intent['request_id'],'trust_id':intent['trust_id'],
        'assurance_id':r['assurance_id'] if r else None,
        'open_gap_ids':r['open_gap_ids'] if r else [],
        'may_issue_credential':False,'may_revoke_credential':False,
        'may_enroll_certificate':False,'may_rotate_key':False,
        'may_destroy_key':False,'may_change_privileged_access':False,
        'may_execute_recovery':False,'may_apply':False,'may_activate':False,
        'next_owner_action':{
            READY:'Use this only as evidence that the exact identity/certificate/key scope is current; trust-service mutations remain under their accountable owners.',
            HOLD_NONE:'Publish current identity-scope, certificate-lifecycle, key-authority, outage/recovery and crypto-agility evidence for the exact trust scope.',
            HOLD_REVIEW:'Refresh the trust-scope or residual-gap review.',
            HOLD_TRUST:'Refresh identity, certificate, key-custody/rotation or crypto-agility evidence.',
            HOLD_OUTAGE:'Repeat KMS/trust outage and independent-recovery tests, including proof of no plaintext fallback.',
            HOLD_GAPS:'Resolve or formally disposition every OPEN identity/crypto gap.',
            HOLD_UNCERTAIN:'Reconcile the authoritative identity, certificate, key and recovery state.',
            HOLD_SCOPE:'Use evidence for the exact site/service/trust/key profile scope.'
        }[result],
        'limits':[
            'A ready result is not credential, certificate, key or privileged-access authority.',
            'This preflight performs no trust-service mutation or recovery action.',
            'CI never applies infrastructure or activates production.'
        ]
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('intent',type=Path)
    p.add_argument('--as-of')
    p.add_argument('--expected-status',choices=(READY,HOLD_NONE,HOLD_REVIEW,HOLD_TRUST,HOLD_OUTAGE,HOLD_GAPS,HOLD_UNCERTAIN,HOLD_SCOPE))
    a=p.parse_args()
    try:
        as_of=assurance.instant(a.as_of,'as_of') if a.as_of else datetime.now(timezone.utc)
        result=evaluate(load(a.intent),as_of=as_of)
        print(json.dumps(result,indent=2))
        if a.expected_status is not None:
            return 0 if result['status']==a.expected_status else 2
        return 0 if result['status']==READY else 2
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({
            'kind':'IDENTITY_CRYPTO_READINESS_PREFLIGHT',
            'status':'INVALID_IDENTITY_CRYPTO_READINESS_INTENT','reason':str(exc),
            'may_issue_credential':False,'may_revoke_credential':False,
            'may_enroll_certificate':False,'may_rotate_key':False,
            'may_destroy_key':False,'may_change_privileged_access':False,
            'may_execute_recovery':False,'may_apply':False,'may_activate':False
        },indent=2)); return 2


if __name__=='__main__':
    raise SystemExit(main())
