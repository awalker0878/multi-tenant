"""Drift detection.

Drift is a statement about *two* states: what the plan declared and what the
native system reports. Where the native state was not observed, drift is
UNKNOWN — a plan is never assumed to match a system nobody read.
"""
from __future__ import annotations

from dataclasses import dataclass

from provisioner.observation import native

DRIFT_FORMAT = 'hosting-native-drift/1'

IN_SYNC = 'IN_SYNC'
DRIFTED = 'DRIFTED'
MISSING = 'MISSING'
UNKNOWN = 'UNKNOWN_NOT_OBSERVED'


@dataclass(frozen=True)
class Difference:
    subject: str
    native_id: str
    field: str
    desired: object
    observed: object
    classification: str

    def to_dict(self) -> dict:
        return {'subject': self.subject, 'native_id': self.native_id, 'field': self.field,
                'desired': self.desired, 'observed': self.observed,
                'classification': self.classification}


def expected_attributes(state) -> dict[tuple[str, str], dict]:
    """The native attributes the desired state claims for each subject."""
    rows: dict[tuple[str, str], dict] = {}
    for domain in state.domains:
        rows[('domain', domain.domain_id)] = {'zone': domain.zone, 'prefix': domain.prefix,
                                              'cluster': domain.cluster_id}
        for workload in domain.workloads:
            rows[('workload', workload.name)] = {'address': workload.address,
                                                 'vcpu': workload.vcpu,
                                                 'memory_gib': workload.memory_gib}
    return rows


def compare(state, observations) -> tuple[Difference, ...]:
    """Compare desired attributes with observed attributes, field by field."""
    known = native.index(observations)
    differences: list[Difference] = []
    for key, desired in sorted(expected_attributes(state).items()):
        observation = known.get(key)
        if observation is None or not observation.trusted:
            differences.append(Difference(subject=key[0], native_id=key[1], field='*',
                                          desired='declared', observed='not observed',
                                          classification=UNKNOWN))
            continue
        for field_name, value in sorted(desired.items()):
            actual = observation.attributes.get(field_name)
            if actual is None:
                differences.append(Difference(subject=key[0], native_id=key[1],
                                              field=field_name, desired=value,
                                              observed='absent', classification=MISSING))
            elif actual != value:
                differences.append(Difference(subject=key[0], native_id=key[1],
                                              field=field_name, desired=value,
                                              observed=actual, classification=DRIFTED))
    return tuple(differences)


def summary(differences: tuple[Difference, ...]) -> dict:
    classes = sorted({d.classification for d in differences})
    status = IN_SYNC if not differences else (
        UNKNOWN if classes == [UNKNOWN] else DRIFTED)
    return {'format': DRIFT_FORMAT, 'status': status,
            'differences': [d.to_dict() for d in differences],
            'classes': classes, 'count': len(differences),
            'limits': ['Unobserved subjects are unknown, not in sync']}


def to_dict(state, observations) -> dict:
    return summary(compare(state, observations))