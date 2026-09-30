"""Thin draft client contract: no database, identity issuer or native adapter.

Only the control API may validate inventory membership and current authority.
Client checks prevent ambiguous files, misdirected results and silent approval
claims; a digest here is not an independent signature or an execution grant.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
from pathlib import Path
from datetime import datetime, timedelta

MAX_DRAFT_BYTES = 131072
_MAX = 2**63 - 1
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z')
_SHA = re.compile(r'[0-9a-f]{64}\Z')
_DRAFT_FIELDS = {'applicationGroupId', 'name', 'ownerId', 'members', 'datasetIds',
                 'consistencyGroups', 'startupOrder'}


def install_parser(groups):
    drafts = groups.add_parser('application-drafts', help='List, load, save drafts or inspect independently signed owner reviews')
    actions = drafts.add_subparsers(dest='action', required=True)
    listing = actions.add_parser('list', help='One live page of latest-revision summaries')
    listing.add_argument('--environment', required=True)
    listing.add_argument('--limit', type=int, default=50)
    listing.add_argument('--after', help='Last applicationGroupId from the previous page')
    get = actions.add_parser('get', help='Read the latest or an exact historical draft')
    get.add_argument('--environment', required=True)
    get.add_argument('--id', required=True)
    get.add_argument('--revision', type=int)
    review = actions.add_parser('review', help='Read exact-draft owner-review status; never accept or revoke')
    review.add_argument('--environment', required=True)
    review.add_argument('--id', required=True)
    review.add_argument('--revision', type=int, required=True)
    review.add_argument('--record-digest', help='Optional exact recordDigest from the previously loaded draft')
    save = actions.add_parser('save', help='Append a draft; never approve ownership or migration')
    save.add_argument('--environment', required=True)
    save.add_argument('--id', required=True)
    save.add_argument('--generation', type=int, required=True)
    save.add_argument('--result-digest', required=True)
    save.add_argument('--expected-revision', type=int, required=True,
                      help='0 for a new group; retain the exact revision for edits/retries')
    save.add_argument('--file', required=True, help='Bounded JSON with exactly draft and dependencies')


def decode_document(raw: bytes, maximum: int) -> dict:
    def pairs(items):
        result = {}
        for name, value in items:
            if name in result:
                raise ValueError('Duplicate JSON field')
            result[name] = value
        return result

    def integer(value):
        parsed = int(value)
        if not -_MAX-1 <= parsed <= _MAX:
            raise ValueError('JSON integer is outside its bound')
        return parsed

    def floating(value):
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError('Non-finite JSON number')
        return parsed

    def constant(_):
        raise ValueError('Non-finite JSON number')

    if not isinstance(raw, bytes) or not 1 <= len(raw) <= maximum:
        raise ValueError('JSON document exceeds its bound')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                           parse_int=integer, parse_float=floating, parse_constant=constant)
        if not isinstance(value, dict):
            raise ValueError('A JSON object is required')
        pending = [(value, 0)]
        while pending:
            item, depth = pending.pop()
            if depth > 64:
                raise ValueError('JSON nesting exceeds its bound')
            if isinstance(item, dict):
                pending.extend((child, depth+1) for child in item.values())
            elif isinstance(item, list):
                pending.extend((child, depth+1) for child in item)
        return value
    except (RecursionError, UnicodeError, OverflowError):
        raise ValueError('Invalid bounded JSON document') from None


def _content(path):
    target = Path(path)
    if not stat.S_ISREG(target.lstat().st_mode):
        raise ValueError('Draft input must be a regular file')
    flags = os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0)
    with os.fdopen(os.open(target, flags), 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or not 1 <= info.st_size <= MAX_DRAFT_BYTES:
            raise ValueError('Draft input must be a bounded regular file')
        value = decode_document(stream.read(MAX_DRAFT_BYTES+1), MAX_DRAFT_BYTES)
    if (set(value) != {'draft', 'dependencies'} or not isinstance(value['draft'], dict)
            or set(value['draft']) != _DRAFT_FIELDS or not isinstance(value['dependencies'], list)
            or len(value['dependencies']) > 500):
        raise ValueError('Only the draft/dependencies proposal is accepted')
    return value


def request(args, identity):
    prefix = '/v1/environments/' + identity(args.environment) + '/application-drafts'
    if args.action == 'list':
        if not 1 <= args.limit <= 100:
            raise ValueError('Draft limit must be between 1 and 100')
        params = {'limit': args.limit}
        if args.after is not None:
            identity(args.after)
            params['after'] = args.after  # Query values are encoded exactly once by HTTPX.
        return 'GET', prefix, params, None
    path = prefix + '/' + identity(args.id)
    if args.action == 'review':
        if (type(args.revision) is not int or not 1 <= args.revision <= _MAX
                or args.record_digest is not None and (not isinstance(args.record_digest, str)
                    or not _SHA.fullmatch(args.record_digest))):
            raise ValueError('An exact draft revision and valid optional digest are required')
        return 'GET', path + '/review', {'revision': args.revision}, None
    if args.action == 'get':
        if args.revision is not None and not 1 <= args.revision <= _MAX:
            raise ValueError('Draft revision is outside its bound')
        return 'GET', path, {'revision': args.revision} if args.revision is not None else None, None
    if args.action != 'save':
        raise ValueError('Unknown application draft operation')
    if (not 1 <= args.generation <= _MAX or not 0 <= args.expected_revision < _MAX
            or not _SHA.fullmatch(args.result_digest)):
        raise ValueError('Exact inventory digest/generation and expected revision are required')
    content = _content(args.file)
    if content['draft']['applicationGroupId'] != args.id:
        raise ValueError('Requested application and proposal identity differ')
    document = {**content, 'generation': args.generation, 'resultDigest': args.result_digest,
                'expectedRevision': args.expected_revision}
    if len(json.dumps(document, ensure_ascii=True, allow_nan=False).encode('ascii')) > MAX_DRAFT_BYTES:
        raise ValueError('The complete draft request exceeds the server bound')
    return 'PUT', path, None, document


def validate_response(args, value, *, submitted=None):
    """Refuse a successful-looking response for another selection or approval."""
    if args.action == 'review':
        _validate_review_response(args, value)
        return
    def revision(item, identity):
        if (not isinstance(item, dict) or item.get('format') != 'hosting-application-draft-revision/1'
                or item.get('environmentId') != args.environment or item.get('applicationGroupId') != identity
                or item.get('status') != 'UNREVIEWED' or item.get('ownershipAccepted') is not False
                or item.get('executionAuthorized') is not False
                or type(item.get('revision')) is not int or not 1 <= item['revision'] <= _MAX
                or type(item.get('generation')) is not int or not 1 <= item['generation'] <= _MAX
                or type(item.get('latestGeneration')) is not int
                or not item['generation'] <= item['latestGeneration'] <= _MAX
                or type(item.get('sourceSuperseded')) is not bool
                or item['sourceSuperseded'] != (item['generation'] != item['latestGeneration'])
                or not isinstance(item.get('resultDigest'), str) or not _SHA.fullmatch(item['resultDigest'])):
            raise ValueError('Invalid scoped draft response')

    if args.action == 'list':
        if (value.get('format') != 'hosting-application-draft-list/1'
                or value.get('environmentId') != args.environment or value.get('consistency') != 'LIVE_PAGE'
                or value.get('executionAuthorized') is not False or not isinstance(value.get('items'), list)
                or len(value['items']) > args.limit):
            raise ValueError('Invalid draft listing')
        latest = value.get('latestGeneration')
        if latest is not None and (type(latest) is not int or not 1 <= latest <= _MAX):
            raise ValueError('Invalid listing source generation')
        previous = args.after or ''
        for item in value['items']:
            name = item.get('applicationGroupId') if isinstance(item, dict) else None
            if not isinstance(name, str) or not _ID.fullmatch(name) or name <= previous or 'proposal' in item:
                raise ValueError('Invalid draft summary order')
            revision(item, name)
            if item['latestGeneration'] != value.get('latestGeneration'):
                raise ValueError('Inconsistent listing source')
            previous = name
        if value.get('nextAfter') is not None and (len(value['items']) != args.limit
                or value['nextAfter'] != previous):
            raise ValueError('Invalid draft listing cursor')
    else:
        revision(value, args.id)
        if args.action == 'get' and args.revision is not None and value['revision'] != args.revision:
            raise ValueError('Historical draft revision differs')
        if args.action == 'save':
            if (value['revision'] != args.expected_revision+1 or value['generation'] != args.generation
                    or value['resultDigest'] != args.result_digest or not isinstance(submitted, dict)):
                raise ValueError('Saved draft does not acknowledge the exact requested revision')
            proposal = value.get('proposal')
            if (not isinstance(proposal, dict) or proposal.get('format') != 'hosting-application-group-candidate/1'
                    or proposal.get('discoveryDigest') != args.result_digest
                    or proposal.get('scope') != value.get('scope')):
                raise ValueError('Saved proposal does not bind its source')
            # The server canonicalizes UTC spellings, but may not drop or alter
            # assertions. Compare against the frozen request, never reread a file
            # that might have changed while the PUT was in flight.
            def content(document):
                edges = document.get('dependencies')
                if not isinstance(edges, list):
                    raise ValueError('Saved dependencies are missing')
                normalized = []
                for edge in edges:
                    if not isinstance(edge, dict) or not isinstance(edge.get('observedAt'), str):
                        raise ValueError('Saved assertion has no timestamp')
                    stamp = datetime.fromisoformat(edge['observedAt'])
                    if stamp.tzinfo is None or stamp.utcoffset() != timedelta(0):
                        raise ValueError('Saved assertion is not UTC')
                    normalized.append({**edge, 'observedAt': stamp.isoformat()})
                return {'draft': document.get('draft'), 'dependencies': normalized}
            if content(proposal) != content(submitted):
                raise ValueError('Saved proposal differs from the submitted content')


def save_unknown(args, document):
    raw = json.dumps(document, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                     allow_nan=False).encode('ascii')
    return {'error': 'APPLICATION_DRAFT_SAVE_UNKNOWN', 'environmentId': args.environment,
            'applicationGroupId': args.id, 'expectedRevision': args.expected_revision,
            'generation': args.generation, 'resultDigest': args.result_digest,
            'requestDigest': hashlib.sha256(raw).hexdigest(), 'executionAuthorized': False,
            'reconciliationRequired': True}


def _validate_review_response(args, value):
    """Check the read contract, not signatures or native/application eligibility.

    Only the API can load current trust and retained observation evidence. A
    consistent response is a status at checkedAt, never a cached approval, an
    ownership transfer or a decision the thin client may issue itself.
    """
    fields = {'format', 'environmentId', 'scope', 'applicationGroupId', 'draftRevision',
        'draftRecordDigest', 'proposalDigest', 'generation', 'resultDigest', 'latestGeneration',
        'latestDraftRevision', 'checkedAt', 'status', 'ownerDecision', 'ownerId',
        'reviewReference', 'evidenceId', 'evidenceRevision', 'evidenceDigest', 'reviewedAt',
        'expiresAt', 'candidateDigest', 'unknownDependencyCount', 'dependencyEvidenceVerified',
        'ownershipAccepted', 'executionAuthorized'}
    statuses = {'UNREVIEWED', 'REVOKED', 'HELD_SUPERSEDED_DRAFT', 'HELD_SUPERSEDED_INVENTORY',
        'HELD_INCOMPLETE_INVENTORY', 'HELD_STALE_INVENTORY',
        'REVIEWED_ASSESSMENT_ONLY', 'REVIEWED_WITH_UNKNOWNS'}

    def integer(item):
        return type(item) is int and 1 <= item <= _MAX

    def sha(item):
        return isinstance(item, str) and _SHA.fullmatch(item) is not None

    def stamp(item):
        if (not isinstance(item, str) or len(item) > 40
                or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}'
                                    r'(?:\.[0-9]{1,6})?(?:Z|\+00:00)', item)):
            raise ValueError('Invalid review time')
        parsed = datetime.fromisoformat(item)
        if parsed.utcoffset() != timedelta(0):
            raise ValueError('Review time must be UTC')
        return parsed

    if (not isinstance(value, dict) or set(value) != fields
            or value['format'] != 'hosting-application-review-status/1'
            or value['environmentId'] != args.environment or value['applicationGroupId'] != args.id
            or not isinstance(value['status'], str) or value['status'] not in statuses
            or not all(integer(value[key]) for key in ('draftRevision', 'generation',
                                                        'latestGeneration', 'latestDraftRevision'))
            or value['draftRevision'] != args.revision
            or value['latestGeneration'] < value['generation']
            or value['latestDraftRevision'] < value['draftRevision']
            or not all(sha(value[key]) for key in ('draftRecordDigest', 'proposalDigest', 'resultDigest'))
            or args.record_digest is not None and value['draftRecordDigest'] != args.record_digest
            or any(value[key] is not False for key in ('dependencyEvidenceVerified',
                                                       'ownershipAccepted', 'executionAuthorized'))):
        raise ValueError('Invalid exact-draft review response')
    scope = value['scope']
    identity_fields = {'organization_id', 'tenant_id', 'site_id', 'security_domain_id', 'endpoint_id'}
    if (not isinstance(scope, dict) or set(scope) != identity_fields | {'native_scope_id', 'platform_family'}
            or any(not isinstance(scope[key], str) or not _ID.fullmatch(scope[key]) for key in identity_fields)
            or not isinstance(scope['platform_family'], str)
            or scope['platform_family'] not in {'vmware', 'nutanix', 'openstack'}
            or not isinstance(scope['native_scope_id'], str) or not 1 <= len(scope['native_scope_id']) <= 512
            or not scope['native_scope_id'].strip()
            or any(ord(c) < 32 or ord(c) == 127 for c in scope['native_scope_id'])):
        raise ValueError('Invalid review scope')
    checked = stamp(value['checkedAt'])
    decision = value['ownerDecision']
    evidence_fields = ('ownerId', 'reviewReference', 'evidenceId', 'evidenceRevision',
                       'evidenceDigest', 'reviewedAt', 'expiresAt')
    if decision is None:
        if any(value[key] is not None for key in evidence_fields):
            raise ValueError('Unreviewed input cannot carry signed-decision claims')
    elif isinstance(decision, str) and decision in {'ACCEPT_FOR_ASSESSMENT', 'REVOKE'}:
        if (any(not isinstance(value[key], str) or not _ID.fullmatch(value[key])
                for key in ('ownerId', 'reviewReference', 'evidenceId'))
                or not integer(value['evidenceRevision']) or not sha(value['evidenceDigest'])):
            raise ValueError('Invalid review evidence identity')
        reviewed, expires = stamp(value['reviewedAt']), stamp(value['expiresAt'])
        if not reviewed <= checked < expires or expires - reviewed > timedelta(hours=1):
            raise ValueError('Review validity does not cover its evaluation')
    else:
        raise ValueError('Invalid owner decision')
    status = value['status']
    candidate = status in {'REVIEWED_ASSESSMENT_ONLY', 'REVIEWED_WITH_UNKNOWNS'}
    if candidate:
        count = value['unknownDependencyCount']
        if (decision != 'ACCEPT_FOR_ASSESSMENT' or not sha(value['candidateDigest'])
                or type(count) is not int or not 0 <= count <= 500
                or (status == 'REVIEWED_WITH_UNKNOWNS') != (count > 0)):
            raise ValueError('Review candidate or unknown count is inconsistent')
    elif value['candidateDigest'] is not None or value['unknownDependencyCount'] is not None:
        raise ValueError('Held or unreviewed input cannot carry a candidate')
    # Enforce wire-state consistency only; do not reconstruct a candidate or
    # reinterpret native completeness, freshness or dependency evidence here.
    if decision == 'REVOKE':
        valid = status == 'REVOKED'
    elif value['latestDraftRevision'] != value['draftRevision']:
        valid = status == 'HELD_SUPERSEDED_DRAFT'
    elif value['latestGeneration'] != value['generation']:
        valid = status == 'HELD_SUPERSEDED_INVENTORY'
    elif decision is None:
        valid = status == 'UNREVIEWED'
    else:
        valid = candidate or status in {'HELD_INCOMPLETE_INVENTORY', 'HELD_STALE_INVENTORY'}
    if not valid:
        raise ValueError('Review status contradicts its source or decision')
