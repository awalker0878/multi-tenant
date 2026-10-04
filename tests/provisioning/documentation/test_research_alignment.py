"""One wave backlog and explicit research boundaries survive documentation changes."""
from pathlib import Path
import json
import re
import unittest

ROOT = Path(__file__).resolve().parents[3]


class ResearchAlignmentTests(unittest.TestCase):
    def test_existing_b_items_remain_unique_and_complete(self):
        text = (ROOT / 'docs/product/enterprise-workload-mobility-execution-plan.md').read_text()
        items = re.findall(r'^\| (B\d{2}) \|', text, re.M)
        self.assertEqual(items, [f'B{i:02}' for i in range(1, 51)])
        self.assertIn('## 8. Research-driven acceptance and implementation delta', text)
        self.assertIn('Native qualification', (ROOT / 'docs/engineering/platform-migration-research.md').read_text())

    def test_active_qualification_owners_are_not_retired_by_research(self):
        for owner in ('registry', 'native', 'provenance', 'target_selection', 'campaign'):
            self.assertTrue((ROOT / f'provisioner/qualification/{owner}.py').is_file())
        registry = json.loads((ROOT / 'provisioner/retired_interfaces.json').read_text())
        self.assertFalse(any(row['interface'].startswith('provisioner/qualification/')
                             for row in registry['retiredInterfaces']))

    def test_current_design_versions_are_consistent_with_index_and_register(self):
        records = json.loads((ROOT / 'sources/documentation/current_design_records.json').read_text())
        for row in records:
            self.assertIn('**Version:** '+row['version'], (ROOT / row['path']).read_text())
            self.assertEqual(row['status'], 'Proposed')
            self.assertIsNone(row['acceptance_evidence'])
        index = (ROOT / 'docs/current/README.md').read_text()
        tad = next(row for row in records if row['id'] == 'TAD-M01')
        self.assertIn('TAD-M01 is **version '+tad['version'], index)

    def test_property_coverage_document_is_not_a_native_claim(self):
        from provisioner.domain.capability_properties import PROPERTY_VALUES
        text = (ROOT / 'docs/engineering/platform-migration-research.md').read_text()
        self.assertIn(f'There are {len(PROPERTY_VALUES)} properties', text)
        self.assertIn('No installed vendor environment was contacted.', text)
        self.assertIn('observedCapabilities', text)
        self.assertIn('source_restart_without_reconciliation',
                      (ROOT / 'provisioner/portability/cutover.py').read_text())
