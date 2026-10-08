#!/usr/bin/env python3
"""Retain E1 commissioning/preflight observations; do not run a native campaign."""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    paths = subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines()
    prefixes = ('services/lifecycle/src/', 'services/lifecycle/tests/', 'scripts/p07/',
                '.github/workflows/p07-', 'release/p07-native-inputs.json',
                'services/lifecycle/pyproject.toml', 'services/lifecycle/uv.lock')
    selected = [p for p in paths if p.startswith(prefixes) and (ROOT / p).is_file()]
    report = {
        'source_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'observed_at': datetime.now(timezone.utc).isoformat(),
        'environment': platform.platform(),
        'evidence_level': 'E1',
        'native_platforms_tested': [],
        'native_write_authorized': False,
        'source_bindings': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in selected},
        'commands': [],
        'limitations': [
            'Synthetic input metadata and native operation plans; no installed OpenStack execution.',
            'No owner authentication, native service/restore/policy/revocation/retirement observation.',
            'The separate P06 regression campaign owns PostgreSQL/Temporal/browser evidence.',
        ],
    }
    commands = [
        (['uv', 'sync', '--locked'], (0,)),
        (['uv', 'run', '--frozen', 'ruff', 'check', 'src', 'tests'], (0,)),
        (['uv', 'run', '--frozen', 'ruff', 'format', '--check', 'src', 'tests'], (0,)),
        (['uv', 'run', '--frozen', 'mypy', 'src', 'tests'], (0,)),
        (['uv', 'run', '--frozen', 'pytest', 'tests/test_commissioning.py',
          'tests/test_native_preflight.py', '-q', '--junitxml=' + str(output / 'preparation.xml')], (0,)),
        (['uv', 'run', '--frozen', 'python', '-m', 'lifecycle.bootstrap.commissioning',
          '--input', str(ROOT / 'release/p07-native-inputs.json'), '--require-complete'], (0, 2)),
    ]
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    for index, (command, expected) in enumerate(commands):
        run = subprocess.run(command, cwd=ROOT / 'services/lifecycle', env=env,
                             capture_output=True, text=True, timeout=600)
        log = run.stdout + run.stderr
        path = output / f'{index:02d}.log'
        path.write_text(log)
        passed = run.returncode in expected
        if index == len(commands) - 1 and passed:
            try:
                readiness = json.loads(run.stdout)
                passed = (readiness['record_valid'] is True
                          and readiness['native_write_authorized'] is False
                          and readiness['native_qualification_established'] is False
                          and run.returncode == (0 if readiness['record_complete'] else 2))
                report['commissioning_result'] = readiness
            except (ValueError, KeyError, TypeError):
                passed = False
        report['commands'].append({'command': command, 'exit_code': run.returncode,
                                   'expected_exit_codes': list(expected), 'passed': passed,
                                   'log': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        print(f'{index:02d}: {"PASS" if passed else "FAIL"}', flush=True)
    report['result'] = 'PASSED' if all(c['passed'] for c in report['commands']) else 'FAILED'
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return 0 if report['result'] == 'PASSED' else 1


if __name__ == '__main__':
    sys.exit(main())
