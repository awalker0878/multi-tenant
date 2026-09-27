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
