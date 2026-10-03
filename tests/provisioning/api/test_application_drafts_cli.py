"""One-request draft CLI behavior; the server retains sole write authority."""
import copy
import io
import json
import os
import ssl
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import certifi
import httpx

from provisioner.cli import operator
from tests.provisioning.discovery.test_application_draft_contract import content


class ApplicationDraftCliTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.file = self.root/'proposal.json'
        self.proposal = content()
        self.file.write_text(json.dumps(self.proposal))
        self.seen = []
        self.value = {'format': 'hosting-application-draft-revision/1',
            'environmentId': 'env:1', 'applicationGroupId': 'application-a',
            'revision': 2, 'generation': 3, 'resultDigest': 'a'*64,
            'latestGeneration': 3, 'sourceSuperseded': False,
            'status': 'UNREVIEWED', 'ownershipAccepted': False, 'executionAuthorized': False,
            'scope': {'organization_id':'org-1'},
            'proposal': {**copy.deepcopy(self.proposal), 'format':'hosting-application-group-candidate/1',
                         'discoveryDigest':'a'*64, 'scope':{'organization_id':'org-1'}},
            'recordedBy': 'actual-server-actor'}

    def command(self, action='get', *extra):
        base = ['application-drafts', action, '--environment', 'env:1']
        if action != 'list': base += ['--id', 'application-a']
        if action == 'save':
            base += ['--generation', '3', '--result-digest', 'a'*64, '--expected-revision', '1',
                     '--file', str(self.file)]
        return base+list(extra)

    def invoke(self, command=None, handler=None, *, ca=False):
        def default(request):
            self.seen.append(request)
            return httpx.Response(200, json=copy.deepcopy(self.value))
        stdout, stderr = io.StringIO(), io.StringIO()
        code = operator.run(['--api-url', 'https://api.example', '--token-stdin',
                            *(['--ca-bundle', certifi.where()] if ca else []),
                            *(command or self.command())],
            stdin=io.StringIO('synthetic-sso-bearer\n'), stdout=stdout, stderr=stderr,
            transport=httpx.MockTransport(handler or default))
        self.assertNotIn('synthetic-sso-bearer', stdout.getvalue()+stderr.getvalue())
        return code, stdout.getvalue(), stderr.getvalue()

    def test_get_and_exact_history_use_only_the_existing_scoped_endpoint(self):
        code, out, err = self.invoke(self.command('get', '--revision', '2'))
        self.assertEqual(code, 0); self.assertEqual(err, '')
        self.assertEqual(self.seen[0].method, 'GET')
        self.assertEqual(self.seen[0].url.path, '/v1/environments/env:1/application-drafts/application-a')
        self.assertEqual(dict(self.seen[0].url.params), {'revision': '2'})
        self.assertEqual(self.seen[0].content, b'')
        self.assertEqual(json.loads(out)['revision'], 2)

    def test_save_preserves_explicit_references_and_unresolved_assertions(self):
        code, out, err = self.invoke(self.command('save'))
        self.assertEqual((code, err), (0, ''))
        self.assertEqual(len(self.seen), 1)
        request = self.seen[0]
        self.assertEqual(request.method, 'PUT')
        self.assertEqual(json.loads(request.content), {**self.proposal, 'generation': 3,
            'resultDigest': 'a'*64, 'expectedRevision': 1})
        self.assertNotIn('recordedBy', json.loads(request.content))
        self.assertEqual(request.headers['Authorization'], 'Bearer synthetic-sso-bearer')
        self.assertIs(json.loads(out)['executionAuthorized'], False)

    def test_listing_passes_cursor_once_and_does_not_fetch_all_pages(self):
        summary = {k:v for k,v in self.value.items() if k != 'proposal'}
        summary['applicationGroupId'] = 'app:z'
        self.value = {'format': 'hosting-application-draft-list/1', 'environmentId': 'env:1',
            'latestGeneration': 3, 'consistency': 'LIVE_PAGE', 'items': [summary],
            'nextAfter': 'app:z', 'executionAuthorized': False}
        code, out, err = self.invoke(self.command('list', '--after', 'app:a', '--limit', '1'))
        self.assertEqual((code, err), (0, ''))
        self.assertEqual(dict(self.seen[0].url.params), {'after':'app:a', 'limit':'1'})
        self.assertEqual(json.loads(out)['nextAfter'], 'app:z')
        self.assertEqual(len(self.seen), 1)

    def test_conflict_is_not_automatically_rebased_or_retried(self):
        def handler(request):
            self.seen.append(request)
            return httpx.Response(409, json={'error': {'code':'APPLICATION_DRAFT_CONFLICT',
                                                      'message':'private source detail'}})
        code, out, err = self.invoke(self.command('save'), handler)
        self.assertEqual(code, 2); self.assertEqual(out, '')
        self.assertEqual(json.loads(err), {'status':409, 'error':'APPLICATION_DRAFT_CONFLICT'})
        self.assertEqual(len(self.seen), 1)

    def test_lost_acknowledgement_is_uncertain_with_original_request_digest(self):
        def lost(request):
            self.seen.append(request)
            raise httpx.ReadTimeout('private token or endpoint')
        code, out, err = self.invoke(self.command('save'), lost)
        self.assertEqual(code, 3); self.assertEqual(out, '')
        value = json.loads(err)
        self.assertEqual(value['error'], 'APPLICATION_DRAFT_SAVE_UNKNOWN')
        self.assertTrue(value['reconciliationRequired'])
        self.assertEqual((value['generation'], value['expectedRevision']), (3, 1))
        self.assertEqual(len(value['requestDigest']), 64)
        self.assertEqual(len(self.seen), 1)
        self.assertNotIn('private', err)
        self.assertEqual(self.invoke(self.command('save'), lost)[2], err)
        self.assertEqual(self.seen[0].content, self.seen[1].content)

    def test_server_failure_redirect_or_bad_success_cannot_claim_save_failed_before_commit(self):
        for status, body in ((503, {'error': {'code':'UNAVAILABLE'}}),
                             (307, {}), (404, {'error': {'code':'RESOURCE_NOT_FOUND'}}),
                             (422, {'error': {'code':'APPLICATION_DRAFT_INVALID'}}),
                             (200, {}), (202, self.value)):
            calls = []
            def handler(request):
                calls.append(request)
                return httpx.Response(status, json=body, headers={'location':'https://foreign.invalid'})
            with self.subTest(status=status):
                code, out, err = self.invoke(self.command('save'), handler)
                self.assertEqual(code, 3); self.assertEqual(out, '')
                self.assertEqual(json.loads(err)['error'], 'APPLICATION_DRAFT_SAVE_UNKNOWN')
                self.assertEqual(len(calls), 1)

    def test_interrupted_save_preserves_uncertainty_without_traceback(self):
        def interrupted(request): raise KeyboardInterrupt()
        code, out, err = self.invoke(self.command('save'), interrupted)
        self.assertEqual(code, 130); self.assertEqual(out, '')
        self.assertTrue(json.loads(err)['reconciliationRequired'])

    def test_wrong_environment_revision_or_execution_claim_is_not_printed(self):
        original = copy.deepcopy(self.value)
        for key, val in (('environmentId','foreign'), ('applicationGroupId','other'),
                         ('status','APPROVED'), ('ownershipAccepted',True), ('executionAuthorized',True),
                         ('revision', True), ('latestGeneration',2), ('sourceSuperseded',True)):
            self.value = {**original, key:val}
            with self.subTest(field=key):
                code, out, err = self.invoke()
                self.assertEqual(code, 3); self.assertEqual(out, '')
                self.assertEqual(json.loads(err)['error'], 'APPLICATION_DRAFT_RESPONSE_INVALID')
        self.value = original
        self.assertEqual(self.invoke(self.command('get', '--revision', '1'))[0], 3)

    def test_save_ack_must_bind_generation_digest_and_next_revision(self):
        original = copy.deepcopy(self.value)
        for key, val in (('generation',2), ('resultDigest','b'*64), ('revision',3)):
            self.value = {**original, key:val}
            code, out, err = self.invoke(self.command('save'))
            self.assertEqual(code, 3); self.assertEqual(out, '')
            self.assertEqual(json.loads(err)['error'], 'APPLICATION_DRAFT_SAVE_UNKNOWN')

    def test_save_ack_cannot_substitute_or_drop_proposal_assertions(self):
        original = copy.deepcopy(self.value)
        for kind in ('name', 'dependencies', 'source', 'missing'):
            self.value = copy.deepcopy(original)
            if kind == 'name': self.value['proposal']['draft']['name'] = 'Different'
            elif kind == 'dependencies': self.value['proposal']['dependencies'] = []
            elif kind == 'source': self.value['proposal']['discoveryDigest'] = 'b'*64
            else: del self.value['proposal']
            with self.subTest(kind=kind):
                code, out, err = self.invoke(self.command('save'))
                self.assertEqual(code, 3); self.assertEqual(out, '')
                self.assertEqual(json.loads(err)['error'], 'APPLICATION_DRAFT_SAVE_UNKNOWN')

    def test_save_ack_uses_frozen_request_and_accepts_equivalent_utc_spelling(self):
        for edge in self.proposal['dependencies']:
            edge['observedAt'] = edge['observedAt'].replace('+00:00','Z')
        self.file.write_text(json.dumps(self.proposal))
        def response(request):
            self.seen.append(request)
            self.file.write_text('{}')  # External editor changes the file during the PUT.
            return httpx.Response(200, json=self.value)
        code, out, err = self.invoke(self.command('save'), response)
        self.assertEqual((code, err), (0, ''))
        self.assertEqual(len(self.seen), 1)

    def test_duplicate_or_nonfinite_response_json_cannot_be_reinterpreted(self):
        for raw in (b'{"executionAuthorized":true,"executionAuthorized":false}',
                    b'{"number":NaN}', b'{"number":1e999}', b'[]', b'{'):
            with self.subTest(raw=raw):
                code, out, err = self.invoke(handler=lambda _:httpx.Response(200,content=raw))
                self.assertEqual(code, 3); self.assertEqual(out, '')

    def test_invalid_inputs_never_send_a_request(self):
        commands = [self.command('get', '--revision', '0'), self.command('get', '--revision', str(2**63)),
                    self.command('list', '--limit','101'), self.command('list', '--after','../other')]
        for flag, val in (('--generation','0'), ('--generation',str(2**63)), ('--expected-revision','-1'),
                          ('--expected-revision',str(2**63-1)), ('--result-digest','bad'), ('--id','../other')):
            command = self.command('save'); command[command.index(flag)+1] = val
            commands.append(command)
        for command in commands:
            with self.subTest(command=command):
                code, out, err = self.invoke(command)
                self.assertEqual(code, 3); self.assertEqual(out, '')
                self.assertEqual(json.loads(err)['error'], 'INVALID_INPUT')
        self.assertEqual(self.seen, [])

    def test_duplicate_keys_nonfinite_overflow_and_nesting_fail_before_http(self):
        for raw in (b'{"draft":{},"draft":{},"dependencies":[]}', b'{"x":NaN}', b'{"x":1e999}',
                    b'{"x":9223372036854775808}', b'{"x":'+b'['*70+b'0'+b']'*70+b'}',
                    b'[]', b' '*131073, b'\xff'):
            self.file.write_bytes(raw)
            with self.subTest(raw=raw[:40]):
                self.assertEqual(self.invoke(self.command('save'))[0], 3)
        self.assertEqual(self.seen, [])

    def test_snapshot_envelopes_and_authority_fields_are_not_accepted_as_edit_content(self):
        for key in ('recordedBy','scope','review','ownershipAccepted','executionAuthorized','expectedRevision'):
            self.file.write_text(json.dumps({**self.proposal, key:'caller-claim'}))
            self.assertEqual(self.invoke(self.command('save'))[0], 3)
        value = copy.deepcopy(self.proposal); value['draft']['applicationGroupId'] = 'another'
        self.file.write_text(json.dumps(value))
        self.assertEqual(self.invoke(self.command('save'))[0], 3)
        self.assertEqual(self.seen, [])

    def test_missing_symlink_fifo_and_directory_inputs_are_rejected(self):
        self.file.unlink()
        self.assertEqual(self.invoke(self.command('save'))[0], 3)
        self.file.symlink_to(self.root/'missing')
        self.assertEqual(self.invoke(self.command('save'))[0], 3)
        self.file.unlink()
        if hasattr(os, 'mkfifo'):
            os.mkfifo(self.file)
            self.assertEqual(self.invoke(self.command('save'))[0], 3)
            self.file.unlink()
        self.file.mkdir()
        self.assertEqual(self.invoke(self.command('save'))[0], 3)
        self.assertEqual(self.seen, [])

    def test_inherited_tls_key_logging_is_not_enabled_with_either_ca_selection(self):
        for explicit in (False, True):
            target = self.root/'tls-session-keys'
            with patch.dict(os.environ, {'SSLKEYLOGFILE':str(target)}):
                self.assertEqual(self.invoke(ca=explicit)[0], 0)
                self.assertEqual(os.environ['SSLKEYLOGFILE'], str(target))
            self.assertFalse(target.exists())

    def test_cli_context_keeps_verification_and_does_not_trust_proxy_environment(self):
        original, seen = httpx.Client, []
        def client(**kwargs):
            seen.append(kwargs)
            return original(**kwargs)
        with patch.object(operator.httpx, 'Client', client):
            self.assertEqual(self.invoke()[0], 0)
        context = seen[0]['verify']
        self.assertIs(context.check_hostname, True)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertEqual(context.minimum_version, ssl.TLSVersion.TLSv1_2)
        self.assertTrue(context.verify_flags & ssl.VERIFY_X509_STRICT)
        self.assertTrue(context.verify_flags & ssl.VERIFY_X509_PARTIAL_CHAIN)
        self.assertIsNone(context.keylog_filename)
        self.assertIs(seen[0]['trust_env'], False)
        self.assertIs(seen[0]['follow_redirects'], False)

    def test_client_module_has_no_controller_database_or_native_imports(self):
        import ast
        from provisioner.cli import application_drafts
        tree = ast.parse(Path(application_drafts.__file__).read_text())
        names = [n.module or '' for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        names += [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
        self.assertFalse(any('controlplane' in n or n.startswith(('psycopg','tools','scripts')) for n in names))


if __name__ == '__main__': unittest.main()
