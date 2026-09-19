"""Storage data-lifecycle assurance tests; no storage mutation."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
import json, subprocess, sys, unittest
from pathlib import Path
from scripts import check_storage_data_lifecycle_assurance as assurance
from scripts import check_storage_data_lifecycle_readiness as readiness

ROOT=Path(__file__).resolve().parents[1]
AS_OF=datetime(2026,9,19,1,50,tzinfo=timezone.utc)
INTENT=ROOT/'examples/storage_data_lifecycle_readiness_intent.json.example'

def accepted_gap():
    return {'gap_id':'STO-GAP-ACCEPTED-01','status':'ACCEPTED','owner_ref':'controlled-owner:storage',
            'treatment_ref':'controlled-treatment:storage','decision_ref':'controlled-decision:storage-gap-accepted',
            'review_by':'2026-12-31T23:59:59Z'}

def open_gap():
    return {'gap_id':'STO-GAP-OPEN-01','status':'OPEN','owner_ref':'controlled-owner:storage',
            'treatment_ref':'controlled-treatment:storage-open','decision_ref':None,
            'review_by':'2026-12-31T23:59:59Z'}

def record(state='CURRENT_QUALIFIED'):
    return {
      'assurance_id':'STORAGE-ASSURANCE-FIXTURE-01','generation':1,'state':state,'storage_id':'storage-fixture-01',
      'scope':{'site_ref':'controlled-site:fixture','service_class_ref':'controlled-service-class:fixture',
               'platform_profile_ref':'controlled-platform-profile:fixture','storage_profile_ref':'controlled-storage-profile:fixture',
               'protection_assurance_ref':'controlled-backup-assurance:fixture','owner_ref':'controlled-owner:storage',
               'accepted_at':'2026-09-19T00:00:00Z','review_by':'2026-12-31T23:59:59Z'},
      'ownership_lineage':{
        'resource_owner_ref':'controlled-storage:owner','categorization_ref':'controlled-storage:categorization',
        'access_scope_ref':'controlled-storage:access','key_policy_ref':'controlled-storage:key-policy',
        'placement_retention_ref':'controlled-storage:placement-retention','lineage_ref':'controlled-storage:lineage',
        'cross_scope_authorization_ref':'controlled-storage:cross-scope-authority',
        'cross_scope_deny_test_ref':'controlled-test:cross-scope-storage-deny',
        'observed_at':'2026-09-19T00:30:00Z','valid_until':'2026-12-31T23:59:59Z'},
      'service_semantics':{
        'capacity_ref':'controlled-storage:capacity','performance_ref':'controlled-storage:performance',
        'consistency_ref':'controlled-storage:consistency','replication_ref':'controlled-storage:replication',
        'snapshot_clone_ref':'controlled-storage:snapshot-clone','portability_ref':'controlled-storage:portability',
        'contention_test_ref':'controlled-test:storage-contention','accepted_failure_test_ref':'controlled-test:storage-failure',
        'observed_at':'2026-09-19T00:35:00Z','valid_until':'2026-12-31T23:59:59Z'},
      'copy_inventory':{
        'copy_catalogue_ref':'controlled-copy:catalogue','derivative_lineage_ref':'controlled-copy:lineage',
        'retained_copy_ref':'controlled-copy:retained','hold_register_ref':'controlled-copy:holds',
        'key_version_mapping_ref':'controlled-copy:key-versions','copy_authority_ref':'controlled-copy:authority',
        'observed_at':'2026-09-19T00:40:00Z','valid_until':'2026-12-31T23:59:59Z'},
      'release_sanitization':{
        'withdrawal_procedure_ref':'controlled-retirement:withdrawal',
        'copy_hold_reconciliation_test_ref':'controlled-test:copy-hold-reconciliation',
        'sanitization_method_ref':'controlled-sanitization:method',
        'sanitization_verification_test_ref':'controlled-test:sanitization-verification',
        'receipt_schema_ref':'controlled-sanitization:receipt-schema',
        'exception_process_ref':'controlled-sanitization:exceptions',
        'observed_at':'2026-09-19T00:45:00Z','valid_until':'2026-12-31T23:59:59Z'},
      'residual_gaps':[accepted_gap()],
      'source_refs':['docs/architecture/shared-services/4-storage-copies-and-retained-data-ownership.md',
                     'docs/engineering/storage-data-lifecycle-assurance.md']
    }

def index(*records):
    value=assurance.load(); value['records']=list(records); return value

def intent():
    value=readiness.load(INTENT)
    value.update({'storage_id':'storage-fixture-01','site_ref':'controlled-site:fixture',
                  'service_class_ref':'controlled-service-class:fixture',
                  'platform_profile_ref':'controlled-platform-profile:fixture',
                  'storage_profile_ref':'controlled-storage-profile:fixture'})
    return value

class StorageLifecycleAssuranceTests(unittest.TestCase):
    def test_empty_index_valid(self): self.assertEqual(assurance.validate(assurance.load(),AS_OF)['record_count'],0)
    def test_current_record_valid(self): self.assertEqual(assurance.validate(index(record()),AS_OF)['current_qualified_count'],1)
    def test_cross_scope_deny_evidence_required(self):
        r=record();r['ownership_lineage']['cross_scope_deny_test_ref']=''
        with self.assertRaises(ValueError): assurance.validate(index(r),AS_OF)
    def test_contention_and_failure_tests_required(self):
        r=record();r['service_semantics']['contention_test_ref']=''
        with self.assertRaises(ValueError): assurance.validate(index(r),AS_OF)
    def test_copy_hold_key_mapping_required(self):
        r=record();r['copy_inventory']['key_version_mapping_ref']=''
        with self.assertRaises(ValueError): assurance.validate(index(r),AS_OF)
    def test_sanitization_receipt_model_required(self):
        r=record();r['release_sanitization']['receipt_schema_ref']=''
        with self.assertRaises(ValueError): assurance.validate(index(r),AS_OF)
    def test_service_test_due(self):
        r=record('SERVICE_TEST_DUE');r['service_semantics']['valid_until']='2026-09-19T01:49:59Z'
        self.assertEqual(assurance.validate(index(r),AS_OF)['service_test_due_count'],1)
    def test_lifecycle_due(self):
        r=record('LIFECYCLE_DUE');r['copy_inventory']['valid_until']='2026-09-19T01:49:59Z'
        self.assertEqual(assurance.validate(index(r),AS_OF)['lifecycle_due_count'],1)
    def test_current_rejects_open_gap(self):
        r=record();r['residual_gaps'].append(open_gap())
        with self.assertRaises(ValueError): assurance.validate(index(r),AS_OF)
    def test_gaps_open(self):
        r=record('GAPS_OPEN');r['residual_gaps'].append(open_gap())
        self.assertEqual(assurance.validate(index(r),AS_OF)['gaps_open_count'],1)
    def test_duplicate_storage_profile_rejected(self):
        one=record();two=deepcopy(one);two['assurance_id']='STORAGE-ASSURANCE-FIXTURE-02'
        with self.assertRaises(ValueError): assurance.validate(index(one,two),AS_OF)
    def test_cli_grants_no_storage_mutation_authority(self):
        run=subprocess.run([sys.executable,str(ROOT/'scripts/check_storage_data_lifecycle_assurance.py'),'--as-of','2026-09-19T01:50:00Z'],capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr);out=json.loads(run.stdout)
        for k in ('may_provision_storage','may_attach_storage','may_snapshot_or_clone','may_export_data','may_delete_copy','may_sanitize_media','may_release_reuse','may_apply','may_activate'):
            self.assertIs(out[k],False)

class StorageLifecycleReadinessTests(unittest.TestCase):
    def test_empty_holds(self): self.assertEqual(readiness.evaluate(readiness.load(INTENT),assurance.load(),AS_OF)['status'],readiness.HOLD_NONE)
    def test_current_ready_only(self):
        result=readiness.evaluate(intent(),index(record()),AS_OF);self.assertEqual(result['status'],readiness.READY);self.assertFalse(result['may_sanitize_media'])
    def test_service_due_holds(self):
        r=record('SERVICE_TEST_DUE');r['ownership_lineage']['valid_until']='2026-09-19T01:49:59Z'
        self.assertEqual(readiness.evaluate(intent(),index(r),AS_OF)['status'],readiness.HOLD_SERVICE)
    def test_lifecycle_due_holds(self):
        r=record('LIFECYCLE_DUE');r['release_sanitization']['valid_until']='2026-09-19T01:49:59Z'
        self.assertEqual(readiness.evaluate(intent(),index(r),AS_OF)['status'],readiness.HOLD_LIFECYCLE)
    def test_scope_mismatch_holds(self):
        value=intent();value['storage_profile_ref']='controlled-storage-profile:other'
        self.assertEqual(readiness.evaluate(value,index(record()),AS_OF)['status'],readiness.HOLD_SCOPE)
    def test_cli_empty_hold(self):
        run=subprocess.run([sys.executable,str(ROOT/'scripts/check_storage_data_lifecycle_readiness.py'),str(INTENT),'--as-of','2026-09-19T01:50:00Z','--expected-status',readiness.HOLD_NONE],capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)

if __name__=='__main__': unittest.main()
