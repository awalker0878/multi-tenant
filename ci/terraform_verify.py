#!/usr/bin/env python3
"""Original-source validation, mocked plans and backend-free provider-schema export.

This tool never applies infrastructure or initializes an HTTP state backend.
A separate temporary root is used ONLY when provider-schema loading requires an
initialized backend. The original root remains unchanged and is validated first.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'implementation' / 'terraform'
EXPECTED = {'nsx-domain', 'nsx-gateway-quarantine', 'nsx-route', 'nutanix-domain', 'nutanix-route', 'nutanix-workload', 'openstack-domain', 'openstack-route', 'openstack-workload', 'vsphere-workload'}
H = lambda b: hashlib.sha256(b).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'reports/terraform-validation.json')
    args = parser.parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    report = {'kind': 'REPOSITORY_TERRAFORM_VALIDATION', 'native_qualification': 'NOT_RUN',
              'may_apply': False, 'may_delete': False, 'may_activate': False,
              'backend_validation': 'NOT_RUN_NO_REMOTE_BACKEND_CONTACT', 'entries': [], 'errors': []}
    binary = shutil.which('terraform')
    locks = {}
    before = {str(p.relative_to(SOURCE)): H(p.read_bytes()) for p in SOURCE.rglob('*') if p.is_file() and '.terraform' not in p.parts}
    report['source_sha256'] = H(json.dumps(before, sort_keys=True).encode())
    spec = importlib.util.spec_from_file_location('original_verifier', ROOT / 'implementation/tools/verify_terraform.py')
    original = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)
    try:
        if not binary:
            raise RuntimeError('Terraform is unavailable; toolchain validation is blocked.')
        for family in ('modules', 'roots'):
            if {p.parent.name for p in (SOURCE / family).glob('*/main.tf.json')} != EXPECTED:
                raise RuntimeError('The expected ten module/root inventory is not present.')
        with tempfile.TemporaryDirectory(prefix='multi-tenant-tf-') as temporary:
            temporary = Path(temporary)
            home = temporary / 'home'
            home.mkdir()
            cache = temporary / 'plugins'
            cache.mkdir()
            denied = ('TF_', 'OS_', 'NUTANIX_', 'NSXT_', 'VSPHERE_', 'AWS_', 'AZURE_', 'ARM_', 'GOOGLE_')
            env = {k: v for k, v in os.environ.items() if not k.startswith(denied)}
            env.update(HOME=str(home), TF_INPUT='0', TF_IN_AUTOMATION='1', CHECKPOINT_DISABLE='1', TF_PLUGIN_CACHE_DIR=str(cache))

            def run(directory: Path | None, *argv: str, timeout: int = 300) -> dict:
                command = [binary] + ([f'-chdir={directory}'] if directory else []) + list(argv)
                try:
                    result = subprocess.run(command, env=env, text=True, capture_output=True, timeout=timeout)
                    return {'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
                except subprocess.TimeoutExpired:
                    return {'exit_code': 124, 'stdout': '', 'stderr': 'Command timed out.'}

            version = run(None, 'version', '-json')
            if version['exit_code']:
                raise RuntimeError('Terraform version could not be read.')
            report['terraform_version'] = json.loads(version['stdout'])['terraform_version']
            work = temporary / 'original'
            shutil.copytree(SOURCE, work, ignore=shutil.ignore_patterns('.terraform', '*.tfstate*', '*.tfplan', '*.tfvars', '*.tfvars.json'))
            for family in ('modules', 'roots'):
                for name in sorted(EXPECTED):
                    directory = work / family / name
                    entry = {'family': family, 'name': name, 'validation': 'NOT_RUN', 'mock_tests': 'NOT_APPLICABLE_ROOT' if family == 'roots' else 'NOT_RUN', 'schema_export': 'NOT_RUN'}
                    report['entries'].append(entry)
                    flags = ['init', '-backend=false', '-input=false', '-no-color']
                    if (directory / '.terraform.lock.hcl').is_file():
                        flags.append('-lockfile=readonly')
                    init = run(directory, *flags)
                    if init['exit_code']:
                        entry.update(validation='BLOCKED_INITIALIZATION', diagnostic=init['stderr'][-12000:])
                        continue
                    validation = run(directory, 'validate', '-json')
                    try:
                        diagnostic = json.loads(validation['stdout'])
                    except ValueError:
                        diagnostic = {'valid': False, 'stderr': validation['stderr'][-12000:]}
                    entry['validation_report'] = diagnostic
                    entry['validation'] = 'PASSED' if validation['exit_code'] == 0 and diagnostic.get('valid') is True else 'FAILED'
                    if family == 'modules' and entry['validation'] == 'PASSED':
                        if not original.plan_only_mock_tests(directory):
                            entry['mock_tests'] = 'BLOCKED_UNSAFE_TEST_SOURCE'
                        else:
                            test = run(directory, 'test', '-no-color')
                            entry.update(mock_tests='PASSED' if test['exit_code'] == 0 else 'FAILED', mock_output=test['stdout'][-16000:], mock_stderr=test['stderr'][-12000:])
                    lock = directory / '.terraform.lock.hcl'
                    if lock.is_file():
                        locks[f'implementation/terraform/{family}/{name}/.terraform.lock.hcl'] = lock.read_text()
                    schema = run(directory, 'providers', 'schema', '-json')
                    entry['original_schema_exit_code'] = schema['exit_code']
                    entry['original_schema_diagnostic'] = schema['stderr'][-12000:]
                    schema_scope = 'ORIGINAL_SOURCE'
                    if schema['exit_code'] and family == 'roots' and 'backend' in schema['stderr'].lower() and 'initializ' in schema['stderr'].lower():
                        harness = temporary / 'schema-harness' / name
                        shutil.copytree(work, harness, ignore=shutil.ignore_patterns('.terraform', '*.tfstate*', '*.tfplan'))
                        target = harness / 'roots' / name
                        config_path = target / 'main.tf.json'
                        config = json.loads(config_path.read_text())
                        removed = config.get('terraform', {}).pop('backend', None)
                        if removed is None:
                            entry['schema_export'] = 'FAILED_NO_BACKEND_TO_EXCLUDE'
                            continue
                        config_path.write_text(json.dumps(config, indent=2) + '\n')
                        entry['schema_harness_excluded_backend'] = removed
                        entry['schema_harness_config_sha256'] = H(config_path.read_bytes())
                        initialized = run(target, 'init', '-backend=false', '-input=false', '-lockfile=readonly', '-no-color')
                        if initialized['exit_code']:
                            entry.update(schema_export='FAILED_HARNESS_INITIALIZATION', schema_diagnostic=initialized['stderr'][-12000:])
                            continue
                        schema = run(target, 'providers', 'schema', '-json')
                        schema_scope = 'TEMPORARY_BACKEND_FREE_SCHEMA_COPY_ORIGINAL_ROOT_VALIDATED_SEPARATELY'
                    try:
                        document = json.loads(schema['stdout'])
                        if schema['exit_code'] or not document.get('provider_schemas'):
                            raise ValueError('No provider schemas returned.')
                        path = output.parent / 'provider-schemas' / family / name / 'provider-schema.json'
                        path.parent.mkdir(parents=True, exist_ok=True)
                        data = (json.dumps(document, indent=2) + '\n').encode()
                        path.write_bytes(data)
                        entry.update(schema_export='PASSED_ACTUAL_PROVIDER_SCHEMAS', schema_scope=schema_scope, schema_sha256=H(data))
                    except (ValueError, TypeError, AttributeError):
                        entry.update(schema_export='FAILED', schema_diagnostic=schema['stderr'][-12000:])
    except (RuntimeError, OSError, ValueError, KeyError) as exc:
        report['errors'].append(str(exc))
    after = {str(p.relative_to(SOURCE)): H(p.read_bytes()) for p in SOURCE.rglob('*') if p.is_file() and '.terraform' not in p.parts}
    report['original_sources_unchanged'] = before == after
    passed = not report['errors'] and before == after and len(report['entries']) == 20 and all(
        e['validation'] == 'PASSED' and e['schema_export'] == 'PASSED_ACTUAL_PROVIDER_SCHEMAS' and e['mock_tests'] in ('PASSED', 'NOT_APPLICABLE_ROOT') for e in report['entries'])
    report['status'] = 'PASSED_TOOLCHAIN_ONLY' if passed else 'FAILED_OR_BLOCKED'
    report['elapsed_seconds'] = round(time.monotonic() - started, 3)
    output.write_text(json.dumps(report, indent=2) + '\n')
    (output.parent / 'provider-locks.json').write_text(json.dumps({'generated_by_actual_terraform': report.get('terraform_version'), 'source_sha256': report['source_sha256'], 'locks': locks}, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'validated': sum(e['validation'] == 'PASSED' for e in report['entries']), 'mock_suites_passed': sum(e['mock_tests'] == 'PASSED' for e in report['entries']), 'schema_exports': sum(e['schema_export'] == 'PASSED_ACTUAL_PROVIDER_SCHEMAS' for e in report['entries']), 'errors': report['errors']}, indent=2))
    return 0 if passed else 1

if __name__ == '__main__':
    raise SystemExit(main())
