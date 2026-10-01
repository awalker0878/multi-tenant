"""Real owner signatures and private-file failures, without database/native access."""
from __future__ import annotations

import copy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import stat
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from provisioner.controlplane.discovery import owner_signing as signing
from provisioner.controlplane.discovery.application_drafts import parse_draft_export, _digest
from provisioner.controlplane.discovery.application_review import APPLICATION_OWNER, require_draft_binding
from provisioner.controlplane.discovery.assessment_inputs import AssessmentInputDenied, parse_evidence
from provisioner.controlplane.discovery.model import _json
from tests.provisioning.discovery.test_application_review import OwnerFixture, stored_fixture, NOW
from tests.provisioning.discovery.test_assessment_inputs import encoded


def private_file(path, data):
    path = Path(path)
    path.write_bytes(data if isinstance(data, bytes) else _json(data).encode('ascii'))
    path.chmod(0o600)
    return path


def fixture_files(root, stored, fixture):
    """Synthetic file custody shared with the actual PostgreSQL integration case."""
    private_file(root/'draft.json', stored.document(latest_generation=stored.generation))
    private_file(root/'owner.key', fixture.keys[APPLICATION_OWNER].private_bytes_raw())
    config = {'format': 'hosting-application-review-signer/1',
        'trust': {'policyFile': str(fixture.path), 'rootKey': encoded(fixture.root.public_key().public_bytes_raw()),
                  'minimumRevision': 1},
        'signer': {'keyId': 'APPLICATION_OWNER-key', 'keyFile': str(root/'owner.key')}}
    private_file(root/'config.json', config)
    return config


def prepare_args(root, stored, *, decision='ACCEPT_FOR_ASSESSMENT', revision=1):
    return ['prepare', '--draft-file', str(root/'draft.json'), '--record-digest', stored.record_digest,
        '--output', str(root/'decision.json'), '--evidence-id', f'owner-review-{revision}',
        '--evidence-revision', str(revision), '--decision', decision,
        '--review-reference', 'ticket-1', '--ttl-seconds', '1800']


def sign_args(root, stored):
    digest = hashlib.sha256((root/'decision.json').read_bytes()).hexdigest()
    return ['sign', '--draft-file', str(root/'draft.json'), '--record-digest', stored.record_digest,
        '--decision-file', str(root/'decision.json'), '--confirm-evidence-digest', digest,
        '--config', str(root/'config.json'), '--output', str(root/'signed.json')]


def invoke(argv, *, clock=lambda: NOW):
    out, err = io.StringIO(), io.StringIO()
    code = signing.main(argv, clock=clock, stdout=out, stderr=err)
    return code, json.loads(out.getvalue() or err.getvalue())


class OwnerSigningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stored, self.result = stored_fixture()
        self.fixture = OwnerFixture(self.root/'policy.json', self.stored)
        self.config = fixture_files(self.root, self.stored, self.fixture)

    def prepare(self, **kwargs):
        code, result = invoke(prepare_args(self.root, self.stored, **kwargs))
        self.assertEqual(code, 0, result)
        return result

    def sign(self, *, clock=lambda: NOW):
        return invoke(sign_args(self.root, self.stored), clock=clock)

    def held(self, argv=None, *, clock=lambda: NOW):
        code, result = invoke(argv or sign_args(self.root, self.stored), clock=clock)
        self.assertEqual(code, 2, result)
        self.assertEqual(result, {'error': 'OWNER_REVIEW_HELD', 'outputMayExist': True})
        self.assertFalse((self.root/'signed.json').exists())
        self.assertEqual(list(self.root.glob('.review-*')), [])

    def test_preparation_uses_the_existing_unsigned_evidence_without_signing(self):
        with patch.object(Ed25519PrivateKey, 'from_private_bytes', side_effect=AssertionError('no key read')):
            result = self.prepare()
        evidence = parse_evidence(json.loads((self.root/'decision.json').read_bytes()))
        require_draft_binding(evidence.value, self.stored)
        self.assertEqual(result['evidenceDigest'], evidence.digest)
        self.assertEqual(result['status'], 'PREPARED_UNSIGNED')
        self.assertNotIn('signatures', json.loads((self.root/'decision.json').read_bytes()))
        self.assertEqual(stat.S_IMODE((self.root/'decision.json').stat().st_mode), 0o600)

    def test_signed_artifact_verifies_with_the_actual_ingest_trust_owner(self):
        prepared = self.prepare(); original = (self.root/'decision.json').read_bytes()
        with patch.object(socket, 'socket', side_effect=AssertionError('offline command')):
            code, result = self.sign()
        self.assertEqual(code, 0, result)
        submission = json.loads((self.root/'signed.json').read_bytes())
        self.assertEqual(set(submission), {'evidence', 'signatures'})
        self.assertEqual(_json(submission['evidence']).encode('ascii'), original)
        evidence = parse_evidence(submission['evidence'])
        policy, subjects = self.fixture.trust.verify(evidence, tuple(submission['signatures']), NOW)
        self.assertEqual(subjects, ('owner-a',))
        self.assertEqual(result['evidenceDigest'], prepared['evidenceDigest'])
        self.assertEqual(result['status'], 'SIGNED_NOT_INGESTED')
        for key in ('ingested', 'dependencyEvidenceVerified', 'ownershipAccepted', 'executionAuthorized'):
            self.assertIs(result[key], False)
        self.assertEqual(result['outputDigest'], hashlib.sha256((self.root/'signed.json').read_bytes()).hexdigest())
        self.assertEqual((self.root/'signed.json').stat().st_nlink, 1)

    def test_confirmation_is_of_exact_prepared_content_not_just_a_draft_id(self):
        self.prepare(); args = sign_args(self.root, self.stored)
        args[args.index('--confirm-evidence-digest')+1] = 'a'*64
        self.held(args)

    def test_decision_cannot_be_changed_or_refreshed_while_signing(self):
        self.prepare(); args = sign_args(self.root, self.stored)
        doc = json.loads((self.root/'decision.json').read_bytes())
        for key, value in (('reviewReference', 'another-ticket'), ('decision', 'REVOKE')):
            changed = copy.deepcopy(doc); changed['payload'][key] = value
            private_file(self.root/'decision.json', changed)
            self.held(args)
        private_file(self.root/'decision.json', doc)
        self.held(clock=lambda: NOW+timedelta(minutes=30))
        self.assertEqual(json.loads((self.root/'decision.json').read_bytes()), doc)

    def test_export_digests_are_checked_without_fabricating_native_observations(self):
        original = self.stored.document(latest_generation=1)
        for key, value in (('proposalDigest', 'a'*64), ('recordDigest', 'b'*64),
                           ('recordedBy', 'different-editor'), ('generation', 2),
                           ('executionAuthorized', True), ('sourceSuperseded', True),
                           ('revision', True), ('latestGeneration', 0), ('status', 'APPROVED')):
            changed = copy.deepcopy(original); changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                parse_draft_export(changed, expected_record_digest=self.stored.record_digest)
        changed = copy.deepcopy(original); changed['proposal']['draft']['name'] = 'changed'
        with self.assertRaises(ValueError):
            parse_draft_export(changed, expected_record_digest=self.stored.record_digest)

    def test_recorded_oidc_subject_is_not_forced_into_logical_id_grammar(self):
        stored, _ = stored_fixture(recorded_by='oidc|author@example.org')
        self.assertEqual(parse_draft_export(stored.document(latest_generation=1),
            expected_record_digest=stored.record_digest), stored)

    def test_unknown_export_fields_and_wrong_scope_are_rejected(self):
        for location in (None, 'scope', 'proposal'):
            doc = copy.deepcopy(self.stored.document(latest_generation=1))
            (doc if location is None else doc[location])['extra'] = True
            with self.subTest(location=location), self.assertRaises(ValueError):
                parse_draft_export(doc, expected_record_digest=self.stored.record_digest)
        doc = copy.deepcopy(self.stored.document(latest_generation=1)); doc['scope']['tenant_id'] = 'foreign'
        with self.assertRaises(ValueError): parse_draft_export(doc, expected_record_digest=self.stored.record_digest)

    def test_precision_order_and_unknown_assertions_are_not_rewritten(self):
        from tests.provisioning.discovery import test_grouping as grouping
        stored, _ = stored_fixture(edges=(replace(grouping.UNKNOWN,
            observed_at=self.result.captured_at.replace(microsecond=123456)),))
        stored = replace(stored, recorded_at=stored.recorded_at.replace(microsecond=654321))
        stored = replace(stored, record_digest=_digest(stored.binding()))
        doc = stored.document(latest_generation=1)
        self.assertEqual(parse_draft_export(doc, expected_record_digest=stored.record_digest), stored)
        self.assertEqual(json.loads(stored.proposal_json)['dependencies'][0]['state'], 'UNKNOWN')

    def test_editor_cannot_review_own_proposal_even_with_an_owner_key(self):
        stored, _ = stored_fixture(recorded_by='owner-a')
        private_file(self.root/'draft.json', stored.document(latest_generation=1))
        self.held(prepare_args(self.root, stored))
        self.assertFalse((self.root/'decision.json').exists())

    def test_preparation_time_and_revision_bounds_are_not_coerced(self):
        from provisioner.controlplane.discovery.owner_signing import prepare_review
        kwargs = dict(evidence_id='evidence-a', evidence_revision=1, decision='ACCEPT_FOR_ASSESSMENT',
                      review_reference='ticket-1', ttl_seconds=1800, checked_at=NOW)
        for key, value in (('evidence_revision', True), ('evidence_revision', 0),
                           ('ttl_seconds', 0), ('ttl_seconds', 3601), ('ttl_seconds', True),
                           ('decision', 'APPROVE_EXECUTION'), ('evidence_id', ''),
                           ('checked_at', NOW.replace(tzinfo=None)),
                           ('checked_at', self.stored.recorded_at-timedelta(seconds=1))):
            with self.subTest(key=key), self.assertRaises((ValueError, AssessmentInputDenied)):
                prepare_review(self.stored, **{**kwargs, key: value})

    def test_superseded_export_can_be_revoked_but_not_accepted(self):
        private_file(self.root/'draft.json', self.stored.document(latest_generation=2))
        self.held(prepare_args(self.root, self.stored))
        self.prepare(decision='REVOKE', revision=2)
        self.assertEqual(self.sign()[0], 0)
        self.assertEqual(json.loads((self.root/'signed.json').read_bytes())['evidence']['payload']['decision'], 'REVOKE')

    def test_unenrolled_wrong_owner_scope_and_revoked_keys_cannot_sign(self):
        self.prepare(); original = copy.deepcopy(self.fixture.policy)
        for field, value in (('subjectId', 'other-owner'), ('role', 'SOURCE_EXIT'),
                             ('environments', []), ('revokedAt', NOW.isoformat()),
                             ('publicKey', encoded(self.fixture.root.public_key().public_bytes_raw()))):
            self.fixture.policy = copy.deepcopy(original)
            self.fixture.policy['enrollments'][-1][field] = value; self.fixture.write()
            with self.subTest(field=field): self.held()

    def test_wrong_private_key_and_wrong_root_do_not_publish(self):
        self.prepare()
        private_file(self.root/'owner.key', Ed25519PrivateKey.generate().private_bytes_raw())
        self.held()
        private_file(self.root/'owner.key', self.fixture.keys[APPLICATION_OWNER].private_bytes_raw())
        self.config['trust']['rootKey'] = encoded(Ed25519PrivateKey.generate().public_key().public_bytes_raw())
        private_file(self.root/'config.json', self.config); self.held()

    def test_expired_policy_and_evidence_revocation_hold(self):
        self.prepare(); original = copy.deepcopy(self.fixture.policy)
        self.fixture.policy['revokedEvidenceIds'] = ['owner-review-1']; self.fixture.write(); self.held()
        self.fixture.policy = original; self.fixture.policy['expiresAt'] = NOW.isoformat()
        self.fixture.write(); self.held()

    def test_revision_floor_and_noncanonical_decision_are_not_fallbacks(self):
        self.prepare()
        self.config['trust']['minimumRevision'] = 2; private_file(self.root/'config.json', self.config); self.held()
        self.config['trust']['minimumRevision'] = 1; private_file(self.root/'config.json', self.config)
        with (self.root/'decision.json').open('ab') as f: f.write(b'\n')
        self.held()

    def test_clock_regression_during_signing_holds_without_output(self):
        self.prepare(); times = iter((NOW, NOW-timedelta(seconds=1)))
        self.held(clock=lambda: next(times))

    def test_final_authority_recheck_discards_a_mid_operation_revocation(self):
        self.prepare()
        original = signing._publish
        def publish(path, raw, recheck):
            self.fixture.policy['revision'] += 1
            self.fixture.policy['revokedEvidenceIds'] = ['owner-review-1']; self.fixture.write()
            return original(path, raw, recheck)
        with patch.object(signing, '_publish', publish): self.held()

    def test_inputs_rotated_before_publication_are_not_spliced(self):
        self.prepare(); original = signing._publish
        for file in ('draft.json', 'decision.json', 'config.json', 'owner.key'):
            target = self.root/file; before = target.read_bytes()
            def publish(path, raw, recheck):
                private_file(target, before+b' ')
                return original(path, raw, recheck)
            with self.subTest(file=file), patch.object(signing, '_publish', publish): self.held()
            private_file(target, before)

    def test_publishing_never_overwrites_existing_files_or_follows_symlinks(self):
        self.prepare(); target = self.root/'signed.json'
        private_file(target, b'original'); code, _ = self.sign()
        self.assertEqual(code, 2); self.assertEqual(target.read_bytes(), b'original')
        target.unlink(); target.symlink_to(self.root/'owner.key')
        before = (self.root/'owner.key').read_bytes(); code, _ = self.sign()
        self.assertEqual(code, 2); self.assertEqual((self.root/'owner.key').read_bytes(), before)

    def test_private_file_types_bounds_links_and_permissions_fail_closed(self):
        self.prepare(); target = self.root/'owner.key'; original = target.read_bytes()
        for raw in (b'', b'x'*31, b'x'*33):
            private_file(target, raw); self.held()
        private_file(target, original); target.chmod(0o644); self.held(); target.chmod(0o600)
        target.unlink(); target.mkdir(); self.held(); target.rmdir()
        os.mkfifo(target, 0o600); self.held(); target.unlink()
        private_file(self.root/'elsewhere', original); target.symlink_to(self.root/'elsewhere')
        self.held(); target.unlink()
        os.link(self.root/'elsewhere', target); self.held()

    def test_symlink_ancestors_and_nonprivate_parents_are_rejected(self):
        self.prepare()
        child = self.root/'custody'; child.mkdir(mode=0o700)
        key = private_file(child/'key', self.fixture.keys[APPLICATION_OWNER].private_bytes_raw())
        alias = self.root/'alias'; alias.symlink_to(child, target_is_directory=True)
        self.config['signer']['keyFile'] = str(alias/'key'); private_file(self.root/'config.json', self.config)
        self.held()
        self.config['signer']['keyFile'] = str(key); private_file(self.root/'config.json', self.config)
        child.chmod(0o755); self.held()

    def test_json_duplicate_nonfinite_deep_and_large_inputs_do_not_publish(self):
        target = self.root/'draft.json'
        for raw in (b'{"format":1,"format":2}', b'{"v":NaN}', b'{"n":'+b'9'*30+b'}',
                    b'{"v":'+b'['*70+b'0'+b']'*70+b'}', b'x'*(signing.MAX_EXPORT_BYTES+1)):
            private_file(target, raw); self.held(prepare_args(self.root, self.stored))

    def test_post_link_failure_preserves_output_and_reports_uncertainty(self):
        self.prepare(); fsync = os.fsync
        def fail_directory(fd):
            if stat.S_ISDIR(os.fstat(fd).st_mode): raise OSError('directory sync failed')
            return fsync(fd)
        with patch.object(os, 'fsync', fail_directory): code, result = self.sign()
        self.assertEqual(code, 2); self.assertTrue(result['outputMayExist'])
        output = self.root/'signed.json'; before = output.read_bytes()
        submission = json.loads(before)
        self.fixture.trust.verify(parse_evidence(submission['evidence']), tuple(submission['signatures']), NOW)
        self.assertEqual(self.sign()[0], 2); self.assertEqual(output.read_bytes(), before)
        self.assertEqual(list(self.root.glob('.review-*')), [])

    def test_wrong_kind_and_unknown_config_cannot_turn_signer_into_general_oracle(self):
        self.prepare()
        self.config['signer']['role'] = 'INSTALLATION'; private_file(self.root/'config.json', self.config)
        self.held()
        private_file(self.root/'decision.json', self.fixture.document('INSTALLATION'))
        self.held()

    def test_signer_preflight_never_accepts_other_evidence_kinds(self):
        evidence = parse_evidence(self.fixture.document('INSTALLATION'))
        with self.assertRaises(AssessmentInputDenied):
            self.fixture.trust.authorize_application_signer(evidence, 'INSTALLATION-key',
                self.fixture.keys['INSTALLATION'].public_key().public_bytes_raw(), NOW)

    def test_missing_cli_confirmation_and_interruption_use_redacted_errors(self):
        self.assertEqual(invoke(['sign', '--secret-value', 'do-not-echo'])[1]['error'], 'OWNER_REVIEW_HELD')
        out, err = io.StringIO(), io.StringIO()
        with patch.object(signing, 'run', side_effect=KeyboardInterrupt):
            code = signing.main(prepare_args(self.root, self.stored), stdout=out, stderr=err)
        self.assertEqual(code, 130); self.assertEqual(out.getvalue(), '')
        self.assertNotIn(str(self.root), err.getvalue())


if __name__ == '__main__':
    unittest.main()
