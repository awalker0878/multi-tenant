#!/usr/bin/env python3
"""Verify profile-integration evidence without relabeling original failed results."""
import hashlib
import json
import subprocess
import zipfile
from functools import lru_cache
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT/'verification/p08/profiles'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

@lru_cache(maxsize=None)
def source_hash(source, path):
    return sha(subprocess.check_output(['git', 'show', source + ':' + path], cwd=ROOT))

def verify():
    campaigns = []
    for record in json.loads((DEST/'manifest.json').read_text()):
        path = DEST/record['archive']
        assert sha(path.read_bytes()) == record['archive_sha256'], path
        with zipfile.ZipFile(path) as archive:
            raw = archive.read('report.json'); report = json.loads(raw)
            assert report['source_revision'] == record['source_revision'], path
            bindings = report.get('source_bindings', report.get('input_sha256', report.get('source_sha256')))
            assert bindings, path
            for name, expected in bindings.items():
                assert source_hash(report['source_revision'], name) == expected, (path, name)
            for command in report['commands']:
                if 'log' in command:
                    assert sha(archive.read(command['log'])) == command['sha256'], (path, command)
                elif 'sha256' in command:
                    assert sha(archive.read(command['name']+'.log')) == command['sha256'], (path, command)
            unavailable = []
            for name, expected in report.get('artifact_sha256', {}).items():
                if name not in archive.namelist():
                    assert name == 'browser/.last-run.json', (path, name)
                    unavailable.append(name)
                else:
                    assert sha(archive.read(name)) == expected, (path, name)
            suites = []
            for declared in report.get('suites', []):
                xml = ElementTree.fromstring(archive.read(declared['name']+'.xml'))
                counts = {k: sum(int(s.get(k, 0)) for s in xml.iter('testsuite')) for k in ('tests', 'failures', 'errors', 'skipped')}
                assert declared == {'name': declared['name'], **counts}, (path, declared)
                suites.append(declared)
            if report['result'] in ('PASS', 'PASSED'):
                assert not report.get('error') and all(c.get('exit_code', 0) == 0 for c in report['commands']), path
                if record['kind'] == 'components':
                    assert len(suites) == 5 and all(s['tests'] > 0 and not any(s[k] for k in ('failures', 'errors', 'skipped')) for s in suites), path
                if record['kind'] == 'browser':
                    assert report['stats']['expected'] == 1 and all(report['stats'][k] == 0 for k in ('unexpected', 'flaky', 'skipped')), path
            else:
                assert report['result'] in ('FAIL', 'FAILED'), path
                assert report.get('error') or any(c.get('exit_code', 0) != 0 for c in report['commands']), path
            report_path = DEST/'reports'/path.stem/'report.json'
            report_path.parent.mkdir(parents=True, exist_ok=True); report_path.write_bytes(raw)
            campaigns.append(record | {'result': report['result'], 'source_bindings_verified': len(bindings),
                'commands': len(report['commands']), 'test_suites': suites, 'stats': report.get('stats'), 'artifact_hashes_unavailable': unavailable,
                'report': str(report_path.relative_to(DEST)), 'report_sha256': sha(raw)})
    baseline = json.loads((DEST/'original-contract-compatibility.json').read_text())
    assert not baseline['conflicts']
    for path, expected in baseline['baseline_sha256'].items():
        assert source_hash(baseline['base_revision'], path) == expected
        assert sha((ROOT/path).read_bytes()) == expected, path
    return {'schema_version': 1, 'evidence_level': 'E2', 'native_write_authorized': False,
            'native_platforms_tested': [], 'campaigns': campaigns,
            'original_contracts_verified': len(baseline['baseline_sha256']),
            'limitations': ['Real PostgreSQL/TLS and actual Vue/Inertia page; synthetic platform, owner and browser HTTP peers.',
                           'Planning preparation is an exact binding, not a complete approved executable native plan.',
                           'Actual native-owner/stage composition, converter/guest and selected application/service/recovery protocols remain required.',
                           'No Q07, G07/G08 receiving, P08 completion or operating acceptance is established.']}

if __name__ == '__main__':
    result = verify()
    (DEST/'qualification-index.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps([{k:c[k] for k in ('kind', 'run_id', 'result', 'source_bindings_verified', 'commands', 'test_suites', 'stats')} for c in result['campaigns']], indent=2))
