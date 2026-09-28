"""Worker listener uses real TLS peer proof before the bounded broker call."""
from __future__ import annotations

import http.client
import json
import ssl
import threading
import unittest
from datetime import datetime, timedelta, timezone

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.worker import GrantDenied, MutualTlsWorkerVerifier
from provisioner.controlplane.reconciliation.registry import NativeLeaseAuthority
from provisioner.controlplane.worker.site_service import (SiteWorkerServer,
    create_site_worker_server)
from provisioner.controlplane.worker.vault import (VaultDynamicCredentialIssuer,
    VaultDynamicRole, VaultWrappedCredential)
from tests.provisioning.worker.tls_fixtures import TestPki


class ExactGrants:
    def __init__(self):
        self.calls = []

    def with_authorized_reference(self, context, identity, grant_id, *, use, **binding):
        self.calls.append((context, identity, grant_id, binding))
        if (identity.subject != 'worker-01' or grant_id != 'grant-01'
                or binding['operation_kind'] != 'DISCOVER_READ'
                or binding['lease_epoch'] != 2):
            raise GrantDenied('Exact grant or B11 lease is unavailable')
        grant = type('Grant', (), {'grant_id': grant_id})()
        return use('vault:site-read', grant, identity.expires_at)


class WrappedIssuer:
    def issue(self, reference, *, grant, expires_at):
        if reference != 'vault:site-read':
            raise GrantDenied('Wrong dynamic role')
        return VaultWrappedCredential('opaque-one-use-token',
                                      'platform/creds/site-read',
                                      min(expires_at,
                                          datetime.now(timezone.utc) + timedelta(seconds=30)),
                                      grant.grant_id)


class SiteWorkerListenerTests(unittest.TestCase):
    def setUp(self):
        self.pki = TestPki()
        self.pki.issue('server')
        uri = 'spiffe://workers.example/org/org-01/tenant/tenant-01/site/site-01/worker/worker-01'
        self.pki.issue('good', client=True, uri=uri)
        self.pki.issue('other-site', client=True,
                       uri=uri.replace('site-01', 'site-02'))
        self.verifier = MutualTlsWorkerVerifier(
            server_certificate=self.pki.root / 'server.pem',
            server_key=self.pki.root / 'server.key',
            trust_bundle=self.pki.root / 'ca.pem',
            crl_bundle=self.pki.root / 'crl.pem',
            trust_domain='workers.example')
        self.scope = PlanScope('org-01', 'tenant-01', 'site-01', 'sd-01',
                               'endpoint-01', 'native-01', 'vmware')
        self.grants = ExactGrants()
        self.server = SiteWorkerServer(
            ('127.0.0.1', 0), site_id='site-01',
            allowed_read_scopes=frozenset({self.scope}),
            verifier=self.verifier, grants=self.grants, issuer=WrappedIssuer())
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.body = {
            'grantId': 'grant-01', 'jobId': 'job-01', 'stepId': 'step-01',
            'operationId': 'operation-01', 'operationKind': 'DISCOVER_READ',
            'scope': {'organizationId': self.scope.organization_id,
                      'tenantId': self.scope.tenant_id,
                      'locationId': self.scope.site_id,
                      'securityDomainId': self.scope.security_domain_id,
                      'endpointId': self.scope.endpoint_id,
                      'nativeScopeId': self.scope.native_scope_id,
                      'platformFamily': self.scope.platform_family},
            'leaseKey': 'lease-01', 'leaseEpoch': 2,
        }

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.pki.close()

    def request(self, body=None, *, worker='good', headers=None,
                path='/v1/worker/credentials', raw=None):
        tls = ssl.create_default_context(cafile=str(self.pki.root / 'ca.pem'))
        if worker is not None:
            tls.load_cert_chain(str(self.pki.root / (worker + '.pem')),
                                str(self.pki.root / (worker + '.key')))
        connection = http.client.HTTPSConnection('localhost', self.server.server_port,
                                                 context=tls, timeout=5)
        try:
            connection.request('POST', path, body=raw if raw is not None else
                               json.dumps(body or self.body),
                               headers={'Content-Type': 'application/json', **(headers or {})})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), json.loads(response.read())
        finally:
            connection.close()

    def test_accepted_tls_peer_is_only_tenant_and_worker_authority(self):
        status, headers, body = self.request()
        self.assertEqual(status, 200)
        self.assertEqual(body['wrappingToken'], 'opaque-one-use-token')
        self.assertEqual(headers['Cache-Control'], 'no-store')
        context, identity, grant_id, binding = self.grants.calls[0]
        self.assertEqual((context.organization_id, context.tenant_id),
                         ('org-01', 'tenant-01'))
        self.assertEqual((identity.subject, identity.site_id), ('worker-01', 'site-01'))
        self.assertEqual((grant_id, binding['lease_key'], binding['lease_epoch']),
                         ('grant-01', 'lease-01', 2))

    def test_native_mutation_wrong_site_and_forwarded_identity_are_held(self):
        mutation = dict(self.body, operationKind='VM_POWER')
        self.assertEqual(self.request(mutation)[0], 423)
        self.assertEqual(self.request(worker='other-site')[0], 403)
        self.assertEqual(self.request(headers={'X-Forwarded-Client-Cert': 'forged'})[0], 400)
        self.assertFalse(self.grants.calls)

    def test_no_client_certificate_or_duplicate_json_cannot_obtain_credential(self):
        with self.assertRaises((ssl.SSLError, OSError, http.client.HTTPException)):
            self.request(worker=None)
        self.assertEqual(self.request(path='/v1/worker/credentials?token=unsafe')[0], 404)
        duplicate = json.dumps(self.body).replace(
            '"grantId": "grant-01"', '"grantId": "grant-01", "grantId": "forged"')
        self.assertEqual(self.request(raw=duplicate)[0], 400)
        self.assertFalse(self.grants.calls)

    def test_production_factory_wires_b11_lease_into_b10_grants(self):
        agent_token = self.pki.write('agent-token', b'agent-token')
        agent_token.chmod(0o600)
        vault = VaultDynamicCredentialIssuer(
            vault_url='https://localhost:8200', ca_bundle=self.pki.root / 'ca.pem',
            agent_token_file=agent_token,
            roles=(VaultDynamicRole('vault:site-read', 'platform/creds/site-read',
                                    self.scope, 'DISCOVER_READ', timedelta(minutes=2)),))
        server = create_site_worker_server(
            ('127.0.0.1', 0), site_id='site-01',
            allowed_read_scopes=frozenset({self.scope}),
            verifier=self.verifier, connect=lambda: None, issuer=vault)
        try:
            self.assertIsInstance(server.broker._grants._leases, NativeLeaseAuthority)
            self.assertIs(server.broker._identities, self.verifier)
        finally:
            server.server_close()


if __name__ == '__main__':
    unittest.main()
