"""Transport tests use isolated ports; separate PostgreSQL tests verify persistence."""
import copy
import json
import unittest
from dataclasses import replace
from types import SimpleNamespace

from fastapi.testclient import TestClient

from provisioner.controlplane.api import create_app
from provisioner.controlplane.authority.service import AuthorityService
from provisioner.controlplane.discovery.application_drafts import ApplicationDraftRepository, ApplicationDraftConflict
from provisioner.controlplane.evidence.gate import EvidenceHold
from provisioner.controlplane.persistence.environments import EnvironmentDeclaration, RegisteredEnvironment
from tests.provisioning.api import test_http as support
from tests.provisioning.discovery.test_application_draft_contract import content


class _Drafts(ApplicationDraftRepository):
    def __init__(self):
        self.saved=[]; self.reads=[]; self.before_check=None; self.conflict=False; self.missing=False

    def save(self,ctx,scope,environment_id,**args):
        if self.before_check: self.before_check()
        args['authorize'](scope,support.NOW)
        if self.conflict: raise ApplicationDraftConflict('private native state')
        self.saved.append((ctx,scope,environment_id,args))
        return SimpleNamespace(revision=args['expected_revision']+1)

    def get(self,ctx,scope,environment_id,application_group_id,*,revision=None,authorize):
        if self.before_check: self.before_check()
        authorize(scope,support.NOW)
        self.reads.append((ctx,scope,environment_id,application_group_id,revision))
        if self.missing: return None
        return {'scope':vars(scope),'environmentId':environment_id,'applicationGroupId':application_group_id,
                'status':'UNREVIEWED','revision':revision or 2,
                'recordedBy':self.saved[-1][3]['audit'].actor_id if self.saved else 'original-actor',
                'sourceSuperseded':True,'ownershipAccepted':False,'executionAuthorized':False}


class ApplicationDraftHttpTests(unittest.TestCase):
    def setUp(self):
        self.identity=support._Identity(); self.repo=_Drafts(); self.environments=support._Environments()
        decl=EnvironmentDeclaration('env-01','Source',support.SOURCE_SCOPE)
        self.environments.rows[('org-01','tenant-01','env-01')]=RegisteredEnvironment(
            decl,'operator',decl.digest(),support.NOW)
        self.gate=support._VerifiedEvidence()
        self.client=self.build()
        self.path='/v1/environments/env-01/application-drafts/application-a'
        self.payload={**content(),'generation':1,'resultDigest':'a'*64,'expectedRevision':0}

    def build(self,enabled=True):
        return TestClient(create_app(support._Records(),
            AuthorityService(self.identity,support._Plans(),support._Ledger(),clock=lambda:support.NOW),
            support._Jobs(),self.environments,evidence_gate=self.gate,
            application_drafts=self.repo if enabled else None,clock=lambda:support.NOW))

    def put(self,token='operator',payload=None):
        return self.client.put(self.path,json=payload or self.payload,
                               headers={'Authorization':'Bearer '+token})

    def test_authenticated_author_and_scope_are_not_taken_from_proposal(self):
        response=self.put('editor'); self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['recordedBy'],'editor@example.org')
        ctx,scope,env,args=self.repo.saved[0]
        self.assertEqual(scope,support.SOURCE_SCOPE); self.assertEqual(env,'env-01')
        self.assertEqual(args['content']['draft']['ownerId'],'owner-a')
        self.assertFalse(response.json()['ownershipAccepted']); self.assertFalse(response.json()['executionAuthorized'])
        self.assertEqual(response.headers['cache-control'],'no-store')

    def test_anonymous_foreign_tenant_or_read_only_user_cannot_write(self):
        self.assertEqual(self.client.put(self.path,json=self.payload).status_code,401)
        for token in ('reader','job-reader','other-tenant','other-wsd','approver'):
            with self.subTest(token=token): self.assertEqual(self.put(token).status_code,404)
        self.assertEqual(self.repo.saved,[])

    def test_exact_scope_reader_can_read_history_without_write_access(self):
        response=self.client.get(self.path+'?revision=1',headers={'Authorization':'Bearer job-reader'})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['revision'],1)
        self.assertTrue(response.json()['sourceSuperseded'])
        self.assertEqual(self.repo.reads[-1][-1],1)

    def test_client_cannot_supply_actor_review_or_execution_claims(self):
        for key in ('recordedBy','review','executionAuthorized','ownershipAccepted','scope'):
            value={**self.payload,key:'untrusted'}
            with self.subTest(key=key): self.assertEqual(self.put(payload=value).status_code,422)
        self.assertEqual(self.repo.saved,[])

    def test_duplicate_nested_json_is_rejected_before_persistence(self):
        raw=json.dumps(self.payload).replace('"source": "CMDB"','"source":"CMDB","source":"GUEST"')
        response=self.client.put(self.path,content=raw,headers={
            'Authorization':'Bearer operator','Content-Type':'application/json'})
        self.assertEqual(response.status_code,422,response.text)
        self.assertEqual(self.repo.saved,[])

    def test_changed_path_identity_and_wrong_media_type_are_rejected(self):
        value=copy.deepcopy(self.payload); value['draft']['applicationGroupId']='other'
        self.assertEqual(self.put(payload=value).status_code,422)
        response=self.client.put(self.path,content=json.dumps(self.payload),headers={'Authorization':'Bearer operator'})
        self.assertEqual(response.status_code,422); self.assertEqual(self.repo.saved,[])

    def test_conflict_does_not_expose_private_error_or_return_success(self):
        self.repo.conflict=True
        response=self.put(); self.assertEqual(response.status_code,409)
        self.assertNotIn('private native state',response.text)

    def test_revocation_during_transaction_rechecks_the_same_session(self):
        self.repo.before_check=lambda:self.identity.tokens.pop('operator')
        self.assertEqual(self.put().status_code,404)
        self.assertEqual(self.repo.saved,[])

    def test_identity_replacement_cannot_attribute_write_to_previous_actor(self):
        def changed():
            self.identity.tokens['operator']=replace(self.identity.tokens['operator'],subject='different-subject')
        self.repo.before_check=changed
        self.assertEqual(self.put().status_code,404); self.assertEqual(self.repo.saved,[])

    def test_evidence_outage_blocks_drafts_but_not_scoped_history(self):
        def held(_): raise EvidenceHold('private evidence service outage')
        self.gate.require=held
        response=self.put(); self.assertEqual(response.status_code,503)
        self.assertNotIn('private evidence',response.text)
        self.assertEqual(self.client.get(self.path,headers={'Authorization':'Bearer operator'}).status_code,200)

    def test_missing_draft_disabled_store_and_invalid_revision_are_explicit(self):
        self.repo.missing=True
        self.assertEqual(self.client.get(self.path,headers={'Authorization':'Bearer operator'}).status_code,404)
        self.assertEqual(self.build(enabled=False).put(self.path,json=self.payload,
            headers={'Authorization':'Bearer operator'}).status_code,503)
        for revision in ('0','-1','true','9223372036854775808'):
            self.assertEqual(self.client.get(self.path+'?revision='+revision,
                headers={'Authorization':'Bearer operator'}).status_code,422)

    def test_boolean_and_float_revisions_are_not_coerced(self):
        for field in ('generation','expectedRevision'):
            for value in (True, 1.0, '1', -1, 2**63):
                payload={**self.payload, field:value}
                self.assertEqual(self.put(payload=payload).status_code,422)
        self.assertEqual(self.repo.saved,[])

    def test_openapi_documents_revision_precondition_without_authority_fields(self):
        operation=self.client.get('/openapi.json').json()['paths'][
            '/v1/environments/{environment_id}/application-drafts/{application_id}']['put']
        schema=operation['requestBody']['content']['application/json']['schema']
        self.assertIn('expectedRevision',schema['required'])
        self.assertFalse(schema['additionalProperties'])
        self.assertIn('security',operation)

    def test_wrong_scope_or_claimed_approval_is_not_returned(self):
        original=self.repo.get
        for key,value in (('scope',{}),('environmentId','foreign'),('executionAuthorized',True),('status','APPROVED')):
            def bad(*args,**kwargs):
                result=original(*args,**kwargs); result[key]=value; return result
            self.repo.get=bad
            response=self.client.get(self.path,headers={'Authorization':'Bearer operator'})
            self.assertEqual(response.status_code,503)
        self.repo.get=original

    def test_oversized_body_is_not_stored(self):
        value=copy.deepcopy(self.payload); value['draft']['name']='x'*131073
        self.assertEqual(self.put(payload=value).status_code,422); self.assertEqual(self.repo.saved,[])


if __name__=='__main__': unittest.main()
