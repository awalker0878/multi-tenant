"""Native AHV hardware facts remain scoped, typed, bounded and unqualified."""
import copy
from dataclasses import replace
import unittest
from uuid import UUID

from provisioner.controlplane.discovery.adapters.ahv import collect_ahv_vms
from provisioner.controlplane.discovery.model import assemble_discovery_result
from provisioner.controlplane.discovery.normalization import normalize_discovery
from tests.provisioning.controlplane.test_ahv_discovery import (
    NOW, VM2, DISK, NIC, Transport, campaign, response, vm)


def observed(value):
    c = campaign()
    result = assemble_discovery_result(c, collect_ahv_vms(
        c, Transport([(200, response([value], 1))]), clock=lambda: NOW), checked_at=NOW)
    return result, {f.name: f for f in result.objects[0].facts}


class AhvHardwareTests(unittest.TestCase):
    def test_native_cpu_pinning_passthrough_agent_and_generation_are_distinct_and_typed(self):
        source=vm();source['isCpuPassthroughEnabled']=True;source['isAgentVm']=True
        result,facts=observed(source)
        self.assertIs(facts['cpuPassthroughEnabled'].value(),True);self.assertIs(facts['agentVm'].value(),True)
        self.assertIs(facts['vcpuHardPinningEnabled'].value(),False);self.assertEqual(facts['numNumaNodes'].value(),0)
        self.assertEqual(facts['nativeGenerationUuid'].value(),source['generationUuid'])
        self.assertNotIn('passthroughDevices',facts);self.assertNotIn('architecture',facts)
        for field,name in (('isCpuPassthroughEnabled','cpuPassthroughEnabled'),('isVcpuHardPinningEnabled','vcpuHardPinningEnabled'),('isAgentVm','agentVm')):
            for invalid in ('false',0,{},[]):
                value=vm();value[field]=invalid
                with self.subTest(field=field,invalid=invalid):self.assertEqual(observed(value)[1][name].reason,'COLLECTION_ERROR')
            value=vm();del value[field]
            self.assertEqual(observed(value)[1][name].reason,'NOT_RETURNED')

    def test_explicit_boot_vtpm_and_hardware_survive_normalization(self):
        source = vm()
        source['bootConfig']['isSecureBootEnabled'] = True
        source['vtpmConfig']['isVtpmEnabled'] = True
        result, facts = observed(source)
        self.assertEqual(result.completeness, 'COMPLETE')
        self.assertEqual(facts['firmware'].value(), 'uefi')
        self.assertIs(facts['secureBootEnabled'].value(), True)
        self.assertIs(facts['vtpmEnabled'].value(), True)
        normalized = {f.name: f for f in normalize_discovery(result).inventory.objects[0].facts}
        self.assertEqual(normalized['diskLayout'].value(), [
            {'extId': DISK, 'busType': 'SCSI', 'index': 0}])
        self.assertEqual(normalized['nicHardware'].value()[0]['model'], 'VIRTIO')
        self.assertEqual(normalized['vcpuCount'].value(), 4)
        self.assertEqual(normalized['secureBootEnabled'], facts['secureBootEnabled'])
        for unobserved in ('architecture', 'storageEncrypted', 'sharedDisks',
                           'passthroughDevices', 'memoryStateRequired'):
            self.assertNotIn(unobserved, facts)

    def test_secure_boot_false_is_observed_not_a_missing_default(self):
        _, facts = observed(vm())
        self.assertIs(facts['secureBootEnabled'].value(), False)
        self.assertIs(facts['vtpmEnabled'].value(), False)
        for parent, key, fact in (('bootConfig', 'isSecureBootEnabled', 'secureBootEnabled'),
                                  ('vtpmConfig', 'isVtpmEnabled', 'vtpmEnabled')):
            for value in (None, 'false', 0, [], {}):
                source = vm(); source[parent][key] = value
                with self.subTest(parent=parent, value=value):
                    result, values = observed(source)
                    self.assertEqual(values[fact].state, 'UNKNOWN')
                    self.assertEqual(result.completeness, 'PARTIAL')
            source = vm(); del source[parent][key]
            self.assertEqual(observed(source)[1][fact].reason, 'NOT_RETURNED')

    def test_boot_union_never_inferred_from_secure_boot_flag(self):
        for config in ({'isSecureBootEnabled': True}, {'$objectType': 'future.Boot'}, []):
            source = vm(); source['bootConfig'] = config
            with self.subTest(config=config):
                self.assertEqual(observed(source)[1]['firmware'].state, 'UNKNOWN')
        source = vm(); source['bootConfig'] = {'$objectType': 'vmm.v4.ahv.config.LegacyBoot'}
        _, facts = observed(source)
        self.assertEqual(facts['firmware'].value(), 'bios')
        self.assertEqual(facts['secureBootEnabled'].state, 'UNKNOWN')

    def test_volume_group_cannot_spoof_vm_disk_capacity(self):
        source = vm()
        source['disks'][0]['backingInfo']['$objectType'] = 'vmm.v4.ahv.config.ADSFVolumeGroupReference'
        _, facts = observed(source)
        self.assertEqual(facts['diskCapacityBytes'].state, 'UNKNOWN')
        self.assertIsNone(facts['disks'].value()[0]['diskSizeBytes'])
        self.assertTrue(facts['disks'].value()[0]['backingType'].endswith('ADSFVolumeGroupReference'))
        source['disks'][0]['backingInfo']['$objectType'] = 'future.VmDisk'
        self.assertEqual(observed(source)[1]['disks'].state, 'UNKNOWN')
        del source['disks'][0]['backingInfo']['$objectType']
        self.assertEqual(observed(source)[1]['diskCapacityBytes'].state, 'UNKNOWN')

    def test_capacity_and_scalar_integers_are_bounded_not_coerced(self):
        for value in (True, 0, -1, 2**63, '100', float('inf')):
            source = vm(); source['disks'][0]['backingInfo']['diskSizeBytes'] = value
            with self.subTest(value=value):
                self.assertEqual(observed(source)[1]['diskCapacityBytes'].state, 'UNKNOWN')
                source = vm(); source['memorySizeBytes'] = value
                self.assertEqual(observed(source)[1]['memorySizeBytes'].state, 'UNKNOWN')
        source = vm()
        source['disks'][0]['backingInfo']['diskSizeBytes'] = 2**63 - 1
        second = copy.deepcopy(source['disks'][0]); second['extId'] = VM2
        second['diskAddress']['index'] = 1
        source['disks'].append(second)
        self.assertEqual(observed(source)[1]['diskCapacityBytes'].state, 'UNKNOWN')

    def test_missing_duplicate_or_invalid_disk_address_is_not_guest_order(self):
        for address in (None, {}, {'busType': 'SCSI', 'index': True},
                        {'busType': 'future', 'index': 1}, {'busType': 'IDE', 'index': -1}):
            source = vm(); source['disks'][0]['diskAddress'] = address
            with self.subTest(address=address):
                self.assertEqual(observed(source)[1]['diskLayout'].state, 'UNKNOWN')
        source = vm(); other = copy.deepcopy(source['disks'][0]); other['extId'] = VM2
        source['disks'].append(other)
        self.assertEqual(observed(source)[1]['diskLayout'].state, 'UNKNOWN')

    def test_nic_request_defaults_are_not_observed_state(self):
        for field in ('model', 'macAddress', 'isConnected'):
            source = vm(); del source['nics'][0]['backingInfo'][field]
            with self.subTest(field=field):
                self.assertEqual(observed(source)[1]['nicHardware'].state, 'UNKNOWN')
        source = vm(); source['nics'][0]['backingInfo']['isConnected'] = False
        self.assertIs(observed(source)[1]['nicHardware'].value()[0]['isConnected'], False)
        source['nics'][0]['backingInfo']['$objectType'] = 'future.PassthroughNic'
        self.assertEqual(observed(source)[1]['nicHardware'].state, 'UNKNOWN')

    def test_duplicate_mac_and_malformed_nic_types_are_unknown(self):
        for field, value in (('model', '_REDACTED'), ('macAddress', 'bad'), ('isConnected', 1)):
            source = vm(); source['nics'][0]['backingInfo'][field] = value
            with self.subTest(field=field):
                self.assertEqual(observed(source)[1]['nicHardware'].state, 'UNKNOWN')
        source = vm(); other = copy.deepcopy(source['nics'][0]); other['extId'] = VM2
        source['nics'].append(other)
        self.assertEqual(observed(source)[1]['nicHardware'].state, 'UNKNOWN')

    def test_explicit_empty_devices_differ_from_omission(self):
        source = vm(); source['disks'] = []; source['nics'] = []
        _, facts = observed(source)
        self.assertEqual(facts['diskCapacityBytes'].value(), 0)
        for name in ('disks', 'diskLayout', 'nics', 'nicHardware', 'networkBindings'):
            self.assertEqual(facts[name].value(), [])
        del source['disks']; del source['nics']
        _, facts = observed(source)
        self.assertEqual(facts['disks'].state, 'UNKNOWN')
        self.assertEqual(facts['nics'].state, 'UNKNOWN')

    def test_oversized_fact_preserves_vm_identity_but_cannot_be_complete(self):
        source = vm(); disk = source['disks'][0]
        source['disks'] = [dict(copy.deepcopy(disk), extId=str(UUID(int=i+1)),
                                diskAddress={'busType': 'SCSI', 'index': i}) for i in range(100)]
        result, facts = observed(source)
        self.assertEqual(len(result.objects), 1)
        self.assertEqual(facts['disks'].reason, 'COLLECTION_ERROR')
        self.assertEqual(result.completeness, 'PARTIAL')

    def test_facts_are_frozen_redacted_and_digest_bound(self):
        source = vm(); source['guestCustomization'] = {'password': 'must-not-leak'}
        source['vtpmConfig']['secret'] = 'must-not-leak'
        result, facts = observed(source)
        encoded = repr(result)
        self.assertNotIn('must-not-leak', encoded)
        source['bootConfig']['isSecureBootEnabled'] = True
        self.assertIs(facts['secureBootEnabled'].value(), False)
        self.assertNotEqual(observed(source)[0].digest, result.digest)
        values = facts['disks'].value(); values.clear()
        self.assertEqual(len(facts['disks'].value()), 1)

    def test_old_collector_interpretation_cannot_reuse_campaign_binding(self):
        c = replace(campaign(), collector_id='nutanix-ahv-v4.0')
        transport = Transport([])
        with self.assertRaises(ValueError):
            collect_ahv_vms(c, transport, clock=lambda: NOW)
        self.assertEqual(transport.calls, [])


if __name__ == '__main__':
    unittest.main()
