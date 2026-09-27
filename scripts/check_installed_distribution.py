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
import json
from pathlib import Path
import sys

site = Path(sys.argv[1]).resolve()
checkout = Path(sys.argv[2]).resolve()
request = Path(sys.argv[3]).resolve()
assert Path.cwd() != checkout and not Path.cwd().is_relative_to(checkout)
assert not any(Path(item).resolve() == checkout for item in sys.path if item)
sys.path.insert(0, str(site))

import provisioner
import scripts
import tools
from provisioner import repository
from provisioner.cli.main import main
from provisioner.domain.enterprise_records import validate_record

for module in (provisioner, scripts, tools):
    assert Path(module.__file__).resolve().is_relative_to(site), module.__file__
for relative in (
    'provisioner/schemas/v1/enterprise-record.schema.json',
    'profiles/security/catalog.json', 'policy/rules/standards.json',
    'sources/capabilities/platform_registry.json', 'terraform/catalog.json',
):
    assert (site / relative).is_file(), relative
for relative in ('ansible/catalog.json', 'config/toolchain.json'):
    asset = repository.asset_path(relative).resolve()
    assert asset.is_file() and asset.is_relative_to(site / 'provisioner' / '_assets'), asset
assert callable(validate_record)

distribution = next(d for d in importlib.metadata.distributions(path=[str(site)])
                    if d.metadata['Name'] == 'hosting-provisioner')
assert any(e.name == 'hosting' and e.value == 'provisioner.cli.main:main'
           for e in distribution.entry_points)

result = main(['plan', str(request)])
for name, module in sys.modules.items():
    if name.split('.')[0] in ('provisioner', 'tools', 'scripts'):
        path = getattr(module, '__file__', None)
        if path is not None:
            assert Path(path).resolve().is_relative_to(site), (name, path)
raise SystemExit(result)
'''


def run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    return subprocess.run(args, cwd=cwd, env=env, text=True,
                          capture_output=True, check=True)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix='hosting-wheel-') as directory:
        scratch = Path(directory)
        wheels = scratch / 'wheels'
        installed = scratch / 'installed'
        foreign = scratch / 'foreign'
        wheels.mkdir()
        foreign.mkdir()
        request = foreign / 'request.yaml'
        shutil.copyfile(ROOT / 'examples/requests/internal-production.yaml', request)

        run(sys.executable, '-m', 'pip', 'wheel', '--no-build-isolation',
            '--no-deps', '--wheel-dir', str(wheels), str(ROOT), cwd=foreign)
        built = list(wheels.glob('hosting_provisioner-*.whl'))
        if len(built) != 1:
            raise AssertionError(f'Expected one built wheel, found {built}')
        run(sys.executable, '-m', 'pip', 'install', '--no-index', '--no-deps',
            '--target', str(installed), str(built[0]), cwd=foreign)

        completed = run(sys.executable, '-I', '-c', CHILD, str(installed),
                        str(ROOT), str(request), cwd=foreign)
        result = json.loads(completed.stdout)
        if (result.get('format') != 'hosting-plan-result/1'
                or result.get('status') != 'PLANNED_DISABLED_NOT_AUTHORIZED'
                or result.get('native_contact') is not False):
            raise AssertionError(f'Installed planning result unexpected: {result}')
        print(json.dumps({'status': 'PASSED', 'wheel': built[0].name,
                          'plan_status': result['status'],
                          'native_contact': result['native_contact']}, sort_keys=True))


if __name__ == '__main__':
    main()
