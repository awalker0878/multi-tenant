"""The thin review command reads live signed decisions through the real API/DB."""
import copy
import io
import json
import os
import unittest
from datetime import datetime, timedelta, timezone

from tests.provisioning.controlplane import test_application_reviews_postgres as support


@unittest.skipUnless(os.environ.get('HOSTING_TEST_POSTGRES_ASSESSMENT_DSN') and
    os.environ.get('HOSTING_TEST_POSTGRES_DISCOVERY_DSN') and
    os.environ.get('HOSTING_TEST_POSTGRES_RUNTIME_DSN'), 'Requires isolated discovery, assessment and runtime PostgreSQL roles')
class ApplicationReviewCliPostgresTests(unittest.TestCase):
    setUpClass = classmethod(support.ApplicationReviewPostgresTests.setUpClass.__func__)
    setUp = support.ApplicationReviewPostgresTests.setUp
    _campaign = support.ApplicationReviewPostgresTests._campaign
    _object = support.ApplicationReviewPostgresTests._object
    _publish = support.ApplicationReviewPostgresTests._publish
    authorize = support.ApplicationReviewPostgresTests.authorize
    save = support.ApplicationReviewPostgresTests.save
    document = support.ApplicationReviewPostgresTests.document
    ingest = support.ApplicationReviewPostgresTests.ingest

    def api(self):
        from fastapi.testclient import TestClient
        from provisioner.controlplane.api import create_app
        from provisioner.controlplane.authority.model import VerifiedPrincipal, RoleGrant
        from provisioner.controlplane.authority.service import AuthorityService, JOB_READER
        from tests.provisioning.api import test_http as http_support
        now = datetime.now(timezone.utc)
        principal = VerifiedPrincipal('review-reader', self.ctx.organization_id, self.ctx.tenant_id,
            'HUMAN', now-timedelta(minutes=1), now+timedelta(minutes=5), None,
            (RoleGrant(JOB_READER, self.scope, now+timedelta(minutes=5)),))
        self.reader_enabled = True
        self.requests = []
        case = self
        class Identity:
            def authenticate(self, token):
                if token != 'synthetic-review-bearer' or not case.reader_enabled:
                    raise PermissionError('invalid credential')
                return principal
        class Evidence:
            def require(self, ctx):
                if (ctx.organization_id, ctx.tenant_id) != (principal.organization_id, principal.tenant_id):
                    raise PermissionError('wrong tenant')
        return TestClient(create_app(http_support._Records(),
            AuthorityService(Identity(), http_support._Plans(), http_support._Ledger()),
            http_support._Jobs(), self.environments, evidence_gate=Evidence(),
            application_drafts=self.repo, application_reviews=self.service))

    def invoke(self, api, *, revision=1, digest=None):
        import httpx
        from provisioner.cli.operator import run
        def transport(request):
            self.requests.append(request.method)
            response = api.request(request.method, request.url.raw_path.decode('ascii'),
                                   content=request.content, headers=dict(request.headers))
            return httpx.Response(response.status_code, content=response.content, headers=response.headers)
        out, err = io.StringIO(), io.StringIO()
        args = ['--api-url', 'https://api.example', '--token-stdin', 'application-drafts', 'review',
                '--environment', self.environment_id, '--id', 'app-1', '--revision', str(revision)]
        if digest is not None:
            args += ['--record-digest', digest]
        code = run(args, stdin=io.StringIO('synthetic-review-bearer\n'), stdout=out, stderr=err,
                   transport=httpx.MockTransport(transport))
        self.assertNotIn('synthetic-review-bearer', out.getvalue()+err.getvalue())
        self.assertEqual(self.requests[-1], 'GET')
        if code == 0:
            self.assertEqual(err.getvalue(), '')
            value = json.loads(out.getvalue())
            self.assertIs(value['executionAuthorized'], False)
            self.assertIs(value['ownershipAccepted'], False)
            return code, value
        self.assertEqual(out.getvalue(), '')
        return code, json.loads(err.getvalue())

    def signed_artifact(self, *, decision='ACCEPT_FOR_ASSESSMENT', revision=1, exported=None):
        from pathlib import Path
        from tests.provisioning.discovery.test_owner_signing import (
            fixture_files, prepare_args, sign_args, invoke, private_file)
        root = Path(self.temp.name) / ('decision-' + str(revision))
        root.mkdir(mode=0o700)
        fixture_files(root, self.original, self.fixture)
        if exported is not None:
            private_file(root/'draft.json', exported)
        clock = lambda: datetime.now(timezone.utc)
        code, prepared = invoke(prepare_args(root, self.original, decision=decision, revision=revision), clock=clock)
        self.assertEqual(code, 0, prepared)
        code, signed = invoke(sign_args(root, self.original), clock=clock)
        self.assertEqual(code, 0, signed)
        self.assertEqual(signed['status'], 'SIGNED_NOT_INGESTED')
        return json.loads((root/'signed.json').read_bytes())

    def test_owner_command_signs_api_export_and_existing_ingest_drives_review(self):
        with self.api() as api:
            path = f'/v1/environments/{self.environment_id}/application-drafts/app-1?revision=1'
            response = api.get(path, headers={'Authorization': 'Bearer synthetic-review-bearer'})
            self.assertEqual(response.status_code, 200, response.text)
            submission = self.signed_artifact(exported=response.json())
            self.assertEqual(self.invoke(api)[1]['status'], 'UNREVIEWED')
            digest = self.evidence_writer.ingest(self.ctx, submission['evidence'], tuple(submission['signatures']))
            code, view = self.invoke(api, digest=self.original.record_digest)
            self.assertEqual(code, 0, view)
            self.assertEqual(view['status'], 'REVIEWED_WITH_UNKNOWNS')
            self.assertEqual(view['evidenceDigest'], digest)
            self.assertIs(view['dependencyEvidenceVerified'], False)

    def test_offline_signature_cannot_accept_a_draft_superseded_before_ingestion(self):
        from provisioner.controlplane.discovery.assessment_inputs import AssessmentInputDenied
        submission = self.signed_artifact()
        content = copy.deepcopy(self.content); content['draft']['name'] = 'New revision'
        self.save(expected_revision=1, content=content)
        with self.assertRaises(AssessmentInputDenied):
            self.evidence_writer.ingest(self.ctx, submission['evidence'], tuple(submission['signatures']))

    def test_owner_command_can_revoke_its_exact_retained_historical_draft(self):
        content = copy.deepcopy(self.content); content['draft']['name'] = 'New revision'
        self.save(expected_revision=1, content=content)
        submission = self.signed_artifact(decision='REVOKE', revision=2)
        self.evidence_writer.ingest(self.ctx, submission['evidence'], tuple(submission['signatures']))
        with self.api() as api:
            self.assertEqual(self.invoke(api, revision=1)[1]['status'], 'REVOKED')
            self.assertEqual(self.invoke(api, revision=2)[1]['status'], 'UNREVIEWED')

    def test_cli_observes_signed_acceptance_revocation_and_live_reader_access(self):
        with self.api() as api:
            self.assertEqual(self.invoke(api)[1]['status'], 'UNREVIEWED')
            digest = self.ingest(self.document())
            code, value = self.invoke(api, digest=self.original.record_digest)
            self.assertEqual(code, 0, value)
            self.assertEqual(value['status'], 'REVIEWED_WITH_UNKNOWNS')
            self.assertEqual(value['evidenceDigest'], digest)
            self.assertEqual(value['unknownDependencyCount'], 1)
            self.ingest(self.document(decision='REVOKE', revision=2))
            code, value = self.invoke(api)
            self.assertEqual(code, 0, value)
            self.assertEqual(value['status'], 'REVOKED')
            self.assertIsNone(value['candidateDigest'])
            self.reader_enabled = False
            self.assertEqual(self.invoke(api)[0], 2)
        self.assertEqual(self.requests, ['GET']*4)
        draft = self.repo.get(self.ctx, self.scope, self.environment_id, 'app-1', authorize=self.authorize)
        self.assertEqual(draft['revision'], 1)
        self.assertEqual(draft['status'], 'UNREVIEWED')

    def test_cli_keeps_exact_history_when_drafts_or_inventory_are_superseded(self):
        self.ingest(self.document())
        content = copy.deepcopy(self.content)
        content['draft']['name'] = 'New proposed application name'
        new_draft = self.save(expected_revision=1, content=content)
        with self.api() as api:
            code, old = self.invoke(api, digest=self.original.record_digest)
            self.assertEqual(code, 0, old)
            self.assertEqual(old['status'], 'HELD_SUPERSEDED_DRAFT')
            self.assertEqual(old['draftRecordDigest'], self.original.record_digest)
            self.assertEqual(old['latestDraftRevision'], 2)
            code, new = self.invoke(api, revision=2, digest=new_draft.record_digest)
            self.assertEqual(code, 0, new)
            self.assertEqual(new['status'], 'UNREVIEWED')
            self.assertIsNone(new['evidenceId'])
            self.assertEqual(self.invoke(api, revision=2, digest=self.original.record_digest)[0], 3)
            self._publish(self._campaign('new'), 'PARTIAL',
                (self._object('vm-1', 'Changed'),), ('VISIBLE_INVENTORY_ONLY',))
            code, new = self.invoke(api, revision=2)
            self.assertEqual(code, 0, new)
            self.assertEqual(new['status'], 'HELD_SUPERSEDED_INVENTORY')
            self.assertEqual(new['resultDigest'], new_draft.result_digest)
        self.assertEqual(self.requests, ['GET']*4)


if __name__ == '__main__':
    unittest.main()
