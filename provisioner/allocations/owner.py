"""The capacity-owner handoff.

The portable plan decides what capacity one workload security domain needs, and it
refuses to place the WSD at all when the reviewed inventory cannot already hold the
demand. That arithmetic is a preflight. It is not a reservation, and this repository
never holds one: the authoritative capacity owner is a separate system with its own
record, and nothing here contacts it, writes to it or speaks for it.

What the repository can do is hand the reviewed decision over in the shape the
owner's existing machinery already accepts, and then report honestly what the
exported evidence says about it:

- `capacity_view()` is the exact commissioned capacity view the placement decision
  was taken against: the reviewed inventory identity, the site, the platform and,
  per zone, the selected cluster, its committed position, its headroom and the
  demand placed on it. It is bound into the reviewed manifest, so a capacity view
  that moved invalidates a stale reservation preflight instead of silently reserving
  against capacity that is already gone.
- `request()` compiles the reviewed demand into `hosting-capacity-request/1` — the
  exact request the repository's existing `tools/capacity.py` owner validates and the
  `capacity` step kind of the existing delivery runner stages. Units are converted
  into the owner's decimal accounting units and every workload is rounded upward, so
  a reservation may exceed the reviewed demand but can never undercharge it.
- `binding()` states the identity a reservation must carry to be *this* plan's
  reservation, and `handoff()` binds the view, the request and the envelope around
  it as one `hosting-capacity-owner-handoff/1` document.
- `reconcile()` reads the repository's existing exported reservation record index
  through the repository's existing checker and classifies the proposal against the
  authoritative records that actually exist. It never writes, never creates and
  never guesses.
- `require_confirmed()` is the gate downstream allocation must pass before it may
  treat capacity as held, `require_current()` refuses a stale view, `require_settled()`
  refuses to hand over a reservation whose authoritative outcome is unknown or
  already spent, and `require_exclusive()` refuses two operations that would each be
  admitted against the same view's free capacity.

Nothing here contacts an owner, mutates a record or holds authority.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from provisioner import repository
from provisioner.domain.errors import ProvisioningError
from provisioner.domain.generation import SCOPE_KEYS
from provisioner.domain.request import digest
from provisioner.placement.eligibility import PLATFORMS

#: The view of the commissioned capacity the placement decision was taken against.
VIEW_FORMAT = 'hosting-capacity-view/1'
#: The repository-side document an operator stages for the capacity owner.
HANDOFF_FORMAT = 'hosting-capacity-owner-handoff/1'
#: The identity a reservation must carry to be this plan's reservation.
BINDING_FORMAT = 'hosting-capacity-binding/1'
#: What the exported reservation records say about a proposal.
RECONCILIATION_FORMAT = 'hosting-capacity-reconciliation/1'
#: Mirrors `tools.capacity.REQUEST_FORMAT`, the declared owner contract.
REQUEST_FORMAT = 'hosting-capacity-request/1'
#: The recorded owner facts an operator supplies so a request can be compiled.
FACTS_FORMAT = 'hosting-capacity-owner-facts/1'

VIEW_KEYS = frozenset({'format', 'inventory', 'site', 'platform', 'zones', 'limits'})
VIEW_ZONE_KEYS = frozenset({'zone', 'cell', 'cluster', 'status', 'demand',
                            'committed_after', 'available'})
BINDING_KEYS = frozenset({'format', 'operation_id', 'generation', 'scope', 'plan_digest',
                          'view_digest', 'reservation_id', 'envelope'})
ENVELOPE_KEYS = frozenset({'id', 'record_sha256'})
REQUEST_KEYS = frozenset({'format', 'owner_id', 'reservation_id', 'operation_id',
                          'generation', 'scope', 'pool_id', 'units', 'capabilities'})

#: Mirrors `tools.readback_core.ID`, the declared identifier grammar.
IDENTIFIER = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$')
SHA256 = re.compile(r'^[0-9a-f]{64}$')

#: The accounting units the capacity owner holds. Mirrors `tools.capacity.UNITS`.
UNITS = ('vcpu', 'memory_mb', 'storage_gb')
#: Mirrors the owner's own accounting bound, so the mirror never accepts a request
#: the authoritative validator would refuse.
MAX_UNITS = 10 ** 15
#: Mirrors `tools.check_reservation_records.STATES` for the states this module reads.
RECORD_STATES = ('HELD', 'CONSUMED', 'RELEASED', 'EXPIRED', 'UNCERTAIN')

#: The reconciled states. None of them is "this repository holds capacity".
PROPOSED = 'PROPOSED_NOT_CONFIRMED'
CONFIRMED = 'CONFIRMED_BY_OWNER'
HOLD_ENVELOPE = 'HOLD_ENVELOPE_NOT_BOUND'
HOLD_CONFLICT = 'HOLD_RESERVATION_IDENTITY_OR_INTENT_CONFLICT'
HOLD_UNCERTAIN = 'HOLD_DISCOVER_RESERVATION_OUTCOME'
HOLD_TERMINAL = 'HOLD_TERMINAL_RESERVATION_NEW_OPERATION_REQUIRED'
EXISTING_CONSUMED = 'EXISTING_CONSUMED_RESERVATION'
STATES = (PROPOSED, CONFIRMED, HOLD_ENVELOPE, HOLD_CONFLICT, HOLD_UNCERTAIN,
          HOLD_TERMINAL, EXISTING_CONSUMED)

#: The refusal an authoritative answer can carry. A conflict is a definite no; an
#: unresolved outcome is an answer the owner has not given yet.
REFUSAL_CONFLICT = 'CAPACITY_RESERVATION_CONFLICT'
REFUSAL_UNRESOLVED = 'CAPACITY_RESERVATION_UNRESOLVED'

#: A state that must stop a handoff. Handing over a reservation whose authoritative
#: outcome is unknown, conflicted or already spent would let a downstream owner act
#: on capacity nobody holds.
REFUSING_STATES = {
    HOLD_CONFLICT: REFUSAL_CONFLICT,
    HOLD_UNCERTAIN: REFUSAL_UNRESOLVED,
    HOLD_TERMINAL: REFUSAL_CONFLICT,
    EXISTING_CONSUMED: REFUSAL_CONFLICT,
}

#: The external facts the repository cannot review. They are named, never invented.
REQUIRED_FACTS = ('owner_id', 'pool_id', 'capabilities', 'database', 'envelope_id',
                  'envelope_record_sha256')

GIB = 1024 ** 3
MEGABYTE = 10 ** 6
GIGABYTE = 10 ** 9

LIMITS = (
    'A compiled capacity request is a proposal; only the capacity owner holds a reservation',
    'The authoritative reservation system is external to this repository',
    'This module contacts no owner, writes no record and grants no capacity',
    'Native qualification and separate production approval remain required',
)


def _refuse(code: str, message: str, path: str, **details) -> None:
    raise ProvisioningError(code, message, path=path, details=details)


def _round_up(value: int, unit: int) -> int:
    whole, remainder = divmod(value, unit)
    return whole + 1 if remainder else whole


def memory_mb(memory_gib: int) -> int:
    """The owner accounts memory in decimal megabytes. Round up; never undercharge."""
    return _round_up(memory_gib * GIB, MEGABYTE)


def storage_gb(storage_gib: int) -> int:
    """The owner accounts storage in decimal gigabytes. Round up; never undercharge."""
    return _round_up(storage_gib * GIB, GIGABYTE)


def _headroom(gib: int, unit: int) -> int:
    """Headroom is rounded *down*, so a refusal is never lost to a rounding artifact."""
    return gib * GIB // unit


def scope_of(plan) -> dict:
    """The five-key scope every capacity document is bound to."""
    return {name: plan.identity.scope[name] for name in SCOPE_KEYS}


def reservation_id_for(plan) -> str:
    """The deterministic reservation identity of one reviewed operation."""
    return f'{plan.operation_id}-capacity'


def _reviewed_cluster(plan, domain):
    """The reviewed cluster a placed domain actually selected."""
    site = plan.inventory.site(plan.desired_state.site_key)
    for cell in site.cells:
        if cell.cell != domain.cell_key:
            continue
        for cluster in cell.clusters:
            if cluster.id == domain.cluster_id:
                return cluster
    _refuse('INVENTORY_INCOMPLETE',
            f'Placed cluster {domain.cluster_id} is absent from reviewed inventory',
            'inventory.sites',
            site=plan.desired_state.site_key, cell=domain.cell_key,
            cluster=domain.cluster_id)


def zone_units(domain) -> dict:
    """One zone's reviewed demand in the owner's decimal accounting units.

    Each workload is rounded up before the zone is summed, so the request can exceed
    the reviewed demand but can never undercharge it.
    """
    return {
        'vcpu': sum(workload.vcpu for workload in domain.workloads),
        'memory_mb': sum(memory_mb(workload.memory_gib) for workload in domain.workloads),
        'storage_gb': sum(storage_gb(workload.boot_disk_gib + workload.data_disk_gib)
                          for workload in domain.workloads),
    }


def units(plan) -> dict:
    """The whole reviewed demand of one operation, in the owner's accounting units."""
    totals = {unit: 0 for unit in UNITS}
    for domain in plan.desired_state.domains:
        for unit, value in zone_units(domain).items():
            totals[unit] += value
    return totals


def capacity_view(plan) -> dict:
    """The exact commissioned capacity view this placement decision used.

    A pure function of the reviewed decision and the reviewed inventory, so it can be
    bound into the manifest before the plan identity exists. It deliberately carries
    no generation: the commissioned capacity is what it is, and two generations of one
    WSD read the same capacity. The generation that claimed it belongs to the binding.
    """
    state = plan.desired_state
    inventory = plan.inventory
    if inventory is None:
        _refuse('INVENTORY_INCOMPLETE', 'A capacity view requires the reviewed inventory',
                'inventory')
    zones = []
    for domain in state.domains:
        reservation = state.reservations.get(domain.zone, {})
        cluster = _reviewed_cluster(plan, domain)
        zones.append({
            'zone': domain.zone, 'cell': domain.cell_key, 'cluster': domain.cluster_id,
            'status': reservation.get('status', ''),
            'demand': dict(reservation.get('demand', {})),
            'committed_after': dict(reservation.get('committed_after', {})),
            'available': {'vcpu': cluster.capacity.vcpu_available,
                          'memory_mb': _headroom(cluster.capacity.memory_gib_available,
                                                 MEGABYTE),
                          'storage_gb': _headroom(cluster.capacity.storage_gib_available,
                                                  GIGABYTE)},
        })
    body = {'format': VIEW_FORMAT,
            'inventory': dict(inventory.reference),
            'site': state.site_key, 'platform': state.platform, 'zones': zones,
            'limits': list(LIMITS)}
    return {**body, 'digest': digest(body)}


def view_digest(plan) -> str:
    """The identity of the commissioned capacity view one plan was decided against."""
    return capacity_view(plan)['digest']


def zones(plan, *, pool_id: str, view: dict | None = None) -> list[dict]:
    """Per zone, the units one operation would reserve and the headroom it read."""
    view = capacity_view(plan) if view is None else view
    return [{'pool_id': pool_id, 'view_digest': view['digest'],
             'operation_id': plan.operation_id, 'zone': row['zone'],
             'cluster': row['cluster'], 'units': zone_units(domain),
             'available': dict(row['available'])}
            for domain, row in zip(plan.desired_state.domains, view['zones'])]


def binding(plan, view: dict | None = None, *, reservation_id: str | None = None,
            envelope_id: str = '', envelope_record_sha256: str = '') -> dict:
    """The identity a reservation must carry to be this plan's reservation.

    The envelope is the reviewed capacity envelope the reservation is accepted
    against. When the operator has not recorded one the envelope is empty and the
    reconciliation reports `HOLD_ENVELOPE_NOT_BOUND` rather than assuming a
    confirmation.
    """
    view = capacity_view(plan) if view is None else view
    return validate_binding({
        'format': BINDING_FORMAT,
        'operation_id': plan.operation_id,
        'generation': plan.generation,
        'scope': scope_of(plan),
        'plan_digest': plan.digest,
        'view_digest': view['digest'],
        'reservation_id': reservation_id or reservation_id_for(plan),
        'envelope': {'id': envelope_id, 'record_sha256': envelope_record_sha256},
    })


def validate_binding(document: dict) -> dict:
    """Refuse a binding that does not carry exactly the declared identity."""
    if not isinstance(document, dict) or set(document) != BINDING_KEYS:
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A capacity binding carries exactly the declared keys',
                '$.capacity.binding',
                keys=sorted(document) if isinstance(document, dict) else None)
    if document['format'] != BINDING_FORMAT:
        _refuse('SCHEMA_VALIDATION_FAILED',
                f'Unknown capacity binding format {document["format"]!r}',
                '$.capacity.binding')
    for key in ('operation_id', 'reservation_id'):
        if not _identifier(document[key]):
            _refuse('SCHEMA_VALIDATION_FAILED',
                    f'A capacity binding {key} is a scoped identifier',
                    '$.capacity.binding', key=key, value=document[key])
    if not _positive_int(document['generation']):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A capacity binding generation is a positive integer',
                '$.capacity.binding', generation=document['generation'])
    if not _sha256(document['plan_digest']) or not _sha256(document['view_digest']):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A capacity binding cites the reviewed plan and the capacity view',
                '$.capacity.binding', plan_digest=document['plan_digest'],
                view_digest=document['view_digest'])
    scope = document['scope']
    if not isinstance(scope, dict) or set(scope) != set(SCOPE_KEYS):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A capacity binding scope carries exactly the declared keys',
                '$.capacity.binding', keys=sorted(scope) if isinstance(scope, dict) else None)
    for name, value in scope.items():
        if not _identifier(value):
            _refuse('SCHEMA_VALIDATION_FAILED',
                    f'Capacity scope component {name} is not a scoped identifier',
                    '$.capacity.binding', name=name, value=value)
    if scope['platform'] not in PLATFORMS:
        _refuse('SCHEMA_VALIDATION_FAILED',
                f'Unknown capacity platform {scope["platform"]!r}',
                '$.capacity.binding', platforms=list(PLATFORMS))
    envelope = document['envelope']
    if not isinstance(envelope, dict) or set(envelope) != ENVELOPE_KEYS:
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A capacity binding envelope carries exactly the declared keys',
                '$.capacity.binding')
    if envelope['id'] and not _identifier(envelope['id']):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A capacity envelope identity is a scoped identifier',
                '$.capacity.binding', envelope_id=envelope['id'])
    if envelope['record_sha256'] and not _sha256(envelope['record_sha256']):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A capacity envelope record digest is a SHA-256',
                '$.capacity.binding', record_sha256=envelope['record_sha256'])
    if bool(envelope['id']) != bool(envelope['record_sha256']):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A capacity envelope is bound by identity and record digest together',
                '$.capacity.binding', envelope=dict(envelope))
    return document


def _identifier(value) -> bool:
    return isinstance(value, str) and bool(IDENTIFIER.match(value))


def _sha256(value) -> bool:
    return isinstance(value, str) and bool(SHA256.match(value))


def _positive_int(value) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value > 0


def request(plan, *, owner_id: str, pool_id: str, capabilities, reservation_id: str | None = None,
            view: dict | None = None) -> dict:
    """Compile the reviewed demand into the declared capacity-owner request.

    `owner_id`, `pool_id` and `capabilities` are host facts the repository cannot
    review: they name the authoritative capacity owner, the pool the reservation is
    taken from and the pool capabilities the reservation must be admitted against.
    They are supplied by the operator and validated here rather than invented.
    """
    view = capacity_view(plan) if view is None else view
    demand = units(plan)
    if not any(demand.values()):
        _refuse('COMPILATION_FAILED',
                'A capacity request cannot be compiled from an empty reviewed demand',
                '$.capacity.request', units=demand)
    document = {
        'format': REQUEST_FORMAT,
        'owner_id': owner_id,
        'reservation_id': reservation_id or reservation_id_for(plan),
        'operation_id': plan.operation_id,
        'generation': plan.generation,
        'scope': scope_of(plan),
        'pool_id': pool_id,
        'units': demand,
        'capabilities': list(capabilities),
    }
    return validate_request(document)


def validate_request(document: dict) -> dict:
    """Refuse any request the declared owner contract would refuse.

    This mirrors the pure shape contract `tools.capacity.validate_request` enforces,
    so the transport can refuse an unusable request without importing the owner.
    `tests/provisioning/unit/test_capacity_owner.py` compares the two on the same
    documents, so the mirror cannot drift from the owner.
    """
    if not isinstance(document, dict) or set(document) != REQUEST_KEYS:
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A capacity request carries exactly the declared keys',
                '$.capacity.request',
                keys=sorted(document) if isinstance(document, dict) else None)
    if document['format'] != REQUEST_FORMAT:
        _refuse('SCHEMA_VALIDATION_FAILED',
                f'Unknown capacity request format {document["format"]!r}',
                '$.capacity.request')
    for key in ('owner_id', 'reservation_id', 'operation_id', 'pool_id'):
        if not _identifier(document[key]):
            _refuse('SCHEMA_VALIDATION_FAILED',
                    f'Capacity request {key} is a scoped identifier',
                    '$.capacity.request', key=key, value=document[key])
    if not _positive_int(document['generation']):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A capacity request generation is a positive integer',
                '$.capacity.request', generation=document['generation'])
    scope = document['scope']
    if not isinstance(scope, dict) or set(scope) != set(SCOPE_KEYS):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A capacity request scope carries exactly the declared keys',
                '$.capacity.request', keys=sorted(scope) if isinstance(scope, dict) else None)
    for name, value in scope.items():
        if not _identifier(value):
            _refuse('SCHEMA_VALIDATION_FAILED',
                    f'Capacity scope component {name} is not a scoped identifier',
                    '$.capacity.request', name=name, value=value)
    if scope['platform'] not in PLATFORMS:
        _refuse('SCHEMA_VALIDATION_FAILED',
                f'Unknown capacity platform {scope["platform"]!r}',
                '$.capacity.request', platforms=list(PLATFORMS))
    request_units = document['units']
    if not isinstance(request_units, dict) or set(request_units) != set(UNITS):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A capacity request states exactly the declared units',
                '$.capacity.request', units=sorted(request_units)
                if isinstance(request_units, dict) else None)
    for unit, value in request_units.items():
        if (isinstance(value, bool) or not isinstance(value, int)
                or not 0 <= value <= MAX_UNITS):
            _refuse('SCHEMA_VALIDATION_FAILED',
                    f'Capacity unit {unit} is a bounded non-negative integer',
                    '$.capacity.request', unit=unit, value=value)
    if not any(request_units.values()):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A capacity request reserves at least one unit',
                '$.capacity.request', units=dict(request_units))
    capabilities = document['capabilities']
    if (not isinstance(capabilities, list) or not capabilities
            or len(capabilities) != len(set(capabilities))):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'Capacity request capabilities are a non-empty duplicate-free list',
                '$.capacity.request', capabilities=capabilities)
    for capability in capabilities:
        if not _identifier(capability):
            _refuse('SCHEMA_VALIDATION_FAILED',
                    'A capacity request capability is a scoped identifier',
                    '$.capacity.request', capability=capability)
    return document


def handoff(plan, *, owner_id: str, pool_id: str, capabilities,
            reservation_id: str | None = None, envelope_id: str = '',
            envelope_record_sha256: str = '') -> dict:
    """Bind the reviewed view, the compiled request and the envelope into one document.

    The handoff is a *proposal*. It states what the owner must be asked for and which
    commissioned capacity view justifies it; it never states that capacity is held.
    """
    view = capacity_view(plan)
    identity = binding(plan, view, reservation_id=reservation_id,
                       envelope_id=envelope_id,
                       envelope_record_sha256=envelope_record_sha256)
    body = {
        'format': HANDOFF_FORMAT,
        'status': PROPOSED,
        'binding': identity,
        'view': view,
        'request': request(plan, owner_id=owner_id, pool_id=pool_id,
                           capabilities=capabilities,
                           reservation_id=identity['reservation_id'], view=view),
        'zones': zones(plan, pool_id=pool_id, view=view),
        'required_facts': list(REQUIRED_FACTS),
        'limits': list(LIMITS),
    }
    return {**body, 'digest': digest(body)}


def validate_facts(document: dict) -> dict:
    """Refuse a facts document that does not name exactly the facts the owner needs.

    These are the facts the repository cannot review. Validating them here is what
    keeps them recorded rather than invented, and keeps the authoritative database
    out of the checkout.
    """
    if not isinstance(document, dict) or set(document) != set(REQUIRED_FACTS):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A capacity owner facts document carries exactly the declared keys',
                '$.capacity.facts',
                keys=sorted(document) if isinstance(document, dict) else None)
    for key in ('owner_id', 'pool_id'):
        if not _identifier(document[key]):
            _refuse('SCHEMA_VALIDATION_FAILED',
                    f'A capacity owner {key} is a scoped identifier',
                    '$.capacity.facts', key=key, value=document[key])
    capabilities = document['capabilities']
    if not isinstance(capabilities, list) or not capabilities:
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A capacity owner facts document names the pool capabilities',
                '$.capacity.facts', capabilities=capabilities)
    for capability in capabilities:
        if not _identifier(capability):
            _refuse('SCHEMA_VALIDATION_FAILED',
                    'A capacity pool capability is a scoped identifier',
                    '$.capacity.facts', capability=capability)
    if len(set(capabilities)) != len(capabilities):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A capacity owner facts document names no duplicate capability',
                '$.capacity.facts', capabilities=list(capabilities))
    database = document['database']
    if not isinstance(database, str) or not database:
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A capacity owner facts document names the authoritative database',
                '$.capacity.facts', database=database)
    if Path(database).resolve().is_relative_to(repository.ROOT):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'The authoritative capacity database is never inside the checkout',
                '$.capacity.facts', database=database)
    envelope_id = document['envelope_id']
    record_sha256 = document['envelope_record_sha256']
    if envelope_id and not _identifier(envelope_id):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A capacity envelope identity is a scoped identifier',
                '$.capacity.facts', envelope_id=envelope_id)
    if record_sha256 and not _sha256(record_sha256):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A capacity envelope record digest is a SHA-256',
                '$.capacity.facts', record_sha256=record_sha256)
    if bool(envelope_id) != bool(record_sha256):
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A capacity envelope is bound by identity and record digest together',
                '$.capacity.facts', envelope_id=envelope_id, record_sha256=record_sha256)
    return document


def load_facts(path) -> dict:
    """Read and validate a recorded capacity owner facts document."""
    target = Path(path)
    try:
        document = json.loads(target.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        _refuse('SCHEMA_VALIDATION_FAILED',
                f'A capacity owner facts document could not be read: {exc}',
                '$.capacity.facts', target=str(target))
    if isinstance(document, dict) and 'format' in document:
        document = {key: document[key] for key in REQUIRED_FACTS if key in document}
    return validate_facts(document)


def handoff_from_facts(plan, facts: dict) -> dict:
    """Compile the owner handoff from recorded owner facts.

    The envelope the operator records is bound into the identity, so the
    reconciliation compares the reservation against the exact envelope the
    reservation was admitted against rather than against whichever envelope is
    current when the export is read.
    """
    facts = validate_facts(facts)
    return handoff(plan, owner_id=facts['owner_id'], pool_id=facts['pool_id'],
                   capabilities=facts['capabilities'],
                   envelope_id=facts['envelope_id'],
                   envelope_record_sha256=facts['envelope_record_sha256'])


def require_current(plan, recorded_view_digest: str) -> str:
    """Refuse a preflight taken against a capacity view that has since moved."""
    current = view_digest(plan)
    if recorded_view_digest and recorded_view_digest != current:
        _refuse('CAPACITY_SNAPSHOT_STALE',
                'The recorded capacity view is not the reviewed capacity view',
                '$.capacity.view',
                recorded=recorded_view_digest, current=current,
                instruction='Re-plan against the current commissioned capacity view '
                            'and obtain a new confirmation')
    return current


def require_exclusive(reservations) -> None:
    """Refuse reservations that only fit because they re-read one capacity view.

    Two operations that were each admitted against the same view's free capacity were
    each admitted against the *same* units. The authoritative owner serialises them
    and would refuse the second; the repository refuses first rather than handing over
    a reservation it cannot justify.
    """
    held: dict[tuple, dict] = {}
    for row in reservations:
        key = (row['pool_id'], row['view_digest'], row['cluster'])
        current = held.get(key)
        if current is None:
            held[key] = {'units': dict(row['units']), 'available': dict(row['available']),
                         'operations': [row['operation_id']], 'zones': [row['zone']]}
            continue
        if row['operation_id'] in current['operations']:
            continue
        combined = {unit: current['units'][unit] + row['units'][unit] for unit in UNITS}
        exceeded = {unit: combined[unit] for unit in UNITS
                    if combined[unit] > current['available'][unit]}
        if exceeded:
            _refuse('CAPACITY_RESERVATION_CONFLICT',
                    'Two operations would consume the same capacity view\'s free capacity',
                    '$.capacity.reservation',
                    pool_id=row['pool_id'], cluster=row['cluster'],
                    view_digest=row['view_digest'],
                    operations=sorted(current['operations'] + [row['operation_id']]),
                    zones=sorted(current['zones'] + [row['zone']]),
                    combined=combined, exceeded=exceeded,
                    available=dict(current['available']),
                    instruction='Reserve through the authoritative capacity owner and '
                                're-plan against the capacity it actually reports')
        current['units'] = combined
        current['operations'].append(row['operation_id'])
        current['zones'].append(row['zone'])


def reconcile(identity: dict, index: dict | None = None, *, as_of=None,
              root=None) -> dict:
    """Classify a proposal against the repository's exported reservation records.

    The authoritative reservation system is external. This reads the repository's
    existing exported evidence, validates it with the repository's existing checker
    and reports what those records actually say about this operation. A missing
    record is a proposal, never a confirmation.
    """
    as_of = datetime.now(timezone.utc) if as_of is None else as_of
    if isinstance(as_of, str):
        as_of = datetime.fromisoformat(as_of.replace('Z', '+00:00'))
    if not isinstance(as_of, datetime) or as_of.tzinfo is None:
        _refuse('SCHEMA_VALIDATION_FAILED',
                'A reservation review instant is a timezone-aware ISO-8601 instant',
                '$.capacity.reconciliation', as_of=repr(as_of))
    if index is None:
        index = repository.reservation_records()
    try:
        summary = repository.validate_reservation_records(index, as_of=as_of, root=root)
    except (ValueError, OSError, TypeError, KeyError) as exc:
        _refuse('SCHEMA_VALIDATION_FAILED',
                f'The exported reservation records are invalid: {exc}',
                'reservation_record_index')

    operation_id = identity['operation_id']
    reservation_id = identity['reservation_id']
    envelope = identity['envelope']
    matches = [record for record in summary['records']
               if record['operation_id'] == operation_id
               or record['reservation_id'] == reservation_id]
    state = PROPOSED
    record = None
    if matches:
        record = matches[0]
        if record['unresolved']:
            state = HOLD_UNCERTAIN
        elif record['operation_id'] != operation_id or record['generation'] != identity['generation']:
            state = HOLD_CONFLICT
        elif record['state'] in ('RELEASED', 'EXPIRED'):
            state = HOLD_TERMINAL
        elif record['state'] == 'CONSUMED':
            state = EXISTING_CONSUMED
        elif record['state'] == 'UNCERTAIN':
            state = HOLD_UNCERTAIN
        elif not envelope['record_sha256'] or record['envelope_record_sha256'] != envelope['record_sha256']:
            state = HOLD_CONFLICT
        elif envelope['id'] and record['envelope_id'] != envelope['id']:
            state = HOLD_CONFLICT
        elif record['state'] == 'HELD':
            state = CONFIRMED
        else:
            state = HOLD_UNCERTAIN
    elif not envelope['record_sha256']:
        state = HOLD_ENVELOPE
    else:
        state = PROPOSED

    return {
        'format': RECONCILIATION_FORMAT,
        'state': state,
        'operation_id': operation_id,
        'generation': identity['generation'],
        'reservation_id': reservation_id,
        'view_digest': identity['view_digest'],
        'plan_digest': identity['plan_digest'],
        'envelope': dict(envelope),
        'record': record,
        'records_checked': summary['record_count'],
        'held_records': summary['held_count'],
        'as_of': as_of.astimezone(timezone.utc).isoformat(),
        'confirmed': state == CONFIRMED,
        'may_allocate': state == CONFIRMED,
        'may_apply': False,
        'may_activate': False,
        'limits': list(LIMITS),
    }


def require_settled(reconciliation: dict) -> None:
    """Refuse a handoff while the authoritative reservation outcome is not settled."""
    state = reconciliation['state']
    code = REFUSING_STATES.get(state)
    if code is None:
        return
    _refuse(code, f'The capacity reservation is not settled: {state}',
            '$.capacity.reconciliation',
            state=state, operation_id=reconciliation['operation_id'],
            reservation_id=reconciliation['reservation_id'],
            envelope=dict(reconciliation['envelope']),
            records_checked=reconciliation['records_checked'],
            instruction='Discover the authoritative reservation outcome through its '
                        'owner before any retry, or claim a new operation identity')


def require_confirmed(reconciliation: dict) -> None:
    """The gate downstream allocation must pass before capacity may be treated as held."""
    if reconciliation.get('confirmed'):
        return
    _refuse('CAPACITY_RESERVATION_UNCONFIRMED',
            f'Capacity is not confirmed by its owner: {reconciliation.get("state", "")}',
            '$.capacity.reconciliation',
            state=reconciliation.get('state', ''),
            operation_id=reconciliation.get('operation_id', ''),
            reservation_id=reconciliation.get('reservation_id', ''),
            records_checked=reconciliation.get('records_checked', 0),
            instruction='Obtain the capacity owner confirmation and record the exported '
                        'reservation record before downstream allocation consumes it')


def review(reconciliation: dict) -> dict:
    """The reviewer-facing summary of one reconciliation."""
    return {'format': RECONCILIATION_FORMAT, 'state': reconciliation['state'],
            'confirmed': reconciliation['confirmed'],
            'operation_id': reconciliation['operation_id'],
            'generation': reconciliation['generation'],
            'reservation_id': reconciliation['reservation_id'],
            'view_digest': reconciliation['view_digest'],
            'records_checked': reconciliation['records_checked'],
            'may_allocate': reconciliation['may_allocate'],
            'limits': list(reconciliation['limits'])}


def to_dict() -> dict:
    """The declared contract, for the documentation drift guard."""
    return {'format': BINDING_FORMAT, 'handoff_format': HANDOFF_FORMAT,
            'view_format': VIEW_FORMAT, 'request_format': REQUEST_FORMAT,
            'reconciliation_format': RECONCILIATION_FORMAT,
            'facts_format': FACTS_FORMAT,
            'scope_keys': list(SCOPE_KEYS), 'units': list(UNITS),
            'record_states': list(RECORD_STATES), 'states': list(STATES),
            'refusing_states': sorted(REFUSING_STATES),
            'required_facts': list(REQUIRED_FACTS),
            'limits': list(LIMITS)}