"""Actual independent Git fixture custody and isolated fixed owner launch."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from lab.run_protected_source_lab import clone_owned_checkout, environment
from lab.run_nft_edge_lab import owner_command
from provisioner.execution.source_integrity import _protected_checkout, verify


def git(root, *arguments):
    return subprocess.check_output(['git', '-C', str(root), *arguments], env=environment(),
                                   stderr=subprocess.PIPE, text=True, timeout=20).strip()


class ProtectedSourceFixtureTests(unittest.TestCase):
    @unittest.skipUnless(os.getuid() == os.geteuid() == 0, 'Root-controlled fixture adoption requires root')
    def test_clone_preserves_commit_and_independent_objects_under_actual_protected_custody(self):
        with tempfile.TemporaryDirectory(prefix='hosting-protected-test-', dir='/var/lib') as directory:
            base=Path(directory); base.chmod(0o755)
            source=base/'original'; source.mkdir(); git(source,'init','-q')
            git(source,'config','user.name','Synthetic fixture')
            git(source,'config','user.email','fixture@example.invalid')
            (source/'data.txt').write_bytes(b'accepted fixture bytes\n')
            git(source,'add','.'); git(source,'commit','-qm','fixture')
            destination=base/'accepted'
            commit=clone_owned_checkout(source,destination)
            self.assertTrue(_protected_checkout(destination))
            result=verify(destination)
            self.assertEqual((result['status'],result['commit']),('HASHES_MATCH',commit))
            self.assertEqual(commit,git(source,'rev-parse','HEAD'))
            self.assertEqual((destination/'data.txt').read_bytes(),(source/'data.txt').read_bytes())
            object_id=git(source,'hash-object','data.txt')
            relative=Path('.git/objects')/object_id[:2]/object_id[2:]
            original=source/relative; adopted=destination/relative
            self.assertNotEqual((original.stat().st_dev,original.stat().st_ino),
                                (adopted.stat().st_dev,adopted.stat().st_ino))
            original.chmod(0o644); original.write_bytes(b'changed original object')
            self.assertEqual(verify(destination)['status'],'HASHES_MATCH')
            (destination/'.git/config').chmod(0o666)
            self.assertFalse(_protected_checkout(destination))

    @unittest.skipUnless(os.getuid() == os.geteuid() == 0, 'Root-controlled fixture adoption requires root')
    def test_changed_source_is_held_before_a_clone_is_created(self):
        with tempfile.TemporaryDirectory(prefix='hosting-protected-test-', dir='/var/lib') as directory:
            source=Path(directory)/'original'; source.mkdir(); git(source,'init','-q')
            git(source,'config','user.name','Synthetic fixture')
            git(source,'config','user.email','fixture@example.invalid')
            (source/'data.txt').write_text('original'); git(source,'add','.'); git(source,'commit','-qm','fixture')
            (source/'data.txt').write_text('changed')
            destination=Path(directory)/'accepted'
            with self.assertRaisesRegex(RuntimeError,'exact clean committed source'):
                clone_owned_checkout(source,destination)
            self.assertFalse(destination.exists())

    def test_fixed_edge_package_commands_launch_isolated_without_checkout_bootstraps(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in ('nft_edge','edge_contain','edge_boot'):
                command=owner_command(name,'--help')
                self.assertEqual(command[1:3],['-I','-B'])
                result=subprocess.run(command,cwd=directory,env=environment(),stdin=subprocess.DEVNULL,
                                      stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=15)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertIn('usage:',result.stdout)
        with self.assertRaises(ValueError): owner_command('foreign','--help')


if __name__ == '__main__':
    unittest.main()
