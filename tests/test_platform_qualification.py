from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

from scripts import check_platform_capabilities as capabilities
from scripts import check_platform_qualification as q

ROOT = Path(__file__).resolve().parents[1]
AS_OF = datetime(2026, 9, 18, 16, 0, tzinfo=timezone.utc)


def record(platform='nutanix', tuple_id='fixture-tuple', caps=('network_domain','ipv4'),
           assurance=()):
    refs=[f'controlled-evidence:{platform}:{cap}:fixture' for cap in caps]
    return {
        'id':'QUAL-NUTANIX-FIXTURE-01',
        'state':'CURRENT_APPROVED',
        'platform':platform,
        'product_tuple_id':tuple_id,
        'product_tuple':{
            'product':'fixture-product',
            'product_version':'1.0',
            'api':'fixture-api',
            'api_version':'1.0',
            'automation_providers':['fixture/provider = 1.0'],
            'hardware_profile_ref':'controlled-record:fixture-hardware',
            'feature_licenses':['fixture-feature-license']
        },
        'assurance_profiles':list(assurance),
        'qualified_capabilities':list(caps),
        'applicable_test_sets':['CT-FIXTURE'],
        'tested_limits':[{
            'name':'fixture-scale',
            'observed_bound':'10',
            'unit':'fixture-units',
            'evidence_ref':refs[0]
        }],
        'evidence':[{
            'ref':ref,
            'sha256':hashlib.sha256(ref.encode()).hexdigest(),
            'observed_at':'2026-09-17T10:00:00Z',
            'expires_at':'2026-12-31T23:59:59Z',
            'test_set':'CT-FIXTURE'
        } for ref in refs],
        'approval':{
            'authority_role':'Fixture security authority',
            'decision_ref':'controlled-decision:fixture-qualification',
            'approved_at':'2026-09-17T12:00:00Z',
            'expires_at':'2026-12-31T23:59:59Z'
        },
        'owners':{
            'platform_engineering_role':'Fixture platform engineering',
            'security_authority_role':'Fixture security authority'
        },
        'exclusions':['Synthetic unit-test record only'],
        'source_refs':[
            'docs/engineering/platform-native-qualification.md',
            'docs/engineering/platform-capability-registry.md'
        ]
    }


class QualificationIndexTests(unittest.TestCase):
    def setUp(self):
        self.index=q.load()

    def test_current_index_is_valid_and_empty(self):
        result=q.validate(self.index,as_of=AS_OF)
        self.assertEqual(result['current_records'],0)
        self.assertEqual(result['qualified_capability_claims'],0)

    def test_current_cli_reports_no_native_records(self):
        run=subprocess.run(
            [sys.executable,str(ROOT/'scripts/check_platform_qualification.py'),
             '--as-of','2026-09-18T16:00:00Z'],
            capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        result=json.loads(run.stdout)
        self.assertEqual(result['current_records'],0)
        for key in ('may_select_site','may_reserve_capacity','may_allocate','may_apply','may_activate'):
            self.assertIs(result[key],False)

    def test_complete_current_record_is_valid(self):
        self.index['records']=[record()]
        result=q.validate(self.index,as_of=AS_OF)
        self.assertEqual(result['current_records'],1)
        self.assertEqual(result['qualified_capability_claims'],2)

    def test_example_not_approved_state_is_rejected(self):
        r=record();r['state']='EXAMPLE_NOT_APPROVED';self.index['records']=[r]
        with self.assertRaises(ValueError):q.validate(self.index,as_of=AS_OF)

    def test_expired_approval_is_rejected(self):
        r=record();r['approval']['expires_at']='2026-09-18T15:59:59Z';self.index['records']=[r]
        with self.assertRaises(ValueError):q.validate(self.index,as_of=AS_OF)

    def test_expired_evidence_is_rejected(self):
        r=record();r['evidence'][0]['expires_at']='2026-09-18T15:59:59Z';self.index['records']=[r]
        with self.assertRaises(ValueError):q.validate(self.index,as_of=AS_OF)

    def test_approval_cannot_predate_required_evidence(self):
        r=record();r['approval']['approved_at']='2026-09-17T09:00:00Z';self.index['records']=[r]
        with self.assertRaises(ValueError):q.validate(self.index,as_of=AS_OF)

    def test_missing_tested_limits_rejected(self):
        r=record();r['tested_limits']=[];self.index['records']=[r]
        with self.assertRaises(ValueError):q.validate(self.index,as_of=AS_OF)

    def test_limit_must_bind_existing_evidence(self):
        r=record();r['tested_limits'][0]['evidence_ref']='controlled-evidence:missing';self.index['records']=[r]
        with self.assertRaises(ValueError):q.validate(self.index,as_of=AS_OF)

    def test_evidence_test_set_must_be_applicable(self):
        r=record();r['evidence'][0]['test_set']='CT-UNREVIEWED';self.index['records']=[r]
        with self.assertRaises(ValueError):q.validate(self.index,as_of=AS_OF)

    def test_unknown_capability_rejected(self):
        r=record();r['qualified_capabilities'].append('vendor_magic');self.index['records']=[r]
        with self.assertRaises(ValueError):q.validate(self.index,as_of=AS_OF)

    def test_missing_source_reference_rejected(self):
        r=record();r['source_refs'].append('docs/missing.md');self.index['records']=[r]
        with self.assertRaises(ValueError):q.validate(self.index,as_of=AS_OF)

    def test_duplicate_record_id_rejected(self):
        r=record();self.index['records']=[r,deepcopy(r)]
        with self.assertRaises(ValueError):q.validate(self.index,as_of=AS_OF)

    def test_registry_native_claim_requires_matching_current_record(self):
        registry=capabilities.load()
        p=registry['profiles']['nutanix'];p['product_tuple']='fixture-tuple'
        p['capabilities']['network_domain']['qualification']='NATIVE_QUALIFIED'
        p['capabilities']['network_domain']['native_evidence_refs']=[
            'controlled-evidence:nutanix:network_domain:fixture']
        with self.assertRaises(ValueError):
            capabilities.validate(registry,qualification_index=self.index,as_of=AS_OF)
        self.index['records']=[record(caps=('network_domain',))]
        result=capabilities.validate(registry,qualification_index=self.index,as_of=AS_OF)
        self.assertEqual(result['native_qualified_claims'],1)

    def test_registry_evidence_must_be_inside_dossier(self):
        registry=capabilities.load();self.index['records']=[record(caps=('network_domain',))]
        p=registry['profiles']['nutanix'];p['product_tuple']='fixture-tuple'
        p['capabilities']['network_domain']['qualification']='NATIVE_QUALIFIED'
        p['capabilities']['network_domain']['native_evidence_refs']=['controlled-evidence:other']
        with self.assertRaises(ValueError):
            capabilities.validate(registry,qualification_index=self.index,as_of=AS_OF)

    def test_registry_tuple_must_match_dossier(self):
        registry=capabilities.load();self.index['records']=[record(caps=('network_domain',))]
        p=registry['profiles']['nutanix'];p['product_tuple']='different-tuple'
        p['capabilities']['network_domain']['qualification']='NATIVE_QUALIFIED'
        p['capabilities']['network_domain']['native_evidence_refs']=[
            'controlled-evidence:nutanix:network_domain:fixture']
        with self.assertRaises(ValueError):
            capabilities.validate(registry,qualification_index=self.index,as_of=AS_OF)

    def test_assurance_profile_must_be_dossier_qualified(self):
        registry=capabilities.load();self.index['records']=[record(caps=('network_domain',))]
        p=registry['profiles']['nutanix'];p['product_tuple']='fixture-tuple'
        p['assurance_profiles']=['PROTECTED-B-FIXTURE']
        with self.assertRaises(ValueError):
            capabilities.validate(registry,qualification_index=self.index,as_of=AS_OF)


if __name__=='__main__':
    unittest.main()
