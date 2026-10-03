"""Build and exercise the real wheel with no checkout on the import path.

These tests intentionally use a fresh virtual environment and an unrelated
working directory. Import-only tests in the source tree cannot detect missing
wheel resources or accidental resolution of files at site-packages root.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import site
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
        # Destructive-output regressions use only this disposable source copy.
        cls.unsafe_build_results = []
        protected = {name: (cls.source / name).read_bytes() for name in
                     ('setup.py', 'provisioner/execution/terraform_catalog.py', 'provisioner/execution/source_integrity.py', 'terraform/catalog.json')}
        for output in (cls.source, cls.base, cls.source / 'provisioner'):
            result = subprocess.run([sys.executable, 'setup.py', 'build_py', '--build-lib', str(output)],
                cwd=cls.source, env=cls.env, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, timeout=120)
            if (result.returncode == 0 or any((cls.source / name).read_bytes() != raw
                                            for name, raw in protected.items())):
                raise AssertionError('Unsafe build destination was not refused before source mutation')
            cls.unsafe_build_results.append(result.stdout)
        cls.staging = cls.base / 'incremental-build'
        cls.retired = ('profiles', 'policy', 'sources', 'terraform', 'ansible',
                       'config', 'docs', 'provisioner/_assets')
        for relative in (*cls.retired, 'hosting_resources/_assets/obsolete'):
            path = cls.staging / relative / 'stale.json'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{}', encoding='utf-8')
        cls.retired_python = ('tools/terraform_catalog.py', 'tools/terraform_catalog.pyc',
                              'tools/__pycache__/terraform_catalog.cpython-313.pyc',
                              'tools/check_release.py', 'tools/check_release.pyc',
                              'tools/__pycache__/check_release.cpython-313.pyc',
                              'scripts/check_reservation_records.py', 'scripts/check_reservation_records.pyc',
                              'scripts/__pycache__/check_reservation_records.cpython-313.pyc')
        for relative in cls.retired_python:
            path = cls.staging / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'retired owner must not be packaged')
        cls.run_checked([sys.executable, 'setup.py', 'build_py', '--build-lib',
                         str(cls.staging)], cwd=cls.source)
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
        # A nested venv's --system-site-packages points at the base interpreter,
        # not an outer venv such as CI/test tooling.  Add only dependency roots
        # that do not already contain this project, so isolated child imports can
        # see PyYAML/httpx/etc. without resolving provisioner from the checkout.
        venv.EnvBuilder(with_pip=True, system_site_packages=True).create(cls.environment)
        cls.python = (cls.environment / ('Scripts/python.exe' if os.name == 'nt'
                                         else 'bin/python'))
        dependency_roots = []
        for candidate in [*site.getsitepackages(), site.getusersitepackages()]:
            root = Path(candidate).resolve()
            if (root.is_dir() and root not in dependency_roots
                    and not (root / 'provisioner').exists()
                    and not (root / 'hosting_resources').exists()):
                dependency_roots.append(root)
        nested_sites = json.loads(subprocess.check_output(
            [str(cls.python), '-I', '-c',
             'import json,site; print(json.dumps(site.getsitepackages()))'],
            text=True, env=cls.env, timeout=30))
        dependency_link = Path(nested_sites[0]) / 'hosting-test-runner-dependencies.pth'
        dependency_link.write_text(''.join(str(root) + '\n' for root in dependency_roots),
                                   encoding='utf-8')
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
        self.assertIn('provisioner/execution/terraform_catalog.py', members)
        self.assertIn('provisioner/execution/source_integrity.py', members)
        self.assertIn('provisioner/allocations/reservation_evidence.py', members)
        self.assertFalse(any(name.startswith('scripts/check_reservation_records.') for name in members))
        self.assertFalse(any(name.startswith('tools/terraform_catalog.') for name in members))
        self.assertFalse(any(name.startswith('tools/check_release.') for name in members))
        for name in members:
            self.assertNotIn(name.split('/')[0],
                             {'profiles', 'policy', 'sources', 'terraform',
                              'ansible', 'config', 'docs'})
        for name in ('profiles/security/catalog.json', 'policy/rules/standards.json',
                     'sources/capabilities/platform_registry.json',
                     'terraform/catalog.json', 'ansible/catalog.json',
                     'config/toolchain.json'):
            self.assertIn('hosting_resources/_assets/' + name, members)

    def test_incremental_build_removes_retired_and_deleted_resources(self):
        for relative in (*self.retired, *self.retired_python):
            self.assertFalse((self.staging / relative).exists(), relative)
        self.assertFalse((self.staging / 'hosting_resources/_assets/obsolete').exists())
        self.assertTrue((self.staging / 'hosting_resources/_assets/terraform/catalog.json').is_file())

    def test_build_refuses_source_ancestor_and_package_destinations(self):
        self.assertEqual(len(self.unsafe_build_results), 3)
        for result in self.unsafe_build_results:
            self.assertIn('Runtime build output overlaps source inputs', result)

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
from provisioner.execution.terraform_catalog import entries
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

    def test_offline_owner_signing_runs_from_the_installed_distribution(self):
        from datetime import datetime, timezone
        from tests.provisioning.discovery.test_application_review import stored_fixture, OwnerFixture
        from tests.provisioning.discovery.test_owner_signing import fixture_files, prepare_args, sign_args
        from provisioner.controlplane.discovery.assessment_inputs import parse_evidence
        # Only the parent builds synthetic inputs. The installed child cannot
        # import tests or the checkout and does not connect to a native system.
        stored, _ = stored_fixture()
        with tempfile.TemporaryDirectory(dir=self.work) as directory:
            root = Path(directory)
            fixture = OwnerFixture(root/'policy.json', stored, at=datetime.now(timezone.utc))
            fixture_files(root, stored, fixture)
            command = [str(self.python), '-I', '-m',
                       'provisioner.controlplane.discovery.owner_signing']
            prepared = json.loads(self.run_checked(command + prepare_args(root, stored)))
            signed = json.loads(self.run_checked(command + sign_args(root, stored)))
            self.assertEqual(prepared['evidenceDigest'], signed['evidenceDigest'])
            self.assertEqual(signed['status'], 'SIGNED_NOT_INGESTED')
            submission = json.loads((root/'signed.json').read_bytes())
            fixture.trust.verify(parse_evidence(submission['evidence']),
                                 tuple(submission['signatures']), datetime.now(timezone.utc))
            self.assertFalse(signed['executionAuthorized'])
        result = self.probe("""
import json, importlib.metadata
from provisioner.controlplane.discovery import owner_signing
entry = next(e for e in importlib.metadata.distribution('hosting-provisioner').entry_points
             if e.name == 'hosting-application-review')
assert entry.load() is owner_signing.main
print(json.dumps({'owner': entry.value}))
""")
        self.assertEqual(result['owner'], 'provisioner.controlplane.discovery.owner_signing:main')

    def test_source_integrity_is_package_owned_and_has_no_checkout_fallback(self):
        result = self.probe('''
import importlib.util, json
from pathlib import Path
from provisioner.execution import source_integrity
from hosting_resources import SOURCE_ROOT
assert SOURCE_ROOT is None
assert Path(source_integrity.__file__).is_relative_to(Path(__import__("sys").prefix))
assert importlib.util.find_spec("tools.check_release") is None
value = source_integrity.verify()
assert value["status"] == "BLOCKED_NO_CURRENT_CHECKOUT"
print(json.dumps({"owner": source_integrity.__name__, "status": value["status"]}))
''')
        self.assertEqual(result['owner'], 'provisioner.execution.source_integrity')
        self.assertEqual(result['status'], 'BLOCKED_NO_CURRENT_CHECKOUT')

    def test_catalog_is_independent_of_checkout_tools_and_working_directory(self):
        result = self.probe('''
import importlib.abc, importlib.util, json, sys
from pathlib import Path
before = list(sys.path)
class NoLegacy(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('tools', 'scripts'):
            raise AssertionError('Catalog reached retired dependency: ' + fullname)
blocker = NoLegacy()
sys.meta_path.insert(0, blocker)
try:
    from provisioner.execution import terraform_catalog
    from hosting_resources import SOURCE_ROOT, RESOURCE_ROOT
    rows = terraform_catalog.entries()
    assert SOURCE_ROOT is None
    assert Path(terraform_catalog.__file__).is_relative_to(Path(sys.prefix))
    assert RESOURCE_ROOT.is_relative_to(Path(sys.prefix))
    assert rows == json.loads((RESOURCE_ROOT / 'terraform/catalog.json').read_text())['entries']
    assert sys.path == before
finally:
    sys.meta_path.remove(blocker)
assert importlib.util.find_spec('tools.terraform_catalog') is None
assert importlib.util.find_spec('tools.check_release') is None
print(json.dumps({'entries': len(rows), 'legacyImports': False, 'nativeContact': False}))
''')
        self.assertGreater(result['entries'], 0)
        self.assertFalse(result['legacyImports'])
        self.assertFalse(result['nativeContact'])

    def test_reservation_evidence_runs_without_legacy_imports_or_checkout(self):
        result = self.probe('''
import importlib.abc, importlib.util, json, os, sys, tempfile
from pathlib import Path
before = list(sys.path)
class NoLegacy(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('tools', 'scripts'):
            raise AssertionError('Reservation evidence reached a legacy owner: ' + fullname)
blocker = NoLegacy()
sys.meta_path.insert(0, blocker)
try:
    from hosting_resources import RESOURCE_ROOT, SOURCE_ROOT
    from provisioner import repository
    from provisioner.allocations import reservation_evidence as records
    assert SOURCE_ROOT is None
    assert Path(records.__file__).is_relative_to(Path(sys.prefix))
    assert records.INDEX.is_relative_to(RESOURCE_ROOT)
    original = records.INDEX.read_bytes()
    with tempfile.TemporaryDirectory() as directory:
        previous = Path.cwd()
        os.chdir(directory)
        try:
            forged = Path('sources/capabilities/reservation_record_index.json')
            forged.parent.mkdir(parents=True)
            forged.write_text('{"forged": true}')
            assert repository.reservation_records() == records.load()
            assert records.validate(records.load())['record_count'] == 0
            records.INDEX.unlink()
            try:
                records.load()
            except FileNotFoundError:
                pass
            else:
                raise AssertionError('Missing installed index resolved a cwd fallback')
        finally:
            records.INDEX.write_bytes(original)
            os.chdir(previous)
    assert sys.path == before
finally:
    sys.meta_path.remove(blocker)
assert importlib.util.find_spec('scripts.check_reservation_records') is None
print(json.dumps({'owner': records.load.__module__, 'legacyImports': False}))
''')
        self.assertEqual(result['owner'], 'provisioner.allocations.reservation_evidence')
        self.assertFalse(result['legacyImports'])
        report = json.loads(self.run_checked([str(self.python), '-I', '-m',
            'provisioner.allocations.reservation_evidence', '--as-of', '2026-10-02T00:00:00Z']))
        self.assertEqual(report['status'], 'PASSED_EXPORTED_RESERVATION_RECORDS')
        self.assertEqual(report['record_count'], 0)
        self.assertTrue(all(value is False for key, value in report.items() if key.startswith('may_')))

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
