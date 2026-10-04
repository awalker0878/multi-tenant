"""Boot denial never restores allows, crosses ownership, or clears native holds."""
from copy import deepcopy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tests.test_nft_edge import fixture
from tests.test_edge_contain import state
from provisioner.execution import edge_boot as boot
from provisioner.execution import nft_edge as edge
from provisioner.execution.run_files import digest,encoded,read_private,write_new


class Kernel:
    def __init__(self,specs): self.specs=specs; self.states={edge.validate(s)[1]:None for s in specs}; self.writes=0; self.fail=False
    def inspect(self,spec):
        value=self.states[edge.validate(spec)[1]]
        return deepcopy(value),digest(encoded(edge.normalized(value)))
    def command(self,args):
        if '--check' in args: return ''
        self.writes+=1
        if self.fail: raise OSError('native boot write failed')
        for spec in self.specs: self.states[edge.validate(spec)[1]]=state(spec)


class EdgeBootTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.base=Path(self.temp.name)
        self.ledger=self.base/'ledger'; self.ledger.mkdir(mode=0o700)
        self.binary=self.base/'nft'; self.binary.write_bytes(b'TEST-ENGINE'); self.binary.chmod(0o700)
        spec=fixture(); spec.update(flows=[],machine_id=Path('/etc/machine-id').read_text().strip(),
            network_namespace_inode=os.stat('/proc/self/ns/net').st_ino,nft_sha256=digest(self.binary.read_bytes()))
        other=deepcopy(spec); other['scope']['tenant_key']='tenant-b'
        other['interfaces']={'domain1':['203.0.113.0/24'],'service0':['198.51.100.0/24']}; other['owned_interfaces']=['domain1']
        self.specs=[spec,other]; self.kernel=Kernel(self.specs)
        self.config={'format':'hosting-edge-boot/1','source_commit':'a'*40,'machine_id':spec['machine_id'],
            'network_namespace_inode':spec['network_namespace_inode'],'nft':str(self.binary),'nft_sha256':spec['nft_sha256'],
            'ledger':str(self.ledger),'specs':[],'boundary_acceptance_ref':'TEST-ONLY','boot_ordering_ref':'TEST-ONLY'}
        for index,item in enumerate(self.specs):
            path=self.base/f'spec-{index}.json'; write_new(path,encoded(item))
            self.config['specs'].append({'path':str(path),'sha256':digest(read_private(path))})
        source=patch.object(boot,'verify',return_value={'status':'HASHES_MATCH','commit':'a'*40}); source.start(); self.addCleanup(source.stop)
    def operate(self,name='run'): return boot.apply(self.config,self.base/name,kernel=self.kernel)
    def test_atomic_host_denial_covers_all_owned_scopes_and_preserves_unknown_head(self):
        scope=edge.validate(self.specs[0])[1]; native=self.ledger/scope; native.mkdir(mode=0o700)
        unknown=encoded({'status':'OUTCOME_UNKNOWN','independent-native-hold':'TEST'})
        write_new(native/'head.json',unknown)
        result=self.operate()
        self.assertEqual(len(result['observations']),2); self.assertEqual(self.kernel.writes,1)
        self.assertFalse(result['production_activation']); self.assertEqual(read_private(native/'head.json'),unknown)
        candidate=(self.base/'run/candidate.nft').read_text()
        self.assertEqual(candidate.count('table inet hosting_'),2)
        self.assertNotIn('counter accept',candidate); self.assertNotIn('flush ruleset',candidate)
    def test_native_failure_never_publishes_ready_receipt(self):
        self.kernel.fail=True
        with self.assertRaises(OSError): self.operate()
        self.assertTrue((self.base/'run/attempt.json').exists()); self.assertFalse((self.base/'run/receipt.json').exists())
    def test_allow_intent_overlap_wrong_machine_and_changed_source_hold(self):
        original=deepcopy(self.config)
        for update in ({'machine_id':'0'*32},{'source_commit':'0'*40}):
            self.config=original|update
            with self.assertRaises(ValueError): self.operate('invalid')
        self.config=original
        item=deepcopy(self.specs[0]); item['flows']=fixture()['flows']
        path=self.base/'allows.json'; write_new(path,encoded(item))
        self.config['specs'][0]={'path':str(path),'sha256':digest(read_private(path))}
        with self.assertRaisesRegex(ValueError,'no allow intent'): self.operate('allows')
        self.assertEqual(self.kernel.writes,0)
    def test_service_has_hard_network_dependency_and_never_removes_policy(self):
        files=boot.service_files('/opt/python/bin/python','/opt/source','/etc/hosting/boot.json',
            '/var/lib/hosting/boot','/var/lib/hosting/ledger','systemd-networkd.service')
        self.assertIn('Before=network-pre.target systemd-networkd.service',files['hosting-edge-boot.service'])
        self.assertEqual(files['network-manager.conf'],'[Unit]\nRequires=hosting-edge-boot.service\nAfter=hosting-edge-boot.service\n')
        self.assertNotIn('ExecStop',files['hosting-edge-boot.service']); self.assertNotIn('PrivateNetwork',files['hosting-edge-boot.service'])
        with self.assertRaises(ValueError): boot.service_files('/opt/python; bad','/source','/config','/output','/ledger','systemd-networkd.service')


if __name__=='__main__': unittest.main()
