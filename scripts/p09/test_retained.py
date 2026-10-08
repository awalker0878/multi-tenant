"""The publication archive must preserve evidence sources without rewriting history."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from verify_any_to_any_retained import git, sha, source_object_store


class SourceHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source = self.root / 'source'
        source.mkdir()
        git(source, 'init', '--quiet', '--initial-branch=enhancement')
        git(source, 'config', 'user.name', 'Evidence fixture')
        git(source, 'config', 'user.email', 'evidence@example.invalid')
        (source / 'source.py').write_text('baseline\n')
        git(source, 'add', 'source.py')
        git(source, 'commit', '--quiet', '-m', 'baseline')
        baseline = git(source, 'rev-parse', 'HEAD')
        git(source, 'branch', 'baseline')
        (source / 'source.py').write_text('qualified source\n')
        git(source, 'commit', '--quiet', '-am', 'qualified source')
        self.revision = git(source, 'rev-parse', 'HEAD')
        self.tree = git(source, 'rev-parse', 'HEAD^{tree}')
        self.published = self.root / 'published'
        git(self.root, 'clone', '--quiet', '--no-local', '--single-branch', '--branch', 'baseline',
            str(source), str(self.published))
        self.evidence = self.root / 'evidence'
        self.evidence.mkdir()
        self.archive = self.evidence / 'source-history.bundle'
        git(source, 'bundle', 'create', str(self.archive), 'enhancement', '^' + baseline)
        self.manifest = {
            'schema_version': 1, 'archive': self.archive.name,
            'archive_sha256': sha(self.archive), 'prerequisite_commit': baseline,
            'archived_head': self.revision, 'archived_head_tree': self.tree,
            'commits': {self.revision: self.tree},
        }
        self.write_manifest()

    def write_manifest(self):
        (self.evidence / 'source-history.json').write_text(json.dumps(self.manifest))

    def test_missing_source_is_verified_without_changing_published_repository(self):
        with self.assertRaises(subprocess.CalledProcessError):
            git(self.published, 'cat-file', '-e', self.revision + '^{commit}')
        refs = git(self.published, 'show-ref')
        objects = sorted((self.published / '.git/objects').rglob('*'))
        with source_object_store(self.published, self.evidence, {self.revision}) as private:
            self.assertEqual(git(private, 'show', self.revision + ':source.py'), 'qualified source')
            self.assertNotEqual(private, self.published)
        self.assertEqual(git(self.published, 'show-ref'), refs)
        self.assertEqual(sorted((self.published / '.git/objects').rglob('*')), objects)
        with self.assertRaises(subprocess.CalledProcessError):
            git(self.published, 'cat-file', '-e', self.revision + '^{commit}')

    def test_changed_bundle_cannot_rebind_original_evidence(self):
        self.archive.write_bytes(self.archive.read_bytes() + b'changed')
        with self.assertRaisesRegex(ValueError, 'source_history_archive_digest_mismatch'):
            with source_object_store(self.published, self.evidence, {self.revision}):
                self.fail('changed archive accepted')

    def test_incorrect_recorded_source_tree_is_rejected(self):
        self.manifest['commits'][self.revision] = '1' * 40
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, 'source_history_commit_tree_mismatch'):
            with source_object_store(self.published, self.evidence, {self.revision}):
                self.fail('incorrect source tree accepted')


if __name__ == '__main__':
    unittest.main()
