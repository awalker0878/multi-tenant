"""Control inheritance and external-dependency assurance tests; no authorization mutation."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import unittest
from scripts import check_control_inheritance_assurance as assurance
from scripts import check_control_inheritance_readiness as readiness

ROOT=Path(__file__).resolve().parents[1]
AS_OF=datetime(2026,9,18,20,0,tzinfo=timezone.utc)
INTENT=ROOT/'examples/control_inheritance_readiness_intent.json.example'

def scope():
    return {'site_ref':'controlled-site:fixture','service_class_ref':'controlled-service-class:fixture',
            'platform_profile_ref':'controlled-platform-profile:fixture',
            'control_catalogue_ref':'controlled-catalogue:fixture',
            'control_selection_ref':'controlled-selection:fixture'}

def control(control_id='AUTH-001',disposition='SHARED'):
    return {'control_id':control_id,'parameter_decision_ref':f'controlled-parameter:{control_id.lower()}',
            'disposition':disposition,'implementation_ref':f'controlled-implementation:{control_id.lower()}',
            'evidence_ref':f'controlled-evidence:{control_id.lower()}',
            'evidence_scope_ref':f'controlled-scope:{control_id.lower()}',
            'owner_refs':['controlled-owner:security','controlled-owner:service'],
            'inherited_service_ref':'controlled-service:inherited-fixture' if disposition=='INHERITED' else None,
            'observed_at':'2026-09-18T18:00:00Z','evidence_valid_until':'2026-12-31T23:59:59Z'}

def external_interfaces():
    return [{'interface':name,'owner_ref':f'controlled-owner:{name.lower()}',
             'evidence_ref':f'controlled-evidence:{name.lower()}',
             'applicability_ref':f'controlled-applicability:{name.lower()}',
             'observed_at':'2026-09-18T18:00:00Z','evidence_valid_until':'2026-12-31T23:59:59Z'}
            for name in sorted(assurance.INTERFACES)]

def accepted_gap():
    return {'gap_id':'GAP-FIXTURE-01','related_control_ids':['STD-002'],'status':'ACCEPTED',
            'owner_role':'Fixture security authority','treatment_ref':'controlled-treatment:fixture',
            'decision_ref':'controlled-decision:accepted-fixture'}

def open_gap():
    return {'gap_id':'GAP-FIXTURE-OPEN','related_control_ids':['STD-002'],'status':'OPEN',
            'owner_role':'Fixture security authority','treatment_ref':'controlled-treatment:open-fixture',
            'decision_ref':None}

def record(state='CURRENT_REVIEWED'):
    return {'assurance_id':'CONTROL-ASSURANCE-FIXTURE-01','generation':1,'state':state,
            'request_id':'EXAMPLE-SITE-CAPACITY-01',
            'wsd_engineering_ref':'docs/current/internal-hosting-solution.md','scope':scope(),
            'review':{'allocation_decision_ref':'controlled-decision:allocation-fixture',
                      'accepted_at':'2026-09-18T17:00:00Z','review_by':'2026-12-31T23:59:59Z',
                      'accountable_role':'Fixture security authority'},
            'controls':[control('AUTH-001','SHARED'),control('STD-002','INHERITED')],
            'external_interfaces':external_interfaces(),'residual_gaps':[accepted_gap()],
            'source_refs':['docs/assurance/site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md',
                           'docs/engineering/control-inheritance-and-external-dependency-assurance.md']}

def index(*records):
    value=assurance.load(); value['records']=list(records); return value

def intent():
    value=readiness.load(INTENT); value['required_scope']=scope()
    value['required_control_ids']=['AUTH-001','STD-002']; return value

class ControlInheritanceRecordTests(unittest.TestCase):
    def test_current_index_is_valid_empty(self):
        self.assertEqual(assurance.validate(assurance.load(),as_of=AS_OF)['record_count'],0)
    def test_current_reviewed_record_is_valid(self):
        self.assertEqual(assurance.validate(index(record()),as_of=AS_OF)['current_reviewed_count'],1)
    def test_inherited_control_requires_inherited_service_reference(self):
        r=record(); r['controls'][1]['inherited_service_ref']=None
        with self.assertRaises(ValueError): assurance.validate(index(r),as_of=AS_OF)
    def test_non_inherited_control_cannot_claim_inherited_service(self):
        r=record(); r['controls'][0]['inherited_service_ref']='controlled-service:not-allowed'
        with self.assertRaises(ValueError): assurance.validate(index(r),as_of=AS_OF)
    def test_all_six_external_interfaces_are_required(self):
        r=record(); r['external_interfaces'].pop()
        with self.assertRaises(ValueError): assurance.validate(index(r),as_of=AS_OF)
    def test_duplicate_external_interface_rejected(self):
        r=record(); r['external_interfaces'][-1]=deepcopy(r['external_interfaces'][0])
        with self.assertRaises(ValueError): assurance.validate(index(r),as_of=AS_OF)
    def test_current_reviewed_rejects_expired_control_evidence(self):
        r=record(); r['controls'][0]['evidence_valid_until']='2026-09-18T19:59:59Z'
        with self.assertRaises(ValueError): assurance.validate(index(r),as_of=AS_OF)
    def test_review_due_requires_expired_review_or_evidence(self):
        r=record('REVIEW_DUE')
        with self.assertRaises(ValueError): assurance.validate(index(r),as_of=AS_OF)
        r['review']['review_by']='2026-09-18T19:59:59Z'
        self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['review_due_count'],1)
    def test_current_reviewed_cannot_have_open_gap(self):
        r=record(); r['residual_gaps'].append(open_gap())
        with self.assertRaises(ValueError): assurance.validate(index(r),as_of=AS_OF)
    def test_gaps_open_requires_open_gap_and_current_evidence(self):
        r=record('GAPS_OPEN'); r['residual_gaps'].append(open_gap())
        self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['gaps_open_count'],1)
    def test_accepted_gap_requires_decision_reference(self):
        r=record(); r['residual_gaps'][0]['decision_ref']=None
        with self.assertRaises(ValueError): assurance.validate(index(r),as_of=AS_OF)
    def test_open_gap_cannot_carry_acceptance_decision(self):
        r=record('GAPS_OPEN'); gap=open_gap(); gap['decision_ref']='controlled-decision:premature'; r['residual_gaps'].append(gap)
        with self.assertRaises(ValueError): assurance.validate(index(r),as_of=AS_OF)
    def test_gap_must_reference_allocated_control(self):
        r=record(); r['residual_gaps'][0]['related_control_ids']=['MISSING-001']
        with self.assertRaises(ValueError): assurance.validate(index(r),as_of=AS_OF)
    def test_duplicate_control_id_rejected(self):
        r=record(); r['controls'].append(deepcopy(r['controls'][0]))
        with self.assertRaises(ValueError): assurance.validate(index(r),as_of=AS_OF)
    def test_duplicate_request_assurance_rejected(self):
        one=record(); two=deepcopy(one); two['assurance_id']='CONTROL-ASSURANCE-FIXTURE-02'
        with self.assertRaises(ValueError): assurance.validate(index(one,two),as_of=AS_OF)
    def test_cli_empty_index_grants_no_control_or_authorization_authority(self):
        run=subprocess.run([sys.executable,str(ROOT/'scripts/check_control_inheritance_assurance.py'),
                            '--as-of','2026-09-18T20:00:00Z'],capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr); out=json.loads(run.stdout)
        self.assertEqual(out['record_count'],0)
        for key in ('may_select_controls','may_accept_inheritance','may_close_residual_gap','may_issue_authorization','may_apply','may_activate'):
            self.assertIs(out[key],False)

class ControlInheritanceReadinessTests(unittest.TestCase):
    def test_current_example_holds_without_control_allocation(self):
        self.assertEqual(readiness.evaluate(readiness.load(INTENT),index=assurance.load(),as_of=AS_OF)['status'],readiness.HOLD_NONE)
    def test_current_reviewed_record_satisfies_only_readiness_prerequisite(self):
        result=readiness.evaluate(intent(),index=index(record()),as_of=AS_OF)
        self.assertEqual(result['status'],readiness.READY)
        for key in ('may_select_controls','may_accept_inheritance','may_close_residual_gap','may_issue_authorization','may_apply','may_activate'):
            self.assertIs(result[key],False)
    def test_review_due_holds(self):
        r=record('REVIEW_DUE'); r['review']['review_by']='2026-09-18T19:59:59Z'
        self.assertEqual(readiness.evaluate(intent(),index=index(r),as_of=AS_OF)['status'],readiness.HOLD_REVIEW)
    def test_open_residual_gap_holds(self):
        r=record('GAPS_OPEN'); r['residual_gaps'].append(open_gap())
        self.assertEqual(readiness.evaluate(intent(),index=index(r),as_of=AS_OF)['status'],readiness.HOLD_GAPS)
    def test_uncertain_allocation_holds(self):
        self.assertEqual(readiness.evaluate(intent(),index=index(record('UNCERTAIN')),as_of=AS_OF)['status'],readiness.HOLD_UNCERTAIN)
    def test_scope_mismatch_holds(self):
        value=intent(); value['required_scope']['site_ref']='controlled-site:other'
        self.assertEqual(readiness.evaluate(value,index=index(record()),as_of=AS_OF)['status'],readiness.HOLD_SCOPE)
    def test_missing_required_control_holds(self):
        value=intent(); value['required_control_ids'].append('STD-001')
        self.assertEqual(readiness.evaluate(value,index=index(record()),as_of=AS_OF)['status'],readiness.HOLD_CONTROL)
    def test_caller_cannot_carry_production_authority(self):
        value=intent(); value['production_authority']='APPROVED'
        with self.assertRaises(ValueError): readiness.evaluate(value,index=index(record()),as_of=AS_OF)
    def test_cli_can_assert_current_empty_hold(self):
        run=subprocess.run([sys.executable,str(ROOT/'scripts/check_control_inheritance_readiness.py'),str(INTENT),
                            '--as-of','2026-09-18T20:00:00Z','--expected-status',readiness.HOLD_NONE],
                           capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        self.assertEqual(json.loads(run.stdout)['status'],readiness.HOLD_NONE)

if __name__=='__main__':
    unittest.main()
