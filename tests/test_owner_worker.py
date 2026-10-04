"""Remote ownership boundaries and lost coordinator response recovery."""
from copy import deepcopy
from datetime import timedelta
import base64
from pathlib import Path
import struct
import unittest
from unittest.mock import patch
import test_delivery_restic as harness
from provisioner.execution import readback_core as c
from provisioner.execution import owner_worker as worker, remote_owner, delivery_run as delivery, delivery_steps as steps
from provisioner.execution.run_files import digest,encoded,load_private,read_private,replace_private,utcnow,write_new


class OwnerWorkerTests(unittest.TestCase):
    def setUp(self):
        harness.DeliveryResticTests.setUp(self)
        self.spool=self.base/'spool'; self.spool.mkdir(mode=0o700)
        self.owner_ledger=self.base/'owner-ledger'; self.owner_ledger.mkdir(mode=0o700)
        harness.DeliveryResticTests.packet(self,'backup','backup')
        packet=load_private(self.inbox/'backup.json')
        self.job={'format':'hosting-owner-job/1','job_id':'capture-01','machine_id':self.config['machine_id'],
            'source_commit':self.plan['source_commit'],'scope':self.plan['scope'],'generation':1,'kind':'restic',
            'parameters':packet['parameters'],'files':packet['files'],
            'delivery':{'plan_sha256':c.digest(self.plan),'step_id':'backup','dependencies':{}},
            'valid_from':(utcnow()-timedelta(minutes=1)).isoformat(),'valid_until':(utcnow()+timedelta(minutes=10)).isoformat(),
            'dispatch_ref':'TEST-ONLY'}
        write_new(self.spool/'capture-01.json',encoded(self.job))
    def request(self,action='execute'):
        return {'format':'hosting-owner-request/1','action':action,'job_id':self.job['job_id'],'job_sha256':c.digest(self.job)}
    def serve(self,action='execute'):
        return worker.serve(self.request(action),self.spool,self.owner_ledger)
    def test_worker_capture_and_receipt_observation_does_not_replay(self):
        result=self.serve(); self.assertEqual(result['owner_status'],'CAPTURED_REQUIRES_RESTORE_TEST')
        self.assertEqual(set(worker.check_result(result,self.job)),{'receipt.json','context.json','manifest.json'})
        count=len(self.calls); self.assertEqual(self.serve('observe'),result); self.assertEqual(len(self.calls),count)
    def test_observe_cannot_start_job_and_unknown_owner_cannot_replay(self):
        with self.assertRaisesRegex(ValueError,'Observation cannot start'): self.serve('observe')
        self.assertEqual(self.calls,[])
        with patch.object(steps,'dispatch',side_effect=InterruptedError('lost owner outcome')):
            with self.assertRaises(InterruptedError): self.serve()
        with patch.object(steps,'dispatch',side_effect=AssertionError('native redispatch')):
            with self.assertRaises(OSError): self.serve('observe')
    def test_staged_job_digest_machine_scope_and_recursive_dispatch_hold(self):
        request=self.request(); request['job_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'Staged owner job'): worker.serve(request,self.spool,self.owner_ledger)
        for mutation in (lambda j:j.update(machine_id='0'*32),lambda j:j.update(kind='remote_owner'),
                         lambda j:j.update(job_id='../escape'),lambda j:j['scope'].update(platform='unknown')):
            original=deepcopy(self.job); mutation(self.job)
            replace_private(self.spool/'capture-01.json',encoded(self.job))
            with self.assertRaises((ValueError,OSError)): self.serve()
            self.job=original
        self.assertEqual(self.calls,[])
    def test_response_identity_and_artifact_mutations_are_rejected(self):
        result=self.serve()
        for mutation in (lambda x:x.update(machine_id='0'*32),lambda x:x.update(job_sha256='0'*64),
                         lambda x:x['artifacts']['manifest.json'].update(sha256='0'*64),
                         lambda x:x['artifacts'].update(secret={'sha256':'0'*64,'base64':'eA=='})):
            bad=deepcopy(result); mutation(bad)
            with self.assertRaises(ValueError): worker.check_result(bad,self.job)
    def test_transport_setup_failures_remove_all_temporary_credentials_before_network_contact(self):
        raw=struct.pack('>I',11)+b'ssh-ed25519'+struct.pack('>I',32)+b'x'*32
        target={'format':'hosting-owner-target/1','address':'192.0.2.10','port':22,'user':'hosting',
            'machine_id':self.job['machine_id'],'host_key':'ssh-ed25519 '+base64.b64encode(raw).decode(),
            'valid_from':self.job['valid_from'],'valid_until':self.job['valid_until'],'max_seconds':30}
        key=self.base/'key'; certificate=self.base/'certificate'
        write_new(key,b'TEST-KEY'); write_new(certificate,b'TEST-CERTIFICATE')
        for failed in ('ssh_key-cert.pub','known_hosts'):
            def failing(path,raw):
                if path.name==failed: raise OSError('Synthetic artifact publication failure')
                return write_new(path,raw)
            with self.subTest(failed=failed),patch.object(remote_owner,'write_new',side_effect=failing), \
                 patch.object(remote_owner.subprocess,'run',side_effect=AssertionError('unexpected network contact')), \
                 self.assertRaises(OSError):
                remote_owner.contact(self.job,target,'/usr/bin/ssh',key,certificate,self.base)
            self.assertFalse(list(self.base.glob('transport-*/ssh_key*')))
            self.assertEqual(read_private(key),b'TEST-KEY'); self.assertEqual(read_private(certificate),b'TEST-CERTIFICATE')
    def test_remote_delivery_recovers_lost_response_by_observation_only(self):
        self.plan['steps']=[{'id':'remote','kind':'remote_owner','needs':[]}]
        self.job['delivery']={'plan_sha256':c.digest(self.plan),'step_id':'remote','dependencies':{}}
        replace_private(self.spool/'capture-01.json',encoded(self.job))
        raw=struct.pack('>I',11)+b'ssh-ed25519'+struct.pack('>I',32)+b'x'*32
        target={'format':'hosting-owner-target/1','address':'192.0.2.10','port':22,'user':'hosting',
            'machine_id':self.job['machine_id'],'host_key':'ssh-ed25519 '+base64.b64encode(raw).decode(),
            'valid_from':self.job['valid_from'],'valid_until':self.job['valid_until'],'max_seconds':30}
        bindings={}
        for name,value in {'job':self.job,'target':target,'ssh_key':'TEST-ONLY','ssh_certificate':'TEST-ONLY'}.items():
            path=self.base/(name+'.json'); write_new(path,encoded(value)); bindings[name]={'path':str(path),'sha256':digest(read_private(path))}
        packet={'format':'hosting-delivery-step/1','plan_sha256':c.digest(self.plan),'step_id':'remote','dependencies':{},
                'parameters':{'ssh':str(self.binary),'ssh_sha256':digest(self.binary.read_bytes())},'files':bindings}
        write_new(self.inbox/'remote.json',encoded(packet))
        modes=[]
        def contact(job,target,binary,key,certificate,directory,*,observe=False):
            modes.append(observe); result=self.serve('observe' if observe else 'execute')
            if not observe: raise InterruptedError('SSH response lost after owner completion')
            self.assertEqual(key,self.base/'renewed-key.json')
            self.assertEqual(certificate,self.base/'renewed-cert.json')
            return result
        with patch.object(remote_owner,'contact',side_effect=contact):
            with self.assertRaises(InterruptedError): delivery.run(self.plan,self.inbox,self.ledger,execute=True)
            # Expired/revoked original credentials may be removed; replacement
            # access can only observe the same pinned endpoint and immutable job.
            (self.base/'ssh_key.json').unlink(); (self.base/'ssh_certificate.json').unlink()
            renewal={'format':'hosting-owner-recovery-access/1','job_sha256':c.digest(self.job),
                     'files':{},'access_ref':'TEST-RENEWED-OBSERVATION'}
            for name,value,suffix in [('target',target|{'valid_until':(utcnow()+timedelta(minutes=30)).isoformat()},'target'),
                                      ('ssh_key','NEW-TEST-KEY','key'),('ssh_certificate','NEW-TEST-CERT','cert')]:
                path=self.base/('renewed-'+suffix+'.json'); write_new(path,encoded(value))
                renewal['files'][name]={'path':str(path),'sha256':digest(read_private(path))}
            write_new(self.inbox/'remote.recovery-authority.json',encoded(renewal))
            self.assertEqual(delivery.run(self.plan,self.inbox,self.ledger,execute=True)['status'],
                             'DELIVERY_EXECUTED_REQUIRES_ACCEPTANCE')
        self.assertEqual(modes,[False,True]); self.assertEqual(self.calls.count('backup'),1)
        # A renewed window cannot select a new endpoint or change its host key.
        for update in ({'address':'192.0.2.20'},{'max_seconds':60},{'user':'different'}):
            path=self.base/'renewed-target.json'; replace_private(path,encoded(target|update))
            renewal['files']['target']['sha256']=digest(read_private(path))
            with self.assertRaisesRegex(ValueError,'original owner endpoint'):
                remote_owner.recovery_access(renewal,self.job,target)


if __name__=='__main__': unittest.main()
