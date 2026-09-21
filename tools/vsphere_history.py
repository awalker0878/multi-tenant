"""Scoped vSphere task-history queries; only session-local collector writes."""
import re
from urllib.parse import quote
from tools import readback_core as c, vsphere_observe as vm
from tools.run_files import require


class CollectorClient(c.ReadClient):
    """Scoped collectors without requiring a previously recorded parent task."""
    def __init__(self, endpoint, expected_origin, session, targets, task_manager_id, ca_file=None):
        c.identifier(task_manager_id)
        super().__init__(endpoint, expected_origin, None, None, targets, ca_file, budget=120, session_token=session)
        self.manager = task_manager_id

    def _collect(self, selected_filter):
        """Drain all pages, then destroy the collector; cleanup failure holds."""
        path = vm.PREFIX + 'TaskManager/' + self.manager + '/CreateCollectorForTasks'
        collector, _ = self._request('POST', path, {'filter': selected_filter})
        try:
            c.exact_keys(collector, {'type', 'value'}, {'_typeName'})
            require(collector['type'] == 'TaskHistoryCollector'
                    and collector.get('_typeName', 'ManagedObjectReference') == 'ManagedObjectReference'
                    and isinstance(collector['value'], str)
                    and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:\[\]-]{0,255}', collector['value']), 'Invalid collector reference')
        except (ValueError, TypeError):
            raise c.ObservationError('VSPHERE_COLLECTOR_IDENTITY_UNKNOWN') from None
        identifier = quote(collector['value'], safe='')
        tasks = []; seen = set()
        try:
            # A newly created collector starts at the oldest item. A short page
            # is not EOF: only an explicit empty page completes this scan.
            for _ in range(6):
                page, _ = self._request('POST', vm.PREFIX + 'TaskHistoryCollector/' + identifier + '/ReadNextTasks',
                                        {'maxCount': 20}, response_type=list)
                if not page: return tasks
                if len(page) > 20 or len(tasks) + len(page) > 100:
                    raise c.ObservationError('VSPHERE_TASK_HISTORY_LIMIT')
                for task in page:
                    key = task.get('key') if isinstance(task, dict) else None
                    if not isinstance(key, str) or key in seen:
                        raise c.ObservationError('VSPHERE_TASK_HISTORY_DUPLICATE_OR_INVALID')
                    seen.add(key)
                tasks.extend(page)
            raise c.ObservationError('VSPHERE_TASK_HISTORY_INCOMPLETE')
        finally:
            # This destroys only the collector just returned in this session.
            # Interrupted/failed cleanup still requires session-owner attention.
            self._request('POST', vm.PREFIX + 'HistoryCollector/' + identifier + '/DestroyCollector', no_content=True)


class Client(CollectorClient):
    """No general POST interface, task cancellation, power or configuration API."""
    def __init__(self, endpoint, expected_origin, session, targets, task_manager_id, parent_ids, ca_file=None):
        require(isinstance(parent_ids, list) and 1 <= len(parent_ids) <= 20 and len(set(parent_ids)) == len(parent_ids), 'Exact bounded parent set required')
        for task in parent_ids: vm.moid(task, 'task')
        super().__init__(endpoint, expected_origin, session, targets, task_manager_id, ca_file)
        self.parents = tuple(sorted(parent_ids))

    def children(self):
        return self._collect({'parentTaskKey': list(self.parents)})


class ActivityClient(Client):
    """Fixed exact-VM queries; no folder recursion or user/task-ID filters."""
    def __init__(self, *args, vm_ids, since, **kwargs):
        require(isinstance(vm_ids, list) and 1 <= len(vm_ids) <= 20, 'Exact bounded VM set required')
        for identity in vm_ids: vm.moid(identity, 'vm')
        require(len(set(vm_ids)) == len(vm_ids) and c.timestamp(since) <= c.timestamp(c.now()), 'Invalid activity scope/window')
        super().__init__(*args, **kwargs)
        self.vm_ids = tuple(sorted(vm_ids)); self.since = since

    def activity(self):
        result = {}; count = 0
        for identity in self.vm_ids:
            entity = {'entity': {'type': 'VirtualMachine', 'value': identity}, 'recursion': 'self'}
            result[identity] = {}
            # Read active work first, then completions. A task crossing the two
            # queries remains visible as a duplicate/changed witness and holds.
            for phase, selected in (
                ('pending', {'entity': entity, 'state': ['queued', 'running']}),
                ('completed', {'entity': entity, 'state': ['success', 'error'],
                               'time': {'timeType': 'completedTime', 'beginTime': self.since}})):
                rows = self._collect(selected); count += len(rows)
                if count > 100: raise c.ObservationError('VSPHERE_ACTIVITY_HISTORY_LIMIT')
                result[identity][phase] = rows
        return result
