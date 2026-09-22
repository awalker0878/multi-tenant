"""Determinism and replay: the same reviewed inputs must produce the same plan."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest

from provisioner.compiler import artifacts
from provisioner.execution import plan as execution_plan

from tests.provisioning import support


class ReplayTest(unittest.TestCase):
    def test_the_request_digest_is_stable(self):
        self.assertEqual(support.reference_document()['metadata']['name'],
                         'wsd-01')
        first = support.reference_plan()
        second = support.reference_plan()
        self.assertEqual(first.request.digest, second.request.digest)

    def test_the_plan_digest_is_stable(self):
        first = support.reference_plan()
        second = support.reference_plan()
        self.assertEqual(first.digest, second.digest)

    def test_the_plan_digest_binds_request_and_environment(self):
        plan = support.reference_plan()
        from provisioner.domain.request import digest as request_digest
        self.assertEqual(plan.digest,
                         request_digest({'request': plan.request.digest,
                                         'environment': plan.environment}))

    def test_the_environment_digest_is_stable(self):
        first = support.reference_plan().environment
        second = support.reference_plan().environment
        self.assertEqual(artifacts.assert_deterministic('environment', first),
                         artifacts.assert_deterministic('environment', second))

    def test_the_desired_state_digest_is_stable(self):
        first = support.reference_plan().desired_state
        second = support.reference_plan().desired_state
        self.assertEqual(first.digest, second.digest)

    def test_the_placement_digest_is_stable(self):
        first = support.reference_plan().decision
        second = support.reference_plan().decision
        self.assertEqual(first.digest, second.digest)

    def test_compiled_inputs_are_byte_identical_across_runs(self):
        first = support.reference_plan().compiled
        second = support.reference_plan().compiled
        self.assertEqual(sorted(first), sorted(second))
        for name in first:
            self.assertEqual(artifacts.render(first[name]), artifacts.render(second[name]), name)

    def test_the_whole_plan_document_is_identical_across_runs(self):
        first = json.dumps(support.reference_plan().to_dict(), sort_keys=True)
        second = json.dumps(support.reference_plan().to_dict(), sort_keys=True)
        self.assertEqual(first, second)

    def test_candidate_and_domain_order_is_canonical(self):
        plan = support.reference_plan()
        candidates = [(c.site_key, c.cell_key, c.zone, c.platform)
                      for c in plan.decision.candidates]
        self.assertEqual(candidates, sorted(candidates))
        self.assertEqual([d.zone for d in plan.desired_state.domains],
                         sorted(d.zone for d in plan.desired_state.domains))

    def test_the_conformance_report_is_identical_across_runs(self):
        first = json.dumps(support.reference_plan().conformance, sort_keys=True)
        second = json.dumps(support.reference_plan().conformance, sort_keys=True)
        self.assertEqual(first, second)


class InputSensitivityTest(unittest.TestCase):
    def _document(self):
        document = support.reference_document()
        return json.loads(json.dumps(document))

    def test_a_changed_request_changes_the_digest(self):
        baseline = support.reference_plan().digest
        document = self._document()
        document['metadata']['name'] = 'wsd-02'
        changed = execution_plan.create_plan(document, 'in-memory', _fixture(),
                                             support.catalogs())
        self.assertNotEqual(changed.digest, baseline)
        self.assertNotEqual(changed.request.digest,
                            support.reference_plan().request.digest)

    def test_a_changed_capacity_profile_changes_the_plan(self):
        baseline = support.reference_plan()
        document = self._document()
        document['spec']['capacity']['computeProfile'] = 'small'
        changed = execution_plan.create_plan(document, 'in-memory', _fixture(),
                                             support.catalogs())
        self.assertNotEqual(changed.digest, baseline.digest)
        self.assertEqual(changed.resolution.profiles['compute'], 'small')
        self.assertEqual(len(changed.desired_state.domains),
                         len(baseline.desired_state.domains))

    def test_disabling_a_zone_required_by_the_profile_is_refused(self):
        from provisioner.domain.errors import ProvisioningError
        document = self._document()
        document['spec']['zones']['restricted']['enabled'] = False
        with self.assertRaises(ProvisioningError) as raised:
            execution_plan.create_plan(document, 'in-memory', _fixture(),
                                       support.catalogs())
        self.assertEqual(raised.exception.code, 'SEMANTIC_INCONSISTENT')


def _fixture():
    from provisioner.inventory.model import fixture
    return fixture()


class CliReplayTest(unittest.TestCase):
    def test_two_plan_invocations_emit_identical_output(self):
        command = [sys.executable, '-m', 'provisioner.cli.main', 'plan',
                   str(support.REQUEST)]
        first = subprocess.run(command, cwd=str(support.ROOT), capture_output=True,
                               text=True, encoding='utf-8')
        second = subprocess.run(command, cwd=str(support.ROOT), capture_output=True,
                                text=True, encoding='utf-8')
        self.assertEqual(first.returncode, 0)
        self.assertEqual(first.stdout, second.stdout)


if __name__ == '__main__':
    unittest.main()