"""Real SQLite transactions, quota accounting, stale authority and retained holds."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch
from provisioner.execution import readback_core as c
from tools import capacity as a
from provisioner.execution.run_files import encoded, utcnow


def window():
    return dict(valid_from=(utcnow()-timedelta(minutes=1)).isoformat(),valid_until=(utcnow()+timedelta(minutes=20)).isoformat())


def units(cpu=16,memory=32768,storage=100): return dict(vcpu=cpu,memory_mb=memory,storage_gb=storage)


class CapacityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.path=Path(self.temp.name)/'capacity.db'
        self.envelope=dict(format='hosting-capacity-envelope/1',owner_id='capacity-01',revision=1,**window(),acceptance_ref='TEST-ONLY',
            pools={'pool-01':dict(origin='https://native.example.invalid',native_id='native-pool-01',platform='openstack',site_key='site-01',
                capacity=units(),reserve=units(4,8192,20),capabilities=['internal-ipv4'],qualification_ref='TEST-ONLY')},
            tenants={'tenant-01':dict(limit=units(8,16384,50),pools=['pool-01'],entitlement_ref='TEST-ONLY'),
                     'tenant-02':dict(limit=units(8,16384,50),pools=['pool-01'],entitlement_ref='TEST-ONLY')})
        self.request=dict(format='hosting-capacity-request/1',owner_id='capacity-01',reservation_id='reservation-01',operation_id='op-01',generation=1,
            scope=dict(environment_key='lab',site_key='site-01',platform='openstack',tenant_key='tenant-01',wsd_key='wsd-01'),
            pool_id='pool-01',units=units(8,8192,20),capabilities=['internal-ipv4'])
        a.initialize(self.path,self.envelope)
    def authority(self,action,request=None,native=None,previous=None):
        return dict(format='hosting-capacity-authority/1',request_sha256=c.digest(request or self.request),action=action,
            native_ids_sha256=c.digest(sorted(native or [])),envelope_sha256=c.digest(self.envelope),
            previous_receipt_sha256=c.digest(previous) if previous else None,**window(),change_ref='TEST',evidence_ref='TEST-NATIVE-EVIDENCE')
    def reserve(self): return a.operate(self.path,self.request,'reserve',self.authority('reserve'))
    def test_reserve_confirm_release_and_retries_preserve_exact_accounting(self):
        reserved=self.reserve(); self.assertEqual(reserved['status'],'RESERVED'); self.assertEqual(self.reserve(),reserved)
        authority=self.authority('confirm',native=['vm-1'],previous=reserved)
        confirmed=a.operate(self.path,self.request,'confirm',authority,['vm-1'])
        self.assertEqual(confirmed['status'],'CONFIRMED')
        self.assertEqual(a.operate(self.path,self.request,'confirm',authority,['vm-1']),confirmed)
        released=a.operate(self.path,self.request,'release',self.authority('release',previous=confirmed))
        self.assertEqual(released['status'],'RELEASED')
        self.assertEqual(a.operate(self.path,self.request,'inspect',None),released)
        with self.assertRaises(ValueError): self.reserve()
    def test_failure_reserve_and_tenant_entitlement_are_both_enforced(self):
        self.reserve()
        for tenant,cpu in [('tenant-01',1),('tenant-02',5)]:
            request=deepcopy(self.request); request.update(reservation_id='reservation-02',operation_id='op-02',units=units(cpu,1,1))
            request['scope']['tenant_key']=tenant
            with self.subTest(tenant=tenant),self.assertRaises(ValueError):
                a.operate(self.path,request,'reserve',self.authority('reserve',request))
        request['units']=units(4,1,1)
        self.assertEqual(a.operate(self.path,request,'reserve',self.authority('reserve',request))['status'],'RESERVED')
    def test_unknown_capability_pool_or_scope_cannot_reserve(self):
        for mutate in (lambda r:r.update(capabilities=['public-ipv6']),lambda r:r.update(pool_id='foreign'),
                       lambda r:r['scope'].update(site_key='foreign'),lambda r:r['units'].update(vcpu=True)):
            request=deepcopy(self.request); mutate(request)
            with self.assertRaises(ValueError): a.operate(self.path,request,'reserve',self.authority('reserve',request))
    def test_stale_release_cannot_recycle_newly_confirmed_native_resources(self):
        reserved=self.reserve(); old=self.authority('release',previous=reserved)
        a.operate(self.path,self.request,'confirm',self.authority('confirm',native=['vm-1'],previous=reserved),['vm-1'])
        with self.assertRaisesRegex(ValueError,'changed since'): a.operate(self.path,self.request,'release',old)
        self.assertEqual(a.operate(self.path,self.request,'inspect',None)['status'],'CONFIRMED')
    def test_transaction_failure_rolls_back_both_reservation_and_event(self):
        original=a.event
        def interrupted(db,kind,data):
            original(db,kind,data)
            if kind=='RESERVE': raise InterruptedError('crash before commit')
        with patch.object(a,'event',side_effect=interrupted),self.assertRaises(InterruptedError): self.reserve()
        with self.assertRaises(ValueError): a.operate(self.path,self.request,'inspect',None)
        self.assertEqual(self.reserve()['status'],'RESERVED')
    def test_two_controllers_cannot_oversubscribe_same_pool(self):
        barrier=threading.Barrier(2)
        def allocate(tenant):
            request=deepcopy(self.request); request['scope']['tenant_key']=tenant; request['reservation_id']=tenant
            barrier.wait()
            try: return a.operate(self.path,request,'reserve',self.authority('reserve',request))['status']
            except (ValueError,sqlite3.OperationalError): return 'HELD'
        with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(allocate,['tenant-01','tenant-02']))
        self.assertEqual(sorted(results),['HELD','RESERVED'])
    def test_envelope_renewal_preserves_live_placement_and_reserved_budget(self):
        self.reserve(); updated=deepcopy(self.envelope); updated.update(revision=2,**window())
        def authority(): return dict(format='hosting-capacity-envelope-authority/1',envelope_sha256=c.digest(updated),
            previous_envelope_sha256=c.digest(self.envelope),**window(),change_ref='TEST-REFRESH')
        updated['pools']['pool-01']['capacity']['vcpu']=9
        with self.assertRaises(ValueError): a.update_envelope(self.path,updated,authority())
        updated['pools']['pool-01']['capacity']['vcpu']=16
        updated['pools']['pool-01']['native_id']='other-pool'
        with self.assertRaises(ValueError): a.update_envelope(self.path,updated,authority())
        updated['pools']['pool-01']['native_id']='native-pool-01'
        self.assertEqual(a.update_envelope(self.path,updated,authority())['status'],'ENVELOPE_UPDATED')
        self.assertEqual(a.operate(self.path,self.request,'inspect',None)['status'],'RESERVED')
    def test_expiry_does_not_release_capacity_and_replay_detects_table_tampering(self):
        receipt=self.reserve()
        auth=self.authority('release',previous=receipt); auth['valid_until']=(utcnow()-timedelta(seconds=1)).isoformat()
        with self.assertRaises(ValueError): a.operate(self.path,self.request,'release',auth)
        self.assertEqual(a.operate(self.path,self.request,'inspect',None)['status'],'RESERVED')
        with sqlite3.connect(self.path) as db: db.execute("UPDATE reservation SET status='RELEASED'")
        with self.assertRaisesRegex(ValueError,'differs from its journal'): a.operate(self.path,self.request,'inspect',None)
    def test_native_confirmation_cannot_duplicate_ownership_or_change_ids(self):
        self.request['units']=units(4,8192,20); first=self.reserve()
        confirmed=a.operate(self.path,self.request,'confirm',self.authority('confirm',native=['vm-1'],previous=first),['vm-1'])
        with self.assertRaises(ValueError):
            a.operate(self.path,self.request,'confirm',self.authority('confirm',native=['vm-2'],previous=confirmed),['vm-2'])
        second=deepcopy(self.request); second.update(reservation_id='reservation-02',operation_id='op-02')
        reserved=a.operate(self.path,second,'reserve',self.authority('reserve',second))
        with self.assertRaises(ValueError): a.operate(self.path,second,'confirm',self.authority('confirm',second,['vm-1'],reserved),['vm-1'])


if __name__=='__main__': unittest.main()
