"""Disposable Git/export source-integrity contracts; no native system access."""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from provisioner.execution import source_integrity as owner


def git(root, *args):
    env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=os.devnull)
    return subprocess.check_output(['git','-C',str(root),*args],env=env,stderr=subprocess.PIPE,timeout=20).decode().strip()


class SourceIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'checkout';self.root.mkdir();git(self.root,'init','-q')
        for key,value in (('user.name','Synthetic fixture'),('user.email','fixture@example.invalid'),('core.autocrlf','false')):
            git(self.root,'config',key,value)
        (self.root/'data').mkdir();(self.root/'data/binary.bin').write_bytes(bytes(range(256)))
        (self.root/'one.txt').write_bytes(b'original\n');(self.root/'.gitignore').write_text('ignored.tmp\n')
        git(self.root,'add','.');git(self.root,'commit','-qm','initial');self.commit=git(self.root,'rev-parse','HEAD')
        self.manifest=self.root.parent/'manifest.json'

    def snapshot(self,names=('one.txt','data/binary.bin')):
        doc={'file_sha256':{name:hashlib.sha256((self.root/name).read_bytes()).hexdigest() for name in names}}
        self.manifest.write_text(json.dumps(doc));return doc

    def test_clean_commit_and_ignored_output_pass_without_index_write(self):
        (self.root/'ignored.tmp').write_text('ignored');before=(self.root/'.git/index').read_bytes()
        result=owner.verify(self.root)
        self.assertEqual(result['status'],'HASHES_MATCH',result);self.assertEqual(result['commit'],self.commit)
        self.assertEqual((self.root/'.git/index').read_bytes(),before)

    def test_dirty_missing_untracked_and_staged_are_not_clean(self):
        (self.root/'one.txt').write_text('changed');(self.root/'data/binary.bin').unlink();(self.root/'new.txt').write_text('new')
        git(self.root,'add','one.txt');result=owner.verify(self.root)
        self.assertEqual(result['status'],'FAILED_INTEGRITY_CHECK')
        self.assertEqual({x['kind'] for x in result['issues']},{'WORKTREE_DIFFERS_FROM_HEAD','MISSING_TRACKED_FILE','UNTRACKED_SOURCE_FILE','INDEX_DIFFERS_FROM_HEAD'})

    def test_head_movement_is_detected_against_original_commit(self):
        original=owner._git;changed=False
        def moving(root,*args):
            nonlocal changed
            if args[0]=='ls-tree' and not changed:
                changed=True;git(root,'commit','--allow-empty','-qm','concurrent')
            return original(root,*args)
        with patch.object(owner,'_git',moving):result=owner.verify(self.root)
        self.assertEqual(result['commit'],self.commit);self.assertIn({'kind':'HEAD_CHANGED_DURING_CHECK'},result['issues'])

    def test_ambient_git_overrides_and_replace_refs_are_ignored(self):
        (self.root/'one.txt').write_text('replacement');git(self.root,'add','.');git(self.root,'commit','-qm','replacement')
        replacement=git(self.root,'rev-parse','HEAD');git(self.root,'update-ref','HEAD',self.commit);git(self.root,'replace',self.commit,replacement)
        with patch.dict(os.environ,{'GIT_DIR':str(self.root.parent/'wrong'),'GIT_WORK_TREE':str(self.root.parent)}):
            result=owner.verify(self.root)
        self.assertIn({'kind':'WORKTREE_DIFFERS_FROM_HEAD','file':'one.txt'},result['issues'])

    def test_external_fsmonitor_is_not_invoked(self):
        marker=self.root.parent/'unexpected';script=self.root.parent/'monitor.sh'
        script.write_text('#!/bin/sh\ntouch "'+str(marker)+'"\n');script.chmod(0o700);git(self.root,'config','core.fsmonitor',str(script))
        self.assertEqual(owner.verify(self.root)['status'],'HASHES_MATCH');self.assertFalse(marker.exists())

    def test_tracked_symlink_or_linked_ancestor_is_unsafe(self):
        for relative in ('one.txt','data'):
            path=self.root/relative;replacement=self.root.parent/(relative+'-actual');path.rename(replacement)
            try:
                path.symlink_to(replacement,target_is_directory=replacement.is_dir())
                self.assertEqual(owner.verify(self.root)['status'],'FAILED_INTEGRITY_CHECK')
            finally:
                path.unlink();replacement.rename(path)

    def test_snapshot_exact_manifest_and_unlisted_file_scope(self):
        self.snapshot();(self.root/'outside').write_text('unlisted')
        result=owner.verify_snapshot(self.root,self.manifest)
        self.assertEqual(result['status'],'HASHES_MATCH');self.assertEqual(result['files_checked'],2);self.assertNotIn('commit',result)

    def test_snapshot_changed_missing_and_unsafe_paths_fail(self):
        self.snapshot();(self.root/'one.txt').write_text('changed');(self.root/'data/binary.bin').unlink()
        result=owner.verify_snapshot(self.root,self.manifest)
        self.assertEqual({x['kind'] for x in result['issues']},{'DIGEST_MISMATCH','MISSING_FILE'})
        digest=hashlib.sha256(b'original\n').hexdigest()
        for name in ('../one','./one.txt','/one.txt','data/../one.txt','data\\x','.git/config','C:/one'):
            self.manifest.write_text(json.dumps({'file_sha256':{name:digest}}))
            self.assertEqual(owner.verify_snapshot(self.root,self.manifest)['status'],'FAILED_INTEGRITY_CHECK')

    def test_snapshot_duplicate_nonfinite_bad_digest_and_extra_fields_fail(self):
        for raw in (b'{"file_sha256":{"one.txt":"a","one.txt":"b"}}',b'{"file_sha256":{},"x":NaN}',b'[]',b'{}'):
            self.manifest.write_bytes(raw);self.assertEqual(owner.verify_snapshot(self.root,self.manifest)['status'],'FAILED_INTEGRITY_CHECK')
        self.manifest.write_text(json.dumps({'file_sha256':{'one.txt':'A'*64}}));self.assertEqual(owner.verify_snapshot(self.root,self.manifest)['status'],'FAILED_INTEGRITY_CHECK')

    def test_file_and_manifest_bounds_fail_closed(self):
        self.snapshot()
        with patch.object(owner,'MAX_FILE_BYTES',8):
            self.assertNotEqual(owner.verify(self.root)['status'],'HASHES_MATCH');self.assertNotEqual(owner.verify_snapshot(self.root,self.manifest)['status'],'HASHES_MATCH')
        with patch.object(owner,'MAX_MANIFEST_BYTES',4):self.assertEqual(owner.verify_snapshot(self.root,self.manifest)['status'],'FAILED_INTEGRITY_CHECK')

    def test_no_checkout_wrong_root_and_git_failure_never_fall_back(self):
        for root in (None,self.root/'data',self.root.parent):self.assertEqual(owner.verify(root)['status'],'BLOCKED_NO_CURRENT_CHECKOUT')
        with patch.object(owner.subprocess,'check_output',side_effect=subprocess.TimeoutExpired('git',60)):
            self.assertEqual(owner.verify(self.root)['status'],'BLOCKED_NO_CURRENT_CHECKOUT')

    def test_cli_accepts_explicit_checkout_and_snapshot(self):
        output=io.StringIO()
        with redirect_stdout(output):code=owner.main(['--root',str(self.root)])
        self.assertEqual(code,0);self.assertEqual(json.loads(output.getvalue())['commit'],self.commit)
        self.snapshot();output=io.StringIO()
        with redirect_stdout(output):code=owner.main(['--root',str(self.root),'--manifest',str(self.manifest)])
        self.assertEqual(code,0);self.assertNotIn('commit',json.loads(output.getvalue()))

    def test_old_module_is_absent_and_runtime_consumers_use_owner(self):
        import importlib.util
        from provisioner import repository
        from tools import terraform_run,terraform_apply,state_export,vsphere_power
        self.assertIsNone(importlib.util.find_spec('tools.check_release'))
        for module in (terraform_run,terraform_apply,state_export,vsphere_power):self.assertIs(module.verify,owner.verify)
        self.assertEqual(repository.source_commit(self.root)['commit'],self.commit)


if __name__=='__main__':unittest.main()
