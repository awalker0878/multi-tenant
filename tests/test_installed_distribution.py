"""Build and exercise the real wheel with no checkout on the import path.

These tests intentionally use a fresh virtual environment and an unrelated
working directory. Import-only tests in the source tree cannot detect missing
wheel resources or accidental resolution of files at site-packages root.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import venv
import zipfile


ROOT = Path(__file__).resolve().parents[1]


class InstalledDistributionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = tempfile.TemporaryDirectory(prefix='hosting-installed-')
        cls.addClassCleanup(cls.workspace.cleanup)
        cls.base = Path(cls.workspace.name)
        cls.source = cls.base / 'source'
        shutil.copytree(ROOT, cls.source, ignore=shutil.ignore_patterns(
            '.git', '.venv', '__pycache__', '.pytest_cache', 'build', 'dist',
            '*.egg-info'))
        cls.work = cls.base / 'operator'
        cls.work.mkdir()
        cls.env = {key: value for key, value in os.environ.items()
                   if not key.startswith(('PYTHON', 'PIP_'))}
        cls.run_checked([sys.executable, 'setup.py', 'sdist', '--dist-dir',
                         str(cls.base / 'dist')], cwd=cls.source)
        archive, = (cls.base / 'dist').glob('*.tar.gz')
        cls.run_checked([sys.executable, '-m', 'pip', '--disable-pip-version-check',
                         'wheel', '--no-build-isolation', '--no-deps',
                         '--wheel-dir', str(cls.base / 'dist'), str(archive)])
        cls.wheel, = (cls.base / 'dist').glob('*.whl')
        cls.environment = cls.base / 'environment'
        # Runtime dependencies come from the test runner's environment; the
        # project itself must be installed solely from the freshly built wheel.
        venv.EnvBuilder(with_pip=True, system_site_packages=True).create(cls.environment)
        cls.python = (cls.environment / ('Scripts/python.exe' if os.name == 'nt'
                                         else 'bin/python'))
        cls.run_checked([str(cls.python), '-I', '-m', 'pip', '--disable-pip-version-check',
                         'install', '--no-deps', '--ignore-installed', str(cls.wheel)])
        shutil.copyfile(ROOT / 'examples/requests/internal-production.yaml',
                        cls.work / 'request.yaml')
        # Even the build tree is gone before any installed runtime is exercised.
        shutil.rmtree(cls.source)

    @classmethod
    def run_checked(cls, command, *, cwd=None):
        result = subprocess.run(command, cwd=cwd or cls.work, env=cls.env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                timeout=120)
        if result.returncode:
            raise AssertionError(f'{command!r} failed ({result.returncode}):\n{result.stdout}')
        return result.stdout

    def probe(self, source):
        return json.loads(self.run_checked([str(self.python), '-I', '-c', source]))

    def test_wheel_owns_all_data_without_shared_top_level_directories(self):
        with zipfile.ZipFile(self.wheel) as wheel:
            members = wheel.namelist()
        for name in members:
            self.assertNotIn(name.split('/')[0],
                             {'profiles', 'policy', 'sources', 'terraform',
                              'ansible', 'config', 'docs'})
        for name in ('profiles/security/catalog.json', 'policy/rules/standards.json',
                     'sources/capabilities/platform_registry.json',
                     'terraform/catalog.json', 'ansible/catalog.json',
                     'config/toolchain.json'):
            self.assertIn('hosting_resources/_assets/' + name, members)

    def test_installed_planning_loads_owner_modules_and_all_resources(self):
        result = self.probe('''
import json, sys
from pathlib import Path
before = list(sys.path)
from hosting_resources import RESOURCE_ROOT, SOURCE_ROOT
from provisioner import repository
from provisioner.cli.main import dispatch
from provisioner.inventory.model import fixture
from provisioner.policy.standards import load_rules
from provisioner.profiles.loader import load_catalogs
from provisioner.schemas.registry import load_schema
from provisioner.portability.artifacts import load as artifact_registry
from provisioner.compiler.artifacts import assert_output_path
from provisioner.domain.errors import ProvisioningError
from tools.terraform_catalog import entries
code, plan = dispatch(['plan', 'request.yaml'])
registry = repository.capability_registry()
eligible, blockers = repository.capability_eligible(registry, 'openstack', {'ipv4'})
declarations = repository.declared_contracts()
assert all(repository.native_variables(platform, phase)
           for platform in ('nutanix', 'vmware', 'openstack')
           for phase in ('domains', 'workloads'))
assert repository.reservation_records()['records'] == []
assert repository.ipam_allocation_records()['records'] == []
assert repository.dns_registration_records()['records'] == []
assert load_schema('workload-security-domain')
assert artifact_registry()['artifacts']
assert load_rules() and len(load_catalogs().families) == 10
assert fixture().status == 'FIXTURE_NOT_AUTHORITATIVE'
assert declarations['reservation_intent']['format']
assert entries()
assert code == 0, plan
assert SOURCE_ROOT is None
assert RESOURCE_ROOT.is_relative_to(Path(sys.prefix))
assert repository.reviewed_source('request.yaml') == str(Path('request.yaml').resolve())
assert repository.reviewed_source('<memory>') == '<memory>'
assert sys.path == before, (before, sys.path)
assert repository.source_commit()['status'] == 'BLOCKED_NO_CURRENT_CHECKOUT'
for path in (RESOURCE_ROOT / 'generated', Path(repository.__file__).parent / 'generated'):
    try:
        assert_output_path(path)
    except ProvisioningError as error:
        assert error.code == 'OUTPUT_PATH_NOT_PRIVATE'
    else:
        raise AssertionError('Generated output accepted inside the installation')
print(json.dumps({'status': plan['status'], 'native_contact': plan['native_contact'],
                  'capability_eligible': eligible, 'blockers': blockers}))
''')
        self.assertFalse(result['native_contact'])
        self.assertFalse(result['capability_eligible'])
        self.assertTrue(result['blockers'])

    def test_missing_packaged_asset_cannot_resolve_a_shared_directory(self):
        result = self.probe('''
import json
from pathlib import Path
import hosting_resources
from provisioner.repository import asset_path, document_exists
root = hosting_resources.RESOURCE_ROOT
target = root / 'config/toolchain.json'
shared = Path(hosting_resources.__file__).resolve().parent.parent / 'config/toolchain.json'
saved = target.read_bytes()
shared.parent.mkdir(exist_ok=True)
shared.write_bytes(saved)
target.unlink()
try:
    assert asset_path('config/toolchain.json') == target
    assert not asset_path('config/toolchain.json').exists()
    assert not document_exists('../config/toolchain.json')
    for value in ('../config/toolchain.json', '/config/toolchain.json',
                  'config\\\\toolchain.json', 'C:/config/toolchain.json',
                  './config/toolchain.json', 'config//toolchain.json'):
        try:
            asset_path(value)
        except ValueError:
            continue
        raise AssertionError('Unsafe resource path accepted: ' + value)
    print(json.dumps({'refused_fallback': True}))
finally:
    target.write_bytes(saved)
    shared.unlink()
    shared.parent.rmdir()
''')
        self.assertTrue(result['refused_fallback'])


if __name__ == '__main__':
    unittest.main()
