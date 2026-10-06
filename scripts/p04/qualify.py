#!/usr/bin/env python3
"""Retain exact-source P04 commands and real PostgreSQL/TLS results without credentials."""
import argparse
import hashlib
import json
import os
import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    bindings = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in paths if name and (ROOT/name).is_file() and name.startswith(('services/inventory/', 'workers/inventory/', 'scripts/p04/', 'contracts/', 'services/governance/'))}
    report = {'source_revision': source, 'environment': platform.platform(), 'evidence_level': 'E2', 'native_platforms_tested': [], 'source_bindings': bindings, 'commands': []}
    commands = []
    for component in ('services/inventory',):
        commands.extend([
            (component, ['uv', 'sync', '--locked']),
            (component, ['uv', 'run', '--frozen', 'ruff', 'check', 'src', 'tests']),
            (component, ['uv', 'run', '--frozen', 'ruff', 'format', '--check', 'src', 'tests']),
            (component, ['uv', 'run', '--frozen', 'mypy', 'src', 'tests']),
            (component, ['uv', 'run', '--frozen', 'pytest', '-q', '--junitxml='+str(out/'inventory.xml')]),
        ])
    failed = False
    for index, (component, command) in enumerate(commands):
        result = subprocess.run(command, cwd=ROOT/component, capture_output=True, text=True, env=os.environ, timeout=600)
        name = f'{index:02d}.log'
        log = result.stdout + result.stderr
        (out/name).write_text(log)
        report['commands'].append({'component': component, 'command': command, 'exit_code': result.returncode, 'log': name, 'sha256': hashlib.sha256(log.encode()).hexdigest()})
        failed |= result.returncode != 0
        print(component, command[2:4], result.returncode, flush=True)
    report['result'] = 'FAILED' if failed else 'PASSED'
    (out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    raise SystemExit(1 if failed else 0)


if __name__ == '__main__':
    main()
