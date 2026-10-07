#!/usr/bin/env python3
"""P08 software qualification; real PostgreSQL/TLS, synthetic platform/owner peers."""

import argparse
import hashlib
import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    paths = subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines()
    prefixes = ('services/lifecycle/', 'services/inventory/', 'services/planning/', 'workers/lifecycle/', 'workers/inventory/', 'apps/console/',
                'scripts/p08/', 'scripts/p04/generate_clients.py', 'contracts/schemas/inventory/', 'contracts/schemas/planning/migration-', 'contracts/openapi/inventory-v1.', 'contracts/openapi/lifecycle-migration-',
                'contracts/openapi/worker-migration-', 'contracts/openapi/planning-migration-', 'contracts/openapi/planning-v1.1.json', 'contracts/fixtures/lifecycle/migration-', 'contracts/fixtures/inventory/migration-',
                '.github/workflows/p08-')
    report = {
        'source_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'observed_at': datetime.now(timezone.utc).isoformat(), 'environment': platform.platform(),
        'evidence_level': 'E2', 'native_platforms_tested': [], 'native_write_authorized': False,
        'source_bindings': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
                            for p in paths if p.startswith(prefixes) and (ROOT / p).is_file()},
        'commands': [], 'suites': [], 'limitations': [
            'Synthetic vSphere/owner fixtures do not qualify an installed VMware/OpenStack tuple.',
            'No application dataset, guest transform, production writer fencing or native Q07 acceptance.',
            'Conversion command tests use a synthetic engine; no QEMU/bubblewrap rootfs or guest boot is qualified.',
            'Current owner/trust composition and site-specific effect integrations remain required.',
        ],
    }
    env = {k: v for k, v in os.environ.items() if not k.startswith(('OS_', 'TF_')) and k != 'PYTHONPATH'}
    env['P05_POSTGRES_BIN'] = env.get('P07_POSTGRES_BIN', '')
    env['P04_POSTGRES_BIN'] = env['P05_POSTGRES_BIN']

    def command(directory, argv):
        index = len(report['commands'])
        try:
            run = subprocess.run(argv, cwd=ROOT / directory, env=env, capture_output=True, text=True, timeout=600)
            code, data = run.returncode, run.stdout + run.stderr
        except subprocess.TimeoutExpired as error:
            code, data = 124, str(error)
        log = output / f'{index:02d}.log'
        log.write_text(data)
        report['commands'].append({'directory': directory, 'argv': argv, 'exit_code': code,
                                   'log': log.name, 'sha256': hashlib.sha256(log.read_bytes()).hexdigest()})
        print(f'{index:02d}: {"PASS" if code == 0 else "FAIL"} {directory}', flush=True)

    try:
        if not env['P05_POSTGRES_BIN']:
            raise RuntimeError('P07_POSTGRES_BIN required; no skipped database qualification')
        for directory, suite in (('services/inventory', 'inventory'), ('services/planning', 'planning'), ('services/lifecycle', 'lifecycle'), ('workers/lifecycle', 'worker'), ('workers/inventory', 'inventory-worker')):
            for argv in (['uv', 'sync', '--locked', '--group', 'build'],
                         ['uv', 'run', '--frozen', 'ruff', 'check', 'src', 'tests'],
                         ['uv', 'run', '--frozen', 'ruff', 'format', '--check', 'src', 'tests'],
                         ['uv', 'run', '--frozen', 'mypy', 'src', 'tests'],
                         ['uv', 'run', '--frozen', 'pytest', '-q', '--junitxml=' + str(output / (suite + '.xml'))],
                         ['uv', 'build', '--no-build-isolation', '--wheel']):
                command(directory, argv)
            xml = ElementTree.parse(output / (suite + '.xml'))
            totals = {k: sum(int(s.get(k, 0)) for s in xml.iter('testsuite')) for k in ('tests', 'failures', 'errors', 'skipped')}
            report['suites'].append({'name': suite, **totals})
            if totals['tests'] == 0 or any(totals[k] for k in ('failures', 'errors', 'skipped')):
                raise RuntimeError(suite + ' not fully passing')
        command('services/planning', ['uv', 'run', '--frozen', 'python', str(ROOT / 'scripts/p08/check_composition.py')])
        command('.', ['python', 'scripts/p04/generate_clients.py', '--check'])
        command('scripts/p01/contracts', ['uv', 'sync', '--locked'])
        command('scripts/p01/contracts', ['uv', 'run', '--frozen', 'python', str(ROOT / 'scripts/p08/check_contract.py')])
        command('scripts/p01/contracts', ['uv', 'run', '--frozen', 'python', str(ROOT / 'scripts/p08/check_profiles.py')])
        command('scripts/p01/contracts', ['uv', 'run', '--frozen', 'python', str(ROOT / 'scripts/p08/check_fleet.py')])
    except Exception as error:
        report['error'] = str(error)
    report['result'] = 'PASSED' if report['commands'] and not report.get('error') and all(c['exit_code'] == 0 for c in report['commands']) else 'FAILED'
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return 0 if report['result'] == 'PASSED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
