"""Native health reporting.

Health answers one narrow question: has the expected native state been observed at
all? It never claims a service is ready, reachable or accepted, because that is a
service-owner assertion this repository cannot make.
"""
from __future__ import annotations

from provisioner.observation import drift, native

HEALTH_FORMAT = 'hosting-native-health/1'

HEALTHY = 'OBSERVED_MATCHES_PLAN'
DEGRADED = 'DRIFT_OR_MISSING_OBSERVED_STATE'
UNKNOWN = 'NOT_OBSERVED'
STATUSES = (HEALTHY, DEGRADED, UNKNOWN)


def assess(state, observations) -> dict:
    """Assess observed native state against the plan, without claiming readiness."""
    expected = native.expected_subjects(state)
    known = native.index(observations)
    observed = [k for k in expected if k in known and known[k].trusted]
    unobserved = [k for k in expected if k not in known or not known[k].trusted]
    differences = drift.compare(state, observations)
    actionable = [d for d in differences if d.classification in (drift.DRIFTED, drift.MISSING)]

    if actionable:
        status = DEGRADED
    elif unobserved:
        status = UNKNOWN
    elif expected:
        status = HEALTHY
    else:
        status = UNKNOWN

    return {'format': HEALTH_FORMAT, 'status': status,
            'expected': len(expected), 'observed': len(observed),
            'not_observed': [{'subject': s, 'native_id': i} for s, i in sorted(unobserved)],
            'drift': drift.summary(differences),
            'service_readiness': 'NOT_ASSERTED_BY_REPOSITORY',
            'native_contact': False,
            'limits': ['Health describes observed native state only',
                       'Service readiness and acceptance are owner assertions',
                       'A healthy observation is not a production authorization']}


def to_dict(state, observations) -> dict:
    return assess(state, observations)