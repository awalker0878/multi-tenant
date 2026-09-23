"""The reviewed-plan manifest: the identity an external approval cites.

A plan identity is only useful for approval if a change to *any* reviewed decision
changes it. What has to be provable here is that every approval-relevant term is
bound into the manifest digest, that nothing derived or volatile is, and that a
differently-formatted but equivalent request still replays to the same plan.

Most binding tests isolate one term by replacing it on an otherwise identical plan
and rebuilding the manifest from the *baseline* delivery graph, so the digest change
can only come from the term under test.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

from provisioner.domain.placement import UNSELECTED_PRODUCT
from provisioner.domain.request import digest as canonical_digest
from provisioner.execution import delivery
from provisioner.execution import manifest as plan_manifest
from provisioner.execution import plan as execution_plan
from provisioner.inventory import model as inventory_model
from provisioner.inventory.model import fixture
from provisioner.policy import standards

from tests.provisioning import support

REQUEST = str(support.REQUEST)
MODULE = 'provisioner.cli'


def checkout_commit() -> str:
    """The commit the checkout reports, so a handoff can bind it explicitly."""
    return support.source_commit()


def _two_site_fixture():
    """The reviewed demonstration fixture with a second, equivalent site added.

    The reviewed corpus only realizes one site, so an end-to-end *placement* test
    needs a second site to choose between. The added site is a copy of the reviewed
    one; the inventory stays non-authoritative.
    """
    document = fixture().to_dict()
    second = copy.deepcopy(document['sites'][0])
    second['site'] = 'site-02'
    document['sites'] = document['sites'] + [second]
    document['prefix_pools'] = document['prefix_pools'] + [
        {**copy.deepcopy(pool), 'pool': f'{pool["pool"]}-2', 'site': 'site-02'}
        for pool in document['prefix_pools']]
    document['services'] = document['services'] + [
        {**copy.deepcopy(service), 'site': 'site-02'}
        for service in document['services']]
    return inventory_model.build(document)


def _run(*arguments: str) -> tuple[int, dict]:
    completed = subprocess.run([sys.executable, '-m', MODULE, *arguments],
                               cwd=str(support.ROOT), capture_output=True, text=True,
                               encoding='utf-8')
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        raise AssertionError(
            f'CLI did not emit JSON (exit {completed.returncode}): '
            f'{completed.stdout!r} {completed.stderr!r}')
    return completed.returncode, payload


def _graph(plan) -> str:
    return delivery.graph_digest(plan.desired_state, list(plan.terraform_scopes))


def _rebuild(plan, graph: str | None = None, **overrides) -> dict:
    """The manifest of `plan` with exactly `overrides` replaced.

    `graph=None` reuses the baseline delivery graph, so a test that replaces a
    desired-state or scope term can prove that term is bound on its own.
    """
    changed = replace(plan, **overrides)
    return plan_manifest.build(changed, delivery_graph=_graph(plan) if graph is None else graph)


def _isolated(plan, **overrides) -> str:
    return plan_manifest.digest_of(_rebuild(plan, **overrides))


class ManifestShapeTest(unittest.TestCase):
    """The manifest is a complete, canonical, non-self-referential enumeration."""

    def test_the_manifest_has_exactly_the_declared_terms(self):
        manifest = support.reference_plan().manifest
        self.assertEqual(sorted(manifest), sorted(plan_manifest.TERMS))
        self.assertEqual(manifest['format'], 'hosting-reviewed-plan-manifest/1')

    def test_the_plan_digest_is_the_manifest_digest(self):
        plan = support.reference_plan()
        self.assertEqual(plan.digest, plan.manifest_digest)
        self.assertEqual(plan.digest, canonical_digest(plan.manifest))
        self.assertEqual(plan.to_dict()['digest'], plan.manifest_digest)
        self.assertEqual(plan.to_dict()['manifest_digest'], plan.manifest_digest)

    def test_the_manifest_names_the_exact_rule_set_it_was_evaluated_against(self):
        plan = support.reference_plan()
        self.assertEqual(plan.policy['rules_digest'], standards.rules_digest())
        self.assertEqual(plan.manifest['policy']['rules_digest'], standards.rules_digest())
        self.assertEqual(plan.manifest['policy']['rules_evaluated'],
                         len(standards.load_rules()))

    def test_the_manifest_records_the_reviewed_inventory_snapshot(self):
        plan = support.reference_plan()
        inventory = fixture()
        self.assertEqual(plan.manifest['inventory']['digest'], inventory.document_digest)
        self.assertEqual(plan.manifest['inventory']['status'], inventory.status)
        self.assertEqual(plan.manifest['inventory']['origin'], inventory.origin)
        self.assertIs(plan.manifest['inventory']['authoritative'], inventory.authoritative)

    def test_a_fixture_inventory_is_recorded_as_non_authoritative(self):
        plan = support.reference_plan()
        self.assertFalse(plan.manifest['inventory']['authoritative'])
        self.assertEqual(plan.manifest['inventory']['status'], 'FIXTURE_NOT_AUTHORITATIVE')

    def test_the_manifest_carries_no_derived_identity(self):
        plan = support.reference_plan()
        manifest = plan.manifest
        # Each of these is computed *from* the manifest, so binding it would make the
        # identity depend on itself.
        for derived in ('digest', 'manifest_digest', 'operation_id', 'identity'):
            self.assertNotIn(derived, manifest, derived)
        for derived in ('plan_digest', 'operation_id', 'identity', 'generation'):
            self.assertNotIn(derived, manifest['delivery'], derived)
        for operation in plan.delivery['operations']:
            self.assertTrue(operation['operation_id'])

    def test_the_manifest_excludes_owner_provisioned_terraform_text(self):
        plan = support.reference_plan()
        self.assertTrue(plan.terraform_scopes)
        for scope in plan.terraform_scopes:
            self.assertIn('backend', scope)
        for scope in plan.manifest['terraform']:
            self.assertNotIn('backend', scope)
            self.assertEqual(sorted(scope), sorted(plan_manifest.TERRAFORM_SCOPE_KEYS))

    def test_the_manifest_binds_the_terraform_state_key_and_root(self):
        plan = support.reference_plan()
        self.assertEqual([scope['state_key'] for scope in plan.manifest['terraform']],
                         [scope['state_key'] for scope in plan.terraform_scopes])
        self.assertEqual([scope['root'] for scope in plan.manifest['terraform']],
                         [scope['root'] for scope in plan.terraform_scopes])

    def test_the_manifest_carries_no_volatile_timestamp(self):
        text = json.dumps(support.reference_plan().manifest, sort_keys=True)
        for brittle in ('timestamp', 'created_at', 'generated_at', 'T00:', 'T12:'):
            self.assertNotIn(brittle, text, brittle)

    def test_the_change_classification_is_declared_not_guessed(self):
        plan = support.reference_plan()
        classification = plan.manifest['classification']
        self.assertEqual(classification['lifecycle'], plan.desired_state.lifecycle)
        self.assertEqual(classification['disruptive'],
                         plan.desired_state.lifecycle == 'production')
        # A greenfield create never destroys anything, and the repository has no
        # replacement or destroy intent yet, so both are declared false.
        self.assertIs(classification['destructive'], False)
        self.assertIs(classification['rebuild'], False)

    def test_the_review_projection_cites_the_same_manifest_digest(self):
        plan = support.reference_plan()
        reviewed = plan_manifest.review(plan.manifest)
        self.assertEqual(reviewed['digest'], plan.manifest_digest)
        self.assertEqual(reviewed['generation'], plan.generation)
        self.assertEqual(reviewed['inventory'], plan.manifest['inventory'])
        self.assertEqual(reviewed['placement'], plan.decision.digest)
        self.assertEqual(reviewed['rules_digest'], standards.rules_digest())


class ManifestBindingTest(unittest.TestCase):
    """Every approval-relevant term changes the identity on its own."""

    def setUp(self):
        self.plan = support.reference_plan()
        self.baseline = self.plan.digest

    def assert_bound(self, term, **overrides):
        changed = _rebuild(self.plan, **overrides)
        self.assertNotEqual(canonical_digest(changed), self.baseline,
                            f'{term} is not bound into the manifest digest')
        return changed

    def test_the_digest_changes_when_the_capacity_reservation_target_changes(self):
        reservations = dict(self.plan.desired_state.reservations)
        zone, reservation = sorted(reservations.items())[0]
        reservations[zone] = {**reservation, 'cell': 'cell-reviewed-elsewhere'}
        changed = self.assert_bound('capacity target',
                                    desired_state=replace(self.plan.desired_state,
                                                          reservations=reservations))
        self.assertEqual(changed['capacity'][zone]['cell'], 'cell-reviewed-elsewhere')

    def test_the_digest_changes_when_the_committed_after_position_changes(self):
        reservations = copy.deepcopy(self.plan.desired_state.reservations)
        zone = sorted(reservations)[0]
        limits = reservations[zone]['committed_after']
        limits['vcpu_committed'] = limits['vcpu_committed'] + 1
        changed = self.assert_bound('committed_after',
                                    desired_state=replace(self.plan.desired_state,
                                                          reservations=reservations))
        self.assertEqual(changed['capacity'][zone]['committed_after']['vcpu_committed'],
                         limits['vcpu_committed'])

    def test_the_digest_changes_when_a_service_endpoint_changes(self):
        bindings = [dict(b) for b in self.plan.desired_state.service_bindings]
        bindings[0]['endpoints'] = {**bindings[0]['endpoints'],
                                    'reviewed_endpoint': 'changed.example.internal'}
        changed = self.assert_bound('service endpoint',
                                    desired_state=replace(self.plan.desired_state,
                                                          service_bindings=tuple(bindings)))
        self.assertIn('reviewed_endpoint', changed['service_bindings'][0]['endpoints'])

    def test_the_digest_changes_when_a_service_binding_class_changes(self):
        bindings = [dict(b) for b in self.plan.desired_state.service_bindings]
        bindings[0]['binding_class'] = 'shared-reviewed-elsewhere'
        changed = self.assert_bound('binding class',
                                    desired_state=replace(self.plan.desired_state,
                                                          service_bindings=tuple(bindings)))
        self.assertEqual(changed['service_bindings'][0]['binding_class'],
                         'shared-reviewed-elsewhere')

    def test_the_digest_changes_when_the_placement_decision_changes(self):
        changed = self.assert_bound('placement',
                                    decision=replace(self.plan.decision, digest='0' * 64))
        self.assertEqual(changed['placement'], '0' * 64)

    def test_the_digest_changes_when_the_qualification_changes(self):
        qualification = dict(self.plan.decision.qualification_identity)
        qualification['source'] = 'REVIEWED_ELSEWHERE'
        changed = self.assert_bound('qualification',
                                    decision=replace(self.plan.decision,
                                                     qualification=qualification))
        self.assertEqual(changed['qualification']['source'], 'REVIEWED_ELSEWHERE')

    def test_the_digest_changes_when_the_product_tuple_changes(self):
        candidates = tuple(replace(candidate, product_tuple=f'{candidate.product_tuple}+1')
                           if candidate.platform == self.plan.decision.platform else candidate
                           for candidate in self.plan.decision.candidates)
        changed = self.assert_bound('product_tuple',
                                    decision=replace(self.plan.decision, candidates=candidates))
        self.assertEqual(changed['product_tuple'], f'{self.plan.decision.product_tuple}+1')

    def test_the_digest_changes_when_a_profile_version_changes(self):
        versions = {**self.plan.resolution.profile_versions, 'compute': 'reviewed-bump'}
        changed = self.assert_bound('profile version',
                                    resolution=replace(self.plan.resolution,
                                                       profile_versions=versions))
        self.assertEqual(changed['resolution']['profile_versions']['compute'], 'reviewed-bump')

    def test_the_digest_changes_when_a_catalog_version_changes(self):
        versions = {**self.plan.resolution.catalog_versions, 'compute': 'reviewed-bump'}
        changed = self.assert_bound('catalog version',
                                    resolution=replace(self.plan.resolution,
                                                       catalog_versions=versions))
        self.assertEqual(changed['resolution']['catalog_versions']['compute'], 'reviewed-bump')

    def test_the_digest_changes_when_the_catalog_digest_changes(self):
        changed = self.assert_bound(
            'catalog digest',
            resolution=replace(self.plan.resolution, catalog_digest='f' * 64))
        self.assertEqual(changed['resolution']['catalog_digest'], 'f' * 64)

    def test_the_digest_changes_when_the_policy_rule_set_changes(self):
        policy = {**self.plan.policy, 'rules_digest': 'f' * 64}
        changed = self.assert_bound('policy rule set', policy=policy)
        self.assertEqual(changed['policy']['rules_digest'], 'f' * 64)

    def test_the_digest_changes_when_the_inventory_snapshot_changes(self):
        changed = self.assert_bound(
            'inventory snapshot',
            inventory=replace(self.plan.inventory, document_digest='f' * 64))
        self.assertEqual(changed['inventory']['digest'], 'f' * 64)

    def test_the_digest_changes_when_a_compiled_input_changes(self):
        name = sorted(self.plan.compiled)[0]
        compiled = {**self.plan.compiled, name: {'reviewed': 'changed'}}
        changed = self.assert_bound('compiled input', compiled=compiled)
        self.assertEqual(changed['compiled_inputs'][name],
                         canonical_digest({'reviewed': 'changed'}))

    def test_the_digest_changes_when_the_environment_changes(self):
        changed = self.assert_bound(
            'environment',
            environment={**self.plan.environment, 'reviewed': 'changed'})
        self.assertEqual(changed['environment'],
                         canonical_digest({**self.plan.environment, 'reviewed': 'changed'}))

    def test_the_digest_changes_when_a_terraform_state_key_changes(self):
        scopes = tuple({**scope, 'state_key': f'{scope["state_key"]}-reviewed'}
                       for scope in self.plan.terraform_scopes)
        changed = self.assert_bound('terraform state key',
                                    terraform_scopes=scopes)
        self.assertEqual([scope['state_key'] for scope in changed['terraform']],
                         [f'{scope["state_key"]}-reviewed'
                          for scope in self.plan.terraform_scopes])

    def test_the_digest_changes_when_a_terraform_root_changes(self):
        scopes = tuple({**scope, 'root': 'stacks/reviewed-elsewhere'}
                       for scope in self.plan.terraform_scopes)
        changed = self.assert_bound('terraform root', terraform_scopes=scopes)
        self.assertEqual([scope['root'] for scope in changed['terraform']],
                         ['stacks/reviewed-elsewhere'] * len(scopes))

    def test_the_digest_changes_when_an_ansible_scope_changes(self):
        scopes = tuple({**scope, 'phase': 'reviewed-elsewhere'}
                       for scope in self.plan.ansible_scopes)
        changed = self.assert_bound('ansible scope', ansible_scopes=scopes)
        self.assertEqual(changed['ansible'][0]['phase'], 'reviewed-elsewhere')

    def test_the_digest_changes_when_the_delivery_graph_changes(self):
        changed = _rebuild(self.plan, graph='0' * 64)
        self.assertNotEqual(canonical_digest(changed), self.baseline)
        self.assertEqual(changed['delivery']['graph'], '0' * 64)
        # The graph is the only delivery term, so nothing else moved.
        self.assertEqual({key: value for key, value in changed.items() if key != 'delivery'},
                         {key: value for key, value in self.plan.manifest.items()
                          if key != 'delivery'})

    def test_the_digest_changes_when_the_generation_changes(self):
        later = support.reference_plan(generation=2)
        self.assertEqual(later.request.digest, self.plan.request.digest)
        self.assertNotEqual(later.digest, self.baseline)
        self.assertEqual(later.manifest['generation'], 2)
        # The desired state carries the generation, so only the generation *and* the
        # desired state move; every other reviewed term is untouched.
        self.assertNotEqual(later.manifest['desired_state'],
                            self.plan.manifest['desired_state'])
        self.assertEqual({key: value for key, value in later.manifest.items()
                          if key not in ('generation', 'desired_state')},
                         {key: value for key, value in self.plan.manifest.items()
                          if key not in ('generation', 'desired_state')})

    def test_the_digest_changes_when_the_change_classification_changes(self):
        lifecycle = 'production' if self.plan.desired_state.lifecycle != 'production' else 'development'
        changed = self.assert_bound('classification',
                                    desired_state=replace(self.plan.desired_state,
                                                          lifecycle=lifecycle))
        self.assertEqual(changed['classification']['lifecycle'], lifecycle)

    def test_the_digest_changes_when_the_request_content_changes(self):
        changed = self.assert_bound(
            'request digest', request=replace(self.plan.request, digest='f' * 64))
        self.assertEqual(changed['request']['digest'], 'f' * 64)

    def test_the_digest_changes_when_the_request_source_changes(self):
        changed = self.assert_bound(
            'request source', request=replace(self.plan.request, source='elsewhere.yaml'))
        self.assertEqual(changed['request']['source'], 'elsewhere.yaml')

    def test_the_digest_changes_when_the_request_identity_changes(self):
        changed = self.assert_bound(
            'request identity', request=replace(self.plan.request, spec={'reviewed': 'changed'}))
        self.assertEqual(changed['request_identity'],
                         canonical_digest({'apiVersion': self.plan.request.api_version,
                                           'kind': self.plan.request.kind,
                                           'metadata': self.plan.request.metadata,
                                           'spec': {'reviewed': 'changed'}}))


class ManifestSensitivityTest(unittest.TestCase):
    """The reviewed inputs themselves move the identity, end to end."""

    def test_a_different_reviewed_inventory_changes_the_identity(self):
        baseline = support.reference_plan()
        other = execution_plan.create_plan(support.reference_document(), REQUEST,
                                           support.reference_fixture('nutanix'),
                                           support.catalogs())
        self.assertNotEqual(other.manifest['inventory']['digest'],
                            baseline.manifest['inventory']['digest'])
        self.assertNotEqual(other.digest, baseline.digest)

    def test_a_different_platform_changes_the_placement_and_the_identity(self):
        nutanix = support.platform_plan('nutanix')
        openstack = support.platform_plan('openstack')
        # The reviewed demonstration corpus declares the same declared tuple for every
        # platform, so the tuple is not a platform discriminator here; the placement
        # decision is, and it is bound into the identity.
        self.assertNotEqual(nutanix.manifest['product_tuple'], UNSELECTED_PRODUCT)
        self.assertNotEqual(nutanix.manifest['placement'], openstack.manifest['placement'])
        self.assertNotEqual(nutanix.digest, openstack.digest)

    def test_a_pinned_site_changes_the_placement_and_the_identity(self):
        # One inventory, two reviewed sites: the only difference between the two plans
        # is the reviewed placement pin, so the placement decision has to move alone.
        inventory = _two_site_fixture()
        unpinned = execution_plan.create_plan(support.reference_document(), REQUEST, inventory,
                                              support.catalogs())
        document = copy.deepcopy(support.reference_document())
        document['spec']['placement']['site'] = 'site-02'
        pinned = execution_plan.create_plan(document, REQUEST, inventory, support.catalogs())
        self.assertEqual(unpinned.decision.site_key, 'site-01')
        self.assertEqual(pinned.decision.site_key, 'site-02')
        self.assertEqual(unpinned.manifest['inventory'], pinned.manifest['inventory'])
        self.assertNotEqual(pinned.decision.digest, unpinned.decision.digest)
        self.assertNotEqual(pinned.manifest['placement'], unpinned.manifest['placement'])
        self.assertNotEqual(pinned.digest, unpinned.digest)

    def test_an_edited_policy_rule_changes_the_identity_without_changing_the_outcome(self):
        baseline = support.reference_plan()
        edited = [dict(rule) for rule in standards.load_rules()]
        edited[0]['description'] = f'{edited[0]["description"]} (reviewed revision 2)'
        with mock.patch.object(standards, 'load_rules', lambda *a, **k: edited):
            changed = execution_plan.create_plan(support.reference_document(), REQUEST,
                                                 fixture(), support.catalogs())
        self.assertEqual(changed.policy['rules_evaluated'],
                         baseline.policy['rules_evaluated'])
        self.assertEqual(changed.policy['rules_failed'], baseline.policy['rules_failed'])
        self.assertEqual(changed.policy['errors'], baseline.policy['errors'])
        self.assertNotEqual(changed.policy['rules_digest'], baseline.policy['rules_digest'])
        self.assertNotEqual(changed.digest, baseline.digest)

    def test_a_bumped_profile_version_changes_the_identity(self):
        baseline = support.reference_plan()
        catalog = support.catalogs()
        family = 'compute'
        bumped = replace(
            catalog,
            families={**catalog.families,
                      family: {name: replace(profile, version='99.0.0')
                               for name, profile in catalog.families[family].items()}},
            versions={**catalog.versions, family: '99.0.0'})
        changed = execution_plan.create_plan(support.reference_document(), REQUEST,
                                             fixture(), bumped)
        self.assertEqual(changed.resolution.profiles, baseline.resolution.profiles)
        self.assertEqual(changed.resolution.profile_versions[family], '99.0.0')
        self.assertNotEqual(changed.desired_state.digest, baseline.desired_state.digest)
        self.assertNotEqual(changed.digest, baseline.digest)

    def test_a_bumped_generation_keeps_every_other_term_identical(self):
        baseline = support.reference_plan()
        later = support.reference_plan(generation=2)
        # The desired state carries the generation by design, so it is the one term
        # that legitimately moves with it; nothing else may.
        self.assertNotEqual(baseline.manifest['desired_state'],
                            later.manifest['desired_state'])
        self.assertEqual({key: value for key, value in baseline.manifest.items()
                          if key not in ('generation', 'desired_state')},
                         {key: value for key, value in later.manifest.items()
                          if key not in ('generation', 'desired_state')})


class ManifestReplayTest(unittest.TestCase):
    """A differently-formatted but equivalent request replays to the same plan."""

    def _variants(self) -> list[str]:
        document = support.reference_document()
        reordered = {key: document[key] for key in reversed(list(document))}
        return [json.dumps(document, sort_keys=True),
                json.dumps(document, indent=4),
                json.dumps(reordered),
                json.dumps(document, sort_keys=True).replace('{', '{\n\n  ')]

    def test_every_equivalent_rendering_of_one_request_replays_one_plan(self):
        from provisioner.domain.request import loads
        baseline = support.reference_plan()
        digests = set()
        for text in self._variants():
            # The same source path: only the rendering of the document differs.
            plan = execution_plan.create_plan(loads(text, REQUEST), REQUEST, fixture(),
                                              support.catalogs())
            digests.add(plan.digest)
            self.assertEqual(plan.manifest['request_identity'],
                             baseline.manifest['request_identity'])
        self.assertEqual(digests, {baseline.digest})

    def test_reordering_the_request_keys_does_not_change_the_identity(self):
        document = support.reference_document()
        reordered = {key: document[key] for key in reversed(list(document))}
        self.assertEqual(canonical_digest(document), canonical_digest(reordered))
        self.assertEqual(plan_manifest.request_identity(_request(document)),
                         plan_manifest.request_identity(_request(reordered)))

    def test_the_manifest_is_stable_across_runs(self):
        first = support.reference_plan()
        second = support.reference_plan()
        self.assertEqual(first.manifest, second.manifest)
        self.assertEqual(first.manifest_digest, second.manifest_digest)


def _request(document):
    from provisioner.domain.request import build
    return build(document, source=REQUEST)


class ApprovedPlanIdentityTest(unittest.TestCase):
    """`hosting apply` proves the approval cites the complete reviewed plan."""

    def _handoff(self) -> tuple[int, dict, dict]:
        code, plan = _run('plan', REQUEST)
        self.assertEqual(code, 0)
        with tempfile.TemporaryDirectory() as directory:
            record = Path(directory) / 'approvals.json'
            record.write_text(json.dumps(
                {'format': 'hosting-plan-approval-set/1',
                 'approvals': [{'plan_digest': plan['digest'],
                                'approved_by': 'reviewer-01',
                                'authority_ref': 'CHG-0001'}]}), encoding='utf-8')
            code, payload = _run('apply', REQUEST, '--approved-plan', plan['digest'],
                                 '--approvals', str(record),
                                 '--source-commit', checkout_commit())
        return code, plan, payload

    def test_the_handoff_cites_the_complete_reviewed_manifest(self):
        code, plan, payload = self._handoff()
        self.assertEqual(code, 2)
        self.assertEqual(payload['status'], 'EXECUTION_REFUSED_HANDOFF_READY')
        self.assertEqual(payload['manifest_digest'], plan['digest'])
        self.assertEqual(payload['manifest'], plan['manifest'])
        self.assertEqual(sorted(payload['manifest']), sorted(plan_manifest.TERMS))
        self.assertEqual(payload['reviewed']['digest'], payload['manifest_digest'])
        self.assertEqual(payload['reviewed']['inventory'], plan['manifest']['inventory'])
        self.assertEqual(payload['reviewed']['rules_digest'],
                         plan['manifest']['policy']['rules_digest'])

    def test_the_handoff_proves_the_approval_cites_that_exact_manifest(self):
        code, _, payload = self._handoff()
        self.assertEqual(code, 2)
        self.assertEqual(payload['approval']['plan_digest'], payload['manifest_digest'])
        self.assertEqual(payload['plan_digest'], payload['manifest_digest'])
        self.assertEqual(canonical_digest(payload['manifest']), payload['manifest_digest'])
        self.assertEqual(payload['generation'], payload['manifest']['generation'])

    def test_a_stale_approval_digest_is_refused_and_names_the_current_manifest(self):
        code, plan = _run('plan', REQUEST)
        self.assertEqual(code, 0)
        code, payload = _run('apply', REQUEST, '--approved-plan', 'f' * 64)
        self.assertEqual(code, 2)
        self.assertEqual(payload['errors'][0]['code'], 'ARTIFACT_INTEGRITY_FAILED')
        self.assertEqual(payload['errors'][0]['details']['manifest_digest'], plan['digest'])

    def test_the_handoff_without_a_digest_names_the_manifest_to_approve(self):
        code, plan = _run('plan', REQUEST)
        self.assertEqual(code, 0)
        code, payload = _run('apply', REQUEST)
        self.assertEqual(code, 2)
        self.assertEqual(payload['errors'][0]['code'], 'AUTHORITY_REQUIRED')
        self.assertEqual(payload['errors'][0]['details']['manifest_digest'], plan['digest'])

    def test_every_read_only_command_reports_the_same_manifest_digest(self):
        code, plan = _run('plan', REQUEST)
        self.assertEqual(code, 0)
        for command in ('status', 'verify', 'evidence'):
            with self.subTest(command=command):
                code, payload = _run(command, REQUEST)
                self.assertEqual(code, 0)
                self.assertEqual(payload['manifest_digest'], plan['digest'])
                self.assertEqual(payload['plan_digest'], plan['digest'])


if __name__ == '__main__':
    unittest.main()