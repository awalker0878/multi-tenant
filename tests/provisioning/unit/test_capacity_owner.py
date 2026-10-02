"""The capacity-owner handoff: reviewed arithmetic is a preflight, not a reservation.

The portable package decides what capacity a workload security domain needs, and it
refuses to place the WSD at all when the reviewed inventory cannot already hold the
demand. That arithmetic is a preflight. It is not a reservation, and this repository
never holds one: the authoritative capacity owner is a separate system with its own
record, and nothing here contacts it, writes to it or speaks for it.

What has to be provable here is that the repository hands the reviewed decision over
in the exact shape that owner's existing machinery accepts, that a proposal is never
represented as a confirmation, that a confirmation is bound to the exact plan
identity, generation and commissioned capacity view it was obtained against, that an
unknown, spent or conflicting authoritative outcome is refused rather than retried
into a second reservation, and that two operations cannot each be admitted against
the same stale view of the same free capacity.

`tools/capacity.py` is the owner of the request contract. Its declarations are read
from its source and compared against the mirror in `provisioner.allocations.owner` on
the same documents, so a key, a unit, a grammar or a bound the owner adds cannot
drift unnoticed.
"""
from __future__ import annotations

import ast
import json
import tempfile
import types
import unittest
from pathlib import Path

from provisioner.allocations import owner as capacity
from provisioner.allocations import reservations
from provisioner.conformance import checks as conformance_checks
from provisioner.domain import request as request_module
from provisioner.domain.errors import ProvisioningError
from provisioner.execution import manifest as manifest_module
from provisioner.execution import service
from tools import capacity as owner_module

from tests.provisioning import support

OWNER = support.ROOT / 'tools' / 'capacity.py'
RECORD_CHECKER = support.ROOT / 'provisioner' / 'allocations' / 'reservation_evidence.py'
PREFLIGHT = support.ROOT / 'scripts' / 'check_reservation_preflight.py'

#: A relative path the repository really owns, for exported-evidence references.
SOURCE_REF = 'examples/requests/internal-production.yaml'
CREATED = '2025-01-01T00:00:00Z'
OBSERVED = '2026-01-01T00:00:00Z'
EXPIRES = '2035-01-01T00:00:00Z'
AS_OF = '2031-01-01T00:00:00Z'
DIGEST = 'b' * 64
ENVELOPE = 'envelope-01'
OWNER_ID = 'capacity-owner-01'
POOL_ID = 'pool-01'

_PLANS: dict[tuple, object] = {}


def _plan(name: str = 'internal-production', platform: str | None = None,
          generation: int = 1):
    """One reviewed plan, built once per shape and never mutated by a test."""
    key = (name, platform, generation)
    if key not in _PLANS:
        _PLANS[key] = (support.reference_plan(name, generation=generation) if platform is None
                       else support.platform_plan(platform, name, generation=generation))
    return _PLANS[key]


def _cluster(plan, domain):
    """The reviewed cluster one placed domain selected."""
    site = plan.inventory.site(plan.desired_state.site_key)
    for cell in site.cells:
        if cell.cell != domain.cell_key:
            continue
        for cluster in cell.clusters:
            if cluster.id == domain.cluster_id:
                return cluster
    raise AssertionError('the placed cluster is absent from the reviewed inventory')


def _bound(plan) -> dict:
    """The identity a reservation must carry, with the envelope the operator recorded."""
    return capacity.binding(plan, envelope_id=ENVELOPE, envelope_record_sha256=DIGEST)


def _facts(**overrides) -> dict:
    document = {'owner_id': OWNER_ID, 'pool_id': POOL_ID,
                'capabilities': ['standard', 'ssd'],
                'database': str(Path(tempfile.gettempdir()) / 'capacity-owner.sqlite3'),
                'envelope_id': ENVELOPE, 'envelope_record_sha256': DIGEST}
    document.update(overrides)
    return document


def _record(plan, identity: dict | None = None, **overrides) -> dict:
    """One exported reservation record, as the authoritative owner would export it."""
    identity = _bound(plan) if identity is None else identity
    record = {
        'reservation_id': identity['reservation_id'],
        'operation_id': identity['operation_id'],
        'generation': identity['generation'],
        'state': 'HELD',
        'request_id': 'request-01',
        'wsd_engineering_ref': SOURCE_REF,
        'envelope_id': identity['envelope']['id'] or ENVELOPE,
        'envelope_record_sha256': identity['envelope']['record_sha256'] or DIGEST,
        'spec_sha256': DIGEST,
        'authoritative_system': {'system_ref': 'capacity-owner',
                                 'record_ref': 'record-01', 'record_version': 1},
        'created_at': CREATED, 'expires_at': EXPIRES, 'last_observed_at': OBSERVED,
        'owners': {'reservation_owner_role': 'capacity-owner',
                   'capacity_owner_role': 'capacity-owner',
                   'service_owner_role': 'platform-owner'},
        'resources': [{'id': 'vcpu', 'unit': 'count', 'quantity': '8',
                       'owner_role': 'capacity-owner'}],
        'dependency_handoffs': [],
        'evidence_refs': ['capacity-owner:record-01'],
        'source_refs': [SOURCE_REF],
    }
    record.update(overrides)
    return record


def _index(*records) -> dict:
    return {'format': 'portable-hosting-reservation-record-index/2',
            'status': 'EXPORTED_RESERVATION_EVIDENCE_NOT_RESERVATION_AUTHORITY',
            'reviewed_source_revision': 'a' * 40,
            'records': list(records)}


def _reconcile(plan, *records, identity: dict | None = None, as_of=AS_OF) -> dict:
    identity = _bound(plan) if identity is None else identity
    return capacity.reconcile(identity, _index(*records), as_of=as_of)


def _literal_set(node) -> set:
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
            and node.func.id == 'frozenset':
        return _literal_set(node.args[0])
    if not isinstance(node, (ast.Set, ast.Tuple, ast.List)):
        raise AssertionError(f'a literal set was expected, found {ast.dump(node)}')
    return {element.value for element in node.elts}


def _subscript_key(node) -> str | None:
    return node.slice.value if isinstance(node.slice, ast.Constant) else None


def _owner_source():
    return ast.parse(OWNER.read_text(encoding='utf-8'))


def _owner_request_keys() -> set:
    """The request key set the authoritative owner itself enforces."""
    for node in ast.walk(_owner_source()):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'exact_keys' and node.args
                and isinstance(node.args[0], ast.Name) and node.args[0].id == 'request'):
            return _literal_set(node.args[1])
    raise AssertionError('tools/capacity.py does not enforce a request key set')


def _owner_scope_keys() -> set:
    """The request scope key set the authoritative owner itself enforces."""
    for node in ast.walk(_owner_source()):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'exact_keys' and node.args
                and isinstance(node.args[0], ast.Subscript)
                and isinstance(node.args[0].value, ast.Name)
                and node.args[0].value.id == 'request'
                and _subscript_key(node.args[0]) == 'scope'):
            return _literal_set(node.args[1])
    raise AssertionError('tools/capacity.py does not enforce a request scope key set')


def _owner_request_format() -> str:
    """The request format string the authoritative owner itself requires."""
    for node in ast.walk(_owner_source()):
        if not isinstance(node, ast.Compare) or not node.comparators:
            continue
        left, right = node.left, node.comparators[0]
        if (isinstance(left, ast.Subscript) and isinstance(left.value, ast.Name)
                and left.value.id == 'request' and _subscript_key(left) == 'format'
                and isinstance(right, ast.Constant) and isinstance(right.value, str)):
            return right.value
    raise AssertionError('tools/capacity.py does not enforce a request format')


def _declared(path: Path, name: str) -> set:
    """The literal set one module declares, read from source rather than imported."""
    for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
        if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == name
                for target in node.targets):
            return _literal_set(node.value)
    raise AssertionError(f'{path.name} does not declare {name}')


def _preflight_outcomes() -> set:
    """Every outcome the repository's existing reservation preflight can report."""
    return {node.value for node in ast.walk(ast.parse(PREFLIGHT.read_text(encoding='utf-8')))
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
            and node.value.isupper() and '_' in node.value}


class DeclaredContractTest(unittest.TestCase):
    """The mirror cannot drift from the authoritative owner's own declarations."""

    def test_the_mirrored_request_keys_are_the_owner_request_keys(self):
        self.assertEqual(set(capacity.REQUEST_KEYS), _owner_request_keys())

    def test_the_mirrored_request_format_is_the_owner_request_format(self):
        self.assertEqual(capacity.REQUEST_FORMAT, _owner_request_format())

    def test_the_mirrored_scope_keys_are_the_owner_scope_keys(self):
        self.assertEqual(set(capacity.SCOPE_KEYS), _owner_scope_keys())

    def test_the_mirrored_units_are_the_owner_units(self):
        self.assertEqual(set(capacity.UNITS), _declared(OWNER, 'UNITS'))

    def test_the_mirrored_record_states_are_the_exported_checker_states(self):
        self.assertEqual(set(capacity.RECORD_STATES), _declared(RECORD_CHECKER, 'STATES'))

    def test_the_mirrored_identifier_grammar_is_the_owner_grammar(self):
        source = ast.parse((support.ROOT / 'tools' / 'readback_core.py').read_text(
            encoding='utf-8'))
        patterns = [node.value.args[0].value for node in ast.walk(source)
                    if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == 'ID'
                            for target in node.targets)
                    and isinstance(node.value, ast.Call) and node.value.args
                    and isinstance(node.value.args[0], ast.Constant)]
        self.assertEqual(patterns, [capacity.IDENTIFIER.pattern])

    def test_the_mirrored_unit_bound_is_the_owner_unit_bound(self):
        bounds = [node.comparators[1].left.value ** node.comparators[1].right.value
                  for node in ast.walk(_owner_source())
                  if isinstance(node, ast.Compare) and len(node.comparators) == 2
                  and isinstance(node.comparators[1], ast.BinOp)
                  and isinstance(node.comparators[1].op, ast.Pow)
                  and isinstance(node.comparators[1].left, ast.Constant)]
        self.assertEqual(bounds, [capacity.MAX_UNITS])

    def test_the_owner_accepts_the_request_shape_the_mirror_declares(self):
        document = capacity.request(_plan(), owner_id=OWNER_ID, pool_id=POOL_ID,
                                    capabilities=['standard'])
        self.assertIsNone(owner_module.validate_request(document))

    def test_the_handoff_request_is_accepted_by_the_owner(self):
        document = capacity.handoff(_plan(), owner_id=OWNER_ID, pool_id=POOL_ID,
                                    capabilities=['standard'])
        self.assertIsNone(owner_module.validate_request(document['request']))

    def test_the_repository_never_holds_a_reservation_of_its_own(self):
        self.assertNotEqual(capacity.REQUEST_FORMAT, reservations.RESERVATION_FORMAT)
        self.assertNotEqual(capacity.BINDING_FORMAT, reservations.RESERVATION_FORMAT)

    def test_the_declared_contract_is_reported_for_the_documentation_guard(self):
        declared = capacity.to_dict()
        self.assertEqual(declared['request_format'], capacity.REQUEST_FORMAT)
        self.assertEqual(declared['view_format'], capacity.VIEW_FORMAT)
        self.assertEqual(declared['handoff_format'], capacity.HANDOFF_FORMAT)
        self.assertEqual(declared['units'], list(capacity.UNITS))
        self.assertEqual(declared['required_facts'], list(capacity.REQUIRED_FACTS))


class MirroredValidatorTest(unittest.TestCase):
    """The mirror refuses everything the owner refuses, on the same documents."""

    def setUp(self):
        self.document = capacity.request(_plan(), owner_id=OWNER_ID, pool_id=POOL_ID,
                                         capabilities=['standard'])

    def _mutate(self, **changes) -> dict:
        document = json.loads(json.dumps(self.document))
        document.update(changes)
        return document

    def _both_refuse(self, document: dict):
        with self.assertRaises(ValueError):
            owner_module.validate_request(document)
        with self.assertRaises(ProvisioningError) as caught:
            capacity.validate_request(document)
        self.assertEqual(caught.exception.code, 'SCHEMA_VALIDATION_FAILED')
        return caught.exception

    def test_the_mirror_returns_the_document_it_accepts(self):
        self.assertIs(capacity.validate_request(self.document), self.document)

    def test_an_unknown_format_is_refused_by_both(self):
        self._both_refuse(self._mutate(format='hosting-capacity-request/2'))

    def test_a_missing_key_is_refused_by_both(self):
        document = self._mutate()
        document.pop('pool_id')
        self._both_refuse(document)

    def test_an_extra_key_is_refused_by_both(self):
        self._both_refuse(self._mutate(confirmed=True))

    def test_an_empty_reservation_is_refused_by_both(self):
        self._both_refuse(self._mutate(units={'vcpu': 0, 'memory_mb': 0, 'storage_gb': 0}))

    def test_a_negative_unit_is_refused_by_both(self):
        self._both_refuse(self._mutate(units={'vcpu': -1, 'memory_mb': 0, 'storage_gb': 0}))

    def test_a_boolean_unit_is_refused_by_both(self):
        self._both_refuse(self._mutate(units={'vcpu': True, 'memory_mb': 0, 'storage_gb': 0}))

    def test_an_unbounded_unit_is_refused_by_both(self):
        self._both_refuse(self._mutate(units={'vcpu': 10 ** 15 + 1, 'memory_mb': 0,
                                              'storage_gb': 0}))

    def test_an_unknown_unit_is_refused_by_both(self):
        self._both_refuse(self._mutate(units={'vcpu': 1, 'memory_mb': 1, 'storage_gb': 1,
                                              'gpu': 1}))

    def test_a_generation_of_zero_is_refused_by_both(self):
        self._both_refuse(self._mutate(generation=0))

    def test_a_boolean_generation_is_refused_by_both(self):
        self._both_refuse(self._mutate(generation=True))

    def test_an_empty_capability_list_is_refused_by_both(self):
        self._both_refuse(self._mutate(capabilities=[]))

    def test_a_duplicate_capability_is_refused_by_both(self):
        self._both_refuse(self._mutate(capabilities=['standard', 'standard']))

    def test_an_ambiguous_owner_identifier_is_refused_by_both(self):
        self._both_refuse(self._mutate(owner_id='capacity owner'))

    def test_a_scope_key_the_owner_does_not_declare_is_refused_by_both(self):
        scope = dict(self.document['scope'])
        scope['region_key'] = 'region-01'
        self._both_refuse(self._mutate(scope=scope))

    def test_an_ambiguous_scope_component_is_refused_by_both(self):
        scope = dict(self.document['scope'])
        scope['platform'] = 'open stack'
        self._both_refuse(self._mutate(scope=scope))

    def test_the_mirror_refuses_a_platform_this_repository_cannot_place(self):
        scope = dict(self.document['scope'])
        scope['platform'] = 'kubernetes'
        document = self._mutate(scope=scope)
        self.assertIsNone(owner_module.validate_request(document))
        with self.assertRaises(ProvisioningError) as caught:
            capacity.validate_request(document)
        self.assertEqual(caught.exception.code, 'SCHEMA_VALIDATION_FAILED')


class CompiledRequestTest(unittest.TestCase):
    """The reviewed demand compiles into the owner's request, rounded up, never up."""

    def setUp(self):
        self.plan = _plan()
        self.document = capacity.request(self.plan, owner_id=OWNER_ID, pool_id=POOL_ID,
                                         capabilities=['standard', 'ssd'])

    def test_the_request_is_bound_to_the_reviewed_operation_and_generation(self):
        self.assertEqual(self.document['operation_id'], self.plan.operation_id)
        self.assertEqual(self.document['generation'], self.plan.generation)
        self.assertEqual(self.document['scope'], self.plan.identity.scope)

    def test_the_request_scope_carries_exactly_the_declared_keys(self):
        self.assertEqual(set(self.document['scope']), set(capacity.SCOPE_KEYS))

    def test_the_reservation_identity_is_derived_from_the_operation_identity(self):
        self.assertEqual(self.document['reservation_id'],
                         f'{self.plan.operation_id}-capacity')
        self.assertTrue(capacity.IDENTIFIER.match(self.document['reservation_id']))

    def test_the_request_units_are_the_reviewed_demand(self):
        self.assertEqual(self.document['units'], capacity.units(self.plan))
        self.assertTrue(all(value > 0 for value in self.document['units'].values()))

    def test_the_request_names_the_recorded_pool_and_owner(self):
        self.assertEqual(self.document['owner_id'], OWNER_ID)
        self.assertEqual(self.document['pool_id'], POOL_ID)
        self.assertEqual(self.document['capabilities'], ['standard', 'ssd'])

    def test_memory_is_accounted_in_decimal_megabytes_rounded_up(self):
        self.assertEqual(capacity.memory_mb(1), 1074)
        self.assertEqual(capacity.memory_mb(2), 2148)
        self.assertEqual(capacity.memory_mb(0), 0)

    def test_storage_is_accounted_in_decimal_gigabytes_rounded_up(self):
        self.assertEqual(capacity.storage_gb(1), 2)
        self.assertEqual(capacity.storage_gb(4), 5)
        self.assertEqual(capacity.storage_gb(0), 0)

    def test_every_zone_rounds_each_workload_up_before_summing(self):
        workload = types.SimpleNamespace(vcpu=1, memory_gib=1, boot_disk_gib=1,
                                         data_disk_gib=0)
        domain = types.SimpleNamespace(workloads=[workload] * 4)
        measured = capacity.zone_units(domain)
        self.assertEqual(measured['vcpu'], 4)
        self.assertEqual(measured['memory_mb'], 4 * capacity.memory_mb(1))
        self.assertEqual(measured['storage_gb'], 4 * capacity.storage_gb(1))
        self.assertGreater(measured['memory_mb'], capacity.memory_mb(4))
        self.assertGreater(measured['storage_gb'], capacity.storage_gb(4))

    def test_the_operation_demand_is_the_sum_of_its_zones(self):
        expected = {unit: 0 for unit in capacity.UNITS}
        for domain in self.plan.desired_state.domains:
            for unit, value in capacity.zone_units(domain).items():
                expected[unit] += value
        self.assertEqual(capacity.units(self.plan), expected)

    def test_an_empty_reviewed_demand_is_refused(self):
        plan = types.SimpleNamespace(desired_state=types.SimpleNamespace(domains=[]),
                                     operation_id='wsd-01-g1-000000000000',
                                     generation=1, inventory=None)
        with self.assertRaises(ProvisioningError) as caught:
            capacity.request(plan, owner_id=OWNER_ID, pool_id=POOL_ID,
                             capabilities=['standard'], view={})
        self.assertEqual(caught.exception.code, 'COMPILATION_FAILED')

    def test_the_compiled_request_grants_no_authority(self):
        self.assertEqual(set(self.document), set(capacity.REQUEST_KEYS))
        self.assertNotIn('confirmed', self.document)
        self.assertNotIn('held', self.document)


class CommissionedViewTest(unittest.TestCase):
    """The view is the exact commissioned capacity the placement decision used."""

    def setUp(self):
        self.plan = _plan()
        self.view = capacity.capacity_view(self.plan)

    def test_the_view_names_the_reviewed_inventory_identity(self):
        inventory = self.plan.inventory
        self.assertEqual(self.view['inventory'], inventory.reference)
        # The read location is diagnostic provenance, not part of the identity.
        self.assertEqual(sorted(self.view['inventory']),
                         ['authoritative', 'digest', 'source', 'status'])

    def test_the_view_names_the_reviewed_site_and_platform(self):
        self.assertEqual(self.view['site'], self.plan.desired_state.site_key)
        self.assertEqual(self.view['platform'], self.plan.desired_state.platform)

    def test_the_view_carries_one_row_for_every_placed_zone(self):
        self.assertEqual(len(self.view['zones']), len(self.plan.desired_state.domains))
        for row, domain in zip(self.view['zones'], self.plan.desired_state.domains):
            self.assertEqual(row['zone'], domain.zone)
            self.assertEqual(row['cell'], domain.cell_key)
            self.assertEqual(row['cluster'], domain.cluster_id)
            self.assertEqual(set(row), set(capacity.VIEW_ZONE_KEYS))

    def test_the_view_carries_no_generation(self):
        self.assertNotIn('generation', self.view)
        self.assertNotIn('generation', capacity.VIEW_KEYS)
        self.assertEqual(set(self.view), set(capacity.VIEW_KEYS) | {'digest'})

    def test_two_generations_read_the_same_commissioned_view(self):
        self.assertEqual(capacity.view_digest(_plan(generation=2)),
                         capacity.view_digest(_plan(generation=1)))

    def test_the_view_headroom_is_rounded_down_never_up(self):
        for row, domain in zip(self.view['zones'], self.plan.desired_state.domains):
            cluster = _cluster(self.plan, domain).capacity
            self.assertEqual(row['available']['vcpu'], cluster.vcpu_available)
            self.assertLessEqual(row['available']['memory_mb'] * capacity.MEGABYTE,
                                 cluster.memory_gib_available * capacity.GIB)
            self.assertLessEqual(row['available']['storage_gb'] * capacity.GIGABYTE,
                                 cluster.storage_gib_available * capacity.GIB)

    def test_the_view_records_the_reviewed_committed_position(self):
        for row, domain in zip(self.view['zones'], self.plan.desired_state.domains):
            reservation = self.plan.desired_state.reservations[domain.zone]
            self.assertEqual(row['status'], reservation['status'])
            self.assertEqual(row['demand'], reservation['demand'])
            self.assertEqual(row['committed_after'], reservation['committed_after'])

    def test_the_view_digest_is_a_sha256_of_the_view_without_its_digest(self):
        body = {key: value for key, value in self.view.items() if key != 'digest'}
        self.assertEqual(self.view['digest'], request_module.digest(body))
        self.assertTrue(capacity.SHA256.match(self.view['digest']))

    def test_the_view_is_bound_into_the_reviewed_manifest(self):
        self.assertEqual(self.plan.manifest['capacity_view'],
                         {'digest': capacity.view_digest(self.plan)})

    def test_the_manifest_review_projects_the_view_and_its_zones(self):
        review = manifest_module.review(self.plan.manifest)
        self.assertEqual(review['capacity_view'], capacity.view_digest(self.plan))
        self.assertEqual(review['capacity_zones'], sorted(self.plan.manifest['capacity']))

    def test_a_moved_commissioned_view_moves_the_plan_identity(self):
        other = _plan(platform='vmware')
        self.assertNotEqual(capacity.view_digest(other), capacity.view_digest(self.plan))
        self.assertNotEqual(other.digest, self.plan.digest)

    def test_a_view_without_reviewed_inventory_is_refused(self):
        plan = types.SimpleNamespace(desired_state=self.plan.desired_state,
                                     inventory=None)
        with self.assertRaises(ProvisioningError) as caught:
            capacity.capacity_view(plan)
        self.assertEqual(caught.exception.code, 'INVENTORY_INCOMPLETE')

    def test_the_view_grants_no_authority(self):
        self.assertNotIn('confirmed', self.view)
        self.assertNotIn('may_allocate', self.view)
        self.assertTrue(any('external' in limit for limit in capacity.LIMITS))
        self.assertTrue(any('holds a reservation' in limit for limit in capacity.LIMITS))


class BindingTest(unittest.TestCase):
    """The identity a reservation must carry to be this plan's reservation."""

    def setUp(self):
        self.plan = _plan()
        self.identity = _bound(self.plan)

    def test_the_binding_carries_exactly_the_declared_keys(self):
        self.assertEqual(set(self.identity), set(capacity.BINDING_KEYS))

    def test_the_binding_binds_the_plan_the_view_and_the_generation(self):
        self.assertEqual(self.identity['plan_digest'], self.plan.digest)
        self.assertEqual(self.identity['view_digest'], capacity.view_digest(self.plan))
        self.assertEqual(self.identity['generation'], self.plan.generation)
        self.assertEqual(self.identity['operation_id'], self.plan.operation_id)
        self.assertEqual(self.identity['scope'], self.plan.identity.scope)

    def test_the_binding_binds_the_recorded_envelope_by_identity_and_digest(self):
        self.assertEqual(self.identity['envelope'],
                         {'id': ENVELOPE, 'record_sha256': DIGEST})

    def test_an_envelope_identity_without_its_digest_is_refused(self):
        document = dict(self.identity)
        document['envelope'] = {'id': ENVELOPE, 'record_sha256': ''}
        with self.assertRaises(ProvisioningError) as caught:
            capacity.validate_binding(document)
        self.assertEqual(caught.exception.code, 'SCHEMA_VALIDATION_FAILED')

    def test_an_envelope_digest_without_its_identity_is_refused(self):
        document = dict(self.identity)
        document['envelope'] = {'id': '', 'record_sha256': DIGEST}
        with self.assertRaises(ProvisioningError) as caught:
            capacity.validate_binding(document)
        self.assertEqual(caught.exception.code, 'SCHEMA_VALIDATION_FAILED')

    def test_a_scope_the_repository_did_not_review_is_refused(self):
        document = dict(self.identity)
        document['scope'] = {**self.identity['scope'], 'region_key': 'region-01'}
        with self.assertRaises(ProvisioningError):
            capacity.validate_binding(document)

    def test_an_unknown_platform_is_refused(self):
        document = dict(self.identity)
        document['scope'] = {**self.identity['scope'], 'platform': 'kubernetes'}
        with self.assertRaises(ProvisioningError):
            capacity.validate_binding(document)

    def test_a_binding_without_the_reviewed_plan_digest_is_refused(self):
        document = dict(self.identity)
        document['plan_digest'] = ''
        with self.assertRaises(ProvisioningError):
            capacity.validate_binding(document)

    def test_a_binding_without_the_capacity_view_is_refused(self):
        document = dict(self.identity)
        document['view_digest'] = ''
        with self.assertRaises(ProvisioningError):
            capacity.validate_binding(document)


class RecordedFactsTest(unittest.TestCase):
    """The host facts the repository cannot review are recorded, never invented."""

    def test_a_facts_document_carries_exactly_the_required_facts(self):
        document = capacity.validate_facts(_facts())
        self.assertEqual(set(document), set(capacity.REQUIRED_FACTS))

    def test_a_facts_document_never_names_a_database_inside_the_checkout(self):
        with self.assertRaises(ProvisioningError) as caught:
            capacity.validate_facts(_facts(database=str(support.ROOT / 'capacity.sqlite3')))
        self.assertEqual(caught.exception.code, 'SCHEMA_VALIDATION_FAILED')

    def test_a_facts_document_requires_a_database_outside_the_checkout(self):
        with self.assertRaises(ProvisioningError):
            capacity.validate_facts(_facts(database=''))

    def test_a_facts_document_names_duplicate_free_capabilities(self):
        with self.assertRaises(ProvisioningError):
            capacity.validate_facts(_facts(capabilities=['standard', 'standard']))
        with self.assertRaises(ProvisioningError):
            capacity.validate_facts(_facts(capabilities=[]))

    def test_a_facts_document_binds_an_envelope_by_identity_and_digest_together(self):
        with self.assertRaises(ProvisioningError):
            capacity.validate_facts(_facts(envelope_id='', envelope_record_sha256=DIGEST))
        with self.assertRaises(ProvisioningError):
            capacity.validate_facts(_facts(envelope_id=ENVELOPE, envelope_record_sha256=''))

    def test_a_facts_document_may_record_an_unbound_envelope(self):
        document = capacity.validate_facts(
            _facts(envelope_id='', envelope_record_sha256=''))
        self.assertEqual(document['envelope_id'], '')

    def test_an_ambiguous_owner_identifier_is_refused(self):
        with self.assertRaises(ProvisioningError):
            capacity.validate_facts(_facts(owner_id='capacity owner'))

    def test_recorded_facts_are_loaded_and_validated_from_disk(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'capacity-facts.json'
            path.write_text(json.dumps(_facts()), encoding='utf-8')
            self.assertEqual(capacity.load_facts(path), _facts())

    def test_an_unreadable_facts_document_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'absent.json'
            with self.assertRaises(ProvisioningError) as caught:
                capacity.load_facts(path)
            self.assertEqual(caught.exception.code, 'SCHEMA_VALIDATION_FAILED')

    def test_the_handoff_from_facts_binds_the_recorded_envelope(self):
        document = capacity.handoff_from_facts(_plan(), _facts())
        self.assertEqual(document['binding']['envelope'],
                         {'id': ENVELOPE, 'record_sha256': DIGEST})
        self.assertEqual(document['request']['owner_id'], OWNER_ID)
        self.assertEqual(document['request']['pool_id'], POOL_ID)


class HandoffTest(unittest.TestCase):
    """The handoff is a proposal, and it says so."""

    def setUp(self):
        self.plan = _plan()
        self.document = capacity.handoff(self.plan, owner_id=OWNER_ID, pool_id=POOL_ID,
                                         capabilities=['standard', 'ssd'])

    def test_the_handoff_states_the_proposal_status(self):
        self.assertEqual(self.document['status'], capacity.PROPOSED)
        self.assertNotEqual(capacity.PROPOSED, capacity.CONFIRMED)

    def test_the_handoff_never_claims_a_confirmed_reservation(self):
        self.assertNotIn('confirmed', self.document)
        self.assertNotIn('held', self.document)
        self.assertFalse(self.document['binding'].get('confirmed', False))

    def test_the_handoff_binds_the_view_the_request_and_the_identity(self):
        self.assertEqual(set(self.document),
                         {'format', 'status', 'binding', 'view', 'request', 'zones',
                          'required_facts', 'limits', 'digest'})
        self.assertEqual(self.document['view'], capacity.capacity_view(self.plan))
        self.assertEqual(self.document['binding'], capacity.binding(self.plan))
        self.assertEqual(self.document['binding']['envelope'],
                         {'id': '', 'record_sha256': ''})

    def test_the_handoff_digest_is_stable_and_content_addressed(self):
        again = capacity.handoff(self.plan, owner_id=OWNER_ID, pool_id=POOL_ID,
                                 capabilities=['standard', 'ssd'])
        self.assertEqual(again['digest'], self.document['digest'])
        body = {key: value for key, value in self.document.items() if key != 'digest'}
        self.assertEqual(self.document['digest'], request_module.digest(body))

    def test_the_handoff_names_the_facts_it_requires_from_the_operator(self):
        self.assertEqual(self.document['required_facts'], list(capacity.REQUIRED_FACTS))

    def test_the_handoff_names_the_zones_and_the_units_it_would_reserve(self):
        rows = self.document['zones']
        self.assertEqual(len(rows), len(self.plan.desired_state.domains))
        for row in rows:
            self.assertEqual(row['pool_id'], POOL_ID)
            self.assertEqual(row['operation_id'], self.plan.operation_id)
            self.assertEqual(row['view_digest'], capacity.view_digest(self.plan))
            self.assertEqual(set(row['units']), set(capacity.UNITS))

    def test_the_handoff_records_its_limits(self):
        self.assertEqual(self.document['limits'], list(capacity.LIMITS))
        self.assertTrue(self.document['limits'])

    def test_the_handoff_request_carries_the_bound_reservation_identity(self):
        self.assertEqual(self.document['request']['reservation_id'],
                         self.document['binding']['reservation_id'])


class ReconciliationTest(unittest.TestCase):
    """What the exported records actually say, and what they never say."""

    def setUp(self):
        self.plan = _plan()

    def test_a_missing_record_is_a_proposal_never_a_confirmation(self):
        document = _reconcile(self.plan)
        self.assertEqual(document['state'], capacity.PROPOSED)
        self.assertFalse(document['confirmed'])
        self.assertFalse(document['may_allocate'])
        self.assertIsNone(document['record'])

    def test_an_unbound_envelope_holds_rather_than_proposing(self):
        document = _reconcile(self.plan, identity=capacity.binding(self.plan))
        self.assertEqual(document['state'], capacity.HOLD_ENVELOPE)
        self.assertFalse(document['confirmed'])

    def test_an_unknown_state_is_never_reported(self):
        self.assertIn(_reconcile(self.plan)['state'], capacity.STATES)

    def test_a_held_record_confirms_exactly_the_bound_identity(self):
        document = _reconcile(self.plan, _record(self.plan))
        self.assertEqual(document['state'], capacity.CONFIRMED)
        self.assertTrue(document['confirmed'])
        self.assertTrue(document['may_allocate'])
        self.assertEqual(document['record']['reservation_id'],
                         document['reservation_id'])

    def test_a_record_for_another_operation_is_a_conflict(self):
        record = _record(self.plan, operation_id='wsd-01-g9-000000000000')
        self.assertEqual(_reconcile(self.plan, record)['state'], capacity.HOLD_CONFLICT)

    def test_a_record_for_another_generation_is_a_conflict(self):
        record = _record(self.plan, generation=self.plan.generation + 1)
        self.assertEqual(_reconcile(self.plan, record)['state'], capacity.HOLD_CONFLICT)

    def test_a_record_bound_to_another_envelope_is_a_conflict(self):
        record = _record(self.plan, envelope_record_sha256='c' * 64)
        self.assertEqual(_reconcile(self.plan, record)['state'], capacity.HOLD_CONFLICT)

    def test_a_record_bound_to_another_envelope_identity_is_a_conflict(self):
        record = _record(self.plan, envelope_id='envelope-02')
        self.assertEqual(_reconcile(self.plan, record)['state'], capacity.HOLD_CONFLICT)

    def test_an_uncertain_record_holds_for_discovery(self):
        record = _record(self.plan, state='UNCERTAIN')
        document = _reconcile(self.plan, record)
        self.assertEqual(document['state'], capacity.HOLD_UNCERTAIN)
        self.assertFalse(document['confirmed'])

    def test_an_uncertain_dependency_handoff_holds_for_discovery(self):
        record = _record(self.plan, dependency_handoffs=[
            {'kind': 'ipam', 'owner_role': 'ipam-owner',
             'operation_id': 'wsd-01-g1-000000000000', 'reservation_ref': None,
             'state': 'UNCERTAIN'}])
        self.assertEqual(_reconcile(self.plan, record)['state'], capacity.HOLD_UNCERTAIN)

    def test_a_released_record_requires_a_new_operation(self):
        record = _record(self.plan, state='RELEASED')
        self.assertEqual(_reconcile(self.plan, record)['state'], capacity.HOLD_TERMINAL)

    def test_an_expired_record_requires_a_new_operation(self):
        record = _record(self.plan, state='EXPIRED',
                         expires_at='2026-01-01T00:00:00Z',
                         last_observed_at='2026-06-01T00:00:00Z')
        self.assertEqual(_reconcile(self.plan, record)['state'], capacity.HOLD_TERMINAL)

    def test_a_consumed_record_is_refused(self):
        record = _record(self.plan, state='CONSUMED')
        self.assertEqual(_reconcile(self.plan, record)['state'], capacity.EXISTING_CONSUMED)

    def test_an_expired_hold_is_not_silently_reusable(self):
        record = _record(self.plan, expires_at='2030-01-01T00:00:00Z')
        with self.assertRaises(ProvisioningError) as caught:
            _reconcile(self.plan, record)
        self.assertEqual(caught.exception.code, 'SCHEMA_VALIDATION_FAILED')

    def test_an_invalid_export_is_refused(self):
        record = _record(self.plan)
        record.pop('spec_sha256')
        with self.assertRaises(ProvisioningError) as caught:
            _reconcile(self.plan, record)
        self.assertEqual(caught.exception.code, 'SCHEMA_VALIDATION_FAILED')

    def test_an_export_from_another_authority_is_refused(self):
        index = _index(_record(self.plan))
        index['status'] = 'RESERVATION_AUTHORITY'
        with self.assertRaises(ProvisioningError):
            capacity.reconcile(_bound(self.plan), index, as_of=AS_OF)

    def test_the_reconciliation_reports_the_records_it_read(self):
        document = _reconcile(self.plan, _record(self.plan))
        self.assertEqual(document['records_checked'], 1)
        self.assertEqual(document['held_records'], 1)

    def test_the_reconciliation_reports_an_empty_export_honestly(self):
        document = _reconcile(self.plan)
        self.assertEqual(document['records_checked'], 0)
        self.assertEqual(document['held_records'], 0)

    def test_the_reconciliation_never_grants_apply_or_activation(self):
        document = _reconcile(self.plan, _record(self.plan))
        self.assertFalse(document['may_apply'])
        self.assertFalse(document['may_activate'])
        self.assertEqual(document['limits'], list(capacity.LIMITS))

    def test_the_reconciliation_is_bound_to_the_plan_it_reconciled(self):
        document = _reconcile(self.plan)
        self.assertEqual(document['operation_id'], self.plan.operation_id)
        self.assertEqual(document['generation'], self.plan.generation)
        self.assertEqual(document['view_digest'], capacity.view_digest(self.plan))
        self.assertEqual(document['plan_digest'], self.plan.digest)

    def test_the_reconciliation_accepts_a_recorded_review_instant(self):
        self.assertEqual(_reconcile(self.plan, as_of=AS_OF)['as_of'],
                         '2031-01-01T00:00:00+00:00')

    def test_a_naive_review_instant_is_refused(self):
        with self.assertRaises(ProvisioningError) as caught:
            _reconcile(self.plan, as_of='2031-01-01T00:00:00')
        self.assertEqual(caught.exception.code, 'SCHEMA_VALIDATION_FAILED')

    def test_the_reconciliation_refusal_vocabulary_mirrors_the_preflight(self):
        outcomes = _preflight_outcomes()
        for state in (capacity.HOLD_CONFLICT, capacity.HOLD_UNCERTAIN,
                      capacity.HOLD_TERMINAL, capacity.EXISTING_CONSUMED):
            self.assertIn(state, capacity.STATES)
            self.assertIn(state, outcomes)

    def test_the_repository_own_holds_are_declared_and_not_borrowed(self):
        outcomes = _preflight_outcomes()
        self.assertIn('HOLD_ENVELOPE_NOT_CURRENTLY_ELIGIBLE', outcomes)
        self.assertNotIn(capacity.HOLD_ENVELOPE, outcomes)
        self.assertIn(capacity.HOLD_ENVELOPE, capacity.STATES)
        self.assertNotIn(capacity.PROPOSED, outcomes)
        self.assertNotIn(capacity.CONFIRMED, outcomes)

    def test_the_review_projection_is_the_reviewer_facing_summary(self):
        document = _reconcile(self.plan, _record(self.plan))
        review = capacity.review(document)
        self.assertEqual(review['state'], capacity.CONFIRMED)
        self.assertTrue(review['confirmed'])
        self.assertEqual(review['reservation_id'], document['reservation_id'])
        self.assertEqual(review['view_digest'], document['view_digest'])
        self.assertNotIn('record', review)


class SettlementGateTest(unittest.TestCase):
    """Nothing downstream may treat capacity as held without the owner's record."""

    def setUp(self):
        self.plan = _plan()

    def test_require_confirmed_refuses_a_proposal(self):
        with self.assertRaises(ProvisioningError) as caught:
            capacity.require_confirmed(_reconcile(self.plan))
        self.assertEqual(caught.exception.code, 'CAPACITY_RESERVATION_UNCONFIRMED')

    def test_require_confirmed_admits_the_owner_confirmation(self):
        self.assertIsNone(capacity.require_confirmed(_reconcile(self.plan, _record(self.plan))))

    def test_require_settled_admits_a_proposal(self):
        self.assertIsNone(capacity.require_settled(_reconcile(self.plan)))

    def test_require_settled_admits_the_owner_confirmation(self):
        self.assertIsNone(capacity.require_settled(_reconcile(self.plan, _record(self.plan))))

    def test_require_settled_refuses_every_refusing_state(self):
        document = _reconcile(self.plan, _record(self.plan))
        for state, code in capacity.REFUSING_STATES.items():
            self.assertIn(state, capacity.STATES)
            with self.assertRaises(ProvisioningError) as caught:
                capacity.require_settled({**document, 'state': state})
            self.assertEqual(caught.exception.code, code)

    def test_an_unresolved_outcome_is_never_retried(self):
        document = _reconcile(self.plan, _record(self.plan, state='UNCERTAIN'))
        with self.assertRaises(ProvisioningError) as caught:
            capacity.require_settled(document)
        self.assertEqual(caught.exception.code, 'CAPACITY_RESERVATION_UNRESOLVED')
        self.assertIn('Discover', caught.exception.details['instruction'])

    def test_a_conflicting_outcome_names_both_operations(self):
        record = _record(self.plan, operation_id='wsd-01-g9-000000000000')
        with self.assertRaises(ProvisioningError) as caught:
            capacity.require_settled(_reconcile(self.plan, record))
        self.assertEqual(caught.exception.code, 'CAPACITY_RESERVATION_CONFLICT')
        self.assertEqual(caught.exception.details['state'], capacity.HOLD_CONFLICT)

    def test_a_consumed_outcome_is_refused_before_any_retry(self):
        with self.assertRaises(ProvisioningError) as caught:
            capacity.require_settled(_reconcile(self.plan, _record(self.plan,
                                                                   state='CONSUMED')))
        self.assertEqual(caught.exception.code, 'CAPACITY_RESERVATION_CONFLICT')

    def test_require_current_admits_the_reviewed_view(self):
        digest = capacity.view_digest(self.plan)
        self.assertEqual(capacity.require_current(self.plan, digest), digest)

    def test_require_current_admits_an_unrecorded_view(self):
        self.assertEqual(capacity.require_current(self.plan, ''),
                         capacity.view_digest(self.plan))

    def test_require_current_refuses_a_recorded_view_that_moved(self):
        with self.assertRaises(ProvisioningError) as caught:
            capacity.require_current(self.plan, 'c' * 64)
        self.assertEqual(caught.exception.code, 'CAPACITY_SNAPSHOT_STALE')
        self.assertEqual(caught.exception.details['recorded'], 'c' * 64)
        self.assertEqual(caught.exception.details['current'],
                         capacity.view_digest(self.plan))

    def test_a_preflight_against_a_moved_view_is_refused_end_to_end(self):
        recorded = capacity.view_digest(_plan(platform='vmware'))
        with self.assertRaises(ProvisioningError) as caught:
            capacity.require_current(self.plan, recorded)
        self.assertEqual(caught.exception.code, 'CAPACITY_SNAPSHOT_STALE')


class ConcurrencyTest(unittest.TestCase):
    """Two operations may not each be admitted against the same stale view."""

    def setUp(self):
        self.plan = _plan()
        self.rows = capacity.zones(self.plan, pool_id=POOL_ID)

    def _intruder(self, **overrides) -> dict:
        row = {**self.rows[0], 'operation_id': 'wsd-99-g1-000000000000', 'zone': 'TZ'}
        row.update(overrides)
        return row

    def test_the_operation_itself_is_never_refused_against_itself(self):
        self.assertIsNone(capacity.require_exclusive(self.rows))
        self.assertIsNone(capacity.require_exclusive([*self.rows, *self.rows]))

    def test_two_operations_over_one_view_are_refused(self):
        intruder = self._intruder(units=dict(self.rows[0]['available']))
        with self.assertRaises(ProvisioningError) as caught:
            capacity.require_exclusive([*self.rows, intruder])
        self.assertEqual(caught.exception.code, 'CAPACITY_RESERVATION_CONFLICT')
        self.assertEqual(sorted(caught.exception.details['operations']),
                         ['wsd-01-g1-' + self.plan.digest[:12],
                          'wsd-99-g1-000000000000'])
        self.assertEqual(caught.exception.details['pool_id'], POOL_ID)

    def test_two_operations_that_fit_together_are_admitted(self):
        intruder = self._intruder(units={unit: 0 for unit in capacity.UNITS})
        self.assertIsNone(capacity.require_exclusive([*self.rows, intruder]))

    def test_two_pools_are_never_confused_for_one_another(self):
        intruder = self._intruder(units=dict(self.rows[0]['available']),
                                  pool_id='pool-02')
        self.assertIsNone(capacity.require_exclusive([*self.rows, intruder]))

    def test_two_views_are_never_confused_for_one_another(self):
        intruder = self._intruder(units=dict(self.rows[0]['available']),
                                  view_digest='c' * 64)
        self.assertIsNone(capacity.require_exclusive([*self.rows, intruder]))

    def test_two_clusters_are_never_confused_for_one_another(self):
        intruder = self._intruder(units=dict(self.rows[0]['available']),
                                  cluster='cluster-99')
        self.assertIsNone(capacity.require_exclusive([*self.rows, intruder]))

    def test_every_placed_zone_reserves_from_its_own_pool(self):
        for row in self.rows:
            self.assertEqual(row['pool_id'], POOL_ID)
            self.assertEqual(row['view_digest'], capacity.view_digest(self.plan))
            self.assertEqual(row['operation_id'], self.plan.operation_id)


class SharedEvidenceTest(unittest.TestCase):
    """Every transport reads capacity the same way, from the repository's evidence."""

    def setUp(self):
        self.plan = _plan()

    def test_the_evidence_reports_the_compiled_binding_and_the_view(self):
        document = service.capacity_evidence(self.plan)
        self.assertEqual(document['binding'], capacity.binding(self.plan))
        self.assertEqual(document['view'], capacity.capacity_view(self.plan))
        self.assertEqual(document['units'], capacity.units(self.plan))
        self.assertEqual(document['scope'], self.plan.identity.scope)
        self.assertEqual(document['required_facts'], list(capacity.REQUIRED_FACTS))

    def test_the_evidence_is_a_proposal_without_recorded_facts(self):
        document = service.capacity_evidence(self.plan)
        self.assertEqual(document['state'], capacity.HOLD_ENVELOPE)
        self.assertFalse(document['confirmed'])
        self.assertFalse(document['may_allocate'])
        self.assertIsNone(document['facts'])
        self.assertIsNone(document['handoff'])

    def test_the_evidence_binds_the_recorded_facts(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'capacity-facts.json'
            path.write_text(json.dumps(_facts()), encoding='utf-8')
            document = service.capacity_evidence(self.plan, facts_path=path)
            self.assertEqual(document['state'], capacity.PROPOSED)
            self.assertEqual(document['facts'], _facts())
            self.assertEqual(document['handoff']['binding']['envelope'],
                             {'id': ENVELOPE, 'record_sha256': DIGEST})

    def test_the_evidence_reads_the_exported_records_from_disk(self):
        with tempfile.TemporaryDirectory() as directory:
            facts = Path(directory) / 'capacity-facts.json'
            facts.write_text(json.dumps(_facts()), encoding='utf-8')
            index = Path(directory) / 'reservation_record_index.json'
            index.write_text(json.dumps(_index(_record(self.plan))), encoding='utf-8')
            document = service.capacity_evidence(self.plan, reservation_index=index,
                                                 facts_path=facts, as_of=AS_OF)
            self.assertEqual(document['state'], capacity.CONFIRMED)
            self.assertTrue(document['confirmed'])
            self.assertTrue(document['may_allocate'])
            self.assertEqual(document['review']['records_checked'], 1)

    def test_the_evidence_reads_the_repository_export_by_default(self):
        document = service.capacity_evidence(self.plan)
        self.assertGreaterEqual(document['reconciliation']['records_checked'], 0)

    def test_the_evidence_never_grants_authority(self):
        document = service.capacity_evidence(self.plan)
        self.assertEqual(document['limits'], list(capacity.LIMITS))
        self.assertFalse(document['reconciliation']['may_apply'])

    def _check(self, name: str, evidence: dict):
        checks = conformance_checks.run(self.plan, capacity=evidence)
        return [item for item in checks if item.name == name][0]

    def test_the_repository_capacity_check_states_intent_not_a_held_reservation(self):
        check = self._check('capacity-proposal', service.capacity_evidence(self.plan))
        self.assertEqual(check.status, 'PASS')
        self.assertEqual(check.authority, 'REPOSITORY')
        self.assertIn('the owner has not answered it', check.detail)
        self.assertEqual(check.evidence['authority'], 'REPOSITORY_CAPACITY_ARITHMETIC')
        self.assertEqual(check.evidence['state'], capacity.PROPOSED)
        self.assertEqual(check.evidence['confirmation_check'], 'capacity-confirmation')

    def test_the_confirmation_check_pends_until_the_owner_records_a_reservation(self):
        check = self._check('capacity-confirmation', service.capacity_evidence(self.plan))
        self.assertEqual(check.status, 'PENDING_EXTERNAL_EVIDENCE')
        self.assertEqual(check.authority, 'EXTERNAL')

    def test_the_confirmation_check_passes_only_on_the_owner_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            facts = Path(directory) / 'capacity-facts.json'
            facts.write_text(json.dumps(_facts()), encoding='utf-8')
            index = Path(directory) / 'reservation_record_index.json'
            index.write_text(json.dumps(_index(_record(self.plan))), encoding='utf-8')
            evidence = service.capacity_evidence(self.plan, reservation_index=index,
                                                 facts_path=facts, as_of=AS_OF)
            check = self._check('capacity-confirmation', evidence)
            self.assertEqual(check.status, 'PASS')
            self.assertEqual(check.authority, 'EXTERNAL')
            self.assertEqual(check.evidence['owner'], 'capacity-owner')
            self.assertTrue(check.evidence['confirmed'])

    def test_the_confirmation_check_fails_on_a_conflicting_reservation(self):
        with tempfile.TemporaryDirectory() as directory:
            index = Path(directory) / 'reservation_record_index.json'
            index.write_text(json.dumps(_index(_record(
                self.plan, operation_id='wsd-01-g9-000000000000'))), encoding='utf-8')
            evidence = service.capacity_evidence(self.plan, reservation_index=index,
                                                 as_of=AS_OF)
            check = self._check('capacity-confirmation', evidence)
            self.assertEqual(check.status, 'FAIL')
            self.assertEqual(check.evidence['state'], capacity.HOLD_CONFLICT)


if __name__ == '__main__':
    unittest.main()