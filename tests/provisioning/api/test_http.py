"""HTTP transport uses independent authority and exact persisted scope.

The in-memory ports here exercise transport behavior. PostgreSQL transaction,
row-security and outbox behavior belong to the B06/B09 integration tests.
"""
from __future__ import annotations

import hashlib
import json
import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from provisioner.controlplane.api import create_app
from provisioner.controlplane.authority.model import (
    ApprovalSnapshot, AuthorizedPlan, FrozenPlan, PlanApproval, PlanScope,
    PortfolioScope, RoleGrant, VerifiedPrincipal,
)
from provisioner.controlplane.authority.service import (
    DESTINATION_OWNER, DESTINATION_SECURITY, EXECUTION_OPERATOR, JOB_READER,
    SOURCE_OWNER, SOURCE_SECURITY, WORKLOAD_EDITOR, WORKLOAD_READER,
    AuthorityService, AuthenticationFailed,
)
from provisioner.controlplane.jobs.repository import Job, JobEvent, JobRepository
from provisioner.controlplane.persistence.store import (
    EnterpriseRecordStore, RecordValidationError, RevisionConflict, StoredRecord,
)
from provisioner.domain.enterprise_records import validate_record
from tests.provisioning.schema.test_enterprise_records import SOURCE, TARGET, workload

NOW = datetime(2026, 9, 27, 1, 0, tzinfo=timezone.utc)
PLAN_DIGEST = 'a' * 64
SOURCE_SCOPE = PlanScope.from_record(SOURCE)
TARGET_SCOPE = PlanScope.from_record(TARGET)
PORTFOLIO = PortfolioScope('org-01', 'tenant-01', 'wsd-01')
OTHER = PortfolioScope('org-01', 'tenant-01', 'wsd-02')


def draft() -> dict:
    item = workload()
    item['spec']['state'] = 'PLANNED'
    for machine in item['spec']['machines']:
        for resource in (machine, *machine['disks'], *machine['nics']):
            resource['bindings'] = []
    for dataset in item['spec']['datasets']:
        dataset['sourceBindings'] = []
    assert not validate_record(item)
    return item


class _Identity:
    def __init__(self):
        expires = NOW + timedelta(hours=1)
        def principal(subject, grants, *, tenant='tenant-01'):
            return VerifiedPrincipal(subject, 'org-01', tenant, 'HUMAN',
                                     NOW - timedelta(minutes=5), expires, None,
                                     tuple(RoleGrant(role, scope, expires)
                                           for role, scope in grants))
        self.tokens = {
            'editor': principal('editor@example.org',
                                [(WORKLOAD_EDITOR, PORTFOLIO),
                                 (WORKLOAD_READER, PORTFOLIO),
                                 (EXECUTION_OPERATOR, SOURCE_SCOPE),
                                 (EXECUTION_OPERATOR, TARGET_SCOPE)]),
            'reader': principal('reader', [(WORKLOAD_READER, PORTFOLIO)]),
            'other-wsd': principal('other-wsd', [(WORKLOAD_READER, OTHER)]),
            'other-tenant': principal('other-tenant',
                                      [(WORKLOAD_READER,
                                        PortfolioScope('org-01', 'tenant-02', 'wsd-01'))],
                                      tenant='tenant-02'),
            'operator': principal('operator',
                                  [(EXECUTION_OPERATOR, SOURCE_SCOPE),
                                   (EXECUTION_OPERATOR, TARGET_SCOPE),
                                   (JOB_READER, SOURCE_SCOPE),
                                   (JOB_READER, TARGET_SCOPE)]),
            'job-reader': principal('job-reader',
                                    [(JOB_READER, SOURCE_SCOPE),
                                     (JOB_READER, TARGET_SCOPE)]),
            'one-sided': principal('one-sided', [(JOB_READER, SOURCE_SCOPE)]),
        }

    def authenticate(self, credential):
        try:
            return self.tokens[credential]
        except KeyError:
            raise AuthenticationFailed('Unverified token') from None


class _Plans:
    def current(self, organization_id, tenant_id, plan_id):
        if (organization_id, tenant_id, plan_id) != ('org-01', 'tenant-01', 'plan-01'):
            raise LookupError('Not found')
        return FrozenPlan('org-01', 'tenant-01', 'plan-01', 1, PLAN_DIGEST,
                          'editor@example.org', SOURCE_SCOPE, TARGET_SCOPE)


class _Ledger:
    def snapshot(self, plan):
        roles = ((SOURCE_OWNER, SOURCE_SCOPE), (DESTINATION_OWNER, TARGET_SCOPE),
                 (SOURCE_SECURITY, SOURCE_SCOPE),
                 (DESTINATION_SECURITY, TARGET_SCOPE))
        return ApprovalSnapshot('org-01', 'tenant-01', 'plan-01', 1, PLAN_DIGEST, 0,
                                tuple(PlanApproval(f'approval-{number}', 'org-01',
                                                   'tenant-01', 'plan-01', 1, PLAN_DIGEST,
                                                   role, scope, f'approver-{number}',
                                                   NOW - timedelta(minutes=1),
                                                   NOW + timedelta(minutes=30), 0)
                                      for number, (role, scope) in enumerate(roles)))


class _Records(EnterpriseRecordStore):
    def __init__(self):
        self.rows = {}
        self.audit = None

    def create(self, ctx, record, audit):
        if validate_record(record):
            raise RecordValidationError(validate_record(record))
        if (ctx.organization_id, ctx.tenant_id) != (
                record['metadata']['organizationId'], record['metadata']['tenantId']):
            raise AssertionError('Unverified tenant context')
        key = (ctx.organization_id, ctx.tenant_id,
               record['metadata']['wsdId'], record['metadata']['workloadId'])
        if key in self.rows:
            raise RevisionConflict('Duplicate')
        self.audit = audit
        digest = hashlib.sha256(json.dumps(record, sort_keys=True,
                                           separators=(',', ':')).encode()).hexdigest()
        row = StoredRecord(deepcopy(record), 1, digest)
        self.rows[key] = row
        return row

    def get(self, ctx, kind, record_id, *, wsd_id=None):
        assert kind == 'Workload' and wsd_id is not None
        return self.rows.get((ctx.organization_id, ctx.tenant_id, wsd_id, record_id))

    def list(self, ctx, kind, *, limit=100, after=None, wsd_id=None):
        assert kind == 'Workload' and wsd_id is not None
        rows = [row for (org, tenant, wsd, item), row in self.rows.items()
                if (org, tenant, wsd) == (ctx.organization_id, ctx.tenant_id, wsd_id)
                and item > (after or '')]
        return sorted(rows, key=lambda row: row.record['metadata']['workloadId'])[:limit]


class _Jobs(JobRepository):
    def __init__(self):
        self.rows = {}
        self.submissions = []

    def submit(self, context, authorization, *, idempotency_key):
        assert isinstance(authorization, AuthorizedPlan)
        assert (context.organization_id, context.tenant_id) == (
            authorization.organization_id, authorization.tenant_id)
        self.submissions.append(authorization)
        key = (context.organization_id, context.tenant_id, idempotency_key)
        if key not in self.rows:
            self.rows[key] = Job('org-01', 'tenant-01', 'job-01', idempotency_key,
                                 authorization.plan_id, authorization.plan_revision,
                                 authorization.plan_digest, authorization.source,
                                 authorization.destination, authorization.actor_subject,
                                 authorization.approval_ids,
                                 authorization.revocation_epoch, 'QUEUED', 1, NOW, NOW)
        return self.rows[key]

    def get(self, context, job_id):
        return next((row for (org, tenant, _), row in self.rows.items()
                     if (org, tenant, row.job_id) == (
                         context.organization_id, context.tenant_id, job_id)), None)

    def events(self, context, job_id, *, after_sequence=0, limit=100):
        if self.get(context, job_id) is None:
            return ()
        events = (JobEvent(1, 'admitted', 'JOB_ADMITTED', 'QUEUED',
                           {'secret': 'must-not-leak'}, NOW),)
        return tuple(event for event in events if event.sequence > after_sequence)[:limit]


class ControlApiTests(unittest.TestCase):
    def setUp(self):
        self.records = _Records()
        self.jobs = _Jobs()
        self.identity = _Identity()
        authority = AuthorityService(self.identity, _Plans(), _Ledger(),
                                     clock=lambda: NOW)
        self.app = create_app(self.records, authority, self.jobs,
                              max_body_bytes=8192, clock=lambda: NOW)
        self.client = TestClient(self.app)

    def auth(self, token):
        return {'Authorization': f'Bearer {token}'}

    def test_workload_create_and_scoped_read(self):
        item = draft()
        response = self.client.post('/v1/wsds/wsd-01/workloads',
                                    headers=self.auth('editor'), json=item)
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()['record'], item)
        self.assertEqual(response.headers['Location'],
                         '/v1/wsds/wsd-01/workloads/workload-01')
        self.assertEqual(self.records.audit.actor_id, 'editor@example.org')
        url = '/v1/wsds/wsd-01/workloads/workload-01'
        self.assertEqual(self.client.get(url, headers=self.auth('reader')).status_code, 200)
        for token in ('other-wsd', 'other-tenant'):
            result = self.client.get(url, headers=self.auth(token))
            self.assertEqual(result.status_code, 404)
            self.assertEqual(result.json()['error']['code'], 'RESOURCE_NOT_FOUND')
        self.assertEqual(self.client.get('/v1/wsds/wsd-01/workloads',
                                         headers=self.auth('reader')).json()['items'][0]['record'], item)

    def test_identity_cannot_be_set_by_headers_or_body(self):
        item = draft()
        forged = self.auth('reader') | {'X-Principal': 'editor', 'X-Tenant': 'tenant-01'}
        self.assertEqual(self.client.post('/v1/wsds/wsd-01/workloads',
                                           headers=forged, json=item).status_code, 404)
        item['metadata']['tenantId'] = 'tenant-02'
        forged = self.auth('editor') | {'X-Tenant': 'tenant-02'}
        self.assertEqual(self.client.post('/v1/wsds/wsd-01/workloads',
                                           headers=forged, json=item).status_code, 404)
        self.assertFalse(self.records.rows)

    def test_verified_subject_is_durable_audit_actor_despite_spoofed_header(self):
        item = draft()
        headers = self.auth('editor') | {'X-Principal': 'approver',
                                         'X-Actor': 'approver'}
        response = self.client.post('/v1/wsds/wsd-01/workloads',
                                    headers=headers, json=item)
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(self.records.audit.actor_id, 'editor@example.org')

    def test_native_claims_and_bad_records_refused(self):
        item = draft()
        item['spec']['machines'][0]['bindings'] = workload()['spec']['machines'][0]['bindings']
        response = self.client.post('/v1/wsds/wsd-01/workloads',
                                    headers=self.auth('editor'), json=item)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()['error']['code'], 'NATIVE_CLAIM_REFUSED')
        item = draft()
        item['spec']['machines'][0]['cpuCount'] = {'state': 'KNOWN', 'value': -1}
        response = self.client.post('/v1/wsds/wsd-01/workloads',
                                    headers=self.auth('editor'), json=item)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()['error']['code'], 'REQUEST_INVALID')
        item = draft()
        item['spec']['machines'][0]['cpuCount'] = {'state': 'UNKNOWN', 'reason': 'not measured'}
        response = self.client.post('/v1/wsds/wsd-01/workloads',
                                    headers=self.auth('editor'), json=item)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()['error']['code'], 'RECORD_INVALID')

    def test_authentication_and_body_limit(self):
        self.assertEqual(self.client.get('/v1/wsds/wsd-01/workloads').status_code, 401)
        self.assertEqual(self.client.get('/v1/wsds/wsd-01/workloads',
                                         headers=self.auth('unknown')).status_code, 401)
        too_large = self.client.post('/v1/wsds/wsd-01/workloads',
                                     headers=self.auth('editor') | {'Content-Type': 'application/json'},
                                     content=b' ' * 8193)
        self.assertEqual(too_large.status_code, 413)
        self.assertEqual(too_large.json()['error']['code'], 'REQUEST_TOO_LARGE')
        chunked = self.client.request(
            'GET', '/v1/wsds/wsd-01/workloads', headers=self.auth('reader'),
            content=(b' ' * count for count in (4096, 4097)))
        self.assertEqual(chunked.status_code, 413)
        understated = self.client.post(
            '/v1/wsds/wsd-01/workloads',
            headers=self.auth('editor') | {'Content-Type': 'application/json',
                                           'Content-Length': '1'},
            content=b' ' * 8193)
        self.assertEqual(understated.status_code, 413)
        self.assertFalse(self.records.rows)

    def test_job_admission_and_persisted_timeline_scope(self):
        url = '/v1/plans/plan-01/jobs'
        headers = self.auth('operator') | {'Idempotency-Key': 'req-01'}
        admitted = self.client.post(url, headers=headers)
        self.assertEqual(admitted.status_code, 202, admitted.text)
        self.assertEqual(admitted.json()['status'], 'QUEUED')
        self.assertEqual(admitted.headers['Location'], '/v1/jobs/job-01')
        self.assertEqual(len(self.jobs.submissions), 1)
        self.assertEqual(self.client.post(url, headers=headers).json()['jobId'], 'job-01')
        self.assertEqual(self.client.get('/v1/jobs/job-01', headers=self.auth('one-sided')).status_code, 404)
        self.assertEqual(self.client.get('/v1/jobs/job-01', headers=self.auth('job-reader')).status_code, 200)
        events = self.client.get('/v1/jobs/job-01/events', headers=self.auth('job-reader'))
        self.assertEqual(events.status_code, 200, events.text)
        self.assertEqual(events.json()['items'][0]['eventType'], 'JOB_ADMITTED')
        self.assertNotIn('secret', events.text)
        self.assertNotIn('approvalIds', admitted.text)

    def test_plan_author_cannot_submit_despite_operator_roles_and_forged_claims(self):
        created = self.client.post('/v1/wsds/wsd-01/workloads',
                                   headers=self.auth('editor'), json=draft())
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(self.records.audit.actor_id,
                         _Plans().current('org-01', 'tenant-01', 'plan-01').author_subject)
        result = self.client.post('/v1/plans/plan-01/jobs',
                                  headers=self.auth('editor') | {'Idempotency-Key': 'req-02',
                                                                 'X-Principal': 'operator'},
                                  json={'principal': 'operator', 'approvalIds': ['forged']})
        self.assertEqual(result.status_code, 403)
        self.assertFalse(self.jobs.submissions)

    def test_openapi_declares_security_and_request_contract(self):
        spec = self.client.get('/openapi.json').json()
        create = spec['paths']['/v1/wsds/{wsd_id}/workloads']['post']
        self.assertEqual(create['requestBody']['content']['application/json']['schema']['$ref'],
                         '#/components/schemas/WorkloadCreate')
        self.assertTrue(create['security'])
        self.assertEqual(spec['components']['schemas']['WorkloadCreate']['properties']['kind']['const'],
                         'Workload')
        self.assertEqual(self.client.get('/docs').status_code, 404)


if __name__ == '__main__':
    unittest.main()
