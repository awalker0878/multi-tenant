#!/usr/bin/env python3
"""Bounded recorded VM task trees with native child-history closure checks."""
import os
from pathlib import Path
import sys
if __package__ in (None, ''): sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import readback_core as c, vsphere_observe as vm, vsphere_task_observe as task, vsphere_history, vsphere_clone_source as source
from tools import vsphere_task_activity as activity
from tools.run_files import require

PROFILE = 'vsphere-vi-json-8.0.3.0-task-tree-history'
CLONE_PROFILE = 'vsphere-vi-json-8.0.3.0-clone-tree-history'
PROFILES = {PROFILE, CLONE_PROFILE, activity.PROFILE}
COVERAGE = 'task-coverage'


def validate(m):
    c.common_manifest(m, 'vmware'); require(m['profile'] in PROFILES, 'Unsupported task-tree profile')
    vm.validate(task.vm_manifest(m)); clones = m['profile'] == CLONE_PROFILE
    keys = {'execution_record_ref', 'coverage_ref', 'task_manager_id', 'records'}
    if clones: keys.add('sources')
    if m['profile'] == activity.PROFILE: keys.add('activity_since')
    c.exact_keys(m['task'], keys); c.text(m['task']['execution_record_ref'])
    c.text(m['task']['coverage_ref']); c.identifier(m['task']['task_manager_id'])
    sources = source.validate(m['task']['sources'], m['resources']) if clones else None
    task.validate_records(m['task']['records'], {r['moid'] for r in m['resources']}, clone_sources=sources, ancestry=True)
    if m['profile'] == activity.PROFILE: activity.validate_window(m)
    records = {r['moid']: r for r in m['task']['records']}
    if clones:
        roots = [r for r in records.values() if r['description_id'] == task.CLONE]
        require(len(roots) == len(m['resources']) and {r['vm_moid'] for r in roots} == {r['moid'] for r in m['resources']}
                and {r['source_moid'] for r in roots} == set(sources)
                and all(r['parent_task_id'] is None for r in roots), 'One accepted clone root per destination required')
    for r in records.values():
        vm.moid(r['root_task_id'], 'task'); parent = r['parent_task_id']
        require(parent is None or parent in records, 'Task parent absent from accepted graph')
        seen = {r['moid']}; node = r
        while node['parent_task_id'] is not None:
            parent = records[node['parent_task_id']]
            require(parent['moid'] not in seen and parent['vm_moid'] == r['vm_moid']
                    and c.timestamp(parent['queued_at']) <= c.timestamp(node['queued_at']), 'Cyclic, foreign or reversed task ancestry')
            seen.add(parent['moid']); node = parent
        require(node['moid'] == r['root_task_id'], 'Accepted task root differs from ancestry')


def targets(m):
    validate(m)
    return (vm.targets(task.vm_manifest(m)) | {task.task_target(r) for r in m['task']['records']}
            | {vm.resource_target(r, 'config') for r in m['task'].get('sources', [])})


def observation_keys(m):
    return (task.observation_keys(m) | {COVERAGE} | {r['moid'] for r in m['task'].get('sources', [])}
            | ({activity.KEY} if m['profile'] == activity.PROFILE else set()))


def history_witness(bodies):
    witnesses = [task.task_witness(body) for body in bodies]
    return sorted(witnesses, key=lambda w: w.get('key', ''))


def coverage_state(m, witness, states):
    status = 'UNKNOWN'; mismatches = []
    try:
        c.exact_keys(witness, {'before', 'after'})
        expected = {r['moid']: r for r in m['task']['records'] if r['parent_task_id'] is not None}
        observed = {s['resource_key']: s['task_witness'] for s in states if s['resource_key'] in expected}
        for phase in ('before', 'after'):
            rows = witness[phase]
            require(isinstance(rows, list) and len(rows) <= 100 and all(isinstance(r, dict) for r in rows), 'Invalid history witness')
            ids = [row.get('key') for row in rows]
            require(all(isinstance(key, str) for key in ids) and len(ids) == len(set(ids)), 'Ambiguous history IDs')
            if set(ids) != set(expected): mismatches.append('/history/' + phase + ':child_set_differs')
        if c.digest(witness['before']) != c.digest(witness['after']): mismatches.append('/history:changed_during_snapshot')
        if any(c.digest(w) != c.digest(observed.get(w.get('key'))) for w in witness['after']):
            mismatches.append('/history:task_get_differs')
        status = 'DIFFERENT' if mismatches else 'MATCH'
    except (ValueError, TypeError, KeyError): mismatches.append('/history:unknown')
    return dict(resource_key=COVERAGE, identity_match=status != 'UNKNOWN', config_status=status,
        progress='UNKNOWN' if status == 'UNKNOWN' else 'COMPLETE', reason='VISIBLE_CHILD_HISTORY_ONLY_NOT_A_WRITER_FENCE',
        config_sha256=c.digest(witness), mismatch_fields=mismatches, history_witness=witness, task_completion_observed=False)


def sample(m, client):
    before_activity = activity.witness(client.activity()) if m['profile'] == activity.PROFILE else None
    sources = m['task'].get('sources', [])
    before_sources = [source.read(r, client) for r in sources]
    before_history = history_witness(client.children())
    before = [task.task_sample(r, client) for r in m['task']['records']]
    snapshots = vm.sample(task.vm_manifest(m), client)
    after = [task.task_sample(r, client) for r in m['task']['records']]
    after_history = history_witness(client.children())
    source_states = [source.state(r, {'before': first, 'after': source.read(r, client)}) for r, first in zip(sources, before_sources)]
    for first, last in zip(before, after):
        if first.get('native_state') in {'success', 'error'} and c.digest(first) != c.digest(last):
            raise c.ObservationError('VSPHERE_TERMINAL_TASK_CHANGED')
    witness = {'before': before_history, 'after': after_history}
    results = snapshots + after + source_states + [coverage_state(m, witness, after)]
    if before_activity is not None:
        evidence = {'before': before_activity, 'after': activity.witness(client.activity())}
        results.append(activity.state(m, evidence, after))
    return results


def validate_observation_history(m, history, states, current=None):
    if len(states) == 1 and states[0].get('resource_key') == 'scope': return
    task.validate_observation_history(m, history, states, current=current)
    try:
        if m['profile'] == activity.PROFILE:
            matches = [s for s in states if s.get('resource_key') == activity.KEY]
            require(len(matches) == 1 and c.digest(matches[0]) == c.digest(activity.state(m, matches[0]['activity_witness'], states, current)), 'Activity summary differs')
        for r in m['task'].get('sources', []):
            matches = [s for s in states if s.get('resource_key') == r['moid']]
            require(len(matches) == 1 and c.digest(matches[0]) == c.digest(source.state(r, matches[0]['source_witness'])), 'Source witness differs')
        coverage = [s for s in states if s.get('resource_key') == COVERAGE]
        require(len(coverage) == 1 and c.digest(coverage[0]) == c.digest(coverage_state(m, coverage[0]['history_witness'], states)), 'History summary differs')
    except (ValueError, TypeError, KeyError):
        raise c.ObservationError('VSPHERE_HISTORY_WITNESS_DIFFERS') from None


def make_client(m, args):
    active = m['profile'] == activity.PROFILE
    client = vsphere_history.ActivityClient if active else vsphere_history.Client
    options = {'vm_ids': [r['moid'] for r in m['resources']], 'since': m['task']['activity_since']} if active else {}
    return client(m['origin'], args.expected_origin, os.environ.get('VCENTER_SESSION', ''), targets(m),
        m['task']['task_manager_id'], [r['moid'] for r in m['task']['records']], args.ca_file, **options)


if __name__ == '__main__':
    from tools.readback_cli import run
    raise SystemExit(run(sys.modules[__name__], 'VCENTER', session=True, client_factory=make_client))
