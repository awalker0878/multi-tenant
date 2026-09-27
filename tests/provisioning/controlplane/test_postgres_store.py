"""Real PostgreSQL tests; CI supplies dedicated migration/runtime DSNs."""
from __future__ import annotations

import os
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from uuid import uuid4

from provisioner.controlplane.persistence import (
    AuditContext, EnterpriseRecordStore, LeaseConflict, NativeBinding,
    OwnershipConflict, RecordNotFound, RevisionConflict, TenantContext,
)
from provisioner.controlplane.persistence.migrate import apply_migrations
from tests.provisioning.schema.test_enterprise_records import SOURCE, binding, workload


class PostgresStoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.migration_dsn = os.environ.get('HOSTING_TEST_POSTGRES_MIGRATION_DSN')
        cls.runtime_dsn = os.environ.get('HOSTING_TEST_POSTGRES_RUNTIME_DSN')
        if not cls.migration_dsn or not cls.runtime_dsn:
            raise unittest.SkipTest('Set both PostgreSQL migration/runtime DSNs')
        try:
            import psycopg
            from psycopg import sql
        except ImportError as exc:
            raise unittest.SkipTest('Install hosting-provisioner[controlplane]') from exc
        cls.psycopg = psycopg
        applied = apply_migrations(lambda: psycopg.connect(cls.migration_dsn))
        assert isinstance(applied, list)
        with psycopg.connect(cls.runtime_dsn) as connection:
            cls.runtime_role = connection.execute('SELECT current_user').fetchone()[0]
            role = connection.execute(
                'SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user'
            ).fetchone()
            if role is None or role[0] or role[1]:
                raise RuntimeError('Integration test requires a real NOBYPASSRLS runtime role')
        with psycopg.connect(cls.migration_dsn) as connection:
            runtime = sql.Identifier(cls.runtime_role)
            for statement in (
                sql.SQL('GRANT USAGE ON SCHEMA hosting_controlplane TO {}'),
                sql.SQL('GRANT SELECT, INSERT, UPDATE ON hosting_controlplane.enterprise_records TO {}'),
                sql.SQL('GRANT SELECT, INSERT ON hosting_controlplane.enterprise_record_history TO {}'),
                sql.SQL('GRANT SELECT, INSERT ON hosting_controlplane.audit_events TO {}'),
                sql.SQL('GRANT SELECT, INSERT, UPDATE ON hosting_controlplane.native_ownership TO {}'),
                sql.SQL('GRANT USAGE ON ALL SEQUENCES IN SCHEMA hosting_controlplane TO {}'),
            ):
                connection.execute(statement.format(runtime))
        cls.store = EnterpriseRecordStore(lambda: psycopg.connect(cls.runtime_dsn))

    def setUp(self):
        suffix = uuid4().hex[:12]
        self.ctx = TenantContext('org-' + suffix, 'tenant-a')
        self.other = TenantContext(self.ctx.organization_id, 'tenant-b')
        self.audit = AuditContext('operator-01', 'test-' + suffix)

    def _workload(self, ctx: TenantContext) -> dict:
        record = workload()
        record['metadata']['organizationId'] = ctx.organization_id
        record['metadata']['tenantId'] = ctx.tenant_id
        record['spec']['machines'][0]['bindings'][0]['binding']['nativeId'] = (
            'vm-' + ctx.organization_id)
        return record

    def test_tenant_isolation_revision_history_and_append_only_audit(self):
        first = self._workload(self.ctx)
        second = self._workload(self.other)
        self.store.create(self.ctx, first, self.audit)
        self.store.create(self.other, second, self.audit)
        self.assertEqual(self.store.get(self.ctx, 'Workload', 'workload-01').record,
                         first)
        self.assertEqual(self.store.get(self.other, 'Workload', 'workload-01').record,
                         second)
        self.assertIsNone(self.store.get(TenantContext(self.ctx.organization_id, 'foreign'),
                                         'Workload', 'workload-01'))
        with self.assertRaises(RecordNotFound):
            self.store.update(self.ctx, second, 1, self.audit)
        next_record = deepcopy(first)
        next_record['metadata']['revision'] = 2
        next_record['spec']['name'] = 'renamed-after-review'
        saved = self.store.update(self.ctx, next_record, 1, self.audit)
        self.assertEqual(saved.revision, 2)
        with self.assertRaises(RevisionConflict):
            self.store.update(self.ctx, next_record, 1, self.audit)
        self.assertEqual([r.revision for r in self.store.list(self.ctx, 'Workload',
                                                               wsd_id='wsd-01')], [2])
        self.assertEqual(self.store.list(self.ctx, 'Workload', wsd_id='wsd-02'), [])
        with self.psycopg.connect(self.runtime_dsn) as connection:
            connection.execute(
                "SELECT set_config('app.organization_id', %s, true), "
                "set_config('app.tenant_id', %s, true)",
                (self.ctx.organization_id, self.ctx.tenant_id))
            history = connection.execute(
                'SELECT revision FROM hosting_controlplane.enterprise_record_history '
                "WHERE record_kind = 'Workload' AND record_id = 'workload-01' "
                'ORDER BY revision').fetchall()
            audit = connection.execute(
                'SELECT action, revision, actor_id, correlation_id '
                'FROM hosting_controlplane.audit_events ORDER BY event_id').fetchall()
            self.assertEqual(history, [(1,), (2,)])
            self.assertEqual(audit, [('RECORD_CREATE', 1, self.audit.actor_id,
                                       self.audit.correlation_id),
                                      ('RECORD_UPDATE', 2, self.audit.actor_id,
                                       self.audit.correlation_id)])
            with self.assertRaises(self.psycopg.Error):
                connection.execute('UPDATE hosting_controlplane.audit_events '
                                   "SET action='RECORD_CREATE'")

    def test_competing_revision_writers_have_one_winner(self):
        first = self._workload(self.ctx)
        self.store.create(self.ctx, first, self.audit)

        def revise(name: str):
            candidate = deepcopy(first)
            candidate['metadata']['revision'] = 2
            candidate['spec']['name'] = name
            try:
                return self.store.update(self.ctx, candidate, 1, self.audit).revision
            except RevisionConflict:
                return 'conflict'

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(revise, ('candidate-a', 'candidate-b')))
        self.assertCountEqual(outcomes, [2, 'conflict'])
        self.assertEqual(self.store.get(self.ctx, 'Workload', 'workload-01').revision, 2)

    def test_native_ownership_epoch_and_foreign_tenant_collision(self):
        self.store.create(self.ctx, self._workload(self.ctx), self.audit)
        self.store.create(self.other, self._workload(self.other), self.audit)
        scope = deepcopy(SOURCE)
        scope.update(organizationId=self.ctx.organization_id, tenantId=self.ctx.tenant_id)
        native = NativeBinding.from_record(binding('vm', 'vm-' + self.ctx.organization_id))
        wrong_wsd_scope = dict(scope, securityDomainId='wsd-02')
        with self.assertRaises(OwnershipConflict):
            self.store.acquire_owner_lease(self.ctx, wrong_wsd_scope,
                                           native,
                                           'workload-01', 'worker-z', 60, self.audit)
        with self.assertRaises(OwnershipConflict):
            self.store.acquire_owner_lease(
                self.ctx, scope,
                NativeBinding.from_record(binding('vm', 'unobserved-' + self.ctx.organization_id)),
                'workload-01', 'worker-z', 60, self.audit)
        initial = self.store.acquire_owner_lease(self.ctx, scope, native,
                                                 'workload-01', 'worker-a', 60, self.audit)
        self.assertTrue(self.store.has_current_owner_lease(self.ctx, initial))
        with self.assertRaises(OwnershipConflict):
            self.store.acquire_owner_lease(self.ctx, scope, native,
                                           'workload-01', 'worker-b', 60, self.audit)
        foreign_scope = dict(scope, tenantId=self.other.tenant_id)
        with self.assertRaises(OwnershipConflict):
            self.store.acquire_owner_lease(self.other, foreign_scope, native,
                                           'workload-01', 'worker-c', 60, self.audit)
        renewed = self.store.renew_owner_lease(self.ctx, initial, 60, self.audit)
        self.assertEqual(renewed.epoch, initial.epoch)
        released_epoch = self.store.release_owner_lease(self.ctx, renewed, self.audit)
        self.assertFalse(self.store.has_current_owner_lease(self.ctx, renewed))
        with self.assertRaises(LeaseConflict):
            self.store.renew_owner_lease(self.ctx, renewed, 60, self.audit)
        next_lease = self.store.acquire_owner_lease(self.ctx, scope, native,
                                                   'workload-01', 'worker-b', 60, self.audit)
        self.assertEqual(next_lease.epoch, released_epoch + 1)

    def test_migration_is_idempotent(self):
        self.assertEqual(apply_migrations(lambda: self.psycopg.connect(
            self.migration_dsn)), [])

    def test_expired_lease_is_held_until_reconciliation(self):
        self.store.create(self.ctx, self._workload(self.ctx), self.audit)
        scope = deepcopy(SOURCE)
        scope.update(organizationId=self.ctx.organization_id, tenantId=self.ctx.tenant_id)
        native = NativeBinding.from_record(binding('vm', 'vm-' + self.ctx.organization_id))
        lease = self.store.acquire_owner_lease(self.ctx, scope, native,
                                               'workload-01', 'worker-a', 1, self.audit)
        time.sleep(1.1)
        self.assertFalse(self.store.has_current_owner_lease(self.ctx, lease))
        with self.assertRaises(OwnershipConflict):
            self.store.acquire_owner_lease(self.ctx, scope, native,
                                           'workload-01', 'worker-b', 60, self.audit)
