"""Live PostgreSQL boundaries for the selected native-capable application.

The plan, four approvals, admitted job, immutable outbox start receipt, worker
enrollment, grant, native owner and claimed intent are real database records.
Independent qualification/evidence custody are explicitly synthetic test owners;
their cryptographic and current-dossier contracts have separate tests. The final
callback is a recorder, never a platform client or a qualification campaign.
"""
from __future__ import annotations

import base64
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from uuid import uuid4

from provisioner.controlplane.authority import postgres as authority_postgres
from provisioner.controlplane.authority.model import AuthorizedPlan, FrozenPlan, PlanApproval, PlanScope
from provisioner.controlplane.authority.postgres import PostgresAuthority
from provisioner.controlplane.authority.service import AuthorityDenied
from provisioner.controlplane.jobs import JobRepository, StartReceipt
from provisioner.controlplane.jobs.repository import _digest
from provisioner.controlplane.operations.action_gate import (
    MINIMUM_PREREQUISITES, OperationsActionGate, _canonical,
    acceptance_digest, acceptance_event_key, scope_digest,
)
from provisioner.controlplane.persistence import AuditContext, EnterpriseRecordStore, TenantContext
from provisioner.controlplane.persistence.migrate import apply_migrations
from provisioner.controlplane.persistence.store import NativeBinding
from provisioner.controlplane.reconciliation.registry import NativeLeaseAuthority, NativeOperationRegistry
from provisioner.controlplane.worker import (
    GrantRequest, PostgresWorkerEnrollment, PostgresWorkerGrants,
    VerifiedWorkerIdentity, WorkerCapability,
)
from provisioner.controlplane.workflow.admitted_job import AdmittedInput
from provisioner.controlplane.workflow.execution_selection import (
    DRIVER, FORMAT, FileExecutionSelectionStore, PostgresExecutionAuthority,
)
from provisioner.domain.enterprise_records import plan_digest
from provisioner.execution.delivery_run import validate as validate_delivery
from provisioner.execution.run_files import encoded, write_new
from tests.provisioning.operations.campaign_fixtures import fixture
from tests.provisioning.operations.test_release import TestSigner
from tests.provisioning.schema.test_enterprise_records import plan, workload
from tests.provisioning.worker.test_postgres_worker import (
    TestEnrollmentAuthorizer, TestWorkerVerifier,
)


SYNTHETIC_VAULT_ROLE_REF = 'vault:synthetic-pg-no-native-use'


class ExecutionAuthorityFixtureTests(unittest.TestCase):
    def test_source_fence_fixture_has_a_valid_opaque_role_reference(self):
        scope = PlanScope.from_record(plan()['spec']['source'])
        capability = WorkerCapability(scope, 'SOURCE_FENCE', SYNTHETIC_VAULT_ROLE_REF)
        self.assertEqual(capability.credential_ref, SYNTHETIC_VAULT_ROLE_REF)
        with self.assertRaises(ValueError):
            WorkerCapability(scope, 'SOURCE_FENCE',
                             'controlled-synthetic-credential:no-native-use')


class SelectedQualificationProof:
    """Exact synthetic proof port, isolated from every installed native dossier."""

    def __init__(self, context, selected_digest):
        self.context, self.selected_digest = context, selected_digest
        self.withdrawn = False
        self.actions = []

    def require_action(self, cursor, admitted, selection, operation_kind):
        cursor.execute("SELECT current_setting('app.organization_id',true),"
                       "current_setting('app.tenant_id',true)")
        if (cursor.fetchone() != (self.context.organization_id, self.context.tenant_id)
                or (admitted.organization_id, admitted.tenant_id) !=
                   (self.context.organization_id, self.context.tenant_id)
                or _digest(selection) != self.selected_digest or self.withdrawn
                or operation_kind not in {'SOURCE_FENCE', 'DISCOVER_READ'}):
            raise AuthorityDenied('Synthetic selected proof is unavailable for this exact action')
        self.actions.append(operation_kind)


class RetainedOperatingProof:
    """Synthetic independently retained evidence; no external checkpoint claimed."""

    def __init__(self, context, selection, envelope):
        self.context, self.evidence = context, self
        self.available_contexts = {context}
        self.available = True
        self.checks = 0
        self.key = acceptance_event_key(selection['operationsAcceptanceDigest'])
        self.retained = (SimpleNamespace(evidence_kind='VERIFICATION_RESULT',
            subject_id=scope_digest(selection), event_key=self.key), deepcopy(envelope))

    def require(self, context):
        if context not in self.available_contexts or not self.available:
            raise AuthorityDenied('Synthetic independent evidence custody is held')
        self.checks += 1

    def get(self, context, key):
        self.require(context)
        return self.retained if key == self.key else None


class NoNativeObservation:
    def verify_native_observation(self, *args):
        raise AssertionError('This PostgreSQL boundary test must not contact a platform')

    def verify_owner_exclusion(self, *args):
        raise AssertionError('This PostgreSQL boundary test cannot qualify old-writer exclusion')


@unittest.skipUnless(os.environ.get('HOSTING_TEST_POSTGRES_MIGRATION_DSN')
                     and os.environ.get('HOSTING_TEST_POSTGRES_RUNTIME_DSN')
                     and os.environ.get('HOSTING_TEST_POSTGRES_AUTHORITY_DSN')
                     and os.environ.get('HOSTING_TEST_POSTGRES_ENROLLMENT_DSN')
                     and os.environ.get('HOSTING_TEST_POSTGRES_ISOLATED') == '1',
                     'Requires the explicitly isolated PostgreSQL CI roles')
class ExecutionAuthorityPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import psycopg
        except ImportError as exc:
            raise unittest.SkipTest('Install hosting-provisioner[controlplane]') from exc
        cls.psycopg = psycopg
        cls.migration_dsn = os.environ['HOSTING_TEST_POSTGRES_MIGRATION_DSN']
        cls.runtime_dsn = os.environ['HOSTING_TEST_POSTGRES_RUNTIME_DSN']
        cls.authority_dsn = os.environ['HOSTING_TEST_POSTGRES_AUTHORITY_DSN']
        cls.enrollment_dsn = os.environ['HOSTING_TEST_POSTGRES_ENROLLMENT_DSN']
        apply_migrations(lambda: psycopg.connect(cls.migration_dsn))

    def runtime(self):
        return self.psycopg.connect(self.runtime_dsn)

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.callbacks = []
        self.build_case()

    def build_case(self, *, acknowledge=True):
        suffix = uuid4().hex[:16]
        self.context = TenantContext('org-execution-' + suffix, 'tenant-execution-' + suffix)
        self.audit = AuditContext('execution-plan-author', 'execution-fixture-' + suffix)
        self.now = datetime.now(timezone.utc)
        self.observed, self.selected = deepcopy(workload()), deepcopy(plan())
        for record in (self.observed, self.selected):
            record['metadata'].update(organizationId=self.context.organization_id,
                                      tenantId=self.context.tenant_id)
        self.observed['metadata']['workloadId'] = 'workload-' + suffix
        self.selected['metadata']['planId'] = 'plan-' + suffix
        self.selected['spec']['workloadId'] = self.observed['metadata']['workloadId']
        for scope in (self.selected['spec']['source'], self.selected['spec']['destination']):
            scope.update(organizationId=self.context.organization_id, tenantId=self.context.tenant_id)
        destination = self.selected['spec']['destination']
        destination.update(platformFamily='openstack', endpointId='openstack-fixture',
                           nativeScopeId='project-fixture')
        self.selected['spec']['route']['method'] = 'REBUILD_RESTORE'
        # Native identity is globally owned: each test observes its own distinct
        # VM/disk/NIC rather than sharing the template's global native objects.
        for machine in self.observed['spec']['machines']:
            for resource in (machine, *machine['disks'], *machine['nics']):
                resource['bindings'][0]['binding']['nativeId'] += '-' + suffix
        for mapping, machine in zip(self.selected['spec']['machineMappings'],
                                    self.observed['spec']['machines']):
            mapping['sourceBinding'] = deepcopy(machine['bindings'][0]['binding'])

        _, _, self.selection = fixture()
        self.selection.update(format=FORMAT,
            workloadId=self.observed['metadata']['workloadId'], workloadRevision=1,
            source=deepcopy(self.selected['spec']['source']), destination=deepcopy(destination),
            executionScope={'environment_key': 'execution-fixture', 'site_key': destination['locationId'],
                'platform': 'openstack', 'tenant_key': self.context.tenant_id,
                'wsd_key': destination['securityDomainId']},
            resourceBundleDigest='1' * 64, datasetSelectionDigest='2' * 64,
            cutoverSelectionDigest='3' * 64)
        self.parameters = {'fixtureAction': 'observe-approved-source'}
        self.step = {'id': 'observe-source', 'kind': 'workload_inputs', 'needs': []}
        self.delivery = {'format': 'hosting-delivery/2',
            'source_commit': self.selection['sourceCommit'], 'operation_id': 'delivery-' + suffix,
            'generation': 1, 'scope': deepcopy(self.selection['executionScope']),
            'steps': [self.step], 'reviewed_plan_digest': '4' * 64,
            'operation_bindings': {}, 'reviewed_parameters': {self.step['id']: self.parameters},
            'compiled_catalog_ids': {}}
        validate_delivery(self.delivery)
        self.selection['deliveryPlanDigest'] = _digest(self.delivery)
        self.selection['stageBindings'] = {self.step['id']: {
            'kind': self.step['kind'], 'parametersDigest': _digest(self.parameters),
            'inputDigests': {'workload': '5' * 64}}}
        self.packet = {'parameters': deepcopy(self.parameters),
                       'files': {'workload': {'sha256': '5' * 64}}}

        self.signer = TestSigner('synthetic-independent-operating-fixture')
        payload = {'format': 'hosting-selected-operating-acceptance/1',
            'scopeDigest': scope_digest(self.selection), 'sourceCommit': self.selection['sourceCommit'],
            'planId': self.selected['metadata']['planId'], 'revocationEpoch': 0,
            'acceptedAt': (self.now - timedelta(minutes=1)).isoformat(),
            'reviewBy': (self.now + timedelta(hours=1)).isoformat(),
            'reviewerRef': 'controlled-operating-reviewer:synthetic-pg-test',
            'prerequisites': [{'id': ident, 'result': 'ACCEPTED',
                'evidenceRef': 'controlled-operating-evidence:synthetic-' + ident,
                'artifactSha256': hashlib.sha256(ident.encode()).hexdigest(),
                'observerRef': 'controlled-independent-observer:synthetic-pg-test',
                'observedAt': (self.now - timedelta(minutes=2)).isoformat(),
                'freshUntil': (self.now + timedelta(hours=1)).isoformat()}
                for ident in sorted(MINIMUM_PREREQUISITES)]}
        self.envelope = {'payload': payload, 'keyId': self.signer.key_id,
                        'signature': base64.b64encode(self.signer.sign(_canonical(payload))).decode()}
        self.selection['operationsAcceptanceDigest'] = acceptance_digest(self.envelope)
        self.selection_digest = _digest(self.selection)
        self.selection_directory = self.root / suffix
        self.selection_directory.mkdir(mode=0o700)
        self.selection_path = self.selection_directory / (self.selection_digest + '.json')
        write_new(self.selection_path, encoded(self.selection))
        self.selections = FileExecutionSelectionStore(self.selection_directory)
        self.selected['spec']['execution'] = {'format': 'hosting-execution-selection/1',
            'driver': DRIVER, 'artifactDigest': self.selection_digest}
        self.selected['spec']['route'].update(qualificationDigest=self.selection['qualificationDigest'],
                                              guestProfile=self.selection['guestProfile'])
        self.selected['metadata']['planDigest'] = plan_digest(self.selected)
        self.store = EnterpriseRecordStore(self.runtime)
        self.store.create(self.context, self.observed, self.audit)
        self.store.create(self.context, self.selected, self.audit)
        self.frozen = FrozenPlan.from_record(self.selected, author_subject=self.audit.actor_id)
        self.approvals = PostgresAuthority(lambda: self.psycopg.connect(self.authority_dsn))
        approval_ids = []
        for index, (role, scope) in enumerate((('SOURCE_OWNER', self.frozen.source),
                ('DESTINATION_OWNER', self.frozen.destination),
                ('SOURCE_SECURITY', self.frozen.source),
                ('DESTINATION_SECURITY', self.frozen.destination))):
            approval = PlanApproval('approval-' + suffix + '-' + str(index),
                self.context.organization_id, self.context.tenant_id, self.frozen.plan_id,
                1, self.frozen.digest, role, scope, 'independent-reviewer-' + str(index),
                self.now - timedelta(minutes=1), self.now + timedelta(hours=1), 0)
            self.approvals.append_if_current(self.frozen, approval, 0)
            approval_ids.append(approval.approval_id)
        decision = AuthorizedPlan(self.context.organization_id, self.context.tenant_id,
            self.frozen.plan_id, 1, self.frozen.digest, self.frozen.source, self.frozen.destination,
            tuple(approval_ids), 0, self.now + timedelta(minutes=3), 'execution-operator')
        self.jobs = JobRepository(self.runtime, authority_postgres)
        self.job = self.jobs.submit(self.context, decision, idempotency_key='execution-' + suffix)
        self.message = self.jobs.claim_start(self.context, dispatcher_id='execution-test')
        self.assertIsNotNone(self.message)
        self.jobs.revalidate_start(self.context, self.message)
        self.jobs.record_start_attempt(self.context, self.message,
                                       namespace='execution-test', retention_seconds=86400)
        self.receipt = StartReceipt('execution-test', self.job.job_id, 'run-' + suffix,
            self.job.job_id, self.frozen.plan_id, 1, self.frozen.digest, _digest(self.message.payload))
        if acknowledge:
            self.assertTrue(self.jobs.mark_started(self.context, self.message, self.receipt,
                                                   namespace='execution-test'))
        self.admitted = AdmittedInput(self.job.job_id, self.context.organization_id,
            self.context.tenant_id, self.frozen.plan_id, 1, self.frozen.digest, 0,
            self.receipt.payload_digest)
        self.qualification = SelectedQualificationProof(self.context, self.selection_digest)
        self.evidence = RetainedOperatingProof(self.context, self.selection, self.envelope)
        self.leases = NativeLeaseAuthority(self.runtime)
        self.grants = PostgresWorkerGrants(self.runtime, self.leases)
        self.operations = OperationsActionGate(evidence_gate=self.evidence,
            operating_verifier=self.signer, operating_key_ids=frozenset({self.signer.key_id}),
            worker_grants=self.grants)
        self.authority = PostgresExecutionAuthority(self.runtime, self.selections,
            self.qualification, self.evidence, self.operations)

    def boundary(self, *, admitted=None, selection_digest=None, **continuation):
        plan_record, selection = self.authority.require_current(admitted or self.admitted,
            selection_digest or self.selection_digest, 'SOURCE_FENCE', **continuation)
        # A recorder at the effect boundary proves a refused check cannot get as
        # far as invoking the native owner. This is deliberately not native I/O.
        self.callbacks.append(('SOURCE_FENCE', plan_record['metadata']['planDigest']))
        return plan_record, selection

    def refused(self, **kwargs):
        before = tuple(self.callbacks)
        with self.assertRaises((AuthorityDenied, PermissionError, ValueError)):
            self.boundary(**kwargs)
        self.assertEqual(tuple(self.callbacks), before)

    def claim_original(self, *, ttl=timedelta(minutes=3)):
        self.identity = VerifiedWorkerIdentity(self.context.organization_id, self.context.tenant_id,
            'worker-' + uuid4().hex[:12], self.frozen.source.site_id,
            uuid4().hex + uuid4().hex, self.now + timedelta(hours=1))
        self.enrollment = PostgresWorkerEnrollment(
            lambda: self.psycopg.connect(self.enrollment_dsn),
            TestWorkerVerifier(), TestEnrollmentAuthorizer())
        self.enrollment.enroll(self.identity, self.context, 'approved-enrollment',
            capabilities=(WorkerCapability(self.frozen.source, 'SOURCE_FENCE',
                                           SYNTHETIC_VAULT_ROLE_REF),))
        self.binding = NativeBinding.from_record(
            self.observed['spec']['machines'][0]['bindings'][0]['binding'])
        self.lease = self.store.acquire_owner_lease(self.context, self.selected['spec']['source'],
            self.binding, self.observed['metadata']['workloadId'], self.identity.subject,
            300, self.audit)
        self.operation_id, self.lease_key = 'operation-' + uuid4().hex, 'lease-' + uuid4().hex
        self.leases.register(self.context, self.lease, self.frozen.source,
            lease_key=self.lease_key, job_id=self.admitted.job_id, operation_id=self.operation_id,
            worker_identity=self.identity)
        request = GrantRequest(self.admitted.job_id, 'source-fence', self.operation_id,
            'SOURCE_FENCE', self.frozen.source, self.lease_key, self.lease.epoch, ttl)
        self.grant = self.grants.issue_grant(self.context, self.identity, request)
        registry = NativeOperationRegistry(self.runtime, grants=self.grants, evidence=NoNativeObservation())
        registry.prepare(self.context, self.lease, self.frozen.source,
            job_id=self.admitted.job_id, grant_id=self.grant.grant_id, step_id=self.grant.step_id,
            lease_key=self.lease_key, worker_identity=self.identity, operation_id=self.operation_id,
            operation_kind='SOURCE_FENCE', request_digest='6' * 64)
        self.assertTrue(registry.claim_once(self.context, self.lease, self.frozen.source,
                                           self.operation_id, self.identity))
        self.assertFalse(registry.claim_once(self.context, self.lease, self.frozen.source,
                                            self.operation_id, self.identity))
        return {'continuation_grant': self.grant, 'continuation_identity': self.identity}

    def scoped_owner(self):
        connection = self.psycopg.connect(self.migration_dsn)
        connection.execute("SELECT set_config('app.organization_id',%s,true),"
                           "set_config('app.tenant_id',%s,true)",
                           (self.context.organization_id, self.context.tenant_id))
        return connection

    def test_approved_original_job_receipt_artifact_and_live_operating_rows_reach_boundary(self):
        selected, artifact = self.boundary()
        self.assertEqual(selected, self.selected)
        self.assertEqual(artifact, self.selection)
        self.assertEqual(self.jobs.start_run(self.context, self.job.job_id), self.receipt)
        self.assertEqual(self.qualification.actions, ['SOURCE_FENCE'])
        self.assertGreaterEqual(self.evidence.checks, 3)

    def test_forged_payload_plan_epoch_or_foreign_tenant_never_reach_boundary(self):
        # These independently current *empty* tenant custody fixtures must not
        # mask a failure of the actual job RLS/scope check. No original selected
        # qualification proof should be reached for either foreign job lookup.
        self.evidence.available_contexts.update({
            TenantContext(self.context.organization_id, 'foreign-tenant'),
            TenantContext('foreign-organization', self.context.tenant_id)})
        for fields in ({'payload_digest': '7' * 64}, {'plan_digest': '8' * 64},
                {'plan_revision': 2}, {'revocation_epoch': 1}, {'plan_id': 'foreign-plan'},
                {'tenant_id': 'foreign-tenant'}, {'organization_id': 'foreign-organization'}):
            with self.subTest(fields=fields):
                self.refused(admitted=replace(self.admitted, **fields))
        self.assertEqual(self.qualification.actions, [])

    def test_tampered_private_bytes_and_unapproved_replacement_digest_are_held(self):
        changed = deepcopy(self.selection)
        changed['stageBindings'][self.step['id']]['parametersDigest'] = '9' * 64
        self.selection_path.write_bytes(encoded(changed))
        self.refused()
        changed_digest = _digest(changed)
        write_new(self.selection_directory / (changed_digest + '.json'), encoded(changed))
        self.refused(selection_digest=changed_digest)
        self.assertEqual(self.qualification.actions, [])

    def test_withdrawn_four_role_approval_is_live_before_every_boundary(self):
        self.boundary()
        self.assertEqual(self.approvals.revoke_if_current(self.frozen, 0,
            'independent-reviewer-0', 'Withdraw the approved change'), 1)
        self.refused()

    def test_current_workload_successor_invalidates_original_admission(self):
        successor = deepcopy(self.observed)
        successor['metadata']['revision'] = 2
        self.store.update(self.context, successor, 1, self.audit)
        self.refused()

    def test_current_plan_successor_cannot_reuse_original_job_or_artifact_admission(self):
        successor = deepcopy(self.selected)
        successor['metadata']['revision'] = 2
        successor['spec']['maxDowntimeSeconds'] += 1
        successor['metadata']['planDigest'] = plan_digest(successor)
        self.store.update(self.context, successor, 1, self.audit)
        self.refused()

    def test_acknowledged_original_run_is_required_even_if_status_was_changed(self):
        self.build_case(acknowledge=False)
        # A process that changes only a projection status cannot forge the
        # original durable run receipt, which is checked independently.
        with self.runtime() as connection:
            connection.execute("SELECT set_config('app.organization_id',%s,true),"
                               "set_config('app.tenant_id',%s,true)",
                               (self.context.organization_id, self.context.tenant_id))
            connection.execute("UPDATE hosting_controlplane.operation_jobs SET status='STARTED' "
                'WHERE organization_id=%s AND tenant_id=%s AND job_id=%s',
                (self.context.organization_id, self.context.tenant_id, self.admitted.job_id))
        self.refused()
        self.assertEqual(self.qualification.actions, [])

    def test_withdrawn_qualification_or_missing_minimum_operating_proof_never_calls_owner(self):
        self.qualification.withdrawn = True
        self.refused()
        self.qualification.withdrawn = False
        self.evidence.retained = None
        self.refused()
        self.evidence.available = False
        self.refused()

    def test_exact_selected_packet_params_and_nonsecret_file_digests_are_mandatory(self):
        self.assertEqual(self.authority.require_packet(self.admitted, self.selection_digest,
            self.delivery, self.step, self.packet, 'DISCOVER_READ'), self.selected)
        changed = deepcopy(self.packet)
        changed['parameters']['fixtureAction'] = 'another-action'
        with self.assertRaises(ValueError):
            self.authority.require_packet(self.admitted, self.selection_digest,
                self.delivery, self.step, changed, 'DISCOVER_READ')
        changed = deepcopy(self.packet)
        changed['files']['workload']['sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            self.authority.require_packet(self.admitted, self.selection_digest,
                self.delivery, self.step, changed, 'DISCOVER_READ')
        self.assertEqual(self.callbacks, [])

    def test_live_claimed_original_grant_continues_but_cannot_enable_new_claim(self):
        continuation = self.claim_original()
        self.refused()
        self.boundary(**continuation)
        self.assertEqual(len(self.callbacks), 1)

    def test_revoked_original_worker_certificate_prevents_continuation_callback(self):
        continuation = self.claim_original()
        self.boundary(**continuation)
        self.enrollment.revoke(self.context, 'approved-revocation',
            worker_subject=self.identity.subject, certificate_sha256=self.identity.certificate_sha256)
        self.refused(**continuation)

    def test_expired_original_grant_cannot_continue_a_still_live_claimed_intent(self):
        continuation = self.claim_original(ttl=timedelta(seconds=5))
        self.boundary(**continuation)
        # Worker grants are append-only. Exercise their actual PostgreSQL-clock
        # expiry without editing that ledger or replacing a current-time owner.
        with self.runtime() as connection:
            connection.execute('SELECT pg_sleep(GREATEST(0, '
                'EXTRACT(EPOCH FROM (%s::timestamptz-clock_timestamp()))+0.05))',
                (self.grant.expires_at,))
        self.refused(**continuation)

    def test_expired_database_lease_and_wrong_original_operation_never_continue(self):
        continuation = self.claim_original()
        self.refused(continuation_grant=replace(self.grant, operation_id='foreign-operation'),
                     continuation_identity=self.identity)
        with self.scoped_owner() as connection:
            connection.execute('UPDATE hosting_controlplane.native_operation_leases SET '
                "expires_at=clock_timestamp()-interval '1 second' WHERE organization_id=%s "
                'AND tenant_id=%s AND lease_key=%s',
                (self.context.organization_id, self.context.tenant_id, self.lease_key))
        self.refused(**continuation)

    def test_uncertain_original_intent_allows_local_observation_but_no_native_callback(self):
        continuation = self.claim_original()
        with self.scoped_owner() as connection:
            connection.execute("UPDATE hosting_controlplane.native_operation_intents SET state='UNCERTAIN' "
                'WHERE organization_id=%s AND tenant_id=%s AND operation_id=%s',
                (self.context.organization_id, self.context.tenant_id, self.operation_id))
        self.refused(**continuation)
        selected, artifact = self.authority.require_observation(self.admitted, self.selection_digest,
                                                                'LOCAL_RETAINED_OBSERVATION')
        self.assertEqual((selected, artifact), (self.selected, self.selection))
        self.assertEqual(self.callbacks, [])

    def test_terminal_original_history_survives_both_successors_without_native_authority(self):
        for status in ('SUCCEEDED', 'FAILED', 'CANCELLED'):
            with self.subTest(status=status):
                if status != 'SUCCEEDED':
                    self.build_case()
                revised_workload = deepcopy(self.observed)
                revised_workload['metadata']['revision'] = 2
                self.store.update(self.context, revised_workload, 1, self.audit)
                revised_plan = deepcopy(self.selected)
                revised_plan['metadata']['revision'] = 2
                revised_plan['spec']['workloadRevision'] = 2
                revised_plan['spec']['maxDowntimeSeconds'] += 1
                revised_plan['metadata']['planDigest'] = plan_digest(revised_plan)
                self.store.update(self.context, revised_plan, 1, self.audit)
                with self.runtime() as connection:
                    connection.execute("SELECT set_config('app.organization_id',%s,true),"
                                       "set_config('app.tenant_id',%s,true)",
                                       (self.context.organization_id, self.context.tenant_id))
                    connection.execute('UPDATE hosting_controlplane.operation_jobs SET status=%s '
                        'WHERE organization_id=%s AND tenant_id=%s AND job_id=%s',
                        (status, self.context.organization_id, self.context.tenant_id, self.admitted.job_id))
                original, artifact = self.authority.require_observation(
                    self.admitted, self.selection_digest, 'LOCAL_RETAINED_OBSERVATION')
                self.assertEqual((original, artifact), (self.selected, self.selection))
                self.assertEqual(self.qualification.actions, [])
                self.refused()
                self.assertEqual(self.callbacks, [])

    def test_named_observation_refuses_original_digest_tamper_foreign_tenant_or_artifact_drift(self):
        self.evidence.available_contexts.add(TenantContext(self.context.organization_id, 'foreign-tenant'))
        for fields in ({'plan_digest': '7' * 64}, {'payload_digest': '8' * 64},
                       {'tenant_id': 'foreign-tenant'}):
            with self.subTest(fields=fields), self.assertRaises((PermissionError, ValueError)):
                self.authority.require_observation(replace(self.admitted, **fields),
                    self.selection_digest, 'LOCAL_RETAINED_OBSERVATION')
        changed = deepcopy(self.selection)
        changed['source']['endpointId'] = 'foreign-native-endpoint'
        self.selection_path.write_bytes(encoded(changed))
        with self.assertRaises((PermissionError, ValueError)):
            self.authority.require_observation(self.admitted, self.selection_digest,
                                                'LOCAL_RETAINED_OBSERVATION')
        self.assertEqual(self.qualification.actions, [])
        self.assertEqual(self.callbacks, [])


if __name__ == '__main__':
    unittest.main()
