"""One authenticated metadata read, not native collection or a health authority."""
from copy import deepcopy
from contextlib import redirect_stderr
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from io import StringIO
import json
import unittest

import httpx
from provisioner.cli import discovery, operator

NOW = datetime(2026, 9, 30, 12, tzinfo=timezone.utc)
BASE = ['--api-url', 'https://control.example', '--token-stdin',
        'discovery', 'freshness', '--environment', 'env-01']


def report(age=60_000_000, *, completeness='COMPLETE', errors=0, privileges=0,
           missing=False, refresh=3600, maximum=86400, count=3):
    observation = None if missing else {
        'generation': 7, 'campaignId': 'campaign-01',
        'authorizationDigest': 'a'*64, 'resultDigest': 'b'*64,
        'capturedAt': (NOW-timedelta(microseconds=age)).isoformat(),
        'completeness': completeness, 'objectCount': count,
        'collectionErrorCount': errors, 'missingPrivilegeCount': privileges}
    freshness = 'MISSING' if missing else 'FUTURE_CAPTURE' if age < 0 else (
        'STALE' if age > maximum*1_000_000 else 'FRESH')
    due = missing or age < 0 or age >= refresh*1_000_000
    issues = []
    if missing:
        issues.append('INVENTORY_MISSING')
    elif age < 0:
        issues.append('INVENTORY_CAPTURE_IN_FUTURE')
    elif freshness == 'STALE':
        issues.append('INVENTORY_STALE')
    elif due:
        issues.append('INVENTORY_REFRESH_DUE')
    if not missing:
        if completeness != 'COMPLETE':
            issues.append('COLLECTION_' + completeness)
        if errors:
            issues.append('COLLECTION_ERRORS_PRESENT')
        if privileges:
            issues.append('MISSING_PRIVILEGES')
    issues.append('NATIVE_VISIBILITY_UNVERIFIED')
    return {'format': 'hosting-discovery-freshness/1', 'environmentId': 'env-01',
        'scope': dict(organization_id='org', tenant_id='tenant', site_id='site',
            security_domain_id='wsd', endpoint_id='vcenter', native_scope_id='folder', platform_family='vmware'),
        'checkedAt': NOW.isoformat(),
        'policy': {'format': 'hosting-discovery-freshness-policy/1',
                   'refreshAfterSeconds': refresh, 'maxAgeSeconds': maximum},
        'observation': observation, 'freshness': freshness,
        'ageMicroseconds': None if missing or age < 0 else age, 'refreshDue': due, 'issues': issues,
        'consistency': 'LIVE_METADATA_RECHECKS', 'integrityVerification': 'METADATA_ONLY',
        'nativeVisibilityVerified': False, 'collectionRequested': False, 'executionAuthorized': False}


def run(value=None, *, check=False, status=200, raw=None, headers=None, handler=None, args=None, token='synthetic-token'):
    calls, out, err = [], StringIO(), StringIO()
    def respond(request):
        calls.append(request)
        if handler is not None:
            return handler(request)
        return httpx.Response(status, content=(json.dumps(value).encode() if raw is None else raw),
            headers={'Content-Type': 'application/json'} if headers is None else headers)
    code = operator.run((BASE + (['--check'] if check else [])) if args is None else args,
        stdin=StringIO(token+'\n'), stdout=out, stderr=err,
        transport=httpx.MockTransport(respond))
    return code, out.getvalue(), err.getvalue(), calls


class FreshnessCliTests(unittest.TestCase):
    def test_inspection_is_one_get_without_query_or_collection_side_effect(self):
        value = report()
        code, out, err, calls = run(value)
        self.assertEqual((code, err), (0, ''))
        self.assertEqual(json.loads(out), value)
        self.assertEqual(len(calls), 1)
        req = calls[0]
        self.assertEqual(req.method, 'GET')
        self.assertEqual(str(req.url), 'https://control.example/v1/environments/env-01/discovery/freshness')
        self.assertEqual(req.content, b'')
        self.assertEqual(req.headers['cache-control'], 'no-store')
        self.assertEqual(req.headers['accept-encoding'], 'identity')
        self.assertEqual(req.headers['authorization'], 'Bearer synthetic-token')
        self.assertNotIn('synthetic-token', out+err)

    def test_check_success_retains_unverified_visibility_and_metadata_only_limit(self):
        value = report()
        code, out, err, _ = run(value, check=True)
        self.assertEqual((code, err), (0, ''))
        self.assertEqual(json.loads(out), value)
        self.assertIn('NATIVE_VISIBILITY_UNVERIFIED', value['issues'])

    def test_valid_unhealthy_inspections_are_read_success_but_check_exit_four(self):
        for value in (report(missing=True), report(-1), report(86400_000_001),
                      report(3600_000_000), report(completeness='PARTIAL'),
                      report(completeness='UNKNOWN', errors=2, privileges=1)):
            with self.subTest(state=value['freshness'], quality=value.get('observation')):
                for check, expected in ((False, 0), (True, 4)):
                    code, out, err, calls = run(value, check=check)
                    self.assertEqual((code, err), (expected, ''))
                    self.assertEqual(json.loads(out), value)
                    self.assertEqual(len(calls), 1)

    def test_complete_empty_inventory_is_not_missing(self):
        self.assertEqual(run(report(count=0), check=True)[0], 0)
        self.assertEqual(run(report(missing=True), check=True)[0], 4)

    def test_exact_refresh_and_maximum_age_boundaries_use_microseconds(self):
        for age, state, code in ((3599_999_999, 'FRESH', 0), (3600_000_000, 'FRESH', 4),
                                 (86400_000_000, 'FRESH', 4), (86400_000_001, 'STALE', 4),
                                 (-1, 'FUTURE_CAPTURE', 4), (0, 'FRESH', 0)):
            value = report(age)
            self.assertEqual(value['freshness'], state)
            self.assertEqual(run(value, check=True)[0], code)

    def test_server_policy_is_used_without_client_threshold_overrides(self):
        for age, code in ((999_999, 0), (1_000_000, 4), (2_000_001, 4)):
            self.assertEqual(run(report(age, refresh=1, maximum=2), check=True)[0], code)
        for extra in (['--max-age', '999999'], ['--refresh'], ['--generation', '1'], ['--after', '0']):
            with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
                operator.build_parser().parse_args(BASE + extra)

    def test_age_above_javascript_safe_integer_is_preserved_exactly(self):
        value = report(2**53+1)
        code, out, _, _ = run(value, check=True)
        self.assertEqual(code, 4)
        self.assertEqual(json.loads(out)['ageMicroseconds'], 2**53+1)

    def test_equivalent_utc_spelling_and_issue_order_do_not_change_semantics(self):
        value = report(completeness='PARTIAL', privileges=1)
        value['checkedAt'] = value['checkedAt'].replace('+00:00', 'Z')
        value['observation']['capturedAt'] = value['observation']['capturedAt'].replace('+00:00', '.000000Z')
        value['issues'].reverse()
        self.assertEqual(run(value, check=True)[0], 4)

    def test_envelope_scope_and_authority_confusion_are_rejected(self):
        mutations = [(('format',), 'hosting-discovery-freshness/0'), (('environmentId',), 'other'),
                     (('scope', 'tenant_id'), ''), (('scope', 'platform_family'), 'unknown'),
                     (('scope',), []), (('consistency',), 'ATOMIC'),
                     (('integrityVerification',), 'VERIFIED')]
        mutations += [((key,), val) for key in ('nativeVisibilityVerified', 'collectionRequested',
                      'executionAuthorized') for val in (True, 0, None)]
        self.assert_mutations_fail(mutations)

    def test_closed_fields_reject_missing_or_injected_payload_data(self):
        for location in ((), ('scope',), ('policy',), ('observation',)):
            value = report(); obj = value
            for key in location:
                obj = obj[key]
            obj['injected'] = 'sensitive native body'
            self.assert_invalid(value)
        for key in report():
            value = report(); del value[key]
            self.assert_invalid(value)

    def test_observation_ids_counts_and_hashes_are_typed_and_bounded(self):
        mutations = [(('observation', key), bad) for key, bads in {
            'generation': [0, True, 2**63, '7'], 'campaignId': ['', []],
            'resultDigest': ['g'*64, 'A'*64], 'authorizationDigest': [None],
            'objectCount': [-1, True, 2**63], 'collectionErrorCount': [-1, 1025, True],
            'missingPrivilegeCount': [1025, 0.0], 'completeness': ['GOOD', []]
        }.items() for bad in bads]
        self.assert_mutations_fail(mutations)

    def test_complete_observation_cannot_carry_collection_errors(self):
        self.assert_invalid(report(errors=1))
        self.assert_invalid(report(privileges=1))

    def test_report_cannot_change_age_due_or_freshness_independently(self):
        self.assert_mutations_fail([(('ageMicroseconds',), x) for x in (None, True, 0, 60_000_000.0)])
        self.assert_mutations_fail([(('refreshDue',), x) for x in (True, None, 0)])
        self.assert_mutations_fail([(('freshness',), x) for x in ('MISSING', 'STALE', 'FUTURE_CAPTURE')])
        for value in (report(-1), report(missing=True)):
            value['ageMicroseconds'] = 0
            self.assert_invalid(value)

    def test_missing_or_duplicate_or_invented_issue_codes_are_rejected(self):
        self.assert_mutations_fail([(('issues',), x) for x in ([], ['NATIVE_VISIBILITY_UNVERIFIED']*2,
            ['APPROVED'], [{'code': 'NATIVE_VISIBILITY_UNVERIFIED'}])])
        value = report(completeness='PARTIAL'); value['issues'].remove('COLLECTION_PARTIAL')
        self.assert_invalid(value)

    def test_bad_or_weakened_server_policy_is_rejected(self):
        self.assert_mutations_fail([(('policy', key), bad) for key, bads in {
            'format': ['changed'], 'refreshAfterSeconds': [0, True, 604801],
            'maxAgeSeconds': [0, 3599, True, 604801, '86400']}.items() for bad in bads])

    def test_invalid_or_non_utc_or_overprecise_timestamps_are_rejected(self):
        invalid = ('2026-09-31T12:00:00Z', '2026-09-30', '2026-09-30T12:00:00',
                   '2026-09-30T12:00:00-00:00', '2026-09-30T13:00:00+01:00',
                   '2026-09-30T12:00:00.1234567Z', '2026-09-30T12:00:00Z\n', None, 0)
        self.assert_mutations_fail([(path, value) for path in (('checkedAt',), ('observation', 'capturedAt'))
                                   for value in invalid])

    def test_non_exact_http_success_never_becomes_a_healthy_check(self):
        for status in (201, 202, 204, 206):
            code, out, err, calls = run(report(), check=True, status=status)
            self.assertEqual((code, out), (3, ''))
            self.assertEqual(json.loads(err)['error'], 'DISCOVERY_FRESHNESS_RESPONSE_INVALID')
            self.assertEqual(len(calls), 1)

    def test_api_denial_or_changed_inventory_does_not_retry_or_print_metadata(self):
        for status in (401, 403, 404, 409, 503, 302):
            code, out, err, calls = run({'error': {'code': 'DISCOVERY_FRESHNESS_CHANGED',
                'message': 'do not print this secret'}}, status=status, check=True)
            self.assertEqual((code, out), (2, ''))
            self.assertNotIn('secret', err)
            self.assertEqual(len(calls), 1)

    def test_invalid_json_utf8_depth_and_numeric_overflow_are_refused(self):
        good = json.dumps(report()).encode()
        for raw in (good.replace(b'{', b'{"format":"injected",', 1), b'\xff', b'[]',
                    b'{"x":'+b'['*70+b'0'+b']'*70+b'}',
                    good.replace(b'60000000', b'9223372036854775808'),
                    good.replace(b'60000000', b'NaN'), good.replace(b'60000000', b'6e7')):
            self.assertEqual(run(raw=raw, check=True)[:2], (3, ''))

    def test_response_size_encoding_media_type_and_length_are_checked(self):
        cases = ({'Content-Type': 'text/html'}, {},
                 {'Content-Type': 'application/json', 'Content-Encoding': 'gzip'},
                 {'Content-Type': 'application/json', 'Content-Length': '16385'},
                 {'Content-Type': 'application/json', 'Content-Length': '1'},
                 {'Content-Type': 'application/json', 'Content-Length': '-1'})
        for headers in cases:
            code, out, _, _ = run(report(), headers=headers)
            self.assertEqual((code, out), (3, ''))
        self.assertEqual(run(raw=b' ' * 16385)[:2], (3, ''))

    def test_stream_is_closed_when_reply_is_refused(self):
        class Stream(httpx.SyncByteStream):
            closed = False
            def __iter__(self):
                yield b' ' * 16385
            def close(self):
                self.closed = True
        stream = Stream()
        result = run(handler=lambda _: httpx.Response(200, stream=stream,
                     headers={'Content-Type': 'application/json'}))
        self.assertEqual(result[:2], (3, ''))
        self.assertTrue(stream.closed)

    def test_transport_errors_and_interruption_are_redacted_and_not_retried(self):
        for exc, expected in ((httpx.ReadTimeout('synthetic-token'), 3), (KeyboardInterrupt(), 130)):
            def fail(_):
                raise exc
            code, out, err, calls = run(handler=fail, check=True)
            self.assertEqual((code, out), (expected, ''))
            self.assertNotIn('synthetic-token', err)
            self.assertEqual(len(calls), 1)

    def test_invalid_input_is_refused_before_http(self):
        code, out, err, calls = run(report(), args=BASE[:-1]+['bad/environment'])
        self.assertEqual((code, out, len(calls)), (3, '', 0))
        self.assertEqual(json.loads(err)['error'], 'INVALID_INPUT')

    def test_existing_generation_and_object_routes_retain_their_query_contract(self):
        prefix = BASE[:3] + ['discovery']
        for suffix, path in ((['generations', '--environment', 'env-01'],
                             '/v1/environments/env-01/discovery/generations?after=0&limit=50'),
                            (['objects', '--environment', 'env-01', '--generation', '7', '--after', 'abc_-'],
                             '/v1/environments/env-01/discovery/generations/7/objects?limit=50&after=abc_-')):
            code, _, _, calls = run({'items': []}, args=prefix+suffix)
            self.assertEqual(code, 0)
            self.assertEqual(calls[0].url.raw_path.decode(), path)

    def assert_mutations_fail(self, mutations):
        for keys, bad in mutations:
            with self.subTest(keys=keys, bad=bad):
                value = report(); target = value
                for key in keys[:-1]:
                    target = target[key]
                target[keys[-1]] = bad
                self.assert_invalid(value)

    def assert_invalid(self, value):
        before = deepcopy(value)
        code, out, err, _ = run(value, check=True)
        self.assertEqual((code, out), (3, ''))
        self.assertEqual(json.loads(err)['error'], 'DISCOVERY_FRESHNESS_RESPONSE_INVALID')
        self.assertEqual(value, before)


class FreshnessApiCliTests(unittest.TestCase):
    def setUp(self):
        from types import SimpleNamespace
        from fastapi.testclient import TestClient
        from provisioner.controlplane.api import create_app
        from provisioner.controlplane.authority.service import AuthorityService
        from provisioner.controlplane.discovery.persistence import DiscoveryRepository, StoredGeneration
        from provisioner.controlplane.persistence.environments import EnvironmentDeclaration, RegisteredEnvironment
        from tests.provisioning.api.test_http import (
            NOW as at, SOURCE_SCOPE, _Identity, _Plans, _Ledger, _Records, _Jobs, _Environments, _VerifiedEvidence)
        class Rows(DiscoveryRepository):
            def __init__(self, value):
                self.values, self.reads, self.after_read = (value,), 0, None
            def latest_generation(self, *args):
                value = self.values[0]
                self.reads += 1
                if self.after_read:
                    self.after_read(self.reads)
                return value
        identities, environments = _Identity(), _Environments()
        declaration = EnvironmentDeclaration('env-01', 'Source', SOURCE_SCOPE)
        environments.rows[(SOURCE_SCOPE.organization_id, SOURCE_SCOPE.tenant_id, 'env-01')] = (
            RegisteredEnvironment(declaration, 'operator', declaration.digest(), at))
        repository = Rows(StoredGeneration('env-01', 7, 'campaign-01', SOURCE_SCOPE,
            'a'*64, 'b'*64, at-timedelta(seconds=60), 'COMPLETE', (), (), 3))
        authority = AuthorityService(identities, _Plans(), _Ledger(), clock=lambda: at)
        client = TestClient(create_app(_Records(), authority, _Jobs(), environments,
            discovery=repository, evidence_gate=_VerifiedEvidence(), clock=lambda: at))
        self.addCleanup(client.close)
        self.fixture = SimpleNamespace(client=client, repository=repository, identities=identities)

    def invoke(self, check=True):
        def actual(request):
            reply = self.fixture.client.request(request.method, request.url.raw_path.decode(),
                headers=dict(request.headers), content=request.content)
            return httpx.Response(reply.status_code, content=reply.content, headers=reply.headers)
        return run(check=check, handler=actual, token='operator')

    def test_cli_consumes_the_actual_authenticated_api_and_two_metadata_reads(self):
        code, out, err, calls = self.invoke()
        self.assertEqual((code, err, len(calls)), (0, '', 1))
        self.assertEqual(self.fixture.repository.reads, 2)
        self.assertEqual(json.loads(out)['integrityVerification'], 'METADATA_ONLY')

    def test_actual_missing_stale_and_partial_rows_have_distinct_health_signals(self):
        original = self.fixture.repository.values[0]
        for row in (None, replace(original, captured_at=original.captured_at-timedelta(days=2)),
                    replace(original, completeness='PARTIAL', missing_privileges=('restricted',))):
            self.fixture.repository.values = (row,)
            self.fixture.repository.reads = 0
            code, out, err, calls = self.invoke()
            self.assertEqual((code, err, len(calls)), (4, '', 1))
            self.assertFalse(json.loads(out)['collectionRequested'])
            self.assertEqual(self.fixture.repository.reads, 2)

    def test_revocation_during_actual_api_read_returns_no_freshness_report(self):
        current = self.fixture.identities.tokens['operator']
        def revoke(_):
            self.fixture.identities.tokens['operator'] = replace(current, grants=())
        self.fixture.repository.after_read = revoke
        code, out, err, calls = self.invoke()
        self.assertEqual((code, out, len(calls)), (2, '', 1))
        self.assertEqual(json.loads(err)['status'], 404)
