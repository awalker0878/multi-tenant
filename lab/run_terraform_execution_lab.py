#!/usr/bin/env python3
"""Exercise saved-plan process handling using only Terraform's built-in data resource.

No platform provider, remote backend, provisioner or live input is permitted.
This checks real engine/filesystem behavior; it does not qualify native execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from provisioner.execution.run_files import encoded, load_private, write_new
from provisioner.execution.terraform_run import command, process_environment


def experiment(binary):
    checks = []
    with tempfile.TemporaryDirectory(prefix='hosting-tf-execution-') as folder:
        directory = Path(folder)
        write_new(directory / 'main.tf.json', encoded({
            'terraform': {'required_version': '= ' + (ROOT / '.terraform-version').read_text().strip()},
            'variable': {'value': {'type': 'string', 'sensitive': True}},
            'resource': {'terraform_data': {'fixture': {'input': '${var.value}'}}},
            'output': {'fixture': {'value': '${terraform_data.fixture.output}', 'sensitive': True}},
        }))
        write_new(directory / 'terraform.rc', b'disable_checkpoint = true\n')
        env = process_environment({})
        env['TF_CLI_CONFIG_FILE'] = str(directory / 'terraform.rc')
        command(binary, directory, ['init', '-input=false', '-no-color', '-backend=false'], env, directory / 'init.log')
        for name in ('first', 'stale', 'latest'):
            write_new(directory / (name + '.json'), encoded({'value': 'SYNTHETIC-PRIVATE-' + name}))

        def plan(name):
            command(binary, directory, ['plan', '-input=false', '-no-color', '-lock=true',
                f'-var-file={directory / (name + ".json")}', f'-out={directory / (name + ".tfplan")}'],
                env, directory / (name + '-plan.log'))

        def apply(name):
            command(binary, directory, ['apply', '-input=false', '-no-color', '-lock=true',
                str(directory / (name + '.tfplan'))], env, directory / (name + '-apply.log'))

        plan('first')
        command(binary, directory, ['show', '-json', str(directory / 'first.tfplan')], env, directory / 'show.json')
        shown = load_private(directory / 'show.json')
        assert shown['resource_changes'][0]['type'] == 'terraform_data'
        assert shown['variables']['value']['value'] == 'SYNTHETIC-PRIVATE-first'
        checks.append('binary-plan-derived-json')
        apply('first')
        plan('stale')
        plan('latest')
        apply('latest')
        try:
            apply('stale')
        except ValueError:
            assert 'stale' in (directory / 'stale-apply.log').read_text().lower()
        else:
            raise AssertionError('Terraform accepted a stale saved plan')
        checks.append('changed-state-rejects-stale-plan')
        command(binary, directory, ['output', '-json'], env, directory / 'outputs.json')
        assert load_private(directory / 'outputs.json')['fixture']['value'] == 'SYNTHETIC-PRIVATE-latest'
        checks.append('exact-applied-output-preserved')
        assert all((directory / name).stat().st_mode & 0o077 == 0
                   for name in ('first.tfplan', 'show.json', 'outputs.json', 'first-apply.log'))
        checks.append('sensitive-plan-output-and-logs-owner-only')
    return {'status': 'PASSED_LOCAL_TERRAFORM_EXECUTION_ONLY', 'checks': checks,
            'native_target_contacted': False, 'native_qualification': False,
            'command_source_sha256': hashlib.sha256((ROOT / 'provisioner/execution/terraform_run.py').read_bytes()).hexdigest(),
            'ci_head_sha': os.environ.get('GITHUB_SHA')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--terraform', type=Path, default=shutil.which('terraform'))
    parser.add_argument('--output', type=Path, default=ROOT / 'build/reports/terraform_execution_lab.json')
    args = parser.parse_args()
    try:
        if args.terraform is None:
            raise ValueError('Pinned Terraform is required')
        result = experiment(args.terraform.resolve(strict=True))
    except (OSError, ValueError, AssertionError):
        result = {'status': 'FAILED_LOCAL_TERRAFORM_EXECUTION', 'native_target_contacted': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(encoded(result))
    print(json.dumps(result))
    return 0 if result['status'].startswith('PASSED_') else 2


if __name__ == '__main__':
    raise SystemExit(main())
