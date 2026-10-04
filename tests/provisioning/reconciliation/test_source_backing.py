"""Fresh TLS disk accounting; B10 enrollment is explicitly synthetic here.

Native identity, privilege and file/task replies cross the actual TLS transport.
These fixtures qualify neither a VMware tuple nor its source-writer exclusion.
"""
from copy import deepcopy
from dataclasses import asdict
from datetime import timedelta
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests import test_application_native_boundaries as native
from tests.test_vsphere_observe import manifest, ref
from provisioner.controlplane.persistence import NativeBinding
from provisioner.controlplane.persistence import canonical_record_digest
from provisioner.allocations.transactions import ResourceUnits
from provisioner.controlplane.reconciliation.adapters.vmware_source_capacity import SourceCapacityReadRuntime
from provisioner.controlplane.reconciliation.adapters.vmware_source_backing import SourceBackingReadRuntime
from provisioner.execution import vsphere_observe as vm
from provisioner.execution.run_files import digest, encoded, utcnow, write_new
from provisioner.migration.vsphere_credentials import _BASE, _PRIVILEGES


class DetachedBackingWireTests(unittest.TestCase):
    def setUp(self):
        self.fixture = native.NativeSessionTests(); self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.expires = utcnow() + timedelta(seconds=90)
        self.fixture.material.expires_at = self.fixture.expires
        self.native = self.fixture.native
        (self.native.directory / 'ca.pem').chmod(0o600)
        self.reader = SourceBackingReadRuntime(self.fixture.enrollment, self.fixture.owner,
            self.native.directory / 'ca.pem', 'VStorageObjectManager',
            digest((self.native.directory / 'ca.pem').read_bytes()))
        self.binding = NativeBinding('vmware', 'vcenter-01', 'datacenter-1', 'vm', 'vm-1')
        self.disk = deepcopy(manifest()['resources'][0]['expected']['config']['hardware']['device'][1])
        self.disk['backing'].update(uuid='6000c290' + '0' * 24, thinProvisioned=True)
        self.native_uuid = self.disk['backing']['uuid']
        self.native.routes[vm.PREFIX + 'Datastore/datastore-1/parent'] = {'body': ref('Folder', 'group-s4')}
        self.native.routes[vm.PREFIX + 'Folder/group-s4/parent'] = {'body': ref('Datacenter', 'datacenter-1')}
        self.native.routes[vm.PREFIX + 'Datastore/datastore-1/summary'] = {'body': dict(
            name='fixture-ds', type='VMFS', accessible=True, multipleHostAccess=True,
            capacity=100 * 1024**3, freeSpace=50 * 1024**3)}
        self.native.routes[vm.PREFIX + 'Datastore/datastore-1/browser'] = {
            'body': ref('HostDatastoreBrowser', 'datastoreBrowser-datastore-1')}
        self.datastore_privileges = sorted(_BASE | {'Datastore.Browse', 'Datastore.FileManagement'})
        self.privilege_path = vm.PREFIX + 'AuthorizationManager/AuthorizationManager/FetchUserPrivilegeOnEntities'
        def privileges(body):
            entity = body['entities'][0]
            values = self.datastore_privileges if entity['type'] == 'Datastore' else sorted(_PRIVILEGES['DISCOVER_READ'])
            return {'body': [dict(entity=entity, privileges=values)]}
        self.native.post_routes[self.privilege_path] = privileges
        self.uuid_path = vm.PREFIX + 'VcenterVStorageObjectManager/VStorageObjectManager/QueryVirtualDiskUuidEx'
        self.native.post_routes[self.uuid_path] = lambda _: {'body': self.native_uuid}
        self.search_path = vm.PREFIX + 'HostDatastoreBrowser/datastoreBrowser-datastore-1/SearchDatastore_Task'
        self.searches = 0; self.task_state = 'success'; self.extra_file = False; self.wrong_task = False
        at = (utcnow() - timedelta(seconds=2)).isoformat()
        self.primary = dict(_typeName='VmDiskFileInfo', path='vm.vmdk', fileSize=512,
            modification=at, diskType='VirtualDiskFlatVer2BackingInfo', capacityKb=self.disk['capacityInKB'],
            thin=True, encryption=dict(_typeName='VmDiskEncryptionInfo'),
            diskExtents=['[fixture-ds] vm/vm-flat.vmdk'])
        self.extent = dict(_typeName='FileInfo', path='vm-flat.vmdk', fileSize=self.disk['capacityInBytes'], modification=at)
        self.task_hook = None
        def search(body):
            self.searches += 1; identifier = 'task-%d' % self.searches
            selected = body['searchSpec']['matchPattern'][0]
            row = self.primary if selected == 'vm.vmdk' else self.extent
            files = [deepcopy(row)] + ([deepcopy(row)] if self.extra_file else [])
            info = dict(_typeName='TaskInfo', key=identifier, task=ref('Task', identifier),
                state=self.task_state, cancelled=False, queueTime=at, startTime=at, completeTime=at,
                result=dict(_typeName='HostDatastoreBrowserSearchResults', datastore=ref('Datastore', 'datastore-1'),
                    folderPath='[fixture-ds] vm/', file=files))
            if self.wrong_task: info['key'] = 'task-999'
            if self.task_hook: self.task_hook(info, self.searches)
            self.native.routes[vm.PREFIX + 'Task/' + identifier + '/info'] = {'body': info}
            return {'body': ref('Task', identifier)}
        self.native.post_routes[self.search_path] = search

    def observe(self):
        return self.reader.observe(self.binding, self.disk)

    def test_uuid_capacity_and_extent_are_fresh_native_reads_with_exact_scoped_privileges(self):
        result = self.observe()
        self.assertEqual(result['native_uuid'], self.disk['backing']['uuid'])
        self.assertEqual(result['extent']['fileSize'], self.disk['capacityInBytes'])
        self.assertEqual(self.searches, 4)
        payloads = [body for path, body in self.native.post_bodies if path == self.search_path]
        self.assertEqual([body['searchSpec']['matchPattern'] for body in payloads],
            [['vm.vmdk'], ['vm-flat.vmdk'], ['vm.vmdk'], ['vm-flat.vmdk']])
        self.assertTrue(all(body['datastorePath'] == '[fixture-ds] vm/' for body in payloads))
        self.assertTrue(all(row['has_session_auth'] and not row['has_basic_auth'] for row in self.native.requests))
        self.assertFalse(any('/Delete' in row['path'] or '/Reconfig' in row['path'] for row in self.native.requests))
        self.assertGreater(self.fixture.checks, 100)

    def test_replaced_uuid_missing_extent_changed_capacity_encryption_and_search_ambiguity_hold(self):
        for name, change in (
            ('uuid', lambda: setattr(self, 'native_uuid', '1' * 32)),
            ('extent', lambda: self.extent.update(path='foreign-flat.vmdk')),
            ('capacity', lambda: self.primary.update(capacityKb=1)),
            ('encrypted', lambda: self.primary['encryption'].update(keyId={'keyId': 'foreign'})),
            ('parent extent', lambda: self.primary.update(diskExtents=['[fixture-ds] foreign/parent.vmdk'])),
            ('duplicate', lambda: setattr(self, 'extra_file', True)),
            ('task identity', lambda: setattr(self, 'wrong_task', True)),
        ):
            primary, extent, identity = deepcopy(self.primary), deepcopy(self.extent), self.native_uuid
            change()
            with self.subTest(name=name), self.assertRaises(ValueError): self.observe()
            self.primary, self.extent, self.native_uuid = primary, extent, identity
            self.extra_file = self.wrong_task = False

    def test_privilege_loss_extra_mutation_or_foreign_datacenter_blocks_before_disk_query(self):
        for privileges in (sorted(_BASE | {'Datastore.Browse'}),
            self.datastore_privileges + ['Datastore.Delete']):
            self.datastore_privileges = privileges
            with self.assertRaises(ValueError): self.observe()
        self.assertFalse(any(row['path'] == self.uuid_path for row in self.native.requests))
        self.datastore_privileges = sorted(_BASE | {'Datastore.Browse', 'Datastore.FileManagement'})
        self.native.routes[vm.PREFIX + 'Folder/group-s4/parent']['body']['value'] = 'datacenter-2'
        with self.assertRaises(ValueError): self.observe()
        self.assertEqual(self.searches, 0)

    def test_torn_file_read_and_revocation_hold_without_resubmitting_original_read_task(self):
        def changed(info, count):
            if count == 4: info['result']['file'][0]['fileSize'] -= 512
        self.task_hook = changed
        with self.assertRaisesRegex(ValueError, 'changed during'): self.observe()
        self.task_hook = None; self.native.requests.clear()
        def revoked(path, _count, spec):
            if path.endswith('/info'): self.fixture.revoked = True
            return spec
        self.native.hook = revoked
        with self.assertRaises(PermissionError): self.observe()
        self.assertTrue(self.native.requests[-1]['path'].endswith('/info'))

    def test_pending_native_read_task_is_not_reported_as_presence_or_resent(self):
        self.task_state = 'running'
        with self.assertRaisesRegex(ValueError, 'no resubmission'): self.observe()
        self.assertEqual(self.searches, 1)

    def test_selector_traversal_glob_chain_and_shared_backing_never_contact_native_site(self):
        for change in (
            lambda: self.disk['backing'].update(fileName='[fixture-ds] ../vm.vmdk'),
            lambda: self.disk['backing'].update(fileName='[fixture-ds] vm/*.vmdk'),
            lambda: self.disk['backing'].update(parent={'uuid': 'retained-parent'}),
            lambda: self.disk['backing'].update(sharing='sharingMultiWriter'),
        ):
            original = deepcopy(self.disk); change()
            with self.assertRaises(ValueError): self.observe()
            self.disk = original
        self.assertEqual(self.native.requests, [])


class RetainedSourceAccountingTests(unittest.TestCase):
    def setUp(self):
        self.wire = DetachedBackingWireTests(); self.wire.setUp()
        self.addCleanup(self.wire.doCleanups)
        wire = self.wire
        self.binding = wire.binding
        current = deepcopy(manifest()['resources'][0]['expected'])
        boot = current['config']['hardware']['device'][1]
        boot['backing'].update(uuid='6000c290' + '1' * 24, thinProvisioned=True)
        data = deepcopy(wire.disk); data.update(key=2001, unitNumber=1)
        data['backing']['fileName'] = '[fixture-ds] vm/data.vmdk'
        self.original = deepcopy(current)
        self.original['config']['hardware']['device'].insert(2, data)
        current['config']['changeVersion'] = 'after-persistent-detach'
        current['runtime']['powerState'] = 'poweredOff'
        wire.primary.update(path='data.vmdk', diskExtents=['[fixture-ds] vm/data-flat.vmdk'])
        wire.extent['path'] = 'data-flat.vmdk'
        old_search = wire.native.post_routes[wire.search_path]
        def search(body):
            # The shared TLS fixture routes the separately selected data file.
            selected = body['searchSpec']['matchPattern'][0]
            transformed = deepcopy(body)
            transformed['searchSpec']['matchPattern'] = ['vm.vmdk' if selected == 'data.vmdk' else 'vm-flat.vmdk']
            return old_search(transformed)
        wire.native.post_routes[wire.search_path] = search
        for key, value in current.items():
            wire.native.routes[vm.PREFIX + 'VirtualMachine/vm-1/' + key] = {'body': value}
        wire.native.routes[vm.PREFIX + 'VirtualMachine/vm-1/snapshot'] = {'body': None}
        self.units = ResourceUnits.from_bytes(vcpu=2, memory_bytes=4096 * 1024**2, storage_bytes=20 * 1024**3)
        self.bundle = SimpleNamespace(admitted=SimpleNamespace(job_id='original-stage', plan_digest='a' * 64),
            selection_digest='b' * 64, digest='c' * 64)
        self.pool = SimpleNamespace(scope=wire.fixture.scope,
            catalog=dict(pool_id='retained-source', origin=wire.native.origin), retained_source=self.units,
            total=lambda **_: asdict(self.units))
        self.capacity = object.__new__(SourceCapacityReadRuntime)
        for name, value in dict(enrollment=wire.fixture.enrollment, credentials=wire.fixture.owner,
            resource_pool_id='resgroup-1', ca_file=wire.reader.ca_file,
            directory=wire.native.directory, backing_reader=wire.reader).items():
            object.__setattr__(self.capacity, name, value)
        # Only canonical plan/SQL enrollment is a synthetic boundary here.
        # Native credentials, VM identity, file/task and capacity reads are real TLS.
        self.addCleanup(patch.stopall)
        patch.object(SourceCapacityReadRuntime, '_selected', return_value=(self.binding,)).start()
        object.__setattr__(wire.fixture.commands, 'identity', SimpleNamespace(subject='independent-source-reader'))
        object.__setattr__(wire.fixture.commands, 'grant', SimpleNamespace(operation_scope=wire.fixture.scope,
            grant_id='original-source-read-grant'))
        self.ids = sorted([self.binding.native_id, boot['backing']['uuid'], data['backing']['uuid']])
        record = dict(format='hosting-vsphere-source-capacity-observation/1',
            job_id=self.bundle.admitted.job_id, selection_digest=self.bundle.selection_digest,
            bundle_digest=self.bundle.digest, reservation_id='original-confirmed-source',
            pool_id=self.pool.catalog['pool_id'], scope=asdict(self.pool.scope), units=asdict(self.units),
            native_ids=self.ids, selected_source_bindings=[asdict(self.binding)],
            facts=[dict(binding=asdict(self.binding), native=self.original, datastores={})],
            reader_subject=wire.fixture.enrollment.subject, reader_grant_id=wire.fixture.commands.grant.grant_id,
            observed_at=utcnow().isoformat(), cleanup_observed=False)
        digest = canonical_record_digest(record)
        write_new(wire.native.directory / (digest + '.json'), encoded(record))
        self.receipt = dict(status='CONFIRMED', reservation_id='original-confirmed-source',
            native_ids=self.ids, units=asdict(self.units), evidence_ref=digest)
        self.plan = dict(metadata=dict(planDigest=self.bundle.admitted.plan_digest),
            spec=dict(machineMappings=[dict(sourceBinding=dict(platformFamily='vmware', endpointId='vcenter-01',
                nativeScopeId='datacenter-1', nativeId='vm-1'))]))

    def accounted(self):
        return self.capacity.require_accounted(None, self.bundle, self.pool, self.receipt, self.plan)

    def test_actual_detached_file_remains_in_original_identity_set_and_full_charge(self):
        original_receipt = deepcopy(self.receipt)
        current = self.accounted()
        self.assertEqual(current['native_ids'], self.ids)
        self.assertEqual(current['units'], asdict(self.units))
        self.assertFalse(current['cleanup_observed'])
        self.assertEqual(self.receipt, original_receipt)
        self.assertEqual(self.wire.searches, 4)
        self.assertTrue(all(body['name'] == '[fixture-ds] vm/data.vmdk'
            for path, body in self.wire.native.post_bodies if path == self.wire.uuid_path))

    def test_attached_original_disks_and_power_changes_keep_charge_without_file_lookup(self):
        path = vm.PREFIX + 'VirtualMachine/vm-1/config'
        self.wire.native.routes[path]['body'] = deepcopy(self.original['config'])
        self.wire.native.routes[vm.PREFIX + 'VirtualMachine/vm-1/runtime']['body']['powerState'] = 'poweredOn'
        self.assertEqual(self.accounted()['units'], asdict(self.units))
        self.assertEqual(self.wire.searches, 0)

    def test_missing_reader_or_replaced_native_file_holds_and_preserves_receipt(self):
        receipt = deepcopy(self.receipt)
        object.__setattr__(self.capacity, 'backing_reader', None)
        with self.assertRaisesRegex(ValueError, 'backing reader'): self.accounted()
        object.__setattr__(self.capacity, 'backing_reader', self.wire.reader)
        self.wire.native_uuid = 'f' * 32
        with self.assertRaisesRegex(ValueError, 'another original disk UUID'): self.accounted()
        self.assertEqual(self.receipt, receipt)

    def test_changed_vm_compute_or_attached_disk_holds_before_detached_file_contact(self):
        path = vm.PREFIX + 'VirtualMachine/vm-1/config'
        for change in (
            lambda value: value.update(uuid='ffffffff-ffff-4fff-8fff-ffffffffffff'),
            lambda value: value['hardware'].update(numCPU=4),
            lambda value: value['hardware']['device'][1]['backing'].update(uuid='f' * 32),
        ):
            original = deepcopy(self.wire.native.routes[path]['body']); change(self.wire.native.routes[path]['body'])
            with self.assertRaises(ValueError): self.accounted()
            self.wire.native.routes[path]['body'] = original
        self.assertEqual(self.wire.searches, 0)

    def test_original_evidence_mismatch_cannot_be_used_as_new_selector(self):
        self.receipt['native_ids'] = ['vm-1']
        with self.assertRaisesRegex(ValueError, 'original independently confirmed'): self.accounted()
        self.assertEqual(self.wire.native.requests, [])
