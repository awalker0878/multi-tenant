"""Reconciliation comparison.

Reconciliation starts from a comparison, never from a remembered intention. The
comparison is only as trustworthy as the observation it is built on, so every row
carries its own evidence status.
"""
from __future__ import annotations

from dataclasses import dataclass

from provisioner.observation import drift, native

COMPARISON_FORMAT = 'hosting-reconciliation-comparison/1'


@dataclass(frozen=True)
class Row:
    subject: str
    native_id: str
    desired: dict
    observed: dict
    evidence: str
    differences: tuple[dict, ...] = ()

    def to_dict(self) -> dict:
        return {'subject': self.subject, 'native_id': self.native_id,
                'desired': dict(self.desired), 'observed': dict(self.observed),
                'evidence': self.evidence, 'differences': [dict(d) for d in self.differences]}


def build(state, observations) -> dict:
    """One comparison row per expected native subject."""
    known = native.index(observations)
    differences: dict[tuple[str, str], list[dict]] = {}
    for difference in drift.compare(state, observations):
        differences.setdefault((difference.subject, difference.native_id), []).append(
            difference.to_dict())

    rows: list[Row] = []
    for key, desired in sorted(drift.expected_attributes(state).items()):
        observation = known.get(key)
        rows.append(Row(subject=key[0], native_id=key[1], desired=desired,
                        observed=dict(observation.attributes) if observation else {},
                        evidence=observation.status if observation else native.NOT_OBSERVED,
                        differences=tuple(differences.get(key, ()))))
    return {'format': COMPARISON_FORMAT, 'status': 'COMPARED_NOT_RECONCILED',
            'rows': [r.to_dict() for r in rows],
            'evidence_available': sum(1 for r in rows if r.evidence == native.OBSERVED),
            'limits': ['Comparison is not reconciliation',
                       'Rows without native evidence cannot be reconciled']}