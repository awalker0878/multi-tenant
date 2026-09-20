#!/usr/bin/env python3
"""Bind vSphere recovery observations to a held Terraform attempt; never release it."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import sys
if __package__ in (None, ''): sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import readback_core as c, recovery_review, vsphere_task_tree_observe as tree
from tools.run_files import digest, encoded, load_private, private_path, read_private, require, write_new, utcnow
from tools.terraform_run import ROOT, select_scope, backend_settings
from tools.plan_review import has_true

HELD = {'STARTED_OUTCOME_UNKNOWN', 'HOLD_RECONCILIATION_REQUIRED'}
OBSERVED_PLAN_FIELDS = {'name', 'num_cpus', 'num_cores_per_socket', 'memory', 'resource_pool_id'}
UPDATE_FIELDS = {'num_cpus', 'num_cores_per_socket', 'memory'}
COMPUTED_FIELDS = {'change_version', 'default_ip_address', 'guest_ip_addresses', 'power_state', 'vapp_transport'}


def valid_unknown_mask(value):
    if type(value) is bool: return True
    if isinstance(value, dict): return all(valid_unknown_mask(x) for x in value.values())
    if isinstance(value, list): return all(valid_unknown_mask(x) for x in value)
    return False


def bind_configuration(change, resource, member_name, member):
    """Compare supported planned configuration; hold changes outside this coverage."""
    before, after, unknown = change['before'], change['after'], change.get('after_unknown', {})
    require(valid_unknown_mask(unknown), 'Malformed planned unknown mask')
    require(not any(has_true(value) for key, value in unknown.items() if key not in COMPUTED_FIELDS), 'Unresolved planned configuration')
    changed = {key for key in set(before) | set(after) if c.digest(before.get(key)) != c.digest(after.get(key))}
    require(changed <= UPDATE_FIELDS | COMPUTED_FIELDS, 'Update exceeds observed configuration coverage')
    require(change['actions'] != ['no-op'] or changed <= COMPUTED_FIELDS, 'No-op contradicts planned configuration')
    expected = resource['expected']; hardware = expected['config']['hardware']
    values = dict(name=expected['config']['name'], num_cpus=hardware['numCPU'], num_cores_per_socket=hardware['numCoresPerSocket'],
                  memory=hardware['memoryMB'], resource_pool_id=expected['resourcePool']['value'])
    require(all(key in after and type(after[key]) is type(value) and after[key] == value for key, value in values.items()), 'Planned configuration differs from native expectations')
    require(values['name'] == member_name and values['num_cpus'] == member.get('vcpu', 2)
            and values['memory'] == member.get('memory_gib', 4) * 1024
            and values['resource_pool_id'] == member['resource_pool_id'], 'Configuration differs from sealed member inputs')
    known_native = dict(moid=resource['moid'], uuid=expected['config']['uuid'], change_version=expected['config']['changeVersion'],
                        power_state={'poweredOn': 'on', 'poweredOff': 'off'}[expected['runtime']['powerState']])
    for key, value in known_native.items():
        if key in after and not has_true(unknown.get(key)):
            require(type(after[key]) is str and after[key] == value, 'Known native plan metadata differs')


def bind_plan(plan, inputs, manifest):
    """Existing VM IDs only. Unknown creates/replacements need native adoption review."""
    require(plan.get('format_version') == '1.2' and plan.get('complete') is True, 'Complete saved plan required')
    require(manifest['profile'] == tree.activity.PROFILE, 'Existing-VM activity coverage required; clone adoption remains separate')
    require(not plan.get('errored') and not plan.get('deferred_changes') and not plan.get('resource_drift')
            and all(isinstance(check, dict) and check.get('status') == 'pass' for check in plan.get('checks', [])), 'Unresolved plan evidence')
    changes = plan.get('resource_changes'); require(isinstance(changes, list), 'Saved resource changes required')
    wanted = {'module.owned.module.member[' + json.dumps(name) + '].vsphere_virtual_machine.workload': name for name in inputs['members']}
    resources = {r['expected']['config']['uuid']: r for r in manifest['resources']}
    actual = {}; ids = set()
    for r in changes:
        require(isinstance(r, dict), 'Resource change object required')
        if r.get('mode') == 'data': continue
        require(r.get('mode') == 'managed' and r.get('type') == 'vsphere_virtual_machine'
                and r.get('provider_name') == 'registry.terraform.io/hashicorp/vsphere'
                and r.get('address') in wanted and r['address'] not in actual, 'Unreviewed resource scope')
        change = r['change']; require(isinstance(change, dict), 'Native change object required')
        require(not r.get('previous_address') and not r.get('deposed') and not change.get('importing'), 'Adoption or moved address requires separate ownership review')
        before, after = change.get('before'), change.get('after')
        require(change.get('actions') in (['no-op'], ['update']) and isinstance(before, dict) and isinstance(after, dict), 'Create/delete/replace requires separate ownership reconciliation')
        identity = before.get('id')
        unknown = change.get('after_unknown', {})
        require(isinstance(unknown, dict) and (unknown.get('id') is None or unknown.get('id') is False), 'Unknown VM identity')
        require(isinstance(identity, str) and c.UUID.fullmatch(identity) and after.get('id') == identity
                and identity not in ids, 'Known unchanged VM identity required')
        require(identity in resources, 'Native VM absent from accepted observation')
        name = wanted[r['address']]
        bind_configuration(change, resources[identity], name, inputs['members'][name])
        ids.add(identity); actual[r['address']] = identity
    require(set(actual) == set(wanted) and ids == set(resources), 'Plan and native VM coverage differ')
    return actual


def review_attempt(operation, ledger_root, manifest_path, report_path, context_path, output):
    operation = private_path(operation, directory=True); ledger_root = private_path(ledger_root, directory=True)
    output = Path(output).absolute()
    require(not output.resolve().is_relative_to(ROOT.resolve()) and not output.resolve().is_relative_to(ledger_root)
            and not output.resolve().is_relative_to(operation), 'New review output must be outside repository, bundle and ledger')
    bundle_bytes = read_private(operation / 'bundle.json'); bundle = c.strict_loads(bundle_bytes)
    require(bundle['format'] == 'hosting-terraform-bundle/1' and bundle['status'] == 'AWAITING_EXACT_PLAN_REVIEW', 'Unknown bundle')
    c.identifier(bundle['operation_id']); require(type(bundle['generation']) is int and bundle['generation'] > 0, 'Invalid generation')
    needed = {'inputs.json', 'backend.json', 'plan.json', 'saved.tfplan'}
    require(needed <= bundle['artifacts'].keys(), 'Incomplete execution evidence')
    for name in needed:
        require(digest(read_private(operation / name)) == bundle['artifacts'][name], 'Sealed execution artifact changed')
    inputs = load_private(operation / 'inputs.json'); _, scope, state_key = select_scope(ROOT, bundle['catalog_id'], inputs)
    require(scope == bundle['scope'] and scope['platform'] == 'vmware' and scope['phase'] == 'workloads'
            and state_key == bundle['state_key'], 'Only exact VMware workload scope supported')
    backend = load_private(operation / 'backend.json'); backend_settings(backend, state_key)
    ledger = private_path(ledger_root / digest(backend['address'].encode()), directory=True)
    lock = private_path(ledger / 'writer.lock')
    fd = os.open(lock, os.O_RDWR | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        head_bytes = read_private(ledger / 'head.json'); head = c.strict_loads(head_bytes)
        attempt_id = digest(encoded({'operation': bundle['operation_id'], 'generation': bundle['generation']}))
        started = load_private(ledger / (attempt_id + '.started.json'))
        require(started['status'] == 'STARTED_OUTCOME_UNKNOWN' and head['status'] in HELD, 'No matching held attempt')
        identity = {'format': 'hosting-terraform-attempt/1', 'bundle_sha256': digest(bundle_bytes), 'scope': scope,
                    'operation_id': bundle['operation_id'], 'generation': bundle['generation']}
        require(all(record.get(k) == v for record in (head, started) for k, v in identity.items())
                and head['started_at'] == started['started_at'] and head['change_ref'] == started['change_ref'], 'Attempt identity differs')
        if head['status'] == 'HOLD_RECONCILIATION_REQUIRED':
            require(load_private(ledger / (attempt_id + '.result.json')) == head, 'Held result differs from ledger head')
        manifest = load_private(manifest_path); report = load_private(report_path); context = load_private(context_path)
        tree.validate(manifest)
        require(manifest['operation_id'] == bundle['operation_id'] and manifest['tenant_id'] == scope['tenant_key']
                and manifest['scope_id'] == scope['wsd_key'], 'Observation scope differs from attempt')
        endpoint = inputs['platform_endpoint']
        expected_origin = c.origin(endpoint if endpoint.startswith('https://') else 'https://' + endpoint)
        require(manifest['origin'] == expected_origin, 'Native origin differs from sealed provider endpoint')
        bound = bind_plan(load_private(operation / 'plan.json'), inputs, manifest)
        require(context['accepted_plan_sha256'] == bundle['artifacts']['saved.tfplan']
                and context['attempted_generation'] == bundle['generation']
                and context['attempted_at'] == head['started_at'] and context['change_record_ref'] == head['change_ref'], 'Context is not the exact attempted plan')
        require(c.timestamp(manifest['task']['activity_since']) == c.timestamp(head['started_at']), 'Activity window differs from immutable attempt start')
        require(all(c.timestamp(r['queued_at']) >= c.timestamp(head['started_at']) for r in manifest['task']['records']), 'Historical tasks cannot resolve this attempt')
        triage = recovery_review.review(manifest, report, context)
        require(read_private(ledger / 'head.json') == head_bytes, 'Ledger changed during review')
        result = dict(format='hosting-terraform-recovery-review/1', reviewed_at=utcnow().isoformat(),
            scope=scope, operation_id=bundle['operation_id'], generation=bundle['generation'], bundle_sha256=digest(bundle_bytes),
            ledger_head_sha256=digest(head_bytes), manifest_sha256=c.digest(manifest), report_sha256=c.digest(report),
            context_sha256=c.digest(context), plan_native_bindings=bound, triage=triage,
            plan_configuration_fields=sorted(OBSERVED_PLAN_FIELDS),
            ledger_status=head['status'], ledger_released=False, may_apply=False, may_delete=False, may_activate=False)
        write_new(output, encoded(result))
        return result
    finally: os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('bundle', 'ledger', 'manifest', 'readback', 'context', 'output'): parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    try:
        result = review_attempt(args.bundle, args.ledger, args.manifest, args.readback, args.context, args.output)
        print(json.dumps({'result': result['triage']['result'], 'ledger_released': False, 'may_apply': False}))
        return 0 if result['triage']['result'] == 'READY_FOR_OPERATOR_RECOVERY_REVIEW' else 2
    except (OSError, ValueError, KeyError, TypeError):
        print('{"result":"HOLD_UNBOUND_EXECUTION_EVIDENCE","ledger_released":false,"may_apply":false}'); return 2


if __name__ == '__main__': raise SystemExit(main())
