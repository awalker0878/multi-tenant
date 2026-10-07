#!/usr/bin/env python3
"""Source-bound P09 conformance with real PostgreSQL/TLS and synthetic native owners."""

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
    files = subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines()
    prefixes = ('services/planning/', 'services/lifecycle/', 'workers/lifecycle/',
                'scripts/p09/', 'contracts/schemas/expansion/', 'contracts/fixtures/expansion/',
                'contracts/openapi/expansion-', '.github/workflows/p09-')
    report = {
        'source_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'observed_at': datetime.now(timezone.utc).isoformat(), 'environment': platform.platform(),
        'evidence_level': 'E2', 'native_platforms_tested': [], 'native_write_authorized': False,
        'source_bindings': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
                            for p in files if p.startswith(prefixes) and (ROOT / p).is_file()},
        'commands': [], 'suites': [], 'limitations': [
            'Synthetic owner/platform responses cannot qualify installed VMware, AHV or OpenStack.',
            'Actual tranche selection, custody, budgets, identity mapping and independent receiving are required.',
            'Native route, guest, adoption, enterprise service and HA outcomes require separate E3 campaigns.',
        ],
    }
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)

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
        if not env.get('P05_POSTGRES_BIN'):
            raise RuntimeError('P05_POSTGRES_BIN required; skipped database tests cannot pass qualification')
        env['P07_POSTGRES_BIN'] = env['P05_POSTGRES_BIN']
        # Check authored source before wheel builds create disposable build/lib copies.
        # The architecture gate intentionally does not ignore arbitrary build folders.
        command('.', ['python', 'scripts/validate_architecture.py'])
        for directory, suite in (('services/planning', 'planning'), ('services/lifecycle', 'lifecycle'), ('workers/lifecycle', 'worker')):
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
        command('services/planning', ['uv', 'run', '--frozen', 'python', str(ROOT / 'scripts/p09/check_contract.py')])
    except Exception as error:
        report['error'] = str(error)
    report['result'] = 'PASSED' if report['commands'] and not report.get('error') and all(c['exit_code'] == 0 for c in report['commands']) else 'FAILED'
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return 0 if report['result'] == 'PASSED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
