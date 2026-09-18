"""Site/service-class capacity evidence tests; no real reservation or placement."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

from scripts import check_platform_qualification as qualification
from scripts import check_site_service_capacity as capacity
from scripts import check_site_service_eligibility as eligibility
from scripts import check_version_source_provenance as provenance

ROOT=Path(__file__).resolve().parents[1]
AS_OF=datetime(2026,9,18,18,0,tzinfo=timezone.utc)
EXAMPLE=ROOT/'examples/site_service_capacity_request.json.example'


def provenance_record():
    kinds=sorted(provenance.BASE_REQUIRED_KINDS)
    return {
        'provenance_id':'PROV-NUTANIX-SYNTHETIC-01',
        'generation':1,
        'state':'CURRENT_SUPPORTED',
        'platform':'nutanix',
        'product_tuple_id':'nutanix-fixture-tuple',
        'product_tuple':{
            'product':'fixture-product','product_version':'1.0','api':'fixture-api',
            'api_version':'1.0','automation_providers':['fixture/provider = 1.0'],
            'hardware_profile_ref':'controlled-record:fixture-hardware','feature_licenses':[]},
        'source_reviews':[{
            'source_id':f'SRC-{kind}','kind':kind,'edition':f'fixture-{kind.lower()}',
            'review_state':'CURRENT_REVIEWED','reviewed_at':'2026-09-17T08:00:00Z',
            'valid_until':'2026-12-31T23:59:59Z',
            'evidence_ref':f'controlled-source-evidence:{kind.lower()}',
            'limitation':'Synthetic unit-test source review only.'
        } for kind in kinds],
        'compatibility':{
            'compatibility_record_ref':'controlled-compatibility:fixture',
            'assessed_at':'2026-09-17T10:00:00Z','valid_until':'2026-12-31T23:59:59Z',
            'product_api_evidence_ref':'controlled-evidence:product-api',
            'provider_evidence_refs':['controlled-evidence:provider'],
            'hardware_evidence_ref':'controlled-evidence:hardware',
            'operation_coverage_ref':'controlled-evidence:operation-coverage',
            'feature_entitlement_evidence_refs':[],'exceptions':[]},
        'lifecycle':{
            'support_status':'SUPPORTED','support_evidence_ref':'controlled-support:fixture',
            'reviewed_at':'2026-09-17T11:00:00Z','review_by':'2026-12-31T23:59:59Z',
            'support_end_at':None,'vulnerability_owner_ref':'controlled-owner:vulnerability',
            'lifecycle_decision_ref':'controlled-decision:continue-supported'},
        'owners':{
            'platform_engineering_role':'Fixture platform engineering',
            'architecture_role':'Fixture architecture',
            'vulnerability_management_role':'Fixture vulnerability management'},
        'exclusions':['Synthetic unit-test provenance only'],
        'source_refs':[
            'docs/engineering/version-source-provenance-and-lifecycle-assurance.md',
            'docs/engineering/platform-realizations/7-implementation-tuple-and-decision-package.md']
    }


def provenance_index():
    value=provenance.load()
    value['records']=[provenance_record()]
    return value


def qrecord():
    refs=['controlled-evidence:nutanix:network_domain','controlled-evidence:nutanix:ipv4']
    return {
        'id':'QUAL-NUTANIX-FIXTURE-01','state':'CURRENT_APPROVED','platform':'nutanix',
        'product_tuple_id':'nutanix-fixture-tuple',
        'product_tuple':{
            'product':'fixture-product','product_version':'1.0','api':'fixture-api',
            'api_version':'1.0','automation_providers':['fixture/provider = 1.0'],
            'hardware_profile_ref':'controlled-record:fixture-hardware','feature_licenses':[]},
        'assurance_profiles':['PROTECTED-B-FIXTURE'],
        'qualified_capabilities':['network_domain','ipv4'],
        'applicable_test_sets':['CT-FIXTURE'],
        'tested_limits':[{'name':'fixture-limit','observed_bound':'1','unit':'fixture',
                          'evidence_ref':refs[0]}],
        'evidence':[{'ref':ref,'sha256':hashlib.sha256(ref.encode()).hexdigest(),
                     'observed_at':'2026-09-17T10:00:00Z','expires_at':'2026-12-31T23:59:59Z',
                     'test_set':'CT-FIXTURE'} for ref in refs],
        'approval':{'authority_role':'Fixture security authority',
                    'decision_ref':'controlled-decision:fixture',
                    'approved_at':'2026-09-17T12:00:00Z',
                    'expires_at':'2026-12-31T23:59:59Z'},
        'owners':{'platform_engineering_role':'Fixture platform owner',
                  'security_authority_role':'Fixture security authority'},
        'exclusions':['Synthetic test only'],
        'source_refs':['docs/engineering/platform-native-qualification.md']
    }


def qindex():
    result=qualification.load()
    result['records']=[qrecord()]
    return result


def profiles():
    return {key:f'controlled-profile:fixture-{key}' for key in capacity.PROFILE_KEYS}


def dimension(ident,unit,surviving='100',reserve='10',commitment='20',unavailable='5',
              procured='140',received='130',staged='120',commissioned='110',
              reserved='10',consumed='20'):
    return {
        'id':ident,'unit':unit,'measured_surviving_capacity':surviving,
        'operational_reserve':reserve,'existing_commitment':commitment,
        'unavailable_capacity':unavailable,'procured':procured,'received':received,
        'staged':staged,'commissioned':commissioned,'reserved':reserved,
        'consumed':consumed,'evidence_ref':f'controlled-capacity:{ident}:fixture'
    }


def site_record():
    return {
        'id':'SITE-CELL-SC-FIXTURE-01','state':'CURRENT_COMMISSIONED',
        'site_id':'site-fixture','cell_id':'cell-fixture','service_class_id':'sc-fixture',
        'platform':'nutanix','product_tuple_id':'nutanix-fixture-tuple',
        'qualification_record_id':'QUAL-NUTANIX-FIXTURE-01',
        'assurance_profiles':['PROTECTED-B-FIXTURE'],
        'profile_refs':profiles(),
        'failure_model':{'id':'FAIL-HOST-FIXTURE','description':'Synthetic one-host failure model',
                         'evidence_ref':'controlled-failure:fixture'},
        'capacity_measured_at':'2026-09-18T12:00:00Z',
        'capacity_expires_at':'2026-09-19T12:00:00Z',
        'dimensions':[
            dimension('memory_gib','GiB'),
            dimension('storage_gib','GiB',surviving='200',reserve='20',commitment='40',unavailable='10',
                      procured='260',received='250',staged='240',commissioned='220',
                      reserved='30',consumed='40'),
            dimension('edge_sessions','sessions',surviving='10000',reserve='2000',
                      commitment='5000',unavailable='0',procured='12000',received='12000',
                      staged='12000',commissioned='10000',reserved='1000',consumed='5000'),
            dimension('attachment_slots','slots',surviving='24',reserve='2',
                      commitment='16',unavailable='2',procured='32',received='32',
                      staged='28',commissioned='24',reserved='2',consumed='16')
        ],
        'owners':{'capacity_owner_role':'Fixture capacity owner',
                  'platform_owner_role':'Fixture platform owner',
                  'service_owner_role':'Fixture service owner'},
        'source_refs':[
            'docs/architecture/reference/4-hosting-cells-resource-pools-and-failure-boundaries.md',
            'docs/assurance/site-qualification/3-capacity-service-envelopes-and-growth-triggers.md'
        ]
    }


def index():
    result=capacity.load()
    result['records']=[site_record()]
    return result


def request():
    r=eligibility.load_request(EXAMPLE)
    r['candidate_platforms']=['nutanix']
    r['required_assurance_profile']='PROTECTED-B-FIXTURE'
    r['required_profile_refs']=profiles()
    r['capacity_demands']=[
        {'id':'memory_gib','unit':'GiB','quantity':'10','quota_remaining':'50'},
        {'id':'storage_gib','unit':'GiB','quantity':'20','quota_remaining':'50'},
        {'id':'edge_sessions','unit':'sessions','quantity':'1000','quota_remaining':'2000'},
        {'id':'attachment_slots','unit':'slots','quantity':'2','quota_remaining':'4'}
    ]
    return r


class SiteCapacityIndexTests(unittest.TestCase):
    def test_current_index_is_valid_and_empty(self):
        result=capacity.validate(capacity.load(),qindex=qualification.load(),as_of=AS_OF)
        self.assertEqual(result['current_service_envelopes'],0)

    def test_complete_synthetic_envelope_is_valid(self):
        result=capacity.validate(index(),qindex=qindex(),provenance_index=provenance_index(),as_of=AS_OF)
        self.assertEqual(result['current_service_envelopes'],1)
        dims={x['id']:x for x in result['records'][0]['dimensions']}
        self.assertEqual(dims['memory_gib']['available_after_failure_and_reserve'],'65')
        self.assertEqual(dims['attachment_slots']['available_after_failure_and_reserve'],'4')

    def test_reserved_and_consumed_are_not_summed_for_admission(self):
        r=site_record();d=r['dimensions'][0]
        d.update(existing_commitment='20',reserved='20',consumed='20')
        idx=capacity.load();idx['records']=[r]
        result=capacity.validate(idx,qindex=qindex(),provenance_index=provenance_index(),as_of=AS_OF)
        dim=next(x for x in result['records'][0]['dimensions'] if x['id']=='memory_gib')
        self.assertEqual(dim['available_after_failure_and_reserve'],'65')

    def test_existing_commitment_must_cover_reporting_observations(self):
        r=site_record();r['dimensions'][0]['existing_commitment']='9'
        idx=capacity.load();idx['records']=[r]
        with self.assertRaises(ValueError):capacity.validate(idx,qindex=qindex(),provenance_index=provenance_index(),as_of=AS_OF)

    def test_lifecycle_inventory_states_do_not_gain_invented_monotonic_semantics(self):
        r=site_record();r['dimensions'][0].update(received='80',staged='120',commissioned='90')
        idx=capacity.load();idx['records']=[r]
        result=capacity.validate(idx,qindex=qindex(),provenance_index=provenance_index(),as_of=AS_OF)
        self.assertEqual(result['current_service_envelopes'],1)

    def test_surviving_measurement_is_not_compared_to_generic_commissioned_count(self):
        r=site_record();r['dimensions'][0].update(measured_surviving_capacity='111',commissioned='90')
        idx=capacity.load();idx['records']=[r]
        result=capacity.validate(idx,qindex=qindex(),provenance_index=provenance_index(),as_of=AS_OF)
        self.assertEqual(result['current_service_envelopes'],1)

    def test_overcommitted_dimension_is_rejected(self):
        r=site_record();r['dimensions'][0].update(
            measured_surviving_capacity='30',operational_reserve='10',
            existing_commitment='20',unavailable_capacity='1')
        idx=capacity.load();idx['records']=[r]
        with self.assertRaises(ValueError):capacity.validate(idx,qindex=qindex(),provenance_index=provenance_index(),as_of=AS_OF)

    def test_expired_measurement_is_rejected(self):
        r=site_record();r['capacity_expires_at']='2026-09-18T17:59:59Z'
        idx=capacity.load();idx['records']=[r]
        with self.assertRaises(ValueError):capacity.validate(idx,qindex=qindex(),provenance_index=provenance_index(),as_of=AS_OF)

    def test_wrong_qualification_record_is_rejected(self):
        r=site_record();r['qualification_record_id']='QUAL-OTHER'
        idx=capacity.load();idx['records']=[r]
        with self.assertRaises(ValueError):capacity.validate(idx,qindex=qindex(),provenance_index=provenance_index(),as_of=AS_OF)

    def test_assurance_cannot_exceed_qualification_scope(self):
        r=site_record();r['assurance_profiles'].append('UNQUALIFIED')
        idx=capacity.load();idx['records']=[r]
        with self.assertRaises(ValueError):capacity.validate(idx,qindex=qindex(),provenance_index=provenance_index(),as_of=AS_OF)

    def test_duplicate_active_envelope_rejected(self):
        idx=capacity.load();idx['records']=[site_record(),deepcopy(site_record())]
        idx['records'][1]['id']='SITE-CELL-SC-FIXTURE-02'
        with self.assertRaises(ValueError):capacity.validate(idx,qindex=qindex(),provenance_index=provenance_index(),as_of=AS_OF)


class SiteEligibilityTests(unittest.TestCase):
    def test_current_empty_inventory_holds(self):
        result=eligibility.evaluate(eligibility.load_request(EXAMPLE),capacity.load(),
                                    qindex=qualification.load(),as_of=AS_OF)
        self.assertEqual(result['status'],eligibility.HOLD)
        self.assertEqual(result['matching_envelopes'],[])

    def test_complete_envelope_matches_without_reservation(self):
        result=eligibility.evaluate(request(),index(),qindex=qindex(),provenance_index=provenance_index(),as_of=AS_OF)
        self.assertEqual(result['status'],eligibility.MATCH)
        self.assertEqual(result['matching_envelopes'],['SITE-CELL-SC-FIXTURE-01'])
        for key in ('may_select_site','may_reserve_capacity','may_allocate',
                    'may_allocate_address','may_apply','may_activate'):
            self.assertIs(result[key],False)
        self.assertNotIn('reservation_id',result)

    def test_one_capacity_bottleneck_blocks_whole_envelope(self):
        r=request();next(x for x in r['capacity_demands'] if x['id']=='edge_sessions')['quantity']='4000'
        result=eligibility.evaluate(r,index(),qindex=qindex(),provenance_index=provenance_index(),as_of=AS_OF)
        self.assertEqual(result['status'],eligibility.HOLD)
        self.assertIn('surviving_capacity:edge_sessions',result['evaluations'][0]['blockers'])

    def test_quota_bottleneck_blocks_even_when_capacity_fits(self):
        r=request();d=next(x for x in r['capacity_demands'] if x['id']=='memory_gib')
        d['quota_remaining']='5'
        result=eligibility.evaluate(r,index(),qindex=qindex(),provenance_index=provenance_index(),as_of=AS_OF)
        self.assertEqual(result['status'],eligibility.HOLD)
        self.assertIn('quota:memory_gib',result['evaluations'][0]['blockers'])

    def test_missing_dimension_blocks(self):
        idx=index();idx['records'][0]['dimensions']=[
            d for d in idx['records'][0]['dimensions'] if d['id']!='attachment_slots']
        result=eligibility.evaluate(request(),idx,qindex=qindex(),provenance_index=provenance_index(),as_of=AS_OF)
        self.assertIn('capacity_dimension:attachment_slots:missing',result['evaluations'][0]['blockers'])

    def test_unit_mismatch_blocks(self):
        r=request();r['capacity_demands'][0]['unit']='MiB'
        result=eligibility.evaluate(r,index(),qindex=qindex(),provenance_index=provenance_index(),as_of=AS_OF)
        self.assertIn('capacity_dimension:memory_gib:unit',result['evaluations'][0]['blockers'])

    def test_profile_mismatch_blocks(self):
        r=request();r['required_profile_refs']['storage']='controlled-profile:different-storage'
        result=eligibility.evaluate(r,index(),qindex=qindex(),provenance_index=provenance_index(),as_of=AS_OF)
        self.assertIn('profile:storage',result['evaluations'][0]['blockers'])

    def test_assurance_mismatch_blocks(self):
        r=request();r['required_assurance_profile']='OTHER'
        result=eligibility.evaluate(r,index(),qindex=qindex(),provenance_index=provenance_index(),as_of=AS_OF)
        self.assertIn('assurance_profile:OTHER',result['evaluations'][0]['blockers'])

    def test_candidate_site_filter_does_not_expand_scope(self):
        r=request();r['candidate_sites']=['other-site']
        result=eligibility.evaluate(r,index(),qindex=qindex(),provenance_index=provenance_index(),as_of=AS_OF)
        self.assertEqual(result['evaluations'],[])
        self.assertEqual(result['status'],eligibility.HOLD)

    def test_cli_current_example_asserts_expected_hold(self):
        run=subprocess.run([
            sys.executable,str(ROOT/'scripts/check_site_service_eligibility.py'),str(EXAMPLE),
            '--expected-status',eligibility.HOLD],capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        self.assertEqual(json.loads(run.stdout)['status'],eligibility.HOLD)

    def test_cli_hold_is_nonzero_without_expected_status(self):
        run=subprocess.run([
            sys.executable,str(ROOT/'scripts/check_site_service_eligibility.py'),str(EXAMPLE)],
            capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,2)
        self.assertEqual(json.loads(run.stdout)['status'],eligibility.HOLD)


if __name__=='__main__':
    unittest.main()
