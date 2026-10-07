#!/usr/bin/env python3
"""Verify source, log and artifact custody for fleet success and original failures."""
import hashlib
import json
import subprocess
import zipfile
from functools import lru_cache
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'verification/p08/fleet'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


@lru_cache(maxsize=None)
def source_sha(source, name):
    return sha(subprocess.check_output(['git', 'show', source + ':' + name], cwd=ROOT))


def verify():
    campaigns = []
    for item in json.loads((DEST / 'manifest.json').read_text()):
        path = DEST / item['archive']
        assert sha(path.read_bytes()) == item['archive_sha256'], path
        with zipfile.ZipFile(path) as archive:
            raw = archive.read('report.json')
            report = json.loads(raw)
            source = report.get('source_revision', report.get('source_sha'))
            assert source == item['source_revision']
            bindings = report.get('source_bindings', report.get('source_sha256'))
            assert bindings
            for name, expected in bindings.items():
                assert source_sha(source, name) == expected, (path, name)
            for command in report['commands']:
                if 'log' in command:
                    assert sha(archive.read(command['log'])) == command['sha256'], (path, command)
                else:
                    for stream in ('stdout', 'stderr'):
                        assert sha(archive.read(command[stream])) == command[stream + '_sha256'], (path, command)
            for name, expected in report.get('artifact_sha256', {}).items():
                assert sha(archive.read(name)) == expected, (path, name)
            if item['kind'] == 'browser' and path.stem.endswith('-pass'):
                screenshot = next(n for n in archive.namelist() if n.endswith('/migration-fleet.png'))
                assert (DEST / 'migration-fleet.png').read_bytes() == archive.read(screenshot)
            suites = []
            for suite in report.get('suites', []):
                xml = ElementTree.fromstring(archive.read(suite['name'] + '.xml'))
                totals = {k: sum(int(s.get(k, 0)) for s in xml.iter('testsuite')) for k in ('tests', 'failures', 'errors', 'skipped')}
                assert suite == {'name': suite['name'], **totals}
                suites.append(suite)
            passed = report['result'] in ('PASSED', 'PASS')
            if passed:
                assert not report.get('error') and not report.get('failure')
                assert all(c.get('passed', c['exit_code'] == 0) for c in report['commands'])
                if item['kind'] == 'components':
                    assert len(suites) == 5 and all(s['tests'] and not any(s[k] for k in ('failures', 'errors', 'skipped')) for s in suites)
                if item['kind'] == 'browser':
                    stats = report['stats']
                    assert stats['expected'] == 2 and not any(stats[k] for k in ('unexpected', 'flaky', 'skipped'))
            else:
                assert report['result'] in ('FAILED', 'FAIL')
                assert any(not c.get('passed', c['exit_code'] == 0) for c in report['commands'])
            output = DEST / 'reports' / path.stem / 'report.json'
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(raw)
            campaigns.append(item | {'result': report['result'], 'source_bindings_verified': len(bindings), 'commands': len(report['commands']), 'suites': suites, 'stats': report.get('stats', report.get('browser_stats')), 'report': str(output.relative_to(DEST)), 'report_sha256': sha(raw)})
    return {'schema_version': 1, 'evidence_level': 'E2', 'campaigns': campaigns,
            'native_write_authorized': False, 'native_platforms_tested': [],
            'limitations': ['Real PostgreSQL/TLS and actual Vue/Inertia browser; synthetic native and owner peers.', 'Bulk preparation is not complete-plan composition or execution; native Q07/G08 remains unaccepted.']}


if __name__ == '__main__':
    result = verify()
    (DEST / 'qualification-index.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps([{k: c[k] for k in ('kind', 'result', 'source_bindings_verified', 'commands', 'suites', 'stats')} for c in result['campaigns']], indent=2))
