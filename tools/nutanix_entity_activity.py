"""Bounded Prism v4.3 entity activity; no writer-exclusion or recovery authority.

TasksApi.ListTasks and ListTasksRequest from prism-go-client/v4.3.1 define
query parameters. Installed-target filter, order, count and RBAC completeness
must be qualified separately for each affected entity kind.
"""
from datetime import datetime, timezone
from urllib.parse import urlencode
from provisioner.execution import readback_core as c
from tools import nutanix_task_tree as tree
from provisioner.execution.run_files import require

KEY = 'task-activity'
PAGE_SIZE = 25
MAX_PAGES = 4
MAX_RECORDS = 100
FIELDS = {'task_id', 'operation', 'native_status', 'created_at', 'completed_at', 'entities'}


def target(m, identity, page):
    require(identity in {r['ext_id'] for r in m['resources']} and type(page) is int and 0 <= page < MAX_PAGES,
            'Exact entity and bounded page required')
    since = c.timestamp(m['task']['created_after']).isoformat().replace('+00:00', 'Z')
    # Fixed OData expression; no caller-supplied filter, arbitrary URL or task-owner filter.
    # Pending work has no creation cutoff, including work started before this attempt.
    predicate = (f"entitiesAffected/any(e:e/extId eq '{identity}') and "
                 f"((status ne 'SUCCEEDED' and status ne 'FAILED' and status ne 'CANCELED') or completedTime ge {since})")
    return '/api/prism/v4.3/config/tasks?' + urlencode({'$page': page, '$limit': PAGE_SIZE,
        '$filter': predicate, '$orderby': 'extId asc'})


def observation_keys(m):
    return {r['ext_id'] for r in m['resources']} | {KEY}


def record(raw, current):
    """Export only identity, operation, chronology and full affected-entity coverage."""
    require(isinstance(raw, dict) and raw.get('$objectType') == 'prism.v4.config.Task', 'Task row type missing')
    identity = tree.task_id(raw.get('extId')); operation = raw.get('operation'); c.text(operation, length=128)
    status = raw.get('status'); require(status in tree.PENDING | tree.FAILED | {'SUCCEEDED'}, 'Unknown activity status')
    created = c.timestamp(raw.get('createdTime')); require(created <= current, 'Future task creation')
    completed = raw.get('completedTime')
    if status in tree.PENDING:
        require(completed is None, 'Pending task has completion time')
    else:
        completed = c.timestamp(completed)
        require(created <= completed <= current, 'Invalid task completion')
    entities = raw.get('entitiesAffected'); count = raw.get('numberOfEntitiesAffected')
    require(isinstance(entities, list) and type(count) is int and 1 <= count == len(entities) <= 100,
            'Complete bounded task entities required')
    ids = [e.get('extId') if isinstance(e, dict) else None for e in entities]
    require(all(isinstance(e, str) and c.UUID.fullmatch(e) for e in ids) and len(set(ids)) == len(ids), 'Ambiguous task entities')
    return dict(task_id=identity, operation=operation, native_status=status, created_at=created.isoformat(),
                completed_at=completed.isoformat() if completed is not None else None, entities=sorted(ids))


def read_activity(m, client, *, error_code):
    result = {}; observed = 0
    for resource in m['resources']:
        identity = resource['ext_id']; pages = []; total = None
        for page in range(MAX_PAGES):
            body, _ = client.get(target(m, identity, page))
            try:
                require(isinstance(body, dict) and isinstance(body.get('metadata'), dict), 'Task metadata required')
                metadata = body['metadata']; rows = body.get('data'); count = metadata.get('totalAvailableResults')
                require(type(count) is int and 0 <= count <= PAGE_SIZE * MAX_PAGES, 'Task count exceeds bounded coverage')
                require(total is None or count == total, 'Task count changed across pages')
                require(metadata.get('messages', []) == [], 'Task query diagnostics require review')
                total = count
                require(isinstance(rows, list) and len(rows) == min(PAGE_SIZE, max(0, total-page*PAGE_SIZE)), 'Truncated task page')
                observed += len(rows); require(observed <= MAX_RECORDS, 'Aggregate activity limit exceeded')
                pages.append(dict(page=page, total=total, tasks=[record(row, datetime.now(timezone.utc)) for row in rows]))
            except (ValueError, TypeError, KeyError):
                raise c.ObservationError(error_code) from None
            if (page+1)*PAGE_SIZE >= total: break
        result[identity] = pages
    return result


def flatten(m, evidence, current):
    c.exact_keys(evidence, {r['ext_id'] for r in m['resources']})
    since = c.timestamp(m['task']['created_after']); result = {}; observed = 0
    for identity, pages in evidence.items():
        require(isinstance(pages, list) and 1 <= len(pages) <= MAX_PAGES, 'Incomplete activity pages')
        rows = {}; total = None; previous = ''
        for index, page in enumerate(pages):
            c.exact_keys(page, {'page', 'total', 'tasks'})
            require(type(page['page']) is int and page['page'] == index and type(page['total']) is int
                    and 0 <= page['total'] <= PAGE_SIZE*MAX_PAGES, 'Invalid activity page bounds')
            require(total is None or page['total'] == total, 'Inconsistent activity total')
            total = page['total']; tasks = page['tasks']
            require(isinstance(tasks, list) and len(tasks) == min(PAGE_SIZE, max(0, total-index*PAGE_SIZE)), 'Incomplete activity rows')
            observed += len(tasks); require(observed <= MAX_RECORDS, 'Aggregate activity witness limit exceeded')
            for row in tasks:
                c.exact_keys(row, FIELDS)
                require(isinstance(row['entities'], list), 'Entity list required')
                raw = dict(extId=row['task_id'], operation=row['operation'], status=row['native_status'],
                    createdTime=row['created_at'], completedTime=row['completed_at'],
                    entitiesAffected=[{'extId': e} for e in row['entities']], numberOfEntitiesAffected=len(row['entities']))
                raw['$objectType'] = 'prism.v4.config.Task'
                require(c.digest(record(raw, current)) == c.digest(row), 'Activity witness differs')
                require(identity in row['entities'] and (row['native_status'] in tree.PENDING
                        or c.timestamp(row['completed_at']) >= since), 'Native query filter contradicted')
                require(row['task_id'] > previous and row['task_id'] not in rows, 'Duplicate or unsorted task pages')
                previous = row['task_id']; rows[row['task_id']] = row
        require(len(pages) == max(1, (total+PAGE_SIZE-1)//PAGE_SIZE) and len(rows) == total, 'Incomplete activity traversal')
        result[identity] = rows
    return result


def activity_state(m, evidence, states, current=None, *, reason):
    current = current or datetime.now(timezone.utc); mismatch = []; status = 'UNKNOWN'
    try:
        c.exact_keys(evidence, {'before', 'after'})
        direct = states[0]['task_tree']
        samples = {phase: flatten(m, evidence[phase], current) for phase in ('before', 'after')}
        for phase in ('before', 'after'):
            for identity, rows in samples[phase].items():
                expected = {n['ext_id'] for n in tree.specs(m) if identity in n['entity_ids']}
                if set(rows) != expected: mismatch.append('/activity/' + phase + ':task_set_differs')
                snapshots = {n['task_id']: n['snapshot'] for n in direct[phase]}
                for ident in set(rows) & expected:
                    snapshot = snapshots[ident]
                    if snapshot is None or c.digest(rows[ident]) != c.digest({k: snapshot[k] for k in FIELDS}):
                        mismatch.append('/activity/' + phase + ':task_get_differs')
        if c.digest(samples['before']) != c.digest(samples['after']): mismatch.append('/activity:changed_during_snapshot')
        status = 'DIFFERENT' if mismatch else 'MATCH'
    except (ValueError, TypeError, KeyError, IndexError): mismatch = ['/activity:unknown_or_incomplete']
    return dict(resource_key=KEY, identity_match=status != 'UNKNOWN', config_status=status,
        progress='UNKNOWN' if status == 'UNKNOWN' else 'COMPLETE', mismatch_fields=mismatch,
        config_sha256=c.digest(evidence), activity_witness=evidence, task_completion_observed=False,
        reason=reason)

