"""Determinism and replay: the same reviewed inputs must produce the same plan."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest

from provisioner.compiler import artifacts
from provisioner.execution import delivery
from provisioner.execution import plan as execution_plan
from provisioner.policy import standards

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

    def test_the_plan_digest_is_the_complete_reviewed_manifest_digest(self):
        from provisioner.domain.request import digest as request_digest
        from provisioner.execution import manifest as plan_manifest
        plan = support.reference_plan()
        self.assertEqual(plan.digest, plan.manifest_digest)
        self.assertEqual(plan.manifest_digest, request_digest(plan.manifest))
        self.assertEqual(plan.manifest['format'], plan_manifest.MANIFEST_FORMAT)
        self.assertEqual(sorted(plan.manifest), sorted(plan_manifest.TERMS))

    def test_the_manifest_binds_every_reviewed_decision(self):
        from provisioner.domain.request import digest as request_digest
        plan = support.reference_plan()
        manifest = plan.manifest
        self.assertEqual(manifest['generation'], plan.generation)
        self.assertEqual(manifest['request']['digest'], plan.request.digest)
        self.assertEqual(manifest['resolution']['catalog_digest'],
                         plan.resolution.catalog_digest)
        self.assertEqual(manifest['resolution']['profile_versions'],
                         dict(plan.resolution.profile_versions))
        self.assertEqual(manifest['policy']['rules_digest'],
                         standards.rules_digest())
        self.assertEqual(manifest['inventory']['digest'], _fixture().document_digest)
        self.assertEqual(manifest['placement'], plan.decision.digest)
        self.assertEqual(manifest['qualification'], plan.decision.qualification_identity)
        self.assertEqual(manifest['product_tuple'], plan.decision.product_tuple)
        self.assertEqual(manifest['capacity'], dict(plan.desired_state.reservations))
        self.assertEqual(manifest['service_bindings'],
                         [dict(b) for b in plan.desired_state.service_bindings])
        self.assertEqual(manifest['desired_state'], plan.desired_state.digest)
        self.assertEqual(manifest['environment'], request_digest(plan.environment))
        self.assertEqual(manifest['compiled_inputs'],
                         {name: request_digest(value)
                          for name, value in sorted(plan.compiled.items())})
        self.assertEqual([scope['state_key'] for scope in manifest['terraform']],
                         [scope['state_key'] for scope in plan.terraform_scopes])
        self.assertEqual(manifest['ansible'], [dict(s) for s in plan.ansible_scopes])
        self.assertEqual(manifest['delivery']['graph'],
                         delivery.graph_digest(plan.desired_state,
                                               list(plan.terraform_scopes)))
        self.assertEqual(manifest['classification'],
                         {'lifecycle': plan.desired_state.lifecycle,
                          'disruptive': plan.desired_state.lifecycle == 'production',
                          'destructive': False, 'rebuild': False})

    def test_the_manifest_carries_no_derived_or_volatile_term(self):
        plan = support.reference_plan()
        manifest = plan.manifest
        # The identity and the delivery operation ids are derived from the manifest, so
        # binding them here would make the identity self-referential.
        self.assertNotIn('digest', manifest)
        self.assertNotIn('manifest_digest', manifest)
        self.assertNotIn('operation_id', manifest)
        self.assertNotIn('identity', manifest)
        self.assertNotIn('plan_digest', manifest['delivery'])
        self.assertNotIn('operation_id', manifest['delivery'])
        # A Terraform scope's `backend` is owner-provisioned free text, not a reviewed
        # decision, so the plan identity must not depend on it.
        for scope in manifest['terraform']:
            self.assertNotIn('backend', scope)
        # No volatile timestamp reaches the identity.
        self.assertNotIn('timestamp', json.dumps(manifest, sort_keys=True))

    def test_the_plan_digest_changes_when_only_the_generation_changes(self):
        plan = support.reference_plan()
        later = support.reference_plan(generation=2)
        self.assertEqual(plan.request.digest, later.request.digest)
        self.assertEqual(plan.environment, later.environment)
        self.assertNotEqual(plan.digest, later.digest)
        self.assertNotEqual(plan.operation_id, later.operation_id)

    def test_the_plan_digest_is_not_the_request_digest(self):
        plan = support.reference_plan()
        self.assertNotEqual(plan.digest, plan.request.digest)
        self.assertTrue(plan.resolution.catalog_digest)
        self.assertEqual(plan.resolution.catalog_digest, support.catalogs().digest)

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
        command = [sys.executable, '-m', 'provisioner.cli', 'plan',
                   str(support.REQUEST)]
        first = subprocess.run(command, cwd=str(support.ROOT), capture_output=True,
                               text=True, encoding='utf-8')
        second = subprocess.run(command, cwd=str(support.ROOT), capture_output=True,
                                text=True, encoding='utf-8')
        self.assertEqual(first.returncode, 0)
        self.assertEqual(first.stdout, second.stdout)


if __name__ == '__main__':
    unittest.main()