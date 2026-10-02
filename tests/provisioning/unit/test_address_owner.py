"""The address-owner handoff: a planning prefix is intent, not ownership.

The portable package decides which prefixes a workload security domain needs and
where its names belong. That decision is a proposal. It is not ownership: the
authoritative IPAM and DNS systems are separate owners with their own records, and
nothing here contacts them, allocates an address, registers a name or speaks for
either of them.

What has to be provable here is that the repository hands the reviewed addressing
over in the exact shape those owners' existing machinery accepts, that a planning
prefix is never represented as a held allocation, that an authoritative allocation
is bound to the exact plan identity, generation, parent capacity reservation,
selected site, zone, pool and allocation intent digest it was obtained against, that
a confirmed allocation may differ from the proposal without changing the approved
plan, that a mismatch, an unknown reply or a lost reply becomes a reconciliation
hold rather than a second allocation, that a name is never registered before the
allocation it depends on is confirmed, and that reusable addressing is never handed
back before the dependent DNS withdrawal has completed.

`scripts/check_ipam_allocation_preflight.py` and
`scripts/check_dns_registration_preflight.py` own the intent contracts, and
`scripts/check_ipam_allocation_records.py` and
`scripts/check_dns_registration_records.py` own the exported-evidence contracts.
Their declarations are read from source and compared against the mirror in
`provisioner.allocations.addresses` on the same documents, so a key, a state, a
grammar or a bound an owner adds cannot drift unnoticed.
"""
from __future__ import annotations

import ast
import hashlib
import json
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from provisioner import repository
from provisioner.allocations import addresses as address_owner
from provisioner.conformance import checks as conformance_checks
from provisioner.conformance import report as conformance_report
from provisioner.domain.errors import ProvisioningError
from provisioner.execution import manifest as manifest_module
from provisioner.execution import service

from tests.provisioning import support

IPAM_PREFLIGHT = support.ROOT / 'scripts' / 'check_ipam_allocation_preflight.py'
DNS_PREFLIGHT = support.ROOT / 'scripts' / 'check_dns_registration_preflight.py'
IPAM_RECORDS = support.ROOT / 'scripts' / 'check_ipam_allocation_records.py'
DNS_RECORDS = support.ROOT / 'scripts' / 'check_dns_registration_records.py'
RESERVATION_PREFLIGHT = support.ROOT / 'scripts' / 'check_reservation_preflight.py'
RESERVATION_RECORDS = support.ROOT / 'provisioner' / 'allocations' / 'reservation_evidence.py'

#: The exported record key sets the two owners declare, filtered from the compiled
#: documents. A compiled intent carries more than an exported record does.
RESERVATION_RECORD_KEYS = frozenset({
    'created_at', 'request_id', 'expires_at', 'wsd_engineering_ref', 'operation_id',
    'evidence_refs', 'last_observed_at', 'owners', 'dependency_handoffs',
    'authoritative_system', 'generation', 'source_refs', 'reservation_id', 'state',
    'resources', 'envelope_record_sha256', 'envelope_id', 'spec_sha256'})
IPAM_RECORD_KEYS = frozenset({
    'family', 'intent_sha256', 'allocation_kind', 'cleanup', 'allocation_ref',
    'created_at', 'request_id', 'requested_prefix_length', 'released_at',
    'wsd_engineering_ref', 'delegated_scope_ref', 'evidence_refs', 'realization_ref',
    'operation_id', 'allocation_policy', 'last_observed_at', 'confirmed_at', 'owners',
    'release_requested_at', 'reuse_not_before', 'authoritative_system', 'source_refs',
    'allocation_id', 'generation', 'state', 'reservation_id', 'hold_expires_at',
    'overlap_exception_ref'})
DNS_RECORD_KEYS = frozenset({
    'intent_sha256', 'registration_id', 'ttl_profile_ref', 'required_observations',
    'created_at', 'request_id', 'forward_zone_ref', 'registered_at', 'released_at',
    'wsd_engineering_ref', 'name_assignment_ref', 'evidence_refs', 'tombstone_until',
    'operation_id', 'last_observed_at', 'owners', 'record_types', 'release_requested_at',
    'authoritative_system', 'source_refs', 'observations', 'generation', 'state',
    'ipam_confirmation_sha256', 'reservation_id', 'ipam_allocation_id',
    'reverse_zone_ref'})

#: A fixed review instant. The system clock is never consulted: an owner reply is
#: reconciled against the instant the reviewed operation was handed over at.
AS_OF = datetime(2026, 9, 18, 18, 0, tzinfo=timezone.utc)
CREATED = AS_OF - timedelta(hours=1)
ENVELOPE = hashlib.sha256(b'c07-envelope').hexdigest()
OTHER_DIGEST = hashlib.sha256(b'other').hexdigest()
RESERVATION_INDEX_NAME = 'reservation_record_index.json'
IPAM_INDEX_NAME = 'ipam_allocation_index.json'
DNS_INDEX_NAME = 'dns_registration_index.json'

_PLANS: dict[tuple, object] = {}
_STATE: dict = {}
_SAVED: dict[Path, bytes | None] = {}
_WORK: tempfile.TemporaryDirectory | None = None
_WRITTEN = [0]


def _plan(name: str = 'internal-production', platform: str | None = None,
          generation: int = 1):
    """One reviewed plan, built once per shape and never mutated by a test."""
    key = (name, platform, generation)
    if key not in _PLANS:
        _PLANS[key] = (support.reference_plan(name, generation=generation) if platform is None
                       else support.platform_plan(platform, name, generation=generation))
    return _PLANS[key]


def _stage() -> None:
    """Compile the reviewed addressing chain and stage it as the operator handover does.

    The owners' own preflights resolve the declared sibling documents from the
    checkout, so the chain is compiled once and staged under the declared staging
    root exactly as an operator would hand it over. Whatever was there before is
    restored when the module is torn down.
    """
    if _STATE:
        return
    global _WORK
    _WORK = tempfile.TemporaryDirectory(prefix='c07-addresses-')
    plan = _plan()
    capacity = address_owner.capacity_request(plan)
    reservation = address_owner.reservation_intent(plan, capacity, as_of=AS_OF)
    for ref, document in ((address_owner.CAPACITY_REQUEST_REF, capacity),
                          (address_owner.RESERVATION_INTENT_REF, reservation)):
        path = support.ROOT / ref
        path.parent.mkdir(parents=True, exist_ok=True)
        _SAVED[path] = path.read_bytes() if path.is_file() else None
        path.write_text(json.dumps(document, indent=2, sort_keys=True), encoding='utf-8')
    _STATE.update(capacity=capacity, reservation=reservation,
                  reservation_spec=repository.reservation_intent_spec(
                      reservation, capacity, as_of=AS_OF,
                      envelope_record_sha256=ENVELOPE))


def setUpModule():
    _stage()


def tearDownModule():
    """Remove the staged chain, restoring anything the checkout already held."""
    for path, original in _SAVED.items():
        if original is None:
            if path.is_file():
                path.unlink()
        else:
            path.write_bytes(original)
    staged = support.ROOT / address_owner.STAGING_ROOT
    if staged.is_dir() and not any(staged.iterdir()):
        staged.rmdir()
    _SAVED.clear()
    if _WORK is not None:
        _WORK.cleanup()


def _capacity() -> dict:
    _stage()
    return _STATE['capacity']


def _reservation() -> dict:
    _stage()
    return _STATE['reservation']


def _reservation_spec() -> dict:
    _stage()
    return _STATE['reservation_spec']


def _domains(plan=None) -> tuple[dict, ...]:
    return address_owner.domains(_plan() if plan is None else plan)


def _zones() -> tuple[str, ...]:
    return tuple(domain['zone'] for domain in _domains())


def _domain(zone: str, plan=None) -> dict:
    for domain in _domains(plan):
        if domain['zone'] == zone:
            return domain
    raise AssertionError(f'the reviewed plan has no zone {zone!r}')


def only(document: dict, keys) -> dict:
    """The exported record a compiled document would become, filtered to its keys."""
    return {key: value for key, value in document.items() if key in keys}


def _system(kind: str) -> dict:
    return {'system_ref': f'owner-system:{kind}', 'record_ref': f'{kind}-record:1',
            'record_version': 1}


def _cleanup(status: str = 'NOT_STARTED') -> dict:
    started = status != 'NOT_STARTED'
    return {key: {'status': status,
                  'evidence_ref': f'evidence:cleanup-{key}' if started else None,
                  'observed_at': AS_OF.isoformat() if started else None}
            for key in sorted(('routes', 'dhcp_leases', 'dns', 'policy',
                               'logging_attribution', 'incident_response'))}


def _parent_record(state: str = 'HELD', *, tamper: bool = False) -> dict:
    """One exported reservation record, as the capacity owner would export it."""
    return {
        **only(_reservation_spec(), RESERVATION_RECORD_KEYS),
        'spec_sha256': OTHER_DIGEST if tamper else repository.canonical_record_digest(
            _reservation_spec()),
        'authoritative_system': _system('reservation'),
        'created_at': CREATED.isoformat(),
        'last_observed_at': AS_OF.isoformat(),
        'dependency_handoffs': [{**only(item, {'kind', 'owner_role', 'operation_id',
                                              'reservation_ref', 'state'}),
                                 'reservation_ref': None, 'state': 'NOT_STARTED'}
                                for item in _reservation_spec()['dependency_handoffs']],
        'evidence_refs': ['evidence:reservation-hold'],
        'source_refs': [address_owner.CAPACITY_REQUEST_REF],
        'state': state,
    }


def _allocation_spec(zone: str, plan=None) -> dict:
    intent = address_owner.allocation_intent(plan or _plan(), _domain(zone, plan), as_of=AS_OF)
    return repository.ipam_allocation_spec(intent, as_of=AS_OF,
                                           parent_envelope_record_sha256=ENVELOPE)


def _allocation_record(zone: str, state: str = 'RESERVED', *, tamper: bool = False,
                       lifecycle: bool = False, plan=None) -> dict:
    """One exported allocation record, as the IPAM owner would export it.

    The exported record deliberately carries no allocated prefix or address value:
    the authoritative IPAM owner is the only source of an allocation value, and the
    repository's contract for reading that evidence has no field to put one in.
    """
    plan = plan or _plan()
    domain = _domain(zone, plan)
    intent = address_owner.allocation_intent(plan, domain, as_of=AS_OF)
    spec = _allocation_spec(zone, plan)
    confirmed = state in ('CONFIRMED', 'RELEASE_PENDING', 'QUARANTINED', 'RELEASED')
    reusable = state in ('QUARANTINED', 'RELEASED')
    return {
        **only(spec, IPAM_RECORD_KEYS),
        'intent_sha256': OTHER_DIGEST if tamper else address_owner.allocation_intent_digest(
            intent, parent_reservation_spec_sha256=spec['parent_reservation_spec_sha256'],
            hold_expires_at=spec['hold_expires_at']),
        'authoritative_system': _system('ipam'),
        'allocation_ref': f'ipam-allocation:{spec["allocation_id"]}',
        'created_at': CREATED.isoformat(),
        'last_observed_at': AS_OF.isoformat(),
        'hold_expires_at': spec['hold_expires_at'] if state in ('RESERVED', 'UNCERTAIN') else None,
        'confirmed_at': CREATED.isoformat() if confirmed else None,
        'realization_ref': 'ipam-realization:1' if confirmed else None,
        'release_requested_at': AS_OF.isoformat() if reusable or state == 'RELEASE_PENDING' else None,
        'cleanup': _cleanup('COMPLETE' if lifecycle and reusable else 'NOT_STARTED'),
        'reuse_not_before': AS_OF.isoformat() if lifecycle and reusable else None,
        'released_at': AS_OF.isoformat() if state == 'RELEASED' else None,
        'evidence_refs': ['evidence:ipam-readback'],
        'source_refs': [address_owner.RESERVATION_INTENT_REF],
        'state': state,
    }


def _confirmation(zone: str, plan=None) -> str:
    """The confirmation digest the exported allocation record carries."""
    index = _index('ipam', [_allocation_record(zone, 'CONFIRMED', plan=plan)])
    summary = repository.validate_ipam_allocation_records(index, as_of=AS_OF)
    return summary['records'][0]['confirmation_sha256']


def _dns_record(zone: str, state: str = 'REGISTERED', plan=None) -> dict:
    """One exported registration record, as the DNS owner would export it."""
    plan = plan or _plan()
    domain = _domain(zone, plan)
    intent = address_owner.registration_intent(plan, domain, as_of=AS_OF)
    spec = intent['spec']
    confirmation = _confirmation(zone, plan)
    release_requested = CREATED if state == 'RELEASED' else AS_OF
    tombstone_until = CREATED if state == 'RELEASED' else AS_OF
    return {
        **only(spec, DNS_RECORD_KEYS),
        'intent_sha256': address_owner.registration_intent_digest(
            intent, ipam_confirmation_sha256=confirmation, valid_until=spec['valid_until']),
        'ipam_confirmation_sha256': confirmation,
        'authoritative_system': _system('dns'),
        'created_at': CREATED.isoformat(),
        'last_observed_at': AS_OF.isoformat(),
        'registered_at': CREATED.isoformat(),
        'release_requested_at': release_requested.isoformat()
                                if state in ('RELEASE_PENDING', 'TOMBSTONED', 'RELEASED') else None,
        'tombstone_until': tombstone_until.isoformat()
                           if state in ('TOMBSTONED', 'RELEASED') else None,
        'released_at': AS_OF.isoformat() if state == 'RELEASED' else None,
        'observations': {
            'AUTHORITATIVE': {'status': 'COMPLETE', 'evidence_ref': 'evidence:dns-readback',
                              'observed_at': AS_OF.isoformat()},
            'RECURSIVE': {'status': 'PENDING', 'evidence_ref': None, 'observed_at': None},
            'SECONDARY': {'status': 'NOT_APPLICABLE', 'evidence_ref': 'evidence:dns-secondary',
                          'observed_at': AS_OF.isoformat()}},
        'evidence_refs': ['evidence:dns-readback'],
        'source_refs': intent['source_refs'],
        'state': state,
    }


def _index(kind: str, records) -> dict:
    """One exported owner index, cloned from the repository's own reviewed export."""
    names = {'reservation': RESERVATION_INDEX_NAME, 'ipam': IPAM_INDEX_NAME,
             'dns': DNS_INDEX_NAME}
    document = json.loads((support.ROOT / 'sources' / 'capabilities'
                           / names[kind]).read_text(encoding='utf-8'))
    document['records'] = list(records)
    return document


def _write(document: dict) -> Path:
    """One exported index on disk, so reconciliation reads it the way a transport does."""
    _WRITTEN[0] += 1
    path = Path(_WORK.name) / f'index-{_WRITTEN[0]}.json'
    path.write_text(json.dumps(document, indent=2, sort_keys=True), encoding='utf-8')
    return path


def _reconcile(plan=None, *, parent: str | None = 'HELD', parent_tamper: bool = False,
               zones=None, allocation_states=None, registration_states=None,
               allocation_tamper: bool = False, lifecycle: bool = False,
               as_of=AS_OF) -> dict:
    """Reconcile the reviewed plan against the exported owner evidence described here.

    `zones` selects which zones get an exported allocation record; every zone of the
    reviewed plan is always classified. `parent=None` exports no reservation record at
    all, which is the only way the owner's evidence says the hold is absent.
    """
    plan = plan or _plan()
    zones = _zones() if zones is None else tuple(zones)
    allocation_states = allocation_states or {}
    registration_states = registration_states or {}
    reservations = [] if parent is None else [_parent_record(parent, tamper=parent_tamper)]
    reservation = _write(_index('reservation', reservations))
    allocations = [_allocation_record(zone, allocation_states.get(zone, 'RESERVED'),
                                      tamper=allocation_tamper, lifecycle=lifecycle, plan=plan)
                   for zone in zones]
    registrations = [_dns_record(zone, registration_states[zone], plan=plan)
                     for zone in zones if zone in registration_states]
    return address_owner.reconcile(
        plan,
        reservation_index=reservation,
        allocation_index=_write(_index('ipam', allocations)) if allocations else None,
        registration_index=_write(_index('dns', registrations)) if registrations else None,
        as_of=as_of)


def _confirmed(*zones, plan=None) -> dict:
    plan = plan or _plan()
    zones = _zones() if not zones else tuple(zones)
    return _reconcile(plan, zones=zones,
                      allocation_states={zone: 'CONFIRMED' for zone in zones})


def _refusal(action, *args, **kwargs) -> ProvisioningError:
    """The refusal one settlement gate raises, or an assertion that it did not."""
    with unittest.TestCase().assertRaises(ProvisioningError) as caught:
        action(*args, **kwargs)
    return caught.exception


def _literal_set(node) -> set:
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
            and node.func.id == 'frozenset':
        return _literal_set(node.args[0])
    if not isinstance(node, (ast.Set, ast.Tuple, ast.List)):
        raise AssertionError(f'a literal set was expected, found {ast.dump(node)}')
    return {element.value for element in node.elts}


def _declared(path: Path, name: str) -> set:
    """The literal set one module declares, read from source rather than imported."""
    for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
        if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == name
                for target in node.targets):
            return _literal_set(node.value)
    raise AssertionError(f'{path.name} does not declare {name}')


def _outcomes(path: Path) -> set:
    """Every state-looking literal one owner module declares."""
    return {node.value for node in ast.walk(ast.parse(path.read_text(encoding='utf-8')))
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
            and node.value.isupper() and '_' in node.value}


class DeclaredContractTest(unittest.TestCase):
    """The mirror cannot drift from the owners' own declarations."""

    def test_the_mirrored_formats_are_the_declared_formats(self):
        declared = address_owner.to_dict()
        self.assertEqual(declared['view_format'], address_owner.VIEW_FORMAT)
        self.assertEqual(declared['binding_format'], address_owner.BINDING_FORMAT)
        self.assertEqual(declared['handoff_format'], address_owner.HANDOFF_FORMAT)
        self.assertEqual(declared['reconciliation_format'],
                         address_owner.RECONCILIATION_FORMAT)
        self.assertEqual(declared['registration_binding_format'],
                         address_owner.REGISTRATION_BINDING_FORMAT)
        for name in ('view_format', 'binding_format', 'handoff_format',
                     'reconciliation_format', 'registration_binding_format'):
            self.assertRegex(declared[name], r'^hosting-[a-z-]+/[12]$')

    def test_the_proposal_authority_is_declared_and_is_never_ownership(self):
        self.assertEqual(address_owner.PROPOSAL_AUTHORITY,
                         'PLANNING_PROPOSAL_NOT_AUTHORITATIVE_ALLOCATION')
        self.assertEqual(address_owner.to_dict()['proposal_authority'],
                         address_owner.PROPOSAL_AUTHORITY)
        self.assertEqual(address_owner.address_view(_plan())['authority'],
                         address_owner.PROPOSAL_AUTHORITY)
        for domain in _domains():
            intent = address_owner.allocation_intent(_plan(), domain, as_of=AS_OF)
            self.assertEqual(intent['production_authority'], 'NOT_ASSESSED')
        self.assertTrue(any('proposal' in line for line in address_owner.LIMITS))
        self.assertTrue(any('No actual address' in line for line in address_owner.LIMITS))

    def test_the_mirrored_scope_keys_are_the_reviewed_scope_keys(self):
        self.assertEqual(set(address_owner.SCOPE_KEYS), set(_plan().identity.scope))
        self.assertEqual(address_owner.scope_of(_plan()), _plan().identity.scope)

    def test_the_mirrored_allocation_states_are_the_owner_declared_states(self):
        declared = set(repository.declared_contracts()['allocation_intent']['statuses'])
        self.assertEqual(set(address_owner.ALLOCATION_STATES), declared)
        self.assertTrue(set(address_owner.ALLOCATION_STATES) <= _outcomes(IPAM_PREFLIGHT))

    def test_the_mirrored_registration_states_are_the_owner_declared_states(self):
        declared = set(repository.declared_contracts()['registration_intent']['statuses'])
        self.assertEqual(set(address_owner.REGISTRATION_STATES), declared)
        self.assertTrue(set(address_owner.REGISTRATION_STATES) <= _outcomes(DNS_PREFLIGHT))

    def test_the_mirrored_allocation_vocabulary_is_the_ipam_record_vocabulary(self):
        self.assertEqual(address_owner.ALLOCATION_POLICY, 'UNIQUE_DEFAULT')
        self.assertIn(address_owner.ALLOCATION_POLICY, _declared(IPAM_RECORDS, 'POLICIES'))
        self.assertIn('PREFIX', _declared(IPAM_RECORDS, 'KINDS'))
        self.assertIn('ADDRESS', _declared(IPAM_RECORDS, 'KINDS'))
        self.assertIn('IPV4', _declared(IPAM_RECORDS, 'FAMILIES'))
        self.assertIn('IPV6', _declared(IPAM_RECORDS, 'FAMILIES'))
        self.assertIn('QUARANTINED', address_owner.REUSABLE_RECORD_STATES)
        self.assertTrue(address_owner.REUSABLE_RECORD_STATES
                        <= _declared(IPAM_RECORDS, 'STATES'))
        self.assertEqual(_declared(IPAM_RECORDS, 'CLEANUP_STATES'),
                         {'NOT_STARTED', 'PENDING', 'COMPLETE', 'NOT_APPLICABLE'})
        self.assertEqual(len(_declared(IPAM_RECORDS, 'CLEANUP_KEYS')), 6)
        self.assertEqual(_declared(IPAM_RECORDS, 'CLEANUP_ITEM_KEYS'),
                         {'status', 'evidence_ref', 'observed_at'})

    def test_the_mirrored_registration_vocabulary_is_the_dns_record_vocabulary(self):
        self.assertEqual(set(address_owner.FORWARD_RECORD_TYPE.values()), {'A', 'AAAA'})
        self.assertEqual(address_owner.REVERSE_RECORD_TYPE, 'PTR')
        self.assertTrue(set(address_owner.FORWARD_RECORD_TYPE.values())
                        | {address_owner.REVERSE_RECORD_TYPE}
                        <= _declared(DNS_RECORDS, 'RECORD_TYPES'))
        self.assertTrue(set(address_owner.REQUIRED_OBSERVATIONS)
                        <= _declared(DNS_RECORDS, 'OBSERVATIONS'))
        self.assertEqual(_declared(DNS_RECORDS, 'OBS_KEYS'),
                         {'status', 'evidence_ref', 'observed_at'})
        self.assertTrue(address_owner.LIVE_REGISTRATION_STATES
                        <= _declared(DNS_RECORDS, 'STATES'))
        self.assertEqual(address_owner.QUARANTINED_REGISTRATION_STATES,
                         frozenset({'TOMBSTONED', 'RELEASED'}))
        self.assertEqual(address_owner.WITHDRAWN_REGISTRATION_STATES, frozenset({'RELEASED'}))

    def test_the_mirrored_owner_roles_cover_every_declared_owner_role(self):
        contracts = repository.declared_contracts()
        for kind in ('reservation_intent', 'allocation_intent', 'registration_intent'):
            self.assertTrue(set(contracts[kind]['owner_keys'])
                            <= set(address_owner.OWNER_ROLES), kind)
        self.assertEqual(len(set(address_owner.OWNER_ROLES.values())),
                         len(address_owner.OWNER_ROLES))

    def test_the_mirrored_demand_units_are_the_capacity_request_units(self):
        demands = {demand['id']: demand['unit'] for demand in _capacity()['capacity_demands']}
        self.assertEqual(dict(address_owner.DEMAND_UNITS), demands)
        self.assertEqual(set(address_owner.DEMAND_UNITS),
                         set(address_owner.to_dict()['demand_units']))

    def test_the_mirrored_allocation_kind_is_the_reviewed_prefix_kind(self):
        self.assertIn('PREFIX', _declared(IPAM_RECORDS, 'KINDS'))
        for domain in _domains():
            self.assertEqual(domain['allocation_kind'], 'PREFIX')
            spec = address_owner.allocation_intent(_plan(), domain, as_of=AS_OF)['spec']
            self.assertEqual(spec['allocation_kind'], 'PREFIX')
            self.assertEqual(spec['allocation_policy'], address_owner.ALLOCATION_POLICY)

    def test_the_mirrored_record_contracts_have_no_field_for_an_allocated_value(self):
        for keys in (IPAM_RECORD_KEYS, DNS_RECORD_KEYS):
            self.assertEqual(keys & {'prefix', 'address', 'value', 'allocation_value',
                                     'prefix_value', 'actual_value', 'dns_name'}, set())
        for name in ('allocation_id', 'allocation_ref', 'delegated_scope_ref',
                     'realization_ref'):
            self.assertIn(name, IPAM_RECORD_KEYS)
        for name in ('registration_id', 'name_assignment_ref', 'forward_zone_ref',
                     'reverse_zone_ref'):
            self.assertIn(name, DNS_RECORD_KEYS)

    def test_the_reconciliation_refusal_vocabulary_mirrors_the_ipam_preflight(self):
        outcomes = _outcomes(IPAM_PREFLIGHT)
        for state, code in address_owner.REFUSING_STATES.items():
            self.assertIn(state, address_owner.ALLOCATION_STATES)
            self.assertIn(state, outcomes)
            self.assertTrue(code.startswith('IPAM_'))
        self.assertIn('IPAM_ALLOCATION_CONFLICT', address_owner.REFUSAL_CONFLICT)
        self.assertIn('IPAM_ALLOCATION_UNRESOLVED', address_owner.REFUSAL_UNRESOLVED)

    def test_the_reconciliation_refusal_vocabulary_mirrors_the_dns_preflight(self):
        outcomes = _outcomes(DNS_PREFLIGHT)
        for state, code in address_owner.REGISTRATION_REFUSING_STATES.items():
            self.assertIn(state, address_owner.REGISTRATION_STATES)
            self.assertIn(state, outcomes)
            self.assertTrue(code.startswith('DNS_'))
        self.assertIn('DNS_REGISTRATION_CONFLICT',
                      address_owner.REGISTRATION_REFUSAL_CONFLICT)
        self.assertIn('DNS_REGISTRATION_UNRESOLVED',
                      address_owner.REGISTRATION_REFUSAL_UNRESOLVED)

    def test_the_repository_own_summary_vocabulary_is_not_borrowed_from_an_owner(self):
        outcomes = _outcomes(IPAM_PREFLIGHT) | _outcomes(DNS_PREFLIGHT)
        for summary in ('CONFIRMED', 'REFUSED', 'PENDING_OWNER'):
            self.assertNotIn(summary, outcomes)
        for document in (_reconcile(), _confirmed()):
            self.assertIn(document['state'], {'CONFIRMED', 'REFUSED', 'PENDING_OWNER'})
        self.assertIn('CONFIRMED', [item['record_state'] for item in
                                    _confirmed()['allocations']])
        self.assertNotIn('CONFIRMED', address_owner.ALLOCATION_STATES)

    def test_the_release_ordering_refusal_is_declared(self):
        self.assertEqual(address_owner.REFUSAL_RELEASE_ORDER,
                         'ADDRESS_RELEASE_ORDER_VIOLATION')
        self.assertIn(address_owner.REFUSAL_RELEASE_ORDER,
                      address_owner.to_dict()['refusal_codes'])

    def test_the_limits_are_declared_and_carried_by_every_document(self):
        self.assertEqual(len(address_owner.LIMITS), 5)
        self.assertEqual(list(address_owner.to_dict()['limits']), list(address_owner.LIMITS))
        self.assertEqual(address_owner.address_view(_plan())['limits'],
                         list(address_owner.LIMITS))
        self.assertEqual(_reconcile()['limits'], list(address_owner.LIMITS))

    def test_the_staging_root_is_the_declared_staging_root(self):
        self.assertEqual(address_owner.STAGING_ROOT, 'runtime/address-handoff')
        self.assertEqual(address_owner.CAPACITY_REQUEST_REF,
                         'runtime/address-handoff/site-service-capacity-request.json')
        self.assertEqual(address_owner.RESERVATION_INTENT_REF,
                         'runtime/address-handoff/reservation-intent.json')
        self.assertEqual(address_owner.to_dict()['hold_horizon_seconds'],
                         int(address_owner.HOLD_HORIZON.total_seconds()))


class CompiledIntentTest(unittest.TestCase):
    """The compiled chain is the owners' own contract, not a second model."""

    def setUp(self):
        self.plan = _plan()
        self.capacity = _capacity()
        self.reservation = _reservation()
        self.domains = _domains()

    def test_the_capacity_request_is_the_owner_demand_contract(self):
        self.assertEqual(set(self.capacity),
                         set(repository.declared_contracts()['capacity_request']['keys']))
        repository.capacity_request_shape(self.capacity)

    def test_the_capacity_request_names_every_reviewed_demand(self):
        demands = {demand['id']: demand['quantity'] for demand in self.capacity['capacity_demands']}
        self.assertEqual(set(demands), set(address_owner.DEMAND_UNITS))
        for demand in self.capacity['capacity_demands']:
            self.assertIn(demand['unit'], set(address_owner.DEMAND_UNITS.values()))

    def test_the_reservation_intent_is_the_declared_shape(self):
        declared = repository.declared_contracts()['reservation_intent']
        self.assertEqual(set(self.reservation), set(declared['keys']))
        self.assertEqual(set(self.reservation['spec']), set(declared['spec_keys']))
        self.assertEqual(self.reservation['status'], declared['status'])

    def test_the_reservation_intent_binds_the_chain_operation_identities(self):
        spec = self.reservation['spec']
        self.assertEqual(spec['reservation_id'], address_owner.reservation_id_for(self.plan))
        self.assertEqual(spec['request_id'], self.capacity['request_id'])
        self.assertEqual(spec['generation'], self.plan.generation)
        self.assertEqual(spec['envelope_id'], f'{self.plan.operation_id}-envelope')
        self.assertEqual({item['operation_id'] for item in spec['dependency_handoffs']},
                         {address_owner.allocation_operation_id_for(self.plan, domain['zone'])
                          for domain in self.domains})

    def test_the_reservation_intent_resources_are_the_reviewed_demands(self):
        resources = {item['id']: (item['unit'], item['quantity'])
                     for item in self.reservation['spec']['resources']}
        self.assertEqual(resources,
                         {demand['id']: (demand['unit'], demand['quantity'])
                          for demand in self.capacity['capacity_demands']})

    def test_the_reservation_intent_expires_after_the_handoff_instant(self):
        self.assertEqual(self.reservation['spec']['expires_at'],
                         (AS_OF + address_owner.HOLD_HORIZON).isoformat().replace('+00:00', 'Z'))
        address_owner.validate_reservation_intent(self.reservation, self.capacity, as_of=AS_OF)

    def test_a_reservation_intent_that_expires_before_the_handoff_is_refused(self):
        expired = dict(self.reservation, spec=dict(self.reservation['spec']))
        expired['spec']['expires_at'] = (AS_OF - timedelta(hours=1)).isoformat()
        error = _refusal(address_owner.validate_reservation_intent, expired, self.capacity,
                         as_of=AS_OF)
        self.assertEqual(error.code, 'SEMANTIC_INCONSISTENT')

    def test_a_reservation_intent_with_a_foreign_request_identity_is_refused(self):
        other = dict(self.reservation, spec=dict(self.reservation['spec'],
                                                request_id='some-other-request'))
        error = _refusal(address_owner.validate_reservation_intent, other, self.capacity,
                         as_of=AS_OF)
        self.assertEqual(error.code, 'SEMANTIC_INCONSISTENT')

    def test_the_allocation_intent_is_the_declared_shape(self):
        declared = repository.declared_contracts()['allocation_intent']
        for domain in self.domains:
            document = address_owner.allocation_intent(self.plan, domain, as_of=AS_OF)
            self.assertEqual(set(document), set(declared['keys']))
            self.assertEqual(set(document['spec']), set(declared['spec_keys']))
            self.assertEqual(document['status'], declared['status'])
            address_owner.validate_allocation_intent(document)

    def test_the_allocation_intent_binds_the_parent_reservation_spec(self):
        expected = repository.canonical_record_digest(_reservation_spec())
        for domain in self.domains:
            spec = _allocation_spec(domain['zone'])
            self.assertEqual(spec['parent_reservation_spec_sha256'], expected)

    def test_the_allocation_intent_names_the_reviewed_pool_and_prefix(self):
        for domain in self.domains:
            spec = _allocation_spec(domain['zone'])
            self.assertEqual(spec['delegated_scope_ref'],
                             f'controlled-ipam-scope:{domain["pool"]}')
            self.assertEqual(spec['requested_prefix_length'], domain['prefix_length'])
            self.assertEqual(spec['family'], domain['family'])
            self.assertEqual(spec['allocation_kind'], domain['allocation_kind'])

    def test_the_registration_intent_is_the_declared_shape(self):
        declared = repository.declared_contracts()['registration_intent']
        for domain in self.domains:
            document = address_owner.registration_intent(self.plan, domain, as_of=AS_OF)
            self.assertEqual(set(document), set(declared['keys']))
            self.assertEqual(set(document['spec']), set(declared['spec_keys']))
            self.assertEqual(document['status'], declared['status'])

    def test_the_registration_intent_binds_the_compiled_allocation(self):
        for domain in self.domains:
            spec = address_owner.registration_intent(self.plan, domain, as_of=AS_OF)['spec']
            self.assertEqual(spec['ipam_allocation_id'],
                             address_owner.allocation_id_for(self.plan, domain['zone']))
            self.assertEqual(spec['name_assignment_ref'],
                             f'controlled-name:{self.plan.operation_id}-{domain["zone"].lower()}')
            self.assertEqual(spec['record_types'],
                             sorted({address_owner.FORWARD_RECORD_TYPE[domain['family']],
                                     address_owner.REVERSE_RECORD_TYPE}))
            self.assertEqual(spec['required_observations'],
                             list(address_owner.REQUIRED_OBSERVATIONS))

    def test_every_compiled_document_denies_production_authority(self):
        for document in (self.reservation,):
            self.assertEqual(document['production_authority'], 'NOT_ASSESSED')
        for domain in self.domains:
            for document in (address_owner.allocation_intent(self.plan, domain, as_of=AS_OF),
                             address_owner.registration_intent(self.plan, domain, as_of=AS_OF)):
                self.assertEqual(document['production_authority'], 'NOT_ASSESSED')
                self.assertEqual(document['status'], 'PLANNING_ONLY_NOT_AUTHORIZED')

    def test_every_compiled_document_cites_only_reviewed_repository_sources(self):
        for domain in self.domains:
            for document in (address_owner.allocation_intent(self.plan, domain, as_of=AS_OF),
                             address_owner.registration_intent(self.plan, domain, as_of=AS_OF)):
                self.assertTrue(document['source_refs'])
                for ref in document['source_refs']:
                    self.assertTrue(repository.document_exists(ref), ref)

    def test_the_owner_preflight_accepts_a_compiled_allocation_intent(self):
        for domain in self.domains:
            document = address_owner.allocation_intent(self.plan, domain, as_of=AS_OF)
            preflight = repository.ipam_allocation_preflight(
                document, reservation_index=_index('reservation', [_parent_record()]),
                allocation_index=_index('ipam', []), as_of=AS_OF)
            self.assertEqual(preflight['status'],
                             'IPAM_INTENT_READY_EXTERNAL_RESERVE_NOT_EXECUTED')
            self.assertFalse(preflight['may_reserve_address'])

    def test_the_owner_preflight_never_returns_an_allocation_value(self):
        for domain in self.domains:
            document = address_owner.allocation_intent(self.plan, domain, as_of=AS_OF)
            preflight = repository.ipam_allocation_preflight(
                document, reservation_index=_index('reservation', [_parent_record()]),
                allocation_index=_index('ipam', []), as_of=AS_OF)
            self.assertIsNone(preflight['actual_allocation_value'])
            self.assertEqual(preflight['actual_allocation_value_source'],
                             'AUTHORITATIVE_IPAM_ONLY')
            for key in ('may_reserve_address', 'may_confirm_address', 'may_release_address',
                        'may_reuse_address', 'may_write_dns', 'may_apply', 'may_activate'):
                self.assertFalse(preflight[key], key)

    def test_the_owner_preflight_holds_an_intent_without_a_held_parent(self):
        for domain in self.domains:
            document = address_owner.allocation_intent(self.plan, domain, as_of=AS_OF)
            preflight = repository.ipam_allocation_preflight(
                document, reservation_index=_index('reservation', []),
                allocation_index=_index('ipam', []), as_of=AS_OF)
            self.assertEqual(preflight['status'], address_owner.HOLD_PARENT)

    def test_the_owner_preflight_reuses_a_matching_reserved_allocation(self):
        for domain in self.domains:
            document = address_owner.allocation_intent(self.plan, domain, as_of=AS_OF)
            preflight = repository.ipam_allocation_preflight(
                document, reservation_index=_index('reservation', [_parent_record()]),
                allocation_index=_index('ipam', [_allocation_record(domain['zone'], 'RESERVED')]),
                as_of=AS_OF)
            self.assertEqual(preflight['status'],
                             'EXISTING_RESERVED_IPAM_ALLOCATION_IDEMPOTENT')

    def test_the_owner_preflight_consumes_a_matching_confirmed_allocation(self):
        for domain in self.domains:
            document = address_owner.allocation_intent(self.plan, domain, as_of=AS_OF)
            preflight = repository.ipam_allocation_preflight(
                document, reservation_index=_index('reservation', [_parent_record()]),
                allocation_index=_index('ipam', [_allocation_record(domain['zone'], 'CONFIRMED')]),
                as_of=AS_OF)
            self.assertEqual(preflight['status'], 'EXISTING_CONFIRMED_IPAM_ALLOCATION')

    def test_the_mirrored_allocation_digest_is_the_owner_normalization(self):
        for domain in self.domains:
            document = address_owner.allocation_intent(self.plan, domain, as_of=AS_OF)
            preflight = repository.ipam_allocation_preflight(
                document, reservation_index=_index('reservation', [_parent_record()]),
                allocation_index=_index('ipam', []), as_of=AS_OF)
            spec = _allocation_spec(domain['zone'])
            self.assertEqual(preflight['intent_sha256'],
                             address_owner.allocation_intent_digest(
                                 document,
                                 parent_reservation_spec_sha256=spec['parent_reservation_spec_sha256'],
                                 hold_expires_at=spec['hold_expires_at']))

    def test_the_mirrored_registration_digest_is_the_owner_normalization(self):
        for domain in self.domains:
            document = address_owner.registration_intent(self.plan, domain, as_of=AS_OF)
            allocation = _allocation_record(domain['zone'], 'CONFIRMED')
            ipam_index = _index('ipam', [allocation])
            summary = repository.validate_ipam_allocation_records(ipam_index, as_of=AS_OF)
            confirmation = summary['records'][0]['confirmation_sha256']
            preflight = repository.dns_registration_preflight(
                document, ipam_index=ipam_index, dns_index=_index('dns', []), as_of=AS_OF)
            spec = repository.dns_registration_spec(
                document, as_of=AS_OF, ipam_confirmation_sha256=confirmation)
            self.assertEqual(preflight['intent_sha256'],
                             address_owner.registration_intent_digest(
                                 document, ipam_confirmation_sha256=confirmation,
                                 valid_until=spec['valid_until']))

    def test_the_compiled_chain_is_staged_under_the_declared_staging_root(self):
        for ref in (address_owner.CAPACITY_REQUEST_REF, address_owner.RESERVATION_INTENT_REF):
            self.assertTrue((support.ROOT / ref).is_file(), ref)

    def test_a_naive_handoff_instant_is_refused(self):
        error = _refusal(address_owner.reservation_intent, self.plan, self.capacity,
                         as_of='2026-09-18T18:00:00')
        self.assertEqual(error.code, 'SCHEMA_VALIDATION_FAILED')


class ProposalAuthorityTest(unittest.TestCase):
    """A planning prefix is a proposal and can never become ownership."""

    def setUp(self):
        self.plan = _plan()
        self.view = address_owner.address_view(self.plan)

    def test_the_view_declares_proposal_authority(self):
        self.assertEqual(self.view['authority'], address_owner.PROPOSAL_AUTHORITY)
        self.assertEqual(self.view['format'], address_owner.VIEW_FORMAT)

    def test_the_view_carries_no_generation_and_no_derived_identity(self):
        for key in ('generation', 'operation_id', 'reservation_id', 'request_id',
                    'allocation_id', 'registration_id'):
            self.assertNotIn(key, self.view)

    def test_the_view_binds_the_reviewed_inventory_and_scope(self):
        self.assertEqual(self.view['site'], self.plan.identity.scope['site_key'])
        self.assertEqual(self.view['platform'], self.plan.identity.scope['platform'])
        self.assertEqual(self.view['wsd'], self.plan.identity.scope['wsd_key'])
        # The read location is diagnostic provenance, not part of the identity.
        self.assertEqual(set(self.view['inventory']),
                         {'digest', 'source', 'status', 'authoritative'})
        self.assertEqual(self.view['inventory']['digest'],
                         self.plan.inventory.document_digest)

    def test_the_view_digest_is_a_pure_function_of_the_reviewed_decision(self):
        self.assertEqual(self.view['digest'], address_owner.view_digest(self.plan))
        self.assertEqual(address_owner.view_digest(_plan()), self.view['digest'])
        self.assertEqual(address_owner.view_digest(support.reference_plan()),
                         self.view['digest'])

    def test_the_view_is_validated_against_its_own_digest(self):
        tampered = dict(self.view, wsd='some-other-wsd')
        error = _refusal(address_owner.validate_view, tampered)
        self.assertEqual(error.code, 'SCHEMA_VALIDATION_FAILED')

    def test_the_view_refuses_a_planning_prefix_outside_its_reviewed_pool(self):
        tampered = json.loads(json.dumps(self.view))
        tampered['domains'][0]['prefix'] = '203.0.113.0/27'
        tampered['digest'] = address_owner.digest(
            {key: value for key, value in tampered.items() if key != 'digest'})
        error = _refusal(address_owner.validate_view, tampered)
        self.assertEqual(error.code, 'SCHEMA_VALIDATION_FAILED')

    def test_the_view_refuses_a_workload_address_outside_the_planning_prefix(self):
        tampered = json.loads(json.dumps(self.view))
        tampered['domains'][0]['addresses'] = ['203.0.113.7']
        tampered['digest'] = address_owner.digest(
            {key: value for key, value in tampered.items() if key != 'digest'})
        error = _refusal(address_owner.validate_view, tampered)
        self.assertEqual(error.code, 'SCHEMA_VALIDATION_FAILED')

    def test_the_view_refuses_a_domain_missing_a_declared_key(self):
        tampered = json.loads(json.dumps(self.view))
        del tampered['domains'][0]['pool']
        tampered['digest'] = address_owner.digest(
            {key: value for key, value in tampered.items() if key != 'digest'})
        error = _refusal(address_owner.validate_view, tampered)
        self.assertEqual(error.code, 'SCHEMA_VALIDATION_FAILED')

    def test_every_proposed_domain_sits_inside_its_reviewed_pool(self):
        import ipaddress
        for domain in self.view['domains']:
            network = ipaddress.ip_network(domain['prefix'], strict=False)
            pool = ipaddress.ip_network(domain['pool_cidr'], strict=False)
            self.assertTrue(network.subnet_of(pool), domain['zone'])
            self.assertEqual(domain['prefix_length'], network.prefixlen)
            for address in domain['addresses']:
                self.assertIn(ipaddress.ip_address(address), network)

    def test_the_proposal_names_the_reviewed_zone_domain_and_pool(self):
        for domain in self.view['domains']:
            self.assertEqual(domain['zone'], domain['zone'])
            self.assertTrue(domain['domain'])
            self.assertTrue(domain['pool'])
            self.assertIn(domain['family'], repository.declared_contracts()
                          ['allocation_intent']['families'])

    def test_the_manifest_binds_the_addressing_proposal_and_its_view_digest(self):
        manifest = manifest_module.build(self.plan)
        self.assertEqual(manifest['addresses']['authority'], address_owner.PROPOSAL_AUTHORITY)
        proposed = {domain['zone']: domain for domain in manifest['addresses']['domains']}
        self.assertEqual(sorted(proposed), sorted(domain['zone'] for domain in self.view['domains']))
        for domain in self.view['domains']:
            self.assertEqual(proposed[domain['zone']],
                             {'zone': domain['zone'], 'prefix': domain['prefix'],
                              'gateway_host_number': domain['gateway_host_number'],
                              'addresses': domain['addresses']})
        self.assertEqual(manifest['allocation_view'], {'digest': self.view['digest']})

    def test_the_manifest_review_names_the_addressing_terms(self):
        review = manifest_module.review(manifest_module.build(self.plan))
        self.assertEqual(review['allocation_view'], self.view['digest'])
        self.assertEqual(review['address_zones'], [domain['zone'] for domain in self.view['domains']])
        self.assertEqual(review['address_authority'], address_owner.PROPOSAL_AUTHORITY)

    def test_a_confirmed_allocation_cannot_change_the_approved_plan(self):
        before = self.plan.digest
        reconciliation = _confirmed()
        self.assertEqual(reconciliation['state'], 'CONFIRMED')
        self.assertEqual(self.plan.digest, before)
        self.assertEqual(address_owner.view_digest(self.plan), self.view['digest'])
        self.assertEqual(manifest_module.build(self.plan)['allocation_view'],
                         {'digest': self.view['digest']})
        rendered = json.dumps(reconciliation)
        for domain in self.view['domains']:
            self.assertNotIn(domain['prefix'], rendered)
            for address in domain['addresses']:
                self.assertNotIn(address, rendered)

    def test_the_proposal_does_not_speak_for_the_owner(self):
        document = service.address_evidence(self.plan, as_of=AS_OF)
        self.assertEqual(document['state'], 'PENDING_OWNER')
        self.assertFalse(document['confirmed'])
        self.assertFalse(document['registered'])
        self.assertEqual(document['view']['authority'], address_owner.PROPOSAL_AUTHORITY)


class BindingTest(unittest.TestCase):
    """An authoritative allocation is bound to the exact reviewed identity."""

    def setUp(self):
        self.plan = _plan()
        self.domain = _domains()[0]

    def test_the_binding_carries_the_reviewed_identity(self):
        document = address_owner.binding(self.plan, self.domain)
        self.assertEqual(document['format'], address_owner.BINDING_FORMAT)
        self.assertEqual(document['operation_id'], self.plan.operation_id)
        self.assertEqual(document['generation'], self.plan.generation)
        self.assertEqual(document['scope'], self.plan.identity.scope)
        self.assertEqual(document['plan_digest'], self.plan.digest)
        self.assertEqual(document['view_digest'], address_owner.view_digest(self.plan))
        self.assertEqual(document['reservation_id'], address_owner.reservation_id_for(self.plan))
        self.assertEqual(document['request_id'], address_owner.request_id_for(self.plan))
        self.assertEqual(document['allocation_id'],
                         address_owner.allocation_id_for(self.plan, self.domain['zone']))
        self.assertEqual(document['zone'], self.domain['zone'])
        self.assertEqual(document['domain'], self.domain['domain'])
        self.assertEqual(document['pool'], self.domain['pool'])
        address_owner.validate_binding(document)

    def test_the_binding_intent_digest_is_empty_until_the_chain_is_compiled(self):
        document = address_owner.binding(self.plan, self.domain)
        self.assertEqual(document['intent_digest'], '')

    def test_the_binding_accepts_the_compiled_intent_digest(self):
        spec = _allocation_spec(self.domain['zone'])
        digest = address_owner.allocation_intent_digest(
            address_owner.allocation_intent(self.plan, self.domain, as_of=AS_OF),
            parent_reservation_spec_sha256=spec['parent_reservation_spec_sha256'],
            hold_expires_at=spec['hold_expires_at'])
        document = address_owner.binding(self.plan, self.domain, intent_digest=digest)
        self.assertEqual(document['intent_digest'], digest)
        address_owner.validate_binding(document)

    def test_the_binding_is_per_zone_and_not_shared(self):
        bindings = {domain['zone']: address_owner.binding(self.plan, domain)
                    for domain in _domains()}
        self.assertEqual(len(bindings), len(_domains()))
        self.assertEqual(len({binding['allocation_id'] for binding in bindings.values()}),
                         len(bindings))
        self.assertEqual(len({binding['zone'] for binding in bindings.values()}), len(bindings))

    def test_the_binding_is_stable_across_plan_instances(self):
        self.assertEqual(address_owner.binding(self.plan, self.domain),
                         address_owner.binding(support.reference_plan(), _domains()[0]))

    def test_a_binding_missing_a_declared_key_is_refused(self):
        document = address_owner.binding(self.plan, self.domain)
        del document['pool']
        error = _refusal(address_owner.validate_binding, document)
        self.assertEqual(error.code, 'SCHEMA_VALIDATION_FAILED')

    def test_a_binding_with_an_unknown_format_is_refused(self):
        document = dict(address_owner.binding(self.plan, self.domain),
                        format='hosting-address-binding/9')
        error = _refusal(address_owner.validate_binding, document)
        self.assertEqual(error.code, 'SCHEMA_VALIDATION_FAILED')

    def test_a_binding_with_an_incomplete_scope_is_refused(self):
        document = dict(address_owner.binding(self.plan, self.domain),
                        scope={'site_key': 'site-01'})
        error = _refusal(address_owner.validate_binding, document)
        self.assertEqual(error.code, 'SCHEMA_VALIDATION_FAILED')

    def test_a_binding_with_a_malformed_intent_digest_is_refused(self):
        document = dict(address_owner.binding(self.plan, self.domain), intent_digest='nope')
        error = _refusal(address_owner.validate_binding, document)
        self.assertEqual(error.code, 'SCHEMA_VALIDATION_FAILED')

    def test_the_registration_binding_names_the_registration_operation(self):
        document = address_owner.registration_binding(self.plan, self.domain)
        self.assertEqual(document['format'], address_owner.REGISTRATION_BINDING_FORMAT)
        self.assertEqual(document['operation_id'],
                         address_owner.registration_operation_id_for(self.plan,
                                                                     self.domain['zone']))
        self.assertEqual(document['registration_id'],
                         address_owner.registration_id_for(self.plan, self.domain['zone']))
        self.assertEqual(document['allocation_id'],
                         address_owner.allocation_id_for(self.plan, self.domain['zone']))
        self.assertEqual(document['scope'], self.plan.identity.scope)
        self.assertEqual(document['plan_digest'], self.plan.digest)
        address_owner.validate_registration_binding(document)

    def test_the_registration_binding_carries_the_confirmation_digest(self):
        document = address_owner.registration_binding(self.plan, self.domain)
        self.assertEqual(document['intent_digest'], '')
        confirmed = address_owner.registration_binding(
            self.plan, self.domain, ipam_confirmation_sha256=_confirmation(self.domain['zone']),
            intent_digest=OTHER_DIGEST)
        self.assertEqual(confirmed['intent_digest'], OTHER_DIGEST)
        address_owner.validate_registration_binding(confirmed)

    def test_a_registration_binding_missing_the_registration_id_is_refused(self):
        document = address_owner.registration_binding(self.plan, self.domain)
        del document['registration_id']
        error = _refusal(address_owner.validate_registration_binding, document)
        self.assertEqual(error.code, 'SCHEMA_VALIDATION_FAILED')

    def test_a_registration_binding_with_an_unknown_format_is_refused(self):
        document = dict(address_owner.registration_binding(self.plan, self.domain),
                        format='hosting-dns-registration-binding/9')
        error = _refusal(address_owner.validate_registration_binding, document)
        self.assertEqual(error.code, 'SCHEMA_VALIDATION_FAILED')

    def test_the_registration_binding_is_distinct_from_the_allocation_binding(self):
        allocation = address_owner.binding(self.plan, self.domain)
        registration = address_owner.registration_binding(self.plan, self.domain)
        self.assertNotEqual(allocation['format'], registration['format'])
        self.assertNotEqual(allocation['operation_id'], registration['operation_id'])
        self.assertNotIn('registration_id', allocation)
        self.assertIn('allocation_id', registration)
        self.assertEqual(set(allocation) & set(registration),
                         {'format', 'operation_id', 'generation', 'scope', 'plan_digest',
                          'view_digest', 'reservation_id', 'request_id', 'allocation_id',
                          'zone', 'domain', 'pool', 'intent_digest'})


class HandoffTest(unittest.TestCase):
    """The whole reviewed chain is compiled and bound as one handover."""

    def setUp(self):
        self.plan = _plan()
        self.document = address_owner.handoff(self.plan, as_of=AS_OF)

    def test_the_handoff_carries_the_reviewed_identity(self):
        self.assertEqual(self.document['format'], address_owner.HANDOFF_FORMAT)
        self.assertEqual(self.document['operation_id'], self.plan.operation_id)
        self.assertEqual(self.document['generation'], self.plan.generation)
        self.assertEqual(self.document['scope'], self.plan.identity.scope)
        self.assertEqual(self.document['plan_digest'], self.plan.digest)
        self.assertEqual(self.document['view_digest'], address_owner.view_digest(self.plan))
        self.assertEqual(self.document['reservation_id'],
                         address_owner.reservation_id_for(self.plan))
        address_owner.validate_handoff(self.document)

    def test_the_handoff_compiles_one_allocation_and_one_registration_per_zone(self):
        self.assertEqual(len(self.document['allocations']), len(_domains()))
        self.assertEqual(len(self.document['registrations']), len(_domains()))
        for document, domain in zip(self.document['allocations'], _domains()):
            self.assertEqual(document['spec']['allocation_id'],
                             address_owner.allocation_id_for(self.plan, domain['zone']))
        for document, domain in zip(self.document['registrations'], _domains()):
            self.assertEqual(document['spec']['registration_id'],
                             address_owner.registration_id_for(self.plan, domain['zone']))

    def test_the_handoff_names_the_staged_sibling_documents(self):
        self.assertEqual(self.document['staged'],
                         {'capacity_request_ref': address_owner.CAPACITY_REQUEST_REF,
                          'reservation_intent_ref': address_owner.RESERVATION_INTENT_REF})
        self.assertEqual(self.document['capacity_request'], _capacity())
        self.assertEqual(self.document['reservation_intent'], _reservation())

    def test_the_handoff_carries_the_digests_the_owner_records(self):
        digests = self.document['digests']
        self.assertEqual(digests['reservation_intent'],
                         repository.canonical_record_digest(_reservation()['spec']))
        self.assertEqual(len(digests['allocations']), len(_domains()))
        self.assertEqual(len(digests['registrations']), len(_domains()))
        self.assertEqual(digests['capacity_request'],
                         address_owner.digest(_capacity()))

    def test_the_handoff_carries_the_declared_limits(self):
        self.assertEqual(self.document['limits'], list(address_owner.LIMITS))

    def test_the_handoff_resolves_against_the_staged_chain(self):
        resolved = address_owner.handoff(self.plan, as_of=AS_OF, resolved=True)
        self.assertEqual(resolved['digests'], self.document['digests'])

    def test_the_handoff_does_not_depend_on_the_reconciliation_instant(self):
        self.assertEqual(address_owner.handoff(self.plan, as_of=AS_OF)['as_of'],
                         AS_OF.isoformat())
        self.assertEqual(address_owner.handoff(self.plan, as_of=AS_OF),
                         address_owner.handoff(self.plan, as_of=AS_OF))

    def test_a_handoff_missing_a_declared_key_is_refused(self):
        document = dict(self.document)
        del document['digests']
        error = _refusal(address_owner.validate_handoff, document)
        self.assertEqual(error.code, 'SCHEMA_VALIDATION_FAILED')

    def test_a_handoff_with_an_unknown_format_is_refused(self):
        document = dict(self.document, format='hosting-address-owner-handoff/9')
        error = _refusal(address_owner.validate_handoff, document)
        self.assertEqual(error.code, 'SCHEMA_VALIDATION_FAILED')

    def test_a_handoff_without_an_allocation_is_refused(self):
        document = dict(self.document, allocations=[])
        error = _refusal(address_owner.validate_handoff, document)
        self.assertEqual(error.code, 'SCHEMA_VALIDATION_FAILED')

    def test_a_handoff_with_unpaired_allocations_is_refused(self):
        document = dict(self.document, registrations=self.document['registrations'][:1])
        error = _refusal(address_owner.validate_handoff, document)
        self.assertEqual(error.code, 'SCHEMA_VALIDATION_FAILED')


class ReconciliationTest(unittest.TestCase):
    """An owner reply is reconciled, and an absent reply stays the owner's work."""

    def setUp(self):
        self.plan = _plan()

    def test_an_unrecorded_chain_is_pending_the_owner(self):
        document = _reconcile(self.plan, zones=())
        self.assertEqual(document['state'], 'PENDING_OWNER')
        self.assertFalse(document['confirmed'])
        self.assertFalse(document['registered'])
        self.assertTrue(document['may_allocate'])
        self.assertFalse(document['may_register'])
        for item in document['allocations']:
            self.assertEqual(item['state'],
                             'IPAM_INTENT_READY_EXTERNAL_RESERVE_NOT_EXECUTED')
            self.assertEqual(item['next_owner_action'],
                             'OWNER_RESERVE_THEN_CONFIRM_ALLOCATION')
            self.assertFalse(item['allocation_present'])
            self.assertFalse(item['confirmed'])

    def test_a_reserved_allocation_is_idempotent_and_not_confirmed(self):
        document = _reconcile(self.plan)
        self.assertEqual(document['state'], 'PENDING_OWNER')
        for item in document['allocations']:
            self.assertEqual(item['state'],
                             'EXISTING_RESERVED_IPAM_ALLOCATION_IDEMPOTENT')
            self.assertEqual(item['record_state'], 'RESERVED')
            self.assertFalse(item['confirmed'])
            self.assertTrue(item['may_allocate'])
            self.assertFalse(item['may_register'])
            self.assertEqual(item['registration_state'],
                             'HOLD_IPAM_ALLOCATION_NOT_CONFIRMED')

    def test_a_confirmed_allocation_confirms_every_zone(self):
        document = _confirmed()
        self.assertEqual(document['state'], 'CONFIRMED')
        self.assertTrue(document['confirmed'])
        self.assertFalse(document['registered'])
        self.assertTrue(document['may_register'])
        for item in document['allocations']:
            self.assertEqual(item['state'], 'EXISTING_CONFIRMED_IPAM_ALLOCATION')
            self.assertEqual(item['registration_state'],
                             'DNS_INTENT_READY_EXTERNAL_CHANGE_NOT_EXECUTED')
            self.assertEqual(item['next_owner_action'], 'OWNER_REGISTER_NAME_THEN_OBSERVE')
            self.assertTrue(item['confirmed'])

    def test_a_registered_name_confirms_the_zone(self):
        zones = _zones()
        document = _reconcile(self.plan, zones=zones,
                              allocation_states={zone: 'CONFIRMED' for zone in zones},
                              registration_states={zone: 'REGISTERED' for zone in zones})
        self.assertEqual(document['state'], 'CONFIRMED')
        self.assertTrue(document['registered'])
        for item in document['allocations']:
            self.assertEqual(item['registration_state'],
                             'EXISTING_REGISTERED_DNS_IDEMPOTENT')
            self.assertEqual(item['next_owner_action'],
                             'NONE_ALLOCATION_AND_REGISTRATION_CONFIRMED')

    def test_a_missing_parent_is_a_hold_for_the_owner(self):
        document = _reconcile(self.plan, zones=(), parent=None)
        self.assertEqual(document['state'], 'PENDING_OWNER')
        self.assertEqual(document['parent']['state'], 'ABSENT')
        self.assertFalse(document['parent']['record_present'])
        for item in document['allocations']:
            self.assertEqual(item['state'], 'HOLD_PARENT_RESERVATION_NOT_HELD')
            self.assertEqual(item['next_owner_action'],
                             'OWNER_HOLD_PARENT_CAPACITY_RESERVATION_FIRST')
            self.assertFalse(item['may_allocate'])

    def test_a_consumed_parent_is_a_hold_for_the_owner(self):
        document = _reconcile(self.plan, zones=(), parent='CONSUMED')
        self.assertEqual(document['parent']['state'], 'NOT_HELD')
        for item in document['allocations']:
            self.assertEqual(item['state'], 'HOLD_PARENT_RESERVATION_NOT_HELD')

    def test_the_reconciliation_carries_the_reviewed_identity(self):
        document = _reconcile(self.plan, zones=())
        self.assertEqual(document['format'], address_owner.RECONCILIATION_FORMAT)
        self.assertEqual(document['operation_id'], self.plan.operation_id)
        self.assertEqual(document['generation'], self.plan.generation)
        self.assertEqual(document['reservation_id'],
                         address_owner.reservation_id_for(self.plan))
        self.assertEqual(document['view_digest'], address_owner.view_digest(self.plan))
        self.assertEqual(document['parent']['reservation_id'],
                         address_owner.reservation_id_for(self.plan))

    def test_the_reconciliation_counts_the_records_it_checked(self):
        self.assertEqual(_reconcile(self.plan, zones=()).get('records_checked'), 1)
        self.assertEqual(_confirmed()['records_checked'], 1 + len(_domains()))
        registered = _reconcile(
            self.plan, allocation_states={zone: 'CONFIRMED' for zone in _zones()},
            registration_states={zone: 'REGISTERED' for zone in _zones()})
        self.assertEqual(registered['records_checked'], 1 + 2 * len(_domains()))

    def test_the_reconciliation_is_deterministic_for_a_fixed_instant(self):
        self.assertEqual(_reconcile(self.plan), _reconcile(self.plan))

    def test_a_naive_review_instant_is_refused(self):
        error = _refusal(_reconcile, self.plan, as_of='2026-09-18T18:00:00')
        self.assertEqual(error.code, 'SCHEMA_VALIDATION_FAILED')

    def test_the_review_projection_is_the_reviewer_facing_summary(self):
        document = _confirmed()
        review = address_owner.review(document)
        self.assertEqual(review['format'], address_owner.RECONCILIATION_FORMAT)
        self.assertEqual(review['state'], document['state'])
        self.assertEqual(review['view_digest'], document['view_digest'])
        self.assertEqual(review['reservation_id'], document['reservation_id'])
        self.assertEqual([zone['zone'] for zone in review['zones']], list(_zones()))
        self.assertNotIn('allocations', review)
        self.assertNotIn('records', review)

    def test_the_review_projection_carries_no_allocated_value(self):
        rendered = json.dumps(address_owner.review(_confirmed()))
        for domain in _domains():
            self.assertNotIn(domain['prefix'], rendered)

    def test_the_reconciliation_never_grants_apply_authority(self):
        document = _confirmed()
        self.assertNotIn('may_apply', document)
        self.assertNotIn('may_activate', document)
        self.assertEqual(document['limits'], list(address_owner.LIMITS))


class UncertainOutcomeTest(unittest.TestCase):
    """An unknown or conflicting reply is reconciled, never retried blindly."""

    def setUp(self):
        self.plan = _plan()

    def test_an_uncertain_allocation_asks_the_owner_to_discover_the_outcome(self):
        document = _reconcile(self.plan, allocation_states={_zones()[0]: 'UNCERTAIN',
                                                           _zones()[1]: 'CONFIRMED'})
        self.assertEqual(document['state'], 'REFUSED')
        item = document['allocations'][0]
        self.assertEqual(item['state'], 'HOLD_DISCOVER_IPAM_OUTCOME')
        self.assertEqual(item['next_owner_action'], 'OWNER_DISCOVER_AUTHORITATIVE_OUTCOME')
        self.assertFalse(item['may_allocate'])
        self.assertFalse(item['confirmed'])

    def test_a_lost_allocation_reply_is_reconciled_and_not_duplicated(self):
        document = _reconcile(self.plan, allocation_states={_zones()[0]: 'UNCERTAIN',
                                                           _zones()[1]: 'CONFIRMED'})
        error = _refusal(address_owner.require_confirmed, document)
        self.assertEqual(error.code, 'IPAM_ALLOCATION_UNRESOLVED')
        self.assertEqual(error.details['allocation_id'],
                         address_owner.allocation_id_for(self.plan, _zones()[0]))

    def test_a_second_zone_is_unaffected_by_one_uncertain_zone(self):
        document = _reconcile(self.plan, allocation_states={_zones()[0]: 'UNCERTAIN',
                                                           _zones()[1]: 'CONFIRMED'})
        item = document['allocations'][1]
        self.assertEqual(item['state'], 'EXISTING_CONFIRMED_IPAM_ALLOCATION')
        self.assertTrue(item['confirmed'])

    def test_an_uncertain_allocation_blocks_registration_for_its_zone(self):
        document = _reconcile(self.plan, allocation_states={_zones()[0]: 'UNCERTAIN',
                                                           _zones()[1]: 'CONFIRMED'})
        item = document['allocations'][0]
        self.assertEqual(item['registration_state'],
                         'HOLD_IPAM_ALLOCATION_NOT_CONFIRMED')
        self.assertFalse(document['may_register'])

    def test_an_uncertain_registration_is_reconciled(self):
        zones = _zones()
        document = _reconcile(
            self.plan,
            allocation_states={zone: 'CONFIRMED' for zone in zones},
            registration_states={zones[0]: 'UNCERTAIN', zones[1]: 'REGISTERED'})
        self.assertEqual(document['allocations'][0]['registration_state'],
                         'HOLD_DISCOVER_DNS_OUTCOME')
        error = _refusal(address_owner.require_settled, document)
        self.assertEqual(error.code, 'DNS_REGISTRATION_UNRESOLVED')

    def test_a_conflicting_parent_is_a_reviewer_hold(self):
        document = _reconcile(self.plan, parent_tamper=True)
        self.assertEqual(document['state'], 'REFUSED')
        self.assertEqual(document['parent']['state'], 'CONFLICT')
        for item in document['allocations']:
            self.assertEqual(item['state'], 'HOLD_IPAM_IDENTITY_OR_INTENT_CONFLICT')
            self.assertEqual(item['next_owner_action'], 'REVIEWER_RECONCILE_ALLOCATION_IDENTITY')
            self.assertIn('parent capacity reservation', item['reasons'][0])

    def test_a_conflicting_allocation_is_a_reviewer_hold(self):
        document = _reconcile(self.plan, allocation_tamper=True)
        self.assertEqual(document['state'], 'REFUSED')
        for item in document['allocations']:
            self.assertEqual(item['state'], 'HOLD_IPAM_IDENTITY_OR_INTENT_CONFLICT')
            self.assertIn('authoritative allocation', item['reasons'][0])

    def test_a_conflicting_allocation_leaves_the_other_zone_unaffected(self):
        document = _reconcile(self.plan, zones=(_zones()[0],),
                              allocation_states={_zones()[0]: 'CONFIRMED'},
                              allocation_tamper=True)
        self.assertEqual(document['allocations'][0]['state'],
                         'HOLD_IPAM_IDENTITY_OR_INTENT_CONFLICT')
        self.assertEqual(document['allocations'][1]['state'],
                         'IPAM_INTENT_READY_EXTERNAL_RESERVE_NOT_EXECUTED')

    def test_a_terminal_allocation_requires_a_new_operation(self):
        document = _reconcile(self.plan, zones=(_zones()[0],),
                              allocation_states={_zones()[0]: 'QUARANTINED'},
                              lifecycle=True)
        item = document['allocations'][0]
        self.assertEqual(item['state'],
                         'HOLD_TERMINAL_IPAM_ALLOCATION_NEW_OPERATION_REQUIRED')
        self.assertEqual(item['next_owner_action'], 'REVIEWER_OPEN_A_NEW_ALLOCATION_OPERATION')

    def test_require_confirmed_refuses_a_conflicting_allocation(self):
        error = _refusal(address_owner.require_confirmed, _reconcile(self.plan,
                                                                    allocation_tamper=True))
        self.assertEqual(error.code, 'IPAM_ALLOCATION_CONFLICT')

    def test_require_confirmed_refuses_a_terminal_allocation(self):
        document = _reconcile(self.plan, zones=(_zones()[0],),
                              allocation_states={_zones()[0]: 'QUARANTINED'},
                              lifecycle=True)
        error = _refusal(address_owner.require_confirmed, document)
        self.assertEqual(error.code, 'IPAM_ALLOCATION_UNCONFIRMED')

    def test_require_confirmed_refuses_an_unconfirmed_allocation(self):
        error = _refusal(address_owner.require_confirmed, _reconcile(self.plan))
        self.assertEqual(error.code, 'IPAM_ALLOCATION_UNCONFIRMED')

    def test_require_confirmed_accepts_a_confirmed_reconciliation(self):
        document = _confirmed()
        self.assertEqual(address_owner.require_confirmed(document), document)

    def test_require_confirmed_refuses_a_document_that_is_not_a_reconciliation(self):
        error = _refusal(address_owner.require_confirmed, {'format': 'something-else'})
        self.assertEqual(error.code, 'SCHEMA_VALIDATION_FAILED')

    def test_require_settled_refuses_an_unknown_outcome_and_accepts_an_absent_one(self):
        document = _reconcile(self.plan, zones=())
        self.assertEqual(address_owner.require_settled(document), document)
        unresolved = _reconcile(self.plan, allocation_states={_zones()[0]: 'UNCERTAIN',
                                                             _zones()[1]: 'CONFIRMED'})
        error = _refusal(address_owner.require_settled, unresolved)
        self.assertEqual(error.code, 'IPAM_ALLOCATION_UNRESOLVED')


class RegistrationOrderingTest(unittest.TestCase):
    """A name is registered only against a confirmed authoritative allocation."""

    def setUp(self):
        self.plan = _plan()
        self.zones = _zones()

    def test_a_name_cannot_be_registered_before_the_allocation_is_confirmed(self):
        document = _reconcile(self.plan)
        for item in document['allocations']:
            self.assertEqual(item['registration_state'],
                             'HOLD_IPAM_ALLOCATION_NOT_CONFIRMED')
            self.assertFalse(item['may_register'])
        error = _refusal(address_owner.require_registered, document)
        self.assertEqual(error.code, 'IPAM_ALLOCATION_UNCONFIRMED')

    def test_a_name_cannot_be_registered_while_the_allocation_is_only_reserved(self):
        document = _reconcile(self.plan, zones=self.zones,
                              allocation_states={zone: 'RESERVED' for zone in self.zones})
        error = _refusal(address_owner.require_registered, document)
        self.assertEqual(error.code, 'IPAM_ALLOCATION_UNCONFIRMED')

    def test_the_owner_preflight_holds_a_registration_without_an_allocation(self):
        for domain in _domains():
            document = address_owner.registration_intent(self.plan, domain, as_of=AS_OF)
            preflight = repository.dns_registration_preflight(
                document, ipam_index=_index('ipam', []), dns_index=_index('dns', []),
                as_of=AS_OF)
            self.assertEqual(preflight['status'], address_owner.REGISTRATION_HOLD_IPAM)
            self.assertIsNone(preflight['actual_dns_name'])
            self.assertIsNone(preflight['actual_record_values'])
            self.assertFalse(preflight['may_write_dns'])
            self.assertFalse(preflight['may_delete_dns'])

    def test_the_owner_preflight_holds_a_registration_against_a_reserved_allocation(self):
        for domain in _domains():
            document = address_owner.registration_intent(self.plan, domain, as_of=AS_OF)
            preflight = repository.dns_registration_preflight(
                document,
                ipam_index=_index('ipam', [_allocation_record(domain['zone'], 'RESERVED')]),
                dns_index=_index('dns', []), as_of=AS_OF)
            self.assertEqual(preflight['status'], address_owner.REGISTRATION_HOLD_IPAM)

    def test_the_owner_preflight_accepts_a_registration_against_a_confirmed_allocation(self):
        for domain in _domains():
            document = address_owner.registration_intent(self.plan, domain, as_of=AS_OF)
            preflight = repository.dns_registration_preflight(
                document,
                ipam_index=_index('ipam', [_allocation_record(domain['zone'], 'CONFIRMED')]),
                dns_index=_index('dns', []), as_of=AS_OF)
            self.assertEqual(preflight['status'],
                             'DNS_INTENT_READY_EXTERNAL_CHANGE_NOT_EXECUTED')

    def test_the_owner_preflight_reuses_a_matching_registration(self):
        for domain in _domains():
            document = address_owner.registration_intent(self.plan, domain, as_of=AS_OF)
            preflight = repository.dns_registration_preflight(
                document,
                ipam_index=_index('ipam', [_allocation_record(domain['zone'], 'CONFIRMED')]),
                dns_index=_index('dns', [_dns_record(domain['zone'], 'REGISTERED')]),
                as_of=AS_OF)
            self.assertEqual(preflight['status'], 'EXISTING_REGISTERED_DNS_IDEMPOTENT')

    def test_a_registration_carrying_a_different_intent_is_a_hold(self):
        domain = _domains()[0]
        tampered = dict(_dns_record(domain['zone'], 'REGISTERED'), intent_sha256=OTHER_DIGEST)
        index = _index('dns', [tampered])
        ipam_index = _index('ipam', [_allocation_record(domain['zone'], 'CONFIRMED')])
        preflight = repository.dns_registration_preflight(
            address_owner.registration_intent(self.plan, domain, as_of=AS_OF),
            ipam_index=ipam_index, dns_index=index, as_of=AS_OF)
        self.assertEqual(preflight['status'], address_owner.REGISTRATION_HOLD_CONFLICT)

    def test_a_registration_operation_identity_is_per_zone(self):
        operations = {address_owner.registration_operation_id_for(self.plan, zone)
                      for zone in self.zones}
        self.assertEqual(len(operations), len(self.zones))
        self.assertEqual(len({address_owner.registration_id_for(self.plan, zone)
                              for zone in self.zones}), len(self.zones))

    def test_the_compiled_registration_intent_is_never_compiled_against_a_proposal(self):
        for domain in _domains():
            spec = address_owner.registration_intent(self.plan, domain, as_of=AS_OF)['spec']
            self.assertEqual(spec['ipam_allocation_id'],
                             address_owner.allocation_id_for(self.plan, domain['zone']))
            self.assertNotIn('prefix', spec)
            self.assertNotIn('address', spec)
            self.assertNotIn('dns_name', spec)

    def test_require_registered_refuses_until_every_zone_is_registered(self):
        document = _reconcile(self.plan, zones=self.zones,
                              allocation_states={zone: 'CONFIRMED' for zone in self.zones},
                              registration_states={self.zones[0]: 'REGISTERED'})
        error = _refusal(address_owner.require_registered, document)
        self.assertEqual(error.code, 'DNS_REGISTRATION_UNCONFIRMED')

    def test_require_registered_accepts_a_fully_registered_reconciliation(self):
        document = _reconcile(self.plan, zones=self.zones,
                              allocation_states={zone: 'CONFIRMED' for zone in self.zones},
                              registration_states={zone: 'REGISTERED' for zone in self.zones})
        self.assertEqual(address_owner.require_registered(document), document)

    def test_require_registered_refuses_a_conflicting_registration(self):
        document = _reconcile(self.plan,
                              allocation_states={zone: 'CONFIRMED' for zone in self.zones},
                              registration_states={self.zones[0]: 'UNCERTAIN'})
        error = _refusal(address_owner.require_registered, document)
        self.assertEqual(error.code, 'DNS_REGISTRATION_UNRESOLVED')


class RetirementOrderingTest(unittest.TestCase):
    """Reusable addressing is never handed back before dependent state is withdrawn."""

    def setUp(self):
        self.plan = _plan()
        self.zones = _zones()

    def _reuse(self, registration_state: str) -> dict:
        return _reconcile(self.plan, zones=self.zones,
                          allocation_states={self.zones[0]: 'QUARANTINED',
                                             self.zones[1]: 'CONFIRMED'},
                          registration_states={self.zones[0]: registration_state},
                          lifecycle=True)

    def test_reusing_a_released_allocation_while_its_name_is_live_is_a_hold(self):
        document = self._reuse('RELEASE_PENDING')
        self.assertEqual(document['state'], 'REFUSED')
        item = document['allocations'][0]
        self.assertEqual(item['state'], 'HOLD_IPAM_RELEASE_LIFECYCLE')
        self.assertEqual(item['registration_state'], 'HOLD_DNS_RELEASE_LIFECYCLE')
        self.assertEqual(item['next_owner_action'],
                         'OWNER_WITHDRAW_DEPENDENT_DNS_BEFORE_ADDRESS_REUSE')
        self.assertTrue(item['reusable'])
        self.assertFalse(item['may_allocate'])

    def test_the_live_name_leaves_the_other_zone_unaffected(self):
        document = self._reuse('RELEASE_PENDING')
        self.assertEqual(document['allocations'][1]['state'],
                         'EXISTING_CONFIRMED_IPAM_ALLOCATION')

    def test_require_releasable_refuses_a_live_registration(self):
        document = self._reuse('RELEASE_PENDING')
        error = _refusal(address_owner.require_releasable, document)
        self.assertEqual(error.code, 'ADDRESS_RELEASE_ORDER_VIOLATION')
        self.assertEqual(error.details['registration_state'], 'RELEASE_PENDING')

    def test_a_withdrawn_registration_unblocks_the_release(self):
        document = self._reuse('TOMBSTONED')
        self.assertEqual(address_owner.require_releasable(document), document)
        self.assertEqual(document['allocations'][0]['registration_state'],
                         'HOLD_DNS_RELEASE_LIFECYCLE')

    def test_a_released_allocation_whose_name_is_only_tombstoned_is_refused(self):
        document = _reconcile(self.plan, zones=self.zones,
                              allocation_states={self.zones[0]: 'RELEASED',
                                                 self.zones[1]: 'CONFIRMED'},
                              registration_states={self.zones[0]: 'TOMBSTONED'},
                              lifecycle=True)
        error = _refusal(address_owner.require_releasable, document)
        self.assertEqual(error.code, 'ADDRESS_RELEASE_ORDER_VIOLATION')
        self.assertEqual(error.details['record_state'], 'RELEASED')
        self.assertEqual(error.details['registration_state'], 'TOMBSTONED')

    def test_a_fully_released_chain_still_requires_a_new_operation(self):
        document = _reconcile(self.plan, zones=self.zones,
                              allocation_states={self.zones[0]: 'RELEASED',
                                                 self.zones[1]: 'CONFIRMED'},
                              registration_states={self.zones[0]: 'RELEASED'},
                              lifecycle=True)
        self.assertEqual(address_owner.require_releasable(document), document)
        item = document['allocations'][0]
        self.assertEqual(item['state'],
                         'HOLD_TERMINAL_IPAM_ALLOCATION_NEW_OPERATION_REQUIRED')
        self.assertEqual(item['registration_state'],
                         'DNS_INTENT_READY_EXTERNAL_CHANGE_NOT_EXECUTED')

    def test_a_reusable_state_with_an_incomplete_cleanup_is_refused_by_the_owner(self):
        incomplete = _allocation_record(self.zones[0], 'QUARANTINED', lifecycle=False)
        error = _refusal(address_owner.reconcile, self.plan,
                         allocation_index=_write(_index('ipam', [incomplete])),
                         as_of=AS_OF)
        self.assertEqual(error.code, 'SCHEMA_VALIDATION_FAILED')
        self.assertIn('cleanup', error.message)
        document = self._reuse('TOMBSTONED')
        self.assertTrue(document['allocations'][0]['cleanup_complete'])

    def test_a_quarantined_allocation_is_never_treated_as_confirmed(self):
        document = self._reuse('TOMBSTONED')
        item = document['allocations'][0]
        self.assertFalse(item['confirmed'])
        self.assertFalse(item['may_allocate'])
        self.assertFalse(item['may_register'])
        error = _refusal(address_owner.require_confirmed, document)
        self.assertEqual(error.code, 'IPAM_ALLOCATION_UNCONFIRMED')

    def test_require_releasable_ignores_a_non_reusable_allocation(self):
        document = _confirmed()
        for item in document['allocations']:
            self.assertFalse(item['reusable'])
        self.assertEqual(address_owner.require_releasable(document), document)

    def test_require_releasable_refuses_a_document_that_is_not_a_reconciliation(self):
        error = _refusal(address_owner.require_releasable, {'format': 'something-else'})
        self.assertEqual(error.code, 'SCHEMA_VALIDATION_FAILED')

    def test_the_owner_preflight_holds_a_quarantined_allocation_for_release(self):
        domain = _domains()[0]
        document = address_owner.allocation_intent(self.plan, domain, as_of=AS_OF)
        preflight = repository.ipam_allocation_preflight(
            document, reservation_index=_index('reservation', [_parent_record()]),
            allocation_index=_index('ipam', [_allocation_record(domain['zone'],
                                                               'QUARANTINED',
                                                               lifecycle=True)]),
            as_of=AS_OF)
        self.assertEqual(preflight['status'], address_owner.HOLD_RELEASE)
        self.assertFalse(preflight['may_release_address'])
        self.assertFalse(preflight['may_reuse_address'])


class SharedEvidenceTest(unittest.TestCase):
    """Every transport reads addressing the same way, from the repository's evidence."""

    def setUp(self):
        self.plan = _plan()

    def test_the_evidence_reports_the_view_and_the_compiled_handoff(self):
        document = service.address_evidence(self.plan, as_of=AS_OF)
        self.assertEqual(document['view'], address_owner.address_view(self.plan))
        self.assertEqual(document['view_digest'], address_owner.view_digest(self.plan))
        self.assertEqual(document['scope'], self.plan.identity.scope)
        self.assertEqual(document['handoff'],
                         address_owner.handoff(self.plan, as_of=AS_OF))
        self.assertEqual(document['limits'], list(address_owner.LIMITS))

    def test_the_evidence_is_a_proposal_without_owner_records(self):
        document = service.address_evidence(self.plan, as_of=AS_OF)
        self.assertEqual(document['state'], 'PENDING_OWNER')
        self.assertFalse(document['confirmed'])
        self.assertFalse(document['registered'])
        self.assertFalse(document['may_register'])
        self.assertEqual(document['view']['authority'], address_owner.PROPOSAL_AUTHORITY)

    def test_the_evidence_reads_the_exported_records_from_disk(self):
        document = service.address_evidence(
            self.plan,
            reservation_index=_write(_index('reservation', [_parent_record()])),
            allocation_index=_write(_index('ipam', [_allocation_record(zone, 'CONFIRMED')
                                                    for zone in _zones()])),
            as_of=AS_OF)
        self.assertEqual(document['state'], 'CONFIRMED')
        self.assertTrue(document['confirmed'])
        self.assertEqual(document['review']['records_checked'], 1 + len(_zones()))

    def test_the_evidence_reads_the_repository_export_by_default(self):
        document = service.address_evidence(self.plan, as_of=AS_OF)
        self.assertGreaterEqual(document['reconciliation']['records_checked'], 0)

    def test_the_evidence_never_grants_authority(self):
        document = service.address_evidence(self.plan, as_of=AS_OF)
        self.assertEqual(document['reconciliation']['limits'], list(address_owner.LIMITS))
        self.assertNotIn('may_apply', document['reconciliation'])
        self.assertNotIn('may_activate', document['handoff'])

    def _check(self, name: str, evidence: dict):
        checks = conformance_checks.run(self.plan, addresses=evidence)
        return [item for item in checks if item.name == name][0]

    def test_the_repository_address_check_states_intent_not_ownership(self):
        check = self._check('address-intent',
                            service.address_evidence(self.plan, as_of=AS_OF))
        self.assertEqual(check.status, 'PASS')
        self.assertEqual(check.authority, 'REPOSITORY')
        self.assertIn('planning intent, not authoritative ownership', check.detail)
        self.assertEqual(check.evidence['authority'], address_owner.PROPOSAL_AUTHORITY)
        self.assertEqual(check.evidence['view_digest'], address_owner.view_digest(self.plan))
        self.assertEqual(check.evidence['confirmation_check'], 'address-confirmation')

    def test_the_confirmation_check_pends_until_the_owner_records_an_allocation(self):
        check = self._check('address-confirmation',
                            service.address_evidence(self.plan, as_of=AS_OF))
        self.assertEqual(check.status, 'PENDING_EXTERNAL_EVIDENCE')
        self.assertEqual(check.authority, 'EXTERNAL')
        self.assertEqual(check.evidence['owner'], 'ipam-owner')

    def test_the_confirmation_check_passes_only_on_the_owner_confirmation(self):
        evidence = service.address_evidence(
            self.plan,
            reservation_index=_write(_index('reservation', [_parent_record()])),
            allocation_index=_write(_index('ipam', [_allocation_record(zone, 'CONFIRMED')
                                                    for zone in _zones()])),
            as_of=AS_OF)
        check = self._check('address-confirmation', evidence)
        self.assertEqual(check.status, 'PASS')
        self.assertEqual(check.authority, 'EXTERNAL')
        self.assertTrue(check.evidence['confirmed'])
        self.assertEqual(check.evidence['parent_state'], 'HELD')

    def test_the_confirmation_check_fails_on_a_conflicting_allocation(self):
        evidence = service.address_evidence(
            self.plan,
            reservation_index=_write(_index('reservation', [_parent_record()])),
            allocation_index=_write(_index('ipam', [
                _allocation_record(zone, 'CONFIRMED', tamper=True) for zone in _zones()])),
            as_of=AS_OF)
        check = self._check('address-confirmation', evidence)
        self.assertEqual(check.status, 'FAIL')
        self.assertEqual(check.evidence['state'], 'REFUSED')
        self.assertIn(address_owner.REFUSAL_CONFLICT, check.evidence['refusals'])

    def test_the_registration_check_pends_until_the_owner_registers_every_name(self):
        check = self._check('dns-registration',
                            service.address_evidence(self.plan, as_of=AS_OF))
        self.assertEqual(check.status, 'PENDING_EXTERNAL_EVIDENCE')
        self.assertEqual(check.evidence['owner'], 'dns-owner')
        self.assertEqual(check.evidence['state'], 'PENDING_OWNER')
        self.assertEqual([zone[1] for zone in check.evidence['zones']],
                         [address_owner.HOLD_PARENT] * len(_domains()))
        self.assertEqual(address_owner.REQUIRED_OBSERVATIONS, ('AUTHORITATIVE',))

    def test_the_registration_check_passes_only_on_the_owner_registration(self):
        evidence = service.address_evidence(
            self.plan,
            reservation_index=_write(_index('reservation', [_parent_record()])),
            allocation_index=_write(_index('ipam', [_allocation_record(zone, 'CONFIRMED')
                                                    for zone in _zones()])),
            registration_index=_write(_index('dns', [_dns_record(zone, 'REGISTERED')
                                                     for zone in _zones()])),
            as_of=AS_OF)
        check = self._check('dns-registration', evidence)
        self.assertEqual(check.status, 'PASS')
        self.assertEqual(check.authority, 'EXTERNAL')
        self.assertTrue(check.evidence['registered'])

    def test_the_registration_check_fails_on_a_conflicting_registration(self):
        zones = _zones()
        evidence = service.address_evidence(
            self.plan,
            reservation_index=_write(_index('reservation', [_parent_record()])),
            allocation_index=_write(_index('ipam', [_allocation_record(zone, 'CONFIRMED')
                                                    for zone in zones])),
            registration_index=_write(_index('dns', [
                dict(_dns_record(zones[0], 'REGISTERED'), intent_sha256=OTHER_DIGEST)])),
            as_of=AS_OF)
        check = self._check('dns-registration', evidence)
        self.assertEqual(check.status, 'FAIL')
        self.assertIn(address_owner.REGISTRATION_REFUSAL_CONFLICT, check.evidence['refusals'])

    def test_every_addressing_check_is_mandatory(self):
        checks = conformance_checks.run(self.plan,
                                       addresses=service.address_evidence(self.plan,
                                                                          as_of=AS_OF))
        for name in ('address-intent', 'address-confirmation', 'dns-registration'):
            check = [item for item in checks if item.name == name][0]
            self.assertTrue(check.mandatory, name)

    def test_the_conformance_report_carries_the_addressing_checks(self):
        evidence = service.address_evidence(self.plan, as_of=AS_OF)
        report = conformance_report.build(self.plan, addresses=evidence)
        document = conformance_report.to_dict(self.plan, addresses=evidence)
        self.assertEqual([item['name'] for item in report['checks']],
                         [item['name'] for item in document['checks']])
        names = [item['name'] for item in document['checks']]
        self.assertIn('address-intent', names)
        self.assertIn('address-confirmation', names)
        self.assertIn('dns-registration', names)

    def test_the_plan_digest_is_unchanged_by_reading_the_evidence(self):
        before = self.plan.digest
        service.address_evidence(self.plan, as_of=AS_OF)
        self.assertEqual(self.plan.digest, before)


if __name__ == '__main__':
    unittest.main()