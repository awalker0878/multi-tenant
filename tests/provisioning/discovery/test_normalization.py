from dataclasses import replace
from datetime import datetime, timezone
import unittest

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.discovery.model import (
    DiscoveryFact, DiscoveryObject, DiscoveryResult, NativeIdentity, _digest, _object_json)
from provisioner.controlplane.discovery.normalization import (
    NormalizationHeld, hydrate_generation, normalize_discovery)
from provisioner.controlplane.discovery.persistence import StoredGeneration, StoredObservation


NOW = datetime(2026, 9, 28, 15, tzinfo=timezone.utc)
SCOPE = PlanScope('org', 'tenant', 'site', 'wsd', 'endpoint', 'cluster', 'nutanix')


def snapshot(values, *, kind='vm', facts=(), completeness='COMPLETE'):
    obj = DiscoveryObject(NativeIdentity('endpoint', 'cluster', 'nutanix', kind, 'native-1'),
                          tuple(DiscoveryFact.known(k, v) for k, v in values.items()) + facts)
    return DiscoveryResult('campaign', 'a' * 64, SCOPE, NOW, completeness, (obj,), (), ())


def stored(result, generation=7):
    header = StoredGeneration('environment', generation, result.campaign_id, result.scope,
                              result.authorization_digest, result.digest, result.captured_at,
                              result.completeness, result.collection_errors,
                              result.missing_privileges, len(result.objects))
    rows = tuple(StoredObservation(generation, obj.identity,
                                   tuple(_object_json(obj)['facts']), _digest(_object_json(obj)))
                 for obj in sorted(result.objects, key=lambda obj: obj.identity.key()))
    return header, rows


def normalized(values, **kwargs):
    result = normalize_discovery(snapshot(values, **kwargs))
    return result, {fact.name: fact for fact in result.inventory.objects[0].facts}


class NormalizationTests(unittest.TestCase):
    def test_stored_full_generation_is_rebuilt_and_digest_verified(self):
        result = snapshot({'numSockets': 2, 'numCoresPerSocket': 4})
        header, rows = stored(result)
        self.assertEqual(hydrate_generation(header, rows).digest, result.digest)
        for changed_header, changed_rows in (
                (replace(header, result_digest='b' * 64), rows),
                (header, (replace(rows[0], generation=8),)),
                (header, (replace(rows[0], object_digest='b' * 64),)),
                (header, ()),
                (replace(header, object_count=2), rows),
                (replace(header, scope=replace(SCOPE, endpoint_id='other')), rows)):
            with self.subTest(header=changed_header, rows=changed_rows):
                with self.assertRaises(NormalizationHeld):
                    hydrate_generation(changed_header, changed_rows)

    def test_fact_extra_keys_and_known_value_with_unknown_reason_are_rejected(self):
        header, rows = stored(snapshot({'numSockets': 2}))
        for patch in ({'extra': 'hidden'}, {'reason': 'NOT_RETURNED'}):
            facts = (dict(rows[0].facts[0], **patch),)
            with self.assertRaises(NormalizationHeld):
                hydrate_generation(header, (replace(rows[0], facts=facts),))

    def test_ahv_cpu_disk_and_nic_values_are_normalized_without_profile_guesses(self):
        raw = snapshot({'numSockets': 2, 'numCoresPerSocket': 4,
                        'memorySizeBytes': 8 * 1024**3,
                        'disks': [{'extId': 'disk-a', 'diskSizeBytes': 10},
                                  {'extId': 'disk-b', 'diskSizeBytes': 20}],
                        'nics': [{'extId': 'nic-a', 'subnetExtId': 'subnet-a'}]})
        result = normalize_discovery(raw)
        facts = {fact.name: fact for fact in result.inventory.objects[0].facts}
        self.assertEqual(facts['vcpuCount'].value(), 8)
        self.assertEqual(facts['diskCapacityBytes'].value(), 30)
        self.assertEqual(facts['networkBindings'].value(), [
            {'nativeNicId': 'nic-a', 'nativeNetworkId': 'subnet-a'}])
        for name in ('guestProfile', 'networkMode', 'dataMode'):
            self.assertEqual(facts[name].state, 'UNKNOWN')
        self.assertNotIn('measuredTransferBytes', facts)
        self.assertEqual(raw.completeness, 'COMPLETE')
        self.assertEqual(result.inventory.completeness, 'PARTIAL')
        self.assertNotEqual(result.original.digest, result.inventory.digest)
        self.assertEqual(result.binding()['rawSnapshotDigest'], raw.digest)
        self.assertEqual(normalize_discovery(raw), result)

    def test_explicit_unknown_privilege_is_preserved(self):
        raw = snapshot({'name': 'vm'}, facts=(DiscoveryFact.unknown(
            'memorySizeBytes', 'MISSING_PRIVILEGE', required_privilege='VM_CONFIG_READ'),),
            completeness='PARTIAL')
        result = normalize_discovery(raw)
        item = next(f for f in result.inventory.objects[0].facts if f.name == 'memorySizeBytes')
        self.assertEqual(item.required_privilege, 'VM_CONFIG_READ')
        self.assertEqual(item.reason, 'MISSING_PRIVILEGE')

    def test_conflicting_numeric_aliases_never_understate_source_requirements(self):
        for values, canonical in (
                ({'vcpuCount': 4, 'vcpus': 64}, 'vcpuCount'),
                ({'vcpuCount': 4, 'numSockets': 8, 'numCoresPerSocket': 8}, 'vcpuCount'),
                ({'vcpus': 4, 'numSockets': 8, 'numCoresPerSocket': 8}, 'vcpuCount'),
                ({'vcpuCount': 4, 'vcpus': 4, 'numSockets': 8,
                  'numCoresPerSocket': 8}, 'vcpuCount'),
                ({'memorySizeBytes': 1024**3, 'memoryMiB': 65536}, 'memorySizeBytes'),
                ({'memorySizeBytes': 1024**3, 'memoryMiB': True}, 'memorySizeBytes'),
                ({'memorySizeBytes': 1024**3, 'memoryMiB': 2**63 - 1}, 'memorySizeBytes'),
                ({'numSockets': 2**62, 'numCoresPerSocket': 4}, 'vcpuCount'),
                ({'vcpuCount': 4, 'numSockets': True, 'numCoresPerSocket': 4}, 'vcpuCount')):
            with self.subTest(values=values):
                result, facts = normalized(values)
                self.assertEqual(facts[canonical].state, 'UNKNOWN')
                self.assertEqual(facts[canonical].reason, 'COLLECTION_ERROR')
                self.assertEqual(result.inventory.completeness, 'PARTIAL')
                self.assertEqual(result.original.completeness, 'COMPLETE')

    def test_agreeing_numeric_aliases_and_socket_counts_remain_known(self):
        _, facts = normalized({'vcpuCount': 8, 'vcpus': 8,
            'numSockets': 2, 'numCoresPerSocket': 4,
            'memorySizeBytes': 8 * 1024**3, 'memoryMiB': 8192})
        self.assertEqual(facts['vcpuCount'].value(), 8)
        self.assertEqual(facts['memorySizeBytes'].value(), 8 * 1024**3)
        _, volume = normalized({'diskCapacityBytes': 10 * 1024**3, 'size_gib': 20},
                               kind='volume')
        self.assertEqual(volume['diskCapacityBytes'].reason, 'COLLECTION_ERROR')

    def test_conflicting_nic_aliases_cannot_hide_a_different_attachment(self):
        canonical = [{'nativeNicId': 'nic-a', 'nativeNetworkId': 'net-a'}]
        for aliases in (
                [{'extId': 'nic-a', 'subnetExtId': 'net-b'}],
                [{'extId': 'nic-b', 'subnetExtId': 'net-a'}],
                [], [{}], True):
            with self.subTest(aliases=aliases):
                _, facts = normalized({'networkBindings': canonical, 'nics': aliases})
                self.assertEqual(facts['networkBindings'].state, 'UNKNOWN')
                self.assertEqual(facts['networkBindings'].reason, 'COLLECTION_ERROR')
        for mixed in ({'nativeNicId': 'nic-a', 'extId': 'nic-b', 'nativeNetworkId': 'net-a'},
                      {'nativeNicId': 'nic-a', 'nativeNetworkId': 'net-a', 'subnetExtId': 'net-b'}):
            with self.subTest(mixed=mixed):
                _, facts = normalized({'networkBindings': [mixed]})
                self.assertEqual(facts['networkBindings'].reason, 'COLLECTION_ERROR')

    def test_nic_alias_order_does_not_create_a_false_conflict(self):
        canonical = [{'nativeNicId': 'nic-a', 'nativeNetworkId': 'net-a'},
                     {'nativeNicId': 'nic-b', 'nativeNetworkId': 'net-b'}]
        _, facts = normalized({'networkBindings': canonical, 'nics': [
            {'extId': 'nic-b', 'subnetExtId': 'net-b'},
            {'extId': 'nic-a', 'subnetExtId': 'net-a'}]})
        self.assertEqual(facts['networkBindings'].value(), canonical)

    def test_port_aliases_cannot_change_native_vm_or_network_ownership(self):
        for values, field in (({'attachedVmId': 'vm-a', 'device_id': 'vm-b'}, 'attachedVmId'),
                              ({'nativeNetworkId': 'net-a', 'network_id': 'net-b'}, 'nativeNetworkId')):
            with self.subTest(values=values):
                _, facts = normalized(values, kind='nic')
                self.assertEqual(facts[field].reason, 'COLLECTION_ERROR')

    def test_disk_contradictions_and_invalid_sizes_never_create_capacity(self):
        for values in (
                {'diskCapacityBytes': 99, 'disks': [{'extId': 'd', 'diskSizeBytes': 10}]},
                {'disks': [{'extId': 'd', 'diskSizeBytes': 10},
                           {'extId': 'd', 'diskSizeBytes': 10}]},
                {'disks': [{'extId': 'd', 'diskSizeBytes': None}]},
                {'vcpuCount': True, 'memorySizeBytes': 2**63, 'diskCapacityBytes': -1}):
            with self.subTest(values=values):
                _, facts = normalized(values)
                self.assertEqual(facts['diskCapacityBytes'].state, 'UNKNOWN')

    def test_openstack_volume_and_port_keep_native_relationships(self):
        _, volume = normalized({'size_gib': 40}, kind='volume')
        self.assertEqual(volume['diskCapacityBytes'].value(), 40 * 1024**3)
        _, nic = normalized({'network_id': 'network-a', 'device_id': 'vm-a'}, kind='nic')
        self.assertEqual(nic['nativeNetworkId'].value(), 'network-a')
        self.assertEqual(nic['attachedVmId'].value(), 'vm-a')
        self.assertNotIn('networkMode', nic)

    def test_network_bindings_require_distinct_nic_and_network_identities(self):
        for bindings in (True, [{}], [{'extId': 'nic', 'subnetExtId': None}],
                         [{'nativeNicId': 'nic', 'nativeNetworkId': 'net'}] * 2):
            with self.subTest(bindings=bindings):
                _, facts = normalized({'networkBindings': bindings})
                self.assertEqual(facts['networkBindings'].state, 'UNKNOWN')
                self.assertEqual(facts['networkBindings'].reason, 'COLLECTION_ERROR')

    def test_quota_requires_observed_usage_and_reservations(self):
        limits = {'cores': 20, 'ram': 1000, 'gigabytes': 100}
        _, only_limits = normalized({'limits': limits}, kind='quota')
        self.assertEqual(only_limits['availableVcpu'].state, 'UNKNOWN')
        _, facts = normalized({'limits': limits,
                               'usage': {'cores': 4, 'ram': 200, 'gigabytes': 30},
                               'reservations': {'cores': 2, 'ram': 100, 'gigabytes': 10}},
                              kind='quota')
        self.assertEqual(facts['availableVcpu'].value(), 14)
        self.assertEqual(facts['availableMemoryBytes'].value(), 700 * 1024**2)
        self.assertEqual(facts['availableStorageBytes'].value(), 60 * 1024**3)
        self.assertEqual(facts['supportedGuestProfiles'].state, 'UNKNOWN')
        _, unlimited = normalized({'limits': {'cores': -1}, 'usage': {'cores': 0},
                                   'reservations': {'cores': 0}}, kind='quota')
        self.assertEqual(unlimited['availableVcpu'].reason, 'NOT_SUPPORTED')


if __name__ == '__main__':
    unittest.main()
