"""Bind authoritative IPAM and DNS lifecycle to the reviewed provisioning plan.

The planning allocator decides which prefix a zone would like to use. That is a
proposal. It is not ownership, it is not a reservation and it is never evidence:
the authoritative IPAM and DNS owners are separate systems with their own records,
and nothing here contacts them, writes to them or speaks for them.

What the repository can do is compile the reviewed decision into the portable
intent documents the owners' existing machinery already accepts, hand them over
with the identity a real allocation must carry, and then report honestly what the
exported owner evidence says:

- `address_view()` is the exact reviewed addressing proposal the placement decision
  was taken against: the site, the platform, the WSD, the operation and, per zone,
  the selected pool, prefix, gateway host number and workload addresses. It carries
  `authority = PLANNING_PROPOSAL_NOT_AUTHORITATIVE_ALLOCATION` and is bound into the
  reviewed manifest, so an addressing proposal that moved invalidates a stale
  allocation preflight instead of silently claiming addresses it never held.
- `capacity_request()`, `reservation_intent()`, `allocation_intent()` and
  `registration_intent()` compile `portable-hosting-site-service-demand/1`,
  `portable-hosting-reservation-intent/1`,
  `portable-hosting-ipam-allocation-intent/1` and
  `portable-hosting-dns-registration-intent/1`. The owner's own preflight normalizes
  the pair it can judge in memory, and the repository's declared vocabulary - not a
  copy of it - decides every key set, policy, family, kind and status.
- `binding()` states the identity an authoritative allocation must carry to be *this*
  plan's allocation: WSD identity, generation, the parent capacity reservation, the
  selected site/zone/domain/pool and the allocation intent digest.
- `reconcile()` reads the repository's existing exported reservation, IPAM and DNS
  record indices through the repository's existing checkers and classifies the
  proposal against the authoritative records that actually exist. It never writes,
  never creates and never guesses.
- `require_confirmed()` is the gate DNS registration must pass before it may treat an
  allocation as real, `require_releasable()` refuses to release reusable addressing
  before dependent DNS withdrawal is complete, and `require_settled()` refuses to
  hand over addressing whose authoritative outcome is unknown or already spent.

Nothing here contacts an owner, mutates a record or holds authority.
"""
from __future__ import annotations

import ipaddress
import json
import re
from datetime import datetime, timedelta, timezone

from provisioner import repository
from provisioner.domain.errors import ProvisioningError
from provisioner.domain.generation import SCOPE_KEYS
from provisioner.domain.request import digest

#: The reviewed addressing proposal. Bound into the manifest; never authoritative.
VIEW_FORMAT = 'hosting-address-view/1'
#: The identity an authoritative IPAM allocation must carry to be this plan's.
BINDING_FORMAT = 'hosting-address-binding/1'
#: The compiled owner handoff around one plan's addressing chain.
HANDOFF_FORMAT = 'hosting-address-owner-handoff/1'
#: The reconciliation of the proposal against exported owner evidence.
RECONCILIATION_FORMAT = 'hosting-address-reconciliation/1'
#: The identity a DNS registration must carry to be this plan's registration.
REGISTRATION_BINDING_FORMAT = 'hosting-dns-registration-binding/1'
VIEW_KEYS = frozenset({'format', 'authority', 'inventory', 'site', 'platform', 'wsd',
                       'domains', 'limits', 'digest'})
DOMAIN_KEYS = frozenset({'zone', 'domain', 'pool', 'cluster', 'pool_cidr', 'family',
                         'allocation_kind', 'prefix', 'prefix_length',
                         'gateway_host_number', 'addresses'})
BINDING_KEYS = frozenset({'format', 'operation_id', 'generation', 'scope', 'plan_digest',
                          'view_digest', 'reservation_id', 'request_id', 'allocation_id',
                          'zone', 'domain', 'pool', 'intent_digest'})
REGISTRATION_BINDING_KEYS = frozenset({'format', 'operation_id', 'generation', 'scope',
                                       'plan_digest', 'view_digest', 'reservation_id',
                                       'request_id', 'allocation_id', 'registration_id',
                                       'zone', 'domain', 'pool', 'intent_digest'})
HANDOFF_KEYS = frozenset({'format', 'operation_id', 'generation', 'scope', 'plan_digest',
                          'view_digest', 'reservation_id', 'request_id', 'as_of',
                          'capacity_request', 'reservation_intent', 'allocations',
                          'registrations', 'digests', 'staged', 'limits'})
RECONCILIATION_KEYS = frozenset({'format', 'operation_id', 'generation', 'reservation_id',
                                 'view_digest', 'parent', 'allocations', 'state',
                                 'confirmed', 'registered', 'may_allocate',
                                 'may_register', 'records_checked', 'limits'})
ALLOCATION_RESULT_KEYS = frozenset({'allocation_id', 'registration_id', 'zone', 'domain',
                                    'pool', 'state', 'registration_state', 'record_state',
                                    'registration_record_state', 'allocation_present',
                                    'registration_present', 'confirmed', 'registered',
                                    'reusable', 'cleanup_complete', 'next_owner_action',
                                    'may_allocate', 'may_register', 'reasons'})

#: The reviewed addressing proposal is a proposal. This is the only authority it has.
PROPOSAL_AUTHORITY = 'PLANNING_PROPOSAL_NOT_AUTHORITATIVE_ALLOCATION'
#: The engineering reference every compiled owner document cites.
ENGINEERING_REF = 'docs/current/internal-hosting-solution.md'
#: Where the operator stages the compiled chain the owner preflights resolve on disk.
STAGING_ROOT = 'runtime/address-handoff'
CAPACITY_REQUEST_REF = f'{STAGING_ROOT}/site-service-capacity-request.json'
RESERVATION_INTENT_REF = f'{STAGING_ROOT}/reservation-intent.json'
#: How long a compiled intent stays valid before it must be recompiled.
HOLD_HORIZON = timedelta(hours=24)
#: The reviewed owner-role declaration every compiled document carries.
OWNER_ROLES = {
    'service_owner_role': 'platform-service-owner',
    'ipam_owner_role': 'platform-ipam-owner',
    'network_owner_role': 'platform-network-owner',
    'capacity_owner_role': 'platform-capacity-owner',
    'reservation_owner_role': 'platform-reservation-owner',
    'dns_owner_role': 'platform-dns-owner',
    'storage_owner_role': 'platform-storage-owner',
}
#: The reviewed capacity demand vocabulary, in the owner's declared demand units.
DEMAND_UNITS = {'vcpu': 'vcpu', 'memory_gib': 'GiB', 'storage_gib': 'GiB'}
DEMAND_OWNER_ROLES = {'vcpu': 'capacity_owner_role', 'memory_gib': 'capacity_owner_role',
                      'storage_gib': 'storage_owner_role'}
#: The IPAM allocation policy the reviewed addressing proposal is compiled under.
ALLOCATION_POLICY = 'UNIQUE_DEFAULT'
#: The DNS record types and observations the reviewed registration is compiled under.
FORWARD_RECORD_TYPE = {'IPV4': 'A', 'IPV6': 'AAAA'}
REVERSE_RECORD_TYPE = 'PTR'
REQUIRED_OBSERVATIONS = ('AUTHORITATIVE',)

MAX_ALLOCATIONS = 16

#: The owner-declared reconciliation states, mirrored by name and asserted at runtime.
READY = 'IPAM_INTENT_READY_EXTERNAL_RESERVE_NOT_EXECUTED'
HOLD_PARENT = 'HOLD_PARENT_RESERVATION_NOT_HELD'
HOLD_CONFLICT = 'HOLD_IPAM_IDENTITY_OR_INTENT_CONFLICT'
HOLD_UNCERTAIN = 'HOLD_DISCOVER_IPAM_OUTCOME'
HOLD_RELEASE = 'HOLD_IPAM_RELEASE_LIFECYCLE'
HOLD_TERMINAL = 'HOLD_TERMINAL_IPAM_ALLOCATION_NEW_OPERATION_REQUIRED'
EXISTING_RESERVED = 'EXISTING_RESERVED_IPAM_ALLOCATION_IDEMPOTENT'
EXISTING_CONFIRMED = 'EXISTING_CONFIRMED_IPAM_ALLOCATION'
REGISTRATION_READY = 'DNS_INTENT_READY_EXTERNAL_CHANGE_NOT_EXECUTED'
REGISTRATION_HOLD_IPAM = 'HOLD_IPAM_ALLOCATION_NOT_CONFIRMED'
REGISTRATION_HOLD_CONFLICT = 'HOLD_DNS_IDENTITY_OR_INTENT_CONFLICT'
REGISTRATION_HOLD_UNCERTAIN = 'HOLD_DISCOVER_DNS_OUTCOME'
REGISTRATION_HOLD_RELEASE = 'HOLD_DNS_RELEASE_LIFECYCLE'
REGISTRATION_HOLD_TERMINAL = 'HOLD_TERMINAL_DNS_REGISTRATION_NEW_OPERATION_REQUIRED'
REGISTRATION_EXISTING = 'EXISTING_REGISTERED_DNS_IDEMPOTENT'

ALLOCATION_STATES = (READY, HOLD_PARENT, HOLD_CONFLICT, HOLD_UNCERTAIN, HOLD_RELEASE,
                     HOLD_TERMINAL, EXISTING_RESERVED, EXISTING_CONFIRMED)
REGISTRATION_STATES = (REGISTRATION_READY, REGISTRATION_HOLD_IPAM, REGISTRATION_HOLD_CONFLICT,
                       REGISTRATION_HOLD_UNCERTAIN, REGISTRATION_HOLD_RELEASE,
                       REGISTRATION_HOLD_TERMINAL, REGISTRATION_EXISTING)
#: A refusal the operator must resolve before the plan may proceed.
REFUSING_ALLOCATION_STATES = frozenset({HOLD_CONFLICT, HOLD_UNCERTAIN, HOLD_RELEASE, HOLD_TERMINAL})
#: The states in which the owner may be asked to reserve or confirm the allocation.
ALLOCATION_READY_STATES = frozenset({READY, EXISTING_RESERVED, EXISTING_CONFIRMED})
REFUSING_REGISTRATION_STATES = frozenset({REGISTRATION_HOLD_CONFLICT, REGISTRATION_HOLD_UNCERTAIN,
                                          REGISTRATION_HOLD_RELEASE, REGISTRATION_HOLD_TERMINAL})
#: The exported IPAM allocation states that no longer own reusable addressing.
REUSABLE_RECORD_STATES = frozenset({'QUARANTINED', 'RELEASED'})
#: The exported DNS registration states that still hold a live name.
LIVE_REGISTRATION_STATES = frozenset({'REGISTERED', 'RELEASE_PENDING'})
WITHDRAWN_REGISTRATION_STATES = frozenset({'RELEASED'})
QUARANTINED_REGISTRATION_STATES = frozenset({'TOMBSTONED', 'RELEASED'})

REFUSAL_CONFLICT = 'IPAM_ALLOCATION_CONFLICT'
REFUSAL_UNRESOLVED = 'IPAM_ALLOCATION_UNRESOLVED'
REFUSAL_UNCONFIRMED = 'IPAM_ALLOCATION_UNCONFIRMED'
REGISTRATION_REFUSAL_CONFLICT = 'DNS_REGISTRATION_CONFLICT'
REGISTRATION_REFUSAL_UNRESOLVED = 'DNS_REGISTRATION_UNRESOLVED'
REGISTRATION_REFUSAL_UNCONFIRMED = 'DNS_REGISTRATION_UNCONFIRMED'

#: The refusal each stopping allocation state raises. A handoff is refused while the
#: authoritative allocation is conflicted, unknown, mid-release or spent, because a
#: downstream owner would otherwise act on addressing nobody holds.
REFUSING_STATES = {
    HOLD_CONFLICT: REFUSAL_CONFLICT,
    HOLD_UNCERTAIN: REFUSAL_UNRESOLVED,
    HOLD_RELEASE: REFUSAL_UNCONFIRMED,
    HOLD_TERMINAL: REFUSAL_UNCONFIRMED,
}

#: The refusal each stopping registration state raises.
REGISTRATION_REFUSING_STATES = {
    REGISTRATION_HOLD_CONFLICT: REGISTRATION_REFUSAL_CONFLICT,
    REGISTRATION_HOLD_UNCERTAIN: REGISTRATION_REFUSAL_UNRESOLVED,
    REGISTRATION_HOLD_RELEASE: REGISTRATION_REFUSAL_UNCONFIRMED,
    REGISTRATION_HOLD_TERMINAL: REGISTRATION_REFUSAL_UNCONFIRMED,
}
REFUSAL_RELEASE_ORDER = 'ADDRESS_RELEASE_ORDER_VIOLATION'

LIMITS = (
    'The planning prefix is a proposal; only the authoritative IPAM owner allocates.',
    'No actual address, prefix or DNS name is stored by the repository.',
    'A missing or uncertain owner reply is reconciled, never guessed and never duplicated.',
    'DNS registration is compiled only against a confirmed authoritative allocation.',
    'Reusable addressing is never released before dependent DNS withdrawal is complete.',
)

_CONTRACTS: dict | None = None


def contracts() -> dict:
    """The owner-declared portable lifecycle contracts, read from the repository."""
    global _CONTRACTS
    if _CONTRACTS is None:
        _CONTRACTS = repository.declared_contracts()
    return _CONTRACTS


def _refuse(code: str, message: str, path: str, **details) -> None:
    raise ProvisioningError(code, message, path=path, details=details)


def _identifier(value) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(contracts()['identifier'], value))


def _sha256(value) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r'[0-9a-f]{64}', value))


def _positive_int(value) -> bool:
    return type(value) is int and value >= 1


def _instant(value) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        _refuse('SCHEMA_VALIDATION_FAILED', 'A timezone-aware instant is required',
                '$.addresses.as_of', value=repr(value))
    return value.astimezone(timezone.utc)


def _assert_declared() -> None:
    """Refuse a state vocabulary the owners no longer declare."""
    allocation = set(contracts()['allocation_intent']['statuses'])
    registration = set(contracts()['registration_intent']['statuses'])
    for name in ALLOCATION_STATES:
        if name not in allocation:
            _refuse('SCHEMA_VALIDATION_FAILED',
                    f'The IPAM owner no longer declares the address state {name!r}',
                    '$.addresses.states', state=name)
    for name in REGISTRATION_STATES:
        if name not in registration:
            _refuse('SCHEMA_VALIDATION_FAILED',
                    f'The DNS owner no longer declares the registration state {name!r}',
                    '$.addresses.registration_states', state=name)


def scope_of(plan) -> dict:
    """The five-key scope every address document is bound to."""
    return {name: plan.identity.scope[name] for name in SCOPE_KEYS}


def request_id_for(plan) -> str:
    """The deterministic chain identity of one reviewed operation."""
    return f'{plan.operation_id}-demand'


def reservation_id_for(plan) -> str:
    """The parent capacity reservation this addressing chain depends on."""
    return f'{plan.operation_id}-capacity'


def allocation_id_for(plan, zone: str) -> str:
    """The deterministic authoritative allocation identity of one zone."""
    return f'{plan.operation_id}-{zone.lower()}-address'


def registration_id_for(plan, zone: str) -> str:
    """The deterministic DNS registration identity of one zone."""
    return f'{plan.operation_id}-{zone.lower()}-name'


def allocation_operation_id_for(plan, zone: str) -> str:
    """The deterministic idempotent IPAM operation identity of one zone."""
    return f'{plan.operation_id}-{zone.lower()}-ipam'


def registration_operation_id_for(plan, zone: str) -> str:
    """The deterministic idempotent DNS operation identity of one zone."""
    return f'{plan.operation_id}-{zone.lower()}-dns'


def family_of(plan) -> str:
    """The reviewed address family, in the owner's declared spelling."""
    declared = plan.resolution.network.get('address_family')
    family = str(declared or '').upper()
    if family not in contracts()['allocation_intent']['families']:
        _refuse('UNSUPPORTED_FEATURE',
                f'The reviewed address family {declared!r} has no owner allocation family',
                '$.addresses.family', family=declared)
    return family


def prefix_length_of(plan) -> int:
    """The reviewed prefix length of one zone's addressing."""
    length = plan.resolution.network.get('prefix_length')
    if type(length) is not int:
        _refuse('SCHEMA_VALIDATION_FAILED',
                'The reviewed network resolution carries no integer prefix length',
                '$.addresses.prefix_length', prefix_length=length)
    return length


def _pool(plan, domain) -> tuple[str, str]:
    """The reviewed prefix pool that contains one zone's planning prefix."""
    site = plan.identity.scope['site_key']
    pools = tuple(plan.inventory.pools(site, domain.zone))
    if not pools:
        _refuse('INVENTORY_INCOMPLETE',
                f'The reviewed inventory holds no prefix pool for zone {domain.zone}',
                '$.addresses.domains', zone=domain.zone, site=site)
    network = ipaddress.ip_network(domain.prefix, strict=False)
    for pool in pools:
        if network.subnet_of(ipaddress.ip_network(str(pool.cidr), strict=False)):
            return str(pool.pool), str(pool.cidr)
    _refuse('INVENTORY_INCOMPLETE',
            f'No reviewed prefix pool contains the planning prefix {domain.prefix}',
            '$.addresses.domains', zone=domain.zone, prefix=domain.prefix,
            pools=[str(pool.cidr) for pool in pools])


def domains(plan) -> tuple[dict, ...]:
    """Per-zone addressing proposals. A proposal is not ownership."""
    out = []
    family = family_of(plan)
    prefix_length = prefix_length_of(plan)
    for domain in plan.desired_state.domains:
        pool, cidr = _pool(plan, domain)
        out.append({
            'zone': domain.zone,
            'domain': domain.domain_id,
            'pool': pool,
            'cluster': domain.cluster_id,
            'pool_cidr': cidr,
            'family': family,
            'allocation_kind': 'PREFIX',
            'prefix': domain.prefix,
            'prefix_length': prefix_length,
            'gateway_host_number': domain.gateway_host_number,
            'addresses': [workload.address for workload in domain.workloads],
        })
    if not out:
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A reviewed plan with addressing must declare at least one zone',
                '$.addresses.domains')
    if len(out) > MAX_ALLOCATIONS:
        _refuse('SCHEMA_VALIDATION_FAILED',
                f'At most {MAX_ALLOCATIONS} zone allocations are supported',
                '$.addresses.domains', zones=len(out))
    return tuple(sorted(out, key=lambda item: item['zone']))


def demands(plan) -> tuple[dict, ...]:
    """The reviewed capacity demand, aggregated per owner demand unit."""
    totals: dict[str, int] = {}
    for reservation in plan.desired_state.reservations.values():
        for unit, quantity in reservation['demand'].items():
            totals[unit] = totals.get(unit, 0) + quantity
    if not totals:
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A reviewed plan with addressing must declare a capacity demand',
                '$.addresses.demands')
    out = []
    for unit in sorted(totals):
        if unit not in DEMAND_UNITS:
            _refuse('UNSUPPORTED_FEATURE',
                    f'The reviewed capacity demand unit {unit!r} has no owner demand unit',
                    '$.addresses.demands', unit=unit)
        quantity = str(totals[unit])
        out.append({'id': unit, 'unit': DEMAND_UNITS[unit], 'quantity': quantity,
                    'quota_remaining': quantity})
    return tuple(out)


def _inventory(plan) -> dict:
    inventory = plan.inventory
    if inventory is None:
        _refuse('INVENTORY_INCOMPLETE', 'An addressing view requires the reviewed inventory',
                '$.addresses.inventory')
    return dict(inventory.reference)


def address_view(plan) -> dict:
    """The exact reviewed addressing proposal this decision was taken against.

    A pure function of the reviewed decision and the reviewed inventory, so it can be
    bound into the manifest before the plan identity exists. It deliberately carries
    no generation and no derived operation identity: the addressing proposal is what
    it is, and the generation that claimed it belongs to the binding.
    """
    body = {'format': VIEW_FORMAT,
            'authority': PROPOSAL_AUTHORITY,
            'inventory': _inventory(plan),
            'site': plan.identity.scope['site_key'],
            'platform': plan.identity.scope['platform'],
            'wsd': plan.identity.scope['wsd_key'],
            'domains': [dict(domain) for domain in domains(plan)],
            'limits': list(LIMITS)}
    return validate_view({**body, 'digest': digest(body)})


def validate_view(document: dict) -> dict:
    """Refuse an addressing view that does not carry exactly the declared proposal."""
    if not isinstance(document, dict) or set(document) != VIEW_KEYS:
        _refuse('SCHEMA_VALIDATION_FAILED',
                'An addressing view carries exactly the declared keys',
                '$.addresses.view',
                keys=sorted(document) if isinstance(document, dict) else None)
    if document['format'] != VIEW_FORMAT:
        _refuse('SCHEMA_VALIDATION_FAILED',
                f'Unknown addressing view format {document["format"]!r}', '$.addresses.view')
    if document['authority'] != PROPOSAL_AUTHORITY:
        _refuse('SCHEMA_VALIDATION_FAILED',
                'An addressing view is a planning proposal and carries no ownership authority',
                '$.addresses.view', authority=document['authority'])
    if not isinstance(document['inventory'], dict) \
            or set(document['inventory']) != {'digest', 'source', 'status', 'authoritative'} \
            or not _sha256(document['inventory']['digest']):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'An addressing view cites the reviewed inventory it was decided against',
                '$.addresses.view')
    for key in ('site', 'platform', 'wsd'):
        if not isinstance(document[key], str) or not document[key]:
            _refuse('SCHEMA_VALIDATION_FAILED',
                    f'An addressing view {key} is bounded text', '$.addresses.view', key=key)
    if not _sha256(document['digest']):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'An addressing view carries its own SHA-256 digest', '$.addresses.view')
    if digest({key: value for key, value in document.items() if key != 'digest'}) \
            != document['digest']:
        _refuse('SCHEMA_VALIDATION_FAILED',
                'An addressing view digest does not match its own content',
                '$.addresses.view')
    if list(document['limits']) != list(LIMITS):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'An addressing view carries exactly the declared limits',
                '$.addresses.view', limits=document['limits'])
    domains_out = document['domains']
    if not isinstance(domains_out, list) or not domains_out:
        _refuse('SCHEMA_VALIDATION_FAILED',
                'An addressing view declares at least one zone', '$.addresses.view.domains')
    zones = set()
    for domain in domains_out:
        if not isinstance(domain, dict) or set(domain) != DOMAIN_KEYS:
            _refuse('SCHEMA_VALIDATION_FAILED',
                    'An addressing domain carries exactly the declared keys',
                    '$.addresses.view.domains',
                    keys=sorted(domain) if isinstance(domain, dict) else None)
        if not isinstance(domain['zone'], str) or not domain['zone'] or domain['zone'] in zones:
            _refuse('SCHEMA_VALIDATION_FAILED',
                    'Addressing zone keys are unique bounded text',
                    '$.addresses.view.domains', zone=domain['zone'])
        zones.add(domain['zone'])
        if not _identifier(domain['domain']) or not _identifier(domain['pool']):
            _refuse('SCHEMA_VALIDATION_FAILED',
                    'An addressing domain names its reviewed domain and pool',
                    '$.addresses.view.domains', zone=domain['zone'])
        if domain['family'] not in contracts()['allocation_intent']['families']:
            _refuse('SCHEMA_VALIDATION_FAILED',
                    f'Unknown address family {domain["family"]!r}',
                    '$.addresses.view.domains', zone=domain['zone'])
        if domain['allocation_kind'] not in contracts()['allocation_intent']['kinds']:
            _refuse('SCHEMA_VALIDATION_FAILED',
                    f'Unknown allocation kind {domain["allocation_kind"]!r}',
                    '$.addresses.view.domains', zone=domain['zone'])
        try:
            network = ipaddress.ip_network(domain['prefix'], strict=False)
            pool = ipaddress.ip_network(domain['pool_cidr'], strict=False)
        except ValueError:
            _refuse('SCHEMA_VALIDATION_FAILED',
                    'An addressing domain carries a parseable prefix inside its pool',
                    '$.addresses.view.domains', zone=domain['zone'])
        if not network.subnet_of(pool):
            _refuse('SCHEMA_VALIDATION_FAILED',
                    'A planning prefix must sit inside the reviewed prefix pool',
                    '$.addresses.view.domains', zone=domain['zone'], prefix=domain['prefix'])
        if not isinstance(domain['addresses'], list) or not domain['addresses']:
            _refuse('SCHEMA_VALIDATION_FAILED',
                    'An addressing domain proposes at least one workload address',
                    '$.addresses.view.domains', zone=domain['zone'])
        for address in domain['addresses']:
            try:
                parsed = ipaddress.ip_address(address)
            except ValueError:
                _refuse('SCHEMA_VALIDATION_FAILED',
                        'A proposed workload address must parse',
                        '$.addresses.view.domains', zone=domain['zone'], address=address)
            if parsed not in network:
                _refuse('SCHEMA_VALIDATION_FAILED',
                        'A proposed workload address must sit inside the planning prefix',
                        '$.addresses.view.domains', zone=domain['zone'], address=address)
    return document


def view_digest(plan) -> str:
    """The identity of the reviewed addressing proposal one plan was decided against."""
    return address_view(plan)['digest']


def binding(plan, domain: dict, *, intent_digest: str = '') -> dict:
    """The identity an authoritative allocation must carry to be this plan's.

    The intent digest is empty until the reviewed operation is compiled at a
    declared handoff instant, because a compiled intent is time-bounded. Every other
    term is a pure function of the reviewed plan.
    """
    return validate_binding({
        'format': BINDING_FORMAT,
        'operation_id': plan.operation_id,
        'generation': plan.generation,
        'scope': scope_of(plan),
        'plan_digest': plan.digest,
        'view_digest': view_digest(plan),
        'reservation_id': reservation_id_for(plan),
        'request_id': request_id_for(plan),
        'allocation_id': allocation_id_for(plan, domain['zone']),
        'zone': domain['zone'],
        'domain': domain['domain'],
        'pool': domain['pool'],
        'intent_digest': intent_digest,
    })


def validate_binding(document: dict) -> dict:
    """Refuse an address binding that does not carry exactly the declared identity."""
    if not isinstance(document, dict) or set(document) != BINDING_KEYS:
        _refuse('SCHEMA_VALIDATION_FAILED',
                'An address binding carries exactly the declared keys',
                '$.addresses.binding',
                keys=sorted(document) if isinstance(document, dict) else None)
    if document['format'] != BINDING_FORMAT:
        _refuse('SCHEMA_VALIDATION_FAILED',
                f'Unknown address binding format {document["format"]!r}', '$.addresses.binding')
    for key in ('operation_id', 'reservation_id', 'request_id', 'allocation_id', 'zone',
                'domain', 'pool'):
        if not _identifier(document[key]):
            _refuse('SCHEMA_VALIDATION_FAILED',
                    f'An address binding {key} is a scoped identifier',
                    '$.addresses.binding', key=key, value=document[key])
    if not _positive_int(document['generation']):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'An address binding generation is a positive integer',
                '$.addresses.binding', generation=document['generation'])
    if not _sha256(document['plan_digest']) or not _sha256(document['view_digest']):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'An address binding cites the reviewed plan and the addressing view',
                '$.addresses.binding')
    if document['intent_digest'] and not _sha256(document['intent_digest']):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'An address binding intent digest is empty or a SHA-256',
                '$.addresses.binding', intent_digest=document['intent_digest'])
    scope = document['scope']
    if not isinstance(scope, dict) or set(scope) != set(SCOPE_KEYS):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'An address binding carries exactly the declared scope keys',
                '$.addresses.binding.scope')
    for name in SCOPE_KEYS:
        if not isinstance(scope[name], str) or not scope[name]:
            _refuse('SCHEMA_VALIDATION_FAILED',
                    f'An address binding scope {name} is bounded text',
                    '$.addresses.binding.scope', key=name)
    return document


def registration_binding(plan, domain: dict, *, ipam_confirmation_sha256: str = '',
                         intent_digest: str = '') -> dict:
    """The identity an authoritative DNS registration must carry to be this plan's.

    A registration is bound to the confirmed authoritative allocation it depends on,
    not merely to the reviewed plan: the confirmation digest is what proves the name
    was registered against an allocation the IPAM owner actually confirmed. It is
    empty until that confirmation exists, and an empty confirmation digest can never
    satisfy a registration.
    """
    return validate_registration_binding({
        'format': REGISTRATION_BINDING_FORMAT,
        'operation_id': registration_operation_id_for(plan, domain['zone']),
        'generation': plan.generation,
        'scope': scope_of(plan),
        'plan_digest': plan.digest,
        'view_digest': view_digest(plan),
        'reservation_id': reservation_id_for(plan),
        'request_id': request_id_for(plan),
        'allocation_id': allocation_id_for(plan, domain['zone']),
        'registration_id': registration_id_for(plan, domain['zone']),
        'zone': domain['zone'],
        'domain': domain['domain'],
        'pool': domain['pool'],
        'intent_digest': intent_digest,
    })


def validate_registration_binding(document: dict) -> dict:
    """Refuse a DNS binding that does not carry exactly the declared identity."""
    if not isinstance(document, dict) or set(document) != REGISTRATION_BINDING_KEYS:
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A DNS registration binding carries exactly the declared keys',
                '$.addresses.registration_binding',
                keys=sorted(document) if isinstance(document, dict) else None)
    if document['format'] != REGISTRATION_BINDING_FORMAT:
        _refuse('SCHEMA_VALIDATION_FAILED',
                f'Unknown DNS registration binding format {document["format"]!r}',
                '$.addresses.registration_binding')
    for key in ('operation_id', 'reservation_id', 'request_id', 'allocation_id',
                'registration_id', 'zone', 'domain', 'pool'):
        if not _identifier(document[key]):
            _refuse('SCHEMA_VALIDATION_FAILED',
                    f'A DNS registration binding {key} is a scoped identifier',
                    '$.addresses.registration_binding', key=key, value=document[key])
    if not _positive_int(document['generation']):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A DNS registration binding generation is a positive integer',
                '$.addresses.registration_binding', generation=document['generation'])
    if not _sha256(document['plan_digest']) or not _sha256(document['view_digest']):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A DNS registration binding cites the reviewed plan and the addressing view',
                '$.addresses.registration_binding')
    if document['intent_digest'] and not _sha256(document['intent_digest']):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A DNS registration binding intent digest is empty or a SHA-256',
                '$.addresses.registration_binding', intent_digest=document['intent_digest'])
    scope = document['scope']
    if not isinstance(scope, dict) or set(scope) != set(SCOPE_KEYS):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A DNS registration binding carries exactly the declared scope keys',
                '$.addresses.registration_binding.scope')
    for name in SCOPE_KEYS:
        if not isinstance(scope[name], str) or not scope[name]:
            _refuse('SCHEMA_VALIDATION_FAILED',
                    f'A DNS registration binding scope {name} is bounded text',
                    '$.addresses.registration_binding.scope', key=name)
    return document


def capacity_request(plan) -> dict:
    """Compile the reviewed demand into the owner's own site-service demand contract."""
    declared = contracts()['capacity_request']
    platform = contracts_platform(plan)
    site = plan.identity.scope['site_key']
    cells = sorted({domain['cluster'] for domain in domains(plan)})
    document = {
        'format': declared['format'],
        'status': declared['status'],
        'request_id': request_id_for(plan),
        'wsd_engineering_ref': ENGINEERING_REF,
        'candidate_platforms': [platform],
        'candidate_sites': [site],
        'candidate_cells': [cell for cell in cells if _identifier(cell)],
        'candidate_service_classes': [],
        'required_assurance_profile': None,
        'required_profile_refs': {key: f'controlled-profile:{key}'
                                  for key in declared['profile_keys']},
        'capacity_demands': [dict(demand) for demand in demands(plan)],
        'production_authority': declared['authority'],
        'source_refs': source_refs(plan),
    }
    return repository.capacity_request_shape(document)


def contracts_platform(plan) -> str:
    """The owner's declared candidate-platform id for the reviewed platform family."""
    from provisioner.placement.eligibility import PLATFORM_FAMILY
    platform = plan.identity.scope['platform']
    mapped = PLATFORM_FAMILY.get(platform)
    if mapped is None or mapped not in contracts()['capacity_request']['platforms']:
        _refuse('UNSUPPORTED_FEATURE',
                f'The reviewed platform {platform!r} has no declared candidate platform id',
                '$.addresses.platform', platform=platform)
    return mapped


def source_refs(plan) -> list[str]:
    """The reviewed repository sources a compiled owner document cites."""
    refs = [ENGINEERING_REF]
    try:
        source = repository.reviewed_source(plan.request.source)
    except Exception:  # pragma: no cover - the reviewed request always has a source
        source = ''
    if source and repository.document_exists(source) and source not in refs:
        refs.append(source)
    return refs


def _expiry(as_of: datetime) -> str:
    return (as_of + HOLD_HORIZON).isoformat().replace('+00:00', 'Z')


def _owner_instant(value, label: str) -> str:
    """One instant in the owner's canonical text form."""
    return repository.instant(value, label).astimezone(timezone.utc).isoformat()


def parent_spec_sha256(plan, parent_record: dict, capacity_document: dict,
                       reservation_document: dict, *, as_of: datetime) -> str:
    """The owner's own digest of the parent reservation spec, recomputed from ours.

    The exported parent reservation record carries the digest the owner computed for
    the intent it was handed. Recomputing it from that same intent binds the
    authoritative reservation to this reviewed operation's identity, resources,
    dependency handoffs and capacity request, so a reservation held for a different
    reviewed operation is a conflict rather than a silently adopted parent.
    """
    try:
        spec = repository.reservation_intent_spec(
            reservation_document, capacity_document, as_of=as_of,
            envelope_record_sha256=parent_record['envelope_record_sha256'])
    except ValueError as exc:
        _refuse('CAPACITY_RESERVATION_CONFLICT', str(exc), '$.addresses.parent',
                operation_id=plan.operation_id)
    return repository.canonical_record_digest(spec)


def allocation_intent_digest(document: dict, *, parent_reservation_spec_sha256: str,
                             hold_expires_at: str | None = None) -> str:
    """The owner's own canonical digest of one compiled allocation intent.

    The owner normalizes a submitted intent and hashes the normalization, so the
    exported allocation record carries the digest of that normalization rather than
    of the compiled document. This mirrors the declared normalization exactly: the
    declared spec keys, the parent reservation spec digest, and the hold expiry in
    the owner's canonical instant form. `handoff(..., resolved=True)` asserts this
    mirror against the owner's own preflight so it cannot drift unnoticed.
    """
    if not _sha256(parent_reservation_spec_sha256):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'An allocation intent digest binds the parent reservation spec digest',
                '$.addresses.allocation_intent')
    spec = dict(document['spec'])
    spec['parent_reservation_spec_sha256'] = parent_reservation_spec_sha256
    spec['hold_expires_at'] = _owner_instant(hold_expires_at or spec['hold_expires_at'],
                                             'hold_expires_at')
    return repository.canonical_record_digest(spec)


def registration_intent_digest(document: dict, *, ipam_confirmation_sha256: str,
                               valid_until: str | None = None) -> str:
    """The owner's own canonical digest of one compiled DNS registration intent.

    Mirrors the declared DNS normalization: the declared spec keys, the confirmed
    allocation digest, sorted record types and observation classes, and the validity
    in the owner's canonical instant form.
    """
    if not _sha256(ipam_confirmation_sha256):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A registration intent digest binds the confirmed allocation digest',
                '$.addresses.registration_intent')
    spec = dict(document['spec'])
    spec['ipam_confirmation_sha256'] = ipam_confirmation_sha256
    spec['valid_until'] = _owner_instant(valid_until or spec['valid_until'], 'valid_until')
    spec['record_types'] = sorted(spec['record_types'])
    spec['required_observations'] = sorted(spec['required_observations'])
    return repository.canonical_dns_intent_digest(spec)


def reservation_intent(plan, capacity_document: dict, *, as_of: datetime,
                       capacity_request_ref: str = CAPACITY_REQUEST_REF) -> dict:
    """Compile the parent capacity reservation the addressing chain depends on."""
    declared = contracts()['reservation_intent']
    as_of = _instant(as_of)
    return {
        'format': declared['format'],
        'status': declared['status'],
        'production_authority': declared['authority'],
        'spec': {
            'reservation_id': reservation_id_for(plan),
            'operation_id': reservation_id_for(plan),
            'generation': plan.generation,
            'request_id': capacity_document['request_id'],
            'wsd_engineering_ref': ENGINEERING_REF,
            'envelope_id': f'{plan.operation_id}-envelope',
            'capacity_request_ref': capacity_request_ref,
            'expires_at': _expiry(as_of),
            'owners': {'reservation_owner_role': OWNER_ROLES['reservation_owner_role'],
                       'capacity_owner_role': OWNER_ROLES['capacity_owner_role'],
                       'service_owner_role': OWNER_ROLES['service_owner_role']},
            'resources': [
                {'id': demand['id'], 'unit': demand['unit'], 'quantity': demand['quantity'],
                 'owner_role': OWNER_ROLES[DEMAND_OWNER_ROLES[demand['id']]]}
                for demand in capacity_document['capacity_demands']
            ],
            'dependency_handoffs': [
                {'kind': 'ipam',
                 'owner_role': OWNER_ROLES['ipam_owner_role'],
                 'operation_id': allocation_operation_id_for(plan, domain['zone'])}
                for domain in domains(plan)
            ],
        },
        'source_refs': source_refs(plan),
    }


def validate_reservation_intent(intent: dict, capacity_document: dict, *, as_of: datetime) -> dict:
    """Check a compiled reservation intent against the owner's declared contract.

    The owner's own preflight resolves the declared `capacity_request_ref` from the
    checkout, so the full contract is applied by `repository.reservation_intent_spec`
    once the compiled chain is staged. Until then this applies the same declared key
    sets, the same resource-to-demand equality and the same expiry rule without
    resolving a sibling document that does not exist yet.
    """
    declared = contracts()['reservation_intent']
    as_of = _instant(as_of)
    if not isinstance(intent, dict) or set(intent) != set(declared['keys']):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A reservation intent carries exactly the declared keys',
                '$.addresses.reservation_intent',
                keys=sorted(intent) if isinstance(intent, dict) else None)
    if intent['format'] != declared['format'] or intent['status'] != declared['status']:
        _refuse('SCHEMA_VALIDATION_FAILED',
                'Unsupported reservation intent format or authority boundary',
                '$.addresses.reservation_intent')
    if intent['production_authority'] != declared['authority']:
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A compiled reservation intent cannot carry production authority',
                '$.addresses.reservation_intent')
    spec = intent['spec']
    if not isinstance(spec, dict) or set(spec) != set(declared['spec_keys']):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'Reservation intent fields are incomplete or unexpected',
                '$.addresses.reservation_intent.spec',
                keys=sorted(spec) if isinstance(spec, dict) else None)
    for key in ('reservation_id', 'operation_id', 'request_id', 'envelope_id'):
        if not _identifier(spec[key]):
            _refuse('SCHEMA_VALIDATION_FAILED',
                    f'A reservation intent {key} is a scoped identifier',
                    '$.addresses.reservation_intent.spec', key=key, value=spec[key])
    if not _positive_int(spec['generation']):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A reservation intent generation is a positive integer',
                '$.addresses.reservation_intent.spec')
    if spec['request_id'] != capacity_document['request_id']:
        _refuse('SEMANTIC_INCONSISTENT',
                'A reservation intent and its capacity request share one request identity',
                '$.addresses.reservation_intent.spec.request_id',
                intent=spec['request_id'], request=capacity_document['request_id'])
    if spec['wsd_engineering_ref'] != capacity_document['wsd_engineering_ref']:
        _refuse('SEMANTIC_INCONSISTENT',
                'A reservation intent and its capacity request share one engineering reference',
                '$.addresses.reservation_intent.spec.wsd_engineering_ref')
    if not isinstance(spec['capacity_request_ref'], str) or not spec['capacity_request_ref']:
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A reservation intent declares the capacity request it was compiled with',
                '$.addresses.reservation_intent.spec.capacity_request_ref')
    try:
        expires = repository.instant(spec['expires_at'], 'expires_at')
    except ValueError as exc:
        _refuse('SCHEMA_VALIDATION_FAILED', str(exc),
                '$.addresses.reservation_intent.spec.expires_at')
    if expires <= as_of:
        _refuse('SEMANTIC_INCONSISTENT',
                'A compiled reservation intent must stay valid past its handoff instant',
                '$.addresses.reservation_intent.spec.expires_at')
    owners = spec['owners']
    if not isinstance(owners, dict) or set(owners) != set(declared['owner_keys']):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'Exact reservation owner roles are required',
                '$.addresses.reservation_intent.spec.owners')
    for key in declared['owner_keys']:
        if not isinstance(owners[key], str) or not owners[key].strip():
            _refuse('SCHEMA_VALIDATION_FAILED',
                    f'A reservation owner role {key} is bounded text',
                    '$.addresses.reservation_intent.spec.owners', key=key)
    resources = spec['resources']
    if not isinstance(resources, list) or not resources:
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A reservation intent declares at least one resource',
                '$.addresses.reservation_intent.spec.resources')
    declared_map = {demand['id']: (demand['unit'], demand['quantity'])
                    for demand in capacity_document['capacity_demands']}
    actual_map = {}
    for resource in resources:
        if not isinstance(resource, dict) or set(resource) != set(declared['resource_keys']):
            _refuse('SCHEMA_VALIDATION_FAILED',
                    'A reservation resource carries exactly the declared keys',
                    '$.addresses.reservation_intent.spec.resources')
        if not _identifier(resource['id']) or resource['id'] in actual_map:
            _refuse('SCHEMA_VALIDATION_FAILED',
                    'Reservation resource identities are unique identifiers',
                    '$.addresses.reservation_intent.spec.resources', resource=resource['id'])
        if not isinstance(resource['unit'], str) or not resource['unit'].strip():
            _refuse('SCHEMA_VALIDATION_FAILED',
                    'A reservation resource unit is bounded text',
                    '$.addresses.reservation_intent.spec.resources')
        if not isinstance(resource['quantity'], str) or not resource['quantity']:
            _refuse('SCHEMA_VALIDATION_FAILED',
                    'A reservation resource quantity is a decimal string',
                    '$.addresses.reservation_intent.spec.resources')
        if not isinstance(resource['owner_role'], str) or not resource['owner_role'].strip():
            _refuse('SCHEMA_VALIDATION_FAILED',
                    'A reservation resource names its owner role',
                    '$.addresses.reservation_intent.spec.resources')
        actual_map[resource['id']] = (resource['unit'], resource['quantity'])
    if actual_map != declared_map:
        _refuse('SEMANTIC_INCONSISTENT',
                'Reservation resources must mirror the capacity request demand exactly',
                '$.addresses.reservation_intent.spec.resources',
                resources=actual_map, demands=declared_map)
    handoffs = spec['dependency_handoffs']
    if not isinstance(handoffs, list) or not handoffs:
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A reservation intent declares its dependent owner handoffs',
                '$.addresses.reservation_intent.spec.dependency_handoffs')
    operations = set()
    for handoff in handoffs:
        if not isinstance(handoff, dict) or set(handoff) != set(declared['dependency_keys']):
            _refuse('SCHEMA_VALIDATION_FAILED',
                    'A reservation dependency carries exactly the declared keys',
                    '$.addresses.reservation_intent.spec.dependency_handoffs')
        if handoff['kind'] != 'ipam':
            _refuse('SCHEMA_VALIDATION_FAILED',
                    'A compiled reservation dependency is an IPAM handoff',
                    '$.addresses.reservation_intent.spec.dependency_handoffs',
                    kind=handoff['kind'])
        if not _identifier(handoff['operation_id']) or handoff['operation_id'] in operations:
            _refuse('SCHEMA_VALIDATION_FAILED',
                    'Reservation dependency operations are unique identifiers',
                    '$.addresses.reservation_intent.spec.dependency_handoffs')
        operations.add(handoff['operation_id'])
        if not isinstance(handoff['owner_role'], str) or not handoff['owner_role'].strip():
            _refuse('SCHEMA_VALIDATION_FAILED',
                    'A reservation dependency names its owner role',
                    '$.addresses.reservation_intent.spec.dependency_handoffs')
    return intent


def allocation_intent(plan, domain: dict, *, as_of: datetime,
                      reservation_intent_ref: str = RESERVATION_INTENT_REF) -> dict:
    """Compile the authoritative IPAM allocation intent of one zone."""
    declared = contracts()['allocation_intent']
    as_of = _instant(as_of)
    document = {
        'format': declared['format'],
        'status': declared['status'],
        'production_authority': declared['authority'],
        'spec': {
            'allocation_id': allocation_id_for(plan, domain['zone']),
            'operation_id': allocation_operation_id_for(plan, domain['zone']),
            'generation': plan.generation,
            'reservation_id': reservation_id_for(plan),
            'request_id': request_id_for(plan),
            'wsd_engineering_ref': ENGINEERING_REF,
            'reservation_intent_ref': reservation_intent_ref,
            'allocation_policy': ALLOCATION_POLICY,
            'overlap_exception_ref': None,
            'family': domain['family'],
            'allocation_kind': domain['allocation_kind'],
            'requested_prefix_length': domain['prefix_length'],
            'delegated_scope_ref': f'controlled-ipam-scope:{domain["pool"]}',
            'hold_expires_at': _expiry(as_of),
            'owners': {'ipam_owner_role': OWNER_ROLES['ipam_owner_role'],
                       'network_owner_role': OWNER_ROLES['network_owner_role'],
                       'service_owner_role': OWNER_ROLES['service_owner_role']},
        },
        'source_refs': source_refs(plan),
    }
    return validate_allocation_intent(document)


def validate_allocation_intent(document: dict) -> dict:
    """Check a compiled IPAM intent against the owner's declared contract."""
    declared = contracts()['allocation_intent']
    if not isinstance(document, dict) or set(document) != set(declared['keys']):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'An IPAM allocation intent carries exactly the declared keys',
                '$.addresses.allocation_intent',
                keys=sorted(document) if isinstance(document, dict) else None)
    if document['format'] != declared['format'] or document['status'] != declared['status']:
        _refuse('SCHEMA_VALIDATION_FAILED',
                'Unsupported IPAM allocation intent format or authority boundary',
                '$.addresses.allocation_intent')
    if document['production_authority'] != declared['authority']:
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A compiled IPAM intent cannot carry production authority',
                '$.addresses.allocation_intent')
    spec = document['spec']
    if not isinstance(spec, dict) or set(spec) != set(declared['spec_keys']):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'IPAM allocation intent fields are incomplete or unexpected',
                '$.addresses.allocation_intent.spec',
                keys=sorted(spec) if isinstance(spec, dict) else None)
    for key in ('allocation_id', 'operation_id', 'reservation_id', 'request_id'):
        if not _identifier(spec[key]):
            _refuse('SCHEMA_VALIDATION_FAILED',
                    f'An IPAM intent {key} is a scoped identifier',
                    '$.addresses.allocation_intent.spec', key=key, value=spec[key])
    if not _positive_int(spec['generation']):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'An IPAM intent generation is a positive integer',
                '$.addresses.allocation_intent.spec')
    if spec['allocation_policy'] not in declared['policies']:
        _refuse('SCHEMA_VALIDATION_FAILED',
                f'Unknown allocation policy {spec["allocation_policy"]!r}',
                '$.addresses.allocation_intent.spec.allocation_policy')
    if spec['allocation_policy'] == 'UNIQUE_DEFAULT':
        if spec['overlap_exception_ref'] is not None:
            _refuse('SCHEMA_VALIDATION_FAILED',
                    'A unique-default allocation cannot carry an overlap exception',
                    '$.addresses.allocation_intent.spec.overlap_exception_ref')
    elif not isinstance(spec['overlap_exception_ref'], str) or not spec['overlap_exception_ref']:
        _refuse('SCHEMA_VALIDATION_FAILED',
                'An overlap allocation requires an explicit exception reference',
                '$.addresses.allocation_intent.spec.overlap_exception_ref')
    if spec['family'] not in declared['families'] or spec['allocation_kind'] not in declared['kinds']:
        _refuse('SCHEMA_VALIDATION_FAILED',
                'Unknown address family or allocation kind',
                '$.addresses.allocation_intent.spec')
    repository.allocation_prefix_shape(spec['family'], spec['allocation_kind'],
                                       spec['requested_prefix_length'])
    repository.opaque_external_ref(spec['delegated_scope_ref'], 'delegated_scope_ref')
    if not isinstance(spec['reservation_intent_ref'], str) or not spec['reservation_intent_ref']:
        _refuse('SCHEMA_VALIDATION_FAILED',
                'An IPAM intent declares the parent reservation intent it was compiled with',
                '$.addresses.allocation_intent.spec.reservation_intent_ref')
    owners = spec['owners']
    if not isinstance(owners, dict) or set(owners) != set(declared['owner_keys']):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'Exact IPAM owner roles are required',
                '$.addresses.allocation_intent.spec.owners')
    for key in declared['owner_keys']:
        if not isinstance(owners[key], str) or not owners[key].strip():
            _refuse('SCHEMA_VALIDATION_FAILED',
                    f'An IPAM owner role {key} is bounded text',
                    '$.addresses.allocation_intent.spec.owners', key=key)
    return document


def registration_intent(plan, domain: dict, *, as_of: datetime) -> dict:
    """Compile the DNS registration intent of one zone.

    Registration is compiled only against the allocation identity the reviewed plan
    binds. It carries no literal name and no literal address: the authoritative
    owner holds those, and the owner's own preflight refuses to evaluate the intent
    until the bound allocation is confirmed.
    """
    declared = contracts()['registration_intent']
    as_of = _instant(as_of)
    forward = FORWARD_RECORD_TYPE.get(domain['family'])
    if forward is None:
        _refuse('UNSUPPORTED_FEATURE',
                f'Address family {domain["family"]!r} has no declared forward record type',
                '$.addresses.registration_intent.family')
    document = {
        'format': declared['format'],
        'status': declared['status'],
        'production_authority': declared['authority'],
        'spec': {
            'registration_id': registration_id_for(plan, domain['zone']),
            'operation_id': registration_operation_id_for(plan, domain['zone']),
            'generation': plan.generation,
            'reservation_id': reservation_id_for(plan),
            'request_id': request_id_for(plan),
            'wsd_engineering_ref': ENGINEERING_REF,
            'ipam_allocation_id': allocation_id_for(plan, domain['zone']),
            'name_assignment_ref': f'controlled-name:{plan.operation_id}-{domain["zone"].lower()}',
            'record_types': [forward, REVERSE_RECORD_TYPE],
            'forward_zone_ref': f'controlled-zone:{domain["pool"]}-forward',
            'reverse_zone_ref': f'controlled-zone:{domain["pool"]}-reverse',
            'ttl_profile_ref': 'controlled-ttl:reviewed-default',
            'required_observations': list(REQUIRED_OBSERVATIONS),
            'valid_until': _expiry(as_of),
            'owners': {'dns_owner_role': OWNER_ROLES['dns_owner_role'],
                       'ipam_owner_role': OWNER_ROLES['ipam_owner_role'],
                       'service_owner_role': OWNER_ROLES['service_owner_role']},
        },
        'source_refs': source_refs(plan),
    }
    repository.dns_registration_spec(document, as_of=as_of)
    return document


def handoff(plan, *, as_of: datetime | None = None,
            capacity_request_ref: str = CAPACITY_REQUEST_REF,
            reservation_intent_ref: str = RESERVATION_INTENT_REF,
            resolved: bool = False) -> dict:
    """Compile and bind the whole reviewed addressing chain for one operation.

    `resolved=True` additionally runs the owners' own preflights, which resolve the
    declared sibling documents from the checkout. It is the handover check the
    operator runs once the compiled chain is staged; the default validates the same
    declared vocabulary without requiring a document that has not been staged yet.
    """
    as_of = _instant(as_of or datetime.now(timezone.utc))
    capacity_document = capacity_request(plan)
    reservation_document = reservation_intent(
        plan, capacity_document, as_of=as_of, capacity_request_ref=capacity_request_ref)
    validate_reservation_intent(reservation_document, capacity_document, as_of=as_of)
    allocations = []
    registrations = []
    for domain in domains(plan):
        allocation_document = allocation_intent(
            plan, domain, as_of=as_of, reservation_intent_ref=reservation_intent_ref)
        allocations.append(allocation_document)
        registrations.append(registration_intent(plan, domain, as_of=as_of))
    if resolved:
        repository.reservation_intent_spec(reservation_document, capacity_document, as_of=as_of)
        envelope = _staged_envelope(plan)
        for document in allocations:
            preflight = repository.ipam_allocation_preflight(document, as_of=as_of)
            spec = repository.ipam_allocation_spec(
                document, as_of=as_of, parent_envelope_record_sha256=envelope)
            mirrored = allocation_intent_digest(
                document,
                parent_reservation_spec_sha256=spec['parent_reservation_spec_sha256'],
                hold_expires_at=spec['hold_expires_at'])
            if mirrored != preflight['intent_sha256']:
                _refuse('IPAM_ALLOCATION_CONFLICT',
                        'The owner normalizes this allocation intent differently',
                        '$.addresses.handoff', allocation_id=document['spec']['allocation_id'])
        for document in registrations:
            preflight = repository.dns_registration_preflight(document, as_of=as_of)
            confirmed = preflight['ipam_confirmation_sha256']
            if confirmed is None:
                continue
            spec = repository.dns_registration_spec(
                document, as_of=as_of, ipam_confirmation_sha256=confirmed)
            mirrored = registration_intent_digest(
                document, ipam_confirmation_sha256=confirmed, valid_until=spec['valid_until'])
            if mirrored != preflight['intent_sha256']:
                _refuse('DNS_REGISTRATION_CONFLICT',
                        'The owner normalizes this registration intent differently',
                        '$.addresses.handoff',
                        registration_id=document['spec']['registration_id'])
    return validate_handoff({
        'format': HANDOFF_FORMAT,
        'operation_id': plan.operation_id,
        'generation': plan.generation,
        'scope': scope_of(plan),
        'plan_digest': plan.digest,
        'view_digest': view_digest(plan),
        'reservation_id': reservation_id_for(plan),
        'request_id': request_id_for(plan),
        'as_of': as_of.isoformat(),
        'capacity_request': capacity_document,
        'reservation_intent': reservation_document,
        'allocations': allocations,
        'registrations': registrations,
        'digests': {
            'capacity_request': digest(capacity_document),
            'reservation_intent': repository.canonical_record_digest(
                reservation_document['spec']),
            'allocations': [digest(document) for document in allocations],
            'registrations': [repository.canonical_dns_intent_digest(
                repository.dns_registration_spec(document, as_of=as_of))
                for document in registrations],
        },
        'staged': {'capacity_request_ref': capacity_request_ref,
                   'reservation_intent_ref': reservation_intent_ref},
        'limits': list(LIMITS),
    })


def validate_handoff(document: dict) -> dict:
    """Refuse a compiled handoff that does not carry exactly the declared shape."""
    if not isinstance(document, dict) or set(document) != HANDOFF_KEYS:
        _refuse('SCHEMA_VALIDATION_FAILED',
                'An address handoff carries exactly the declared keys',
                '$.addresses.handoff',
                keys=sorted(document) if isinstance(document, dict) else None)
    if document['format'] != HANDOFF_FORMAT:
        _refuse('SCHEMA_VALIDATION_FAILED',
                f'Unknown address handoff format {document["format"]!r}', '$.addresses.handoff')
    if not _identifier(document['operation_id']):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'An address handoff operation is a scoped identifier', '$.addresses.handoff')
    if not _positive_int(document['generation']):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'An address handoff generation is a positive integer', '$.addresses.handoff')
    if not _sha256(document['plan_digest']) or not _sha256(document['view_digest']):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'An address handoff cites the reviewed plan and the addressing view',
                '$.addresses.handoff')
    scope = document['scope']
    if not isinstance(scope, dict) or set(scope) != set(SCOPE_KEYS):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'An address handoff carries exactly the declared scope keys',
                '$.addresses.handoff.scope')
    for key in ('allocations', 'registrations'):
        if not isinstance(document[key], list) or not document[key]:
            _refuse('SCHEMA_VALIDATION_FAILED',
                    f'An address handoff declares at least one {key} document',
                    '$.addresses.handoff', key=key)
    if len(document['allocations']) != len(document['registrations']):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'Every compiled allocation is accompanied by its registration',
                '$.addresses.handoff')
    return document


def _staged_reservation(plan, capacity_document: dict, as_of: datetime) -> dict:
    """The reservation intent the owner was handed, if the chain has been staged.

    The parent digest is the owner's digest of the intent it was given, so it can only
    be recomputed from that same intent. Reading the staged document is what makes the
    binding a comparison against the reviewed operation rather than against whatever
    instant reconciliation happens to run at. The compiled intent is the fallback for
    the case where nothing has been staged, which is also the case where the owner
    cannot have recorded anything yet.
    """
    staged = reservation_intent(plan, capacity_document, as_of=as_of)
    if not repository.document_exists(RESERVATION_INTENT_REF):
        return staged
    document = repository.repository_document(RESERVATION_INTENT_REF)
    if (isinstance(document, dict)
            and document.get('operation_id') == plan.operation_id
            and document.get('generation') == plan.generation):
        return document
    return staged


def _staged_envelope(plan) -> str | None:
    """The envelope digest the authoritative reservation record accepted, if any.

    The owner's IPAM preflight resolves the parent reservation from the checkout and
    takes the envelope digest from the exported reservation record, so the mirror of
    the owner's normalization has to be computed with the same envelope digest.
    """
    index = repository.reservation_records()
    for record in index.get('records', []):
        if record.get('reservation_id') == reservation_id_for(plan):
            return record.get('envelope_record_sha256')
    return None


def _index_paths(reservation_index, allocation_index, registration_index):
    """The exported owner evidence, loaded through the repository's own readers."""
    return (repository.reservation_records(reservation_index),
            repository.ipam_allocation_records(allocation_index),
            repository.dns_registration_records(registration_index))


def reconcile(plan, *, reservation_index=None, allocation_index=None,
              registration_index=None, as_of: datetime | None = None) -> dict:
    """Classify the reviewed addressing proposal against exported owner evidence.

    Nothing is created and nothing is guessed. A missing record is reported as an
    intent that is ready for the owner to execute, an unreadable or mismatched record
    is a hold, and an unknown outcome is a reconciliation request rather than a
    second allocation attempt.
    """
    _assert_declared()
    as_of = _instant(as_of or datetime.now(timezone.utc))
    capacity_document = capacity_request(plan)
    reservation_document = _staged_reservation(plan, capacity_document, as_of)
    try:
        paths = _index_paths(reservation_index, allocation_index, registration_index)
        reservation_summary = repository.validate_reservation_records(paths[0], as_of=as_of)
        allocation_summary = repository.validate_ipam_allocation_records(paths[1], as_of=as_of)
        registration_summary = repository.validate_dns_registration_records(
            paths[2], ipam_index=paths[1], as_of=as_of)
    except (ValueError, OSError, TypeError, KeyError, json.JSONDecodeError) as exc:
        _refuse('SCHEMA_VALIDATION_FAILED',
                f'The exported owner records are invalid: {exc}',
                '$.addresses.records')
    reservations = {record['reservation_id']: record
                    for record in reservation_summary['records']}
    allocations = {record['allocation_id']: record
                   for record in allocation_summary['records']}
    registrations = {record['registration_id']: record
                     for record in registration_summary['records']}
    parent = reservations.get(reservation_id_for(plan))
    parent_state, parent_sha256 = _parent_state(plan, parent, capacity_document,
                                                reservation_document, as_of)
    results = []
    for domain in domains(plan):
        results.append(_reconcile_zone(plan, domain, parent_state, parent_sha256, parent,
                                       allocations, registrations, as_of))
    confirmed = all(item['confirmed'] for item in results)
    registered = all(item['registered'] for item in results)
    refusing = any(item['state'] in REFUSING_ALLOCATION_STATES
                   or item['registration_state'] in REFUSING_REGISTRATION_STATES
                   for item in results)
    return {
        'format': RECONCILIATION_FORMAT,
        'operation_id': plan.operation_id,
        'generation': plan.generation,
        'reservation_id': reservation_id_for(plan),
        'view_digest': view_digest(plan),
        'parent': {'reservation_id': reservation_id_for(plan), 'state': parent_state,
                   'record_present': parent is not None,
                   'spec_sha256': parent_sha256,
                   'expires_at': parent['expires_at'] if parent is not None else None},
        'allocations': results,
        'state': 'CONFIRMED' if confirmed else ('REFUSED' if refusing else 'PENDING_OWNER'),
        'confirmed': confirmed,
        'registered': registered,
        'may_allocate': all(item['may_allocate'] for item in results),
        'may_register': confirmed and not refusing and all(item['may_register'] for item in results),
        'records_checked': (reservation_summary['record_count']
                            + allocation_summary['record_count']
                            + registration_summary['record_count']),
        'limits': list(LIMITS),
    }


def _parent_state(plan, parent: dict | None, capacity_document: dict,
                  reservation_document: dict, as_of: datetime) -> tuple[str, str | None]:
    """Reconcile the parent reservation and return the digest the owner recorded.

    The digest is the owner's own digest of the intent it was handed. Recomputing it
    from the reviewed intent binds the authoritative reservation to this operation's
    identity, resources, dependency handoffs and capacity request, and a divergence is
    a conflict rather than a silently adopted reservation.
    """
    if parent is None:
        return 'ABSENT', None
    expected = parent_spec_sha256(plan, parent, capacity_document, reservation_document,
                                  as_of=as_of)
    if expected != parent['spec_sha256']:
        return 'CONFLICT', None
    if parent['state'] == 'UNCERTAIN':
        return 'UNRESOLVED', parent['spec_sha256']
    if parent['state'] != 'HELD':
        return 'NOT_HELD', parent['spec_sha256']
    return 'HELD', parent['spec_sha256']


def _reconcile_zone(plan, domain: dict, parent_state: str, parent_sha256: str | None,
                    parent: dict | None, allocations: dict, registrations: dict,
                    as_of: datetime) -> dict:
    """Classify one zone's allocation and its dependent registration."""
    allocation_id = allocation_id_for(plan, domain['zone'])
    registration_id = registration_id_for(plan, domain['zone'])
    record = allocations.get(allocation_id)
    registration = registrations.get(registration_id)
    reasons: list[str] = []
    state = READY
    intent_sha256 = None
    if parent_sha256 is not None:
        intent_sha256 = allocation_intent_digest(
            allocation_intent(plan, domain, as_of=as_of),
            parent_reservation_spec_sha256=parent_sha256,
            hold_expires_at=parent['expires_at'])
    if parent_state == 'CONFLICT':
        state = HOLD_CONFLICT
        reasons.append('The parent capacity reservation carries a different reviewed identity')
    elif parent_state == 'UNRESOLVED':
        state = HOLD_UNCERTAIN
        reasons.append('The parent capacity reservation outcome is unknown')
    elif parent_state != 'HELD':
        state = HOLD_PARENT
        reasons.append('The parent capacity reservation is not held')
    elif record is None:
        state = READY
    elif record['unresolved']:
        state = HOLD_UNCERTAIN
        reasons.append('The authoritative allocation outcome is unknown')
    elif not _same_allocation_scope(plan, domain, record, intent_sha256):
        state = HOLD_CONFLICT
        reasons.append('The authoritative allocation carries a different reviewed identity')
    elif record['state'] == 'RESERVED':
        state = EXISTING_RESERVED
    elif record['state'] == 'CONFIRMED':
        state = EXISTING_CONFIRMED
    else:
        state = HOLD_TERMINAL
        reasons.append(f'The authoritative allocation is in state {record["state"]}')
    registration_sha256 = None
    if (record is not None and record['confirmation_sha256'] is not None
            and parent is not None):
        registration_sha256 = registration_intent_digest(
            registration_intent(plan, domain, as_of=as_of),
            ipam_confirmation_sha256=record['confirmation_sha256'],
            valid_until=parent['expires_at'])
    registration_state = _registration_state(plan, domain, state, registration, reasons,
                                            registration_sha256)
    if (record is not None and record['state'] in REUSABLE_RECORD_STATES
            and registration is not None and registration['state'] in LIVE_REGISTRATION_STATES
            and state not in (HOLD_PARENT, HOLD_CONFLICT, HOLD_UNCERTAIN)):
        state = HOLD_RELEASE
        reasons.append('Addressing was released while its DNS registration is still live')
    confirmed = state == EXISTING_CONFIRMED
    registered = registration_state == REGISTRATION_EXISTING
    return {
        'allocation_id': allocation_id,
        'registration_id': registration_id,
        'zone': domain['zone'],
        'domain': domain['domain'],
        'pool': domain['pool'],
        'state': state,
        'registration_state': registration_state,
        'record_state': record['state'] if record is not None else None,
        'registration_record_state': registration['state'] if registration is not None else None,
        'allocation_present': record is not None,
        'registration_present': registration is not None,
        'confirmed': confirmed,
        'registered': registered,
        'reusable': record is not None and record['state'] in REUSABLE_RECORD_STATES,
        'cleanup_complete': (all(item['status'] in ('COMPLETE', 'NOT_APPLICABLE')
                                 for item in record['cleanup'].values())
                             if record is not None else False),
        'next_owner_action': _next_action(state, registration_state),
        'may_allocate': state in ALLOCATION_READY_STATES,
        'may_register': confirmed and registration_state not in REFUSING_REGISTRATION_STATES,
        'reasons': reasons,
    }


def _same_allocation_scope(plan, domain: dict, record: dict, intent_sha256: str | None) -> bool:
    """Whether an authoritative allocation carries this plan's reviewed identity."""
    if record['generation'] != plan.generation:
        return False
    if record['reservation_id'] != reservation_id_for(plan):
        return False
    if record['request_id'] != request_id_for(plan):
        return False
    if record['family'] != domain['family'] or record['allocation_kind'] != domain['allocation_kind']:
        return False
    if record['requested_prefix_length'] != domain['prefix_length']:
        return False
    if record['delegated_scope_ref'] != f'controlled-ipam-scope:{domain["pool"]}':
        return False
    if intent_sha256 is not None and record['intent_sha256'] != intent_sha256:
        return False
    return True


def _registration_state(plan, domain: dict, allocation_state: str, registration: dict | None,
                        reasons: list[str], intent_sha256: str | None = None) -> str:
    """Classify one zone's DNS registration against its authoritative allocation."""
    if registration is None:
        if allocation_state != EXISTING_CONFIRMED:
            reasons.append('DNS registration waits for a confirmed authoritative allocation')
            return REGISTRATION_HOLD_IPAM
        return REGISTRATION_READY
    if registration['unresolved']:
        reasons.append('The authoritative DNS outcome is unknown')
        return REGISTRATION_HOLD_UNCERTAIN
    if (registration['generation'] != plan.generation
            or registration['reservation_id'] != reservation_id_for(plan)
            or registration['request_id'] != request_id_for(plan)):
        reasons.append('The authoritative registration carries a different reviewed identity')
        return REGISTRATION_HOLD_CONFLICT
    if intent_sha256 is not None and registration['intent_sha256'] != intent_sha256:
        reasons.append('The authoritative registration carries a different normalized DNS intent')
        return REGISTRATION_HOLD_CONFLICT
    if registration['state'] == 'REGISTERED':
        if allocation_state != EXISTING_CONFIRMED:
            reasons.append('A registered name cannot outlive its confirmed allocation')
            return REGISTRATION_HOLD_IPAM
        return REGISTRATION_EXISTING
    if registration['state'] in ('RELEASE_PENDING', 'TOMBSTONED'):
        return REGISTRATION_HOLD_RELEASE
    if registration['state'] == 'RELEASED':
        return REGISTRATION_READY
    return REGISTRATION_HOLD_TERMINAL


def _next_action(state: str, registration_state: str) -> str:
    if state in (READY, EXISTING_RESERVED):
        return 'OWNER_RESERVE_THEN_CONFIRM_ALLOCATION'
    if state == HOLD_PARENT:
        return 'OWNER_HOLD_PARENT_CAPACITY_RESERVATION_FIRST'
    if state == HOLD_CONFLICT:
        return 'REVIEWER_RECONCILE_ALLOCATION_IDENTITY'
    if state == HOLD_UNCERTAIN:
        return 'OWNER_DISCOVER_AUTHORITATIVE_OUTCOME'
    if state == HOLD_RELEASE:
        return 'OWNER_WITHDRAW_DEPENDENT_DNS_BEFORE_ADDRESS_REUSE'
    if state == HOLD_TERMINAL:
        return 'REVIEWER_OPEN_A_NEW_ALLOCATION_OPERATION'
    if registration_state in (REGISTRATION_READY, REGISTRATION_HOLD_IPAM):
        return 'OWNER_REGISTER_NAME_THEN_OBSERVE'
    if registration_state == REGISTRATION_EXISTING:
        return 'NONE_ALLOCATION_AND_REGISTRATION_CONFIRMED'
    return 'REVIEWER_RECONCILE_REGISTRATION_IDENTITY'


def review(reconciliation: dict) -> dict:
    """The reviewer-facing summary of one addressing reconciliation."""
    return {'format': RECONCILIATION_FORMAT,
            'state': reconciliation['state'],
            'confirmed': reconciliation['confirmed'],
            'registered': reconciliation['registered'],
            'operation_id': reconciliation['operation_id'],
            'generation': reconciliation['generation'],
            'reservation_id': reconciliation['reservation_id'],
            'view_digest': reconciliation['view_digest'],
            'parent_state': reconciliation['parent']['state'],
            'zones': [{'zone': item['zone'], 'state': item['state'],
                       'registration_state': item['registration_state'],
                       'next_owner_action': item['next_owner_action']}
                      for item in reconciliation['allocations']],
            'records_checked': reconciliation['records_checked'],
            'may_allocate': reconciliation['may_allocate'],
            'may_register': reconciliation['may_register'],
            'limits': list(reconciliation['limits'])}


def require_confirmed(reconciliation: dict, *, path: str = '$.addresses') -> dict:
    """Refuse to treat addressing as held until every allocation is confirmed."""
    _assert_declared()
    if not isinstance(reconciliation, dict) or reconciliation.get('format') != RECONCILIATION_FORMAT:
        _refuse('SCHEMA_VALIDATION_FAILED',
                'An addressing reconciliation is required', path)
    for item in reconciliation['allocations']:
        if item['state'] == HOLD_CONFLICT:
            _refuse(REFUSAL_CONFLICT,
                    f'Allocation {item["allocation_id"]} carries a conflicting identity',
                    path, allocation_id=item['allocation_id'], reasons=item['reasons'])
        if item['state'] == HOLD_UNCERTAIN:
            _refuse(REFUSAL_UNRESOLVED,
                    f'Allocation {item["allocation_id"]} has an unknown authoritative outcome',
                    path, allocation_id=item['allocation_id'], reasons=item['reasons'])
        if item['state'] in (HOLD_RELEASE, HOLD_TERMINAL):
            _refuse(REFUSAL_UNCONFIRMED,
                    f'Allocation {item["allocation_id"]} is not usable: {item["state"]}',
                    path, allocation_id=item['allocation_id'], reasons=item['reasons'])
        if not item['confirmed']:
            _refuse(REFUSAL_UNCONFIRMED,
                    f'Allocation {item["allocation_id"]} is not confirmed by the owner',
                    path, allocation_id=item['allocation_id'], state=item['state'],
                    reasons=item['reasons'])
    return reconciliation


def require_registered(reconciliation: dict, *, path: str = '$.addresses') -> dict:
    """Refuse to treat a name as registered until the owner confirms every registration."""
    _assert_declared()
    require_confirmed(reconciliation, path=path)
    for item in reconciliation['allocations']:
        state = item['registration_state']
        if state == REGISTRATION_HOLD_CONFLICT:
            _refuse(REGISTRATION_REFUSAL_CONFLICT,
                    f'Registration {item["registration_id"]} carries a conflicting identity',
                    path, registration_id=item['registration_id'], reasons=item['reasons'])
        if state == REGISTRATION_HOLD_UNCERTAIN:
            _refuse(REGISTRATION_REFUSAL_UNRESOLVED,
                    f'Registration {item["registration_id"]} has an unknown authoritative outcome',
                    path, registration_id=item['registration_id'], reasons=item['reasons'])
        if not item['registered']:
            _refuse(REGISTRATION_REFUSAL_UNCONFIRMED,
                    f'Registration {item["registration_id"]} is not confirmed by the owner',
                    path, registration_id=item['registration_id'], state=state,
                    reasons=item['reasons'])
    return reconciliation


def require_releasable(reconciliation: dict, *, path: str = '$.addresses') -> dict:
    """Refuse to release reusable addressing before dependent state is withdrawn.

    The authoritative IPAM record is the only authority on address ownership, and the
    exported DNS record is the only authority on the name that depended on it. A
    released or quarantined allocation whose registration is still live is an
    ordering violation: reusable addressing was handed back while a dependent name
    still resolved to it.
    """
    _assert_declared()
    if not isinstance(reconciliation, dict) or reconciliation.get('format') != RECONCILIATION_FORMAT:
        _refuse('SCHEMA_VALIDATION_FAILED',
                'An addressing reconciliation is required', path)
    for item in reconciliation['allocations']:
        record_state = item['record_state']
        if record_state not in REUSABLE_RECORD_STATES:
            continue
        registration_state = item['registration_record_state']
        if registration_state is not None and registration_state not in QUARANTINED_REGISTRATION_STATES:
            _refuse(REFUSAL_RELEASE_ORDER,
                    f'Allocation {item["allocation_id"]} was handed back for reuse while '
                    f'registration {item["registration_id"]} is still {registration_state}',
                    path, allocation_id=item['allocation_id'],
                    registration_id=item['registration_id'],
                    record_state=record_state, registration_state=registration_state)
        if not item['cleanup_complete']:
            _refuse(REFUSAL_RELEASE_ORDER,
                    f'Allocation {item["allocation_id"]} was handed back for reuse before every '
                    f'dependent cleanup was complete',
                    path, allocation_id=item['allocation_id'], record_state=record_state)
        if record_state == 'RELEASED' and registration_state is not None \
                and registration_state not in WITHDRAWN_REGISTRATION_STATES:
            _refuse(REFUSAL_RELEASE_ORDER,
                    f'Allocation {item["allocation_id"]} is released while registration '
                    f'{item["registration_id"]} is still {registration_state}',
                    path, allocation_id=item['allocation_id'],
                    registration_id=item['registration_id'],
                    record_state=record_state, registration_state=registration_state)
    return reconciliation


def require_settled(reconciliation: dict, *, path: str = '$.addresses') -> dict:
    """Refuse to hand over addressing whose authoritative outcome is unknown or spent."""
    _assert_declared()
    if not isinstance(reconciliation, dict) or reconciliation.get('format') != RECONCILIATION_FORMAT:
        _refuse('SCHEMA_VALIDATION_FAILED',
                'An addressing reconciliation is required', path)
    for item in reconciliation['allocations']:
        if item['state'] == HOLD_UNCERTAIN:
            _refuse(REFUSAL_UNRESOLVED,
                    f'Allocation {item["allocation_id"]} has an unknown authoritative outcome',
                    path, allocation_id=item['allocation_id'], reasons=item['reasons'])
        if item['state'] == HOLD_TERMINAL:
            _refuse(REFUSAL_UNCONFIRMED,
                    f'Allocation {item["allocation_id"]} requires a new operation',
                    path, allocation_id=item['allocation_id'], reasons=item['reasons'])
        if item['registration_state'] == REGISTRATION_HOLD_UNCERTAIN:
            _refuse(REGISTRATION_REFUSAL_UNRESOLVED,
                    f'Registration {item["registration_id"]} has an unknown authoritative outcome',
                    path, registration_id=item['registration_id'], reasons=item['reasons'])
    return reconciliation


def to_dict() -> dict:
    """The declared contract, for the documentation drift guard."""
    return {'view_format': VIEW_FORMAT, 'binding_format': BINDING_FORMAT,
            'handoff_format': HANDOFF_FORMAT,
            'reconciliation_format': RECONCILIATION_FORMAT,
            'registration_binding_format': REGISTRATION_BINDING_FORMAT,
            'proposal_authority': PROPOSAL_AUTHORITY,
            'engineering_ref': ENGINEERING_REF,
            'staging_root': STAGING_ROOT,
            'capacity_request_ref': CAPACITY_REQUEST_REF,
            'reservation_intent_ref': RESERVATION_INTENT_REF,
            'hold_horizon_seconds': int(HOLD_HORIZON.total_seconds()),
            'scope_keys': list(SCOPE_KEYS),
            'demand_units': dict(DEMAND_UNITS),
            'allocation_policy': ALLOCATION_POLICY,
            'required_observations': list(REQUIRED_OBSERVATIONS),
            'allocation_states': list(ALLOCATION_STATES),
            'registration_states': list(REGISTRATION_STATES),
            'refusing_allocation_states': sorted(REFUSING_ALLOCATION_STATES),
            'refusing_registration_states': sorted(REFUSING_REGISTRATION_STATES),
                        'refusal_by_state': {state: REFUSING_STATES[state]
                                             for state in sorted(REFUSING_STATES)},
                        'registration_refusal_by_state': {
                            state: REGISTRATION_REFUSING_STATES[state]
                            for state in sorted(REGISTRATION_REFUSING_STATES)},
            'refusal_codes': [REFUSAL_CONFLICT, REFUSAL_UNRESOLVED, REFUSAL_UNCONFIRMED,
                              REGISTRATION_REFUSAL_CONFLICT, REGISTRATION_REFUSAL_UNRESOLVED,
                              REGISTRATION_REFUSAL_UNCONFIRMED, REFUSAL_RELEASE_ORDER],
            'limits': list(LIMITS)}