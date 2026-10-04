"""Owner decisions use real signed evidence, independent SQL ingest and RLS."""
import copy
import hashlib
import json
import os
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from provisioner.controlplane.discovery.application_reviews import ApplicationReviewService, ApplicationReviewUnavailable
from provisioner.controlplane.discovery.assessment_inputs import AssessmentInputRepository, AssessmentInputDenied, parse_evidence
from provisioner.controlplane.discovery.model import _json
from provisioner.controlplane.discovery.persistence import DiscoveryRepository
from provisioner.controlplane.persistence.store import AuditContext, TenantContext
from tests.provisioning.controlplane import test_application_drafts_postgres as draft_support
from tests.provisioning.discovery.test_application_review import OwnerFixture, review_document


@unittest.skipUnless(os.environ.get('HOSTING_TEST_POSTGRES_ASSESSMENT_DSN') and
    os.environ.get('HOSTING_TEST_POSTGRES_DISCOVERY_DSN') and
    os.environ.get('HOSTING_TEST_POSTGRES_RUNTIME_DSN'), 'Requires isolated discovery, assessment and runtime PostgreSQL roles')
class ApplicationReviewPostgresTests(unittest.TestCase):
    setUpClass = classmethod(draft_support.ApplicationDraftPostgresTests.setUpClass.__func__)
    _campaign = draft_support.ApplicationDraftPostgresTests._campaign
    _object = draft_support.ApplicationDraftPostgresTests._object
    _publish = draft_support.ApplicationDraftPostgresTests._publish
    authorize = draft_support.ApplicationDraftPostgresTests.authorize

    def setUp(self):
        draft_support.ApplicationDraftPostgresTests.setUp(self)
        self.source = self._publish(self._campaign('complete'),'COMPLETE',
            (self._object('vm-1','Database'),self._object('vm-2','Frontend')))
        self.original = self.save()
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.fixture = OwnerFixture(Path(self.temp.name)/'owner-policy.json',self.original,
                                    at=datetime.now(timezone.utc))
        self.evidence_dsn = os.environ['HOSTING_TEST_POSTGRES_ASSESSMENT_DSN']
        self.evidence_writer = AssessmentInputRepository(lambda:self.psycopg.connect(self.evidence_dsn),
            self.fixture.trust, ingest_role='hosting_assessment_ingest')
        self.evidence_reader = AssessmentInputRepository(lambda:self.psycopg.connect(self.runtime_dsn), self.fixture.trust)
        self.service = ApplicationReviewService(self.repo,self.evidence_reader)

    def save(self,**changes):
        values=dict(generation=self.source.generation,result_digest=self.source.result_digest,
            content=self.content,expected_revision=0,audit=self.audit,authorize=self.authorize)
        values.update(changes)
        return self.repo.save(self.ctx,self.scope,self.environment_id,**values)

    def document(self,**changes):
        return review_document(self.original,at=datetime.now(timezone.utc),**changes)

    def ingest(self,document):
        return self.evidence_writer.ingest(self.ctx,document,self.fixture.sign(document))

    def get(self,**changes):
        args=dict(revision=1,authorize=self.authorize);args.update(changes)
        return self.service.get(self.ctx,self.scope,self.environment_id,'app-1',**args)

    def test_signed_owner_decision_is_retained_and_consumed_without_native_authority(self):
        self.assertEqual(self.get()['status'],'UNREVIEWED')
        document=self.document();digest=self.ingest(document)
        view=self.get()
        self.assertEqual(view['status'],'REVIEWED_WITH_UNKNOWNS')
        self.assertEqual(view['evidenceDigest'],digest)
        self.assertEqual(view['unknownDependencyCount'],1)
        self.assertFalse(view['dependencyEvidenceVerified'])
        self.assertFalse(view['ownershipAccepted']);self.assertFalse(view['executionAuthorized'])
        self.assertEqual(self.repo.get(self.ctx,self.scope,self.environment_id,'app-1',authorize=self.authorize)['status'],'UNREVIEWED')

    def test_exact_evidence_retry_is_idempotent_and_retains_one_audit(self):
        document=self.document();self.assertEqual(self.ingest(document),self.ingest(document))
        with self.repo._session(self.ctx,self.scope,self.environment_id,self.authorize) as con:
            self.assertEqual(con.execute("SELECT count(*) FROM hosting_controlplane.audit_events "
                "WHERE record_kind='AssessmentInput'").fetchone()[0],1)

    def test_explicit_revocation_has_no_fallback_to_prior_acceptance(self):
        accepted=self.document();self.ingest(accepted)
        revoked=self.document(decision='REVOKE',revision=2);self.ingest(revoked)
        self.assertEqual(self.get()['status'],'REVOKED')
        with self.assertRaises(AssessmentInputDenied): self.ingest(accepted)

    def test_live_owner_key_or_evidence_revocation_holds_existing_review(self):
        document=self.document();self.ingest(document)
        self.fixture.policy['revision']+=1
        self.fixture.policy['revokedEvidenceIds']=[document['evidenceId']]
        self.fixture.write()
        with self.assertRaises(ApplicationReviewUnavailable): self.get()

    def test_new_draft_does_not_inherit_acceptance_and_history_is_superseded(self):
        self.ingest(self.document())
        content=copy.deepcopy(self.content);content['draft']['name']='Changed'
        self.save(expected_revision=1,content=content)
        self.assertEqual(self.get()['status'],'HELD_SUPERSEDED_DRAFT')
        self.assertEqual(self.get(revision=2)['status'],'UNREVIEWED')
        with self.assertRaises(AssessmentInputDenied): self.ingest(self.document(revision=2))

    def test_new_inventory_does_not_refresh_old_review_but_revocation_remains_possible(self):
        self.ingest(self.document())
        self._publish(self._campaign('new'),'PARTIAL',(self._object('vm-1','New'),),('VISIBLE_INVENTORY_ONLY',))
        self.assertEqual(self.get()['status'],'HELD_SUPERSEDED_INVENTORY')
        self.ingest(self.document(decision='REVOKE',revision=2))
        self.assertEqual(self.get()['status'],'REVOKED')

    def test_partial_inventory_owner_acceptance_does_not_produce_candidate(self):
        self.source=self._publish(self._campaign('partial'),'PARTIAL',
            (self._object('vm-1','Database'),self._object('vm-2','Frontend')),('VISIBLE_INVENTORY_ONLY',))
        self.original=self.save(expected_revision=1)
        self.ingest(self.document())
        view=self.get(revision=2)
        self.assertEqual(view['status'],'HELD_INCOMPLETE_INVENTORY');self.assertIsNone(view['candidateDigest'])

    def test_wrong_draft_digests_owner_and_generation_are_not_persisted(self):
        for key,value in (('draftRecordDigest','f'*64),('proposalDigest','e'*64),
                          ('resultDigest','d'*64),('generation',999),('draftRevision',99)):
            document=self.document();document['payload'][key]=value
            with self.subTest(field=key),self.assertRaises((ValueError,AssessmentInputDenied)):
                self.ingest(document)
        self.assertEqual(self.get()['status'],'UNREVIEWED')

    def test_runtime_cannot_ingest_decisions_or_update_original_drafts(self):
        document=self.document()
        with self.assertRaises(AssessmentInputDenied):
            self.evidence_reader.ingest(self.ctx,document,self.fixture.sign(document))
        with self.assertRaises(self.psycopg.errors.InsufficientPrivilege):
            with self.evidence_reader._session(self.ctx) as con:
                con.execute("UPDATE hosting_controlplane.assessment_inputs SET kind='APPLICATION_REVIEW'")
        with self.assertRaises(self.psycopg.errors.InsufficientPrivilege):
            with self.evidence_writer._session(self.ctx,write=True) as con:
                con.execute("UPDATE hosting_controlplane.application_draft_revisions SET status='APPROVED'")

    def test_foreign_tenant_cannot_retrieve_owner_review(self):
        self.ingest(self.document());evidence=parse_evidence(self.document())
        self.assertIsNone(self.evidence_reader.latest(TenantContext(self.ctx.organization_id,'other'),
            evidence.kind,evidence.binding_digest,datetime.now(timezone.utc)))

    def test_trust_revocation_after_lock_wait_prevents_append(self):
        document=self.document();entered=threading.Event();outcomes=[]
        args=DiscoveryRepository._scope_args(self.ctx,self.scope,self.environment_id)
        key=int.from_bytes(hashlib.sha256(_json(args).encode()).digest()[:8],'big',signed=True)
        original=self.fixture.trust.verify
        def verify(*args):
            result=original(*args);entered.set();return result
        def worker():
            try:self.ingest(document);outcomes.append('saved')
            except AssessmentInputDenied:outcomes.append('held')
        with patch.object(self.fixture.trust,'verify',verify):
            with self.psycopg.connect(self.runtime_dsn) as con:
                con.execute('SELECT pg_advisory_xact_lock(%s::bigint)',(key,))
                thread=threading.Thread(target=worker);thread.start()
                self.assertTrue(entered.wait(timeout=3))
                self.fixture.policy['revision']+=1;self.fixture.policy['revokedEvidenceIds']=[document['evidenceId']]
                self.fixture.write()
            thread.join(timeout=10);self.assertFalse(thread.is_alive())
        self.assertEqual(outcomes,['held'])
        self.assertEqual(self.get()['status'],'UNREVIEWED')

    def test_revocation_after_insert_rolls_back_evidence_and_audit(self):
        document=self.document();original=self.fixture.trust.verify;calls=[]
        def verify(*args):
            calls.append(1)
            if len(calls)==3:raise AssessmentInputDenied('revoked before commit')
            return original(*args)
        with patch.object(self.fixture.trust,'verify',verify),self.assertRaises(AssessmentInputDenied):
            self.ingest(document)
        self.assertEqual(self.get()['status'],'UNREVIEWED')
        with self.repo._session(self.ctx,self.scope,self.environment_id,self.authorize) as con:
            self.assertEqual(con.execute("SELECT count(*) FROM hosting_controlplane.audit_events "
                "WHERE record_kind='AssessmentInput'").fetchone()[0],0)

    def test_authorization_revoked_after_source_read_discloses_no_review(self):
        self.ingest(self.document());calls=[]
        def authorize(scope,at):
            calls.append(at)
            if len(calls)==3:raise PermissionError('reader revoked')
        with self.assertRaises(PermissionError):self.get(authorize=authorize)

    def test_authenticated_api_consumes_persisted_review_and_never_accepts_browser_approval(self):
        from dataclasses import replace
        from fastapi.testclient import TestClient
        from provisioner.controlplane.api import create_app
        from provisioner.controlplane.authority.model import VerifiedPrincipal, RoleGrant
        from provisioner.controlplane.authority.service import AuthorityService, JOB_READER
        from tests.provisioning.api import test_http as http_support
        from datetime import timedelta
        now=datetime.now(timezone.utc)
        principal=VerifiedPrincipal('reader',self.ctx.organization_id,self.ctx.tenant_id,'HUMAN',
            now-timedelta(minutes=1),now+timedelta(minutes=5),None,
            (RoleGrant(JOB_READER,self.scope,now+timedelta(minutes=5)),))
        class Identity:
            def authenticate(inner,token):
                if token!='synthetic-bearer':raise PermissionError('invalid')
                return principal
        class Evidence:
            def require(inner,ctx):pass
        self.ingest(self.document())
        app=create_app(http_support._Records(),AuthorityService(Identity(),http_support._Plans(),http_support._Ledger()),
            http_support._Jobs(),self.environments,evidence_gate=Evidence(),
            application_drafts=self.repo,application_reviews=self.service)
        path=f'/v1/environments/{self.environment_id}/application-drafts/app-1/review?revision=1'
        with TestClient(app) as client:
            response=client.get(path,headers={'Authorization':'Bearer synthetic-bearer'})
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(response.json()['status'],'REVIEWED_WITH_UNKNOWNS')
            self.assertFalse(response.json()['executionAuthorized'])
            self.assertEqual(client.post(path,headers={'Authorization':'Bearer synthetic-bearer'},json={'approve':True}).status_code,405)


if __name__=='__main__':unittest.main()
