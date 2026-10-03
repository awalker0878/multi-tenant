"""Monotonic credential denial survives crashes and later endpoint installation."""
from copy import deepcopy
from datetime import timedelta
import fcntl
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from tests import test_owner_install as fixture
from provisioner.execution import readback_core as c
from tools import owner_install as installer, owner_revocations as d, execution_journal as journal
from provisioner.execution.run_files import digest,encoded,load_private,utcnow
key=fixture.key


class RevocationTests(unittest.TestCase):
    def setUp(self):
        fixture.InstallTests.setUp(self)
        self.install_authority=self.authority
        installer.install(self.config,self.install_authority,host=self.host)
        self.request=dict(format='hosting-owner-revocation/1',config_sha256=c.digest(self.config),
                          operation_id='revoke-01',keys=[key(3)],identity_ref='TEST-COMPROMISED-SUBJECT')
        self.authority=dict(format='hosting-owner-revocation-authority/1',request_sha256=c.digest(self.request),
            valid_from=(utcnow()-timedelta(minutes=1)).isoformat(),valid_until=(utcnow()+timedelta(minutes=10)).isoformat(),
            change_ref='TEST-IDENTITY-CHANGE',recovery_access_ref='TEST-INDEPENDENT-CONSOLE')
        self.policy=self.host.path(installer.CONFIG/'revoked-keys')
    def revoke(self): return d.revoke(self.config,self.request,self.authority,host=self.host)
    def events(self): return list(self.host.path(installer.STATE/'revocations').glob('*.json'))

    def test_revocation_is_monotonic_idempotent_and_preserved_by_repeat_installation(self):
        calls=len(self.host.calls); result=self.revoke()
        self.assertEqual(result['status'],'SUBJECTS_REVOKED_FOR_NEW_AUTHENTICATION')
        self.assertFalse(result['existing_sessions_terminated'] or result['native_fencing'])
        self.assertEqual(len(self.host.calls),calls)
        self.revoke(); self.assertEqual(len(self.events()),1)
        self.request.update(operation_id='revoke-02',keys=[key(4)]); self.authority['request_sha256']=c.digest(self.request)
        self.revoke(); expected=('\n'.join(sorted([key(3),key(4)]))+'\n').encode()
        self.assertEqual(self.policy.read_bytes(),expected)
        installer.install(self.config,self.install_authority,host=self.host)
        self.assertEqual(self.policy.read_bytes(),expected)

    def test_crash_after_intent_recovers_stronger_denial_with_fresh_authority(self):
        with patch.object(self.host,'replace_revocations',side_effect=InterruptedError),self.assertRaises(InterruptedError):
            self.revoke()
        self.assertEqual(len(self.events()),1); self.assertEqual(self.policy.read_bytes(),b'\n')
        self.authority['change_ref']='TEST-RENEWED-READ-AND-DENIAL'
        self.authority['valid_until']=(utcnow()+timedelta(minutes=20)).isoformat()
        self.revoke(); self.assertEqual(len(self.events()),1)
        self.assertEqual(self.policy.read_text(),key(3)+'\n')

    def test_missing_reply_after_publication_never_adds_duplicate_event(self):
        actual=self.host.replace_revocations
        def interrupted(*args): actual(*args); raise InterruptedError
        with patch.object(self.host,'replace_revocations',side_effect=interrupted),self.assertRaises(InterruptedError):
            self.revoke()
        self.assertEqual(self.policy.read_text(),key(3)+'\n')
        self.revoke(); self.assertEqual(len(self.events()),1)

    def test_unknown_extra_revocations_are_never_erased_and_missing_policy_holds(self):
        self.revoke(); self.policy.write_text(key(5)+'\n')
        with self.assertRaisesRegex(ValueError,'Unrecognized revocation'): self.revoke()
        with self.assertRaisesRegex(ValueError,'Unrecognized revocation'):
            installer.install(self.config,self.install_authority,host=self.host)
        self.assertEqual(self.policy.read_text(),key(5)+'\n')
        self.policy.unlink()
        with self.assertRaisesRegex(ValueError,'missing'): self.revoke()
        self.assertFalse(self.policy.exists())

    def test_changed_operation_authority_static_trust_and_corrupt_history_hold(self):
        self.revoke(); original=deepcopy(self.request)
        self.request['keys']=[key(4)]; self.authority['request_sha256']=c.digest(self.request)
        with self.assertRaisesRegex(ValueError,'identity cannot change'): self.revoke()
        self.request=original; self.authority['request_sha256']=c.digest(self.request)
        self.authority['valid_until']=(utcnow()-timedelta(seconds=1)).isoformat()
        with self.assertRaises(ValueError): self.revoke()
        self.authority['valid_until']=(utcnow()+timedelta(minutes=10)).isoformat()
        path=self.host.path(installer.CONFIG/'user-ca.pub'); original_ca=path.read_bytes(); path.write_text(key(5)+'\n')
        with self.assertRaisesRegex(ValueError,'Existing worker file changed'): self.revoke()
        path.write_bytes(original_ca)
        event=self.events()[0]; value=load_private(event); value['data']['request']['keys']=[key(5)]; event.write_bytes(encoded(value))
        with self.assertRaises(ValueError): self.revoke()
        self.assertEqual(self.policy.read_text(),key(3)+'\n')

    def test_installer_lock_and_failed_journal_prevent_policy_writes(self):
        fd=os.open(self.host.path(installer.STATE/'writer.lock'),os.O_RDWR)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError): self.revoke()
        finally: os.close(fd)
        with patch.object(journal.Journal,'append',side_effect=OSError),self.assertRaises(OSError): self.revoke()
        self.assertEqual(self.policy.read_bytes(),b'\n'); self.assertEqual(self.events(),[])

    def test_original_key_staging_can_be_removed_without_losing_revocation_control(self):
        Path(self.config['host_private']['path']).unlink()
        self.assertEqual(self.revoke()['revoked_policy_sha256'],digest((key(3)+'\n').encode()))


if __name__=='__main__': unittest.main()
