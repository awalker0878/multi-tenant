"""Bind a successful stable job to its actual checkout, including PR test merges."""
from datetime import datetime, timezone
import argparse
import json
import os
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser();parser.add_argument('--name', required=True);args = parser.parse_args()
    source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    if source != os.environ['GITHUB_SHA']:
        raise ValueError('job_checkout_mismatch')
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    pr = event.get('pull_request')
    report = {'schema_version': 1, 'result': 'PASSED', 'name': args.name, 'source_revision': source,
              'event': os.environ['GITHUB_EVENT_NAME'], 'run_id': int(os.environ['GITHUB_RUN_ID']),
              'run_attempt': int(os.environ['GITHUB_RUN_ATTEMPT']), 'job': os.environ['GITHUB_JOB'],
              'workflow_ref': os.environ['GITHUB_WORKFLOW_REF'], 'recorded_at': datetime.now(timezone.utc).isoformat(),
              'pull_request': None if not pr else {'number': pr['number'], 'head': pr['head']['sha'], 'base': pr['base']['sha']}}
    path = Path(os.environ['RUNNER_TEMP']) / 'p01-check-source';path.mkdir(exist_ok=False)
    (path / 'report.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
