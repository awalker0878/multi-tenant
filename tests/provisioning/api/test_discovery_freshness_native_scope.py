"""Native scope text follows EnvironmentDeclaration, not a logical-ID regex."""
import json
import unittest

from tests.provisioning.api.test_discovery_freshness_cli import report, run


class FreshnessNativeScopeTests(unittest.TestCase):
    def test_native_scope_preserves_paths_unicode_and_the_full_environment_bound(self):
        for native_scope in ('/Datacenter/vm/team', 'Cluster café / finance', 's'*512, ' padded scope '):
            with self.subTest(native_scope=native_scope):
                value = report()
                value['scope']['native_scope_id'] = native_scope
                code, out, err, calls = run(value, check=True)
                self.assertEqual((code, err, len(calls)), (0, '', 1))
                self.assertEqual(json.loads(out)['scope']['native_scope_id'], native_scope)

    def test_native_scope_rejects_empty_oversized_and_control_character_values(self):
        for native_scope in ('', '   ', 's'*513, 'scope\n', 'scope\x7f', None, [], 1):
            with self.subTest(native_scope=native_scope):
                value = report()
                value['scope']['native_scope_id'] = native_scope
                code, out, err, calls = run(value, check=True)
                self.assertEqual((code, out, len(calls)), (3, '', 1))
                self.assertEqual(json.loads(err)['error'], 'DISCOVERY_FRESHNESS_RESPONSE_INVALID')
