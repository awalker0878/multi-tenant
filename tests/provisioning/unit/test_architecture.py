"""The dependency direction the architecture document claims, made checkable.

`docs/provisioning/architecture.md` states the layer order and names the modules
that are allowed to reach across it. Nothing else verified those claims, so a new
import could have reversed an edge without failing a single test.
"""
from __future__ import annotations

import ast
import unittest
from pathlib import Path

from tests.provisioning import support

PACKAGE = support.ROOT / 'provisioner'
#: The one module allowed to resolve the existing compiler and generators by name.
BACKREACH_MODULE = PACKAGE / 'repository.py'
#: Modules that own the transport rather than a single command.
TRANSPORT_MODULES = frozenset({'__init__.py', '__main__.py', 'main.py', 'support.py'})


def _sources(directory: Path):
    return sorted(path for path in directory.rglob('*.py')
                  if '__pycache__' not in path.parts)


def _absolute_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding='utf-8'))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and not node.level:
            names.add(node.module or '')
    return names


def _module_name(path: Path) -> str:
    return '.'.join(path.relative_to(support.ROOT).with_suffix('').parts)


class DependencyDirectionTest(unittest.TestCase):
    def test_the_package_contains_sources(self):
        self.assertTrue(_sources(PACKAGE), 'no provisioner sources were found')

    def test_no_source_carries_a_byte_order_mark(self):
        """A BOM is invisible to the interpreter and breaks text-level tooling."""
        for path in _sources(PACKAGE):
            with self.subTest(source=_module_name(path)):
                self.assertFalse(path.read_bytes().startswith(b'\xef\xbb\xbf'),
                                 f'{_module_name(path)} starts with a UTF-8 BOM')

    def test_only_the_repository_bridge_reaches_into_tools_and_scripts(self):
        for path in _sources(PACKAGE):
            for name in _absolute_imports(path):
                if name.split('.')[0] in ('tools', 'scripts'):
                    with self.subTest(source=_module_name(path), imports=name):
                        self.assertEqual(path, BACKREACH_MODULE,
                                         f'{_module_name(path)} reaches into {name}')

    def test_nothing_outside_the_transport_imports_the_cli(self):
        for path in _sources(PACKAGE):
            if path.is_relative_to(PACKAGE / 'cli'):
                continue
            for name in _absolute_imports(path):
                with self.subTest(source=_module_name(path), imports=name):
                    self.assertFalse(name.startswith('provisioner.cli'),
                                     f'{_module_name(path)} imports {name}')

    def test_a_cli_command_imports_no_other_command(self):
        for path in _sources(PACKAGE / 'cli'):
            if path.name in TRANSPORT_MODULES:
                continue
            for name in _absolute_imports(path):
                if not name.startswith('provisioner.cli.'):
                    continue
                    imported = Path(*name.split('.')).with_suffix('.py').name
                    with self.subTest(source=_module_name(path), imports=name):
                        self.assertIn(imported, TRANSPORT_MODULES,
                                      f'{_module_name(path)} imports the command {name}')

    def test_the_existing_compiler_never_imports_the_portable_core(self):
        compiler = support.ROOT / 'tools' / 'compile_wsd.py'
        self.assertTrue(compiler.is_file())
        for name in _absolute_imports(compiler):
            with self.subTest(imports=name):
                self.assertFalse(name.startswith('provisioner'),
                                 f'compile_wsd.py imports {name}')


if __name__ == '__main__':
    unittest.main()