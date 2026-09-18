"""G34 knowledge maintenance and cross-link integrity tests; no publication authority."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import unittest

from scripts import check_knowledge_maintenance_assurance as assurance
from scripts import check_knowledge_maintenance_readiness as readiness

ROOT=Path(__file__).resolve().parents[1]
AS_OF=datetime(2026,9,18,21,5,tzinfo=timezone.utc)
INTENT=ROOT/'examples/knowledge_maintenance_readiness_intent.json.example'


def version_set():
    return {
        'architecture':'docs/architecture/reference/README.md',
        'engineering':'docs/engineering/README.md',
        'requirements':'reference/Portable_Hosting_Delivery_Kits_v1_1/04_Shared/requirements.csv',
        'tests':'reference/Portable_Hosting_Delivery_Kits_v1_1/04_Shared/tests.csv',
        'gap_register':'docs/assurance/gap-map/3-detailed-gap-register-and-treatment.md',
        'source_reviews':'reference/Portable_Hosting_Delivery_Kits_v1_1/04_Shared/development/source_reviews.csv',
        'knowledge_homes':'sources/documentation/knowledge_home_registry.json',
        'generator':'scripts/build_documentation.py',
    }


def record(state='CURRENT_MAINTAINED'):
    return {
        'assurance_id':'KNOWLEDGE-MAINT-FIXTURE-01',
        'generation':1,
        'state':state,
        'release_id':'fixture-release-01',
        'reviewed_revision':'f12fbfd75a225414cb0eaf5bfe0b1c6c9ad71a27',
        'version_set':version_set(),
        'maintenance':{
            'owner_ref':'controlled-owner:architecture-document',
            'cadence_ref':'controlled-cadence:architecture-release',
            'reviewed_at':'2026-09-18T20:00:00Z',
            'review_by':'2026-12-31T23:59:59Z',
        },
        'validation':{
            'documentation_check_ref':'controlled-validation:documentation',
            'repository_check_ref':'controlled-validation:repository',
            'link_validation_ref':'controlled-validation:links-and-anchors',
            'requirement_mapping_ref':'controlled-validation:requirement-mapping',
            'primary_home_review_ref':'controlled-validation:primary-homes',
            'duplicate_policy_review_ref':'controlled-validation:duplicate-policy',
            'drift_review_ref':'controlled-validation:parent-supplement-drift',
            'scenario_consistency_ref':'controlled-validation:scenario-consistency',
            'observed_at':'2026-09-18T20:30:00Z',
            'valid_until':'2026-12-31T23:59:59Z',
            'status':'PASSED_RELEASE_INTEGRITY',
        },
        'change_control':{
            'change_record_ref':'controlled-change:fixture-release',
            'approval_ref':'controlled-approval:fixture-release',
            'approved_at':'2026-09-18T20:45:00Z',
            'owner_ref':'controlled-owner:architecture-change',
            'affected_topic_ids':['PROVISIONING_CHANGE','CAPACITY_OPERATIONS_ASSURANCE'],
            'ripple_review_ref':'controlled-review:change-ripple',
        },
        'unresolved_conflicts':[],
        'source_refs':[
            'docs/assurance/gap-map/2-primary-knowledge-homes-and-cross-cutting-changes.md',
            'docs/engineering/knowledge-maintenance-and-release-integrity-assurance.md',
        ],
    }


def index(*records):
    value=assurance.load()
    value['records']=list(records)
    return value


def intent():
    value=readiness.load(INTENT)
    value['release_id']='fixture-release-01'
    return value


class KnowledgeHomeRegistryTests(unittest.TestCase):
    def test_source_derived_registry_is_complete_and_resolves(self):
        result=assurance.validate_registry(assurance.load_registry())
        self.assertEqual(result['topic_count'],8)
        self.assertEqual({x['id'] for x in result['topics']},assurance.TOPIC_IDS)

    def test_missing_topic_is_rejected(self):
        value=assurance.load_registry()
        value['topics'].pop()
        with self.assertRaises(ValueError):
            assurance.validate_registry(value)

    def test_duplicate_primary_home_is_rejected(self):
        value=assurance.load_registry()
        value['topics'][1]['primary_home_ref']=value['topics'][0]['primary_home_ref']
        with self.assertRaises(ValueError):
            assurance.validate_registry(value)

    def test_bad_parent_anchor_is_rejected(self):
        value=assurance.load_registry()
        value['topics'][0]['parent_refs'][0]=value['topics'][0]['parent_refs'][0].split('#')[0]+'#MISSING'
        with self.assertRaises(ValueError):
            assurance.validate_registry(value)


class ReleaseMaintenanceRecordTests(unittest.TestCase):
    def test_current_assurance_index_is_valid_empty(self):
        result=assurance.validate(assurance.load(),as_of=AS_OF)
        self.assertEqual(result['record_count'],0)
        self.assertEqual(result['knowledge_topic_count'],8)

    def test_current_maintained_record_is_valid(self):
        result=assurance.validate(index(record()),as_of=AS_OF)
        self.assertEqual(result['current_maintained_count'],1)

    def test_version_set_must_cover_all_roles(self):
        r=record()
        r['version_set'].pop('source_reviews')
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_version_set_roles_cannot_alias_same_file(self):
        r=record()
        r['version_set']['tests']=r['version_set']['requirements']
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_approved_change_must_follow_validation(self):
        r=record()
        r['change_control']['approved_at']='2026-09-18T20:15:00Z'
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_unknown_affected_topic_is_rejected(self):
        r=record()
        r['change_control']['affected_topic_ids'].append('UNKNOWN_TOPIC')
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_current_maintained_cannot_have_unresolved_conflict(self):
        r=record()
        r['unresolved_conflicts']=['controlled-conflict:duplicate-policy']
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_review_due_requires_expired_maintenance_review(self):
        r=record('REVIEW_DUE')
        r['maintenance']['review_by']='2026-09-18T21:04:59Z'
        self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['review_due_count'],1)

    def test_validation_due_requires_current_maintenance_and_expired_validation(self):
        r=record('VALIDATION_DUE')
        r['validation']['valid_until']='2026-09-18T21:04:59Z'
        self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['validation_due_count'],1)

    def test_conflicts_open_requires_current_evidence_and_conflict(self):
        r=record('CONFLICTS_OPEN')
        r['unresolved_conflicts']=['controlled-conflict:supplement-drift']
        self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['conflicts_open_count'],1)

    def test_duplicate_release_record_is_rejected(self):
        one=record()
        two=deepcopy(one)
        two['assurance_id']='KNOWLEDGE-MAINT-FIXTURE-02'
        with self.assertRaises(ValueError):
            assurance.validate(index(one,two),as_of=AS_OF)

    def test_cli_empty_index_grants_no_publication_authority(self):
        run=subprocess.run([
            sys.executable,str(ROOT/'scripts/check_knowledge_maintenance_assurance.py'),
            '--as-of','2026-09-18T21:05:00Z',
        ],capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        out=json.loads(run.stdout)
        self.assertEqual(out['record_count'],0)
        for key in (
            'may_publish_release','may_approve_change','may_reassign_primary_home',
            'may_accept_conflict','may_authorize_architecture','may_apply','may_activate'
        ):
            self.assertIs(out[key],False)


class KnowledgeMaintenanceReadinessTests(unittest.TestCase):
    def test_current_example_holds_without_maintenance_record(self):
        result=readiness.evaluate(readiness.load(INTENT),index=assurance.load(),as_of=AS_OF)
        self.assertEqual(result['status'],readiness.HOLD_NONE)

    def test_current_record_is_only_maintenance_prerequisite(self):
        result=readiness.evaluate(intent(),index=index(record()),as_of=AS_OF)
        self.assertEqual(result['status'],readiness.READY)
        for key in (
            'may_publish_release','may_approve_change','may_reassign_primary_home',
            'may_accept_conflict','may_authorize_architecture','may_apply','may_activate'
        ):
            self.assertIs(result[key],False)

    def test_review_due_holds(self):
        r=record('REVIEW_DUE')
        r['maintenance']['review_by']='2026-09-18T21:04:59Z'
        self.assertEqual(readiness.evaluate(intent(),index=index(r),as_of=AS_OF)['status'],readiness.HOLD_REVIEW)

    def test_validation_due_holds(self):
        r=record('VALIDATION_DUE')
        r['validation']['valid_until']='2026-09-18T21:04:59Z'
        self.assertEqual(readiness.evaluate(intent(),index=index(r),as_of=AS_OF)['status'],readiness.HOLD_VALIDATION)

    def test_open_conflict_holds(self):
        r=record('CONFLICTS_OPEN')
        r['unresolved_conflicts']=['controlled-conflict:duplicate-policy']
        self.assertEqual(readiness.evaluate(intent(),index=index(r),as_of=AS_OF)['status'],readiness.HOLD_CONFLICTS)

    def test_uncertain_holds(self):
        self.assertEqual(
            readiness.evaluate(intent(),index=index(record('UNCERTAIN')),as_of=AS_OF)['status'],
            readiness.HOLD_UNCERTAIN)

    def test_revision_mismatch_holds(self):
        value=intent()
        value['reviewed_revision']='0000000000000000000000000000000000000000'
        self.assertEqual(readiness.evaluate(value,index=index(record()),as_of=AS_OF)['status'],readiness.HOLD_REVISION)

    def test_required_topic_set_cannot_be_reduced(self):
        value=intent()
        value['required_topic_ids'].pop()
        with self.assertRaises(ValueError):
            readiness.evaluate(value,index=index(record()),as_of=AS_OF)

    def test_caller_cannot_carry_publication_authority(self):
        value=intent()
        value['publication_authority']='APPROVED'
        with self.assertRaises(ValueError):
            readiness.evaluate(value,index=index(record()),as_of=AS_OF)

    def test_cli_can_assert_current_empty_hold(self):
        run=subprocess.run([
            sys.executable,str(ROOT/'scripts/check_knowledge_maintenance_readiness.py'),str(INTENT),
            '--as-of','2026-09-18T21:05:00Z',
            '--expected-status',readiness.HOLD_NONE,
        ],capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        self.assertEqual(json.loads(run.stdout)['status'],readiness.HOLD_NONE)


if __name__=='__main__':
    unittest.main()
