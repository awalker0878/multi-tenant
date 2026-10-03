"""The operator CLI only transports verified-actor calls to the API."""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path

import httpx

from provisioner.cli.operator import run
from tests.provisioning.api.test_http import draft


class OperatorCliTests(unittest.TestCase):
    def invoke(self, command, handler, *, token='opaque-access-token', api_url='https://control.example'):
        stdout, stderr = io.StringIO(), io.StringIO()
        code = run(['--api-url', api_url, '--token-stdin', *command],
                   stdin=io.StringIO(token + '\n'), stdout=stdout, stderr=stderr,
                   transport=httpx.MockTransport(handler))
        return code, stdout.getvalue(), stderr.getvalue()

    def test_scopes_uses_bearer_and_prints_server_response(self):
        def handler(request):
            self.assertEqual(request.url.path, '/v1/access/scopes')
            self.assertEqual(request.headers['Authorization'], 'Bearer opaque-access-token')
            self.assertNotIn('opaque-access-token', str(request.url))
            return httpx.Response(200, json={'items': [{'kind': 'PORTFOLIO',
                                                        'securityDomainId': 'wsd-01'}]})
        code, out, err = self.invoke(['scopes'], handler)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)['items'][0]['securityDomainId'], 'wsd-01')
        self.assertEqual(err, '')
        self.assertNotIn('opaque-access-token', out)

    def test_workload_list_and_create_follow_same_http_contract(self):
        requests = []
        def handler(request):
            requests.append(request)
            if request.method == 'GET':
                self.assertEqual(request.url.path, '/v1/wsds/wsd-01/workloads')
                self.assertEqual(request.url.params['limit'], '2')
                self.assertEqual(request.url.params['after'], 'workload-01')
                return httpx.Response(200, json={'items': [], 'nextAfter': None})
            self.assertEqual(request.url.path, '/v1/wsds/wsd-01/workloads')
            self.assertEqual(json.loads(request.content), draft())
            return httpx.Response(201, json={'record': draft(), 'revision': 1,
                                             'digest': 'a' * 64})
        result = self.invoke(['workloads', 'list', '--wsd', 'wsd-01',
                              '--limit', '2', '--after', 'workload-01'], handler)
        self.assertEqual(result[0], 0)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'workload.json'
            path.write_text(json.dumps(draft()), encoding='utf-8')
            created = self.invoke(['workloads', 'create', '--wsd', 'wsd-01',
                                   '--file', str(path)], handler)
        self.assertEqual(created[0], 0)
        self.assertEqual([request.method for request in requests], ['GET', 'POST'])

    def test_environment_registration_and_read_use_unverified_api_contract(self):
        declaration = {
            'environmentId': 'environment-01', 'displayName': 'Candidate only',
            'siteId': 'site-01', 'securityDomainId': 'wsd-01',
            'endpointId': 'endpoint-01', 'nativeScopeId': 'cluster-01',
            'platformFamily': 'vmware',
        }
        seen = []
        def handler(request):
            seen.append((request.method, request.url.path))
            if request.method == 'POST':
                self.assertEqual(json.loads(request.content), declaration)
                return httpx.Response(201, json=declaration | {
                    'status': 'DECLARED_UNVERIFIED', 'recordDigest': 'a' * 64,
                    'registeredAt': '2026-09-27T12:00:00Z'})
            if request.url.path.endswith('/environment-01'):
                return httpx.Response(200, json=declaration | {'status': 'DECLARED_UNVERIFIED'})
            self.assertEqual(request.url.params['wsdId'], 'wsd-01')
            return httpx.Response(200, json={'items': [declaration | {
                'status': 'DECLARED_UNVERIFIED'}], 'nextAfter': None})
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'environment.json'
            file.write_text(json.dumps(declaration), encoding='utf-8')
            registered = self.invoke(['environments', 'register', '--file', str(file)], handler)
        listed = self.invoke(['environments', 'list', '--wsd', 'wsd-01'], handler)
        selected = self.invoke(['environments', 'get', '--id', 'environment-01'], handler)
        self.assertEqual([registered[0], listed[0], selected[0]], [0, 0, 0])
        self.assertEqual(json.loads(registered[1])['status'], 'DECLARED_UNVERIFIED')
        self.assertEqual(seen, [('POST', '/v1/environments'),
                                ('GET', '/v1/environments'),
                                ('GET', '/v1/environments/environment-01')])

    def test_discovery_generations_and_objects_are_scoped_read_only_calls(self):
        seen = []
        cursor = 'WyJ2bSIsInZtLTEiXQ'
        def handler(request):
            seen.append((request.method, request.url.path,
                         dict(request.url.params)))
            self.assertEqual(request.method, 'GET')
            self.assertEqual(request.content, b'')
            self.assertEqual(request.headers['Authorization'],
                             'Bearer opaque-access-token')
            self.assertNotIn('opaque-access-token', str(request.url))
            if request.url.path.endswith('/generations'):
                return httpx.Response(200, json={
                    'items': [{'generation': 2, 'completeness': 'PARTIAL'}],
                    'nextAfter': 2})
            return httpx.Response(200, json={
                'environmentId': 'environment-01', 'generation': 2,
                'items': [{'nativeId': 'vm-01', 'resourceKind': 'vm'}],
                'nextAfter': None})
        generations = self.invoke([
            'discovery', 'generations', '--environment', 'environment-01',
            '--after', '1', '--limit', '2'], handler)
        objects = self.invoke([
            'discovery', 'objects', '--environment', 'environment-01',
            '--generation', '2', '--after', cursor, '--limit', '10'], handler)
        self.assertEqual((generations[0], objects[0]), (0, 0))
        self.assertEqual(json.loads(generations[1])['items'][0]['completeness'],
                         'PARTIAL')
        self.assertEqual(json.loads(objects[1])['items'][0]['nativeId'], 'vm-01')
        self.assertEqual(seen, [
            ('GET', '/v1/environments/environment-01/discovery/generations',
             {'after': '1', 'limit': '2'}),
            ('GET', '/v1/environments/environment-01/discovery/generations/2/objects',
             {'after': cursor, 'limit': '10'}),
        ])

    def test_discovery_rejects_path_cursor_and_budget_injection_before_http(self):
        def unexpected(_request):
            self.fail('Invalid discovery command must not contact the API')
        for command in (
                ['discovery', 'generations', '--environment', '../foreign'],
                ['discovery', 'generations', '--environment', 'env-01',
                 '--after', '-1'],
                ['discovery', 'generations', '--environment', 'env-01',
                 '--limit', '101'],
                ['discovery', 'objects', '--environment', 'env-01',
                 '--generation', '0'],
                ['discovery', 'objects', '--environment', 'env-01',
                 '--generation', '1', '--after', '../foreign?token=x'],
                ['discovery', 'objects', '--environment', 'env-01',
                 '--generation', '1', '--after', 'a' * 4097]):
            with self.subTest(command=command):
                code, out, err = self.invoke(command, unexpected)
                self.assertEqual(code, 3)
                self.assertEqual(out, '')
                self.assertEqual(json.loads(err), {'error': 'INVALID_INPUT'})
                self.assertNotIn('opaque-access-token', err)

    @staticmethod
    def comparison_command():
        return ['assessments', 'compare', '--source-environment', 'source:01',
                '--source-generation', '7', '--workload-native-id', 'folder/vm:101',
                '--destination', 'target:02', '9', '--destination', 'target-03', '12',
                '--method', 'COLD_VM_CONVERSION', '--guest-profile', 'linux-uefi',
                '--network-mode', 'renumber', '--data-mode', 'image-copy']

    def test_comparison_maps_flags_without_native_tuple_claims_or_json_files(self):
        def handler(request):
            self.assertEqual(request.method, 'POST')
            self.assertEqual(request.url.path, '/v1/assessments/compare')
            self.assertEqual(request.headers['Authorization'], 'Bearer opaque-access-token')
            self.assertNotIn('Idempotency-Key', request.headers)
            self.assertEqual(json.loads(request.content), {
                'source': {'environmentId': 'source:01', 'generation': 7},
                'workloadNativeId': 'folder/vm:101',
                'destinations': [
                    {'environmentId': 'target:02', 'generation': 9,
                     'capacityKind': 'cluster', 'capacityNativeId': 'cluster/path:02'},
                    {'environmentId': 'target-03', 'generation': 12}],
                'method': 'COLD_VM_CONVERSION', 'guestProfile': 'linux-uefi',
                'networkMode': 'renumber', 'dataMode': 'image-copy'})
            return httpx.Response(200, json={'executionAuthorized': False,
                'assessments': [{'status': 'UNKNOWN', 'issues': [
                    {'reason': 'Evidence missing', 'remediation': 'Collect current evidence'}]}]})
        code, output, error = self.invoke(self.comparison_command() + [
            '--capacity', 'target:02', 'cluster', 'cluster/path:02'], handler)
        self.assertEqual(code, 0)
        self.assertEqual(error, '')
        self.assertFalse(json.loads(output)['executionAuthorized'])
        self.assertEqual(json.loads(output)['assessments'][0]['status'], 'UNKNOWN')

    def test_comparison_invalid_or_ambiguous_selection_never_reaches_api(self):
        def unexpected(_request):
            self.fail('Invalid comparison must not contact the API')
        commands = []
        for flag, value in [('--source-generation', '0'), ('--source-generation', str(2**63)),
                            ('--workload-native-id', 'vm\n101'),
                            ('--guest-profile', '../unreviewed')]:
            command = self.comparison_command()
            command[command.index(flag) + 1] = value
            commands.append(command)
        for environment, generation in [('target:02', '13'), ('source:01', '4'),
                                        ('target-04', 'nan'), ('target-04', str(2**63))]:
            commands.append(self.comparison_command() + ['--destination', environment, generation])
        commands.extend(self.comparison_command() + tail for tail in [
            ['--capacity', 'other', 'pool', 'p-01'],
            ['--capacity', 'target:02', 'vm', 'vm-01'],
            ['--capacity', 'target:02', 'pool', 'p-01', '--capacity', 'target:02', 'pool', 'p-02'],
            ['--capacity', 'target:02', 'pool', ' ']])
        one = self.comparison_command()
        second = one.index('--destination', one.index('--destination') + 1)
        del one[second:second + 3]
        commands.append(one)
        for command in commands:
            with self.subTest(command=command):
                code, out, err = self.invoke(command, unexpected)
                self.assertEqual(code, 3)
                self.assertEqual(out, '')
                self.assertEqual(json.loads(err), {'error': 'INVALID_INPUT'})

    def test_job_submit_requires_stable_key_and_sends_no_approval_body(self):
        def handler(request):
            self.assertEqual(request.method, 'POST')
            self.assertEqual(request.url.path, '/v1/plans/plan-01/jobs')
            self.assertEqual(request.headers['Idempotency-Key'], 'retry-01')
            self.assertEqual(request.content, b'')
            return httpx.Response(202, json={'jobId': 'job-01', 'status': 'QUEUED'})
        code, out, _ = self.invoke(['jobs', 'submit', '--plan', 'plan-01',
                                    '--idempotency-key', 'retry-01'], handler)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)['jobId'], 'job-01')

    def test_job_events_only_print_recorded_server_status(self):
        def handler(request):
            self.assertEqual(request.url.path, '/v1/jobs/job-01/events')
            self.assertEqual(request.url.params['after'], '3')
            return httpx.Response(200, json={
                'items': [{'sequence': 4, 'eventType': 'STEP_HELD', 'status': 'HELD'}],
                'nextAfter': None})
        code, out, _ = self.invoke(['jobs', 'events', '--id', 'job-01',
                                    '--after', '3'], handler)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)['items'][0]['status'], 'HELD')

    def test_plan_review_is_an_authenticated_scoped_api_read(self):
        def handler(request):
            self.assertEqual(request.url.path, '/v1/plans/plan-01/review')
            self.assertEqual(request.headers['Authorization'], 'Bearer opaque-access-token')
            return httpx.Response(200, json={'planId': 'plan-01',
                                             'planRevision': 1,
                                             'planDigest': 'a' * 64})
        code, out, err = self.invoke(['plans', 'review', '--id', 'plan-01'], handler)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)['planDigest'], 'a' * 64)
        self.assertEqual(err, '')

    def test_approval_commands_only_forward_bounded_decisions(self):
        seen = []
        def handler(request):
            seen.append((request.url.path, json.loads(request.content)))
            if request.url.path.endswith('/approvals'):
                return httpx.Response(201, json={'approvalId': 'approval-01',
                                                 'planId': 'plan-01', 'role': 'SOURCE_OWNER'})
            return httpx.Response(200, json={'planId': 'plan-01', 'revocationEpoch': 1})
        first = self.invoke(['approvals', 'record', '--plan', 'plan-01',
                             '--role', 'SOURCE_OWNER', '--ttl-seconds', '300',
                             '--expected-revision', '1',
                             '--expected-digest', 'a' * 64], handler)
        second = self.invoke(['approvals', 'revoke', '--plan', 'plan-01',
                              '--reason', 'Owner withdrew approval'], handler)
        self.assertEqual((first[0], second[0]), (0, 0))
        self.assertEqual(seen, [('/v1/plans/plan-01/approvals',
                                 {'role': 'SOURCE_OWNER', 'ttlSeconds': 300,
                                  'expectedPlanRevision': 1,
                                  'expectedPlanDigest': 'a' * 64}),
                                ('/v1/plans/plan-01/revoke',
                                 {'reason': 'Owner withdrew approval'})])

    def test_refusal_does_not_leak_token_or_server_details(self):
        def handler(_request):
            return httpx.Response(403, json={'error': {'code': 'ADMISSION_DENIED',
                                                        'message': 'sensitive internal detail'}})
        code, out, err = self.invoke(['jobs', 'submit', '--plan', 'plan-01',
                                      '--idempotency-key', 'retry-01'], handler)
        self.assertEqual(code, 2)
        self.assertEqual(out, '')
        self.assertEqual(json.loads(err), {'status': 403, 'error': 'ADMISSION_DENIED'})
        self.assertNotIn('sensitive', err)
        self.assertNotIn('opaque-access-token', err)

    def test_cleartext_http_is_refused_even_on_loopback_before_reading_token(self):
        def unexpected(_request):
            self.fail('Network request must not be sent')
        for url in ('http://control.example', 'http://localhost:8080',
                    'http://127.0.0.1:8080', 'http://[::1]:8080'):
            with self.subTest(url=url):
                code, out, err = self.invoke(['scopes'], unexpected, api_url=url)
                self.assertEqual(code, 3)
                self.assertEqual(out, '')
                self.assertEqual(json.loads(err), {'error': 'INVALID_INPUT'})

    def test_redirect_is_refused_without_forwarding_token(self):
        calls = []
        def handler(request):
            calls.append(request)
            return httpx.Response(302, headers={'Location': 'https://elsewhere.example/'},
                                  json={'error': {'code': 'REDIRECT_REFUSED'}})
        code, _, err = self.invoke(['scopes'], handler)
        self.assertEqual(code, 2)
        self.assertEqual(len(calls), 1)
        self.assertEqual(json.loads(err)['status'], 302)


if __name__ == '__main__':
    unittest.main()
