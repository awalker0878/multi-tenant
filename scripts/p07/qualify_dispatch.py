#!/usr/bin/env python3
"""Retain native orchestration evidence on real Temporal/TLS and disposable PostgreSQL."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/p06'))
from temporal_fixture import TemporalFixture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=True)
    private = Path(tempfile.mkdtemp(prefix='p07-native-dispatch-')); private.chmod(0o700)
    redactions = []
    fixture = None
    paths = subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines()
    prefixes = ('services/lifecycle/', 'workers/lifecycle/', 'contracts/openapi/lifecycle-native-',
                'contracts/openapi/worker-native-', 'contracts/fixtures/lifecycle/',
                'scripts/p07/', 'scripts/p06/temporal_', 'scripts/p01/stateful/runtime.py',
                'scripts/p01/local_runtime.py', 'deploy/fixtures/stateful/', 'deploy/dependencies/stateful/inputs.lock.json',
                '.github/workflows/p07-native-readiness.yml')
    report = {
        'source_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'observed_at': datetime.now(timezone.utc).isoformat(), 'environment': platform.platform(),
        'evidence_level': 'E2', 'native_platforms_tested': [], 'native_write_authorized': False,
        'source_bindings': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths if p.startswith(prefixes)},
        'commands': [], 'limitations': [
            'Actual Temporal/TLS/JWT, internal effect/boundary TLS and separate worker PostgreSQL journal.',
            'Native authority, native API requests, provider observations and other stage effects remain synthetic.',
            'No provider, guest, enterprise service, native fence, Q05/Q06 or receiving acceptance is established.',
        ],
    }
    env = {k: v for k, v in os.environ.items() if not k.startswith(('OS_', 'TF_')) and k != 'PYTHONPATH'}
    env['PYTHONPATH'] = ':'.join(str(ROOT / p) for p in ['services/lifecycle/src', 'services/lifecycle/tests', 'workers/lifecycle/src'])
    env['P05_POSTGRES_BIN'] = os.environ.get('P07_POSTGRES_BIN', '')
    env['P07_DISPATCH_OBSERVATIONS'] = str(out / 'observations.json')

    def run(argv, label, env=None):
        result = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
        log = result.stdout + result.stderr
        for secret in sorted(redactions, key=len, reverse=True):
            log = log.replace(secret, '[REDACTED]')
        name = f'{len(report["commands"]):02d}-{label}.log'
        (out / name).write_text(log)
        report['commands'].append({'label': label, 'command': argv, 'exit_code': result.returncode,
                                   'log': name, 'sha256': hashlib.sha256(log.encode()).hexdigest()})
        print(label, result.returncode, flush=True)
        if result.returncode:
            raise RuntimeError(label + '_failed')
        return result.stdout

    try:
        if not env['P05_POSTGRES_BIN']:
            raise RuntimeError('P07_POSTGRES_BIN_required')
        run(['uv', 'sync', '--project', 'services/lifecycle', '--locked'], 'locked-lifecycle-install', env=env)
        fixture = TemporalFixture(ROOT, private, run, redactions)
        report['images'] = fixture.images
        fixture.start(); env.update(fixture.environment)
        python = str(ROOT / 'services/lifecycle/.venv/bin/python')
        run([python, 'scripts/p06/temporal_process.py', 'initialize'], 'native-temporal-namespace', env=env)
        run([python, '-m', 'pytest', 'scripts/p07/test_native_temporal.py', '-q', '--junitxml=' + str(out / 'temporal.xml')], 'native-orchestration-and-replay', env=env)
        suites = ElementTree.parse(out / 'temporal.xml')
        if any(int(s.get(k, 0)) for s in suites.iter('testsuite') for k in ('skipped', 'errors', 'failures')):
            raise RuntimeError('native_temporal_tests_not_passed')
        measured = json.loads((out / 'observations.json').read_text())
        if not measured['checks'] or len(measured['histories']) != 6:
            raise RuntimeError('native_temporal_observations_incomplete')
        if any(not (out / ('history-' + row['workflow_id'] + '.json')).is_file() for row in measured['histories']):
            raise RuntimeError('native_temporal_histories_not_retained')
        report['check_count'] = len(measured['checks'])
        report['replayed_histories'] = len(measured['histories'])
    except Exception as error:
        report['qualification_error'] = type(error).__name__ + ': ' + str(error)
    finally:
        if fixture:
            try:
                fixture.close()
            except Exception:
                report['cleanup_error'] = 'temporal_fixture_cleanup_failed'
        shutil.rmtree(private)
    report['artifacts'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file() and p.name != 'report.json'}
    report['result'] = 'PASSED' if report['commands'] and not any(k.endswith('_error') for k in report) and all(c['exit_code'] == 0 for c in report['commands']) else 'FAILED'
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return 0 if report['result'] == 'PASSED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
