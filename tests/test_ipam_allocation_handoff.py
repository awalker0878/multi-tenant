"""Authoritative IPAM evidence/preflight tests; no real IPAM mutation or address value."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import unittest

from scripts import check_ipam_allocation_preflight as preflight
from scripts import check_ipam_allocation_records as ipam
from scripts import check_reservation_preflight as reservation_preflight
from scripts import check_reservation_records as reservation_records
from scripts import check_site_service_eligibility as sitecheck

ROOT=Path(__file__).resolve().parents[1]
AS_OF=datetime(2026,9,18,18,0,tzinfo=timezone.utc)
INTENT=ROOT/'examples/ipam_allocation_intent.json.example'
RES_INTENT=ROOT/'examples/reservation_intent.json.example'


def cleanup(status='NOT_STARTED'):
    result={}
    for key in ipam.CLEANUP_KEYS:
        if status=='NOT_STARTED':
            result[key]={'status':'NOT_STARTED','evidence_ref':None,'observed_at':None}
        elif status=='COMPLETE':
            result[key]={'status':'COMPLETE','evidence_ref':f'controlled-cleanup:{key}:fixture',
                         'observed_at':'2026-09-18T17:35:00Z'}
        else:
            raise ValueError(status)
    return result


def parent_spec():
    parent=reservation_preflight.load(RES_INTENT)
    cap_ref=parent['spec']['capacity_request_ref']
    cap=sitecheck.load_request(ROOT/cap_ref)
    return reservation_preflight.normalized_spec(parent,cap,as_of=AS_OF)


def parent_record(state='HELD'):
    spec=parent_spec()
    deps=[{
        'kind':d['kind'],'owner_role':d['owner_role'],'operation_id':d['operation_id'],
        'reservation_ref':None,'state':'NOT_STARTED'
    } for d in spec['dependency_handoffs']]
    return {
        'reservation_id':spec['reservation_id'],'operation_id':spec['operation_id'],
        'generation':spec['generation'],'state':state,'request_id':spec['request_id'],
        'wsd_engineering_ref':spec['wsd_engineering_ref'],'envelope_id':spec['envelope_id'],
        'spec_sha256':reservation_records.canonical_digest(spec),
        'authoritative_system':{'system_ref':'external-reservation-system:fixture',
                                'record_ref':'reservation-record:fixture','record_version':1},
        'created_at':'2026-09-18T17:00:00Z','expires_at':spec['expires_at'],
        'last_observed_at':'2026-09-18T17:30:00Z',
        'owners':deepcopy(spec['owners']),'resources':deepcopy(spec['resources']),
        'dependency_handoffs':deps,
        'evidence_refs':['controlled-evidence:reservation-fixture'],
        'source_refs':['docs/engineering/reservation-preflight-and-reconciliation.md']
    }


def reservation_index(state='HELD'):
    x=reservation_records.load()
    x['records']=[parent_record(state)]
    return x


def intent():
    return preflight.load(INTENT)


def normalized(i=None):
    return preflight.normalized_spec(i or intent(),as_of=AS_OF)


def allocation_record(state='RESERVED'):
    spec=normalized()
    hold=spec['hold_expires_at'] if state in ('RESERVED','UNCERTAIN') else None
    confirmed='2026-09-18T17:20:00Z' if state in ('CONFIRMED','RELEASE_PENDING','QUARANTINED','RELEASED') else None
    realization='controlled-realization:fixture' if confirmed else None
    release='2026-09-18T17:30:00Z' if state in ('RELEASE_PENDING','QUARANTINED','RELEASED') else None
    clean=cleanup()
    reuse=None;released=None
    if state=='RELEASE_PENDING':
        clean['routes']={'status':'COMPLETE','evidence_ref':'controlled-cleanup:routes:fixture',
                         'observed_at':'2026-09-18T17:35:00Z'}
        clean['dns']={'status':'PENDING','evidence_ref':'controlled-cleanup:dns:fixture',
                      'observed_at':'2026-09-18T17:35:00Z'}
    elif state in ('QUARANTINED','RELEASED'):
        clean=cleanup('COMPLETE')
        clean['dhcp_leases']={'status':'NOT_APPLICABLE',
                              'evidence_ref':'controlled-cleanup:dhcp-na:fixture',
                              'observed_at':'2026-09-18T17:35:00Z'}
        reuse='2026-09-18T20:00:00Z' if state=='QUARANTINED' else '2026-09-18T17:40:00Z'
        if state=='RELEASED':released='2026-09-18T17:50:00Z'
    return {
        'allocation_id':spec['allocation_id'],'operation_id':spec['operation_id'],
        'generation':spec['generation'],'state':state,
        'reservation_id':spec['reservation_id'],'request_id':spec['request_id'],
        'wsd_engineering_ref':spec['wsd_engineering_ref'],
        'intent_sha256':reservation_records.canonical_digest(spec),
        'allocation_policy':spec['allocation_policy'],
        'overlap_exception_ref':spec['overlap_exception_ref'],
        'family':spec['family'],'allocation_kind':spec['allocation_kind'],
        'requested_prefix_length':spec['requested_prefix_length'],
        'delegated_scope_ref':spec['delegated_scope_ref'],
        'authoritative_system':{'system_ref':'external-ipam:fixture',
                                'record_ref':'ipam-record:fixture','record_version':1},
        'allocation_ref':'ipam-allocation:fixture-01',
        'created_at':'2026-09-18T17:10:00Z',
        'last_observed_at':'2026-09-18T17:45:00Z',
        'hold_expires_at':hold,'confirmed_at':confirmed,'realization_ref':realization,
        'release_requested_at':release,'cleanup':clean,'reuse_not_before':reuse,
        'released_at':released,
        'owners':deepcopy(spec['owners']),
        'evidence_refs':['controlled-evidence:ipam-fixture'],
        'source_refs':['docs/engineering/authoritative-ipam-allocation-handoff.md']
    }


def allocation_index(*items):
    x=ipam.load();x['records']=list(items);return x


class IPAMRecordTests(unittest.TestCase):
    def test_current_index_is_valid_empty_and_value_free(self):
        result=ipam.validate(ipam.load(),as_of=AS_OF)
        self.assertEqual(result['record_count'],0)
        run=subprocess.run([
            sys.executable,str(ROOT/'scripts/check_ipam_allocation_records.py'),
            '--as-of','2026-09-18T18:00:00Z'],
            capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        out=json.loads(run.stdout)
        self.assertIs(out['actual_allocation_values_in_repository'],False)

    def test_reserved_record_is_valid_before_expiry(self):
        result=ipam.validate(allocation_index(allocation_record()),as_of=AS_OF)
        self.assertEqual(result['reserved_count'],1)

    def test_expired_reserved_record_requires_reconciliation(self):
        r=allocation_record();r['hold_expires_at']='2026-09-18T17:59:59Z'
        with self.assertRaises(ValueError):ipam.validate(allocation_index(r),as_of=AS_OF)

    def test_confirmed_requires_realization_reference(self):
        r=allocation_record('CONFIRMED');r['realization_ref']=None
        with self.assertRaises(ValueError):ipam.validate(allocation_index(r),as_of=AS_OF)

    def test_release_pending_preserves_incomplete_cleanup(self):
        result=ipam.validate(allocation_index(allocation_record('RELEASE_PENDING')),as_of=AS_OF)
        self.assertEqual(result['release_lifecycle_count'],1)

    def test_quarantine_requires_every_cleanup_resolved(self):
        r=allocation_record('QUARANTINED')
        r['cleanup']['dns']={'status':'PENDING','evidence_ref':'controlled-cleanup:dns:fixture',
                             'observed_at':'2026-09-18T17:35:00Z'}
        with self.assertRaises(ValueError):ipam.validate(allocation_index(r),as_of=AS_OF)

    def test_released_before_quarantine_boundary_is_rejected(self):
        r=allocation_record('RELEASED');r['released_at']='2026-09-18T17:30:00Z'
        with self.assertRaises(ValueError):ipam.validate(allocation_index(r),as_of=AS_OF)

    def test_released_after_cleanup_and_quarantine_is_valid(self):
        result=ipam.validate(allocation_index(allocation_record('RELEASED')),as_of=AS_OF)
        self.assertEqual(result['release_lifecycle_count'],1)

    def test_uncertain_can_preserve_partial_release_evidence(self):
        r=allocation_record('UNCERTAIN')
        r['hold_expires_at']=None
        r['release_requested_at']='2026-09-18T17:30:00Z'
        r['cleanup']['routes']={'status':'COMPLETE','evidence_ref':'controlled-cleanup:routes:fixture',
                                'observed_at':'2026-09-18T17:35:00Z'}
        result=ipam.validate(allocation_index(r),as_of=AS_OF)
        self.assertEqual(result['unresolved_count'],1)

    def test_unique_default_cannot_carry_overlap_exception(self):
        r=allocation_record();r['overlap_exception_ref']='controlled-exception:fixture'
        with self.assertRaises(ValueError):ipam.validate(allocation_index(r),as_of=AS_OF)

    def test_overlap_requires_explicit_exception_reference(self):
        r=allocation_record();r['allocation_policy']='OVERLAP_EXCEPTION';r['overlap_exception_ref']=None
        with self.assertRaises(ValueError):ipam.validate(allocation_index(r),as_of=AS_OF)

    def test_raw_address_field_is_not_part_of_record_schema(self):
        r=allocation_record();r['address']='192.0.2.10'
        with self.assertRaises(ValueError):ipam.validate(allocation_index(r),as_of=AS_OF)

    def test_opaque_allocation_ref_rejects_literal_address(self):
        r=allocation_record();r['allocation_ref']='ipam:192.0.2.10'
        with self.assertRaises(ValueError):ipam.validate(allocation_index(r),as_of=AS_OF)

    def test_duplicate_operation_identity_rejected(self):
        one=allocation_record();two=deepcopy(one);two['allocation_id']='EXAMPLE-IPAM-ALLOCATION-02'
        with self.assertRaises(ValueError):ipam.validate(allocation_index(one,two),as_of=AS_OF)


class IPAMPreflightTests(unittest.TestCase):
    def evaluate(self,i=None,aidx=None,ridx=None):
        return preflight.evaluate(
            i or intent(),
            reservation_index=ridx if ridx is not None else reservation_index(),
            allocation_index=aidx if aidx is not None else ipam.load(),
            as_of=AS_OF)

    def test_current_example_holds_without_parent_reservation_record(self):
        result=preflight.evaluate(intent(),reservation_index=reservation_records.load(),
                                  allocation_index=ipam.load(),as_of=AS_OF)
        self.assertEqual(result['status'],preflight.HOLD_PARENT)
        self.assertIsNone(result['actual_allocation_value'])

    def test_parent_held_makes_intent_ready_only_for_external_ipam(self):
        result=self.evaluate()
        self.assertEqual(result['status'],preflight.READY)
        self.assertIsNone(result['actual_allocation_value'])
        self.assertEqual(result['actual_allocation_value_source'],'AUTHORITATIVE_IPAM_ONLY')
        for key in ('may_reserve_address','may_confirm_address','may_release_address',
                    'may_reuse_address','may_write_dns','may_apply','may_activate'):
            self.assertIs(result[key],False)

    def test_parent_consumed_does_not_start_new_ipam_reserve(self):
        result=self.evaluate(ridx=reservation_index('CONSUMED'))
        self.assertEqual(result['status'],preflight.HOLD_PARENT)

    def test_same_operation_same_intent_reuses_reserved_allocation(self):
        result=self.evaluate(aidx=allocation_index(allocation_record()))
        self.assertEqual(result['status'],preflight.EXISTING_RESERVED)

    def test_confirmed_allocation_is_not_reallocated(self):
        result=self.evaluate(aidx=allocation_index(allocation_record('CONFIRMED')))
        self.assertEqual(result['status'],preflight.EXISTING_CONFIRMED)

    def test_changed_generation_conflicts_with_existing_operation(self):
        i=intent();r=allocation_record();i['spec']['generation']=2
        result=self.evaluate(i,aidx=allocation_index(r))
        self.assertEqual(result['status'],preflight.HOLD_CONFLICT)

    def test_same_allocation_id_different_authoritative_operation_conflicts(self):
        r=allocation_record();r['operation_id']='OTHER-IPAM-OP-01'
        result=self.evaluate(aidx=allocation_index(r))
        self.assertEqual(result['status'],preflight.HOLD_CONFLICT)

    def test_uncertain_allocation_stops_retry(self):
        result=self.evaluate(aidx=allocation_index(allocation_record('UNCERTAIN')))
        self.assertEqual(result['status'],preflight.HOLD_UNCERTAIN)

    def test_release_lifecycle_stops_reallocation(self):
        for state in ('RELEASE_PENDING','QUARANTINED'):
            with self.subTest(state=state):
                result=self.evaluate(aidx=allocation_index(allocation_record(state)))
                self.assertEqual(result['status'],preflight.HOLD_RELEASE)

    def test_released_allocation_requires_new_operation(self):
        result=self.evaluate(aidx=allocation_index(allocation_record('RELEASED')))
        self.assertEqual(result['status'],preflight.HOLD_TERMINAL)

    def test_caller_cannot_supply_guessed_address(self):
        i=intent();i['spec']['requested_address']='192.0.2.99'
        with self.assertRaises(ValueError):self.evaluate(i)

    def test_operation_must_match_parent_ipam_dependency(self):
        i=intent();i['spec']['operation_id']='OTHER-IPAM-OP-01'
        with self.assertRaises(ValueError):self.evaluate(i)

    def test_overlap_intent_requires_explicit_exception(self):
        i=intent();i['spec']['allocation_policy']='OVERLAP_EXCEPTION'
        with self.assertRaises(ValueError):self.evaluate(i)

    def test_cli_can_assert_current_parent_hold(self):
        run=subprocess.run([
            sys.executable,str(ROOT/'scripts/check_ipam_allocation_preflight.py'),str(INTENT),
            '--as-of','2026-09-18T18:00:00Z',
            '--expected-status',preflight.HOLD_PARENT],
            capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        self.assertEqual(json.loads(run.stdout)['status'],preflight.HOLD_PARENT)


if __name__=='__main__':unittest.main()
