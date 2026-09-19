"""Identity/PKI/KMS assurance tests; no trust-service mutation."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
import json, subprocess, sys, unittest
from pathlib import Path
from scripts import check_identity_crypto_assurance as assurance
from scripts import check_identity_crypto_readiness as readiness

ROOT=Path(__file__).resolve().parents[1]
AS_OF=datetime(2026,9,18,23,0,tzinfo=timezone.utc)
INTENT=ROOT/'examples/identity_crypto_readiness_intent.json.example'

def accepted_gap():
    return {'gap_id':'TRUST-GAP-ACCEPTED-01','status':'ACCEPTED','owner_ref':'controlled-owner:security',
            'treatment_ref':'controlled-treatment:trust','decision_ref':'controlled-decision:trust-gap-accepted',
            'review_by':'2026-12-31T23:59:59Z'}

def open_gap():
    return {'gap_id':'TRUST-GAP-OPEN-01','status':'OPEN','owner_ref':'controlled-owner:security',
            'treatment_ref':'controlled-treatment:trust-open','decision_ref':None,
            'review_by':'2026-12-31T23:59:59Z'}

def record(state='CURRENT_QUALIFIED'):
    return {
      'assurance_id':'TRUST-ASSURANCE-FIXTURE-01','generation':1,'state':state,'trust_id':'trust-fixture-01',
      'scope':{'site_ref':'controlled-site:fixture','service_class_ref':'controlled-service-class:fixture',
               'trust_profile_ref':'controlled-trust-profile:fixture','key_profile_ref':'controlled-key-profile:fixture',
               'owner_ref':'controlled-owner:trust-service','accepted_at':'2026-09-18T20:00:00Z',
               'review_by':'2026-12-31T23:59:59Z'},
      'identity':{
        'human_scope_ref':'controlled-identity:human','workload_scope_ref':'controlled-identity:workload',
        'automation_scope_ref':'controlled-identity:automation','provider_authority_separation_ref':'controlled-identity:no-provider-inheritance',
        'privileged_path_ref':'controlled-pam:path','strong_auth_ref':'controlled-pam:strong-auth',
        'time_bound_delegation_ref':'controlled-pam:time-bound','emergency_access_ref':'controlled-pam:emergency',
        'supplier_access_ref':'controlled-pam:supplier','revocation_propagation_ref':'controlled-identity:revocation',
        'cached_token_test_ref':'controlled-identity:cached-token-test','observed_at':'2026-09-18T21:00:00Z',
        'valid_until':'2026-12-31T23:59:59Z'},
      'certificates':{
        'issuer_ref':'controlled-pki:issuer','relying_party_trust_ref':'controlled-pki:trust',
        'endpoint_identity_validation_ref':'controlled-pki:endpoint-validation','issuance_scope_ref':'controlled-pki:issuance-scope',
        'renewal_ref':'controlled-pki:renewal','revocation_ref':'controlled-pki:revocation',
        'tls_profile_ref':'controlled-pki:tls-profile','crypto_module_evidence_ref':'controlled-pki:module-evidence',
        'observed_at':'2026-09-18T21:05:00Z','valid_until':'2026-12-31T23:59:59Z'},
      'keys':{
        'use_authority_ref':'controlled-key-authority:use','administration_authority_ref':'controlled-key-authority:admin',
        'recovery_authority_ref':'controlled-key-authority:recovery','destruction_authority_ref':'controlled-key-authority:destroy',
        'retained_data_dependency_ref':'controlled-data-dependency:retained-copies',
        'destruction_disposition_ref':'controlled-data-disposition:key-destroy',
        'custody_ref':'controlled-key:custody','key_version_inventory_ref':'controlled-key:inventory',
        'rotation_ref':'controlled-key:rotation','observed_at':'2026-09-18T21:10:00Z','valid_until':'2026-12-31T23:59:59Z'},
      'outage_recovery':{
        'kms_outage_test_ref':'controlled-test:kms-outage','no_plaintext_fallback_ref':'controlled-test:no-plaintext-fallback',
        'trust_service_outage_ref':'controlled-test:trust-outage','independent_recovery_path_ref':'controlled-recovery:independent-trust',
        'emergency_identity_ref':'controlled-recovery:emergency-identity','recovery_audit_ref':'controlled-recovery:audit',
        'observed_at':'2026-09-18T21:15:00Z','valid_until':'2026-12-31T23:59:59Z'},
      'agility':{
        'cryptographic_inventory_ref':'controlled-crypto:inventory','certificate_rotation_plan_ref':'controlled-crypto:cert-rotation',
        'algorithm_transition_plan_ref':'controlled-crypto:algorithm-transition','exception_register_ref':'controlled-crypto:exceptions',
        'observed_at':'2026-09-18T21:20:00Z','valid_until':'2026-12-31T23:59:59Z'},
      'residual_gaps':[accepted_gap()],
      'source_refs':['docs/architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md',
                     'docs/engineering/identity-crypto-trust-assurance.md']
    }

def index(*records):
    value=assurance.load(); value['records']=list(records); return value

def intent():
    value=readiness.load(INTENT)
    value.update({'trust_id':'trust-fixture-01','site_ref':'controlled-site:fixture',
                  'service_class_ref':'controlled-service-class:fixture',
                  'trust_profile_ref':'controlled-trust-profile:fixture',
                  'key_profile_ref':'controlled-key-profile:fixture'})
    return value

class IdentityCryptoAssuranceTests(unittest.TestCase):
    def test_empty_index_valid(self): self.assertEqual(assurance.validate(assurance.load(),AS_OF)['record_count'],0)
    def test_current_record_valid(self): self.assertEqual(assurance.validate(index(record()),AS_OF)['current_qualified_count'],1)
    def test_key_authorities_must_be_separate(self):
        r=record();r['keys']['destruction_authority_ref']=r['keys']['administration_authority_ref']
        with self.assertRaises(ValueError): assurance.validate(index(r),AS_OF)
    def test_revocation_evidence_required(self):
        r=record();r['identity']['cached_token_test_ref']=''
        with self.assertRaises(ValueError): assurance.validate(index(r),AS_OF)
    def test_retained_data_dependency_required_before_key_destruction(self):
        r=record();r['keys']['retained_data_dependency_ref']=''
        with self.assertRaises(ValueError): assurance.validate(index(r),AS_OF)
    def test_plaintext_fallback_evidence_required(self):
        r=record();r['outage_recovery']['no_plaintext_fallback_ref']=''
        with self.assertRaises(ValueError): assurance.validate(index(r),AS_OF)
    def test_trust_evidence_due(self):
        r=record('TRUST_EVIDENCE_DUE');r['certificates']['valid_until']='2026-09-18T22:59:59Z'
        self.assertEqual(assurance.validate(index(r),AS_OF)['trust_evidence_due_count'],1)
    def test_outage_test_due(self):
        r=record('OUTAGE_TEST_DUE');r['outage_recovery']['valid_until']='2026-09-18T22:59:59Z'
        self.assertEqual(assurance.validate(index(r),AS_OF)['outage_test_due_count'],1)
    def test_current_rejects_open_gap(self):
        r=record();r['residual_gaps'].append(open_gap())
        with self.assertRaises(ValueError): assurance.validate(index(r),AS_OF)
    def test_gaps_open(self):
        r=record('GAPS_OPEN');r['residual_gaps'].append(open_gap())
        self.assertEqual(assurance.validate(index(r),AS_OF)['gaps_open_count'],1)
    def test_cli_grants_no_mutation_authority(self):
        run=subprocess.run([sys.executable,str(ROOT/'scripts/check_identity_crypto_assurance.py'),'--as-of','2026-09-18T23:00:00Z'],capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr);out=json.loads(run.stdout)
        for k in ('may_issue_credential','may_revoke_credential','may_enroll_certificate','may_rotate_key','may_destroy_key','may_change_privileged_access','may_execute_recovery','may_apply','may_activate'):
            self.assertIs(out[k],False)

class IdentityCryptoReadinessTests(unittest.TestCase):
    def test_empty_holds(self): self.assertEqual(readiness.evaluate(readiness.load(INTENT),assurance.load(),AS_OF)['status'],readiness.HOLD_NONE)
    def test_current_ready_only(self):
        result=readiness.evaluate(intent(),index(record()),AS_OF);self.assertEqual(result['status'],readiness.READY);self.assertFalse(result['may_rotate_key'])
    def test_trust_due_holds(self):
        r=record('TRUST_EVIDENCE_DUE');r['keys']['valid_until']='2026-09-18T22:59:59Z'
        self.assertEqual(readiness.evaluate(intent(),index(r),AS_OF)['status'],readiness.HOLD_TRUST)
    def test_outage_due_holds(self):
        r=record('OUTAGE_TEST_DUE');r['outage_recovery']['valid_until']='2026-09-18T22:59:59Z'
        self.assertEqual(readiness.evaluate(intent(),index(r),AS_OF)['status'],readiness.HOLD_OUTAGE)
    def test_scope_mismatch_holds(self):
        value=intent();value['key_profile_ref']='controlled-key-profile:other'
        self.assertEqual(readiness.evaluate(value,index(record()),AS_OF)['status'],readiness.HOLD_SCOPE)
    def test_cli_empty_hold(self):
        run=subprocess.run([sys.executable,str(ROOT/'scripts/check_identity_crypto_readiness.py'),str(INTENT),'--as-of','2026-09-18T23:00:00Z','--expected-status',readiness.HOLD_NONE],capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)

if __name__=='__main__': unittest.main()
