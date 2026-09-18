from __future__ import annotations
from pathlib import Path
import socket
import tempfile
import unittest
from lab import mtls_fixture as t


class IdentityTests(unittest.TestCase):
    family=4
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='hosting-test-pki-')
        self.addCleanup(self.temp.cleanup)
        self.m=t.material(Path(self.temp.name))
        self.address='127.0.0.1' if self.family==4 else '::1'
        self.server=t.Service(self.address,0,self.m['server']['certificate'],self.m['server']['key'],self.m['ca'],[self.m['client']['fingerprint']])
        self.addCleanup(self.server.close)
    def call(self,label='client',**kwargs):
        args={} if label is None else {k:self.m[label][k] for k in ('certificate','key')}
        return t.probe(self.address,self.server.port,kwargs.pop('ca',self.m['ca']),**args,**kwargs)
    def test_verified_endpoint_and_identity(self):
        result=self.call();self.assertTrue(result['success']);self.assertEqual(result['tls_version'],'TLSv1.3')
        self.assertEqual(result['server_certificate_sha256'],self.m['server']['fingerprint'])
    def test_wrong_hostname(self):
        self.assertFalse(self.call(hostname='incorrect.fixture.invalid')['success']);self.assertTrue(self.call()['success'])
    def test_other_trusted_tenant_is_resource_denial(self):
        r=self.call('other-tenant');self.assertEqual(r['observation'],'RESOURCE_DENIED')
        self.assertEqual(self.server.stats()['resource_denied'],1)
    def test_expired_and_missing_credentials(self):
        self.assertFalse(self.call('expired')['success']);self.assertFalse(self.call(None)['success'])
        self.assertTrue(self.call()['success'])
    def test_untrusted_chain_both_directions(self):
        self.assertFalse(self.call('foreign')['success']);self.assertFalse(self.call(ca=self.m['other_ca'])['success'])
        self.assertTrue(self.call()['success'])
    def test_overlap_then_withdrawal_closes_existing(self):
        old=f'old-{self.family}';new=f'new-{self.family}'
        self.assertTrue(self.call(retained=old)['success'])
        self.server.grants([self.m['client']['fingerprint'],self.m['rotated']['fingerprint']])
        self.assertTrue(self.call('rotated',retained=new)['success'])
        self.server.grants([self.m['rotated']['fingerprint']])
        self.assertFalse(self.call(retained=old)['success'])
        self.assertFalse(self.call()['success'])
        self.assertTrue(self.call('rotated',retained=new)['success'])
        self.server.grants([])
        self.assertFalse(self.call('rotated',retained=new)['success'])
    def test_plaintext_rejected(self):
        try:
            with socket.create_connection((self.address,self.server.port),timeout=.3) as s:
                s.sendall(b'not a TLS record, do not accept it')
                received=s.recv(64)
                self.assertNotEqual(received,b'OKAY')
        except (ConnectionResetError,socket.timeout):pass
        self.assertTrue(self.call()['success'])
    def test_ambient_keylogging_does_not_export_session_secrets(self):
        from unittest.mock import patch
        path=Path(self.temp.name)/'must-not-exist.log'
        with patch.dict('os.environ',{'SSLKEYLOGFILE':str(path)}):
            self.assertTrue(self.call()['success'])
        self.assertFalse(path.exists())
    def test_private_material_permissions(self):
        for p in Path(self.temp.name).iterdir():self.assertEqual(p.stat().st_mode & 0o777,0o600)
        self.assertEqual(Path(self.temp.name).stat().st_mode & 0o777,0o700)
    def test_generated_credentials_explicitly_local(self):
        self.assertNotEqual(self.m['client']['fingerprint'],self.m['rotated']['fingerprint'])
        self.assertEqual(self.m['client']['identity'],self.m['rotated']['identity'])
        self.assertNotIn('private-key',str(self.server.stats()))


class IPv6EndpointIdentityTests(IdentityTests):
    """Actual ::1 endpoint TLS, NOT routed IPv6, overlay or edge evidence."""
    family=6
