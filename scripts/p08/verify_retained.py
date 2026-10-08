#!/usr/bin/env python3
"""Verify original P08 campaign bytes, Git source bindings and reported outcomes."""

import hashlib
import json
import subprocess
import zipfile
from functools import lru_cache
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'verification/p08'
QUALIFIED_SOURCE = 'a72d0e88b3626b6912cf189c46ce45cf2fc4878c'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


@lru_cache(maxsize=None)
def source_hash(source, path):
    return sha(subprocess.check_output(['git', 'show', source + ':' + path], cwd=ROOT))


def verify():
    campaigns = []
    for record in json.loads((DEST / 'manifest.json').read_text()):
        path = DEST / record['archive']
        assert sha(path.read_bytes()) == record['archive_sha256'], path
        with zipfile.ZipFile(path) as archive:
            raw = archive.read('report.json')
            report = json.loads(raw)
            assert report['source_revision'] == record['source_revision'], path
            assert report['source_bindings'], path
            for name, expected in report['source_bindings'].items():
                assert source_hash(report['source_revision'], name) == expected, (path, name)
            for command in report['commands']:
                assert sha(archive.read(command['log'])) == command['sha256'], (path, command)
            suites = []
            for declared in report['suites']:
                xml = ElementTree.fromstring(archive.read(declared['name'] + '.xml'))
                actual = {k: sum(int(s.get(k, 0)) for s in xml.iter('testsuite'))
                          for k in ('tests', 'failures', 'errors', 'skipped')}
                assert declared == {'name': declared['name'], **actual}, (path, declared)
                suites.append(declared)
            if report['result'] == 'PASSED':
                assert not report.get('error') and report['commands'] and len(suites) == 3, path
                assert all(c['exit_code'] == 0 for c in report['commands']), path
                assert all(s['tests'] > 0 and not any(s[k] for k in ('failures', 'errors', 'skipped')) for s in suites), path
            else:
                assert report['result'] == 'FAILED', path
                assert report.get('error') or any(c['exit_code'] for c in report['commands']), path
            report_path = DEST / 'reports' / path.stem / 'report.json'
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_bytes(raw)
            campaigns.append(record | {
                'result': report['result'], 'observed_at': report['observed_at'],
                'source_bindings_verified': len(report['source_bindings']),
                'command_logs_verified': len(report['commands']), 'test_suites': suites,
                'original_nonzero_commands': [c for c in report['commands'] if c['exit_code']],
                'report': str(report_path.relative_to(DEST)), 'report_sha256': sha(raw),
            })
    assert any(c['source_revision'] == QUALIFIED_SOURCE and c['result'] == 'PASSED' for c in campaigns)
    regression = json.loads((DEST / 'regressions/failure-receipt.json').read_text())
    archive_path = DEST / 'regressions' / regression['archive']
    assert sha(archive_path.read_bytes()) == regression['archive_sha256']
    with zipfile.ZipFile(archive_path) as archive:
        raw = archive.read('report.json')
        assert raw == (DEST / 'regressions/p06-firefox-failure-report.json').read_bytes()
        report = json.loads(raw)
        assert report['source_revision'] == regression['source_revision'] and report['result'] == 'FAIL'
        for path, expected in report['source_sha256'].items():
            assert source_hash(report['source_revision'], path) == expected, path
        for command in report['commands']:
            assert sha(archive.read(command['name'] + '.log')) == command['sha256']
        for path, expected in report['artifact_sha256'].items():
            assert sha(archive.read(path)) == expected, path
        regression = regression | {'artifact_hashes_verified': len(report['artifact_sha256'])}
    return {
        'schema_version': 1, 'evidence_level': 'E2', 'source_revision': QUALIFIED_SOURCE,
        'native_platforms_tested': [], 'native_write_authorized': False,
        'production_native_dispatch_enabled': False, 'campaigns': campaigns,
        'regression_failure': regression,
        'limitations': [
            'Real PostgreSQL, TLS and subprocess limits; synthetic vSphere/OpenStack and current-owner/application peers.',
            'No installed QEMU/bubblewrap rootfs or guest boot/transform is qualified.',
            'Inventory/Planning/Console migration integration and commissioned current-owner/trust/stage composition remain unfinished.',
            'Native fencing, selected guest/service/delta/traffic/recovery interfaces and actual Q07 results are not supplied.',
            'No G07/G08 receiving decision, native route support, P08 completion or operating acceptance is established.',
        ],
    }


if __name__ == '__main__':
    result = verify()
    (DEST / 'qualification-index.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps([{k: c[k] for k in ('run_id', 'result', 'source_bindings_verified', 'command_logs_verified', 'test_suites')} for c in result['campaigns']], indent=2))
