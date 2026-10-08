"""Privilege and ingress invariants for the private dependency renderer."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from stateful.runtime import prepare


class StatefulTopology(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent=Path(tempfile.mkdtemp(prefix='stateful-test-'))
        cls.root=Path(__file__).resolve().parents[2]
        cls.images={name:'sha256:'+'a'*64 for name in ('rabbitmq','temporal','temporal_admin','postgres','probe','minio','mc')}
        cls.path=prepare(cls.root,cls.parent/'runtime',cls.images)
        cls.config=json.loads(cls.path.read_text())

    @classmethod
    def tearDownClass(cls):shutil.rmtree(cls.parent)

    def test_no_host_ingress_or_shared_network(self):
        self.assertTrue(all(n['internal'] for n in self.config['networks'].values()))
        for name,service in self.config['services'].items():
            self.assertNotIn('ports',service)
            if name != 'temporal':self.assertEqual(1,len(service['networks']))

    def test_no_root_or_issuer_material_in_consumers(self):
        for name in ('broker-client','workflow-client','evidence-client','restore-evidence-client','database-client','temporal'):
            mounted={s['source'] for s in self.config['services'][name]['secrets']}
            self.assertFalse(mounted & {'root-password','restore-root-password','jwt-admin','temporal-migrator-password','visibility-migrator-password','ca.key','issuer.key'})
        self.assertNotIn('ca.key',self.config['secrets'])
        self.assertNotIn('issuer.key',self.config['secrets'])

    def test_restore_uses_distinct_credentials_and_volume(self):
        for source,target in [('evidence','evidence-restore'),('evidence-client','restore-evidence-client')]:
            a={s['source'] for s in self.config['services'][source]['secrets']}
            b={s['source'] for s in self.config['services'][target]['secrets']}
            self.assertEqual(a&b,{'ca.crt'} if 'client' in source else set())
        self.assertNotEqual(self.config['services']['evidence']['volumes'][0],self.config['services']['evidence-restore']['volumes'][0])

    def test_temporal_authorization_and_internal_binding(self):
        cfg=json.loads((self.path.parent/'secrets/temporal.yaml').read_text())
        self.assertEqual('default',cfg['global']['authorization']['authorizer'])
        self.assertEqual('default',cfg['global']['authorization']['claimMapper'])
        self.assertEqual('p01-temporal',cfg['global']['authorization']['audience'])
        for name,rpc in cfg['services'].items():
            if name!='frontend':self.assertTrue(rpc['rpc']['bindOnLocalHost'])
        for db in cfg['persistence']['datastores'].values():
            self.assertTrue(db['sql']['tls']['enableHostVerification'])
            self.assertTrue(db['sql']['user'].endswith('_runtime'))

    def test_unpinned_image_rejected_before_directory_creation(self):
        target=self.parent/'bad'
        with self.assertRaises(ValueError):prepare(self.root,target,{**self.images,'minio':'minio:latest'})
        self.assertFalse(target.exists())


if __name__=='__main__':unittest.main()
