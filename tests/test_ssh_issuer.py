"""Actual OpenSSH signatures, durable serials and monotonic issuance denial."""
from copy import deepcopy
from datetime import timedelta
import fcntl
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from tools import ssh_issuer as d, readback_core as c
from tools.run_files import digest, encoded, utcnow, write_new


class EngineHost(d.Host):
    def __init__(self): self.signatures = 0; self.failure = None
    def identity(self, config, root): pass
    def sign(self, *args):
        self.signatures += 1
        if self.failure == 'before': raise InterruptedError
        super().sign(*args)
        if self.failure == 'after': raise InterruptedError


class IssuerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup); self.base = Path(temporary.name)
        self.keygen = shutil.which('ssh-keygen')
        self.assertIsNotNone(self.keygen, 'OpenSSH signer is required for issuer tests')
        for name in ('ca', 'subject', 'other'):
            d.Host().command([self.keygen, '-q', '-t', 'ed25519', '-N', '', '-f', self.base/name])
        def public(name): return ' '.join((self.base/(name+'.pub')).read_text().split()[:2])
        self.other = public('other'); self.host = EngineHost()
        self.config = dict(format='hosting-ssh-issuer/1', source_commit='a'*40,
            machine_id=Path('/etc/machine-id').read_text().strip(), uid=os.getuid(), source=str(d.ROOT),
            ssh_keygen=self.keygen, ssh_keygen_sha256=digest(Path(self.keygen).read_bytes()),
            ca_private=dict(path=str(self.base/'ca'), sha256=digest((self.base/'ca').read_bytes())), ca_public=public('ca'),
            principal='accepted-worker', source_ranges=['127.0.0.1/32'], maximum_validity_seconds=300,
            serial_floor=100, data_directory=str(self.base/'ledger'),
            policy_ref='TEST-SCOPED-IDENTITY', recovery_ref='TEST-INDEPENDENT-CUSTODY')
        now = utcnow()
        self.request = dict(format='hosting-ssh-issuer-request/1', config_sha256=c.digest(self.config),
            operation_id='issue-01', action='issue', subject=public('subject'), identity_ref='TEST-ENROLLMENT',
            valid_after=int(now.timestamp())-10, valid_before=int(now.timestamp())+180, source_range='127.0.0.1/32')
        self.authority = dict(format='hosting-ssh-issuer-authority/1', request_sha256=c.digest(self.request), action='issue', ledger_mode='new',
            valid_from=(now-timedelta(minutes=1)).isoformat(), valid_until=(now+timedelta(minutes=5)).isoformat(), change_ref='TEST-ONLY')
    def bind(self): self.request['config_sha256'] = c.digest(self.config); self.authority['request_sha256'] = c.digest(self.request)
    def execute(self):
        if self.authority['action'] == 'observe': self.authority['ledger_mode'] = 'retained'
        return d.execute(self.config, self.request, self.authority, host=self.host)
    def events(self): return sorted(Path(self.config['data_directory']).glob('*.json'))

    def test_native_certificate_exact_scope_and_completed_read_does_not_sign_again(self):
        result = self.execute(); raw = Path(result['certificate_path']).read_bytes()
        cert = d.verify_certificate(self.config, self.request, 100, raw)
        self.assertEqual(cert.extensions, {}); self.assertFalse(result['subject_revoked'])
        self.assertFalse(result['native_fencing'] or result['production_activation'])
        self.authority['action'] = 'observe'; again = self.execute()
        self.assertEqual(again['certificate_sha256'], result['certificate_sha256'])
        self.assertEqual(self.host.signatures, 1); self.assertEqual(len(self.events()), 3)
        self.assertEqual(Path(result['certificate_path']).stat().st_mode & 0o777, 0o600)
        self.request['operation_id'] = 'issue-02'; self.authority['action'] = 'issue'; self.bind()
        self.assertEqual(self.execute()['serial'], 101)

    def test_lost_signature_response_is_observed_without_signing_or_extending_validity(self):
        self.host.failure = 'after'
        with self.assertRaises(InterruptedError): self.execute()
        with self.assertRaisesRegex(ValueError, 'read-only recovery'): self.execute()
        self.authority['action'] = 'observe'
        result = self.execute(); self.assertEqual(self.host.signatures, 1)
        self.assertEqual(result['valid_before'], self.request['valid_before']); self.assertEqual(len(self.events()), 3)

    def test_missing_unknown_signature_consumes_serial_and_never_retries(self):
        self.host.failure = 'before'
        with self.assertRaises(InterruptedError): self.execute()
        self.authority['action'] = 'observe'
        with self.assertRaises(FileNotFoundError): self.execute()
        self.host.failure = None; self.request['operation_id'] = 'issue-02'; self.authority['action'] = 'issue'; self.bind()
        self.assertEqual(self.execute()['serial'], 101); self.assertEqual(self.host.signatures, 2)

    def test_revocation_prevents_renewal_and_historical_read_reports_denial(self):
        issued = self.execute(); original = deepcopy(self.request)
        self.request = {key:value for key,value in original.items() if key not in {'valid_after', 'valid_before', 'source_range'}}
        self.request.update(action='revoke', operation_id='revoke-01'); self.authority['action'] = 'revoke'; self.bind()
        result = self.execute(); self.execute()
        self.assertEqual(result['revoked_subjects'], [original['subject']]); self.assertFalse(result['endpoint_revocation_observed'])
        self.request = original; self.authority['action'] = 'observe'; self.bind()
        self.assertTrue(self.execute()['subject_revoked'])
        self.assertEqual(self.execute()['certificate_sha256'], issued['certificate_sha256'])
        self.request['operation_id'] = 'renewal-01'; self.authority['action'] = 'issue'; self.bind()
        with self.assertRaisesRegex(ValueError, 'revoked'): self.execute()
        self.assertEqual(self.host.signatures, 1)

    def test_crash_after_revocation_intent_still_denies_new_issuance(self):
        self.execute(); original = deepcopy(self.request)
        self.request = {key:value for key,value in original.items() if key not in {'valid_after', 'valid_before', 'source_range'}}
        self.request.update(action='revoke', operation_id='revoke-01'); self.authority['action'] = 'revoke'; self.bind()
        with patch.object(d, 'write_new', side_effect=InterruptedError), self.assertRaises(InterruptedError): self.execute()
        self.request = original; self.request['operation_id'] = 'renewal-01'; self.authority['action'] = 'issue'; self.bind()
        with self.assertRaisesRegex(ValueError, 'revoked'): self.execute()

    def test_forged_certificate_rejected_even_if_its_claims_match(self):
        self.execute(); directory = Path(self.config['data_directory'])/('operation-'+digest(self.request['operation_id'].encode()))
        wrong = deepcopy(self.config); wrong['ca_private']['path'] = str(self.base/'other')
        d.Host().sign(wrong, self.request, 100, directory)
        with self.assertRaisesRegex(ValueError, 'trust or subject'):
            d.verify_certificate(self.config, self.request, 100, (directory/'subject-cert.pub').read_bytes())
        self.authority['action'] = 'observe'
        with self.assertRaisesRegex(ValueError, 'certificate changed'): self.execute()

    def test_signature_tampering_and_changed_claims_are_rejected(self):
        result = self.execute(); raw = Path(result['certificate_path']).read_bytes()
        import base64
        parts = raw.split(); payload = bytearray(base64.b64decode(parts[1])); payload[-1] ^= 1
        tampered = parts[0]+b' '+base64.b64encode(payload)
        with self.assertRaises(Exception): d.verify_certificate(self.config, self.request, 100, tampered)
        for key,value in [('valid_before', self.request['valid_before']+1), ('subject', self.other), ('source_range', '127.0.0.2/32')]:
            changed = self.request | {key:value}
            with self.assertRaises(ValueError): d.verify_certificate(self.config, changed, 100, raw)
        with self.assertRaises(ValueError): d.verify_certificate(self.config, self.request, 101, raw)

    def test_added_native_extension_is_rejected(self):
        result = self.execute(); path = Path(result['certificate_path'])
        self.host.command([self.keygen, '-q', '-s', self.base/'ca', '-I', 'hosting:'+c.digest(self.request),
            '-n', self.config['principal'], '-O', 'clear', '-O', 'permit-pty', '-O', 'source-address=127.0.0.1/32',
            '-V', f"0x{self.request['valid_after']:x}:0x{self.request['valid_before']:x}", '-z', '100', path.parent/'subject.pub'])
        with self.assertRaisesRegex(ValueError, 'grants differ'): d.verify_certificate(self.config, self.request, 100, path.read_bytes())

    def test_expired_certificate_read_never_claims_renewed_lifetime(self):
        self.execute(); self.authority['action'] = 'observe'
        future = utcnow()+timedelta(minutes=10)
        self.authority.update(valid_from=(future-timedelta(seconds=10)).isoformat(), valid_until=(future+timedelta(minutes=1)).isoformat())
        with patch('tools.run_files.utcnow', return_value=future): result = self.execute()
        self.assertLess(result['valid_before'], future.timestamp()); self.assertEqual(self.host.signatures, 1)

    def test_policy_scope_lifetime_authority_and_operation_cannot_expand(self):
        for changes in ({'source_range':'10.0.0.1/32'}, {'valid_before':self.request['valid_after']+301}, {'subject':self.config['ca_public']}):
            with self.subTest(changes=changes), self.assertRaises(ValueError): d.validate_request(self.config, self.request|changes)
        original = deepcopy(self.authority); self.authority['valid_until'] = (utcnow()+timedelta(seconds=5)).isoformat()
        with self.assertRaises(ValueError): self.execute()
        self.authority = original; self.execute(); self.request['identity_ref'] = 'CHANGED'; self.bind()
        with self.assertRaisesRegex(ValueError, 'cannot change'): self.execute()
        self.assertEqual(self.host.signatures, 1)

    def test_competing_writer_and_failed_intent_do_not_sign(self):
        self.execute(); fd = os.open(Path(self.config['data_directory'])/'writer.lock', os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError): self.execute()
        finally: os.close(fd)
        self.request['operation_id'] = 'issue-02'; self.bind()
        with patch.object(d.journal.Journal, 'append', side_effect=OSError), self.assertRaises(OSError): self.execute()
        self.assertEqual(self.host.signatures, 1)

    def test_retained_missing_policy_change_and_exhausted_serial_hold(self):
        self.authority['ledger_mode'] = 'retained'; self.bind()
        with self.assertRaisesRegex(ValueError, 'history is missing'): self.execute()
        self.authority['ledger_mode'] = 'new'; self.config['serial_floor'] = 2**64-1; self.bind()
        self.assertEqual(self.execute()['serial'], 2**64-1)
        self.request['operation_id'] = 'issue-02'; self.bind()
        with self.assertRaisesRegex(ValueError, 'available serial'): self.execute()
        self.config['policy_ref'] = 'CHANGED'; self.bind()
        with self.assertRaisesRegex(ValueError, 'custody or policy changed'): self.execute()

    def test_actual_host_checks_ca_bytes_and_public_identity_before_any_signing(self):
        # Source hash is fixture-only; production host/key/binary checks are real.
        with tempfile.TemporaryDirectory(dir=Path.home()) as tmp, \
             patch.object(d, 'verify', return_value={'status':'HASHES_MATCH', 'commit':'a'*40}):
            root = Path(tmp); self.config['source'] = str(root)
            d.Host().identity(self.config, root)
            wrong = deepcopy(self.config); wrong['ca_public'] = self.other
            with self.assertRaisesRegex(ValueError, 'Signing key identity differs'): d.Host().identity(wrong, root)
            wrong = deepcopy(self.config); wrong['ca_private']['sha256'] = '0'*64
            with self.assertRaisesRegex(ValueError, 'Signing key bytes changed'): d.Host().identity(wrong, root)
            wrong = deepcopy(self.config); wrong['machine_id'] = '0'*32
            with self.assertRaisesRegex(ValueError, 'Wrong issuer'): d.Host().identity(wrong, root)
            root.chmod(0o777)
            with self.assertRaisesRegex(ValueError, 'controlled by its custodian'): d.Host().identity(self.config, root)


if __name__ == '__main__': unittest.main()
