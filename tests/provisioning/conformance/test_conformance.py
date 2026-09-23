"""Conformance must never promote unknown evidence into a pass.

A repository-side check reports a proposal. Only the owner's own row reports the
owner's state, and external evidence is only evidence for the plan and generation it
names. Each regression below pins one of those claims.
"""
from __future__ import annotations

import re
import unittest
from datetime import datetime, timezone
from unittest import mock

from provisioner.conformance import activation, checks, report
from provisioner.domain.errors import ProvisioningError
from provisioner.execution import authority, service
from provisioner.observation import native

from tests.provisioning import support

#: A reviewed instant inside every fixture's validity window.
AS_OF = datetime(2026, 9, 18, 18, 0, tzinfo=timezone.utc)

_OWNERSHIP = re.compile(r'\b(' + '|'.join(checks.OWNERSHIP_VOCABULARY) + r')\b',
                        re.IGNORECASE)


def _words(text: str):
    return sorted(match.group(0).lower() for match in _OWNERSHIP.finditer(text))


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

    def test_every_required_external_answer_blocks_activation(self):
        plan = support.reference_plan()
        with self.assertRaises(ProvisioningError) as raised:
            activation.require_conformant(plan)
        blocking = raised.exception.details['blocking']
        for name in ('native-qualification', 'capacity-confirmation',
                     'address-confirmation', 'dns-registration', 'service-acceptance',
                     'native-observation', 'production-authorization'):
            self.assertIn(name, blocking)
        self.assertNotIn('recovery-readiness', blocking)
        rows = {row.name: row for row in checks.run(plan)}
        self.assertEqual(rows['recovery-readiness'].status, checks.PENDING)
        self.assertFalse(rows['recovery-readiness'].mandatory)

    def test_activation_is_still_refused_when_the_owners_have_answered(self):
        plan = support.reference_plan()
        approval = authority.Approval(plan_digest=plan.digest, approved_by='reviewer',
                                      authority_ref='AR-2026-001')
        with self.assertRaises(ProvisioningError) as raised:
            activation.require_conformant(plan,
                                          capacity=service.capacity_evidence(plan),
                                          addresses=service.address_evidence(plan, as_of=AS_OF),
                                          authorization=approval)
        self.assertEqual(raised.exception.code, 'ACTIVATION_REFUSED')
        blocking = raised.exception.details['blocking']
        self.assertNotIn('production-authorization', blocking)
        self.assertIn('native-observation', blocking)


class ProposalLanguageTest(unittest.TestCase):
    """A repository-side check reports intent; the owner's row reports state."""

    def setUp(self):
        self.plan = support.reference_plan()

    def test_no_repository_row_claims_an_owner_outcome(self):
        self.assertEqual(report.ownership_claims(checks.run(self.plan)), [])

    def test_no_repository_row_states_ownership_vocabulary(self):
        for row in checks.run(self.plan):
            if row.authority != 'REPOSITORY':
                continue
            self.assertEqual(_words(row.detail), [], f'{row.name}: {row.detail!r}')

    def test_a_proposal_carries_no_ownership_value(self):
        rows = {row.name: row for row in checks.run(self.plan)}
        for name in checks.CONFIRMATION_OF:
            for value in report._strings(rows[name].evidence):
                self.assertEqual(_words(value), [], f'{name}: {value!r}')

    def test_a_proposal_is_not_reported_as_confirmed_ownership(self):
        document = self.plan.conformance
        rows = {row['name']: row for row in document['checks']}
        for name, owner_check in checks.CONFIRMATION_OF.items():
            self.assertEqual(rows[name]['authority'], 'REPOSITORY')
            self.assertEqual(rows[name]['status'], checks.PASS)
            self.assertEqual(rows[owner_check]['authority'], 'EXTERNAL')
            self.assertEqual(rows[owner_check]['status'], checks.PENDING)
            self.assertNotIn(name, document['blocking'])
            self.assertIn(owner_check, document['blocking'])
        self.assertEqual(document['status'], report.BLOCKED)
        self.assertFalse(document['ready'])

    def test_the_proposal_block_names_the_owner_check_that_settles_each_proposal(self):
        block = self.plan.conformance['proposal']
        self.assertEqual(block['format'], report.PROPOSAL_FORMAT)
        self.assertEqual(block['authority'], report.PROPOSAL_AUTHORITY)
        self.assertEqual(block['checks'], sorted(checks.CONFIRMATION_OF))
        self.assertEqual(block['confirmed_by'], dict(checks.CONFIRMATION_OF))
        self.assertEqual(block['unconfirmed'], sorted(checks.CONFIRMATION_OF))
        self.assertTrue(block['limits'])

    def test_a_proposal_that_claims_an_unconfirmed_outcome_is_refused(self):
        claiming = checks.Check(name='capacity-proposal', status=checks.PASS,
                                authority='REPOSITORY', mandatory=True,
                                detail='The capacity arithmetic reserved every unit')
        with mock.patch.object(checks, 'run', lambda *a, **k: (claiming,)):
            with self.assertRaises(ProvisioningError) as raised:
                report.build(self.plan)
        self.assertEqual(raised.exception.code, 'CONFORMANCE_CLAIM_UNPROVEN')
        self.assertEqual(raised.exception.details['claims'],
                         [{'check': 'capacity-proposal', 'words': ['reserved'],
                           'confirmation_check': 'capacity-confirmation'}])

    def test_a_proposal_that_claims_an_outcome_the_owner_confirmed_is_allowed(self):
        claiming = checks.Check(name='capacity-proposal', status=checks.PASS,
                                authority='REPOSITORY', mandatory=True,
                                detail='The capacity owner reserved every unit')
        confirmed = checks.Check(name='capacity-confirmation', status=checks.PASS,
                                 authority='EXTERNAL', mandatory=True)
        with mock.patch.object(checks, 'run', lambda *a, **k: (claiming, confirmed)):
            built = report.build(self.plan)
        self.assertNotIn('capacity-proposal', built['proposal']['unconfirmed'])
        self.assertEqual(built['status'], report.READY)


class EvidenceBindingTest(unittest.TestCase):
    """External evidence is only evidence for the plan and generation it names."""

    def setUp(self):
        self.plan = support.reference_plan(generation=1)

    def _rows(self, **kwargs):
        return {row.name: row for row in checks.run(self.plan, **kwargs)}

    def test_another_generations_capacity_reading_is_not_this_plans_evidence(self):
        other = support.reference_plan(generation=2)
        row = self._rows(capacity=service.capacity_evidence(other))['capacity-confirmation']
        self.assertEqual(row.status, checks.PENDING)
        self.assertEqual(row.evidence['foreign'],
                         ['generation', 'operation_id', 'plan_digest'])
        self.assertEqual(row.evidence['expected_operation_id'], self.plan.operation_id)

    def test_a_moved_capacity_view_is_not_this_plans_evidence(self):
        evidence = service.capacity_evidence(self.plan)
        tampered = {**evidence, 'binding': dict(evidence['binding'], view_digest='0' * 64)}
        row = self._rows(capacity=tampered)['capacity-confirmation']
        self.assertEqual(row.status, checks.PENDING)
        self.assertEqual(row.evidence['foreign'], ['view_digest'])

    def test_a_bound_capacity_reading_of_this_plan_names_no_mismatch(self):
        evidence = service.capacity_evidence(self.plan)
        row = self._rows(capacity=evidence)['capacity-confirmation']
        self.assertEqual(row.evidence.get('foreign'), None)
        self.assertEqual(row.evidence['operation_id'], self.plan.operation_id)
        self.assertEqual(row.evidence['view_digest'], evidence['view']['digest'])

    def test_another_operations_address_reading_is_not_this_plans_evidence(self):
        evidence = service.address_evidence(self.plan, as_of=AS_OF)
        tampered = {**evidence,
                    'reconciliation': dict(evidence['reconciliation'],
                                           operation_id=f'{self.plan.operation_id}-other')}
        rows = self._rows(addresses=tampered)
        for name in ('address-confirmation', 'dns-registration'):
            self.assertEqual(rows[name].status, checks.PENDING, name)
            self.assertEqual(rows[name].evidence['foreign'], ['operation_id'], name)

    def test_a_moved_address_view_is_not_this_plans_evidence(self):
        evidence = service.address_evidence(self.plan, as_of=AS_OF)
        tampered = {**evidence,
                    'reconciliation': dict(evidence['reconciliation'],
                                           view_digest='0' * 64)}
        row = self._rows(addresses=tampered)['address-confirmation']
        self.assertEqual(row.status, checks.PENDING)
        self.assertEqual(row.evidence['foreign'], ['view_digest'])

    def test_an_approval_for_another_plan_is_not_this_plans_authorization(self):
        record = authority.Approval(plan_digest='0' * 64, approved_by='reviewer',
                                    authority_ref='AR-2026-001')
        row = self._rows(authorization=record)['production-authorization']
        self.assertEqual(row.status, checks.PENDING)
        self.assertEqual(row.evidence['foreign'], ['plan_digest'])
        self.assertFalse(row.evidence['bound'])

    def test_an_approval_for_this_plan_is_the_owners_authorization(self):
        record = authority.Approval(plan_digest=self.plan.digest, approved_by='reviewer',
                                    authority_ref='AR-2026-001')
        row = self._rows(authorization=record)['production-authorization']
        self.assertEqual(row.status, checks.PASS)
        self.assertEqual(row.authority, 'EXTERNAL')
        self.assertTrue(row.evidence['bound'])

    def test_an_observation_from_another_generation_never_becomes_a_pass(self):
        subjects = native.expected_subjects(self.plan.desired_state)
        stale = [native.observed(subject, native_id, {'present': True}, 'readback',
                                 generation=2) for subject, native_id in subjects]
        rows = self._rows(observations=stale)
        self.assertEqual(rows['generation'].status, checks.FAIL)
        self.assertEqual(rows['native-observation'].status, checks.PENDING)
        self.assertEqual(rows['native-observation'].evidence['stale'], len(subjects))
        self.assertEqual(rows['native-observation'].evidence['bound'], 0)

    def test_an_observation_that_names_no_generation_is_not_attributable(self):
        subjects = native.expected_subjects(self.plan.desired_state)
        unbound = [native.observed(subject, native_id, {'present': True}, 'readback')
                   for subject, native_id in subjects]
        rows = self._rows(observations=unbound)
        self.assertEqual(rows['generation'].status, checks.FAIL)
        self.assertEqual(rows['native-observation'].evidence['unbound'], len(subjects))

    def test_a_bound_observation_is_still_not_the_owners_attestation(self):
        subjects = native.expected_subjects(self.plan.desired_state)
        bound = [native.observed(subject, native_id, {'present': True}, 'readback',
                                 generation=1) for subject, native_id in subjects]
        rows = self._rows(observations=bound)
        self.assertEqual(rows['generation'].status, checks.PASS)
        self.assertEqual(rows['native-observation'].status, checks.PENDING)
        self.assertEqual(rows['native-observation'].evidence['bound'], len(subjects))


if __name__ == '__main__':
    unittest.main()
