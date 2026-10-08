"""Local TLS receiver exercise, explicitly not a real on-call acknowledgement."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "p01"))
from alert_delivery import deliver, fixture_receiver, observed_alert


class Operations(unittest.TestCase):
    def test_tls_delivery_acknowledges_exact_redacted_event_and_denies_bad_identity(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(
                [
                    "openssl",
                    "req",
                    "-x509",
                    "-newkey",
                    "rsa:2048",
                    "-nodes",
                    "-keyout",
                    str(root / "console.key"),
                    "-out",
                    str(root / "console.crt"),
                    "-days",
                    "1",
                    "-subj",
                    "/CN=localhost",
                    "-addext",
                    "subjectAltName=DNS:localhost",
                ],
                check=True,
                capture_output=True,
                timeout=15,
            )
            with fixture_receiver(root) as (endpoint, token, receipts):
                alert = observed_alert("lifecycle", "a" * 40)
                self.assertEqual(
                    deliver(endpoint, token, root / "console.crt", alert),
                    {"event_id": alert["event_id"], "acknowledged": True},
                )
                import urllib.error

                with self.assertRaises(urllib.error.HTTPError) as denied:
                    deliver(endpoint, "invalid", root / "console.crt", alert)
                self.assertEqual(denied.exception.code, 403)
                self.assertEqual(receipts, [alert])


if __name__ == "__main__":
    unittest.main()
