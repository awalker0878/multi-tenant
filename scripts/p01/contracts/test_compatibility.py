"""Breaking/additive changes must not mutate an already published artifact."""
import unittest
from pathlib import Path
import subprocess
import tempfile

from compatibility import check, compare


class PublishedContractTests(unittest.TestCase):
    def test_preserves_existing_and_accepts_new_version(self):
        self.assertEqual(compare({'v1.json': b'original'},
                                 {'v1.json': b'original', 'v2.json': b'new'}), [])

    def test_rejects_removed_version(self):
        self.assertEqual(compare({'v1.json': b'original'}, {}), ['v1.json'])

    def test_rejects_in_place_mutations_including_apparently_additive(self):
        for changed in (b'{"enum":["old","new"]}', b'{"required":[]}',
                        b'{"additionalProperties":true}', b'changed channel or auth'):
            with self.subTest(changed=changed):
                self.assertEqual(compare({'v1.json': b'original'}, {'v1.json': changed}), ['v1.json'])


class PublishedHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'repository'
        self.root.mkdir()
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Contract fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.write('README.md', 'Synthetic contract history\n')
        self.commit('Initial repository')

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.root, check=True,
                              capture_output=True, text=True).stdout.strip()

    def write(self, path, value):
        destination = self.root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(value)

    def commit(self, message):
        self.git('add', '.')
        self.git('commit', '-m', message)
        return self.git('rev-parse', 'HEAD')

    def test_prior_corruption_cannot_reset_published_bytes_and_restoration_is_allowed(self):
        path = 'contracts/example-v1.json'
        self.write(path, '{"frozen":true}\n')
        published = self.commit('Publish v1')
        self.write(path, '{"mutated":true}\n')
        corrupted = self.commit('Historical invalid mutation')
        with self.assertRaisesRegex(ValueError, 'Published contract removed or changed'):
            check(self.root, corrupted)
        self.write(path, '{"frozen":true}\n')
        self.write('contracts/example-v1.1.json', '{"mutated":true}\n')
        result = check(self.root, corrupted)
        self.assertEqual(result['published_revisions'][path], published)
        self.assertEqual(result['added'], ['contracts/example-v1.1.json'])

    def test_source_fragments_and_duplicated_fixtures_are_not_frozen_releases(self):
        self.write("contracts/fixtures/planning/old-example.json", '{"case":1}\\n')
        self.write("contracts/source/example/base.json", '{"draft":true}\\n')
        published = self.commit("Add editable contract inputs")
        self.write("contracts/fixtures/planning/old-example.json", '{"case":2}\\n')
        (self.root / "contracts/source/example/base.json").unlink()
        self.assertEqual(check(self.root, published)["conflicts"], [])

    def test_merge_publishes_final_side_branch_bytes(self):
        self.git('checkout', '-b', 'draft')
        self.write('contracts/example-v1.json', '{"draft":true}\n')
        self.commit('Unpublished draft')
        self.write('contracts/example-v1.json', '{"published":true}\n')
        self.commit('Finalize draft')
        self.git('checkout', 'main')
        self.git('merge', '--no-ff', 'draft', '-m', 'Publish version')
        published = self.git('rev-parse', 'HEAD')
        result = check(self.root, published)
        self.assertEqual(result['published_revisions']['contracts/example-v1.json'], published)

    def test_deletion_rename_and_readdition_cannot_hide_original(self):
        path = 'contracts/a space-v1.json'
        self.write(path, 'original\n')
        self.commit('Publish v1')
        self.git('mv', path, 'contracts/renamed-v1.json')
        renamed = self.commit('Move published artifact')
        with self.assertRaisesRegex(ValueError, 'a space-v1.json'):
            check(self.root, renamed)
        self.write(path, 'replacement\n')
        readded = self.commit('Readd changed artifact')
        with self.assertRaisesRegex(ValueError, 'a space-v1.json'):
            check(self.root, readded)
        self.write(path, 'original\n')
        self.assertEqual(check(self.root, readded)['conflicts'], [])

    def test_shallow_and_missing_parent_history_fail_explicitly(self):
        self.write('contracts/example-v1.json', '{}\n')
        published = self.commit('Publish v1')
        shallow = Path(self.temp.name) / 'shallow'
        self.git('clone', '--depth=1', self.root.as_uri(), str(shallow))
        with self.assertRaisesRegex(ValueError, 'Complete Git history.*shallow'):
            check(shallow, published)
        parent = self.git('rev-parse', 'HEAD^')
        (self.root / '.git/objects' / parent[:2] / parent[2:]).unlink()
        with self.assertRaisesRegex(ValueError, 'Complete Git history'):
            check(self.root, published)


if __name__ == '__main__':
    unittest.main()
