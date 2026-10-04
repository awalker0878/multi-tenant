"""Offline storage regression; these fixtures are not native qualification."""
from __future__ import annotations

import json
import unittest
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.jobs.repository import _job
from provisioner.controlplane.persistence import NativeBinding, OwnerLease, TenantContext
from provisioner.controlplane.reconciliation.registry import (
    NativeLeaseAuthority, NativeOperationRegistry, OperationConflict, RecoveryHeld)
from provisioner.controlplane.worker.grants import VerifiedWorkerIdentity
from tests.provisioning.schema.test_enterprise_records import plan


class _StoredJob:
    """A current B09 row and native owner facts behind a bounded SQL test port."""

    def __init__(self, *, destination=False, decoded_json=False):
        self.now = datetime.now(timezone.utc)
        self.record = plan()
        self.source = PlanScope.from_record(self.record['spec']['source'])
        self.destination = PlanScope.from_record(self.record['spec']['destination'])
        self.context = TenantContext(self.source.organization_id, self.source.tenant_id)
        # This is the serialization used by JobRepository.submit_in_transaction.
        self.source_json = json.dumps(asdict(self.source))
        self.destination_json = json.dumps(asdict(self.destination))
        if decoded_json:
            self.source_json = json.loads(self.source_json)
            self.destination_json = json.loads(self.destination_json)
        self.job = _job((self.context.organization_id, self.context.tenant_id,
                         'job-1', 'key-1', self.record['metadata']['planId'], 1,
                         self.record['metadata']['planDigest'], self.source_json,
                         self.destination_json, 'operator-1', '[]', 0,
                         'STARTED', 1, self.now, self.now))
        self.status = self.job.status
        self.scope = self.destination if destination else self.source
        self.binding = NativeBinding(self.scope.platform_family,
                                     self.scope.endpoint_id,
                                     self.scope.native_scope_id, 'vm', 'native-vm-1')
        self.owner = OwnerLease(self.binding, self.context.organization_id,
                                self.context.tenant_id, self.scope.security_domain_id,
                                'workload-1', 'worker-1', 3,
                                self.now + timedelta(minutes=5))
        self.owner_row = (self.owner.organization_id, self.owner.tenant_id,
                          self.owner.security_domain_id, self.owner.workload_id,
                          self.owner.worker_id, self.owner.epoch, self.owner.expires_at)
        self.identity = VerifiedWorkerIdentity(
            self.context.organization_id, self.context.tenant_id, 'worker-1',
            self.scope.site_id, 'd' * 64, self.now + timedelta(minutes=5))
        self.role = (False, False)
        self.conversion_admitted = True
        self.contained = False
        self.mapping = None
        self.operation = None
        self.writes = []
        self.leases = NativeLeaseAuthority(self.connect)
        self.grants = _CurrentGrant(self.leases)
        self.registry = NativeOperationRegistry(self.connect, grants=self.grants,
                                                evidence=_UnusedEvidence())

    def connect(self):
        return _Connection(self)

    def register(self):
        self.leases.register(self.context, self.owner, self.scope,
                             lease_key='lease-1', job_id=self.job.job_id,
                             operation_id='operation-1', worker_identity=self.identity)

    def prepare(self):
        return self.registry.prepare(
            self.context, self.owner, self.scope, job_id=self.job.job_id,
            grant_id='grant-1', step_id='step-1', lease_key='lease-1',
            worker_identity=self.identity, operation_id='operation-1',
            operation_kind='VM_POWER', request_digest='f' * 64)


class _Connection:
    autocommit = False

    def __init__(self, facts):
        self.facts = facts

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def cursor(self):
        return _Cursor(self)


class _Cursor:
    def __init__(self, connection):
        self.connection = connection
        self.result = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def fetchone(self):
        return self.result

    def execute(self, sql, params=()):
        facts = self.connection.facts
        self.result = None
        if sql.startswith('SELECT rolsuper, rolbypassrls'):
            self.result = facts.role
        elif sql.startswith("SELECT set_config('app.organization_id'"):
            if params != (facts.context.organization_id, facts.context.tenant_id):
                raise AssertionError('Unexpected tenant context')
        elif 'FROM hosting_controlplane.operation_jobs' in sql:
            if params == (facts.context.organization_id, facts.context.tenant_id,
                          facts.job.job_id):
                if sql.startswith('SELECT status, source_scope'):
                    self.result = (facts.status, facts.source_json, facts.destination_json)
                else:
                    self.result = (facts.source_json, facts.destination_json, facts.status)
        elif sql == 'SELECT clock_timestamp()':
            self.result = (facts.now,)
        elif sql.startswith('SELECT hosting_controlplane.retained_conversion_write_is_admitted('):
            if params != (facts.context.organization_id,facts.context.tenant_id,
                          facts.owner.security_domain_id,facts.owner.workload_id):
                raise AssertionError('Unexpected converted workload scope')
            self.result = (facts.conversion_admitted,)
        elif 'FROM hosting_controlplane.native_ownership' in sql:
            if params == facts.binding.key():
                self.result = facts.owner_row
        elif 'FROM hosting_controlplane.native_containment_holds' in sql:
            if params == facts.binding.key() and facts.contained:
                self.result = (1,)
        elif sql.startswith('INSERT INTO hosting_controlplane.native_operation_leases '):
            facts.writes.append('lease')
            expiry = min(params[14], params[15], facts.now + timedelta(seconds=params[16]))
            facts.mapping = (*params[3:14], expiry)
        elif 'FROM hosting_controlplane.lock_native_worker_scope(' in sql:
            if facts.mapping is not None and params == (
                    facts.context.organization_id, facts.context.tenant_id, 'lease-1'):
                self.result = (*facts.mapping, facts.owner_row[0], facts.owner_row[1],
                               facts.owner_row[2], *facts.owner_row[4:])
        elif sql.startswith('INSERT INTO hosting_controlplane.native_operation_intents '):
            facts.writes.append('intent')
            facts.operation = (*params[2:7], *params[7:], 'PREPARED', None, None)
        elif 'FROM hosting_controlplane.native_operation_intents' in sql:
            self.result = facts.operation
        else:
            raise AssertionError('Unexpected SQL in bounded test port: ' + sql)


class _CurrentGrant:
    def __init__(self, leases):
        self.leases = leases
        self.calls = 0
        self.revoked = False

    def verify_intent(self, cursor, context, *, grant_id, job_id, step_id,
                      operation_id, operation_kind, operation_scope,
                      worker_identity, lease_key, lease_epoch):
        self.calls += 1
        if self.revoked or (grant_id, step_id, operation_kind) != (
                'grant-1', 'step-1', 'VM_POWER'):
            raise OperationConflict('Synthetic current grant is denied')
        self.leases.require_current(
            cursor, context, lease_key=lease_key, lease_epoch=lease_epoch,
            job_id=job_id, operation_id=operation_id, scope=operation_scope,
            worker_subject=worker_identity.subject)


class _UnusedEvidence:
    def verify_native_observation(self, *_):
        raise AssertionError('No native evidence in this storage regression')

    def verify_owner_exclusion(self, *_):
        raise AssertionError('No native evidence in this storage regression')


class NativeJobScopeStorageTest(unittest.TestCase):
    def test_current_b09_source_and_destination_roundtrip_through_both_owners(self):
        for destination in (False, True):
            for decoded in (False, True):
                with self.subTest(destination=destination, decoded_json=decoded):
                    facts = _StoredJob(destination=destination, decoded_json=decoded)
                    self.assertEqual((facts.job.source, facts.job.destination),
                                     (facts.source, facts.destination))
                    self.assertIn('organization_id', asdict(facts.scope))
                    self.assertNotIn('organizationId', asdict(facts.scope))
                    facts.register()
                    operation = facts.prepare()
                    self.assertEqual(operation.binding, facts.binding)
                    self.assertEqual(operation.owner_epoch, facts.owner.epoch)
                    self.assertEqual(operation.state, 'PREPARED')
                    self.assertEqual(facts.writes, ['lease', 'intent'])
                    self.assertEqual(facts.grants.calls, 1)

    def test_canonical_missing_mixed_and_malformed_scope_storage_is_denied(self):
        for owner in ('register', 'prepare'):
            for invalid in ('canonical', 'missing', 'mixed', 'malformed', 'extra'):
                with self.subTest(owner=owner, invalid=invalid):
                    facts = _StoredJob()
                    if owner == 'prepare':
                        facts.register()
                        facts.writes.clear()
                    source = asdict(facts.source)
                    if invalid == 'canonical':
                        source = facts.record['spec']['source']
                    elif invalid == 'missing':
                        del source['site_id']
                    elif invalid == 'mixed':
                        source['organizationId'] = source.pop('organization_id')
                    elif invalid == 'extra':
                        source['extra'] = 'unaccepted'
                    facts.source_json = '{' if invalid == 'malformed' else json.dumps(source)
                    with self.assertRaisesRegex(OperationConflict, 'persisted job scope'):
                        getattr(facts, owner)()
                    self.assertEqual(facts.writes, [])
                    self.assertEqual(facts.grants.calls, 0)

    def test_same_native_scope_with_other_site_tenant_or_wsd_is_not_selected(self):
        for owner in ('register', 'prepare'):
            for field in ('site_id', 'organization_id', 'tenant_id', 'security_domain_id',
                          'endpoint_id', 'native_scope_id', 'platform_family'):
                with self.subTest(owner=owner, field=field):
                    facts = _StoredJob()
                    if owner == 'prepare':
                        facts.register()
                        facts.writes.clear()
                    facts.source_json = json.dumps(asdict(replace(facts.source,
                                                                 **{field: 'other'})))
                    with self.assertRaisesRegex(OperationConflict, 'not selected'):
                        getattr(facts, owner)()
                    self.assertEqual(facts.writes, [])
                    self.assertEqual(facts.grants.calls, 0)

    def test_job_hold_owner_epoch_expiry_and_containment_still_deny_both_owners(self):
        for owner in ('register', 'prepare'):
            for change in ('job-held', 'owner-epoch', 'owner-worker', 'owner-expired',
                           'containment', 'bypass-role'):
                with self.subTest(owner=owner, change=change):
                    facts = _StoredJob()
                    if owner == 'prepare':
                        facts.register()
                        facts.writes.clear()
                    if change == 'job-held':
                        facts.status = 'HELD'
                    elif change == 'owner-epoch':
                        facts.owner_row = (*facts.owner_row[:5], 4, facts.owner_row[6])
                    elif change == 'owner-worker':
                        facts.owner_row = (*facts.owner_row[:4], 'other-worker',
                                           *facts.owner_row[5:])
                    elif change == 'owner-expired':
                        facts.owner_row = (*facts.owner_row[:6], facts.now)
                    elif change == 'containment':
                        facts.contained = True
                    else:
                        facts.role = (False, True)
                    with self.assertRaises((OperationConflict, RecoveryHeld, RuntimeError)):
                        getattr(facts, owner)()
                    self.assertEqual(facts.writes, [])

    def test_registration_requires_current_verified_worker_site_and_identity(self):
        for change in ('subject', 'site_id', 'organization_id', 'tenant_id', 'expires_at'):
            with self.subTest(change=change):
                facts = _StoredJob()
                value = facts.now if change == 'expires_at' else 'other-worker-identity'
                facts.identity = replace(facts.identity, **{change: value})
                with self.assertRaises(OperationConflict):
                    facts.register()
                self.assertEqual(facts.writes, [])

    def test_prepare_rechecks_current_grant_and_exact_lease_job_binding(self):
        for change in ('revoked-grant', 'lease-job', 'lease-operation', 'lease-epoch',
                       'lease-worker', 'lease-expired'):
            with self.subTest(change=change):
                facts = _StoredJob()
                facts.register()
                facts.writes.clear()
                if change == 'revoked-grant':
                    facts.grants.revoked = True
                else:
                    mapping = list(facts.mapping)
                    index = {'lease-job': 0, 'lease-operation': 1, 'lease-epoch': 10,
                             'lease-worker': 9, 'lease-expired': 11}[change]
                    mapping[index] = (facts.now if change == 'lease-expired' else
                                      4 if change == 'lease-epoch' else 'other-binding')
                    facts.mapping = tuple(mapping)
                with self.assertRaises(OperationConflict):
                    facts.prepare()
                self.assertEqual(facts.writes, [])
                self.assertEqual(facts.grants.calls, 1)

    def test_converted_observation_only_scope_denies_both_owners_before_grants_or_writes(self):
        from provisioner.controlplane.authority.service import AuthorityDenied
        for owner in ('register','prepare'):
            with self.subTest(owner=owner):
                facts=_StoredJob()
                if owner=='prepare':
                    facts.register()
                    facts.writes.clear()
                facts.conversion_admitted=False
                with self.assertRaisesRegex(AuthorityDenied,'observation-only'):
                    getattr(facts,owner)()
                self.assertEqual(facts.writes,[])
                self.assertEqual(facts.grants.calls,0)


if __name__ == '__main__':
    unittest.main()
