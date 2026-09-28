"""Cross-platform realization contract.

One portable request must generate valid provider-specific realization inputs for
Nutanix, VMware/NSX and OpenStack when each platform is represented by a compatible
reviewed fixture inventory. The request itself never carries a native field.
"""
from __future__ import annotations

import copy
import json
import unittest

from provisioner.compiler.environment import compile_document
from provisioner.inventory import model as inventory_model
from provisioner.placement import eligibility
from tools import compile_wsd

from tests.provisioning import support

PLATFORMS = ('nutanix', 'vmware', 'openstack')
STATE = 'PREPARED_NOT_QUALIFIED_NOT_SERVICE_READY'

#: What a completed native domain phase would read back, per platform.
DOMAIN_READBACK = {
    'nutanix': {'subnet_id': 'mock-subnet', 'security_category_id': 'mock-category'},
    'vmware': {'quarantine_network_id': 'mock-network', 'segment_path': '/mock/segment'},
    'openstack': {'network_id': 'mock-network', 'subnet_id': 'mock-subnet',
                  'security_group_id': 'mock-group'},
}


def compiler():
    return compile_wsd


def native_fields(platform):
    """The native input names the reviewed Terraform modules actually declare.

    Read from the module configuration itself so the contract is checked against
    the reviewed artifact rather than against the compiler accessor the
    provisioner calls.
    """
    module = compiler()
    declared = {}
    for phase in ('domains', 'workloads'):
        path = (support.ROOT / 'terraform' / 'modules'
                / module.COMPONENTS[platform][phase] / 'main.tf.json')
        declared[phase] = set(json.loads(path.read_text(encoding='utf-8'))['variable'])
    return {'placement': set(module.PLACEMENT[platform]),
            'network': set(module.NETWORK[platform]),
            **declared}


request_document = support.platform_request
plan_for = support.platform_plan


def domain_outputs(plan) -> tuple[dict, dict | None]:
    """Synthetic domain-phase readback a native domain phase would produce."""
    platform = plan.desired_state.platform
    key = f'{plan.request.tenant}/{plan.request.wsd}'
    scope = {'tenant_key': plan.request.tenant, 'wsd_key': plan.request.wsd,
             'environment_key': plan.environment['environment_key'],
             'site_key': plan.environment['site_key'], 'platform': platform,
             'phase': 'domains'}
    members = {domain['id']: {'delivery_state': STATE, **DOMAIN_READBACK[platform]}
               for domain in plan.environment['wsds'][0]['domains']}
    outputs = {key: {'scope': {'value': scope}, 'delivery_state': {'value': STATE},
                     'members': {'value': members}}}
    bindings = None
    if platform == 'vmware':
        bindings = {f'{key}/{domain_id}': {
            'segment_path': DOMAIN_READBACK['vmware']['segment_path'],
            'network_id': DOMAIN_READBACK['vmware']['quarantine_network_id']}
            for domain_id in members}
    return outputs, bindings


def workload_inputs(plan) -> dict:
    """Compile the workloads phase for the plan and return the emitted members."""
    outputs, bindings = domain_outputs(plan)
    files, _ = compile_document(plan.environment, 'workloads', outputs, bindings)
    return files[sorted(files)[0]]['members']


class SameRequestEveryPlatformTest(unittest.TestCase):
    """The portable request is identical; only the platform preference is selected."""

    def setUp(self):
        self.plans = {platform: plan_for(platform) for platform in PLATFORMS}

    def test_only_the_platform_preference_differs(self):
        reference = request_document('nutanix')
        for platform in PLATFORMS:
            document = request_document(platform)
            self.assertEqual(document['apiVersion'], reference['apiVersion'])
            self.assertEqual(document['kind'], reference['kind'])
            self.assertEqual(document['metadata'], reference['metadata'])
            expected = copy.deepcopy(reference['spec'])
            expected['platform']['preference'] = platform
            self.assertEqual(document['spec'], expected, platform)

    def test_no_request_key_is_a_native_field_name(self):
        names = set()
        for platform in PLATFORMS:
            fields = native_fields(platform)
            names |= fields['placement'] | fields['network']
        seen = set()

        def walk(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    seen.add(key)
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(request_document('nutanix'))
        self.assertEqual(sorted(seen & names), [])

    def test_every_platform_compiles_the_same_portable_facts(self):
        portable = {}
        for platform, plan in self.plans.items():
            state = plan.desired_state
            portable[platform] = {
                'tenant': state.tenant, 'wsd': state.wsd, 'environment': state.lifecycle,
                'site': state.site_key, 'trust': state.trust,
                'service_class': state.service_class,
                'prefixes': [d['inputs']['ipv4_cidr'] for d in plan.environment['wsds'][0]['domains']],
                'domains': [d['id'] for d in plan.environment['wsds'][0]['domains']],
                'workloads': [sorted(d['workloads']) for d in plan.environment['wsds'][0]['domains']],
                'addresses': [[w.address for w in d.workloads] for d in state.domains],
                'profiles': dict(state.profiles), 'status': plan.status,
                'native_contact': plan.native_contact,
            }
        self.assertEqual(len({json.dumps(v, sort_keys=True) for v in portable.values()}), 1)
        self.assertEqual(portable['nutanix']['status'], 'PLANNED_DISABLED_NOT_AUTHORIZED')
        self.assertFalse(portable['nutanix']['native_contact'])

    def test_platform_family_comes_from_the_repository_registry(self):
        for platform, plan in self.plans.items():
            self.assertEqual(plan.desired_state.platform, platform)
            self.assertEqual(plan.desired_state.platform_family,
                             eligibility.PLATFORM_FAMILY[platform])

    def test_the_environment_document_names_the_selected_platform(self):
        for platform, plan in self.plans.items():
            self.assertEqual(plan.environment['platform'], platform)
            self.assertEqual(plan.desired_state.to_dict()['platform'], platform)


class ReviewedFixtureCorpusTest(unittest.TestCase):
    """Each platform is represented by a compatible, non-authoritative fixture."""

    def test_every_platform_has_a_reviewed_fixture_inventory(self):
        for platform in PLATFORMS:
            with self.subTest(platform=platform):
                inventory = support.reference_fixture(platform)
                self.assertEqual(inventory.status, inventory_model.FIXTURE)
                self.assertFalse(inventory.authoritative)
                self.assertEqual(inventory.site('site-01').platform, platform)

    def test_fixture_placement_identity_is_that_platforms_declared_shape(self):
        for platform in PLATFORMS:
            declared = native_fields(platform)['placement']
            cells = support.reference_fixture(platform).site('site-01').cells
            for cluster in [c for cell in cells for c in cell.clusters]:
                self.assertEqual(set(cluster.native), declared, platform)

    def test_fixture_defaults_never_name_an_undeclared_input(self):
        for platform in PLATFORMS:
            declared = native_fields(platform)
            allowed = declared['domains'] | declared['workloads']
            site = support.reference_fixture(platform).site('site-01')
            supplied = set(site.defaults.get('domain_inputs', {}))
            supplied |= set(site.defaults.get('workload_inputs', {}))
            for flavor_class in site.defaults.get('by_flavor_class', {}):
                supplied |= set(site.workload_inputs(flavor_class, ''))
            self.assertEqual(sorted(supplied - allowed), [], platform)

    def test_the_fixture_is_never_placement_authority(self):
        for platform in PLATFORMS:
            plan = plan_for(platform)
            decision = plan.decision.to_dict()
            self.assertEqual(decision['authority'], 'FIXTURE_NOT_PLACEMENT_AUTHORITY', platform)
            self.assertFalse(decision['qualification']['authoritative'], platform)
            self.assertFalse(plan.decision.authorized, platform)
            self.assertTrue(any('cannot authorize anything' in reason
                                for reason in decision['reasons']), platform)


class ProviderSpecificRealizationTest(unittest.TestCase):
    """Realization inputs differ per platform and match that platform's own modules."""

    def setUp(self):
        self.plans = {platform: plan_for(platform) for platform in PLATFORMS}

    def test_cluster_native_identity_is_the_declared_placement_shape(self):
        for platform, plan in self.plans.items():
            declared = native_fields(platform)['placement']
            for row in plan.environment['clusters']:
                self.assertEqual(set(row['native']), declared, platform)

    def test_domain_inputs_are_declared_by_that_platform_only(self):
        for platform, plan in self.plans.items():
            declared = native_fields(platform)['domains']
            domain = plan.environment['wsds'][0]['domains'][0]
            self.assertLessEqual(set(domain['inputs']), declared, platform)
            defaults = support.reference_fixture(platform).site('site-01').domain_inputs()
            self.assertEqual(set(domain['inputs']) - {'ipv4_cidr', 'gateway_host_number'},
                             set(defaults), platform)

    def test_workload_inputs_are_declared_by_that_platform_only(self):
        for platform, plan in self.plans.items():
            declared = native_fields(platform)['workloads']
            emitted = {name: set(row) for name, row in workload_inputs(plan).items()}
            for name, fields in emitted.items():
                self.assertLessEqual(fields, declared, f'{platform}/{name}')
            self.assertTrue(emitted)

    def test_placement_and_network_identity_reach_the_workloads_phase(self):
        for platform, plan in self.plans.items():
            declared = native_fields(platform)
            members = workload_inputs(plan)
            sample = members[sorted(members)[0]]
            self.assertLessEqual(declared['placement'] | declared['network'], set(sample),
                                 platform)

    def test_no_platform_leaks_another_platforms_fields(self):
        shapes = {platform: set(workload_inputs(self.plans[platform])[
            sorted(workload_inputs(self.plans[platform]))[0]]) for platform in PLATFORMS}
        self.assertIn('storage_container_id', shapes['nutanix'])
        self.assertNotIn('storage_container_id', shapes['vmware'])
        self.assertIn('resource_pool_id', shapes['vmware'])
        self.assertNotIn('resource_pool_id', shapes['nutanix'])
        self.assertIn('network_id', shapes['openstack'])
        self.assertNotIn('network_id', shapes['vmware'])

    def test_each_platform_compiles_into_its_own_reviewed_stack_root(self):
        for platform, plan in self.plans.items():
            roots = {scope['root'] for scope in plan.terraform_scopes}
            self.assertEqual(roots, {f'terraform/stacks/wsd/{platform}/domains'}, platform)


class RealizationBoundaryTest(unittest.TestCase):
    """A platform that cannot carry a computed fact must say so."""

    def test_vsphere_reports_the_address_it_cannot_carry(self):
        plan = plan_for('vmware')
        warnings = [w for w in plan.warnings if w['code'] == 'REALIZATION_INPUT_UNAVAILABLE']
        self.assertEqual(len(warnings), 1)
        self.assertIn('ipv4_address', warnings[0]['message'])
        self.assertEqual(warnings[0]['layer'], 'compilation')

    def test_platforms_that_accept_the_address_do_not_warn(self):
        for platform in ('nutanix', 'openstack'):
            plan = plan_for(platform)
            self.assertEqual([w for w in plan.warnings
                              if w['code'] == 'REALIZATION_INPUT_UNAVAILABLE'], [], platform)

    def test_the_address_is_still_allocated_for_every_platform(self):
        for platform in PLATFORMS:
            plan = plan_for(platform)
            addresses = [w.address for d in plan.desired_state.domains for w in d.workloads]
            self.assertTrue(addresses, platform)
            self.assertEqual(len(set(addresses)), len(addresses), platform)


class ReferenceCorpusCrossPlatformTest(unittest.TestCase):
    """Every reviewed reference request compiles for every platform."""

    def test_every_reference_request_compiles_on_every_platform(self):
        for name in support.REFERENCE_REQUESTS:
            for platform in PLATFORMS:
                plan = support.platform_plan(platform, name)
                self.assertEqual(plan.status, 'PLANNED_DISABLED_NOT_AUTHORIZED',
                                 f'{name}/{platform}')
                self.assertFalse(plan.native_contact, f'{name}/{platform}')
                self.assertTrue(plan.compiled, f'{name}/{platform}')


if __name__ == '__main__':
    unittest.main()
