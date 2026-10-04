"""Installer custody, interrupted host actions and native unit parsing."""
from copy import deepcopy
from datetime import timedelta
import fcntl
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tests import test_nft_edge as edge_fixture
from provisioner.execution import readback_core as c
from provisioner.execution import edge_install as d
from provisioner.execution.run_files import digest, encoded, load_private, utcnow, write_new


class Host(d.Host):
    def __init__(self, base):
        super().__init__(base, custodian_uid=os.getuid(), custodian_gid=os.getgid())
        for path in ('etc/systemd/system', 'var/lib'): (base/path).mkdir(parents=True)
        self.calls=[]; self.loaded=False; self.active=False; self.manager_active=False
        self.fail=None; self.guard_dropins=''; self.manager_extra=''; self.dependencies=True; self.deny=True
    def identity(self, config, root): pass
    def command(self, argv):
        args=list(map(str,argv)); self.calls.append(args)
        if self.fail and self.fail in args: raise OSError('Synthetic installation interruption')
        if 'daemon-reload' in args: self.loaded=True
        if 'start' in args: self.active=True
        if 'is-enabled' in args: return 'enabled'
        return ''
    def property(self, config, service, name):
        guard=service==d.SERVICE
        if name=='LoadState': return 'not-found' if guard and not self.loaded else 'loaded'
        if name=='FragmentPath': return (str(self.path(d.UNIT)) if self.loaded else '') if guard else config['manager_unit']['path']
        if name=='DropInPaths':
            if guard: return self.guard_dropins
            return ' '.join([row['path'] for row in config['manager_dropins']]+
                ([str(d.dropin(config))] if self.loaded else [])+([self.manager_extra] if self.manager_extra else []))
        if name=='ActiveState': return ('active' if self.active else 'inactive') if guard else ('active' if self.manager_active else 'inactive')
        if name=='SubState': return 'exited' if guard and self.active else 'running' if self.manager_active else 'dead'
        if name in {'After','Requires'}: return d.SERVICE if self.dependencies else ''
        raise AssertionError(name)
    def denial(self, config, directory):
        if not self.deny: raise ValueError('Current denial unconfirmed')
        return {'fixture-scope':{'status':'FIXTURE-DENIAL'}}


class InstallTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='hosting-edge-test-',dir='/var/tmp')
        self.addCleanup(temporary.cleanup); self.base=Path(temporary.name); self.host=Host(self.base/'host')
        ledger=self.base/'native-ledger'; ledger.mkdir(mode=0o700); self.native=ledger/'unknown.json'
        write_new(self.native,b'PRESERVE UNKNOWN NATIVE ATTEMPT')
        nft=self.base/'nft'; write_new(nft,b'TEST-ENGINE')
        spec=edge_fixture.fixture(); spec.update(flows=[],nft_sha256=digest(nft.read_bytes()))
        spec_path=self.base/'boundary.json'; write_new(spec_path,encoded(spec))
        self.config=dict(format='hosting-edge-install/1',source='/opt/hosting-source',python='/usr/bin/python3',
            systemctl='/usr/bin/systemctl',systemd_analyze='/usr/bin/systemd-analyze',manager='systemd-networkd.service',
            manager_unit={'path':'/usr/lib/systemd/system/systemd-networkd.service','sha256':'b'*64},
            manager_dropins=[],custody_ref='TEST-INDEPENDENT-CONSOLE',
            boot=dict(format='hosting-edge-boot/1',source_commit='a'*40,machine_id=spec['machine_id'],
                network_namespace_inode=spec['network_namespace_inode'],nft=str(nft),nft_sha256=spec['nft_sha256'],
                ledger=str(ledger),specs=[{'path':str(spec_path),'sha256':digest(encoded(spec))}],
                boundary_acceptance_ref='TEST-ONLY',boot_ordering_ref='TEST-ONLY'))
        for name in ('python','systemctl','systemd_analyze'): self.config[name+'_sha256']='c'*64
        self.authority=dict(format='hosting-edge-install-authority/1',config_sha256=c.digest(self.config),
            valid_from=(utcnow()-timedelta(minutes=1)).isoformat(),valid_until=(utcnow()+timedelta(minutes=10)).isoformat(),
            change_ref='TEST-CHANGE',maintenance_ref='TEST-OFFLINE-MANAGER',recovery_access_ref='TEST-OOB')
    def install(self): return d.install(self.config,self.authority,host=self.host)
    def count(self,arg): return sum(arg in command for command in self.host.calls)
    def bind(self): self.authority['config_sha256']=c.digest(self.config)

    def test_installs_durable_boundaries_and_dependency_without_starting_networking(self):
        first=self.install(); again=self.install()
        self.assertEqual(first['status'],again['status']); self.assertFalse(first['network_manager_started'])
        self.assertFalse(first['actual_reboot_tested'] or first['production_activation'])
        self.assertEqual(self.native.read_bytes(),b'PRESERVE UNKNOWN NATIVE ATTEMPT')
        installed=load_private(self.host.path(d.CONFIG/'boot.json'))
        self.assertEqual(installed['ledger'],self.config['boot']['ledger'])
        self.assertEqual(installed['specs'][0]['path'],str(d.CONFIG/'boundary-000.json'))
        self.assertEqual(self.host.path(d.CONFIG/'boundary-000.json').stat().st_mode & 0o777,0o600)
        self.assertEqual(self.host.path(d.dropin(self.config)).read_text(),
            '[Unit]\nRequires=hosting-edge-boot.service\nAfter=hosting-edge-boot.service\n')
        self.assertEqual(self.count('stop')+self.count('restart'),0)
        for args in self.host.calls:
            if 'start' in args: self.assertEqual(args[-1],d.SERVICE)

    def test_running_manager_holds_before_any_unit_installation(self):
        self.host.manager_active=True
        with self.assertRaisesRegex(ValueError,'manager stopped'): self.install()
        self.assertFalse(self.host.path(d.UNIT).exists()); self.assertEqual(self.count('daemon-reload'),0)
        self.assertFalse((self.host.path(d.STATE)/'intent.json').exists())

    def test_interrupted_reload_and_start_resume_without_erasing_history(self):
        self.host.fail='daemon-reload'
        with self.assertRaises(OSError): self.install()
        self.assertTrue(self.host.path(d.UNIT).is_file())
        self.host.fail='start'
        with self.assertRaises(OSError): self.install()
        self.assertTrue(self.host.loaded); self.assertFalse(self.host.active)
        self.host.fail=None; self.install()
        self.assertEqual(self.native.read_bytes(),b'PRESERVE UNKNOWN NATIVE ATTEMPT')
        self.assertEqual(len(list(self.host.path(d.STATE).glob('receipt-*.json'))),1)

    def test_native_parse_failure_keeps_startup_held(self):
        self.host.fail='verify'
        with self.assertRaises(OSError): self.install()
        self.assertEqual(self.count('daemon-reload')+self.count('start'),0)
        self.assertEqual(list(self.host.path(d.STATE).glob('receipt-*.json')),[])

    def test_changed_policy_and_existing_bytes_never_overwrite_or_restart(self):
        self.install(); starts=self.count('start'); old=deepcopy(self.config)
        self.config['custody_ref']='CHANGED'; self.bind()
        with self.assertRaisesRegex(ValueError,'Another installation'): self.install()
        self.config=old; self.bind(); path=self.host.path(d.CONFIG/'boundary-000.json'); path.write_bytes(b'FOREIGN')
        with self.assertRaisesRegex(ValueError,'Existing worker file changed'): self.install()
        self.assertEqual(path.read_bytes(),b'FOREIGN'); self.assertEqual(self.count('start'),starts)

    def test_foreign_loaded_overrides_and_missing_hard_dependency_hold(self):
        self.host.manager_extra='/run/systemd/system/systemd-networkd.service.d/foreign.conf'
        with self.assertRaisesRegex(ValueError,'overrides differ'): self.install()
        self.host.manager_extra=''; self.host.guard_dropins='/run/systemd/system/service.d/foreign.conf'
        with self.assertRaisesRegex(ValueError,'Unmanaged loaded startup guard'): self.install()
        self.assertEqual(self.count('start'),0)
        self.host.guard_dropins=''; self.host.dependencies=False
        with self.assertRaisesRegex(ValueError,'hard startup guard dependency'): self.install()
        self.assertEqual(self.count('start'),0)

    def test_active_guard_with_unconfirmed_policy_is_not_restarted_to_hide_drift(self):
        self.install(); self.host.deny=False
        with self.assertRaisesRegex(ValueError,'denial unconfirmed'): self.install()
        self.assertEqual(self.count('restart')+self.count('stop'),0)
        self.assertEqual(len(list(self.host.path(d.STATE).glob('receipt-*.json'))),1)

    def test_unknown_preexisting_service_and_concurrent_installer_hold(self):
        self.host.file(d.UNIT,b'FOREIGN',0o644)
        with self.assertRaisesRegex(ValueError,'Unmanaged startup guard'): self.install()
        self.host.path(d.UNIT).unlink(); self.install()
        fd=os.open(self.host.path(d.STATE/'writer.lock'),os.O_RDWR)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError): self.install()
        finally: os.close(fd)

    def test_expired_authority_and_volatile_dependencies_are_rejected(self):
        self.authority['valid_until']=(utcnow()-timedelta(seconds=1)).isoformat()
        with self.assertRaises(ValueError): self.install()
        for update in ({'source':'/home/owner/source'},{'python':'/run/runtime/python'},{'manager':'ssh.service'}):
            with self.subTest(update=update),self.assertRaises(ValueError): d.validate(self.config|update)
        bad=deepcopy(self.config); bad['boot']['specs'][0]['sha256']='0'*64
        with self.assertRaises(ValueError): d.validate(bad)

    def test_generated_guard_and_manager_dependency_parse_with_real_systemd(self):
        analyze=shutil.which('systemd-analyze')
        self.assertIsNotNone(analyze,'Native unit parser is required for installation tests')
        _,rendered=d.installed_files(self.config)
        unit=self.base/d.SERVICE; unit.write_bytes(rendered[d.UNIT][0])
        manager=self.base/self.config['manager']
        manager.write_text('[Unit]\nRequires=hosting-edge-boot.service\nAfter=hosting-edge-boot.service\n'
            '[Service]\nType=oneshot\nExecStart=/usr/bin/true\n')
        result=subprocess.run([analyze,'verify','--man=no',str(unit),str(manager)],capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)


if __name__=='__main__': unittest.main()
