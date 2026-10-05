"""Read-only deployment probe from a branch push, not a merge authorization hook."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request


def main():
    root = Path(__file__).resolve().parents[3]
    request = json.loads((root / 'release/admission-probe.json').read_text())
    if request['status'] != 'REQUESTED':
        print('No admission deployment probe requested.');return 0
    repo = 'awalker0878/multi-tenant'
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}/pulls/{int(request['pull_request'])}",
                                 headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN']})
    with urllib.request.urlopen(req, timeout=30) as response:
        pr = json.load(response)
    if pr['head']['sha'] != request['expected_head'] or not pr['draft']:
        raise ValueError('fixture_identity_changed')
    output = Path(os.environ['RUNNER_TEMP']) / 'p01-admission-probe';output.mkdir()
    event = output / 'event.json'
    event.write_text(json.dumps({'repository': {'full_name': repo}, 'pull_request': pr}))
    result = subprocess.run([sys.executable, str(root / 'scripts/p01/admission/check_pr.py'), '--output', str(output / 'evaluation')],
                            env=os.environ | {'GITHUB_EVENT_PATH': str(event)}, capture_output=True, timeout=240)
    event.unlink()  # Retain the sanitized evaluator snapshot, not arbitrary PR text.
    (output / 'evaluation.log').write_bytes(result.stdout + result.stderr)
    report = json.loads((output / 'evaluation/report.json').read_text())
    base = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    head_script = subprocess.check_output(['git', 'show', pr['head']['sha'] + ':scripts/p01/admission/check_pr.py'], cwd=root)
    marker = b'CANDIDATE_ADMISSION_SCRIPT_EXECUTED'
    passed = (result.returncode == 1 and report['denial'] == 'review_roles_unconfigured'
              and report['source_revision'] == base == pr['base']['sha']
              and marker in head_script and marker not in result.stdout + result.stderr)
    files = ['scripts/p01/admission/check_pr.py', 'scripts/p01/admission/policy.py',
             'scripts/p01/admission/probe_pr.py', '.github/workflows/p01-admission-probe.yml',
             'release/review-policy.json', 'release/exceptions.json', 'release/admission-probe.json']
    summary = {'result': 'PASSED' if passed else 'FAILED', 'source_revision': base,
               'head_revision': pr['head']['sha'], 'pull_request': pr['number'],
               'candidate_script_sha256': hashlib.sha256(head_script).hexdigest(),
               'source_sha256': {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in files},
               'denial': report.get('denial'), 'candidate_marker_executed': marker in result.stdout + result.stderr,
               'limitations': 'Explicit read-only push probe; automatic default-branch hook and enforced check publication are not installed.'}
    (output / 'report.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary));return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
