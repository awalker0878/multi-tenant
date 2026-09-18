"""Fail-closed platform-family eligibility tests; not placement or native qualification."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import unittest

from scripts import check_platform_capabilities as capabilities
from scripts import check_platform_family_eligibility as admission

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / 'examples/pre_placement_capability_request.json.example'


class PlatformFamilyEligibilityTests(unittest.TestCase):
    def setUp(self):
        self.registry = capabilities.load()
        self.request = admission.load_request(EXAMPLE)

    def evaluate(self):
        return admission.evaluate(self.request, self.registry)

    def qualify(self, platform='nutanix'):
        profile = self.registry['profiles'][platform]
        profile['product_tuple'] = 'fixture-selected-product-api-provider-tuple'
        for cap in self.request['mandatory_capabilities']:
            profile['capabilities'][cap]['qualification'] = 'NATIVE_QUALIFIED'
            profile['capabilities'][cap]['native_evidence_refs'] = [
                f'controlled-evidence:{platform}:{cap}:fixture'
            ]

    def test_current_registry_fails_closed(self):
        result = self.evaluate()
        self.assertEqual(result['status'], admission.HOLD)
        self.assertEqual(result['eligible_platforms'], [])

    def test_current_registry_discloses_optional_ipv6_as_unavailable(self):
        result = self.evaluate()
        self.assertTrue(all('ipv6' in row['optional_unavailable']
                            for row in result['evaluations']))

    def test_no_result_grants_placement_or_activation(self):
        result = self.evaluate()
        for key in ('may_select_site', 'may_reserve_capacity', 'may_allocate',
                    'may_apply', 'may_activate'):
            self.assertIs(result[key], False)

    def test_qualified_family_is_still_only_a_family_match(self):
        self.qualify('nutanix')
        result = self.evaluate()
        self.assertEqual(result['status'], admission.MATCH)
        self.assertEqual(result['eligible_platforms'], ['nutanix'])
        self.assertIs(result['may_select_site'], False)
        self.assertIn('site/cell/service-class eligibility', result['remaining_gates'])

    def test_unqualified_optional_capability_does_not_weaken_mandatory_gate(self):
        self.qualify('nutanix')
        result = self.evaluate()
        nutanix = next(x for x in result['evaluations'] if x['platform'] == 'nutanix')
        self.assertTrue(nutanix['family_capability_eligible'])
        self.assertEqual(nutanix['optional_unavailable'], ['ipv6'])

    def test_assurance_profile_is_a_separate_blocker(self):
        self.qualify('nutanix')
        self.request['required_assurance_profile'] = 'PROTECTED-B-FIXTURE'
        result = self.evaluate()
        nutanix = next(x for x in result['evaluations'] if x['platform'] == 'nutanix')
        self.assertFalse(nutanix['family_capability_eligible'])
        self.assertIn('assurance_profile:PROTECTED-B-FIXTURE',
                      nutanix['mandatory_blockers'])

    def test_assurance_profile_can_be_explicitly_recorded_after_qualification(self):
        self.qualify('nutanix')
        self.registry['profiles']['nutanix']['assurance_profiles'] = ['PROTECTED-B-FIXTURE']
        self.request['required_assurance_profile'] = 'PROTECTED-B-FIXTURE'
        result = self.evaluate()
        self.assertEqual(result['eligible_platforms'], ['nutanix'])

    def test_selected_tuple_without_qualified_capabilities_still_holds(self):
        self.registry['profiles']['nutanix']['product_tuple'] = 'selected-but-unqualified'
        result = self.evaluate()
        nutanix = next(x for x in result['evaluations'] if x['platform'] == 'nutanix')
        self.assertFalse(nutanix['family_capability_eligible'])
        self.assertTrue(any(x in self.request['mandatory_capabilities']
                            for x in nutanix['mandatory_blockers']))

    def test_candidate_subset_does_not_expand_scope(self):
        self.qualify('nutanix')
        self.request['candidate_platforms'] = ['vmware-nsx']
        result = self.evaluate()
        self.assertEqual([x['platform'] for x in result['evaluations']], ['vmware-nsx'])
        self.assertEqual(result['eligible_platforms'], [])

    def test_unknown_platform_rejected(self):
        self.request['candidate_platforms'] = ['unknown-stack']
        with self.assertRaises(ValueError):
            admission.evaluate(self.request, self.registry)

    def test_unknown_capability_rejected(self):
        self.request['mandatory_capabilities'].append('vendor_magic')
        with self.assertRaises(ValueError):
            admission.evaluate(self.request, self.registry)

    def test_duplicate_candidate_rejected(self):
        self.request['candidate_platforms'].append('nutanix')
        with self.assertRaises(ValueError):
            admission.evaluate(self.request, self.registry)

    def test_mandatory_optional_overlap_rejected(self):
        self.request['optional_capabilities'].append('network_domain')
        with self.assertRaises(ValueError):
            admission.evaluate(self.request, self.registry)

    def test_composite_mode_rejected_by_initial_profile(self):
        self.request['placement_mode'] = 'COMPOSITE_MULTI_PLATFORM'
        with self.assertRaises(ValueError):
            admission.evaluate(self.request, self.registry)

    def test_site_binding_cannot_be_selected_by_precheck(self):
        self.request['site_binding']['site_ref'] = 'site-01'
        with self.assertRaises(ValueError):
            admission.evaluate(self.request, self.registry)

    def test_production_authority_cannot_be_carried(self):
        self.request['production_authority'] = 'APPROVED'
        with self.assertRaises(ValueError):
            admission.evaluate(self.request, self.registry)

    def test_missing_source_reference_rejected(self):
        self.request['source_refs'].append('docs/does-not-exist.md')
        with self.assertRaises(ValueError):
            admission.evaluate(self.request, self.registry)

    def test_wsd_reference_must_be_in_source_set(self):
        self.request['source_refs'].remove(self.request['wsd_engineering_ref'])
        with self.assertRaises(ValueError):
            admission.evaluate(self.request, self.registry)

    def test_cli_hold_is_nonzero_without_explicit_expected_status(self):
        run = subprocess.run(
            [sys.executable, str(ROOT/'scripts/check_platform_family_eligibility.py'),
             str(EXAMPLE)], capture_output=True, text=True, timeout=10)
        self.assertEqual(run.returncode, 2)
        self.assertEqual(json.loads(run.stdout)['status'], admission.HOLD)

    def test_ci_can_assert_the_expected_current_hold_explicitly(self):
        run = subprocess.run(
            [sys.executable, str(ROOT/'scripts/check_platform_family_eligibility.py'),
             str(EXAMPLE), '--expected-status', admission.HOLD],
            capture_output=True, text=True, timeout=10)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    def test_expected_match_cannot_turn_a_hold_green(self):
        run = subprocess.run(
            [sys.executable, str(ROOT/'scripts/check_platform_family_eligibility.py'),
             str(EXAMPLE), '--expected-status', admission.MATCH],
            capture_output=True, text=True, timeout=10)
        self.assertEqual(run.returncode, 2)


if __name__ == '__main__':
    unittest.main()
