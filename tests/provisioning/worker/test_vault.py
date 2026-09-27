"""Vault dynamic role request over verified HTTPS with wrapping guardrails."""
from __future__ import annotations

import json
import ssl
import threading
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from provisioner.controlplane.authority.model import PlanScope, WorkerGrant
from provisioner.controlplane.worker import (GrantDenied, VaultDynamicCredentialIssuer,
                                             VaultDynamicRole)
from tests.provisioning.worker.tls_fixtures import TestPki


class VaultHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.seen.append((self.path, self.headers['X-Vault-Wrap-TTL'],
                                 self.headers['X-Vault-Token']))
        if self.server.mode == 'unwrapped':
            payload = {'data': {'password': 'forbidden'}}
        elif self.server.mode == 'missing-wrap':
            payload = {'data': None}
        else:
            payload = {'data': None, 'auth': None,
                       'wrap_info': {'token': 'one-use-wrapping-token', 'ttl': 30,
                                     'creation_path': 'platform/creds/site-power'}}
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class VaultIssuerTests(unittest.TestCase):
    def setUp(self):
        self.pki = TestPki()
        self.pki.issue('server')
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), VaultHandler)
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(str(self.pki.root / 'server.pem'),
                            str(self.pki.root / 'server.key'))
        self.server.socket = tls.wrap_socket(self.server.socket, server_side=True)
        self.server.mode = 'valid'
        self.server.seen = []
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.scope = PlanScope('org-01', 'tenant-01', 'site-01', 'sd-01',
                               'endpoint-01', 'scope-01', 'vmware')
        now = datetime.now(timezone.utc)
        self.grant = WorkerGrant(
            'grant-01', 'org-01', 'tenant-01', 'plan-01', 1, 'a' * 64,
            self.scope, self.scope, 'worker-01', 'step-01', 'operation-01',
            'VM_POWER', self.scope, 'lease-01', 2, ('approval-01',), 0,
            now, now + timedelta(minutes=2))
        self.token_file = self.pki.write('vault-agent-token', b'agent-scoped-token\n')
        self.token_file.chmod(0o600)
        self.issuer = VaultDynamicCredentialIssuer(
            vault_url=f'https://localhost:{self.server.server_port}',
            ca_bundle=self.pki.root / 'ca.pem', agent_token_file=self.token_file,
            roles=(VaultDynamicRole('vault:site-power',
                                    'platform/creds/site-power', self.scope,
                                    'VM_POWER', timedelta(minutes=2)),))

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.pki.close()

    def issue(self):
        return self.issuer.issue('vault:site-power', grant=self.grant,
                                 expires_at=self.grant.expires_at)

    def test_verified_https_response_wrapping_and_no_secret_repr(self):
        wrapped = self.issue()
        self.assertEqual(wrapped.wrapping_token, 'one-use-wrapping-token')
        self.assertNotIn(wrapped.wrapping_token, repr(wrapped))
        self.assertLessEqual(wrapped.expires_at, self.grant.expires_at)
        self.assertEqual(self.server.seen[0][0], '/v1/platform/creds/site-power')
        self.assertEqual(self.server.seen[0][2], 'agent-scoped-token')

    def test_wrong_scope_kind_and_unsafe_response_fail_closed(self):
        with self.assertRaises(GrantDenied):
            self.issuer.issue('vault:site-power', grant=replace(
                self.grant, operation_kind='VM_CREATE'), expires_at=self.grant.expires_at)
        self.assertFalse(self.server.seen)
        self.server.mode = 'unwrapped'
        with self.assertRaises(GrantDenied):
            self.issue()
        self.server.mode = 'missing-wrap'
        with self.assertRaises(GrantDenied):
            self.issue()

    def test_insecure_agent_token_file_is_rejected(self):
        self.token_file.chmod(0o644)
        with self.assertRaises(GrantDenied):
            self.issue()
        self.assertFalse(self.server.seen)


if __name__ == '__main__':
    unittest.main()
