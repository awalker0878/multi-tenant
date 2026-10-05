"""Resolve and scan declared official image alternatives without adopting them."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from bundle import digest, encode, require
from campaign import redacted_results
from tools import install


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    args.output.mkdir(parents=True, exist_ok=False)
    candidate_path = root / 'deploy/build/remediation-candidates.json'
    inputs = json.loads(candidate_path.read_bytes())
    report = {'schema_version': 1, 'result': 'FAILED', 'scope': inputs['scope'],
              'source_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
              'source_sha256': {p: digest(root / p) for p in [
                  'deploy/build/remediation-candidates.json', 'scripts/p01/artifacts/observe_remediation.py',
                  'scripts/p01/artifacts/bundle.py', 'scripts/p01/artifacts/campaign.py',
                  'scripts/p01/artifacts/tools.py', 'release/artifact-tools.lock.json',
                  '.github/workflows/p01-image-remediation.yml']},
              'started_at': datetime.now(timezone.utc).isoformat(), 'images': {}}

    def run(argv, timeout=240):
        result = subprocess.run(list(map(str, argv)), capture_output=True, timeout=timeout)
        require(result.returncode == 0, 'command_failed:' + str(argv[0]))
        return result.stdout

    try:
        require(inputs['platform'] == 'linux/amd64' and len(inputs['images']) == 4, 'unexpected_candidate_scope')
        with tempfile.TemporaryDirectory(prefix='p01-image-observation-') as private:
            work = Path(private); tools = install(root, work / 'tools'); trivy = tools['trivy']
            cache = work / 'cache'
            run([trivy, 'image', '--cache-dir', cache, '--download-db-only', '--no-progress'])
            database = json.loads((cache / 'db/metadata.json').read_bytes())
            database['sha256'] = digest(cache / 'db/trivy.db')
            report['database'] = database
            report['scanner_sha256'] = digest(Path(trivy))
            for name, candidate in inputs['images'].items():
                row = {'candidate': candidate, 'result': 'FAILED'}
                report['images'][name] = row
                try:
                    require(candidate.startswith(('docker.io/library/python:', 'docker.io/library/php:')),
                            'non_official_candidate')
                    raw = run(['docker', 'buildx', 'imagetools', 'inspect', '--raw', candidate])
                    index = json.loads(raw)
                    selected = [m for m in index['manifests'] if m.get('platform') == {'os': 'linux', 'architecture': 'amd64'}]
                    require(len(selected) == 1, 'ambiguous_image_platform')
                    image_digest = selected[0]['digest']
                    reference = candidate.rsplit(':', 1)[0] + '@' + image_digest
                    child = run(['docker', 'buildx', 'imagetools', 'inspect', '--raw', reference])
                    require('sha256:' + hashlib.sha256(child).hexdigest() == image_digest, 'child_digest_mismatch')
                    (args.output / (name + '-index.json')).write_bytes(raw)
                    (args.output / (name + '-manifest.json')).write_bytes(child)
                    raw_scan = work / (name + '.json')
                    run([trivy, 'image', '--image-src', 'remote', '--cache-dir', cache, '--skip-db-update',
                         '--config', '', '--ignorefile', '', '--secret-config', '', '--no-progress',
                         '--scanners', 'vuln,secret', '--image-config-scanners', 'secret', '--list-all-pkgs',
                         '--format', 'json', '--output', raw_scan, reference], timeout=420)
                    scan = json.loads(raw_scan.read_bytes())
                    require(scan['SchemaVersion'] == 2 and scan.get('Results'), 'empty_image_scan')
                    results = redacted_results(scan)
                    blocked = [v for r in results for v in r['Vulnerabilities']
                               if v['Severity'] in {'HIGH', 'CRITICAL', 'UNKNOWN'}]
                    secrets = sum(len(r['Secrets']) for r in results)
                    require(sum(r['packages_count'] for r in results) > 0, 'empty_package_inventory')
                    row.update(result='OBSERVED', index_digest='sha256:' + hashlib.sha256(raw).hexdigest(),
                               digest=image_digest, reference=reference, results=results,
                               blocking_matches=len(blocked), distinct_advisories=len({v['VulnerabilityID'] for v in blocked}),
                               fixed_versions_available=sum(bool(v.get('FixedVersion')) for v in blocked), secrets=secrets)
                except Exception as error:
                    row['error'] = str(error) if isinstance(error, ValueError) else type(error).__name__
            report['result'] = 'OBSERVED' if all(x['result'] == 'OBSERVED' for x in report['images'].values()) else 'PARTIAL'
    except Exception as error:
        report['error'] = str(error) if isinstance(error, ValueError) else type(error).__name__
    report['completed_at'] = datetime.now(timezone.utc).isoformat()
    (args.output / 'report.json').write_bytes(encode(report))
    print(json.dumps({'result': report['result'], 'images': {k: {f: v.get(f) for f in
        ['result', 'reference', 'blocking_matches', 'fixed_versions_available', 'secrets', 'error']}
        for k, v in report['images'].items()}}))
    return 0 if report['result'] == 'OBSERVED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
