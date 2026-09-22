"""Placement must be deterministic, auditable and fail-closed.

Native qualification is a mandatory eligibility filter. The repository's reviewed
registry currently qualifies no platform tuple, so every test that needs an
*eligible* candidate uses the repository's declared demonstration qualification
together with a non-authoritative fixture inventory; every test that exercises the
authoritative path uses the reviewed registry and therefore holds.
"""
from __future__ import annotations

import unittest

from provisioner.domain.placement import (AUTHORITATIVE, AUTHORITIES, FIXTURE, STATUSES,
                                         PlacementDecision)
from provisioner.inventory import model as inventory_model
from provisioner.inventory.capacity import Demand
from provisioner.placement import eligibility, resolver

from tests.provisioning import support

CAPABILITIES = ('ipv4', 'network_domain')
SERVICES = ('dns', 'ntp', 'identity', 'logging', 'backup')
DECLARED_SOURCE = 'declared:repository-demonstration-corpus'


def _cluster(cluster_id: str, zone: str, *, vcpu: int = 64, tenant: str = '') -> dict:
    return {'id': cluster_id, 'role': 'workload', 'zone': zone, 'trust': 'restricted',
            'service_classes': ['workload'],
            'eligible_tenants': [tenant] if tenant else [],
            'dedicated_wsd': None, 'host_ids': [f'{cluster_id}-host-01'], 'native': {},
            'capacity': {'vcpu_total': vcpu, 'vcpu_committed': 0,
                         'memory_gib_total': 512, 'memory_gib_committed': 0,
                         'storage_gib_total': 4096, 'storage_gib_committed': 0}}


def _pool(zone: str, allocations: int = 0, site: str = 'site-01') -> dict:
    rows = [{'tenant': 'other', 'wsd': 'other-wsd', 'domain': f'other-{zone}-{i}',
             'cidr': f'198.51.100.{i}/27'} for i in range(allocations)]
    return {'pool': f'pool-{site}-{zone.lower()}', 'site': site, 'zone': zone,
            'cidr': '198.51.100.0/24', 'prefix_length': 27, 'gateway_host_number': 1,
            'allocations': rows}


def inventory_document(*, status: str, zones=('OZ', 'RZ'), allocations: int = 0,
                       services=SERVICES, vcpu: int = 64, platform: str = 'openstack') -> dict:
    return {'format': inventory_model.INVENTORY_FORMAT, 'status': status,
            'source': 'placement-test',
            'sites': [{'site': 'site-01', 'region': 'region-01', 'platform': platform,
                       'defaults': {},
                       'cells': [{'cell': 'cell-01', 'capabilities': list(CAPABILITIES),
                                  'clusters': [_cluster(f'cluster-{z.lower()}-01', z, vcpu=vcpu)
                                               for z in zones]}]}],
            'prefix_pools': [_pool(z, allocations) for z in zones],
            'services': [{'service': name, 'binding_class': 'default', 'site': 'site-01',
                          'endpoints': {}} for name in services]}


def two_platform_document(*, status: str) -> dict:
    """One region offering the same shape on openstack and on nutanix."""
    document = inventory_document(status=status, zones=('OZ',))
    document['sites'].append({
        'site': 'site-02', 'region': 'region-01', 'platform': 'nutanix', 'defaults': {},
        'cells': [{'cell': 'cell-01', 'capabilities': list(CAPABILITIES),
                   'clusters': [_cluster('cluster-oz-01', 'OZ')]}]})
    document['prefix_pools'].append(_pool('OZ', site='site-02'))
    document['services'].extend(
        {'service': name, 'binding_class': 'default', 'site': 'site-02', 'endpoints': {}}
        for name in SERVICES)
    return document


def authoritative(**kwargs) -> inventory_model.Inventory:
    return inventory_model.build(inventory_document(status=inventory_model.AUTHORITATIVE, **kwargs))


def demonstration(**kwargs) -> inventory_model.Inventory:
    """A non-authoritative fixture, planned against the declared qualification."""
    return inventory_model.build(inventory_document(status=inventory_model.FIXTURE, **kwargs))


def declared(*, platforms=eligibility.PLATFORMS, capabilities=CAPABILITIES,
             source='declared:placement-test') -> eligibility.DeclaredQualification:
    return eligibility.DeclaredQualification(
        source=source, capability_ids=tuple(capabilities),
        platforms={platform: 'DECLARED-TEST-TUPLE' for platform in platforms})


def request(*, zones=('OZ',), required=CAPABILITIES, services=SERVICES,
            platform: str = 'openstack', site_pin: str | None = None,
            cell_pin: str | None = None, demand: Demand | None = None,
            trust: str = 'restricted', service_class: str = 'workload') -> resolver.PlacementRequest:
    return resolver.PlacementRequest(
        tenant='tenant-01', wsd='wsd-01', region='region-01',
        platform_preference=platform, zones=tuple(zones), trust=trust,
        service_class=service_class, required_capabilities=tuple(required),
        demand=demand or Demand(vcpu=8, memory_gib=32, storage_gib=100),
        services={name: True for name in services}, request_digest='a' * 64,
        site_pin=site_pin, cell_pin=cell_pin)


class QualifiedRepository(eligibility.RepositoryQualification):
    """Injected authoritative qualification: every reviewed platform is qualified.

    This is controlled test data, not a registry edit: it proves the authoritative
    path can place and authorize when qualification really is present, without
    inventing qualification in the reviewed registry.
    """

    def gate(self, platform, required, assurance_profile=None):
        if platform not in eligibility.PLATFORMS:
            raise ValueError(f'Unknown platform: {platform}')
        return True, ()

    def product_tuple(self, platform):
        return f'CONTROLLED-TUPLE-{platform.upper()}'


def qualified_source() -> QualifiedRepository:
    return QualifiedRepository(source='injected-qualified-registry',
                               status='CONTROLLED_TEST_QUALIFICATION')


class QualificationGateTest(unittest.TestCase):
    """Native qualification is mandatory, never a note on an eligible candidate."""

    def test_an_injected_qualified_registry_places_and_authorizes(self):
        source = qualified_source()
        decision = resolver.place(request(), authoritative(), source)
        self.assertEqual(decision.status, 'PLACED')
        self.assertTrue(decision.authorized)
        self.assertEqual(decision.qualification_blockers, ())
        self.assertEqual(decision.qualification['source'], 'injected-qualified-registry')
        self.assertTrue(decision.qualification['authoritative'])
        self.assertEqual(decision.qualification['product_tuples'],
                         {'openstack': 'CONTROLLED-TUPLE-OPENSTACK'})
        for candidate in decision.candidates:
            self.assertTrue(candidate.eligible)
            self.assertEqual(candidate.blocker_classes, ())
            self.assertEqual(candidate.product_tuple, 'CONTROLLED-TUPLE-OPENSTACK')

    def test_an_authoritative_inventory_never_places_on_an_unqualified_platform(self):
        decision = resolver.place(request(), authoritative())
        self.assertEqual(decision.status, 'HOLD_PLATFORM_NOT_QUALIFIED')
        self.assertTrue(decision.held)
        self.assertFalse(decision.authorized)
        self.assertIsNone(decision.selected)
        self.assertTrue(decision.qualification_blockers)
        self.assertTrue(any('product_tuple:UNSELECTED' in b
                            for b in decision.qualification_blockers))
        self.assertTrue(all(b.startswith('openstack: ') for b in decision.qualification_blockers))
        self.assertTrue(all(b.startswith('openstack: capability:')
                            or b.startswith('openstack: product_tuple:')
                            for b in decision.qualification_blockers))
        self.assertTrue(decision.candidates)
        for candidate in decision.candidates:
            self.assertFalse(candidate.eligible)
            self.assertEqual(candidate.blocker_classes, ('qualification',))
            self.assertTrue(any('not natively qualified' in b for b in candidate.blockers))

    def test_the_default_qualification_source_is_the_reviewed_registry(self):
        decision = resolver.place(request(), authoritative())
        self.assertEqual(decision.qualification['source'], eligibility.REPOSITORY_SOURCE)
        self.assertEqual(decision.qualification['status'], eligibility.REPOSITORY_STATUS)
        self.assertTrue(decision.qualification['authoritative'])
        self.assertEqual(decision.qualification['product_tuples'], {'openstack': 'UNSELECTED'})

    def test_the_reviewed_registry_still_records_no_qualified_tuple(self):
        for platform in eligibility.PLATFORMS:
            self.assertEqual(eligibility.product_tuple(platform), 'UNSELECTED', platform)
            ok, blockers = eligibility.gate(platform, set(CAPABILITIES))
            self.assertFalse(ok, platform)
            self.assertTrue(blockers, platform)

    def test_a_declared_qualification_is_recorded_and_never_authorizes(self):
        source = eligibility.demonstration()
        decision = resolver.place(request(), demonstration())
        self.assertEqual(decision.status, 'PLACED')
        self.assertEqual(decision.qualification['source'], DECLARED_SOURCE)
        self.assertEqual(decision.qualification['status'], eligibility.DECLARED_STATUS)
        self.assertFalse(decision.qualification['authoritative'])
        self.assertFalse(decision.authorized)
        self.assertEqual(decision.qualification['product_tuples'],
                         {'openstack': source.product_tuple('openstack')})
        self.assertTrue(all(candidate.product_tuple == source.product_tuple(candidate.platform)
                            for candidate in decision.candidates))
        self.assertTrue(any('cannot authorize anything' in reason for reason in decision.reasons))

    def test_a_declared_qualification_cannot_plan_an_authoritative_inventory(self):
        with self.assertRaises(ValueError):
            resolver.place(request(), authoritative(), eligibility.demonstration())

    def test_a_platform_outside_the_declaration_holds(self):
        decision = resolver.place(request(), demonstration(), declared(platforms=('nutanix',)))
        self.assertEqual(decision.status, 'HOLD_PLATFORM_NOT_QUALIFIED')
        self.assertEqual(decision.qualification_blockers,
                         ('openstack: platform:openstack:NOT_DECLARED',))
        self.assertEqual([c.product_tuple for c in decision.candidates], ['UNSELECTED'])
        self.assertTrue(all(not c.eligible for c in decision.candidates))

    def test_a_declared_qualification_missing_a_capability_holds(self):
        decision = resolver.place(request(), demonstration(), declared(capabilities=('ipv4',)))
        self.assertEqual(decision.status, 'HOLD_PLATFORM_NOT_QUALIFIED')
        self.assertEqual(decision.candidates[0].qualification_blockers,
                         ('capability:network_domain:DECLARED_NOT_NATIVE_QUALIFICATION',))

    def test_platform_auto_skips_an_unqualified_platform(self):
        inventory = inventory_model.build(two_platform_document(status=inventory_model.FIXTURE))
        decision = resolver.place(request(platform='auto'), inventory,
                                  declared(platforms=('nutanix',)))
        self.assertEqual(decision.status, 'PLACED')
        self.assertEqual(decision.platform, 'nutanix')
        self.assertEqual(decision.site_key, 'site-02')
        self.assertEqual(sorted({c.eligible for c in decision.candidates}), [False, True])

    def test_platform_auto_holds_when_no_candidate_platform_is_qualified(self):
        inventory = inventory_model.build(two_platform_document(status=inventory_model.FIXTURE))
        decision = resolver.place(request(platform='auto'), inventory,
                                  declared(platforms=('vmware',)))
        self.assertEqual(decision.status, 'HOLD_PLATFORM_NOT_QUALIFIED')
        self.assertEqual(sorted(c.platform for c in decision.candidates),
                         ['nutanix', 'openstack'])
        self.assertTrue(all(not c.eligible for c in decision.candidates))

    def test_a_cell_capability_gap_stays_distinguishable_from_qualification(self):
        decision = resolver.place(request(required=CAPABILITIES + ('audit_logging',)),
                                  demonstration())
        self.assertEqual(decision.status, 'HOLD_CAPABILITY_NOT_QUALIFIED')
        self.assertEqual(decision.candidates[0].cell_blockers, ('audit_logging',))
        self.assertEqual(decision.candidates[0].qualification_blockers, ())
        self.assertEqual(decision.candidates[0].blocker_classes, ('capability',))
        self.assertEqual(decision.qualification_blockers, ())

    def test_both_gaps_are_recorded_but_the_specific_hold_wins(self):
        decision = resolver.place(request(required=CAPABILITIES + ('audit_logging',)),
                                  authoritative())
        self.assertEqual(decision.status, 'HOLD_CAPABILITY_NOT_QUALIFIED')
        self.assertEqual(decision.candidates[0].blocker_classes, ('capability', 'qualification'))
        self.assertEqual(decision.candidates[0].cell_blockers, ('audit_logging',))
        self.assertTrue(decision.candidates[0].qualification_blockers)

    def test_the_declared_document_is_not_native_evidence(self):
        document = eligibility.declaration()
        self.assertEqual(document['format'], eligibility.DECLARATION_FORMAT)
        self.assertEqual(document['status'], eligibility.DECLARED_STATUS)
        self.assertIn('not native qualification', document['boundary'])
        self.assertTrue(set(document['capability_ids']) <= set(eligibility.capabilities()))
        self.assertTrue(set(document['platforms']) <= set(eligibility.PLATFORMS))
        for platform, entry in document['platforms'].items():
            self.assertIn('NOT-NATIVE-EVIDENCE', entry['product_tuple'], platform)
        self.assertFalse(eligibility.demonstration().authoritative)


class CandidateEvaluationTest(unittest.TestCase):
    def test_a_qualified_platform_places(self):
        decision = resolver.place(request(), demonstration())
        self.assertEqual(decision.status, 'PLACED')
        self.assertEqual(decision.authority, FIXTURE)
        self.assertFalse(decision.held)
        self.assertEqual(decision.site_key, 'site-01')
        self.assertEqual(decision.cell_key, 'cell-01')
        self.assertEqual(decision.clusters, {'OZ': 'cluster-oz-01'})

    def test_selection_rule_is_recorded(self):
        decision = resolver.place(request(), demonstration())
        self.assertEqual(decision.selection_rule, resolver.SELECTION_RULE)

    def test_every_candidate_is_evaluated_and_sorted(self):
        decision = resolver.place(request(zones=('OZ', 'RZ')), demonstration())
        keys = [(c.site_key, c.cell_key, c.zone, c.platform) for c in decision.candidates]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual({c.zone for c in decision.candidates}, {'OZ', 'RZ'})

    def test_selection_prefers_larger_available_vcpu(self):
        document = inventory_document(status=inventory_model.FIXTURE, zones=('OZ',))
        document['sites'][0]['cells'][0]['clusters'] = [
            _cluster('cluster-a', 'OZ', vcpu=8), _cluster('cluster-b', 'OZ', vcpu=64)]
        inventory = inventory_model.build(document)
        decision = resolver.place(request(), inventory)
        self.assertEqual(decision.clusters['OZ'], 'cluster-b')


class FailClosedTest(unittest.TestCase):
    def test_fixture_inventory_is_never_placement_authority(self):
        inventory = demonstration()
        decision = resolver.place(request(), inventory)
        self.assertEqual(decision.authority, FIXTURE)
        self.assertFalse(inventory.authoritative)
        self.assertFalse(decision.authorized)
        self.assertTrue(any('non-authoritative fixture' in r for r in decision.reasons))

    def test_unqualified_platforms_are_recorded_without_fabricating_qualification(self):
        decision = resolver.place(request(), authoritative())
        self.assertTrue(decision.qualification_blockers)
        self.assertTrue(any('product_tuple:UNSELECTED' in b
                            for b in decision.qualification_blockers))
        self.assertEqual(decision.qualification['product_tuples'], {'openstack': 'UNSELECTED'})
        profiles = eligibility.registry()['profiles']
        for platform in eligibility.PLATFORMS:
            profile = profiles[eligibility.PLATFORM_FAMILY[platform]]
            self.assertEqual(profile['product_tuple'], 'UNSELECTED')
            self.assertTrue(all(claim['qualification'] == 'NOT_QUALIFIED'
                                for claim in profile['capabilities'].values()))
            self.assertTrue(all(not claim['native_evidence_refs']
                                for claim in profile['capabilities'].values()))

    def test_unknown_platform_is_refused(self):
        with self.assertRaises(ValueError):
            eligibility.gate('hyper-v', set(CAPABILITIES))

    def test_missing_zone_holds_with_reasons(self):
        decision = resolver.place(request(zones=('OZ', 'RZ')), demonstration(zones=('OZ',)))
        self.assertEqual(decision.status, 'HOLD_NO_ELIGIBLE_SITE')
        self.assertTrue(decision.held)
        self.assertTrue(any(r.startswith('RZ: no reviewed candidate') for r in decision.reasons))

    def test_insufficient_capacity_is_a_recorded_blocker(self):
        decision = resolver.place(
            request(demand=Demand(vcpu=1000, memory_gib=1000, storage_gib=1000)),
            authoritative())
        self.assertEqual(decision.status, 'HOLD_CAPACITY_INSUFFICIENT')
        self.assertTrue(any('vcpu: required 1000' in r for r in decision.reasons))

    def test_missing_service_binding_is_a_recorded_blocker(self):
        decision = resolver.place(request(), authoritative(services=('dns',)))
        self.assertEqual(decision.status, 'HOLD_SERVICE_UNAVAILABLE')
        self.assertTrue(any('site lacks service bindings' in r for r in decision.reasons))

    def test_exhausted_prefix_pool_is_a_recorded_blocker(self):
        decision = resolver.place(request(), authoritative(zones=('OZ',), allocations=8))
        self.assertEqual(decision.status, 'HOLD_PREFIX_POOL_EXHAUSTED')
        self.assertTrue(any('can issue a /27' in r for r in decision.reasons))

    def test_missing_cell_capability_is_a_recorded_blocker(self):
        decision = resolver.place(request(required=CAPABILITIES + ('audit_logging',)),
                                  authoritative())
        self.assertEqual(decision.status, 'HOLD_CAPABILITY_NOT_QUALIFIED')
        self.assertTrue(any('cell lacks capabilities' in r for r in decision.reasons))

    def test_unknown_capability_requirement_is_refused(self):
        with self.assertRaises(ValueError):
            resolver.place(request(required=CAPABILITIES + ('quantum_edge',)), authoritative())

    def test_residency_mismatch_is_a_recorded_blocker(self):
        decision = resolver.place(request(service_class='data'), authoritative())
        self.assertEqual(decision.status, 'HOLD_NO_ELIGIBLE_PLATFORM')
        self.assertTrue(any('residency does not match' in r for r in decision.reasons))

    def test_pins_that_match_nothing_hold(self):
        decision = resolver.place(request(site_pin='site-99'), authoritative())
        self.assertEqual(decision.status, 'HOLD_NO_ELIGIBLE_SITE')
        self.assertTrue(any('matching pins' in r for r in decision.reasons))

    def test_require_placed_raises_on_a_hold(self):
        decision = resolver.place(request(zones=('OZ', 'RZ')), demonstration(zones=('OZ',)))
        self.assertTrue(decision.held)
        from provisioner.domain.errors import ProvisioningError
        with self.assertRaises(ProvisioningError) as raised:
            resolver.require_placed(decision)
        self.assertEqual(raised.exception.code, 'NO_ELIGIBLE_PLACEMENT')


class VocabularyTest(unittest.TestCase):
    """No status may be declared unless the resolver can actually emit it."""

    def _emitted_statuses(self) -> set:
        reviewed = authoritative()
        return {
            resolver.place(request(), reviewed).status,
            resolver.place(request(), demonstration()).status,
            resolver.place(request(zones=('OZ', 'RZ')), demonstration(zones=('OZ',))).status,
            resolver.place(request(site_pin='site-99'), reviewed).status,
            resolver.place(request(demand=Demand(vcpu=1000, memory_gib=1000,
                                                 storage_gib=1000)), reviewed).status,
            resolver.place(request(required=CAPABILITIES + ('audit_logging',)),
                           reviewed).status,
            resolver.place(request(), authoritative(services=('dns',))).status,
            resolver.place(request(), authoritative(zones=('OZ',), allocations=8)).status,
            resolver.place(request(service_class='data'), reviewed).status,
        }

    def test_every_declared_status_is_emitted(self):
        self.assertEqual(self._emitted_statuses(), set(STATUSES))

    def test_the_decision_schema_matches_the_model_vocabulary(self):
        from provisioner.schemas import registry
        schema = registry.load_schema('placement-decision')['properties']
        self.assertEqual(set(schema['status']['enum']), set(STATUSES))
        self.assertEqual(set(schema['authority']['enum']), set(AUTHORITIES))


class ReferencePlacementTest(unittest.TestCase):
    def test_reference_request_places_on_the_fixture_as_a_demonstration(self):
        plan = support.reference_plan()
        self.assertEqual(plan.decision.status, 'PLACED')
        self.assertEqual(plan.decision.authority, FIXTURE)
        self.assertFalse(plan.decision.authorized)

    def test_decision_serialises_without_secrets(self):
        plan = support.reference_plan()
        payload = plan.decision.to_dict()
        self.assertEqual(payload['format'], 'hosting-placement-decision/1')
        self.assertIsInstance(payload['candidates'], list)
        self.assertEqual(payload['digest'], plan.decision.digest)
        self.assertEqual(payload['required_capabilities'],
                         list(plan.decision.required_capabilities))


if __name__ == '__main__':
    unittest.main()