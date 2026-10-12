"""Negative tests for current active-release immutability, without history replay."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from compatibility import check, compare


class ActiveContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Contract test")
        self.git("config", "user.email", "contracts@example.invalid")
        self.write("contracts/openapi/current-v1.json", "{}\n")
        self.registry(["contracts/openapi/current-v1.json"])
        self.retirement([])
        self.base = self.commit()

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, check=True,
                              capture_output=True, text=True).stdout.strip()

    def write(self, path, value):
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(value)

    def registry(self, paths):
        self.write("architecture/contract-consumers.json",
                   json.dumps({"active_releases": [{"path": p} for p in paths]}))

    def retirement(self, paths):
        self.write("architecture/retired-contract-releases.json",
                   json.dumps({"retired": paths}))

    def commit(self):
        self.git("add", ".")
        self.git("commit", "-m", "Snapshot active release")
        return self.git("rev-parse", "HEAD")

    def test_exact_active_bytes_are_immutable(self):
        self.assertEqual(compare({"a": b"one"}, {"a": b"one"}), [])
        self.write("contracts/openapi/current-v1.json", '{"added":true}\n')
        with self.assertRaisesRegex(ValueError, "Active published contract removed or changed"):
            check(self.root, self.base)

    def test_new_current_version_can_be_added(self):
        other = "contracts/openapi/current-v2.json"
        self.write(other, "{}\n")
        self.registry(["contracts/openapi/current-v1.json", other])
        result = check(self.root, self.base)
        self.assertEqual(result["added"], [other])
        self.assertEqual(result["checked_active_releases"], 2)

    def test_missing_current_release_is_rejected(self):
        (self.root / "contracts/openapi/current-v1.json").unlink()
        with self.assertRaisesRegex(ValueError, "Active canonical missing"):
            check(self.root, self.base)

    def test_retirement_requires_active_registry_removal(self):
        path = "contracts/openapi/current-v1.json"
        self.retirement([path])
        with self.assertRaisesRegex(ValueError, "Active contract cannot be retired"):
            check(self.root, self.base)
        self.registry([])
        (self.root / path).unlink()
        self.assertEqual(check(self.root, self.base)["retired"], [path])

    def test_invalid_base_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "explicit existing base"):
            check(self.root, "0" * 40)


if __name__ == "__main__":
    unittest.main()
