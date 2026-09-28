"""Destination-scoped restore evidence remains bound to source and live authority."""
from pathlib import Path
import unittest
from unittest.mock import patch

from tools import delivery_steps as steps, restic_run
from tools.run_files import digest, encoded, load_private, read_private, write_new


class DeliveryTransferTests(unittest.TestCase):
    def setUp(self):
        from tests.test_restic_transfer import TransferTests
        self.fixture=TransferTests(); self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        f=self.fixture
        binary=f.root/'restic'; binary.write_bytes(b'fixture-only'); binary.chmod(0o700)
        f.config['restic_sha256']=digest(binary.read_bytes())
        f.envelope['source_config_sha256']=digest(encoded(f.config))
        f.restore_authority['config_sha256']=digest(encoded(f.config))
        f.configure_authority()
        self.step={'id':'restore','kind':'restic','needs':[]}
        self.plan={'scope':f.envelope['destination_execution_scope'],'steps':[self.step]}
        self.packet={'parameters':{'action':'restore','restic':str(binary),
            'restic_sha256':f.config['restic_sha256'],'target':str(f.target)},'files':{}}
        for name,value in dict(config=f.config,credentials={},receipt=f.receipt,manifest=f.manifest,
                               restore_authority=f.restore_authority,transfer_manifest=f.envelope).items():
            path=f.root/(name+'.json'); write_new(path,encoded(value))
            self.packet['files'][name]={'path':str(path),'sha256':digest(read_private(path))}
        self.directory=f.root/'steps/restore'; self.directory.mkdir(mode=0o700,parents=True)
        self.directory.parent.chmod(0o700)
        self.engine=patch.object(restic_run,'Restic',return_value=f.engine)
        self.engine.start(); self.addCleanup(self.engine.stop)
        original=Path.read_text
        def machine(path,*args,**kwargs):
            return 'f'*32 if str(path)=='/etc/machine-id' else original(path,*args,**kwargs)
        self.machine=patch.object(Path,'read_text',new=machine)
        self.machine.start(); self.addCleanup(self.machine.stop)

    def dispatch(self,**kwargs):
        return steps.dispatch(self.step,self.packet,self.directory,self.fixture.root,self.plan,
                              restic_run.ROOT,**kwargs)

    def recover(self):
        return steps.recover(self.step,self.packet,self.directory,self.fixture.root,self.plan,restic_run.ROOT)

    def test_file_transfer_manifest_alone_is_held_before_repository_contact(self):
        with self.assertRaisesRegex(ValueError,'live trusted worker'):
            self.dispatch()
        self.assertEqual(self.fixture.calls,[])
        self.assertFalse(self.fixture.target.exists())

    def test_trusted_transfer_emits_separate_source_and_destination_receipts(self):
        result,names=self.dispatch(transfer_guard=self.fixture.guard)
        self.assertEqual(result['scope'],self.plan['scope'])
        source=load_private(self.directory/'receipt.json')
        self.assertEqual(source['scope'],self.fixture.config['scope'])
        self.assertNotEqual(source['scope'],result['scope'])
        self.assertIn('transfer-receipt.json',names)
        self.assertEqual(result['source_receipt_sha256'],digest(encoded(self.fixture.receipt)))

    def test_completed_transfer_recovers_without_replaying_repository_commands(self):
        with patch.object(steps,'complete',side_effect=InterruptedError('coordinator lost')):
            with self.assertRaises(InterruptedError): self.dispatch(transfer_guard=self.fixture.guard)
        calls=list(self.fixture.calls)
        result,names=self.recover()
        self.assertEqual(result['scope'],self.plan['scope'])
        self.assertEqual(self.fixture.calls,calls)
        self.assertIn('transfer-receipt.json',names)

    def test_missing_destination_receipt_cannot_be_reconstructed_or_replayed(self):
        with patch.object(steps,'complete',side_effect=InterruptedError('coordinator lost')):
            with self.assertRaises(InterruptedError): self.dispatch(transfer_guard=self.fixture.guard)
        (self.directory/'execution/transfer-receipt.json').unlink()
        calls=list(self.fixture.calls)
        with self.assertRaises(OSError): self.recover()
        self.assertEqual(self.fixture.calls,calls)
        self.assertFalse((self.directory/'owner-completion.json').exists())

    def test_destination_scope_cannot_be_substituted_by_packet_metadata(self):
        self.plan['scope']=self.plan['scope']|{'tenant_key':'foreign'}
        with self.assertRaisesRegex(ValueError,'Foreign delivery'):
            self.dispatch(transfer_guard=self.fixture.guard)
        self.assertEqual(self.fixture.calls,[])


if __name__=='__main__': unittest.main()
