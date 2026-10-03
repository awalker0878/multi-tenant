"""Descriptor and real sandbox command boundaries, with synthetic disk metadata."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from provisioner.domain.enterprise_records import plan_digest
from provisioner.execution.image_sandbox import ImageLimits, ImageSandboxHold, SandboxToolchain
from provisioner.migration.cold_descriptor import (
    FORMAT, ColdCaptureDescriptor, ColdDescriptorHold, inspect_retained_disks,
)
from tests.provisioning.operations.campaign_fixtures import AS_OF, fixture
from tests.provisioning.schema.test_enterprise_records import plan


class ColdDescriptorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / 'source'; self.source.mkdir(mode=0o700)
        self.plan = plan()
        self.plan['spec']['destination']['platformFamily'] = 'openstack'
        self.plan['spec']['route'].update(method='COLD_VM_CONVERSION', guestProfile='linux-ubuntu-2404')
        self.plan['metadata']['planDigest'] = plan_digest(self.plan)
        spec, _, _ = fixture()
        self.spec = replace(spec, method='COLD_WHOLE_VM', workload_id=self.plan['spec']['workloadId'],
                            plan_digest=self.plan['metadata']['planDigest'])
        self.disks = []
        for slot in (0, 1):
            path = self.source / f'disk-{slot}.raw'
            path.write_bytes(b'fixture-cold-disk'); path.chmod(0o600)
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            self.disks.append({'diskId': f'disk-1-{slot}', 'slot': slot, 'path': path.name,
                'format': 'raw', 'virtualSize': 17, 'sha256': sha, 'standalone': True, 'encrypted': False,
                'chain': [{'nativeId': 'native-disk-' + str(slot), 'parentNativeId': None, 'sha256': sha}]})
        self.body = {'format': FORMAT, 'campaignDigest': self.spec.digest,
            'source': deepcopy(self.plan['spec']['source']), 'destination': deepcopy(self.plan['spec']['destination']),
            'sourceBinding': deepcopy(self.plan['spec']['machineMappings'][0]['sourceBinding']),
            'capture': {'snapshotId': self.plan['spec']['sourceSnapshotId'], 'capturedAt': AS_OF.isoformat(),
                'sourceObservationDigest': 'a' * 64, 'powerState': 'POWERED_OFF',
                'writerFenceDigest': 'b' * 64, 'nativeTaskIds': [], 'nativeTaskState': 'QUIESCED',
                'nativeTaskObservationDigest': 'c' * 64, 'snapshotChainComplete': True},
            'guest': {'profile': 'linux-ubuntu-2404', 'architecture': 'x86_64', 'firmware': 'UEFI',
                'secureBoot': True, 'bootDiskId': 'disk-1-0', 'devicesComplete': True,
                'devices': [{'deviceId': 'controller-01', 'kind': 'VIRTUAL_CONTROLLER',
                             'model': 'pvscsi', 'backingId': 'native-controller-01'}],
                'driverEvidenceDigest': 'd' * 64, 'remediationPlanDigest': 'e' * 64}, 'disks': self.disks}
        self.tools = SandboxToolchain(Path('/usr/bin/bwrap'), Path('/usr/bin/qemu-img'),
                                      Path('/usr/bin/prlimit'), *(['f' * 64] * 3))
        self.limits = ImageLimits(1024, 1024)
        self.commands = []

    def descriptor(self):
        return ColdCaptureDescriptor.from_record(self.body, self.spec, self.plan)

    def runner(self, argv, **kwargs):
        self.commands.append(argv)
        command = argv[argv.index('/usr/bin/qemu-img') + 1:]
        self.assertEqual(command, ['info', '--output=json', '-f', 'raw', '/input/disk.image'])
        self.assertEqual(kwargs['env'], {'PATH': '/usr/bin'})
        self.assertEqual(kwargs['stdin'], subprocess.DEVNULL)
        self.assertIn('--unshare-all', argv)
        self.assertIn('--clearenv', argv)
        self.assertIn('--cap-drop', argv)
        self.assertNotIn('--share-net', argv)
        self.assertNotIn('--unshare-user-try', argv)
        kwargs['stdout'].write(json.dumps({'format': 'raw', 'virtual-size': 17}).encode())

    def inspect(self, runner=None):
        return inspect_retained_disks(self.descriptor(), self.spec, self.source,
            self.root / 'inspection', tools=self.tools, limits=self.limits, as_of=AS_OF,
            runner=runner or self.runner)

    def test_valid_descriptor_inspects_each_standalone_disk_but_whole_vm_route_remains_held(self):
        with patch.object(SandboxToolchain, 'verify'):
            report = self.inspect()
        self.assertEqual(report['status'], 'RETAINED_DISKS_INSPECTED_ROUTE_UNAVAILABLE')
        self.assertEqual(len(report['diskInspections']), 2)
        self.assertEqual(len(self.commands), 2)
        self.assertIn('NATIVE_COLD_CAPTURE_EXPORT_OWNER_MISSING', report['nativeImplementationBlockers'])
        for field in ('capturePerformed', 'captureAuthenticated', 'conversionPerformed',
                      'targetImported', 'guestBootQualified', 'mutationAuthorized', 'nativeContact'):
            self.assertFalse(report[field])
        self.assertFalse(any(self.root.rglob('*.qcow2')))

    def test_unknown_power_tasks_boot_devices_encryption_or_chain_prevents_parser_contact(self):
        for mutate in (
            lambda value: value['capture'].update(powerState='UNKNOWN'),
            lambda value: value['capture'].update(nativeTaskState='IN_FLIGHT'),
            lambda value: value['capture'].update(snapshotChainComplete=False),
            lambda value: value['capture'].update(writerFenceDigest=None),
            lambda value: value['guest'].update(firmware='UNKNOWN'),
            lambda value: value['guest'].update(secureBoot='UNKNOWN'),
            lambda value: value['guest'].update(devicesComplete=False),
            lambda value: value['guest'].update(driverEvidenceDigest=None),
            lambda value: value['guest']['devices'][0].update(kind='GPU_PASSTHROUGH'),
            lambda value: value['disks'][0].update(encrypted='UNKNOWN'),
            lambda value: value['disks'][0].update(standalone=False),
        ):
            original = deepcopy(self.body); mutate(self.body)
            report = self.inspect(runner=lambda *a, **k: self.fail('held descriptor reached parser'))
            self.assertEqual(report['status'], 'COLD_DESCRIPTOR_HELD')
            self.assertTrue(report['inspectionBlockers'])
            self.assertFalse((self.root / 'inspection').exists())
            self.body = original

    def test_missing_foreign_or_partial_canonical_identity_rejects_descriptor(self):
        for mutate in (
            lambda value: value['sourceBinding'].update(nativeScopeId='foreign'),
            lambda value: value['destination'].update(locationId='foreign-site'),
            lambda value: value['capture'].update(snapshotId='another-snapshot'),
            lambda value: value['guest'].update(bootDiskId='absent-boot-disk'),
            lambda value: value['disks'].pop(),
            lambda value: value['disks'][0].pop('encrypted'),
            lambda value: value.update(campaignDigest='f' * 64),
        ):
            original = deepcopy(self.body); mutate(self.body)
            with self.assertRaises((ColdDescriptorHold, ValueError)):
                self.descriptor()
            self.body = original

    def test_disk_chain_lineage_or_native_identity_duplication_never_becomes_standalone(self):
        row = self.body['disks'][0]
        row['chain'].append({'nativeId': 'delta-01', 'parentNativeId': 'unknown-parent', 'sha256': row['sha256']})
        with self.assertRaisesRegex(ColdDescriptorHold, 'lineage'):
            self.descriptor()
        row['chain'][-1]['parentNativeId'] = row['chain'][0]['nativeId']
        report = self.inspect(runner=lambda *a, **k: self.fail('disk chain must not reach isolated parser'))
        self.assertIn('COLD_DISK_CHAIN_REQUIRES_NATIVE_CONSOLIDATION', report['inspectionBlockers'])

    def test_retained_byte_change_fails_before_metadata_parser(self):
        (self.source / self.disks[0]['path']).write_bytes(b'changed disk image')
        with patch.object(SandboxToolchain, 'verify'), self.assertRaisesRegex(ImageSandboxHold, 'immutable capture digest'):
            self.inspect(runner=lambda *a, **k: self.fail('changed retained bytes reached parser'))

    def test_observed_virtual_extent_mismatch_does_not_qualify_declared_disk(self):
        def runner(argv, **kwargs):
            kwargs['stdout'].write(b'{"format":"raw","virtual-size":18}')
        with patch.object(SandboxToolchain, 'verify'), self.assertRaisesRegex(ColdDescriptorHold, 'virtual extent'):
            self.inspect(runner=runner)

    def test_missing_mandatory_tools_or_kernel_isolation_has_no_unconfined_fallback(self):
        with self.assertRaises(ImageSandboxHold):
            self.inspect(runner=lambda *a, **k: self.fail('unreviewed tool reached parser'))
        # New destination after the held first call; no original directory reused.
        self.root = self.root / 'kernel-case'; self.root.mkdir(mode=0o700)
        def failed(argv, **kwargs):
            raise subprocess.CalledProcessError(1, argv)
        with patch.object(SandboxToolchain, 'verify'), self.assertRaisesRegex(ImageSandboxHold, 'isolation'):
            self.inspect(runner=failed)

    def test_path_escape_and_raw_descriptor_constructor_are_rejected(self):
        self.body['disks'][0]['path'] = '../outside.raw'
        with self.assertRaisesRegex(ColdDescriptorHold, 'relative retained'):
            self.descriptor()
        with self.assertRaises(TypeError):
            ColdCaptureDescriptor('{}', self.spec.digest)

    def test_reverse_method_or_guest_change_cannot_reuse_descriptor(self):
        for changed in (replace(self.spec, source=self.spec.destination, destination=self.spec.source),
                        replace(self.spec, method='APPLICATION_REBUILD_RESTORE'),
                        replace(self.spec, guest_profile='windows-server-2022')):
            with self.assertRaises(ColdDescriptorHold):
                ColdCaptureDescriptor.from_record(self.body, changed, self.plan)


if __name__ == '__main__':
    unittest.main()
