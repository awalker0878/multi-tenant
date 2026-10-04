"""Actual pinned TLS lease retirement; backend responses are synthetic."""
from datetime import timedelta
import ssl
import threading
import unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer

from provisioner.controlplane.worker.native_retirement import _exchange
from provisioner.execution import readback_core as c
from provisioner.execution.run_files import encoded,utcnow
from tests.provisioning.worker import test_vault as fixture_module


class RetirementHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        raw=self.rfile.read(int(self.headers['Content-Length']))
        body=c.strict_loads(raw);self.server.contacts.append((self.path,body))
        revoke=self.path=='/v1/sys/leases/revoke'
        payload=b'' if revoke else encoded({'errors':['invalid lease']})
        status=204 if revoke else 400
        if self.server.mode=='valid-lease' and not revoke:
            status=200;payload=encoded({'data':{'id':body['lease_id']}})
        if self.server.mode=='generic-error' and not revoke:payload=encoded({'errors':['permission denied']})
        if self.server.mode=='async-only' and revoke:status=202
        if self.server.mode=='revoke-with-body' and revoke:payload=b'{}'
        self.send_response(status);self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
    def log_message(self,*_):pass


class NativeRetirementProtocolTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture_module.VaultIssuerTests();self.fixture.setUp();self.addCleanup(self.fixture.tearDown)
        fixture=self.fixture;fixture.server.shutdown();fixture.server.server_close();fixture.thread.join(timeout=5)
        fixture.server=ThreadingHTTPServer(('127.0.0.1',0),RetirementHandler)
        tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(str(fixture.pki.root/'server.pem'),str(fixture.pki.root/'server.key'))
        fixture.server.socket=tls.wrap_socket(fixture.server.socket,server_side=True)
        fixture.server.contacts=[];fixture.server.mode='valid'
        fixture.thread=threading.Thread(target=fixture.server.serve_forever,daemon=True);fixture.thread.start()
        fixture.issuer._port=fixture.server.server_port
        self.issuer=fixture.issuer;self.deadline=utcnow()+timedelta(seconds=30)

    def current(self):return self.deadline

    def test_exact_synchronous_revoke_then_authenticated_invalid_lease(self):
        _exchange(self.issuer,self.current,'revoke','backend/exact-original-lease')
        _exchange(self.issuer,self.current,'lookup','backend/exact-original-lease')
        self.assertEqual(self.fixture.server.contacts,[('/v1/sys/leases/revoke',
            {'lease_id':'backend/exact-original-lease','sync':True}),('/v1/sys/leases/lookup',
            {'lease_id':'backend/exact-original-lease'})])

    def test_existing_lease_generic_denial_and_async_revoke_do_not_prove_exclusion(self):
        for mode,path in [('valid-lease','lookup'),('generic-error','lookup'),('async-only','revoke')]:
            self.fixture.server.mode=mode
            with self.subTest(mode=mode),self.assertRaises(ValueError):
                _exchange(self.issuer,self.current,path,'backend/exact-original-lease')

    def test_expired_authority_and_broad_revocation_routes_never_contact_vault(self):
        self.deadline=utcnow()-timedelta(seconds=1)
        with self.assertRaises(ValueError):_exchange(self.issuer,self.current,'revoke','exact')
        self.deadline=utcnow()+timedelta(seconds=30)
        with self.assertRaises(ValueError):_exchange(self.issuer,self.current,'revoke-prefix','backend/')
        self.assertEqual(self.fixture.server.contacts,[])
