"""Private immutable phase custody; no native database or method qualification."""
from copy import deepcopy
import unittest

from provisioner.execution import execution_journal
from provisioner.execution.run_files import encoded,write_new
from provisioner.migration.activities import MigrationActivityRequest
from provisioner.migration.postgresql_activities import (DatabaseHeld,DatabaseRuntimeBindings,
    FilePostgresqlSelectionStore,PostgresqlSyncActivities)
from provisioner.migration.postgresql_sync import PostgresqlSyncSelection
from tests.provisioning.mobility import test_postgresql_authority as authority_fixture


class PostgresqlActivityCustodyTests(unittest.TestCase):
    def setUp(self):
        selected=authority_fixture.DatabaseAuthorityTests();selected.setUp();self.addCleanup(selected.doCleanups)
        self.selected=selected;self.fixture=selected.fixture
        paths={}
        for name in ('db-selection','db-journals','db-outputs'):
            paths[name]=self.fixture.pki.root/name;paths[name].mkdir(mode=0o700)
        self.store=FilePostgresqlSelectionStore(paths['db-selection'])
        self.descriptor=self.fixture.descriptor
        self.path=self.store.directory/(self.descriptor.sha256+'.json');write_new(self.path,self.descriptor.canonical)
        self.activities=PostgresqlSyncActivities(authority=self.fixture.workers['source'].command.authority,
            selections=self.store,runtimes=DatabaseRuntimeBindings({},{}),journals_directory=paths['db-journals'],
            outputs_directory=paths['db-outputs'],source_root=self.fixture.pki.root)
        self.request=MigrationActivityRequest(self.fixture.admitted,self.fixture.coordination.artifact_digest,
                                             self.descriptor.to_dict()['memberId'])

    def test_lost_phase_response_retains_start_and_never_replays_original_effect(self):
        marker=self.fixture.pki.root/'explicit-unit-effect-marker'
        def original_effect():
            write_new(marker,b'explicit synthetic unit effect, no native database\n')
            raise ConnectionError('Lost original phase result')
        with self.assertRaises(ConnectionError):self.activities._once(self.request,self.descriptor,'DATABASE_INITIAL',original_effect)
        with self.assertRaisesRegex(DatabaseHeld,'ORIGINAL_DATABASE_EFFECT_REQUIRES_RECONCILIATION'):
            self.activities._once(self.request,self.descriptor,'DATABASE_INITIAL',lambda:self.fail('Must not replay'))
        with execution_journal.locked(self.activities._ledger(self.request.admitted.job_id),
            self.activities._phase_scope(self.request,self.descriptor,'DATABASE_INITIAL')) as journal:
            self.assertEqual([row['kind'] for row in journal.events],['DATABASE_PHASE_STARTED'])
        self.assertTrue(marker.is_file())

    def test_completed_original_phase_is_retained_and_observation_never_creates_work(self):
        expected={'selection_sha256':self.descriptor.sha256,'status':'EXPLICIT_UNIT_CUSTODY_ONLY','native_qualification':False}
        self.assertEqual(self.activities._once(self.request,self.descriptor,'DATABASE_INITIAL',lambda:expected),expected)
        original=MigrationActivityRequest(self.request.admitted,self.request.selection_digest,self.request.member_id,'OBSERVE_ORIGINAL')
        self.assertEqual(self.activities._once(original,self.descriptor,'DATABASE_INITIAL',lambda:self.fail('Must not replay')),expected)
        self.assertEqual(self.activities._receipt(original,self.descriptor,'DATABASE_INITIAL'),expected)
        with self.assertRaisesRegex(DatabaseHeld,'ORIGINAL_DATABASE_EFFECT_REQUIRES_RECONCILIATION'):
            self.activities._once(original,self.descriptor,'DATABASE_FINAL',lambda:self.fail('Observe cannot dispatch'))
        with execution_journal.locked(self.activities._ledger(original.admitted.job_id),
            self.activities._phase_scope(original,self.descriptor,'DATABASE_FINAL')) as journal:self.assertEqual(journal.events,[])

    def test_empty_installed_typed_bindings_hold_before_a_new_phase(self):
        with self.assertRaises(DatabaseHeld) as error:self.activities._preflight(self.request)
        self.assertEqual(error.exception.code,'APPLICATION_DATABASE_RUNTIME_UNAVAILABLE')
        self.assertEqual(list(self.activities.journals.iterdir()),[])
        with self.assertRaises(ValueError):DatabaseRuntimeBindings({('job','member','source'):{'allow':True}}, {})

    def test_selected_bytes_digest_protection_and_native_identity_are_immutable(self):
        self.assertEqual(self.store.load(self.descriptor.sha256),self.descriptor)
        body=self.descriptor.to_dict();body['maxRows']=body['maxRows']+1
        self.path.write_bytes(encoded(body))
        with self.assertRaises(ValueError):self.store.load(self.descriptor.sha256)
        self.path.write_bytes(self.descriptor.canonical);self.path.chmod(0o644)
        with self.assertRaises(ValueError):self.store.load(self.descriptor.sha256)
        self.path.chmod(0o600);self.path.unlink()
        real=self.store.directory/'other-private-selection.json';write_new(real,self.descriptor.canonical)
        self.path.symlink_to(real)
        with self.assertRaises((ValueError,OSError)):self.store.load(self.descriptor.sha256)

    def test_unsupported_or_ambiguous_selection_never_becomes_live_method_coverage(self):
        body=self.descriptor.to_dict()
        changes=(lambda row:row.update(maxRows=1001),lambda row:row['sourceGuest'].update(native_uuid='-'*36),
            lambda row:row['source'].update(caFile='/protected/../ca.pem'),
            lambda row:row['source'].update(readRole=row['source']['fenceOwnerRole']),
            lambda row:row['operations']['fence'].update(operationId=row['operations']['source']['operationId']),
            lambda row:row['tables'][0]['columns'][0].update(key=False),
            lambda row:row['tables'][0]['columns'][0].update(typeOid=1184),
            lambda row:row.update(callbackModule='unapproved.factory'))
        for change in changes:
            selected=deepcopy(body);change(selected)
            with self.subTest(selected=selected),self.assertRaises(ValueError):PostgresqlSyncSelection.from_record(selected)


if __name__=='__main__':unittest.main()
