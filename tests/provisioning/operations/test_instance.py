from copy import deepcopy
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from provisioner.controlplane.authority.service import AuthorityDenied
from provisioner.controlplane.operations.instance import HANDOVER_CHECKS, OperatingInstanceGate, digest
from provisioner.controlplane.persistence import TenantContext
from provisioner.controlplane.workflow.installed_identity import InstalledApplicationIdentity
from tests.provisioning.operations.isolated_instance import commission_isolated_instance
from tests.provisioning.operations.signed_intake_fixtures import RetainedFixture, signed
from tests.provisioning.operations.test_release import TestSigner


class Cursor:
    def __init__(self, row, context, now):
        self.row, self.context, self.now, self.current = row, context, now, None
        self.oid = 42
    def execute(self, query, values=None):
        if 'clock_timestamp()' in query:
            self.current = (self.context.organization_id, self.context.tenant_id, self.now, self.oid)
        elif 'lock_operating_instance' in query:
            self.current = self.row
        else:
            self.current = (self.context.organization_id, self.context.tenant_id)
    def fetchone(self):
        return self.current


class InstanceTests(unittest.TestCase):
    def setUp(self):
        self.context = TenantContext('operating-fixture-org', 'operating-fixture-tenant')
        self.now = datetime.now(timezone.utc)
        self.observer, self.operating = TestSigner('separate-observer-fixture'), TestSigner('separate-handover-fixture')
        self.custody = RetainedFixture(self.context)
        # Cryptographic fixtures cannot commission an actual installed service.
        installation = patch.object(InstalledApplicationIdentity, 'require_current',
                                    return_value=('a' * 40, 'b' * 64))
        installation.start()
        self.addCleanup(installation.stop)
        installed = InstalledApplicationIdentity(Path('/synthetic-not-installed.json'),
            Path('/synthetic-not-installed'), '0' * 64, 'a' * 40, 'b' * 64)
        self.gate = OperatingInstanceGate(evidence_gate=self.custody, observer_verifier=self.observer,
            observer_key_ids=frozenset({self.observer.key_id}), operating_verifier=self.operating,
            operating_key_ids=frozenset({self.operating.key_id}), source_commit='a' * 40,
            artifact_sha256='b' * 64, installed_identity=installed)
        checks = []
        for name in sorted(HANDOVER_CHECKS):
            raw_key = 'observed-' + name
            raw = {'instanceId': 'c' * 32, 'checkId': name, 'sourceCommit': 'a' * 40,
                   'artifactSha256': 'b' * 64, 'measurements': {'syntheticNeverHA': True}}
            self.custody.values[raw_key] = raw
            proof = signed({'format': 'hosting-independent-operating-check/1', 'checkId': name,
                'instanceId': 'c' * 32, 'generation': 2, 'sourceCommit': 'a' * 40, 'artifactSha256': 'b' * 64,
                'observedAt': (self.now - timedelta(minutes=3)).isoformat(),
                'freshUntil': (self.now + timedelta(minutes=30)).isoformat(),
                'observationEventKey': raw_key, 'observationDigest': digest(raw), 'result': 'ACCEPTED'}, self.observer)
            self.custody.values[name] = proof
            checks.append({'id': name, 'eventKey': name, 'sha256': digest(proof)})
        report = {'format': 'hosting-operating-handover-observation/1', 'instanceId': 'c' * 32,
            'generation': 2, 'databaseOid': 42, 'databaseSystemIdentifier': '123456789',
            'sourceCommit': 'a' * 40, 'artifactSha256': 'b' * 64,
            'observedAt': (self.now - timedelta(minutes=2)).isoformat(),
            'freshUntil': (self.now + timedelta(minutes=30)).isoformat(), 'stateDigest': 'd' * 64,
            'checks': checks}
        self.report = signed(report, self.observer)
        acceptance = {'format': 'hosting-operating-instance-handover/1', 'instanceId': 'c' * 32,
            'generation': 2, 'sourceCommit': 'a' * 40, 'artifactSha256': 'b' * 64,
            'reportSha256': digest(self.report), 'acceptedAt': (self.now - timedelta(minutes=1)).isoformat(),
            'reviewUntil': (self.now + timedelta(minutes=20)).isoformat(), 'changeRef': 'fixture-change'}
        self.acceptance = signed(acceptance, self.operating)
        self.custody.values['report-fixture'] = self.report
        self.custody.values['handover-fixture'] = self.acceptance
        self.row = ['c' * 32, 42, 2, 'ACTIVE', self.context.organization_id, self.context.tenant_id,
            'a' * 40, 'b' * 64, 'report-fixture', digest(self.report), 'handover-fixture', digest(self.acceptance),
            self.now + timedelta(minutes=20), '123456789']
        self.cursor = Cursor(self.row, self.context, self.now)

    def test_current_separate_signatures_and_every_original_observation_allow_gate_only(self):
        self.assertIsNone(self.gate.require_write_admission(self.cursor, self.context))
        self.assertFalse(hasattr(self.gate, 'start_writer'))

    def test_observe_modes_missing_acceptance_wrong_database_expiry_and_code_fail_closed(self):
        for column, value in ((3, 'OBSERVATION_ONLY'), (3, 'UNCOMMISSIONED'), (3, 'DRAINED'),
                              (1, 99), (12, self.now), (6, 'f' * 40), (7, 'e' * 64), (2, 3)):
            with self.subTest(column=column, value=value):
                self.cursor.row = list(self.row)
                self.cursor.row[column] = value
                with self.assertRaises(AuthorityDenied):
                    self.gate.require_write_admission(self.cursor, self.context)
        self.cursor.row = None
        with self.assertRaises(AuthorityDenied):
            self.gate.require_write_admission(self.cursor, self.context)

    def test_boolean_claim_or_unsigned_report_and_missing_original_check_never_arm(self):
        self.custody.values['report-fixture'] = {'accepted': True}
        self.cursor.row[9] = digest({'accepted': True})
        with self.assertRaises(AuthorityDenied):
            self.gate.require_write_admission(self.cursor, self.context)
        self.custody.values['report-fixture'] = self.report
        self.cursor.row[9] = digest(self.report)
        del self.custody.values['observed-' + next(iter(HANDOVER_CHECKS))]
        with self.assertRaises(AuthorityDenied):
            self.gate.require_write_admission(self.cursor, self.context)

    def test_revoked_observer_invalid_signature_or_foreign_tenant_prevents_native_gate(self):
        self.report['keyId'] = 'withdrawn-observer'
        self.cursor.row[9] = digest(self.report)
        with self.assertRaises(AuthorityDenied):
            self.gate.require_write_admission(self.cursor, self.context)
        with self.assertRaises(AuthorityDenied):
            self.gate.require_write_admission(self.cursor, TenantContext('foreign', 'foreign'))

    def test_signed_operating_check_cannot_use_binding_metadata_as_original_measurements(self):
        name = next(iter(HANDOVER_CHECKS))
        raw_key = 'observed-' + name
        self.custody.values[raw_key]['measurements'] = {}
        proof = self.custody.values[name]
        proof['payload']['observationDigest'] = digest(self.custody.values[raw_key])
        proof = signed(proof['payload'], self.observer)
        self.custody.values[name] = proof
        for fact in self.report['payload']['checks']:
            if fact['id'] == name:
                fact['sha256'] = digest(proof)
        self.report = signed(self.report['payload'], self.observer)
        self.custody.values['report-fixture'] = self.report
        self.cursor.row[9] = digest(self.report)
        self.acceptance['payload']['reportSha256'] = digest(self.report)
        self.acceptance = signed(self.acceptance['payload'], self.operating)
        self.custody.values['handover-fixture'] = self.acceptance
        self.cursor.row[11] = digest(self.acceptance)
        with self.assertRaises(AuthorityDenied):
            self.gate.require_write_admission(self.cursor, self.context)

    def test_named_observation_requires_current_scope_and_custody_but_no_active_writer(self):
        self.cursor.row = None
        self.gate.require_observation(self.cursor, self.context)
        self.custody.available = False
        with self.assertRaises(ValueError):
            self.gate.require_observation(self.cursor, self.context)

    def test_installed_identity_is_concrete_and_rechecked_for_every_write(self):
        with patch.object(InstalledApplicationIdentity, 'require_current',
                          return_value=('a' * 40, 'b' * 64)) as current:
            installed = InstalledApplicationIdentity(Path('/synthetic-not-installed.json'),
                Path('/synthetic-not-installed'), '0' * 64, 'a' * 40, 'b' * 64)
            gate = OperatingInstanceGate(evidence_gate=self.custody, observer_verifier=self.observer,
                observer_key_ids=frozenset({self.observer.key_id}), operating_verifier=self.operating,
                operating_key_ids=frozenset({self.operating.key_id}), source_commit='a' * 40,
                artifact_sha256='b' * 64, installed_identity=installed)
            current.reset_mock()
            gate.require_write_admission(self.cursor, self.context)
            gate.require_write_admission(self.cursor, self.context)
            self.assertEqual(current.call_count, 4)
            current.side_effect = AuthorityDenied('Actual installed wheel changed')
            with self.assertRaises(AuthorityDenied):
                gate.require_write_admission(self.cursor, self.context)
        with self.assertRaises(ValueError):
            OperatingInstanceGate(evidence_gate=self.custody, observer_verifier=self.observer,
                observer_key_ids=frozenset({self.observer.key_id}), operating_verifier=self.operating,
                operating_key_ids=frozenset({self.operating.key_id}), source_commit='a' * 40,
                artifact_sha256='b' * 64, installed_identity=SimpleNamespace(
                    source_commit='a' * 40, artifact_sha256='b' * 64, require_current=lambda: True))

    def test_absent_installed_identity_is_observation_only_and_cannot_handover(self):
        self.gate.installed_identity = None
        self.gate.require_observation(self.cursor, self.context)
        with self.assertRaises(AuthorityDenied):
            self.gate.require_write_admission(self.cursor, self.context)
        with self.assertRaises(AuthorityDenied):
            self.gate.accept_handover(None, self.context, report_key='report-fixture',
                report_sha256=digest(self.report), handover_key='handover-fixture',
                handover_sha256=digest(self.acceptance))


@unittest.skipUnless(os.environ.get('HOSTING_TEST_POSTGRES_MIGRATION_DSN')
                     and os.environ.get('HOSTING_TEST_POSTGRES_ISOLATED') == '1',
                     'Requires explicit disposable PostgreSQL migration role')
class InstancePostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        from provisioner.controlplane.persistence.migrate import apply_migrations
        cls.psycopg = psycopg
        cls.dsn = os.environ['HOSTING_TEST_POSTGRES_MIGRATION_DSN']
        apply_migrations(lambda: psycopg.connect(cls.dsn))
        commission_isolated_instance(cls.dsn)

    def test_held_instance_cannot_override_readonly_default_to_acquire_writer(self):
        with self.psycopg.connect(self.dsn) as connection:
            # The whole transition rolls back, preserving the shared CI fixture.
            with connection.transaction(force_rollback=True):
                connection.execute("UPDATE hosting_controlplane.operating_instance SET mode='OBSERVATION_ONLY',"
                    'generation=generation+1,updated_at=clock_timestamp() WHERE singleton')
                connection.execute('SET LOCAL default_transaction_read_only=off')
                with self.assertRaises(self.psycopg.errors.InsufficientPrivilege):
                    with connection.transaction():
                        connection.execute('SELECT hosting_controlplane.require_operating_instance_active()')

    def test_restored_foreign_database_oid_and_review_due_hold_current_writer(self):
        for change in ("database_oid=0,mode='OBSERVATION_ONLY'", "review_until=clock_timestamp()"):
            with self.subTest(change=change), self.psycopg.connect(self.dsn) as connection:
                with connection.transaction(force_rollback=True):
                    connection.execute('UPDATE hosting_controlplane.operating_instance SET ' + change +
                        ',generation=generation+1,updated_at=clock_timestamp() WHERE singleton')
                    if 'database_oid' in change:
                        connection.execute("UPDATE hosting_controlplane.operating_instance SET mode='ACTIVE',"
                            'generation=generation+1,updated_at=clock_timestamp() WHERE singleton')
                    with self.assertRaises(self.psycopg.errors.InsufficientPrivilege):
                        with connection.transaction():
                            connection.execute('SELECT hosting_controlplane.require_operating_instance_active()')

    def test_foreign_cluster_identity_is_rejected_even_if_database_oid_is_equal(self):
        with self.psycopg.connect(self.dsn) as connection:
            with connection.transaction(force_rollback=True):
                connection.execute("UPDATE hosting_controlplane.operating_instance SET mode='OBSERVATION_ONLY',"
                    "database_system_identifier='1',generation=generation+1,updated_at=clock_timestamp() WHERE singleton")
                connection.execute("UPDATE hosting_controlplane.operating_instance SET mode='ACTIVE',"
                    'generation=generation+1,updated_at=clock_timestamp() WHERE singleton')
                with self.assertRaises(self.psycopg.errors.InsufficientPrivilege):
                    with connection.transaction():
                        connection.execute('SELECT hosting_controlplane.require_operating_instance_active()')

    def test_monotonic_custody_and_no_delete(self):
        with self.psycopg.connect(self.dsn) as connection:
            for query in ('DELETE FROM hosting_controlplane.operating_instance',
                          "UPDATE hosting_controlplane.operating_instance SET mode='DRAINED'"):
                with self.subTest(query=query), self.assertRaises(self.psycopg.errors.RaiseException):
                    with connection.transaction():
                        connection.execute(query)


if __name__ == '__main__':
    unittest.main()
