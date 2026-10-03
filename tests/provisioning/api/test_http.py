"""HTTP transport uses independent authority and exact persisted scope.

The in-memory ports here exercise transport behavior. PostgreSQL transaction,
row-security and outbox behavior belong to the B06/B09 integration tests.
"""
from __future__ import annotations

import hashlib
import json
import unittest
from copy import deepcopy
from dataclasses import replace
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
from provisioner.controlplane.evidence.gate import EvidenceHold
from provisioner.controlplane.persistence.store import (
    EnterpriseRecordStore, RecordValidationError, RevisionConflict, StoredRecord,
    canonical_record_digest,
)
from provisioner.controlplane.persistence.environments import (
    EnvironmentConflict, EnvironmentRepository, RegisteredEnvironment,
)
from provisioner.domain.enterprise_records import validate_record
from tests.provisioning.schema.test_enterprise_records import SOURCE, TARGET, plan, workload

NOW = datetime(2026, 9, 27, 1, 0, tzinfo=timezone.utc)
PLAN_DIGEST = plan()['metadata']['planDigest']
SOURCE_SCOPE = PlanScope.from_record(SOURCE)
TARGET_SCOPE = PlanScope.from_record(TARGET)
PORTFOLIO = PortfolioScope('org-01', 'tenant-01', 'wsd-01')
OTHER = PortfolioScope('org-01', 'tenant-01', 'wsd-02')


class _VerifiedEvidence:
    """Focused HTTP transport tests inject a passing independent gate."""

    def require(self, context):
        assert context.organization_id == 'org-01'


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
        def principal(subject, grants, *, tenant='tenant-01', step_up=False):
            return VerifiedPrincipal(subject, 'org-01', tenant, 'HUMAN',
                                     NOW - timedelta(minutes=5), expires,
                                     NOW - timedelta(minutes=1) if step_up else None,
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
            'approver': principal('approver-new',
                                  [(SOURCE_OWNER, SOURCE_SCOPE)], step_up=True),
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
    def __init__(self, *, empty=False):
        self.empty = empty
        self.recorded = []
        self.revocations = []

    def snapshot(self, plan):
        roles = ((SOURCE_OWNER, SOURCE_SCOPE), (DESTINATION_OWNER, TARGET_SCOPE),
                 (SOURCE_SECURITY, SOURCE_SCOPE),
                 (DESTINATION_SECURITY, TARGET_SCOPE))
        approvals = tuple(PlanApproval(f'approval-{number}', 'org-01',
                                                   'tenant-01', 'plan-01', 1, PLAN_DIGEST,
                                                   role, scope, f'approver-{number}',
                                                   NOW - timedelta(minutes=1),
                                                   NOW + timedelta(minutes=30), 0)
                          for number, (role, scope) in enumerate(roles))
        return ApprovalSnapshot('org-01', 'tenant-01', 'plan-01', 1, PLAN_DIGEST, 0,
                                () if self.empty else approvals)

    def append_if_current(self, plan, approval, expected_epoch):
        self.recorded.append(approval)

    def revoke_if_current(self, plan, expected_epoch, actor_subject, reason):
        self.revocations.append((actor_subject, reason))
        return expected_epoch + 1


class _Records(EnterpriseRecordStore):
    def __init__(self):
        self.rows = {}
        self.audit = None
        document = plan()
        self.plan_row = StoredRecord(document, 1, canonical_record_digest(document))

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
        if kind == 'MigrationPlan':
            assert wsd_id is None
            if (ctx.organization_id, ctx.tenant_id, record_id) == (
                    'org-01', 'tenant-01', 'plan-01'):
                return self.plan_row
            return None
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


class _Environments(EnvironmentRepository):
    def __init__(self):
        self.rows = {}
        self.audit = None

    def create(self, ctx, declaration, audit):
        key = (ctx.organization_id, ctx.tenant_id, declaration.environment_id)
        if key in self.rows:
            raise EnvironmentConflict('duplicate')
        self.audit = audit
        row = RegisteredEnvironment(declaration, audit.actor_id,
                                    declaration.digest(), NOW)
        self.rows[key] = row
        return row

    def get(self, ctx, environment_id):
        return self.rows.get((ctx.organization_id, ctx.tenant_id, environment_id))

    def list(self, ctx, wsd_id, scopes, *, after=None, limit=51):
        return sorted((row for (org, tenant, identifier), row in self.rows.items()
                       if (org, tenant, row.scope.security_domain_id) ==
                       (ctx.organization_id, ctx.tenant_id, wsd_id)
                       and identifier > (after or '') and row.scope in scopes),
                      key=lambda row: row.declaration.environment_id)[:limit]


class ControlApiTests(unittest.TestCase):
    def setUp(self):
        self.records = _Records()
        self.jobs = _Jobs()
        self.environments = _Environments()
        self.identity = _Identity()
        authority = AuthorityService(self.identity, _Plans(), _Ledger(),
                                     clock=lambda: NOW)
        self.app = create_app(self.records, authority, self.jobs, self.environments,
                              evidence_gate=_VerifiedEvidence(),
                              max_body_bytes=8192, clock=lambda: NOW)
        self.client = TestClient(self.app)

    def auth(self, token):
        return {'Authorization': f'Bearer {token}'}

    def test_monitor_service_never_enters_human_operator_endpoints(self):
        human=self.identity.tokens['operator']
        self.identity.tokens['monitor-service']=replace(human,kind='SERVICE',subject='monitor-service',
            grants=(RoleGrant('DISCOVERY_MONITOR',SOURCE_SCOPE,human.expires_at),))
        for method,path,body in [('get','/v1/access/scopes',None),
                                 ('get','/v1/environments?wsdId=wsd-01',None),
                                 ('put','/v1/environments/env-01/discovery/freshness/checks/check-1',{})]:
            options={'headers':self.auth('monitor-service')}
            if body is not None:options['json']=body
            result=getattr(self.client,method)(path,**options)
            self.assertEqual(result.status_code,403,result.text)
            self.assertEqual(result.json()['error']['code'],'HUMAN_ROLE_REQUIRED')

    def test_environment_declaration_is_unverified_and_exact_scope_visible(self):
        source = {
            'environmentId': 'declared-source', 'displayName': 'Candidate source',
            'siteId': SOURCE_SCOPE.site_id,
            'securityDomainId': SOURCE_SCOPE.security_domain_id,
            'endpointId': SOURCE_SCOPE.endpoint_id,
            'nativeScopeId': SOURCE_SCOPE.native_scope_id,
            'platformFamily': SOURCE_SCOPE.platform_family,
        }
        self.assertEqual(self.client.post('/v1/environments', json=source).status_code, 401)
        self.assertEqual(self.client.post('/v1/environments', headers=self.auth('reader'),
                                          json=source).status_code, 404)
        forged = self.client.post('/v1/environments', headers=self.auth('operator'),
                                  json=source | {'status': 'QUALIFIED'})
        self.assertEqual(forged.status_code, 422)
        created = self.client.post('/v1/environments', headers=self.auth('operator'),
                                   json=source)
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()['status'], 'DECLARED_UNVERIFIED')
        self.assertEqual(created.headers['location'], '/v1/environments/declared-source')
        self.assertEqual(self.environments.audit.actor_id, 'operator')
        self.assertEqual(self.client.post('/v1/environments',
                                          headers=self.auth('operator'),
                                          json=source).status_code, 409)
        listed = self.client.get('/v1/environments?wsdId=wsd-01',
                                 headers=self.auth('job-reader'))
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual([row['environmentId'] for row in listed.json()['items']],
                         ['declared-source'])
        self.assertEqual(self.client.get('/v1/environments/declared-source',
                                         headers=self.auth('one-sided')).status_code, 200)
        for token in ('reader', 'other-wsd', 'other-tenant'):
            self.assertEqual(self.client.get('/v1/environments/declared-source',
                                             headers=self.auth(token)).status_code, 404)
            self.assertEqual(self.client.get('/v1/environments?wsdId=wsd-01',
                                             headers=self.auth(token)).status_code, 404)
        target = source | {
            'environmentId': 'declared-target',
            'siteId': TARGET_SCOPE.site_id,
            'securityDomainId': TARGET_SCOPE.security_domain_id,
            'endpointId': TARGET_SCOPE.endpoint_id,
            'nativeScopeId': TARGET_SCOPE.native_scope_id,
            'platformFamily': TARGET_SCOPE.platform_family,
        }
        self.assertEqual(self.client.post('/v1/environments',
                                          headers=self.auth('operator'),
                                          json=target).status_code, 201)
        self.assertEqual(self.client.get('/v1/environments/declared-target',
                                         headers=self.auth('one-sided')).status_code, 404)
        self.assertEqual(self.client.get('/v1/environments?wsdId=wsd-02',
                                         headers=self.auth('one-sided')).status_code, 404)

    def test_app_composition_requires_explicit_evidence_gate(self):
        authority = AuthorityService(self.identity, _Plans(), _Ledger(), clock=lambda: NOW)
        with self.assertRaises(TypeError):
            create_app(self.records, authority, self.jobs, self.environments,
                       evidence_gate=None)

    def test_evidence_outage_holds_creates_approvals_and_jobs_but_allows_revocation(self):
        class Held:
            def require(self, context):
                raise EvidenceHold('unavailable')

        ledger = _Ledger()
        authority = AuthorityService(self.identity, _Plans(), ledger, clock=lambda: NOW)
        client = TestClient(create_app(self.records, authority, self.jobs,
                                       self.environments,
                                       clock=lambda: NOW, evidence_gate=Held()))
        attempts = (
            ('/v1/wsds/wsd-01/workloads', 'editor', draft(), {}),
            ('/v1/plans/plan-01/jobs', 'operator', {}, {'Idempotency-Key': 'held-job'}),
            ('/v1/plans/plan-01/approvals', 'approver',
             {'role': SOURCE_OWNER, 'ttlSeconds': 300,
              'expectedPlanRevision': 1, 'expectedPlanDigest': PLAN_DIGEST}, {}),
        )
        for path, actor, body, headers in attempts:
            result = client.post(path, headers=self.auth(actor) | headers, json=body)
            self.assertEqual((result.status_code, result.json()['error']['code']),
                             (503, 'EVIDENCE_HOLD'))
        self.assertFalse(self.records.rows)
        self.assertFalse(self.jobs.submissions)
        self.assertFalse(ledger.recorded)
        revoked = client.post('/v1/plans/plan-01/revoke',
                              headers=self.auth('approver'),
                              json={'reason': 'Credential incident'})
        self.assertEqual(revoked.status_code, 200)

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

    def test_access_scopes_are_verified_role_selectors(self):
        response = self.client.get('/v1/access/scopes', headers=self.auth('reader'))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['items'][0]['kind'], 'PORTFOLIO')
        self.assertEqual(response.json()['items'][0]['securityDomainId'], 'wsd-01')
        self.assertNotIn('environmentStatus', response.text)
        self.assertEqual(self.client.get('/v1/access/scopes').status_code, 401)

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

    def test_step_up_approval_and_revocation_have_durable_receipts(self):
        ledger = _Ledger(empty=True)
        authority = AuthorityService(self.identity, _Plans(), ledger, clock=lambda: NOW)
        client = TestClient(create_app(self.records, authority, self.jobs,
                                       self.environments,
                                       evidence_gate=_VerifiedEvidence(),
                                       max_body_bytes=8192, clock=lambda: NOW))
        url = '/v1/plans/plan-01/approvals'
        forged = client.post(url, headers=self.auth('approver'),
                             json={'role': SOURCE_OWNER, 'ttlSeconds': 300,
                                   'approvalIds': ['forged']})
        self.assertEqual(forged.status_code, 422)
        self.assertFalse(ledger.recorded)
        approved = client.post(url, headers=self.auth('approver'),
                               json={'role': SOURCE_OWNER, 'ttlSeconds': 300,
                                     'expectedPlanRevision': 1,
                                     'expectedPlanDigest': PLAN_DIGEST})
        self.assertEqual(approved.status_code, 201, approved.text)
        self.assertEqual(approved.json()['planId'], 'plan-01')
        self.assertEqual(ledger.recorded[0].approver_subject, 'approver-new')
        self.assertNotIn('approverSubject', approved.text)
        revoked = client.post('/v1/plans/plan-01/revoke',
                              headers=self.auth('approver'),
                              json={'reason': 'Owner withdrew approval'})
        self.assertEqual(revoked.status_code, 200, revoked.text)
        self.assertEqual(revoked.json()['revocationEpoch'], 1)
        self.assertEqual(ledger.revocations,
                         [('approver-new', 'Owner withdrew approval')])

    def test_approval_without_step_up_fails(self):
        result = self.client.post('/v1/plans/plan-01/approvals',
                                  headers=self.auth('editor'),
                                  json={'role': SOURCE_OWNER, 'ttlSeconds': 300,
                                        'expectedPlanRevision': 1,
                                        'expectedPlanDigest': PLAN_DIGEST})
        self.assertEqual(result.status_code, 403)

    def test_review_is_exactly_scoped_and_redacts_mappings_and_author(self):
        url = '/v1/plans/plan-01/review'
        self.assertEqual(self.client.get(url).status_code, 401)
        self.assertEqual(self.client.get(url, headers=self.auth('reader')).status_code, 404)
        self.assertEqual(self.client.get(url, headers=self.auth('other-tenant')).status_code, 404)
        reviewed = self.client.get(url, headers=self.auth('approver'))
        self.assertEqual(reviewed.status_code, 200, reviewed.text)
        facts = reviewed.json()
        self.assertEqual((facts['planRevision'], facts['planDigest']), (1, PLAN_DIGEST))
        self.assertEqual(facts['source']['securityDomainId'], 'wsd-01')
        self.assertEqual(facts['destination']['securityDomainId'], 'wsd-02')
        self.assertEqual(facts['routeMethod'], 'SAME_PLATFORM_RELOCATION')
        self.assertEqual(facts['selectedMachineCount'], 2)
        self.assertEqual(facts['maxDowntimeSeconds'], 3600)
        self.assertEqual(facts['eligibleRoles'], [SOURCE_OWNER])
        for confidential in ('machineMappings', 'targetNetworkRef',
                             'authorSubject', 'approvalIds'):
            self.assertNotIn(confidential, reviewed.text)
        self.assertEqual(self.client.get(url, headers=self.auth('editor')).status_code, 404)

    def test_review_fails_closed_if_record_and_authority_disagree(self):
        self.records.plan_row = StoredRecord(
            self.records.plan_row.record, 2, self.records.plan_row.digest)
        response = self.client.get('/v1/plans/plan-01/review',
                                   headers=self.auth('approver'))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['error']['code'], 'PLAN_REVIEW_STALE')

    def test_approval_requires_reviewed_binding_and_rejects_stale_revision(self):
        ledger = _Ledger(empty=True)
        authority = AuthorityService(self.identity, _Plans(), ledger, clock=lambda: NOW)
        client = TestClient(create_app(self.records, authority, self.jobs,
                                       self.environments,
                                       evidence_gate=_VerifiedEvidence(),
                                       max_body_bytes=8192, clock=lambda: NOW))
        url = '/v1/plans/plan-01/approvals'
        absent = client.post(url, headers=self.auth('approver'),
                             json={'role': SOURCE_OWNER, 'ttlSeconds': 300})
        self.assertEqual(absent.status_code, 422)
        stale = client.post(url, headers=self.auth('approver'),
                            json={'role': SOURCE_OWNER, 'ttlSeconds': 300,
                                  'expectedPlanRevision': 1,
                                  'expectedPlanDigest': '0' * 64})
        self.assertEqual(stale.status_code, 409, stale.text)
        self.assertEqual(stale.json()['error']['code'], 'PLAN_REVIEW_STALE')
        self.assertFalse(ledger.recorded)

    def test_openapi_declares_security_and_request_contract(self):
        spec = self.client.get('/openapi.json').json()
        create = spec['paths']['/v1/wsds/{wsd_id}/workloads']['post']
        self.assertEqual(create['requestBody']['content']['application/json']['schema']['$ref'],
                         '#/components/schemas/WorkloadCreate')
        self.assertTrue(create['security'])
        self.assertEqual(spec['components']['schemas']['WorkloadCreate']['properties']['kind']['const'],
                         'Workload')
        self.assertTrue(spec['paths']['/v1/plans/{plan_id}/review']['get']['security'])
        approval = spec['components']['schemas']['ApprovalRequest']['required']
        self.assertIn('expectedPlanRevision', approval)
        self.assertIn('expectedPlanDigest', approval)
        self.assertEqual(self.client.get('/docs').status_code, 404)


if __name__ == '__main__':
    unittest.main()
