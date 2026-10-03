"""The package compiler's private input parser has no native observer dependency."""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from provisioner.compiler import wsd

ROOT = Path(__file__).resolve().parents[1]


class CompilerInputTests(unittest.TestCase):
    def test_parser_preserves_valid_json_values(self):
        document = {'members': [1, 1.5, True, None, {'name': 'a'}]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.json'
            path.write_text(json.dumps(document))
            self.assertEqual(wsd._read_json(path), document)

    def test_bounded_read_rejects_oversized_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.json'
            path.write_text('{"value":"' + 'x' * 32 + '"}')
            with patch.object(wsd, 'INPUT_LIMIT', 32):
                with self.assertRaisesRegex(ValueError, 'exceeds bounded size'):
                    wsd._read_json(path)

    def test_ambiguous_nonfinite_and_deep_inputs_create_no_output(self):
        invalid = ('{"x":1,"x":2}', '{"x":{"a":1,"a":2}}',
                   '{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}',
                   '{"x":1e9999}', '{"x":-1e9999}', '[' * 1500 + ']' * 1500)
        for text in invalid:
            with self.subTest(text=text[:50]), tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / 'input.json'
                output = Path(directory) / 'output'
                source.write_text(text)
                with patch.object(sys, 'argv', ['compiler', str(source), '--output', str(output)]):
                    with contextlib.redirect_stdout(io.StringIO()) as captured:
                        self.assertEqual(wsd.main(), 2)
                self.assertFalse(output.exists())
                self.assertEqual(json.loads(captured.getvalue())['status'], 'REJECTED')

    def test_clean_interpreter_compiles_without_legacy_imports_or_path_mutation(self):
        # Only this harness adds the source directory. The compiler must not
        # mutate sys.path or import tools/scripts, even transitively.
        child = r'''
import importlib.abc, json, pathlib, sys
sys.path.insert(0, sys.argv[1])
class RefuseLegacy(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'tools', 'scripts'}:
            raise AssertionError('Legacy runtime import: '+fullname)
        return None
sys.meta_path.insert(0, RefuseLegacy())
original_path = list(sys.path)
from provisioner.compiler import components, wsd
for platform in components.COMPONENTS:
    for phase in ('domains', 'workloads'):
        assert wsd.native_variables(platform, phase)
    source = pathlib.Path(sys.argv[1]) / 'examples/environments' / (platform+'.json.example')
    files, result = wsd.compile_environment(json.loads(source.read_text()))
    assert files and result['status'] == 'DRAFT_DISABLED_NOT_AUTHORIZED'
    assert result['native_contact'] is False
    assert all(value['allow_restricted_build'] is False for value in files.values())
assert sys.path == original_path
'''
        with tempfile.TemporaryDirectory() as directory:
            completed = subprocess.run([sys.executable, '-I', '-c', child, str(ROOT)],
                                       cwd=directory, capture_output=True, text=True, timeout=30)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)


if __name__ == '__main__':
    unittest.main()
