"""The reviewed guest snapshot must not import owners from the host installation."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

from provisioner.execution import guest_run

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_FILES = (
    '.hosting-root', 'pyproject.toml', 'hosting_resources/__init__.py', 'hosting_resources/runtime-documents.json',
    'provisioner/__init__.py', 'provisioner/domain/__init__.py',
    'provisioner/domain/errors.py', 'provisioner/compiler/__init__.py',
    'provisioner/compiler/wsd.py', 'provisioner/compiler/components.py',
    'provisioner/execution/__init__.py', 'provisioner/execution/neutron_observe.py',
    'provisioner/execution/readback_core.py', 'provisioner/execution/run_files.py',
    'provisioner/execution/guest_inventory.py', 'provisioner/execution/guest_services.py',
    'provisioner/execution/restic_run.py',
)
CHILD = r'''
import importlib.util, pathlib, sys
root = pathlib.Path(sys.argv[1]).resolve()
path = root / 'ansible/filter_plugins/guest_filters.py'
spec = importlib.util.spec_from_file_location('sealed_guest_filters', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert set(module.FilterModule().filters()) == {
    'hosting_guest_gate', 'hosting_resolvers_bound', 'hosting_handoff_current'}
import hosting_resources
from provisioner.compiler import components, wsd
from provisioner.execution import guest_inventory, guest_services, restic_run
assert hosting_resources.SOURCE_ROOT == root
assert hosting_resources.RESOURCE_ROOT == root
assert set(components.COMPONENTS) == {'nutanix', 'vmware', 'openstack'}
assert wsd.identity('reviewed-guest') == 'reviewed-guest'
assert callable(guest_inventory.gate) and callable(guest_services.validate_services)
assert callable(restic_run.validate)
for name, owner in sys.modules.items():
    if name.split('.')[0] in {'tools', 'provisioner', 'hosting_resources'}:
        path = getattr(owner, '__file__', None)
        assert path is not None and pathlib.Path(path).resolve().is_relative_to(root), (name, path)
'''


def snapshot(destination: Path) -> None:
    for source in guest_run.source_paths(ROOT):
        target = destination / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def import_snapshot(destination: Path):
    # -S removes all site packages, including editable checkout hooks. The
    # snapshot alone must own the pure gate's imports; third-party Ansible
    # runtime verification is exercised separately by the real controller test.
    return subprocess.run([sys.executable, '-I', '-S', '-B', '-c', CHILD, str(destination)],
                          cwd=destination.parent, capture_output=True, text=True, timeout=15)


class GuestSourceClosureTests(unittest.TestCase):
    def test_manifest_covers_package_owners_not_the_retired_build_dependency(self):
        paths = {p.relative_to(ROOT).as_posix() for p in guest_run.source_paths(ROOT)}
        self.assertTrue(set(PACKAGE_FILES) <= paths, sorted(set(PACKAGE_FILES) - paths))
        self.assertNotIn('scripts/build_wsd_compositions.py', paths)
        self.assertNotIn('scripts/__init__.py', paths)
        self.assertFalse(any(path.startswith('tools/') for path in paths))

    def test_guest_backup_role_installs_its_actual_package_import_closure(self):
        role = ROOT / 'ansible/roles/linux_guest_backup/tasks/main.yml'
        tasks = yaml.safe_load(role.read_text())
        block = next(task['block'] for task in tasks if 'block' in task)
        install = next(task for task in block
                       if task['name'] == 'Install the exact reviewed backup implementation')
        self.assertEqual(install['ansible.builtin.copy']['src'],
                         '{{ playbook_dir }}/../../../{{ item }}')
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / 'owned-backup'
            sealed = Path(folder) / 'sealed'
            snapshot(sealed)
            for relative in install['loop']:
                self.assertTrue(relative.startswith('provisioner/'), relative)
                source = sealed / relative
                self.assertTrue(source.is_file(), relative)
                target = destination / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
            # Use the service's cwd and isolation flags; no installed package,
            # editable checkout, executable restic or native repository is used.
            result = subprocess.run([sys.executable, '-S', '-E', '-s', '-B', '-m',
                                     'provisioner.execution.restic_run', '--help'],
                                    cwd=destination, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('backup,restore', result.stdout)
        unit = (ROOT / 'ansible/roles/linux_guest_backup/templates/hosting-backup.service.j2').read_text()
        self.assertIn('WorkingDirectory=/usr/local/lib/hosting\n', unit)
        self.assertIn('ExecStart=/usr/bin/python3 -E -s -B -m provisioner.execution.restic_run ', unit)

    def test_pure_gate_imports_with_no_checkout_or_installed_package_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / 'source'
            snapshot(destination)
            result = import_snapshot(destination)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_changed_compiler_copy_is_rejected_before_controller_dispatch(self):
        from unittest.mock import patch
        from tests.test_guest_apply import configured, SOURCE
        from provisioner.execution import guest_apply
        # This negative unit test never launches Python/SSH as a controller.
        # Mock only runtime inventory, then require rejection before dispatch.
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(guest_run, 'runtime_record',
                              return_value={'ssh_path': '/fixture-only/ssh'}):
                args = configured(Path(folder))
            owner = args.bundle / 'source/provisioner/compiler/components.py'
            owner.write_bytes(owner.read_bytes() + b'\n# changed after review\n')
            with patch.object(guest_run, 'verify', return_value=SOURCE), \
                 patch.object(guest_apply, 'run_process') as controller:
                with self.assertRaisesRegex(ValueError, 'Guest source copy differs'):
                    guest_apply.apply(args)
                controller.assert_not_called()

    def test_missing_package_owner_cannot_fall_back_to_installed_code(self):
        for relative in ('provisioner/compiler/wsd.py', 'provisioner/compiler/components.py',
                         'hosting_resources/__init__.py', 'hosting_resources/runtime-documents.json', 'provisioner/execution/neutron_observe.py',
                         'provisioner/execution/run_files.py', 'provisioner/execution/guest_inventory.py',
                         'provisioner/execution/guest_services.py', 'provisioner/execution/restic_run.py'):
            with self.subTest(owner=relative), tempfile.TemporaryDirectory() as folder:
                destination = Path(folder) / 'source'
                snapshot(destination)
                path = destination / relative
                self.assertTrue(path.is_file(), relative)
                path.unlink()
                self.assertNotEqual(import_snapshot(destination).returncode, 0)


if __name__ == '__main__':
    unittest.main()
