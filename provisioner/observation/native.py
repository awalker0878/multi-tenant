"""Native observation.

Observation is deliberately separate from execution: the thing that made a change
is never trusted to describe the result. An observation is only ever produced by a
readback against the native system, so an absent observation is recorded as
absent — never inferred, never defaulted to healthy.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from provisioner.domain.generation import require_generation
from provisioner.domain.request import digest

OBSERVATION_FORMAT = 'hosting-native-observation/1'

OBSERVED = 'OBSERVED'
NOT_OBSERVED = 'NOT_OBSERVED'
STALE = 'STALE'

# Native objects this pipeline expects to be able to read back.
SUBJECTS = ('domain', 'workload', 'network', 'route', 'service')


@dataclass(frozen=True)
class Observation:
    """One native readback of one subject."""

    subject: str
    native_id: str
    status: str
    attributes: dict = field(default_factory=dict)
    source: str = ''
    generation: int | None = None
    digest: str = ''
    format: str = OBSERVATION_FORMAT

    def __post_init__(self):
        if self.status not in (OBSERVED, NOT_OBSERVED, STALE):
            raise ValueError(f'Unknown observation status: {self.status}')
        if self.generation is not None:
            require_generation(self.generation)

    @property
    def trusted(self) -> bool:
        return self.status == OBSERVED

    def to_dict(self) -> dict:
        return {'format': self.format, 'subject': self.subject, 'native_id': self.native_id,
                'status': self.status, 'attributes': dict(self.attributes),
                'source': self.source, 'generation': self.generation, 'digest': self.digest,
                'limits': ['An observation describes native state; it is not an authorization']}


def observed(subject: str, native_id: str, attributes: dict, source: str,
             generation: int | None = None) -> Observation:
    row = Observation(subject=subject, native_id=native_id, status=OBSERVED,
                      attributes=dict(attributes), source=source, generation=generation)
    body = row.to_dict()
    body.pop('digest')
    return Observation(**{**row.__dict__, 'digest': digest(body)})


def unobserved(subject: str, native_id: str, source: str = '') -> Observation:
    return Observation(subject=subject, native_id=native_id, status=NOT_OBSERVED, source=source)


def expected_subjects(state) -> tuple[tuple[str, str], ...]:
    """Every (subject, native identity) the desired state expects to exist."""
    rows: list[tuple[str, str]] = []
    for domain in state.domains:
        rows.append(('domain', domain.domain_id))
        for workload in domain.workloads:
            rows.append(('workload', workload.name))
    return tuple(sorted(rows))


def index(observations) -> dict[tuple[str, str], Observation]:
    return {(o.subject, o.native_id): o for o in observations}


BINDING_BOUND = 'BOUND'
BINDING_STALE = 'STALE'
BINDING_UNBOUND = 'UNBOUND'
BINDINGS = (BINDING_BOUND, BINDING_STALE, BINDING_UNBOUND)


def binding(observations, generation: int) -> dict:
    """Classify every observation against the current generation.

    A readback describes the native state of one generation. An observation that
    belongs to another generation describes a state that no longer exists, and one
    that names no generation cannot be attributed at all. Neither is allowed to
    stand in for current evidence, and neither is discarded silently: both are
    reported with the reason.
    """
    rows = []
    for observation in observations:
        if observation.generation is None:
            state = BINDING_UNBOUND
            reason = 'The observation names no generation'
        elif observation.generation != generation:
            state = BINDING_STALE
            reason = (f'The observation belongs to generation {observation.generation}; '
                      f'the current generation is {generation}')
        else:
            state = BINDING_BOUND
            reason = f'The observation belongs to generation {generation}'
        rows.append({'subject': observation.subject, 'native_id': observation.native_id,
                     'observation_generation': observation.generation,
                     'binding': state, 'trusted': observation.trusted, 'reason': reason})
    counts = {state: sum(1 for row in rows if row['binding'] == state) for state in BINDINGS}
    return {'generation': generation, 'count': len(rows),
            'bound': counts[BINDING_BOUND], 'stale': counts[BINDING_STALE],
            'unbound': counts[BINDING_UNBOUND], 'rows': rows,
            'limits': ['An observation from another generation never satisfies current conformance',
                       'An observation that names no generation is not attributable evidence']}


def bound(observations, generation: int) -> tuple[Observation, ...]:
    """Only the observations that belong to the current generation."""
    return tuple(o for o in observations
                 if o.generation is not None and o.generation == generation)


def to_dict(observations, state=None, generation: int | None = None) -> dict:
    rows = [o.to_dict() for o in observations]
    payload = {'format': OBSERVATION_FORMAT, 'status': 'READBACK_ONLY',
               'count': len(rows), 'observations': rows,
               'limits': ['Native readback is produced outside this repository',
                          'Absent observation is not evidence of absence or of health']}
    if generation is not None:
        payload['generation'] = generation
        payload['binding'] = binding(observations, generation)
    if state is not None:
        known = index(observations)
        missing = [(s, i) for s, i in expected_subjects(state) if (s, i) not in known]
        payload['expected'] = len(expected_subjects(state))
        payload['not_observed'] = [{'subject': s, 'native_id': i} for s, i in missing]
    return payload