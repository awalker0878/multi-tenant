"""Check visible task activity on exact VMs; observation is never a writer fence."""
from tools import readback_core as c, vsphere_observe as vm, vsphere_task_observe as task
from tools.run_files import require

PROFILE = 'vsphere-vi-json-8.0.3.0-vm-task-activity'
KEY = 'task-activity'


def validate_window(m):
    since = c.timestamp(m['task']['activity_since'])
    require(since <= c.timestamp(c.now()) and all(since <= c.timestamp(r['queued_at']) for r in m['task']['records']),
            'Activity window must include every accepted task')


def witness(activity):
    return {identity: {phase: sorted((task.task_witness(row) for row in rows), key=lambda w: w.get('key', ''))
                      for phase, rows in queries.items()} for identity, queries in activity.items()}


def flatten(m, sample, current):
    c.exact_keys(sample, {r['moid'] for r in m['resources']})
    since = c.timestamp(m['task']['activity_since']); found = {}
    for identity, queries in sample.items():
        c.exact_keys(queries, {'pending', 'completed'})
        for phase, rows in queries.items():
            require(isinstance(rows, list) and len(rows) <= 100, 'Bounded activity witness required')
            for row in rows:
                c.exact_keys(row, {'has_error', 'has_result'}, task.WITNESS_FIELDS | {'result_reference'})
                key = row.get('key'); vm.moid(key, 'task')
                require(key not in found and len(found) < 100, 'Duplicate or excessive activity')
                vm.reference(row.get('entity'), 'VirtualMachine', 'vm'); vm.reference(row.get('task'), 'Task', 'task')
                require(row.get('_typeName') == 'TaskInfo' and row['entity']['value'] == identity and row['task']['value'] == key,
                        'Activity entity/task differs from selected query')
                require(all(type(row.get(k)) is bool for k in ('has_error', 'has_result', 'cancelled')), 'Typed activity flags required')
                queued = c.timestamp(row['queueTime']); require(queued <= current, 'Future activity')
                start = row.get('startTime')
                if start is not None: require(queued <= c.timestamp(start) <= current, 'Reversed activity start')
                if phase == 'pending':
                    require(row.get('state') in {'queued', 'running'} and row.get('completeTime') is None, 'Pending filter contradicted')
                else:
                    end = c.timestamp(row['completeTime'])
                    require(row.get('state') in {'success', 'error'} and max(since, queued) <= end <= current, 'Completion filter contradicted')
                    if start is not None: require(c.timestamp(start) <= end, 'Reversed activity completion')
                found[key] = row
    return found


def state(m, evidence, states, current=None):
    status = 'UNKNOWN'; mismatches = []; current = current or c.timestamp(c.now())
    try:
        c.exact_keys(evidence, {'before', 'after'})
        expected = {r['moid'] for r in m['task']['records']}
        direct = {s['resource_key']: s['task_witness'] for s in states if s['resource_key'] in expected}
        before, after = (flatten(m, evidence[phase], current) for phase in ('before', 'after'))
        if set(before) != expected or set(after) != expected: mismatches.append('/activity:task_set_differs')
        if c.digest(before) != c.digest(after): mismatches.append('/activity:changed_during_snapshot')
        if c.digest(after) != c.digest(direct): mismatches.append('/activity:task_get_differs')
        status = 'DIFFERENT' if mismatches else 'MATCH'
    except (ValueError, KeyError, TypeError): mismatches = ['/activity:unknown_or_contradictory']
    return dict(resource_key=KEY, identity_match=status != 'UNKNOWN', config_status=status,
        progress='UNKNOWN' if status == 'UNKNOWN' else 'COMPLETE', mismatch_fields=mismatches,
        config_sha256=c.digest(evidence), activity_witness=evidence, task_completion_observed=False,
        reason='VISIBLE_VM_TASK_ACTIVITY_ONLY_NOT_NATIVE_WRITER_EXCLUSION')
