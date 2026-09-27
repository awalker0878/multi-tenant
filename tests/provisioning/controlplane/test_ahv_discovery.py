"""Prism VMM enumeration contracts; no installed platform is simulated as qualified."""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.discovery.ahv import (API_VERSION, COLLECTOR_ID,
                                                   VM_PATH, collect_ahv_vms)
from provisioner.controlplane.discovery.model import (
    DiscoveryCampaignAuthorization, assemble_discovery_result)


NOW = datetime(2026, 9, 27, 18, 0, tzinfo=timezone.utc)
CLUSTER = '89f6ef24-1189-4bcb-8bea-14408b79ef10'
VM1 = 'db20fc83-8fe4-4138-a654-d181965f43d8'
VM2 = 'c916efcc-dae4-4528-908d-3a0d0968934a'
DISK = '8bf181c9-3886-4ae0-9775-c3f9953f4454'
NIC = '51d2749b-28d6-4d66-8745-888943ee4768'
SUBNET = '23225bf8-dbcf-40fd-a6f7-33a37673d522'


def scope(cluster: str = CLUSTER) -> PlanScope:
    return PlanScope('org-1', 'tenant-1', 'site-1', 'wsd-1', 'pc-1',
                     cluster, 'nutanix')


def campaign(*, pages: int = 3, page_size: int = 1, objects: int = 10):
    return DiscoveryCampaignAuthorization(
        'campaign-1', scope(), 'issued-1', COLLECTOR_ID, ('vm',), NOW,
        NOW + timedelta(minutes=5), pages, objects, page_size)


def vm(vm_id: str = VM1, *, native_cluster: str = CLUSTER) -> dict:
    return {
        'extId': vm_id, 'name': 'app-01', 'cluster': {'extId': native_cluster},
        'powerState': 'ON', 'numSockets': 1, 'numCoresPerSocket': 4,
        'memorySizeBytes': 8 * 1024**3,
        'disks': [{'extId': DISK, 'backingInfo': {
            '$objectType': 'vmm.v4.ahv.config.VmDisk',
            'diskSizeBytes': 100 * 1024**3,
            'storageContainer': {'extId': CLUSTER}}}],
        'nics': [{'extId': NIC, 'networkInfo': {'subnet': {'extId': SUBNET}}}],
    }


def response(data: list, total: int, *, next_page: int | None = None,
             limit: int = 1) -> dict:
    links = [{'rel': 'self', 'href': VM_PATH}]
    if next_page is not None:
        filters = f"cluster/extId eq '{CLUSTER}'"
        links.append({'rel': 'next', 'href': VM_PATH + '?' + urlencode({
            '$page': next_page, '$limit': limit, '$filter': filters})})
    return {'$objectType': 'vmm.v4.ahv.config.ListVmsApiResponse',
            'metadata': {'totalAvailableResults': total, 'links': links},
            'data': data}


class Transport:
    def __init__(self, responses, *, binding=None, version=API_VERSION,
                 read_only=True):
        self.scope = binding or scope()
        self.api_version = version
        self.read_only = read_only
        self.responses = iter(responses)
        self.calls = []

    def get(self, path, *, params):
        self.calls.append((path, dict(params)))
        answer = next(self.responses)
        if isinstance(answer, BaseException):
            raise answer
        return answer


class AhvDiscoveryTests(unittest.TestCase):
    def collect(self, config, responses):
        transport = Transport(responses)
        pages = collect_ahv_vms(config, transport, clock=lambda: NOW)
        result = assemble_discovery_result(config, pages, checked_at=NOW)
        return pages, result, transport

    def test_two_pages_use_exact_cluster_filter_and_stable_native_ids(self):
        c = campaign()
        pages, result, transport = self.collect(c, [
            (200, response([vm()], 2, next_page=1)),
            (200, response([vm(VM2)], 2))])
        self.assertEqual(result.completeness, 'COMPLETE')
        self.assertEqual([p.requested_cursor for p in pages], [None, '1'])
        self.assertEqual([x.identity.native_id for x in result.objects], [VM1, VM2])
        self.assertEqual(len(transport.calls), 2)
        for index, (path, params) in enumerate(transport.calls):
            self.assertEqual(path, VM_PATH)
            self.assertEqual(params, {'$page': index, '$limit': 1,
                                      '$filter': f"cluster/extId eq '{CLUSTER}'"})
        facts = {fact.name: fact for fact in result.objects[0].facts}
        self.assertEqual(facts['disks'].value()[0]['extId'], DISK)
        self.assertEqual(facts['diskCapacityBytes'].value(), 100 * 1024**3)
        self.assertEqual(facts['networkBindings'].value()[0]['subnetExtId'], SUBNET)

    def test_genuinely_empty_authorized_response_is_complete(self):
        _, result, transport = self.collect(campaign(), [(200, response([], 0))])
        self.assertEqual(result.completeness, 'COMPLETE')
        self.assertEqual(result.objects, ())
        self.assertEqual(len(transport.calls), 1)

    def test_no_response_during_permission_denial_is_not_an_empty_portfolio(self):
        _, result, _ = self.collect(campaign(), [(403, {'error': 'denied'})])
        self.assertEqual(result.completeness, 'UNKNOWN')
        self.assertIn('VM_LIST_READ', result.missing_privileges)
        self.assertIn('VM_LIST_PERMISSION_DENIED', result.collection_errors)

    def test_missing_disk_network_and_capacity_are_explicit_unknowns(self):
        sparse = vm()
        sparse.pop('disks')
        sparse['nics'] = [{'extId': NIC, 'networkInfo': {}}]
        _, result, _ = self.collect(campaign(), [(200, response([sparse], 1))])
        self.assertEqual(result.completeness, 'PARTIAL')
        facts = {f.name: f for f in result.objects[0].facts}
        for field in ('disks', 'diskCapacityBytes', 'networkBindings'):
            self.assertEqual((facts[field].state, facts[field].reason),
                             ('UNKNOWN', 'NOT_RETURNED'))

    def test_changed_total_and_truncated_page_do_not_prove_absence(self):
        for second in (response([], 2), response([vm(VM2)], 3)):
            with self.subTest(second=second['metadata']['totalAvailableResults']):
                _, result, _ = self.collect(campaign(), [
                    (200, response([vm()], 2)), (200, second)])
                self.assertEqual(result.completeness, 'UNKNOWN')
                self.assertEqual([o.identity.native_id for o in result.objects], [VM1])

    def test_duplicate_id_and_cross_cluster_row_are_held(self):
        for second in (vm(), vm(VM2, native_cluster=VM2)):
            with self.subTest(second=second):
                _, result, _ = self.collect(campaign(), [
                    (200, response([vm()], 2)), (200, response([second], 2))])
                self.assertEqual(result.completeness, 'UNKNOWN')
                self.assertEqual(len(result.objects), 1)

    def test_repeated_next_link_is_ignored_as_authority_and_rejected(self):
        _, result, transport = self.collect(campaign(), [
            (200, response([vm()], 2, next_page=0))])
        self.assertEqual(result.completeness, 'UNKNOWN')
        self.assertEqual(len(transport.calls), 1)
        self.assertIn('REPEATED_OR_CROSS_SCOPE_CURSOR', result.collection_errors)

    def test_warning_or_unexpected_next_link_never_claims_complete(self):
        warning = response([vm()], 1)
        warning['metadata']['messages'] = [
            {'severity': 'WARNING', 'message': 'partial privileges'}]
        next_after_end = response([vm()], 1, next_page=1)
        for payload in (warning, next_after_end):
            with self.subTest(payload=payload):
                _, result, _ = self.collect(campaign(), [(200, payload)])
                self.assertEqual(result.completeness, 'UNKNOWN')

    def test_page_budget_and_request_error_remain_incomplete(self):
        c = campaign(pages=1)
        pages, result, _ = self.collect(c, [(200, response([vm()], 2))])
        self.assertEqual(len(pages), 1)
        self.assertEqual(result.completeness, 'UNKNOWN')
        self.assertIn('PAGE_BUDGET_EXCEEDED', result.collection_errors)
        _, result, _ = self.collect(campaign(), [TimeoutError()])
        self.assertEqual(result.completeness, 'UNKNOWN')

    def test_wrong_version_scope_role_and_collector_cannot_call_transport(self):
        c = campaign()
        for transport in (Transport([], version='v4.1'),
                          Transport([], version='unknown'),
                          Transport([], binding=scope(VM2)),
                          Transport([], read_only=False)):
            with self.subTest(transport=transport):
                with self.assertRaises(ValueError):
                    collect_ahv_vms(c, transport, clock=lambda: NOW)
                self.assertEqual(transport.calls, [])
        wrong_collector = DiscoveryCampaignAuthorization(
            'campaign-1', c.scope, 'issued-1', 'other', ('vm',), NOW,
            c.expires_at, 3, 10, 1)
        with self.assertRaises(ValueError):
            collect_ahv_vms(wrong_collector, Transport([]), clock=lambda: NOW)

    def test_missing_vm_identity_and_malformed_envelope_are_unknown(self):
        for payload in (response([{'name': 'app'}], 1),
                        {'data': [], 'metadata': {}},
                        {'$objectType': 'vmm.v4.1.ListVmsApiResponse',
                         'data': [], 'metadata': {'totalAvailableResults': 0}}):
            with self.subTest(payload=payload):
                _, result, _ = self.collect(campaign(), [(200, payload)])
                self.assertEqual(result.completeness, 'UNKNOWN')


if __name__ == '__main__':
    unittest.main()
