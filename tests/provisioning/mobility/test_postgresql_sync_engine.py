"""Native PostgreSQL17 fixture; independent of platform/method qualification."""
from contextlib import contextmanager
import os
import unittest

import psycopg
from psycopg import sql

from provisioner.migration.postgresql_pgoutput import decode_transactions
from provisioner.migration.postgresql_readback import _no_other_writers,_ACTIVE_WRITERS
from tests.provisioning.mobility.postgresql_sync_fixture import NativeEngineFixture,EngineSession
from tests.provisioning.mobility.prepare_postgresql_sync import PREFIX,native_admin,owner_role


@unittest.skipUnless(os.environ.get(PREFIX+'ISOLATED')=='1','No disposable PostgreSQL17 database sync fixture')
class PostgresqlEngineTests(unittest.TestCase):
    def setUp(self):
        self.fixture=NativeEngineFixture();self.addCleanup(self.fixture.close)
        self.engine=self.fixture.engine;self.body=self.fixture.body

    def test_actual_initial_snapshot_slot_publication_and_disabled_subscription(self):
        self.fixture.insert_initial();result=self.engine.initial_snapshot()
        self.assertEqual(result['status'],'INITIAL_SNAPSHOT_COMMITTED');self.assertEqual(result['rowCount'],3)
        self.assertFalse(result['backgroundApplyEnabled']);self.assertEqual(self.engine.rows(self.fixture.source),self.engine.rows(self.fixture.target))
        self.assertEqual(self.engine.observe_stream(),result['sourcePosition'])
        self.assertEqual(self.fixture.target.execute('SELECT count(pid) FROM pg_stat_subscription WHERE subname=%s',(self.body['subscription'],)).fetchone(),(0,))
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):self.fixture.target.execute('SELECT * FROM hosting_sync.commits')
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):self.fixture.target.execute('SELECT subconninfo FROM pg_subscription')

    def test_whole_committed_changes_apply_before_slot_acknowledgement(self):
        self.fixture.insert_initial();original=self.engine.initial_snapshot()['sourcePosition']
        with self.fixture.writer.transaction():
            self.fixture.source_write('UPDATE {} SET id=%s,body=%s WHERE id=%s',11,'changed',1)
            self.fixture.source_write('DELETE FROM {} WHERE id=%s',2)
            self.fixture.source_write('INSERT INTO {} VALUES(%s,%s)',3,'new')
            self.fixture.writer.execute(sql.SQL('TRUNCATE {}').format(sql.Identifier(self.fixture.schema,'notes')))
        found=self.engine.capture();self.assertEqual(len(found),1)
        self.assertEqual(self.engine.observe_stream(),original)
        self.engine.apply(found[0]);self.assertEqual(self.engine.observe_stream(),original)
        self.assertEqual(self.engine.rows(self.fixture.source),self.engine.rows(self.fixture.target))
        self.engine.acknowledge(found[0]);self.assertEqual(self.engine.capture(),())
        self.assertEqual(self.engine.observe_stream(),found[0].end_lsn)

    def test_atomic_native_target_journal_rolls_back_failed_apply(self):
        self.engine.initial_snapshot()
        with self.fixture.writer.transaction():
            self.fixture.source_write('INSERT INTO {} VALUES(%s,%s)',1,'one')
            self.fixture.source_write('INSERT INTO {} VALUES(%s,%s)',2,'two')
        found=self.engine.capture()[0]
        self.fixture.target.execute(sql.SQL('INSERT INTO {} VALUES(%s,%s)').format(sql.Identifier(self.fixture.schema,'accounts')),(2,'divergence'))
        with self.assertRaises(psycopg.errors.UniqueViolation):self.engine.apply(found)
        self.assertEqual(self.fixture.target.execute(sql.SQL('SELECT id FROM {} ORDER BY id').format(sql.Identifier(self.fixture.schema,'accounts'))).fetchall(),[(2,)])
        self.assertIsNone(self.fixture.target.execute('SELECT hosting_sync.inspect_commit(%s,%s)',(self.body['streamId'],found.end_lsn)).fetchone()[0])
        self.assertNotEqual(self.engine.observe_stream(),found.end_lsn)

    def test_lost_target_commit_receipt_requires_independent_observation_without_reapply(self):
        self.engine.initial_snapshot();self.fixture.source_write('INSERT INTO {} VALUES(%s,%s)',1,'one')
        found=self.engine.capture()[0];actual=self.fixture.target.transaction
        @contextmanager
        def lose_receipt():
            with actual():yield
            raise ConnectionError('fixture lost the actual committed target acknowledgement')
        self.fixture.target.transaction=lose_receipt
        with self.assertRaises(ConnectionError):self.engine.apply(found)
        self.fixture.target.transaction=actual
        known=self.fixture.target.execute('SELECT hosting_sync.inspect_commit(%s,%s)',(self.body['streamId'],found.end_lsn)).fetchone()[0]
        self.assertEqual(known['transactionDigest'],found.digest)
        with self.assertRaisesRegex(ValueError,'independent reconciliation'):self.engine.apply(found)
        self.assertNotEqual(self.engine.observe_stream(),found.end_lsn)

    def test_lost_source_acknowledgement_retains_actual_original_target_commit(self):
        self.engine.initial_snapshot();self.fixture.source_write('INSERT INTO {} VALUES(%s,%s)',1,'one')
        found=self.engine.capture()[0];self.engine.apply(found);actual=self.fixture.source.execute
        def lose_receipt(query,parameters=None):
            result=actual(query,parameters)
            if isinstance(query,str) and 'pg_replication_slot_advance' in query:raise ConnectionError('fixture lost native slot acknowledgement')
            return result
        self.fixture.source.execute=lose_receipt
        with self.assertRaises(ConnectionError):self.engine.acknowledge(found)
        self.fixture.source.execute=actual
        self.assertEqual(self.engine.observe_stream(),found.end_lsn)
        self.assertEqual(self.engine.capture(),())
        with self.assertRaisesRegex(ValueError,'independent reconciliation'):self.engine.apply(found)

    def test_schema_change_and_row_divergence_refuse_final_comparison(self):
        self.fixture.insert_initial();self.engine.initial_snapshot()
        self.fixture.target.execute(sql.SQL('UPDATE {} SET body=%s WHERE id=1').format(sql.Identifier(self.fixture.schema,'accounts')),('wrong',))
        with self.assertRaisesRegex(ValueError,'diverged'):self.engine.compare_locked()
        self.fixture.source.execute(sql.SQL('ALTER TABLE {} ADD COLUMN unapproved text').format(sql.Identifier(self.fixture.schema,'accounts')))
        with self.assertRaisesRegex(ValueError,'schema differs'):self.engine.capture()

    def test_defaults_and_sequences_are_not_inferred_as_replicated(self):
        self.fixture.source.execute(sql.SQL("ALTER TABLE {} ALTER COLUMN body SET DEFAULT 'unselected'").format(sql.Identifier(self.fixture.schema,'accounts')))
        with self.assertRaisesRegex(ValueError,'defaults'):self.engine.initial_snapshot()
        self.fixture.source.execute(sql.SQL('ALTER TABLE {} ALTER COLUMN body DROP DEFAULT').format(sql.Identifier(self.fixture.schema,'accounts')))
        self.fixture.source.execute(sql.SQL('CREATE SEQUENCE {}').format(sql.Identifier(self.fixture.schema,'excluded')))
        with self.assertRaisesRegex(ValueError,'sequences'):self.engine.initial_snapshot()

    def test_publication_change_or_unknown_slot_refuses_apply(self):
        self.engine.initial_snapshot()
        self.fixture.source.execute(sql.SQL('ALTER PUBLICATION {} DROP TABLE {}').format(
            sql.Identifier(self.body['publication']),sql.Identifier(self.fixture.schema,'notes')))
        with self.assertRaisesRegex(ValueError,'table set'):self.engine.capture()
        self.fixture.source.execute(sql.SQL('ALTER PUBLICATION {} ADD TABLE {}').format(
            sql.Identifier(self.body['publication']),sql.Identifier(self.fixture.schema,'notes')))
        self.fixture.source.execute('SELECT pg_drop_replication_slot(%s)',(self.body['slot'],))
        with self.assertRaisesRegex(ValueError,'unavailable'):self.engine.capture()

    def test_actual_database_writer_fence_keeps_engine_running_and_blocks_relogin(self):
        self.fixture.insert_initial();self.engine.initial_snapshot()
        self.fixture.source_write('INSERT INTO {} VALUES(%s,%s)',3,'last committed')
        result=self.fixture.fence.execute('SELECT hosting_sync.fence_application_writers(%s,%s)',
            (self.body['streamId'],self.fixture.selection.sha256)).fetchone()[0]
        self.assertEqual(result['state'],'SELECTED_APPLICATION_WRITERS_FENCED')
        self.assertTrue(result['databaseRunning']);self.assertFalse(result['applicationLoginAllowed'])
        self.assertEqual(self.engine.writer_fence_observation()['activeApplicationSessions'],0)
        with self.assertRaises(psycopg.OperationalError):psycopg.connect(self.fixture.dsns['WRITER'],connect_timeout=2)
        for transaction in self.engine.capture():self.engine.apply(transaction);self.engine.acknowledge(transaction)
        final=self.engine.compare_locked();self.assertEqual(final['pendingSelectedTransactions'],0)
        self.assertFalse(final['sourcePersistentFenceVerified']);self.assertGreaterEqual(final['retainedWalBytes'],0)
        self.assertTrue(final['globalWalBytesIncludeUnpublishedWork'])
        with native_admin(self.fixture.dsns['SETUP'],self.fixture.parsed['SOURCE']['dbname']) as admin:
            admin.execute(sql.SQL('ALTER ROLE {} LOGIN').format(sql.Identifier(self.fixture.parsed['WRITER']['user'])))
        with self.assertRaisesRegex(ValueError,'restored or widened'):self.engine.writer_fence_observation()

    def test_fence_enrollment_and_native_administrator_cannot_be_substituted(self):
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):self.fixture.source.execute(
            'SELECT hosting_sync.fence_application_writers(%s,%s)',(self.body['streamId'],self.fixture.selection.sha256))
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):self.fixture.fence.execute(
            'SELECT hosting_sync.fence_application_writers(%s,%s)',(self.body['streamId'],'b'*64))
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):self.fixture.fence.execute('SELECT * FROM hosting_sync.writer_fences')

    def test_actual_independent_reader_peeks_only_the_enrolled_stream_without_slot_or_table_writes(self):
        original=self.engine.initial_snapshot()['sourcePosition']
        self.fixture.source_write('INSERT INTO {} VALUES(%s,%s)',1,'native reader')
        source=EngineSession(self.fixture.dsns['SOURCE_READER'],owner_role(self.fixture.parsed,'SOURCE_READER'))
        target=EngineSession(self.fixture.dsns['TARGET_READER'],owner_role(self.fixture.parsed,'TARGET_READER'))
        self.addCleanup(source.close);self.addCleanup(target.close)
        source.execute('SET default_transaction_read_only=on');target.execute('SET default_transaction_read_only=on')
        wire=source.execute('SELECT * FROM hosting_sync.peek_source(%s,%s)',
            (self.body['streamId'],self.fixture.selection.sha256)).fetchall()
        transactions=decode_transactions(wire,self.body['tables'],max_changes=1000,max_bytes=4194304)
        self.assertEqual(len(transactions),1);self.assertEqual(self.engine.observe_stream(),original)
        self.assertEqual(target.execute('SELECT hosting_sync.inspect_commit(%s,%s)',
            (self.body['streamId'],original)).fetchone()[0]['kind'],'INITIAL')
        for session in (source,target):
            self.assertTrue(session.execute('SELECT hosting_sync.inspect_directory(%s,%s)',
                (self.body['streamId'],self.fixture.selection.sha256)).fetchone()[0].startswith('/'))
            self.assertEqual(session.execute('SELECT rolsuper,rolreplication,rolcanlogin FROM pg_roles WHERE rolname=current_user').fetchone(),
                (False,False,False))
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):session.execute('SELECT * FROM hosting_sync.commits')
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):source.execute('SELECT pg_replication_slot_advance(%s,%s)',
            (self.body['slot'],transactions[0].end_lsn))
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):source.execute('SELECT * FROM hosting_sync.peek_source(%s,%s)',
            (self.body['streamId'],'b'*64))
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):target.execute('SELECT hosting_sync.record_commit(%s,%s,%s,%s,%s)',
            (self.body['streamId'],transactions[0].end_lsn,transactions[0].digest,self.fixture.selection.sha256,'INCREMENTAL'))
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):target.execute('SELECT subconninfo FROM pg_subscription')
        self.engine.apply(transactions[0]);self.engine.acknowledge(transactions[0])
        self.assertEqual(source.execute('SELECT * FROM hosting_sync.peek_source(%s,%s)',
            (self.body['streamId'],self.fixture.selection.sha256)).fetchall(),[])

    def test_same_name_native_publication_and_table_replacements_do_not_reuse_original_generations(self):
        self.engine.initial_snapshot()
        self.fixture.source.execute(sql.SQL('DROP PUBLICATION {}').format(sql.Identifier(self.body['publication'])))
        self.fixture.source.execute(sql.SQL("CREATE PUBLICATION {} FOR TABLE {},{} WITH (publish='insert,update,delete,truncate')").format(
            sql.Identifier(self.body['publication']),sql.Identifier(self.fixture.schema,'accounts'),sql.Identifier(self.fixture.schema,'notes')))
        with self.assertRaisesRegex(ValueError,'publication was replaced'):self.engine.capture()
        self.fixture.target.execute(sql.SQL('DROP TABLE {}').format(sql.Identifier(self.fixture.schema,'accounts')))
        self.fixture.target.execute(sql.SQL('CREATE TABLE {} (id integer PRIMARY KEY,body text)').format(sql.Identifier(self.fixture.schema,'accounts')))
        with self.assertRaisesRegex(ValueError,'table was replaced'):self.engine.validate()

    def test_native_set_role_delegation_and_active_writer_sessions_are_not_excluded_by_nologin(self):
        table=self.body['tables'][0];name=table['schema']+'.'+table['name']
        login=self.fixture.parsed['SOURCE']['user']
        self.assertEqual(self.fixture.source.execute("SELECT has_table_privilege(%s,%s,'INSERT,UPDATE,DELETE,TRUNCATE')",
            (login,name)).fetchone(),(False,))
        with self.assertRaisesRegex(ValueError,'writer remains available'):_no_other_writers(self.fixture.source,table)
        with native_admin(self.fixture.dsns['SETUP'],self.fixture.parsed['SOURCE']['dbname']) as admin:
            admin.execute(sql.SQL('ALTER ROLE {} NOLOGIN').format(sql.Identifier(login)))
        try:
            self.assertGreater(self.fixture.source.execute(_ACTIVE_WRITERS,(name,)).fetchone()[0],0)
        finally:
            with native_admin(self.fixture.dsns['SETUP'],self.fixture.parsed['SOURCE']['dbname']) as admin:
                admin.execute(sql.SQL('ALTER ROLE {} LOGIN').format(sql.Identifier(login)))

    def test_actual_native_helper_body_or_public_exposure_change_is_held_before_snapshot(self):
        with native_admin(self.fixture.dsns['SETUP'],self.fixture.parsed['SOURCE']['dbname']) as admin:
            original=admin.execute("SELECT prosrc FROM pg_proc WHERE oid='hosting_sync.inspect_directory(text,text)'::regprocedure").fetchone()[0]
            declaration=sql.SQL('CREATE OR REPLACE FUNCTION hosting_sync.inspect_directory(stream text,selection_digest text) RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,hosting_sync AS {}')
            admin.execute(declaration.format(sql.Literal("BEGIN RETURN '/forged-placement'; END;")))
        try:
            with self.assertRaisesRegex(ValueError,'helper definition'):self.engine.initial_snapshot()
        finally:
            with native_admin(self.fixture.dsns['SETUP'],self.fixture.parsed['SOURCE']['dbname']) as admin:
                admin.execute(declaration.format(sql.Literal(original)))
        with native_admin(self.fixture.dsns['SETUP'],self.fixture.parsed['SOURCE']['dbname']) as admin:
            admin.execute('GRANT EXECUTE ON FUNCTION hosting_sync.inspect_directory(text,text) TO PUBLIC')
        try:
            with self.assertRaisesRegex(ValueError,'helper definition'):self.engine.initial_snapshot()
        finally:
            with native_admin(self.fixture.dsns['SETUP'],self.fixture.parsed['SOURCE']['dbname']) as admin:
                admin.execute('REVOKE ALL ON FUNCTION hosting_sync.inspect_directory(text,text) FROM PUBLIC')
        self.assertEqual(self.engine.initial_snapshot()['status'],'INITIAL_SNAPSHOT_COMMITTED')

    def test_actual_native_snapshot_row_and_field_ceiling_hold_without_copying_an_unbounded_response(self):
        self.fixture.writer.execute(sql.SQL('INSERT INTO {} SELECT n,%s FROM generate_series(1,1001) n').format(
            sql.Identifier(self.fixture.schema,'accounts')),('bounded',))
        with self.assertRaisesRegex(ValueError,'row ceiling'):self.engine.initial_snapshot()

    def test_actual_native_snapshot_large_field_is_outside_the_selected_decoder_contract(self):
        self.fixture.source_write('INSERT INTO {} VALUES(%s,%s)',1,'a'*(1024*1024+1))
        with self.assertRaisesRegex(ValueError,'one MiB'):self.engine.initial_snapshot()


if __name__=='__main__':unittest.main()
