"""vCenter native facts enter campaign evidence without inventing visibility."""
from dataclasses import replace
from datetime import timedelta
import unittest

from provisioner.controlplane.discovery.adapters.vmware_rest import (
    API_RELEASE, PROFILE, RestResponse, collect_vmware_vms, enumerate_visible_vms)
from provisioner.controlplane.discovery.model import DiscoveryCampaignAuthorization, assemble_discovery_result
from provisioner.controlplane.discovery.normalization import normalize_discovery
from tests.provisioning.controlplane.test_ahv_discovery import NOW
from tests.provisioning.discovery.test_vmware_rest import SCOPE, SELECTED, VM1, IDENTITIES

SELECTION = replace(SELECTED, folder_ids=('group-v1',))
LIST = '/api/vcenter/vm?folders=group-v1&datacenters=datacenter-1'
DETAIL = '/api/vcenter/vm/vm-101'


def detail():
    return {'name': VM1['name'], 'identity': {'instance_uuid': IDENTITIES['vm-101']},
            'power_state': VM1['power_state'], 'guest_os': 'OTHER_64',
            'cpu': {'count': 2, 'cores_per_socket': 1}, 'memory': {'size_mib': 4096},
            'boot': {'type': 'EFI', 'efi_legacy_boot': False},
            'disks': {'2000': {'type': 'SCSI', 'scsi': {'bus': 0, 'unit': 0},
                               'backing': {'type': 'VMDK_FILE', 'vmdk_file': '[datastore] private/path.vmdk'},
                               'capacity': 100 * 1024**3}},
            'nics': {'4000': {'type': 'VMXNET3', 'mac_address': '02:00:00:00:00:01',
                              'state': 'CONNECTED', 'start_connected': True,
                              'backing': {'type': 'STANDARD_PORTGROUP', 'network': 'network-42'}}}}


def campaign(**changes):
    c = DiscoveryCampaignAuthorization('campaign-vmware', SCOPE, 'review-1', PROFILE,
        ('vm',), NOW, NOW + timedelta(minutes=5), 3, 10, 1)
    return replace(c, **changes)


class Transport:
    scope = SCOPE
    api_release = API_RELEASE
    read_only = True

    def __init__(self, value=None, overrides=None):
        self.responses = {LIST: RestResponse(200, [dict(VM1)]),
                          DETAIL: RestResponse(200, value if value is not None else detail())}
        self.responses.update(overrides or {})
        self.calls = []

    def get(self, path):
        self.calls.append(path)
        answer = self.responses[path]
        if isinstance(answer, Exception):
            raise answer
        return answer


def observed(value=None, **kwargs):
    config = kwargs.pop('config', campaign())
    transport = Transport(value, kwargs.pop('overrides', None))
    pages = collect_vmware_vms(config, SELECTION, transport, clock=kwargs.pop('clock', lambda: NOW))
    result = assemble_discovery_result(config, pages, checked_at=NOW)
    facts = {f.name: f for f in result.objects[0].facts} if result.objects else {}
    return result, facts, transport


class VmwareHardwareTests(unittest.TestCase):
    def test_native_hardware_flows_into_campaign_and_normalization(self):
        result, facts, transport = observed()
        self.assertEqual(transport.calls, [LIST, DETAIL])
        self.assertEqual(result.completeness, 'PARTIAL')
        self.assertIn('VISIBLE_INVENTORY_ONLY', result.collection_errors)
        normalized = normalize_discovery(result)
        values = {f.name: f for f in normalized.inventory.objects[0].facts}
        self.assertEqual(values['vcpuCount'].value(), 2)
        self.assertEqual(values['memorySizeBytes'].value(), 4096 * 1024**2)
        self.assertEqual(values['diskCapacityBytes'].value(), 100 * 1024**3)
        self.assertEqual(values['firmware'].value(), 'uefi')
        self.assertEqual(values['diskLayout'].value(), [
            {'extId': '2000', 'busType': 'SCSI', 'bus': 0, 'unit': 0}])
        self.assertEqual(values['networkBindings'].value(), [
            {'nativeNicId': '4000', 'nativeNetworkId': 'network-42'}])
        self.assertEqual(values['instanceUuid'].value(), IDENTITIES['vm-101'])
        self.assertEqual(values['nativeFolderId'].value(), 'group-v1')
        self.assertEqual(values['folderCoverageDigest'].value(), SELECTION.coverage_digest)
        self.assertEqual(normalized.binding()['rawSnapshotDigest'], result.digest)

    def test_rest_does_not_invent_soap_or_guest_security_facts(self):
        value = detail()
        value['boot']['efiSecureBootEnabled'] = True  # SOAP field is not this REST contract
        value['vtpmEnabled'] = True
        value['architecture'] = 'x86_64'
        _, facts, _ = observed(value)
        for name in ('architecture', 'vtpmEnabled', 'secureBootEnabled', 'sharedDisks',
                     'storageEncrypted', 'passthroughDevices'):
            self.assertEqual(facts[name].state, 'UNKNOWN')
        self.assertEqual(facts['nativeGuestOS'].value(), 'OTHER_64')
        self.assertNotIn('guestProfile', facts)

    def test_native_device_id_is_scoped_to_vm_not_used_as_boot_order(self):
        value = detail()
        value['disks']['1000'] = {'type': 'SCSI', 'scsi': {'bus': 0, 'unit': 3},
                                 'backing': {'type': 'VMDK_FILE'}, 'capacity': 12}
        _, facts, _ = observed(value)
        self.assertEqual(facts['diskLayout'].value()[0]['extId'], '1000')
        self.assertEqual(facts['diskLayout'].value()[0]['unit'], 3)
        self.assertNotIn('bootOrder', facts)

    def test_duplicate_controller_slot_or_mac_is_unknown(self):
        value = detail(); value['disks']['2001'] = dict(value['disks']['2000'])
        self.assertEqual(observed(value)[1]['diskLayout'].state, 'UNKNOWN')
        value = detail(); value['nics']['4001'] = dict(value['nics']['4000'])
        self.assertEqual(observed(value)[1]['nicHardware'].state, 'UNKNOWN')

    def test_opaque_network_and_display_name_are_not_network_resource_ids(self):
        value = detail()
        value['nics']['4000']['backing'] = {'type': 'OPAQUE_NETWORK', 'network_name': 'network-42',
                                           'opaque_network_id': 'opaque-42', 'distributed_port': '42'}
        result, facts, _ = observed(value)
        self.assertEqual(facts['networkBindings'].state, 'UNKNOWN')
        norm = {f.name: f for f in normalize_discovery(result).inventory.objects[0].facts}
        self.assertEqual(norm['networkBindings'].state, 'UNKNOWN')

    def test_invalid_or_oversized_device_facts_are_not_silently_truncated(self):
        for raw in ([], {'x': None}, {str(i): {} for i in range(257)}):
            value = detail(); value['disks'] = raw
            with self.subTest(raw=str(raw)[:30]):
                self.assertEqual(observed(value)[1]['disks'].state, 'UNKNOWN')
        value = detail(); value['disks'] = {
            str(i): {'type': 'SCSI', 'scsi': {'bus': 0, 'unit': i},
                     'capacity': 1, 'backing': {'type': 'VMDK_FILE'}} for i in range(200)}
        result, facts, _ = observed(value)
        self.assertEqual(len(result.objects), 1)
        self.assertEqual(facts['disks'].reason, 'COLLECTION_ERROR')

    def test_capacity_overflow_boolean_and_missing_are_not_numbers(self):
        for capacity in (True, -1, 2**63, '100', None):
            value = detail(); value['disks']['2000']['capacity'] = capacity
            with self.subTest(capacity=capacity):
                self.assertEqual(observed(value)[1]['diskCapacityBytes'].state, 'UNKNOWN')
        value = detail(); value['memory']['size_mib'] = 2**63 - 1
        # No summary memory field: exercise detail's own bounded conversion.
        result, facts, _ = observed(value, overrides={LIST: RestResponse(200, [{'vm': VM1['vm'], 'name': VM1['name']}])})
        self.assertEqual(facts['memorySizeBytes'].state, 'UNKNOWN')

    def test_disconnected_false_and_explicit_empty_devices_are_retained(self):
        value = detail(); value['nics']['4000']['start_connected'] = False
        self.assertIs(observed(value)[1]['nicHardware'].value()[0]['startConnected'], False)
        value = detail(); value['disks'] = {}; value['nics'] = {}
        _, facts, _ = observed(value)
        self.assertEqual(facts['diskCapacityBytes'].value(), 0)
        self.assertEqual(facts['networkBindings'].value(), [])
        del value['disks']; del value['nics']
        self.assertEqual(observed(value)[1]['networkBindings'].state, 'UNKNOWN')

    def test_secrets_and_backing_paths_are_not_ingested_and_facts_are_immutable(self):
        value = detail(); value['extraConfig'] = {'password': 'must-not-leak'}
        value['nics']['4000']['backing']['password'] = 'must-not-leak'
        result, facts, _ = observed(value)
        self.assertNotIn('must-not-leak', repr(result))
        self.assertNotIn('private/path', repr(result))
        value['cpu']['count'] = 100
        self.assertEqual(facts['vcpuCount'].value(), 2)
        nics = facts['nics'].value(); nics.clear()
        self.assertEqual(len(facts['nics'].value()), 1)

    def test_list_detail_configuration_race_discards_scan(self):
        for key, changed in (('cpu', {'count': 99}), ('memory', {'size_mib': 99}),
                              ('power_state', 'POWERED_OFF')):
            value = detail(); value[key] = changed
            with self.subTest(key=key):
                result, _, _ = observed(value)
                self.assertEqual(result.objects, ())
                self.assertEqual(result.completeness, 'UNKNOWN')
                self.assertIn('NATIVE_READ_INCONCLUSIVE', result.collection_errors)

    def test_native_error_or_empty_visible_list_never_proves_empty_inventory(self):
        for answer in (RestResponse(403, {}), RuntimeError('must-not-leak')):
            result, _, _ = observed(overrides={DETAIL: answer})
            self.assertEqual(result.completeness, 'UNKNOWN')
            self.assertEqual(result.objects, ())
            self.assertNotIn('must-not-leak', repr(result))
        result, _, transport = observed(overrides={LIST: RestResponse(200, [])})
        self.assertEqual(result.completeness, 'PARTIAL')
        self.assertEqual(result.objects, ())
        self.assertEqual(transport.calls, [LIST])

    def test_hardware_and_folder_review_changes_change_snapshot_digest(self):
        base = detail(); transport = Transport(base)
        def scan(selection=SELECTION):
            return enumerate_visible_vms(selection, lambda s, p, r: transport.get(p), clock=lambda: NOW)
        result = scan()
        self.assertEqual(result.digest, scan().digest)
        base['boot']['type'] = 'BIOS'
        self.assertNotEqual(result.digest, scan().digest)
        self.assertNotEqual(scan().digest, scan(replace(SELECTION, coverage_digest='b' * 64)).digest)
        self.assertFalse(result.native_qualified)
        self.assertFalse(result.ownership_accepted)

    def test_scope_role_release_and_old_profile_reject_before_get(self):
        c = campaign()
        for field, wrong in (('scope', replace(SCOPE, tenant_id='other')),
                              ('read_only', False), ('api_release', '9.0.0.0')):
            transport = Transport(); setattr(transport, field, wrong)
            with self.subTest(field=field), self.assertRaises(ValueError):
                collect_vmware_vms(c, SELECTION, transport, clock=lambda: NOW)
            self.assertEqual(transport.calls, [])
        for bad in (replace(c, collector_id='vcenter-rest-vm-list-8.0.3.0-visible-only'),
                    replace(c, allowed_kinds=('disk',)), replace(c, scope=replace(SCOPE, site_id='other'))):
            transport = Transport()
            with self.assertRaises(ValueError):
                collect_vmware_vms(bad, SELECTION, transport, clock=lambda: NOW)
            self.assertEqual(transport.calls, [])

    def test_expiry_before_or_during_read_cannot_publish_late_evidence(self):
        c = campaign()
        transport = Transport()
        with self.assertRaises(ValueError):
            collect_vmware_vms(c, SELECTION, transport, clock=lambda: c.expires_at)
        self.assertEqual(transport.calls, [])
        times = iter([NOW, NOW, c.expires_at, c.expires_at])
        with self.assertRaises(ValueError):
            collect_vmware_vms(c, SELECTION, transport, clock=lambda: next(times))
        self.assertEqual(transport.calls, [LIST])

    def test_multiple_emitted_pages_are_a_single_bound_visible_snapshot(self):
        second = detail()
        second['name'] = 'Second VM'
        second['identity']['instance_uuid'] = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'
        transport = Transport(overrides={
            LIST: RestResponse(200, [dict(VM1), dict(VM1, vm='vm-102', name='Second VM')]),
            '/api/vcenter/vm/vm-102': RestResponse(200, second)})
        c = campaign()
        pages = collect_vmware_vms(c, SELECTION, transport, clock=lambda: NOW)
        self.assertEqual([p.requested_cursor for p in pages], [None, '1'])
        self.assertEqual([p.next_cursor for p in pages], ['1', None])
        result = assemble_discovery_result(c, pages, checked_at=NOW)
        self.assertEqual(result.completeness, 'PARTIAL')
        self.assertEqual(len(result.objects), 2)
        self.assertEqual(result.authorization_digest, c.digest())
        self.assertEqual([o.identity.native_id for o in result.objects], ['vm-101', 'vm-102'])
        self.assertEqual(transport.calls, [LIST, DETAIL, '/api/vcenter/vm/vm-102'])

    def test_page_and_object_budgets_are_checked_before_detail_read(self):
        transport = Transport(overrides={LIST: RestResponse(200, [dict(VM1), dict(VM1, vm='vm-102')])})
        pages = collect_vmware_vms(campaign(max_pages=1, max_page_size=1), SELECTION,
                                   transport, clock=lambda: NOW)
        self.assertEqual(pages[0].terminal_completeness, 'UNKNOWN')
        self.assertEqual(transport.calls, [LIST, DETAIL])


if __name__ == '__main__':
    unittest.main()
