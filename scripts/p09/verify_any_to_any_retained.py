"""Verify retained local evidence without promoting skips to native qualification."""
import hashlib
import io
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'verification/p09/any-to-any-local'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

index = json.loads((EVIDENCE / 'qualification-index.json').read_text())
for name, expected in index['artifact_sha256'].items():
    assert sha(EVIDENCE / name) == expected, name
for path in EVIDENCE.rglob('report.json'):
    report = json.loads(path.read_text())
    for command in report.get('commands', []):
        assert sha(path.parent / command['log']) == command['sha256'], path
    for name, expected in report.get('artifact_sha256', {}).items():
        assert sha(path.parent / name) == expected, name
    bindings = report.get('source_bindings', {})
    if bindings:
        source = report['source_revision']
        raw = subprocess.check_output(['git', 'cat-file', '--batch'], cwd=ROOT,
            input=''.join(source + ':' + name + '\n' for name in bindings).encode())
        stream = io.BytesIO(raw)
        for name, expected in bindings.items():
            header = stream.readline().decode().split()
            assert header[1] == 'blob', name
            data = stream.read(int(header[2]))
            assert stream.read(1) == b'\n'
            assert hashlib.sha256(data).hexdigest() == expected, (source, name)
component = json.loads((EVIDENCE / 'components/report.json').read_text())
assert all(row['result'] != 'FAILED' for row in component['suites'])
assert sum(row['suite']['tests'] - row['suite']['skipped'] for row in component['suites']) == 1637
assert sum(row['suite']['skipped'] for row in component['suites']) == 146
assert all(row['suite']['failures'] == row['suite']['errors'] == 0 for row in component['suites'])
browser = json.loads((EVIDENCE / 'browser/report.json').read_text())
assert browser['result'] == 'PASSED' and browser['stats']['expected'] == 9
assert all(browser['stats'][key] == 0 for key in ('unexpected', 'flaky', 'skipped'))
assert index['full_qualification'] == 'not_established'
print('Verified 1,637 passing component tests, 146 explicit database skips, nine browser journeys, historical source/log/artifact hashes and original failures. Native qualification remains unestablished.')
