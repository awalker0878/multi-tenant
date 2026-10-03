"""Real SQLite capacity composition with local-only admitted/evidence doubles.

These cases execute one capacity owner's transactions and event replay. The
authority/evidence fixtures are deliberately synthetic, not PostgreSQL/native
qualification. No real platform or production allocation is contacted.
"""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
import sqlite3
import unittest
from unittest.mock import patch

from tests import test_capacity as harness
from tests.test_capacity_demand import fixture
from provisioner.allocations import capacity_owner as owner
from provisioner.allocations.transactions import (
    PoolDemand, ResourceBundle, ResourceUnits, ResourceTransactions,
    ResourceAuthorityWindow, ResourceObservation)
from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.workflow.admitted_job import AdmittedInput
from provisioner.execution import readback_core as c
from provisioner.execution.run_files import utcnow


class LocalAuthority:
    def __init__(self, source, destination):
        self.source,self.destination=source,destination
        self.now=utcnow()
        self.lease_seconds=300
        self.allowed_bundle=None
        self.refused=False
        self.calls=[]
        self.evidence=set()

    @contextmanager
    def locked(self,bundle,action,observations):
        self.calls.append(action)
        if self.refused or bundle.digest!=self.allowed_bundle:
            raise ValueError('Synthetic authority rejected exact resource selection')
        if any(observation.evidence_digest not in self.evidence for observation in observations):
            raise ValueError('Synthetic independent observer rejected evidence')
        yield ResourceAuthorityWindow(self.source,self.destination,self.now,
                                      self.now+timedelta(seconds=self.lease_seconds),'a'*64)


class ResourceTransactionTests(unittest.TestCase):
    def setUp(self):
        harness.CapacityTests.setUp(self)
        self.source=PlanScope('org-01','tenant-01','source-01','wsd-01',
                              'source-endpoint','source-pool','vmware')
        self.destination=PlanScope('org-01','tenant-01','site-01','wsd-01',
                                   'destination-endpoint','native-pool-01','openstack')
        self.inputs,self.catalog=fixture('openstack',self.request['scope'])
        zero=harness.units(0,0,0)
        self.pool=PoolDemand.from_workload(scope=self.destination,catalog=self.catalog,
            inputs=self.inputs,envelope_sha256=c.digest(self.envelope),
            budgets={'staging':harness.units(0,0,2),'snapshots':harness.units(0,0,2),
                     'retained-source':zero},capabilities=('internal-ipv4',))
        self.admitted=AdmittedInput('job-01','org-01','tenant-01','plan-01',1,'b'*64,0,'c'*64)
        self.bundle=ResourceBundle(self.admitted,'d'*64,'workload-01',1,(self.pool,))
        self.authority=LocalAuthority(self.source,self.destination)
        self.authority.allowed_bundle=self.bundle.digest
        self.service=ResourceTransactions(self.path,self.authority,clock=lambda:self.authority.now)

    def observation(self,receipt,outcome='EFFECT_PRESENT',*,native=('server-01','volume-01'),units=None):
        self.authority.evidence.add('e'*64)
        return ResourceObservation(receipt['reservation_id'],'e'*64,native,
                                   units or ResourceUnits(2,4295,43),outcome,self.authority.now)

    def reserve(self):
        return self.service.reserve(self.bundle)['receipts'][0]

    def test_workload_staging_snapshot_budgets_share_one_authoritative_charge(self):
        receipt=self.reserve()
        self.assertEqual(receipt['units'],harness.units(2,4295,47))
        self.assertEqual(receipt['format'],'hosting-capacity-receipt/2')
        self.assertEqual(self.service.require_ready(self.bundle)['receipts'][0],receipt)
        self.assertEqual(self.reserve(),receipt)
        with owner.database(self.path) as db:
            rows=owner.verify_events(db)
            self.assertEqual(len(rows),1)
            self.assertEqual(owner.usage(rows),harness.units(2,4295,47))
            request=c.strict_loads(rows[0][1])
            self.assertEqual(request['resource_binding']['job']['plan_digest'],'b'*64)
            self.assertEqual(request['resource_binding']['components']['staging']['storage_gb'],2)

    def test_selection_digest_is_acyclic_and_input_dicts_are_immutable(self):
        changed=replace(self.bundle,admitted=replace(self.admitted,job_id='job-02',
                        plan_digest='f'*64,payload_digest='0'*64),selection_digest='1'*64)
        self.assertEqual(changed.digest,self.bundle.digest)
        self.assertNotEqual(changed.requests('capacity-01'),self.bundle.requests('capacity-01'))
        before=self.bundle.digest
        self.inputs['members']['processor-01']['boot_disk_gib']=999
        self.catalog['native_id']='foreign'
        self.assertEqual(self.bundle.digest,before)
        self.assertEqual(self.pool.total()['storage_gb'],47)

    def test_job_revocation_prevents_every_owner_mutation(self):
        self.authority.refused=True
        with patch.object(owner,'event',side_effect=AssertionError('Owner mutation reached')):
            with self.assertRaisesRegex(ValueError,'authority rejected'):
                self.reserve()
        with owner.database(self.path) as db:
            self.assertEqual(owner.verify_events(db),[])

    def test_owner_cli_cannot_mutate_v2_using_a_copied_authority(self):
        request=self.bundle.requests('capacity-01')[0]
        with self.assertRaises(ValueError):
            owner.operate(self.path,request,'reserve',{})
        with owner.database(self.path) as db:
            self.assertEqual(owner.verify_events(db),[])

    def test_whole_pool_bundle_reservation_rolls_back_when_later_pool_exhausted(self):
        # Both pools remain in the exact source/destination scopes. Destination
        # selection commits no partial resource hold if source retention fails.
        expanded=deepcopy(self.envelope)
        expanded['pools']['source-pool']=deepcopy(expanded['pools']['pool-01'])
        expanded['pools']['source-pool'].update(platform='vmware',site_key='source-01',
                                               native_id='source-pool')
        expanded['tenants']['tenant-01']['pools'].append('source-pool')
        self.path.unlink(); owner.initialize(self.path,expanded)
        inputs,catalog=fixture('vmware',self.request['scope']|{'site_key':'source-01','platform':'vmware'})
        catalog.update(pool_id='source-pool',native_id='source-pool')
        source=PoolDemand.from_workload(scope=self.source,catalog=catalog,inputs=None,
            environment_key='lab',envelope_sha256=c.digest(expanded),
            budgets={'staging':harness.units(0,0,0),'snapshots':harness.units(0,0,0),
                     'retained-source':harness.units(8,20000,50)},capabilities=('internal-ipv4',))
        destination=replace(self.pool,envelope_sha256=c.digest(expanded))
        bundle=replace(self.bundle,pools=(destination,source))
        self.authority.allowed_bundle=bundle.digest
        with self.assertRaisesRegex(ValueError,'entitlement exhausted'):
            self.service.reserve(bundle)
        with owner.database(self.path) as db:
            self.assertEqual(owner.verify_events(db),[])

    def test_expired_hold_still_charges_capacity_and_can_be_reauthorized_renewed(self):
        with patch('provisioner.execution.run_files.utcnow',side_effect=lambda:self.authority.now), \
                patch.object(c,'now',side_effect=lambda:self.authority.now.isoformat()):
            receipt=self.reserve()
            self.authority.now+=timedelta(minutes=6)
            with self.assertRaisesRegex(ValueError,'expired'):
                self.service.require_ready(self.bundle)
            self.assertEqual(self.service.inspect(self.bundle)['receipts'][0]['status'],'RESERVED')
            with owner.database(self.path) as db:
                self.assertEqual(owner.usage(owner.verify_events(db)),receipt['units'])
            renewed=self.service.renew(self.bundle)['receipts'][0]
            self.assertGreater(c.timestamp(renewed['lease_expires_at']),c.timestamp(receipt['lease_expires_at']))
            self.assertEqual(self.service.require_ready(self.bundle)['receipts'][0],renewed)
            with owner.database(self.path) as db:
                self.assertEqual(len(owner.verify_events(db)),1)

    def test_confirmation_and_release_need_complete_fresh_verified_native_evidence(self):
        reserved=self.reserve()
        for outcome in ('UNKNOWN','IN_PROGRESS','NO_EFFECT'):
            observation=self.observation(reserved,outcome)
            with self.subTest(outcome=outcome),self.assertRaisesRegex(ValueError,'uncertain'):
                self.service.confirm(self.bundle,(observation,))
        missing=self.observation(reserved)
        self.authority.evidence.clear()
        with self.assertRaisesRegex(ValueError,'observer rejected'):
            self.service.confirm(self.bundle,(missing,))
        confirmed=self.service.confirm(self.bundle,(self.observation(reserved),))['receipts'][0]
        self.assertEqual(confirmed['status'],'CONFIRMED')
        self.assertIsNone(confirmed['lease_expires_at'])
        incomplete=self.observation(confirmed,'NO_EFFECT',native=('server-01',),units=ResourceUnits())
        with self.assertRaisesRegex(ValueError,'every confirmed native identity'):
            self.service.release(self.bundle,(incomplete,))
        alive=self.observation(confirmed,'NO_EFFECT',units=ResourceUnits(0,0,1))
        with self.assertRaisesRegex(ValueError,'still consumes'):
            self.service.release(self.bundle,(alive,))
        cleanup=self.observation(confirmed,'NO_EFFECT',units=ResourceUnits())
        released=self.service.release(self.bundle,(cleanup,))['receipts'][0]
        self.assertEqual(released['status'],'RELEASED')
        with self.assertRaises(ValueError): self.service.require_ready(self.bundle)

    def test_underreported_or_oversized_native_occupancy_cannot_confirm(self):
        reserved=self.reserve()
        for units in (ResourceUnits(2,4295,48),ResourceUnits(1,4295,43),ResourceUnits(2,1,43)):
            with self.subTest(units=units),self.assertRaises(ValueError):
                self.service.confirm(self.bundle,(self.observation(reserved,units=units),))
        self.assertEqual(self.service.inspect(self.bundle)['receipts'][0]['status'],'RESERVED')

    def test_old_envelope_or_unselected_scope_cannot_admit(self):
        foreign=replace(self.pool,envelope_sha256='0'*64)
        bundle=replace(self.bundle,pools=(foreign,))
        self.authority.allowed_bundle=bundle.digest
        with self.assertRaisesRegex(ValueError,'envelope changed'):
            self.service.reserve(bundle)
        self.authority.allowed_bundle=self.bundle.digest
        self.authority.destination=self.source
        with self.assertRaisesRegex(ValueError,'not selected'):
            self.reserve()

    def test_malformed_budget_unknown_flavor_or_undersized_retention_is_refused(self):
        with self.assertRaises(ValueError): ResourceUnits(vcpu=True)
        with self.assertRaises(ValueError): ResourceUnits.from_bytes(storage_bytes=-1)
        self.assertEqual(ResourceUnits.from_bytes(memory_bytes=1,storage_bytes=1),ResourceUnits(0,1,1))
        inputs=deepcopy(self.pool.inputs); inputs['members']['processor-01']['flavor_id']='unknown'
        with self.assertRaises(ValueError):
            PoolDemand.from_workload(scope=self.destination,catalog=self.pool.catalog,inputs=inputs,
                envelope_sha256=c.digest(self.envelope),budgets={key:harness.units(0,0,0)
                for key in ('staging','snapshots','retained-source')},capabilities=('internal-ipv4',))

    def test_replay_detects_changed_resource_binding_and_keeps_existing_charge(self):
        self.reserve()
        with sqlite3.connect(self.path) as db:
            request=c.strict_loads(db.execute('SELECT request FROM reservation').fetchone()[0])
            request['resource_binding']['job']['plan_digest']='e'*64
            from provisioner.execution.run_files import encoded
            db.execute('UPDATE reservation SET request=?',(encoded(request).decode(),))
        with self.assertRaisesRegex(ValueError,'differs from its journal'):
            self.service.inspect(self.bundle)


if __name__=='__main__': unittest.main()
