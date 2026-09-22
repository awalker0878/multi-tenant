#!/usr/bin/env python3
"""Bind operations alerts to accountable acknowledgement, escalation and containment release."""
import argparse
from datetime import timedelta
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ''):
    sys.path.insert(0, str(ROOT))

from tools import readback_core as c
from tools.run_files import encoded, load_private, require, write_new

RESULT_FORMAT = 'hosting-operations-review-result/1'
ACK_FORMAT = 'hosting-operations-acknowledgement/1'
RELEASE_FORMAT = 'hosting-operations-containment-release/1'
HEX64 = re.compile(r'^[0-9a-f]{64}$')
HEALTHY = 'OPERATIONS_HEALTHY'
NON_HEALTHY = {
    'OPERATIONS_ACTION_REQUIRED',
    'OPERATIONS_HOLD_CONTAINMENT_REQUIRED',
    'OPERATIONS_HOLD_EMERGENCY_OVERRIDE_PRESERVED',
}
SEVERITIES = {'critical', 'high', 'warning'}


class AlertHold(RuntimeError):
    """An operations alert that is not accounted for must not advance.

    Acknowledgement and escalation are accountability failures, not evidence that
    the owned edge boundary is exposed, so the hold never requests withdrawal.
    """
    def __init__(self, message, *, escalate=False):
        super().__init__(message)
        self.escalate = escalate
        self.containment_required = False


def _alert(result, observation_id):
    for alert in result['alerts']:
        if alert['observation_id'] == observation_id:
            return alert
    raise ValueError('Alert acknowledgement names an observation with no alert')


def _observation(review, observation_id):
    for row in review['observations']:
        if row['id'] == observation_id:
            return row
    raise ValueError('Operations alert names an observation outside the review')


def validate_result(result):
    c.exact_keys(result, {
        'format', 'review_sha256', 'scope', 'authorization_ref', 'observed_at', 'status',
        'observations', 'alerts', 'containment_required', 'ordinary_reconciliation_authorized',
        'emergency_override_preserved', 'native_acceptance', 'production_activation',
    })
    require(result['format'] == RESULT_FORMAT, 'Exact operations review result required')
    require(isinstance(result['review_sha256'], str) and HEX64.fullmatch(result['review_sha256']),
            'Invalid operations review digest')
    require(result['status'] in {HEALTHY} | NON_HEALTHY, 'Unknown operations review status')
    for key in ('containment_required', 'emergency_override_preserved', 'native_acceptance',
                'production_activation', 'ordinary_reconciliation_authorized'):
        require(type(result[key]) is bool, 'Operations review flags must be booleans')
    require(result['ordinary_reconciliation_authorized'] is False and result['native_acceptance'] is False
            and result['production_activation'] is False,
            'Operations review result cannot authorize reconciliation or activation')
    c.timestamp(result['observed_at'])
    require(isinstance(result['alerts'], list), 'Operations alerts must be a list')
    seen = set()
    for alert in result['alerts']:
        c.exact_keys(alert, {'observation_id', 'classification', 'severity', 'owner', 'route_ref',
                             'evidence_ref', 'containment_required'})
        c.identifier(alert['observation_id'])
        require(alert['observation_id'] not in seen, 'Duplicate operations alert')
        seen.add(alert['observation_id'])
        c.text(alert['classification'])
        require(alert['severity'] in SEVERITIES, 'Unknown operations alert severity')
        c.text(alert['owner'])
        c.text(alert['route_ref'])
        c.text(alert['evidence_ref'])
        require(type(alert['containment_required']) is bool, 'Alert containment flag must be boolean')
    require(bool(result['alerts']) or result['status'] == HEALTHY, 'Non-healthy review without alerts')
    require(result['containment_required'] == any(a['containment_required'] for a in result['alerts']),
            'Operations containment flag does not match its alerts')
    return result


def validate_acknowledgement(result, record):
    c.exact_keys(record, {'format', 'review_sha256', 'observation_id', 'classification', 'owner',
                          'acknowledged_by', 'acknowledged_at', 'response_ref'})
    require(record['format'] == ACK_FORMAT and record['review_sha256'] == result['review_sha256'],
            'Acknowledgement does not bind this operations review')
    alert = _alert(result, record['observation_id'])
    require(record['classification'] == alert['classification'],
            'Acknowledgement does not bind the exact alert classification')
    require(record['owner'] == alert['owner'],
            'Acknowledgement must come from the accountable alert owner')
    c.text(record['acknowledged_by'])
    c.text(record['response_ref'])
    c.timestamp(record['acknowledged_at'])
    return record


def validate_release(result, record):
    c.exact_keys(record, {'format', 'review_sha256', 'observation_ids', 'authority_ref',
                          'released_at', 'restoration_ref'})
    require(record['format'] == RELEASE_FORMAT and record['review_sha256'] == result['review_sha256'],
            'Containment release does not bind this operations review')
    c.text(record['authority_ref'])
    c.text(record['restoration_ref'])
    c.timestamp(record['released_at'])
    require(isinstance(record['observation_ids'], list) and record['observation_ids']
            and all(isinstance(x, str) for x in record['observation_ids'])
            and len(record['observation_ids']) == len(set(record['observation_ids'])),
            'Exact containment release observations required')
    for observation_id in record['observation_ids']:
        c.identifier(observation_id)
    return record


def evaluate(review, result, records, *, release=None, now=None):
    """Classify alert acknowledgement, escalation and containment release.

    Acknowledgement binds the exact review digest, observation, classification and
    accountable owner, so an alert cannot be closed by another route or against a
    different review. An alert that is still unacknowledged one review cadence
    after it was observed has escalated.
    """
    from tools.operations_review import validate as validate_review
    validate_review(review)
    validate_result(result)
    require(result['review_sha256'] == c.digest(review), 'Operations result does not bind this review')
    require(isinstance(records, list), 'Acknowledgements must be a list')
    current = c.timestamp(now) if isinstance(now, str) else c.timestamp(c.now())

    acknowledged = {}
    for record in records:
        validate_acknowledgement(result, record)
        require(record['observation_id'] not in acknowledged,
                'Duplicate acknowledgement for one operations alert')
        require(c.timestamp(record['acknowledged_at']) <= current,
                'Acknowledgement cannot postdate the current review')
        acknowledged[record['observation_id']] = record

    states = []
    escalated = False
    pending = False
    for alert in result['alerts']:
        observation = _observation(review, alert['observation_id'])
        due = c.timestamp(observation['observed_at']) + timedelta(seconds=review['cadence_seconds'])
        record = acknowledged.get(alert['observation_id'])
        if record is None:
            state = 'ESCALATED' if current >= due else 'PENDING'
        else:
            state = 'LATE' if c.timestamp(record['acknowledged_at']) >= due else 'ACKNOWLEDGED'
        escalated = escalated or state in {'ESCALATED', 'LATE'}
        pending = pending or state == 'PENDING'
        states.append({
            'observation_id': alert['observation_id'],
            'classification': alert['classification'],
            'severity': alert['severity'],
            'owner': alert['owner'],
            'containment_required': alert['containment_required'],
            'state': state,
            'acknowledged_by': record['acknowledged_by'] if record else None,
            'response_ref': record['response_ref'] if record else None,
            'acknowledged_at': record['acknowledged_at'] if record else None,
            'escalate_by': due.isoformat(),
        })

    if not states:
        status = 'ALERTS_NONE'
    elif escalated:
        status = 'ALERTS_ESCALATED'
    elif pending:
        status = 'ALERTS_PENDING'
    else:
        status = 'ALERTS_ACKNOWLEDGED'

    contained = [row for row in states if row['containment_required']]
    release_authorized = False
    release_blocked_reason = None
    if release is not None:
        validate_release(result, release)
        if not contained:
            release_blocked_reason = 'NO_CONTAINMENT_TO_RELEASE'
        elif set(release['observation_ids']) != {row['observation_id'] for row in contained}:
            release_blocked_reason = 'RELEASE_DOES_NOT_BIND_EXACT_CONTAINED_ALERTS'
        elif any(row['state'] != 'ACKNOWLEDGED' for row in contained):
            release_blocked_reason = 'CONTAINED_ALERT_NOT_ACKNOWLEDGED'
        elif c.timestamp(release['released_at']) < max(
                c.timestamp(row['acknowledged_at']) for row in contained):
            release_blocked_reason = 'RELEASE_PRECEDES_ACCOUNTABLE_RESPONSE'
        else:
            release_authorized = True

    return {
        'format': 'hosting-operations-alert-accounting/1',
        'review_sha256': result['review_sha256'],
        'scope': result['scope'],
        'review_status': result['status'],
        'observed_at': current.isoformat(),
        'status': status,
        'alerts': states,
        'containment_required': result['containment_required'],
        'release_requested': release is not None,
        'containment_release_authorized': release_authorized,
        'release_blocked_reason': release_blocked_reason,
        'escalation_owner_required': status == 'ALERTS_ESCALATED',
        'native_acceptance': False,
        'production_activation': False,
    }


def enforce(outcome):
    if outcome['status'] == 'ALERTS_ESCALATED':
        raise AlertHold('Operations alert escalation requires accountable resolution', escalate=True)
    if outcome['status'] == 'ALERTS_PENDING':
        raise AlertHold('Operations alerts remain unacknowledged')
    if outcome['release_requested'] and not outcome['containment_release_authorized']:
        raise AlertHold(f"Containment release is not authorized: {outcome['release_blocked_reason']}")
    return outcome


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--result', type=Path, required=True)
    parser.add_argument('--acknowledgements', type=Path, required=True)
    parser.add_argument('--release', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        outcome = evaluate(load_private(args.review), load_private(args.result),
                           load_private(args.acknowledgements),
                           release=load_private(args.release) if args.release else None)
        data = encoded(outcome)
        if args.output:
            write_new(args.output, data)
        else:
            print(data.decode().rstrip())
        enforce(outcome)
        return 0
    except (ValueError, OSError, KeyError, TypeError, AlertHold):
        print(json.dumps({
            'status': 'HOLD_OPERATIONS_ALERTS',
            'native_acceptance': False,
            'production_activation': False,
        }))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())