"""Fail closed on synthetic cluster evidence, policy ambiguity and cleanup failure."""

import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from run_kubernetes import KubernetesCampaign, image_identity


class KubernetesCampaignTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        parent = Path(self.directory.name)
        self.root = parent / "source"
        self.root.mkdir()
        self.revision = "a" * 40
        self.campaign = KubernetesCampaign(self.root, parent / "evidence", self.revision)
        self.addCleanup(shutil.rmtree, self.campaign.runtime.parent, True)

    def test_image_source_owner_platform_and_shape_are_checked(self):
        image = "sha256:" + "b" * 64
        labels = {"org.opencontainers.image.revision": self.revision, "io.product.component": "planning"}
        valid = [image, "linux", "amd64", labels]
        encode = lambda values: " ".join(json.dumps(value) for value in values).encode()
        self.assertEqual(image_identity(encode(valid), image, "planning", self.revision)["image_id"], image)
        for values in ([image, "linux", "arm64", labels], valid[:3], [image, "linux", "amd64", None]):
            with self.subTest(values=values), self.assertRaises(ValueError):
                image_identity(encode(values), image, "planning", self.revision)
        with self.assertRaises(ValueError):
            image_identity(encode(valid), image, "inventory", self.revision)
        with self.assertRaises(ValueError):
            image_identity(encode(valid), image, "planning", "c" * 40)

    def test_download_mismatch_cannot_execute_or_be_accepted(self):
        with patch("run_kubernetes.urllib.request.urlopen", return_value=io.BytesIO(b"tampered executable")):
            with self.assertRaisesRegex(RuntimeError, "artifact-integrity"):
                self.campaign.download("kind", "https://example.invalid/kind", "https://example.invalid/checksum", "0" * 64)
        self.assertEqual(self.campaign.report["tool_artifacts"], [])
        self.assertFalse((self.campaign.tools / "kind").stat().st_mode & 0o111)

    def test_policy_denial_requires_timeout_not_dns_or_connection_failure(self):
        for result in ({"outcome": "connected"}, {"outcome": "error", "error_type": "gaierror"},
                       {"outcome": "error", "error_type": "ConnectionRefusedError"}):
            with self.subTest(result=result), patch.object(self.campaign, "exec", return_value=json.dumps(result).encode()):
                with self.assertRaisesRegex(RuntimeError, "cilium-deny"):
                    self.campaign.network_check("planning", "10.0.0.2", 8443, False)
        with patch.object(self.campaign, "exec", return_value=b'{"outcome":"timeout"}'):
            self.campaign.network_check("planning", "10.0.0.2", 8443, False)

    def test_cleanup_still_deletes_owned_cluster_after_log_failure(self):
        self.campaign.cluster_attempted = True
        calls = []

        def command(name, argv, **kwargs):
            calls.append((name, argv))
            if name.startswith("container-logs-"):
                raise RuntimeError("logs unavailable")
            return b""

        with patch.object(self.campaign, "command", side_effect=command):
            self.campaign.cleanup(keep=False)
        self.assertEqual(calls[-1], ("delete-owned-kind-cluster", [str(self.campaign.tools / "kind"), "delete", "cluster", "--name", self.campaign.cluster]))
        self.assertTrue(self.campaign.report["cleanup_complete"])
        self.assertFalse(self.campaign.runtime.parent.exists())

    def test_failed_cluster_deletion_preserves_recovery_and_marks_fail(self):
        self.campaign.cluster_attempted = True
        self.campaign.report["result"] = "PASS"

        def command(name, argv, **kwargs):
            if name == "delete-owned-kind-cluster":
                raise RuntimeError("delete failed")
            return b""

        with patch.object(self.campaign, "command", side_effect=command):
            with self.assertRaises(RuntimeError):
                self.campaign.cleanup(keep=False)
        self.assertEqual(self.campaign.report["result"], "FAIL")
        self.assertFalse(self.campaign.report["cleanup_complete"])
        self.assertTrue(self.campaign.runtime.parent.exists())

    def test_cluster_commands_cannot_inherit_user_kubeconfig_or_namespace(self):
        argv = self.campaign.k("get", "pods")
        self.assertEqual(argv[:5], [str(self.campaign.tools / "kubectl"), "--kubeconfig", str(self.campaign.kubeconfig), "--namespace", self.campaign.namespace])
        self.assertEqual(self.campaign.k("get", "pods", namespace="kube-system")[4], "kube-system")


if __name__ == "__main__":
    unittest.main()
