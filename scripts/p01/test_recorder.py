"""Verify failure evidence and binary log integrity for the CI recorder."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location("p01_recorder", Path(__file__).with_name("run_quality.py"))
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RecorderTest(unittest.TestCase):
    def evidence(self, root):
        return MODULE.Evidence(root, {"commands": [], "checks": []})

    def test_stdout_and_stderr_preserve_exact_bytes_and_hashes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            recorder = self.evidence(root)
            stdout = recorder.run("bytes", [sys.executable, "-c", "import os; os.write(1,b'a\\r\\nb\\xff'); os.write(2,b'problem\\r')"], root)
            self.assertEqual(stdout, b"a\r\nb\xff")
            command = json.loads((root / "evidence/report.json").read_text())["commands"][0]
            self.assertEqual(command["stdout_sha256"], hashlib.sha256(stdout).hexdigest())
            self.assertEqual((root / "evidence" / command["stderr"]).read_bytes(), b"problem\r")

    def test_expected_negative_exit_is_distinct_from_unexpected_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            recorder = self.evidence(root)
            recorder.run("negative", [sys.executable, "-c", "raise SystemExit(2)"], root, expected=2)
            with self.assertRaises(RuntimeError):
                recorder.run("failure", [sys.executable, "-c", "raise SystemExit(2)"], root)
            commands = json.loads((root / "evidence/report.json").read_text())["commands"]
            self.assertTrue(commands[0]["passed"])
            self.assertFalse(commands[1]["passed"])

    def test_timeout_cannot_be_accepted_as_an_expected_exit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            recorder = self.evidence(root)
            with self.assertRaises(RuntimeError):
                recorder.run("timeout", [sys.executable, "-c", "import time; time.sleep(30)"], root, expected=124, timeout=0.05)
            command = json.loads((root / "evidence/report.json").read_text())["commands"][0]
            self.assertTrue(command["timed_out"])
            self.assertFalse(command["passed"])
            self.assertEqual(command["exit_code"], 124)


if __name__ == "__main__":
    unittest.main()
