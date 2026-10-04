"""Actual isolated PostgreSQL custody, no operational database commissioning."""
import os
import unittest

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
            connection.execute('SELECT grant_id FROM hosting_controlplane.worker_grants '
                'WHERE organization_id=%s AND tenant_id=%s AND grant_id=%s FOR UPDATE',
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


if __name__=='__main__':unittest.main()
