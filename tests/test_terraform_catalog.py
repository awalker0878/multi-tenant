import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.terraform_catalog import ROOT, entries


class TerraformCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / 'terraform', self.root / 'terraform',
                        ignore=shutil.ignore_patterns('.terraform'))

    def test_all_registered(self):
        self.assertTrue(entries(self.root))

    def test_unregistered_configuration_rejected(self):
        p = self.root / 'terraform/extra/main.tf.json'
        p.parent.mkdir()
        p.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'Unregistered'):
            entries(self.root)

    def test_wrong_module_rejected(self):
        row = entries(self.root)[0]
        p = self.root / row['root'] / 'main.tf.json'
        doc = json.loads(p.read_text())
        doc['module']['owned']['source'] = '../wrong'
        p.write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError, 'ownership mismatch'):
            entries(self.root)

    def test_duplicate_rejected(self):
        p = self.root / 'terraform/catalog.json'
        doc = json.loads(p.read_text())
        doc['entries'].append(doc['entries'][0])
        p.write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            entries(self.root)
