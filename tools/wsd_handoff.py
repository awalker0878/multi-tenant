#!/usr/bin/env python3
"""Compile disabled workload inputs from exact, successful domain execution receipts."""
from __future__ import annotations

import argparse
from datetime import datetime
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import readback_core as c
from tools.compile_wsd import compile_environment
from tools.run_files import (digest, encoded, load_private, new_directory,
                            read_private, require, utcnow, write_new)
from tools.terraform_apply import verify_outputs


def execution_outputs(directory, phase):
    directory = Path(directory)
    bundle = load_private(directory / 'bundle.json')
    result = load_private(directory / 'result.json')
    require(bundle['format'] == 'hosting-terraform-bundle/1'
            and result['format'] == 'hosting-terraform-attempt/1', 'Unknown execution receipt')
    require(result['status'] == 'APPLIED_REQUIRES_NATIVE_ACCEPTANCE', 'Execution is incomplete or uncertain')
    require(result['bundle_sha256'] == digest(read_private(directory / 'bundle.json'))
            and result['scope'] == bundle['scope'] and result['operation_id'] == bundle['operation_id']
            and result['generation'] == bundle['generation'], 'Execution receipt identity changed')
    require(bundle['scope']['phase'] == phase, 'Wrong execution phase')
    completed = datetime.fromisoformat(result['completed_at'])
    require(completed.tzinfo is not None and 0 <= (utcnow() - completed).total_seconds() <= 86400,
            'Execution receipt is stale or future-dated; obtain current native observations')
    for name, expected in [('outputs.json', result['outputs_sha256']), ('inputs.json', bundle['artifacts']['inputs.json'])]:
        require(digest(read_private(directory / name)) == expected, 'Execution handoff bytes changed')
    inputs = load_private(directory / 'inputs.json')
    outputs = load_private(directory / 'outputs.json')
    verify_outputs(outputs, bundle, inputs)
    return outputs, inputs, {'bundle_sha256': result['bundle_sha256'],
                            'outputs_sha256': result['outputs_sha256'], 'source_commit': bundle['source_commit'],
                            'operation_id': bundle['operation_id'], 'generation': bundle['generation']}


def compile_runs(environment, directories, vmware_bindings=None):
    domain_files, expected = compile_environment(environment)
    expected_scopes = {row['scope']['tenant_key'] + '/' + row['scope']['wsd_key']: row for row in expected['scopes']}
    outputs, provenance = {}, {}
    for directory in directories:
        value, inputs, receipt = execution_outputs(directory, 'domains')
        scope = value['scope']['value']
        key = scope['tenant_key'] + '/' + scope['wsd_key']
        require(key in expected_scopes and key not in outputs and scope == expected_scopes[key]['scope'],
                'Missing, duplicate or foreign domain execution scope')
        intended = domain_files[expected_scopes[key]['input']]
        require(inputs['members'] == intended['members'], 'Domain execution inputs differ from current WSD intent')
        outputs[key], provenance[key] = value, receipt
    require(set(outputs) == set(expected_scopes), 'Every intended WSD requires exactly one successful domain run')
    files, scopes = compile_environment(environment, 'workloads', outputs, vmware_bindings)
    return files, scopes, {'status': 'BOUND_EXECUTION_OUTPUTS_NOT_NATIVE_ACCEPTANCE', 'runs': provenance}



def compile_scope_runs(environment, directories, scope, vmware_bindings=None):
    """Validate the full accepted environment, then compile one exact WSD."""
    _, all_scopes = compile_environment(environment)
    c.exact_keys(scope, {'environment_key','site_key','platform','tenant_key','wsd_key'})
    selected = [row for row in all_scopes['scopes']
                if {key:row['scope'][key] for key in scope} == scope]
    require(len(selected) == 1, 'Delivery scope is absent or ambiguous in the accepted environment')
    narrowed = deepcopy(environment)
    narrowed['wsds'] = [row for row in environment['wsds']
                       if (row['tenant_key'],row['wsd_key']) == (scope['tenant_key'],scope['wsd_key'])]
    files, scopes, provenance = compile_runs(narrowed, directories, vmware_bindings)
    provenance.update(environment_sha256=c.digest(environment), selected_scope=scope)
    return files, scopes, provenance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--environment', type=Path, required=True)
    parser.add_argument('--domain-run', type=Path, action='append', required=True)
    parser.add_argument('--vmware-bindings', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        files, scopes, provenance = compile_runs(load_private(args.environment), args.domain_run,
            load_private(args.vmware_bindings) if args.vmware_bindings else None)
        output = new_directory(args.output, ROOT)
        for name, value in {**files, 'scopes.json': scopes, 'execution-handoff.json': provenance}.items():
            path = output / name
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            for parent in path.parents:
                if parent == output:
                    break
                parent.chmod(0o700)
            write_new(path, encoded(value))
        print(json.dumps({'status': scopes['status'], 'scopes': len(scopes['scopes']), 'native_contact': False}))
        return 0
    except (OSError, ValueError, KeyError, TypeError):
        print(json.dumps({'status': 'REJECTED', 'reason': 'Execution receipts do not match the requested WSD handoff'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
