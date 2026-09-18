"""Bounded extension adoption tests; no bare-metal, cluster or device provisioning."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import unittest

from scripts import check_extension_adoption_assurance as assurance
from scripts import check_extension_adoption_readiness as readiness

ROOT=Path(__file__).resolve().parents[1]
AS_OF=datetime(2026,9,18,21,0,tzinfo=timezone.utc)
INTENT=ROOT/'examples/extension_adoption_readiness_intent.json.example'


def specific(kind):
    return {
        key:f'controlled-extension-evidence:{kind.lower()}:{key}'
        for key in sorted(assurance.KIND_REQUIREMENTS[kind])
    }


def dimension_evidence():
    return {
        key:f'controlled-extension-dimension:{key}'
        for key in sorted(assurance.QUAL_DIMENSIONS)
    }


def accepted_gap():
    return {
        'gap_id':'EXT-GAP-ACCEPTED-01',
        'status':'ACCEPTED',
        'owner_ref':'controlled-owner:extension',
        'treatment_ref':'controlled-treatment:extension',
        'decision_ref':'controlled-decision:accepted-extension-gap',
        'review_by':'2026-12-31T23:59:59Z',
    }


def open_gap():
    return {
        'gap_id':'EXT-GAP-OPEN-01',
        'status':'OPEN',
        'owner_ref':'controlled-owner:extension',
        'treatment_ref':'controlled-treatment:open-extension-gap',
        'decision_ref':None,
        'review_by':'2026-12-31T23:59:59Z',
    }


def record(kind='CONTAINER_HOSTING',state='CURRENT_ADOPTED'):
    return {
        'assurance_id':'EXT-ASSURANCE-FIXTURE-01',
        'generation':1,
        'state':state,
        'extension_kind':kind,
        'extension_id':'fixture-extension-01',
        'scope':{
            'extension_profile_ref':'controlled-extension-profile:fixture',
            'service_class_ref':'controlled-service-class:fixture-extension',
            'adoption_decision_ref':'controlled-decision:extension-adoption',
            'accepted_at':'2026-09-18T16:00:00Z',
            'review_by':'2026-12-31T23:59:59Z',
            'extension_owner_ref':'controlled-owner:extension',
            'base_service_status':'EXTENSION_ONLY',
            'portability_impact_ref':'controlled-portability-impact:fixture',
        },
        'design':{
            'topology_ref':'controlled-design:topology',
            'trust_boundaries_ref':'controlled-design:trust-boundaries',
            'failure_model_ref':'controlled-design:failure-model',
            'management_ref':'controlled-design:management',
            'network_ref':'controlled-design:network',
            'storage_ref':'controlled-design:storage',
            'identity_ref':'controlled-design:identity',
            'provisioning_ref':'controlled-design:provisioning',
            'recovery_ref':'controlled-design:recovery',
            'retirement_ref':'controlled-design:retirement',
        },
        'specific_evidence':specific(kind),
        'qualification':{
            'applicable_test_sets':['CT-035','CT-065'],
            'dimension_evidence':dimension_evidence(),
            'qualified_at':'2026-09-18T18:00:00Z',
            'valid_until':'2026-12-31T23:59:59Z',
            'decision_ref':'controlled-decision:extension-qualification',
            'authority_role':'Fixture extension qualification authority',
        },
        'unsupported_capabilities':['fixture-unsupported-optional-capability'],
        'mandatory_control_weakening':'DENIED',
        'residual_gaps':[accepted_gap()],
        'source_refs':[
            'docs/architecture/reference/19-physical-workloads-and-future-platform-extensions.md',
            'docs/assurance/site-qualification/8-extensions-and-release-maintenance.md',
            'docs/engineering/bounded-extension-adoption-and-qualification-assurance.md',
        ],
    }


def index(*records):
    value=assurance.load()
    value['records']=list(records)
    return value


def intent(kind='CONTAINER_HOSTING'):
    value=readiness.load(INTENT)
    value['extension_kind']=kind
    value['extension_id']='fixture-extension-01'
    value['extension_profile_ref']='controlled-extension-profile:fixture'
    value['service_class_ref']='controlled-service-class:fixture-extension'
    return value


class ExtensionAssuranceTests(unittest.TestCase):
    def test_current_index_is_valid_empty(self):
        self.assertEqual(assurance.validate(assurance.load(),as_of=AS_OF)['record_count'],0)

    def test_complete_container_extension_is_current(self):
        result=assurance.validate(index(record()),as_of=AS_OF)
        self.assertEqual(result['current_adopted_count'],1)

    def test_complete_bare_metal_extension_is_current(self):
        result=assurance.validate(index(record('BARE_METAL')),as_of=AS_OF)
        self.assertEqual(result['current_adopted_count'],1)

    def test_extension_can_never_claim_base_service_status(self):
        r=record()
        r['scope']['base_service_status']='BASE_SERVICE'
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_container_namespace_only_is_not_complete_boundary_evidence(self):
        r=record()
        r['specific_evidence']={
            'network_policy_enforcement':'controlled-evidence:namespace-policy'
        }
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_bare_metal_vrf_only_is_not_complete_boundary_evidence(self):
        r=record('BARE_METAL')
        r['specific_evidence']={
            'port_gateway_authority':'controlled-evidence:physical-vrf'
        }
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_all_qualification_dimensions_are_required(self):
        r=record()
        r['qualification']['dimension_evidence'].pop('storage')
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_unsupported_capability_cannot_weaken_mandatory_control(self):
        r=record()
        r['mandatory_control_weakening']='ALLOWED'
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_current_adoption_rejects_expired_qualification(self):
        r=record()
        r['qualification']['valid_until']='2026-09-18T20:59:59Z'
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_qualification_due_requires_expired_qualification_only(self):
        r=record(state='QUALIFICATION_DUE')
        r['qualification']['valid_until']='2026-09-18T20:59:59Z'
        self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['qualification_due_count'],1)

    def test_review_due_requires_expired_scope_or_gap_review(self):
        r=record(state='REVIEW_DUE')
        r['scope']['review_by']='2026-09-18T20:59:59Z'
        self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['review_due_count'],1)

    def test_current_adoption_cannot_have_open_gap(self):
        r=record()
        r['residual_gaps'].append(open_gap())
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_gaps_open_requires_open_gap(self):
        r=record(state='GAPS_OPEN')
        r['residual_gaps'].append(open_gap())
        self.assertEqual(assurance.validate(index(r),as_of=AS_OF)['gaps_open_count'],1)

    def test_open_gap_cannot_carry_acceptance_decision(self):
        r=record(state='GAPS_OPEN')
        gap=open_gap()
        gap['decision_ref']='controlled-decision:premature'
        r['residual_gaps'].append(gap)
        with self.assertRaises(ValueError):
            assurance.validate(index(r),as_of=AS_OF)

    def test_duplicate_extension_id_rejected(self):
        one=record()
        two=deepcopy(one)
        two['assurance_id']='EXT-ASSURANCE-FIXTURE-02'
        with self.assertRaises(ValueError):
            assurance.validate(index(one,two),as_of=AS_OF)

    def test_cli_empty_index_grants_no_extension_authority(self):
        run=subprocess.run([
            sys.executable,str(ROOT/'scripts/check_extension_adoption_assurance.py'),
            '--as-of','2026-09-18T21:00:00Z',
        ],capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        out=json.loads(run.stdout)
        self.assertEqual(out['record_count'],0)
        for key in (
            'may_add_to_base_service','may_provision_extension','may_change_physical_fabric',
            'may_create_cluster','may_assign_device','may_apply','may_activate'
        ):
            self.assertIs(out[key],False)


class ExtensionReadinessTests(unittest.TestCase):
    def test_current_example_holds_without_extension_adoption(self):
        result=readiness.evaluate(readiness.load(INTENT),index=assurance.load(),as_of=AS_OF)
        self.assertEqual(result['status'],readiness.HOLD_NONE)

    def test_current_extension_is_ready_only_as_extension_prerequisite(self):
        result=readiness.evaluate(intent(),index=index(record()),as_of=AS_OF)
        self.assertEqual(result['status'],readiness.READY)
        self.assertEqual(result['base_service_status'],'EXTENSION_ONLY')
        for key in (
            'may_add_to_base_service','may_provision_extension','may_change_physical_fabric',
            'may_create_cluster','may_assign_device','may_apply','may_activate'
        ):
            self.assertIs(result[key],False)

    def test_bare_metal_kind_matches_only_bare_metal_record(self):
        result=readiness.evaluate(
            intent('BARE_METAL'),index=index(record('BARE_METAL')),as_of=AS_OF)
        self.assertEqual(result['status'],readiness.READY)

    def test_kind_mismatch_holds(self):
        result=readiness.evaluate(
            intent('BARE_METAL'),index=index(record('CONTAINER_HOSTING')),as_of=AS_OF)
        self.assertEqual(result['status'],readiness.HOLD_SCOPE)

    def test_review_due_holds(self):
        r=record(state='REVIEW_DUE')
        r['scope']['review_by']='2026-09-18T20:59:59Z'
        self.assertEqual(readiness.evaluate(intent(),index=index(r),as_of=AS_OF)['status'],readiness.HOLD_REVIEW)

    def test_qualification_due_holds(self):
        r=record(state='QUALIFICATION_DUE')
        r['qualification']['valid_until']='2026-09-18T20:59:59Z'
        self.assertEqual(readiness.evaluate(intent(),index=index(r),as_of=AS_OF)['status'],readiness.HOLD_QUALIFICATION)

    def test_open_gap_holds(self):
        r=record(state='GAPS_OPEN')
        r['residual_gaps'].append(open_gap())
        self.assertEqual(readiness.evaluate(intent(),index=index(r),as_of=AS_OF)['status'],readiness.HOLD_GAPS)

    def test_uncertain_holds(self):
        self.assertEqual(
            readiness.evaluate(intent(),index=index(record(state='UNCERTAIN')),as_of=AS_OF)['status'],
            readiness.HOLD_UNCERTAIN)

    def test_profile_mismatch_holds(self):
        value=intent()
        value['extension_profile_ref']='controlled-extension-profile:other'
        self.assertEqual(readiness.evaluate(value,index=index(record()),as_of=AS_OF)['status'],readiness.HOLD_SCOPE)

    def test_caller_cannot_carry_production_authority(self):
        value=intent()
        value['production_authority']='APPROVED'
        with self.assertRaises(ValueError):
            readiness.evaluate(value,index=index(record()),as_of=AS_OF)

    def test_cli_can_assert_current_empty_hold(self):
        run=subprocess.run([
            sys.executable,str(ROOT/'scripts/check_extension_adoption_readiness.py'),str(INTENT),
            '--as-of','2026-09-18T21:00:00Z',
            '--expected-status',readiness.HOLD_NONE,
        ],capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        self.assertEqual(json.loads(run.stdout)['status'],readiness.HOLD_NONE)


if __name__=='__main__':
    unittest.main()
