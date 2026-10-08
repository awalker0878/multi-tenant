"""Exercise failure evidence and teardown without Docker or real credentials."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from run_local import Campaign, SERVICES


class LocalCampaignTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        parent = Path(self.directory.name)
        self.root = parent / "source"
        self.root.mkdir()
        self.output = parent / "evidence"
        self.revision = "a" * 40

    def campaign(self):
        campaign = Campaign(self.root, self.output, self.revision)
        self.addCleanup(shutil.rmtree, campaign.runtime.parent, True)
        campaign.runtime.mkdir()
        campaign.compose = campaign.runtime / "compose.json"
        campaign.compose.write_text("{}\n")
        return campaign

    def test_timeout_retains_exact_bytes_and_cannot_satisfy_expected_124(self):
        campaign = self.campaign()
        stdout, stderr = b"partial\r\n\xff", b"diagnostic\r\x00"
        failure = subprocess.TimeoutExpired(["bounded-command"], 1, output=stdout, stderr=stderr)
        with patch("run_local.subprocess.run", side_effect=failure):
            with self.assertRaises(RuntimeError):
                campaign.command("timeout", ["bounded-command"], expected=124, timeout=1)
        report = json.loads((self.output / "report.json").read_text())
        command = report["commands"][0]
        self.assertTrue(command["timed_out"])
        self.assertEqual(command["exit_code"], 124)
        self.assertEqual(command["expected_exit"], 124)
        self.assertEqual((self.output / command["stdout"]["path"]).read_bytes(), stdout)
        self.assertTrue((self.output / command["stderr"]["path"]).read_bytes().startswith(stderr))
        for stream in ("stdout", "stderr"):
            raw = (self.output / command[stream]["path"]).read_bytes()
            self.assertEqual(command[stream]["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(command[stream]["bytes"], len(raw))

    def test_failed_log_capture_still_tears_down_project(self):
        campaign = self.campaign()
        with patch.object(campaign, "command", side_effect=[RuntimeError("log timeout"), b""]) as command:
            campaign.cleanup(keep=False)
        self.assertEqual([call.args[0] for call in command.call_args_list],
                         ["container-logs", "remove-isolated-project"])
        teardown = command.call_args_list[1]
        self.assertEqual(teardown.args[1][-3:], ["down", "--volumes", "--remove-orphans"])
        self.assertNotIn("expected", teardown.kwargs)
        self.assertTrue(campaign.report["container_log_capture_failed"])
        self.assertTrue(campaign.report["cleanup_complete"])
        self.assertFalse(campaign.runtime.parent.exists())

    def test_failed_teardown_preserves_recovery_files_and_rejects_pass(self):
        campaign = self.campaign()
        campaign.report["result"] = "PASS"
        with patch.object(campaign, "command", side_effect=[b"logs", RuntimeError("down failed")]):
            with self.assertRaises(RuntimeError):
                campaign.cleanup(keep=False)
        report = json.loads((self.output / "report.json").read_text())
        self.assertEqual(report["result"], "FAIL")
        self.assertFalse(report["cleanup_complete"])
        self.assertEqual(report["cleanup_runtime_preserved"], str(campaign.runtime))
        self.assertTrue(campaign.compose.is_file())

    def test_evidence_inside_workspace_rejected_before_creating_files(self):
        with patch("run_local.tempfile.mkdtemp") as temporary:
            for destination in (self.root, self.root / "evidence"):
                with self.subTest(destination=destination), self.assertRaises(ValueError):
                    Campaign(self.root, destination, self.revision)
            temporary.assert_not_called()
        self.assertFalse((self.root / "evidence").exists())

    def test_unowned_supplied_images_rejected_before_preparing_installation(self):
        campaign = self.campaign()
        images = {service: "sha256:" + "b" * 64 for service in SERVICES}
        images_file = Path(self.directory.name) / "images.json"
        images_file.write_text(json.dumps(images))
        for defect in ("revision", "component", "platform"):
            with self.subTest(defect=defect):
                labels = {"org.opencontainers.image.revision": self.revision,
                          "io.product.component": "console"}
                architecture = "amd64"
                if defect == "revision":
                    labels["org.opencontainers.image.revision"] = "c" * 40
                elif defect == "component":
                    labels["io.product.component"] = "governance"
                else:
                    architecture = "arm64"
                inspection = " ".join(json.dumps(field) for field in
                                      (images["console"], "linux", architecture, labels)).encode()
                with patch.object(campaign, "command", side_effect=[self.revision.encode(), b"", inspection]):
                    with patch("run_local.prepare") as prepare:
                        with self.assertRaisesRegex(RuntimeError, "owned-image-source-and-platform"):
                            campaign.run(images_file)
                        prepare.assert_not_called()


if __name__ == "__main__":
    unittest.main()
