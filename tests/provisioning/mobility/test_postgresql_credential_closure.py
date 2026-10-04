"""Actual isolated PostgreSQL custody, no operational database commissioning."""
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from threading import Event
from time import monotonic

from provisioner.controlplane.worker.vault_consumer import VaultCredentialConsumer
from tests.provisioning.worker import test_credential_custody as custody_fixture


@unittest.skipUnless(os.environ.get('HOSTING_TEST_POSTGRES_MIGRATION_DSN') and
    os.environ.get('HOSTING_TEST_POSTGRES_RUNTIME_DSN') and
    os.environ.get('HOSTING_TEST_POSTGRES_ENROLLMENT_DSN') and
    os.environ.get('HOSTING_TEST_POSTGRES_ISOLATED')=='1','Requires isolated PostgreSQL B10 roles')
class PostgresqlCredentialClosureTests(unittest.TestCase):
    _tenant=custody_fixture.CredentialCustodyPostgresTests._tenant
    setUpClass=classmethod(custody_fixture.CredentialCustodyPostgresTests.setUpClass.__func__)
    setUp=custody_fixture.CredentialCustodyPostgresTests.setUp
    rows=custody_fixture.CredentialCustodyPostgresTests.rows
    issue=custody_fixture.CredentialCustodyPostgresTests.issue

    def close_issuance(self):
        with self.psycopg.connect(self.runtime_dsn) as connection:
            self._tenant(connection)
            connection.execute('SELECT hosting_controlplane.lock_native_credential_grant(%s,%s,%s)',
                (self.context.organization_id,self.context.tenant_id,self.grant.grant_id))
            connection.execute('INSERT INTO hosting_controlplane.native_credential_issuance_closures '
                '(organization_id,tenant_id,grant_id,operation_id,selection_digest,closed_by) VALUES(%s,%s,%s,%s,%s,%s)',
                (self.context.organization_id,self.context.tenant_id,self.grant.grant_id,
                 self.grant.operation_id,'a'*64,self.grant.worker_subject))

    def test_original_closure_blocks_later_issuance_before_vault_and_preserves_all_original_custody(self):
        VaultCredentialConsumer(self.issuer).unwrap(self.issue(),self.grant)
        before=len(self.fixture.server.seen);self.close_issuance()
        with self.assertRaisesRegex(ValueError,'durably closed'):self.issue()
        self.assertEqual(len(self.fixture.server.seen),before)
        self.assertEqual(len(self.rows('native_credential_attempts')),1)
        self.assertEqual(len(self.rows('native_credential_leases')),1)
        self.assertEqual(len(self.rows('native_credential_issuance_closures')),1)

    def test_original_closure_cannot_be_mutated_removed_or_observed_by_another_tenant(self):
        self.close_issuance()
        for command in ('UPDATE hosting_controlplane.native_credential_issuance_closures SET selection_digest=%s',
                        'DELETE FROM hosting_controlplane.native_credential_issuance_closures WHERE selection_digest=%s'):
            with self.psycopg.connect(self.runtime_dsn) as connection:
                self._tenant(connection)
                with self.assertRaises(self.psycopg.Error):connection.execute(command,('a'*64,))
        with self.psycopg.connect(self.runtime_dsn) as connection:
            connection.execute("SELECT set_config('app.organization_id',%s,true),set_config('app.tenant_id',%s,true)",
                (self.context.organization_id,self.foreign.tenant_id))
            self.assertEqual(connection.execute('SELECT count(*) FROM hosting_controlplane.native_credential_issuance_closures').fetchone(),(0,))

    def test_scoped_lock_does_not_grant_update_or_expose_another_tenant(self):
        with self.psycopg.connect(self.runtime_dsn) as connection:
            self._tenant(connection)
            self.assertEqual(connection.execute(
                "SELECT has_table_privilege(current_user,'hosting_controlplane.worker_grants','UPDATE')").fetchone(),(False,))
            self.assertEqual(connection.execute(
                'SELECT hosting_controlplane.lock_native_credential_grant(%s,%s,%s)',
                (self.context.organization_id,self.context.tenant_id,self.grant.grant_id)).fetchone(),(self.grant.grant_id,))
            connection.execute("SELECT set_config('app.tenant_id',%s,true)",(self.foreign.tenant_id,))
            self.assertEqual(connection.execute(
                'SELECT hosting_controlplane.lock_native_credential_grant(%s,%s,%s)',
                (self.context.organization_id,self.foreign.tenant_id,self.grant.grant_id)).fetchone(),(None,))
            with self.assertRaises(self.psycopg.errors.InsufficientPrivilege):
                connection.execute('SELECT hosting_controlplane.lock_native_credential_grant(%s,%s,%s)',
                    (self.context.organization_id,self.context.tenant_id,self.grant.grant_id))

    def test_direct_attempt_append_cannot_bypass_durable_closure(self):
        self.close_issuance()
        with self.psycopg.connect(self.runtime_dsn) as connection:
            self._tenant(connection)
            with self.assertRaises(self.psycopg.errors.InsufficientPrivilege):
                connection.execute('INSERT INTO hosting_controlplane.native_credential_attempts '
                    '(organization_id,tenant_id,issuance_id,grant_id,role_reference,creation_path) '
                    'VALUES(%s,%s,%s,%s,%s,%s)',
                    (self.context.organization_id,self.context.tenant_id,'direct-after-closure',
                     self.grant.grant_id,self.role.reference,self.role.api_path))
        self.assertEqual(self.rows('native_credential_attempts'),[])

    def test_repeatable_snapshot_cannot_bypass_current_closure_observation(self):
        with self.psycopg.connect(self.runtime_dsn) as connection:
            connection.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
            self._tenant(connection)
            with self.assertRaises(self.psycopg.errors.InsufficientPrivilege):
                connection.execute('SELECT hosting_controlplane.lock_native_credential_grant(%s,%s,%s)',
                    (self.context.organization_id,self.context.tenant_id,self.grant.grant_id))

    def test_concurrent_issuance_waits_for_original_closure_and_never_contacts_vault(self):
        pending=Queue();pause=Event()
        original_connect=self.store.connect
        def competing_connection():
            connection=original_connect();pending.put(connection.info.backend_pid)
            return connection
        self.store.connect=competing_connection
        with self.psycopg.connect(self.runtime_dsn) as closure:
            self._tenant(closure)
            closure.execute('SELECT hosting_controlplane.lock_native_credential_grant(%s,%s,%s)',
                (self.context.organization_id,self.context.tenant_id,self.grant.grant_id))
            with ThreadPoolExecutor(max_workers=1) as pool:
                future=pool.submit(self.store.begin,self.grant,self.role)
                try:
                    backend=pending.get(timeout=5);deadline=monotonic()+5
                    with self.psycopg.connect(self.migration_dsn,autocommit=True) as observer:
                        while closure.info.backend_pid not in observer.execute(
                            'SELECT pg_blocking_pids(%s)',(backend,)).fetchone()[0]:
                            if monotonic()>=deadline:self.fail('Issuance did not wait on the original grant')
                            pause.wait(.01)
                    closure.execute('INSERT INTO hosting_controlplane.native_credential_issuance_closures '
                        '(organization_id,tenant_id,grant_id,operation_id,selection_digest,closed_by) VALUES(%s,%s,%s,%s,%s,%s)',
                        (self.context.organization_id,self.context.tenant_id,self.grant.grant_id,
                         self.grant.operation_id,'a'*64,self.grant.worker_subject))
                    closure.commit()
                    with self.assertRaisesRegex(ValueError,'durably closed'):future.result(timeout=5)
                finally:closure.rollback()
        self.assertEqual(self.rows('native_credential_attempts'),[])
        self.assertFalse(self.fixture.server.seen)


if __name__=='__main__':unittest.main()
