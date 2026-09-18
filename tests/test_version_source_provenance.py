"""Version/source provenance and lifecycle assurance tests; no native qualification."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import unittest

from scripts import check_version_source_provenance as provenance
from scripts import check_version_source_readiness as readiness

ROOT=Path(__file__).resolve().parents[1]
AS_OF=datetime(2026,9,18,22,0,tzinfo=timezone.utc)
INTENT=ROOT/'examples/version_source_readiness_intent.json.example'


def product_tuple(*,licensed=True):
    return {
        'product':'fixture-product',
        'product_version':'1.0',
        'api':'fixture-api',
        'api_version':'1.0',
        'automation_providers':['fixture/provider = 1.0'],
        'hardware_profile_ref':'controlled-record:fixture-hardware',
        'feature_licenses':['fixture-feature-license'] if licensed else [],
    }


def source(kind,state='CURRENT_REVIEWED',valid_until='2026-12-31T23:59:59Z'):
    return {
        'source_id':f'SRC-{kind}',
        'kind':kind,
        'edition':f'fixture-{kind.lower()}-edition',
        'review_state':state,
        'reviewed_at':'2026-09-17T08:00:00Z',
        'valid_until':valid_until,
        'evidence_ref':f'controlled-source-evidence:{kind.lower()}',
        'limitation':'Synthetic unit-test source review only.',
    }


def record(state='CURRENT_SUPPORTED',*,licensed=True):
    kinds=sorted(provenance.BASE_REQUIRED_KINDS | ({'FEATURE_ENTITLEMENT'} if licensed else set()))
    return {
        'provenance_id':'PROV-NUTANIX-FIXTURE-01',
        'generation':1,
        'state':state,
        'platform':'nutanix',
        'product_tuple_id':'fixture-tuple',
        'product_tuple':product_tuple(licensed=licensed),
        'source_reviews':[source(kind) for kind in kinds],
        'compatibility':{
            'compatibility_record_ref':'controlled-compatibility:fixture',
            'assessed_at':'2026-09-17T10:00:00Z',
            'valid_until':'2026-12-31T23:59:59Z',
            'product_api_evidence_ref':'controlled-evidence:product-api',
            'provider_evidence_refs':['controlled-evidence:provider'],
            'hardware_evidence_ref':'controlled-evidence:hardware',
            'operation_coverage_ref':'controlled-evidence:operation-coverage',
            'feature_entitlement_evidence_refs':['controlled-evidence:entitlement'] if licensed else [],
            'exceptions':[],
        },
        'lifecycle':{
            'support_status':'SUPPORTED',
            'support_evidence_ref':'controlled-support:fixture',
            'reviewed_at':'2026-09-17T11:00:00Z',
            'review_by':'2026-12-31T23:59:59Z',
            'support_end_at':None,
            'vulnerability_owner_ref':'controlled-owner:vulnerability',
            'lifecycle_decision_ref':'controlled-decision:continue-supported',
        },
        'owners':{
            'platform_engineering_role':'Fixture platform engineering',
            'architecture_role':'Fixture architecture',
            'vulnerability_management_role':'Fixture vulnerability management',
        },
        'exclusions':['Synthetic unit-test provenance only'],
        'source_refs':[
            'docs/engineering/version-source-provenance-and-lifecycle-assurance.md',
            'docs/engineering/platform-realizations/7-implementation-tuple-and-decision-package.md',
        ],
    }


def index(*records):
    value=provenance.load()
    value['records']=list(records)
    return value


def intent(*,licensed=True):
    value=readiness.load(INTENT)
    value['product_tuple_id']='fixture-tuple'
    value['required_product_tuple']=product_tuple(licensed=licensed)
    return value


class ProvenanceRecordTests(unittest.TestCase):
    def test_current_index_is_valid_empty(self):
        self.assertEqual(provenance.validate(provenance.load(),as_of=AS_OF)['record_count'],0)

    def test_current_supported_record_is_valid(self):
        result=provenance.validate(index(record()),as_of=AS_OF)
        self.assertEqual(result['current_supported_count'],1)

    def test_source_edition_does_not_substitute_for_current_review(self):
        r=record()
        target=next(x for x in r['source_reviews'] if x['kind']=='PRODUCT_SUPPORT')
        target['review_state']='INHERITED_NOT_REVERIFIED'
        with self.assertRaises(ValueError):
            provenance.validate(index(r),as_of=AS_OF)

    def test_partial_access_does_not_satisfy_current_required_source(self):
        r=record()
        target=next(x for x in r['source_reviews'] if x['kind']=='API_REFERENCE')
        target['review_state']='PARTIAL_ACCESS'
        with self.assertRaises(ValueError):
            provenance.validate(index(r),as_of=AS_OF)

    def test_missing_release_notes_rejected_for_current_supported(self):
        r=record()
        r['source_reviews']=[x for x in r['source_reviews'] if x['kind']!='RELEASE_NOTES']
        with self.assertRaises(ValueError):
            provenance.validate(index(r),as_of=AS_OF)

    def test_licensed_features_require_entitlement_source_and_evidence(self):
        r=record()
        r['source_reviews']=[x for x in r['source_reviews'] if x['kind']!='FEATURE_ENTITLEMENT']
        with self.assertRaises(ValueError):
            provenance.validate(index(r),as_of=AS_OF)
        r=record()
        r['compatibility']['feature_entitlement_evidence_refs']=[]
        with self.assertRaises(ValueError):
            provenance.validate(index(r),as_of=AS_OF)

    def test_review_due_requires_expired_evidence(self):
        r=record('REVIEW_DUE')
        with self.assertRaises(ValueError):
            provenance.validate(index(r),as_of=AS_OF)
        target=next(x for x in r['source_reviews'] if x['kind']=='PRODUCT_SUPPORT')
        target['valid_until']='2026-09-18T21:59:59Z'
        result=provenance.validate(index(r),as_of=AS_OF)
        self.assertEqual(result['review_due_count'],1)

    def test_expired_compatibility_rejects_current_supported(self):
        r=record()
        r['compatibility']['valid_until']='2026-09-18T21:59:59Z'
        with self.assertRaises(ValueError):
            provenance.validate(index(r),as_of=AS_OF)

    def test_support_end_scheduled_requires_date(self):
        r=record()
        r['lifecycle']['support_status']='SUPPORT_END_SCHEDULED'
        with self.assertRaises(ValueError):
            provenance.validate(index(r),as_of=AS_OF)

    def test_past_support_end_requires_unsupported_state(self):
        r=record('UNSUPPORTED')
        r['lifecycle']['support_status']='SUPPORT_END_SCHEDULED'
        r['lifecycle']['support_end_at']='2026-09-18T21:59:59Z'
        result=provenance.validate(index(r),as_of=AS_OF)
        self.assertEqual(result['unsupported_count'],1)

    def test_unknown_support_cannot_be_current_supported(self):
        r=record()
        r['lifecycle']['support_status']='UNKNOWN'
        with self.assertRaises(ValueError):
            provenance.validate(index(r),as_of=AS_OF)

    def test_duplicate_exact_tuple_rejected(self):
        one=record()
        two=deepcopy(one)
        two['provenance_id']='PROV-NUTANIX-FIXTURE-02'
        with self.assertRaises(ValueError):
            provenance.validate(index(one,two),as_of=AS_OF)

    def test_cli_empty_index_grants_no_qualification_authority(self):
        run=subprocess.run([
            sys.executable,str(ROOT/'scripts/check_version_source_provenance.py'),
            '--as-of','2026-09-18T22:00:00Z',
        ],capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        out=json.loads(run.stdout)
        self.assertEqual(out['record_count'],0)
        for key in ('may_claim_native_qualification','may_select_site','may_reserve_capacity',
                    'may_allocate','may_apply','may_activate'):
            self.assertIs(out[key],False)


class ProvenanceReadinessTests(unittest.TestCase):
    def test_current_example_holds_without_provenance(self):
        result=readiness.evaluate(readiness.load(INTENT),index=provenance.load(),as_of=AS_OF)
        self.assertEqual(result['status'],readiness.HOLD_NONE)

    def test_current_supported_satisfies_only_provenance_prerequisite(self):
        result=readiness.evaluate(intent(),index=index(record()),as_of=AS_OF)
        self.assertEqual(result['status'],readiness.READY)
        self.assertIs(result['may_claim_native_qualification'],False)

    def test_review_due_holds(self):
        r=record('REVIEW_DUE')
        r['compatibility']['valid_until']='2026-09-18T21:59:59Z'
        self.assertEqual(readiness.evaluate(intent(),index=index(r),as_of=AS_OF)['status'],readiness.HOLD_REVIEW)

    def test_unsupported_holds(self):
        r=record('UNSUPPORTED')
        r['lifecycle']['support_status']='UNSUPPORTED'
        self.assertEqual(readiness.evaluate(intent(),index=index(r),as_of=AS_OF)['status'],readiness.HOLD_UNSUPPORTED)

    def test_uncertain_holds(self):
        self.assertEqual(readiness.evaluate(intent(),index=index(record('UNCERTAIN')),as_of=AS_OF)['status'],readiness.HOLD_UNCERTAIN)

    def test_exact_tuple_mismatch_holds(self):
        value=intent()
        value['required_product_tuple']['api_version']='2.0'
        self.assertEqual(readiness.evaluate(value,index=index(record()),as_of=AS_OF)['status'],readiness.HOLD_TUPLE)

    def test_caller_cannot_carry_production_authority(self):
        value=intent()
        value['production_authority']='APPROVED'
        with self.assertRaises(ValueError):
            readiness.evaluate(value,index=index(record()),as_of=AS_OF)

    def test_cli_can_assert_current_empty_hold(self):
        run=subprocess.run([
            sys.executable,str(ROOT/'scripts/check_version_source_readiness.py'),str(INTENT),
            '--as-of','2026-09-18T22:00:00Z','--expected-status',readiness.HOLD_NONE,
        ],capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        self.assertEqual(json.loads(run.stdout)['status'],readiness.HOLD_NONE)


if __name__=='__main__':
    unittest.main()
