"""vCenter REST's unpageable 4000-visible-VM limit is never completeness."""
from __future__ import annotations

from dataclasses import replace
import unittest

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.discovery.vmware import EnumerationHeld
from provisioner.controlplane.discovery.vmware_rest import (
    FolderSelection, RestResponse, enumerate_visible_vms,
)


SCOPE = PlanScope('org-a', 'tenant-a', 'site-a', 'wsd-a', 'vc-a',
                  'datacenter-1', 'vmware')
SELECTED = FolderSelection(SCOPE, ('group-v1', 'group-v2'), 'a' * 64)
VM1 = {'vm': 'vm-101', 'name': 'Old name', 'power_state': 'POWERED_ON',
       'cpu_count': 2, 'memory_size_mib': 4096}
VM2 = {'vm': 'vm-102', 'name': 'Database', 'power_state': 'POWERED_OFF',
       'cpu_count': 4, 'memory_size_mib': 8192}
IDENTITIES = {
    'vm-101': 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
    'vm-102': 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
}


class RestAdapterTests(unittest.TestCase):
    def _transport(self, overrides=None):
        requests = []
        responses = {
            '/api/vcenter/vm?folders=group-v1&datacenters=datacenter-1':
                RestResponse(200, [VM1]),
            '/api/vcenter/vm?folders=group-v2&datacenters=datacenter-1':
                RestResponse(200, [VM2]),
            '/api/vcenter/vm/vm-101': RestResponse(200, {
                'name': VM1['name'], 'identity': {'instance_uuid': IDENTITIES['vm-101']}}),
            '/api/vcenter/vm/vm-102': RestResponse(200, {
                'name': VM2['name'], 'identity': {'instance_uuid': IDENTITIES['vm-102']}}),
        }
        responses.update(overrides or {})

        def get(scope, path, release):
            requests.append((scope, path, release))
            return responses[path]

        return get, requests

    def test_exact_folder_and_datacenter_filters_then_detail_identity(self):
        get, requests = self._transport()
        result = enumerate_visible_vms(SELECTED, get)
        self.assertEqual(len(requests), 4)
        self.assertTrue(all(scope == SCOPE and release == '8.0.3.0'
                            for scope, _, release in requests))
        self.assertEqual([item.moid for item in result.items], ['vm-101', 'vm-102'])
        self.assertEqual(result.items[0].instance_uuid, IDENTITIES['vm-101'])
        self.assertEqual(result.status, 'SCOPED_VISIBLE_ONLY')
        self.assertFalse(result.native_qualified)
        self.assertFalse(result.ownership_accepted)
        self.assertEqual(result.folder_coverage_digest, 'a' * 64)

    def test_exactly_4000_visible_rows_is_ambiguous_and_holds(self):
        path = '/api/vcenter/vm?folders=group-v1&datacenters=datacenter-1'
        get, requests = self._transport({path: RestResponse(200, [VM1] * 4000)})
        with self.assertRaisesRegex(EnumerationHeld, 'unpageable'):
            enumerate_visible_vms(SELECTED, get)
        self.assertEqual(len(requests), 1)

    def test_partial_folder_or_vm_permission_failure_never_returns_partial_rows(self):
        for path in ('/api/vcenter/vm?folders=group-v2&datacenters=datacenter-1',
                     '/api/vcenter/vm/vm-102'):
            with self.subTest(path=path):
                get, _ = self._transport({path: RestResponse(403, {'error': 'denied'})})
                with self.assertRaisesRegex(EnumerationHeld, 'unavailable or unauthorized'):
                    enumerate_visible_vms(SELECTED, get)

    def test_folder_wire_shape_and_detail_identity_changes_hold(self):
        folder = '/api/vcenter/vm?folders=group-v1&datacenters=datacenter-1'
        detail = '/api/vcenter/vm/vm-101'
        for override in (
                {folder: RestResponse(200, {'value': [VM1]})},
                {folder: RestResponse(200, [{'name': 'Missing id'}])},
                {detail: RestResponse(200, {'name': 'Renamed during scan',
                                            'identity': {'instance_uuid': IDENTITIES['vm-101']}})},
                {detail: RestResponse(200, {'name': VM1['name']})},
                {detail: RestResponse(200, {'name': VM1['name'], 'identity': {}})},
        ):
            with self.subTest(override=override):
                get, _ = self._transport(override)
                with self.assertRaises(EnumerationHeld):
                    enumerate_visible_vms(SELECTED, get)

    def test_duplicate_across_folder_or_budget_holds(self):
        folder = '/api/vcenter/vm?folders=group-v2&datacenters=datacenter-1'
        get, _ = self._transport({folder: RestResponse(200, [VM1])})
        with self.assertRaisesRegex(EnumerationHeld, 'more than one'):
            enumerate_visible_vms(SELECTED, get)
        get, _ = self._transport()
        with self.assertRaisesRegex(EnumerationHeld, 'budget'):
            enumerate_visible_vms(SELECTED, get, max_vms=1)

    def test_folder_scope_and_version_are_explicit(self):
        get, _ = self._transport()
        for selection in (
                replace(SELECTED, scope=replace(SCOPE, platform_family='nutanix')),
                replace(SELECTED, scope=replace(SCOPE, native_scope_id='dc-a')),
                replace(SELECTED, folder_ids=()),
                replace(SELECTED, folder_ids=('group-v1', 'group-v1')),
                replace(SELECTED, folder_ids=('folder-with-untrusted-query&names=',)),
                replace(SELECTED, coverage_digest='unreviewed'),
                replace(SELECTED, api_release='9.0.0.0'),
        ):
            with self.subTest(selection=selection), self.assertRaises(ValueError):
                enumerate_visible_vms(selection, get)


if __name__ == '__main__':
    unittest.main()
