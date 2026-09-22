"""The compiler boundary: environment contract, desired state and determinism."""
from __future__ import annotations

import json
import unittest

from provisioner.compiler import artifacts, desired_state, environment
from provisioner.domain.errors import ProvisioningError

from tests.provisioning import support


class DesiredStateTest(unittest.TestCase):
    def test_state_is_bound_to_the_request_digest(self):
        plan = support.reference_plan()
        self.assertEqual(plan.desired_state.request_digest, plan.request.digest)

    def test_state_declares_both_zones_with_stable_domain_identities(self):
        plan = support.reference_plan()
        state = plan.desired_state
        self.assertEqual([d.zone for d in state.domains], ['OZ', 'RZ'])
        self.assertEqual([d.domain_id for d in state.domains], ['wsd-01-OZ', 'wsd-01-RZ'])

    def test_every_zone_has_a_prefix_a_gateway_and_workloads(self):
        plan = support.reference_plan()
        for domain in plan.desired_state.domains:
            self.assertTrue(domain.prefix.endswith('/27'))
            self.assertEqual(domain.gateway_host_number, 1)
            self.assertTrue(domain.workloads)
            for workload in domain.workloads:
                self.assertRegex(workload.address, r'^\d+\.\d+\.\d+\.\d+$')

    def test_workload_names_are_derived_from_portable_names(self):
        plan = support.reference_plan()
        names = sorted(w.name for d in plan.desired_state.domains for w in d.workloads)
        self.assertEqual(names, ['tenant-01-wsd-01-oz-01', 'tenant-01-wsd-01-rz-01'])
        self.assertTrue(all(n.startswith('tenant-01-wsd-01-') for n in names))

    def test_no_native_identifier_appears_in_the_desired_state(self):
        plan = support.reference_plan()
        payload = plan.desired_state.to_dict()
        self.assertFalse(payload['native_contact'])
        self.assertNotIn('native', json.dumps(payload['domains'][0]).lower())
        self.assertEqual(payload['platform_family'], 'openstack')

    def test_capacity_is_proposed_never_applied(self):
        plan = support.reference_plan()
        for reservation in plan.desired_state.reservations.values():
            self.assertEqual(reservation['status'], 'PROPOSED_NOT_APPLIED')
            self.assertFalse(reservation['applied'])

    def test_service_bindings_come_from_reviewed_inventory(self):
        plan = support.reference_plan()
        self.assertTrue(plan.desired_state.service_bindings)
        for binding in plan.desired_state.service_bindings:
            self.assertEqual(binding['site'], 'site-01')

    def test_state_cannot_be_assembled_from_a_held_decision(self):
        from provisioner.domain.placement import PlacementDecision
        held = PlacementDecision(status='HOLD_NO_ELIGIBLE_PLATFORM', authority='FIXTURE',
                                 request_digest='a' * 64, selection_rule='test')
        self.assertTrue(held.held)
        with self.assertRaises(ProvisioningError) as raised:
            desired_state.build(None, None, held, None)
        self.assertEqual(raised.exception.code, 'NO_ELIGIBLE_PLACEMENT')


class EnvironmentContractTest(unittest.TestCase):
    def test_environment_uses_the_reviewed_contract(self):
        plan = support.reference_plan()
        self.assertEqual(plan.environment['format'], 'hosting-wsd-environment/1')

    def test_environment_key_is_site_plus_lifecycle(self):
        plan = support.reference_plan()
        self.assertEqual(plan.environment['environment_key'],
                         f"{plan.environment['site_key']}-{plan.environment['lifecycle']}")

    def test_environment_carries_clusters_and_wsds_only(self):
        plan = support.reference_plan()
        self.assertEqual(sorted(plan.environment.keys()),
                         ['clusters', 'environment_key', 'format', 'lifecycle',
                          'platform', 'site_key', 'wsds'])
        self.assertEqual(len(plan.environment['wsds']), 1)

    def test_environment_is_deterministic(self):
        first = support.reference_plan().environment
        second = support.reference_plan().environment
        self.assertEqual(artifacts.render(first), artifacts.render(second))


class ArtifactTest(unittest.TestCase):
    def test_render_is_canonical_and_newline_terminated(self):
        rendered = artifacts.render({'b': 1, 'a': 2})
        self.assertTrue(rendered.endswith('\n'))
        self.assertEqual(rendered, '{"a":2,"b":1}\n')

    def test_deterministic_artifacts_return_a_stable_digest(self):
        value = {'a': 1}
        self.assertEqual(artifacts.assert_deterministic('x', value),
                         artifacts.assert_deterministic('x', dict(value)))

    def test_output_outside_the_repository_is_refused(self):
        with self.assertRaises(ProvisioningError) as raised:
            artifacts.assert_output_path(support.ROOT / 'generated')
        self.assertEqual(raised.exception.code, 'OUTPUT_PATH_NOT_PRIVATE')

    def test_generated_inputs_are_never_committed(self):
        names = {name.split('.')[-1] for name in support.reference_plan().compiled}
        self.assertNotIn('tfvars', names - {'json'})


class NormalizeTest(unittest.TestCase):
    def test_defaults_cover_every_group_the_pipeline_needs(self):
        from provisioner.compiler import normalize
        self.assertEqual(sorted(normalize.DEFAULTS),
                         ['assurance', 'capacity', 'exposure', 'network', 'placement',
                          'recovery', 'services', 'zones'])

    def test_environment_module_derives_native_domain_ids(self):
        self.assertEqual(environment.domain_id('wsd-01', 'OZ'), 'wsd-01-OZ')
        self.assertEqual(environment.workload_name('tenant-01', 'wsd-01', 'RZ', 0),
                         'tenant-01-wsd-01-rz-01')


if __name__ == '__main__':
    unittest.main()