"""Recheck retained commissioning archives against their permanent source heads."""
import hashlib
import io
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'verification/p08/commissioning'
index = json.loads((DEST / 'qualification-index.json').read_text())
for campaign in index['campaigns']:
    raw = (DEST / campaign['archive']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == campaign['archive_sha256']
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        report = json.loads(archive.read('report.json'))
        assert report['source_revision'] == campaign['tested_merge_commit']
        assert report['result'] == campaign['result']
        head = campaign['published_head']
        assert subprocess.check_output(['git', 'rev-parse', head+'^{tree}'], cwd=ROOT, text=True).strip() == campaign['source_tree']
        bindings = report['source_bindings']
        data = subprocess.check_output(['git', 'cat-file', '--batch'], cwd=ROOT,
            input=''.join(head+':'+path+'\n' for path in bindings).encode())
        stream = io.BytesIO(data)
        for path, expected in bindings.items():
            header = stream.readline().decode().split()
            assert header[1] == 'blob', path
            raw = stream.read(int(header[2])); assert stream.read(1) == b'\n'
            assert hashlib.sha256(raw).hexdigest() == expected, path
        for command in report['commands']:
            assert hashlib.sha256(archive.read(command['log'])).hexdigest() == command['sha256']
        for path, expected in report.get('artifact_sha256', {}).items():
            assert hashlib.sha256(archive.read(path)).hexdigest() == expected, path
        if campaign['name'] in {'components', 'console'}:
            assert report['result'] == 'PASSED'
            assert all(c['exit_code'] == 0 for c in report['commands'])
        if campaign['name'] == 'components':
            assert sum(s['tests'] for s in report['suites']) == 1336
            assert all(not s['failures'] and not s['errors'] and not s['skipped'] for s in report['suites'])
        if campaign['name'] == 'console':
            assert report['stats']['expected'] == 5
            assert all(report['stats'][k] == 0 for k in ('unexpected', 'flaky', 'skipped'))
            for path in archive.namelist():
                if 'operator-readiness-' in path and path.endswith('.png'):
                    assert (DEST / Path(path).name).read_bytes() == archive.read(path)
print('Verified four original archives, their source/log hashes, 1,336 tests and five browser journeys.')
