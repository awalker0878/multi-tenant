"""Actual signatures and file custody; transaction doubles do not qualify PostgreSQL."""
import copy
from datetime import timedelta
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from provisioner.controlplane.discovery import review_intake as intake, review_files, owner_signing
from provisioner.controlplane.discovery.assessment_inputs import AssessmentInputDenied
from provisioner.controlplane.discovery.model import _json, _scope_json
from tests.provisioning.discovery.test_application_review import stored_fixture, review_document, OwnerFixture, NOW
from tests.provisioning.discovery.test_assessment_inputs import encoded
from tests.provisioning.discovery.test_owner_signing import private_file

ROLE = 'hosting_assessment_ingest'


def files(root, stored, fixture, *, at=NOW):
    document = review_document(stored, at=at)
    submission = {'evidence': document, 'signatures': list(fixture.sign(document))}
    private_file(root/'signed.json', submission)
    private_file(root/'password', b'synthetic-password')
    private_file(root/'ca.pem', b'Synthetic transport test material')
    private_file(root/'crl.pem', b'Synthetic transport test material')
    config = {'format': 'hosting-application-review-ingest/1',
        'environmentId': stored.environment_id, 'scope': _scope_json(stored.scope),
        'database': {'host': 'database.example', 'hostaddr': '127.0.0.1', 'port': 5432,
            'name': 'test_database', 'role': ROLE, 'passwordFile': str(root/'password'),
            'caFile': str(root/'ca.pem'), 'crlFile': str(root/'crl.pem')},
        'trust': {'policyFile': str(fixture.path), 'rootKey': encoded(fixture.root.public_key().public_bytes_raw()),
                  'minimumRevision': 1}}
    private_file(root/'intake.json', config)
    return config, submission


def args(root, *, receipt='receipt.json'):
    raw = (root/'signed.json').read_bytes()
    return ['--config', str(root/'intake.json'), '--submission-file', str(root/'signed.json'),
            '--submission-digest', hashlib.sha256(raw).hexdigest(), '--receipt', str(root/receipt)]


class Database:
    """Only role guard responses and commit/rollback boundaries, not a SQL implementation."""
    autocommit = False
    def __init__(self):
        self.answers = [(ROLE, ROLE, False, False, False, False, False), (False,), (False,),
                        (False, False), (False,), (False,), (True,), (True,), (True,)]
        self.calls, self.commits, self.rollbacks, self.fail_commit = [], 0, 0, False
    def __enter__(self):
        return self
    def __exit__(self, typ, value, traceback):
        if typ is not None:
            self.rollbacks += 1
        elif self.fail_commit:
            raise OSError('private database credential must never appear')
        else:
            self.commits += 1
    def execute(self, statement, parameters=None):
        if parameters is not None and '%' in statement.replace('%s', ''):
            raise ValueError('Unescaped literal percent in a parameterized query')
        index = len(self.calls); self.calls.append((statement, parameters))
        return SimpleNamespace(fetchone=lambda: self.answers[index])


class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stored, _ = stored_fixture()
        self.fixture = OwnerFixture(self.root/'policy.json', self.stored)
        self.config, self.submission = files(self.root, self.stored, self.fixture)
        self.db, self.parameters, self.operations = Database(), [], []
        case = self
        class Repository:
            def __init__(self, connect, trust, *, ingest_role):
                self.connect, self.trust = connect, trust
                case.assertEqual(ingest_role, ROLE)
            def ingest(self, ctx, document, signatures):
                evidence = intake.parse_evidence(document)
                with self.connect():
                    self.trust.verify(evidence, signatures, NOW)
                    case.operations.append((ctx, document, signatures))
                    case.during_transaction()
                return evidence.digest
        self.during_transaction = lambda: None
        self.addCleanup(patch.stopall)
        patch.object(intake, 'AssessmentInputRepository', Repository).start()
        def connect(parameters):
            self.parameters.append(parameters)
            return self.db
        patch.object(intake, '_connect_database', connect).start()

    def invoke(self, argv=None, *, clock=lambda: NOW):
        out, err = io.StringIO(), io.StringIO()
        code = intake.main(argv or args(self.root), clock=clock, stdout=out, stderr=err)
        self.assertNotIn('synthetic-password', out.getvalue()+err.getvalue())
        self.assertNotIn(str(self.root), out.getvalue()+err.getvalue())
        return code, json.loads(out.getvalue() or err.getvalue())

    def held(self, argv=None, **kwargs):
        code, result = self.invoke(argv, **kwargs)
        self.assertEqual(code, 2, result)
        self.assertEqual(result, {'error':'REVIEW_INTAKE_HELD', 'ingestAttempted':False,
                                 'recorded':False, 'outputMayExist':True})
        self.assertFalse((self.root/'receipt.json').exists())
        self.assertFalse(self.operations)

    def test_exact_owner_artifact_commits_once_then_emits_a_non_authoritative_receipt(self):
        code, receipt = self.invoke()
        self.assertEqual(code, 0, receipt)
        self.assertEqual(receipt['status'], 'RECORDED_ASSESSMENT_ONLY')
        self.assertEqual(receipt['draftRecordDigest'], self.stored.record_digest)
        self.assertEqual(receipt['submissionDigest'], hashlib.sha256((self.root/'signed.json').read_bytes()).hexdigest())
        self.assertEqual(json.loads((self.root/'receipt.json').read_bytes()), receipt)
        self.assertEqual(self.db.commits, 1); self.assertEqual(len(self.parameters), 1)
        self.assertEqual(self.operations[0][1], self.submission['evidence'])
        self.assertEqual(self.operations[0][2], tuple(self.submission['signatures']))
        self.assertEqual((self.root/'receipt.json').stat().st_mode & 0o777, 0o600)
        for flag in ('executionAuthorized','ownershipAccepted','dependencyEvidenceVerified'):
            self.assertIs(receipt[flag], False)
        self.assertEqual(list(self.root.glob('.review-*')), [])

    def test_changed_confirmed_bytes_are_rejected_before_connection(self):
        argv = args(self.root)
        self.submission['evidence']['payload']['reviewReference'] = 'changed'
        private_file(self.root/'signed.json', self.submission)
        self.held(argv); self.assertFalse(self.parameters)

    def test_bad_signature_is_rejected_before_database_password_read(self):
        self.submission['signatures'][0]['signature'] = encoded(bytes(64))
        private_file(self.root/'signed.json', self.submission)
        original = review_files.read_private
        def read(path, limit):
            self.assertNotEqual(path, str(self.root/'password'))
            return original(path, limit)
        with patch.object(review_files, 'read_private', read): self.held()
        self.assertFalse(self.parameters)

    def test_other_evidence_kinds_unknown_fields_duplicates_and_noncanonical_bytes_hold(self):
        for raw in (b'{"evidence":1,"evidence":2}', b'{"v":NaN}',
                    _json({**self.submission,'extra':True}).encode(),
                    _json(self.submission).encode()+b'\n', b'x'*(intake.MAX_SUBMISSION_BYTES+1)):
            private_file(self.root/'signed.json', raw); self.held()
        doc=self.fixture.document('INSTALLATION')
        private_file(self.root/'signed.json', {'evidence':doc,'signatures':self.fixture.sign(doc)})
        self.held(); self.assertFalse(self.parameters)

    def test_wrong_environment_scope_or_revision_floor_holds_without_network(self):
        for field, value in (('environmentId','another'),('minimumRevision',2),('scope','another')):
            changed=copy.deepcopy(self.config)
            if field=='minimumRevision': changed['trust'][field]=value
            elif field=='scope': changed['scope']['tenantId']=value
            else: changed[field]=value
            private_file(self.root/'intake.json', changed); self.held()
        self.assertFalse(self.parameters)

    def test_expired_or_revoked_evidence_never_opens_database(self):
        self.held(clock=lambda:NOW+timedelta(minutes=30))
        self.fixture.policy['revokedEvidenceIds']=[self.submission['evidence']['evidenceId']]
        self.fixture.write(); self.held(); self.assertFalse(self.parameters)

    def test_unknown_database_option_cannot_weaken_transport(self):
        self.config['database']['sslmode']='disable'
        private_file(self.root/'intake.json', self.config); self.held(); self.assertFalse(self.parameters)

    def test_actual_role_guard_rejects_every_bad_response_before_ingest(self):
        original=copy.deepcopy(self.db.answers)
        for index in range(len(original)):
            self.db.answers=copy.deepcopy(original); self.db.answers[index]=None; self.db.calls=[]
            with self.subTest(index=index): self.held()
        self.assertEqual(self.db.commits,0)

    def test_ambient_role_set_or_autocommit_is_not_an_intake_login(self):
        self.db.autocommit=True; self.held(); self.assertEqual(self.db.calls,[])
        self.db.autocommit=False; self.db.answers[0]=(ROLE,'another',False,False,False,False,False)
        self.held()

    def test_existing_output_or_symlink_is_rejected_before_connection(self):
        target=self.root/'receipt.json'; target.symlink_to(self.root/'password')
        code,result=self.invoke(); self.assertEqual(code,2); self.assertFalse(self.parameters)
        self.assertEqual((self.root/'password').read_bytes(), b'synthetic-password')
        target.unlink();private_file(target,b'old receipt')
        self.assertEqual(self.invoke()[0],2);self.assertEqual(target.read_bytes(),b'old receipt')

    def test_config_or_submission_changes_during_transaction_roll_back(self):
        for filename in ('intake.json','signed.json','password','ca.pem','crl.pem'):
            target=self.root/filename; original=target.read_bytes(); self.db.calls=[]
            self.during_transaction=lambda:private_file(target,original+b' ')
            with self.subTest(filename=filename):
                code,out=self.invoke();self.assertEqual(code,3,out);self.assertFalse(out['recorded'])
                self.assertFalse((self.root/'receipt.json').exists())
            private_file(target,original)
        self.assertEqual(self.db.commits,0);self.assertEqual(self.db.rollbacks,5)

    def test_live_policy_revocation_before_commit_rolls_back(self):
        def revoke():
            self.fixture.policy['revision']+=1
            self.fixture.policy['revokedEvidenceIds']=[self.submission['evidence']['evidenceId']]
            self.fixture.write()
        self.during_transaction=revoke
        code,out=self.invoke();self.assertEqual(code,3,out);self.assertFalse(out['recorded'])
        self.assertEqual(self.db.rollbacks,1);self.assertEqual(self.db.commits,0)

    def test_commit_disconnect_is_unknown_not_retry_or_success(self):
        self.db.fail_commit=True
        code,out=self.invoke();self.assertEqual(code,3,out)
        self.assertTrue(out['ingestAttempted']);self.assertFalse(out['recorded'])
        self.assertEqual(len(self.parameters),1);self.assertFalse((self.root/'receipt.json').exists())

    def test_receipt_failure_after_commit_preserves_confirmed_recorded_state(self):
        with patch.object(review_files,'publish_once',side_effect=OSError('private')):
            code,out=self.invoke()
        self.assertEqual(code,3,out);self.assertTrue(out['recorded']);self.assertEqual(self.db.commits,1)
        self.assertEqual(len(self.operations),1)

    def test_expiry_after_commit_does_not_relabel_database_success_as_rollback(self):
        # Local receipt is a committed-ingest acknowledgement, not a current owner review.
        calls=0
        def clock():
            nonlocal calls
            calls+=1
            return NOW+timedelta(hours=1) if self.db.commits else NOW
        code,out=self.invoke(clock=clock)
        self.assertEqual(code,0,out);self.assertEqual(out['acknowledgedAt'],(NOW+timedelta(hours=1)).isoformat())

    def test_private_signer_functions_are_moved_not_forwarded_or_copied(self):
        self.assertFalse(hasattr(owner_signing,'_read')); self.assertFalse(hasattr(owner_signing,'_publish'))
        self.assertIs(owner_signing.review_files, intake.review_files)

    def test_interruption_in_transaction_reports_possible_commit_without_receipt(self):
        self.during_transaction=lambda: (_ for _ in ()).throw(KeyboardInterrupt())
        code,out=self.invoke();self.assertEqual(code,130);self.assertTrue(out['ingestAttempted'])
        self.assertFalse(out['recorded']);self.assertFalse((self.root/'receipt.json').exists())

    def test_invalid_cli_never_echoes_a_misplaced_credential(self):
        self.held(['--password','private-secret-value']);self.assertFalse(self.parameters)

    def test_unsafe_password_files_and_nonprivate_configuration_hold(self):
        private_file(self.root/'password', b'secret\n'); self.held()
        private_file(self.root/'password', b'synthetic-password')
        (self.root/'intake.json').chmod(0o644);self.held()

    def test_clock_regression_before_commit_rolls_back(self):
        changed=False
        def change():
            nonlocal changed
            changed=True
        self.during_transaction=change
        code,out=self.invoke(clock=lambda:NOW-timedelta(microseconds=1) if changed else NOW)
        self.assertEqual(code,3,out);self.assertEqual(self.db.commits,0)


class DatabaseTransportTests(unittest.TestCase):
    def setUp(self):
        self.database={'host':'db.example','hostaddr':'127.0.0.1','port':5432,'name':'test_db',
            'role':ROLE,'passwordFile':'/custody/password','caFile':'/custody/ca','crlFile':'/custody/crl'}

    def test_endpoint_and_database_fields_are_strict_and_never_dsn_fragments(self):
        for field,value in (('host','db,evil'),('host','/tmp'),('host','db\n'),('hostaddr','0.0.0.0'),
                            ('hostaddr','ff02::1'),('port',True),('port',0),('port',65536),
                            ('role','a;SET ROLE postgres'),('name','postgresql://evil/db')):
            with self.subTest(field=field),self.assertRaises((ValueError,TypeError)):
                intake.connection_parameters({**self.database,field:value}, b'synthetic')

    def test_production_connector_passes_fixed_tls_authentication_and_no_implicit_credential(self):
        parameters=intake.connection_parameters(self.database,b'synthetic')
        from unittest.mock import Mock
        driver=SimpleNamespace(pq=SimpleNamespace(version=lambda:170000),connect=Mock(return_value='connection'))
        with patch.dict('sys.modules',psycopg=driver),patch.dict(os.environ,{},clear=True):
            self.assertEqual(intake._connect_database(parameters),'connection')
        options=driver.connect.call_args.kwargs
        for key,value in {'sslmode':'verify-full','channel_binding':'require','require_auth':'scram-sha-256',
                          'sslcertmode':'disable','gssencmode':'disable','connect_timeout':5,
                          'passfile':'/dev/null','autocommit':False}.items():self.assertEqual(options[key],value)
        self.assertEqual(options['hostaddr'],'127.0.0.1')

    def test_old_libpq_or_ambient_overrides_are_refused_without_connection(self):
        from unittest.mock import Mock
        driver=SimpleNamespace(pq=SimpleNamespace(version=lambda:160000),connect=Mock())
        parameters=intake.connection_parameters(self.database,b'synthetic')
        with patch.dict('sys.modules',psycopg=driver),patch.dict(os.environ,{},clear=True):
            with self.assertRaises(ValueError):intake._connect_database(parameters)
        driver.pq.version=lambda:170000
        for name in ('PGSERVICE','PGPASSWORD','PGHOST','PGOPTIONS','SSLKEYLOGFILE'):
            with patch.dict('sys.modules',psycopg=driver),patch.dict(os.environ,{name:'private'},clear=True):
                with self.assertRaises(ValueError):intake._connect_database(parameters)
        driver.connect.assert_not_called()


if __name__=='__main__':unittest.main()
