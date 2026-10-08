#!/usr/bin/env python3
"""Record clean lock installation and run the bounded contract experiment."""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--workspace', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
workspace = args.workspace.resolve()
output = args.output.resolve()
output.mkdir(parents=True, exist_ok=False)
bootstrap = output / 'bootstrap'
bootstrap.mkdir()
source = workspace / 'spikes/compatibility/contracts'
state = {'result': 'RUNNING', 'source_sha': os.environ.get('GITHUB_SHA'),
         'run_id': os.environ.get('GITHUB_RUN_ID'), 'run_attempt': os.environ.get('GITHUB_RUN_ATTEMPT'),
         'started_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'commands': [], 'source_sha256': {}}
for path in [source / 'uv.lock', source / 'package-lock.json', source / 'pyproject.toml',
             source / 'package.json', Path(__file__).resolve(), workspace / '.github/workflows/p00-contract-compatibility.yml']:
    state['source_sha256'][str(path.relative_to(workspace))] = hashlib.sha256(path.read_bytes()).hexdigest()

def save():
    (bootstrap / 'report.json').write_text(json.dumps(state, indent=2) + '\n')

def run(label, command, timeout=300):
    record = {'label': label, 'command': command, 'log': label + '.log'}
    state['commands'].append(record)
    save()
    start = time.monotonic()
    log = bootstrap / record['log']
    with log.open('wb') as stream:
        process = subprocess.Popen(command, cwd=workspace, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            record['exit_code'] = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)
            record['exit_code'] = 124
    record['duration_seconds'] = round(time.monotonic() - start, 3)
    record['log_sha256'] = hashlib.sha256(log.read_bytes()).hexdigest()
    save()
    print(f"{label}: exit {record['exit_code']}", flush=True)
    if record['exit_code']:
        print(log.read_bytes().decode('utf-8', errors='replace')[-16000:], flush=True)
        raise RuntimeError(f'{label} failed')

try:
    for label, command in [('python-version', ['python', '--version']), ('uv-version', ['uv', '--version']),
                           ('node-version', ['node', '--version']), ('npm-version', ['npm', '--version']),
                           ('php-version', ['php', '--version']), ('java-version', ['java', '-version'])]:
        run(label, command, 30)
    run('uv-clean-install', ['uv', 'sync', '--locked', '--directory', str(source)])
    run('npm-clean-install', ['npm', 'ci', '--prefix', str(source), '--ignore-scripts', '--no-audit', '--no-fund'])
    run('contract-probe', ['uv', 'run', '--locked', '--directory', str(source), 'python', 'probe.py',
                           '--results', str(output / 'evidence'), '--require-php'], 600)
    state['result'] = 'PASS'
except Exception as error:
    state['result'] = 'FAIL'
    state['failure'] = f'{type(error).__name__}: {error}'
    print(state['failure'], flush=True)
finally:
    state['completed_at'] = dt.datetime.now(dt.timezone.utc).isoformat()
    save()
raise SystemExit(0 if state['result'] == 'PASS' else 1)
