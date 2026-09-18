"""Authoritative DNS registration evidence/preflight tests; no real DNS mutation."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import unittest

from scripts import check_dns_registration_preflight as preflight
from scripts import check_dns_registration_records as dnsrecords
from scripts import check_ipam_allocation_records as ipam
from tests.test_ipam_allocation_handoff import allocation_index, allocation_record

ROOT=Path(__file__).resolve().parents[1]
AS_OF=datetime(2026,9,18,18,0,tzinfo=timezone.utc)
INTENT=ROOT/'examples/dns_registration_intent.json.example'


def intent():
    return preflight.load(INTENT)


def normalized(i=None):
    return preflight.normalized_spec(i or intent(),as_of=AS_OF)


def observations(required=('AUTHORITATIVE','RECURSIVE')):
    out={}
    for key in dnsrecords.OBSERVATIONS:
        if key in required:
            out[key]={'status':'COMPLETE','evidence_ref':f'controlled-dns-observation:{key.lower()}:fixture',
                      'observed_at':'2026-09-18T17:50:00Z'}
        else:
            out[key]={'status':'NOT_APPLICABLE','evidence_ref':f'controlled-dns-observation:{key.lower()}:na',
                      'observed_at':'2026-09-18T17:50:00Z'}
    return out


def dns_record(state='REGISTERED'):
    spec=normalized()
    registered='2026-09-18T17:45:00Z'
    release=None;tombstone=None;released=None
    if state in ('RELEASE_PENDING','TOMBSTONED','RELEASED'):
        release='2026-09-18T17:52:00Z'
    if state in ('TOMBSTONED','RELEASED'):
        tombstone='2026-09-18T19:00:00Z' if state=='TOMBSTONED' else '2026-09-18T17:54:00Z'
    if state=='RELEASED':
        released='2026-09-18T17:55:00Z'
    return {
        'registration_id':spec['registration_id'],'operation_id':spec['operation_id'],
        'generation':spec['generation'],'state':state,
        'reservation_id':spec['reservation_id'],'request_id':spec['request_id'],
        'wsd_engineering_ref':spec['wsd_engineering_ref'],
        'ipam_allocation_id':spec['ipam_allocation_id'],
        'name_assignment_ref':spec['name_assignment_ref'],
        'record_types':deepcopy(spec['record_types']),
        'forward_zone_ref':spec['forward_zone_ref'],'reverse_zone_ref':spec['reverse_zone_ref'],
        'ttl_profile_ref':spec['ttl_profile_ref'],
        'required_observations':deepcopy(spec['required_observations']),
        'authoritative_system':{
            'system_ref':'external-dns:fixture','record_ref':'dns-record:fixture','record_version':1},
        'created_at':'2026-09-18T17:35:00Z','last_observed_at':'2026-09-18T17:56:00Z',
        'registered_at':registered,'release_requested_at':release,
        'tombstone_until':tombstone,'released_at':released,
        'observations':observations(spec['required_observations']),
        'owners':deepcopy(spec['owners']),
        'evidence_refs':['controlled-evidence:dns-fixture'],
        'source_refs':['docs/engineering/authoritative-dns-registration-handoff.md']
    }


def dns_index(*records):
    x=dnsrecords.load();x['records']=list(records);return x


def confirmed_ipam():
    return allocation_index(allocation_record('CONFIRMED'))


class DNSRecordTests(unittest.TestCase):
    def test_current_index_is_empty_value_and_name_free(self):
        result=dnsrecords.validate(dnsrecords.load(),ipam_index=ipam.load(),as_of=AS_OF)
        self.assertEqual(result['record_count'],0)
        run=subprocess.run([
            sys.executable,str(ROOT/'scripts/check_dns_registration_records.py'),
            '--as-of','2026-09-18T18:00:00Z'],
            capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        out=json.loads(run.stdout)
        self.assertIs(out['literal_dns_names_in_repository'],False)
        self.assertIs(out['literal_allocation_values_in_repository'],False)

    def test_registered_record_requires_confirmed_ipam(self):
        result=dnsrecords.validate(dns_index(dns_record()),ipam_index=confirmed_ipam(),as_of=AS_OF)
        self.assertEqual(result['registered_count'],1)
        with self.assertRaises(ValueError):
            dnsrecords.validate(dns_index(dns_record()),
                                ipam_index=allocation_index(allocation_record('RESERVED')),
                                as_of=AS_OF)

    def test_required_recursive_observation_cannot_be_pending(self):
        r=dns_record();r['observations']['RECURSIVE']={
            'status':'PENDING','evidence_ref':None,'observed_at':None}
        with self.assertRaises(ValueError):
            dnsrecords.validate(dns_index(r),ipam_index=confirmed_ipam(),as_of=AS_OF)

    def test_secondary_may_be_not_applicable_when_not_required(self):
        result=dnsrecords.validate(dns_index(dns_record()),ipam_index=confirmed_ipam(),as_of=AS_OF)
        rec=result['records'][0]
        self.assertEqual(rec['observations']['SECONDARY']['status'],'NOT_APPLICABLE')

    def test_authoritative_observation_is_always_required(self):
        r=dns_record();r['required_observations']=['RECURSIVE']
        with self.assertRaises(ValueError):
            dnsrecords.validate(dns_index(r),ipam_index=confirmed_ipam(),as_of=AS_OF)

    def test_literal_dns_name_in_opaque_ref_is_rejected(self):
        r=dns_record();r['name_assignment_ref']='host.internal.example.'
        with self.assertRaises(ValueError):
            dnsrecords.validate(dns_index(r),ipam_index=confirmed_ipam(),as_of=AS_OF)

    def test_literal_ip_in_zone_ref_is_rejected(self):
        r=dns_record();r['forward_zone_ref']='zone:192.0.2.10'
        with self.assertRaises(ValueError):
            dnsrecords.validate(dns_index(r),ipam_index=confirmed_ipam(),as_of=AS_OF)

    def test_family_mismatch_rejected(self):
        alloc=allocation_record('CONFIRMED');alloc['family']='IPV6'
        with self.assertRaises(ValueError):
            dnsrecords.validate(dns_index(dns_record()),ipam_index=allocation_index(alloc),as_of=AS_OF)

    def test_ptr_requires_reverse_scope(self):
        r=dns_record();r['reverse_zone_ref']=None
        with self.assertRaises(ValueError):
            dnsrecords.validate(dns_index(r),ipam_index=confirmed_ipam(),as_of=AS_OF)

    def test_release_pending_and_tombstone_lifecycle(self):
        result=dnsrecords.validate(dns_index(dns_record('RELEASE_PENDING')),
                                   ipam_index=confirmed_ipam(),as_of=AS_OF)
        self.assertEqual(result['release_lifecycle_count'],1)
        result=dnsrecords.validate(dns_index(dns_record('TOMBSTONED')),
                                   ipam_index=confirmed_ipam(),as_of=AS_OF)
        self.assertEqual(result['release_lifecycle_count'],1)

    def test_release_before_tombstone_boundary_rejected(self):
        r=dns_record('RELEASED');r['released_at']='2026-09-18T17:53:00Z'
        with self.assertRaises(ValueError):
            dnsrecords.validate(dns_index(r),ipam_index=confirmed_ipam(),as_of=AS_OF)

    def test_uncertain_record_is_preserved_not_registered(self):
        r=dns_record('UNCERTAIN');r['registered_at']=None
        result=dnsrecords.validate(dns_index(r),ipam_index=confirmed_ipam(),as_of=AS_OF)
        self.assertEqual(result['unresolved_count'],1)


class DNSPreflightTests(unittest.TestCase):
    def evaluate(self,i=None,didx=None,iidx=None):
        return preflight.evaluate(
            i or intent(),
            ipam_index=iidx if iidx is not None else ipam.load(),
            dns_index=didx if didx is not None else dnsrecords.load(),
            as_of=AS_OF)

    def test_current_example_holds_without_confirmed_ipam(self):
        result=self.evaluate()
        self.assertEqual(result['status'],preflight.HOLD_IPAM)
        self.assertIsNone(result['actual_dns_name'])
        self.assertIsNone(result['actual_record_values'])

    def test_confirmed_ipam_makes_intent_ready_only_for_dns_owner(self):
        result=self.evaluate(iidx=confirmed_ipam())
        self.assertEqual(result['status'],preflight.READY)
        self.assertEqual(result['actual_name_value_source'],
                         'AUTHORITATIVE_IPAM_AND_DNS_NAME_AUTHORITY_ONLY')
        for key in ('may_write_dns','may_delete_dns','may_release_name','may_apply','may_activate'):
            self.assertIs(result[key],False)

    def test_reserved_ipam_does_not_allow_dns_registration(self):
        result=self.evaluate(iidx=allocation_index(allocation_record('RESERVED')))
        self.assertEqual(result['status'],preflight.HOLD_IPAM)

    def test_existing_registered_is_idempotent(self):
        result=self.evaluate(didx=dns_index(dns_record()),iidx=confirmed_ipam())
        self.assertEqual(result['status'],preflight.EXISTING_REGISTERED)

    def test_uncertain_dns_stops_retry(self):
        r=dns_record('UNCERTAIN');r['registered_at']=None
        result=self.evaluate(didx=dns_index(r),iidx=confirmed_ipam())
        self.assertEqual(result['status'],preflight.HOLD_UNCERTAIN)

    def test_release_lifecycle_stops_new_update(self):
        for state in ('RELEASE_PENDING','TOMBSTONED'):
            with self.subTest(state=state):
                result=self.evaluate(didx=dns_index(dns_record(state)),iidx=confirmed_ipam())
                self.assertEqual(result['status'],preflight.HOLD_RELEASE)

    def test_changed_generation_conflicts(self):
        i=intent();i['spec']['generation']=2
        result=self.evaluate(i,didx=dns_index(dns_record()),iidx=confirmed_ipam())
        self.assertEqual(result['status'],preflight.HOLD_CONFLICT)

    def test_caller_cannot_add_literal_dns_name(self):
        i=intent();i['spec']['fqdn']='host.internal.example.'
        with self.assertRaises(ValueError):self.evaluate(i,iidx=confirmed_ipam())

    def test_caller_cannot_add_literal_address(self):
        i=intent();i['spec']['address']='192.0.2.10'
        with self.assertRaises(ValueError):self.evaluate(i,iidx=confirmed_ipam())

    def test_cli_can_assert_current_ipam_hold(self):
        run=subprocess.run([
            sys.executable,str(ROOT/'scripts/check_dns_registration_preflight.py'),str(INTENT),
            '--as-of','2026-09-18T18:00:00Z','--expected-status',preflight.HOLD_IPAM],
            capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        self.assertEqual(json.loads(run.stdout)['status'],preflight.HOLD_IPAM)


if __name__=='__main__':unittest.main()
