import json
import unittest

from scripts.build_wsd_compositions import ROOT, rendered
from tools.terraform_catalog import entries
from tools.verify_terraform import plan_only_mock_tests


class WsdCompositionsTests(unittest.TestCase):
    def test_interfaces_regenerate_exactly(self):
        for name, expected in rendered().items():
            with self.subTest(path=name):
                self.assertEqual((ROOT / name).read_text(), expected)

    def test_separate_phases_keep_native_provider_and_lifecycle_guards(self):
        for row in entries():
            if row['kind'] != 'composition':
                continue
            with self.subTest(scope=row['id']):
                directory = ROOT / row['module']
                doc = json.loads((directory / 'main.tf.json').read_text())
                self.assertNotIn('backend', doc['terraform'])
                self.assertNotIn('provider', doc)
                self.assertFalse(doc['variable']['allow_restricted_build']['default'])
                child = doc['module']['member']
                self.assertEqual(child['for_each'], '${var.members}')
                native = json.loads((directory / child['source'] / 'main.tf.json').read_text())
                self.assertEqual(set(child) - {'source', 'for_each'}, set(native['variable']))
                self.assertTrue(plan_only_mock_tests(directory))
