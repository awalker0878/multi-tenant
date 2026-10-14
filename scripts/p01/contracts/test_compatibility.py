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
        self.write("architecture/installed-contract-usage.json", '{"copies": []}\n')
        self.base = self.commit()

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, check=True,
                              capture_output=True, text=True).stdout.strip()

    def write(self, path, content):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)

    def registry(self, paths, *, consumers=None, copies=None, depends_on=None):
        self.write("architecture/contract-consumers.json",
                   __import__("json").dumps({"active_releases": [
                       {"path": path, "owner": "inventory",
                        "consumers": consumers or [], "copies": copies or [],
                        "depends_on": depends_on or []} for path in paths
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

    def test_retirement_blocked_by_prior_declared_consumer(self):
        self.registry([PATH], consumers=["planning"])
        self.write("services/planning/src/planning/reader.py",
                   'CONTRACT = "' + PATH + '"\n')
        self.base = self.commit()
        self.registry([])
        (self.root / PATH).unlink()
        with self.assertRaisesRegex(ValueError, "current reference services/planning"):
            check(self.root, self.base)

    def test_retirement_blocked_by_prior_installed_copy(self):
        self.registry([PATH], copies=["services/inventory/resources/contracts/current-v1.json"])
        self.write("services/inventory/resources/contracts/current-v1.json", "{}\n")
        self.base = self.commit()
        self.registry([])
        (self.root / PATH).unlink()
        with self.assertRaisesRegex(ValueError, "installed copies"):
            check(self.root, self.base)

    def test_retirement_blocked_by_prior_dependent_release(self):
        self.registry([PATH, NEW], depends_on=[PATH])
        self.write(NEW, '{"$ref":"current-v1.json"}\n')
        self.base = self.commit()
        self.registry([NEW])
        (self.root / PATH).unlink()
        with self.assertRaisesRegex(ValueError, "dependent releases"):
            check(self.root, self.base)

    def test_retirement_blocked_by_prior_runtime_registration(self):
        self.write("architecture/installed-contract-usage.json",
                   '{"copies": [{"canonical": "' + PATH + '"}]}\n')
        self.base = self.commit()
        self.registry([])
        (self.root / PATH).unlink()
        with self.assertRaisesRegex(ValueError, "current reference architecture/installed-contract-usage"):
            check(self.root, self.base)

    def test_retirement_allowed_after_real_consumer_copy_and_loader_removal(self):
        copy = "services/planning/src/planning/infrastructure/inputs/current-v1.json"
        loader = "services/planning/src/planning/reader.py"
        self.registry([PATH], consumers=["planning"], copies=[copy])
        self.write(copy, "{}\n")
        self.write(loader, 'NAME = "current-v1"\n')
        self.write("architecture/installed-contract-usage.json",
                   '{"copies": [{"canonical": "' + PATH + '", "copy": "' + copy + '"}]}\n')
        self.base = self.commit()
        self.registry([])
        self.write("architecture/installed-contract-usage.json", '{"copies": []}\n')
        for path in (PATH, copy, loader):
            (self.root / path).unlink()
        self.assertEqual(check(self.root, self.base)["removed"], [PATH])

    def test_simultaneous_deletion_does_not_hide_surviving_typed_loader(self):
        copy = "services/planning/src/planning/infrastructure/inputs/current-v1.json"
        self.registry([PATH], consumers=["planning"], copies=[copy])
        self.write(copy, "{}\n")
        self.write("services/planning/src/planning/reader.py", 'NAME = "current-v1"\n')
        self.base = self.commit()
        self.registry([])
        (self.root / PATH).unlink()
        (self.root / copy).unlink()
        with self.assertRaisesRegex(ValueError, "current reference services/planning"):
            check(self.root, self.base)

    def test_removal_allowed_with_prior_consumer_after_verified_migration(self):
        self.registry([PATH], consumers=["planning"])
        self.write("services/planning/src/planning/reader.py", 'CONTRACT = "' + PATH + '"\n')
        self.base = self.commit()
        self.registry([NEW], consumers=["planning"])
        self.write(NEW, "{}\n")
        self.write("services/planning/src/planning/reader.py", 'CONTRACT = "' + NEW + '"\n')
        (self.root / PATH).unlink()
        self.assertEqual(check(self.root, self.base)["removed"], [PATH])

    def test_unregistered_prior_uri_reference_survives_registry_deletion(self):
        self.write(PATH, '{"$id":"urn:current:v1","type":"object"}\n')
        self.write(NEW, '{"$ref":"urn:current:v1"}\n')
        self.registry([PATH, NEW])
        self.base = self.commit()
        self.registry([NEW])
        (self.root / PATH).unlink()
        with self.assertRaisesRegex(ValueError, "dependent canonical identity"):
            check(self.root, self.base)

    def test_base_revision_must_exist(self):
        with self.assertRaisesRegex(ValueError, "explicit existing base"):
            check(self.root, "0" * 40)


if __name__ == "__main__":
    unittest.main()
