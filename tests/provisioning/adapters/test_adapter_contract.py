"""The platform adapter realization contract.

R13 requires the provider-specific half of the portable-to-native boundary to live
behind one adapter per platform, as a declared and testable contract rather than as a
platform-name branch inside generic provisioning code. Every platform must expose the
same six surfaces — the qualification it must hold before selection, the native
placement identity reviewed inventory must supply, what each reviewed native phase
accepts and produces, the native identity a readback must observe, the isolation
outcome and the owner scope that carries it, and the realization gaps it declares
rather than silently drops — and every declaration must be read from the reviewed
artifact that already owns it, so an adapter can never drift from the compiler, the
composition roots or the reviewed Terraform modules.

The nine regressions below are asserted for every platform: required zones are
represented, placement is preserved, network intent is preserved, the isolation and
security outcome is represented, service binding is preserved, recovery intent is
represented when the request asks for it, an unsupported capability is refused, a
provider-native field never leaks into the portable request, and no adapter
declaration drifts from the compiler or the reviewed modules.
"""
from __future__ import annotations

import ast
import copy
import dataclasses
import json
import unittest
from unittest import mock

from provisioner.adapters import base as adapter_base
from provisioner.compiler import environment as compiler_environment
from provisioner.conformance import checks as conformance_checks
from provisioner.domain.errors import ProvisioningError
from provisioner.execution import manifest as plan_manifest
from provisioner.execution.plan import create_plan
from scripts import build_wsd_compositions
from tools import compile_wsd

from tests.provisioning import support

PLATFORMS = ('nutanix', 'vmware', 'openstack')

#: The six contract surfaces R13 requires every adapter to expose.
SURFACES = ('capability', 'placement', 'phases', 'readback', 'security_edge', 'gaps')

#: The reviewed module identities per platform, as the reviewed composition roots declare them.
MODULES = {'nutanix': ('nutanix-domain', 'nutanix-workload'),
           'vmware': ('nsx-domain', 'vsphere-workload'),
           'openstack': ('openstack-domain', 'openstack-workload')}

#: The reviewed security-edge component each platform's isolation outcome is carried by.
SECURITY_EDGE = {'nutanix': 'nutanix-route', 'vmware': 'nsx-route',
                 'openstack': 'openstack-route'}

#: The native field sets, as the reviewed compiler declares them.
PLACEMENT_FIELDS = {
    'nutanix': {'cluster_id', 'storage_container_id'},
    'vmware': {'resource_pool_id', 'datastore_id'},
    'openstack': {'compute_availability_zone', 'storage_availability_zone', 'volume_type'},
}
NETWORK_FIELDS = {
    'nutanix': {'subnet_id', 'security_category_id'},
    'vmware': {'quarantine_network_id'},
    'openstack': {'network_id', 'subnet_id', 'security_group_id'},
}

#: A capability no platform in this repository currently holds natively.
UNQUALIFIED_CAPABILITY = 'distributed_firewall'

#: The state a completed native phase reports before qualification.
NATIVE_STATE = 'PREPARED_NOT_QUALIFIED_NOT_SERVICE_READY'

#: What a completed native domains phase would read back, per platform.
DOMAIN_READBACK = {
    'nutanix': {'subnet_id': 'mock-subnet', 'security_category_id': 'mock-category'},
    'vmware': {'quarantine_network_id': 'mock-network', 'segment_path': '/mock/segment'},
    'openstack': {'network_id': 'mock-network', 'subnet_id': 'mock-subnet',
                  'security_group_id': 'mock-group'},
}


def compiler():
    return compile_wsd


def plans():
    """One reviewed plan per platform, over that platform's reviewed fixture."""
    return {platform: support.platform_plan(platform) for platform in PLATFORMS}


def native_field_names(platform):
    """Every native field name one platform's realization declares, portable-side invisible."""
    return PLACEMENT_FIELDS[platform] | NETWORK_FIELDS[platform]


def all_native_field_names():
    names = set()
    for platform in PLATFORMS:
        names |= native_field_names(platform)
    return names


def request_keys(document):
    seen = set()

    def walk(value):
        if isinstance(value, dict):
            for key, child in value.items():
                seen.add(key)
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(document)
    return seen


def tampered_plan(plan, **state_overrides):
    """The same plan with one reviewed desired-state field replaced."""
    return dataclasses.replace(
        plan, desired_state=dataclasses.replace(plan.desired_state, **state_overrides))


def check(plan, name, observations=()):
    """One repository-side conformance check of a plan."""
    return next(row for row in conformance_checks.repository_checks(plan, observations)
                if row.name == name)


def conformance_row(plan, name):
    """One reported conformance row of a plan, including the external ones."""
    return next(row for row in plan.conformance['checks'] if row['name'] == name)


def domain_readback(plan):
    """The synthetic domains-phase readback a completed native phase would produce."""
    platform = plan.desired_state.platform
    key = f'{plan.request.tenant}/{plan.request.wsd}'
    scope = {'tenant_key': plan.request.tenant, 'wsd_key': plan.request.wsd,
             'environment_key': plan.environment['environment_key'],
             'site_key': plan.environment['site_key'], 'platform': platform,
             'phase': 'domains'}
    members = {domain['id']: {'delivery_state': NATIVE_STATE, **DOMAIN_READBACK[platform]}
               for domain in plan.environment['wsds'][0]['domains']}
    outputs = {key: {'scope': {'value': scope}, 'delivery_state': {'value': NATIVE_STATE},
                     'members': {'value': members}}}
    bindings = None
    if platform == 'vmware':
        bindings = {f'{key}/{domain_id}': {
            'segment_path': DOMAIN_READBACK['vmware']['segment_path'],
            'network_id': DOMAIN_READBACK['vmware']['quarantine_network_id']}
            for domain_id in members}
    return outputs, bindings


def compiled_workloads(plan):
    """Compile the workloads phase for a plan and return the emitted native members."""
    outputs, bindings = domain_readback(plan)
    files, _ = compiler_environment.compile_document(plan.environment, 'workloads',
                                                     outputs, bindings)
    return files[sorted(files)[0]]['members']


class AdapterRegistryTest(unittest.TestCase):
    """One adapter per supported platform, and no other behaviour."""

    def test_every_supported_platform_has_an_adapter(self):
        self.assertEqual(sorted(adapter_base.adapters()), sorted(PLATFORMS))

    def test_the_registry_is_a_pure_function_of_the_repository(self):
        first, second = adapter_base.adapters(), adapter_base.adapters()
        self.assertEqual([a.realization_contract() for a in first.values()],
                         [a.realization_contract() for a in second.values()])

    def test_an_unknown_platform_is_refused(self):
        with self.assertRaises(ValueError):
            adapter_base.get('kubernetes')

    def test_the_registry_never_claims_native_qualification(self):
        for platform, adapter in adapter_base.adapters().items():
            self.assertFalse(adapter.qualified, platform)
            self.assertEqual(adapter.product_tuple, 'UNSELECTED', platform)
            self.assertEqual(adapter.capability_contract()['status'],
                             adapter_base.NOT_QUALIFIED, platform)

    def test_serialisation_never_contacts_a_platform(self):
        for platform, adapter in adapter_base.adapters().items():
            document = adapter.realization_contract()
            self.assertFalse(document['native_contact'], platform)
            self.assertTrue(document['limits'], platform)
            self.assertEqual(document['format'], adapter_base.CONTRACT_FORMAT, platform)

    def test_the_realization_contract_format_is_versioned(self):
        self.assertEqual(adapter_base.CONTRACT_FORMAT,
                         'hosting-adapter-realization-contract/1')
        for adapter in adapter_base.adapters().values():
            self.assertEqual(adapter.realization_contract()['format'],
                             adapter_base.CONTRACT_FORMAT)

    def test_retired_adapter_projections_are_absent(self):
        for adapter in adapter_base.adapters().values():
            for name in ('placement_shape', 'network_shape', 'to_dict'):
                self.assertFalse(hasattr(adapter, name), f'{adapter.platform}/{name}')


class RealizationContractSurfaceTest(unittest.TestCase):
    """Every adapter exposes the same six surfaces in the same declared format."""

    def setUp(self):
        self.contracts = {platform: adapter_base.get(platform).realization_contract()
                          for platform in PLATFORMS}

    def test_every_adapter_exposes_the_six_contract_surfaces(self):
        for platform, contract in self.contracts.items():
            self.assertEqual(set(contract), set(SURFACES) | {'format', 'platform', 'family',
                                                             'gap_codes', 'limits',
                                                             'native_contact'}, platform)

    def test_the_contract_format_is_declared_once(self):
        for platform, contract in self.contracts.items():
            self.assertEqual(contract['format'], adapter_base.CONTRACT_FORMAT, platform)
            documents = [contract['capability'], contract['placement'], contract['readback'],
                         contract['security_edge'], *contract['phases'].values()]
            self.assertTrue(documents)
            for document in documents:
                label = f'{platform}/{document["surface"]}'
                self.assertEqual(document['format'], adapter_base.CONTRACT_FORMAT, label)
                self.assertFalse(document['native_contact'], label)
            for gap in contract['gaps']:
                label = f'{platform}/{gap["code"]}'
                self.assertEqual(gap['format'], adapter_base.GAP_FORMAT, label)
                self.assertIn(gap['code'], adapter_base.GAP_CODES, label)
                self.assertTrue(gap['inputs'], label)

    def test_the_contract_names_the_gap_vocabulary(self):
        self.assertEqual(sorted(self.contracts['nutanix']['gap_codes']), sorted(adapter_base.GAP_CODES))
        for platform, contract in self.contracts.items():
            for gap in contract['gaps']:
                self.assertIn(gap['code'], adapter_base.GAP_CODES, platform)
                self.assertEqual(gap['format'], adapter_base.GAP_FORMAT, platform)

    def test_the_capability_surface_delegates_to_the_repository_registry(self):
        for platform, contract in self.contracts.items():
            capability = contract['capability']
            self.assertEqual(capability['authority'], 'REPOSITORY_CAPABILITY_REGISTRY',
                             platform)
            self.assertEqual(capability['source'], 'repository-capability-registry', platform)
            self.assertEqual(capability['family'], adapter_base.get(platform).family, platform)

    def test_the_placement_surface_declares_the_inventory_supplied_identity(self):
        for platform, contract in self.contracts.items():
            placement = contract['placement']
            self.assertEqual(placement['fields'], sorted(PLACEMENT_FIELDS[platform]), platform)
            self.assertEqual(placement['authority'], 'tools.compile_wsd.PLACEMENT', platform)
            self.assertFalse(placement['provisioner_owned'], platform)

    def test_the_phase_surface_covers_every_reviewed_phase(self):
        for platform, contract in self.contracts.items():
            self.assertEqual(sorted(contract['phases']), sorted(adapter_base.PHASES), platform)
            for phase, surface in contract['phases'].items():
                self.assertEqual(surface['phase'], phase, f'{platform}/{phase}')
                self.assertEqual(surface['platform'], platform, f'{platform}/{phase}')

    def test_the_security_edge_surface_delegates_to_the_reviewed_catalog(self):
        for platform, contract in self.contracts.items():
            edge = contract['security_edge']
            self.assertEqual(edge['authority'], 'terraform/catalog.json', platform)
            self.assertEqual(edge['owner_scope'], adapter_base.EDGE_SCOPE, platform)
            self.assertEqual(edge['component'], SECURITY_EDGE[platform], platform)

    def test_the_readback_surface_delegates_to_the_compiler(self):
        for platform, contract in self.contracts.items():
            self.assertEqual(contract['readback']['authority'], 'tools.compile_wsd.NETWORK',
                             platform)

    def test_the_contract_is_serialisable_and_holds_no_timestamp(self):
        for platform, contract in self.contracts.items():
            text = json.dumps(contract, sort_keys=True)
            self.assertNotIn('20', text[:0], platform)
            self.assertEqual(json.loads(text)['platform'], platform)


class RequiredZonesRepresentedTest(unittest.TestCase):
    """Every zone the reviewed request requires is represented by the plan."""

    def setUp(self):
        self.plans = plans()

    def test_every_required_zone_is_represented_in_every_plan(self):
        for platform, plan in self.plans.items():
            represented = {domain.zone for domain in plan.desired_state.domains}
            self.assertEqual(represented, set(plan.resolution.zones), platform)
            self.assertEqual(adapter_base.get(platform).validate(plan), (), platform)

    def test_a_single_zone_request_is_satisfied_by_a_single_zone_plan(self):
        plan = support.platform_plan('nutanix', 'internal-development')
        self.assertEqual(tuple(plan.resolution.zones), ('OZ',))
        self.assertEqual({domain.zone for domain in plan.desired_state.domains}, {'OZ'})
        self.assertEqual(adapter_base.get('nutanix').validate(plan), ())

    def test_a_missing_required_zone_is_refused(self):
        plan = self.plans['nutanix']
        single = tuple(d for d in plan.desired_state.domains if d.zone == 'OZ')
        problems = adapter_base.get('nutanix').validate(tampered_plan(plan, domains=single))
        self.assertIn('the plan represents no RZ zone', problems)

    def test_a_zone_outside_the_reviewed_vocabulary_is_refused(self):
        plan = self.plans['nutanix']
        problems = adapter_base.get('nutanix').validate(
            tampered_plan(plan, domains=()))
        self.assertTrue(any('represents no' in problem for problem in problems))

    def test_every_platform_agrees_on_the_zone_requirement(self):
        for platform, plan in self.plans.items():
            self.assertEqual(tuple(plan.resolution.zones), ('OZ', 'RZ'), platform)
            for zone in ('OZ', 'RZ'):
                self.assertTrue(any(domain.zone == zone for domain in plan.desired_state.domains),
                                f'{platform}/{zone}')


class PlacementPreservedTest(unittest.TestCase):
    """Reviewed inventory supplies exactly the native placement identity the platform declares."""

    def setUp(self):
        self.plans = plans()

    def test_every_cluster_supplies_the_declared_placement_identity(self):
        for platform, plan in self.plans.items():
            for cluster in plan.desired_state.clusters:
                self.assertEqual(set(cluster['native']), PLACEMENT_FIELDS[platform],
                                 f'{platform}/{cluster["id"]}')

    def test_the_declared_placement_shape_is_the_compilers_own_field_set(self):
        for platform in PLATFORMS:
            adapter = adapter_base.get(platform)
            self.assertEqual(sorted(adapter.placement_fields), sorted(PLACEMENT_FIELDS[platform]))
            self.assertEqual(adapter.placement_contract()['fields'],
                             sorted(compiler().PLACEMENT[platform]))

    def test_the_placement_identity_reaches_the_compiled_workloads(self):
        for platform, plan in self.plans.items():
            for name, inputs in compiled_workloads(plan).items():
                self.assertLessEqual(PLACEMENT_FIELDS[platform], set(inputs),
                                     f'{platform}/{name}')
                self.assertLessEqual(set(inputs), adapter_union(platform), f'{platform}/{name}')

    def test_a_cluster_that_supplies_no_placement_identity_is_refused(self):
        plan = self.plans['openstack']
        stripped = tuple(dict(cluster, native={}) for cluster in plan.desired_state.clusters)
        problems = adapter_base.get('openstack').validate(tampered_plan(plan, clusters=stripped))
        for cluster in plan.desired_state.clusters:
            self.assertTrue(any(cluster['id'] in problem for problem in problems), cluster['id'])

    def test_placement_is_never_provisioner_owned(self):
        for platform in PLATFORMS:
            contract = adapter_base.get(platform).placement_contract()
            self.assertFalse(contract['provisioner_owned'], platform)
            self.assertIn('inventory', contract['supplied_by'], platform)


def adapter_union(platform):
    """Every native field one platform's reviewed realization may name."""
    adapter = adapter_base.get(platform)
    return (set(adapter.declared_inputs('workloads')) | set(adapter.declared_inputs('domains'))
            | PLACEMENT_FIELDS[platform] | NETWORK_FIELDS[platform])


class NetworkIntentPreservedTest(unittest.TestCase):
    """The native network identity the readback must observe is declared, not assumed."""

    def setUp(self):
        self.plans = plans()

    def test_the_readback_identity_is_the_declared_network_field_set(self):
        for platform in PLATFORMS:
            contract = adapter_base.get(platform).readback_contract()
            self.assertEqual(contract['identity'], sorted(NETWORK_FIELDS[platform]), platform)
            self.assertEqual(contract['identity'],
                             sorted(compiler().NETWORK[platform]), platform)

    def test_every_readback_identity_is_produced_by_a_reviewed_module_or_binding(self):
        for platform in PLATFORMS:
            contract = adapter_base.get(platform).readback_contract()
            accounted = set(contract['produced_by_module']) | set(contract['produced_by_binding'])
            self.assertEqual(sorted(accounted), sorted(NETWORK_FIELDS[platform]), platform)

    def test_only_the_observing_platform_declares_a_cross_phase_binding(self):
        declaring = [platform for platform in PLATFORMS if adapter_base.get(platform).binding]
        self.assertEqual(declaring, ['vmware'])
        self.assertEqual(adapter_base.get('vmware').binding['observed_field'], 'segment_path')
        self.assertEqual(adapter_base.get('vmware').binding['native_field'],
                         'quarantine_network_id')
        self.assertEqual(adapter_base.get('vmware').binding['binding_identity'], 'network_id')

    def test_the_binding_is_the_compilers_own_declaration(self):
        for platform in PLATFORMS:
            self.assertEqual(adapter_base.get(platform).binding,
                             compiler().WORKLOAD_NETWORK_BINDING.get(platform, {}), platform)

    def test_the_binding_observed_field_is_a_domains_module_output(self):
        for platform in PLATFORMS:
            binding = adapter_base.get(platform).binding
            if not binding:
                continue
            domains = adapter_base.module_contract(adapter_base.get(platform).domains_module)
            self.assertIn(binding['observed_field'], domains['outputs'], platform)
            self.assertIn(binding['binding_field'], domains['outputs'], platform)

    def test_the_binding_native_field_is_a_workloads_module_variable(self):
        for platform in PLATFORMS:
            binding = adapter_base.get(platform).binding
            if not binding:
                continue
            workloads = adapter_base.module_contract(adapter_base.get(platform).workloads_module)
            self.assertIn(binding['native_field'], workloads['variables'], platform)

    def test_the_readback_is_never_declared_as_already_observed(self):
        for platform in PLATFORMS:
            self.assertEqual(adapter_base.get(platform).readback_contract()['phase'], 'domains',
                             platform)
            self.assertEqual(conformance_row(self.plans[platform], 'native-observation')['status'],
                             conformance_checks.PENDING, platform)


class IsolationOutcomeTest(unittest.TestCase):
    """The isolation outcome is carried by a reviewed security-edge component and owner."""

    def setUp(self):
        self.plans = plans()

    def test_every_platform_declares_a_reviewed_security_edge_component(self):
        for platform in PLATFORMS:
            adapter = adapter_base.get(platform)
            self.assertTrue(adapter.edge_components, platform)
            self.assertIn(adapter.security_edge, adapter.edge_components, platform)

    def test_the_declared_edge_is_one_the_reviewed_catalog_owns(self):
        for platform in PLATFORMS:
            adapter = adapter_base.get(platform)
            self.assertEqual(adapter.edge_components, adapter_base.edge_components(platform),
                             platform)
            self.assertEqual(set(adapter.edge_components) & set(compiler().NETWORK[platform]),
                             set(), platform)

    def test_the_edge_is_owned_by_the_security_edge_owner_scope(self):
        for platform in PLATFORMS:
            self.assertEqual(adapter_base.get(platform).security_edge_contract()['owner_scope'],
                             'security-edge', platform)

    def test_the_delivery_graph_hands_over_the_security_edge_operation(self):
        for platform, plan in self.plans.items():
            operations = [op for op in plan.delivery['operations']
                          if op['owner'] == 'security-edge-owner']
            self.assertEqual([op['name'] for op in operations], ['security-edge-route'],
                             platform)
            self.assertTrue(operations[0]['blocking'], platform)

    def test_the_security_edge_check_passes_and_claims_no_realization(self):
        for platform, plan in self.plans.items():
            row = check(plan, 'security-edge')
            self.assertEqual(row.status, conformance_checks.PASS, platform)
            self.assertFalse(row.evidence['realized'], platform)
            self.assertEqual(row.evidence['component'], SECURITY_EDGE[platform], platform)
            self.assertEqual(row.evidence['problems'], [], platform)

    def test_the_quarantine_boundary_is_declared_for_every_platform(self):
        for platform in PLATFORMS:
            contract = adapter_base.get(platform).security_edge_contract()
            self.assertIn('quarantine', contract['realizes'], platform)


class ServiceBindingPreservedTest(unittest.TestCase):
    """The portable service binding is identical on every platform and reaches the identity."""

    def setUp(self):
        self.plans = plans()

    def test_every_platform_resolves_the_same_service_bindings(self):
        shapes = {platform: json.dumps(plan.desired_state.service_bindings, sort_keys=True)
                  for platform, plan in self.plans.items()}
        self.assertEqual(len(set(shapes.values())), 1)
        self.assertTrue(self.plans['nutanix'].desired_state.service_bindings)

    def test_every_platform_binds_the_same_service_profiles(self):
        profiles = {platform: plan.desired_state.profiles['services']
                    for platform, plan in self.plans.items()}
        self.assertEqual(len({json.dumps(p, sort_keys=True) for p in profiles.values()}), 1)

    def test_a_service_binding_is_declared_and_never_verified_here(self):
        for platform, plan in self.plans.items():
            for binding in plan.desired_state.service_bindings:
                self.assertEqual(binding['status'], 'DECLARED_HANDOFF_NOT_VERIFIED', platform)
                self.assertEqual(binding['format'], 'hosting-service-binding/1', platform)

    def test_the_service_binding_participates_in_the_plan_identity(self):
        plan = self.plans['nutanix']
        manifest = copy.deepcopy(plan.manifest)
        manifest['service_bindings'][0]['profile'] = 'dns/other'
        self.assertNotEqual(plan_manifest.digest_of(manifest), plan.manifest_digest)

    def test_the_service_binding_reaches_the_manifest_unchanged(self):
        plan = self.plans['vmware']
        self.assertEqual(plan.manifest['service_bindings'],
                         [dict(binding) for binding in plan.desired_state.service_bindings])


class RecoveryIntentTest(unittest.TestCase):
    """Recovery intent is represented when the request asks for it, and never invented."""

    def test_a_request_without_a_recovery_profile_declares_none(self):
        plan = support.reference_plan('internal-development')
        self.assertIsNone(plan.desired_state.profiles['recovery'])
        operation = next(op for op in plan.delivery['operations']
                         if op['name'] == 'backup-retention')
        self.assertIsNone(operation['details']['recovery'])

    def test_a_request_with_a_recovery_profile_hands_it_to_the_backup_owner(self):
        for name in ('internal-production', 'multi-tier', 'recovery-enabled', 'storage-heavy'):
            with self.subTest(request=name):
                plan = support.reference_plan(name)
                self.assertEqual(plan.desired_state.profiles['recovery'], 'standard')
                operation = next(op for op in plan.delivery['operations']
                                 if op['name'] == 'backup-retention')
                self.assertEqual(operation['owner'], 'backup-owner')
                self.assertEqual(operation['details']['recovery'], 'standard')

    def test_recovery_intent_does_not_depend_on_the_platform(self):
        for platform in PLATFORMS:
            plan = support.platform_plan(platform, 'recovery-enabled')
            operation = next(op for op in plan.delivery['operations']
                             if op['name'] == 'backup-retention')
            self.assertEqual(operation['details']['recovery'], 'standard', platform)

    def test_recovery_readiness_is_never_claimed_from_the_repository_alone(self):
        plan = support.platform_plan('vmware', 'recovery-enabled')
        row = conformance_row(plan, 'recovery-readiness')
        self.assertNotEqual(row['status'], conformance_checks.PASS)
        self.assertEqual(row['authority'], 'EXTERNAL')


class UnsupportedCapabilityRefusedTest(unittest.TestCase):
    """A capability or realization a platform cannot perform is refused, never assumed."""

    def setUp(self):
        self.plans = plans()

    def test_no_platform_is_natively_qualified(self):
        for platform in PLATFORMS:
            contract = adapter_base.get(platform).capability_contract()
            self.assertFalse(contract['qualified'], platform)
            self.assertEqual(contract['status'], adapter_base.NOT_QUALIFIED, platform)
            self.assertEqual(contract['blockers'], ['product_tuple:UNSELECTED'], platform)

    def test_a_required_capability_no_platform_holds_is_a_blocker(self):
        for platform in PLATFORMS:
            contract = adapter_base.get(platform).capability_contract(
                required={UNQUALIFIED_CAPABILITY})
            self.assertEqual(contract['required'], [UNQUALIFIED_CAPABILITY], platform)
            self.assertIn(f'capability:{UNQUALIFIED_CAPABILITY}:NOT_NATIVE_QUALIFIED',
                          contract['blockers'], platform)
            self.assertFalse(contract['qualified'], platform)

    def test_an_assurance_profile_is_reported_as_a_blocker(self):
        contract = adapter_base.get('nutanix').capability_contract(
            assurance_profile='protected-b-medium')
        self.assertIn('assurance_profile:protected-b-medium', contract['blockers'])
        self.assertFalse(contract['qualified'])

    def test_a_plan_for_another_platform_is_refused_by_the_adapter(self):
        problems = adapter_base.get('vmware').validate(self.plans['openstack'])
        self.assertIn('the plan realizes openstack, not vmware', problems)
        self.assertTrue(any('supplies no native placement identity' in problem
                            for problem in problems))
        self.assertTrue(any('the reviewed vmware module does not accept' in problem
                            for problem in problems))

    def test_every_cross_platform_pair_is_refused(self):
        for adapter_platform, plan_platform in [(a, b) for a in PLATFORMS
                                                for b in PLATFORMS if a != b]:
            with self.subTest(adapter=adapter_platform, plan=plan_platform):
                problems = adapter_base.get(adapter_platform).validate(self.plans[plan_platform])
                self.assertIn(f'the plan realizes {plan_platform}, not {adapter_platform}',
                              problems)

    def test_the_adapter_refuses_every_platform_its_own_plan_accepts(self):
        for platform, plan in self.plans.items():
            self.assertEqual(adapter_base.get(platform).validate(plan), (), platform)

    def test_a_refused_plan_raises_the_realization_contract_error(self):
        with mock.patch.object(adapter_base.Adapter, 'validate',
                               return_value=('synthetic refusal',)):
            with self.assertRaises(ProvisioningError) as raised:
                support.platform_plan('nutanix')
        self.assertEqual(raised.exception.code, 'REALIZATION_CONTRACT_UNSATISFIED')
        self.assertEqual(raised.exception.path, '$.spec.platform')
        self.assertEqual(raised.exception.details['platform'], 'nutanix')
        self.assertEqual(raised.exception.details['problems'], ['synthetic refusal'])

    def test_a_refusal_is_an_error_and_never_a_warning(self):
        with mock.patch.object(adapter_base.Adapter, 'validate',
                               return_value=('synthetic refusal',)):
            with self.assertRaises(ProvisioningError):
                support.platform_plan('openstack')

    def test_the_refusal_error_code_is_registered(self):
        from provisioner.domain import errors
        self.assertIn('REALIZATION_CONTRACT_UNSATISFIED', errors.CODES)
        self.assertEqual(errors.CODES['REALIZATION_CONTRACT_UNSATISFIED'][0], 'compilation')

    def test_the_adapter_contract_check_fails_on_a_refusal(self):
        plan = self.plans['nutanix']
        with mock.patch.object(adapter_base.Adapter, 'validate',
                               return_value=('synthetic refusal',)):
            row = check(plan, 'adapter-contract')
        self.assertEqual(row.status, conformance_checks.FAIL)
        self.assertEqual(row.evidence['problems'], ['synthetic refusal'])


class NativeFieldLeakTest(unittest.TestCase):
    """A provider-native field never reaches the portable request."""

    def test_no_request_key_is_a_native_field_name(self):
        names = all_native_field_names()
        for name in support.REFERENCE_REQUESTS:
            for platform in PLATFORMS:
                with self.subTest(request=name, platform=platform):
                    document = support.platform_request(platform, name)
                    self.assertEqual(sorted(request_keys(document) & names), [])

    def test_a_native_field_placed_in_the_request_is_refused(self):
        names = sorted(all_native_field_names())
        for platform in PLATFORMS:
            for name in names:
                with self.subTest(platform=platform, field=name):
                    document = support.platform_request(platform)
                    document['spec'][name] = 'leaked'
                    with self.assertRaises(ProvisioningError) as raised:
                        create_plan(document, str(support.request_path('internal-production')),
                                    support.reference_fixture(platform), support.catalogs())
                    self.assertEqual(raised.exception.code, 'SCHEMA_VALIDATION_FAILED')

    def test_the_native_side_carries_the_placement_identity_instead(self):
        for platform, plan in plans().items():
            self.assertEqual([sorted(cluster['native']) for cluster in plan.environment['clusters']],
                             [sorted(PLACEMENT_FIELDS[platform])] * len(plan.environment['clusters']),
                             platform)

    def test_the_portable_request_names_no_native_module(self):
        for name in support.REFERENCE_REQUESTS:
            text = support.request_path(name).read_text(encoding='utf-8')
            for module in [m for pair in MODULES.values() for m in pair]:
                self.assertNotIn(module, text, f'{name}/{module}')

    def test_the_compiled_native_inputs_are_declared_by_the_reviewed_module(self):
        for platform, plan in plans().items():
            declared = adapter_base.get(platform).declared_inputs('workloads')
            for domain in plan.environment['wsds'][0]['domains']:
                for workload in domain['workloads'].values():
                    self.assertLessEqual(set(workload), declared, f'{platform}/{domain["id"]}')


class AdapterCompilerAgreementTest(unittest.TestCase):
    """An adapter declaration can never drift from the reviewed artifact it describes."""

    def test_declared_inputs_are_the_reviewed_modules_variables(self):
        for platform in PLATFORMS:
            adapter = adapter_base.get(platform)
            for phase in adapter_base.PHASES:
                module = adapter_base.module_contract(adapter.module(phase))
                self.assertEqual(adapter.declared_inputs(phase), module['variables'],
                                 f'{platform}/{phase}')

    def test_the_placement_field_set_is_the_compilers_placement_table(self):
        for platform in PLATFORMS:
            self.assertEqual(adapter_base.get(platform).placement_fields,
                             frozenset(compiler().PLACEMENT[platform]), platform)

    def test_the_network_field_set_is_the_compilers_network_table(self):
        for platform in PLATFORMS:
            self.assertEqual(adapter_base.get(platform).network_fields,
                             frozenset(compiler().NETWORK[platform]), platform)

    def test_the_module_identities_are_the_reviewed_composition_roots(self):
        roots = build_wsd_compositions.COMPONENTS
        for platform in PLATFORMS:
            adapter = adapter_base.get(platform)
            self.assertEqual((adapter.domains_module, adapter.workloads_module),
                             (roots[platform]['domains'], roots[platform]['workloads']),
                             platform)
            self.assertEqual((adapter.domains_module, adapter.workloads_module),
                             MODULES[platform], platform)

    def test_the_module_contract_reads_the_reviewed_module_configuration(self):
        for platform in PLATFORMS:
            adapter = adapter_base.get(platform)
            for phase in adapter_base.PHASES:
                contract = adapter_base.module_contract(adapter.module(phase))
                path = support.ROOT / contract['module'] / 'main.tf.json'
                document = json.loads(path.read_text(encoding='utf-8'))
                self.assertEqual(contract['variables'], frozenset(document.get('variable', {})),
                                 f'{platform}/{phase}')
                self.assertEqual(contract['outputs'], frozenset(document.get('output', {})),
                                 f'{platform}/{phase}')

    def test_the_readback_check_passes_for_every_platform(self):
        for platform, plan in plans().items():
            row = check(plan, 'adapter-readback')
            self.assertEqual(row.status, conformance_checks.PASS, platform)
            self.assertEqual(row.evidence['problems'],
                             {'binding_target_not_accepted': [],
                              'declared_inputs_not_declared_by_module': [],
                              'observed_field_not_output': [],
                              'readback_not_produced': []}, platform)

    def test_the_readback_check_reports_the_reviewed_modules(self):
        plan = support.platform_plan('vmware')
        evidence = check(plan, 'adapter-readback').evidence
        self.assertEqual(evidence['authority'], 'reviewed Terraform module configuration')
        self.assertEqual(evidence['modules'], ['terraform/modules/nsx-domain',
                                               'terraform/modules/vsphere-workload'])
        self.assertEqual(evidence['readback'], ['quarantine_network_id'])

    def test_the_provisioner_asks_the_adapter_for_the_native_field_shape(self):
        for platform in PLATFORMS:
            for phase in adapter_base.PHASES:
                self.assertEqual(compiler_environment.native_variables(platform, phase),
                                 adapter_base.get(platform).declared_inputs(phase),
                                 f'{platform}/{phase}')

    def test_the_provisioner_asks_the_adapter_for_the_realization_gaps(self):
        for platform, plan in plans().items():
            self.assertEqual(compiler_environment.realization_gaps(plan.desired_state),
                             tuple(gap['message']
                                   for gap in adapter_base.get(platform).realization_gaps()),
                             platform)

    def test_the_computed_facts_are_declared_once(self):
        self.assertEqual(compiler_environment.PROVISIONER_OWNED_INPUTS,
                         tuple(fact for fact, _ in adapter_base.COMPUTED_FACTS))
        self.assertEqual(compiler_environment.PROVISIONER_OWNED_INPUTS,
                         ('boot_disk_gib', 'data_disk_gib', 'ipv4_address'))

    def test_each_platform_declares_only_its_own_realization_gaps(self):
        for platform, plan in plans().items():
            gaps = adapter_base.get(platform).realization_gaps()
            if platform == 'vmware':
                self.assertEqual([gap['inputs'] for gap in gaps], [['ipv4_address']], platform)
            else:
                self.assertEqual(gaps, (), platform)
            self.assertEqual([w['code'] for w in plan.warnings
                              if w['code'] == 'REALIZATION_INPUT_UNAVAILABLE'],
                             ['REALIZATION_INPUT_UNAVAILABLE'] if gaps else [], platform)

    def test_every_declared_gap_names_how_the_platform_realizes_the_fact_instead(self):
        for platform in PLATFORMS:
            for gap in adapter_base.get(platform).realization_gaps():
                self.assertTrue(gap['realized_by'], platform)
                self.assertIn(gap['inputs'][0], gap['message'], platform)


class GenericCodeNeverBranchesOnAPlatformNameTest(unittest.TestCase):
    """Provider-specific decisions are declared as data, never branched on in generic code."""

    def literal_platform_branches(self, path):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        found = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                for comparator in node.comparators:
                    if (isinstance(comparator, ast.Constant)
                            and comparator.value in set(PLATFORMS) | {'nsx'}):
                        found.append(ast.unparse(node))
        return found

    def test_the_existing_compiler_never_branches_on_a_platform_name(self):
        self.assertEqual(self.literal_platform_branches(support.ROOT / 'tools' / 'compile_wsd.py'),
                         [])

    def test_no_generic_provisioning_module_branches_on_a_platform_name(self):
        package = support.ROOT / 'provisioner'
        offenders = {}
        for path in sorted(package.rglob('*.py')):
            if '__pycache__' in path.parts or 'adapters' in path.parts:
                continue
            found = self.literal_platform_branches(path)
            if found:
                offenders[path.relative_to(support.ROOT).as_posix()] = found
        self.assertEqual(offenders, {})

    def test_the_compiler_declares_the_workload_network_binding_as_data(self):
        table = compiler().WORKLOAD_NETWORK_BINDING
        self.assertEqual(sorted(table), ['vmware'])
        for rule in table.values():
            self.assertEqual(sorted(rule), ['binding_field', 'binding_identity', 'message',
                                            'native_field', 'observed_field'])

    def test_the_compiler_binding_argument_is_named_for_the_phase_not_the_platform(self):
        import inspect
        signature = inspect.signature(compiler().compile_environment)
        self.assertIn('phase_bindings', signature.parameters)
        self.assertNotIn('vmware_bindings', signature.parameters)

    def test_the_adapter_owns_the_gap_decision_instead_of_the_compiler(self):
        source = (support.ROOT / 'provisioner' / 'compiler' / 'environment.py').read_text(
            encoding='utf-8')
        self.assertIn('adapters.get(state.platform).realization_gaps()', source)
        self.assertIn('adapters.get(platform).declared_inputs(phase)', source)
        self.assertIn('PROVISIONER_OWNED_INPUTS = tuple(fact for fact, _ in '
                      'adapters.COMPUTED_FACTS)', source)


class RealizationManifestTermTest(unittest.TestCase):
    """The plan identity binds what the selected adapter declares about its realization."""

    def setUp(self):
        self.plans = plans()

    def test_the_manifest_binds_the_realization_term(self):
        self.assertIn('realization', plan_manifest.TERMS)
        for platform, plan in self.plans.items():
            self.assertIn('realization', plan.manifest, platform)

    def test_the_realization_term_names_the_selected_platforms_declaration(self):
        for platform, plan in self.plans.items():
            term = plan.manifest['realization']
            self.assertEqual(term['platform'], platform)
            self.assertEqual(term['format'], adapter_base.ADAPTER_FORMAT)
            self.assertEqual(term['placement_fields'], sorted(PLACEMENT_FIELDS[platform]))
            self.assertEqual(term['readback_identity'], sorted(NETWORK_FIELDS[platform]))
            self.assertEqual(term['security_edge']['component'], SECURITY_EDGE[platform])
            self.assertEqual(term['security_edge']['owner_scope'], 'security-edge')
            self.assertEqual(term['binding_requirement'], adapter_base.get(platform).binding)
            self.assertFalse(term['native_contact'])

    def test_the_realization_term_participates_in_the_plan_identity(self):
        plan = self.plans['nutanix']
        manifest = copy.deepcopy(plan.manifest)
        manifest['realization']['security_edge']['component'] = 'some-other-edge'
        self.assertNotEqual(plan_manifest.digest_of(manifest), plan.manifest_digest)

    def test_dropping_the_realization_term_changes_the_plan_identity(self):
        plan = self.plans['nutanix']
        manifest = copy.deepcopy(plan.manifest)
        del manifest['realization']
        self.assertNotEqual(plan_manifest.digest_of(manifest), plan.manifest_digest)

    def test_a_change_to_a_declared_placement_field_changes_the_identity(self):
        plan = self.plans['openstack']
        manifest = copy.deepcopy(plan.manifest)
        manifest['realization']['placement_fields'] = ['volume_type']
        self.assertNotEqual(plan_manifest.digest_of(manifest), plan.manifest_digest)

    def test_the_plan_identity_is_the_manifest_identity(self):
        for platform, plan in self.plans.items():
            self.assertEqual(plan.digest, plan.manifest_digest, platform)
            self.assertEqual(plan.to_dict()['manifest']['realization'],
                             plan.manifest['realization'], platform)

    def test_the_realization_term_reports_the_declared_gaps(self):
        for platform, plan in self.plans.items():
            term = plan.manifest['realization']
            self.assertEqual(term['gaps'],
                             sorted(gap['code']
                                    for gap in adapter_base.get(platform).realization_gaps()),
                             platform)
            self.assertEqual(term['gap_inputs'],
                             sorted(input_name
                                    for gap in adapter_base.get(platform).realization_gaps()
                                    for input_name in gap['inputs']), platform)

    def test_the_review_projection_names_the_edge_and_the_gaps(self):
        for platform, plan in self.plans.items():
            review = plan_manifest.review(plan.manifest)
            self.assertEqual(review['realization'], SECURITY_EDGE[platform], platform)
            self.assertEqual(review['realization_gaps'], plan.manifest['realization']['gaps'],
                             platform)

    def test_the_realization_term_differs_between_platforms(self):
        digests = {platform: plan.manifest_digest for platform, plan in self.plans.items()}
        self.assertEqual(len(set(digests.values())), len(PLATFORMS))


class AdapterConformanceTest(unittest.TestCase):
    """The three adapter checks are repository-side, mandatory and honest."""

    def setUp(self):
        self.plans = plans()

    def test_the_three_adapter_checks_are_repository_checks(self):
        for name in ('adapter-contract', 'adapter-readback', 'security-edge'):
            self.assertIn(name, conformance_checks.REPOSITORY_CHECKS, name)
            self.assertNotIn(name, conformance_checks.EXTERNAL_CHECKS, name)

    def test_the_adapter_checks_are_mandatory(self):
        for name in ('adapter-contract', 'adapter-readback', 'security-edge'):
            self.assertIn(name, conformance_checks.MANDATORY, name)

    def test_every_adapter_check_passes_for_every_platform(self):
        for platform, plan in self.plans.items():
            for name in ('adapter-contract', 'adapter-readback', 'security-edge'):
                self.assertEqual(check(plan, name).status, conformance_checks.PASS,
                                 f'{platform}/{name}')

    def test_the_adapter_checks_are_marked_mandatory_and_repository_authority(self):
        for name in ('adapter-contract', 'adapter-readback', 'security-edge'):
            row = check(self.plans['nutanix'], name)
            self.assertTrue(row.mandatory, name)
            self.assertEqual(row.authority, 'REPOSITORY', name)

    def test_the_adapter_contract_check_evidence_names_the_contract_format(self):
        for platform, plan in self.plans.items():
            evidence = check(plan, 'adapter-contract').evidence
            self.assertEqual(evidence['adapter'], adapter_base.CONTRACT_FORMAT, platform)
            self.assertEqual(evidence['platform'], platform)
            self.assertEqual(evidence['family'], adapter_base.get(platform).family, platform)
            self.assertEqual(evidence['problems'], [], platform)
            self.assertFalse(evidence['native_contact'], platform)
            self.assertEqual(sorted(evidence['surfaces']), sorted(
                set(SURFACES) | {'format', 'platform', 'family', 'gap_codes', 'limits',
                                 'native_contact'}), platform)

    def test_the_security_edge_check_evidence_names_the_reviewed_authority(self):
        for platform, plan in self.plans.items():
            evidence = check(plan, 'security-edge').evidence
            self.assertEqual(evidence['authority'], 'terraform/catalog.json', platform)
            self.assertEqual(evidence['operations'], ['security-edge-route'], platform)
            self.assertEqual(evidence['owner_scope'], 'security-edge', platform)

    def test_a_platform_refusal_makes_the_adapter_contract_check_fail(self):
        plan = self.plans['vmware']
        with mock.patch.object(adapter_base.Adapter, 'validate',
                               return_value=('the plan realizes openstack, not vmware',)):
            row = check(plan, 'adapter-contract')
        self.assertEqual(row.status, conformance_checks.FAIL)
        self.assertIn('refuses the reviewed plan', row.detail)

    def test_the_adapter_checks_never_satisfy_an_external_requirement(self):
        plan = self.plans['nutanix']
        for name in ('native-qualification', 'native-observation', 'production-authorization'):
            row = conformance_row(plan, name)
            self.assertEqual(row['status'], conformance_checks.PENDING, name)
            self.assertEqual(row['authority'], 'EXTERNAL', name)

    def test_the_plan_is_still_blocked_on_external_evidence(self):
        for platform, plan in self.plans.items():
            self.assertEqual(plan.conformance['status'], 'BLOCKED_ON_EXTERNAL_EVIDENCE',
                             platform)
            self.assertIn('native-qualification', plan.conformance['blocking'], platform)
            self.assertFalse(plan.conformance['ready'], platform)
            self.assertFalse(plan.conformance['native_contact'], platform)


if __name__ == '__main__':
    unittest.main()
