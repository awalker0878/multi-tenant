"""Bounded explicit parent/child task readback for the Nutanix v4.3 API.

This optional profile extends the existing exact VPC/subnet observer. It reads
ONLY recorded task IDs, never follows hrefs, lists/discovers tasks or cancels work.
A truncated native subtask list stays unknown even if a caller supplies more IDs.
"""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from urllib.parse import quote
from tools import readback_core as c

PROFILE = 'nutanix-networking-prism-v4.3-task-tree'
MAX_TASKS = 16
MAX_DEPTH = 4
ROOT_FIELDS = {'ext_id', 'operation', 'created_after', 'created_before', 'entity_ids', 'descendants'}
CHILD_FIELDS = {'ext_id', 'operation', 'parent_ext_id', 'entity_ids'}
SNAPSHOT_FIELDS = {'task_id', 'operation', 'native_status', 'created_at', 'completed_at',
                   'parent_id', 'root_id', 'children', 'entities', 'diagnostics_present'}
PENDING = {'QUEUED', 'RUNNING', 'CANCELING', 'SUSPENDED'}
FAILED = {'FAILED', 'CANCELED'}
REASONS = {'TASK_BODY_MISSING', 'TASK_IDENTITY_MISMATCH', 'TASK_TIME_INVALID',
           'TASK_REFERENCE_MISMATCH', 'TASK_CHILD_COVERAGE_INCOMPLETE',
           'TASK_ENTITY_COVERAGE_INCOMPLETE', 'TASK_BATCH_NOT_SUPPORTED',
           'TASK_DIAGNOSTICS_REQUIRE_REVIEW', 'TASK_STATE_UNKNOWN', 'TASK_COMPLETION_INVALID',
           'TASK_SHAPE_INVALID', 'TASK_SUCCESS_REPORTED', 'TASK_PENDING', 'TASK_FAILURE_REPORTED'}


def task_id(value: object) -> str:
    from tools.nutanix_observe import TASK_ID
    if not isinstance(value, str) or not TASK_ID.fullmatch(value) or '..' in value:
        raise ValueError('An exact recorded task ID is required, not a URL')
    return value


def specs(m: dict) -> list[dict]:
    root = m['task']
    nodes = [{'ext_id': root['ext_id'], 'operation': root['operation'],
              'parent_ext_id': None, 'entity_ids': root['entity_ids']}, *root['descendants']]
    by_id = {n['ext_id']: n for n in nodes}
    def depth(node):
        count = 0
        while node['parent_ext_id'] is not None:
            count += 1
            if count >= MAX_TASKS: raise ValueError('Task tree cycle')
            node = by_id[node['parent_ext_id']]
        return count
    return sorted(nodes, key=lambda n: (depth(n), n['ext_id']))


def validate(m: dict) -> None:
    from tools import nutanix_observe as native
    c.common_manifest(m, 'nutanix')
    if m['profile'] != PROFILE: raise ValueError('Wrong explicit task-tree profile')
    task = m.get('task'); c.exact_keys(task, ROOT_FIELDS)
    if not isinstance(task['descendants'], list) or not 1 <= len(task['descendants']) < MAX_TASKS:
        raise ValueError('The task-tree profile requires 2-16 explicitly recorded tasks')
    # Reuse the existing selected-resource validation. This is internal schema
    # composition, not native API version negotiation or a fallback request.
    legacy = deepcopy(m); legacy['profile'] = native.PROFILE
    legacy['task'] = {k: task[k] for k in ('ext_id', 'operation', 'created_after', 'entity_ids')}
    native.validate(legacy)
    if c.timestamp(task['created_after']) > c.timestamp(task['created_before']):
        raise ValueError('Reversed accepted task-creation window')
    root_id = task_id(task['ext_id']); allowed_entities = set(task['entity_ids'])
    ids = {root_id}; by_id = {}
    if len({r['expected']['tenantId'] for r in m['resources']}) != 1:
        raise ValueError('One native tenant scope is required for this task-tree profile')
    for child in task['descendants']:
        c.exact_keys(child, CHILD_FIELDS)
        ident = task_id(child['ext_id']); parent = task_id(child['parent_ext_id'])
        c.text(child['operation'], 'expected native operation', 128)
        if ident in ids or ident == parent: raise ValueError('Duplicate or self-parenting task')
        ids.add(ident); by_id[ident] = child
        entities = child['entity_ids']
        if (not isinstance(entities, list) or any(not isinstance(e, str) or e not in allowed_entities for e in entities)
                or len(entities) != len(set(entities))):
            raise ValueError('Child task entity scope must be explicit and within accepted resources')
    for ident, child in by_id.items():
        seen = {ident}; parent = child['parent_ext_id']; depth = 1
        while parent != root_id:
            if parent not in by_id or parent in seen: raise ValueError('Unbound, disconnected or cyclic task tree')
            seen.add(parent); parent = by_id[parent]['parent_ext_id']; depth += 1
        if depth > MAX_DEPTH: raise ValueError('Task tree exceeds four parent/child levels')


def target(ident: str) -> str:
    return '/api/prism/v4.3/config/tasks/' + quote(task_id(ident), safe='')


def targets(m: dict) -> set[str]:
    from tools.nutanix_observe import resource_target
    validate(m)
    return {target(n['ext_id']) for n in specs(m)} | {resource_target(r) for r in m['resources']}


def children(m: dict, ident: str) -> list[str]:
    return sorted(n['ext_id'] for n in m['task']['descendants'] if n['parent_ext_id'] == ident)


def node_observation(body: dict, spec: dict, m: dict, current: datetime) -> dict:
    """Export only validated identity/time/status/relationships, never native text/URLs."""
    def result(progress, reason, snapshot=None):
        return {'task_id': spec['ext_id'], 'progress': progress, 'reason': reason, 'snapshot': snapshot}
    def unknown(reason): return result('UNKNOWN', reason)
    task = body.get('data') if isinstance(body, dict) else None
    if not isinstance(task, dict): return unknown('TASK_BODY_MISSING')
    if (task.get('$objectType') != 'prism.v4.config.Task' or task.get('extId') != spec['ext_id']
            or task.get('operation') != spec['operation']):
        return unknown('TASK_IDENTITY_MISMATCH')
    try:
        created = c.timestamp(task.get('createdTime'))
        if not c.timestamp(m['task']['created_after']) <= created <= min(c.timestamp(m['task']['created_before']), current):
            return unknown('TASK_TIME_INVALID')
        if task.get('batchSummary') is not None: return unknown('TASK_BATCH_NOT_SUPPORTED')
        root_id = m['task']['ext_id']
        def reference(name, expected, absent_ok=False):
            raw = task.get(name)
            if raw is None: return absent_ok
            return (isinstance(raw, dict) and isinstance(raw.get('extId'), str)
                    and raw['extId'] == expected
                    and raw.get('$objectType', 'prism.v4.config.TaskReferenceInternal') == 'prism.v4.config.TaskReferenceInternal')
        if spec['parent_ext_id'] is None:
            if task.get('parentTask') is not None or not reference('rootTask', root_id, True):
                return unknown('TASK_REFERENCE_MISMATCH')
        elif not reference('parentTask', spec['parent_ext_id']) or not reference('rootTask', root_id):
            return unknown('TASK_REFERENCE_MISMATCH')
        expected_children = children(m, spec['ext_id']); count = task.get('numberOfSubtasks')
        refs = task.get('subTasks', [])
        if (type(count) is not int or count != len(expected_children) or not isinstance(refs, list)
                or len(refs) != count or any(not isinstance(n, dict) or not isinstance(n.get('extId'), str) for n in refs)):
            return unknown('TASK_CHILD_COVERAGE_INCOMPLETE')
        actual_children = [n['extId'] for n in refs]
        if sorted(actual_children) != expected_children:
            return unknown('TASK_CHILD_COVERAGE_INCOMPLETE')
        count = task.get('numberOfEntitiesAffected'); refs = task.get('entitiesAffected', [])
        if (type(count) is not int or not isinstance(refs, list) or count != len(refs)
                or count != len(spec['entity_ids']) or any(not isinstance(n, dict) or not isinstance(n.get('extId'), str) for n in refs)):
            return unknown('TASK_ENTITY_COVERAGE_INCOMPLETE')
        entities = sorted(n['extId'] for n in refs)
        if entities != sorted(spec['entity_ids']): return unknown('TASK_ENTITY_COVERAGE_INCOMPLETE')
        status = task.get('status')
        if not isinstance(status, str) or status not in PENDING | FAILED | {'SUCCEEDED'}:
            return unknown('TASK_STATE_UNKNOWN')
        diagnostics = False
        for field in ('errorMessages', 'warnings'):
            value = task.get(field, [])
            if not isinstance(value, list): return unknown('TASK_SHAPE_INVALID')
            diagnostics = diagnostics or bool(value)
        legacy = task.get('legacyErrorMessage', '')
        if not isinstance(legacy, str): return unknown('TASK_SHAPE_INVALID')
        diagnostics = diagnostics or bool(legacy)
        if diagnostics and status not in FAILED: return unknown('TASK_DIAGNOSTICS_REQUIRE_REVIEW')
        completed = None
        if task.get('completedTime') is not None:
            completed = c.timestamp(task['completedTime'])
            if completed < created or completed > current: return unknown('TASK_COMPLETION_INVALID')
        if status == 'SUCCEEDED' and completed is None: return unknown('TASK_COMPLETION_INVALID')
        if status in PENDING and completed is not None: return unknown('TASK_COMPLETION_INVALID')
        snapshot = {'task_id': spec['ext_id'], 'operation': spec['operation'], 'native_status': status,
                    'created_at': created.isoformat(), 'completed_at': completed.isoformat() if completed else None,
                    'parent_id': spec['parent_ext_id'], 'root_id': root_id, 'children': expected_children,
                    'entities': entities, 'diagnostics_present': diagnostics}
        if status in FAILED: return result('FAILED', 'TASK_FAILURE_REPORTED', snapshot)
        if status in PENDING: return result('PENDING', 'TASK_PENDING', snapshot)
        return result('COMPLETE', 'TASK_SUCCESS_REPORTED', snapshot)
    except (ValueError, TypeError, KeyError, RecursionError):
        return unknown('TASK_SHAPE_INVALID')


def summary(m: dict, witness: dict) -> tuple[str, str]:
    phases = [witness['before'], witness['after']]; records = phases[0] + phases[1]
    if any(n['progress'] == 'UNKNOWN' for n in records): return 'UNKNOWN', 'TASK_TREE_INCOMPLETE_OR_UNBOUND'
    for phase in phases:
        by_id = {n['task_id']: n['snapshot'] for n in phase}
        for node in by_id.values():
            if node['parent_id'] is None: continue
            parent = by_id[node['parent_id']]
            if c.timestamp(node['created_at']) < c.timestamp(parent['created_at']):
                return 'UNKNOWN', 'TASK_TREE_TIME_RELATION_INVALID'
            if parent['native_status'] == node['native_status'] == 'SUCCEEDED':
                if c.timestamp(node['completed_at']) > c.timestamp(parent['completed_at']):
                    return 'UNKNOWN', 'TASK_TREE_TIME_RELATION_INVALID'
    for before, after in zip(*phases):
        a, b = before['snapshot'], after['snapshot']
        if a['created_at'] != b['created_at']: return 'UNKNOWN', 'TASK_IDENTITY_CHANGED_DURING_READBACK'
    # Never let a later success erase a failure already seen on this task identity.
    if any(n['progress'] == 'FAILED' for n in records): return 'FAILED', 'TASK_TREE_FAILURE_REPORTED'
    if any(n['progress'] == 'PENDING' for n in records): return 'PENDING', 'TASK_TREE_PENDING'
    if c.digest(phases[0]) != c.digest(phases[1]): return 'UNKNOWN', 'TERMINAL_TASK_CHANGED_DURING_READBACK'
    return 'COMPLETE', 'TASK_TREE_SUCCESS_REPORTED'


def sample(m: dict, client) -> list[dict]:
    from tools.nutanix_observe import sample_resources
    ordered = specs(m)
    def phase(reverse=False):
        observed = {}
        for node in reversed(ordered) if reverse else ordered:
            # A failed GET exits through the existing bounded reader; do not retry
            # it, follow response hrefs, or continue on an apparently successful parent.
            body, _ = client.get(target(node['ext_id']))
            observed[node['ext_id']] = node_observation(body, node, m, datetime.now(timezone.utc))
        return [observed[n['ext_id']] for n in ordered]
    before = phase(); resources = sample_resources(m, client); after = phase(True)
    witness = {'before': before, 'after': after}
    progress, reason = summary(m, witness)
    for resource in resources:
        resource.update(progress=progress, reason=reason, task_sha256=c.digest(witness))
    # Store the complete witness once per round, not once per resource. All
    # resource observations carry its digest; bounded histories stay small.
    resources[0]['task_tree'] = witness
    return resources


def validate_witness(m: dict, witness: dict, current: datetime) -> None:
    """Check exported evidence against the declared task graph, not just its PASS label."""
    c.exact_keys(witness, {'before', 'after'}); ordered = specs(m)
    for phase in ('before', 'after'):
        records = witness[phase]
        if not isinstance(records, list) or len(records) != len(ordered): raise ValueError('Task evidence is incomplete')
        for record, spec in zip(records, ordered):
            c.exact_keys(record, {'task_id', 'progress', 'reason', 'snapshot'})
            if record['task_id'] != spec['ext_id'] or record['reason'] not in REASONS: raise ValueError('Unbound task record')
            if record['snapshot'] is None:
                if record['progress'] != 'UNKNOWN' or record['reason'] in ('TASK_SUCCESS_REPORTED', 'TASK_PENDING', 'TASK_FAILURE_REPORTED'):
                    raise ValueError('Unsupported task completion claim')
                continue
            snap = record['snapshot']; c.exact_keys(snap, SNAPSHOT_FIELDS)
            if type(snap['diagnostics_present']) is not bool: raise ValueError('Invalid diagnostic flag')
            for field in ('children', 'entities'):
                if not isinstance(snap[field], list) or any(not isinstance(x, str) for x in snap[field]):
                    raise ValueError('Invalid task relationship list')
            native = {'$objectType': 'prism.v4.config.Task', 'extId': snap['task_id'], 'operation': snap['operation'],
                      'createdTime': snap['created_at'], 'completedTime': snap['completed_at'], 'status': snap['native_status'],
                      'numberOfSubtasks': len(snap['children']), 'subTasks': [{'extId': x} for x in snap['children']],
                      'numberOfEntitiesAffected': len(snap['entities']), 'entitiesAffected': [{'extId': x} for x in snap['entities']],
                      'parentTask': {'extId': snap['parent_id']} if snap['parent_id'] is not None else None,
                      'rootTask': {'extId': snap['root_id']}, 'errorMessages': [{}] if snap['diagnostics_present'] else []}
            replay = node_observation({'data': native}, spec, m, current)
            if c.digest(replay) != c.digest(record): raise ValueError('Task witness disagrees with accepted scope or status')


def validate_history(m: dict, history: list[dict], states: list[dict], current: datetime | None = None) -> None:
    """Shared online/offline invariant: every task and stable identity remains bound."""
    current = current or datetime.now(timezone.utc)
    try:
        if len(states) == 1 and states[0].get('resource_key') == 'scope':
            if states[0].get('progress') == states[0].get('config_status') == 'UNKNOWN': return
            raise ValueError('Unbound scope record')
        if [s.get('resource_key') for s in states] != [r['ext_id'] for r in m['resources']]:
            raise ValueError('Incomplete resource scope')
        witness = states[0]['task_tree']; validate_witness(m, witness, current)
        progress, reason = summary(m, witness); digest = c.digest(witness)
        for index, state in enumerate(states):
            if (state.get('task_sha256') != digest or (index and 'task_tree' in state)
                    or state.get('progress') != progress or state.get('reason') != reason):
                raise ValueError('Resource and task summaries disagree')
        seen = {}
        for row in [*history, {'states': states}]:
            previous = row['states'][0].get('task_tree')
            if previous is None: continue
            for phase in ('before', 'after'):
                for record in previous[phase]:
                    snap = record['snapshot']
                    if snap is None: continue
                    old = seen.get(record['task_id'])
                    if old:
                        if old['created_at'] != snap['created_at']: raise ValueError('Recorded task identity changed across observations')
                        if old['native_status'] in FAILED | {'SUCCEEDED'} and c.digest(old) != c.digest(snap):
                            # A failure retained in this same sample still receives a
                            # failure hold; it must never become a later accepting run.
                            if old['native_status'] in FAILED and progress == 'FAILED': continue
                            raise ValueError('Terminal task state changed across observations')
                    seen[record['task_id']] = snap
    except (ValueError, TypeError, KeyError, IndexError, RecursionError):
        raise c.ObservationError('TASK_TREE_WITNESS_OR_HISTORY_INVALID') from None
