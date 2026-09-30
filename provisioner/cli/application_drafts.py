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
    drafts = groups.add_parser('application-drafts', help='List, load or save unreviewed application drafts')
    actions = drafts.add_subparsers(dest='action', required=True)
    listing = actions.add_parser('list', help='One live page of latest-revision summaries')
    listing.add_argument('--environment', required=True)
    listing.add_argument('--limit', type=int, default=50)
    listing.add_argument('--after', help='Last applicationGroupId from the previous page')
    get = actions.add_parser('get', help='Read the latest or an exact historical draft')
    get.add_argument('--environment', required=True)
    get.add_argument('--id', required=True)
    get.add_argument('--revision', type=int)
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
    if args.action == 'get':
        if args.revision is not None and not 1 <= args.revision <= _MAX:
            raise ValueError('Draft revision is outside its bound')
        return 'GET', path, {'revision': args.revision} if args.revision is not None else None, None
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
