"""Scoped vSphere task-history queries; only session-local collector writes."""
import re
from urllib.parse import quote
from tools import readback_core as c, vsphere_observe as vm
from tools.run_files import require


class Client(c.ReadClient):
    """No general POST interface, task cancellation, power or configuration API."""
    def __init__(self, endpoint, expected_origin, session, targets, task_manager_id, parent_ids, ca_file=None):
        c.identifier(task_manager_id)
        require(isinstance(parent_ids, list) and 1 <= len(parent_ids) <= 20 and len(set(parent_ids)) == len(parent_ids), 'Exact bounded parent set required')
        for task in parent_ids: vm.moid(task, 'task')
        super().__init__(endpoint, expected_origin, None, None, targets, ca_file, budget=120, session_token=session)
        self.manager = task_manager_id; self.parents = tuple(sorted(parent_ids))

    def children(self):
        """Drain all pages, then destroy the collector; cleanup failure holds."""
        path = vm.PREFIX + 'TaskManager/' + self.manager + '/CreateCollectorForTasks'
        collector, _ = self._request('POST', path, {'filter': {'parentTaskKey': list(self.parents)}})
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
