"""Stable WSD identity and monotonic desired-state generation.

A generation is the reviewed change counter for one WSD identity. It exists so two
independent facts can be stated without ambiguity:

- *what* is being changed, which is the identity: tenant, WSD, environment, site
  and platform together, named exactly as the existing `hosting-delivery/1` scope
  names them;
- *which* change it is, which is the generation: a positive integer that only ever
  moves forward for that identity.

This module owns the semantics — replay safety, monotonicity, supersession and the
refusal of a second concurrent claim. It deliberately does **not** own the storage:
the ledger that records which generation is current belongs to the owner that holds
the record, so `InMemoryLedger` exists for controlled tests and says so. A local
counter is not authority, and this repository never treats it as one.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from provisioner.domain.errors import ProvisioningError
from provisioner.domain.request import digest

IDENTITY_FORMAT = 'hosting-wsd-identity/1'
GENERATION_FORMAT = 'hosting-wsd-generation/1'
LEDGER_FORMAT = 'hosting-wsd-generation-ledger/1'

#: The delivery scope contract, exactly as `hosting-delivery/1` names it.
SCOPE_KEYS = ('environment_key', 'site_key', 'platform', 'tenant_key', 'wsd_key')

#: Mirrors `tools.readback_core.ID`, which `tools/delivery_run.validate` enforces.
#: `tests/provisioning/unit/test_generation.py` compares the two, so the delivery
#: contract stays the owner and this copy cannot drift unnoticed.
SCOPE_IDENTIFIER = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$')

#: A generation's lifecycle in the authoritative ledger.
OPEN = 'OPEN'
SUPERSEDED = 'SUPERSEDED'
CLOSED = 'CLOSED'
STATUSES = (OPEN, SUPERSEDED, CLOSED)

#: Claim outcomes.
CLAIMED = 'CLAIMED'
REPLAYED = 'REPLAYED'


@dataclass(frozen=True)
class WsdIdentity:
    """The five identifiers that name one WSD, plus their canonical key and digest."""

    tenant_key: str
    wsd_key: str
    environment_key: str
    site_key: str
    platform: str

    def __post_init__(self):
        for name in SCOPE_KEYS:
            value = getattr(self, name)
            if not isinstance(value, str) or not SCOPE_IDENTIFIER.match(value):
                raise ProvisioningError(
                    'SCHEMA_VALIDATION_FAILED',
                    f'WSD identity component {name} is not a scoped identifier',
                    path=f'$.identity.{name}', details={'value': value})

    @property
    def key(self) -> str:
        """Canonical identity key: what a ledger record is filed under."""
        return (f'{self.tenant_key}/{self.wsd_key}'
                f'@{self.environment_key}/{self.site_key}/{self.platform}')

    @property
    def scope(self) -> dict:
        """The delivery scope projection, key for key."""
        return {name: getattr(self, name) for name in SCOPE_KEYS}

    def to_dict(self) -> dict:
        return {'format': IDENTITY_FORMAT, 'key': self.key, 'digest': self.digest,
                **self.scope,
                'limits': ['Identity names the reviewed scope; it grants no authority']}

    @property
    def digest(self) -> str:
        return digest({'identity': self.scope})


def identity_of(state) -> WsdIdentity:
    """Derive the WSD identity of a resolved desired state.

    Derived rather than stored twice: the desired state already carries the tenant,
    WSD, environment, site and platform, so the identity is a projection of them and
    a second stored copy could only drift.
    """
    return WsdIdentity(tenant_key=state.tenant, wsd_key=state.wsd,
                       environment_key=environment_key(state), site_key=state.site_key,
                       platform=state.platform)


def environment_key(state) -> str:
    """The environment identity the existing delivery contract expects."""
    return f'{state.site_key}-{state.lifecycle}'


def require_generation(value) -> int:
    """Accept only a positive integer generation."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ProvisioningError('SCHEMA_VALIDATION_FAILED',
                                'A generation is a positive integer',
                                path='$.generation', details={'generation': value})
    return value


def operation_id(identity: WsdIdentity, generation: int, plan_digest: str) -> str:
    """The deterministic operation identity for one generation of one WSD.

    Derived, never chosen: the same reviewed plan always produces the same
    operation identity, so a resumed run recognises its own operation instead of
    creating a second one.
    """
    return f'{identity.wsd_key}-g{require_generation(generation)}-{plan_digest[:12]}'


def wsd_key_of(identity_key: str) -> str:
    """The WSD component of a canonical identity key.

    `GenerationRecord` stores the identity key rather than the whole identity, so
    the operation identity is re-derived from it. Parsing it in one place keeps the
    derived form identical to `operation_id`.
    """
    tenant, _, rest = identity_key.partition('/')
    wsd, _, _ = rest.partition('@')
    if not tenant or not wsd:
        raise ValueError(f'Not a canonical WSD identity key: {identity_key}')
    return wsd


@dataclass(frozen=True)
class GenerationRecord:
    """One claimed generation of one WSD identity."""

    identity_key: str
    identity_digest: str
    generation: int
    desired_state_digest: str
    plan_digest: str
    status: str = OPEN
    superseded_by: int | None = None
    format: str = GENERATION_FORMAT

    def __post_init__(self):
        require_generation(self.generation)
        if self.status not in STATUSES:
            raise ValueError(f'Unknown generation status: {self.status}')

    @property
    def operation_id(self) -> str:
        return f'{wsd_key_of(self.identity_key)}-g{self.generation}-{self.plan_digest[:12]}'

    def to_dict(self) -> dict:
        return {**self.body(), 'digest': self.digest,
                'limits': ['A recorded generation is a reviewed change counter, not an approval']}

    def body(self) -> dict:
        """Everything the record digest covers. `digest` itself is not covered."""
        return {'format': self.format, 'identity_key': self.identity_key,
                'identity_digest': self.identity_digest, 'generation': self.generation,
                'desired_state_digest': self.desired_state_digest,
                'plan_digest': self.plan_digest, 'operation_id': self.operation_id,
                'status': self.status, 'superseded_by': self.superseded_by}

    @property
    def digest(self) -> str:
        return digest(self.body())


def record(identity: WsdIdentity, generation: int, desired_state_digest: str,
           plan_digest: str, status: str = OPEN) -> GenerationRecord:
    """Build the record for one generation of one identity."""
    return GenerationRecord(identity_key=identity.key, identity_digest=identity.digest,
                            generation=require_generation(generation),
                            desired_state_digest=desired_state_digest,
                            plan_digest=plan_digest, status=status)


def record_for(plan) -> GenerationRecord:
    """The generation record a reviewed plan claims."""
    state = plan.desired_state
    return record(identity_of(state), plan.generation, state.digest, plan.digest)


class GenerationLedger(Protocol):
    """Where an authoritative generation record lives.

    The repository defines the interface and the semantics. The owner that holds
    the record supplies the implementation, because only it can decide which
    generation is current.
    """

    def current(self, identity_key: str) -> GenerationRecord | None:
        """The record currently held for one identity, or None."""

    def compare_and_set(self, expected: GenerationRecord | None,
                        proposed: GenerationRecord) -> None:
        """Commit `proposed` only while the held record is still exactly `expected`."""


class InMemoryLedger:
    """A ledger that keeps its records in memory.

    It exists so the claim semantics can be exercised deterministically in
    repository tests. It is not authority and says so in every result it produces.
    """

    AUTHORITY = 'IN_MEMORY_NOT_AUTHORITATIVE'

    def __init__(self, records=()) -> None:
        self._records: dict[str, GenerationRecord] = {}
        for existing in records:
            self._records[existing.identity_key] = existing

    def current(self, identity_key: str) -> GenerationRecord | None:
        return self._records.get(identity_key)

    def compare_and_set(self, expected: GenerationRecord | None,
                        proposed: GenerationRecord) -> None:
        """Commit `proposed` only while the held record is still exactly `expected`."""
        held = self._records.get(proposed.identity_key)
        if held is not expected:
            raise ProvisioningError(
                'GENERATION_CONFLICT',
                'Another claim became current for this identity first',
                path='$.generation',
                details={'identity_key': proposed.identity_key,
                         'generation': proposed.generation,
                         'held': held.digest if held is not None else None})
        self._records[proposed.identity_key] = proposed

    def commit(self, expected: GenerationRecord | None, proposed: GenerationRecord) -> None:
        self.compare_and_set(expected, proposed)

    def to_dict(self) -> dict:
        return {'format': LEDGER_FORMAT, 'authority': self.AUTHORITY,
                'identities': sorted(self._records),
                'limits': ['An in-memory ledger is a test double, never production authority']}


def claim(ledger, proposed: GenerationRecord, *, allow_open_supersession: bool = False) -> dict:
    """Claim one generation of one identity, or refuse and say why.

    The rules are the ones the existing delivery runner already enforces, restated
    for the portable plan:

    - the first generation of an identity is 1;
    - the same generation with the same desired state is a replay: no duplicate
      external operation is created;
    - the same generation with a different desired state is refused, because changed
      desired state requires a new generation;
    - a lower generation is stale;
    - a higher generation supersedes a *closed* record. Superseding an unfinished
      operation is refused unless the caller states that reconciliation has decided
      it, so an uncertain operation is never silently abandoned.
    """
    current = ledger.current(proposed.identity_key)
    superseded = None

    if current is None:
        if proposed.generation != 1:
            raise ProvisioningError(
                'GENERATION_CONFLICT',
                'The first generation of a WSD identity is 1',
                path='$.generation',
                details={'identity_key': proposed.identity_key,
                         'generation': proposed.generation})
        outcome = CLAIMED
    elif current.identity_digest != proposed.identity_digest:
        raise ProvisioningError(
            'GENERATION_IDENTITY_MISMATCH',
            'The held generation belongs to a different WSD identity',
            path='$.generation',
            details={'identity_key': proposed.identity_key,
                     'held': current.identity_digest,
                     'proposed': proposed.identity_digest})
    elif proposed.generation == current.generation:
        if (current.desired_state_digest != proposed.desired_state_digest
                or current.plan_digest != proposed.plan_digest):
            raise ProvisioningError(
                'GENERATION_CONFLICT',
                'Changed desired state requires a new generation',
                path='$.generation',
                details={'identity_key': proposed.identity_key,
                         'generation': proposed.generation,
                         'held_desired_state': current.desired_state_digest,
                         'proposed_desired_state': proposed.desired_state_digest})
        outcome = REPLAYED
    elif proposed.generation < current.generation:
        raise ProvisioningError(
            'STALE_GENERATION',
            'A newer generation already holds this WSD identity',
            path='$.generation',
            details={'identity_key': proposed.identity_key,
                     'held': current.generation, 'proposed': proposed.generation})
    elif current.status == OPEN and not allow_open_supersession:
        raise ProvisioningError(
            'GENERATION_CONFLICT',
            'An unfinished generation must be reconciled or closed before a newer one takes over',
            path='$.generation',
            details={'identity_key': proposed.identity_key,
                     'held': current.generation, 'proposed': proposed.generation,
                     'held_status': current.status})
    else:
        superseded = current
        outcome = CLAIMED

    ledger.compare_and_set(current, proposed)
    return {'format': LEDGER_FORMAT, 'status': outcome,
            'identity_key': proposed.identity_key,
            'identity_digest': proposed.identity_digest,
            'generation': proposed.generation,
            'operation_id': proposed.operation_id,
            'desired_state_digest': proposed.desired_state_digest,
            'plan_digest': proposed.plan_digest,
            'superseded': (superseded.to_dict() if superseded is not None else None),
            'duplicate_operations': False,
            'authority': getattr(ledger, 'AUTHORITY', 'EXTERNAL_NOT_INSPECTED'),
            'native_contact': False,
            'limits': ['A claim records which generation is current; it authorizes nothing',
                       'Execution authority and production approval remain external']}


def to_dict() -> dict:
    """The generation model as a document, for a reviewer and for the CLI."""
    return {'format': GENERATION_FORMAT, 'identity_format': IDENTITY_FORMAT,
            'ledger_format': LEDGER_FORMAT, 'scope_keys': list(SCOPE_KEYS),
            'statuses': list(STATUSES), 'outcomes': [CLAIMED, REPLAYED],
            'first_generation': 1,
            'authority': 'EXTERNAL_LEDGER_ONLY',
            'limits': ['The repository owns the generation semantics, not the record',
                       'A local counter is never production authority',
                       'A generation is a change counter, not an approval']}