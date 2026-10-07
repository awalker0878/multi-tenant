"""Candidate identity survives evidence commits, but changes with execution inputs."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from dossier import freeze
from evidence import Held


class Candidate(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Synthetic qualification")
        self.git("config", "user.email", "qualification@example.invalid")
        self.git("config", "core.filemode", "true")
        self.git("config", "commit.gpgsign", "false")
        self.write("deploy/build/components.json", '{"components":[{"id":"example"}]}')
        self.write("scripts/run.py", "print('candidate')\n")
        self.write("requirements-docs.txt", "PyYAML==6.0.3\n")
        self.write("release/p10-inputs.json", "{}\n")
        self.commit()

    def git(self, *args):
        return subprocess.check_output(
            ["git", *args], cwd=self.root, stderr=subprocess.STDOUT
        )

    def write(self, path, text):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def commit(self):
        self.git("add", ".")
        self.git("commit", "-qm", "Synthetic candidate fixture")

    def test_evidence_only_commit_preserves_candidate_and_records_new_provenance(self):
        before = freeze(self.root)
        self.write(
            "release/p10-inputs.json",
            json.dumps({"candidate_sha256": before["candidate_sha256"]}),
        )
        self.write("verification/p10/report.json", '{"synthetic":true}\n')
        self.commit()
        after = freeze(self.root)
        self.assertNotEqual(before["source_revision"], after["source_revision"])
        self.assertEqual(before["candidate_sha256"], after["candidate_sha256"])
        self.assertEqual(before["source_bindings"], after["source_bindings"])

    def test_source_tool_lock_and_executable_mode_changes_require_rerun(self):
        previous = freeze(self.root)
        for path, text in (
            ("scripts/run.py", "print('changed')\n"),
            ("requirements-docs.txt", "PyYAML==6.0.2\n"),
        ):
            self.write(path, text)
            self.commit()
            current = freeze(self.root)
            self.assertNotEqual(
                previous["candidate_sha256"], current["candidate_sha256"]
            )
            previous = current
        os.chmod(self.root / "scripts/run.py", 0o755)
        self.commit()
        current = freeze(self.root)
        self.assertNotEqual(previous["candidate_sha256"], current["candidate_sha256"])
        self.assertEqual(previous["source_bindings"], current["source_bindings"])

    def test_dirty_or_symlinked_source_cannot_freeze(self):
        self.write("scripts/run.py", "changed")
        with self.assertRaisesRegex(Held, "dirty"):
            freeze(self.root)
        (self.root / "scripts/run.py").unlink()
        (self.root / "scripts/run.py").symlink_to("../requirements-docs.txt")
        self.commit()
        with self.assertRaisesRegex(Held, "unsupported_candidate_source"):
            freeze(self.root)


if __name__ == "__main__":
    unittest.main()
