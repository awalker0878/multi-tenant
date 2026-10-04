"""Exact-project, bounded read-only OpenStack collection adversarial cases."""
from __future__ import annotations

import copy
import unittest
from datetime import datetime, timedelta, timezone

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.discovery.model import (
    DiscoveryCampaignAuthorization, assemble_discovery_result)
from provisioner.controlplane.discovery.adapters.openstack import (
    OpenStackDiscoveryHeld, OpenStackHTTPError, OpenStackServiceEndpoints,
    collect_openstack_project)


PROJECT = '11111111111111111111111111111111'
OTHER = '22222222222222222222222222222222'
VM1 = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
VM2 = 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'
VM3 = 'cccccccccccccccccccccccccccccccc'
VOLUME = 'dddddddddddddddddddddddddddddddd'
PORT = 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee'
SCOPE = PlanScope('org-01', 'tenant-01', 'site-01', 'wsd-01', 'endpoint-01',
                  PROJECT, 'openstack')
ENDPOINTS = OpenStackServiceEndpoints(
    'endpoint-01', PROJECT,
    f'https://nova.site.example/v2.1/{PROJECT}',
    f'https://cinder.site.example/v3/{PROJECT}',
    'https://neutron.site.example/v2.0',
    'https://glance.site.example/v2')


def campaign(*, page_size=2, max_pages=20, max_objects=100):
    now = datetime.now(timezone.utc)
    return DiscoveryCampaignAuthorization(
        'campaign-01', SCOPE, 'approval-01', 'site-worker-01',
        ('vm', 'volume', 'nic', 'quota', 'image'), now - timedelta(minutes=1),
        now + timedelta(minutes=10), max_pages, max_objects, page_size)


def responses():
    return {
        (ENDPOINTS.compute, 'servers/detail', None): {
            'servers': [{'id': VM1, 'tenant_id': PROJECT, 'name': 'app',
                         'status': 'ACTIVE',
                         'locked': False,'OS-EXT-STS:vm_state':'active','OS-EXT-STS:task_state':None,
                         'OS-EXT-STS:power_state':1,'OS-EXT-AZ:availability_zone':'az-1',
                         'flavor': {'vcpus': 4, 'ram': 8192, 'disk': 20,
                                    'ephemeral': 0, 'swap': 0},
                         'image': {'id': VM3},
                         'os-extended-volumes:volumes_attached': [
                             {'id': VOLUME, 'delete_on_termination': False}]}]},
        (ENDPOINTS.volume, 'volumes/detail', None): {
            'volumes': [{'id': VOLUME, 'os-vol-tenant-attr:tenant_id': PROJECT,
                         'name': 'data', 'status': 'in-use', 'size': 50,
                         'encrypted': True, 'multiattach': False, 'volume_type': 'encrypted',
                         'attachments': [{'attachment_id': VM2, 'volume_id': VOLUME,
                                          'server_id': VM1, 'device': '/dev/vdb'}]}]},
        (ENDPOINTS.network, 'ports', None): {
            'ports': [{'id': PORT, 'project_id': PROJECT,
                       'network_id': VM2, 'device_id': VM1, 'status': 'ACTIVE',
                       'port_security_enabled': True, 'binding:vnic_type': 'normal',
                       'binding:vif_type': 'ovs', 'security_groups': [VM3],
                       'mac_address': '02:00:00:00:00:01', 'qos_policy_id': None,
                       'allowed_address_pairs': [],
                       'fixed_ips': [{'subnet_id': VM3, 'ip_address': '10.1.0.4'}]}]},
        (ENDPOINTS.compute, f'os-quota-sets/{PROJECT}', None): {
            'quota_set': {'id': PROJECT, 'instances': 12, 'cores': 40,
                          'ram': 65536}},
        (ENDPOINTS.volume, f'os-quota-sets/{PROJECT}', None): {
            'quota_set': {'id': PROJECT, 'volumes': 30, 'gigabytes': 1024}},
        (ENDPOINTS.network, f'quotas/{PROJECT}', None): {
            'quota': {'network': 10, 'subnet': 10, 'port': 50}},
        (ENDPOINTS.image, f'images/{VM3}', None): {
            'id': VM3, 'name': 'ubuntu-golden', 'status': 'active',
            'disk_format': 'qcow2', 'container_format': 'bare', 'size': 2147483648,
            'virtual_size': 4294967296, 'min_disk': 20, 'min_ram': 2048,
            'visibility': 'shared', 'owner': OTHER, 'protected': True, 'os_hidden': False,
            'os_hash_algo': 'sha512', 'os_hash_value': 'a'*128,
            'architecture': 'x86_64', 'os_distro': 'ubuntu',
            'hw_machine_type': 'q35', 'hw_firmware_type': 'uefi', 'hw_disk_bus': 'scsi',
            'hw_vif_model': 'virtio', 'hw_scsi_model': 'virtio-scsi',
            'hw_qemu_guest_agent': 'yes', 'hw_vif_multiqueue_enabled': 'true',
            'os_secure_boot': 'required'},
    }


class FakeTransport:
    bound_scope = SCOPE
    authenticated_project_id = PROJECT

    def __init__(self, values=None):
        self.values = responses() if values is None else values
        self.calls = []

    def get_json(self, endpoint, path, params):
        self.calls.append((endpoint, path, dict(params)))
        key = (endpoint, path, params.get('marker'))
        result = self.values[key]
        if isinstance(result, Exception):
            raise result
        return copy.deepcopy(result)


class OpenStackDiscoveryTests(unittest.TestCase):
    def _collected(self, values):
        authority = campaign()
        pages = collect_openstack_project(authority, ENDPOINTS, FakeTransport(values))
        return assemble_discovery_result(authority, pages, checked_at=datetime.now(timezone.utc))

    def test_native_port_security_and_volume_properties_are_observed_not_qualified(self):
        result = self._collected(responses())
        facts = {obj.identity.resource_kind: {f.name: f.value() for f in obj.facts}
                 for obj in result.objects if obj.identity.resource_kind != 'quota'}
        self.assertIs(facts['volume']['encrypted'], True)
        self.assertIs(facts['volume']['multiattach'], False)
        self.assertEqual(facts['nic']['security_groups'], [VM3])
        self.assertEqual(facts['nic']['binding_vnic_type'], 'normal')
        self.assertIsNone(facts['nic']['qos_policy_id'])
        self.assertNotIn('capabilityProperties', facts['nic'])
        self.assertNotIn('nativeQualified', facts['volume'])
        self.assertEqual(facts['image']['diskFormat'], 'qcow2')
        self.assertEqual(facts['image']['hashAlgorithm'], 'sha512')
        self.assertEqual(facts['image']['ownerId'], OTHER)
        self.assertEqual(facts['image']['minDiskBytes'], 20 * 1024**3)
        self.assertNotIn('compatible', facts['image'])
        self.assertNotIn('guestDriverReady', facts['image'])

    def test_exact_extended_server_states_are_observations_and_omission_is_unknown(self):
        values=responses();server=values[(ENDPOINTS.compute,'servers/detail',None)]['servers'][0]
        result=self._collected(values);facts={fact.name:fact for fact in next(obj for obj in result.objects if obj.identity.resource_kind=='vm').facts}
        self.assertIs(facts['locked'].value(),False);self.assertIsNone(facts['nativeTaskState'].value())
        self.assertEqual(facts['nativePowerState'].value(),1)
        del server['OS-EXT-STS:power_state']
        result=self._collected(values);facts={fact.name:fact for fact in next(obj for obj in result.objects if obj.identity.resource_kind=='vm').facts}
        self.assertEqual(facts['nativePowerState'].state,'UNKNOWN');self.assertEqual(result.completeness,'PARTIAL')
        for value in (True,'1',-1,2,2**63):
            server['OS-EXT-STS:power_state']=value
            with self.subTest(value=value),self.assertRaises((ValueError,OpenStackDiscoveryHeld)):self._collected(values)


    def test_referenced_image_metadata_is_bounded_observation_not_compatibility(self):
        values = responses()
        image = values[(ENDPOINTS.image, f'images/{VM3}', None)]
        result = self._collected(values)
        obj = next(row for row in result.objects if row.identity.resource_kind == 'image')
        facts = {fact.name: fact for fact in obj.facts}
        self.assertEqual(facts['sizeBytes'].value(), image['size'])
        self.assertEqual(facts['virtualSizeBytes'].value(), image['virtual_size'])
        self.assertEqual(facts['architecture'].value(), 'x86_64')
        self.assertEqual(facts['hwFirmwareType'].value(), 'uefi')
        self.assertEqual(facts['hwVifModel'].value(), 'virtio')
        self.assertEqual(facts['hwScsiModel'].value(), 'virtio-scsi')
        self.assertEqual(facts['hwQemuGuestAgent'].value(), 'yes')
        self.assertEqual(facts['hwVifMultiqueueEnabled'].value(), 'true')
        self.assertEqual(facts['osSecureBoot'].value(), 'required')
        self.assertNotIn('checksum', facts)
        self.assertNotIn('compatible', facts)
        self.assertNotIn('nativeQualified', facts)

    def test_image_guest_driver_and_secure_boot_metadata_remain_typed_observations(self):
        for field, invalid in (
                ('hw_scsi_model', 'lsi'),
                ('hw_qemu_guest_agent', 'enabled'),
                ('hw_vif_multiqueue_enabled', True),
                ('hw_vif_multiqueue_enabled', 'TRUE'),
                ('os_secure_boot', 'yes'),
                ('hw_vif_model', ''),
                ('hw_vif_model', 'x' * 129)):
            values = responses()
            values[(ENDPOINTS.image, f'images/{VM3}', None)][field] = invalid
            with self.subTest(field=field, invalid=invalid), self.assertRaises(OpenStackDiscoveryHeld):
                self._collected(values)

        values = responses()
        image = values[(ENDPOINTS.image, f'images/{VM3}', None)]
        for field in ('hw_vif_model', 'hw_scsi_model', 'hw_qemu_guest_agent',
                      'hw_vif_multiqueue_enabled', 'os_secure_boot'):
            del image[field]
        result = self._collected(values)
        facts = {fact.name: fact for obj in result.objects
                 if obj.identity.resource_kind == 'image' for fact in obj.facts}
        for name in ('hwVifModel', 'hwScsiModel', 'hwQemuGuestAgent',
                     'hwVifMultiqueueEnabled', 'osSecureBoot'):
            self.assertEqual(facts[name].state, 'UNKNOWN')

    def test_image_hash_pair_and_referenced_identity_fail_closed(self):
        for change in (
            lambda row: row.pop('os_hash_value'),
            lambda row: row.update(os_hash_algo='SHA-512'),
            lambda row: row.update(os_hash_value='xyz'),
            lambda row: row.update(id=OTHER)):
            values = responses(); image = values[(ENDPOINTS.image, f'images/{VM3}', None)]
            change(image)
            with self.subTest(image=image), self.assertRaises(OpenStackDiscoveryHeld):
                self._collected(values)

    def test_volume_backed_vm_does_not_trigger_glance_read(self):
        values = responses()
        values[(ENDPOINTS.compute, 'servers/detail', None)]['servers'][0]['image'] = ''
        del values[(ENDPOINTS.image, f'images/{VM3}', None)]
        transport = FakeTransport(values); authority = campaign()
        pages = collect_openstack_project(authority, ENDPOINTS, transport)
        result = assemble_discovery_result(authority, pages, checked_at=datetime.now(timezone.utc))
        self.assertNotIn('image', {obj.identity.resource_kind for obj in result.objects})
        self.assertFalse(any(call[0] == ENDPOINTS.image for call in transport.calls))

    def test_image_page_budget_is_not_out_of_band(self):
        authority = campaign(max_pages=6)
        pages = collect_openstack_project(authority, ENDPOINTS, FakeTransport())
        self.assertEqual(pages[-1].terminal_completeness, 'PARTIAL')
        self.assertIn('PAGE_BUDGET_EXCEEDED', pages[-1].collection_errors)
        self.assertNotIn('image', {obj.identity.resource_kind for page in pages for obj in page.objects})

    def test_omitted_fields_remain_unknown_but_explicit_false_is_known(self):
        values = responses()
        port = values[(ENDPOINTS.network, 'ports', None)]['ports'][0]
        volume = values[(ENDPOINTS.volume, 'volumes/detail', None)]['volumes'][0]
        del port['binding:vif_type']
        del port['security_groups']
        del volume['multiattach']
        port['port_security_enabled'] = False
        result = self._collected(values)
        self.assertEqual(result.completeness, 'PARTIAL')
        facts = {obj.identity.resource_kind: {f.name: f for f in obj.facts} for obj in result.objects}
        self.assertEqual(facts['nic']['security_groups'].state, 'UNKNOWN')
        self.assertEqual(facts['nic']['binding_vif_type'].state, 'UNKNOWN')
        self.assertEqual(facts['volume']['multiattach'].state, 'UNKNOWN')
        self.assertIs(facts['nic']['port_security_enabled'].value(), False)
        self.assertEqual(facts['nic']['port_security_enabled'].state, 'KNOWN')

    def test_malformed_extension_types_and_relationships_abort_collection(self):
        for service, path, collection, field, value in (
            ('network', 'ports', 'ports', 'port_security_enabled', 1),
            ('network', 'ports', 'ports', 'binding:vnic_type', True),
            ('network', 'ports', 'ports', 'security_groups', [VM3, VM3]),
            ('network', 'ports', 'ports', 'security_groups', ['foreign-unresolved-id']),
            ('network', 'ports', 'ports', 'security_groups', [VM3] * 65),
            ('network', 'ports', 'ports', 'qos_policy_id', ''),
            ('volume', 'volumes/detail', 'volumes', 'encrypted', 'false'),
            ('volume', 'volumes/detail', 'volumes', 'multiattach', 0),
            ('volume', 'volumes/detail', 'volumes', 'size', 2**63),
        ):
            with self.subTest(field=field, value=value):
                values = responses()
                values[(ENDPOINTS.for_service(service), path, None)][collection][0][field] = value
                with self.assertRaises(OpenStackDiscoveryHeld):
                    self._collected(values)

    def test_address_sets_are_bounded_canonical_and_not_silently_broadened(self):
        values = responses()
        port = values[(ENDPOINTS.network, 'ports', None)]['ports'][0]
        port['allowed_address_pairs'] = [{'ip_address': '2001:0db8::/64',
                                         'mac_address': '02:AA:00:00:00:01', 'metadata': 'not copied'}]
        result = self._collected(values)
        nic = next(obj for obj in result.objects if obj.identity.resource_kind == 'nic')
        self.assertEqual(next(f.value() for f in nic.facts if f.name == 'allowed_address_pairs'),
                         [{'ip_address': '2001:db8::/64', 'mac_address': '02:aa:00:00:00:01'}])
        for field, invalid in (
            ('allowed_address_pairs', [{'ip_address': '10.1.0.9/24', 'mac_address': '02:00:00:00:00:01'}]),
            ('allowed_address_pairs', [{'ip_address': '10.0.0.0/24'}]),
            ('allowed_address_pairs', port['allowed_address_pairs'] * 2),
            ('allowed_address_pairs', port['allowed_address_pairs'] * 33),
            ('fixed_ips', [{'subnet_id': VM3, 'ip_address': 'fe80::1%eth0'}]),
            ('fixed_ips', [{'subnet_id': VM3, 'ip_address': '10.1.0.4'}] * 2),
            ('fixed_ips', [{}] * 33),
            ('mac_address', 'not-a-mac'),
        ):
            with self.subTest(field=field, invalid=invalid):
                changed = responses()
                changed[(ENDPOINTS.network, 'ports', None)]['ports'][0][field] = invalid
                with self.assertRaises(OpenStackDiscoveryHeld):
                    self._collected(changed)

    def test_sensitive_response_fields_are_not_imported_as_policy_evidence(self):
        values = responses()
        for service, path, collection in (('network', 'ports', 'ports'),
                                          ('volume', 'volumes/detail', 'volumes')):
            values[(ENDPOINTS.for_service(service), path, None)][collection][0].update(
                metadata={'capabilityProperties': {'distributed_firewall.enforcement': 'enforce'}},
                user_data='private', connection_info={'auth_password': 'private'})
        result = self._collected(values)
        names = {f.name for obj in result.objects for f in obj.facts}
        self.assertFalse(names & {'metadata', 'user_data', 'connection_info', 'capabilityProperties'})

    def test_read_only_complete_exact_project_and_stable_identities(self):
        authority = campaign()
        transport = FakeTransport()
        pages = collect_openstack_project(authority, ENDPOINTS, transport)
        result = assemble_discovery_result(authority, pages,
                                           checked_at=datetime.now(timezone.utc))
        self.assertEqual(result.completeness, 'COMPLETE')
        self.assertEqual(len(pages), 7)
        self.assertEqual({obj.identity.key() for obj in result.objects}, {
            ('endpoint-01', PROJECT, 'openstack', 'vm', VM1),
            ('endpoint-01', PROJECT, 'openstack', 'volume', VOLUME),
            ('endpoint-01', PROJECT, 'openstack', 'nic', PORT),
            ('endpoint-01', PROJECT, 'openstack', 'image', VM3),
            *{('endpoint-01', PROJECT, 'openstack', 'quota', service)
              for service in ('compute', 'volume', 'network')},
        })
        self.assertEqual(transport.calls[0],
                         (ENDPOINTS.compute, 'servers/detail',
                          {'limit': '2', 'all_tenants': 'false'}))
        self.assertEqual([call[1] for call in transport.calls[3:]], [
            f'os-quota-sets/{PROJECT}', f'os-quota-sets/{PROJECT}',
            f'quotas/{PROJECT}', f'images/{VM3}'])

    def test_native_marker_page_chain_and_link_are_not_followed(self):
        values = responses()
        complete = values[(ENDPOINTS.compute, 'servers/detail', None)]['servers'][0]
        values[(ENDPOINTS.compute, 'servers/detail', None)] = {
            'servers': [dict(complete, id=VM1, name='a'),
                        dict(complete, id=VM2, name='b')],
            'servers_links': [{'rel': 'next', 'href':
                f'{ENDPOINTS.compute}/servers/detail?limit=2&marker={VM2}'}],
        }
        values[(ENDPOINTS.compute, 'servers/detail', VM2)] = {
            'servers': [dict(complete, id=VM3, name='c')]}
        authority = campaign()
        transport = FakeTransport(values)
        pages = collect_openstack_project(authority, ENDPOINTS, transport)
        result = assemble_discovery_result(authority, pages,
                                           checked_at=datetime.now(timezone.utc))
        self.assertEqual(result.completeness, 'COMPLETE')
        self.assertEqual(len(pages), 8)
        self.assertEqual(transport.calls[1],
                         (ENDPOINTS.compute, 'servers/detail',
                          {'limit': '2', 'marker': VM2, 'all_tenants': 'false'}))

    def test_transport_binding_and_pinned_https_catalog_are_mandatory(self):
        transport = FakeTransport()
        transport.authenticated_project_id = OTHER
        with self.assertRaises(ValueError):
            collect_openstack_project(campaign(), ENDPOINTS, transport)
        self.assertFalse(transport.calls)
        with self.assertRaises(ValueError):
            OpenStackServiceEndpoints('endpoint-01', PROJECT,
                f'http://nova.site.example/v2.1/{PROJECT}',
                ENDPOINTS.volume, ENDPOINTS.network, ENDPOINTS.image)
        with self.assertRaises(ValueError):
            OpenStackServiceEndpoints('endpoint-01', PROJECT,
                f'https://nova.site.example/v2.1/{OTHER}',
                ENDPOINTS.volume, ENDPOINTS.network, ENDPOINTS.image)

    def test_foreign_or_unattributed_row_and_quota_are_never_ingested(self):
        for key, field in ((ENDPOINTS.compute, 'tenant_id'),
                           (ENDPOINTS.volume, 'os-vol-tenant-attr:tenant_id'),
                           (ENDPOINTS.network, 'project_id')):
            with self.subTest(service=key):
                values = responses()
                route = next(route for route in values if route[0] == key
                             and route[1] in ('servers/detail', 'volumes/detail', 'ports'))
                collection = next(iter(values[route]))
                values[route][collection][0][field] = OTHER
                with self.assertRaises(OpenStackDiscoveryHeld):
                    collect_openstack_project(campaign(), ENDPOINTS,
                                              FakeTransport(values))
        values = responses()
        values[(ENDPOINTS.volume, f'os-quota-sets/{PROJECT}', None)]['quota_set']['id'] = OTHER
        with self.assertRaises(OpenStackDiscoveryHeld):
            collect_openstack_project(campaign(), ENDPOINTS, FakeTransport(values))

    def test_privilege_loss_yields_partial_with_exact_service_gap(self):
        values = responses()
        values[(ENDPOINTS.volume, 'volumes/detail', None)] = OpenStackHTTPError(403)
        authority = campaign()
        transport = FakeTransport(values)
        pages = collect_openstack_project(authority, ENDPOINTS, transport)
        result = assemble_discovery_result(authority, pages,
                                           checked_at=datetime.now(timezone.utc))
        self.assertEqual(result.completeness, 'PARTIAL')
        self.assertEqual(result.collection_errors, ('volume.READ_DENIED',))
        self.assertEqual(result.missing_privileges, ('openstack.volume.read',))
        self.assertEqual(len(result.objects), 1)
        self.assertEqual(len(transport.calls), 2)

    def test_down_cell_incomplete_server_detail_is_not_complete(self):
        values = responses()
        values[(ENDPOINTS.compute, 'servers/detail', None)]['servers'][0].pop('status')
        authority = campaign()
        result = assemble_discovery_result(
            authority, collect_openstack_project(authority, ENDPOINTS,
                                                  FakeTransport(values)),
            checked_at=datetime.now(timezone.utc))
        self.assertEqual(result.completeness, 'PARTIAL')
        self.assertEqual(next(obj for obj in result.objects
                              if obj.identity.resource_kind == 'vm').facts[1].reason,
                         'NOT_RETURNED')

    def test_repeated_id_or_escape_link_aborts_without_result(self):
        for second in ({'servers': [{'id': VM1, 'tenant_id': PROJECT,
                                    'name': 'duplicate', 'status': 'ACTIVE'}]},
                       {'servers': [{'id': VM3, 'tenant_id': PROJECT,
                                    'name': 'new', 'status': 'ACTIVE'}],
                        'servers_links': [{'rel': 'next', 'href':
                            f'https://other.example/servers/detail?limit=2&marker={VM3}'}]}):
            values = responses()
            values[(ENDPOINTS.compute, 'servers/detail', None)]['servers'].append(
                {'id': VM2, 'tenant_id': PROJECT, 'name': 'b', 'status': 'ACTIVE'})
            values[(ENDPOINTS.compute, 'servers/detail', VM2)] = second
            with self.assertRaises(OpenStackDiscoveryHeld):
                collect_openstack_project(campaign(), ENDPOINTS,
                                          FakeTransport(values))

    def test_missing_project_or_native_page_over_limit_is_held(self):
        values = responses()
        values[(ENDPOINTS.volume, 'volumes/detail', None)]['volumes'][0].pop(
            'os-vol-tenant-attr:tenant_id')
        with self.assertRaises(OpenStackDiscoveryHeld):
            collect_openstack_project(campaign(), ENDPOINTS, FakeTransport(values))
        values = responses()
        values[(ENDPOINTS.compute, 'servers/detail', None)]['servers'] *= 3
        with self.assertRaises(OpenStackDiscoveryHeld):
            collect_openstack_project(campaign(), ENDPOINTS, FakeTransport(values))

    def test_missing_required_quota_limit_is_partial(self):
        values = responses()
        values[(ENDPOINTS.network, f'quotas/{PROJECT}', None)]['quota'].pop('port')
        authority = campaign()
        result = assemble_discovery_result(
            authority, collect_openstack_project(authority, ENDPOINTS,
                                                  FakeTransport(values)),
            checked_at=datetime.now(timezone.utc))
        self.assertEqual(result.completeness, 'PARTIAL')
        quota = next(obj for obj in result.objects
                     if obj.identity.resource_kind == 'quota'
                     and obj.identity.native_id == 'network')
        self.assertEqual(quota.facts[0].reason, 'NOT_RETURNED')

    def test_response_bounds_and_service_unavailable(self):
        values = responses()
        values[(ENDPOINTS.network, 'ports', None)] = OpenStackHTTPError(503)
        authority = campaign()
        result = assemble_discovery_result(
            authority, collect_openstack_project(authority, ENDPOINTS,
                                                  FakeTransport(values)),
            checked_at=datetime.now(timezone.utc))
        self.assertEqual(result.completeness, 'PARTIAL')
        self.assertEqual(result.collection_errors, ('network.READ_UNAVAILABLE',))
        self.assertEqual(result.missing_privileges, ())
        limited = campaign(max_pages=2)
        result = assemble_discovery_result(
            limited, collect_openstack_project(limited, ENDPOINTS, FakeTransport()),
            checked_at=datetime.now(timezone.utc))
        self.assertEqual(result.completeness, 'PARTIAL')
        self.assertEqual(result.collection_errors, ('PAGE_BUDGET_EXCEEDED',))
        self.assertEqual(len(result.objects), 2)
        limited = campaign(max_objects=1)
        result = assemble_discovery_result(
            limited, collect_openstack_project(limited, ENDPOINTS, FakeTransport()),
            checked_at=datetime.now(timezone.utc))
        self.assertEqual(result.completeness, 'PARTIAL')
        self.assertEqual(result.collection_errors, ('OBJECT_BUDGET_EXCEEDED',))
        self.assertEqual(len(result.objects), 1)


if __name__ == '__main__':
    unittest.main()
