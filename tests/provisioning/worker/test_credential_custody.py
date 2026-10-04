"""Actual loopback Vault exchanges and opt-in B10 PostgreSQL custody.

The protocol responses and site authority are synthetic; these tests do not
qualify Vault plugins, native token revocation or production writer exclusion.
"""
from dataclasses import replace
from datetime import timedelta
import json
import os
import ssl
import threading
import unittest
from http.server import ThreadingHTTPServer

from provisioner.controlplane.worker.grants import CredentialBroker,GrantDenied
from provisioner.controlplane.worker.vault import VaultDynamicCredentialIssuer,VaultDynamicRole
from provisioner.controlplane.worker.vault_consumer import VaultCredentialConsumer
from provisioner.controlplane.worker.credential_custody import VaultNativeCredentialLeaseStore
from provisioner.execution.run_files import digest
from tests.provisioning.worker import test_vault as vault_fixture
from tests.provisioning.worker import test_postgres_worker as postgres_fixture


class UnwrapHandler(vault_fixture.VaultHandler):
    def do_POST(self):
        self.server.unwrap_seen.append((self.path,self.headers.get('X-Vault-Token'),
                                       self.headers.get('X-Vault-Namespace')))
        payload={'data':{'format':'synthetic-native-token/1','token':'private-native-token'},
                 'lease_id':'platform/creds/site-power/native-lease-01','lease_duration':30,
                 'auth':None,'wrap_info':None}
        if self.server.unwrap_mode=='no-lease': payload['lease_id']=''
        if self.server.unwrap_mode=='auth-token': payload['auth']={'client_token':'forbidden'}
        if self.server.unwrap_mode=='long-lease': payload['lease_duration']=100000
        if self.server.unwrap_mode=='wrapped': payload['wrap_info']={'token':'forbidden'}
        raw=json.dumps(payload).encode()
        self.send_response(200); self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)


def start_unwrap(test):
    # Reuse only the PKI and selected role fixture, then replace its HTTP owner.
    test.fixture=vault_fixture.VaultIssuerTests(); test.fixture.setUp()
    test.addCleanup(test.fixture.tearDown)
    fixture=test.fixture
    fixture.server.shutdown(); fixture.server.server_close(); fixture.thread.join(timeout=5)
    fixture.server=ThreadingHTTPServer(('127.0.0.1',0),UnwrapHandler)
    tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.load_cert_chain(str(fixture.pki.root/'server.pem'),str(fixture.pki.root/'server.key'))
    fixture.server.socket=tls.wrap_socket(fixture.server.socket,server_side=True)
    fixture.server.mode='valid'; fixture.server.seen=[]
    fixture.server.unwrap_mode='valid'; fixture.server.unwrap_seen=[]
    fixture.thread=threading.Thread(target=fixture.server.serve_forever,daemon=True); fixture.thread.start()


class VaultConsumptionTests(unittest.TestCase):
    def setUp(self):
        start_unwrap(self); fixture=self.fixture
        self.issuer=VaultDynamicCredentialIssuer(vault_url=f'https://localhost:{fixture.server.server_port}',
            ca_bundle=fixture.pki.root/'ca.pem',agent_token_file=fixture.token_file,
            roles=(VaultDynamicRole('vault:site-power','platform/creds/site-power',fixture.scope,
                                    'VM_POWER',timedelta(minutes=2)),),namespace='enrolled-fixture')
        self.consumer=VaultCredentialConsumer(self.issuer)

    def handle(self):
        return self.issuer.issue('vault:site-power',grant=self.fixture.grant,
                                 expires_at=self.fixture.grant.expires_at)

    def test_real_pinned_tls_unwrap_uses_only_single_use_token_and_retains_no_secret_repr(self):
        handle=self.handle(); material=self.consumer.unwrap(handle,self.fixture.grant)
        self.assertEqual(self.fixture.server.unwrap_seen,[('/v1/sys/wrapping/unwrap',
            'one-use-wrapping-token','enrolled-fixture')])
        self.assertEqual(material.lease_digest,digest(b'platform/creds/site-power/native-lease-01'))
        self.assertLessEqual(material.expires_at,handle.expires_at)
        self.assertNotIn('private-native-token',repr(material))
        self.assertNotIn('agent-scoped-token',str(self.fixture.server.unwrap_seen))

    def test_unrevocable_auth_nested_wrap_and_unbounded_native_lease_are_rejected(self):
        for mode in ('no-lease','auth-token','long-lease','wrapped'):
            self.fixture.server.unwrap_mode=mode
            with self.subTest(mode=mode),self.assertRaises(GrantDenied):
                self.consumer.unwrap(self.handle(),self.fixture.grant)

    def test_foreign_grant_or_role_fails_before_actual_unwrap(self):
        handle=self.handle()
        for changed in (replace(self.fixture.grant,grant_id='foreign'),
                        replace(self.fixture.grant,operation_kind='VM_CREATE')):
            with self.assertRaises(GrantDenied): self.consumer.unwrap(handle,changed)
        self.assertFalse(self.fixture.server.unwrap_seen)


@unittest.skipUnless(os.environ.get('HOSTING_TEST_POSTGRES_MIGRATION_DSN') and
    os.environ.get('HOSTING_TEST_POSTGRES_RUNTIME_DSN') and
    os.environ.get('HOSTING_TEST_POSTGRES_ENROLLMENT_DSN') and
    os.environ.get('HOSTING_TEST_POSTGRES_ISOLATED')=='1','Requires isolated PostgreSQL B10 roles')
class CredentialCustodyPostgresTests(unittest.TestCase):
    _tenant=postgres_fixture.WorkerPostgresTests._tenant

    @classmethod
    def setUpClass(cls):
        postgres_fixture.WorkerPostgresTests.setUpClass.__func__(cls)
        from tests.provisioning.operations.isolated_instance import commission_isolated_instance
        commission_isolated_instance(cls.migration_dsn)

    def setUp(self):
        postgres_fixture.WorkerPostgresTests.setUp(self)
        start_unwrap(self)
        self.grant=self.grants.issue_grant(self.context,self.identity,self.request)
        directory=self.fixture.pki.root/'custody'; directory.mkdir(mode=0o700)
        self.store=VaultNativeCredentialLeaseStore(lambda:self.psycopg.connect(self.runtime_dsn),directory=directory)
        self.role=VaultDynamicRole('vault:site-power','platform/creds/site-power',self.scope,
                                  'VM_POWER',timedelta(minutes=2))
        self.issuer=VaultDynamicCredentialIssuer(vault_url=f'https://localhost:{self.fixture.server.server_port}',
            ca_bundle=self.fixture.pki.root/'ca.pem',agent_token_file=self.fixture.token_file,
            roles=(self.role,),lease_store=self.store)

    def rows(self,table):
        with self.psycopg.connect(self.runtime_dsn) as connection:
            self._tenant(connection)
            return connection.execute('SELECT * FROM hosting_controlplane.'+table+
                ' WHERE organization_id=%s AND tenant_id=%s',
                (self.context.organization_id,self.context.tenant_id)).fetchall()

    def issue(self):
        return self.issuer.issue(self.role.reference,grant=self.grant,expires_at=self.grant.expires_at)

    def test_actual_issuer_and_unwrap_append_exact_grant_custody_without_tokens(self):
        handle=self.issue()
        self.assertEqual(len(self.rows('native_credential_attempts')),1)
        self.assertEqual(len(self.rows('native_credential_wrappings')),1)
        self.assertEqual(self.rows('native_credential_leases'),[])
        VaultCredentialConsumer(self.issuer).unwrap(handle,self.grant)
        rows=self.rows('native_credential_leases'); self.assertEqual(len(rows),1)
        self.assertNotIn('private-native-token',str(rows))
        self.assertNotIn('one-use-wrapping-token',str(self.rows('native_credential_wrappings')))
        with self.psycopg.connect(self.runtime_dsn) as connection:
            self._tenant(connection)
            with self.assertRaises(self.psycopg.Error):
                connection.execute('DELETE FROM hosting_controlplane.native_credential_attempts '
                    'WHERE organization_id=%s AND tenant_id=%s',
                    (self.context.organization_id,self.context.tenant_id))

    def test_lost_issuance_keeps_durable_unconsumed_attempt_and_never_claims_expiry_as_fence(self):
        self.fixture.server.mode='missing-wrap'
        with self.assertRaises(GrantDenied): self.issue()
        self.assertEqual(len(self.rows('native_credential_attempts')),1)
        self.assertEqual(self.rows('native_credential_wrappings'),[])
        self.assertEqual(self.rows('native_credential_leases'),[])
        self.assertFalse(hasattr(self.store,'clear_expired'))

    def test_foreign_or_changed_grant_cannot_create_custody_or_contact_vault(self):
        with self.assertRaises(Exception):
            self.store.begin(replace(self.grant,plan_digest='f'*64),self.role)
        self.assertEqual(self.rows('native_credential_attempts'),[])
        self.assertFalse(self.fixture.server.seen)
        with self.psycopg.connect(self.runtime_dsn) as connection:
            connection.execute("SELECT set_config('app.organization_id',%s,true),set_config('app.tenant_id',%s,true)",
                (self.context.organization_id,self.foreign.tenant_id))
            self.assertEqual(connection.execute('SELECT count(*) FROM hosting_controlplane.native_credential_attempts').fetchone(),(0,))

    def test_real_observation_cursor_issues_through_same_b10_transaction_without_second_job_connection(self):
        request=replace(self.request,operation_kind='DISCOVER_READ',step_id='step-read')
        grant=self.grants.issue_grant(self.context,self.identity,request)
        role=VaultDynamicRole('vault:site-read','platform/creds/site-power',self.scope,
                              'DISCOVER_READ',timedelta(minutes=2))
        issuer=VaultDynamicCredentialIssuer(vault_url=f'https://localhost:{self.fixture.server.server_port}',
            ca_bundle=self.fixture.pki.root/'ca.pem',agent_token_file=self.fixture.token_file,
            roles=(role,),lease_store=self.store)
        broker=CredentialBroker(postgres_fixture.TestWorkerVerifier(),self.grants,issuer)
        def competing_connection(): raise AssertionError('A second B10 job connection could self-deadlock')
        self.grants._connect=competing_connection
        with self.psycopg.connect(self.runtime_dsn) as connection,connection.cursor() as cursor:
            self._tenant(connection)
            connection.execute("SET LOCAL statement_timeout='2s'")
            handle=broker.acquire_observation(cursor,self.identity,self.context,grant.grant_id,
                job_id=self.job_id,step_id=request.step_id,operation_id=request.operation_id,
                operation_kind='DISCOVER_READ',operation_scope=self.scope,
                lease_key=request.lease_key,lease_epoch=request.lease_epoch)
            self.assertEqual(handle.grant_id,grant.grant_id)
            self.assertTrue(handle.issuance_id)
            with self.assertRaises(GrantDenied):
                broker.acquire_observation(cursor,self.identity,self.context,grant.grant_id,
                    job_id=self.job_id,step_id=request.step_id,operation_id=request.operation_id,
                    operation_kind='VM_POWER',operation_scope=self.scope,
                    lease_key=request.lease_key,lease_epoch=request.lease_epoch)
        self.assertEqual(len(self.rows('native_credential_attempts')),1)
