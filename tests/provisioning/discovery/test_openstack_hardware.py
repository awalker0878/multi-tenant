"""Nova 2.79/Cinder 3.60 facts retain units and uncertainty, not authority."""
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from provisioner.controlplane.discovery.adapters.openstack import (
    OpenStackDiscoveryHeld, collect_openstack_project)
from provisioner.controlplane.discovery.model import assemble_discovery_result
from provisioner.controlplane.discovery.normalization import normalize_discovery
from tests.provisioning.discovery.test_openstack import (
    ENDPOINTS, VM1, VM2, VM3, VOLUME, FakeTransport, campaign, responses)


def server(values):
    return values[(ENDPOINTS.compute, 'servers/detail', None)]['servers'][0]


def volume(values):
    return values[(ENDPOINTS.volume, 'volumes/detail', None)]['volumes'][0]


def collected(values):
    authority = campaign()
    transport = FakeTransport(values)
    pages = collect_openstack_project(authority, ENDPOINTS, transport)
    return assemble_discovery_result(authority, pages,
        checked_at=datetime.now(timezone.utc)), transport


def facts(result, kind='vm'):
    obj = next(obj for obj in result.objects if obj.identity.resource_kind == kind)
    return {fact.name: fact for fact in obj.facts}


class OpenStackHardwareTests(unittest.TestCase):
    def test_embedded_allocation_reaches_normalization_without_flavor_lookup(self):
        values = responses()
        server(values)['flavor'].update(ephemeral=7, swap=128)
        raw, transport = collected(values)
        normalized = normalize_discovery(raw)
        vm = facts(normalized.inventory)
        self.assertEqual(vm['vcpuCount'].value(), 4)
        self.assertEqual(vm['memorySizeBytes'].value(), 8 * 1024**3)
        source = facts(raw)
        self.assertEqual(source['flavorRootDiskBytes'].value(), 20 * 1024**3)
        self.assertEqual(source['flavorEphemeralDiskBytes'].value(), 7 * 1024**3)
        self.assertEqual(source['flavorSwapBytes'].value(), 128 * 1024**2)
        # Flavor size + an attached data volume do not prove complete root storage.
        self.assertEqual(vm['diskCapacityBytes'].state, 'UNKNOWN')
        self.assertEqual(normalized.original.digest, raw.digest)
        self.assertEqual(len(transport.calls), 7)
        self.assertFalse(any('flavor' in path for _, path, _ in transport.calls))

    def test_missing_or_legacy_embedded_values_do_not_become_zero(self):
        for flavor in ({}, {'id': '4', 'links': [{'href': 'https://untrusted.invalid'}]}):
            with self.subTest(flavor=flavor):
                values = responses()
                server(values)['flavor'] = flavor
                result, _ = collected(values)
                self.assertEqual(result.completeness, 'PARTIAL')
                for key in ('vcpuCount', 'memorySizeBytes', 'flavorRootDiskBytes',
                            'flavorEphemeralDiskBytes', 'flavorSwapBytes'):
                    self.assertEqual(facts(result)[key].state, 'UNKNOWN')
        values = responses()
        del server(values)['flavor']
        result, _ = collected(values)
        self.assertEqual(facts(result)['vcpuCount'].state, 'UNKNOWN')

    def test_numeric_fields_reject_booleans_coercions_negatives_and_overflow(self):
        for key, minimum, scale in (('vcpus', 1, 1), ('ram', 1, 1024**2),
                                   ('disk', 0, 1024**3), ('ephemeral', 0, 1024**3),
                                   ('swap', 0, 1024**2)):
            for invalid in (True, False, '4', 4.0, None, minimum - 1,
                            (2**63 - 1) // scale + 1):
                with self.subTest(key=key, invalid=invalid):
                    values = responses()
                    server(values)['flavor'][key] = invalid
                    with self.assertRaises(OpenStackDiscoveryHeld):
                        collected(values)
            values = responses()
            server(values)['flavor'][key] = (2**63 - 1) // scale
            collected(values)

    def test_malformed_flavor_is_not_an_empty_known_allocation(self):
        for invalid in (None, [], '', 4, True):
            values = responses()
            server(values)['flavor'] = invalid
            with self.subTest(invalid=invalid), self.assertRaises(OpenStackDiscoveryHeld):
                collected(values)

    def test_image_identity_empty_volume_boot_and_omission_are_distinct(self):
        values = responses()
        result, _ = collected(values)
        self.assertEqual(facts(result)['imageId'].value(), VM3)
        server(values)['image'] = ''
        result, _ = collected(values)
        self.assertIsNone(facts(result)['imageId'].value())
        self.assertNotIn('bootVolumeId', facts(result))
        for missing in (False, True):
            values = responses()
            if missing:
                del server(values)['image']
            else:
                server(values)['image'] = {}
            result, _ = collected(values)
            self.assertEqual(facts(result)['imageId'].state, 'UNKNOWN')
        for invalid in (None, [], 0, False, {'id': ''}, {'id': 'not-a-uuid'}):
            values = responses()
            server(values)['image'] = invalid
            with self.subTest(invalid=invalid), self.assertRaises(OpenStackDiscoveryHeld):
                collected(values)

    def test_explicit_false_deletion_disposition_and_relationships_are_retained(self):
        result, _ = collected(responses())
        vm = facts(result)
        self.assertEqual(vm['attachedVolumeIds'].value(), [VOLUME])
        self.assertEqual(vm['volumeDeleteOnTermination'].value(),
                         [{'volumeId': VOLUME, 'deleteOnTermination': False}])
        self.assertEqual(facts(result, 'volume')['volumeAttachments'].value(),
                         [{'attachmentId': VM2, 'volumeId': VOLUME,
                           'serverId': VM1, 'device': '/dev/vdb'}])

    def test_missing_deletion_field_preserves_ids_but_not_guessed_disposition(self):
        values = responses()
        del server(values)['os-extended-volumes:volumes_attached'][0]['delete_on_termination']
        result, _ = collected(values)
        self.assertEqual(facts(result)['attachedVolumeIds'].value(), [VOLUME])
        self.assertEqual(facts(result)['volumeDeleteOnTermination'].state, 'UNKNOWN')
        for invalid in ('false', 0, 1, None):
            values = responses()
            server(values)['os-extended-volumes:volumes_attached'][0]['delete_on_termination'] = invalid
            with self.subTest(invalid=invalid), self.assertRaises(OpenStackDiscoveryHeld):
                collected(values)

    def test_missing_attachment_sets_do_not_become_empty(self):
        for native_key, fact_key, row in (
                ('os-extended-volumes:volumes_attached', 'attachedVolumeIds', server),
                ('attachments', 'volumeAttachments', volume)):
            kind = 'vm' if row is server else 'volume'
            values = responses()
            del row(values)[native_key]
            result, _ = collected(values)
            self.assertEqual(facts(result, kind)[fact_key].state, 'UNKNOWN')
            row(values)[native_key] = []
            result, _ = collected(values)
            self.assertEqual(facts(result, kind)[fact_key].value(), [])

    def test_nova_relationship_bounds_duplicates_and_malformed_ids_hold(self):
        good = {'id': VOLUME, 'delete_on_termination': False}
        for invalid in (None, {}, [None], [{}], [{'id': 'bad'}], [good, good],
                        [dict(good, id=f'{n:032x}') for n in range(65)]):
            values = responses()
            server(values)['os-extended-volumes:volumes_attached'] = invalid
            with self.subTest(invalid=invalid), self.assertRaises(OpenStackDiscoveryHeld):
                collected(values)

    def test_cinder_relationships_reject_cross_volume_duplicates_and_oversize(self):
        good = volume(responses())['attachments'][0]
        for invalid in (None, {}, [None], [{}], [dict(good, volume_id=VM3)],
                        [dict(good, server_id='foreign-name')], [good, good],
                        [dict(good, attachment_id=f'{n:032x}') for n in range(33)],
                        [dict(good, attachment_id=f'{n:032x}', device='x'*128)
                         for n in range(32)]):
            values = responses()
            volume(values)['attachments'] = invalid
            with self.subTest(invalid=invalid), self.assertRaises(OpenStackDiscoveryHeld):
                collected(values)

    def test_device_label_is_not_invented_or_used_as_a_path(self):
        for missing in (False, True):
            values = responses()
            attachment = volume(values)['attachments'][0]
            if missing:
                del attachment['device']
            else:
                attachment['device'] = None
            result, _ = collected(values)
            binding = facts(result, 'volume')['volumeAttachments'].value()[0]
            if missing:
                self.assertNotIn('device', binding)
            else:
                self.assertIsNone(binding['device'])
        for invalid in ('', 'x'*129, 'bad\nlabel', '\x7f', False, 7, []):
            values = responses()
            volume(values)['attachments'][0]['device'] = invalid
            with self.subTest(invalid=invalid), self.assertRaises(OpenStackDiscoveryHeld):
                collected(values)

    def test_relationship_order_is_canonical_not_guest_disk_order(self):
        values = responses()
        volume(values)['multiattach'] = True
        volume(values)['attachments'].append(
            {'attachment_id': VM3, 'server_id': VM2, 'volume_id': VOLUME, 'device': '/dev/vdc'})
        original, _ = collected(values)
        volume(values)['attachments'].reverse()
        reversed_result, _ = collected(values)
        self.assertEqual(facts(original, 'volume')['volumeAttachments'],
                         facts(reversed_result, 'volume')['volumeAttachments'])
        self.assertNotIn('diskOrder', facts(original, 'volume'))
        self.assertNotIn('writerExcluded', facts(original, 'volume'))

    def test_whitelisted_hardware_never_imports_secrets_or_policy_claims(self):
        values = responses()
        server(values)['flavor']['extra_specs'] = {'auth_password': 'sensitive'}
        server(values)['image']['properties'] = {'nativeQualified': True}
        volume(values)['attachments'][0].update(
            connection_info={'password': 'sensitive'}, host_name='private-host',
            metadata={'capabilityProperties': {'guest_drivers.verified': True}})
        result, _ = collected(values)
        serialized = repr([(f.name, f.value_json) for obj in result.objects for f in obj.facts])
        for forbidden in ('sensitive', 'private-host', 'connection_info', 'nativeQualified',
                          'capabilityProperties', 'extra_specs'):
            self.assertNotIn(forbidden, serialized)


class OpenStackHardwareHttpsTests(unittest.TestCase):
    def setUp(self):
        from tests.provisioning.discovery.test_openstack_https import OpenStackHttpsTests
        self.native = OpenStackHttpsTests()
        self.addCleanup(self.native.doCleanups)
        self.native.setUp()

    def test_new_hardware_contract_crosses_the_signed_tls_boundary(self):
        native = self.native
        result = assemble_discovery_result(native.campaign, native.transport.collect(),
                                           checked_at=native.now)
        vm = facts(result)
        self.assertEqual(vm['vcpuCount'].value(), 4)
        self.assertEqual(vm['memorySizeBytes'].value(), 8 * 1024**3)
        self.assertEqual(len(vm['attachedVolumeIds'].value()), 1)
        self.assertEqual(result.completeness, 'PARTIAL')
        self.assertIn('VISIBLE_INVENTORY_ONLY', result.collection_errors)

    def test_retired_collector_profile_is_not_a_forwarding_alias(self):
        from dataclasses import replace
        native = self.native
        native.campaign = replace(native.campaign, collector_id='openstack-project-https-1')
        with self.assertRaises(ValueError):
            native.client()
        self.assertEqual(native.calls, [])


if __name__ == '__main__':
    unittest.main()
