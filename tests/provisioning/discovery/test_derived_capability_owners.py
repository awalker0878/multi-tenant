"""Hardware-derived requirements cannot bypass their observed capability owners."""
import unittest

from provisioner.controlplane.discovery.compatibility import check_compatibility
from tests.provisioning.discovery.test_assessment import TARGET_B, source_snapshot, target_snapshot
from tests.provisioning.discovery.test_compatibility import change, remove


def known(obj, name):
    return next(f.value() for f in obj.facts if f.name == name and f.state == 'KNOWN')


class DerivedCapabilityOwnerTests(unittest.TestCase):
    def setUp(self):
        self.source = source_snapshot().objects[0]
        self.target = target_snapshot(TARGET_B)[0].objects[0]

    def check(self, source, target, method='COLD_VM_CONVERSION'):
        return check_compatibility(source, target, method)

    def test_each_hardware_requirement_requires_its_owner_even_when_property_matches(self):
        scenarios = (
            ({}, {}, 'cpu_topology'),
            ({}, {}, 'vm_create'),
            ({}, {}, 'guest_drivers'),
            ({'secureBootEnabled': True}, {'secure_boot.enabled': True}, 'secure_boot'),
            ({'vtpmEnabled': True}, {'vtpm.state_handling': 'preserve'}, 'vtpm'),
            ({'storageEncrypted': True, 'storageEncryptionLayer': 'hypervisor'},
             {'storage_encryption.layer': 'hypervisor',
              'storage_encryption.destination_key_ready': True}, 'storage_encryption'),
            ({'sharedDisks': True}, {'shared_disks.writer_coordination': True}, 'shared_disks'),
            ({'passthroughDevices': ['gpu-1']},
             {'pci_passthrough.mapping_verified': True}, 'pci_passthrough'),
        )
        for source_fields, target_properties, owner in scenarios:
            with self.subTest(owner=owner):
                source = change(self.source, **source_fields)
                available = sorted(set(known(self.target, 'observedCapabilities')) | {owner})
                target = change(self.target, observedCapabilities=available, capabilityProperties={
                    **known(self.target, 'capabilityProperties'), **target_properties})
                self.assertEqual(self.check(source, target), ())
                target = change(target, observedCapabilities=[c for c in available if c != owner])
                issues = self.check(source, target)
                self.assertTrue(any(i[0] == 'BLOCKER' and i[1] == 'REQUIRED_CAPABILITY_ABSENT'
                                    and owner in i[2] for i in issues), issues)

    def test_observed_disabled_optional_hardware_does_not_require_enabling_it(self):
        target = change(self.target, observedCapabilities=['cpu_topology', 'vm_create', 'guest_drivers'])
        self.assertEqual(self.check(self.source, target), ())
        # A missing enabled/disabled observation is still unknown, not false.
        self.assertTrue(self.check(remove(self.source, 'secureBootEnabled'), target))

    def test_invalid_target_set_is_unknown_and_never_reconstructed_from_properties(self):
        source = change(self.source, vtpmEnabled=True)
        target = change(self.target, observedCapabilities=None, capabilityProperties={
            **known(self.target, 'capabilityProperties'), 'vtpm.state_handling': 'preserve'})
        self.assertIn('DESTINATION_CAPABILITY_SET_UNVERIFIED',
                      {i[1] for i in self.check(source, target)})

    def test_same_platform_relocation_does_not_require_conversion_drivers(self):
        target = change(self.target, observedCapabilities=['cpu_topology', 'vm_create'])
        properties = dict(known(target, 'capabilityProperties'))
        del properties['guest_drivers.verified']
        target = change(target, capabilityProperties=properties)
        self.assertEqual(self.check(self.source, target, 'SAME_PLATFORM_RELOCATION'), ())
        self.assertIn('REQUIRED_CAPABILITY_ABSENT', {i[1] for i in self.check(self.source, target)})


if __name__ == '__main__':
    unittest.main()
