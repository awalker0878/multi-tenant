"""Actual HTTPS retirement and mTLS, explicit synthetic control ledger.

The Vault protocol is synthetic. These tests prove exact request scopes and
unknown-outcome custody; they do not qualify a real Vault PostgreSQL plugin.
"""
from datetime import timedelta
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import socket
import ssl
import threading
import unittest

from provisioner.controlplane.worker.vault import VaultDynamicCredentialIssuer,VaultDynamicRole
from provisioner.migration.postgresql_authority import DatabaseCredentialRetirer
from provisioner.execution.run_files import digest
from tests.provisioning.mobility import test_postgresql_authority as authority_fixture


class _RetirementHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.server.seen.append((self.path,body,self.headers.get('X-Vault-Token')))
        if self.path=='/v1/sys/leases/revoke':
            self.server.revoked.add(body.get('lease_id'))
            if self.server.mode=='lost-revoke':self.connection.shutdown(socket.SHUT_RDWR);self.connection.close();return
            if self.server.mode=='withdrawn':self.server.withdraw()
            payload=b'';status=204
        elif self.path=='/v1/sys/leases/lookup':
            payload=json.dumps({'errors':['invalid lease']} if self.server.mode!='still-usable' else {'data':{'ttl':30}}).encode()
            status=400 if self.server.mode!='still-usable' else 200
        else:payload=b'{}';status=403
        self.send_response(status);self.send_header('Content-Length',str(len(payload)));self.end_headers()
        self.wfile.write(payload)
    def log_message(self,*arguments):pass


class _CustodyCursor:
    def __init__(self,connection):self.connection=connection;self.fixture=connection.test.fixture
    def __enter__(self):return self
    def __exit__(self,*arguments):return False
    def __getattr__(self,name):return getattr(self.fixture.cursor,name)
    def execute(self,query,parameters=()):
        test=self.connection.test
        if query.startswith('SELECT rolsuper, rolbypassrls FROM pg_catalog.pg_roles'):
            self.row=(False,False)
        elif query.startswith('SELECT set_config('):
            assert parameters==(test.guard.runtime.command.context.organization_id,test.guard.runtime.command.context.tenant_id)
            self.row=None
        elif query=='SELECT hosting_controlplane.lock_native_credential_grant(%s,%s,%s)':
            assert parameters[-1]==test.guard.runtime.command.grant.grant_id
            self.row=(parameters[-1],)
        elif query.startswith('INSERT INTO hosting_controlplane.native_credential_issuance_closures'):
            if test.closed:raise ValueError('Original issuance closure already exists')
            test.assertEqual(parameters[2:5],(test.guard.runtime.command.grant.grant_id,
                test.guard.runtime.command.grant.operation_id,test.guard.descriptor.sha256))
            self.connection.pending=True
        elif query.startswith('SELECT a.issuance_id,l.lease_id,l.lease_digest'):
            assert 'FOR SHARE' not in query and parameters[-1]==test.guard.runtime.command.grant.grant_id
            self.rows=test.rows
        else:raise AssertionError('Unexpected synthetic custody query: '+query)
    def fetchone(self):return self.row
    def fetchall(self):return self.rows


class _CustodyConnection:
    def __init__(self,test):self.test=test;self.pending=False;self.autocommit=False
    def __enter__(self):return self
    def __exit__(self,kind,*arguments):
        if kind is None and self.pending:self.test.closed=True
        return False
    def cursor(self):return _CustodyCursor(self)


class PostgresqlRetirementTests(unittest.TestCase):
    def setUp(self):
        selected=authority_fixture.DatabaseAuthorityTests();selected.setUp();self.addCleanup(selected.doCleanups)
        self.selected=selected;self.fixture=selected.fixture;self.closed=False
        registry=self.fixture.workers['source'].registry
        connect=lambda:_CustodyConnection(self)
        registry._connect=connect
        registry.mark_uncertain=lambda context,operation,worker:self.fixture.cursor.intents.__setitem__(
            operation,('UNCERTAIN',)+self.fixture.cursor.intents[operation][1:])
        for worker in self.fixture.workers.values():worker.broker._issuer._lease_store.connect=connect
        self.server=ThreadingHTTPServer(('127.0.0.1',0),_RetirementHandler)
        tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(str(self.fixture.pki.root/'server.pem'),str(self.fixture.pki.root/'server.key'))
        self.server.socket=tls.wrap_socket(self.server.socket,server_side=True)
        self.server.seen=[];self.server.revoked=set();self.server.mode='valid'
        self.server.withdraw=lambda:self.fixture.grants.revoked.add('grant-source')
        thread=threading.Thread(target=self.server.serve_forever,daemon=True);thread.start()
        self.addCleanup(lambda:(self.server.shutdown(),self.server.server_close(),thread.join(timeout=3)))
        token=self.fixture.pki.write('retirement-agent-token',b'explicit-scoped-test-agent\n');token.chmod(0o600)
        runtime=self.fixture.workers['source'];store=runtime.broker._issuer._lease_store
        runtime.broker._issuer=VaultDynamicCredentialIssuer(vault_url=f'https://localhost:{self.server.server_port}',
            ca_bundle=self.fixture.pki.root/'ca.pem',agent_token_file=token,roles=(VaultDynamicRole(
                'vault:selected-source','database/creds/selected-source',runtime.command.grant.operation_scope,
                'RESTORE_DATA',timedelta(minutes=2)),),lease_store=store)
        self.guard=selected.guard();self.guard.claim()
        self.lease='database/creds/selected-source/original-lease'
        self.rows=[('original-issuance',self.lease,digest(self.lease.encode()))]
        self.retirer=DatabaseCredentialRetirer(self.guard)

    def test_exact_synchronous_revoke_and_authenticated_invalid_lease_are_required_before_sealing(self):
        result=self.retirer.close()
        self.assertTrue(self.closed);self.assertTrue(self.guard.sealed)
        self.assertEqual(self.server.seen,[('/v1/sys/leases/revoke',{'lease_id':self.lease,'sync':True},'explicit-scoped-test-agent'),
            ('/v1/sys/leases/lookup',{'lease_id':self.lease},'explicit-scoped-test-agent')])
        self.assertEqual(result['issuances'],[{'issuanceId':'original-issuance','leaseDigest':digest(self.lease.encode())}])
        self.assertNotIn(self.lease,str(result))
        with self.assertRaises(ValueError):self.retirer.close()
        self.assertEqual(len(self.server.seen),2)

    def test_lost_actual_revoke_response_preserves_durable_closure_and_original_uncertainty(self):
        self.server.mode='lost-revoke'
        with self.assertRaises(Exception):self.retirer.close()
        self.assertTrue(self.closed);self.assertIn(self.lease,self.server.revoked);self.assertFalse(self.guard.sealed)
        self.assertEqual(self.fixture.cursor.intents['op-source'][0],'UNCERTAIN')
        with self.assertRaises(Exception):self.retirer.close()
        self.assertEqual([row[0] for row in self.server.seen],['/v1/sys/leases/revoke'])

    def test_still_usable_lease_or_current_grant_withdrawal_never_acknowledges_retirement(self):
        for mode in ('still-usable','withdrawn'):
            with self.subTest(mode=mode):
                self.server.mode=mode;self.closed=False;self.server.seen=[]
                self.fixture.grants.revoked.clear()
                self.fixture.cursor.intents['op-source']=self.fixture.intent('source','IN_FLIGHT')
                with self.assertRaises(Exception):self.retirer.close()
                self.assertTrue(self.closed);self.assertFalse(self.guard.sealed)
                self.assertEqual(self.fixture.cursor.intents['op-source'][0],'UNCERTAIN')
                if mode=='withdrawn':self.assertEqual(len(self.server.seen),1)

    def test_unknown_original_issuance_or_open_native_session_holds_before_revoke(self):
        self.rows.append(('unknown-issuance',None,None))
        with self.assertRaisesRegex(ValueError,'no exact consumed lease'):self.retirer.close()
        self.assertFalse(self.closed);self.assertFalse(self.server.seen)
        self.fixture.cursor.intents['op-source']=self.fixture.intent('source','IN_FLIGHT')
        self.rows.pop();self.guard.sessions.add(object())
        with self.assertRaisesRegex(ValueError,'connections must close'):self.retirer.close()
        self.assertFalse(self.server.seen)


if __name__=='__main__':unittest.main()
