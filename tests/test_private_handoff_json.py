import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from provisioner.compiler import wsd as compile_wsd
from provisioner.execution import guest_inventory


class PrivateHandoffJsonTests(unittest.TestCase):
    def test_ambiguous_or_nonfinite_inputs_cannot_create_output(self):
        for module in (compile_wsd, guest_inventory):
            for content in ('{"scope": {}, "scope": {}}', '{"value": NaN}'):
                with self.subTest(module=module.__name__, content=content), tempfile.TemporaryDirectory() as td:
                    source = Path(td) / 'input.json'; source.write_text(content)
                    output = Path(td) / 'result'
                    positional = [str(source)] * (2 if module is guest_inventory else 1)
                    stdout = io.StringIO()
                    with patch.object(sys, 'argv', ['test', *positional, '--output', str(output)]), contextlib.redirect_stdout(stdout):
                        self.assertEqual(module.main(), 2)
                    self.assertFalse(output.exists())
                    self.assertIn('REJECTED', stdout.getvalue())
