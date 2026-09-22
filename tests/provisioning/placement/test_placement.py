"""Placement must be deterministic, auditable and fail-closed."""
from __future__ import annotations

import unittest

from provisioner.domain.placement import AUTHORITATIVE, FIXTURE, PlacementDecision
from provisioner.inventory import model as inventory_model
from provisioner.inventory.capacity import Demand
from provisioner.placement import eligibility, resolver

from tests.provisioning import support

CAPABILITIES = ('ipv4', 'network_domain')
SERVICES = ('dns', 'ntp', 'identity', 'logging', 'backup')


def _cluster(cluster_id: str, zone: str, *, vcpu: int = 64, tenant: str = '') -> dict:
    return {'id': cluster_id, 'role': 'workload', 'zone': zone, 'trust': 'restricted',
            'service_classes': ['workload'],
            'eligible_tenants': [tenant] if tenant else [],
            'dedicated_wsd': None, 'host_ids': [f'{cluster_id}-host-01'], 'native': {},
            'capacity': {'vcpu_total': vcpu, 'vcpu_committed': 0,
                         'memory_gib_total': 512, 'memory_gib_committed': 0,
                         'storage_gib_total': 4096, 'storage_gib_committed': 0}}


def _pool(zone: str, allocations: int = 0) -> dict:
    rows = [{'tenant': 'other', 'wsd': 'other-wsd', 'domain': f'other-{zone}-{i}',
             'cidr': f'198.51.100.{i}/27'} for i in range(allocations)]
    return {'pool': f'pool-{zone.lower()}', 'site': 'site-01', 'zone': zone,
            'cidr': '198.51.100.0/24', 'prefix_length': 27, 'gateway_host_number': 1,
            'allocations': rows}


def inventory_document(*, status: str, zones=('OZ', 'RZ'), allocations: int = 0,
                       services=SERVICES, vcpu: int = 64) -> dict:
    return {'format': inventory_model.INVENTORY_FORMAT, 'status': status,
            'source': 'placement-test',
            'sites': [{'site': 'site-01', 'region': 'region-01', 'platform': 'openstack',
                       'defaults': {},
                       'cells': [{'cell': 'cell-01', 'capabilities': list(CAPABILITIES),
                                  'clusters': [_cluster(f'cluster-{z.lower()}-01', z, vcpu=vcpu)
                                               for z in zones]}]}],
            'prefix_pools': [_pool(z, allocations) for z in zones],
            'services': [{'service': name, 'binding_class': 'default', 'site': 'site-01',
                          'endpoints': {}} for name in services]}


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


class CandidateEvaluationTest(unittest.TestCase):
    def test_authoritative_inventory_places(self):
        inventory = inventory_model.build(inventory_document(status=inventory_model.AUTHORITATIVE))
        decision = resolver.place(request(), inventory)
        self.assertEqual(decision.status, 'PLACED')
        self.assertEqual(decision.authority, AUTHORITATIVE)
        self.assertFalse(decision.held)
        self.assertEqual(decision.site_key, 'site-01')
        self.assertEqual(decision.cell_key, 'cell-01')
        self.assertEqual(decision.clusters, {'OZ': 'cluster-oz-01'})

    def test_selection_rule_is_recorded(self):
        inventory = inventory_model.build(inventory_document(status=inventory_model.AUTHORITATIVE))
        decision = resolver.place(request(), inventory)
        self.assertEqual(decision.selection_rule, resolver.SELECTION_RULE)

    def test_every_candidate_is_evaluated_and_sorted(self):
        inventory = inventory_model.build(inventory_document(status=inventory_model.AUTHORITATIVE))
        decision = resolver.place(request(zones=('OZ', 'RZ')), inventory)
        keys = [(c.site_key, c.cell_key, c.zone, c.platform) for c in decision.candidates]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual({c.zone for c in decision.candidates}, {'OZ', 'RZ'})

    def test_selection_prefers_larger_available_vcpu(self):
        document = inventory_document(status=inventory_model.AUTHORITATIVE, zones=('OZ',))
        document['sites'][0]['cells'][0]['clusters'] = [
            _cluster('cluster-a', 'OZ', vcpu=8), _cluster('cluster-b', 'OZ', vcpu=64)]
        inventory = inventory_model.build(document)
        decision = resolver.place(request(), inventory)
        self.assertEqual(decision.clusters['OZ'], 'cluster-b')


class FailClosedTest(unittest.TestCase):
    def test_fixture_inventory_is_never_placement_authority(self):
        inventory = inventory_model.build(inventory_document(status=inventory_model.FIXTURE))
        decision = resolver.place(request(), inventory)
        self.assertEqual(decision.authority, FIXTURE)
        self.assertFalse(inventory.authoritative)
        self.assertTrue(any('non-authoritative fixture' in r for r in decision.reasons))

    def test_registry_blockers_are_recorded_without_fabricating_qualification(self):
        inventory = inventory_model.build(inventory_document(status=inventory_model.AUTHORITATIVE))
        decision = resolver.place(request(), inventory)
        self.assertTrue(decision.registry_blockers)
        self.assertTrue(any('product_tuple:UNSELECTED' in b for b in decision.registry_blockers))

    def test_registry_gate_reports_unqualified_for_every_platform(self):
        for platform in eligibility.PLATFORMS:
            ok, blockers = eligibility.gate(platform, set(CAPABILITIES))
            self.assertFalse(ok, platform)
            self.assertTrue(blockers, platform)

    def test_unknown_platform_is_refused(self):
        with self.assertRaises(ValueError):
            eligibility.gate('hyper-v', set(CAPABILITIES))

    def test_missing_zone_holds_with_reasons(self):
        document = inventory_document(status=inventory_model.AUTHORITATIVE, zones=('OZ',))
        inventory = inventory_model.build(document)
        decision = resolver.place(request(zones=('OZ', 'RZ')), inventory)
        self.assertEqual(decision.status, 'HOLD_NO_ELIGIBLE_PLATFORM')
        self.assertTrue(decision.held)
        self.assertTrue(any(r.startswith('RZ: no reviewed candidate') for r in decision.reasons))

    def test_insufficient_capacity_is_a_recorded_blocker(self):
        inventory = inventory_model.build(inventory_document(status=inventory_model.AUTHORITATIVE))
        decision = resolver.place(
            request(demand=Demand(vcpu=1000, memory_gib=1000, storage_gib=1000)), inventory)
        self.assertEqual(decision.status, 'HOLD_NO_ELIGIBLE_PLATFORM')
        self.assertTrue(any('vcpu: required 1000' in r for r in decision.reasons))

    def test_missing_service_binding_is_a_recorded_blocker(self):
        inventory = inventory_model.build(
            inventory_document(status=inventory_model.AUTHORITATIVE, services=('dns',)))
        decision = resolver.place(request(), inventory)
        self.assertEqual(decision.status, 'HOLD_NO_ELIGIBLE_PLATFORM')
        self.assertTrue(any('site lacks service bindings' in r for r in decision.reasons))

    def test_exhausted_prefix_pool_is_a_recorded_blocker(self):
        inventory = inventory_model.build(
            inventory_document(status=inventory_model.AUTHORITATIVE, zones=('OZ',),
                               allocations=8))
        decision = resolver.place(request(), inventory)
        self.assertEqual(decision.status, 'HOLD_NO_ELIGIBLE_PLATFORM')
        self.assertTrue(any('can issue a /27' in r for r in decision.reasons))

    def test_missing_cell_capability_is_a_recorded_blocker(self):
        inventory = inventory_model.build(inventory_document(status=inventory_model.AUTHORITATIVE))
        decision = resolver.place(request(required=CAPABILITIES + ('audit_logging',)), inventory)
        self.assertEqual(decision.status, 'HOLD_NO_ELIGIBLE_PLATFORM')
        self.assertTrue(any('cell lacks capabilities' in r for r in decision.reasons))

    def test_unknown_capability_requirement_is_refused(self):
        inventory = inventory_model.build(inventory_document(status=inventory_model.AUTHORITATIVE))
        with self.assertRaises(ValueError):
            resolver.place(request(required=CAPABILITIES + ('quantum_edge',)), inventory)

    def test_residency_mismatch_is_a_recorded_blocker(self):
        inventory = inventory_model.build(inventory_document(status=inventory_model.AUTHORITATIVE))
        decision = resolver.place(request(service_class='data'), inventory)
        self.assertEqual(decision.status, 'HOLD_NO_ELIGIBLE_PLATFORM')
        self.assertTrue(any('residency does not match' in r for r in decision.reasons))

    def test_pins_that_match_nothing_hold(self):
        inventory = inventory_model.build(inventory_document(status=inventory_model.AUTHORITATIVE))
        decision = resolver.place(request(site_pin='site-99'), inventory)
        self.assertEqual(decision.status, 'HOLD_NO_ELIGIBLE_PLATFORM')
        self.assertTrue(any('matching pins' in r for r in decision.reasons))

    def test_require_placed_raises_on_a_hold(self):
        inventory = inventory_model.build(
            inventory_document(status=inventory_model.AUTHORITATIVE, zones=('OZ',)))
        decision = resolver.place(request(zones=('OZ', 'RZ')), inventory)
        self.assertTrue(decision.held)
        from provisioner.domain.errors import ProvisioningError
        with self.assertRaises(ProvisioningError) as raised:
            resolver.require_placed(decision)
        self.assertEqual(raised.exception.code, 'NO_ELIGIBLE_PLACEMENT')


class ReferencePlacementTest(unittest.TestCase):
    def test_reference_request_places_on_the_fixture_as_a_demonstration(self):
        plan = support.reference_plan()
        self.assertEqual(plan.decision.status, 'PLACED')
        self.assertEqual(plan.decision.authority, FIXTURE)

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