"""Moving an owner into the package must not remove it from test evidence."""
from pathlib import Path
import hashlib
import tempfile
import unittest

from tools.check_local import source_snapshot

ROOT = Path(__file__).resolve().parents[1]


class RuntimeSourceCoverageTests(unittest.TestCase):
    def test_actual_runtime_and_build_owners_are_in_the_recorded_source_map(self):
        files = source_snapshot(ROOT)
        for name in ('provisioner/repository.py', 'provisioner/execution/terraform_catalog.py',
                     'provisioner/controlplane/discovery/review_intake.py', 'hosting_resources/__init__.py',
                     'pyproject.toml', 'setup.py', 'MANIFEST.in'):
            self.assertEqual(files[name], hashlib.sha256((ROOT/name).read_bytes()).hexdigest())
        self.assertEqual(files['tools/check_release.py'],
                         hashlib.sha256((ROOT/'tools/check_release.py').read_bytes()).hexdigest())
        self.assertNotIn('tools/terraform_catalog.py', files)
        self.assertFalse(any('__pycache__' in name or '/.terraform/' in name for name in files))

    def test_runtime_changes_affect_the_digest_map_without_a_git_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('pyproject.toml','setup.py','MANIFEST.in','.gitattributes','.gitignore','.editorconfig',
                         '.terraform-version','requirements-runtime.txt','requirements-test.txt',
                         'requirements-repository.txt','requirements-dev.txt','Makefile','sources/artifact_catalog.json'):
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'fixture')
            runtime=root/'provisioner/owner.py';runtime.parent.mkdir();runtime.write_bytes(b'before')
            before=source_snapshot(root)
            runtime.write_bytes(b'after')
            after=source_snapshot(root)
            self.assertNotEqual(before['provisioner/owner.py'],after['provisioner/owner.py'])
            self.assertEqual(after['provisioner/owner.py'],hashlib.sha256(b'after').hexdigest())
            self.assertFalse((root/'.git').exists())


if __name__=='__main__':
    unittest.main()
