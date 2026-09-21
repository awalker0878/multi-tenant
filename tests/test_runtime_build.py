"""Offline build boundaries, full retained bytes, interruption and exact reuse."""
from copy import deepcopy
from datetime import timedelta
import fcntl
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from tools import runtime_build as d, readback_core as c
from tools.run_files import digest, encoded, utcnow, write_new


def zipped(files):
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w') as archive:
        for name,raw in files.items(): archive.writestr(name,raw)
    return output.getvalue()


def authority(config):
    return dict(format='hosting-runtime-build-authority/1',config_sha256=c.digest(config),
        valid_from=(utcnow()-timedelta(minutes=1)).isoformat(),valid_until=(utcnow()+timedelta(minutes=15)).isoformat(),change_ref='TEST-ONLY')


class Host(d.Host):
    def __init__(self, config): self.config=config; self.calls=[]; self.fail=None; self.extra={}; self.identity_calls=0
    def identity(self,config,root): self.identity_calls+=1
    def command(self,argv,cwd):
        args=list(map(str,argv)); self.calls.append(args)
        if self.fail and self.fail in args: raise OSError('Synthetic interruption')
        if d.PROFILE_CODE in args:
            return json.dumps(dict(version='3.13.15',implementation='CPython',platform='linux',machine='x86_64',
                prefix='/opt/python',base_prefix='/opt/python',stdlib='/opt/python/lib/python3.13'))
        if 'venv' in args:
            env=Path(args[-1]); (env/'bin').mkdir(parents=True); (env/'bin/python').write_bytes(b'PYTHON')
            # Accepted base copies can retain a group-writable source mode.
            (env/'bin/python').chmod(0o775); (env/'lib').mkdir(); (env/'lib64').symlink_to('lib')
            (env/'pyvenv.cfg').write_text('include-system-site-packages = false\n'); return ''
        if d.PACKAGES_CODE in args:
            return json.dumps(dict(packages={x['name']:x['version'] for x in self.config['wheels']}|self.extra,
                prefix=str(Path(self.config['output'])/'env'),base_prefix='/opt/python'))
        if 'version' in args: return json.dumps(dict(terraform_version='1.13.5',platform='linux_amd64'))
        return ''


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup); self.base=Path(temporary.name)
        wheels=[]
        for name,version in (d.pins(d.ROOT)|{'pip':'26.2.1'}).items():
            path=self.base/(name.replace('-','_')+'-'+version+'-py3-none-any.whl')
            raw=zipped({name.replace('-','_')+'-'+version+'.dist-info/METADATA':f'Name: {name}\nVersion: {version}\n'})
            write_new(path,raw); wheels.append(dict(name=name,version=version,path=str(path),sha256=digest(raw)))
        terraform=zipped({'terraform':b'TERRAFORM'}); path=self.base/'terraform.zip'; write_new(path,terraform)
        self.config=dict(format='hosting-runtime-build/1',enabled=True,source_commit='a'*40,python='/opt/python/bin/python',
            python_sha256='b'*64,python_version='3.13.15',base_os_sha256='c'*64,base_runtime_ref='TEST-BASE',
            artifact_acceptance_ref='TEST-ARTIFACTS',wheels=wheels,output=str(self.base/'built'),
            terraform=dict(path=str(path),sha256=digest(terraform),binary_sha256=digest(b'TERRAFORM'),version='1.13.5'))
        self.host=Host(self.config)
    def build(self,**kw): return d.build(self.config,authority(self.config),host=self.host,**kw)

    def test_exact_build_offline_commands_and_readonly_reuse(self):
        receipt=self.build(); self.assertFalse(receipt['native_qualification']); before=list(self.host.calls)
        self.assertEqual(self.build(),receipt); self.assertEqual(self.host.calls,before)
        self.assertEqual(d.build(self.config,None,host=self.host,observe=True),receipt); self.assertEqual(self.host.calls,before)
        pip=next(call for call in self.host.calls if 'install' in call)
        for flag in ('--no-index','--no-deps','--require-hashes','--only-binary=:all:','--no-cache-dir','--no-compile'):
            self.assertIn(flag,pip)
        self.assertEqual(d.ENV['PIP_CONFIG_FILE'],'/dev/null')
        self.assertNotIn('PYTHONPATH',d.ENV); self.assertIn('env/lib64',receipt['files'])
        self.assertEqual(receipt['files']['bin/terraform']['mode'],0o700)
        self.assertEqual(receipt['files']['env/bin/python']['mode'],0o700)
        self.assertEqual(receipt['files']['env/pyvenv.cfg']['mode'],0o600)

    def test_interrupted_install_never_repeats_or_deletes_partial_runtime(self):
        self.host.fail='install'
        with self.assertRaises(OSError): self.build()
        output=Path(self.config['output']); self.assertTrue((output/'env/bin/python').exists())
        before=list(self.host.calls); self.host.fail=None
        with self.assertRaisesRegex(ValueError,'Incomplete runtime'): self.build()
        self.assertEqual(self.host.calls,before); self.assertTrue((output/'intent.json').exists())
        self.assertFalse((output/'receipt.json').exists())

    def test_changed_completed_file_extra_file_mode_or_symlink_cannot_repair(self):
        self.build(); output=Path(self.config['output']); before=list(self.host.calls)
        binary=output/'bin/terraform'; binary.write_bytes(b'CHANGED')
        with self.assertRaisesRegex(ValueError,'runtime changed'): self.build()
        binary.write_bytes(b'TERRAFORM'); (output/'foreign').write_bytes(b'EXTRA')
        with self.assertRaisesRegex(ValueError,'runtime changed'): self.build()
        (output/'foreign').unlink(); binary.chmod(0o777)
        with self.assertRaisesRegex(ValueError,'writable mode'): self.build()
        binary.chmod(0o700); (output/'env/foreign').symlink_to('/etc')
        with self.assertRaisesRegex(ValueError,'runtime symlink'): self.build()
        self.assertEqual(self.host.calls,before)

    def test_wheel_hash_and_metadata_mismatch_prevent_any_artifact_execution(self):
        wheel=self.config['wheels'][0]; Path(wheel['path']).write_bytes(b'WRONG')
        with self.assertRaisesRegex(ValueError,'artifact changed'): self.build()
        self.assertEqual(self.host.calls,[])
        self.config['output']=str(self.base/'other')
        raw=zipped({'foreign-1.dist-info/METADATA':'Name: foreign\nVersion: 1\n'})
        Path(wheel['path']).write_bytes(raw); wheel['sha256']=digest(raw)
        with self.assertRaisesRegex(ValueError,'identity differs'): self.build()
        self.assertEqual(self.host.calls,[])

    def test_unsafe_archive_symlinks_duplicate_paths_and_unknown_terraform_files(self):
        for name in ('../escape','/absolute','a\\b','a//b','a/./b'):
            with self.subTest(name=name),self.assertRaises(ValueError): d.archive(zipped({name:'BAD'}))
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w') as z:
            item=zipfile.ZipInfo('link'); item.external_attr=(stat.S_IFLNK|0o777)<<16; z.writestr(item,'/etc')
        with self.assertRaisesRegex(ValueError,'file type'): d.archive(buffer.getvalue())
        raw=zipped({'terraform':b'TERRAFORM','extra':b'BAD'}); self.config['terraform']['sha256']=digest(raw)
        Path(self.config['terraform']['path']).write_bytes(raw)
        with self.assertRaisesRegex(ValueError,'Unexpected Terraform archive'): self.build()
        self.assertEqual(self.host.calls,[])

    def test_missing_pins_pip_duplicates_wrong_version_or_unsafe_output_fail_before_creation(self):
        original=deepcopy(self.config)
        changes=[{'wheels':original['wheels'][1:]},{'wheels':original['wheels'][:-1]},
                 {'wheels':original['wheels']+[original['wheels'][0]]},{'python_version':'3.12.14'},
                 {'output':str(d.ROOT/'build/runtime')},{'enabled':'true'}]
        for change in changes:
            with self.subTest(change=list(change)),self.assertRaises(ValueError): d.validate(original|change)
        self.assertFalse(Path(self.config['output']).exists())

    def test_expired_changed_or_disabled_authority_cannot_create_output(self):
        expired=authority(self.config); expired['valid_until']=(utcnow()-timedelta(seconds=1)).isoformat()
        for record in (expired,authority(self.config)|{'config_sha256':'d'*64}):
            with self.assertRaises(ValueError): d.build(self.config,record,host=self.host)
        self.config['enabled']=False
        with self.assertRaisesRegex(ValueError,'disabled'): self.build()
        self.assertFalse(Path(self.config['output']).exists()); self.assertEqual(self.host.calls,[])

    def test_dependency_failure_and_unexpected_installed_package_have_no_receipt(self):
        self.host.fail='check'
        with self.assertRaises(OSError): self.build()
        self.assertFalse((Path(self.config['output'])/'receipt.json').exists())
        self.config['output']=str(self.base/'other'); self.host.fail=None; self.host.extra={'foreign':'1'}
        with self.assertRaisesRegex(ValueError,'Installed packages'): self.build()
        self.assertFalse((Path(self.config['output'])/'receipt.json').exists())

    def test_completed_operation_identity_is_immutable_and_shared_lock_serializes(self):
        self.build(); self.config['base_runtime_ref']='CHANGED'
        with self.assertRaisesRegex(ValueError,'identity changed'): self.build()
        self.config['base_runtime_ref']='TEST-BASE'
        with (Path(self.config['output'])/'writer.lock').open('rb') as held:
            fcntl.flock(held,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError): self.build()

    def test_completed_verification_needs_neither_staged_wheels_nor_new_authority(self):
        self.build()
        for wheel in self.config['wheels']: Path(wheel['path']).unlink()
        Path(self.config['terraform']['path']).unlink()
        self.assertEqual(d.build(self.config,None,host=self.host,observe=True)['status'],
                         'RUNTIME_BUILT_REQUIRES_PLATFORM_ACCEPTANCE')

    def test_private_artifact_and_output_symlink_are_rejected(self):
        Path(self.config['wheels'][0]['path']).chmod(0o644)
        with self.assertRaisesRegex(ValueError,'owner-only'): self.build()
        self.config['output']=str(self.base/'symlink'); Path(self.config['output']).symlink_to(self.base/'built')
        with self.assertRaisesRegex(ValueError,'Symlink'): self.build()

    def test_native_host_checks_reject_source_or_base_python_changes(self):
        host=d.Host()
        with patch.object(d,'verify',return_value={'status':'FAILED_INTEGRITY_CHECK','commit':'a'*40}):
            with self.assertRaisesRegex(ValueError,'source changed'): host.identity(self.config,d.ROOT)
        self.config['python']=str(Path('/usr/bin/python3').resolve())
        with patch.object(d,'verify',return_value={'status':'HASHES_MATCH','commit':'a'*40}):
            with self.assertRaisesRegex(ValueError,'Base Python executable changed'): host.identity(self.config,d.ROOT)

    def test_command_environment_cannot_inherit_pip_python_or_proxy_overrides(self):
        result=type('Result',(),{'returncode':0,'stdout':b'{}'})()
        with patch.dict(os.environ,{'PIP_TARGET':'/bad','PIP_INDEX_URL':'https://bad.invalid','PYTHONPATH':'/bad','https_proxy':'bad'}), \
             patch.object(d.subprocess,'run',return_value=result) as command:
            d.Host().command(['/accepted/python','-I'],self.base)
        env=command.call_args.kwargs['env']
        self.assertEqual(command.call_args.kwargs['umask'],0o077)
        self.assertEqual(env,d.ENV); self.assertNotIn('PIP_TARGET',env); self.assertNotIn('https_proxy',env)
