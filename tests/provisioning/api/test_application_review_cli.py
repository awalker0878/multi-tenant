"""Read-only operator review status; server evidence remains the sole authority."""
import copy
import io
import json
import unittest
from dataclasses import replace
from datetime import timedelta
from unittest.mock import patch

import httpx

from provisioner.cli import operator, application_drafts
from provisioner.controlplane.discovery.application_reviews import _view, REVIEW_STATUSES
from provisioner.controlplane.discovery.assessment_inputs import parse_evidence
from tests.provisioning.discovery.test_application_review import stored_fixture, review_document, NOW
from tests.provisioning.discovery import test_grouping as grouping


class ApplicationReviewCliTests(unittest.TestCase):
    def setUp(self):
        self.stored, self.result = stored_fixture()
        self.evidence = parse_evidence(review_document(self.stored))
        self.value = _view(self.stored, self.result, self.evidence, 1, 1, NOW)
        self.seen = []

    def command(self, *extra):
        return ['application-drafts', 'review', '--environment', self.stored.environment_id,
                '--id', self.stored.application_group_id, '--revision', '1', *extra]

    def invoke(self, command=None, handler=None):
        def default(request):
            self.seen.append(request)
            return httpx.Response(200, json=copy.deepcopy(self.value))
        out, err = io.StringIO(), io.StringIO()
        code = operator.run(['--api-url', 'https://api.example', '--token-stdin',
            *(command or self.command())], stdin=io.StringIO('synthetic-sso-token\n'),
            stdout=out, stderr=err, transport=httpx.MockTransport(handler or default))
        self.assertNotIn('synthetic-sso-token', out.getvalue()+err.getvalue())
        return code, out.getvalue(), err.getvalue()

    def test_exact_revision_is_one_get_without_a_decision_or_signature(self):
        code, out, err = self.invoke(self.command('--record-digest', self.stored.record_digest))
        self.assertEqual((code, err), (0, ''))
        self.assertEqual(json.loads(out), self.value)
        self.assertEqual(len(self.seen), 1)
        request = self.seen[0]
        self.assertEqual(request.method, 'GET')
        self.assertEqual(request.url.path,
            '/v1/environments/source/application-drafts/'+self.stored.application_group_id+'/review')
        self.assertEqual(dict(request.url.params), {'revision': '1'})
        self.assertEqual(request.content, b'')
        self.assertEqual(request.headers['Cache-Control'], 'no-store')
        self.assertFalse(json.loads(out)['executionAuthorized'])
        self.assertFalse(json.loads(out)['ownershipAccepted'])

    def test_required_revision_and_nonexistent_mutation_verbs_are_parser_errors(self):
        for argv in (self.command()[:-2], self.command()+['--approve'],
                     ['application-drafts','accept'], ['application-drafts','revoke']):
            with self.subTest(argv=argv), patch('sys.stderr', io.StringIO()), self.assertRaises(SystemExit):
                operator.build_parser().parse_args(['--api-url','https://api.example','--token-stdin',*argv])
        self.assertEqual(self.seen, [])

    def test_invalid_revision_digest_and_escaped_identity_fail_before_http(self):
        for revision in ('0', '-1', '9223372036854775808'):
            with self.subTest(revision=revision):
                code, out, err = self.invoke(self.command()[:-1]+[revision])
                self.assertEqual((code,out),(3,''))
                self.assertEqual(json.loads(err)['error'],'INVALID_INPUT')
        for digest in ('A'*64,'a'*63,'a'*64+'\n'):
            self.assertEqual(self.invoke(self.command('--record-digest',digest))[0],3)
        args=operator.build_parser().parse_args(['--api-url','https://api.example','--token-stdin',*self.command()])
        for value in (True, 0, 2**63):
            args.revision=value
            with self.assertRaises(ValueError):operator._request(args)
        args.revision=1
        for field,value in (('id','../foreign'),('environment','env?scope=other')):
            original=getattr(args,field);setattr(args,field,value)
            with self.assertRaises(ValueError):operator._request(args)
            setattr(args,field,original)
        self.assertEqual(self.seen, [])

    def test_every_actual_server_status_retains_its_meaning_and_false_authority(self):
        variants=[_view(self.stored,self.result,None,1,1,NOW),
                  _view(self.stored,None,None,1,2,NOW),
                  _view(self.stored,None,None,2,1,NOW),
                  self.value,
                  _view(self.stored,self.result,parse_evidence(review_document(self.stored,decision='REVOKE')),1,1,NOW)]
        for completeness,captured,edges in (
                ('PARTIAL',NOW-timedelta(minutes=10),None),
                ('COMPLETE',NOW-timedelta(hours=2),None),
                ('COMPLETE',NOW-timedelta(minutes=10),(replace(grouping.UNKNOWN,observed_at=NOW-timedelta(minutes=10)),))):
            result=replace(self.result,completeness=completeness,captured_at=captured,
                collection_errors=('VISIBLE_INVENTORY_ONLY',) if completeness=='PARTIAL' else ())
            stored,result=stored_fixture(result=result,edges=edges)
            variants.append(_view(stored,result,parse_evidence(review_document(stored)),1,1,NOW))
        self.assertEqual({v['status'] for v in variants}, REVIEW_STATUSES)
        for value in variants:
            self.value=value
            with self.subTest(status=value['status']):
                code,out,err=self.invoke()
                self.assertEqual((code,err),(0,''))
                self.assertEqual(json.loads(out),value)

    def test_record_digest_mismatch_is_not_printed_or_retried(self):
        code,out,err=self.invoke(self.command('--record-digest','f'*64))
        self.assertEqual((code,out),(3,''))
        self.assertEqual(json.loads(err)['error'],'APPLICATION_DRAFT_RESPONSE_INVALID')
        self.assertEqual(len(self.seen),1)

    def test_missing_extra_or_misdirected_fields_are_not_successful_reviews(self):
        valid=copy.deepcopy(self.value)
        for field in valid:
            self.value={k:v for k,v in valid.items() if k!=field}
            with self.subTest(missing=field):self.assertEqual(self.invoke()[0],3)
        for field,value in (('environmentId','other'),('applicationGroupId','other'),
                ('draftRevision',2),('draftRevision',True),('generation',True),('latestGeneration',0),
                ('latestDraftRevision',0),('draftRecordDigest','bad'),('proposalDigest','A'*64),
                ('resultDigest','x'*64),('evidenceDigest','bad'),('status','APPROVED'),
                ('dependencyEvidenceVerified',True),('executionAuthorized',True),
                ('ownershipAccepted',True),('unexpected','private-server-value'),
                ('scope',{}),('scope',{**valid['scope'],'platform_family':'unknown'}),
                ('scope',{**valid['scope'],'endpoint_id':'bad\n'})):
            self.value={**copy.deepcopy(valid),field:value}
            with self.subTest(field=field):
                code,out,err=self.invoke()
                self.assertEqual((code,out),(3,''));self.assertNotIn('private',err)

    def test_candidate_and_status_contradictions_fail_closed(self):
        valid=copy.deepcopy(self.value)
        for changes in ({'candidateDigest':None},{'unknownDependencyCount':True},
                {'unknownDependencyCount':1},{'ownerDecision':'REVOKE'},
                {'latestDraftRevision':2},{'latestGeneration':2},
                {'status':'REVOKED'}, {'status':'HELD_INCOMPLETE_INVENTORY'},
                {'status':'HELD_SUPERSEDED_DRAFT'}, {'status':'REVIEWED_WITH_UNKNOWNS'},
                {'evidenceRevision':0}, {'evidenceRevision':True}, {'ownerId':None}):
            self.value={**copy.deepcopy(valid),**changes}
            with self.subTest(changes=changes):self.assertEqual(self.invoke()[0],3)
        empty=_view(self.stored,self.result,None,1,1,NOW)
        for changes in ({'ownerId':'owner-a'},{'evidenceId':'claim'},
                        {'status':'REVIEWED_ASSESSMENT_ONLY'},{'candidateDigest':'a'*64}):
            self.value={**empty,**changes}
            with self.subTest(changes=changes):self.assertEqual(self.invoke()[0],3)

    def test_expiry_and_timestamp_coherence_are_checked_without_reissuing_evidence(self):
        valid=copy.deepcopy(self.value)
        for field,value in (('checkedAt','bad'),('checkedAt',NOW.replace(tzinfo=None).isoformat()),
                ('reviewedAt',(NOW+timedelta(seconds=1)).isoformat()),
                ('expiresAt',NOW.isoformat()),('expiresAt',(NOW+timedelta(hours=2)).isoformat()),
                ('expiresAt','2026-09-30T00:00:00+01:00')):
            self.value={**valid,field:value}
            with self.subTest(field=field,value=value):self.assertEqual(self.invoke()[0],3)
        self.value={**valid,'checkedAt':valid['checkedAt'].replace('+00:00','Z')}
        self.assertEqual(self.invoke()[0],0)

    def test_revoked_or_held_review_cannot_smuggle_a_candidate(self):
        revoked=_view(self.stored,None,parse_evidence(review_document(self.stored,decision='REVOKE')),2,2,NOW)
        self.value=revoked
        self.assertEqual(self.invoke()[0],0)
        for changes in ({'candidateDigest':'a'*64},{'unknownDependencyCount':0},
                        {'status':'UNREVIEWED'},{'ownerDecision':'ACCEPT_FOR_ASSESSMENT'}):
            self.value={**revoked,**changes}
            with self.subTest(changes=changes):self.assertEqual(self.invoke()[0],3)

    def test_transport_failures_do_not_fall_back_to_draft_or_prior_review(self):
        for status in (302,401,403,404,503):
            def failed(request):
                self.seen.append(request)
                return httpx.Response(status,json={'error':{'code':'APPLICATION_REVIEW_UNAVAILABLE',
                    'message':'private owner key detail'}},headers={'location':'https://other.invalid'})
            before=len(self.seen)
            code,out,err=self.invoke(handler=failed)
            with self.subTest(status=status):
                self.assertEqual((code,out),(2,''));self.assertNotIn('private',err)
                self.assertEqual(len(self.seen),before+1)
        def lost(request):
            self.seen.append(request);raise httpx.ReadTimeout('private credentials')
        code,out,err=self.invoke(handler=lost)
        self.assertEqual((code,out),(3,''));self.assertEqual(json.loads(err)['error'],'API_UNAVAILABLE')

    def test_strict_json_bounds_and_non_200_success_are_not_review_status(self):
        duplicate=json.dumps(self.value)[:-1]+',"status":"APPROVED"}'
        for status,raw in ((200,duplicate.encode()),(200,b'{"revision":1e999}'),
                (200,b'\xff'),(202,json.dumps(self.value).encode()),(204,b'')):
            def reply(request):
                self.seen.append(request);return httpx.Response(status,content=raw)
            with self.subTest(status=status,raw=raw[:30]):
                code,out,err=self.invoke(handler=reply)
                self.assertEqual((code,out),(3,''))
        with patch.object(operator,'_MAX_RESPONSE',100):
            self.assertEqual(self.invoke()[0],3)

    def test_unknown_action_is_not_treated_as_save(self):
        args=operator.build_parser().parse_args(['--api-url','https://api.example','--token-stdin',*self.command()])
        args.action='approve'
        with self.assertRaises(ValueError):operator._request(args)


if __name__ == '__main__':
    unittest.main()
