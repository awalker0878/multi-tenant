#!/usr/bin/env python3
"""Source-bound P08 review UI checks; isolated HTTP fixture, not service/native acceptance."""
import argparse
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONSOLE = ROOT / 'apps/console'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    output = parser.parse_args().output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    paths = subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines()
    report = {'source_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'observed_at': datetime.now(timezone.utc).isoformat(), 'evidence_level': 'E2', 'native_write_authorized': False,
              'source_bindings': {p: sha(ROOT/p) for p in paths if p.startswith(('apps/console/', 'scripts/p08/', 'contracts/fixtures/inventory/migration-', 'contracts/fixtures/inventory/ahv-', '.github/workflows/p08-')) and (ROOT/p).is_file()},
              'commands': [], 'limitations': ['Actual Vue/Inertia review page with isolated synthetic HTTP observations.', 'Service persistence/authority is qualified separately; no native migration, representative-user review or assistive-tool acceptance.']}
    commands = [['node', '--version'], ['npm', 'run', 'typecheck'], ['npm', 'run', 'test:boundaries'], ['npm', 'run', 'build'], ['npx', 'playwright', 'test', '--config', 'tests/browser-p08/playwright.config.ts']]
    for index, argv in enumerate(commands):
        try:
            result = subprocess.run(argv, cwd=CONSOLE, capture_output=True, text=True, timeout=180)
            code, data = result.returncode, result.stdout + result.stderr
        except subprocess.TimeoutExpired as error:
            code, data = 124, str(error)
        path = output / f'{index:02d}.log'; path.write_text(data)
        report['commands'].append({'argv': argv, 'exit_code': code, 'log': path.name, 'sha256': sha(path)})
        print(f'{index}: {"PASS" if code == 0 else "FAIL"}', flush=True)
    browser = CONSOLE/'test-results/p08-browser.json'
    if browser.exists():
        shutil.copyfile(browser, output/'browser.json')
        report['stats'] = json.loads(browser.read_text())['stats']
    artifacts = CONSOLE/'test-results/p08-artifacts'
    if artifacts.exists():
        shutil.copytree(artifacts, output/'browser', dirs_exist_ok=True)
    stats = report.get('stats', {})
    report['result'] = 'PASSED' if all(c['exit_code'] == 0 for c in report['commands']) and stats.get('expected') == 5 and not any(stats.get(k, 1) for k in ('unexpected', 'flaky', 'skipped')) else 'FAILED'
    report['artifact_sha256'] = {str(p.relative_to(output)): sha(p) for p in output.rglob('*') if p.is_file() and p.name != 'report.json' and not any(part.startswith('.') for part in p.relative_to(output).parts)}
    (output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    return 0 if report['result'] == 'PASSED' else 1

if __name__ == '__main__':
    raise SystemExit(main())
