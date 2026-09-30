"""Thin enterprise operator CLI for the authenticated control API.

This command never reads PostgreSQL or calls a platform adapter. The operator
supplies a short-lived SSO access token through stdin; it is not accepted as a
command-line argument, put in a URL, written to a file, or echoed in errors.
The API independently verifies the token and all scoped authority.
"""
from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
from collections.abc import Callable
from pathlib import Path
from typing import IO
from urllib.parse import quote, urlsplit

import httpx
import certifi

from . import application_drafts, assessments

_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$')
_DISCOVERY_CURSOR = re.compile(r'^[A-Za-z0-9_-]{1,4096}$')
_MAX_GENERATION = 2**63 - 1
_MAX_DOCUMENT = 1024 * 1024
_MAX_RESPONSE = 8 * 1024 * 1024



def _identity(value: str) -> str:
    if not _ID.fullmatch(value):
        raise ValueError('Identity must be a 1–128 character platform ID')
    return quote(value, safe='')


def _discovery_after(value: str) -> str:
    # Treat the server cursor as an opaque query value, never as a URL/path.
    if not isinstance(value, str) or _DISCOVERY_CURSOR.fullmatch(value) is None:
        raise ValueError('Invalid bounded discovery cursor')
    return value


def _base_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        if (not value or value != value.strip() or parsed.username is not None
                or parsed.password is not None or parsed.query or parsed.fragment
                or not parsed.hostname or parsed.port == 0):
            raise ValueError
        if parsed.scheme != 'https':
            raise ValueError
        if '//' in parsed.path or '..' in parsed.path.split('/'):
            raise ValueError
    except ValueError:
        raise ValueError('API URL must be HTTPS without credentials, query or fragment') from None
    return value.rstrip('/')


def _token(source: IO[str]) -> str:
    value = source.readline(16386)
    token = value.rstrip('\r\n')
    if (not token or len(token) > 16384 or token != token.strip()
            or '\r' in token or '\n' in token):
        raise ValueError('A bounded SSO access token is required on stdin')
    return token


def _document(path: str) -> dict:
    target = Path(path)
    if target.stat().st_size > _MAX_DOCUMENT:
        raise ValueError('Workload document exceeds the API request limit')
    raw = target.read_bytes()
    if len(raw) > _MAX_DOCUMENT:
        raise ValueError('Workload document exceeds the API request limit')
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise ValueError('Workload file must contain one JSON object') from None
    if not isinstance(value, dict):
        raise ValueError('Workload file must contain one JSON object')
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='hosting-operator',
        description='Inspect scoped workloads and submitted jobs through the control API.')
    parser.add_argument('--api-url', required=True, help='HTTPS control API base URL')
    parser.add_argument('--token-stdin', required=True, action='store_true',
                        help='Read one SSO access token line from stdin; never pass it in argv')
    parser.add_argument('--ca-bundle', help='Trusted enterprise PEM CA bundle')
    groups = parser.add_subparsers(dest='resource', required=True)
    application_drafts.install_parser(groups)
    groups.add_parser('scopes', help='Show active authorized WSD and native scopes')

    environments = groups.add_parser('environments',
                                     help='List or declare unverified environment selectors')
    environment_actions = environments.add_subparsers(dest='action', required=True)
    environment_list = environment_actions.add_parser('list')
    environment_list.add_argument('--wsd', required=True)
    environment_list.add_argument('--limit', type=int, default=50)
    environment_list.add_argument('--after')
    environment_get = environment_actions.add_parser('get')
    environment_get.add_argument('--id', required=True)
    environment_register = environment_actions.add_parser('register')
    environment_register.add_argument('--file', required=True,
                                      help='Unverified selector JSON without status')

    discovery = groups.add_parser('discovery',
                                  help='Browse read-only inventory generations and objects')
    discovery_actions = discovery.add_subparsers(dest='action', required=True)
    generations = discovery_actions.add_parser('generations')
    generations.add_argument('--environment', required=True)
    generations.add_argument('--after', type=int, default=0)
    generations.add_argument('--limit', type=int, default=50)
    objects = discovery_actions.add_parser('objects')
    objects.add_argument('--environment', required=True)
    objects.add_argument('--generation', type=int, required=True)
    objects.add_argument('--after', help='Opaque nextAfter value from the API')
    objects.add_argument('--limit', type=int, default=50)

    assessments.install_parser(groups)

    workloads = groups.add_parser('workloads', help='Browse or submit planned workload records')
    workload_actions = workloads.add_subparsers(dest='action', required=True)
    listing = workload_actions.add_parser('list')
    listing.add_argument('--wsd', required=True)
    listing.add_argument('--limit', type=int, default=50)
    listing.add_argument('--after')
    one = workload_actions.add_parser('get')
    one.add_argument('--wsd', required=True)
    one.add_argument('--id', required=True)
    created = workload_actions.add_parser('create')
    created.add_argument('--wsd', required=True)
    created.add_argument('--file', required=True, help='Canonical planned Workload JSON file')

    jobs = groups.add_parser('jobs', help='Submit an approved plan or read real job progress')
    job_actions = jobs.add_subparsers(dest='action', required=True)
    submit = job_actions.add_parser('submit')
    submit.add_argument('--plan', required=True)
    submit.add_argument('--idempotency-key', required=True,
                        help='Stable key retained by the operator for safe retries')
    get = job_actions.add_parser('get')
    get.add_argument('--id', required=True)
    events = job_actions.add_parser('events')
    events.add_argument('--id', required=True)
    events.add_argument('--after', type=int, default=0)
    events.add_argument('--limit', type=int, default=50)

    plans = groups.add_parser('plans', help='Review the current scoped migration decision')
    plan_actions = plans.add_subparsers(dest='action', required=True)
    review = plan_actions.add_parser('review')
    review.add_argument('--id', required=True)

    approvals = groups.add_parser('approvals',
                                  help='Record or revoke an independently verified plan approval')
    approval_actions = approvals.add_subparsers(dest='action', required=True)
    approved = approval_actions.add_parser('record')
    approved.add_argument('--plan', required=True)
    approved.add_argument('--role', required=True,
                          choices=('SOURCE_OWNER', 'DESTINATION_OWNER',
                                   'SOURCE_SECURITY', 'DESTINATION_SECURITY'))
    approved.add_argument('--ttl-seconds', type=int, required=True)
    approved.add_argument('--expected-revision', type=int, required=True,
                          help='Revision shown by plans review')
    approved.add_argument('--expected-digest', required=True,
                          help='Digest shown by plans review')
    revoked = approval_actions.add_parser('revoke')
    revoked.add_argument('--plan', required=True)
    revoked.add_argument('--reason', required=True)
    return parser


def _request(args) -> tuple[str, str, dict | None, dict | None]:
    """Map CLI verbs to the same API operations used by the portal."""
    if args.resource == 'application-drafts':
        return application_drafts.request(args, _identity)
    if args.resource == 'scopes':
        return 'GET', '/v1/access/scopes', None, None
    if args.resource == 'assessments':
        return assessments.request(args, _identity)
    if args.resource == 'environments':
        if args.action == 'get':
            return 'GET', '/v1/environments/' + _identity(args.id), None, None
        if args.action == 'register':
            return 'POST', '/v1/environments', None, _document(args.file)
        if not 1 <= args.limit <= 100:
            raise ValueError('Limit must be between 1 and 100')
        params = {'wsdId': _identity(args.wsd), 'limit': args.limit}
        if args.after:
            params['after'] = _identity(args.after)
        return 'GET', '/v1/environments', params, None
    if args.resource == 'discovery':
        prefix = '/v1/environments/' + _identity(args.environment)
        if not 1 <= args.limit <= 100:
            raise ValueError('Discovery limit must be between 1 and 100')
        if args.action == 'generations':
            if not 0 <= args.after <= _MAX_GENERATION:
                raise ValueError('Invalid discovery generation cursor')
            return ('GET', prefix + '/discovery/generations',
                    {'after': args.after, 'limit': args.limit}, None)
        if not 1 <= args.generation <= _MAX_GENERATION:
            raise ValueError('Invalid discovery generation')
        params = {'limit': args.limit}
        if args.after is not None:
            params['after'] = _discovery_after(args.after)
        return ('GET', prefix + '/discovery/generations/'
                + str(args.generation) + '/objects', params, None)
    if args.resource == 'plans':
        return 'GET', '/v1/plans/' + _identity(args.id) + '/review', None, None
    if args.resource == 'workloads':
        prefix = '/v1/wsds/' + _identity(args.wsd) + '/workloads'
        if args.action == 'list':
            if not 1 <= args.limit <= 100:
                raise ValueError('Limit must be between 1 and 100')
            params = {'limit': args.limit}
            if args.after:
                params['after'] = _identity(args.after)
            return 'GET', prefix, params, None
        if args.action == 'get':
            return 'GET', prefix + '/' + _identity(args.id), None, None
        return 'POST', prefix, None, _document(args.file)
    if args.resource == 'approvals':
        prefix = '/v1/plans/' + _identity(args.plan)
        if args.action == 'record':
            if not 1 <= args.ttl_seconds <= 28800:
                raise ValueError('Approval TTL must be between 1 and 28800 seconds')
            if args.expected_revision < 1 or not re.fullmatch(r'[0-9a-f]{64}', args.expected_digest):
                raise ValueError('A reviewed plan revision and digest are required')
            return 'POST', prefix + '/approvals', None, {
                'role': args.role, 'ttlSeconds': args.ttl_seconds,
                'expectedPlanRevision': args.expected_revision,
                'expectedPlanDigest': args.expected_digest}
        if (not 1 <= len(args.reason) <= 512
                or any(ord(char) < 32 or ord(char) == 127 for char in args.reason)):
            raise ValueError('Revocation reason must be one bounded line')
        return 'POST', prefix + '/revoke', None, {'reason': args.reason}
    if args.action == 'submit':
        _identity(args.idempotency_key)
        return 'POST', '/v1/plans/' + _identity(args.plan) + '/jobs', None, None
    prefix = '/v1/jobs/' + _identity(args.id)
    if args.action == 'get':
        return 'GET', prefix, None, None
    if args.after < 0 or not 1 <= args.limit <= 100:
        raise ValueError('Progress cursor or limit is invalid')
    return 'GET', prefix + '/events', {'after': args.after, 'limit': args.limit}, None


def _read_response(response: httpx.Response, *, strict: bool = False,
                   maximum: int | None = None) -> dict:
    maximum = min(_MAX_RESPONSE, maximum) if maximum is not None else _MAX_RESPONSE
    size = 0
    chunks = []
    for chunk in response.iter_bytes():
        size += len(chunk)
        if size > maximum:
            raise ValueError('API response exceeds the CLI size limit')
        chunks.append(chunk)
    if strict:
        return application_drafts.decode_document(b''.join(chunks), maximum)
    try:
        payload = json.loads(b''.join(chunks))
    except (ValueError, UnicodeDecodeError):
        raise ValueError('API returned an invalid JSON response') from None
    if not isinstance(payload, dict):
        raise ValueError('API returned an invalid JSON response')
    return payload


def run(argv: list[str] | None = None, *, stdin: IO[str] = sys.stdin,
        stdout: IO[str] = sys.stdout, stderr: IO[str] = sys.stderr,
        transport: httpx.BaseTransport | None = None) -> int:
    args = build_parser().parse_args(argv)
    draft_save_attempted = False
    draft_request_started = False
    comparison_started = False
    application_compare = args.resource == 'assessments' and args.action == 'compare-application'
    document = None
    try:
        base = _base_url(args.api_url)
        method, path, params, document = _request(args)
        credential = _token(stdin)
        # An explicit context avoids inherited SSLKEYLOGFILE even when HTTPX
        # would otherwise build its own environment-sensitive default context.
        verify = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        verify.minimum_version = ssl.TLSVersion.TLSv1_2
        verify.verify_flags |= ssl.VERIFY_X509_STRICT | ssl.VERIFY_X509_PARTIAL_CHAIN
        verify.load_verify_locations(cafile=args.ca_bundle or certifi.where())
        headers = {'Authorization': 'Bearer ' + credential, 'Accept': 'application/json'}
        if application_compare or args.resource == 'application-drafts' and args.action == 'review':
            headers['Cache-Control'] = 'no-store'
        if args.resource == 'jobs' and args.action == 'submit':
            headers['Idempotency-Key'] = args.idempotency_key
        with httpx.Client(timeout=httpx.Timeout(10.0, connect=5.0),
                          follow_redirects=False, trust_env=False, verify=verify,
                          transport=transport) as client:
            comparison_started = application_compare
            draft_request_started = args.resource == 'application-drafts'
            draft_save_attempted = draft_request_started and args.action == 'save'
            with client.stream(method, base + path, params=params,
                               headers=headers, json=document) as response:
                payload = _read_response(response, strict=application_compare or args.resource == 'application-drafts',
                    maximum=assessments.MAX_RESPONSE_BYTES if application_compare else None)
                status = response.status_code
        conflict = (status == 409 and isinstance(payload.get('error'), dict)
                    and payload['error'].get('code') == 'APPLICATION_DRAFT_CONFLICT')
        # Even 404 may follow a committed PUT if authority is revoked before
        # the API's response readback. Only an exact ACK proves this save.
        if draft_save_attempted and status != 200 and not conflict:
            print(json.dumps(application_drafts.save_unknown(args, document)), file=stderr)
            return 3
        if not 200 <= status < 300:
            error = payload.get('error')
            code = error.get('code') if isinstance(error, dict) else None
            if not isinstance(code, str) or not re.fullmatch(r'[A-Z][A-Z0-9_]{0,63}', code):
                code = 'API_REFUSED'
            print(json.dumps({'status': status, 'error': code}),
                  file=stderr)
            return 2
        if args.resource == 'application-drafts':
            if status != 200:
                raise ValueError('Draft response is not an exact acknowledgement')
            application_drafts.validate_response(args, payload, submitted=document)
        if application_compare:
            if status != 200:
                raise ValueError('Application comparison requires an exact response')
            application_drafts.validate_response(argparse.Namespace(action='review',
                environment=args.source_environment, id=args.application_group, revision=args.draft_revision,
                record_digest=args.draft_record_digest), payload.get('applicationReview'))
            assessments.validate_application_response(document, payload)
        print(json.dumps(payload, sort_keys=True, separators=(',', ':')),
              file=stdout)
        return 0
    except KeyboardInterrupt:
        outcome = (application_drafts.save_unknown(args, document) if draft_save_attempted
                   else {'error': 'INTERRUPTED'})
        print(json.dumps(outcome), file=stderr)
        return 130
    except (ValueError, OSError, httpx.HTTPError) as exc:
        # Do not print transport URLs, request bodies or the token: exception
        # strings may include those, particularly from a proxy/TLS stack.
        if draft_save_attempted:
            print(json.dumps(application_drafts.save_unknown(args, document)), file=stderr)
            return 3
        if comparison_started and isinstance(exc, ValueError):
            code = 'APPLICATION_COMPARISON_RESPONSE_INVALID'
        elif draft_request_started and isinstance(exc, ValueError):
            code = 'APPLICATION_DRAFT_RESPONSE_INVALID'
        else:
            code = 'INVALID_INPUT' if isinstance(exc, (ValueError, OSError)) else 'API_UNAVAILABLE'
        print(json.dumps({'error': code}), file=stderr)
        return 3


def main(argv: list[str] | None = None) -> int:
    return run(argv)


if __name__ == '__main__':
    raise SystemExit(main())
