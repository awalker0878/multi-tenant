#!/usr/bin/env python3
"""Exercise only the localhost preflight. No remote hosts or infrastructure apply."""
from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'reports/ansible-validation.json'
checks = []
env = dict(os.environ, ANSIBLE_CONFIG=str(ROOT / 'ansible/ansible.cfg'), ANSIBLE_NOCOLOR='1')

def run(name, command, expected=0):
    result = subprocess.run(command, cwd=ROOT / 'ansible', env=env, text=True, capture_output=True, timeout=180)
    passed = result.returncode == expected if expected == 0 else result.returncode != 0
    checks.append({'name': name, 'passed': passed, 'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr})
    return result

try:
    if not shutil.which('ansible-playbook') or not shutil.which('ansible-lint'):
        raise RuntimeError('Ansible executables are unavailable; tests are BLOCKED, not passed.')
    run('version', ['ansible-playbook', '--version'])
    run('lint', ['ansible-lint', '--offline', 'playbooks/repository_preflight.yml', 'roles/repository_preflight'])
    base = ['ansible-playbook', 'playbooks/repository_preflight.yml', '-i', 'inventories/local/hosts.yml']
    run('syntax', [*base, '--syntax-check'])
    with tempfile.TemporaryDirectory(prefix='multi-tenant-', dir='/tmp') as temporary:
        variables = {'repository_preflight_enabled': True, 'repository_preflight_root': str(ROOT), 'repository_preflight_output_directory': temporary}
        args = [*base, '-e', json.dumps(variables)]
        run('check-mode', [*args, '--check', '--diff'])
        receipt = Path(temporary) / 'preflight.json'
        checks.append({'name': 'check-mode-no-write', 'passed': not receipt.exists()})
        run('local-first-convergence', args)
        before = receipt.read_bytes()
        second = run('local-second-convergence', args)
        checks.append({'name': 'idempotency', 'passed': bool(re.search(r'localhost\s*:.*changed=0\b', second.stdout)) and receipt.read_bytes() == before})
        document = json.loads(before)
        checks.append({'name': 'no-native-authorization', 'passed': all(document[k] is False for k in ('may_apply', 'may_delete', 'may_activate'))})
        denied = dict(variables, repository_preflight_enabled=False)
        rejection = run('disabled-refused', [*base, '-e', json.dumps(denied)], expected=1)
        checks.append({'name': 'disabled-refusal-reason', 'passed': 'Local preflight scope' in rejection.stdout})
        unsafe = dict(variables, repository_preflight_output_directory='/tmp/not-an-accepted-output')
        run('unsafe-output-refused', [*base, '-e', json.dumps(unsafe)], expected=1)
except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
    checks.append({'name': 'runner-error', 'passed': False, 'detail': str(exc)})

REPORT.parent.mkdir(exist_ok=True)
passed = bool(checks) and all(c['passed'] for c in checks)
report = {'status': 'PASSED_LOCAL_ANSIBLE_ONLY' if passed else 'FAILED_OR_BLOCKED', 'native_qualification': 'NOT_RUN', 'checks': checks}
REPORT.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': report['status'], 'checks': len(checks), 'failed': [c['name'] for c in checks if not c['passed']]}, indent=2))
sys.exit(0 if passed else 1)
