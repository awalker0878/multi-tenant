"""Real cross-tenant wave locks, original B09 admission and retained charges.

External IAM/native budgets here are isolated synthetic fixtures. They do not
commission a native estate or establish a migration qualification claim.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import os
import unittest
from unittest.mock import patch
from uuid import uuid4

from provisioner.controlplane.jobs.repository import _tenant
from provisioner.controlplane.persistence import TenantContext
from provisioner.migration.enterprise_wave import EnterpriseWavePool, PoolDomain
from tests.provisioning.mobility import test_wave_schedule_postgres as original_wave


@unittest.skipUnless(os.environ.get('HOSTING_TEST_POSTGRES_DSN') and
                     os.environ.get('HOSTING_TEST_POSTGRES_MIGRATION_DSN') and
                     os.environ.get('HOSTING_TEST_POSTGRES_ISOLATED') == '1',
                     'Requires explicitly isolated PostgreSQL admin and non-bypass migration roles')
class EnterpriseWavePostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        original_wave.WavePostgresTests.setUpClass()

    def setUp(self):
        self.a, self.b = original_wave.WavePostgresTests(), original_wave.WavePostgresTests()
        self.a.setUp(); self.b.setUp()
        self.b.ctx = TenantContext(self.a.ctx.organization_id, 'tenant-b')
        for fixture, names in ((self.a, ('a1', 'a2')), (self.b, ('b1', 'b2'))):
            for name in names:
                fixture.add_member(name)
            fixture.enroll(); fixture.register()

    def pool(self, *, jobs=8, risk=8):
        budget = replace(self.a.domain.budget, concurrent_jobs=jobs, risk_units=risk)
        now = datetime.now(timezone.utc)
        result = EnterpriseWavePool('pool-'+uuid4().hex,
            tuple(PoolDomain.from_domain(f.domain, {'native-risk':'physical-cluster'})
                  for f in (self.a, self.b)), budget, (('physical-cluster', risk),),
            'c'*64, now-timedelta(minutes=1), now+timedelta(hours=1))
        with self.a.migration() as connection:
            connection.execute('INSERT INTO hosting_controlplane.enterprise_wave_pools '
                '(pool_id,document_digest,document_json,enrolled_by) VALUES(%s,%s,%s::jsonb,%s)',
                (result.pool_id, result.digest, json.dumps(result.to_record()),
                 'isolated-synthetic-native-budget-fixture'))
        return result

    def ticket(self, fixture, member):
        with fixture.runtime() as connection, connection.cursor() as cursor:
            _tenant(cursor, fixture.ctx)
            cursor.execute('SELECT hosting_controlplane.migration_wave_pool_turn(%s,%s,%s,%s,%s,%s,'
                           "clock_timestamp()+interval '20 seconds')",
                (fixture.ctx.organization_id, fixture.ctx.tenant_id, fixture.domain.domain_id,
                 fixture.definition.digest, member, fixture.principal.subject))
            return cursor.fetchone()[0]

    def test_distinct_tenant_races_share_one_budget_and_original_outbox(self):
        self.pool(jobs=1)
        self.ticket(self.a, 'a1'); self.ticket(self.b, 'b1')
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = [f.result(timeout=20) for f in
                       (executor.submit(self.a.admit), executor.submit(self.b.admit))]
        self.assertEqual(sum(row.status == 'JOB_QUEUED' for row in results), 1)
        self.assertEqual(self.a.counts()[:2], (1,1))
        self.assertEqual(self.b.counts()[:2], (0,0))
        self.assertFalse(any(row.mutation_authorized for row in results))

    def test_one_turn_per_tenant_prevents_split_wave_starvation(self):
        self.pool()
        self.assertEqual(self.a.admit().member_id, 'a1')
        self.assertTrue(self.ticket(self.b, 'b1'))
        self.assertEqual(self.a.admit().status, 'WAITING_ENTERPRISE_TURN')
        self.assertEqual(self.b.admit().member_id, 'b1')
        self.assertEqual(self.a.admit().member_id, 'a2')
        self.assertEqual(self.a.counts()[:2], (2,2))
        self.assertEqual(self.b.counts()[:2], (1,1))

    def test_unknown_job_retains_global_physical_risk_and_resource_charge(self):
        self.pool(risk=1)
        first = self.a.admit()
        self.a.jobs.append_progress(self.a.ctx, first.job_id, event_key='lost-original-native',
            event_type='NATIVE_OUTCOME_UNKNOWN', status='HELD',
            detail={'stepId':'transfer','phase':'TRANSFER','reasonCode':'NATIVE_UNCERTAIN'})
        self.assertEqual(self.b.admit().status, 'WAITING_ENTERPRISE_TURN')
        self.assertEqual(self.a.scheduler.reconcile_release('synthetic-verified-session',
            self.a.ctx, self.a.definition.digest, 'a1'), 'HELD_NATIVE_RELEASE_ACCEPTANCE_REQUIRED')
        self.assertEqual(self.b.counts()[:2], (0,0))

    def test_tenant_blocked_by_shared_native_risk_does_not_starve_a_fitting_tenant(self):
        third = original_wave.WavePostgresTests()
        third.setUp()
        third.ctx = TenantContext(self.a.ctx.organization_id, 'tenant-c')
        third.add_member('c1'); third.enroll(); third.register()
        now = datetime.now(timezone.utc)
        pool = EnterpriseWavePool('pool-'+uuid4().hex,
            (PoolDomain.from_domain(self.a.domain, {'native-risk':'cluster-ab'}),
             PoolDomain.from_domain(self.b.domain, {'native-risk':'cluster-ab'}),
             PoolDomain.from_domain(third.domain, {'native-risk':'cluster-c'})),
            replace(self.a.domain.budget, concurrent_jobs=8, risk_units=2),
            (('cluster-ab',1),('cluster-c',1)), 'c'*64,
            now-timedelta(minutes=1), now+timedelta(hours=1))
        with self.a.migration() as connection:
            connection.execute('INSERT INTO hosting_controlplane.enterprise_wave_pools '
                '(pool_id,document_digest,document_json,enrolled_by) VALUES(%s,%s,%s::jsonb,%s)',
                (pool.pool_id,pool.digest,json.dumps(pool.to_record()),
                 'isolated-synthetic-native-budget-fixture'))
        self.assertEqual(self.a.admit().status,'JOB_QUEUED')
        self.assertFalse(self.ticket(self.b,'b1'))
        self.assertEqual(third.admit().status,'JOB_QUEUED')
        self.assertEqual(self.b.admit().status,'WAITING_ENTERPRISE_TURN')
        self.assertEqual(third.counts()[:2],(1,1))

    def test_null_or_omitted_independent_budget_cannot_be_enrolled(self):
        now = datetime.now(timezone.utc)
        pool = EnterpriseWavePool('pool-'+uuid4().hex,
            tuple(PoolDomain.from_domain(f.domain,{'native-risk':'physical-cluster'})
                  for f in (self.a,self.b)), self.a.domain.budget,
            (('physical-cluster',1),), 'c'*64,
            now-timedelta(minutes=1),now+timedelta(hours=1))
        for omitted in ('nativeBudgetEvidenceDigest','observedAt','expiresAt'):
            for remove in (True,False):
                with self.subTest(field=omitted,remove=remove):
                    record = pool.to_record()
                    if remove:
                        record.pop(omitted)
                    else:
                        record[omitted] = None
                    with self.a.migration() as connection:
                        with self.assertRaises(self.a.psycopg.Error):
                            connection.execute('INSERT INTO hosting_controlplane.enterprise_wave_pools '
                                '(pool_id,document_digest,document_json,enrolled_by) '
                                'VALUES(%s,%s,%s::jsonb,%s)',
                                (pool.pool_id,pool.digest,json.dumps(record),
                                 'isolated-missing-fact-fixture'))

    def test_dependency_blocked_ticket_does_not_take_a_fitting_tenant_turn(self):
        blocked, fitting = original_wave.WavePostgresTests(), original_wave.WavePostgresTests()
        for fixture, tenant in ((blocked,'tenant-b-blocked'),(fitting,'tenant-c')):
            fixture.setUp()
            fixture.ctx = TenantContext(self.a.ctx.organization_id,tenant)
        blocked.add_member('parent')
        blocked.add_member('child',dependencies=('parent',))
        fitting.add_member('fitting')
        for fixture in (blocked,fitting):
            fixture.enroll(); fixture.register()
        now = datetime.now(timezone.utc)
        pool = EnterpriseWavePool('pool-'+uuid4().hex,
            tuple(PoolDomain.from_domain(f.domain,{'native-risk':'physical-cluster'})
                  for f in (self.a,blocked,fitting)),
            replace(self.a.domain.budget,concurrent_jobs=8,risk_units=8),
            (('physical-cluster',8),),'c'*64,
            now-timedelta(minutes=1),now+timedelta(hours=1))
        with self.a.migration() as connection:
            connection.execute('INSERT INTO hosting_controlplane.enterprise_wave_pools '
                '(pool_id,document_digest,document_json,enrolled_by) VALUES(%s,%s,%s::jsonb,%s)',
                (pool.pool_id,pool.digest,json.dumps(pool.to_record()),
                 'isolated-synthetic-native-budget-fixture'))
        self.assertEqual(self.a.admit().status,'JOB_QUEUED')
        self.assertFalse(self.ticket(blocked,'child'))
        self.assertEqual(fitting.admit().status,'JOB_QUEUED')
        self.assertEqual(blocked.counts()[:2],(0,0))

    def test_failed_original_wave_event_rolls_back_job_turn_and_outbox(self):
        pool = self.pool()
        with patch.object(self.a.scheduler, '_event', side_effect=OSError('isolated journal fault')):
            with self.assertRaises(OSError):
                self.a.admit()
        self.assertEqual(self.a.counts(), (0,0,0))
        with self.a.migration() as connection:
            self.assertEqual(connection.execute('SELECT generation FROM '
                'hosting_controlplane.enterprise_wave_pool_turns WHERE pool_id=%s',
                (pool.pool_id,)).fetchone(), (0,))
        self.assertEqual(self.a.admit().status, 'JOB_QUEUED')

    def test_runtime_cannot_enroll_read_or_move_another_tenant_ticket(self):
        pool = self.pool()
        for sql, params in (
            ('SELECT * FROM hosting_controlplane.enterprise_wave_pool_domains', ()),
            ('SELECT * FROM hosting_controlplane.enterprise_wave_pool_turns', ()),
            ('UPDATE hosting_controlplane.enterprise_wave_pool_turns SET generation=10 WHERE pool_id=%s',
             (pool.pool_id,)),
            ('SELECT hosting_controlplane.migration_wave_pool_turn(%s,%s,%s,%s,%s,%s,'
             "clock_timestamp()+interval '20 seconds')",
             (self.b.ctx.organization_id, self.b.ctx.tenant_id, self.b.domain.domain_id,
              self.b.definition.digest, 'b1', self.b.principal.subject))):
            with self.a.runtime() as connection, connection.cursor() as cursor:
                _tenant(cursor, self.a.ctx)
                with self.assertRaises(self.a.psycopg.Error):
                    cursor.execute(sql, params)
