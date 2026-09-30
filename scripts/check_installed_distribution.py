#!/usr/bin/env python3
"""Build the wheel and exercise its installed runtime outside this checkout.

The child interpreter uses isolated mode so an import cannot silently resolve to
the source directory or a PYTHONPATH entry. Fixture input is copied to an unrelated
temporary directory; no native platform is contacted.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CHILD = r'''
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import sys

site = Path(sys.argv[1]).resolve()
checkout = Path(sys.argv[2]).resolve()
request = Path(sys.argv[3]).resolve()
assert Path.cwd() != checkout and not Path.cwd().is_relative_to(checkout)
assert not any(Path(item).resolve() == checkout for item in sys.path if item)
sys.path.insert(0, str(site))

# Compiler execution must work without importing the legacy owner packages.
import importlib.abc
class NoLegacyCompilerImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'tools', 'scripts'}:
            raise AssertionError('Compiler imported legacy owner: '+fullname)
        return None

blocker = NoLegacyCompilerImports()
sys.meta_path.insert(0, blocker)
compiler_path = list(sys.path)
try:
    import provisioner
    from provisioner.compiler import components, wsd
    from provisioner.cli import application_drafts as draft_client
    import argparse
    client_parser = argparse.ArgumentParser()
    draft_client.install_parser(client_parser.add_subparsers(dest='resource', required=True))
    client_args = client_parser.parse_args(['application-drafts', 'list', '--environment', 'env-1'])
    assert draft_client.request.__module__ == draft_client.__name__
    assert draft_client.request(client_args, lambda value: value) == (
        'GET', '/v1/environments/env-1/application-drafts', {'limit': 50}, None)
    review_args = client_parser.parse_args(['application-drafts', 'review', '--environment', 'env-1',
        '--id', 'app-1', '--revision', '1', '--record-digest', 'a'*64])
    assert draft_client.request(review_args, lambda value: value) == (
        'GET', '/v1/environments/env-1/application-drafts/app-1/review', {'revision': 1}, None)
    from provisioner.controlplane.discovery import collector_runtime, collector_settings
    from provisioner.controlplane.discovery.adapters import collector_config
    from provisioner.controlplane.discovery import native_credentials, native_https, publication, publication_https, application_drafts, grouping, application_review, application_reviews
    from provisioner.controlplane.discovery.adapters import vmware_credentials, vmware_https, ahv_credentials, ahv_https, openstack_credentials, openstack_https
    assert vmware_credentials.SignedFileVmwareCredentialSource.__module__ == vmware_credentials.__name__
    assert not hasattr(native_credentials, 'SignedFileVmwareCredentialSource')
    assert not hasattr(native_credentials, 'VmwareSessionMaterial')
    assert not hasattr(native_credentials, 'selection_digest')
    assert ahv_credentials.SignedFileAhvCredentialSource.__module__ == ahv_credentials.__name__
    assert not hasattr(native_credentials, 'SignedFileAhvCredentialSource')
    assert ahv_https.read_json is native_https.read_json
    assert openstack_credentials.SignedFileOpenStackCredentialSource.__module__ == openstack_credentials.__name__
    assert openstack_https.OpenStackHttpsTransport.__module__ == openstack_https.__name__
    assert not hasattr(native_credentials, 'SignedFileOpenStackCredentialSource')
    assert openstack_https.read_json is native_https.read_json
    assert vmware_https.read_json is native_https.read_json
    assert application_drafts.ApplicationDraftRepository.__module__ == application_drafts.__name__
    assert application_review.parse_review.__module__ == application_review.__name__
    assert application_reviews.ApplicationReviewService.__module__ == application_reviews.__name__
    assert grouping.validate_draft.__module__ == grouping.__name__
    assert publication.stage_submission.__module__ == publication.__name__
    assert publication.PrivateDiscoveryOutbox.__module__ == publication.__name__
    assert callable(publication.PrivateDiscoveryOutbox.for_campaign)
    assert publication_https.DiscoveryHttpsPublisher.__module__ == publication_https.__name__
    assert collector_runtime.main.__module__ == collector_runtime.__name__
    assert collector_settings.DiscoveryCollectorSettings.__module__ == collector_settings.__name__
    assert collector_config.create_native_collector.__module__ == collector_config.__name__
    for platform in components.COMPONENTS:
        for phase in ('domains', 'workloads'):
            assert wsd.native_variables(platform, phase)
        environment = json.loads((request.parent / 'environments' /
                                  (platform+'.json.example')).read_text())
        inputs, summary = wsd.compile_environment(environment)
        assert inputs and summary['native_contact'] is False
        assert summary['status'] == 'DRAFT_DISABLED_NOT_AUTHORIZED'
        assert all(value['allow_restricted_build'] is False for value in inputs.values())
    assert sys.path == compiler_path
finally:
    sys.meta_path.remove(blocker)
assert importlib.util.find_spec('tools.compile_wsd') is None
import scripts
import tools
import hosting_resources
from provisioner import repository
from provisioner.qualification import campaign, native, provenance, registry, target_selection
from provisioner.cli.main import main
from provisioner.domain.enterprise_records import validate_record
from provisioner.controlplane.discovery import (adoption, assessment, grouping,
                                                 ingest, model, persistence, routes,
                                                 runtime, trust, witness)
from provisioner.controlplane.discovery.adapters import (ahv, openstack, vmware,
                                                          vmware_rest)

for module in (provisioner, draft_client, application_review, application_reviews, application_drafts, collector_runtime, collector_settings, collector_config, publication, publication_https, components, wsd, native_credentials, native_https, openstack_credentials, openstack_https, ahv_credentials, ahv_https, vmware_credentials, vmware_https, scripts, tools, hosting_resources, campaign, native, provenance, registry, target_selection, adoption, ahv, assessment, grouping,
               ingest, model, openstack, persistence, routes, runtime, trust,
               vmware, vmware_rest, witness):
    assert Path(module.__file__).resolve().is_relative_to(site), module.__file__
for relative in (
    'provisioner/schemas/v1/enterprise-record.schema.json',
    'provisioner/controlplane/persistence/migrations/0001_controlplane.sql',
    'provisioner/controlplane/persistence/migrations/0002_jobs.sql',
    'provisioner/controlplane/persistence/migrations/0003_authority.sql',
    'provisioner/controlplane/persistence/migrations/0004_worker_grants.sql',
    'provisioner/controlplane/persistence/migrations/0005_native_registry.sql',
    'provisioner/controlplane/persistence/migrations/0006_evidence.sql',
    'provisioner/controlplane/persistence/migrations/0007_worker_certificate_rotation.sql',
    'provisioner/controlplane/persistence/migrations/0008_audit_chain.sql',
    'provisioner/controlplane/persistence/migrations/0009_directory.sql',
    'provisioner/controlplane/persistence/migrations/0010_workflow_run_binding.sql',
    'provisioner/controlplane/persistence/migrations/0011_job_gate_lock.sql',
    'provisioner/controlplane/persistence/migrations/0012_directory_audit_binding.sql',
    'provisioner/controlplane/persistence/migrations/0013_environment_registrations.sql',
    'provisioner/controlplane/persistence/migrations/0014_worker_read_lock.sql',
    'provisioner/controlplane/persistence/migrations/0015_worker_directory_audit_actions.sql',
    'provisioner/controlplane/persistence/migrations/0016_site_worker_role_binding.sql',
    'provisioner/controlplane/persistence/migrations/0017_site_lock_guards.sql',
    'provisioner/controlplane/persistence/migrations/0018_site_role_superuser_classification.sql',
    'provisioner/controlplane/persistence/migrations/0019_discovery_inventory.sql',
    'provisioner/controlplane/persistence/migrations/0021_application_drafts.sql',
    'provisioner/controlplane/persistence/migrations/0022_application_review_evidence.sql',
    'provisioner/controlplane/api/portal/index.html',
    'provisioner/controlplane/api/portal/app.js',
    'provisioner/controlplane/api/portal/application_drafts.js',
    'provisioner/controlplane/api/portal/style.css',
):
    assert (site / relative).is_file(), relative
for relative in ('profiles/security/catalog.json', 'policy/rules/standards.json',
                 'sources/capabilities/platform_registry.json', 'terraform/catalog.json',
                 'ansible/catalog.json', 'config/toolchain.json'):
    asset = repository.asset_path(relative).resolve()
    assert asset.is_file() and asset.is_relative_to(site / 'hosting_resources' / '_assets'), asset
assert hosting_resources.SOURCE_ROOT is None
assert importlib.util.find_spec('scripts.check_platform_capabilities') is None
assert importlib.util.find_spec('scripts.check_platform_qualification') is None
assert importlib.util.find_spec('scripts.check_version_source_provenance') is None
assert importlib.util.find_spec('scripts.check_qualification_campaign_assurance') is None
assert importlib.util.find_spec('scripts.check_target_selection_assurance') is None
assert registry.validate(registry.load())['capabilities_per_platform'] == len(registry.CAPABILITIES)
assert callable(validate_record)

distribution = next(d for d in importlib.metadata.distributions(path=[str(site)])
                    if d.metadata['Name'] == 'hosting-provisioner')
assert any(e.name == 'hosting' and e.value == 'provisioner.cli.main:main'
           for e in distribution.entry_points)
assert any(e.name == 'hosting-operator' and e.value == 'provisioner.cli.operator:main'
           for e in distribution.entry_points)
assert any(e.name == 'hosting-api' and e.value == 'provisioner.controlplane.api.server:main'
           for e in distribution.entry_points)
assert any(e.name == 'hosting-evidence' and
           e.value == 'provisioner.controlplane.evidence.runtime:main'
           for e in distribution.entry_points)
assert any(e.name == 'hosting-site-worker' and
           e.value == 'provisioner.controlplane.worker.runtime:main'
           for e in distribution.entry_points)
assert any(e.name == 'hosting-discovery-ingest' and
           e.value == 'provisioner.controlplane.discovery.runtime:main'
           for e in distribution.entry_points)

entry = next(e for e in distribution.entry_points if e.name == 'hosting-discovery-collect')
assert entry.value == 'provisioner.controlplane.discovery.collector_runtime:main'
assert entry.load() is collector_runtime.main
import io
from contextlib import redirect_stdout
outcome = io.StringIO()
missing_config = Path.cwd() / 'not-configured-collector.json'
assert not missing_config.exists()
with redirect_stdout(outcome):
    assert entry.load()(['publish', '--config', str(missing_config)]) == 2
assert json.loads(outcome.getvalue()) == {
    'format': 'hosting-discovery-collector-outcome/1', 'status': 'HELD', 'executionAuthorized': False}

result = main(['plan', str(request)])
for name, module in sys.modules.items():
    if name.split('.')[0] in ('provisioner', 'tools', 'scripts', 'hosting_resources'):
        path = getattr(module, '__file__', None)
        if path is not None:
            assert Path(path).resolve().is_relative_to(site), (name, path)
raise SystemExit(result)
'''


def run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    completed = subprocess.run(args, cwd=cwd, env=env, text=True,
                               capture_output=True, timeout=120)
    if completed.returncode:
        raise RuntimeError(f'Installed-wheel check failed (exit {completed.returncode}): '
                           f'{args[:4]}\nstdout:\n{completed.stdout[-8000:]}\n'
                           f'stderr:\n{completed.stderr[-8000:]}')
    return completed


def main() -> None:
    with tempfile.TemporaryDirectory(prefix='hosting-wheel-') as directory:
        scratch = Path(directory)
        archives = scratch / 'archives'
        wheels = scratch / 'wheels'
        installed = scratch / 'installed'
        foreign = scratch / 'foreign'
        source = scratch / 'source'
        archives.mkdir()
        wheels.mkdir()
        foreign.mkdir()
        request = foreign / 'request.yaml'
        shutil.copyfile(ROOT / 'examples/requests/internal-production.yaml', request)
        shutil.copytree(ROOT / 'examples/environments', foreign / 'environments')
        shutil.copytree(ROOT, source, ignore=shutil.ignore_patterns(
            '.git', '.venv', '__pycache__', '.pytest_cache', 'build', 'dist',
            '*.egg-info'))

        # Build through the source distribution to test MANIFEST.in as well as
        # the wheel: published source archives must not lose reviewed assets.
        run(sys.executable, 'setup.py', 'sdist', '--dist-dir', str(archives), cwd=source)
        source_archives = list(archives.glob('hosting_provisioner-*.tar.gz'))
        if len(source_archives) != 1:
            raise AssertionError(f'Expected one source archive, found {source_archives}')
        run(sys.executable, '-m', 'pip', 'wheel', '--no-build-isolation',
            '--no-deps', '--wheel-dir', str(wheels), str(source_archives[0]), cwd=foreign)
        built = list(wheels.glob('hosting_provisioner-*.whl'))
        if len(built) != 1:
            raise AssertionError(f'Expected one built wheel, found {built}')
        run(sys.executable, '-m', 'pip', 'install', '--no-index', '--no-deps',
            '--target', str(installed), str(built[0]), cwd=foreign)
        shutil.rmtree(source)

        completed = run(sys.executable, '-I', '-c', CHILD, str(installed),
                        str(ROOT), str(request), cwd=foreign)
        result = json.loads(completed.stdout)
        if (result.get('format') != 'hosting-plan-result/1'
                or result.get('status') != 'PLANNED_DISABLED_NOT_AUTHORIZED'
                or result.get('native_contact') is not False):
            raise AssertionError(f'Installed planning result unexpected: {result}')
        print(json.dumps({'status': 'PASSED', 'sdist': source_archives[0].name,
                          'wheel': built[0].name,
                          'plan_status': result['status'],
                          'native_contact': result['native_contact']}, sort_keys=True))


if __name__ == '__main__':
    main()
