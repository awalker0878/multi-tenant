"""Definition projections, handler coverage and all historical stage combinations."""

import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('capability_generator', ROOT / 'scripts/generate_capabilities.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


class CapabilityDefinitionsTest(unittest.TestCase):
    def test_projections_and_all_thirty_orders(self):
        data = json.loads(generator.SOURCE.read_text())
        projected = generator.projections(data)
        for path, content in projected.items():
            self.assertEqual(path.read_text(), content, str(path))
        self.assertEqual(sum(len(v['stages']) for v in data['methods'].values()), 30)
        source = projected[ROOT / 'services/planning/src/planning/domain/capability_definitions.py']
        for root, package in generator.PYTHON.items():
            self.assertEqual(source, projected[ROOT / f'{root}/src/{package}/domain/capability_definitions.py'])

    def test_new_method_cannot_claim_an_unimplemented_handler(self):
        data = json.loads(generator.SOURCE.read_text())
        method = copy.deepcopy(data['methods']['cold_export'])
        method['v1_alias'] = 'UNIMPLEMENTED_NATIVE_METHOD'
        data['methods']['future_method'] = method
        with self.assertRaisesRegex(ValueError, 'does not implement'):
            generator.projections(data)

    def test_stage_without_before_or_after_cases_is_rejected(self):
        data = json.loads(generator.SOURCE.read_text())
        del data['stage_before']['capture']
        with self.assertRaisesRegex(ValueError, 'stages/cases'):
            generator.projections(data)
