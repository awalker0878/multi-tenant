import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from verify_retained import verify_record


class RetainedEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.log = self.root / 'build.log'
        self.log.write_bytes(b'progress\rfinished\r\n')
        self.record = self.root / 'retrieval.json'
        self.write({'build.log': hashlib.sha256(self.log.read_bytes()).hexdigest()})

    def write(self, files):
        self.record.write_text(json.dumps({'retained_file_sha256': files}))

    def test_original_bytes_pass(self):
        self.assertEqual(verify_record(self.record)['files_verified'], 1)

    def test_text_mode_normalization_is_denied(self):
        self.log.write_text(self.log.read_text())
        with self.assertRaisesRegex(ValueError, 'retained_digest_mismatch'):
            verify_record(self.record)

    def test_missing_log_is_denied(self):
        self.log.unlink()
        with self.assertRaisesRegex(ValueError, 'missing_retained_file'):
            verify_record(self.record)

    def test_traversal_and_absolute_paths_are_denied(self):
        for path in ['../outside', '/tmp/outside', 'a/../build.log', 'a\\build.log']:
            with self.subTest(path=path):
                self.write({path: 'a' * 64})
                with self.assertRaisesRegex(ValueError, 'unsafe_evidence_path'):
                    verify_record(self.record)

    def test_symlink_is_denied_even_when_digest_matches(self):
        other = self.root / 'other'
        self.log.rename(other)
        self.log.symlink_to(other)
        with self.assertRaisesRegex(ValueError, 'symlinked_evidence_path'):
            verify_record(self.record)

    def test_empty_inventory_cannot_pass(self):
        self.write({})
        with self.assertRaisesRegex(ValueError, 'missing_retained_inventory'):
            verify_record(self.record)


if __name__ == '__main__':
    unittest.main()
