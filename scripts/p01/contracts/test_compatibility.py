"""Git-backed tests for active-only canonical files and immutable survivors."""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from compatibility import check, compare

PATH = "contracts/openapi/current-v1.json"
NEW = "contracts/openapi/current-v2.json"


class ActiveContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Contract fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.write(PATH, "{}\n")
        self.registry([PATH])
        self.base = self.commit()

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, check=True,
                              capture_output=True, text=True).stdout.strip()

    def write(self, path, content):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)

    def registry(self, paths):
        self.write("architecture/contract-consumers.json",
                   __import__("json").dumps({"active_releases": [
                       {"path": path} for path in paths
                   ]}))

    def commit(self):
        self.git("add", "-A")
        self.git("commit", "-m", "Current contract snapshot")
        return self.git("rev-parse", "HEAD")

    def test_existing_published_version_is_immutable(self):
        self.assertEqual(compare({"a": b"one"}, {"a": b"one"}), [])
        self.write(PATH, '{"altered":true}\n')
        with self.assertRaisesRegex(ValueError, "Active published contract removed or changed"):
            check(self.root, self.base)

    def test_new_canonical_version_is_explicit(self):
        self.write(NEW, "{}\n")
        self.registry([PATH, NEW])
        self.assertEqual(check(self.root, self.base)["added"], [NEW])

    def test_registered_file_cannot_be_absent(self):
        (self.root / PATH).unlink()
        with self.assertRaisesRegex(ValueError, "Canonical inventory does not match"):
            check(self.root, self.base)

    def test_orphan_canonical_file_is_rejected(self):
        self.write(NEW, "{}\n")
        with self.assertRaisesRegex(ValueError, "Canonical inventory does not match"):
            check(self.root, self.base)

    def test_remove_unused_version_without_storing_archive_or_shim(self):
        self.registry([])
        (self.root / PATH).unlink()
        report = check(self.root, self.base)
        self.assertEqual(report["removed"], [PATH])
        self.assertEqual(report["checked_active_releases"], 0)

    def test_base_revision_must_exist(self):
        with self.assertRaisesRegex(ValueError, "explicit existing base"):
            check(self.root, "0" * 40)


if __name__ == "__main__":
    unittest.main()
