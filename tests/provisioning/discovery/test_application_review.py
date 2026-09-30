"""Real owner signatures bound to synthetic drafts; no native qualification."""
import copy
import json
import tempfile
import unittest
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from provisioner.controlplane.discovery.application_drafts import StoredApplicationDraft, _digest
from provisioner.controlplane.discovery.application_review import (
    APPLICATION_OWNER, REVIEW_KIND, require_draft_binding, review_binding)
from provisioner.controlplane.discovery.application_reviews import _view, ApplicationReviewUnavailable
from provisioner.controlplane.discovery.assessment_inputs import AssessmentInputDenied, parse_evidence
from provisioner.controlplane.discovery.grouping import proposal_document
from provisioner.controlplane.discovery.model import _json, _scope_json
from tests.provisioning.discovery.test_assessment_inputs import SignedFixture, NOW, encoded
from tests.provisioning.discovery import test_grouping as grouping


def stored_fixture(*, result=None, edges=None, recorded_by='editor-a'):
    result = result or replace(grouping.RESULT, captured_at=NOW-timedelta(minutes=10))
    edges = edges if edges is not None else (replace(grouping.KNOWN, observed_at=result.captured_at),)
    proposal = proposal_document(result, grouping.DRAFT, edges)
    row = StoredApplicationDraft('source', result.scope, grouping.DRAFT.application_group_id,
        1, 1, result.digest, _json(proposal), _digest(proposal), recorded_by,
        NOW-timedelta(minutes=5), '')
    return replace(row, record_digest=_digest(row.binding())), result


def review_document(stored, *, at=NOW, decision='ACCEPT_FOR_ASSESSMENT', revision=1):
    return {'format':'hosting-assessment-evidence/1', 'kind':REVIEW_KIND,
        'evidenceId':'owner-decision-'+str(revision), 'revision':revision,
        'issuedAt':at.isoformat(), 'expiresAt':(at+timedelta(minutes=30)).isoformat(),
        'payload':{'environmentId':stored.environment_id,'scope':_scope_json(stored.scope),
            'applicationGroupId':stored.application_group_id,'draftRevision':stored.revision,
            'draftRecordDigest':stored.record_digest,'generation':stored.generation,
            'resultDigest':stored.result_digest,'proposalDigest':stored.proposal_digest,
            'ownerId':json.loads(stored.proposal_json)['draft']['ownerId'],
            'decision':decision,'reviewReference':'owner-ticket-1','reviewedAt':at.isoformat()}}


class OwnerFixture(SignedFixture):
    def __init__(self, path, stored, *, at=NOW):
        super().__init__(path)
        self.keys[APPLICATION_OWNER] = Ed25519PrivateKey.generate()
        self.policy['issuedAt'] = (at-timedelta(minutes=10)).isoformat()
        self.policy['expiresAt'] = (at+timedelta(hours=2)).isoformat()
        self.policy['enrollments'].append({
            'keyId':APPLICATION_OWNER+'-key','subjectId':json.loads(stored.proposal_json)['draft']['ownerId'],
            'role':APPLICATION_OWNER, 'publicKey':encoded(self.keys[APPLICATION_OWNER].public_key().public_bytes_raw()),
            'environments':[{'environmentId':stored.environment_id,'scope':_scope_json(stored.scope)}],
            'notBefore':(at-timedelta(hours=1)).isoformat(),'expiresAt':(at+timedelta(hours=2)).isoformat(),
            'revokedAt':None})
        self.write()

    def sign(self, document):
        if document['kind'] != REVIEW_KIND:
            return super().sign(document)
        return ({'keyId':APPLICATION_OWNER+'-key', 'signature':encoded(
            self.keys[APPLICATION_OWNER].sign(_json(document).encode('ascii')))},)


class ApplicationReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.stored, self.result = stored_fixture()
        self.fixture = OwnerFixture(Path(self.temp.name)/'trust.json',self.stored)
        self.document = review_document(self.stored)

    def verify(self, document=None, *, at=NOW, signatures=None):
        doc = document or self.document
        evidence = parse_evidence(doc)
        self.fixture.trust.verify(evidence, signatures or self.fixture.sign(doc), at)
        return evidence

    def test_real_signature_and_exact_draft_produce_only_assessment_candidate(self):
        evidence = self.verify()
        require_draft_binding(evidence.value,self.stored)
        view = _view(self.stored,self.result,evidence,1,1,NOW)
        self.assertEqual(view['status'],'REVIEWED_ASSESSMENT_ONLY')
        self.assertEqual(view['ownerId'],'owner-a')
        self.assertEqual(view['evidenceDigest'],evidence.digest)
        self.assertEqual(len(view['candidateDigest']),64)
        self.assertFalse(view['ownershipAccepted']); self.assertFalse(view['executionAuthorized'])

    def test_unknown_dependencies_survive_review(self):
        edges=(replace(grouping.UNKNOWN, observed_at=self.result.captured_at),)
        stored,result=stored_fixture(edges=edges)
        evidence=self.verify(review_document(stored))
        view=_view(stored,result,evidence,1,1,NOW)
        self.assertEqual(view['status'],'REVIEWED_WITH_UNKNOWNS')
        self.assertEqual(view['unknownDependencyCount'],1)

    def test_partial_or_unknown_inventory_is_not_promoted_by_owner_signature(self):
        for completeness in ('PARTIAL','UNKNOWN'):
            result=replace(self.result,completeness=completeness,collection_errors=('VISIBLE_INVENTORY_ONLY',))
            stored,result=stored_fixture(result=result)
            evidence=self.verify(review_document(stored))
            view=_view(stored,result,evidence,1,1,NOW)
            self.assertEqual(view['status'],'HELD_INCOMPLETE_INVENTORY')
            self.assertIsNone(view['candidateDigest'])

    def test_stale_inventory_cannot_be_requalified_by_recent_owner_review(self):
        result=replace(self.result,captured_at=NOW-timedelta(hours=2))
        stored,result=stored_fixture(result=result)
        view=_view(stored,result,self.verify(review_document(stored)),1,1,NOW)
        self.assertEqual(view['status'],'HELD_STALE_INVENTORY')

    def test_changed_revision_or_inventory_does_not_reuse_old_review(self):
        for generation,revision,status in ((2,1,'HELD_SUPERSEDED_INVENTORY'),(1,2,'HELD_SUPERSEDED_DRAFT')):
            view=_view(self.stored,None,self.verify(),generation,revision,NOW)
            self.assertEqual(view['status'],status); self.assertIsNone(view['candidateDigest'])

    def test_missing_review_is_unreviewed_not_inferred_from_owner_text(self):
        view=_view(self.stored,None,None,1,1,NOW)
        self.assertEqual(view['status'],'UNREVIEWED'); self.assertIsNone(view['ownerDecision'])

    def test_revoke_shares_acceptance_stream_but_cannot_make_candidate(self):
        accept=self.verify()
        revoke=self.verify(review_document(self.stored,decision='REVOKE',revision=2))
        self.assertEqual(accept.binding_digest,revoke.binding_digest)
        view=_view(self.stored,None,revoke,2,3,NOW)
        self.assertEqual(view['status'],'REVOKED'); self.assertIsNone(view['candidateDigest'])

    def test_each_immutable_draft_reference_is_required(self):
        original=self.verify().value
        for name,value in (('environment_id','other'),('scope',replace(self.stored.scope,endpoint_id='other')),
            ('application_group_id','other'),('draft_revision',2),('draft_record_digest','b'*64),
            ('generation',2),('result_digest','c'*64),('proposal_digest','d'*64),('owner_id','other')):
            with self.subTest(field=name),self.assertRaises(ValueError):
                require_draft_binding(replace(original,**{name:value}),self.stored)

    def test_author_cannot_sign_as_own_independent_reviewer(self):
        with self.assertRaises(ValueError):
            require_draft_binding(self.verify().value,replace(self.stored,recorded_by='owner-a'))

    def test_owner_review_cannot_predate_the_persisted_proposal(self):
        with self.assertRaises(ValueError):
            require_draft_binding(replace(self.verify().value,
                reviewed_at=self.stored.recorded_at-timedelta(microseconds=1)),self.stored)

    def test_a_different_enrolled_owner_cannot_sign_the_proposed_owner_name(self):
        self.fixture.policy['enrollments'][-1]['subjectId']='other-owner'
        self.fixture.write()
        with self.assertRaises(AssessmentInputDenied): self.verify()

    def test_source_platform_reviewer_is_not_an_application_owner(self):
        sig=({'keyId':'SOURCE_EXIT-key','signature':encoded(self.fixture.keys['SOURCE_EXIT'].sign(
            _json(self.document).encode('ascii')))},)
        with self.assertRaises(AssessmentInputDenied): self.verify(signatures=sig)

    def test_signature_tampering_and_missing_signatures_are_rejected(self):
        evidence=parse_evidence(self.document)
        for signatures in ((),({'keyId':APPLICATION_OWNER+'-key','signature':encoded(b'x'*64)},)):
            with self.assertRaises(AssessmentInputDenied): self.fixture.trust.verify(evidence,signatures,NOW)
        changed=copy.deepcopy(self.document); changed['payload']['reviewReference']='changed'
        with self.assertRaises(AssessmentInputDenied): self.verify(changed,signatures=self.fixture.sign(self.document))

    def test_owner_enrollment_cannot_use_root_or_another_roles_identity(self):
        for field,value in (('publicKey',encoded(self.fixture.root.public_key().public_bytes_raw())),
                            ('subjectId','SOURCE_EXIT-reviewer')):
            original=copy.deepcopy(self.fixture.policy)
            self.fixture.policy['enrollments'][-1][field]=value; self.fixture.write()
            with self.assertRaises(AssessmentInputDenied): self.verify()
            self.fixture.policy=original

    def test_current_key_revocation_removal_scope_and_evidence_revocation_hold(self):
        original=copy.deepcopy(self.fixture.policy)
        for mode in ('key','removed','scope','evidence'):
            self.fixture.policy=copy.deepcopy(original)
            if mode=='key': self.fixture.policy['enrollments'][-1]['revokedAt']=NOW.isoformat()
            if mode=='removed': self.fixture.policy['enrollments'].pop()
            if mode=='scope': self.fixture.policy['enrollments'][-1]['environments'][0]['environmentId']='other'
            if mode=='evidence': self.fixture.policy['revokedEvidenceIds']=[self.document['evidenceId']]
            self.fixture.policy['revision']+=('key','removed','scope','evidence').index(mode)+1
            self.fixture.write()
            with self.assertRaises(AssessmentInputDenied): self.verify()

    def test_expired_or_not_yet_valid_review_is_never_usable(self):
        for at in (NOW-timedelta(seconds=1),NOW+timedelta(minutes=30)):
            with self.subTest(at=at),self.assertRaises(AssessmentInputDenied): self.verify(at=at)

    def test_unknown_fields_decisions_and_unsafe_numeric_bindings_are_rejected(self):
        for name,value in (('draftRevision',True),('generation',0),('draftRevision',2**63),
            ('decision','APPROVE_EXECUTION'),('decision',{}),('ownerId',''),('reviewReference',''),
            ('draftRecordDigest','F'*64),('proposalDigest',None),('executionAuthorized',True)):
            doc=copy.deepcopy(self.document);doc['payload'][name]=value
            with self.subTest(field=name),self.assertRaises((ValueError,AssessmentInputDenied)):
                parse_evidence(doc)

    def test_review_lifetime_and_timestamp_order_are_bounded(self):
        for name,value in (('expiresAt',(NOW+timedelta(hours=2)).isoformat()),
                           ('issuedAt',(NOW-timedelta(seconds=1)).isoformat())):
            doc=copy.deepcopy(self.document);doc[name]=value
            with self.assertRaises(AssessmentInputDenied): parse_evidence(doc)

    def test_every_exact_draft_has_distinct_stream_and_no_boolean_revision(self):
        evidence=self.verify()
        self.assertNotEqual(evidence.binding_digest,review_binding(self.stored.environment_id,
            self.stored.scope,self.stored.application_group_id,2,self.stored.record_digest))
        with self.assertRaises(ValueError):
            review_binding('source',self.stored.scope,self.stored.application_group_id,True,self.stored.record_digest)

    def test_missing_or_mismatched_source_is_not_accepted(self):
        for result in (None,replace(self.result,campaign_id='other')):
            with self.assertRaises(ApplicationReviewUnavailable):
                _view(self.stored,result,self.verify(),1,1,NOW)


if __name__=='__main__': unittest.main()
