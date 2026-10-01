"""Real PostgreSQL coverage for audited freshness checks, not native qualification."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import os
import threading
import unittest
from unittest import mock

from provisioner.controlplane.discovery.freshness_history import (
    FreshnessHistoryRepository, FreshnessCheckConflict, _LOCK_SQL)
from provisioner.controlplane.discovery.persistence import DiscoveryRepository
from provisioner.controlplane.persistence.store import AuditContext, TenantContext
from tests.provisioning.controlplane import test_discovery_persistence as support

TABLE = 'hosting_controlplane.discovery_freshness_checks'


class InterceptConnection:
    """Inject a failure around real SQL while preserving the real transaction."""
    def __init__(self, connection, intercept):
        self.connection, self.intercept = connection, intercept
    def __getattr__(self, name):
        return getattr(self.connection, name)
    def __enter__(self):
        self.connection.__enter__()
        return self
    def __exit__(self, *args):
        return self.connection.__exit__(*args)
    def execute(self, sql, parameters=()):
        self.intercept(sql, 'before')
        result = self.connection.execute(sql, parameters)
        self.intercept(sql, 'after')
        return result


@unittest.skipUnless(os.environ.get('HOSTING_TEST_POSTGRES_DISCOVERY_DSN') and
                     os.environ.get('HOSTING_TEST_POSTGRES_RUNTIME_DSN'),
                     'Requires disposable PostgreSQL discovery/runtime roles')
class FreshnessHistoryPostgresTests(unittest.TestCase):
    setUpClass = classmethod(support.DiscoveryPersistenceTests.setUpClass.__func__)
    _campaign = support.DiscoveryPersistenceTests._campaign
    _object = support.DiscoveryPersistenceTests._object
    _publish = support.DiscoveryPersistenceTests._publish

    def setUp(self):
        support.DiscoveryPersistenceTests.setUp(self)
        self.history = FreshnessHistoryRepository(self.reader)
        self.audit = AuditContext('history-operator', 'history-request')
        self.source = self._publish(self._campaign('first'), 'PARTIAL',
            (self._object('vm-1', 'First'),), ('VISIBLE_INVENTORY_ONLY',))
        self.revoked = False

    def authorize(self, scope, at):
        self.assertEqual(scope, self.scope)
        self.assertIsNotNone(at.tzinfo)
        if self.revoked:
            raise PermissionError('test revocation')

    def capture(self, check='check-1', **options):
        return self.history.capture(self.ctx, self.scope, self.environment_id, check,
            audit=options.pop('audit', self.audit), authorize=options.pop('authorize', self.authorize), **options)

    def get(self, check='check-1', **options):
        return self.history.get(self.ctx, self.scope, self.environment_id, check,
            authorize=options.pop('authorize', self.authorize), **options)

    def counts(self):
        with self.reader._session(self.ctx) as con:
            rows = con.execute('SELECT count(*) FROM ' + TABLE).fetchone()[0]
            events = con.execute("SELECT count(*) FROM hosting_controlplane.audit_events "
                "WHERE record_kind='DiscoveryFreshnessCheck'").fetchone()[0]
        return rows, events

    def intercept(self, callback):
        return FreshnessHistoryRepository(DiscoveryRepository(
            lambda: InterceptConnection(self.psycopg.connect(self.runtime_dsn), callback)))

    def test_capture_persists_real_metadata_and_exact_audit_binding(self):
        value = self.capture()
        self.assertEqual(value, self.get())
        self.assertEqual(value['report']['observation']['resultDigest'], self.source.result_digest)
        self.assertEqual(value['recordedBy'], self.audit.actor_id)
        self.assertEqual(value['changeKinds'], ['INITIAL_CHECK'])
        self.assertTrue(value['historicalOnly'])
        self.assertFalse(value['executionAuthorized'])
        self.assertFalse(value['notificationAttempted'])
        with self.reader._session(self.ctx) as con:
            event = con.execute("SELECT record_digest, actor_id, revision FROM hosting_controlplane.audit_events "
                "WHERE record_kind='DiscoveryFreshnessCheck'").fetchone()
        self.assertEqual(event, (value['recordDigest'], self.audit.actor_id, 1))
        self.assertEqual(self.counts(), (1, 1))

    def test_retry_never_replaces_original_with_a_newer_generation(self):
        first = self.capture()
        self._publish(self._campaign('new'), 'COMPLETE', (self._object('vm-1', 'New'),))
        with mock.patch.object(self.reader, 'latest_generation', side_effect=AssertionError('retry resampled')):
            self.assertEqual(self.capture(), first)
        second = self.capture('check-2')
        self.assertEqual(second['report']['observation']['generation'], 2)
        self.assertEqual(second['previousRecordDigest'], first['recordDigest'])
        self.assertEqual(second['changeKinds'], ['OBSERVATION_CHANGED', 'COLLECTION_HEALTH_CHANGED'])
        self.assertEqual(self.get(), first)
        self.assertEqual(self.counts(), (2, 2))

    def test_concurrent_identical_check_ids_have_one_record_and_audit(self):
        barrier = threading.Barrier(2)
        def run(_):
            barrier.wait(timeout=5)
            return self.capture()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run, n) for n in range(2)]
            values = [future.result(timeout=15) for future in futures]
        self.assertEqual(values[0], values[1])
        self.assertEqual(self.counts(), (1, 1))

    def test_concurrent_different_actors_cannot_claim_each_others_check(self):
        barrier = threading.Barrier(2)
        def run(actor):
            barrier.wait(timeout=5)
            try:
                return self.capture(audit=AuditContext(actor, actor))['recordedBy']
            except FreshnessCheckConflict:
                return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run, actor) for actor in ('actor-a', 'actor-b')]
            values = [future.result(timeout=15) for future in futures]
        self.assertEqual(values.count('conflict'), 1)
        self.assertIn(self.get()['recordedBy'], values)
        self.assertEqual(self.counts(), (1, 1))

    def test_concurrent_new_ids_form_one_consecutive_chain(self):
        barrier = threading.Barrier(2)
        def run(check):
            barrier.wait(timeout=5)
            return self.capture(check)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run, check) for check in ('check-a', 'check-b')]
            values = sorted([f.result(timeout=15) for f in futures], key=lambda v: v['sequence'])
        self.assertEqual([v['sequence'] for v in values], [1, 2])
        self.assertEqual(values[1]['previousRecordDigest'], values[0]['recordDigest'])
        self.assertEqual(self.counts(), (2, 2))

    def test_authority_is_rechecked_after_real_lock_wait(self):
        entered = threading.Event()
        def authorize(scope, at):
            entered.set()
            self.authorize(scope, at)
        with ThreadPoolExecutor(max_workers=1) as pool:
            with self.psycopg.connect(self.runtime_dsn) as con:
                con.execute(_LOCK_SQL, (self.ctx.organization_id, self.ctx.tenant_id, self.environment_id))
                future = pool.submit(self.capture, authorize=authorize)
                self.assertTrue(entered.wait(timeout=5))
                self.revoked = True
            with self.assertRaises(PermissionError):
                future.result(timeout=15)
        self.assertEqual(self.counts(), (0, 0))

    def test_post_insert_revocation_rolls_back_both_tables(self):
        def after(sql, phase):
            if sql.startswith('INSERT INTO ' + TABLE) and phase == 'after':
                self.revoked = True
        self.history = self.intercept(after)
        with self.assertRaises(PermissionError):
            self.capture()
        self.assertEqual(self.counts(), (0, 0))

    def test_audit_failure_rolls_back_real_insert(self):
        def before(sql, phase):
            if sql.startswith('INSERT INTO hosting_controlplane.audit_events') and phase == 'before':
                raise RuntimeError('test audit failure')
        self.history = self.intercept(before)
        with self.assertRaises(RuntimeError):
            self.capture()
        self.assertEqual(self.counts(), (0, 0))

    def test_tenant_rls_and_exact_native_scope_hide_history(self):
        self.capture()
        other = TenantContext(self.ctx.organization_id, 'other-tenant')
        with self.reader._session(other) as con:
            self.assertEqual(con.execute('SELECT count(*) FROM ' + TABLE).fetchone()[0], 0)
        changed = replace(self.scope, endpoint_id='other-endpoint')
        self.assertIsNone(self.history.get(self.ctx, changed, self.environment_id, 'check-1', authorize=lambda *_: None))
        with self.assertRaises(ValueError):
            self.history.get(other, self.scope, self.environment_id, 'check-1', authorize=lambda *_: None)

    def test_runtime_cannot_update_delete_or_truncate_history(self):
        self.capture()
        for sql in ('UPDATE ' + TABLE + " SET recorded_by='forged'", 'DELETE FROM ' + TABLE, 'TRUNCATE ' + TABLE):
            with self.subTest(sql=sql), self.assertRaises(self.psycopg.errors.InsufficientPrivilege):
                with self.reader._session(self.ctx) as con:
                    con.execute(sql)
        self.assertEqual(self.counts(), (1, 1))

    def test_sql_guards_reject_gaps_wrong_predecessors_and_authority_claims(self):
        from psycopg import sql
        first = self.capture()
        with self.reader._session(self.ctx) as con:
            original = con.execute('SELECT to_jsonb(f) FROM ' + TABLE + ' f').fetchone()[0]
        forged = dict(json.loads(original['report_json']), executionAuthorized=True)
        for changes in ({'sequence': 3}, {'previous_record_digest': 'f' * 64},
                        {'report_json': json.dumps(forged)}, {'environment_id': 'unregistered'}):
            row = {**original, 'check_id': 'check-2', 'sequence': 2,
                   'previous_record_digest': first['recordDigest'], **changes}
            with self.subTest(changes=changes), self.assertRaises(self.psycopg.IntegrityError):
                with self.reader._session(self.ctx) as con:
                    statement = sql.SQL('INSERT INTO ' + TABLE + ' ({}) VALUES ({})').format(
                        sql.SQL(',').join(map(sql.Identifier, row)),
                        sql.SQL(',').join(sql.Placeholder() for _ in row))
                    con.execute(statement, tuple(row.values()))
        self.assertEqual(self.counts(), (1, 1))

    def test_history_pages_retain_originals_with_no_new_audits(self):
        values = [self.capture('check-' + str(i)) for i in range(3)]
        first = self.history.list_checks(self.ctx, self.scope, self.environment_id, limit=2, authorize=self.authorize)
        self.assertEqual(first['items'], values[:2])
        self.assertEqual(first['nextAfter'], 2)
        last = self.history.list_checks(self.ctx, self.scope, self.environment_id, after=2, authorize=self.authorize)
        self.assertEqual(last['items'], values[2:])
        self.assertIsNone(last['nextAfter'])
        self.assertEqual(self.counts(), (3, 3))

    def test_read_revocation_discards_exact_record_and_page(self):
        self.capture()
        for read in (lambda auth: self.get(authorize=auth), lambda auth: self.history.list_checks(
                self.ctx, self.scope, self.environment_id, authorize=auth)):
            calls = []
            def revoke_after_read(scope, at):
                calls.append(at)
                if len(calls) == 2:
                    raise PermissionError('revoked after SQL read')
            with self.assertRaises(PermissionError):
                read(revoke_after_read)
        self.assertEqual(self.counts(), (1, 1))

    def test_site_worker_cannot_read_or_record_checks(self):
        if not self.site_dsn:
            self.skipTest('Requires disposable site-worker role')
        history = FreshnessHistoryRepository(DiscoveryRepository(lambda: self.psycopg.connect(self.site_dsn)))
        with self.assertRaises(PermissionError):
            history.capture(self.ctx, self.scope, self.environment_id, 'worker', audit=self.audit, authorize=self.authorize)
        with self.assertRaises(PermissionError):
            history.list_checks(self.ctx, self.scope, self.environment_id, authorize=self.authorize)

    def test_api_captures_and_reads_real_database_without_job_or_new_inventory(self):
        from fastapi.testclient import TestClient
        from provisioner.controlplane.api import create_app
        from provisioner.controlplane.authority.model import RoleGrant, VerifiedPrincipal
        from provisioner.controlplane.authority.service import AuthorityService, EXECUTION_OPERATOR
        from tests.provisioning.api import test_http as api
        now = datetime.now(timezone.utc)
        principal = VerifiedPrincipal('history-api-operator', self.ctx.organization_id, self.ctx.tenant_id,
            'HUMAN', now-timedelta(minutes=1), now+timedelta(minutes=5), None,
            (RoleGrant(EXECUTION_OPERATOR, self.scope, now+timedelta(minutes=5)),))
        class Identity:
            def authenticate(self, token):
                if token != 'test-history-token':
                    raise PermissionError('invalid fixture credential')
                return principal
        class Evidence:
            def require(inner, ctx):
                if ctx != self.ctx:
                    raise PermissionError('wrong test tenant')
        jobs = api._Jobs()
        app = create_app(api._Records(), AuthorityService(Identity(), api._Plans(), api._Ledger()),
            jobs, self.environments, discovery=self.reader, evidence_gate=Evidence())
        base = f'/v1/environments/{self.environment_id}/discovery/freshness/checks'
        with TestClient(app) as client:
            headers = {'Authorization': 'Bearer test-history-token'}
            result = client.put(base + '/check-api', json={}, headers=headers)
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(result.json()['recordedBy'], principal.subject)
            self.assertEqual(client.get(base + '/check-api', headers=headers).json(), result.json())
            self.assertEqual(client.put(base + '/check-api', json={}, headers=headers).json(), result.json())
            self.assertEqual(client.get(base, headers=headers).json()['items'], [result.json()])
        self.assertEqual(self.counts(), (1, 1))
        self.assertEqual(jobs.submissions, [])
        self.assertEqual(self.reader.latest_generation(self.ctx, self.scope, self.environment_id), self.source)
