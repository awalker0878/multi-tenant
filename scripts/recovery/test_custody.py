import base64
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import custody


class CustodyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.keys_directory = tempfile.TemporaryDirectory(prefix='synthetic-custody-keys-')
        root = Path(cls.keys_directory.name)
        cls.phrase = b'synthetic-disposable-recovery-fixture-passphrase'
        phrase = root / 'passphrase'
        phrase.write_bytes(cls.phrase); phrase.chmod(0o600)
        cls.keys, cls.public = [], []
        for number in range(2):
            key = root / f'key-{number}.pem'
            custody.openssl(['genpkey', '-algorithm', 'RSA', '-pkeyopt', 'rsa_keygen_bits:3072', '-aes-256-cbc', '-pass', 'file:' + str(phrase), '-out', str(key)])
            key.chmod(0o600)
            cls.keys.append(key)
            cls.public.append(custody.openssl(['pkey', '-in', str(key), '-passin', 'file:' + str(phrase), '-pubout']).decode())

    @classmethod
    def tearDownClass(cls):
        cls.keys_directory.cleanup()

    def setUp(self):
        self.private = tempfile.TemporaryDirectory(prefix='synthetic-custody-')
        self.addCleanup(self.private.cleanup)
        self.root = Path(self.private.name)
        self.store = self.root / 'independent'
        self.policy = {'version': 1, 'installation_id': '550e8400-e29b-41d4-a716-446655440099',
                       'valid_from': int(time.time()) - 10, 'valid_until': int(time.time()) + 3600,
                       'principals': [{'id': '550e8400-e29b-41d4-a716-44665544000' + str(n), 'role': role, 'public_key_pem': self.public[n]}
                                      for n, role in enumerate(['recovery_owner', 'security_reviewer'])]}
        self.trust = self.put('trust.json', self.policy)
        self.initial = {'version': 1, 'installation_id': self.policy['installation_id'], 'epoch': 'a' * 64, 'state': 'active', 'bootstrap_allowed': False}
        self.original = self.put('initial.json', self.initial)
        custody.enroll(self.store, self.original, self.trust)
        custody.hold(self.store, 'REC-SYNTHETIC-100')

    def put(self, name, value):
        path = self.root / name
        custody.write_new(path, custody.canonical(value))
        return path

    def plan(self, purpose='resume'):
        descriptor = custody.admission(self.store)
        return {'version': 1, 'purpose': purpose, 'recovery_id': '550e8400-e29b-41d4-a716-446655440020',
                'installation_id': self.policy['installation_id'], 'trust_sha256': custody.digest(self.policy),
                'created_at': int(time.time()), 'expires_at': int(time.time()) + 900,
                'descriptor_sha256': custody.digest(descriptor), 'post_snapshot_sha256': hashlib.sha256(b'synthetic-post-reconciliation').hexdigest(),
                'binding_sha256': hashlib.sha256((descriptor['installation_id'] + ':' + descriptor['epoch']).encode()).hexdigest()}

    def envelope(self, plan=None, prefix='one'):
        plan = plan or self.plan()
        payload = self.put(prefix + '-plan.json', plan)
        signatures = []
        for n, principal in enumerate(self.policy['principals']):
            signature = self.root / f'{prefix}-signature-{n}.json'
            custody.sign(self.trust, payload, principal['id'], self.keys[n], signature, passphrase=self.phrase)
            signatures.append(signature)
        envelope = self.root / (prefix + '-envelope.json')
        custody.assemble(self.trust, payload, signatures, envelope)
        packet = custody.decode(custody.read(envelope, private=True))
        confirmation = self.put(prefix + '-confirmation.json', {'recovery_id': plan['recovery_id'], 'envelope_sha256': custody.digest(packet),
                                'post_snapshot_sha256': plan['post_snapshot_sha256'], 'admission': 'HELD_CONFIRMED'})
        return envelope, confirmation

    def test_two_encrypted_keys_can_release_only_the_current_confirmed_held_generation(self):
        envelope, confirmation = self.envelope()
        custody.resume(self.store, envelope, confirmation)
        entries, current = custody.checked(self.store)
        self.assertEqual(current['state'], 'active')
        self.assertFalse(current['bootstrap_allowed'])
        self.assertEqual([e['kind'] for e in entries], ['enrolled', 'held', 'resume_authorized'])
        with self.assertRaises(custody.Held):
            custody.resume(self.store, envelope, confirmation)

    def test_rotated_epoch_rejects_previously_signed_release(self):
        envelope, confirmation = self.envelope()
        old = custody.admission(self.store)
        custody.hold(self.store, 'REC-SYNTHETIC-101')
        with self.assertRaises(custody.Held):
            custody.resume(self.store, envelope, confirmation)
        self.assertNotEqual(custody.admission(self.store)['epoch'], old['epoch'])
        self.assertEqual(custody.admission(self.store)['state'], 'held')

    def test_expired_future_long_lived_or_wrong_installation_payload_cannot_be_signed(self):
        for n, changes in enumerate([{'expires_at': int(time.time())}, {'created_at': int(time.time()) + 20},
                                     {'expires_at': int(time.time()) + 901}, {'installation_id': '550e8400-e29b-41d4-a716-446655440090'}]):
            with self.subTest(changes=changes), self.assertRaises(custody.Held):
                custody.payload(custody.canonical(self.plan() | changes), self.policy)

    def test_duplicate_person_key_role_or_expired_policy_cannot_authorize(self):
        for index, field in enumerate(['id', 'public_key_pem', 'role', 'expiry']):
            policy = json.loads(json.dumps(self.policy))
            if field == 'expiry':
                policy['valid_until'] = int(time.time())
            else:
                policy['principals'][1][field] = policy['principals'][0][field]
            path = self.put(f'invalid-policy-{index}.json', policy)
            with self.subTest(field=field), self.assertRaises(custody.Held):
                custody.policy(path)

    def test_tampered_or_duplicate_signature_does_not_release(self):
        envelope, confirmation = self.envelope()
        original = custody.decode(custody.read(envelope, private=True))
        for n, kind in enumerate(['tamper', 'duplicate']):
            packet = json.loads(json.dumps(original))
            if kind == 'tamper':
                packet['signatures'][0]['signature'] = base64.b64encode(b'x' * 384).decode()
            else:
                packet['signatures'][1] = packet['signatures'][0]
            with self.subTest(kind=kind), self.assertRaises(custody.Held):
                custody.resume(self.store, self.put(f'tampered-{n}.json', packet), confirmation)
        self.assertEqual(custody.admission(self.store)['state'], 'held')

    def test_signer_key_must_match_the_independently_enrolled_public_key(self):
        plan = self.put('sign-plan.json', self.plan())
        with self.assertRaises(custody.Held):
            custody.sign(self.trust, plan, self.policy['principals'][0]['id'], self.keys[1], self.root / 'invalid-signature.json', passphrase=self.phrase)
        self.assertFalse((self.root / 'invalid-signature.json').exists())

    def test_descriptor_or_confirmation_substitution_cannot_release(self):
        envelope, confirmation = self.envelope()
        invalid = self.put('unconfirmed.json', {'recovery_id': self.plan()['recovery_id'], 'admission': 'HELD'})
        with self.assertRaises(custody.Held):
            custody.resume(self.store, envelope, invalid)
        custody.atomic(self.store / 'public' / 'identity-admission.json', custody.canonical(self.initial), 0o444)
        with self.assertRaises(custody.Held):
            custody.resume(self.store, envelope, confirmation)

    def test_crash_between_authorization_and_admission_stays_held_and_requires_a_new_epoch(self):
        envelope, confirmation = self.envelope()
        original = custody.atomic
        def interrupted(path, wire, mode):
            if Path(path).name == 'identity-admission.json':
                raise OSError('synthetic power loss')
            return original(path, wire, mode)
        with patch.object(custody, 'atomic', side_effect=interrupted), self.assertRaises(OSError):
            custody.resume(self.store, envelope, confirmation)
        self.assertEqual(custody.admission(self.store)['state'], 'held')
        with self.assertRaises(custody.Held):
            custody.checked(self.store)
        custody.hold(self.store, 'REC-SYNTHETIC-RECONTAIN')
        custody.checked(self.store)
        with self.assertRaises(custody.Held):
            custody.resume(self.store, envelope, confirmation)

    def test_corrupt_journal_still_allows_containment_but_never_resumption(self):
        custody.atomic(self.store / 'journal.jsonl', b'{"corrupt":true}', 0o600)
        epoch = custody.admission(self.store)['epoch']
        with self.assertRaises(custody.Held):
            custody.hold(self.store, 'REC-CORRUPT')
        self.assertEqual(custody.admission(self.store)['state'], 'held')
        self.assertNotEqual(custody.admission(self.store)['epoch'], epoch)

    def test_canonical_json_rejects_duplicate_keys_and_float_ambiguity(self):
        for wire in [b'{"v":1,"v":2}', b'{"v":1.0}', b'{ "v":1}', b'{"v":1}\n']:
            with self.subTest(wire=wire), self.assertRaises(custody.Held):
                custody.decode(wire)

    def test_private_files_cannot_be_world_readable_symlinked_or_overwritten(self):
        path = self.put('private.json', {'v': 1})
        path.chmod(0o644)
        with self.assertRaises(custody.Held):
            custody.read(path, private=True)
        with self.assertRaises(FileExistsError):
            custody.write_new(path, b'{}')
        link = self.root / 'symlink.json'
        link.symlink_to(self.trust)
        with self.assertRaises(OSError):
            custody.read(link)


if __name__ == '__main__':
    unittest.main()
