"""Actual PostgreSQL pagination and authority checks for retained freshness.

This creates monitoring records only in the existing disposable test database.
"""
import os
import unittest

from provisioner.controlplane.discovery.freshness_history import FreshnessHistoryRepository
from provisioner.controlplane.discovery.persistence import DiscoveryRepository
from provisioner.controlplane.persistence.store import AuditContext
from tests.provisioning.controlplane import test_discovery_persistence as support


class ObservedConnection:
    def __init__(self, connection, reads):
        self.connection, self.reads = connection, reads

    def __getattr__(self, name):
        return getattr(self.connection, name)

    def __enter__(self):
        self.connection.__enter__()
        return self

    def __exit__(self, *args):
        return self.connection.__exit__(*args)

    def execute(self, statement, parameters=()):
        if statement.startswith('SELECT ') and 'FROM hosting_controlplane.discovery_freshness_checks' in statement:
            self.reads.append((statement, parameters))
        return self.connection.execute(statement, parameters)


@unittest.skipUnless(os.environ.get('HOSTING_TEST_POSTGRES_DISCOVERY_DSN') and
                     os.environ.get('HOSTING_TEST_POSTGRES_RUNTIME_DSN'),
                     'Requires disposable PostgreSQL discovery/runtime roles')
class FreshnessHistoryPagesPostgresTests(unittest.TestCase):
    setUpClass = classmethod(support.DiscoveryPersistenceTests.setUpClass.__func__)

    def setUp(self):
        support.DiscoveryPersistenceTests.setUp(self)
        self.history = FreshnessHistoryRepository(self.reader)
        self.audit = AuditContext('page-operator', 'history-page')

    def authorize(self, scope, at):
        self.assertEqual(scope, self.scope)
        self.assertIsNotNone(at.tzinfo)

    def capture(self, name):
        return self.history.capture(self.ctx, self.scope, self.environment_id, name,
            audit=self.audit, authorize=self.authorize)

    def page(self, **values):
        return self.history.list_checks(self.ctx, self.scope, self.environment_id,
            authorize=self.authorize, **values)

    def test_cursor_predecessor_and_lookahead_share_one_bounded_real_select(self):
        values = [self.capture('check-' + str(n)) for n in range(3)]
        reads = []
        reader = DiscoveryRepository(lambda: ObservedConnection(
            self.psycopg.connect(self.runtime_dsn), reads))
        page = FreshnessHistoryRepository(reader).list_checks(self.ctx, self.scope,
            self.environment_id, after=1, limit=1, authorize=self.authorize)
        self.assertEqual(page['items'], values[1:2])
        self.assertEqual(page['nextAfter'], 2)
        self.assertEqual(len(reads), 1)
        self.assertEqual(reads[0][1][-2:], (0, 3))

    def test_maximum_page_and_tail_preserve_every_original_without_resampling(self):
        values = [self.capture('check-' + str(n)) for n in range(53)]
        first = self.page(limit=50)
        self.assertEqual(first['items'], values[:50])
        self.assertEqual(first['nextAfter'], 50)
        last = self.page(after=50, limit=50)
        self.assertEqual(last['items'], values[50:])
        self.assertIsNone(last['nextAfter'])
        self.assertEqual(self.page(after=53)['items'], [])
        self.assertEqual(self.page(after=2**63 - 1)['items'], [])
        with self.reader._session(self.ctx) as con:
            count = con.execute("SELECT count(*) FROM hosting_controlplane.audit_events "
                "WHERE record_kind='DiscoveryFreshnessCheck'").fetchone()[0]
        self.assertEqual(count, 53)

    def test_new_checks_between_pages_do_not_change_previously_returned_history(self):
        original = [self.capture('first'), self.capture('second')]
        first = self.page(limit=1)
        third = self.capture('third')
        self.assertEqual(first['items'], original[:1])
        self.assertEqual(self.page(after=first['nextAfter'])['items'], [original[1], third])
        self.assertEqual(self.page(limit=1)['items'], first['items'])

    def test_terminal_page_still_rechecks_live_authority_after_anchor_read(self):
        self.capture('first')
        calls = []
        def revoke(scope, at):
            calls.append(at)
            if len(calls) == 2:
                raise PermissionError('test post-read revocation')
        with self.assertRaises(PermissionError):
            self.history.list_checks(self.ctx, self.scope, self.environment_id,
                after=1, authorize=revoke)
        self.assertEqual(self.page()['items'][0]['sequence'], 1)
