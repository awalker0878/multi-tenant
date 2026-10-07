#!/usr/bin/env python3
"""Retain P07 adapter component evidence. Synthetic providers are not E3 qualification."""

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
    selected = [p for p in paths if p.startswith(('workers/lifecycle/', 'services/lifecycle/', 'contracts/openapi/lifecycle-native-', 'contracts/openapi/worker-native-', 'contracts/fixtures/lifecycle/', 'scripts/p07/', '.github/workflows/p07-'))
                and '/verification/' not in p and (ROOT / p).is_file()]
    report = {
        'source_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'observed_at': datetime.now(timezone.utc).isoformat(),
        'environment': platform.platform(), 'evidence_level': 'E2',
        'native_platforms_tested': [], 'native_write_authorized': False,
        'source_bindings': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in selected},
        'commands': [], 'limitations': [
            'Real PostgreSQL/TLS/process boundaries with synthetic identities and native responses.',
            'Native API request and export/import components against synthetic HTTPS peers; no installed-platform qualification.',
            'No current native authority integration, per-provider request fencing, guest/service activation or retirement campaign.',
            'An adapter heartbeat does not establish immediate provider-side revocation or stale-worker exclusion.',
        ],
    }
    env = {k: v for k, v in os.environ.items() if not k.startswith(('OS_', 'TF_')) and k != 'PYTHONPATH'}
    env['CHECKPOINT_DISABLE'] = '1'

    def command(cwd, argv):
        index = len(report['commands'])
        run = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=600)
        log = output / f'{index:02d}.log'
        log.write_text(run.stdout + run.stderr)
        report['commands'].append({'command': argv, 'exit_code': run.returncode, 'log': log.name,
                                   'sha256': hashlib.sha256(log.read_bytes()).hexdigest()})
        print(f'{index:02d}: {"PASS" if run.returncode == 0 else "FAIL"}', flush=True)
        return run.returncode == 0

    try:
        if not env.get('P07_POSTGRES_BIN'):
            raise RuntimeError('P07_POSTGRES_BIN is required; skipped persistence tests cannot qualify the worker')
        command(ROOT / 'scripts/p01/contracts', ['uv', 'sync', '--locked'])
        command(ROOT / 'scripts/p01/contracts', ['uv', 'run', '--frozen', 'python', str(ROOT / 'scripts/p07/check_native_contract.py')])
        env['P05_POSTGRES_BIN'] = env['P07_POSTGRES_BIN']
        service = ROOT / 'services/lifecycle'
        for argv in (
            ['uv', 'sync', '--locked', '--group', 'build'],
            ['uv', 'run', '--frozen', 'ruff', 'check', 'src', 'tests'],
            ['uv', 'run', '--frozen', 'ruff', 'format', '--check', 'src', 'tests'],
            ['uv', 'run', '--frozen', 'mypy', 'src', 'tests'],
            ['uv', 'run', '--frozen', 'pytest', '-q', '--junitxml=' + str(output / 'lifecycle.xml')],
            ['uv', 'build', '--no-build-isolation', '--wheel'],
        ):
            command(service, argv)
        lifecycle_suites = ElementTree.parse(output / 'lifecycle.xml')
        if any(int(s.get('skipped', 0)) for s in lifecycle_suites.iter('testsuite')):
            raise RuntimeError('native workflow tests skipped')
        report['lifecycle_test_count'] = sum(int(s.get('tests', 0)) for s in lifecycle_suites.iter('testsuite'))
        component = ROOT / 'workers/lifecycle'
        commands = [
            ['uv', 'sync', '--locked', '--group', 'build'],
            ['uv', 'run', '--frozen', 'ruff', 'check', 'src', 'tests'],
            ['uv', 'run', '--frozen', 'ruff', 'format', '--check', 'src', 'tests'],
            ['uv', 'run', '--frozen', 'mypy', 'src', 'tests'],
            ['uv', 'run', '--frozen', 'pytest', '-q', '--junitxml=' + str(output / 'native.xml')],
            ['uv', 'build', '--no-build-isolation', '--wheel'],
        ]
        for argv in commands:
            command(component, argv)
        suites = ElementTree.parse(output / 'native.xml')
        if any(int(s.get('skipped', 0)) for s in suites.iter('testsuite')):
            raise RuntimeError('native adapter tests skipped')
        report['test_count'] = sum(int(s.get('tests', 0)) for s in suites.iter('testsuite'))
    except Exception as error:
        report['qualification_error'] = type(error).__name__ + ': ' + str(error)
    report['result'] = 'PASSED' if report['commands'] and not report.get('qualification_error') and all(
        c['exit_code'] == 0 for c in report['commands']) else 'FAILED'
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return 0 if report['result'] == 'PASSED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
