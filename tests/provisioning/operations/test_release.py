import base64
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes

from provisioner.qualification import mobility, release
from tests.provisioning.operations.campaign_fixtures import AS_OF, fixture


class TestSigner:
    key_id = 'synthetic-pilot-and-release-key'
    def __init__(self, key_id=None):
        if key_id is not None:
            self.key_id = key_id
        self.key = ec.generate_private_key(ec.SECP256R1())
    def sign(self, payload):
        return self.key.sign(payload, ec.ECDSA(hashes.SHA256()))
    def verify(self, key_id, payload, signature):
        if key_id != self.key_id:
            raise ValueError('Untrusted or revoked key')
        self.key.public_key().verify(signature, payload, ec.ECDSA(hashes.SHA256()))


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.archive = self.root / 'fixture-runtime.whl'
        self.archive.write_bytes(b'synthetic-runtime-artifact')
        artifact_digest = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        self.spec, self.bundle, _ = fixture(artifact_digest)
        assessment = mobility.assess(self.spec, qualification_index=self.bundle['qualification'],
            provenance_index=self.bundle['provenance'], campaign_index=self.bundle['campaign'],
            selection_index=self.bundle['targetSelection'], as_of=AS_OF)
        self.matrix = mobility.unsupported_matrix([assessment])
        self.signer = TestSigner()
        self.release_signer = TestSigner('independent-synthetic-release-key')
        self.payload = {'format': 'hosting-pilot-acceptance/1',
            'codeRevision': self.spec.code_revision, 'installedArtifactSha256': artifact_digest,
            'supportMatrixSha256': hashlib.sha256(release._canonical(self.matrix)).hexdigest(),
            'receivingTeamRef': 'controlled-receiving-team:synthetic',
            'changeAuthorityRef': 'controlled-change-authority:synthetic',
            'acceptanceRef': 'controlled-acceptance:synthetic', 'acceptedAt': '2026-10-02T00:00:00Z',
            'expiresAt': '2026-12-31T23:59:59Z',
            'scenarios': [{'id': scenario, 'result': 'ACCEPTED',
                           'evidenceRef': 'controlled-pilot-evidence:' + scenario,
                           'artifactSha256': hashlib.sha256(scenario.encode()).hexdigest()}
                          for scenario in release.PILOT_SCENARIOS]}

    def tearDown(self):
        self.temporary.cleanup()

    def envelope(self):
        return {'payload': self.payload, 'keyId': self.signer.key_id,
                'signature': base64.b64encode(self.signer.sign(release._canonical(self.payload))).decode()}

    def prepare(self, **kwargs):
        return release.prepare(self.archive, [self.spec],
            qualification_index=self.bundle['qualification'], provenance_index=self.bundle['provenance'],
            campaign_index=self.bundle['campaign'], selection_index=self.bundle['targetSelection'],
            pilot_envelope=kwargs.pop('pilot_envelope', self.envelope()), pilot_verifier=self.signer,
            release_signer=self.release_signer, destination=self.root / 'prepared-release', as_of=AS_OF, **kwargs)

    def test_signed_synthetic_pilot_and_current_routes_prepare_verifiable_release(self):
        result = self.prepare()
        self.assertEqual(result['status'], 'SIGNED_RELEASE_PREPARED_FOR_OWNER_PUBLICATION')
        self.assertFalse(result['remotePublicationAttempted'])
        root = self.root / 'prepared-release'
        signed = json.loads((root / 'release-manifest.json').read_bytes())
        matrix = json.loads((root / 'support-matrix.json').read_bytes())
        pilot = json.loads((root / 'pilot-acceptance.json').read_bytes())
        verified = release.verify_artifact(self.archive, signed, matrix, pilot, release_verifier=self.release_signer)
        self.assertFalse(verified['mutationAuthorized'])
        self.assertTrue(verified['currentQualificationRecheckRequired'])
        self.archive.write_bytes(b'changed-code')
        with self.assertRaises(ValueError):
            release.verify_artifact(self.archive, signed, matrix, pilot, release_verifier=self.release_signer)

    def test_no_pilot_stale_final_revision_or_unsupported_route_cannot_prepare_release(self):
        with self.assertRaises(ValueError):
            self.prepare(pilot_envelope={})
        self.payload['codeRevision'] = 'e' * 40
        with self.assertRaisesRegex(ValueError, 'final installed'):
            self.prepare()
        self.payload['codeRevision'] = self.spec.code_revision
        self.spec = replace(self.spec, guest_profile='ENCRYPTED_VTPM')
        with self.assertRaisesRegex(ValueError, 'advertised route'):
            self.prepare()
        self.assertFalse((self.root / 'prepared-release').exists())

    def test_altered_or_revoked_acceptance_and_unaccepted_scenario_fail_closed(self):
        envelope = self.envelope()
        envelope['payload'] = deepcopy(envelope['payload'])
        envelope['payload']['acceptanceRef'] = 'controlled-acceptance:forged'
        with self.assertRaises(Exception):
            self.prepare(pilot_envelope=envelope)
        envelope = self.envelope()
        envelope['keyId'] = 'withdrawn-key'
        with self.assertRaises(ValueError):
            self.prepare(pilot_envelope=envelope)
        self.payload['scenarios'][0]['result'] = 'NOT_RUN'
        with self.assertRaisesRegex(ValueError, 'unaccepted'):
            self.prepare()

    def test_pilot_and_release_owner_cannot_sign_their_own_acceptance(self):
        self.release_signer = self.signer
        with self.assertRaisesRegex(ValueError, 'different owner'):
            self.prepare()


if __name__ == '__main__':
    unittest.main()
