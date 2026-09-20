import contextlib
import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import neutron_observe as observer

ROOT = Path(__file__).resolve().parents[1]


class NeutronValidationCliTests(unittest.TestCase):
    def test_validation_never_constructs_client(self):
        output = io.StringIO()
        with patch.object(sys, 'argv', ['observe', str(ROOT / 'ansible/fixtures/neutron_manifest.json'), '--validate-only']), \
                patch.object(observer, 'Client', side_effect=AssertionError('No network allowed')), contextlib.redirect_stdout(output):
            self.assertEqual(observer.main(), 0)
        self.assertEqual(json.loads(output.getvalue()), {'status': 'INPUT_VALID_NO_CONTACT', 'target_contacted': False, 'may_activate': False})

    def test_modes_are_exclusive(self):
        with patch.object(sys, 'argv', ['observe', 'unused', '--validate-only', '--read-authorized-target']), \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            observer.main()

    def test_read_without_target_binding_rejected(self):
        with patch.object(sys, 'argv', ['observe', 'unused', '--read-authorized-target']), \
                patch.object(observer, 'Client', side_effect=AssertionError('No network allowed')), \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            observer.main()
