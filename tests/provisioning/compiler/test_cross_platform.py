"""Cross-platform realization contract.

One portable request must generate valid provider-specific realization inputs for
Nutanix, VMware/NSX and OpenStack when each platform is represented by compatible
reviewed fixture inventory. The request itself never carries a native field.
"""
from __future__ import annotations

import copy
import json
import unittest

from provisioner.compiler.environment import compile_document
from provisioner.domain.request import load as load_document
from provisioner.execution.plan import create_plan
from provisioner.inventory import model as inventory_model
from provisioner.repository import repository_module
from provisioner.placement import eligibility

from tests.provisioning import support

PLATFORMS = ('nutanix', 'vmware', 'openstack')
STATE = 'PREPARED_NOT_QUALIFIED_NOT_SERVICE_READY'

#: Reviewed inventory defaults per platform: the native inputs the site owns.
SITE_DEFAULTS = {
    'nutanix': {'domain_inputs': {},
                'workload_inputs': {'project_id': 'mock-project', 'image_id': 'mock-image'}},
    'vmware': {'domain_inputs': {'transport_zone_path': 'mock-tz', 'quarantine_sequence': 10},
               'workload_inputs': {'template_uuid': 'mock-template', 'guest_id': 'mock-guest',
                                   'scsi_type': 'mock-scsi', 'firmware': 'mock-firmware',
                                   'storage_policy_id': 'mock-policy'}},
    'openstack': {'domain_inputs': {'project_id': 'mock-project'},
                  'workload_inputs': {'image_id': 'mock-image'},
                  'by_flavor_class': {'small': {'flavor_id': 'mock-flavor-small'},
                                      'medium': {'flavor_id': 'mock-flavor-medium'},
                                      'large': {'flavor_id': 'mock-flavor-large'}}},
}

#: What a completed native domain phase would read back, per platform.
DOMAIN_READBACK = {
    'nutanix': {'subnet_id': 'mock-subnet', 'security_category_id': 'mock-category'},
    'vmware': {'quarantine_network_id': 'mock-network', 'segment_path': '/mock/segment'},
    'openstack': {'network_id': 'mock-network', 'subnet_id': 'mock-subnet',
                  'security_group_id': 'mock-group'},
}

CAPABILITIES = ('network_domain', 'ipv4', 'gateway_policy', 'distributed_firewall',
                'audit_logging', 'dedicated_edge_context', 'native_load_balancer')

SERVICES = (
    ('dns', 'dns-internal', {'resolvers': ['198.51.100.53', '198.51.101.53'],
                             'zone': 'internal.invalid'}),
    ('ntp', 'ntp-internal', {'sources': ['198.51.100.123', '198.51.101.123']}),
    ('identity', 'identity-directory', {'realm': 'INTERNAL.INVALID',
                                        'servers': ['198.51.100.10', '198.51.101.10']}),
    ('logging', 'logging-protected', {'collectors': ['198.51.100.20', '198.51.101.20']}),
    ('backup', 'backup-isolated', {'target': '198.51.100.30'}),
)


def compiler():
    return repository_module('tools.compile_wsd')


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


def cluster(cluster_id: str, zone: str, platform: str) -> dict:
    return {'id': cluster_id, 'role': 'workload', 'zone': zone, 'trust': 'internal-trust',
            'service_classes': ['standard', 'protected-b'], 'eligible_tenants': ['tenant-01'],
            'dedicated_wsd': None, 'host_ids': [f'host-{cluster_id}'],
            'native': {field: f'mock-{field}' for field in sorted(native_fields(platform)['placement'])},
            'capacity': {'vcpu_total': 128, 'vcpu_committed': 16, 'memory_gib_total': 512,
                         'memory_gib_committed': 64, 'storage_gib_total': 4096,
                         'storage_gib_committed': 512}}


def inventory_document(platform: str) -> dict:
    """Compatible reviewed fixture inventory for one platform."""
    return {
        'format': inventory_model.INVENTORY_FORMAT,
        'status': inventory_model.FIXTURE,
        'source': 'cross-platform-realization-test',
        'sites': [{'site': 'site-01', 'region': 'east', 'platform': platform,
                   'defaults': copy.deepcopy(SITE_DEFAULTS[platform]),
                   'cells': [{'cell': 'cell-01', 'capabilities': list(CAPABILITIES),
                              'clusters': [cluster('cluster-oz-01', 'OZ', platform),
                                           cluster('cluster-rz-01', 'RZ', platform)]}]}],
        'prefix_pools': [
            {'pool': 'pool-oz', 'site': 'site-01', 'zone': 'OZ', 'cidr': '198.51.100.0/24',
             'prefix_length': 27, 'gateway_host_number': 1, 'allocations': []},
            {'pool': 'pool-rz', 'site': 'site-01', 'zone': 'RZ', 'cidr': '198.51.101.0/24',
             'prefix_length': 27, 'gateway_host_number': 1, 'allocations': []}],
        'services': [{'service': name, 'binding_class': binding_class, 'site': 'site-01',
                      'endpoints': dict(endpoints)} for name, binding_class, endpoints in SERVICES],
    }


def request_document(platform: str) -> dict:
    """The reviewed reference request with only the platform preference selected."""
    document = copy.deepcopy(support.reference_document())
    document['spec']['platform']['preference'] = platform
    return document


def plan_for(platform: str, compile_environment: bool = True):
    return create_plan(request_document(platform), '<cross-platform>',
                       inventory_model.build(inventory_document(platform)),
                       support.catalogs(), compile_environment=compile_environment)


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
            self.assertEqual(set(domain['inputs']) - {'ipv4_cidr', 'gateway_host_number'},
                             set(SITE_DEFAULTS[platform]['domain_inputs']), platform)

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
            document = load_document(support.request_path(name))
            for platform in PLATFORMS:
                variant = copy.deepcopy(document)
                variant['spec']['platform']['preference'] = platform
                plan = create_plan(variant, f'<{name}>',
                                   inventory_model.build(inventory_document(platform)),
                                   support.catalogs())
                self.assertEqual(plan.status, 'PLANNED_DISABLED_NOT_AUTHORIZED',
                                 f'{name}/{platform}')
                self.assertFalse(plan.native_contact, f'{name}/{platform}')
                self.assertTrue(plan.compiled, f'{name}/{platform}')


if __name__ == '__main__':
    unittest.main()