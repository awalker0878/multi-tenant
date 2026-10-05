"""Breaking/additive changes must not mutate an already published artifact."""
import unittest

from compatibility import compare


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


if __name__ == '__main__':
    unittest.main()
