"""Actual TLS vCenter boundaries; B10/PG enrollment is synthetic in this fixture.

These tests exercise owned native methods, not a native campaign or permission
to activate a production application. Separate PostgreSQL and mTLS campaigns
exercise the actual original grant/custody owners used before these contacts.
"""
from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from lab.native_readback_fixture import Fixture
from tests.test_application_lifecycle import lifecycle_record
from tests.test_vsphere_observe import ref
from provisioner.controlplane.authority import PlanScope
from provisioner.controlplane.reconciliation.read_enrollment import NativeReadEnrollment
from provisioner.controlplane.worker.command_runtime import WorkerCommandRuntime, ApplicationWorkerCommandAuthority
from provisioner.execution import readback_core as c, vsphere_observe as vm, vsphere_task_observe as task, vsphere_power
from provisioner.execution.run_files import utcnow
from provisioner.migration.lifecycle import LifecycleCommandGuard
from provisioner.migration.source_exclusion import _ApplicationVsphereClient, SourceDiskFenceRuntime, observe_removed, selected_disks
from provisioner.migration.vsphere_credentials import (VsphereNativeCredentialOwner, VsphereNativeCredentialProfile,
                                                       NativeVsphereSession, _PRIVILEGES)


class NativeSessionTests(unittest.TestCase):
    def setUp(self):
        self.native = Fixture(); self.addCleanup(self.native.close)
        self.scope = PlanScope('org-01', 'tenant-01', 'site-01', 'wsd-01', 'vcenter-01', 'datacenter-1', 'vmware')
        self.commands = object.__new__(WorkerCommandRuntime)
        object.__setattr__(self.commands, 'grant', SimpleNamespace(operation_scope=self.scope))
        self.enrollment = object.__new__(NativeReadEnrollment)
        object.__setattr__(self.enrollment, 'command', self.commands)
        self.owner = object.__new__(VsphereNativeCredentialOwner)
        object.__setattr__(self.owner, 'commands', self.commands)
        object.__setattr__(self.owner, 'profile', VsphereNativeCredentialProfile(self.native.origin,
            'datacenter-1', 'SessionManager', 'AuthorizationManager', 'hosting-source-reader'))
        self.expires = utcnow() + timedelta(seconds=40); self.revoked = False; self.checks = 0
        self.material = SimpleNamespace(data={'format': 'hosting-vsphere-session/1', 'origin': self.native.origin,
            'native_scope_id': 'datacenter-1', 'principal': 'hosting-source-reader', 'session_token': 'local-native-session'},
            expires_at=self.expires)
        def current(_enrollment, **_):
            self.checks += 1
            if self.revoked:
                raise PermissionError('Local-only original read revoked')
            return SimpleNamespace(grant_id='reader-grant'), self.expires + timedelta(seconds=20)
        self.addCleanup(patch.stopall)
        patch.object(NativeReadEnrollment, 'require_current', current).start()
        patch.object(NativeReadEnrollment, 'acquire', lambda *_, **__: self.material).start()
        self.native.routes = {
            vm.PREFIX + 'SessionManager/SessionManager/currentSession': {'body': {'userName': 'hosting-source-reader', 'key': 'local-native-session'}},
            vm.PREFIX + 'VirtualMachine/vm-1/parent': {'body': ref('Folder', 'group-v4')},
            vm.PREFIX + 'Folder/group-v4/parent': {'body': ref('Datacenter', 'datacenter-1')}}
        self.native.post_routes[vm.PREFIX + 'AuthorizationManager/AuthorizationManager/FetchUserPrivilegeOnEntities'] = {
            'body': [{'entity': ref('VirtualMachine', 'vm-1'), 'privileges': sorted(_PRIVILEGES['DISCOVER_READ'])}]}

    def acquire(self):
        return self.owner.acquire_session(self.enrollment, native_id='vm-1', origin=self.native.origin,
            ca_file=self.native.directory / 'ca.pem')

    def test_real_tls_session_user_lineage_exact_privileges_and_expiry_are_required(self):
        session = self.acquire()
        self.assertIsInstance(session, NativeVsphereSession)
        self.assertEqual(session.expires_at, self.expires)
        self.assertNotIn('local-native-session', repr(session))
        self.assertEqual(self.native.post_bodies[0][1], {'entities': [{'type': 'VirtualMachine', 'value': 'vm-1'}],
            'userName': 'hosting-source-reader'})
        self.assertGreaterEqual(self.checks, 10)
        self.assertTrue(all(row['has_session_auth'] and not row['has_basic_auth'] for row in self.native.requests))

    def test_payload_scope_label_cannot_substitute_actual_foreign_user_or_datacenter(self):
        for mutation in ('user', 'datacenter'):
            with self.subTest(mutation=mutation):
                path = vm.PREFIX + ('SessionManager/SessionManager/currentSession' if mutation == 'user' else 'Folder/group-v4/parent')
                old = deepcopy(self.native.routes[path])
                self.native.routes[path]['body'].update({'userName': 'foreign-reader'} if mutation == 'user' else {'value': 'datacenter-2'})
                with self.assertRaises(ValueError): self.acquire()
                self.native.routes[path] = old

    def test_extra_write_privilege_missing_view_or_expired_material_fail_closed(self):
        path = vm.PREFIX + 'AuthorizationManager/AuthorizationManager/FetchUserPrivilegeOnEntities'
        for privileges in (sorted(_PRIVILEGES['DISCOVER_READ'] | {'VirtualMachine.Interact.PowerOn'}), ['System.Read']):
            self.native.post_routes[path]['body'][0]['privileges'] = privileges
            with self.assertRaises(ValueError): self.acquire()
        self.material.expires_at = utcnow() - timedelta(seconds=1)
        before = len(self.native.requests)
        with self.assertRaises(ValueError): self.acquire()
        self.assertEqual(len(self.native.requests), before)

    def test_current_revocation_between_identity_and_scope_blocks_next_native_exchange(self):
        def hook(path, _count, spec):
            if path.endswith('/currentSession'):
                self.revoked = True
            return spec
        self.native.hook = hook
        with self.assertRaises(PermissionError): self.acquire()
        self.assertEqual(len(self.native.requests), 1)

    def test_cold_export_profile_does_not_grant_snapshot_mutation_or_random_disk_write(self):
        self.assertEqual(_PRIVILEGES['SNAPSHOT_EXPORT'], _PRIVILEGES['DISCOVER_READ'] | {'VApp.Export'})


class NativeDiskRemovalTests(unittest.TestCase):
    def setUp(self):
        self.native = Fixture(); self.addCleanup(self.native.close)
        self.member = lifecycle_record(self.native.directory)['members'][0]
        self.request = self.member['native_fence']['power_request']
        self.request['snapshot']['origin'] = self.native.origin
        self.resource = self.request['snapshot']['resources'][0]
        before = self.resource['expected']
        self.before = vsphere_power.normalize_after(self.request, before)
        self.disks = selected_disks(self.request, [2001])
        self.guard = object.__new__(LifecycleCommandGuard)
        self.guard.phase = 'SOURCE_FENCE'; self.guard.operation_kind = 'SOURCE_FENCE'
        self.authority = object.__new__(ApplicationWorkerCommandAuthority); self.authority.intent_guard = self.guard
        self.runtime = object.__new__(SourceDiskFenceRuntime)
        object.__setattr__(self.runtime, 'source', SimpleNamespace(session='unused-old-session', ca_file=self.native.directory / 'ca.pem'))
        object.__setattr__(self.runtime, 'credentials', object.__new__(VsphereNativeCredentialOwner))
        self.checks = 0; self.revoked = False
        def current(*_):
            self.checks += 1
            if self.revoked: raise PermissionError('Local-only current application authority revoked')
            return SimpleNamespace(grant_id='actual-selected-grant'), utcnow() + timedelta(seconds=30)
        self.addCleanup(patch.stopall)
        patch.object(LifecycleCommandGuard, 'require_current', current).start()
        patch.object(ApplicationWorkerCommandAuthority, 'require_current', current).start()
        patch.object(ApplicationWorkerCommandAuthority, 'timeout', lambda *args: 20).start()
        patch.object(SourceDiskFenceRuntime, 'require_previous_exclusion', current).start()
        patch.object(VsphereNativeCredentialOwner, 'acquire_session', lambda *_, **__: NativeVsphereSession(
            'fresh-local-native-session', utcnow() + timedelta(seconds=20))).start()
        self.after = deepcopy(self.before); self.after['config']['changeVersion'] = 'next-revision'
        self.after['config']['hardware']['device'] = [row for row in self.after['config']['hardware']['device'] if row['key'] != 2001]
        at = c.now()
        self.witness = dict(_typeName='TaskInfo', key='task-1', task=ref('Task', 'task-1'),
            entity=ref('VirtualMachine', 'vm-1'), descriptionId='VirtualMachine.reconfigure', eventChainId=123,
            queueTime=at, startTime=at, completeTime=at, state='success', cancelled=False)
        self.native.routes = {vm.resource_target(self.resource, key): {'body': value} for key, value in self.after.items()}
        self.native.routes[task.task_target({'moid': 'task-1'})] = {'body': self.witness}
        self.native.post_routes[vm.resource_target(self.resource, 'ReconfigVM_Task')] = {'body': ref('Task', 'task-1')}
        pages = []
        def collector(body):
            pages[:] = [[deepcopy(self.witness)]] if body['filter']['state'] == ['success', 'error'] else []
            pages.append([])
            return {'body': ref('TaskHistoryCollector', 'collector-1')}
        self.native.post_routes[vm.PREFIX + 'TaskManager/TaskManager/CreateCollectorForTasks'] = collector
        self.native.post_routes[vm.PREFIX + 'TaskHistoryCollector/collector-1/ReadNextTasks'] = lambda _: {'body': pages.pop(0)}
        self.native.post_routes[vm.PREFIX + 'HistoryCollector/collector-1/DestroyCollector'] = {'status': 204}
        self.client = _ApplicationVsphereClient(self.request, self.runtime, self.guard, self.authority)

    def test_real_native_remove_preserves_backing_boot_disk_and_optimistic_revision(self):
        original = deepcopy(self.before)
        task_id = self.client.detach(original, self.disks)
        payload = self.native.post_bodies[0][1]['spec']
        self.assertEqual(payload['changeVersion'], original['config']['changeVersion'])
        self.assertEqual(payload['deviceChange'], [{'operation': 'remove', 'device': self.disks[0]}])
        self.assertNotIn('fileOperation', payload['deviceChange'][0])
        observed = observe_removed(self.request, self.disks, task_id, self.witness['queueTime'], self.client)
        self.assertEqual(observed['state'], 'SOURCE_DATA_DISKS_DETACHED_PERSISTENTLY')
        self.assertIn(2000, {row['key'] for row in observed['vm_snapshot']['config']['hardware']['device']})
        self.assertGreater(self.checks, 20)

    def test_running_source_or_revocation_cannot_send_disk_remove(self):
        running = deepcopy(self.before); running['runtime']['powerState'] = 'poweredOn'
        with self.assertRaises(ValueError): self.client.detach(running, self.disks)
        self.revoked = True
        with self.assertRaises(PermissionError): self.client.detach(self.before, self.disks)
        self.assertEqual(self.native.post_bodies, [])

    def test_late_restarted_vm_retained_boot_change_or_foreign_task_blocks_completion(self):
        path = vm.resource_target(self.resource, 'config')
        for boundary in ('boot', 'source-restart', 'foreign-task'):
            with self.subTest(boundary=boundary):
                old = deepcopy(self.native.routes)
                if boundary == 'boot': self.native.routes[path]['body']['hardware']['device'][1]['backing']['uuid'] = 'foreign-boot-backing'
                elif boundary == 'source-restart': self.native.routes[vm.resource_target(self.resource, 'runtime')]['body']['powerState'] = 'poweredOn'
                else: self.native.routes[task.task_target({'moid': 'task-1'})]['body']['entity']['value'] = 'vm-2'
                with self.assertRaises(ValueError):
                    observe_removed(self.request, self.disks, 'task-1', self.witness['queueTime'], self.client)
                self.native.routes = old


if __name__ == '__main__':
    unittest.main()
