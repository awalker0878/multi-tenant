"""Scoped history queries must include earlier pending work and late completions."""
from datetime import timedelta
import unittest
from unittest.mock import patch
from lab.native_readback_fixture import Fixture
from tests.test_vsphere_history import routes
from provisioner.execution import readback_core as c
from tools import vsphere_history as h
from provisioner.execution.run_files import utcnow


class ActivityTransportTests(unittest.TestCase):
    def client(self, f, **changes):
        options = dict(vm_ids=['vm-2', 'vm-1'], since='2026-01-01T00:00:00Z') | changes
        return h.ActivityClient(f.origin, f.origin, 'fixture-session', {'/allowed'}, 'TaskManager', ['task-1'],
                                str(f.directory / 'ca.pem'), **options)
    def test_exact_vm_pending_then_completed_filters_and_cleanup_over_tls(self):
        with Fixture() as f:
            create, read, destroy = routes(f, []); filters = []; pages = []
            def collect(body):
                filters.append(body['filter']); pages[:] = [[{'key': 'task-' + str(len(filters))}], []]
                return {'body': {'type': 'TaskHistoryCollector', 'value': 'collector-1'}}
            f.post_routes[create] = collect; f.post_routes[read] = lambda _: {'body': pages.pop(0)}
            result = self.client(f).activity()
            self.assertEqual(set(result), {'vm-1', 'vm-2'})
            for index, identity in enumerate(('vm-1', 'vm-2')):
                entity = {'entity': {'type': 'VirtualMachine', 'value': identity}, 'recursion': 'self'}
                self.assertEqual(filters[2 * index], {'entity': entity, 'state': ['queued', 'running']})
                self.assertEqual(filters[2 * index + 1], {'entity': entity, 'state': ['success', 'error'],
                    'time': {'timeType': 'completedTime', 'beginTime': '2026-01-01T00:00:00Z'}})
            self.assertEqual(sum(r['path'] == destroy for r in f.requests), 4)
            self.assertTrue(all(r['has_session_auth'] and r['path'] in {create, read, destroy} for r in f.requests))
    def test_scope_is_validated_before_contact(self):
        with Fixture() as f:
            for changes in ({'vm_ids': []}, {'vm_ids': ['vm-1', 'vm-1']}, {'vm_ids': ['group-1']},
                            {'vm_ids': ['../vm-1']}, {'since': (utcnow() + timedelta(days=1)).isoformat()}):
                with self.assertRaises(ValueError): self.client(f, **changes)
            self.assertEqual(f.requests, [])
    def test_total_activity_budget_is_shared_across_queries(self):
        with Fixture() as f:
            client = self.client(f)
            with patch.object(client, '_collect', side_effect=[[{'key': 'task-' + str(i)} for i in range(100)], [{'key': 'task-101'}]]):
                with self.assertRaises(c.ObservationError): client.activity()
            self.assertEqual(f.requests, [])
    def test_page_failure_destroys_collector_and_stops_following_queries(self):
        with Fixture() as f:
            create, read, destroy = routes(f, [])
            f.post_routes[read] = {'status': 503}
            with self.assertRaises(c.ObservationError): self.client(f).activity()
            self.assertEqual([r['path'] for r in f.requests], [create, read, destroy])


if __name__ == '__main__': unittest.main()
