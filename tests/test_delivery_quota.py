"""Quota owner handoff, lost coordinator replies and renewed read credentials."""
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch
from tests import test_openstack_quota as fixture
from provisioner.execution import readback_core as c
from provisioner.execution import delivery_steps as steps, openstack_quota as quota
from provisioner.execution.run_files import digest,encoded,load_private,write_new


class DeliveryQuotaTests(unittest.TestCase):
    setUpClass=classmethod(fixture.QuotaTests.setUpClass.__func__)
    tearDownClass=classmethod(fixture.QuotaTests.tearDownClass.__func__)
    configure=fixture.QuotaTests.configure
    authority=fixture.QuotaTests.authority
    puts=fixture.QuotaTests.puts
    def setUp(self):
        fixture.QuotaTests.setUp(self)
        self.base_path=self.ledger/'runs'/'scope'/'generation'
        self.base_path.mkdir(parents=True,mode=0o700)
        self.directory=self.base_path/'steps'/'quota'; self.directory.mkdir(parents=True,mode=0o700)
        self.step={'id':'quota','kind':'openstack_quota','needs':[]}
        self.plan=dict(format='hosting-delivery/2',source_commit='a'*40,operation_id='delivery-01',generation=1,reviewed_plan_digest='0'*64,
            scope=self.request['scope']|{'wsd_key':'wsd-a'},steps=[self.step], operation_bindings={},reviewed_parameters={},compiled_catalog_ids={})
        self.packet=dict(format='hosting-delivery-step/1',plan_sha256=c.digest(self.plan),step_id='quota',
            dependencies={},parameters={},files={})
        for name,raw in {'request':encoded(self.request),'authority':encoded(self.authority()),'token':self.token,'ca':self.ca}.items():
            path=self.ledger/name; write_new(path,raw); self.packet['files'][name]={'path':str(path),'sha256':digest(raw)}
    def dispatch(self):
        return steps.dispatch(self.step,self.packet,self.directory,self.base_path,self.plan,quota.ROOT)
    def recovery(self):
        bindings={}
        for name,raw in {'authority':encoded(self.authority('observe')),'token':self.token,'ca':self.ca}.items():
            path=self.ledger/('renewed-'+name); write_new(path,raw); bindings[name]={'path':str(path),'sha256':digest(raw)}
        path=self.ledger/'recovery.json'
        write_new(path,encoded({'format':'hosting-openstack-quota-recovery/1','request_sha256':c.digest(self.request),'files':bindings}))
        return path

    def test_exact_dispatch_and_lost_completion_use_one_native_put(self):
        actual=steps.complete
        with patch.object(steps,'complete',side_effect=InterruptedError),self.assertRaises(InterruptedError): self.dispatch()
        self.assertTrue((self.directory/'result.json').is_file()); self.assertEqual(self.puts(),1)
        for name in ('token','ca','authority'): Path(self.packet['files'][name]['path']).unlink()
        result,names=steps.recover(self.step,self.packet,self.directory,self.base_path,self.plan,quota.ROOT)
        self.assertEqual(result['project_id'],fixture.PROJECT); self.assertEqual(self.puts(),1)
        self.assertIn('owner-completion.json',names)
        result,_=steps.recover(self.step,self.packet,self.directory,self.base_path,self.plan,quota.ROOT)
        self.assertEqual(result['status'],'PROJECT_QUOTAS_OBSERVED_REQUIRES_ENFORCEMENT_ACCEPTANCE')

    def test_missing_coordinator_result_uses_fresh_read_only_credentials(self):
        native=quota.operate
        def lost(*args,**kwargs):
            native(*args,**kwargs); raise TimeoutError('Synthetic lost owner reply')
        with patch.object(quota,'operate',side_effect=lost),self.assertRaises(TimeoutError): self.dispatch()
        with self.assertRaisesRegex(ValueError,'read-only authority'):
            steps.recover(self.step,self.packet,self.directory,self.base_path,self.plan,quota.ROOT)
        self.token=b'rotated-fixture-token'
        recovery=self.recovery()
        for name in ('token','ca','authority'): Path(self.packet['files'][name]['path']).unlink()
        result,_=steps.recover(self.step,self.packet,self.directory,self.base_path,self.plan,quota.ROOT,recovery_authority=recovery)
        self.assertEqual(result['quotas']['cores']['limit'],8); self.assertEqual(self.puts(),1)
        self.assertTrue(any(headers.get('X-Auth-Token')=='rotated-fixture-token' for _,_,headers in type(self).calls))

    def test_foreign_tenant_is_refused_before_owner_contact(self):
        self.plan['scope']['tenant_key']='other-tenant'
        with self.assertRaisesRegex(ValueError,'Foreign tenant quota'): self.dispatch()
        self.assertEqual(type(self).calls,[])

    def test_later_native_generation_blocks_old_coordinator_completion(self):
        with patch.object(steps,'complete',side_effect=InterruptedError),self.assertRaises(InterruptedError): self.dispatch()
        original=deepcopy(self.request)
        self.request.update(operation_id='quota-02',generation=2,before=dict(self.request['after']),after={'cores':10,'instances':5})
        quota.operate(self.request,self.authority(),self.token,self.ca,steps.owner_ledger(self.base_path,'openstack_quota'))
        self.request=original
        with self.assertRaisesRegex(ValueError,'superseded'):
            steps.recover(self.step,self.packet,self.directory,self.base_path,self.plan,quota.ROOT)
        self.assertEqual(self.puts(),2)

    def test_recovery_cannot_expand_an_apply_authority(self):
        native=quota.operate
        def lost(*args,**kwargs):
            native(*args,**kwargs); raise TimeoutError
        with patch.object(quota,'operate',side_effect=lost),self.assertRaises(TimeoutError): self.dispatch()
        path=self.recovery(); record=load_private(path); authority_path=Path(record['files']['authority']['path'])
        raw=encoded(self.authority('apply')); authority_path.write_bytes(raw)
        record['files']['authority']['sha256']=digest(raw); path.write_bytes(encoded(record))
        with self.assertRaisesRegex(ValueError,'read-only authority'):
            steps.recover(self.step,self.packet,self.directory,self.base_path,self.plan,quota.ROOT,recovery_authority=path)
        self.assertEqual(self.puts(),1)


if __name__=='__main__': unittest.main()
