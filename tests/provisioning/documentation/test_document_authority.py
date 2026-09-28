"""Current implementation sequence must not drift back to historical prompts."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
INDEX = ROOT / 'docs/provisioning/README.md'


class CurrentDocumentAuthorityTest(unittest.TestCase):
    def test_current_backlog_is_separate_from_retained_refactor_history(self):
        text = INDEX.read_text(encoding='utf-8')
        active = text.split('## Active documents', 1)[1].split('## Retained refactor history', 1)[0]
        history = text.split('## Retained refactor history', 1)[1].split('## Command line', 1)[0]
        self.assertIn('../product/enterprise-workload-mobility-execution-plan.md', active)
        self.assertNotIn('deepseek-', active)
        self.assertIn('deepseek-refactor-completion-audit.md', history)
        self.assertIn('deepseek-refactor-completion-execution-prompt.md', history)
        self.assertIn('not current execution', history)


if __name__ == '__main__':
    unittest.main()
