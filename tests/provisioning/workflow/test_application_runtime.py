"""Installed composition and private graph checks; no native qualification.

Real SQLite accounting, descriptor parsing and fixed live-gate construction are
used. PostgreSQL/native proofs and signature backends below are deliberately
synthetic refusing fixtures, never a commissioning or acceptance record.
"""
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from provisioner.allocations import capacity_owner
from provisioner.allocations.transactions import PoolDemand, ResourceBundle
from provisioner.controlplane.authority import AuthorityService, PlanScope
from provisioner.controlplane.authority.service import AuthorityDenied
from provisioner.controlplane.evidence.gate import EvidenceMutationGate
from provisioner.controlplane.operations import runtime as operations_runtime
from provisioner.controlplane.persistence import TenantContext
from provisioner.controlplane.persistence.store import NativeBinding, OwnerLease
from provisioner.controlplane.reconciliation.registry import NativeLeaseAuthority, NativeOperationRegistry
from provisioner.controlplane.worker.grants import PostgresWorkerGrants, VerifiedWorkerIdentity
from provisioner.controlplane.workflow.admitted_job import AdmittedInput
from provisioner.controlplane.workflow.application_runtime import (
    ApplicationNativeProofBindings, ApplicationRuntimeHold, ApplicationRuntimeSettings,
    application_execution_enabled, build_application_worker_components, read_only_graph,
    selected_application_runtime_required)
from provisioner.controlplane.jobs.repository import _job, _payload_from_job
from provisioner.controlplane.workflow.provisioning_activity import FileResourceBundleStore
from provisioner.execution import readback_core as c
from provisioner.execution.run_files import digest, encoded, load_private, utcnow, write_new
from provisioner.migration.activities import MigrationRuntimeBindings
from provisioner.migration.application import ApplicationDataSelection, DatasetWorkerRuntime
from provisioner.migration.cutover import SourceFenceSelection, FORMAT as CUTOVER_FORMAT
from provisioner.migration.resources import LinuxTransferResources, TransferLimits
from tests.provisioning.evidence.test_retained_adapters import FakeTransit
from tests.provisioning.evidence.test_runtime import environment as evidence_environment
from tests.provisioning.schema.test_enterprise_records import SOURCE, TARGET, plan, workload
from provisioner.domain.enterprise_records import plan_digest
from tests.test_restic_run import fixture as restic_config
from tests.test_vsphere_power import request as power_request


class RetainedScopeFixture:
    def __init__(self):
        self.calls = []
        self.refused = False
    def verify(self, context):
        self.calls.append(context)
        if self.refused:
            raise ValueError('Synthetic independent custody refusal')
        return SimpleNamespace(unanchored_count=0)
    def get(self, context, key):
        return None


class RefusingNativeProof:
    """Exercise typed wiring; this fixture cannot assert any native proof."""
    def verify_resource_observation(self, *args):
        raise AuthorityDenied('Synthetic proof is never accepted')
    def verify_creation_observation(self, *args):
        raise AuthorityDenied('Synthetic proof is never accepted')
    def verify_creation_owner_exclusion(self, *args):
        raise AuthorityDenied('Synthetic proof is never accepted')
    def verify_native_observation(self, *args):
        raise AuthorityDenied('Synthetic proof is never accepted')
    def verify_owner_exclusion(self, *args):
        raise AuthorityDenied('Synthetic proof is never accepted')


class ApplicationRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        names = ('execution', 'delivery', 'resource', 'inbox', 'dataset', 'cutover',
                 'migration_input', 'journal', 'result')
        paths = {}
        self.environment = evidence_environment()
        for name in names:
            path = self.root / name
            path.mkdir(mode=0o700)
            paths[name + '_store'] = path
            self.environment['HOSTING_APPLICATION_' + name.upper() + '_STORE'] = str(path)
        self.source_root = self.root / 'accepted-source'
        self.source_root.mkdir(mode=0o755)
        self.database = self.root / 'capacity.db'
        self.environment.update(HOSTING_APPLICATION_CAPACITY_DATABASE=str(self.database),
            HOSTING_APPLICATION_SOURCE_ROOT=str(self.source_root), HOSTING_APPLICATION_EXECUTION='1',
            HOSTING_OPS_ACCEPTANCE_VAULT_TRUST_JSON='{"operating-fixture":["operating","acceptance"]}',
            HOSTING_NATIVE_OBSERVER_VAULT_TRUST_JSON='{"observer-fixture":["observer","native"]}',
            HOSTING_OPERATING_HANDOVER_VAULT_TRUST_JSON='{"handover-fixture":["operating","handover"]}')
        self.source = deepcopy(SOURCE)
        self.destination = TARGET | {'platformFamily': 'openstack', 'endpointId': 'openstack-01',
                                    'nativeScopeId': 'native-pool-01'}
        self.scope = {'environment_key': 'app', 'site_key': self.destination['locationId'],
            'platform': 'openstack', 'tenant_key': self.destination['tenantId'],
            'wsd_key': self.destination['securityDomainId']}
        window = {'valid_from': (utcnow() - timedelta(minutes=1)).isoformat(),
                  'valid_until': (utcnow() + timedelta(minutes=30)).isoformat()}
        units = lambda cpu, memory, storage: dict(vcpu=cpu, memory_mb=memory, storage_gb=storage)
        self.envelope = {'format': 'hosting-capacity-envelope/1', 'owner_id': 'capacity-fixture',
            'revision': 1, **window, 'acceptance_ref': 'TEST-ONLY', 'pools': {'pool-01': {
                'origin': 'https://native.example.invalid', 'native_id': 'native-pool-01',
                'platform': 'openstack', 'site_key': self.scope['site_key'],
                'capacity': units(16, 32768, 100), 'reserve': units(4, 8192, 20),
                'capabilities': ['internal-ipv4'], 'qualification_ref': 'TEST-ONLY'}},
            'tenants': {self.scope['tenant_key']: {'limit': units(8, 16384, 80),
                'pools': ['pool-01'], 'entitlement_ref': 'TEST-ONLY'}}}
        capacity_owner.initialize(self.database, self.envelope)
        catalog = {'format': 'hosting-capacity-sizing/1', 'pool_id': 'pool-01',
            'origin': 'https://native.example.invalid', 'native_id': 'native-pool-01',
            'platform': 'openstack', 'site_key': self.scope['site_key'],
            'placements': [{'compute_availability_zone': 'nova', 'storage_availability_zone': 'nova',
                            'volume_type': 'reviewed'}], 'provider_selector': {'openstack_cloud': 'target'},
            'cloud_sha256': 'a' * 64, 'flavors': {'small': {'vcpu': 2, 'ram_mib': 4096,
                'root_gib': 0, 'ephemeral_gib': 0, 'swap_mib': 0}}, **window,
            'acceptance_ref': 'TEST-ONLY'}
        inputs = {key: value for key, value in self.scope.items() if key != 'platform'}
        inputs.update(openstack_cloud='target', members={'target-machine-1': {
            **catalog['placements'][0], 'flavor_id': 'small', 'boot_disk_gib': 40, 'data_disk_gib': 0}})
        pool = PoolDemand.from_workload(scope=PlanScope.from_record(self.destination), catalog=catalog,
            inputs=inputs, envelope_sha256=c.digest(self.envelope), capabilities=('internal-ipv4',),
            budgets={'staging': units(0, 0, 2), 'snapshots': units(0, 0, 2),
                     'retained-source': units(0, 0, 0)})
        self.admitted = AdmittedInput('application-job', self.source['organizationId'],
            self.source['tenantId'], 'plan-01', 1, 'c' * 64, 0, 'd' * 64)
        self.resource = ResourceBundle(self.admitted, 'e' * 64, 'workload-01', 1, (pool,)).document()
        config = restic_config()
        captured_at = utcnow().isoformat()
        manifest = {'format': 'hosting-file-manifest/1', 'scope': config['scope'], 'member': config['member'],
            'source': config['source'], 'captured_at': captured_at, 'consistency_ref': config['consistency_ref'],
            'files': {'payload': {'size': 4, 'sha256': digest(b'data')}}}
        receipt = {'format': 'hosting-restic-receipt/1', 'status': 'CAPTURED_REQUIRES_RESTORE_TEST',
            'scope': config['scope'], 'member': config['member'], 'repository_id': config['repository_id'],
            'source': config['source'], 'manifest_sha256': digest(encoded(manifest)),
            'captured_at': captured_at, 'snapshot_id': 'f' * 64}
        stage = self.root / 'dedicated-stage'
        self.dataset = {'format': 'hosting-application-dataset-selection/1',
            'source_scope': self.source, 'destination_scope': self.destination,
            'guest_profile': 'linux-ubuntu-2404', 'datasets': [{'step_id': 'restore-1',
                'operation_id': 'restore-operation-1', 'dataset_id': 'dataset-1',
                'target_ref': 'target-dataset-1', 'consistency_group_id': 'group-1',
                'target_member': 'target-guest', 'target_root': str(stage / 'dataset-1'),
                'source_config': config, 'source_receipt': receipt, 'file_manifest': manifest,
                'resources': {'stage_parent': str(stage), 'cgroup': '/hosting/isolated-transfer',
                    'block_device': '8:1', 'limits': {'download_kib_per_second': 128,
                        'block_iops': 20, 'stage_bytes': 1024 * 1024, 'expected_bytes': 4}},
                'target_metadata': {'payload': {'mode': 0o600, 'uid': os.getuid(), 'gid': os.getgid()}}}]}
        self.cutover = {'format': CUTOVER_FORMAT,
            'source_scope': self.source, 'destination_scope': self.destination,
            'source_members': [{'machine_id': 'machine-1', 'step_id': 'fence-1',
                'operation_id': 'fence-operation-1', 'native_id': 'vm-1', 'power_request': power_request()}]}
        self.delivery = {'format': 'hosting-delivery/2', 'source_commit': 'a' * 40,
            'operation_id': 'delivery-1', 'generation': 1, 'reviewed_plan_digest': 'b' * 64,
            'scope': self.scope, 'steps': [{'id': 'inputs', 'kind': 'workload_inputs', 'needs': []},
                {'id': 'plan', 'kind': 'terraform_plan', 'needs': ['inputs']},
                {'id': 'apply', 'kind': 'terraform_apply', 'needs': ['plan']},
                {'id': 'guest', 'kind': 'guest_apply', 'needs': ['apply']}],
            'operation_bindings': {}, 'reviewed_parameters': {}, 'compiled_catalog_ids': {}}
        self.artifact = {'format': 'hosting-openstack-execution-artifact/1',
            'driver': 'openstack-linux-rebuild/1', 'sourceCommit': 'a' * 40,
            'workloadId': 'workload-01', 'workloadRevision': 1, 'source': self.source,
            'destination': self.destination, 'executionScope': self.scope,
            'resourceBundleDigest': c.digest(self.resource),
            'datasetSelectionDigest': ApplicationDataSelection.from_record(self.dataset).sha256,
            'cutoverSelectionDigest': SourceFenceSelection.from_record(self.cutover).sha256,
            'deliveryPlanDigest': c.digest(self.delivery), 'qualificationDigest': '0' * 64,
            'operationsAcceptanceDigest': '1' * 64, 'sourceTuple': {}, 'destinationTuple': {},
            'guestProfile': 'linux-ubuntu-2404', 'stageBindings': {
                step['id']: {'kind': step['kind'], 'parametersDigest': '2' * 64, 'inputDigests': {}}
                for step in self.delivery['steps']}}
        self.selected = c.digest(self.artifact)
        for name, value in (('execution', self.artifact), ('resource', self.resource),
                            ('dataset', self.dataset), ('cutover', self.cutover), ('delivery', self.delivery)):
            write_new(paths[name + '_store'] / (c.digest(value) + '.json'), encoded(value))
        scope_file = self.root / 'startup-scopes.json'
        write_new(scope_file, encoded([{'organizationId': self.source['organizationId'],
                                      'tenantId': self.source['tenantId']}]))
        self.environment['HOSTING_EVIDENCE_SCOPES_FILE'] = str(scope_file)
        self.settings = ApplicationRuntimeSettings.from_environment(self.environment)
        self.audit, self.evidence = RetainedScopeFixture(), RetainedScopeFixture()
        self.gate = EvidenceMutationGate(self.audit, self.evidence, max_unanchored_count=0)
        self.connect = lambda: (_ for _ in ()).throw(AssertionError('No PostgreSQL or native calls in composition'))

    def build(self, **kwargs):
        # Fixed production composition still runs; only Vault transport is the
        # existing synthetic signer fixture. No environment-selected factory.
        def real_gate(gate, **arguments):
            return operations_runtime.build_action_gate(gate, verifier_client=FakeTransit(), **arguments)
        with patch('provisioner.controlplane.workflow.application_runtime.build_action_gate', side_effect=real_gate):
            return build_application_worker_components(self.connect, self.gate,
                settings=self.settings, environment=self.environment, **kwargs)

    def test_exact_opt_in_and_no_factory_or_store_creation(self):
        self.assertFalse(application_execution_enabled({}))
        self.assertFalse(application_execution_enabled({'HOSTING_APPLICATION_EXECUTION': '0'}))
        self.assertTrue(application_execution_enabled({'HOSTING_APPLICATION_EXECUTION': '1'}))
        for value in ('true', 'yes', 1, ' 1', '01'):
            with self.assertRaises(ApplicationRuntimeHold):
                application_execution_enabled({'HOSTING_APPLICATION_EXECUTION': value})
        missing = self.environment.copy()
        missing.pop('HOSTING_APPLICATION_EXECUTION_STORE')
        with self.assertRaises(ApplicationRuntimeHold) as raised:
            ApplicationRuntimeSettings.from_environment(missing)
        self.assertEqual(raised.exception.dependency, 'HOSTING_APPLICATION_EXECUTION_STORE')
        with self.assertRaises(ApplicationRuntimeHold):
            ApplicationRuntimeSettings.from_environment(self.environment | {
                'HOSTING_APPLICATION_FACTORY': 'untrusted.module:create'})
        self.assertNotIn(str(self.root), str(raised.exception))

    def test_paths_must_be_private_separate_and_not_replaced(self):
        directory = self.settings.inbox_store
        directory.chmod(0o755)
        with self.assertRaises(ApplicationRuntimeHold):
            self.settings.require_current()
        directory.chmod(0o700)
        directory.rename(directory.with_name('old-inbox'))
        directory.mkdir(mode=0o700)
        with self.assertRaises(ApplicationRuntimeHold) as raised:
            self.settings.require_current()
        self.assertEqual(raised.exception.hold_code, 'APPLICATION_STORE_IDENTITY_CHANGED')
        with self.assertRaises(ApplicationRuntimeHold):
            replace(self.settings, result_store=self.settings.execution_store)
        linked = self.root / 'linked'; linked.symlink_to(self.settings.execution_store)
        with self.assertRaises(ApplicationRuntimeHold):
            replace(self.settings, execution_store=linked)

    def test_empty_native_bindings_have_real_fixed_owners_and_precise_holds(self):
        components = self.build()
        self.assertIs(components.worker_grants._leases, components.planned_leases)
        self.assertIs(components.planned_leases.resources, components.resources)
        self.assertIs(components.authority.qualification, components.action_gate.qualification)
        self.assertIs(components.authority.operations, components.action_gate.operations)
        self.assertIs(components.action_gate.operations.worker_grants, components.worker_grants)
        self.assertIs(components.provisioning.authority, components.migration.authority)
        self.assertEqual(len(components.activities), 34)
        self.assertIsNone(components.creation_registry)
        self.assertIsNone(components.native_registry)
        self.assertIn('ENROLLED_NATIVE_PROVISIONING_WORKERS_REQUIRED', components.hold_codes)
        self.assertIn('ENROLLED_ISOLATED_TRANSFER_WORKERS_REQUIRED', components.hold_codes)
        self.assertIn('GUEST_PER_COMMAND_AUTHORITY_UNAVAILABLE', components.hold_codes)
        self.assertFalse(components.projection()['nativeExecutionAuthorized'])
        with self.assertRaises(AuthorityDenied):
            components.resources.authority._evidence.verify_resource_observation(None, None, 'release', None)
        context = TenantContext(self.source['organizationId'], self.source['tenantId'])
        self.assertEqual(self.audit.calls, [context])
        self.assertEqual(self.evidence.calls, [context])

    def test_native_proof_owner_is_explicit_and_no_positive_default_exists(self):
        proof = RefusingNativeProof()
        components = self.build(native_proof_bindings=ApplicationNativeProofBindings(proof, proof, proof))
        self.assertIs(components.creation_registry._evidence, proof)
        self.assertIs(components.native_registry._evidence, proof)
        self.assertIs(components.resources.authority._evidence, proof)
        with self.assertRaises(AuthorityDenied):
            components.resources.authority._evidence.verify_resource_observation(None, None, 'confirm', None)
        for forged in ({'accepted': True}, lambda *args: True, 'proof.json'):
            with self.assertRaises(TypeError):
                ApplicationNativeProofBindings(resource=forged)
        with self.assertRaises(TypeError):
            self.build(provisioning_bindings={('job', 'step'): lambda: True})

    def test_scope_custody_and_distinct_operating_trust_fail_closed_at_startup(self):
        self.audit.refused = True
        with self.assertRaises(ApplicationRuntimeHold) as raised:
            self.build()
        self.assertEqual(raised.exception.hold_code, 'APPLICATION_EVIDENCE_OR_OPERATING_TRUST_UNAVAILABLE')
        self.audit.refused = False
        for trust in ('{"evidence-2026":["transit","checkpoints"]}', '{}'):
            self.environment['HOSTING_OPS_ACCEPTANCE_VAULT_TRUST_JSON'] = trust
            with self.assertRaises(ApplicationRuntimeHold):
                self.build()
        self.environment['HOSTING_OPS_ACCEPTANCE_VAULT_TRUST_JSON'] = '{"operating-fixture":["operating","acceptance"]}'
        scope_path = Path(self.environment['HOSTING_EVIDENCE_SCOPES_FILE'])
        scope_path.write_text('[]')
        with self.assertRaises(ApplicationRuntimeHold):
            self.build()

    def test_corrupt_capacity_chain_or_different_grant_lease_owner_holds_before_registration(self):
        grants = PostgresWorkerGrants(self.connect, NativeLeaseAuthority(self.connect))
        with self.assertRaises(ApplicationRuntimeHold) as raised:
            self.build(worker_grants=grants)
        self.assertEqual(raised.exception.hold_code, 'PLANNED_WORKER_GRANT_OWNER_REQUIRED')
        with capacity_owner.database(self.database) as database:
            database.execute("UPDATE event SET digest=? WHERE sequence=1", ('f' * 64,))
        with self.assertRaises(ApplicationRuntimeHold) as raised:
            self.build()
        self.assertEqual(raised.exception.hold_code, 'APPLICATION_CAPACITY_OWNER_UNAVAILABLE')

    def test_prebuilt_owner_reuses_the_same_live_capacity_and_lease_mux(self):
        components = self.build()
        reused = self.build(worker_grants=components.worker_grants)
        self.assertIs(reused.worker_grants, components.worker_grants)
        self.assertIs(reused.resources, components.resources)
        self.assertIs(reused.planned_leases, components.planned_leases)

    def dataset_runtime(self, components, *, registry=None):
        scope = PlanScope.from_record(self.destination)
        now = utcnow()
        controls = LinuxTransferResources(self.root / 'dedicated-stage', '/hosting/isolated-transfer',
                                          '8:1', TransferLimits(128, 20, 1024 * 1024, 4))
        lease = OwnerLease(NativeBinding('openstack', scope.endpoint_id, scope.native_scope_id,
            'dataset', 'target-dataset-1'), scope.organization_id, scope.tenant_id,
            scope.security_domain_id, 'workload-01', 'worker-fixture', 1, now + timedelta(minutes=5))
        identity = VerifiedWorkerIdentity(scope.organization_id, scope.tenant_id, 'worker-fixture',
                                         scope.site_id, 'a' * 64, now + timedelta(minutes=5))
        return DatasetWorkerRuntime(AuthorityService(None, None, None), registry or components.native_registry,
            TenantContext(scope.organization_id, scope.tenant_id), lease, identity,
            'never-used-synthetic-worker-token', 'grant-fixture', 'lease-fixture',
            Path('/commissioned/restic'), {'password': 'SECRET-DO-NOT-PROJECT'}, controls)

    def test_typed_rebind_is_immutable_and_cannot_cross_the_actual_b10_owner(self):
        proof = RefusingNativeProof()
        components = self.build(native_proof_bindings=ApplicationNativeProofBindings(proof, proof, proof))
        runtime = self.dataset_runtime(components)
        bindings = MigrationRuntimeBindings({('application-job', 'dataset-1'): runtime}, {})
        bound = components.with_enrolled_bindings(migration_bindings=bindings)
        self.assertIs(bound.migration.runtimes, bindings)
        self.assertEqual(dict(components.migration.runtimes.dataset_workers), {})
        self.assertNotIn('ENROLLED_ISOLATED_TRANSFER_WORKERS_REQUIRED', bound.hold_codes)
        foreign = NativeOperationRegistry(self.connect,
            grants=PostgresWorkerGrants(self.connect, NativeLeaseAuthority(self.connect)), evidence=proof)
        with self.assertRaises(ApplicationRuntimeHold):
            components.with_enrolled_bindings(migration_bindings=MigrationRuntimeBindings({
                ('application-job', 'dataset-1'): replace(runtime, registry=foreign)}, {}))

    def test_graph_is_bounded_original_digest_content_and_never_claims_authority(self):
        graph = read_only_graph(self.settings, self.selected, job_id='application-job')
        self.assertEqual(graph['status'], 'READ_ONLY')
        self.assertEqual([row['stepId'] for row in graph['provisioning']], ['inputs', 'plan', 'apply', 'guest'])
        self.assertEqual(graph['datasetChildren'][0]['datasetId'], 'dataset-1')
        self.assertEqual(graph['sourceMembers'][0]['machineId'], 'machine-1')
        self.assertFalse(graph['nativeExecutionAuthorized'])
        self.assertFalse(graph['productionActivationAuthorized'])
        raw = json.dumps(graph)
        for secret in (str(self.root), 'target_root', self.dataset['datasets'][0]['source_config']['repository'],
                       'power_request', 'SECRET-DO-NOT-PROJECT'):
            self.assertNotIn(secret, raw)
        with self.assertRaises(ApplicationRuntimeHold):
            read_only_graph(self.settings, '../credential')
        path = self.settings.delivery_store / (self.artifact['deliveryPlanDigest'] + '.json')
        path.write_bytes(encoded(self.delivery | {'source_commit': 'c' * 40}))
        with self.assertRaises(ApplicationRuntimeHold) as raised:
            read_only_graph(self.settings, self.selected)
        self.assertEqual(raised.exception.hold_code, 'APPLICATION_GRAPH_INPUTS_UNAVAILABLE')

    def test_real_cli_displays_graph_and_sanitizes_missing_dependencies(self):
        command = [sys.executable, '-m', 'provisioner.controlplane.workflow.application_runtime',
                   'graph', '--selection-digest', self.selected]
        result = subprocess.run(command, cwd=Path(__file__).resolve().parents[3],
            env=os.environ | self.environment, text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['selectionDigest'], self.selected)
        missing = self.environment.copy(); missing.pop('HOSTING_APPLICATION_EXECUTION_STORE')
        clean = {key: value for key, value in os.environ.items() if not key.startswith('HOSTING_APPLICATION_')}
        result = subprocess.run(command, cwd=Path(__file__).resolve().parents[3],
            env=clean | missing, text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(json.loads(result.stdout)['dependency'], 'HOSTING_APPLICATION_EXECUTION_STORE')
        self.assertNotIn(str(self.root), result.stdout)

    def disabled_selection(self, selected=False, *, changed_payload=False, revoked=False):
        record = plan(target=self.destination)
        record['spec']['route']['method'] = 'REBUILD_RESTORE'
        if selected:
            record['spec']['execution'] = {'format': 'hosting-execution-selection/1',
                'driver': 'openstack-linux-rebuild/1', 'artifactDigest': self.selected}
        record['metadata']['planDigest'] = plan_digest(record)
        now = utcnow()
        row = (self.source['organizationId'], self.source['tenantId'], 'application-job',
            'idempotent-key', record['metadata']['planId'], 1, record['metadata']['planDigest'],
            asdict(PlanScope.from_record(record['spec']['source'])),
            asdict(PlanScope.from_record(record['spec']['destination'])), 'operator-01',
            ['approval-01'], 0, 'ADMITTED', 1, now, now)
        job = _job(row)
        admitted = replace(self.admitted, plan_digest=job.plan_digest,
            payload_digest='f' * 64 if changed_payload else c.digest(_payload_from_job(job)))
        queries = []
        class Cursor:
            connection = SimpleNamespace(autocommit=False)
            def __enter__(owner): return owner
            def __exit__(owner, *args): pass
            def execute(owner, query, parameters=()):
                queries.append(query)
                if 'SELECT rolsuper' in query: owner.row = (False, False)
                elif 'lock_job_scope' in query: owner.row = (True,)
                elif 'FROM hosting_controlplane.operation_jobs' in query: owner.row = row
                elif 'clock_timestamp' in query: owner.row = (now,)
                elif "record_kind='MigrationPlan'" in query:
                    owner.row = (1, c.digest(record), record)
                elif "record_kind = 'Workload'" in query:
                    observed = workload(); owner.row = (1, c.digest(observed), observed)
                else: owner.row = None
            def fetchone(owner): return owner.row
        class Connection:
            def __enter__(owner): return owner
            def __exit__(owner, *args): pass
            def cursor(owner): return Cursor()
        with patch('provisioner.controlplane.workflow.application_runtime.authority_postgres.revalidate_start',
                side_effect=AuthorityDenied('Synthetic revocation') if revoked else None) as current:
            result = selected_application_runtime_required(Connection, admitted)
        self.assertTrue(current.called)
        self.assertTrue(any('FOR SHARE' in query for query in queries))
        return result

    def test_disabled_dispatch_rechecks_current_plan_and_never_downgrades_selected_execution(self):
        self.assertIsNone(self.disabled_selection())
        with self.assertRaises(ApplicationRuntimeHold) as raised:
            self.disabled_selection(selected=True)
        self.assertEqual(raised.exception.hold_code, 'APPLICATION_SELECTED_DRIVER_RUNTIME_REQUIRED')
        for kwargs in ({'changed_payload': True}, {'revoked': True}):
            with self.assertRaises(ApplicationRuntimeHold) as raised:
                self.disabled_selection(**kwargs)
            self.assertEqual(raised.exception.hold_code, 'APPLICATION_SELECTION_CANNOT_BE_VERIFIED')


if __name__ == '__main__':
    unittest.main()
