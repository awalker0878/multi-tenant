from __future__ import annotations
from copy import deepcopy
import unittest
from scripts import check_platform_capabilities as c


class CapabilityRegistryTests(unittest.TestCase):
    def setUp(self): self.registry = c.load()
    def test_current_registry_is_valid(self):
        summary = c.validate(self.registry); self.assertEqual(summary['platforms'], 3); self.assertEqual(summary['native_qualified_claims'], 0)
    def test_current_registry_has_no_production_eligible_platform(self):
        for platform in c.PLATFORMS:
            allowed, blockers = c.eligible(self.registry, platform, {'network_domain','ipv4'})
            self.assertFalse(allowed); self.assertIn('product_tuple:UNSELECTED', blockers)
    def test_candidate_source_is_not_native_qualification(self):
        for platform in c.PLATFORMS:
            self.assertNotEqual(self.registry['profiles'][platform]['capabilities']['network_domain']['qualification'], 'NATIVE_QUALIFIED')
    def test_local_ipv6_fixture_cannot_enable_native_ipv6(self):
        for platform in c.PLATFORMS:
            claim = self.registry['profiles'][platform]['capabilities']['ipv6']
            self.assertEqual(claim['source_state'], 'LOCAL_FIXTURE_ONLY'); self.assertEqual(claim['qualification'], 'NOT_QUALIFIED')
    def test_native_claim_requires_selected_tuple(self):
        r = deepcopy(self.registry); r['profiles']['nutanix']['capabilities']['network_domain']['qualification'] = 'NATIVE_QUALIFIED'; r['profiles']['nutanix']['capabilities']['network_domain']['native_evidence_refs'] = ['external:evidence-1']
        with self.assertRaises(ValueError): c.validate(r)
    def test_native_claim_requires_evidence(self):
        r = deepcopy(self.registry); r['profiles']['nutanix']['product_tuple'] = 'site-accepted-tuple'; r['profiles']['nutanix']['capabilities']['network_domain']['qualification'] = 'NATIVE_QUALIFIED'
        with self.assertRaises(ValueError): c.validate(r)
    def test_unqualified_claim_cannot_carry_native_evidence(self):
        r = deepcopy(self.registry); r['profiles']['openstack']['capabilities']['ipv4']['native_evidence_refs'] = ['external:evidence-1']
        with self.assertRaises(ValueError): c.validate(r)
    def test_unselected_tuple_cannot_publish_assurance_profile(self):
        r = deepcopy(self.registry); r['profiles']['vmware-nsx']['assurance_profiles'] = ['standard']
        with self.assertRaises(ValueError): c.validate(r)
    def test_missing_capability_rejected(self):
        r = deepcopy(self.registry); del r['profiles']['openstack']['capabilities']['audit_logging']
        with self.assertRaises(ValueError): c.validate(r)
    def test_unknown_capability_requirement_rejected(self):
        with self.assertRaises(ValueError): c.eligible(self.registry, 'nutanix', {'magic_feature'})
    def test_assurance_requirement_fails_closed(self):
        allowed, blockers = c.eligible(self.registry, 'openstack', set(), 'standard'); self.assertFalse(allowed); self.assertIn('assurance_profile:standard', blockers)
    def test_repository_evidence_must_exist(self):
        r = deepcopy(self.registry); r['profiles']['nutanix']['capabilities']['ipv4']['evidence_refs'] = ['missing/file.md']
        with self.assertRaises(ValueError): c.validate(r)
    def test_duplicate_capability_vocabulary_rejected(self):
        r = deepcopy(self.registry); r['capability_ids'].append('ipv4')
        with self.assertRaises(ValueError): c.validate(r)
    def test_registry_does_not_claim_service_insertion_or_load_balancer(self):
        for platform in c.PLATFORMS:
            for cap in ('service_insertion','native_load_balancer'):
                self.assertEqual(self.registry['profiles'][platform]['capabilities'][cap]['qualification'], 'NOT_QUALIFIED')


if __name__ == '__main__': unittest.main()
