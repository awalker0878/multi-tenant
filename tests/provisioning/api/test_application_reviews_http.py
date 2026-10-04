"""The owner-review API is scoped read-only composition, never a signing service."""
import copy
import unittest
from dataclasses import replace

from fastapi.testclient import TestClient
from provisioner.controlplane.api import create_app
from provisioner.controlplane.authority.service import AuthorityService
from provisioner.controlplane.discovery.application_reviews import ApplicationReviewService, ApplicationReviewUnavailable
from tests.provisioning.api import test_http as support
from tests.provisioning.api import test_application_drafts_http as draft_support


class Reviews(ApplicationReviewService):
    def __init__(self):
        self.before_check=None;self.corrupt={};self.missing=False;self.held=False;self.calls=[]
    def get(self,ctx,scope,environment_id,application_group_id,*,revision,authorize):
        if self.before_check:self.before_check()
        authorize(scope,support.NOW)
        self.calls.append((ctx,scope,environment_id,application_group_id,revision))
        if self.held:raise ApplicationReviewUnavailable('private reviewer key file')
        if self.missing:return None
        return {'format':'hosting-application-review-status/1','scope':vars(scope),
            'environmentId':environment_id,'applicationGroupId':application_group_id,
            'draftRevision':revision,'status':'REVIEWED_WITH_UNKNOWNS',
            'dependencyEvidenceVerified':False,'ownershipAccepted':False,'executionAuthorized':False,**self.corrupt}


class ApplicationReviewHttpTests(unittest.TestCase):
    def setUp(self):
        draft_support.ApplicationDraftHttpTests.setUp(self)
        self.reviews=Reviews();self.client=self.build();self.path+='/review'

    def build(self,enabled=True):
        return TestClient(create_app(support._Records(),
            AuthorityService(self.identity,support._Plans(),support._Ledger(),clock=lambda:support.NOW),
            support._Jobs(),self.environments,evidence_gate=self.gate,application_drafts=self.repo,
            application_reviews=getattr(self,'reviews',None) if enabled else None,clock=lambda:support.NOW))

    def get(self,token='job-reader',suffix='?revision=1'):
        return self.client.get(self.path+suffix,headers={'Authorization':'Bearer '+token})

    def test_scoped_reader_obtains_only_exact_revision_review(self):
        response=self.get();self.assertEqual(response.status_code,200,response.text)
        self.assertFalse(response.json()['ownershipAccepted']);self.assertFalse(response.json()['executionAuthorized'])
        self.assertEqual(response.headers['cache-control'],'no-store')
        self.assertEqual(self.reviews.calls[0][-1],1)

    def test_anonymous_foreign_scope_and_worker_cannot_read(self):
        self.assertEqual(self.client.get(self.path+'?revision=1').status_code,401)
        for token in ('other-tenant','other-wsd','approver','reader'):
            with self.subTest(token=token):self.assertEqual(self.get(token).status_code,404)
        self.assertEqual(self.reviews.calls,[])

    def test_exact_revision_is_required_and_invalid_bounds_are_rejected(self):
        for suffix in ('','?revision=0','?revision=-1','?revision=true','?revision=9223372036854775808'):
            with self.subTest(suffix=suffix):self.assertEqual(self.get(suffix=suffix).status_code,422)
        self.assertEqual(self.reviews.calls,[])

    def test_missing_disabled_or_invalid_live_evidence_does_not_fall_back(self):
        self.reviews.missing=True;self.assertEqual(self.get().status_code,404)
        self.reviews.missing=False;self.reviews.held=True
        response=self.get();self.assertEqual(response.status_code,503)
        self.assertNotIn('private reviewer',response.text)
        self.assertEqual(self.build(False).get(self.path+'?revision=1',headers={'Authorization':'Bearer operator'}).status_code,503)

    def test_user_approval_post_or_put_is_not_an_endpoint(self):
        for method in ('post','put','delete'):
            response=getattr(self.client,method)(self.path,headers={'Authorization':'Bearer operator'})
            self.assertEqual(response.status_code,405)
        self.assertEqual(self.reviews.calls,[])

    def test_changed_actor_or_revoked_read_scope_is_rechecked(self):
        self.reviews.before_check=lambda:self.identity.tokens.pop('job-reader')
        self.assertEqual(self.get().status_code,404)
        self.assertEqual(self.reviews.calls,[])

    def test_response_cannot_inject_ownership_or_change_draft_binding(self):
        for key,value in (('executionAuthorized',True),('ownershipAccepted',True),('scope',{}),
            ('draftRevision',True),('draftRevision',2),('status','APPROVED'),('dependencyEvidenceVerified',True),('environmentId','other'),('applicationGroupId','other')):
            self.reviews.corrupt={key:value}
            with self.subTest(field=key):self.assertEqual(self.get().status_code,503)


if __name__=='__main__':unittest.main()
