"""Reconciliation decisions.

A decision states what the owner should do next. It is advice with an explicit
authority, never an action: this repository cannot replay, roll back or mutate a
native platform, so every decision names the owner that must act.
"""
from __future__ import annotations

from provisioner.reconciliation import classify as classifier

DECISION_FORMAT = 'hosting-reconciliation-decision/1'

NO_ACTION = 'NO_ACTION'
REPLAN = 'REPLAN_REQUIRED'
DISCOVER = 'DISCOVERY_REQUIRED'
CONTAIN = 'CONTAINMENT_REQUIRED'
ADOPT = 'ADOPTION_REVIEW_REQUIRED'

ACTIONS = (NO_ACTION, REPLAN, DISCOVER, CONTAIN, ADOPT)

DECISIONS = {
    classifier.IN_SYNC: (NO_ACTION, 'hosting-platform',
                         'No difference was observed; nothing is required'),
    classifier.DRIFTED: (REPLAN, 'hosting-platform',
                         'Observed native state differs from the plan; replan before any change'),
    classifier.MISSING: (ADOPT, 'hosting-platform',
                         'A declared object was not observed; review whether it was created elsewhere'),
    classifier.UNKNOWN: (DISCOVER, 'platform-owner',
                         'Native state was not observed; discover it before deciding anything'),
    classifier.CONTAINMENT: (CONTAIN, 'incident-owner',
                             'A trust, zone or prefix boundary diverged; contain before routine work'),
}


def decide(classification: dict) -> dict:
    """Turn a classification into one owner-scoped recommendation."""
    recommendations = []
    for row in classification['rows']:
        action, owner, reason = DECISIONS[row['classification']]
        recommendations.append({'subject': row['subject'], 'native_id': row['native_id'],
                                'classification': row['classification'], 'action': action,
                                'owner': owner, 'reason': reason})
    actions = sorted({r['action'] for r in recommendations if r['action'] != NO_ACTION})
    return {'format': DECISION_FORMAT, 'status': 'ADVISORY_NOT_EXECUTED',
            'recommendations': recommendations, 'actions': actions,
            'native_contact': False,
            'limits': ['This repository does not replay, roll back or mutate native state',
                       'Every action belongs to the named owner']}


def to_dict(state, observations) -> dict:
    from provisioner.reconciliation import compare
    return decide(classifier.classify(compare.build(state, observations)))