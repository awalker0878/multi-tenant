"""Ambiguous canonical, registry, source and evidence documents must fail closed."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts/contracts'))
from contract_io import loads


class ContractDocumentTests(unittest.TestCase):
    def test_duplicate_json_and_yaml_authority_fields_are_rejected(self):
        for source, yaml in [(' {"owner":"inventory","owner":"planning"}', False),
                             ('{"scope":{"tenant":"one","tenant":"two"}}', False),
                             ('owner: inventory\nowner: planning\n', True),
                             ('scope:\n  tenant: one\n  tenant: two\n', True),
                             ('scope: {<<: {tenant: one}, tenant: two}', True)]:
            with self.subTest(source=source), self.assertRaisesRegex(ValueError, 'Duplicate'):
                loads(source, yaml_document=yaml)

    def test_non_json_numbers_keys_and_yaml_scalars_are_rejected(self):
        for source, yaml in [('{"expiry":NaN}', False), ('{"expiry":Infinity}', False),
                             ('{"expiry":1e999}', False), ('expiry: .nan', True),
                             ('expiry: .inf', True), ('1: owner', True),
                             ('expiry: 2026-10-16', True)]:
            with self.subTest(source=source), self.assertRaises(ValueError):
                loads(source, yaml_document=yaml)

    def test_recursive_yaml_and_non_scalar_mapping_keys_are_rejected(self):
        for source in ['scope: &scope [*scope]', '? [owner, consumer]\n: planning']:
            with self.subTest(source=source), self.assertRaises(ValueError):
                loads(source, yaml_document=True)

    def test_json_and_yaml_preserve_equivalent_closed_document_values(self):
        expected = {'owner': 'planning', 'claims': ['producer', 'consumer'], 'expiry': 123, 'active': True, 'context': None}
        self.assertEqual(loads('{"owner":"planning","claims":["producer","consumer"],"expiry":123,"active":true,"context":null}'), expected)
        self.assertEqual(loads('owner: planning\nclaims: [producer, consumer]\nexpiry: 123\nactive: true\ncontext: null', yaml_document=True), expected)
