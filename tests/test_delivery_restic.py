"""Actual delivery and restic owner integration with a synthetic repository engine."""
from datetime import timedelta
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from tools import delivery_steps as steps, restic_run as restic
from provisioner.execution.run_files import digest, encoded, load_private, read_private, replace_private, utcnow, write_new
import test_delivery_run as harness
from test_restic_run import fixture


class DeliveryResticTests(unittest.TestCase):
    run_delivery = harness.DeliveryTests.run_delivery
    def setUp(self):
        harness.DeliveryTests.setUp(self)
        self.plan['steps']=[{'id':'backup','kind':'restic','needs':[]}]
        self.config=fixture(); self.config['scope']=self.plan['scope']
        self.source_dir=self.base/'export'; self.source_dir.mkdir(mode=0o700)
        (self.source_dir/'data').write_bytes(b'useful tenant data')
        self.config['source']=str(self.source_dir)
        self.config['machine_id']=Path('/etc/machine-id').read_text().strip()
        self.binary=self.base/'restic'; self.binary.write_bytes(b'synthetic test engine'); self.binary.chmod(0o700)
        self.config['restic_sha256']=digest(self.binary.read_bytes())
        self.credentials={'password':'test-only','username':'test','http_password':'test-only'}
        self.captured={}; self.calls=[]
        outer=self
        class Engine:
            def __init__(self,binary,config,credentials,operation,ca_file):
                self.operation=operation; self.deadline=10**20
            def repository(self): outer.calls.append('repository')
            def command(self,argv):
                outer.calls.append(argv[0])
                if argv[0]=='backup':
                    for path in [*outer.source_dir.rglob('*'),Path(argv[-1])]:
                        if path.is_file(): outer.captured[str(path)]=path.read_bytes()
                    outer.native={'id':'d'*64,'tags':[argv[6],argv[8]],'hostname':argv[4],
                                  'paths':[argv[-2],argv[-1]]}
                    return json.dumps({'message_type':'summary','snapshot_id':'d'*64})
                if argv[0]=='snapshots': return json.dumps([outer.native])
                if argv[0]=='restore':
                    target=Path(argv[3])
                    for original,raw in outer.captured.items():
                        path=target/original.lstrip('/'); path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(raw)
                    return '{}'
                raise AssertionError(argv)
        self.engine=patch.object(restic,'Restic',Engine); self.engine.start(); self.addCleanup(self.engine.stop)

    def packet(self,identity,action,dependencies=None,**extra):
        files={'config':self.config,'credentials':self.credentials,**extra}
        bindings={}
        for name,value in files.items():
            path=self.base/(identity+'-'+name+'.json'); replace_private(path,encoded(value))
            bindings[name]={'path':str(path),'sha256':digest(read_private(path))}
        from provisioner.execution import readback_core as c
        packet={'format':'hosting-delivery-step/1','plan_sha256':c.digest(self.plan),'step_id':identity,
                'dependencies':dependencies or {},'parameters':{'action':action,'restic':str(self.binary),
                'restic_sha256':self.config['restic_sha256'],'target':str(self.base/'restored') if action=='restore' else None},
                'files':bindings}
        replace_private(self.inbox/(identity+'.json'),encoded(packet))

    def test_backup_completed_before_coordinator_receipt_recovers_without_capture(self):
        self.packet('backup','backup')
        with patch.object(steps,'complete',side_effect=InterruptedError('lost coordinator')):
            with self.assertRaises(InterruptedError): self.run_delivery()
        calls=list(self.calls)
        self.assertEqual(self.run_delivery()['status'],'DELIVERY_EXECUTED_REQUIRES_ACCEPTANCE')
        self.assertEqual(self.calls,calls)
        receipt=load_private(next(self.ledger.glob('*/runs/*/steps/backup/receipt.json')))
        self.assertEqual(receipt['file_count'],1); self.assertFalse(receipt['native_qualification'])

    def test_unknown_capture_is_not_replayed(self):
        self.packet('backup','backup')
        with patch.object(restic,'backup',side_effect=InterruptedError('capture unknown')):
            with self.assertRaises(InterruptedError): self.run_delivery()
        with self.assertRaises(OSError): self.run_delivery()
        self.assertEqual(self.calls,[])

    def test_capture_restore_uses_exact_manifest_and_requires_independent_machine(self):
        self.plan['steps'].append({'id':'restore','kind':'restic','needs':['backup']})
        self.packet('backup','backup'); waiting=self.run_delivery()
        parent=next(self.ledger.glob('*/runs/*/steps/backup'))
        receipt=load_private(parent/'receipt.json'); manifest=load_private(parent/'manifest.json')
        target=self.base/'restored'
        authority={'valid_from':(utcnow()-timedelta(minutes=1)).isoformat(),
            'valid_until':(utcnow()+timedelta(minutes=10)).isoformat(),'config_sha256':digest(encoded(self.config)),
            'receipt_sha256':digest(encoded(receipt)),'machine_id':self.config['machine_id'],
            'target':str(target),'isolation_ref':'TEST-ISOLATED','change_ref':'TEST-RESTORE'}
        self.packet('restore','restore',waiting['dependencies'],receipt=receipt,manifest=manifest,restore_authority=authority)
        with self.assertRaisesRegex(ValueError,'independent isolated'): self.run_delivery()
        self.assertFalse(target.exists())
        # Run the same verified restore operation on an independently identified worker.
        authority['machine_id']='f'*32
        operation=self.base/'independent'
        original=Path.read_text
        def machine(path,*args,**kwargs):
            return 'f'*32 if str(path)=='/etc/machine-id' else original(path,*args,**kwargs)
        (self.source_dir/'data').write_bytes(b'changed after backup')
        with patch.object(Path,'read_text',new=machine):
            result=restic.execute('restore',self.config,self.credentials,self.binary,operation,
                receipt=receipt,expected=manifest,target=target,authority=authority)
        self.assertEqual((target/str(self.source_dir).lstrip('/')/'data').read_bytes(),b'useful tenant data')
        self.assertEqual(result['status'],'RESTORED_FILE_BYTES_VERIFIED_NOT_APPLICATION_ACCEPTED')

    def test_foreign_backup_scope_rejected_before_engine(self):
        self.config['scope']=self.config['scope']|{'tenant_key':'foreign'}
        self.packet('backup','backup')
        with self.assertRaisesRegex(ValueError,'Foreign delivery'): self.run_delivery()
        self.assertEqual(self.calls,[])


if __name__=='__main__': unittest.main()
