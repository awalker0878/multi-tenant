"""Real TLS source/result queries, collector cleanup and no mutation surface."""
from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from lab.native_readback_fixture import Fixture
from tests.test_vsphere_clone_activity import manifest, Client
from tests.test_vsphere_history import routes as history_routes
from provisioner.execution import readback_core as c
from tools import vsphere_task_tree_observe as tree, vsphere_task_activity as activity


def routes(f, m):
    client = Client(m); f.routes.update({key: dict(body=value) for key, value in client.routes.items()})
    existing = dict(f.post_routes); create, read, destroy = history_routes(f, []); f.post_routes.update(existing)
    pages = []; filters = []
    def collect(body):
        selected = body['filter']; filters.append(deepcopy(selected))
        if 'entity' in selected:
            identity = selected['entity']['entity']['value']
            phase = 'pending' if selected.get('state') == ['queued', 'running'] else 'completed'
            rows = client.activity_rows[identity][phase]
        else: rows = client.history
        # Include a short page and explicit EOF; each native collector is drained.
        pages[:] = [[deepcopy(row)] for row in rows] + [[]]
        return dict(body=dict(type='TaskHistoryCollector', value='collector-1'))
    f.post_routes[create] = collect; f.post_routes[read] = lambda _: dict(body=pages.pop(0))
    return client, filters, (create, read, destroy)


class CloneActivityTransportTests(unittest.TestCase):
    def client(self, m, f):
        with patch.dict('os.environ', VCENTER_SESSION='fixture-session'):
            return tree.make_client(m, SimpleNamespace(expected_origin=f.origin, ca_file=str(f.directory / 'ca.pem')))
    def test_exact_source_and_destination_queries_bracket_native_reads(self):
        with Fixture() as f:
            m = manifest(f.origin); _, filters, methods = routes(f, m)
            report = c.observe(m, self.client(m, f), tree, interval=0)
            self.assertEqual(report['outcome'], 'READBACK_MATCH_NOT_QUALIFIED')
            expected = []
            for identity in ('vm-1', 'vm-9'):
                entity = {'entity': {'type': 'VirtualMachine', 'value': identity}, 'recursion': 'self'}
                expected.extend([{'entity': entity, 'state': ['queued', 'running']},
                    {'entity': entity, 'state': ['success', 'error'], 'time': {'timeType': 'completedTime', 'beginTime': m['task']['activity_since']}}])
            children = {'parentTaskKey': ['task-1', 'task-2']}
            self.assertEqual(filters, (expected + [children, children] + expected) * 2)
            self.assertEqual(sum(r['path'] == methods[2] for r in f.requests), 20)
            self.assertEqual(set(r['path'] for r in f.requests if r['method'] == 'GET'), tree.targets(m))
            self.assertTrue(all(r['method'] == 'GET' or r['path'] in methods for r in f.requests))
            self.assertTrue(all(r['has_session_auth'] and not r['has_basic_auth'] for r in f.requests))
    def test_unreadable_source_activity_and_cleanup_failure_keep_observation_unknown(self):
        for failure in ('page', 'cleanup'):
            with Fixture() as f:
                m = manifest(f.origin); _, filters, methods = routes(f, m)
                method = methods[1 if failure == 'page' else 2]; original = f.post_routes[method]
                def respond(body):
                    if filters[-1].get('entity', {}).get('entity', {}).get('value') == 'vm-9': return dict(status=503)
                    return original(body) if callable(original) else original
                f.post_routes[method] = respond
                report = c.observe(m, self.client(m, f), tree, interval=0)
                self.assertEqual(report['outcome'], 'HOLD_UNCERTAIN')
                self.assertEqual(f.requests[-1]['path'], methods[2])
                self.assertFalse(any(r['method'] == 'GET' for r in f.requests))
    def test_omitted_source_root_is_not_an_empty_success(self):
        with Fixture() as f:
            m = manifest(f.origin); client, _, _ = routes(f, m); client.activity_rows['vm-9']['completed'].clear()
            self.assertEqual(c.observe(m, self.client(m, f), tree, interval=0)['outcome'], 'HOLD_DIFFERENCE')
    def test_source_omission_or_bad_window_cannot_create_a_collector(self):
        with Fixture() as f:
            for field in ('sources', 'activity_since'):
                m = manifest(f.origin); m['task'].pop(field)
                with self.assertRaises((ValueError, KeyError)): self.client(m, f)
            self.assertFalse(f.requests)


if __name__ == '__main__': unittest.main()
