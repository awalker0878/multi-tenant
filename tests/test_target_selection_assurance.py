"""Actual target-selection assurance tests; no target contact or native execution."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
import json, subprocess, sys, unittest
from pathlib import Path
from scripts import check_target_selection_assurance as assurance
from scripts import check_target_selection_readiness as readiness

ROOT=Path(__file__).resolve().parents[1]
AS_OF=datetime(2026,9,19,15,30,tzinfo=timezone.utc)
INTENT=ROOT/'examples/target_selection_readiness_intent.json.example'

def accepted_gap():
    return {'gap_id':'TARGET-GAP-ACCEPTED-01','status':'ACCEPTED','owner_ref':'controlled-owner:platform',
            'treatment_ref':'controlled-treatment:target-selection',
            'decision_ref':'controlled-decision:target-gap-accepted',
            'review_by':'2026-12-31T23:59:59Z'}

def open_gap():
    return {'gap_id':'TARGET-GAP-OPEN-01','status':'OPEN','owner_ref':'controlled-owner:platform',
            'treatment_ref':'controlled-treatment:target-selection-open',
            'decision_ref':None,'review_by':'2026-12-31T23:59:59Z'}

def record(state='CURRENT_SELECTED',platform='NUTANIX'):
    return {
      'assurance_id':'TARGET-ASSURANCE-FIXTURE-01','generation':1,'state':state,
      'selection_id':'target-selection-fixture-01',
      'scope':{
        'site_ref':'controlled-site:fixture','cell_ref':'controlled-cell:fixture',
        'campaign_scope_ref':'controlled-campaign-scope:fixture',
        'change_authority_ref':'controlled-authority:change',
        'target_contact_authority_ref':'controlled-authority:target-contact',
        'target_contact_valid_until':'2026-12-31T23:59:59Z',
        'stop_authority_ref':'controlled-authority:stop',
        'owner_ref':'controlled-owner:platform',
        'selected_at':'2026-09-19T13:00:00Z',
        'review_by':'2026-12-31T23:59:59Z'
      },
      'implementation_tuple':{
        'platform_family':platform,
        'product_tuple_id':'fixture-product-tuple',
        'hardware_inventory_ref':'controlled-target:hardware',
        'product_api_provider_ref':'controlled-target:product-api-provider',
        'feature_entitlement_ref':'controlled-target:feature-entitlement',
        'version_source_provenance_ref':'controlled-target:version-provenance',
        'security_edge_realization_ref':'controlled-target:security-edge',
        'management_oob_ref':'controlled-target:management-oob',
        'network_backend_ref':'controlled-target:network-backend',
        'storage_backend_ref':'controlled-target:storage-backend'
      },
      'campaign':{
        'qualification_campaign_ref':'controlled-campaign:qualification',
        'native_api_scope_ref':'controlled-campaign:native-api-scope',
        'observer_scope_ref':'controlled-campaign:observer-scope',
        'writer_scope_ref':'controlled-campaign:writer-scope',
        'credential_custody_ref':'controlled-campaign:credential-custody',
        'evidence_workspace_ref':'controlled-campaign:evidence-workspace',
        'data_restriction_ref':'controlled-campaign:no-production-data',
        'permitted_operations_ref':'controlled-campaign:permitted-operations',
        'prohibited_operations_ref':'controlled-campaign:prohibited-operations',
        'cleanup_ref':'controlled-campaign:cleanup',
        'contact_window_ref':'controlled-campaign:contact-window',
        'production_authority_status':'NOT_ISSUED'
      },
      'residual_gaps':[accepted_gap()],
      'source_refs':[
        'docs/implementation/delivery-guide/1-implementation-workplan-and-required-inputs.md',
        'docs/engineering/platform-realizations/7-implementation-tuple-and-decision-package.md',
        'docs/engineering/actual-target-selection-assurance.md'
      ]
    }

def index(*records):
    value=assurance.load(); value['records']=list(records); return value

def intent(platform='NUTANIX'):
    value=readiness.load(INTENT)
    value.update({
      'selection_id':'target-selection-fixture-01',
      'site_ref':'controlled-site:fixture',
      'cell_ref':'controlled-cell:fixture',
      'campaign_scope_ref':'controlled-campaign-scope:fixture',
      'platform_family':platform,
      'product_tuple_id':'fixture-product-tuple'
    })
    return value

class TargetSelectionAssuranceTests(unittest.TestCase):
    def test_empty_index_valid(self):
        self.assertEqual(assurance.validate(assurance.load(),AS_OF)['record_count'],0)

    def test_current_selection_valid(self):
        self.assertEqual(assurance.validate(index(record()),AS_OF)['current_selected_count'],1)

    def test_all_platform_families_can_be_recorded(self):
        for platform in sorted(assurance.PLATFORMS):
            with self.subTest(platform=platform):
                self.assertEqual(assurance.validate(index(record(platform=platform)),AS_OF)['current_selected_count'],1)

    def test_production_authority_forbidden(self):
        r=record(); r['campaign']['production_authority_status']='APPROVED'
        with self.assertRaises(ValueError):
            assurance.validate(index(r),AS_OF)

    def test_contact_authority_expiry_requires_due_state(self):
        r=record('CONTACT_AUTHORITY_DUE')
        r['scope']['target_contact_valid_until']='2026-09-19T15:29:59Z'
        self.assertEqual(assurance.validate(index(r),AS_OF)['contact_authority_due_count'],1)

    def test_current_selection_rejects_expired_contact_authority(self):
        r=record(); r['scope']['target_contact_valid_until']='2026-09-19T15:29:59Z'
        with self.assertRaises(ValueError):
            assurance.validate(index(r),AS_OF)

    def test_review_due_requires_expired_review(self):
        r=record('REVIEW_DUE'); r['scope']['review_by']='2026-09-19T15:29:59Z'
        self.assertEqual(assurance.validate(index(r),AS_OF)['review_due_count'],1)

    def test_current_selection_rejects_open_gap(self):
        r=record(); r['residual_gaps'].append(open_gap())
        with self.assertRaises(ValueError):
            assurance.validate(index(r),AS_OF)

    def test_gaps_open_requires_open_gap(self):
        r=record('GAPS_OPEN'); r['residual_gaps'].append(open_gap())
        self.assertEqual(assurance.validate(index(r),AS_OF)['gaps_open_count'],1)

    def test_duplicate_selection_id_rejected(self):
        one=record(); two=deepcopy(one); two['assurance_id']='TARGET-ASSURANCE-FIXTURE-02'
        with self.assertRaises(ValueError):
            assurance.validate(index(one,two),AS_OF)

    def test_cli_grants_no_target_contact_authority(self):
        run=subprocess.run([
            sys.executable,str(ROOT/'scripts/check_target_selection_assurance.py'),
            '--as-of','2026-09-19T15:30:00Z'
        ],capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        out=json.loads(run.stdout)
        self.assertEqual(out['record_count'],0)
        for key in ('may_select_target','may_contact_target','may_retrieve_credentials','may_run_native_tests','may_apply','may_activate'):
            self.assertIs(out[key],False)

class TargetSelectionReadinessTests(unittest.TestCase):
    def test_empty_holds(self):
        self.assertEqual(readiness.evaluate(readiness.load(INTENT),assurance.load(),AS_OF)['status'],readiness.HOLD_NONE)

    def test_current_selection_ready_only(self):
        result=readiness.evaluate(intent(),index(record()),AS_OF)
        self.assertEqual(result['status'],readiness.READY)
        self.assertFalse(result['may_contact_target'])

    def test_contact_due_holds(self):
        r=record('CONTACT_AUTHORITY_DUE')
        r['scope']['target_contact_valid_until']='2026-09-19T15:29:59Z'
        self.assertEqual(readiness.evaluate(intent(),index(r),AS_OF)['status'],readiness.HOLD_CONTACT)

    def test_platform_mismatch_holds(self):
        self.assertEqual(readiness.evaluate(intent('OPENSTACK'),index(record()),AS_OF)['status'],readiness.HOLD_SCOPE)

    def test_tuple_mismatch_holds(self):
        value=intent(); value['product_tuple_id']='other-tuple'
        self.assertEqual(readiness.evaluate(value,index(record()),AS_OF)['status'],readiness.HOLD_SCOPE)

    def test_caller_cannot_carry_production_authority(self):
        value=intent(); value['production_authority']='APPROVED'
        with self.assertRaises(ValueError):
            readiness.evaluate(value,index(record()),AS_OF)

    def test_cli_empty_hold(self):
        run=subprocess.run([
            sys.executable,str(ROOT/'scripts/check_target_selection_readiness.py'),str(INTENT),
            '--as-of','2026-09-19T15:30:00Z','--expected-status',readiness.HOLD_NONE
        ],capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        self.assertEqual(json.loads(run.stdout)['status'],readiness.HOLD_NONE)

if __name__=='__main__':
    unittest.main()
