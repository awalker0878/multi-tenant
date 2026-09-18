"""Operational handover and incident-readiness assurance tests; no live operations."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import unittest

from scripts import check_operational_handover_assurance as assurance
from scripts import check_operational_handover_readiness as readiness

ROOT=Path(__file__).resolve().parents[1]
AS_OF=datetime(2026,9,18,21,0,tzinfo=timezone.utc)
INTENT=ROOT/'examples/operational_handover_readiness_intent.json.example'


def scope():
    return {
        'site_ref':'controlled-site:fixture',
        'service_class_ref':'controlled-service-class:fixture',
        'platform_profile_ref':'controlled-platform-profile:fixture',
        'operating_model_ref':'controlled-operating-model:fixture',
        'recovery_profile_ref':'controlled-recovery-profile:fixture',
    }


def decision_owners():
    return {
        key:{
            'owner_ref':f'controlled-owner:{key}',
            'evidence_ref':f'controlled-evidence:{key}',
        }
        for key in assurance.DECISION_KEYS
    }


def accepted_obligation():
    return {
        'obligation_id':'OPS-OBLIGATION-FIXTURE-01',
        'status':'ACCEPTED',
        'owner_ref':'controlled-owner:service',
        'treatment_ref':'controlled-treatment:fixture',
        'decision_ref':'controlled-decision:accepted-fixture',
        'review_by':'2026-12-31T23:59:59Z',
    }


def open_obligation():
    return {
        'obligation_id':'OPS-OBLIGATION-OPEN-01',
        'status':'OPEN',
        'owner_ref':'controlled-owner:service',
        'treatment_ref':'controlled-treatment:open-fixture',
        'decision_ref':None,
        'review_by':'2026-12-31T23:59:59Z',
    }


def record(state='CURRENT_ACCEPTED'):
    return {
        'assurance_id':'OPS-HANDOVER-FIXTURE-01',
        'generation':1,
        'state':state,
        'request_id':'EXAMPLE-SITE-CAPACITY-01',
        'wsd_engineering_ref':'docs/current/internal-hosting-solution.md',
        'scope':scope(),
        'handover':{
            'acceptance_ref':'controlled-decision:handover-fixture',
            'accepted_at':'2026-09-18T17:00:00Z',
            'review_by':'2026-12-31T23:59:59Z',
            'receiving_owner_ref':'controlled-owner:receiving-operations',
            'support_owner_ref':'controlled-owner:support',
            'escalation_ref':'controlled-escalation:fixture',
            'on_call_ref':'controlled-on-call:fixture',
            'as_built_ref':'controlled-as-built:fixture',
            'dependency_ref':'controlled-dependency-set:fixture',
            'slo_recovery_ref':'controlled-service-objective:fixture',
            'capacity_ref':'controlled-capacity-envelope:fixture',
            'runbook_ref':'controlled-runbook-set:fixture',
            'evidence_package_ref':'controlled-evidence-package:fixture',
        },
        'decision_owners':decision_owners(),
        'credential_review':{
            'review_ref':'controlled-review:privileged-access',
            'observed_at':'2026-09-18T18:00:00Z',
            'valid_until':'2026-12-31T23:59:59Z',
            'privileged_paths_ref':'controlled-paths:privileged',
            'custody_ref':'controlled-custody:credentials',
            'break_glass_test_ref':'controlled-test:break-glass',
            'stale_grants':'NONE_UNRESOLVED',
        },
        'monitoring':{
            'monitoring_ref':'controlled-monitoring:service',
            'alerting_ref':'controlled-alerting:service',
            'evidence_loss_ref':'controlled-monitoring:evidence-loss',
            'observed_at':'2026-09-18T18:00:00Z',
            'valid_until':'2026-12-31T23:59:59Z',
        },
        'incident_exercise':{
            'exercise_ref':'controlled-exercise:incident-fixture',
            'test_set':'CT-057',
            'incident_authority_ref':'controlled-authority:incident',
            'containment_scope_ref':'controlled-scope:containment',
            'containment_evidence_ref':'controlled-evidence:containment',
            'release_decision_ref':'controlled-decision:containment-release',
            'evidence_custody_ref':'controlled-custody:incident-evidence',
            'coordination_ref':'controlled-coordination:incident',
            'recovery_acceptance_ref':'controlled-decision:recovery-acceptance',
            'emergency_change_reconciliation_ref':'controlled-reconciliation:emergency-change',
            'started_at':'2026-09-18T18:10:00Z',
            'contained_at':'2026-09-18T18:15:00Z',
            'released_at':'2026-09-18T18:40:00Z',
            'reconciled_at':'2026-09-18T18:50:00Z',
            'evidence_valid_until':'2026-12-18T18:50:00Z',
            'unrelated_service_impact':'WITHIN_APPROVED_SCOPE',
            'outcome':'PASSED_SCOPED_EXERCISE',
        },
        'residual_obligations':[accepted_obligation()],
        'source_refs':[
            'docs/assurance/site-qualification/7-operating-accountability-handover-and-change.md',
            'docs/engineering/operational-handover-and-incident-readiness-assurance.md',
        ],
    }


def index(*records):
    value=assurance.load()
    value['records']=list(records)
    return value


def intent():
    value=readiness.load(INTENT)
    value['required_scope']=scope()
    return value


class OperationalHandoverRecordTests(unittest.TestCase):
    def test_current_index_is_valid_empty(self):
        self.assertEqual(assurance.validate(assurance.load(),as_of=AS_OF)['record_count'],0)

    def test_current_accepted_record_is_valid(self):
        self.assertEqual(assurance.validate(index(record()),as_of=AS_OF)['current_accepted_count'],1)

    def test_all_decision_owners_are_required(self):
        r=record()
        r['decision_owners'].pop('containment_release')
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_unresolved_stale_privileged_grants_rejected(self):
        r=record()
        r['credential_review']['stale_grants']='PRESENT'
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_incident_release_must_be_attributable(self):
        r=record()
        r['incident_exercise']['release_decision_ref']=''
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_incident_exercise_must_be_scoped(self):
        r=record()
        r['incident_exercise']['unrelated_service_impact']='BROAD_OUTAGE'
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_incident_exercise_chronology_rejected(self):
        r=record()
        r['incident_exercise']['released_at']='2026-09-18T18:14:00Z'
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_current_acceptance_rejects_expired_credential_review(self):
        r=record()
        r['credential_review']['valid_until']='2026-09-18T20:59:59Z'
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_review_due_requires_expired_review_evidence(self):
        r=record('REVIEW_DUE')
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)
        r['monitoring']['valid_until']='2026-09-18T20:59:59Z'
        self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['review_due_count'],1)

    def test_exercise_due_requires_expired_exercise_only(self):
        r=record('EXERCISE_DUE')
        r['incident_exercise']['evidence_valid_until']='2026-09-18T20:59:59Z'
        self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['exercise_due_count'],1)

    def test_current_accepted_cannot_have_open_obligation(self):
        r=record()
        r['residual_obligations'].append(open_obligation())
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_gaps_open_requires_open_obligation(self):
        r=record('GAPS_OPEN')
        r['residual_obligations'].append(open_obligation())
        self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['gaps_open_count'],1)

    def test_open_obligation_cannot_carry_acceptance_decision(self):
        r=record('GAPS_OPEN')
        item=open_obligation()
        item['decision_ref']='controlled-decision:premature'
        r['residual_obligations'].append(item)
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_duplicate_request_assurance_rejected(self):
        one=record()
        two=deepcopy(one)
        two['assurance_id']='OPS-HANDOVER-FIXTURE-02'
        with self.assertRaises(ValueError):
            assurance.validate(index(one,two),as_of=AS_OF)

    def test_cli_empty_index_grants_no_operations_authority(self):
        run=subprocess.run([
            sys.executable,str(ROOT/'scripts/check_operational_handover_assurance.py'),
            '--as-of','2026-09-18T21:00:00Z',
        ],capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        out=json.loads(run.stdout)
        self.assertEqual(out['record_count'],0)
        for key in (
            'may_change_privileged_access','may_start_containment','may_release_containment',
            'may_execute_recovery','may_reconcile_emergency_change','may_apply','may_activate'
        ):
            self.assertIs(out[key],False)


class OperationalHandoverReadinessTests(unittest.TestCase):
    def test_current_example_holds_without_handover(self):
        result=readiness.evaluate(readiness.load(INTENT),index=assurance.load(),as_of=AS_OF)
        self.assertEqual(result['status'],readiness.HOLD_NONE)

    def test_current_handover_satisfies_only_readiness_prerequisite(self):
        result=readiness.evaluate(intent(),index=index(record()),as_of=AS_OF)
        self.assertEqual(result['status'],readiness.READY)
        for key in (
            'may_change_privileged_access','may_start_containment','may_release_containment',
            'may_execute_recovery','may_reconcile_emergency_change','may_apply','may_activate'
        ):
            self.assertIs(result[key],False)

    def test_review_due_holds(self):
        r=record('REVIEW_DUE')
        r['handover']['review_by']='2026-09-18T20:59:59Z'
        self.assertEqual(readiness.evaluate(intent(),index=index(r),as_of=AS_OF)['status'],readiness.HOLD_REVIEW)

    def test_exercise_due_holds(self):
        r=record('EXERCISE_DUE')
        r['incident_exercise']['evidence_valid_until']='2026-09-18T20:59:59Z'
        self.assertEqual(readiness.evaluate(intent(),index=index(r),as_of=AS_OF)['status'],readiness.HOLD_EXERCISE)

    def test_open_obligation_holds(self):
        r=record('GAPS_OPEN')
        r['residual_obligations'].append(open_obligation())
        self.assertEqual(readiness.evaluate(intent(),index=index(r),as_of=AS_OF)['status'],readiness.HOLD_GAPS)

    def test_uncertain_handover_holds(self):
        self.assertEqual(readiness.evaluate(intent(),index=index(record('UNCERTAIN')),as_of=AS_OF)['status'],readiness.HOLD_UNCERTAIN)

    def test_scope_mismatch_holds(self):
        value=intent()
        value['required_scope']['operating_model_ref']='controlled-operating-model:other'
        self.assertEqual(readiness.evaluate(value,index=index(record()),as_of=AS_OF)['status'],readiness.HOLD_SCOPE)

    def test_caller_cannot_carry_production_authority(self):
        value=intent()
        value['production_authority']='APPROVED'
        with self.assertRaises(ValueError):
            readiness.evaluate(value,index=index(record()),as_of=AS_OF)

    def test_cli_can_assert_current_empty_hold(self):
        run=subprocess.run([
            sys.executable,str(ROOT/'scripts/check_operational_handover_readiness.py'),str(INTENT),
            '--as-of','2026-09-18T21:00:00Z',
            '--expected-status',readiness.HOLD_NONE,
        ],capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        self.assertEqual(json.loads(run.stdout)['status'],readiness.HOLD_NONE)


if __name__=='__main__':
    unittest.main()
