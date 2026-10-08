"""Scan exact tracked repository content for secrets; retain only redacted findings."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from bundle import digest, encode, require
from campaign import redacted_results


def scan(trivy: Path, source: Path, output: Path) -> dict:
    env = {key: value for key, value in os.environ.items() if not key.startswith('TRIVY_')}
    result = subprocess.run([str(trivy), 'fs', '--config', '', '--ignorefile', '', '--secret-config', '',
                             '--scanners', 'secret', '--no-progress', '--timeout', '5m',
                             '--format', 'json', '--output', str(output), str(source)],
                            env=env, capture_output=True, timeout=330)
    require(result.returncode == 0, 'repository_secret_scanner_failed')
    raw = json.loads(output.read_bytes())
    require(raw.get('SchemaVersion') == 2 and isinstance(raw.get('Results', []), list), 'invalid_secret_scan')
    return {'results': redacted_results(raw),
            'secrets': sum(len(row.get('Secrets') or []) for row in raw.get('Results', []))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trivy', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    args.output.mkdir(parents=True, exist_ok=False)
    report = {'schema_version': 1, 'result': 'FAILED', 'scope': 'Tracked repository secret detection only',
              'started_at': datetime.now(timezone.utc).isoformat(), 'promotion_authorized': False}
    try:
        def git(*argv):
            return subprocess.check_output(['git', *argv], cwd=root, timeout=30)
        revision = git('rev-parse', 'HEAD').decode().strip()
        require(re.fullmatch(r'[0-9a-f]{40}', revision), 'invalid_repository_revision')
        require(not git('status', '--porcelain', '--untracked-files=no').strip(), 'dirty_repository_input')
        report['source_revision'] = revision
        tools = json.loads((root / 'release/artifact-tools.lock.json').read_bytes())
        # Bind the executable to the already reviewed tool lock, not a PATH lookup.
        expected = tools['trivy']['binary_sha256']
        require(digest(args.trivy) == expected, 'untrusted_scanner_binary')
        report['scanner_sha256'] = expected
        inventory = {}
        with tempfile.TemporaryDirectory(prefix='p01-private-repository-scan-') as private:
            work = Path(private);source = work / 'source';source.mkdir()
            for entry in git('ls-tree', '-r', '-z', revision).split(b'\0'):
                if not entry:
                    continue
                header, path_bytes = entry.split(b'\t', 1)
                mode, kind, blob = header.decode().split()
                name = path_bytes.decode()
                require(mode in {'100644', '100755'} and kind == 'blob', 'unsupported_tracked_object')
                require(not Path(name).is_absolute() and '..' not in Path(name).parts
                        and '\\' not in name, 'unsafe_tracked_path')
                original = root / name
                require(original.is_file() and not original.is_symlink(), 'missing_tracked_file')
                destination = source / name;destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(original, destination)
                raw = destination.read_bytes()
                require(hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == blob,
                        'tracked_blob_changed_during_scan')
                inventory[name] = digest(destination)
            require(inventory, 'empty_repository_snapshot')
            # Positive detector control uses a generated non-credential in a separate
            # temporary tree. Neither fixture bytes nor raw findings are retained.
            fixture = work / 'fixture';fixture.mkdir()
            (fixture / 'credential.txt').write_text('token=' + 'ghp_' + 'A7b9C2d4E6f8G1h3I5j7K9l2M4n6P8q1R3s5' + '\n')
            positive = scan(args.trivy, fixture, work / 'positive.json')
            require(positive['secrets'] > 0, 'secret_detector_control_failed')
            result = scan(args.trivy, source, work / 'raw.json')
            report.update(result)
            report['result'] = 'PASSED' if result['secrets'] == 0 else 'HELD'
            report['detector_positive_control'] = 'PASSED'
            report['source_sha256'] = inventory
            report['tracked_files'] = len(inventory)
            report['limitations'] = 'Heuristic text detector coverage, not proof of secret absence; no history scan. No source-tree exclusion is configured.'
    except Exception as error:
        report['error'] = str(error) if isinstance(error, ValueError) else type(error).__name__
    report['completed_at'] = datetime.now(timezone.utc).isoformat()
    (args.output / 'report.json').write_bytes(encode(report))
    print(json.dumps({k: report.get(k) for k in ('result', 'source_revision', 'tracked_files', 'secrets', 'error')}))
    return 0 if report['result'] == 'PASSED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
