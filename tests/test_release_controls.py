import json
from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


class ReleaseControlsTests(unittest.TestCase):
    def test_required_checks_are_unconditional_pr_jobs(self):
        ruleset = json.loads((ROOT / 'config/github-main-ruleset.json').read_text())
        rule = next(row for row in ruleset['rules'] if row['type'] == 'required_status_checks')
        actual = {}
        for path in (ROOT / '.github/workflows').glob('*.yml'):
            workflow = yaml.load(path.read_text(), Loader=yaml.BaseLoader)
            if 'pull_request' not in workflow['on']:
                continue
            self.assertFalse((workflow['on']['pull_request'] or {}).get('paths'))
            for key, job in workflow['jobs'].items():
                name = job.get('name', key)
                self.assertNotIn(name, actual, 'Ambiguous required-check name')
                actual[name] = job
        for check in rule['parameters']['required_status_checks']:
            self.assertIn(check['context'], actual)
            self.assertNotIn('if', actual[check['context']], 'Required job must not silently skip')
            self.assertEqual(check['integration_id'], 15368)
