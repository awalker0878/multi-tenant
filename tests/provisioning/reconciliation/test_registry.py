"""Native-operation state and opt-in PostgreSQL fencing/recovery contract."""
from __future__ import annotations

import json
import os
import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from provisioner.controlplane.authority.model import (PlanScope, RoleGrant,
                                                       VerifiedPrincipal)
from provisioner.controlplane.persistence import (AuditContext, EnterpriseRecordStore,
                                                  NativeBinding, TenantContext)
from provisioner.controlplane.persistence.migrate import apply_migrations
from provisioner.controlplane.reconciliation.registry import (
    NativeLeaseAuthority, NativeObservation, NativeOperationRegistry,
    OperationConflict, OwnerRecoveryEvidence, RecoveryHeld, _row)
from provisioner.controlplane.worker.grants import VerifiedWorkerIdentity
from provisioner.domain.enterprise_records import plan_digest
from tests.provisioning.schema.test_enterprise_records import plan, workload


class NativeRegistryValidationTest(unittest.TestCase):
    def test_immutable_row_mapping_and_independent_evidence_shape(self):
        values = ('op-1', 'job-1', 'grant-1', 'step-1', 'lease-1', 'vmware',
                  'endpoint-1', 'scope-1', 'vm', 'vm-1', 'workload-1', 'wsd-1',
                  'worker-1', 3, 'VM_POWER', 'a' * 64, 'UNCERTAIN', None, None)
        operation = _row(values)
        self.assertEqual(operation.binding.key(), values[5:10])
        self.assertEqual(operation.owner_epoch, 3)
        with self.assertRaises(ValueError):
            NativeObservation('observation-1', 'a' * 64, 'reader-1', None,
                              'NO_EFFECT', True,
                              datetime.now(timezone.utc).replace(tzinfo=None))
        with self.assertRaises(ValueError):
            OwnerRecoveryEvidence('a' * 64, 'bad-digest',
                                  datetime.now(timezone.utc), 'incident-1')


class _TestEvidence:
    def verify_native_observation(self, cursor, operation, observation):
        if observation.evidence_digest != 'a' * 64:
            raise RecoveryHeld('Untrusted native observation')

    def verify_owner_exclusion(self, cursor, lease, scope, evidence):
        if (evidence.native_evidence_digest != 'b' * 64
                or evidence.worker_fence_digest != 'c' * 64):
            raise RecoveryHeld('Native exclusion or worker fence is unverified')


class _TestGrant:
    def __init__(self, leases):
        self.leases = leases

    def verify_intent(self, cursor, context, *, grant_id, job_id, step_id,
                      operation_id, operation_kind, operation_scope,
                      worker_identity, lease_key, lease_epoch):
        if grant_id != 'grant-1' or step_id != 'step-1':
            raise OperationConflict('Grant not found')
        self.leases.require_current(
            cursor, context, lease_key=lease_key, lease_epoch=lease_epoch,
            job_id=job_id, operation_id=operation_id,
            scope=operation_scope, worker_subject=worker_identity.subject)


@unittest.skipUnless(os.environ.get('HOSTING_TEST_POSTGRES_RUNTIME_DSN') and
                     os.environ.get('HOSTING_TEST_POSTGRES_ISOLATED') == '1',
                     'Requires isolated PostgreSQL runtime and migration roles')
class NativeRegistryPostgresTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        cls.psycopg = psycopg
        cls.runtime_dsn = os.environ['HOSTING_TEST_POSTGRES_RUNTIME_DSN']
        apply_migrations(lambda: psycopg.connect(
            os.environ['HOSTING_TEST_POSTGRES_MIGRATION_DSN']))

    def setUp(self):
        suffix = uuid4().hex[:12]
        self.ctx = TenantContext('org-' + suffix, 'tenant-' + suffix)
        self.audit = AuditContext('operator-1', 'reconcile-' + suffix)
        self.workload = deepcopy(workload())
        self.plan = deepcopy(plan())
        for record in (self.workload, self.plan):
            record['metadata']['organizationId'] = self.ctx.organization_id
            record['metadata']['tenantId'] = self.ctx.tenant_id
        self.workload['metadata']['workloadId'] = 'workload-' + suffix
        self.plan['spec']['workloadId'] = self.workload['metadata']['workloadId']
        self.plan['metadata']['planId'] = 'plan-' + suffix
        for scope in (self.plan['spec']['source'], self.plan['spec']['destination']):
            scope['organizationId'] = self.ctx.organization_id
            scope['tenantId'] = self.ctx.tenant_id
        native = self.workload['spec']['machines'][0]['bindings'][0]['binding']
        native['nativeId'] = 'vm-' + suffix
        self.plan['spec']['machineMappings'][0]['sourceBinding']['nativeId'] = (
            native['nativeId'])
        self.plan['metadata']['planDigest'] = plan_digest(self.plan)
        self.binding = NativeBinding.from_record(native)
        self.scope = PlanScope.from_record(self.plan['spec']['source'])
        self.job_id = 'job-' + suffix
        self.operation_id = 'operation-' + suffix
        self.lease_key = 'lease-' + suffix
        self.store = EnterpriseRecordStore(self.runtime)
        self.store.create(self.ctx, self.workload, self.audit)
        self.store.create(self.ctx, self.plan, self.audit)
        with self.runtime() as connection:
            self.tenant_sql(connection)
            connection.execute(
                'INSERT INTO hosting_controlplane.operation_jobs '
                '(organization_id, tenant_id, job_id, idempotency_key, plan_id, '
                'plan_revision, plan_digest, source_scope, destination_scope, '
                'actor_subject, approval_ids, revocation_epoch, status) '
                'VALUES (%s, %s, %s, %s, %s, 1, %s, %s::jsonb, %s::jsonb, '
                "%s, '[]'::jsonb, 0, 'STARTED')",
                (self.ctx.organization_id, self.ctx.tenant_id,
                 self.job_id, 'key-' + suffix, self.plan['metadata']['planId'],
                 self.plan['metadata']['planDigest'],
                 json.dumps(self.plan['spec']['source']),
                 json.dumps(self.plan['spec']['destination']), 'operator-1'))
        self.owner = self.store.acquire_owner_lease(
            self.ctx, self.plan['spec']['source'], self.binding,
            self.workload['metadata']['workloadId'], 'worker-1', 60, self.audit)
        now = datetime.now(timezone.utc)
        self.identity = VerifiedWorkerIdentity(
            self.ctx.organization_id, self.ctx.tenant_id, 'worker-1',
            self.scope.site_id, 'd' * 64, now + timedelta(minutes=5))
        self.leases = NativeLeaseAuthority(self.runtime)
        self.leases.register(self.ctx, self.owner, self.scope,
                             lease_key=self.lease_key, job_id=self.job_id,
                             operation_id=self.operation_id,
                             worker_identity=self.identity)
        self.registry = NativeOperationRegistry(
            self.runtime, grants=_TestGrant(self.leases), evidence=_TestEvidence())

    def runtime(self):
        return self.psycopg.connect(self.runtime_dsn)

    def tenant_sql(self, connection):
        connection.execute(
            "SELECT set_config('app.organization_id', %s, true), "
            "set_config('app.tenant_id', %s, true)",
            (self.ctx.organization_id, self.ctx.tenant_id))

    def operator(self, subject, role='EXECUTION_OPERATOR'):
        now = datetime.now(timezone.utc)
        return VerifiedPrincipal(subject, self.ctx.organization_id,
                                 self.ctx.tenant_id, 'HUMAN',
                                 now - timedelta(minutes=1),
                                 now + timedelta(minutes=10), now,
                                 (RoleGrant(role, self.scope,
                                            now + timedelta(minutes=10)),))

    def prepare(self):
        return self.registry.prepare(
            self.ctx, self.owner, self.scope, job_id=self.job_id,
            grant_id='grant-1', step_id='step-1', lease_key=self.lease_key,
            worker_identity=self.identity, operation_id=self.operation_id,
            operation_kind='VM_POWER', request_digest='f' * 64)

    def test_uncertain_timeout_never_replays_and_blocks_owner_release(self):
        self.assertEqual(self.prepare().state, 'PREPARED')
        self.assertTrue(self.registry.claim_once(
            self.ctx, self.owner, self.scope, self.operation_id, self.identity))
        self.assertFalse(self.registry.claim_once(
            self.ctx, self.owner, self.scope, self.operation_id, self.identity))
        self.assertFalse(self.registry.claim_once(
            self.ctx, self.owner, self.scope, self.operation_id, self.identity))
        self.assertTrue(self.registry.mark_uncertain(
            self.ctx, self.operation_id, 'worker-1'))
        self.assertEqual(self.prepare().state, 'UNCERTAIN')
        with self.assertRaises(self.psycopg.Error):
            self.store.release_owner_lease(self.ctx, self.owner, self.audit)
        with self.runtime() as connection:
            self.tenant_sql(connection)
            connection.execute(
                'UPDATE hosting_controlplane.native_ownership SET '
                "lease_expires_at = clock_timestamp() - interval '1 second' "
                'WHERE platform_family = %s AND endpoint_id = %s '
                'AND native_scope_id = %s AND resource_kind = %s AND native_id = %s',
                self.binding.key())
        with self.assertRaises(RecoveryHeld):
            self.registry.clear_expired_owner(
                self.ctx, self.owner, self.scope,
                OwnerRecoveryEvidence('b' * 64, 'c' * 64,
                                      datetime.now(timezone.utc), 'incident-1'))

    def test_two_reviews_resolve_and_expired_owner_needs_separate_fence(self):
        self.prepare()
        self.registry.claim_once(self.ctx, self.owner, self.scope,
                                 self.operation_id, self.identity)
        self.registry.mark_uncertain(self.ctx, self.operation_id, 'worker-1')
        observed = NativeObservation('observation-' + uuid4().hex,
                                     'a' * 64, 'independent-reader', None,
                                     'NO_EFFECT', True, datetime.now(timezone.utc))
        self.registry.observe(self.ctx, self.operation_id, observed)
        self.assertFalse(self.registry.review_outcome(
            self.ctx, self.operation_id, observed.observation_id,
            self.operator('operator-2'), self.scope,
            decision='NO_EFFECT', incident_id='incident-1'))
        self.assertTrue(self.registry.review_outcome(
            self.ctx, self.operation_id, observed.observation_id,
            self.operator('operator-3'), self.scope,
            decision='NO_EFFECT', incident_id='incident-1'))
        with self.runtime() as connection:
            self.tenant_sql(connection)
            connection.execute(
                'UPDATE hosting_controlplane.native_ownership SET '
                "lease_expires_at = clock_timestamp() - interval '1 second' "
                'WHERE platform_family = %s AND endpoint_id = %s '
                'AND native_scope_id = %s AND resource_kind = %s AND native_id = %s',
                self.binding.key())
        evidence = OwnerRecoveryEvidence('b' * 64, 'c' * 64,
                                         datetime.now(timezone.utc), 'incident-1')
        with self.assertRaises(RecoveryHeld):
            self.registry.clear_expired_owner(self.ctx, self.owner, self.scope,
                                              evidence)
        self.registry.review_expired_owner(self.ctx, self.owner, self.scope,
                                           self.operator('security-1', 'SOURCE_SECURITY'),
                                           evidence)
        self.registry.review_expired_owner(self.ctx, self.owner, self.scope,
                                           self.operator('security-2', 'SOURCE_SECURITY'),
                                           evidence)
        self.assertEqual(self.registry.clear_expired_owner(
            self.ctx, self.owner, self.scope, evidence), self.owner.epoch + 1)
        with self.runtime() as connection, connection.cursor() as cursor:
            self.tenant_sql(connection)
            with self.assertRaises(OperationConflict):
                self.leases.require_current(
                    cursor, self.ctx, lease_key=self.lease_key,
                    lease_epoch=self.owner.epoch, job_id=self.job_id,
                    operation_id=self.operation_id, scope=self.scope,
                    worker_subject='worker-1')

    def test_containment_blocks_live_release_renew_and_intent(self):
        self.registry.contain(
            self.ctx, self.owner, self.operator('security-1', 'SOURCE_SECURITY'),
            self.scope, incident_id='incident-1', reason='Native task status uncertain')
        with self.assertRaises(self.psycopg.Error):
            self.store.release_owner_lease(self.ctx, self.owner, self.audit)
        with self.assertRaises(self.psycopg.Error):
            self.store.renew_owner_lease(self.ctx, self.owner, 60, self.audit)
        with self.assertRaises(RecoveryHeld):
            self.prepare()
