"""Failure boundaries around the concrete selected application restore owner."""
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
import os
from pathlib import Path
import types
import unittest
from unittest.mock import Mock, patch

from tests import test_restic_transfer as capture_fixture

from provisioner.controlplane.authority import AuthorityDenied
from provisioner.controlplane.persistence import TenantContext, canonical_record_digest
from provisioner.controlplane.persistence.store import NativeBinding, OwnerLease
from provisioner.controlplane.reconciliation import NativeOperation, NativeOperationRegistry
from provisioner.controlplane.worker.grants import VerifiedWorkerIdentity
from provisioner.domain.enterprise_records import plan_digest
from provisioner.execution import restic_run
from provisioner.execution.run_files import digest, encoded, utcnow
from provisioner.migration.application import (
    ApplicationDataRunner, ApplicationDataSelection, DatasetWorkerRuntime)
from provisioner.migration.cutover import recovery_projection
from provisioner.migration.resources import LinuxTransferResources, TransferLimits
from provisioner.migration.authority import ApplicationCommandAuthority
from provisioner.controlplane.workflow.admitted_job import AdmittedInput
from provisioner.controlplane.workflow.execution_selection import PostgresExecutionAuthority


class ApplicationMigrationTests(unittest.TestCase):
    def setUp(self):
        self.f = capture_fixture.TransferTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.f.plan['spec']['selectedMachineIds'] = ['machine-1']
        self.f.plan['spec']['machineMappings'] = self.f.plan['spec']['machineMappings'][:1]
        self.f.plan['spec']['selectedDatasetIds'] = ['dataset-1']
        self.f.plan['spec']['datasetMappings'] = self.f.plan['spec']['datasetMappings'][:1]
        self.resources = LinuxTransferResources(
            self.f.root, '/hosting/dataset-worker', '8:1',
            TransferLimits(256, 32, 1024 * 1024, len(b'original useful workload bytes')))
        info = (self.f.source / 'payload').stat()
        self.descriptor = dict(step_id='dataset-restore', operation_id='restore-01',
            dataset_id='dataset-1', target_ref='target-dataset-1', consistency_group_id='group-01',
            target_member='target-guest', target_root=str(self.f.target),
            source_config=deepcopy(self.f.config), source_receipt=deepcopy(self.f.receipt),
            file_manifest=deepcopy(self.f.manifest), resources=self.resources.binding(),
            target_metadata={'payload': dict(mode=info.st_mode & 0o7777, uid=info.st_uid, gid=info.st_gid)})
        self.selection_body = dict(format='hosting-application-dataset-selection/1',
            source_scope=self.f.plan['spec']['source'], destination_scope=self.f.plan['spec']['destination'],
            guest_profile='linux-ubuntu-2404', datasets=[self.descriptor])
        self.selection = ApplicationDataSelection.from_record(self.selection_body)
        self.artifact = dict(datasetSelectionDigest=self.selection.sha256,
                             cutoverSelectionDigest='e' * 64, resourceBundleDigest='f' * 64,
                             deliveryPlanDigest='d' * 64)
        self.f.plan['spec']['execution'] = dict(format='hosting-execution-selection/1',
            driver='openstack-linux-rebuild/1', artifactDigest=canonical_record_digest(self.artifact))
        self.f.plan['metadata']['planDigest'] = plan_digest(self.f.plan)
        self.f.transfer['metadata']['planDigest'] = self.f.plan['metadata']['planDigest']
        self.f.envelope['migration_plan'] = self.f.plan
        self.f.configure_authority()
        self.f.restore_authority['machine_id'] = Path('/etc/machine-id').read_text().strip()
        self.registry = Mock(spec=NativeOperationRegistry)
        self.registry.claim_once.return_value = True
        self.lease = OwnerLease(
            NativeBinding('openstack', self.f.grant.destination.endpoint_id,
                          self.f.grant.destination.native_scope_id, 'dataset', 'target-dataset-1'),
            self.f.grant.organization_id, self.f.grant.tenant_id,
            self.f.grant.destination.security_domain_id, 'workload-01', 'worker', 7,
            self.f.now + timedelta(minutes=5))
        self.runtime = DatasetWorkerRuntime(
            self.f.service, self.registry,
            TenantContext(self.f.grant.organization_id, self.f.grant.tenant_id), self.lease,
            VerifiedWorkerIdentity(self.f.grant.organization_id, self.f.grant.tenant_id,
                                  'worker', self.f.grant.destination.site_id, 'c' * 64,
                                  self.f.now + timedelta(hours=1)),
            'worker-token', 'grant-01', 'binding:dataset-1', Path('/private/restic'),
            dict(password='secret', username='scoped', http_password='secret'), self.resources)
        self.ledger = self.f.root / 'ledger'; self.ledger.mkdir(mode=0o700)
        self.runner = ApplicationDataRunner(job_id='job-01', plan=self.f.plan,
            execution_artifact=self.artifact, selection=self.selection, ledger=self.ledger)
        meta = self.f.plan['metadata']
        self.root_authority = Mock(spec=PostgresExecutionAuthority)
        self.root_authority.require_current.return_value = (self.f.plan, self.artifact)
        admitted = AdmittedInput('job-01', meta['organizationId'], meta['tenantId'],
            meta['planId'], meta['revision'], meta['planDigest'], 0, 'a' * 64)
        self.command_authority = ApplicationCommandAuthority(self.root_authority, admitted,
            canonical_record_digest(self.artifact), self.runtime.identity, 'RESTORE_DATA')
        resource_patch = patch.object(LinuxTransferResources, 'require_current', autospec=True,
                                      side_effect=lambda obj: obj.binding())
        self.addCleanup(resource_patch.stop); resource_patch.start()
        client_patch = patch.object(restic_run, 'Restic', return_value=self.f.engine)
        self.addCleanup(client_patch.stop); client_patch.start()

    def execute(self):
        return self.runner.execute_dataset('dataset-1', runtime=self.runtime,
            envelope=self.f.envelope, restore_authority=self.f.restore_authority,
            command_authority=self.command_authority)

    def test_independent_root_command_authority_cannot_be_omitted(self):
        with self.assertRaisesRegex(ValueError, 'command authority'):
            self.runner.execute_dataset('dataset-1', runtime=self.runtime,
                envelope=self.f.envelope, restore_authority=self.f.restore_authority)
        self.registry.prepare.assert_not_called(); self.assertEqual(self.f.calls, [])

    def test_foreign_dataset_owner_cannot_use_the_selected_target_grant(self):
        self.runtime = replace(self.runtime, lease=replace(self.lease,
            binding=replace(self.lease.binding, native_id='another-target-dataset')))
        with self.assertRaisesRegex(ValueError, 'exact selected target'): self.execute()
        self.registry.prepare.assert_not_called(); self.assertEqual(self.f.calls, [])

    def test_real_cross_scope_executor_is_composed_after_native_claim(self):
        source_bytes = encoded(self.f.receipt)
        result = self.execute()
        self.assertEqual(self.f.calls, ['repository', 'snapshots', 'restore'])
        self.registry.prepare.assert_called_once()
        self.assertEqual(self.registry.prepare.call_args.kwargs['operation_kind'], 'RESTORE_DATA')
        self.registry.claim_once.assert_called_once()
        self.assertEqual(result['status'], 'DATASET_BYTES_AND_SELECTED_METADATA_VERIFIED')
        self.assertTrue(result['native_intent_requires_independent_resolution'])
        self.assertEqual(result['measured_bytes'], self.resources.limits.expected_bytes)
        self.assertEqual(self.runner.join()['dataset_ids'], ['dataset-1'])
        self.assertEqual(encoded(self.f.receipt), source_bytes)
        self.assertFalse(result['application_acceptance'])
        self.assertFalse(result['production_activation'])

    def test_failed_native_claim_retains_attempt_and_never_calls_repository(self):
        self.registry.claim_once.return_value = False
        with self.assertRaisesRegex(ValueError, 'already claimed'):
            self.execute()
        self.assertEqual(self.f.calls, [])
        self.assertEqual(self.runner.inspect()['datasets'][0]['status'], 'OUTCOME_UNKNOWN_RECONCILE_ORIGINAL')
        self.registry.claim_once.return_value = True
        with self.assertRaisesRegex(ValueError, 'was attempted'):
            self.execute()
        self.assertEqual(self.f.calls, [])

    def test_timeout_after_repository_effect_never_retries(self):
        def lose_response(_argv):
            raise TimeoutError('synthetic acknowledgement loss')
        self.f.engine.command = lose_response
        with self.assertRaises(TimeoutError):
            self.execute()
        self.registry.mark_uncertain.assert_called_once()
        with self.assertRaisesRegex(ValueError, 'was attempted'):
            self.execute()
        with self.assertRaises((OSError, ValueError)):
            self.runner.reconcile_dataset('dataset-1', runtime=self.runtime, envelope=self.f.envelope)
        self.assertFalse(self.f.target.exists())

    def test_checkpoint_loss_reconciles_original_bytes_without_restore(self):
        from provisioner.execution import execution_journal
        original = execution_journal.Journal.append
        def lose_completed(log, kind, data):
            if kind == 'DATASET_COMPLETED':
                raise OSError('synthetic completion acknowledgement loss')
            return original(log, kind, data)
        with patch.object(execution_journal.Journal, 'append', lose_completed):
            with self.assertRaises(OSError):
                self.execute()
        self.registry.mark_uncertain.assert_called_once()
        calls = list(self.f.calls)
        result = self.runner.reconcile_dataset('dataset-1', runtime=self.runtime, envelope=self.f.envelope)
        self.assertEqual(self.f.calls, calls)
        self.assertIsNone(result['elapsed_seconds'])
        self.assertEqual(self.runner.join()['status'], 'DATASET_PLAN_FILE_BYTES_VERIFIED_NOT_APPLICATION_ACCEPTED')

    def test_changed_metadata_and_current_data_hold_reconciliation_and_join(self):
        self.execute()
        payload = self.f.target / str(self.f.source).lstrip('/') / 'payload'
        payload.chmod(0o600)
        with self.assertRaisesRegex(ValueError, 'ownership or modes'):
            self.runner.join()
        payload.chmod(self.descriptor['target_metadata']['payload']['mode'])
        payload.write_bytes(b'new target writes')
        with self.assertRaisesRegex(ValueError, 'Current useful'):
            self.runner.reconcile_dataset('dataset-1', runtime=self.runtime, envelope=self.f.envelope)

    def test_stale_grant_and_wrong_mapping_hold_before_native_claim(self):
        self.f.ledger.epoch += 1
        with self.assertRaises(AuthorityDenied):
            self.execute()
        self.assertEqual(self.f.calls, [])
        self.registry.prepare.assert_not_called()

    def test_changed_full_execution_artifact_cannot_reuse_approvals(self):
        with self.assertRaisesRegex(ValueError, 'full independent execution artifact'):
            ApplicationDataRunner(job_id='job-01', plan=self.f.plan,
                execution_artifact=self.artifact | {'datasetSelectionDigest': 'b' * 64},
                selection=self.selection, ledger=self.ledger)

    def test_dataset_omission_wrong_guest_and_overlapping_roots_are_refused(self):
        for mutate in (
                lambda body: body.__setitem__('guest_profile', 'windows-2022'),
                lambda body: body['datasets'].append(deepcopy(body['datasets'][0])),
                lambda body: body['datasets'][0]['target_metadata'].clear(),
                lambda body: body['datasets'][0]['resources']['limits'].__setitem__('expected_bytes', 1)):
            body = deepcopy(self.selection_body); mutate(body)
            with self.assertRaises(ValueError):
                ApplicationDataSelection.from_record(body)
        body = deepcopy(self.selection_body)
        body['datasets'][0]['dataset_id'] = 'dataset-2'
        selected = ApplicationDataSelection.from_record(body)
        artifact = self.artifact | {'datasetSelectionDigest': selected.sha256}
        plan = deepcopy(self.f.plan)
        plan['spec']['execution']['artifactDigest'] = canonical_record_digest(artifact)
        plan['metadata']['planDigest'] = plan_digest(plan)
        with self.assertRaisesRegex(ValueError, 'every selected canonical'):
            ApplicationDataRunner(job_id='job-01', plan=plan, execution_artifact=artifact,
                                  selection=selected, ledger=self.ledger)


class TransferResourcesTests(unittest.TestCase):
    def setUp(self):
        self.f = capture_fixture.TransferTests(); self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        device = self.f.root.stat().st_dev
        self.device = f'{os.major(device)}:{os.minor(device)}'
        self.resources = LinuxTransferResources(self.f.root, '/hosting/worker-01', self.device,
                                                TransferLimits(128, 20, 4096, 64))

    def kernel(self, *, io=None, membership=None, volume_blocks=4):
        paths = {'/proc/self/cgroup': membership or '0::/hosting/worker-01\n',
                 '/sys/fs/cgroup/hosting/worker-01/cgroup.type': 'domain\n',
                 '/sys/fs/cgroup/hosting/cgroup.subtree_control': 'io memory\n',
                 '/sys/fs/cgroup/hosting/worker-01/io.max': io or
                    f'{self.device} rbps=131072 wbps=131072 riops=20 wiops=20\n'}
        original_read = Path.read_text
        original_exists = Path.exists
        self.enterContext(patch.object(Path, 'read_text', lambda path, *a, **k:
            paths[str(path)] if str(path) in paths else original_read(path, *a, **k)))
        self.enterContext(patch.object(Path, 'exists', lambda path:
            True if str(path) == '/sys/dev/block/' + self.device else original_exists(path)))
        self.enterContext(patch('os.path.ismount', return_value=True))
        self.enterContext(patch('os.statvfs', return_value=types.SimpleNamespace(
            f_blocks=volume_blocks, f_frsize=1024, f_bavail=volume_blocks,
            f_flag=os.ST_NOSUID | os.ST_NODEV | os.ST_NOEXEC)))

    def test_actual_kernel_controls_and_bounded_mount_are_read(self):
        self.kernel()
        self.assertEqual(self.resources.require_current(), self.resources.binding())
        self.resources.require_capacity(1024)

    def test_unlimited_iops_escape_shared_larger_disk_and_missing_space_are_refused(self):
        for kernel in (dict(io=f'{self.device} rbps=131072 wbps=131072 riops=max wiops=20\n'),
                       dict(membership='0::/other-worker\n'), dict(volume_blocks=5)):
            with self.subTest(kernel=kernel):
                with patch.object(Path, 'read_text') as read, patch.object(Path, 'exists', return_value=True), \
                     patch('os.path.ismount', return_value=True), \
                     patch('os.statvfs', return_value=types.SimpleNamespace(
                         f_blocks=kernel.get('volume_blocks', 4), f_frsize=1024, f_bavail=4,
                         f_flag=os.ST_NOSUID | os.ST_NODEV | os.ST_NOEXEC)):
                    def content(path, *args, **kwargs):
                        raise AssertionError(path)
                    read.side_effect = [kernel.get('membership', '0::/hosting/worker-01\n'),
                                        'domain\n', 'io memory\n', kernel.get('io',
                                        f'{self.device} rbps=131072 wbps=131072 riops=20 wiops=20\n')]
                    with self.assertRaises(ValueError): self.resources.require_current()
        with patch.object(LinuxTransferResources, 'require_current'), \
             patch('os.statvfs', return_value=types.SimpleNamespace(f_frsize=1, f_bavail=1)):
            with self.assertRaisesRegex(ValueError, 'insufficient'):
                self.resources.require_capacity(100)

    def test_restore_command_sets_real_native_bandwidth_flag(self):
        binary = self.f.root / 'restic'; binary.write_bytes(b'fixture executable')
        config = self.f.config | {'restic_sha256': restic_run.sha_file(binary)}
        operation = self.f.root / 'rate-operation'; operation.mkdir(mode=0o700)
        calls = []
        def command(argv, **kwargs):
            calls.append(argv); kwargs['stdout'].write(b'{}'); return types.SimpleNamespace(returncode=0)
        with patch.object(LinuxTransferResources, 'require_current'), \
             patch.object(restic_run.subprocess, 'run', side_effect=command):
            client = restic_run.Restic(binary, config, dict(password='x', username='x', http_password='x'),
                                      operation, resource_control=self.resources)
            client.command(['cat', 'config'])
        self.assertIn('--limit-download', calls[0])
        self.assertEqual(calls[0][calls[0].index('--limit-download') + 1], '128')


class RecoveryBoundaryTests(unittest.TestCase):
    def setUp(self):
        from provisioning.schema.test_enterprise_records import plan
        self.plan = plan()
        self.intent = NativeOperation('activate-01', 'job-01', 'grant-01', 'activate', 'lease-01',
            NativeBinding('vmware', 'vcenter-02', 'dc2', 'vm', 'vm-2'),
            'workload-01', 'wsd-02', 'worker-01', 1, 'DESTINATION_ACTIVATE',
            'a' * 64, 'PREPARED', None, None)

    def test_unknown_and_claimed_activation_never_allow_source_restart(self):
        for value in (None, replace(self.intent, state='IN_FLIGHT'),
                      replace(self.intent, state='TASK_ACCEPTED', native_task_id='task-01'),
                      replace(self.intent, state='UNCERTAIN'),
                      replace(self.intent, state='RESOLVED', outcome='EFFECT_PRESENT')):
            with self.subTest(value=value):
                result = recovery_projection(self.plan, target_activation=value,
                                              job_id='job-01', original_activation_operation_id='activate-01')
                self.assertFalse(result['source_restart_authorized'])
                self.assertIn('SELECT_REVERSE_SYNC_RESTORE_OR_FORWARD_REPAIR', result['actions'])
                self.assertNotIn('REVIEW_PRE_WRITE_SOURCE_RETURN_WITH_CURRENT_TARGET_EXCLUSION', result['actions'])

    def test_prepared_and_no_effect_still_require_current_exclusion(self):
        for value in (self.intent, replace(self.intent, state='RESOLVED', outcome='NO_EFFECT')):
            result = recovery_projection(self.plan, target_activation=value,
                                          job_id='job-01', original_activation_operation_id='activate-01')
            self.assertEqual(result['target_write_boundary'], 'BEFORE_TARGET_WRITES_REQUIRES_CURRENT_EXCLUSION')
            self.assertFalse(result['source_restart_authorized'])
            self.assertFalse(result['capacity_release_authorized'])

    def test_foreign_activation_intent_is_refused(self):
        with self.assertRaises(ValueError):
            recovery_projection(self.plan, target_activation=replace(self.intent, operation_id='other-01'),
                                job_id='job-01', original_activation_operation_id='activate-01')


class SourceFenceCompositionTests(unittest.TestCase):
    def setUp(self):
        import test_vsphere_power as source_fixture
        from provisioner.controlplane.authority import RoleGrant, VerifiedPrincipal
        from provisioner.controlplane.authority.service import LeaseState, WORKER
        from provisioner.migration.cutover import SourceFenceRunner, SourceFenceSelection, SourceWorkerRuntime
        self.f = capture_fixture.TransferTests(); self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.request = source_fixture.request()
        self.power_authority = source_fixture.authority(self.request)
        self.client = source_fixture.FakeClient(self.request)
        self.selection = SourceFenceSelection.from_record(dict(
            format='hosting-application-cutover-selection/1', source_scope=self.f.plan['spec']['source'],
            destination_scope=self.f.plan['spec']['destination'], source_members=[dict(
                machine_id='machine-1', native_id='vm-1', step_id='source-fence', operation_id='fence-01',
                power_request=self.request)]))
        self.f.plan['spec']['selectedMachineIds'] = ['machine-1']
        self.f.plan['spec']['machineMappings'] = self.f.plan['spec']['machineMappings'][:1]
        self.artifact = dict(cutoverSelectionDigest=self.selection.sha256, datasetSelectionDigest='f' * 64)
        self.f.plan['spec']['execution'] = dict(format='hosting-execution-selection/1',
            driver='openstack-linux-rebuild/1', artifactDigest=canonical_record_digest(self.artifact))
        self.f.plan['metadata']['planDigest'] = plan_digest(self.f.plan)
        self.f.configure_authority()
        source = self.f.grant.source
        self.f.provider.identities['source-token'] = VerifiedPrincipal(
            'source-worker', source.organization_id, source.tenant_id, 'WORKER',
            self.f.now - timedelta(seconds=1), self.f.now + timedelta(hours=1), None,
            (RoleGrant(WORKER, source, self.f.now + timedelta(hours=1)),))
        self.grant = replace(self.f.grant, grant_id='source-grant', worker_subject='source-worker',
                             step_id='source-fence', operation_id='fence-01', operation_kind='SOURCE_FENCE',
                             operation_scope=source, lease_key='binding:vm-1')
        self.f.ledger.grants['source-grant'] = self.grant
        self.f.leases.lease = LeaseState('binding:vm-1', 7, 'source-worker', self.f.now + timedelta(minutes=5))
        self.registry = Mock(spec=NativeOperationRegistry); self.registry.claim_once.return_value = True
        lease = OwnerLease(NativeBinding('vmware', source.endpoint_id, source.native_scope_id, 'vm', 'vm-1'),
                           source.organization_id, source.tenant_id, source.security_domain_id,
                           'workload-01', 'source-worker', 7, self.f.now + timedelta(minutes=5))
        self.runtime = SourceWorkerRuntime(self.f.service, self.registry,
            TenantContext(source.organization_id, source.tenant_id), lease,
            VerifiedWorkerIdentity(source.organization_id, source.tenant_id, 'source-worker',
                                  source.site_id, 'c' * 64, self.f.now + timedelta(hours=1)),
            'source-token', 'source-grant', 'binding:vm-1', 'fixture-session')
        ledger = self.f.root / 'source-ledger'; ledger.mkdir(mode=0o700)
        self.runner = SourceFenceRunner(job_id='job-01', plan=self.f.plan,
            execution_artifact=self.artifact, selection=self.selection, ledger=ledger,
            source_root=self.f.root)
        meta = self.f.plan['metadata']
        self.root_authority = Mock(spec=PostgresExecutionAuthority)
        self.root_authority.require_current.return_value = (self.f.plan, self.artifact)
        admitted = AdmittedInput('job-01', meta['organizationId'], meta['tenantId'],
            meta['planId'], meta['revision'], meta['planDigest'], 0, 'a' * 64)
        self.command_authority = ApplicationCommandAuthority(self.root_authority, admitted,
            canonical_record_digest(self.artifact), self.runtime.identity, 'SOURCE_FENCE')
        from provisioner.migration import cutover
        self.guarded_client_type = cutover._GuardedPowerClient
        self.enterContext(patch.object(cutover, '_GuardedPowerClient', return_value=self.client))
        self.enterContext(patch.object(cutover.vsphere_power, 'verify',
                                     return_value=dict(status='HASHES_MATCH', commit='a' * 40)))
        self.enterContext(patch.object(cutover.vsphere_power, 'verify_runtime',
                                     return_value=dict(status='RUNTIME_SOURCES_MATCH')))

    def fence(self, **kwargs):
        return self.runner.source_fence('machine-1', runtime=self.runtime,
            power_authority=self.power_authority, command_authority=self.command_authority, **kwargs)

    def test_independent_root_command_authority_is_required_before_source_claim(self):
        with self.assertRaisesRegex(ValueError, 'exact admitted'):
            self.runner.source_fence('machine-1', runtime=self.runtime, power_authority=self.power_authority)
        self.registry.prepare.assert_not_called(); self.assertEqual(self.client.writes, 0)

    def test_source_native_owner_from_another_workload_is_refused(self):
        self.runtime = replace(self.runtime, lease=replace(self.runtime.lease, workload_id='another-workload'))
        with self.assertRaisesRegex(ValueError, 'exact reviewed original VM'): self.fence()
        self.registry.prepare.assert_not_called(); self.assertEqual(self.client.writes, 0)

    def test_native_power_completion_does_not_grant_writer_exclusion(self):
        result = self.fence()
        self.assertEqual(self.client.writes, 1)
        self.assertEqual(self.registry.prepare.call_args.kwargs['operation_kind'], 'SOURCE_FENCE')
        self.assertEqual(result['status'], 'SOURCE_POWERED_OFF_RESTART_EXCLUSION_HELD')
        self.assertFalse(result['final_sync_authorized'])
        self.assertFalse(result['traffic_switch_authorized'])
        self.assertFalse(result['production_activation'])

    def test_power_timeout_is_uncertain_and_resume_never_resends(self):
        from provisioner.execution.readback_core import ObservationError
        self.client.lost = True
        with self.assertRaises(ObservationError): self.fence()
        self.registry.mark_uncertain.assert_called_once()
        with self.assertRaisesRegex(ValueError, 'response was lost'): self.fence(resume=True)
        self.assertEqual(self.client.writes, 1)

    def test_source_grant_revocation_prevents_power_and_native_claim(self):
        self.f.ledger.epoch += 1
        with self.assertRaises(AuthorityDenied): self.fence()
        self.assertEqual(self.client.writes, 0)
        self.registry.prepare.assert_not_called()

    def test_retained_shutdown_is_reread_and_restart_blocks_resume(self):
        from provisioner.execution import vsphere_observe
        self.fence()
        resource = self.request['snapshot']['resources'][0]
        self.client.routes[vsphere_observe.resource_target(resource, 'runtime')]['powerState'] = 'poweredOn'
        with self.assertRaisesRegex(ValueError, 'power state differs'):
            self.fence(resume=True)
        self.assertEqual(self.client.writes, 1)

    def test_actual_source_transport_rechecks_complete_admitted_selection_per_request(self):
        import time
        from provisioner.controlplane.workflow.admitted_job import AdmittedInput
        from provisioner.controlplane.workflow.execution_selection import PostgresExecutionAuthority
        from provisioner.migration.authority import ApplicationCommandAuthority
        from provisioner.migration.cutover import _SourcePowerGuard
        from provisioner.execution import vsphere_power
        meta = self.f.plan['metadata']
        admitted = AdmittedInput('job-01', meta['organizationId'], meta['tenantId'],
            meta['planId'], meta['revision'], meta['planDigest'], 0, 'a' * 64)
        root = Mock(spec=PostgresExecutionAuthority)
        root.require_current.return_value = (self.f.plan, self.artifact)
        guard = _SourcePowerGuard(self.runtime, self.selection.to_dict()['source_members'][0], self.f.plan)
        guard.command_authority = ApplicationCommandAuthority(root, admitted,
            canonical_record_digest(self.artifact), self.runtime.identity, 'SOURCE_FENCE')
        guard.claimed = True
        client = object.__new__(self.guarded_client_type)
        client.guard = guard; client.deadline = time.monotonic() + 120
        with patch.object(vsphere_power.Client, '_request', return_value=({'native': 'fixture'}, {})) as native:
            self.assertEqual(client._request('GET', '/selected-vm')[0], {'native': 'fixture'})
            self.assertEqual(root.require_current.call_count, 2)
            self.assertEqual(root.require_current.call_args.kwargs['continuation_grant'], self.grant)
            root.require_current.side_effect = AuthorityDenied('qualification withdrawn after observation')
            with self.assertRaises(AuthorityDenied): client._request('POST', '/selected-power-off')
            self.assertEqual(native.call_count, 1)


class MigrationActivityCompositionTests(unittest.TestCase):
    def setUp(self):
        from provisioner.controlplane.workflow.admitted_job import AdmittedInput
        from provisioner.controlplane.workflow.execution_selection import PostgresExecutionAuthority
        from provisioner.execution.run_files import write_new
        from provisioner.migration.activities import (ApplicationMigrationActivities,
            FileMigrationSelectionStore, MigrationActivityRequest, MigrationRuntimeBindings)
        self.owner = ApplicationMigrationTests(); self.owner.setUp()
        self.addCleanup(self.owner.doCleanups)
        self.root = self.owner.f.root
        paths = {}
        for name in ('datasets', 'cutovers', 'runtime-packets', 'activity-journal', 'activity-output'):
            paths[name] = self.root / name; paths[name].mkdir(mode=0o700)
        write_new(paths['datasets'] / (self.owner.selection.sha256 + '.json'), self.owner.selection.canonical)
        packet_dir = paths['runtime-packets'] / 'job-01'; packet_dir.mkdir(mode=0o700)
        write_new(packet_dir / 'dataset-dataset-1.json', encoded(dict(
            envelope=self.owner.f.envelope, restore_authority=self.owner.f.restore_authority)))
        self.store = FileMigrationSelectionStore(dataset_directory=paths['datasets'],
            cutover_directory=paths['cutovers'], runtime_directory=paths['runtime-packets'])
        self.authority = Mock(spec=PostgresExecutionAuthority)
        self.authority.require_current.return_value = (self.owner.f.plan, self.owner.artifact)
        self.authority.require_observation.return_value = (self.owner.f.plan, self.owner.artifact)
        self.activities = ApplicationMigrationActivities(authority=self.authority, selections=self.store,
            runtimes=MigrationRuntimeBindings({('job-01', 'dataset-1'): self.owner.runtime}, {}),
            journals_directory=paths['activity-journal'], outputs_directory=paths['activity-output'],
            source_root=self.root)
        plan = self.owner.f.plan['metadata']
        self.admitted = AdmittedInput('job-01', plan['organizationId'], plan['tenantId'],
            plan['planId'], plan['revision'], plan['planDigest'], 0, 'a' * 64)
        self.request = MigrationActivityRequest(self.admitted,
            canonical_record_digest(self.owner.artifact), 'dataset-1')
        self.outputs = paths['activity-output']

    def test_activity_calls_actual_owner_and_history_contains_only_redacted_reference(self):
        from dataclasses import asdict
        from provisioner.execution.run_files import load_private
        result = self.activities.transfer_dataset(self.request)
        self.assertEqual(result.status, 'STAGE_VERIFIED')
        self.assertEqual(self.owner.f.calls, ['repository', 'snapshots', 'restore'])
        continuation = [call for call in self.authority.require_current.call_args_list
                        if 'continuation_grant' in call.kwargs]
        self.assertGreaterEqual(len(continuation), 2 * len(self.owner.f.calls))
        self.assertTrue(all(call.kwargs['continuation_grant'] == self.owner.f.grant
                            for call in continuation))
        retained = load_private(self.outputs / (result.evidence_digest + '.json'))
        self.assertEqual(canonical_record_digest(retained), result.evidence_digest)
        public = encoded(asdict(result))
        self.assertNotIn(str(self.root).encode(), public)
        self.assertNotIn(b'secret', public)
        self.assertNotIn(b'repository', public)

    def test_activity_revocation_before_effect_prevents_native_owner(self):
        self.authority.require_current.side_effect = AuthorityDenied('synthetic current gate rejection')
        result = self.activities.transfer_dataset(self.request)
        self.assertEqual((result.status, result.reason_code), ('HELD', 'AUTHORITY_REVOKED'))
        self.assertEqual(self.owner.f.calls, [])
        self.owner.registry.prepare.assert_not_called()

    def test_activity_revocation_after_effect_never_reports_success(self):
        current = self.authority.require_current.return_value
        def current_until_restore(*_args, **_kwargs):
            if 'restore' in self.owner.f.calls:
                raise AuthorityDenied('synthetic current gate rejection after effect')
            return current
        self.authority.require_current.side_effect = current_until_restore
        result = self.activities.transfer_dataset(self.request)
        self.assertEqual((result.status, result.reason_code), ('HELD', 'AUTHORITY_REVOKED'))
        self.assertIn('restore', self.owner.f.calls)
        self.assertIsNone(result.evidence_digest)
        self.owner.registry.mark_uncertain.assert_called_once()

    def test_selected_operations_or_qualification_withdrawal_stops_next_repository_command(self):
        current = self.authority.require_current.return_value
        def current_until_snapshot(*_args, **_kwargs):
            if 'snapshots' in self.owner.f.calls:
                raise AuthorityDenied('synthetic selected operating acceptance withdrawn')
            return current
        self.authority.require_current.side_effect = current_until_snapshot
        result = self.activities.transfer_dataset(self.request)
        self.assertEqual((result.status, result.reason_code), ('HELD', 'AUTHORITY_REVOKED'))
        self.assertEqual(self.owner.f.calls, ['repository', 'snapshots'])
        self.owner.registry.mark_uncertain.assert_called_once()

    def test_activity_repeat_holds_and_explicit_reconciliation_never_restores_again(self):
        self.assertEqual(self.activities.transfer_dataset(self.request).status, 'STAGE_VERIFIED')
        calls = list(self.owner.f.calls)
        repeated = self.activities.transfer_dataset(self.request)
        self.assertEqual((repeated.status, repeated.reason_code), ('HELD', 'NATIVE_UNCERTAIN'))
        reconciled = self.activities.reconcile_dataset(self.request)
        self.assertEqual(reconciled.status, 'STAGE_VERIFIED')
        self.assertEqual(self.owner.f.calls, calls)

    def test_held_original_can_be_inspected_without_new_native_admission(self):
        self.assertEqual(self.activities.transfer_dataset(self.request).status, 'STAGE_VERIFIED')
        calls = list(self.owner.f.calls)
        self.authority.require_current.side_effect = AuthorityDenied('new native admission held')
        result = self.activities.inspect_datasets(self.request)
        self.assertEqual(result.status, 'STAGE_VERIFIED')
        self.assertEqual(self.authority.require_observation.call_count, 2)
        self.assertEqual(self.owner.f.calls, calls)

    def test_observation_gate_failure_cannot_grant_restore_or_read_retained_data(self):
        self.authority.require_observation.side_effect = AuthorityDenied('original custody denied')
        result = self.activities.reconcile_dataset(self.request)
        self.assertEqual((result.status, result.reason_code), ('HELD', 'AUTHORITY_REVOKED'))
        self.assertEqual(self.owner.f.calls, [])
        self.owner.registry.claim_once.assert_not_called()

    def test_content_addressed_selection_tamper_holds_before_effect(self):
        from provisioner.execution.run_files import replace_private
        path = self.store.dataset_directory / (self.owner.selection.sha256 + '.json')
        body = self.owner.selection.to_dict(); body['datasets'][0]['target_member'] = 'another-target'
        replace_private(path, encoded(body))
        result = self.activities.transfer_dataset(self.request)
        self.assertEqual(result.status, 'HELD')
        self.assertEqual(self.owner.f.calls, [])
        self.owner.registry.prepare.assert_not_called()

    def test_missing_native_rehearsal_final_sync_and_cutover_owners_never_activate(self):
        cases = [(self.activities.rehearsal, 'ISOLATED_REHEARSAL_OWNER_UNAVAILABLE'),
                 (self.activities.final_sync, 'FINAL_CONSISTENCY_OWNER_UNAVAILABLE'),
                 (self.activities.cutover, 'TRAFFIC_AND_TARGET_ACTIVATION_OWNER_UNAVAILABLE')]
        for method, code in cases:
            with self.subTest(code=code):
                result = method(self.request)
                self.assertEqual((result.status, result.reason_code, result.hold_code),
                                 ('HELD', 'OPERATOR_HOLD', code))
        self.assertEqual(self.owner.f.calls, [])
        self.owner.registry.claim_once.assert_not_called()

    def test_typed_admitted_request_round_trips_through_temporal_converter(self):
        import asyncio
        from temporalio.converter import DataConverter
        from provisioner.migration.activities import MigrationActivityRequest
        async def encode_decode():
            converter = DataConverter.default
            payloads = await converter.encode([self.request])
            result = await converter.decode(payloads, [MigrationActivityRequest])
            return result[0]
        self.assertEqual(asyncio.run(encode_decode()), self.request)
