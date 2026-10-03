"""Actual signed command -> dedicated SQL intake -> authenticated review read.

The injected test connector uses disposable CI DSNs, not the production TLS/SCRAM
transport. The real repository, role guard, RLS and commit/rollback run unchanged.
"""
import copy
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from provisioner.controlplane.discovery import review_intake as intake, owner_signing
from tests.provisioning.controlplane import test_application_reviews_postgres as support
from tests.provisioning.controlplane import test_application_review_cli_postgres as cli_support
from tests.provisioning.discovery.test_review_intake import files, args
from tests.provisioning.discovery.test_owner_signing import fixture_files, prepare_args, sign_args, private_file


@unittest.skipUnless(all(os.environ.get(key) for key in (
    'HOSTING_TEST_POSTGRES_ASSESSMENT_DSN', 'HOSTING_TEST_POSTGRES_DISCOVERY_DSN',
    'HOSTING_TEST_POSTGRES_RUNTIME_DSN')), 'Requires isolated PostgreSQL intake, discovery and runtime roles')
class ReviewIntakePostgresTests(unittest.TestCase):
    setUpClass = classmethod(support.ApplicationReviewPostgresTests.setUpClass.__func__)
    _campaign = support.ApplicationReviewPostgresTests._campaign
    _object = support.ApplicationReviewPostgresTests._object
    _publish = support.ApplicationReviewPostgresTests._publish
    authorize = support.ApplicationReviewPostgresTests.authorize
    save = support.ApplicationReviewPostgresTests.save
    get = support.ApplicationReviewPostgresTests.get
    api = cli_support.ApplicationReviewCliPostgresTests.api

    def setUp(self):
        support.ApplicationReviewPostgresTests.setUp(self)
        self.root = Path(self.temp.name)
        self.config, _ = files(self.root, self.original, self.fixture, at=datetime.now(timezone.utc))
        fixture_files(self.root, self.original, self.fixture)
        (self.root/'signed.json').unlink()
        for argv in (prepare_args(self.root, self.original),):
            out, err = io.StringIO(), io.StringIO()
            self.assertEqual(owner_signing.main(argv, stdout=out, stderr=err), 0, err.getvalue())
        out, err = io.StringIO(), io.StringIO()
        self.assertEqual(owner_signing.main(sign_args(self.root, self.original), stdout=out, stderr=err),0,err.getvalue())

    def invoke(self, *, receipt='receipt.json', dsn=None, connector=None):
        out, err = io.StringIO(), io.StringIO()
        with patch.object(intake, '_connect_database', connector or
                          (lambda _:self.psycopg.connect(dsn or self.evidence_dsn))):
            code = intake.main(args(self.root, receipt=receipt), stdout=out, stderr=err)
        return code, json.loads(out.getvalue() or err.getvalue())

    def test_installed_command_artifact_flows_into_real_sql_and_authenticated_review(self):
        code, receipt = self.invoke()
        self.assertEqual(code,0,receipt)
        self.assertEqual(receipt['status'],'RECORDED_ASSESSMENT_ONLY')
        with self.api() as api:
            response = api.get(f'/v1/environments/{self.environment_id}/application-drafts/app-1/review?revision=1',
                               headers={'Authorization':'Bearer synthetic-review-bearer'})
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(response.json()['evidenceDigest'],receipt['evidenceDigest'])
            self.assertEqual(response.json()['status'],'REVIEWED_WITH_UNKNOWNS')
            self.assertIs(response.json()['executionAuthorized'],False)
        self.assertEqual(self.repo.get(self.ctx,self.scope,self.environment_id,'app-1',authorize=self.authorize)['status'],'UNREVIEWED')

    def test_explicit_same_artifact_retry_preserves_one_evidence_and_audit(self):
        self.assertEqual(self.invoke()[0],0)
        code, receipt = self.invoke(receipt='receipt-retry.json')
        self.assertEqual(code,0,receipt)
        with self.repo._session(self.ctx,self.scope,self.environment_id,self.authorize) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM hosting_controlplane.audit_events "
                "WHERE record_kind='AssessmentInput'").fetchone()[0],1)
            self.assertEqual(connection.execute('SELECT count(*) FROM hosting_controlplane.assessment_inputs').fetchone()[0],1)

    def test_runtime_or_owner_login_cannot_substitute_for_the_intake_session(self):
        code, result = self.invoke(dsn=self.runtime_dsn)
        self.assertEqual(code,2,result);self.assertFalse(result['ingestAttempted'])
        self.assertEqual(self.get()['status'],'UNREVIEWED')

    def test_superseded_draft_is_not_accepted_by_an_offline_signature(self):
        content=copy.deepcopy(self.content);content['draft']['name']='Next revision'
        self.save(expected_revision=1,content=content)
        code,result=self.invoke();self.assertEqual(code,3,result);self.assertFalse(result['recorded'])
        self.assertFalse((self.root/'receipt.json').exists())
        self.assertEqual(self.get(revision=2)['status'],'UNREVIEWED')

    def test_commit_then_lost_ack_is_unknown_and_exact_retry_reconciles(self):
        case=self
        class LostAck:
            def __init__(self):self.connection=case.psycopg.connect(case.evidence_dsn)
            def __enter__(self):return self.connection.__enter__()
            def __exit__(self,*exc):
                self.connection.__exit__(*exc)
                if exc[0] is None:raise OSError('simulated commit acknowledgement loss')
        code,out=self.invoke(connector=lambda _:LostAck())
        self.assertEqual(code,3,out);self.assertFalse(out['recorded']);self.assertTrue(out['ingestAttempted'])
        self.assertEqual(self.get()['status'],'REVIEWED_WITH_UNKNOWNS')
        self.assertEqual(self.invoke(receipt='reconciled.json')[0],0)
        with self.repo._session(self.ctx,self.scope,self.environment_id,self.authorize) as connection:
            self.assertEqual(connection.execute('SELECT count(*) FROM hosting_controlplane.assessment_inputs').fetchone()[0],1)

    @unittest.skipUnless(os.environ.get('HOSTING_TEST_POSTGRES_ADMIN_DSN'),'Requires isolated admin for temporary negative grant')
    def test_column_only_mutation_privilege_is_detected_without_table_grant(self):
        with self.psycopg.connect(os.environ['HOSTING_TEST_POSTGRES_ADMIN_DSN'],autocommit=True) as admin:
            admin.execute('GRANT UPDATE (proposal_json) ON hosting_controlplane.application_draft_revisions TO hosting_assessment_ingest')
            try:
                code,out=self.invoke();self.assertEqual(code,2,out);self.assertFalse(out['ingestAttempted'])
            finally:
                admin.execute('REVOKE UPDATE (proposal_json) ON hosting_controlplane.application_draft_revisions FROM hosting_assessment_ingest')
        self.assertEqual(self.get()['status'],'UNREVIEWED')


if __name__=='__main__':unittest.main()
