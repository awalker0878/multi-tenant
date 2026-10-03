#!/usr/bin/env python3
"""Classify current operations evidence without authorizing repair or native mutation."""
import argparse
from datetime import timezone
import json
from pathlib import Path
import re
import sys

from hosting_resources import SOURCE_ROOT
ROOT = SOURCE_ROOT

from provisioner.execution import readback_core as c
from provisioner.execution.source_integrity import verify, verify_runtime
from provisioner.execution.run_files import encoded, load_private, require, write_new

ROUTES = {'operations', 'incident', 'capacity', 'service'}
KINDS = {'configuration', 'health', 'capacity', 'telemetry'}
HEX64 = re.compile(r'^[0-9a-f]{64}$')
HEALTH = {'healthy', 'degraded', 'failed', 'unknown'}
CAPACITY = {'within_envelope', 'warning', 'exhausted', 'unknown'}
TELEMETRY = {'current', 'stale', 'unavailable', 'unknown'}


class OperationsHold(RuntimeError):
    """A non-healthy review that must not advance ordinary reconciliation."""
    def __init__(self, message, *, containment_required=False):
        super().__init__(message)
        self.containment_required = containment_required


def _digest_or_none(value, name):
    require(value is None or (isinstance(value, str) and HEX64.fullmatch(value)), f'Invalid {name}')


def _text_or_none(value, name):
    require(value is None or (isinstance(value, str) and value.strip()), f'Invalid {name}')


def validate(review):
    c.exact_keys(review, {
        'format', 'source_commit', 'operation_id', 'generation', 'scope',
        'cadence_seconds', 'authorization_ref', 'routes', 'observations'
    })
    require(
        review['format'] == 'hosting-operations-review/1'
        and isinstance(review['source_commit'], str)
        and re.fullmatch(r'[0-9a-f]{40}', review['source_commit']),
        'Exact operations source required',
    )
    c.identifier(review['operation_id'])
    require(type(review['generation']) is int and review['generation'] > 0, 'Positive operations generation required')
    c.exact_keys(review['scope'], {'environment_key', 'site_key', 'platform', 'tenant_key', 'wsd_key'})
    for value in review['scope'].values():
        c.identifier(value)
    require(review['scope']['platform'] in {'nutanix', 'vmware', 'openstack'}, 'Unknown operations platform')
    require(type(review['cadence_seconds']) is int and 60 <= review['cadence_seconds'] <= 604800,
            'Operations cadence must be between one minute and seven days')
    c.text(review['authorization_ref'])

    c.exact_keys(review['routes'], ROUTES)
    for route in review['routes'].values():
        c.exact_keys(route, {'owner', 'route_ref'})
        c.text(route['owner'])
        c.text(route['route_ref'])

    require(isinstance(review['observations'], list) and review['observations'],
            'At least one operations observation is required')
    seen = set()
    for row in review['observations']:
        c.exact_keys(row, {
            'id', 'kind', 'owner_route', 'observed_at', 'evidence_ref',
            'security_relevant', 'containment_on_failure', 'state',
            'expected_sha256', 'observed_sha256', 'emergency_override'
        })
        c.identifier(row['id'])
        require(row['id'] not in seen and row['kind'] in KINDS, 'Duplicate or unsupported operations observation')
        seen.add(row['id'])
        require(row['owner_route'] in ROUTES, 'Unknown operations alert route')
        c.timestamp(row['observed_at'])
        c.text(row['evidence_ref'])
        require(type(row['security_relevant']) is bool and type(row['containment_on_failure']) is bool,
                'Operations risk flags must be booleans')

        if row['kind'] == 'configuration':
            require(row['state'] is None, 'Configuration observations use exact digests, not a supplied status')
            _digest_or_none(row['expected_sha256'], 'expected configuration digest')
            _digest_or_none(row['observed_sha256'], 'observed configuration digest')
            require(row['expected_sha256'] is not None and row['observed_sha256'] is not None,
                    'Configuration observations require exact expected and observed digests')
            if row['security_relevant']:
                require(row['containment_on_failure'] is True,
                        'Security-significant configuration drift must be containment eligible')
            if row['emergency_override'] is not None:
                override = row['emergency_override']
                c.exact_keys(override, {
                    'ref', 'expected_sha256', 'observed_sha256',
                    'valid_from', 'valid_until', 'incident_ref', 'closure_ref'
                })
                for key in ('ref', 'incident_ref'):
                    c.text(override[key])
                _text_or_none(override['closure_ref'], 'emergency closure reference')
                require(
                    override['expected_sha256'] == row['expected_sha256']
                    and override['observed_sha256'] == row['observed_sha256'],
                    'Emergency override does not bind the exact configuration drift',
                )
                c.timestamp(override['valid_from'])
                c.timestamp(override['valid_until'])
        else:
            require(row['expected_sha256'] is None and row['observed_sha256'] is None
                    and row['emergency_override'] is None,
                    'Non-configuration observations cannot carry configuration drift fields')
            allowed = {'health': HEALTH, 'capacity': CAPACITY, 'telemetry': TELEMETRY}[row['kind']]
            require(row['state'] in allowed, 'Unsupported operations observation state')
            if row['kind'] == 'capacity':
                require(not row['security_relevant'] and not row['containment_on_failure'],
                        'Capacity pressure is an admission/operations hold, not automatic security containment')
    return review


def _fresh(row, review, now):
    observed = c.timestamp(row['observed_at'])
    require(observed <= now.replace(tzinfo=timezone.utc), 'Operations observation is from the future')
    return (now - observed).total_seconds() <= review['cadence_seconds']


def _active_override(row, now):
    override = row['emergency_override']
    if override is None or override['closure_ref'] is not None:
        return False
    return c.timestamp(override['valid_from']) <= now < c.timestamp(override['valid_until'])


def classify(row, review, now):
    if not _fresh(row, review, now):
        return 'UNKNOWN'

    if row['kind'] == 'configuration':
        if row['expected_sha256'] == row['observed_sha256']:
            require(row['emergency_override'] is None, 'Matched configuration cannot retain an active drift override')
            return 'MATCHED'
        if _active_override(row, now):
            return 'APPROVED_EMERGENCY'
        if row['emergency_override'] is not None:
            return 'SECURITY_CRITICAL' if row['security_relevant'] else 'UNKNOWN'
        return 'SECURITY_CRITICAL' if row['security_relevant'] else 'BENIGN_DRIFT'

    if row['kind'] == 'health':
        return {
            'healthy': 'HEALTHY',
            'degraded': 'DEGRADED',
            'failed': 'FAILED',
            'unknown': 'UNKNOWN',
        }[row['state']]
    if row['kind'] == 'capacity':
        return {
            'within_envelope': 'WITHIN_ENVELOPE',
            'warning': 'WARNING',
            'exhausted': 'EXHAUSTED',
            'unknown': 'UNKNOWN',
        }[row['state']]
    return {
        'current': 'CURRENT',
        'stale': 'STALE',
        'unavailable': 'UNAVAILABLE',
        'unknown': 'UNKNOWN',
    }[row['state']]


def _severity(row, classification):
    if classification in {'MATCHED', 'HEALTHY', 'WITHIN_ENVELOPE', 'CURRENT'}:
        return None
    if classification in {'SECURITY_CRITICAL', 'FAILED', 'EXHAUSTED', 'UNAVAILABLE'}:
        return 'critical'
    if classification in {'UNKNOWN', 'STALE'}:
        return 'high'
    if classification in {'APPROVED_EMERGENCY'}:
        return 'high'
    return 'warning'


def evaluate(review, *, now=None):
    validate(review)
    current = c.timestamp(now) if isinstance(now, str) else c.timestamp(c.now())
    observations = []
    alerts = []
    containment_required = False
    ordinary_reconciliation_blocked = False
    emergency_preserved = False

    for row in review['observations']:
        classification = classify(row, review, current)
        containment = False
        if classification == 'SECURITY_CRITICAL':
            containment = row['containment_on_failure']
        elif classification in {'FAILED', 'UNKNOWN', 'UNAVAILABLE', 'STALE'}:
            containment = row['containment_on_failure']
        severity = _severity(row, classification)
        healthy = classification in {'MATCHED', 'HEALTHY', 'WITHIN_ENVELOPE', 'CURRENT'}

        if not healthy:
            ordinary_reconciliation_blocked = True
            route = review['routes'][row['owner_route']]
            alerts.append({
                'observation_id': row['id'],
                'classification': classification,
                'severity': severity,
                'owner': route['owner'],
                'route_ref': route['route_ref'],
                'evidence_ref': row['evidence_ref'],
                'containment_required': containment,
            })
        if classification == 'APPROVED_EMERGENCY':
            emergency_preserved = True
        containment_required = containment_required or containment
        observations.append({
            'id': row['id'],
            'kind': row['kind'],
            'classification': classification,
            'evidence_ref': row['evidence_ref'],
            'fresh': _fresh(row, review, current),
        })

    if containment_required:
        status = 'OPERATIONS_HOLD_CONTAINMENT_REQUIRED'
    elif emergency_preserved:
        status = 'OPERATIONS_HOLD_EMERGENCY_OVERRIDE_PRESERVED'
    elif ordinary_reconciliation_blocked:
        status = 'OPERATIONS_ACTION_REQUIRED'
    else:
        status = 'OPERATIONS_HEALTHY'

    return {
        'format': 'hosting-operations-review-result/1',
        'review_sha256': c.digest(review),
        'scope': review['scope'],
        'authorization_ref': review['authorization_ref'],
        'observed_at': current.isoformat(),
        'status': status,
        'observations': observations,
        'alerts': alerts,
        'containment_required': containment_required,
        'ordinary_reconciliation_authorized': False,
        'emergency_override_preserved': emergency_preserved,
        'native_acceptance': False,
        'production_activation': False,
    }


def enforce(result):
    if result['status'] != 'OPERATIONS_HEALTHY':
        raise OperationsHold(
            'Operations evidence requires accountable action before ordinary reconciliation',
            containment_required=result['containment_required'],
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--source-root', type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        review = load_private(args.review)
        require(isinstance(args.source_root,Path) and verify_runtime(args.source_root)['status']=='RUNTIME_SOURCES_MATCH',
                'Exact runtime and explicitly selected source checkout required')
        source = verify(args.source_root)
        require(source['status'] == 'HASHES_MATCH' and source['commit'] == review['source_commit'],
                'Exact clean operations source required')
        result = evaluate(review)
        data = encoded(result)
        if args.output:
            write_new(args.output, data)
        else:
            print(data.decode().rstrip())
        return 0 if result['status'] == 'OPERATIONS_HEALTHY' else 2
    except (ValueError, OSError, KeyError, TypeError):
        print(json.dumps({
            'status': 'HOLD_OPERATIONS_RECONCILIATION',
            'native_acceptance': False,
            'production_activation': False,
        }))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
