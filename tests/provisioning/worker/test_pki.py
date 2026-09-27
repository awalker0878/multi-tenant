"""Worker identity is derived from a real certificate-validated TLS session."""
from __future__ import annotations

import queue
import socket
import ssl
import threading
import unittest

from provisioner.controlplane.worker import GrantDenied, MutualTlsWorkerVerifier
from tests.provisioning.worker.tls_fixtures import TestPki


class WorkerPkiTests(unittest.TestCase):
    def setUp(self):
        self.pki = TestPki()
        self.pki.issue('server')
        self.good_uri = 'spiffe://workers.example/org/org-01/tenant/tenant-01/site/site-01/worker/worker-01'
        self.pki.issue('good', client=True, uri=self.good_uri)
        self.revoked = self.pki.issue('revoked', client=True, uri=self.good_uri)
        self.pki.issue('wrong-site', client=True, uri=self.good_uri.replace('site-01', 'site-02'))
        self.pki.issue('wrong-domain', client=True,
                       uri=self.good_uri.replace('workers.example', 'untrusted.example'))
        self.pki.write_crl([self.revoked.serial_number])
        self.verifier = MutualTlsWorkerVerifier(
            server_certificate=self.pki.root / 'server.pem',
            server_key=self.pki.root / 'server.key',
            trust_bundle=self.pki.root / 'ca.pem', crl_bundle=self.pki.root / 'crl.pem',
            trust_domain='workers.example')
        # Match Python 3.13's default strict X.509 verification on older CI.
        self.verifier.context.verify_flags |= ssl.VERIFY_X509_STRICT

    def tearDown(self):
        self.pki.close()

    def handshake(self, name):
        outcomes = queue.Queue()
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen(1)
            port = listener.getsockname()[1]

            def serve():
                try:
                    raw, _ = listener.accept()
                    with self.verifier.context.wrap_socket(raw, server_side=True) as peer:
                        outcomes.put(self.verifier.verify(peer))
                except Exception as exc:
                    outcomes.put(exc)

            thread = threading.Thread(target=serve, daemon=True)
            thread.start()
            client = ssl.create_default_context(cafile=str(self.pki.root / 'ca.pem'))
            client.verify_flags |= ssl.VERIFY_X509_STRICT
            client.load_cert_chain(str(self.pki.root / (name + '.pem')),
                                   str(self.pki.root / (name + '.key')))
            try:
                with client.wrap_socket(socket.create_connection(('127.0.0.1', port)),
                                        server_hostname='localhost') as peer:
                    peer.sendall(b'worker-present')
            except ssl.SSLError:
                pass  # Server may terminate a rejected TLS session during send.
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())
            return outcomes.get_nowait()

    def test_valid_client_certificate_and_exact_san(self):
        identity = self.handshake('good')
        self.assertNotIsInstance(identity, Exception)
        self.assertEqual((identity.organization_id, identity.tenant_id,
                          identity.site_id, identity.subject),
                         ('org-01', 'tenant-01', 'site-01', 'worker-01'))
        self.assertEqual(len(identity.certificate_sha256), 64)

    def test_revoked_chain_and_wrong_trust_domain_fail(self):
        self.assertIsInstance(self.handshake('revoked'), ssl.SSLError)
        self.assertIsInstance(self.handshake('wrong-domain'), GrantDenied)
        self.assertEqual(self.handshake('wrong-site').site_id, 'site-02')
        with self.assertRaises(GrantDenied):
            self.verifier.verify({'X-Client-Certificate': 'forged'})


if __name__ == '__main__':
    unittest.main()
