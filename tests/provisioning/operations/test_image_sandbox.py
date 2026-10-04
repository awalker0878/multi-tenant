import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from provisioner.execution.image_sandbox import (
    convert, inspect, ImageLimits, ImageSandboxHold, SandboxToolchain,
)


class ImageSandboxTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / 'cold-disk.raw'
        self.source.write_bytes(b'fixture-cold-disk')
        self.digest = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.tools = SandboxToolchain(Path('/usr/bin/bwrap'), Path('/usr/bin/qemu-img'),
            Path('/usr/bin/prlimit'), *(['b' * 64] * 3))
        self.limits = ImageLimits(1024, 1024)

    def tearDown(self):
        self.temporary.cleanup()

    def runner(self, argv, **kwargs):
        self.argv = argv
        self.assertEqual(kwargs['env'], {'PATH': '/usr/bin'})
        self.assertEqual(kwargs['stdin'], subprocess.DEVNULL)
        command = argv[argv.index('/usr/bin/qemu-img') + 1:]
        if command[0] == 'info':
            kwargs['stdout'].write(json.dumps({'format': command[3], 'virtual-size': 17}).encode())
        else:
            output_host = Path(argv[argv.index('--bind') + 1])
            (output_host / 'disk.qcow2').write_bytes(b'synthetic-converted-disk')

    def test_fixed_converter_command_namespaces_ro_source_and_fresh_artifact(self):
        with patch.object(SandboxToolchain, 'verify'):
            result = convert(self.source, self.root / 'conversion', source_sha256=self.digest,
                input_format='raw', tools=self.tools, limits=self.limits, runner=self.runner)
        self.assertEqual(result['status'], 'CONVERTED_DISK_ARTIFACT_NOT_GUEST_QUALIFICATION')
        self.assertFalse(result['guestBootQualified'])
        self.assertFalse(result['mutationAuthorized'])
        self.assertIn('--unshare-all', self.argv)
        self.assertIn('--cap-drop', self.argv)
        self.assertIn('--clearenv', self.argv)
        self.assertNotIn('--share-net', self.argv)
        self.assertNotIn('--unshare-user-try', self.argv)
        self.assertEqual(self.source.read_bytes(), b'fixture-cold-disk')
        self.assertEqual(Path(result['outputPath']).stat().st_mode & 0o777, 0o400)

    def test_wrong_digest_existing_output_and_unknown_format_never_run_parser(self):
        with patch.object(SandboxToolchain, 'verify'):
            for options in ({'source_sha256': 'c' * 64, 'input_format': 'raw'},
                            {'source_sha256': self.digest, 'input_format': 'unreviewed'}):
                with self.assertRaises(ImageSandboxHold):
                    convert(self.source, self.root / 'bad-conversion', tools=self.tools,
                            limits=self.limits, runner=lambda *a, **k: self.fail('must not parse'), **options)
            with self.assertRaises(ImageSandboxHold):
                convert(self.source, self.root, source_sha256=self.digest,
                        input_format='raw', tools=self.tools, limits=self.limits,
                        runner=lambda *a, **k: self.fail('must not parse'))

    def test_backing_encryption_oversize_and_namespace_failure_hold_before_conversion(self):
        for metadata in ({'backing-filename': 'nbd:outside'}, {'encrypted': True}, {'virtual-size': 10000}):
            with self.subTest(metadata=metadata), patch.object(SandboxToolchain, 'verify'):
                def runner(argv, **kwargs):
                    kwargs['stdout'].write(json.dumps({'format': 'raw', 'virtual-size': 17, **metadata}).encode())
                with self.assertRaises(ImageSandboxHold):
                    convert(self.source, self.root / ('held-' + str(len(list(self.root.iterdir())))),
                        source_sha256=self.digest, input_format='raw', tools=self.tools,
                        limits=self.limits, runner=runner)
        with patch.object(SandboxToolchain, 'verify'):
            def failed(argv, **kwargs):
                raise subprocess.CalledProcessError(1, argv)
            with self.assertRaisesRegex(ImageSandboxHold, 'isolation'):
                convert(self.source, self.root / 'missing-user-namespace', source_sha256=self.digest,
                    input_format='raw', tools=self.tools, limits=self.limits, runner=failed)

    def test_missing_or_changed_actual_reviewed_tools_never_fall_back(self):
        with self.assertRaises(ImageSandboxHold):
            convert(self.source, self.root / 'no-tools', source_sha256=self.digest,
                input_format='raw', tools=self.tools, limits=self.limits,
                runner=lambda *a, **k: self.fail('must not run unreviewed binaries'))

    def test_source_growth_after_descriptor_check_is_bounded_before_any_parser(self):
        original = self.source.read_bytes()
        original_stat = os.fstat
        def grow_after_stat(descriptor):
            info = original_stat(descriptor)
            self.source.write_bytes(original + b'x' * 4096)
            return info
        with patch.object(SandboxToolchain, 'verify'), \
             patch('provisioner.execution.image_sandbox.os.fstat', side_effect=grow_after_stat), \
             self.assertRaisesRegex(ImageSandboxHold, 'grew beyond'):
            convert(self.source, self.root / 'growing-capture', source_sha256=self.digest,
                input_format='raw', tools=self.tools, limits=self.limits,
                runner=lambda *a, **k: self.fail('changed input must not reach the parser'))
        retained = self.root / 'growing-capture' / 'retained-input' / 'disk.image'
        self.assertLessEqual(retained.stat().st_size, len(original))
        self.assertFalse(list((self.root / 'growing-capture' / 'converted').iterdir()))

    def test_public_output_parent_cannot_become_converter_storage(self):
        shared = self.root / 'shared-parent'
        shared.mkdir(mode=0o755)
        with patch.object(SandboxToolchain, 'verify'), self.assertRaisesRegex(ImageSandboxHold, 'private storage'):
            inspect(self.source, shared / 'inspection', source_sha256=self.digest,
                input_format='raw', tools=self.tools, limits=self.limits,
                runner=lambda *a, **k: self.fail('public destination must not reach the parser'))
        self.assertFalse((shared / 'inspection').exists())

    def test_inspection_uses_only_fixed_info_on_retained_digest_bound_source(self):
        commands = []
        def run(argv, **kwargs):
            commands.append(argv[argv.index('/usr/bin/qemu-img') + 1])
            self.runner(argv, **kwargs)
        with patch.object(SandboxToolchain, 'verify'):
            result = inspect(self.source, self.root / 'inspection', source_sha256=self.digest,
                input_format='raw', tools=self.tools, limits=self.limits, runner=run)
        self.assertEqual(commands, ['info'])
        self.assertEqual(result['format'], 'hosting-isolated-disk-inspection/1')
        self.assertEqual(result['sourceSha256'], self.digest)
        self.assertFalse(result['mutationAuthorized'])
        self.assertFalse(list((self.root / 'inspection' / 'converted').iterdir()))

    @unittest.skipUnless(shutil.which('qemu-img') and shutil.which('bwrap'),
                         'Actual qemu-img/bwrap engine pair unavailable; no conversion engine pass claimed')
    def test_actual_engine_convert_or_mandatory_kernel_namespace_hold(self):
        tools = SandboxToolchain(*(Path(shutil.which(name)) for name in ('bwrap', 'qemu-img', 'prlimit')),
            *(hashlib.sha256(Path(shutil.which(name)).read_bytes()).hexdigest()
              for name in ('bwrap', 'qemu-img', 'prlimit')))
        try:
            result = convert(self.source, self.root / 'actual-engine', source_sha256=self.digest,
                input_format='raw', tools=tools, limits=self.limits)
        except ImageSandboxHold as exc:
            # This container may intentionally deny user namespaces. There must
            # be an explicit hold and no unconfined fallback/import success.
            self.assertIn('isolation', str(exc))
        else:
            self.assertFalse(result['guestBootQualified'])


if __name__ == '__main__':
    unittest.main()
