"""Exact resumable endpoint installation; no real host service is changed."""
import base64
from copy import deepcopy
from datetime import timedelta
import os
from pathlib import Path
import tempfile
import unittest

from tools import owner_install as d, readback_core as c
from tools.run_files import digest, encoded, utcnow, write_new


def key(byte):
    return 'ssh-ed25519 '+base64.b64encode(b'\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20'+bytes([byte])*32).decode()


def config(private):
    result = dict(format='hosting-owner-install/1', source_commit='a'*40, machine_id='b'*32,
        account='owner', uid=os.getuid(), gid=os.getgid(), listen_address='10.0.0.10', port=2222, principal='hosting-owner',
        source='/opt/hosting-source', python='/usr/bin/python3', sshd='/usr/sbin/sshd', systemctl='/usr/bin/systemctl',
        ssh_keygen='/usr/bin/ssh-keygen', host_private={'path':str(private),'sha256':digest(private.read_bytes())},
        host_public=key(1), user_ca=key(2), data_directory='/var/lib/hosting-owner-edge', ledger_mode='new', custody_ref='TEST-CUSTODY')
    for name in ('python','sshd','systemctl','ssh_keygen'): result[name+'_sha256']='c'*64
    return result


class Host(d.Host):
    def __init__(self, base):
        super().__init__(base,custodian_uid=os.getuid(),custodian_gid=os.getgid())
        for path in ('etc/systemd/system','etc/tmpfiles.d','var/lib','run'): (base/path).mkdir(parents=True)
        self.calls=[]; self.fail=None; self.dropins=''; self.public=key(1)
    def identity(self, config, root): pass
    def command(self, argv):
        args=list(map(str,argv)); self.calls.append(args)
        if self.fail and self.fail in args: raise OSError('Synthetic host interruption')
        if args[0].endswith('ssh-keygen'): return self.public
        if '--property=FragmentPath' in args: return str(self.path(d.UNIT))
        if '--property=DropInPaths' in args: return self.dropins
        if 'is-active' in args: return 'active'
        if 'is-enabled' in args: return 'enabled'
        return ''


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.base=Path(self.temp.name)
        private=self.base/'host-key'; write_new(private,b'TEST-KEY')
        self.config=config(private); self.host=Host(self.base/'host')
        self.authority=dict(format='hosting-owner-install-authority/1',config_sha256=c.digest(self.config),
            valid_from=(utcnow()-timedelta(minutes=1)).isoformat(),valid_until=(utcnow()+timedelta(minutes=10)).isoformat(),
            change_ref='TEST-CHANGE',recovery_access_ref='TEST-INDEPENDENT-CONSOLE')
    def install(self): return d.install(self.config,self.authority,host=self.host)
    def count(self, arg): return sum(arg in command for command in self.host.calls)

    def test_install_and_repeat_preserve_private_jobs_native_holds_and_management(self):
        self.host.public=key(1)+' fixture-key-comment'
        management=self.host.path('/etc/ssh'); management.mkdir(); (management/'sshd_config').write_text('UNCHANGED')
        self.assertEqual(self.install()['status'],'WORKER_INSTALLED_REQUIRES_ENDPOINT_ACCEPTANCE')
        ledger=self.host.path(self.config['data_directory'])/'ledger'; write_new(ledger/'held.json',b'UNKNOWN NATIVE OPERATION')
        self.assertEqual(self.install()['status'],'WORKER_INSTALLED_REQUIRES_ENDPOINT_ACCEPTANCE')
        self.assertEqual((ledger/'held.json').read_bytes(),b'UNKNOWN NATIVE OPERATION')
        self.assertEqual((management/'sshd_config').read_text(),'UNCHANGED')
        self.assertEqual(self.count('restart')+self.count('stop'),0)
        daemon=self.host.path(d.CONFIG/'sshd_config').read_text()
        self.assertIn('AuthorizedKeysFile none\n',daemon); self.assertIn('DisableForwarding yes\n',daemon)
        self.assertIn('ForceCommand /usr/bin/python3 -I /opt/hosting-source/tools/owner_worker.py',daemon)
        self.assertIn('SetEnv GIT_CONFIG_COUNT=1',daemon)
        self.assertEqual(self.host.path(d.CONFIG/'host-key').stat().st_mode & 0o777,0o600)
        self.assertEqual(self.host.path(d.CONFIG/'principals').read_text(),'hosting-owner\n')

    def test_lost_service_start_reply_resumes_exact_install_without_resetting_ledger(self):
        self.host.fail='start'
        with self.assertRaises(OSError): self.install()
        ledger=self.host.path(self.config['data_directory'])/'ledger'; write_new(ledger/'held.json',b'PRESERVE')
        self.host.fail=None; self.install()
        self.assertEqual((ledger/'held.json').read_bytes(),b'PRESERVE')
        self.assertTrue(self.host.path(d.STATE/'intent.json').is_file())
        self.assertEqual(len(list(self.host.path(d.STATE).glob('receipt-*.json'))),1)

    def test_changed_configuration_or_installed_bytes_cannot_trigger_service_action(self):
        self.install(); before=len(self.host.calls)
        self.config['principal']='other'; self.authority['config_sha256']=c.digest(self.config)
        with self.assertRaisesRegex(ValueError,'Another installation'): self.install()
        self.assertEqual(self.host.calls[before:],[['/usr/bin/ssh-keygen','-y','-f',self.config['host_private']['path']]])
        self.config['principal']='hosting-owner'; self.authority['config_sha256']=c.digest(self.config)
        self.host.path(d.CONFIG/'principals').write_text('FOREIGN')
        before=self.count('start')
        with self.assertRaisesRegex(ValueError,'Existing worker file changed'): self.install()
        self.assertEqual(self.count('start'),before)

    def test_retained_custody_requires_existing_private_state_and_never_creates_empty_ledger(self):
        self.config['ledger_mode']='retained'; self.authority['config_sha256']=c.digest(self.config)
        with self.assertRaisesRegex(ValueError,'Retained worker state is missing'): self.install()
        self.assertFalse(self.host.path(self.config['data_directory']).exists()); self.assertEqual(self.count('start'),0)
        data=Path(self.config['data_directory'])
        for path in (data,data/'spool',data/'ledger'):
            self.host.directory(path,os.getuid(),os.getgid())
        write_new(self.host.path(data/'ledger'/'unknown.json'),b'HELD')
        self.install(); self.assertEqual(self.host.path(data/'ledger'/'unknown.json').read_bytes(),b'HELD')

    def test_invalid_native_config_keys_or_dropins_hold_before_start(self):
        self.host.public=key(3)
        with self.assertRaisesRegex(ValueError,'public identity'): self.install()
        self.assertFalse(self.host.path(d.STATE).exists())
        self.host.public=key(1); self.host.fail='-t'
        with self.assertRaises(OSError): self.install()
        self.assertFalse(self.host.path(d.UNIT).exists())
        self.host.fail=None; self.host.dropins='/run/systemd/system/hosting-owner.service.d/foreign.conf'
        with self.assertRaisesRegex(ValueError,'Loaded worker service differs'): self.install()
        self.assertEqual(self.count('start'),0)

    def test_unmanaged_endpoint_symlinks_and_unsafe_or_expired_inputs_hold(self):
        original=deepcopy(self.config)
        for changes in ({'port':22},{'port':True},{'principal':'owner\nroot'},{'source':'/opt/$(shell)'},
                        {'data_directory':'/var/lib/hosting-owner-install'},{'host_public':'ssh-ed25519 AAAA'}):
            with self.subTest(changes=changes),self.assertRaises(ValueError): d.validate(original|changes)
        self.authority['valid_until']=(utcnow()-timedelta(seconds=1)).isoformat()
        with self.assertRaises(ValueError): self.install()
        self.authority['valid_until']=(utcnow()+timedelta(minutes=10)).isoformat()
        self.host.path(d.CONFIG).symlink_to(self.base,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'Unmanaged endpoint'): self.install()
        self.assertEqual(self.count('start'),0)


if __name__=='__main__': unittest.main()
