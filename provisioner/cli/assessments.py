"""Remote comparison contracts; no inventory, policy engine or execution owner.

The API reconstructs membership and verifies authority. These checks bind its
reply to the exact submitted selection and reject dropped members, contradictory
capacity/status summaries and accidental execution claims. They do not qualify
native platforms, verify signatures or reserve resources.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta

MAX_RESPONSE_BYTES = 1024 * 1024
MAX_REQUEST_BYTES = 131072
METHODS = ('REBUILD_RESTORE', 'COLD_VM_CONVERSION', 'SAME_PLATFORM_RELOCATION',
           'APPLICATION_NATIVE', 'WARM_VM_TRANSFER')
_MAX = 2**63 - 1
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z')
_SHA = re.compile(r'[0-9a-f]{64}\Z')
_FAMILIES = {'vmware', 'nutanix', 'openstack'}
_READY = {'REVIEWED_ASSESSMENT_ONLY', 'REVIEWED_WITH_UNKNOWNS'}
_FLAGS = {'ownershipAccepted', 'executionAuthorized', 'dependencyEvidenceVerified', 'reservationHeld'}


def _require(valid: bool) -> None:
    if not valid:
        raise ValueError('Invalid exact-selection application comparison')


def _integer(value, minimum=1):
    return type(value) is int and minimum <= value <= _MAX


def _id(value):
    return isinstance(value, str) and _ID.fullmatch(value) is not None


def _sha(value):
    return isinstance(value, str) and _SHA.fullmatch(value) is not None


def _native(value):
    return (isinstance(value, str) and 1 <= len(value) <= 512 and bool(value.strip())
            and not any(ord(c) < 32 or ord(c) == 127 for c in value))


def _keys(value, names):
    _require(isinstance(value, dict) and set(value) == set(names))


def _time(value):
    _require(isinstance(value, str) and len(value) <= 40 and re.fullmatch(
        r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}'
        r'(?:\.[0-9]{1,6})?(?:Z|\+00:00)', value) is not None)
    result = datetime.fromisoformat(value)
    _require(result.utcoffset() == timedelta(0))
    return result


def selection_digest(document):
    """Public request identity, not a signature or independent authorization."""
    return hashlib.sha256(json.dumps(document, sort_keys=True, ensure_ascii=True,
        separators=(',', ':'), allow_nan=False).encode('ascii')).hexdigest()


def install_parser(groups):
    group = groups.add_parser('assessments', help='Read-only workload and application comparison')
    actions = group.add_subparsers(dest='action', required=True)
    for name in ('compare', 'compare-application'):
        command = actions.add_parser(name, help='Calculate advice; never submit a migration')
        command.add_argument('--source-environment', required=True)
        command.add_argument('--source-generation', type=int, required=True)
        command.add_argument('--destination', nargs=2, action='append', required=True,
                             metavar=('ENVIRONMENT', 'GENERATION'),
                             help='Repeat for 2–20 distinct destination environments')
        command.add_argument('--capacity', nargs=3, action='append', default=[],
                             metavar=('ENVIRONMENT', 'KIND', 'NATIVE_ID'),
                             help='Optional exact observed capacity identity per destination')
        command.add_argument('--method', choices=METHODS, required=True)
        command.add_argument('--network-mode', required=True)
        command.add_argument('--data-mode', required=True)
        if name == 'compare':
            command.add_argument('--workload-native-id', required=True)
            command.add_argument('--guest-profile', required=True)
        else:
            command.add_argument('--application-group', required=True)
            command.add_argument('--draft-revision', type=int, required=True)
            command.add_argument('--draft-record-digest', required=True)
            command.add_argument('--member-profile', nargs=2, action='append', required=True,
                                 metavar=('WORKLOAD_ID', 'GUEST_PROFILE'),
                                 help='One explicit guest profile per retained application member')


def request(args, identity):
    """Compose the same closed selections used by the existing control API."""
    identity(args.source_environment)
    _require(_integer(args.source_generation) and args.method in METHODS)
    _require(_id(args.network_mode) and _id(args.data_mode))
    _require(isinstance(args.destination, list) and 2 <= len(args.destination) <= 20)
    destinations = {}
    for entry in args.destination:
        _require(isinstance(entry, (list, tuple)) and len(entry) == 2)
        environment, raw = entry
        identity(environment)
        _require(isinstance(raw, str) and re.fullmatch(r'[1-9][0-9]{0,18}', raw) is not None
                 and _integer(int(raw)))
        _require(environment != args.source_environment and environment not in destinations)
        destinations[environment] = {'environmentId': environment, 'generation': int(raw)}
    _require(isinstance(args.capacity, list) and len(args.capacity) <= len(destinations))
    for entry in args.capacity:
        _require(isinstance(entry, (list, tuple)) and len(entry) == 3)
        environment, kind, native_id = entry
        _require(isinstance(environment, str) and environment in destinations
                 and 'capacityKind' not in destinations[environment]
                 and isinstance(kind, str) and kind in {'pool', 'cluster', 'quota', 'datastore'}
                 and _native(native_id))
        destinations[environment].update(capacityKind=kind, capacityNativeId=native_id)
    document = {'source': {'environmentId': args.source_environment, 'generation': args.source_generation},
                'destinations': list(destinations.values()), 'method': args.method,
                'networkMode': args.network_mode, 'dataMode': args.data_mode}
    if args.action == 'compare':
        _require(_native(args.workload_native_id) and _id(args.guest_profile))
        document.update(workloadNativeId=args.workload_native_id, guestProfile=args.guest_profile)
        return 'POST', '/v1/assessments/compare', None, document
    _require(args.action == 'compare-application' and _id(args.application_group)
             and _integer(args.draft_revision) and _sha(args.draft_record_digest))
    _require(isinstance(args.member_profile, list) and 2 <= len(args.member_profile) <= 100
             and len(args.member_profile) * len(destinations) <= 200)
    members = {}
    for entry in args.member_profile:
        _require(isinstance(entry, (list, tuple)) and len(entry) == 2)
        workload, guest = entry
        _require(_id(workload) and _id(guest) and workload not in members)
        members[workload] = guest
    document.update(applicationGroupId=args.application_group, draftRevision=args.draft_revision,
        draftRecordDigest=args.draft_record_digest,
        memberProfiles=[{'workloadId': name, 'guestProfile': guest} for name, guest in members.items()])
    _require(len(json.dumps(document, ensure_ascii=True).encode('ascii')) <= MAX_REQUEST_BYTES)
    return 'POST', '/v1/assessments/applications/compare', None, document


def _binding(value, selected):
    _keys(value, {'environmentId', 'generation', 'endpointId', 'nativeScopeId', 'platformFamily',
                  'productTupleId', 'productTupleDigest', 'observation', 'superseded', 'latestObservation'})
    _require(value['environmentId'] == selected['environmentId'] and _integer(value['generation'])
             and value['generation'] == selected['generation'] and _id(value['endpointId'])
             and _native(value['nativeScopeId']) and isinstance(value['platformFamily'], str)
             and value['platformFamily'] in _FAMILIES and _id(value['productTupleId'])
             and _sha(value['productTupleDigest']) and type(value['superseded']) is bool)
    latest = value['latestObservation']
    _keys(latest, {'generation', 'rawSnapshotDigest', 'capturedAt', 'collectionCompleteness',
                   'collectionErrors', 'missingPrivileges'})
    _require(_integer(latest['generation']) and latest['generation'] >= value['generation']
             and _sha(latest['rawSnapshotDigest'])
             and value['superseded'] == (latest['generation'] > value['generation'])
             and latest['collectionCompleteness'] in ('COMPLETE', 'PARTIAL', 'UNKNOWN'))
    _time(latest['capturedAt'])
    for name in ('collectionErrors', 'missingPrivileges'):
        _require(isinstance(latest[name], list) and len(latest[name]) <= 1024
                 and all(_native(item) for item in latest[name]))
    observation = value['observation']
    if observation is not None:
        _keys(observation, {'rawSnapshotDigest', 'assessmentSnapshotDigest', 'normalizerVersion',
                           'capturedAt', 'collectionCompleteness', 'assessmentCompleteness'})
        _require(_sha(observation['rawSnapshotDigest']) and _sha(observation['assessmentSnapshotDigest'])
                 and observation['normalizerVersion'] == 'hosting-assessment-normalizer/2'
                 and observation['collectionCompleteness'] in ('COMPLETE', 'PARTIAL', 'UNKNOWN')
                 and observation['assessmentCompleteness'] in ('COMPLETE', 'PARTIAL', 'UNKNOWN'))
        _time(observation['capturedAt'])
        if not value['superseded']:
            _require(observation['rawSnapshotDigest'] == latest['rawSnapshotDigest']
                     and _time(observation['capturedAt']) == _time(latest['capturedAt'])
                     and observation['collectionCompleteness'] == latest['collectionCompleteness'])
    return [value['endpointId'], value['nativeScopeId'], value['platformFamily']]


def _issues(value):
    _require(isinstance(value, list) and len(value) <= 2048)
    for item in value:
        _keys(item, {'severity', 'code'})
        _require(item['severity'] in ('BLOCKER', 'UNKNOWN', 'CONDITION') and _id(item['code']))
    return {item['severity'] for item in value}


def _status(severities):
    return ('BLOCKED' if 'BLOCKER' in severities else 'UNKNOWN' if 'UNKNOWN' in severities
            else 'CONDITIONAL' if 'CONDITION' in severities else 'ELIGIBLE')


def validate_application_response(submitted, value):
    """Wire consistency only; the caller separately validates the embedded review."""
    common = {'format', 'selectionDigest', 'applicationReview', 'sourceInput', 'destinationInputs',
              'assessments', 'status', 'consistency'} | _FLAGS
    _require(isinstance(value, dict) and value.get('status') in
             ('HELD_APPLICATION_REVIEW', 'ASSESSED_NOT_AUTHORIZED'))
    held = value['status'] == 'HELD_APPLICATION_REVIEW'
    _keys(value, common if held else common | {'startupOrder', 'datasetCount', 'consistencyGroupCount'})
    _require(value['format'] == 'hosting-application-comparison/2'
             and value['selectionDigest'] == selection_digest(submitted)
             and value['consistency'] == 'PINNED_INPUTS_LIVE_RECHECKS'
             and all(value[flag] is False for flag in _FLAGS))
    review = value['applicationReview']
    _require(isinstance(review, dict) and review.get('generation') == submitted['source']['generation'])
    if held:
        _require(review.get('status') not in _READY and value['sourceInput'] is None
                 and value['destinationInputs'] == [] and value['assessments'] == [])
        return
    _require(review.get('status') in _READY)
    source_scope = _binding(value['sourceInput'], submitted['source'])
    scope = review['scope']
    _require(source_scope == [scope['endpoint_id'], scope['native_scope_id'], scope['platform_family']]
             and not value['sourceInput']['superseded']
             and value['sourceInput']['observation'] is not None
             and value['sourceInput']['observation']['rawSnapshotDigest'] == review['resultDigest'])
    wanted = {item['workloadId']: item['guestProfile'] for item in submitted['memberProfiles']}
    order = value['startupOrder']
    _require(isinstance(order, list) and len(order) == len(wanted)
             and all(_id(item) for item in order) and set(order) == set(wanted)
             and _integer(value['datasetCount'], 0) and _integer(value['consistencyGroupCount'], 0)
             and value['consistencyGroupCount'] <= value['datasetCount'])
    targets, rows = value['destinationInputs'], value['assessments']
    _require(isinstance(targets, list) and isinstance(rows, list)
             and len(targets) == len(rows) == len(submitted['destinations']))
    scopes, native_members, demand = {tuple(source_scope)}, None, None
    for selected, target, row in zip(submitted['destinations'], targets, rows):
        native_scope = _binding(target, selected)
        _require(tuple(native_scope) not in scopes)
        scopes.add(tuple(native_scope))
        _keys(row, {'environmentId', 'status', 'capacity', 'capacityIdentity', 'issues', 'members',
                    'executionAuthorized'})
        _require(row['environmentId'] == selected['environmentId'] and row['executionAuthorized'] is False)
        identity = (native_scope + [selected['capacityKind'], selected['capacityNativeId']]
                    if 'capacityKind' in selected else None)
        _require(row['capacityIdentity'] == identity)
        severities = _issues(row['issues'])
        codes = {(item['severity'], item['code']) for item in row['issues']}
        _require({('CONDITION', 'APPLICATION_POLICY_DATA_REVIEW_REQUIRED'),
                  ('CONDITION', 'APPLICATION_RESERVATION_NOT_HELD')} <= codes)
        _require(isinstance(row['members'], list) and len(row['members']) == len(wanted))
        observed = {}
        for member in row['members']:
            _keys(member, {'workloadId', 'nativeVm', 'guestProfile', 'assessedAt', 'status', 'issues',
                          'executionAuthorized'})
            name, native = member['workloadId'], member['nativeVm']
            _require(_id(name) and name in wanted and name not in observed
                     and member['guestProfile'] == wanted[name] and member['executionAuthorized'] is False
                     and isinstance(native, list) and len(native) == 5
                     and native[:4] == source_scope + ['vm'] and _native(native[4]))
            _require(_time(member['assessedAt']) <= _time(review['checkedAt']))
            member_severities = _issues(member['issues'])
            _require(member['status'] == _status(member_severities))
            severities |= member_severities
            observed[name] = native
        _require(len({tuple(native) for native in observed.values()}) == len(wanted))
        _require(native_members is None or observed == native_members)
        native_members = observed
        capacity = row['capacity']
        _keys(capacity, {'basis', 'memberCount', 'resources', 'reservationHeld',
                         'transientAndRecoveryFootprintIncluded'})
        _require(capacity['basis'] == 'SUM_OF_OBSERVED_LOGICAL_VM_REQUIREMENTS'
                 and _integer(capacity['memberCount']) and capacity['memberCount'] == len(wanted)
                 and capacity['reservationHeld'] is False and capacity['transientAndRecoveryFootprintIncluded'] is False)
        _keys(capacity['resources'], {'VM_COUNT', 'VCPU', 'MEMORY', 'STORAGE'})
        required = {}
        for resource, quantities in capacity['resources'].items():
            _keys(quantities, {'required', 'available'})
            need, available = quantities['required'], quantities['available']
            _require((need is None or _integer(need)) and (available is None or _integer(available, 0)))
            if identity is None or target['observation'] is None:
                _require(available is None)
            if resource == 'VM_COUNT':
                _require(need == len(wanted))
            for missing, kind in ((need is None, 'DEMAND'), (available is None, 'CAPACITY')):
                if missing:
                    _require(('UNKNOWN', f'APPLICATION_{resource}_{kind}_UNKNOWN') in codes)
            if need is not None and available is not None and need > available:
                _require(('BLOCKER', f'APPLICATION_{resource}_CAPACITY_INSUFFICIENT') in codes)
            required[resource] = need
        _require(demand is None or required == demand)
        demand = required
        if review['unknownDependencyCount']:
            _require(('UNKNOWN', 'APPLICATION_DEPENDENCIES_UNRESOLVED') in codes)
        _require(row['status'] == _status(severities))
