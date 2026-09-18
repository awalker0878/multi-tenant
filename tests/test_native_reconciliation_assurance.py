"""Native readback, writer-fencing and reconciliation assurance tests; no mutation."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import unittest

from scripts import check_native_reconciliation_assurance as assurance
from scripts import check_native_reconciliation_readiness as readiness

ROOT=Path(__file__).resolve().parents[1]
AS_OF=datetime(2026,9,18,22,5,tzinfo=timezone.utc)
INTENT=ROOT/'examples/native_reconciliation_readiness_intent.json.example'


def accepted_gap():
    return {
        'gap_id':'NATIVE-GAP-ACCEPTED-01',
        'status':'ACCEPTED',
        'owner_ref':'controlled-owner:native-platform',
        'treatment_ref':'controlled-treatment:native-gap',
        'decision_ref':'controlled-decision:native-gap-accepted',
        'review_by':'2026-12-31T23:59:59Z',
    }


def open_gap():
    return {
        'gap_id':'NATIVE-GAP-OPEN-01',
        'status':'OPEN',
        'owner_ref':'controlled-owner:native-platform',
        'treatment_ref':'controlled-treatment:native-gap-open',
        'decision_ref':None,
        'review_by':'2026-12-31T23:59:59Z',
    }


def record(state='CURRENT_RECONCILED',platform='NUTANIX'):
    return {
        'assurance_id':'NATIVE-RECONCILE-FIXTURE-01',
        'generation':1,
        'state':state,
        'operation_id':'native-op-fixture-01',
        'platform':platform,
        'scope':{
            'engineering_record_ref':'docs/NATIVE_READBACK.md',
            'operation_scope_ref':'controlled-operation-scope:fixture',
            'resource_set_ref':'controlled-resource-set:fixture',
            'change_record_ref':'controlled-change:fixture',
            'operation_owner_ref':'controlled-owner:native-platform',
            'operation_generation':7,
            'accepted_at':'2026-09-18T20:00:00Z',
            'review_by':'2026-12-31T23:59:59Z',
        },
        'native_interface':{
            'installed_tuple_ref':'controlled-platform-tuple:fixture',
            'api_profile_ref':'controlled-api-profile:fixture',
            'api_version_ref':'controlled-api-version:fixture',
            'rbac_evidence_ref':'controlled-rbac-evidence:fixture',
            'default_omission_evidence_ref':'controlled-default-omission:fixture',
            'version_token_evidence_ref':'controlled-version-token:fixture',
            'task_entity_coverage_ref':'controlled-task-entity-coverage:fixture',
            'coverage_state':'EXACT_ACCEPTED_SCOPE',
            'observed_at':'2026-09-18T21:00:00Z',
            'valid_until':'2026-12-31T23:59:59Z',
        },
        'observation':{
            'manifest_ref':'controlled-readback-manifest:fixture',
            'report_ref':'controlled-readback-report:fixture',
            'manifest_sha256':'a'*64,
            'report_sha256':'b'*64,
            'outcome':'MATCHED_ACCEPTED_SCOPE',
            'stable_samples':2,
            'observed_at':'2026-09-18T21:15:00Z',
            'valid_until':'2026-12-31T23:59:59Z',
        },
        'writer_fence':{
            'state':'VERIFIED_FENCED',
            'mechanism_ref':'controlled-writer-fence:fixture',
            'scope_ref':'controlled-writer-scope:fixture',
            'owner_ref':'controlled-owner:native-writer',
            'competing_writer_review_ref':'controlled-review:competing-writers',
            'observed_at':'2026-09-18T21:20:00Z',
            'valid_until':'2026-12-31T23:59:59Z',
        },
        'containment':{
            'state':'NONE',
            'authority_ref':'controlled-authority:incident',
            'scope_ref':'controlled-containment-scope:fixture',
            'state_evidence_ref':'controlled-containment-state:none',
            'release_decision_ref':None,
        },
        'reconciliation':{
            'status':'RECONCILED_NO_CHANGE',
            'decision_ref':'controlled-decision:reconciled-no-change',
            'source_of_truth_reconciliation_ref':'controlled-source-of-truth:reconciled',
            'data_impact_ref':'controlled-data-impact:none',
            'shared_dependency_ref':'controlled-shared-dependency:reviewed',
            'repair_plan_ref':None,
            'operation_generation':7,
            'decided_at':'2026-09-18T21:30:00Z',
        },
        'residual_gaps':[accepted_gap()],
        'source_refs':[
            'docs/NATIVE_READBACK.md',
            'docs/INTERRUPTED_CHANGE_RECOVERY.md',
            'docs/engineering/native-readback-writer-fencing-and-reconciliation-assurance.md',
        ],
    }


def index(*records):
    value=assurance.load()
    value['records']=list(records)
    return value


def intent(platform='NUTANIX'):
    value=readiness.load(INTENT)
    value['operation_id']='native-op-fixture-01'
    value['platform']=platform
    value['engineering_record_ref']='docs/NATIVE_READBACK.md'
    value['operation_scope_ref']='controlled-operation-scope:fixture'
    value['resource_set_ref']='controlled-resource-set:fixture'
    value['operation_generation']=7
    return value


class NativeReconciliationAssuranceTests(unittest.TestCase):
    def test_current_index_is_valid_empty(self):
        self.assertEqual(assurance.validate(assurance.load(),as_of=AS_OF)['record_count'],0)

    def test_current_reconciled_record_is_valid(self):
        self.assertEqual(assurance.validate(index(record()),as_of=AS_OF)['current_reconciled_count'],1)

    def test_all_supported_platform_labels_can_be_recorded(self):
        for platform in sorted(assurance.PLATFORMS):
            r=record(platform=platform)
            self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['current_reconciled_count'],1)

    def test_exact_native_interface_scope_is_required(self):
        r=record()
        r['native_interface']['coverage_state']='PARTIAL'
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_matched_readback_requires_two_stable_samples(self):
        r=record()
        r['observation']['stable_samples']=1
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_observation_digests_are_exact_sha256(self):
        r=record()
        r['observation']['report_sha256']='not-a-digest'
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_matching_readback_without_fence_cannot_be_current(self):
        r=record()
        r['writer_fence']['state']='NOT_FENCED'
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_fence_due_can_represent_current_observation_without_real_fence(self):
        r=record('FENCE_DUE')
        r['writer_fence']['state']='NOT_FENCED'
        self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['fence_due_count'],1)

    def test_stale_native_observation_is_observation_due(self):
        r=record('OBSERVATION_DUE')
        r['observation']['valid_until']='2026-09-18T22:04:59Z'
        self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['observation_due_count'],1)

    def test_review_due_requires_expired_scope_or_gap_review(self):
        r=record('REVIEW_DUE')
        r['scope']['review_by']='2026-09-18T22:04:59Z'
        self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['review_due_count'],1)

    def test_active_containment_cannot_be_current_reconciled(self):
        r=record()
        r['containment']['state']='ACTIVE'
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_active_containment_has_its_own_hold_state(self):
        r=record('CONTAINMENT_ACTIVE')
        r['containment']['state']='ACTIVE'
        self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['containment_active_count'],1)

    def test_containment_release_requires_explicit_decision(self):
        r=record()
        r['containment']['state']='RELEASED'
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)
        r['containment']['release_decision_ref']='controlled-decision:containment-release'
        self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['current_reconciled_count'],1)

    def test_pending_native_task_requires_reconciliation_state(self):
        r=record('RECONCILIATION_REQUIRED')
        r['observation']['outcome']='PENDING_NATIVE_TASK'
        r['observation']['stable_samples']=1
        r['reconciliation']['status']='PENDING_DECISION'
        r['reconciliation']['decision_ref']=None
        r['reconciliation']['repair_plan_ref']=None
        r['reconciliation']['decided_at']=None
        self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['reconciliation_required_count'],1)

    def test_partial_failure_cannot_be_promoted_to_current(self):
        r=record()
        r['observation']['outcome']='PARTIAL_FAILURE'
        r['observation']['stable_samples']=1
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_reconciliation_generation_must_match_operation_generation(self):
        r=record()
        r['reconciliation']['operation_generation']=8
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_reconciliation_decision_must_follow_observation_and_fence(self):
        r=record()
        r['reconciliation']['decided_at']='2026-09-18T21:10:00Z'
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_forward_repair_decision_needs_plan_but_does_not_authorize_repair(self):
        r=record()
        r['reconciliation']['status']='RECONCILED_FORWARD_REPAIR_DECIDED'
        r['reconciliation']['decision_ref']='controlled-decision:forward-repair'
        r['reconciliation']['repair_plan_ref']='controlled-repair-plan:fixture'
        self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['current_reconciled_count'],1)

    def test_current_reconciled_cannot_have_open_gap(self):
        r=record()
        r['residual_gaps'].append(open_gap())
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_gaps_open_requires_open_gap(self):
        r=record('GAPS_OPEN')
        r['residual_gaps'].append(open_gap())
        self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['gaps_open_count'],1)

    def test_duplicate_operation_assurance_is_rejected(self):
        one=record()
        two=deepcopy(one)
        two['assurance_id']='NATIVE-RECONCILE-FIXTURE-02'
        with self.assertRaises(ValueError):
            assurance.validate(index(one,two),as_of=AS_OF)

    def test_cli_empty_index_grants_no_native_mutation_authority(self):
        run=subprocess.run([
            sys.executable,str(ROOT/'scripts/check_native_reconciliation_assurance.py'),
            '--as-of','2026-09-18T22:05:00Z',
        ],capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        out=json.loads(run.stdout)
        self.assertEqual(out['record_count'],0)
        for key in (
            'may_list_tasks','may_cancel_task','may_release_containment',
            'may_import_state','may_repair','may_apply','may_delete','may_activate'
        ):
            self.assertIs(out[key],False)


class NativeReconciliationReadinessTests(unittest.TestCase):
    def test_current_example_holds_without_native_reconciliation(self):
        result=readiness.evaluate(readiness.load(INTENT),index=assurance.load(),as_of=AS_OF)
        self.assertEqual(result['status'],readiness.HOLD_NONE)

    def test_current_reconciled_satisfies_only_readiness_prerequisite(self):
        result=readiness.evaluate(intent(),index=index(record()),as_of=AS_OF)
        self.assertEqual(result['status'],readiness.READY)
        for key in (
            'may_list_tasks','may_cancel_task','may_release_containment',
            'may_import_state','may_repair','may_apply','may_delete','may_activate'
        ):
            self.assertIs(result[key],False)

    def test_observation_due_holds(self):
        r=record('OBSERVATION_DUE')
        r['observation']['valid_until']='2026-09-18T22:04:59Z'
        self.assertEqual(readiness.evaluate(intent(),index=index(r),as_of=AS_OF)['status'],readiness.HOLD_OBSERVATION)

    def test_fence_due_holds(self):
        r=record('FENCE_DUE')
        r['writer_fence']['state']='NOT_FENCED'
        self.assertEqual(readiness.evaluate(intent(),index=index(r),as_of=AS_OF)['status'],readiness.HOLD_FENCE)

    def test_active_containment_holds(self):
        r=record('CONTAINMENT_ACTIVE')
        r['containment']['state']='ACTIVE'
        self.assertEqual(readiness.evaluate(intent(),index=index(r),as_of=AS_OF)['status'],readiness.HOLD_CONTAINMENT)

    def test_pending_reconciliation_holds(self):
        r=record('RECONCILIATION_REQUIRED')
        r['reconciliation']['status']='PENDING_DECISION'
        r['reconciliation']['decision_ref']=None
        r['reconciliation']['repair_plan_ref']=None
        r['reconciliation']['decided_at']=None
        self.assertEqual(readiness.evaluate(intent(),index=index(r),as_of=AS_OF)['status'],readiness.HOLD_RECONCILIATION)

    def test_open_gap_holds(self):
        r=record('GAPS_OPEN')
        r['residual_gaps'].append(open_gap())
        self.assertEqual(readiness.evaluate(intent(),index=index(r),as_of=AS_OF)['status'],readiness.HOLD_GAPS)

    def test_uncertain_holds(self):
        self.assertEqual(
            readiness.evaluate(intent(),index=index(record('UNCERTAIN')),as_of=AS_OF)['status'],
            readiness.HOLD_UNCERTAIN)

    def test_scope_generation_mismatch_holds(self):
        value=intent()
        value['operation_generation']=8
        self.assertEqual(readiness.evaluate(value,index=index(record()),as_of=AS_OF)['status'],readiness.HOLD_SCOPE)

    def test_caller_cannot_carry_production_authority(self):
        value=intent()
        value['production_authority']='APPROVED'
        with self.assertRaises(ValueError):
            readiness.evaluate(value,index=index(record()),as_of=AS_OF)

    def test_cli_can_assert_current_empty_hold(self):
        run=subprocess.run([
            sys.executable,str(ROOT/'scripts/check_native_reconciliation_readiness.py'),str(INTENT),
            '--as-of','2026-09-18T22:05:00Z',
            '--expected-status',readiness.HOLD_NONE,
        ],capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        self.assertEqual(json.loads(run.stdout)['status'],readiness.HOLD_NONE)


if __name__=='__main__':
    unittest.main()
