"""Typed source/target semantics are mandatory even with positive route reviews."""
from dataclasses import replace
import unittest

from provisioner.controlplane.discovery.compatibility import check_compatibility
from provisioner.controlplane.discovery.model import DiscoveryFact
from provisioner.controlplane.discovery.normalization import normalize_discovery
from provisioner.domain.capability_properties import contract_digest
from tests.provisioning.discovery.test_assessment import (
    AssessmentEngine, RouteCatalogue, TARGET_B, TARGET_C, claim, compare,
    fact_set, option, source_snapshot, target_snapshot,
)
from tests.provisioning.discovery import test_service


def change(obj, **values):
    fields = {f.name: f.value() for f in obj.facts if f.state == 'KNOWN'}
    fields.update(values)
    return replace(obj, facts=fact_set(**fields))


def remove(obj, name):
    return replace(obj, facts=tuple(f for f in obj.facts if f.name != name))


class CompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.source = source_snapshot().objects[0]
        self.target = target_snapshot(TARGET_B)[0].objects[0]

    def codes(self, source=None, target=None, method='COLD_VM_CONVERSION'):
        return {i[1] for i in check_compatibility(source or self.source, target or self.target, method)}

    def test_explicit_hardware_properties_pass_without_granting_authority(self):
        self.assertEqual(self.codes(), set())
        for name in ('architecture', 'firmware', 'secureBootEnabled', 'vtpmEnabled',
                     'storageEncrypted', 'sharedDisks', 'passthroughDevices', 'memoryStateRequired',
                     'requiredCapabilities', 'capabilityRequirements', 'capabilityPropertySchemaDigest'):
            with self.subTest(name=name):
                self.assertTrue(self.codes(remove(self.source, name)))

    def test_required_capabilities_cannot_be_dropped_even_without_properties(self):
        source = change(self.source, requiredCapabilities=['storage_qos'])
        self.assertIn('REQUIRED_CAPABILITY_ABSENT', self.codes(source))
        for available in (None, ['vm_create'] * 2, ['invented']):
            self.assertIn('DESTINATION_CAPABILITY_SET_UNVERIFIED', self.codes(source,
                change(self.target, observedCapabilities=available)))

    def test_native_boot_architecture_and_driver_mismatch_is_a_blocker(self):
        original = next(f.value() for f in self.target.facts if f.name == 'capabilityProperties')
        for prop, value in (('cpu_topology.architecture', 'aarch64'),
                            ('vm_create.firmware', 'bios'), ('guest_drivers.verified', False)):
            with self.subTest(prop=prop):
                target = change(self.target, capabilityProperties={**original, prop: value})
                self.assertIn('PROPERTY_MISMATCH', self.codes(target=target))

    def test_vtpm_recreation_is_not_state_preservation(self):
        source = change(self.source, vtpmEnabled=True)
        target = change(self.target, capabilityProperties={
            **next(f.value() for f in self.target.facts if f.name == 'capabilityProperties'),
            'vtpm.state_handling': 'recreate'})
        self.assertIn('PROPERTY_MISMATCH', self.codes(source, target))

    def test_encryption_layer_and_keys_are_not_inferred_from_a_feature_flag(self):
        source = change(self.source, storageEncrypted=True)
        self.assertIn('SOURCE_ENCRYPTION_LAYER_UNVERIFIED', self.codes(source))
        source = change(source, storageEncryptionLayer='hypervisor')
        self.assertIn('PROPERTY_UNKNOWN', self.codes(source))
        target = change(self.target, capabilityProperties={
            **next(f.value() for f in self.target.facts if f.name == 'capabilityProperties'),
            'storage_encryption.destination_key_ready': True,
            'storage_encryption.layer': 'storage-backend'})
        self.assertIn('PROPERTY_MISMATCH', self.codes(source, target))

    def test_shared_disks_and_passthrough_require_observed_mappings(self):
        self.assertIn('PROPERTY_UNKNOWN', self.codes(change(self.source, sharedDisks=True)))
        self.assertIn('PROPERTY_UNKNOWN', self.codes(change(self.source, passthroughDevices=['gpu-1'])))
        for invalid in (True, ['gpu-1'] * 2, [{}], ['a\n'], ['x'] * 257):
            with self.subTest(invalid=invalid):
                self.assertIn('SOURCE_PASSTHROUGH_DEVICES_UNVERIFIED',
                              self.codes(change(self.source, passthroughDevices=invalid)))

    def test_profile_cannot_contradict_native_source_observation(self):
        source = change(self.source, requiredCapabilities=['cpu_topology'], capabilityRequirements=[{
            'property': 'cpu_topology.architecture', 'operator': 'eq', 'value': 'aarch64'}])
        self.assertIn('SOURCE_PROFILE_NATIVE_CONTRADICTION', self.codes(source))

    def test_malformed_or_superseded_property_evidence_stays_unknown(self):
        for digest in (None, 'f' * 64, True):
            with self.subTest(digest=digest):
                self.assertIn('SOURCE_PROPERTY_SCHEMA_UNVERIFIED',
                              self.codes(change(self.source, capabilityPropertySchemaDigest=digest)))
        for properties in ({'storage_qos.minimum_iops': True}, {'unowned': True}, [], None):
            with self.subTest(properties=properties):
                self.assertIn('DESTINATION_CAPABILITY_PROPERTIES_UNVERIFIED',
                              self.codes(target=change(self.target, capabilityProperties=properties)))
        for required in (['made-up'], ['vm_create', 'vm_create'], [True], None):
            self.assertIn('SOURCE_CAPABILITY_REQUIREMENTS_UNVERIFIED',
                          self.codes(change(self.source, requiredCapabilities=required)))

    def test_disk_copy_routes_do_not_claim_running_memory_transfer(self):
        source = change(self.source, memoryStateRequired=True)
        for method in ('COLD_VM_CONVERSION', 'WARM_VM_TRANSFER'):
            self.assertIn('MEMORY_STATE_TRANSFER_NOT_IMPLEMENTED', self.codes(source, method=method))

    def test_warm_transfer_requires_measured_convergence_with_typed_samples(self):
        source = change(self.source, dirtyRateBytesPerSecond=50, dirtyRateSampleSeconds=60)
        target = change(self.target, measuredTransferBytesPerSecond=200, transferSampleSeconds=60)
        self.assertEqual(self.codes(source, target, 'WARM_VM_TRANSFER'), set())
        for invalid in (True, -1, 2**63, None):
            self.assertIn('WARM_TRANSFER_MEASUREMENT_MISSING', self.codes(
                change(source, dirtyRateBytesPerSecond=invalid), target, 'WARM_VM_TRANSFER'))
        for dirty in (200, 300):
            self.assertIn('WARM_TRANSFER_NONCONVERGENT', self.codes(
                change(source, dirtyRateBytesPerSecond=dirty), target, 'WARM_VM_TRANSFER'))
        self.assertIn('WARM_TRANSFER_MEASUREMENT_MISSING',
                      self.codes(source, remove(target, 'transferSampleSeconds'), 'WARM_VM_TRANSFER'))

    def test_positive_review_and_other_target_properties_cannot_hide_one_target_gap(self):
        source = source_snapshot()
        target, pool = target_snapshot(TARGET_B)
        target = replace(target, objects=(remove(target.objects[0], 'capabilityProperties'),))
        results = compare(AssessmentEngine(RouteCatalogue((claim(TARGET_B), claim(TARGET_C)))), source,
                          option(TARGET_B, source, target=target, capacity_id=pool), option(TARGET_C, source))
        self.assertEqual([r.status for r in results], ['UNKNOWN', 'ELIGIBLE'])
        self.assertTrue(all(not r.execution_authorized for r in results))

    def test_raw_normalization_rejects_old_property_revision_and_preserves_custody(self):
        raw = source_snapshot()
        raw = replace(raw, objects=(change(raw.objects[0], capabilityPropertySchemaDigest='f' * 64),))
        normalized = normalize_discovery(raw)
        facts = {f.name: f for f in normalized.inventory.objects[0].facts}
        self.assertEqual(facts['capabilityPropertySchemaDigest'].state, 'UNKNOWN')
        self.assertEqual(normalized.original, raw)
        self.assertNotEqual(normalized.original.digest, normalized.inventory.digest)

    def test_normalizer_does_not_supply_unobserved_requirements(self):
        raw = source_snapshot()
        raw = replace(raw, objects=(remove(raw.objects[0], 'capabilityRequirements'),))
        normalized = normalize_discovery(raw)
        self.assertEqual(next(f.state for f in normalized.inventory.objects[0].facts
                              if f.name == 'capabilityRequirements'), 'UNKNOWN')

    def test_cross_family_relocation_is_reported_instead_of_losing_comparison(self):
        source = source_snapshot()
        result = compare(AssessmentEngine(RouteCatalogue(())), source,
                         option(TARGET_B, source), option(TARGET_C, source),
                         method='SAME_PLATFORM_RELOCATION')
        self.assertEqual(len(result), 2)
        self.assertTrue(all('RELOCATION_REQUIRES_SAME_PLATFORM' in row.blockers for row in result))


class ServiceRouteSemanticsTests(unittest.TestCase):
    def test_mixed_destination_relocation_keeps_both_scoped_results(self):
        fixture = test_service.AssessmentServiceTests('test_eligibility_requires_verified_routes_and_normalized_snapshot_bound_reviews')
        fixture.setUp()
        fixture.inputs.qualified = True
        results = fixture.compare(method='SAME_PLATFORM_RELOCATION').assessments
        self.assertEqual(results[0].status, 'ELIGIBLE')
        self.assertIn('RELOCATION_REQUIRES_SAME_PLATFORM', results[1].blockers)
        self.assertFalse(results[1].execution_authorized)
