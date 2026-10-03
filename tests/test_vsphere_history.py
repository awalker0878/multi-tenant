"""Actual TLS collector pagination/cleanup without native configuration writes."""
import unittest
from lab.native_readback_fixture import Fixture
from provisioner.execution import readback_core as c
from provisioner.execution import vsphere_history as h
from provisioner.execution import vsphere_observe as vm


def routes(f, pages):
    create = vm.PREFIX + 'TaskManager/TaskManager/CreateCollectorForTasks'
    read = vm.PREFIX + 'TaskHistoryCollector/collector-1/ReadNextTasks'
    destroy = vm.PREFIX + 'HistoryCollector/collector-1/DestroyCollector'
    f.post_routes = {create: {'body': {'type': 'TaskHistoryCollector', 'value': 'collector-1'}},
                    read: lambda _: {'body': pages.pop(0)}, destroy: {'status': 204}}
    return create, read, destroy


class HistoryTransportTests(unittest.TestCase):
    def client(self, f): return h.Client(f.origin, f.origin, 'fixture-session', {'/allowed'}, 'TaskManager', ['task-1'], str(f.directory / 'ca.pem'))
    def test_short_pages_are_drained_and_only_the_created_collector_is_destroyed(self):
        with Fixture() as f:
            create, read, destroy = routes(f, [[{'key': 'task-2'}], [{'key': 'task-3'}], []])
            self.assertEqual(self.client(f).children(), [{'key': 'task-2'}, {'key': 'task-3'}])
            self.assertEqual([r['path'] for r in f.requests], [create, read, read, read, destroy])
            self.assertEqual(f.post_bodies[0][1], {'filter': {'parentTaskKey': ['task-1']}})
            self.assertTrue(all(r['has_session_auth'] and not r['has_basic_auth'] for r in f.requests))
    def test_repeated_page_limit_and_cleanup_failures_hold(self):
        for mode in ('duplicate', 'limit', 'cleanup'):
            with Fixture() as f:
                create, read, destroy = routes(f, [[{'key': 'task-2'}], [{'key': 'task-2'}]])
                if mode == 'limit': f.post_routes[read] = {'body': [{'key': 'task-' + str(i)} for i in range(1, 22)]}
                if mode == 'cleanup': f.post_routes[read] = {'body': []}; f.post_routes[destroy] = {'status': 503}
                with self.subTest(mode=mode), self.assertRaises(c.ObservationError): self.client(f).children()
                self.assertEqual(f.requests[-1]['path'], destroy)
    def test_foreign_or_path_injected_collector_reference_never_followed(self):
        for ref in ({'type': 'VirtualMachine', 'value': 'vm-1'}, {'type': 'TaskHistoryCollector', 'value': '../vm-1'}):
            with Fixture() as f:
                create, _, _ = routes(f, [])
                f.post_routes[create] = {'body': ref}
                with self.assertRaises(c.ObservationError): self.client(f).children()
                self.assertEqual(len(f.requests), 1)
    def test_post_redirect_not_followed_and_existing_get_client_has_no_post_api(self):
        with Fixture() as f:
            create, _, _ = routes(f, [])
            f.post_routes[create] = {'status': 302, 'headers': [('Location', '/foreign')]}
            with self.assertRaises(c.ObservationError): self.client(f).children()
            self.assertEqual(len(f.requests), 1)
            self.assertFalse(hasattr(c.ReadClient, 'post'))
            with self.assertRaises(c.ObservationError): self.client(f).get('/unaccepted')


if __name__ == '__main__': unittest.main()
