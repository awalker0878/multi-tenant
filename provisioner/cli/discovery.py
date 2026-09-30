"""Read-only discovery client contracts; no scheduler or native authority.

The operator owns HTTP and strict JSON decoding. This module checks request/reply
consistency and preserves age, collection quality and native visibility as
separate facts. A successful metadata check is never migration qualification.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta

MAX_FRESHNESS_BYTES = 16384
MAX_INTEGER = 2**63 - 1
_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$')
_SHA = re.compile(r'^[0-9a-f]{64}$')
_CURSOR = re.compile(r'^[A-Za-z0-9_-]{1,4096}$')
_UTC = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)$')
_SCOPE = {'organization_id', 'tenant_id', 'site_id', 'security_domain_id',
          'endpoint_id', 'native_scope_id', 'platform_family'}
_FIELDS = {'format', 'environmentId', 'scope', 'checkedAt', 'policy', 'observation',
           'freshness', 'ageMicroseconds', 'refreshDue', 'issues', 'consistency',
           'integrityVerification', 'nativeVisibilityVerified',
           'collectionRequested', 'executionAuthorized'}
_OBSERVATION = {'generation', 'campaignId', 'authorizationDigest', 'resultDigest',
                'capturedAt', 'completeness', 'objectCount',
                'collectionErrorCount', 'missingPrivilegeCount'}


def _require(value: bool) -> None:
    if not value:
        raise ValueError('Invalid discovery freshness response')


def _integer(value, minimum=0, maximum=MAX_INTEGER) -> bool:
    return type(value) is int and minimum <= value <= maximum


def _matches(pattern, value) -> bool:
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def _time(value) -> datetime:
    _require(_matches(_UTC, value))
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise ValueError('Invalid discovery freshness timestamp') from None
    _require(parsed.utcoffset() == timedelta(0))
    return parsed


def install_parser(groups) -> None:
    discovery = groups.add_parser('discovery',
        help='Browse read-only inventory generations, objects and capture health')
    actions = discovery.add_subparsers(dest='action', required=True)
    generations = actions.add_parser('generations')
    generations.add_argument('--environment', required=True)
    generations.add_argument('--after', type=int, default=0)
    generations.add_argument('--limit', type=int, default=50)
    objects = actions.add_parser('objects')
    objects.add_argument('--environment', required=True)
    objects.add_argument('--generation', type=int, required=True)
    objects.add_argument('--after', help='Opaque nextAfter value from the API')
    objects.add_argument('--limit', type=int, default=50)
    freshness = actions.add_parser('freshness',
        help='Inspect latest capture metadata; does not request collection')
    freshness.add_argument('--environment', required=True)
    freshness.add_argument('--check', action='store_true',
        help='Exit 4 for missing, future, stale, refresh-due or incomplete metadata; not qualification')


def request(args, identity) -> tuple[str, str, dict | None, None]:
    prefix = '/v1/environments/' + identity(args.environment) + '/discovery'
    if args.action == 'freshness':
        return 'GET', prefix + '/freshness', None, None
    if not _integer(args.limit, 1, 100):
        raise ValueError('Discovery limit must be between 1 and 100')
    if args.action == 'generations':
        if not _integer(args.after):
            raise ValueError('Invalid discovery generation cursor')
        return 'GET', prefix + '/generations', {'after': args.after, 'limit': args.limit}, None
    if args.action != 'objects' or not _integer(args.generation, 1):
        raise ValueError('Invalid discovery generation')
    params = {'limit': args.limit}
    if args.after is not None:
        if not _matches(_CURSOR, args.after):
            raise ValueError('Invalid bounded discovery cursor')
        params['after'] = args.after
    return 'GET', prefix + '/generations/' + str(args.generation) + '/objects', params, None


def validate_freshness(environment_id: str, payload: dict) -> bool:
    """Validate the as-of report and return only its age/collection-health result.

    Intervals come from the server's bounded policy, not client overrides. Exact
    integer microseconds preserve inclusive maximum-age and refresh-due boundaries.
    No local clock, signature validation or underlying observation hydration is
    used: the API still owns identity and the current metadata read.
    """
    _require(type(payload) is dict and set(payload) == _FIELDS)
    _require(payload['format'] == 'hosting-discovery-freshness/1'
             and _matches(_ID, environment_id) and payload['environmentId'] == environment_id
             and payload['consistency'] == 'LIVE_METADATA_RECHECKS'
             and payload['integrityVerification'] == 'METADATA_ONLY'
             and all(payload[key] is False for key in (
                 'nativeVisibilityVerified', 'collectionRequested', 'executionAuthorized'))
             and type(payload['refreshDue']) is bool)
    scope, policy = payload['scope'], payload['policy']
    _require(type(scope) is dict and set(scope) == _SCOPE
             and all(_matches(_ID, value) for value in scope.values())
             and scope['platform_family'] in ('vmware', 'nutanix', 'openstack'))
    _require(type(policy) is dict and set(policy) == {
        'format', 'refreshAfterSeconds', 'maxAgeSeconds'}
        and policy['format'] == 'hosting-discovery-freshness-policy/1'
        and _integer(policy['refreshAfterSeconds'], 1, 604800)
        and _integer(policy['maxAgeSeconds'], policy['refreshAfterSeconds'], 604800))
    checked = _time(payload['checkedAt'])
    observation = payload['observation']
    expected, age, due = [], None, True
    complete = False
    if observation is None:
        freshness = 'MISSING'
        expected.append('INVENTORY_MISSING')
    else:
        _require(type(observation) is dict and set(observation) == _OBSERVATION
                 and _integer(observation['generation'], 1)
                 and _matches(_ID, observation['campaignId'])
                 and _matches(_SHA, observation['authorizationDigest'])
                 and _matches(_SHA, observation['resultDigest'])
                 and observation['completeness'] in ('COMPLETE', 'PARTIAL', 'UNKNOWN')
                 and _integer(observation['objectCount'])
                 and _integer(observation['collectionErrorCount'], 0, 1024)
                 and _integer(observation['missingPrivilegeCount'], 0, 1024))
        complete = observation['completeness'] == 'COMPLETE'
        _require(not complete or (observation['collectionErrorCount'] == 0
                                  and observation['missingPrivilegeCount'] == 0))
        delta = checked - _time(observation['capturedAt'])
        if delta < timedelta(0):
            freshness = 'FUTURE_CAPTURE'
            expected.append('INVENTORY_CAPTURE_IN_FUTURE')
        else:
            age = (delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds
            freshness = 'STALE' if age > policy['maxAgeSeconds'] * 1000000 else 'FRESH'
            due = age >= policy['refreshAfterSeconds'] * 1000000
            if freshness == 'STALE':
                expected.append('INVENTORY_STALE')
            elif due:
                expected.append('INVENTORY_REFRESH_DUE')
        if not complete:
            expected.append('COLLECTION_' + observation['completeness'])
        if observation['collectionErrorCount']:
            expected.append('COLLECTION_ERRORS_PRESENT')
        if observation['missingPrivilegeCount']:
            expected.append('MISSING_PRIVILEGES')
    expected.append('NATIVE_VISIBILITY_UNVERIFIED')
    actual_age = payload['ageMicroseconds']
    _require((actual_age is None if age is None else _integer(actual_age) and actual_age == age)
             and payload['freshness'] == freshness and payload['refreshDue'] is due)
    issues = payload['issues']
    _require(type(issues) is list and len(issues) == len(expected)
             and all(type(issue) is str for issue in issues)
             and len(set(issues)) == len(issues) and set(issues) == set(expected))
    return freshness == 'FRESH' and not due and complete
