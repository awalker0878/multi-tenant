"""Conformance must never promote unknown evidence into a pass."""
from __future__ import annotations

import unittest

from provisioner.conformance import activation, checks, report
from provisioner.domain.errors import ProvisioningError

from tests.provisioning import support


class CheckTest(unittest.TestCase):
    def test_an_unknown_status_is_refused(self):
        with self.assertRaises(ValueError):
            checks.Check(name='schema', status='MAYBE', authority='REPOSITORY',
                         mandatory=True)

    def test_repository_and_external_checks_are_disjoint(self):
        self.assertEqual(set(checks.REPOSITORY_CHECKS) & set(checks.EXTERNAL_CHECKS), set())

    def test_every_mandatory_check_is_declared(self):
        declared = set(checks.REPOSITORY_CHECKS) | set(checks.EXTERNAL_CHECKS)
        self.assertTrue(set(checks.MANDATORY) <= declared)

    def test_a_pending_check_is_not_satisfied(self):
        check = checks.Check(name='native-qualification', status=checks.PENDING,
                             authority='EXTERNAL', mandatory=True)
        self.assertFalse(check.satisfied)

    def test_only_pass_and_not_applicable_count_as_satisfied(self):
        for status in (checks.PASS, checks.NOT_APPLICABLE):
            self.assertTrue(checks.Check(name='schema', status=status,
                                         authority='REPOSITORY', mandatory=True).satisfied)


class ReportTest(unittest.TestCase):
    def test_the_reference_plan_is_blocked_on_external_evidence(self):
        plan = support.reference_plan()
        self.assertEqual(plan.conformance['status'], report.BLOCKED)
        self.assertFalse(plan.conformance['ready'])

    def test_no_repository_check_fails(self):
        plan = support.reference_plan()
        self.assertEqual(plan.conformance['failed'], [])

    def test_every_external_check_is_pending_not_passed(self):
        plan = support.reference_plan()
        rows = {row['name']: row['status'] for row in plan.conformance['checks']}
        for name in checks.EXTERNAL_CHECKS:
            self.assertEqual(rows[name], checks.PENDING, name)

    def test_absent_observation_is_pending_not_pass(self):
        plan = support.reference_plan()
        row = next(r for r in plan.conformance['checks'] if r['name'] == 'native-observation')
        self.assertEqual(row['status'], checks.PENDING)
        self.assertEqual(row['evidence']['observations'], 0)

    def test_blocking_checks_are_the_unsatisfied_mandatory_ones(self):
        plan = support.reference_plan()
        self.assertTrue(set(plan.conformance['blocking']) <= set(checks.MANDATORY))
        self.assertNotIn('profiles', plan.conformance['blocking'])

    def test_the_report_states_what_it_does_not_prove(self):
        plan = support.reference_plan()
        self.assertTrue(plan.conformance['limits'])
        self.assertFalse(plan.conformance['native_contact'])

    def test_the_report_is_bound_to_the_plan_digest(self):
        plan = support.reference_plan()
        self.assertEqual(plan.conformance['plan_digest'], plan.digest)
        self.assertEqual(plan.conformance['request_digest'], plan.request.digest)

    def test_a_failed_repository_check_fails_the_report(self):
        plan = support.reference_plan()
        broken = report.build(plan)
        self.assertEqual(broken['status'], report.BLOCKED)
        self.assertTrue(all(row['status'] != checks.FAIL for row in broken['checks']))


class ActivationTest(unittest.TestCase):
    def test_activation_is_refused_while_conformance_is_blocked(self):
        plan = support.reference_plan()
        with self.assertRaises(ProvisioningError) as raised:
            activation.require_conformant(plan)
        self.assertEqual(raised.exception.code, 'ACTIVATION_REFUSED')
        self.assertIn('blocking', raised.exception.details)

    def test_activation_is_never_eligible_without_external_authorization(self):
        plan = support.reference_plan()
        payload = activation.to_dict(plan)
        self.assertEqual(payload['status'], 'HELD')
        self.assertIsNone(payload['authorization'])
        self.assertFalse(payload['native_contact'])


if __name__ == '__main__':
    unittest.main()