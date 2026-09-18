"""Reservation record and preflight tests; no live reservation-system mutation."""
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
from scripts import check_reservation_preflight as preflight
from scripts import check_reservation_records as records
from scripts import check_site_service_capacity as capacity
from scripts import check_site_service_eligibility as sitecheck
from scripts import check_version_source_provenance as provenance

ROOT=Path(__file__).resolve().parents[1]
AS_OF=datetime(2026,9,18,18,0,tzinfo=timezone.utc)
INTENT=ROOT/'examples/reservation_intent.json.example'
CAPREQ=ROOT/'examples/site_service_capacity_request.json.example'


def provenance_record():
    kinds=sorted(provenance.BASE_REQUIRED_KINDS)
    return {
        'provenance_id':'PROV-NUTANIX-SYNTHETIC-01',
        'generation':1,
        'state':'CURRENT_SUPPORTED',
        'platform':'nutanix',
        'product_tuple_id':'nutanix-res-fixture',
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
    ref='controlled-evidence:nutanix:fixture'
    return {
        'id':'QUAL-NUTANIX-RES-FIXTURE-01','state':'CURRENT_APPROVED',
        'platform':'nutanix','product_tuple_id':'nutanix-res-fixture',
        'product_tuple':{
            'product':'fixture-product','product_version':'1.0','api':'fixture-api',
            'api_version':'1.0','automation_providers':['fixture/provider = 1.0'],
            'hardware_profile_ref':'controlled-record:fixture-hardware','feature_licenses':[]},
        'assurance_profiles':[],'qualified_capabilities':['network_domain'],
        'applicable_test_sets':['CT-FIXTURE'],
        'tested_limits':[{'name':'fixture','observed_bound':'1','unit':'fixture','evidence_ref':ref}],
        'evidence':[{'ref':ref,'sha256':hashlib.sha256(ref.encode()).hexdigest(),
                     'observed_at':'2026-09-17T10:00:00Z','expires_at':'2026-12-31T23:59:59Z',
                     'test_set':'CT-FIXTURE'}],
        'approval':{'authority_role':'Fixture security authority',
                    'decision_ref':'controlled-decision:fixture',
                    'approved_at':'2026-09-17T12:00:00Z','expires_at':'2026-12-31T23:59:59Z'},
        'owners':{'platform_engineering_role':'Fixture platform owner',
                  'security_authority_role':'Fixture security authority'},
        'exclusions':['Synthetic test only'],
        'source_refs':['docs/engineering/platform-native-qualification.md']
    }


def qindex():
    x=qualification.load();x['records']=[qrecord()];return x


def cap_request():
    r=sitecheck.load_request(CAPREQ)
    r['candidate_platforms']=['nutanix']
    return r


def cap_record():
    req=cap_request()
    dims=[]
    for demand in req['capacity_demands']:
        dims.append({
            'id':demand['id'],'unit':demand['unit'],
            'measured_surviving_capacity':'10','operational_reserve':'1',
            'existing_commitment':'1','unavailable_capacity':'0',
            'procured':'10','received':'10','staged':'10','commissioned':'10',
            'reserved':'1','consumed':'1',
            'evidence_ref':'controlled-capacity:'+demand['id']
        })
    return {
        'id':'ENV-FIXTURE-01','state':'CURRENT_COMMISSIONED',
        'site_id':'site-fixture','cell_id':'cell-fixture','service_class_id':'sc-fixture',
        'platform':'nutanix','product_tuple_id':'nutanix-res-fixture',
        'qualification_record_id':'QUAL-NUTANIX-RES-FIXTURE-01',
        'assurance_profiles':[],'profile_refs':deepcopy(req['required_profile_refs']),
        'failure_model':{'id':'FAIL-FIXTURE','description':'Synthetic failure model',
                         'evidence_ref':'controlled-failure:fixture'},
        'capacity_measured_at':'2026-09-18T12:00:00Z',
        'capacity_expires_at':'2026-09-19T12:00:00Z',
        'dimensions':dims,
        'owners':{'capacity_owner_role':'Fixture capacity owner',
                  'platform_owner_role':'Fixture platform owner',
                  'service_owner_role':'Fixture service owner'},
        'source_refs':['docs/engineering/site-service-capacity-eligibility.md']
    }


def cap_index():
    x=capacity.load();x['records']=[cap_record()];return x


def intent():
    x=preflight.load(INTENT)
    x['spec']['envelope_id']='ENV-FIXTURE-01'
    return x


def normalized(i):
    req=sitecheck.load_request(ROOT/i['spec']['capacity_request_ref'])
    return preflight.normalized_spec(i,req,as_of=AS_OF)


def reservation_record(i,state='HELD',dependency_state='NOT_STARTED'):
    spec=normalized(i)
    dep_ref=None if dependency_state in ('NOT_STARTED','UNCERTAIN','RELEASED') else 'external-reservation:fixture'
    deps=[{
        'kind':d['kind'],'owner_role':d['owner_role'],'operation_id':d['operation_id'],
        'reservation_ref':dep_ref,'state':dependency_state
    } for d in spec['dependency_handoffs']]
    return {
        'reservation_id':spec['reservation_id'],'operation_id':spec['operation_id'],
        'generation':spec['generation'],'state':state,'request_id':spec['request_id'],
        'wsd_engineering_ref':spec['wsd_engineering_ref'],'envelope_id':spec['envelope_id'],
        'spec_sha256':records.canonical_digest(spec),
        'authoritative_system':{'system_ref':'external-reservation-system:fixture',
                                'record_ref':'reservation-record:fixture','record_version':1},
        'created_at':'2026-09-18T17:00:00Z','expires_at':spec['expires_at'],
        'last_observed_at':'2026-09-18T17:30:00Z',
        'owners':deepcopy(spec['owners']),'resources':deepcopy(spec['resources']),
        'dependency_handoffs':deps,
        'evidence_refs':['controlled-evidence:reservation-fixture'],
        'source_refs':['docs/engineering/reservation-preflight-and-reconciliation.md']
    }


def journal(*items):
    x=records.load();x['records']=list(items);return x


class ReservationRecordTests(unittest.TestCase):
    def test_current_export_index_is_valid_and_empty(self):
        result=records.validate(records.load(),as_of=AS_OF)
        self.assertEqual(result['record_count'],0)

    def test_current_cli_keeps_all_mutation_authority_false(self):
        run=subprocess.run([
            sys.executable,str(ROOT/'scripts/check_reservation_records.py'),
            '--as-of','2026-09-18T18:00:00Z'],
            capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        result=json.loads(run.stdout)
        self.assertEqual(result['record_count'],0)
        for key in ('may_create_reservation','may_extend_reservation','may_consume_reservation',
                    'may_release_reservation','may_allocate_address','may_apply','may_activate'):
            self.assertIs(result[key],False)

    def test_confirmed_held_record_is_valid(self):
        result=records.validate(journal(reservation_record(intent())),as_of=AS_OF)
        self.assertEqual(result['held_count'],1)
        self.assertEqual(result['unresolved_count'],0)

    def test_expired_held_record_requires_reconciliation(self):
        r=reservation_record(intent());r['expires_at']='2026-09-18T17:59:59Z'
        with self.assertRaises(ValueError):records.validate(journal(r),as_of=AS_OF)

    def test_duplicate_operation_identity_rejected(self):
        one=reservation_record(intent());two=deepcopy(one)
        two['reservation_id']='EXAMPLE-RESERVATION-02'
        with self.assertRaises(ValueError):records.validate(journal(one,two),as_of=AS_OF)

    def test_reserved_dependency_requires_authoritative_ref(self):
        r=reservation_record(intent(),dependency_state='RESERVED')
        r['dependency_handoffs'][0]['reservation_ref']=None
        with self.assertRaises(ValueError):records.validate(journal(r),as_of=AS_OF)

    def test_uncertain_dependency_is_preserved_as_unresolved(self):
        r=reservation_record(intent(),dependency_state='UNCERTAIN')
        result=records.validate(journal(r),as_of=AS_OF)
        self.assertEqual(result['unresolved_count'],1)


class ReservationPreflightTests(unittest.TestCase):
    def evaluate(self,i=None,j=None):
        return preflight.evaluate(
            i or intent(),capacity_index=cap_index(),
            reservation_index=j or records.load(),qindex=qindex(),
            provenance_index=provenance_index(),as_of=AS_OF)

    def test_current_repository_example_holds_without_envelope(self):
        result=preflight.evaluate(
            preflight.load(INTENT),capacity_index=capacity.load(),
            reservation_index=records.load(),qindex=qualification.load(),as_of=AS_OF)
        self.assertEqual(result['status'],preflight.HOLD_ENVELOPE)

    def test_eligible_spec_is_ready_only_for_external_create(self):
        result=self.evaluate()
        self.assertEqual(result['status'],preflight.READY)
        for key in ('may_create_reservation','may_extend_reservation','may_consume_reservation',
                    'may_release_reservation','may_allocate_address','may_apply','may_activate'):
            self.assertIs(result[key],False)

    def test_same_operation_same_spec_is_idempotent_existing_hold(self):
        i=intent();result=self.evaluate(i,journal(reservation_record(i)))
        self.assertEqual(result['status'],preflight.EXISTING_HELD)

    def test_same_operation_changed_generation_is_conflict(self):
        i=intent();r=reservation_record(i);i['spec']['generation']=2
        result=self.evaluate(i,journal(r))
        self.assertEqual(result['status'],preflight.HOLD_CONFLICT)

    def test_same_reservation_different_operation_is_conflict(self):
        i=intent();r=reservation_record(i);i['spec']['operation_id']='EXAMPLE-RESERVATION-OP-02'
        result=self.evaluate(i,journal(r))
        self.assertEqual(result['status'],preflight.HOLD_CONFLICT)

    def test_uncertain_reservation_stops_retry(self):
        i=intent();r=reservation_record(i,state='UNCERTAIN')
        result=self.evaluate(i,journal(r))
        self.assertEqual(result['status'],preflight.HOLD_UNCERTAIN)

    def test_uncertain_dependency_stops_retry(self):
        i=intent();r=reservation_record(i,dependency_state='UNCERTAIN')
        result=self.evaluate(i,journal(r))
        self.assertEqual(result['status'],preflight.HOLD_UNCERTAIN)

    def test_released_reservation_requires_new_operation_identity(self):
        i=intent();r=reservation_record(i,state='RELEASED')
        result=self.evaluate(i,journal(r))
        self.assertEqual(result['status'],preflight.HOLD_TERMINAL)

    def test_consumed_reservation_is_not_recreated(self):
        i=intent();r=reservation_record(i,state='CONSUMED')
        result=self.evaluate(i,journal(r))
        self.assertEqual(result['status'],preflight.EXISTING_CONSUMED)

    def test_resource_quantity_must_match_capacity_request_exactly(self):
        i=intent();i['spec']['resources'][0]['quantity']='2'
        with self.assertRaises(ValueError):self.evaluate(i)

    def test_production_authority_cannot_be_carried(self):
        i=intent();i['production_authority']='APPROVED'
        with self.assertRaises(ValueError):self.evaluate(i)

    def test_cli_can_assert_current_expected_hold(self):
        run=subprocess.run([
            sys.executable,str(ROOT/'scripts/check_reservation_preflight.py'),str(INTENT),
            '--as-of','2026-09-18T18:00:00Z',
            '--expected-status',preflight.HOLD_ENVELOPE],
            capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        self.assertEqual(json.loads(run.stdout)['status'],preflight.HOLD_ENVELOPE)


if __name__=='__main__':unittest.main()
