#!/usr/bin/env python3
"""Run Python regressions, source inspections and the illustrative route audit.

This command does not invoke Terraform or providers. A separately recorded toolchain
report is referenced only as a historical result; it is not rerun by this command.
"""
from __future__ import annotations
import io
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from provisioner.execution.route_audit import Topology, load_json


def source_snapshot(root: Path) -> dict[str, str]:
    """Hash implemented source in either owner location; this is not a release signature."""
    snapshot = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                for directory in ('provisioner', 'hosting_resources', 'tools', 'tests', 'lab', 'terraform', 'scripts', 'ansible', 'config', '.github')
                for p in (root/directory).rglob('*') if p.is_file()
                and '__pycache__' not in p.parts and '.terraform' not in p.parts}
    for name in ('pyproject.toml', 'setup.py', 'MANIFEST.in', '.gitattributes', '.gitignore', '.editorconfig', '.terraform-version',
                 'requirements-runtime.txt', 'requirements-test.txt',
                 'requirements-repository.txt', 'requirements-dev.txt', 'Makefile',
                 'sources/artifact_catalog.json'):
        snapshot[name] = hashlib.sha256((root/name).read_bytes()).hexdigest()
    return snapshot


def main() -> int:
    started = time.monotonic()
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'))
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    quality = ROOT / 'build/reports'
    quality.mkdir(parents=True, exist_ok=True)
    (quality / 'local_test_output.txt').write_text(stream.getvalue(), encoding='utf-8')
    model = Topology(load_json(ROOT / 'examples/wd14-routing.json')).audit()
    (quality / 'reference_route_checks.json').write_text(json.dumps(model, indent=2) + '\n', encoding='utf-8')
    recorded_toolchain = 'NO_REPORT'
    path = quality / 'terraform_validation.json'
    if path.is_file():
        try:
            recorded_toolchain = load_json(path).get('status', 'INVALID_REPORT')
        except (ValueError, OSError, AttributeError):
            recorded_toolchain = 'INVALID_REPORT'
    snapshot = source_snapshot(ROOT)
    (quality/'tested_source_manifest.json').write_text(json.dumps(snapshot, indent=2)+'\n')
    report = {
        'status': 'PASSED_LOCAL_ONLY' if result.wasSuccessful() and not model['failed'] else 'FAILED_LOCAL',
        'python': platform.python_version(),
        'source_snapshot_files': len(snapshot),
        'source_snapshot_sha256': hashlib.sha256(json.dumps(snapshot,sort_keys=True).encode()).hexdigest(),
        'unit_and_source_tests': {
            'run': result.testsRun, 'failures': len(result.failures),
            'errors': len(result.errors), 'skipped': len(result.skipped),
        },
        'modeled_route_and_intent_checks': {'passed': model['passed'], 'failed': model['failed']},
        'terraform_engine_validation': 'NOT_RUN_BY_THIS_COMMAND',
        'separate_recorded_toolchain_status': recorded_toolchain,
        'provider_mock_tests': 'NOT_RUN_BY_THIS_COMMAND',
        'ansible_engine_validation': 'GUEST_CONTROLLER_FIXTURE_ONLY',
        'live_infrastructure_qualification': 'NOT_RUN',
        'formal_authorization': 'NOT_ISSUED',
        'elapsed_seconds': round(time.monotonic() - started, 3),
        'note': 'The suite includes a pinned Ansible controller dispatch to a non-networking SSH fixture. It does not run Terraform/provider engines, configure a native guest or prove native security behavior; full Ansible profile verification is separate.',
    }
    (quality / 'local_validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    if not result.wasSuccessful():
        print(stream.getvalue())
    return 0 if report['status'] == 'PASSED_LOCAL_ONLY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
