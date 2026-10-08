"""Retain source-bound results from review policy and real signing controls."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cosign', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    args.output.mkdir(parents=True, exist_ok=False)
    paths = [Path(__file__).relative_to(root), Path('.github/workflows/p01-policy-controls.yml'),
             Path('.github/workflows/p01-admission.yml'), Path('scripts/p01/select_components.py'),
             Path('scripts/p01/verify_retained.py'),
             *[p.relative_to(root) for directory in ['scripts/p01/artifacts', 'scripts/p01/admission', 'release', 'architecture']
               for p in (root / directory).rglob('*') if p.is_file() and p.suffix in {'.py', '.json', '.yaml'}]]
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    report = {'schema_version': 1, 'scope': 'P01 development control fixtures; no operated admission',
              'source_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
              'source_sha256': {str(p): sha(root / p) for p in sorted(set(paths))},
              'started_at': datetime.now(timezone.utc).isoformat(), 'result': 'FAILED', 'commands': []}
    try:
        for name, script in [('reviews', 'admission/test_policy.py'), ('bundles', 'artifacts/test_bundle.py'),
                             ('redaction', 'artifacts/test_campaign.py'), ('check-sources', 'admission/test_check_sources.py'),
                             ('exclusions', 'admission/test_exclusions.py'),
                             ('operating-inputs', 'admission/test_operating_inputs.py'),
                             ('release-set', 'artifacts/test_release_set.py')]:
            argv = [sys.executable, str(root / 'scripts/p01' / script), '-v']
            result = subprocess.run(argv, env=os.environ | {'P01_COSIGN': args.cosign},
                                    capture_output=True, timeout=180)
            path = args.output / (name + '.log');path.write_bytes(result.stdout + result.stderr)
            report['commands'].append({'name': name, 'exit_code': result.returncode,
                                       'path': path.name, 'sha256': sha(path)})
            if result.returncode:
                raise ValueError(name + '_failed')
        report['result'] = 'PASSED'
    finally:
        report['completed_at'] = datetime.now(timezone.utc).isoformat()
        (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
