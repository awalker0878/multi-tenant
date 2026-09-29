"""Native credentials must not be exposed through inherited TLS key-log settings."""
import os
import ssl
import unittest
from unittest.mock import patch

from provisioner.controlplane.discovery import native_https
from tests.provisioning.discovery import test_ahv_https as native_fixture


class NativeTlsCustodyTests(unittest.TestCase):
    def setUp(self):
        self.native = native_fixture.AhvHttpsTests()
        self.native.setUp()
        self.addCleanup(self.native.doCleanups)

    def test_native_reads_ignore_keylog_environment_without_changing_it(self):
        path = self.native.root / 'not-an-authorized-key-log'
        with patch.dict(os.environ, {'SSLKEYLOGFILE': str(path)}):
            self.native.transport.collect()
            self.assertEqual(os.environ['SSLKEYLOGFILE'], str(path))
        self.assertEqual(len(self.native.calls), 2)
        self.assertFalse(path.exists(), 'Native read enabled unauthorized TLS session-key logging')

    def test_client_keeps_certificate_hostname_and_strict_chain_verification(self):
        contexts = []
        load = native_https.ssl.SSLContext.load_verify_locations
        def capture(context, *args, **kwargs):
            contexts.append(context)
            return load(context, *args, **kwargs)
        with patch.object(native_https.ssl.SSLContext, 'load_verify_locations', capture):
            self.native.transport.collect()
        self.assertEqual(len(contexts), 2)
        for context in contexts:
            self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
            self.assertTrue(context.check_hostname)
            self.assertTrue(context.verify_flags & ssl.VERIFY_X509_STRICT)
            self.assertTrue(context.verify_flags & ssl.VERIFY_X509_PARTIAL_CHAIN)
            self.assertGreaterEqual(context.minimum_version, ssl.TLSVersion.TLSv1_2)
            self.assertIsNone(context.keylog_filename)


if __name__ == '__main__':
    unittest.main()
