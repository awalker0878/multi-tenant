"""Concrete application file/native failure boundaries; no native qualification."""
from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from tests.test_restic_run import fixture as restic_config
from tests.test_vsphere_power import request as power_request
from tests.provisioning.schema.test_enterprise_records import SOURCE, TARGET
from provisioner.execution.run_files import digest, encoded
from provisioner.migration.guest_lifecycle import ACTION_SOURCE_FILES, tree, _copy
from provisioner.migration.lifecycle import ApplicationLifecycleSelection, PHASES


def lifecycle_record(root, *, source_root=None, source_scope=None, destination_scope=None):
    """A complete valid descriptor with real selected package closure bytes.

    Filesystem/syscalls and native API evidence are exercised separately. This
    helper is a selector fixture, never a writer-exclusion or acceptance proof.
    """
    root = Path(root).absolute()
    source_root = Path(source_root) if source_root is not None else Path(__file__).resolve().parents[1]
    source_scope = deepcopy(SOURCE if source_scope is None else source_scope)
    destination_scope = deepcopy(TARGET if destination_scope is None else destination_scope)
    destination_scope['platformFamily'] = 'openstack'; destination_scope['endpointId'] = 'openstack-01'
    native = power_request()
    expected = native['snapshot']['resources'][0]['expected']
    disk = deepcopy(expected['config']['hardware']['device'][1])
    disk.update(key=2001, unitNumber=1)
    disk['backing'].update(uuid='6000c290000000000000000000000001', fileName='[fixture-ds] vm/app.vmdk')
    expected['config']['hardware']['device'].insert(2, disk)
    closure = {'root': '/opt/hosting-application', 'python_sha256': digest(Path('/usr/bin/python3').resolve().read_bytes()),
               'source_files': {name: digest((source_root / name).read_bytes()) for name in ACTION_SOURCE_FILES}}
    target_uuid = '11111111-1111-4111-8111-111111111111'
    volume_id = '22222222-2222-4222-8222-222222222222'

    def guest(side, native_id, native_uuid, machine_id, serial):
        mount = root / (side + '-disk')
        return {'native_id': native_id, 'native_uuid': native_uuid, 'machine_id': machine_id,
            'unit': 'hosting-application.service', 'unit_sha256': 'a' * 64, 'uid': 1000, 'gid': 1000,
            'mount_path': str(mount), 'filesystem_uuid': '33333333-3333-4333-8333-333333333333',
            'data_path': str(mount / 'app'), 'block_serial': serial,
            'executable': {'path': '/usr/local/libexec/hosting-application', 'sha256': 'b' * 64, 'arguments': []},
            'health': {'port': 8080, 'path': '/health', 'response_sha256': digest(b'application-ready')},
            'action_runtime': deepcopy(closure)}

    source = guest('source', 'vm-1', expected['config']['uuid'], 'a' * 32, disk['backing']['uuid'])
    target = guest('target', target_uuid, target_uuid, Path('/etc/machine-id').read_text().strip(), volume_id.replace('-', ''))
    config = restic_config(); config['source'] = source['data_path']; config['machine_id'] = source['machine_id']
    target_config = deepcopy(config); target_config.update(source=target['data_path'], machine_id=target['machine_id'], member='target-guest')
    target_config['scope'] = config['scope'] | {'platform': 'openstack', 'site_key': 'site-b', 'wsd_key': 'science-target'}
    maximum = 1024 * 1024

    def resources(side):
        return {'stage_parent': str(root / (side + '-stage')), 'cgroup': '/hosting/' + side + '-restore',
            'block_device': '8:1' if side == 'source' else '8:2',
            'limits': {'download_kib_per_second': 256, 'block_iops': 20, 'stage_bytes': 16 * maximum, 'expected_bytes': maximum}}

    member = {'machine_id': 'machine-1', 'dataset_id': 'dataset-1', 'source': source, 'target': target,
        'initial_target_path': str(root / 'target-stage' / 'initial' / source['data_path'].lstrip('/')),
        'rehearsal_path': str(root / 'target-stage' / 'rehearsal'), 'final_target_path': str(root / 'target-stage' / 'final'),
        'recovery_target_path': str(root / 'source-stage' / 'reverse'), 'forward_target_path': str(root / 'target-stage' / 'forward'),
        'max_bytes': maximum, 'source_export': config, 'target_export': target_config,
        'source_resources': resources('source'), 'target_resources': resources('target'),
        'source_io': {'cgroup': '/hosting/source-export', 'block_device': '8:3', 'bandwidth_kib_per_second': 256, 'block_iops': 20},
        'target_io': {'cgroup': '/hosting/target-export', 'block_device': '8:4', 'bandwidth_kib_per_second': 256, 'block_iops': 20},
        'phases': {name: {'step_id': 'application-' + name.lower().replace('_', '-'),
            'operation_id': 'operation-' + name.lower().replace('_', '-'), 'scope_side': side, 'operation_kind': kind}
            for name, (side, kind) in PHASES.items()},
        'native_fence': {'power_request': native, 'disk_keys': [2001],
            'previous_owner': {'worker_id': 'old-source-writer', 'owner_epoch': 1, 'incident_id': 'source-incident'}},
        'target_native_fence': {'volume_id': volume_id, 'device': '/dev/vdb',
            'previous_owner': {'worker_id': 'old-target-writer', 'owner_epoch': 1, 'incident_id': 'target-incident'},
            'identity_url': 'https://identity.example.invalid/v3', 'compute_endpoint': 'https://compute.example.invalid/v2.1',
            'volume_endpoint': 'https://volume.example.invalid/v3/' + destination_scope['nativeScopeId'],
            'region': 'RegionOne', 'interface': 'internal', 'cloud_alias': 'target', 'ca_sha256': 'c' * 64},
        'traffic_steps': {name: name.replace('_', '-') for name in
                          ('cutover_dns', 'cutover_propagation', 'return_dns', 'return_propagation')}}
    return {'format': 'hosting-application-lifecycle-selection/1', 'guest_profile': 'linux-ubuntu-2404',
            'source_scope': source_scope, 'destination_scope': destination_scope, 'members': [member]}


def lifecycle_fixture(root, **keywords):
    return ApplicationLifecycleSelection.from_record(lifecycle_record(root, **keywords))


class LifecycleSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.body = lifecycle_record(self.root)

    def test_complete_native_and_source_bound_descriptor_roundtrips(self):
        selected = ApplicationLifecycleSelection.from_record(self.body)
        self.assertEqual(selected.to_dict(), self.body)
        self.assertEqual(selected.member('machine-1')['phases']['SOURCE_REATTACH']['operation_kind'], 'DISK_ATTACH')
        self.assertEqual(selected.member('machine-1')['phases']['SOURCE_START']['operation_kind'], 'VM_POWER')
        self.assertEqual(selected.member('machine-1')['phases']['VERIFY_READ']['operation_kind'], 'DISCOVER_READ')

    def test_native_alias_wrong_disk_or_source_closure_cannot_be_selected(self):
        for change in (
            lambda row: row['phases']['SOURCE_REATTACH'].__setitem__('operation_kind', 'VM_POWER'),
            lambda row: row['source'].__setitem__('block_serial', 'f' * 32),
            lambda row: row['source']['action_runtime']['source_files'].pop('provisioner/execution/restic_run.py'),
            lambda row: row.__setitem__('rehearsal_path', row['final_target_path']),
            lambda row: row['target_native_fence'].__setitem__('volume_id', '44444444-4444-4444-8444-444444444444')):
            body = deepcopy(self.body); change(body['members'][0])
            with self.assertRaises(ValueError): ApplicationLifecycleSelection.from_record(body)


class ActualFileTreeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name); self.source = self.root / 'source'; self.source.mkdir(mode=0o700)
        (self.source / 'nested').mkdir(mode=0o750)
        (self.source / 'nested' / 'business').write_bytes(b'committed business data')
        (self.source / 'nested' / 'business').chmod(0o640)

    def test_actual_copy_retains_complete_useful_bytes_and_file_directory_metadata(self):
        manifest = tree(str(self.source), 4096)
        copied = self.root / 'rehearsal'
        result = _copy(str(self.source), str(copied), manifest, 4096)
        self.assertEqual(tree(str(copied), 4096), manifest)
        self.assertEqual(result['destination_sha256'], digest(encoded(manifest)))
        with self.assertRaises(ValueError): _copy(str(self.source), str(copied), manifest, 4096)

    def test_link_alias_special_metadata_and_byte_budget_fail_closed(self):
        file = self.source / 'nested' / 'business'
        with self.assertRaises(ValueError): tree(str(self.source), 1)
        file.chmod(0o4640)
        with self.assertRaises(ValueError): tree(str(self.source), 4096)
        file.chmod(0o640)
        (self.source / 'linked').symlink_to(file)
        with self.assertRaises(ValueError): tree(str(self.source), 4096)

    def test_changed_source_after_manifest_cannot_be_published(self):
        manifest = tree(str(self.source), 4096)
        (self.source / 'nested' / 'business').write_bytes(b'a later committed transaction')
        with self.assertRaises(ValueError): _copy(str(self.source), str(self.root / 'copy'), manifest, 4096)


if __name__ == '__main__':
    unittest.main()
