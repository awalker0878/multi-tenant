"""Failure boundaries for exact observed VM stages, using synthetic native IO."""
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
import types
import unittest
from unittest.mock import Mock, patch

from tests import test_restic_transfer as capture_fixture
from provisioner.controlplane.authority import AuthorityDenied
from provisioner.controlplane.persistence import TenantContext, canonical_record_digest
from provisioner.controlplane.persistence.store import NativeBinding, OwnerLease
from provisioner.controlplane.reconciliation import NativeOperationRegistry
from provisioner.controlplane.worker.grants import VerifiedWorkerIdentity
from provisioner.controlplane.workflow.admitted_job import AdmittedInput
from provisioner.controlplane.workflow.execution_selection import PostgresExecutionAuthority
from provisioner.execution import delivery_steps, nft_edge, qualify_target, terraform_run
from provisioner.execution.run_files import digest, encoded, load_private, utcnow, write_new
from provisioner.migration.provisioning import (
    GuestCommandExclusion, LocalOpenStackTarget, ObservedProvisioningGuard,
    ObservedProvisioningRuntime, ProvisioningHeld)


class _ObservedFixture:
    def setUp(self):
        self.f = capture_fixture.TransferTests(); self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.root = self.f.root
        self.step = {'id': 'policy-01', 'kind': 'edge_policy', 'needs': []}
        self.scope = self.f.grant.destination
        self.f.grant = replace(self.f.grant, step_id=self.step['id'], operation_id='policy-01',
                               operation_kind='POLICY_APPLY')
        self.f.ledger.grants[self.f.grant.grant_id] = self.f.grant
        self.selection = {'workloadId': 'workload-01', 'sourceCommit': 'a' * 40, 'executionScope':
                          self.f.envelope['destination_execution_scope']}
        self.authority = Mock(spec=PostgresExecutionAuthority)
        self.authority.require_current.return_value = (self.f.plan, self.selection)
        self.authority.require_packet.return_value = self.f.plan
        self.registry = Mock(spec=NativeOperationRegistry); self.registry.claim_once.return_value = True
        self.binding = NativeBinding(self.scope.platform_family, self.scope.endpoint_id,
            self.scope.native_scope_id, 'vm', '11111111-1111-1111-1111-111111111111')
        self.lease = OwnerLease(self.binding, self.scope.organization_id, self.scope.tenant_id,
            self.scope.security_domain_id, 'workload-01', 'worker', 7, self.f.now + timedelta(minutes=5))
        self.identity = VerifiedWorkerIdentity(self.scope.organization_id, self.scope.tenant_id,
            'worker', self.scope.site_id, 'a' * 64, self.f.now + timedelta(minutes=5))
        self.runtime = ObservedProvisioningRuntime(self.authority, self.f.service, self.registry,
            TenantContext(self.scope.organization_id, self.scope.tenant_id), self.lease,
            self.identity, 'worker-token', self.f.grant.grant_id, self.f.grant.lease_key,
            self.f.grant.operation_id, self.scope, LocalOpenStackTarget(self.binding))
        meta = self.f.plan['metadata']
        self.admitted = AdmittedInput('job-01', meta['organizationId'], meta['tenantId'],
            meta['planId'], meta['revision'], meta['planDigest'], 0, 'b' * 64)
        self.base = self.root / 'delivery/scopes/generation'; self.base.mkdir(mode=0o700, parents=True)
        self.directory = self.base / 'policy'; self.directory.mkdir(mode=0o700)
        self.source = self.root / 'source-root'; self.source.mkdir(mode=0o700)
        self.binary = self.root / 'nft'; write_new(self.binary, b'controlled synthetic executable')
        self.binary.chmod(0o700)
        self.spec = dict(format='hosting-nft-edge/1', scope=self.selection['executionScope'],
            machine_id='a' * 32, network_namespace_inode=123, nft_sha256=digest(self.binary.read_bytes()),
            operation_id=self.runtime.operation_id, generation=1,
            interfaces={'domain0': ['192.0.2.0/24'], 'service0': ['198.51.100.0/24']},
            owned_interfaces=['domain0'], flows=[dict(ingress='domain0', egress='service0',
                source='192.0.2.10', destination='198.51.100.20', protocol='tcp', port=443, phase='active')],
            max_lease_seconds=60)
        table, scope_digest = nft_edge.validate(self.spec)
        self.native_state = {'nftables': [{'table': {'family': 'inet', 'name': table,
                                                   'comment': 'hosting:' + scope_digest + ':deny'}}]}
        self.policy_authority = dict(spec_sha256=digest(encoded(self.spec)), mode='active',
            expected_state_sha256=digest(encoded(nft_edge.normalized(self.native_state))),
            valid_from=(self.f.now - timedelta(seconds=1)).isoformat(),
            valid_until=(self.f.now + timedelta(seconds=90)).isoformat(),
            change_ref='CHANGE-1', boundary_acceptance_ref='BOUNDARY-1', readiness_ref='READINESS-1')
        self.packet = {'parameters': dict(nft=str(self.binary), nft_sha256=self.spec['nft_sha256'], mode='active'),
                       'files': {}, 'dependencies': {}}
        for name, value in [('spec', self.spec), ('authority', self.policy_authority)]:
            path = self.root / (name + '.json'); write_new(path, encoded(value))
            self.packet['files'][name] = dict(path=str(path), sha256=digest(encoded(value)))
        self.plan = {'scope': self.spec['scope'], 'source_commit': 'a' * 40}
        self.calls = []
        self.revoke_on_write = False
        self.fail_on_write = False
        def native(argv, **keywords):
            self.calls.append((argv, keywords['timeout']))
            if '--file' in argv and '--check' not in argv:
                self.native_state['nftables'][0]['table']['comment'] += ':applied'
                if self.revoke_on_write: self.f.ledger.epoch += 1
                if self.fail_on_write: raise TimeoutError('synthetic post-write acknowledgement loss')
            document = {'nftables': [self.native_state['nftables'][0]]} if 'table' in argv else \
                       {'nftables': [{'table': {'family': 'inet', 'name': table}}]}
            keywords['stdout'].write(encoded(document))
            return types.SimpleNamespace(returncode=0)
        self.io_patch = patch('provisioner.migration.provisioning.subprocess.run', side_effect=native)
        self.addCleanup(self.io_patch.stop); self.io_patch.start()
        for target, attribute, value in (
                ('provisioner.execution.source_integrity', 'verify', {'status': 'HASHES_MATCH', 'commit': 'a' * 40}),
                ('provisioner.execution.source_integrity', 'verify_runtime', {'status': 'RUNTIME_SOURCES_MATCH'})):
            p = patch(target + '.' + attribute, return_value=value); p.start(); self.addCleanup(p.stop)
        p = patch.object(LocalOpenStackTarget, 'require_current', return_value={'observed': 'synthetic'})
        p.start(); self.addCleanup(p.stop)

    def execute(self):
        return self.runtime.run_step(self.admitted, self.selection, self.plan, self.step,
                                     self.packet, self.directory, self.base, self.source)


class ObservedProvisioningTests(_ObservedFixture, unittest.TestCase):
    def test_actual_nft_owner_uses_exact_policy_grant_for_each_native_command(self):
        result, names = self.execute()
        self.assertEqual(result['status'], 'APPLIED_EXPIRING_POLICY_NOT_QUALIFIED')
        self.assertFalse(result['production_qualified'])
        self.assertIn('owner-completion.json', names)
        self.registry.prepare.assert_called_once()
        self.assertEqual(self.registry.prepare.call_args.kwargs['operation_kind'], 'POLICY_APPLY')
        writes = [argv for argv, _timeout in self.calls if '--file' in argv and '--check' not in argv]
        self.assertEqual(len(writes), 1)
        continuation = [c for c in self.authority.require_current.call_args_list
                        if 'continuation_grant' in c.kwargs]
        self.assertGreaterEqual(len(continuation), len(self.calls) * 2)
        self.assertTrue(all(c.kwargs['continuation_grant'] == self.f.grant for c in continuation))
        self.assertTrue(all(0 < timeout <= 10 for _argv, timeout in self.calls))

    def test_revocation_after_actual_policy_write_is_uncertain_without_completion(self):
        self.revoke_on_write = True
        with self.assertRaises(AuthorityDenied): self.execute()
        self.registry.mark_uncertain.assert_called_once_with(self.runtime.context, 'policy-01', 'worker')
        self.assertFalse((self.directory / 'owner-completion.json').exists())
        self.assertEqual(load_private(next((self.root / 'owners/edge_policy').glob('*/head.json')))['status'],
                         'OUTCOME_UNKNOWN')

    def test_lost_write_response_never_replays_native_effect(self):
        self.fail_on_write = True
        with self.assertRaises(TimeoutError): self.execute()
        self.assertEqual(len([argv for argv, _t in self.calls if '--file' in argv and '--check' not in argv]), 1)
        other = self.base / 'repeat'; other.mkdir(mode=0o700)
        self.registry.claim_once.return_value = False
        with self.assertRaisesRegex(ValueError, 'already claimed'):
            self.runtime.run_step(self.admitted, self.selection, self.plan, self.step,
                                  self.packet, other, self.base, self.source)
        self.assertEqual(len([argv for argv, _t in self.calls if '--file' in argv and '--check' not in argv]), 1)

    def test_vm_power_grant_cannot_be_reused_as_policy_authority(self):
        self.f.ledger.grants[self.f.grant.grant_id] = replace(self.f.grant, operation_kind='VM_POWER')
        with self.assertRaises(AuthorityDenied): self.execute()
        self.registry.prepare.assert_not_called(); self.assertEqual(self.calls, [])

    def test_local_target_drift_holds_before_claim(self):
        with patch.object(LocalOpenStackTarget, 'require_current', side_effect=ValueError('native guest drift')):
            with self.assertRaisesRegex(ValueError, 'guest drift'): self.execute()
        self.registry.prepare.assert_not_called(); self.assertEqual(self.calls, [])

    def test_wider_native_allow_window_cannot_outlive_worker_grant(self):
        wider = dict(self.policy_authority, valid_until=(self.f.now + timedelta(minutes=10)).isoformat())
        path = self.root / 'wide-authority.json'; write_new(path, encoded(wider))
        self.packet['files']['authority'] = dict(path=str(path), sha256=digest(encoded(wider)))
        with self.assertRaisesRegex(ValueError, 'worker grant window'): self.execute()
        self.registry.prepare.assert_not_called(); self.assertEqual(self.calls, [])

    def test_guest_multi_vm_inventory_is_rejected_before_dispatch(self):
        self._guest({'first': {'native_id': self.binding.native_id}, 'second': {'native_id': 'other'}},
                    expected='multi-VM')

    def test_single_vm_guest_holds_without_real_per_command_ssh_owner(self):
        self._guest({'first': {'native_id': self.binding.native_id}}, expected='GUEST_PER_COMMAND_AUTHORITY_UNAVAILABLE',
                    exclusion=GuestCommandExclusion())

    def _guest(self, targets, *, expected, exclusion=None):
        step = dict(self.step, kind='guest_apply')
        self.f.grant = replace(self.f.grant, operation_kind='GUEST_CONFIG')
        self.f.ledger.grants[self.f.grant.grant_id] = self.f.grant
        runtime = replace(self.runtime, guest_commands=exclusion)
        self.packet['files']['approval'] = self.packet['files']['authority']
        with patch.object(delivery_steps, 'validate_packet'), \
             patch.object(delivery_steps, 'prepared_directory', return_value=self.root), \
             patch('provisioner.migration.provisioning.guest_apply.validate_bundle',
                   return_value=({'operation_id': runtime.operation_id}, {'targets': targets}, {})), \
             patch('provisioner.migration.provisioning.guest_apply.apply') as native:
            with self.assertRaisesRegex((ValueError, ProvisioningHeld), expected):
                runtime.run_step(self.admitted, self.selection, self.plan, step,
                                 self.packet, self.directory, self.base, self.source)
        native.assert_not_called(); self.registry.prepare.assert_not_called(); self.assertEqual(self.calls, [])

    def test_request_objects_and_callback_booleans_cannot_be_native_bindings(self):
        with self.assertRaises(ValueError): replace(self.runtime, guest_commands=True)
        with self.assertRaises(ValueError): replace(self.runtime, local_target=lambda _spec: True)
        with self.assertRaises(ValueError): replace(self.runtime, scope=self.f.grant.source)

    def test_static_cloud_contact_cannot_authorize_a_planning_read(self):
        self.f.grant = replace(self.f.grant, operation_kind='DISCOVER_READ')
        self.f.ledger.grants[self.f.grant.grant_id] = self.f.grant
        with patch.object(delivery_steps, 'validate_packet'), \
             patch.object(terraform_run, 'prepare') as native:
            with self.assertRaisesRegex(ProvisioningHeld, 'SCOPED_PLANNING_CREDENTIAL_OWNER_UNAVAILABLE'):
                self.runtime.run_step(self.admitted, self.selection, self.plan,
                    dict(self.step, kind='terraform_plan'), self.packet, self.directory, self.base, self.source)
        native.assert_not_called(); self.registry.prepare.assert_not_called(); self.assertEqual(self.calls, [])

    def test_observation_manifest_cannot_cross_the_real_granted_project(self):
        self.f.grant = replace(self.f.grant, operation_kind='DISCOVER_READ')
        self.f.ledger.grants[self.f.grant.grant_id] = self.f.grant
        manifest = {'project_id': 'foreign-native-project'}
        path = self.root / 'foreign-manifest.json'; write_new(path, encoded(manifest))
        campaign = {'format': 'hosting-target-campaign/2', 'scope': self.selection['executionScope'],
            'assets': {name: {'path': str(path), 'sha256': digest(encoded(manifest))}
                       for name in ('native_manifest', 'workload_manifest')}}
        path = self.root / 'campaign.json'; write_new(path, encoded(campaign))
        packet = {'parameters': dict(ssh=str(self.binary), ssh_sha256=digest(self.binary.read_bytes())),
                  'files': {'plan': {'path': str(path), 'sha256': digest(encoded(campaign))}}}
        with patch.object(delivery_steps, 'validate_packet'), \
             patch.object(qualify_target, 'execute') as native:
            with self.assertRaisesRegex(ValueError, 'another granted project'):
                self.runtime.run_step(self.admitted, self.selection, self.plan,
                    dict(self.step, kind='target_campaign'), packet, self.directory, self.base, self.source)
        native.assert_not_called(); self.registry.prepare.assert_not_called(); self.assertEqual(self.calls, [])


class ReadCommandGuardTests(_ObservedFixture, unittest.TestCase):
    def guard(self):
        self.f.grant = replace(self.f.grant, operation_kind='DISCOVER_READ')
        self.f.ledger.grants[self.f.grant.grant_id] = self.f.grant
        return ObservedProvisioningGuard(self.runtime, self.admitted, self.selection,
                                         dict(self.step, kind='target_campaign'), 'DISCOVER_READ')

    def test_actual_terraform_command_hook_rechecks_revocation_after_subprocess(self):
        guard = self.guard()
        def command(*_args, **kwargs):
            self.assertLessEqual(kwargs['timeout'], 120)
            self.f.ledger.epoch += 1
            return 0
        with patch.object(terraform_run, 'command', side_effect=command):
            with self.assertRaises(AuthorityDenied):
                terraform_run.authorized_command(self.policy_authority, self.binary, self.root,
                    ['version', '-json'], {}, self.root / 'version.json', command_guard=guard)

    def test_campaign_cannot_use_write_grant_for_observation(self):
        guard = ObservedProvisioningGuard(self.runtime, self.admitted, self.selection,
            dict(self.step, kind='target_campaign'), 'DISCOVER_READ')
        with self.assertRaises(AuthorityDenied):
            qualify_target.budget(self.policy_authority, 20, command_guard=guard)
        self.assertEqual(self.calls, [])

    def test_read_only_hook_rejects_arbitrary_callback_or_boolean(self):
        with self.assertRaises(ValueError): qualify_target.budget(self.policy_authority, 20, command_guard=True)
        with self.assertRaises(ValueError):
            terraform_run.authorized_command(self.policy_authority, command_guard=lambda: True)
