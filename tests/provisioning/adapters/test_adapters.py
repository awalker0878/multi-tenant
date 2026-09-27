"""The platform adapter boundary and the execution scopes it feeds."""
from __future__ import annotations

import unittest

from provisioner.adapters import base as adapter_base
from provisioner.domain.errors import ProvisioningError
from provisioner.execution import ansible, delivery, terraform
from provisioner.placement import eligibility
from scripts import build_wsd_compositions
from tools import compile_wsd

from tests.provisioning import support

PLATFORMS = ('nutanix', 'vmware', 'openstack')


class AdapterBoundaryTest(unittest.TestCase):
    def test_one_adapter_is_declared_per_platform(self):
        self.assertEqual(sorted(adapter_base.adapters()), sorted(PLATFORMS))

    def test_an_unknown_platform_has_no_adapter(self):
        with self.assertRaises(ValueError):
            adapter_base.get('hyper-v')

    def test_every_adapter_declares_both_phase_modules(self):
        for platform, adapter in adapter_base.adapters().items():
            self.assertEqual(adapter.platform, platform)
            self.assertTrue(adapter.domains_module, platform)
            self.assertTrue(adapter.workloads_module, platform)
            self.assertTrue(adapter.security_edge, platform)

    def test_adapters_cannot_drift_from_the_existing_compiler(self):
        for platform, adapter in adapter_base.adapters().items():
            self.assertEqual(sorted(adapter.placement_fields), sorted(compile_wsd.PLACEMENT[platform]))
            self.assertEqual(sorted(adapter.network_fields), sorted(compile_wsd.NETWORK[platform]))

    def test_adapters_cannot_drift_from_the_composition_roots(self):
        components = build_wsd_compositions.COMPONENTS
        for platform, adapter in adapter_base.adapters().items():
            self.assertEqual(adapter.domains_module, components[platform]['domains'])
            self.assertEqual(adapter.workloads_module, components[platform]['workloads'])

    def test_no_adapter_claims_native_qualification(self):
        for platform, adapter in adapter_base.adapters().items():
            self.assertFalse(adapter.qualified, platform)
            self.assertEqual(adapter.product_tuple, 'UNSELECTED')
            self.assertEqual(adapter.capability_contract()['status'],
                             'NATIVE_QUALIFICATION_ABSENT')

    def test_adapter_shape_matches_the_capability_registry(self):
        registry = eligibility.registry()
        for platform, adapter in adapter_base.adapters().items():
            self.assertEqual(registry['profiles'][adapter.family]['product_tuple'],
                             adapter.product_tuple)

    def test_adapter_serialisation_never_contacts_a_platform(self):
        for adapter in adapter_base.adapters().values():
            payload = adapter.realization_contract()
            self.assertFalse(payload['native_contact'])
            self.assertTrue(payload['limits'])
            self.assertEqual(payload['format'], adapter_base.CONTRACT_FORMAT)


class TerraformScopeTest(unittest.TestCase):
    def test_the_reviewed_catalog_is_readable(self):
        self.assertEqual(terraform.catalog()['format'], 'hosting-terraform-catalog/1')

    def test_every_platform_phase_has_a_reviewed_composition(self):
        for platform in PLATFORMS:
            for phase in terraform.PHASES:
                entry = terraform.composition(platform, phase)
                self.assertEqual(entry['root'], f'terraform/stacks/wsd/{platform}/{phase}')

    def test_an_unknown_phase_is_refused(self):
        with self.assertRaises(ProvisioningError) as raised:
            terraform.composition('openstack', 'networks')
        self.assertEqual(raised.exception.code, 'UNSUPPORTED_FEATURE')

    def test_an_undeclared_composition_root_is_refused(self):
        scope = {'root': 'terraform/stacks/wsd/openstack/elsewhere',
                 'scope': {'phase': 'domains'}}
        with self.assertRaises(ProvisioningError) as raised:
            terraform.assert_scopes([scope], 'openstack')
        self.assertEqual(raised.exception.code, 'ENVIRONMENT_CONTRACT_INVALID')

    def test_compiled_scopes_are_disabled_and_unauthorized(self):
        plan = support.reference_plan()
        self.assertTrue(plan.terraform_scopes)
        for scope in plan.terraform_scopes:
            self.assertEqual(scope['status'], 'DRAFT_DISABLED_NOT_AUTHORIZED')
            self.assertEqual(scope['owner_scope'], 'wsd')
            self.assertEqual(scope['catalog_id'], 'openstack-wsd-domains')

    def test_the_state_backend_is_owned_by_the_stack_owner(self):
        plan = support.reference_plan()
        self.assertTrue(any('owner' in scope['backend'] for scope in plan.terraform_scopes))

    def test_compiled_inputs_are_named_inside_the_private_output_tree(self):
        plan = support.reference_plan()
        for scope in plan.terraform_scopes:
            self.assertIn(scope['input'], plan.compiled)


class AnsibleScopeTest(unittest.TestCase):
    def test_the_reviewed_catalog_is_readable(self):
        self.assertEqual(ansible.catalog()['format'], 'hosting-ansible-catalog/1')

    def test_every_profile_resolves_to_a_registered_playbook(self):
        registered = {row['path'] for row in ansible.catalog()['playbooks']}
        for profile in ansible.PROFILES:
            scope = ansible.scope(profile, 'workloads')
            self.assertTrue(set(scope['playbooks']) <= registered)

    def test_an_unknown_profile_is_refused(self):
        with self.assertRaises(ProvisioningError) as raised:
            ansible.scope('windows', 'workloads')
        self.assertEqual(raised.exception.code, 'UNSUPPORTED_FEATURE')

    def test_guest_scope_waits_for_platform_identity(self):
        plan = support.reference_plan()
        self.assertTrue(plan.ansible_scopes)
        for scope in plan.ansible_scopes:
            self.assertEqual(scope['status'], 'HELD_PENDING_PLATFORM_IDENTITY')
            self.assertFalse(scope['native_contact'])


class DeliveryPlanTest(unittest.TestCase):
    def test_every_owner_operation_is_named_once(self):
        plan = support.reference_plan()
        names = [operation['name'] for operation in plan.delivery['operations']]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(names[0], 'state-backend')
        self.assertIn('production-authorization', names)
        self.assertIn('guest-configuration', names)

    def test_blocking_operations_are_a_subset_of_the_operations(self):
        plan = support.reference_plan()
        names = {operation['name'] for operation in plan.delivery['operations']}
        self.assertTrue(set(plan.delivery['blocking']) <= names)

    def test_execution_authority_is_never_held_here(self):
        plan = support.reference_plan()
        self.assertEqual(plan.delivery['status'], 'PLANNED_DISABLED_NOT_AUTHORIZED')
        self.assertFalse(plan.delivery['native_contact'])

    def test_require_unblocked_refuses_while_an_owner_operation_is_outstanding(self):
        plan = support.reference_plan()
        with self.assertRaises(ProvisioningError) as raised:
            delivery.require_unblocked(plan.delivery)
        self.assertEqual(raised.exception.code, 'EXECUTION_REFUSED')

    def test_each_operation_names_its_owner_and_effect(self):
        plan = support.reference_plan()
        for operation in plan.delivery['operations']:
            self.assertTrue(operation['owner'], operation['name'])
            self.assertTrue(operation['description'], operation['name'])
            self.assertTrue(operation['details'])


class PhaseTest(unittest.TestCase):
    def test_domains_compile_and_workloads_hold(self):
        plan = support.reference_plan()
        phases = {phase['phase']: phase['status'] for phase in plan.phases}
        self.assertEqual(phases['domains'], 'COMPILED_DISABLED_NOT_AUTHORIZED')
        self.assertEqual(phases['workloads'], 'HELD_PENDING_NATIVE_DOMAIN_OUTPUTS')

    def test_the_plan_holds_no_authority(self):
        plan = support.reference_plan()
        self.assertEqual(plan.status, 'PLANNED_DISABLED_NOT_AUTHORIZED')
        self.assertFalse(plan.to_dict()['native_contact'])


if __name__ == '__main__':
    unittest.main()
