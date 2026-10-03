"""Incident dispatch keeps native holds and observes each remote invocation."""
from copy import deepcopy
from datetime import timedelta
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tests.test_edge_contain import Kernel
from tests.test_nft_edge import fixture
from provisioner.execution import delivery_containment as incident,delivery_run as delivery,delivery_steps as steps
from provisioner.execution import readback_core as c
from provisioner.execution import owner_worker as worker, edge_contain
from provisioner.execution.run_files import digest,encoded,load_private,read_private,replace_private,utcnow,write_new


class RemoteContainmentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.base=Path(self.temp.name)
        self.spool=self.base/'spool'; self.spool.mkdir(mode=0o700)
        self.ledger=self.base/'ledger'; self.ledger.mkdir(mode=0o700)
        self.binary=self.base/'nft'; self.binary.write_bytes(b'test'); self.binary.chmod(0o700)
        self.spec=fixture(); self.spec.update(machine_id=Path('/etc/machine-id').read_text().strip(),
            network_namespace_inode=os.stat('/proc/self/ns/net').st_ino,nft_sha256=digest(self.binary.read_bytes()))
        self.kernel=Kernel(self.spec)
        self.authority={'format':'hosting-edge-containment-authority/1','spec_sha256':digest(encoded(self.spec)),
            'incident_id':'incident-01','valid_from':(utcnow()-timedelta(minutes=1)).isoformat(),
            'valid_until':(utcnow()+timedelta(minutes=10)).isoformat(),'change_ref':'TEST-ONLY','boundary_acceptance_ref':'TEST-ONLY'}
        self.job={'format':'hosting-owner-job/1','job_id':'incident-01','machine_id':self.spec['machine_id'],
            'source_commit':'a'*40,'scope':self.spec['scope'],'generation':1,'kind':'edge_containment',
            'parameters':{'nft':str(self.binary),'nft_sha256':self.spec['nft_sha256']},'files':{},
            'delivery':{'plan_sha256':'b'*64,'step_id':'incident-containment','dependencies':{}},
            'valid_from':self.authority['valid_from'],'valid_until':self.authority['valid_until'],'dispatch_ref':'TEST-ONLY'}
        for name,value in {'spec':self.spec,'authority':self.authority}.items():
            path=self.base/(name+'.json'); write_new(path,encoded(value))
            self.job['files'][name]={'path':str(path),'sha256':digest(read_private(path))}
        self.save_job()
        source=patch.object(delivery,'verify',return_value={'status':'HASHES_MATCH','commit':'a'*40}); source.start(); self.addCleanup(source.stop)
        kernel=patch.object(edge_contain.edge,'Kernel',return_value=self.kernel); kernel.start(); self.addCleanup(kernel.stop)
    def save_job(self): replace_private(self.spool/'incident-01.json',encoded(self.job))
    def serve(self,action='execute'):
        return worker.serve({'format':'hosting-owner-request/1','action':action,'job_id':'incident-01',
                             'job_sha256':c.digest(self.job)},self.spool,self.ledger)
    def test_incident_bypasses_held_forward_graph_but_keeps_shared_native_ledger(self):
        plan={'format':'hosting-delivery/2','source_commit':'a'*40,'scope':self.spec['scope'],'operation_id':'failed-forward',
              'generation':1,'reviewed_plan_digest':'0'*64,'steps':[{'id':'edge','kind':'edge_policy','needs':[]}], 'operation_bindings':{},'reviewed_parameters':{},'compiled_catalog_ids':{}}
        inbox=self.base/'forward'; inbox.mkdir(mode=0o700)
        # A held forward graph with no completed edge stage cannot block withdrawal.
        delivery.run(plan,inbox,self.ledger,execute=True)
        first=self.serve(); self.assertEqual(first['owner_status'],'CONTAINED_OBSERVED_NOT_QUALIFIED')
        self.assertEqual(self.kernel.writes,1)
        self.assertTrue(list((self.ledger/'owners/edge_policy').glob('*/head.json')))
        second=self.serve('observe'); self.assertEqual(self.kernel.writes,1)
        self.assertNotEqual(first['artifacts'],second['artifacts'])
        # A stored prior receipt cannot mask reopened native policy.
        self.kernel.state['nftables'][-1]['rule']['expr'][-1]={'accept':None}
        with self.assertRaises(ValueError): self.serve()
        self.assertEqual(self.kernel.writes,1)
    def test_unstarted_observation_and_changed_job_files_cannot_withdraw(self):
        with self.assertRaisesRegex(ValueError,'Observation cannot start'): self.serve('observe')
        replace_private(self.base/'authority.json',encoded(self.authority|{'incident_id':'changed'}))
        with self.assertRaisesRegex(ValueError,'input bytes changed'): self.serve()
        self.assertEqual(self.kernel.writes,0)
    def test_remote_failure_hook_transports_only_containment_and_retains_receipt(self):
        from provisioner.execution import remote_owner
        import base64,struct
        plan={'format':'hosting-delivery/2','source_commit':'a'*40,'scope':self.spec['scope'],'operation_id':'central',
              'generation':1,'reviewed_plan_digest':'0'*64,'steps':[{'id':'verify','kind':'acceptance','needs':[]}], 'operation_bindings':{},'reviewed_parameters':{},'compiled_catalog_ids':{}}
        self.job['delivery']['plan_sha256']=c.digest(plan); self.save_job()
        raw=struct.pack('>I',11)+b'ssh-ed25519'+struct.pack('>I',32)+b'x'*32
        target={'format':'hosting-owner-target/1','address':'192.0.2.1','port':22,'user':'owner',
            'host_key':'ssh-ed25519 '+base64.b64encode(raw).decode(),'machine_id':self.spec['machine_id'],
            'valid_from':self.authority['valid_from'],'valid_until':self.authority['valid_until'],'max_seconds':30}
        config={'format':'hosting-delivery-containment/2','plan_sha256':c.digest(plan),'trigger_steps':['verify'],
                'ssh':str(self.binary),'ssh_sha256':digest(self.binary.read_bytes())}
        for name,value in {'job':self.job,'target':target,'ssh_key':'TEST','ssh_certificate':'TEST'}.items():
            path=self.base/('central-'+name+'.json'); write_new(path,encoded(value))
            config[name]={'path':str(path),'sha256':digest(read_private(path))}
        central=self.base/'central'; central.mkdir(mode=0o700)
        with patch.object(remote_owner,'contact',side_effect=lambda *args,**kwargs:self.serve()) as contact:
            result=incident.execute(config,plan,'verify',central,delivery.ROOT)
        self.assertEqual(result['status'],'CONTAINED_OBSERVED_NOT_QUALIFIED'); self.assertEqual(contact.call_count,1)
        self.assertTrue(list(central.glob('containment/*/remote-result.json')))
        bad=deepcopy(self.job); bad['kind']='edge_policy'; bad['parameters']['mode']='active'
        replace_private(self.base/'central-job.json',encoded(bad)); config['job']['sha256']=digest(encoded(bad))
        with self.assertRaisesRegex(ValueError,'only this delivery boundary'): incident.validate(config,plan)


if __name__=='__main__': unittest.main()
