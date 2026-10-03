"""Regressions that keep generated catalogues and indexes host-independent.

Generated repository-relative paths are committed bytes. A host that prints native
separators or sorts case-insensitively must not be able to rewrite a committed
catalogue, so each generator is asserted on the representation and the order it
produces rather than on the host's own path behaviour.
"""
from __future__ import annotations
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))

from scripts.catalog_artifacts import collect
from provisioner.execution.terraform_catalog import entries


def relative_paths(value):
    """Every repository-relative path string inside a nested catalogue value."""
    if isinstance(value, str):
        return [value] if '/' in value or '\\' in value else []
    if isinstance(value, dict):
        return [p for item in value.values() for p in relative_paths(item)]
    if isinstance(value, list):
        return [p for item in value for p in relative_paths(item)]
    return []


class GeneratedPathTests(unittest.TestCase):
    def test_artifact_catalogue_is_posix_ordered(self):
        rows = collect(ROOT)
        committed = json.loads((ROOT / 'sources/artifact_catalog.json').read_text(encoding='utf-8'))
        self.assertEqual(rows, committed)
        paths = [row['path'] for row in rows]
        self.assertEqual(paths, sorted(paths))
        self.assertEqual([p for p in paths if '\\' in p], [])

    def test_terraform_catalogue_registers_every_actual_posix_root(self):
        rows = entries(ROOT)
        registered = set()
        for row in rows:
            for field in ('module', 'root'):
                self.assertNotIn('\\', row[field], row[field])
                self.assertEqual(row[field], Path(row[field]).as_posix())
                registered.add(row[field])
        actual = {p.parent.relative_to(ROOT).as_posix()
                  for p in (ROOT / 'terraform').rglob('main.tf.json') if '.terraform' not in p.parts}
        self.assertEqual(actual, registered)

    def test_ansible_catalogue_paths_are_posix(self):
        catalogue = json.loads((ROOT / 'ansible/catalog.json').read_text(encoding='utf-8'))
        declared = {row['path'] for row in catalogue['playbooks']}
        self.assertEqual([p for p in declared if '\\' in p], [])
        actual = {p.relative_to(ROOT / 'ansible').as_posix()
                  for p in (ROOT / 'ansible/playbooks').rglob('*.yml')}
        self.assertEqual(actual, declared)

    def test_assurance_index_source_paths_are_posix(self):
        index = json.loads((ROOT / 'sources/assurance/verification_families.json').read_text(encoding='utf-8'))
        paths = relative_paths(index)
        self.assertTrue(paths)
        self.assertEqual([p for p in paths if '\\' in p], [])


if __name__ == '__main__':
    unittest.main()