"""Reconciliation classification.

Classification turns a comparison row into one of a small, fixed set of outcomes.
It never guesses: an outcome that depends on evidence the repository does not have
is classified as needing discovery rather than being assumed benign.
"""
from __future__ import annotations

from provisioner.observation import drift, native

CLASSIFICATION_FORMAT = 'hosting-reconciliation-classification/1'

IN_SYNC = 'IN_SYNC'
DRIFTED = 'DRIFTED'
MISSING = 'MISSING_NATIVE_OBJECT'
UNKNOWN = 'UNKNOWN_REQUIRES_DISCOVERY'
CONTAINMENT = 'CONTAINMENT_REQUIRED'

CLASSES = (IN_SYNC, DRIFTED, MISSING, UNKNOWN, CONTAINMENT)

# Fields whose divergence is an incident-containment matter, not routine drift.
CONTAINMENT_FIELDS = ('zone', 'prefix', 'trust', 'service_class')


def classify_row(row: dict) -> str:
    if row['evidence'] != native.OBSERVED:
        return UNKNOWN
    classes = {d['classification'] for d in row['differences']}
    fields = {d['field'] for d in row['differences']}
    if not classes:
        return IN_SYNC
    if classes == {drift.MISSING}:
        return MISSING
    if classes == {drift.UNKNOWN}:
        return UNKNOWN
    if fields & set(CONTAINMENT_FIELDS):
        return CONTAINMENT
    return DRIFTED


def classify(comparison: dict) -> dict:
    """Classify every comparison row and summarise the outcome."""
    rows = [{'subject': row['subject'], 'native_id': row['native_id'],
             'classification': classify_row(row)} for row in comparison['rows']]
    classes = sorted({row['classification'] for row in rows})
    return {'format': CLASSIFICATION_FORMAT, 'status': 'CLASSIFIED_NOT_RECONCILED',
            'rows': rows, 'classes': classes,
            'requires_containment': CONTAINMENT in classes,
            'requires_discovery': UNKNOWN in classes,
            'limits': ['Classification never mutates native state',
                       'Containment is an incident decision above routine reconciliation']}