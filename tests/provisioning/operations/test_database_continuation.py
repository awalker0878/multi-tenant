"""Actual mTLS peers; explicit synthetic control-ledger fixtures, no native SQL.

These tests verify the three-owner continuation boundary and its query scopes.
They neither commission a database endpoint nor produce migration evidence.
"""
from copy import deepcopy
from datetime import timedelta
import queue
from pathlib import Path
import socket
import ssl
import tempfile
import threading
import unittest

from provisioner.controlplane.authority.model import PlanScope, WorkerGrant
from provisioner.controlplane.authority.service import AuthorityDenied
from provisioner.controlplane.operations.action_gate import scope_digest
from provisioner.controlplane.persistence import TenantContext
from provisioner.controlplane.persistence.store import NativeBinding, OwnerLease
from provisioner.controlplane.reconciliation.registry import NativeOperationRegistry
from provisioner.controlplane.worker.command_runtime import WorkerCommandRuntime
from provisioner.controlplane.worker.credential_custody import VaultNativeCredentialLeaseStore
from provisioner.controlplane.worker.grants import CredentialBroker, GrantDenied, PostgresWorkerGrants
from provisioner.controlplane.worker.pki import MutualTlsWorkerVerifier
from provisioner.controlplane.worker.vault import VaultDynamicCredentialIssuer
from provisioner.controlplane.workflow.admitted_job import AdmittedInput
from provisioner.controlplane.workflow.execution_selection import PostgresExecutionAuthority
from provisioner.execution.run_files import digest, encoded
from provisioner.migration.postgresql_authority import DatabaseOperationContext, DatabaseWorkerRuntime
from provisioner.migration.postgresql_sync import FORMAT, PostgresqlSyncSelection
from tests.provisioning.operations.campaign_fixtures import AS_OF
from tests.provisioning.operations import test_operations_gate as operating_fixtures
from tests.provisioning.worker.tls_fixtures import TestPki


class _SyntheticGrants(PostgresWorkerGrants):
    def __init__(self):
        self.grants = {}; self.revoked = set(); self.checks = []

    def verify_intent(self, cursor, context, **arguments):
        self.checks.append((cursor, context, arguments))
        grant = self.grants[arguments['grant_id']]
        if grant.grant_id in self.revoked or grant.expires_at <= cursor.now:
            raise GrantDenied('Synthetic original grant withdrawn or expired')
        assert (context.organization_id, context.tenant_id) == (grant.organization_id, grant.tenant_id)
        assert arguments['job_id'] == cursor.admitted.job_id
        assert arguments['worker_identity'].subject == grant.worker_subject
        assert all(arguments[key] == getattr(grant, key) for key in (
            'step_id', 'operation_id', 'operation_kind', 'operation_scope', 'lease_key', 'lease_epoch'))
        return grant


class _SyntheticAuthority(PostgresExecutionAuthority):
    def __init__(self, gate):
        self.operations = gate


class _NoCredentials(VaultDynamicCredentialIssuer):
    def __init__(self, store):
        self._lease_store = store

    def issue(self, *args, **kwargs):
        raise AssertionError('This test cannot issue native credentials')


class _Cursor:
    def __init__(self, admitted, workers):
        self.admitted, self.now = admitted, AS_OF
        self.intents = {}; self.exemptions = []; self.containment = set()
        self.owners = {worker.lease.binding.key(): (
            worker.lease.organization_id, worker.lease.tenant_id, worker.lease.security_domain_id,
            worker.lease.workload_id, worker.lease.worker_id, worker.lease.epoch, worker.lease.expires_at)
            for worker in workers.values()}

    def execute(self, query, parameters=()):
        if query == 'SELECT clock_timestamp()':
            self.row = (self.now,)
        elif query.startswith('SELECT organization_id, tenant_id, security_domain_id, workload_id, '):
            self.row = self.owners.get(parameters)
        elif query.startswith('SELECT 1 FROM hosting_controlplane.native_containment_holds'):
            self.row = (1,) if parameters in self.containment else None
        elif query.startswith('SELECT state,job_id,grant_id,step_id,lease_key,owner_epoch,worker_id,'):
            assert 'FOR SHARE' in query
            assert parameters[:2] == (self.admitted.organization_id, self.admitted.tenant_id)
            self.row = self.intents.get(parameters[2])
        elif query.startswith("SELECT current_setting('app.organization_id',true)"):
            assert "i.job_id=%s AND i.operation_id=ANY(%s::text[]) AND i.state IN ('IN_FLIGHT','TASK_ACCEPTED')" in query
            assert parameters[-3:] == (self.admitted.organization_id, self.admitted.tenant_id, self.admitted.job_id)
            excluded = set(parameters[5]); job_id = parameters[4]
            self.exemptions.append(tuple(parameters[5]))
            unresolved = sum(row[0] in ('IN_FLIGHT', 'TASK_ACCEPTED', 'UNCERTAIN')
                and not (row[1] == job_id and op in excluded and row[0] in ('IN_FLIGHT', 'TASK_ACCEPTED'))
                for op, row in self.intents.items())
            self.row = (self.admitted.organization_id, self.admitted.tenant_id, self.now, 'RUNNING',
                self.admitted.plan_revision, self.admitted.plan_digest, self.admitted.revocation_epoch,
                unresolved, len(self.containment))
        else:
            raise AssertionError('Unexpected SQL in this explicit fixture: ' + query)

    def fetchone(self):
        return self.row


class DatabaseContinuationTests(unittest.TestCase):
    def setUp(self):
        # Existing signed minimum prerequisite fixture, independently from the
        # original SQL owner grants and actual TLS enrollment below.
        minimum = operating_fixtures.OperatingGateTests(
            'test_current_actual_signed_retained_prerequisites_and_epoch_pass_synthetic_fixture')
        minimum.setUp()
        self.minimum, self.gate = minimum, minimum.gate
        self.admitted = AdmittedInput('job-fixture', 'org-fixture', 'tenant-fixture', 'plan-fixture',
                                     1, 'c' * 64, 0, 'd' * 64)
        self.selection = minimum.selection
        self.selection.update(driver='openstack-linux-application-database/1', workloadId='workload-fixture')
        scope = lambda side: PlanScope.from_record(self.selection[side])
        source, target = scope('source'), scope('destination')
        endpoint = lambda name: dict(nativeDatasetId='dataset-' + name, database='application',
            systemIdentifier='123456789' if name == 'source' else '987654321', host='postgres.example',
            hostaddr='127.0.0.1', port=5432, caFile='/fixture/not-a-native-ca.pem', caDigest='a' * 64,
            ownerRole='sync_' + name, readRole='independent_' + name)
        body = dict(format=FORMAT, datasetId='data-fixture', memberId='member-fixture', streamId='stream-fixture',
            targetRef='database-target', consistencyGroupId='sql-consistency',
            source_scope=self.selection['source'], target_scope=self.selection['destination'],
            source={**endpoint('source'), 'fenceOwnerRole': 'sync_fence'}, target=endpoint('target'),
            sourceGuest=dict(native_id='vm-source', native_uuid='1' * 8 + '-1111-1111-1111-' + '1' * 12, machine_id='1' * 32),
            targetGuest=dict(native_id='vm-target', native_uuid='2' * 8 + '-2222-2222-2222-' + '2' * 12, machine_id='2' * 32),
            publication='pub_fixture', subscription='sub_fixture', slot='slot_fixture',
            tables=[dict(schema='application', name='accounts', columns=[dict(name='id', typeOid=23,
                typeModifier=-1, key=True, notNull=True)])], maxRows=100, maxBytes=4096,
            operations={side: dict(stepId='step-' + side, operationId='op-' + side)
                        for side in ('source', 'target', 'fence')}, sourceWriterRoles=['application_writer'])
        self.descriptor = PostgresqlSyncSelection.from_record(body)
        self.selection['applicationDatabaseSelectionDigest'] = self.descriptor.sha256
        minimum.payload['scopeDigest'] = scope_digest(self.selection)
        minimum.retain()
        self.grants = _SyntheticGrants(); self.gate.worker_grants = self.grants
        authority = _SyntheticAuthority(self.gate)
        registry = NativeOperationRegistry(lambda: self.fail('Fixture cannot connect to a control database'),
            grants=self.grants, evidence=type('NoNativeEvidence', (), {
                'verify_native_observation': lambda *args: None, 'verify_owner_exclusion': lambda *args: None})())
        custody = tempfile.TemporaryDirectory(); self.addCleanup(custody.cleanup)
        store = VaultNativeCredentialLeaseStore(registry._connect, directory=Path(custody.name))
        self.pki = TestPki(); self.addCleanup(self.pki.close); self.pki.issue('server')
        self.verifier = MutualTlsWorkerVerifier(server_certificate=self.pki.root / 'server.pem',
            server_key=self.pki.root / 'server.key', trust_bundle=self.pki.root / 'ca.pem',
            crl_bundle=self.pki.root / 'crl.pem', trust_domain='workers.example')
        peers = {side: self.peer(side, site) for side, site in (('source', source.site_id), ('target', target.site_id))}
        self.workers = {}
        for side in ('source', 'target', 'fence'):
            native = 'source' if side == 'fence' else side
            scope = source if native == 'source' else target
            peer, identity = peers[native]
            kind = 'SOURCE_FENCE' if side == 'fence' else 'RESTORE_DATA'
            grant = WorkerGrant('grant-' + side, self.admitted.organization_id, self.admitted.tenant_id,
                self.admitted.plan_id, 1, self.admitted.plan_digest, source, target, identity.subject,
                'step-' + side, 'op-' + side, kind, scope, 'lease-' + side, 1, ('approval-fixture',),
                0, AS_OF - timedelta(minutes=1), AS_OF + timedelta(minutes=4))
            self.grants.grants[grant.grant_id] = grant
            binding = NativeBinding(scope.platform_family, scope.endpoint_id, scope.native_scope_id,
                                    'dataset', body[native]['nativeDatasetId'])
            lease = OwnerLease(binding, grant.organization_id, grant.tenant_id, scope.security_domain_id,
                               self.selection['workloadId'], identity.subject, 1, grant.expires_at)
            command = WorkerCommandRuntime(authority, self.grants, self.verifier, peer,
                TenantContext(grant.organization_id, grant.tenant_id), identity, grant)
            broker = CredentialBroker(self.verifier, self.grants, _NoCredentials(store))
            self.workers[side] = DatabaseWorkerRuntime(command, registry, lease, broker)
        self.coordination = DatabaseOperationContext(self.admitted, encoded(self.selection),
                                                     self.descriptor, self.workers)
        self.cursor = _Cursor(self.admitted, self.workers)

    def peer(self, side, site):
        self.pki.issue(side, client=True,
            uri=f'spiffe://workers.example/org/org-fixture/tenant/tenant-fixture/site/{site}/worker/{side}-owner')
        listener = socket.socket(); listener.bind(('127.0.0.1', 0)); listener.listen(1)
        peers, finished = queue.Queue(), threading.Event()
        def accept():
            try:
                raw, _ = listener.accept()
                peer = self.verifier.context.wrap_socket(raw, server_side=True)
                peers.put(peer); finished.wait(60); peer.close()
            except Exception as exc:
                peers.put(exc)
        thread = threading.Thread(target=accept, daemon=True); thread.start()
        context = ssl.create_default_context(cafile=str(self.pki.root / 'ca.pem'))
        context.load_cert_chain(str(self.pki.root / (side + '.pem')), str(self.pki.root / (side + '.key')))
        client = context.wrap_socket(socket.create_connection(listener.getsockname()), server_hostname='localhost')
        peer = peers.get(timeout=5); self.assertIsInstance(peer, ssl.SSLSocket)
        self.addCleanup(listener.close); self.addCleanup(client.close)
        self.addCleanup(lambda: (finished.set(), thread.join(timeout=3)))
        return peer, self.verifier.verify(peer)

    def intent(self, side, state):
        worker = self.workers[side]; grant = worker.command.grant
        return (state, self.admitted.job_id, grant.grant_id, grant.step_id, grant.lease_key, grant.lease_epoch,
            grant.worker_subject, grant.operation_kind, *worker.lease.binding.key(), self.selection['workloadId'],
            grant.operation_scope.security_domain_id,
            digest(encoded({'descriptor': self.descriptor.sha256, 'side': side})))

    def require(self, *, coordination=None, selection=None):
        self.gate.require_database_continuation(self.cursor, self.admitted,
            self.selection if selection is None else selection,
            coordination=self.coordination if coordination is None else coordination)

    def test_all_original_grants_and_actual_peers_checked_before_claim_with_no_exemption(self):
        self.require()
        self.assertEqual(self.cursor.exemptions, [()])
        self.assertEqual([check[2]['operation_id'] for check in self.grants.checks],
                         ['op-source', 'op-target', 'op-fence'] * 2)
        self.assertTrue(all(check[0] is self.cursor for check in self.grants.checks))

    def test_selected_claims_only_exempt_the_original_current_job_and_request(self):
        self.cursor.intents = {'op-source': self.intent('source', 'IN_FLIGHT'),
                              'op-target': self.intent('target', 'TASK_ACCEPTED'),
                              'op-fence': self.intent('fence', 'PREPARED')}
        self.require()
        self.assertEqual(self.cursor.exemptions, [('op-source', 'op-target')])
        self.cursor.intents['op-fence'] = self.intent('fence', 'RESOLVED')
        self.require()

    def test_uncertain_or_unrelated_work_never_contributes_an_exemption(self):
        for side in ('source', 'target', 'fence'):
            self.cursor.intents = {'op-' + side: self.intent(side, 'UNCERTAIN')}
            with self.assertRaises(AuthorityDenied): self.require()
        self.cursor.intents = {'unselected-operation': self.intent('source', 'IN_FLIGHT')}
        with self.assertRaisesRegex(AuthorityDenied, 'Unresolved native work'): self.require()

    def test_wrong_original_intent_job_grant_worker_epoch_dataset_request_and_scope_hold(self):
        original = self.intent('source', 'IN_FLIGHT')
        for index, value in ((1, 'foreign-job'), (2, 'foreign-grant'), (5, 2), (6, 'other-worker'),
                             (9, 'other-endpoint'), (10, 'other-native-scope'), (12, 'other-database'),
                             (13, 'foreign-workload'), (15, 'b' * 64)):
            changed = list(original); changed[index] = value
            self.cursor.intents = {'op-source': tuple(changed)}
            with self.subTest(field=index), self.assertRaises(AuthorityDenied): self.require()

    def test_one_withdrawn_original_grant_or_owner_epoch_stops_all_commands(self):
        for side in ('source', 'target', 'fence'):
            self.grants.revoked = {'grant-' + side}
            with self.assertRaises(AuthorityDenied): self.require()
        self.grants.revoked = set()
        key = self.workers['target'].lease.binding.key()
        owner = self.cursor.owners[key]
        self.cursor.owners[key] = (*owner[:5], 2, owner[6])
        with self.assertRaises(AuthorityDenied): self.require()

    def test_all_three_original_grants_must_exist_before_first_native_claim(self):
        self.grants.grants.pop('grant-fence')
        with self.assertRaises(AuthorityDenied): self.require()
        self.assertEqual(self.cursor.exemptions, [])

    def test_no_operation_list_forged_artifact_or_different_concrete_grant_owner_is_accepted(self):
        for forged in ({'operations': ['op-source', 'op-target', 'op-fence']}, True):
            with self.assertRaises(AuthorityDenied): self.require(coordination=forged)
        changed = deepcopy(self.selection); changed['workloadId'] = 'foreign-workload'
        with self.assertRaises(AuthorityDenied): self.require(selection=changed)
        self.gate.worker_grants = _SyntheticGrants()
        with self.assertRaises(AuthorityDenied): self.require()

    def test_mtls_trust_rotation_holds_every_original_sql_owner(self):
        self.verifier.reload_trust()
        with self.assertRaises(AuthorityDenied): self.require()

    def test_expiry_or_raw_prerequisite_loss_after_first_locked_check_holds(self):
        original = self.minimum.evidence.require
        def expire(context):
            original(context)
            if self.minimum.evidence.checks >= 2:
                self.cursor.now = AS_OF + timedelta(minutes=5)
        self.minimum.evidence.require = expire
        with self.assertRaises(AuthorityDenied): self.require()
        self.cursor.now = AS_OF
        self.minimum.evidence.require = original
        proof = self.minimum.evidence.artifacts[self.minimum.payload['prerequisites'][0]['evidenceRef']]
        del self.minimum.evidence.artifacts[proof['payload']['observationEventKey']]
        with self.assertRaisesRegex(AuthorityDenied, 'measurements'): self.require()


if __name__ == '__main__':
    unittest.main()
