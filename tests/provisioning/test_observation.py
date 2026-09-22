"""Observation, drift, health and reconciliation are readback-only."""
from __future__ import annotations

import unittest

from provisioner.observation import drift, health, native
from provisioner.reconciliation import classify, compare

from tests.provisioning import support


class ObservationTest(unittest.TestCase):
    def test_an_unknown_status_is_refused(self):
        with self.assertRaises(ValueError):
            native.Observation(subject='domain', native_id='wsd-01-OZ', status='MAYBE')

    def test_only_an_observed_row_is_trusted(self):
        self.assertTrue(native.observed('domain', 'wsd-01-OZ', {}, 'readback').trusted)
        self.assertFalse(native.unobserved('domain', 'wsd-01-OZ').trusted)

    def test_an_observation_is_content_addressed(self):
        first = native.observed('domain', 'wsd-01-OZ', {'zone': 'OZ'}, 'readback')
        second = native.observed('domain', 'wsd-01-OZ', {'zone': 'OZ'}, 'readback')
        self.assertEqual(first.digest, second.digest)
        self.assertTrue(first.digest)

    def test_expected_subjects_are_derived_from_the_desired_state(self):
        plan = support.reference_plan()
        subjects = native.expected_subjects(plan.desired_state)
        self.assertEqual(subjects, tuple(sorted(subjects)))
        self.assertEqual(len(subjects), 4)
        self.assertEqual({s for s, _ in subjects}, {'domain', 'workload'})

    def test_an_absent_observation_is_recorded_as_absent(self):
        plan = support.reference_plan()
        payload = native.to_dict((), plan.desired_state)
        self.assertEqual(payload['count'], 0)
        self.assertEqual(len(payload['not_observed']), 4)
        self.assertEqual(payload['expected'], 4)


class DriftTest(unittest.TestCase):
    def test_unobserved_state_is_unknown_not_in_sync(self):
        plan = support.reference_plan()
        payload = drift.to_dict(plan.desired_state, ())
        self.assertEqual(payload['status'], drift.UNKNOWN)
        self.assertEqual(payload['classes'], [drift.UNKNOWN])

    def test_a_matching_observation_is_in_sync(self):
        plan = support.reference_plan()
        domain = plan.desired_state.domains[0]
        observations = (native.observed(
            'domain', domain.domain_id,
            {'zone': domain.zone, 'prefix': domain.prefix, 'cluster': domain.cluster_id},
            'readback'),)
        payload = drift.to_dict(plan.desired_state, observations)
        self.assertNotIn(drift.DRIFTED, payload['classes'])

    def test_a_divergent_field_is_classified_as_drifted(self):
        plan = support.reference_plan()
        domain = plan.desired_state.domains[0]
        observations = (native.observed(
            'domain', domain.domain_id,
            {'zone': domain.zone, 'prefix': '203.0.113.0/27', 'cluster': domain.cluster_id},
            'readback'),)
        payload = drift.to_dict(plan.desired_state, observations)
        self.assertEqual(payload['status'], drift.DRIFTED)
        self.assertTrue(any(d['classification'] == drift.DRIFTED for d in payload['differences']))


class HealthTest(unittest.TestCase):
    def test_health_is_unknown_without_observation(self):
        plan = support.reference_plan()
        payload = health.to_dict(plan.desired_state, ())
        self.assertEqual(payload['status'], health.UNKNOWN)

    def test_health_never_asserts_service_readiness(self):
        plan = support.reference_plan()
        payload = health.to_dict(plan.desired_state, ())
        self.assertEqual(payload['service_readiness'], 'NOT_ASSERTED_BY_REPOSITORY')
        self.assertFalse(payload['native_contact'])

    def test_drift_degrades_health(self):
        plan = support.reference_plan()
        domain = plan.desired_state.domains[0]
        observations = (native.observed(
            'domain', domain.domain_id,
            {'zone': domain.zone, 'prefix': '203.0.113.0/27', 'cluster': domain.cluster_id},
            'readback'),)
        self.assertEqual(health.to_dict(plan.desired_state, observations)['status'],
                         health.DEGRADED)


class ReconciliationTest(unittest.TestCase):
    def test_a_comparison_row_exists_per_expected_subject(self):
        plan = support.reference_plan()
        comparison = compare.build(plan.desired_state, ())
        self.assertEqual(len(comparison['rows']), 4)
        self.assertEqual(comparison['evidence_available'], 0)

    def test_without_evidence_every_row_is_unknown_requires_discovery(self):
        plan = support.reference_plan()
        classification = classify.classify(compare.build(plan.desired_state, ()))
        self.assertEqual(set(classification['classes']), {classify.UNKNOWN})
        self.assertTrue(classification['requires_discovery'])

    def test_a_zone_change_requires_containment(self):
        plan = support.reference_plan()
        domain = plan.desired_state.domains[0]
        observations = (native.observed(
            'domain', domain.domain_id,
            {'zone': 'RZ', 'prefix': domain.prefix, 'cluster': domain.cluster_id},
            'readback'),)
        classification = classify.classify(compare.build(plan.desired_state, observations))
        self.assertTrue(classification['requires_containment'])

    def test_a_missing_native_object_is_classified_as_missing(self):
        plan = support.reference_plan()
        domain = plan.desired_state.domains[0]
        observations = (native.observed('domain', domain.domain_id,
                                        {'cluster': domain.cluster_id}, 'readback'),)
        classification = classify.classify(compare.build(plan.desired_state, observations))
        row = next(r for r in classification['rows'] if r['native_id'] == domain.domain_id)
        self.assertEqual(row['classification'], classify.MISSING)

    def test_reconciliation_never_mutates_native_state(self):
        plan = support.reference_plan()
        payload = classify.classify(compare.build(plan.desired_state, ()))
        self.assertEqual(payload['status'], 'CLASSIFIED_NOT_RECONCILED')
        self.assertTrue(payload['limits'])


if __name__ == '__main__':
    unittest.main()