"""The dependency direction the architecture document claims, made checkable.

`docs/provisioning/architecture.md` states the layer order and names the modules
that are allowed to reach across it. Nothing else verified those claims, so a new
import could have reversed an edge without failing a single test.
"""
from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path

from tests.provisioning import support

PACKAGE = support.ROOT / 'provisioner'
#: The one module allowed to resolve the existing compiler and generators by name.
BACKREACH_MODULE = PACKAGE / 'repository.py'
#: Modules that own the transport rather than a single command.
TRANSPORT_MODULES = frozenset({'__init__.py', '__main__.py', 'main.py', 'support.py'})
#: The one module that holds the operations every command delegates to.
SERVICE_MODULE = 'provisioner.execution.service'


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


def _command_imports(path: Path) -> list[str]:
    """Every `provisioner.cli.<name>` target a module imports, in any import form.

    Both `from provisioner.cli import plan` and `from provisioner.cli.plan import
    plan_for` name the command `plan`, so the rule has to read the AST rather than
    the module prefix alone.
    """
    tree = ast.parse(path.read_text(encoding='utf-8'))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names
                         if alias.name.startswith('provisioner.cli.'))
        elif isinstance(node, ast.ImportFrom) and not node.level:
            module = node.module or ''
            if module.startswith('provisioner.cli.'):
                names.append(module)
            elif module == 'provisioner.cli':
                names.extend(f'provisioner.cli.{alias.name}' for alias in node.names)
    return sorted(set(names))


def _command_couplings(module: str, path: Path) -> list[str]:
    """The command-to-command imports of one command module, sorted.

    A command may import the shared transport helpers and any core module. It may
    not import a peer: the operations the commands share live below the transport in
    `provisioner.execution.service`, so a command that imports another command has
    reversed the dependency direction the architecture document claims.
    """
    if f'{module.rsplit(".", 1)[-1]}.py' in TRANSPORT_MODULES:
        return []
    return sorted(name for name in _command_imports(path)
                  if f'{name.rsplit(".", 1)[-1]}.py' not in TRANSPORT_MODULES)


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
            module = _module_name(path)
            for name in _command_couplings(module, path):
                with self.subTest(source=module, imports=name):
                    self.fail(f'{module} imports the command {name}')

    def test_the_command_rule_refuses_a_controlled_command_to_command_import(self):
        """The rule must have teeth: a reversed edge has to be reported.

        The fixture is parsed from source exactly like a real command module, so the
        AST path the rule depends on is exercised rather than assumed.
        """
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / 'status.py'
            fixture.write_text(
                'from provisioner.cli import plan as plan_command\n'
                'from provisioner.cli.plan import plan_for\n'
                'from provisioner.cli.support import EXIT_OK\n'
                'from provisioner.execution.service import Context\n',
                encoding='utf-8')
            self.assertEqual(_command_couplings('provisioner.cli.status', fixture),
                             ['provisioner.cli.plan'])
            self.assertEqual(_command_couplings('provisioner.cli.main', fixture), [])

    def test_every_command_delegates_to_the_shared_service(self):
        """No command builds a plan of its own, and none reaches for a peer to do it."""
        for path in _sources(PACKAGE / 'cli'):
            if path.name in TRANSPORT_MODULES:
                continue
            with self.subTest(command=_module_name(path)):
                self.assertIn(SERVICE_MODULE, _absolute_imports(path),
                              f'{_module_name(path)} does not use {SERVICE_MODULE}')

    def test_the_existing_compiler_never_imports_the_portable_core(self):
        compiler = support.ROOT / 'tools' / 'compile_wsd.py'
        self.assertTrue(compiler.is_file())
        for name in _absolute_imports(compiler):
            with self.subTest(imports=name):
                self.assertFalse(name.startswith('provisioner'),
                                 f'compile_wsd.py imports {name}')


if __name__ == '__main__':
    unittest.main()