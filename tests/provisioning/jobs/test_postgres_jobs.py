"""Opt-in PostgreSQL contract: real transactions, uniqueness, RLS and replay.

Run only against a throwaway database with HOSTING_TEST_POSTGRES_ISOLATED=1,
an admin DSN and a separate non-bypass migration owner. This test creates a
no-login runtime role. It is not a replacement for native qualification.
"""
from __future__ import annotations

import json
import os
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from provisioner.controlplane.authority.model import AuthorizedPlan, FrozenPlan
from provisioner.controlplane.authority import postgres as authority_postgres
from provisioner.controlplane.jobs import (AdmissionConflict, AdmissionRefused,
                                            JobRepository, OutboxDispatcher,
                                            StartReceipt)
from provisioner.controlplane.jobs.repository import _digest
from provisioner.controlplane.persistence import TenantContext, canonical_record_digest
from provisioner.controlplane.persistence.migrate import apply_migrations
from provisioner.domain.enterprise_records import plan_digest
from tests.provisioning.schema.test_enterprise_records import plan, workload


@unittest.skipUnless(os.environ.get('HOSTING_TEST_POSTGRES_DSN') and
                     os.environ.get('HOSTING_TEST_POSTGRES_ISOLATED') == '1',
                     'Requires an explicitly isolated PostgreSQL test database')
class JobPostgresTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg

        cls.psycopg = psycopg
        cls.dsn = os.environ['HOSTING_TEST_POSTGRES_DSN']
        migration_dsn = os.environ['HOSTING_TEST_POSTGRES_MIGRATION_DSN']
        apply_migrations(lambda: psycopg.connect(migration_dsn))
        with psycopg.connect(cls.dsn) as connection:
            connection.execute(
                "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles "
                "WHERE rolname = 'hosting_jobs_test_runtime') THEN "
                'CREATE ROLE hosting_jobs_test_runtime NOLOGIN NOBYPASSRLS; '
                'END IF; END $$')
            connection.execute(
                'GRANT USAGE ON SCHEMA hosting_controlplane TO hosting_jobs_test_runtime')
            connection.execute(
                'GRANT SELECT ON hosting_controlplane.enterprise_records, '
                'hosting_controlplane.audit_events, '
                'hosting_controlplane.plan_authority_state, '
                'hosting_controlplane.plan_approvals TO hosting_jobs_test_runtime')
            connection.execute(
                'GRANT INSERT, UPDATE ON hosting_controlplane.enterprise_records '
                'TO hosting_jobs_test_runtime')
            connection.execute(
                'GRANT SELECT, INSERT, UPDATE ON '
                'hosting_controlplane.operation_jobs, '
                'hosting_controlplane.job_outbox TO hosting_jobs_test_runtime')
            connection.execute(
                'GRANT SELECT, INSERT ON hosting_controlplane.job_events '
                'TO hosting_jobs_test_runtime')
            connection.execute(
                'GRANT EXECUTE ON FUNCTION '
                'hosting_controlplane.lock_authority_scope(text, text, text) '
                'TO hosting_jobs_test_runtime')

    @classmethod
    def runtime(cls):
        connection = cls.psycopg.connect(cls.dsn)
        connection.execute('SET ROLE hosting_jobs_test_runtime')
        return connection

    def setUp(self):
        self.key_prefix = uuid4().hex[:12]
        # Outbox claims are tenant scoped. Give each test its own tenant so an
        # unfinished intent from an earlier test cannot be claimed here.
        organization_id = 'org-' + self.key_prefix
        tenant_id = 'tenant-' + self.key_prefix
        def scoped(value):
            if isinstance(value, dict):
                return {key: scoped(item) for key, item in value.items()}
            if isinstance(value, list):
                return [scoped(item) for item in value]
            return {'org-01': organization_id,
                    'tenant-01': tenant_id}.get(value, value) if isinstance(value, str) else value
        selected = scoped(deepcopy(plan()))
        observed = scoped(deepcopy(workload()))
        observed['metadata']['workloadId'] = 'job-workload-' + uuid4().hex
        selected['spec']['workloadId'] = observed['metadata']['workloadId']
        selected['metadata']['planId'] = 'job-plan-' + uuid4().hex
        selected['metadata']['planDigest'] = plan_digest(selected)
        self.selected = selected
        self.observed = observed
        self.tenant = TenantContext(organization_id, tenant_id)
        self.foreign = TenantContext(organization_id, 'tenant-foreign')
        frozen = FrozenPlan.from_record(selected, author_subject='plan-author')
        self.frozen = frozen
        now = datetime.now(timezone.utc)
        roles = (('SOURCE_OWNER', frozen.source),
                 ('DESTINATION_OWNER', frozen.destination),
                 ('SOURCE_SECURITY', frozen.source),
                 ('DESTINATION_SECURITY', frozen.destination))
        approvals = tuple('approval-' + uuid4().hex for _ in roles)
        self.decision = AuthorizedPlan(
            frozen.organization_id, frozen.tenant_id, frozen.plan_id,
            frozen.revision, frozen.digest, frozen.source, frozen.destination,
            approvals, 0, now + timedelta(hours=1), 'operator-01')
        with self.psycopg.connect(self.dsn) as connection:
            connection.execute(
                "SELECT set_config('app.organization_id', %s, true), "
                "set_config('app.tenant_id', %s, true)",
                (self.tenant.organization_id, self.tenant.tenant_id))
            connection.execute(
                'INSERT INTO hosting_controlplane.enterprise_records '
                '(organization_id, tenant_id, record_kind, record_id, revision, '
                'record_json, record_digest) VALUES '
                "(%s, %s, 'Workload', %s, 1, %s::jsonb, %s)",
                (self.tenant.organization_id, self.tenant.tenant_id,
                 observed['metadata']['workloadId'], json.dumps(observed),
                 canonical_record_digest(observed)))
            connection.execute(
                'INSERT INTO hosting_controlplane.enterprise_records '
                '(organization_id, tenant_id, record_kind, record_id, revision, '
                'record_json, record_digest) VALUES '
                "(%s, %s, 'MigrationPlan', %s, 1, %s::jsonb, %s)",
                (self.tenant.organization_id, self.tenant.tenant_id,
                 frozen.plan_id, json.dumps(selected), canonical_record_digest(selected)))
            connection.execute(
                'INSERT INTO hosting_controlplane.audit_events '
                '(organization_id, tenant_id, actor_id, correlation_id, action, '
                'record_kind, record_id, revision, record_digest) VALUES '
                "(%s, %s, 'plan-author', %s, 'RECORD_CREATE', 'MigrationPlan', %s, 1, %s)",
                (self.tenant.organization_id, self.tenant.tenant_id,
                 uuid4().hex, frozen.plan_id, canonical_record_digest(selected)))
            for index, ((role, scope), approval_id) in enumerate(zip(roles, approvals)):
                connection.execute(
                    'INSERT INTO hosting_controlplane.plan_approvals '
                    '(approval_id, organization_id, tenant_id, plan_id, '
                    'plan_revision, plan_digest, revocation_epoch, role, '
                    'site_id, security_domain_id, endpoint_id, native_scope_id, '
                    'platform_family, approver_subject, issued_at, expires_at) '
                    'VALUES (%s, %s, %s, %s, 1, %s, 0, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                    (approval_id, frozen.organization_id, frozen.tenant_id,
                     frozen.plan_id, frozen.digest, role, scope.site_id,
                     scope.security_domain_id, scope.endpoint_id,
                     scope.native_scope_id, scope.platform_family,
                     f'approver-{index}', now - timedelta(minutes=1),
                     now + timedelta(hours=2)))
        self.jobs = JobRepository(self.runtime, authority_postgres)

    def key(self, value):
        return f'{self.key_prefix}-{value}'

    def test_concurrent_duplicate_admission_one_job_outbox_and_event(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.jobs.submit, self.tenant, self.decision,
                                   idempotency_key=self.key('submit-01')) for _ in range(2)]
            results = [future.result(timeout=20) for future in futures]
        self.assertEqual(results[0].job_id, results[1].job_id)
        self.assertEqual(results[0].source, self.frozen.source)
        self.assertEqual(results[0].destination, self.frozen.destination)
        self.assertEqual(len(self.jobs.events(self.tenant, results[0].job_id)), 1)
        self.assertIsNone(self.jobs.get(self.foreign, results[0].job_id))
        self.assertEqual(self.jobs.events(self.foreign, results[0].job_id), ())
        with self.assertRaises(AdmissionConflict):
            self.jobs.submit(self.tenant, self.decision,
                             idempotency_key=self.key('new-key'))
        with self.psycopg.connect(self.dsn) as connection:
            counts = connection.execute(
                'SELECT (SELECT count(*) FROM hosting_controlplane.operation_jobs '
                'WHERE job_id = %s), (SELECT count(*) FROM hosting_controlplane.job_outbox '
                'WHERE job_id = %s)',
                (results[0].job_id, results[0].job_id)).fetchone()
        self.assertEqual(counts, (1, 1))

    def test_stale_scope_or_epoch_refuses_before_job_commit(self):
        with self.assertRaises(AdmissionRefused):
            self.jobs.submit(self.tenant,
                             replace(self.decision, destination=self.frozen.source),
                             idempotency_key=self.key('wrong-scope'))
        with self.psycopg.connect(self.dsn) as connection:
            connection.execute(
                'UPDATE hosting_controlplane.plan_authority_state '
                'SET revocation_epoch = revocation_epoch + 1 '
                'WHERE organization_id = %s AND tenant_id = %s AND plan_id = %s',
                (self.tenant.organization_id, self.tenant.tenant_id,
                 self.frozen.plan_id))
        with self.assertRaises(PermissionError):
            self.jobs.submit(self.tenant, self.decision,
                             idempotency_key=self.key('revoked'))

    def test_workload_revision_drift_refuses_admission_and_prestart(self):
        admitted = self.jobs.submit(self.tenant, self.decision,
                                    idempotency_key=self.key('current-before-edit'))
        successor = deepcopy(self.observed)
        successor['metadata']['revision'] = 2
        with self.psycopg.connect(self.dsn) as connection:
            connection.execute(
                'UPDATE hosting_controlplane.enterprise_records SET '
                'revision = 2, record_json = %s::jsonb, record_digest = %s '
                "WHERE organization_id = %s AND tenant_id = %s "
                "AND record_kind = 'Workload' AND record_id = %s",
                (json.dumps(successor), canonical_record_digest(successor),
                 self.tenant.organization_id, self.tenant.tenant_id,
                 successor['metadata']['workloadId']))
        with self.assertRaises(AdmissionRefused):
            self.jobs.submit(self.tenant, self.decision,
                             idempotency_key=self.key('admit-after-edit'))
        message = self.jobs.claim_start(self.tenant, dispatcher_id='test-recheck')
        self.assertEqual(message.job_id, admitted.job_id)
        with self.assertRaises(AdmissionRefused):
            self.jobs.revalidate_start(self.tenant, message)

    def test_crash_after_start_retries_same_workflow_and_progress_is_idempotent(self):
        job = self.jobs.submit(self.tenant, self.decision,
                               idempotency_key=self.key('dispatch-01'))

        class Workflow:
            def __init__(self):
                self.runs = {}
                self.fail_after_persist = True

            def start(self, *, namespace, workflow_id, payload):
                key = (namespace, workflow_id)
                self.runs.setdefault(key, StartReceipt(
                    namespace, workflow_id, 'run-01', payload['job_id'],
                    payload['plan_id'], payload['plan_revision'],
                    payload['plan_digest'], _digest(payload)))
                if self.fail_after_persist:
                    self.fail_after_persist = False
                    raise ConnectionError('ack lost after durable start')
                return self.runs[key]

        workflow = Workflow()
        dispatcher = OutboxDispatcher(self.jobs, workflow,
                                      dispatcher_id='site-a', namespace='mobility-test',
                                      start_history_retention_seconds=86400)
        with self.assertRaises(ConnectionError):
            dispatcher.run_one(self.tenant, lease_seconds=1)
        # Simulate lease expiry without a time-based sleep. The first run is
        # already durable, and the outbox still has not acknowledged it.
        with self.psycopg.connect(self.dsn) as connection:
            connection.execute(
                "UPDATE hosting_controlplane.job_outbox SET claimed_until = "
                "clock_timestamp() - interval '1 second' WHERE job_id = %s",
                (job.job_id,))
        self.assertEqual(dispatcher.run_one(self.tenant).disposition, 'STARTED')
        self.assertEqual(len(workflow.runs), 1)
        binding = self.jobs.start_run(self.tenant, job.job_id)
        self.assertEqual((binding.namespace, binding.run_id),
                         ('mobility-test', 'run-01'))
        with self.psycopg.connect(self.dsn) as connection:
            connection.execute(
                "SELECT set_config('app.organization_id', %s, true), "
                "set_config('app.tenant_id', %s, true)",
                (self.tenant.organization_id, self.tenant.tenant_id))
            with self.assertRaises(self.psycopg.Error):
                connection.execute(
                    'UPDATE hosting_controlplane.job_outbox SET start_run_id = %s '
                    'WHERE job_id = %s', ('forged-run', job.job_id))
        progress = self.jobs.append_progress(
            self.tenant, job.job_id, event_key='workflow-event-01',
            event_type='WAITING_FOR_REVIEW', status='WAITING_APPROVAL',
            detail={'stepId': 'approval-gate'})
        replay = self.jobs.append_progress(
            self.tenant, job.job_id, event_key='workflow-event-01',
            event_type='WAITING_FOR_REVIEW', status='WAITING_APPROVAL',
            detail={'stepId': 'approval-gate'})
        self.assertEqual(progress.sequence, replay.sequence)
        self.assertEqual([event.sequence for event in
                          self.jobs.events(self.tenant, job.job_id)], [1, 2, 3])

    def test_workflow_progress_before_outbox_ack_does_not_rewind_status(self):
        job = self.jobs.submit(self.tenant, self.decision,
                               idempotency_key=self.key('early-workflow-event'))
        message = self.jobs.claim_start(self.tenant, dispatcher_id='first-claim',
                                        lease_seconds=1)
        self.assertEqual(message.job_id, job.job_id)
        self.jobs.append_progress(
            self.tenant, job.job_id, event_key='workflow-finished',
            event_type='WORKFLOW_FINISHED', status='SUCCEEDED', detail={})
        with self.psycopg.connect(self.dsn) as connection:
            connection.execute(
                "UPDATE hosting_controlplane.job_outbox SET claimed_until = "
                "clock_timestamp() - interval '1 second' WHERE job_id = %s",
                (job.job_id,))

        class ExistingWorkflow:
            def start(self, *, namespace, workflow_id, payload):
                return StartReceipt(namespace, workflow_id, 'prior-run',
                                    payload['job_id'], payload['plan_id'],
                                    payload['plan_revision'], payload['plan_digest'],
                                    _digest(payload))

        result = OutboxDispatcher(self.jobs, ExistingWorkflow(),
                                  dispatcher_id='retry-claim',
                                  namespace='mobility-test',
                                  start_history_retention_seconds=86400).run_one(self.tenant)
        self.assertEqual(result.disposition, 'STARTED')
        self.assertEqual(self.jobs.get(self.tenant, job.job_id).status, 'SUCCEEDED')
        self.assertEqual([event.event_type for event in
                          self.jobs.events(self.tenant, job.job_id)],
                         ['JOB_ADMITTED', 'WORKFLOW_FINISHED'])

    def test_uncertain_start_past_history_window_holds_without_replay(self):
        job = self.jobs.submit(self.tenant, self.decision,
                               idempotency_key=self.key('retention-bound'))

        class LostStart:
            calls = 0
            def start(self, *, namespace, workflow_id, payload):
                self.calls += 1
                raise ConnectionError('result of durable start is unknown')

        workflow = LostStart()
        dispatcher = OutboxDispatcher(
            self.jobs, workflow, dispatcher_id='retention-dispatch',
            namespace='mobility-test', start_history_retention_seconds=1)
        with self.assertRaises(ConnectionError):
            dispatcher.run_one(self.tenant, lease_seconds=1)
        time.sleep(1.2)
        result = dispatcher.run_one(self.tenant)
        self.assertEqual(result.disposition, 'HELD')
        self.assertEqual(workflow.calls, 1)
        self.assertEqual(self.jobs.get(self.tenant, job.job_id).status, 'HELD')
        self.assertEqual(self.jobs.events(self.tenant, job.job_id)[-1].event_type,
                         'START_RETENTION_HOLD')


if __name__ == '__main__':
    unittest.main()
