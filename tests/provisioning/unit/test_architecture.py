"""The dependency direction the architecture document claims, made checkable.

`docs/provisioning/architecture.md` states the layer order and names the modules
that are allowed to reach across it. Nothing else verified those claims, so a new
import could have reversed an edge without failing a single test.
"""
from __future__ import annotations

import ast
from importlib.util import resolve_name
import sys
import tempfile
import unittest
from pathlib import Path

from tests.provisioning import support

PACKAGE = support.ROOT / 'provisioner'
#: The one module allowed to resolve the existing compiler and generators by name.
BACKREACH_MODULE = PACKAGE / 'repository.py'
#: Modules that own the transport rather than a single command.
TRANSPORT_MODULES = frozenset({'__init__.py', '__main__.py', 'main.py', 'support.py'})
# The enterprise operator talks to the control API; it is not a local owner
# command and must not import the planning or delivery execution modules.
API_ONLY_COMMANDS = frozenset({'operator.py', 'application_drafts.py'})
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


def _api_client_import_violations(path: Path, module: str) -> list[str]:
    """Resolve all static import forms, including relative controller backreach.

    Only the exact API-client modules may bypass the local execution service.
    The operator may compose its draft contract; that contract has only standard
    library imports. New CLI modules are not implicitly classified as clients.
    """
    tree = ast.parse(path.read_text(encoding='utf-8'))
    targets = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ''
            if node.level:
                base = resolve_name('.' * node.level + base, module.rpartition('.')[0])
            targets.update(base + '.' + alias.name for alias in node.names)
    allowed = set(sys.stdlib_module_names)
    if module == 'provisioner.cli.operator':
        allowed.update({'httpx', 'certifi'})
    internal = 'provisioner.cli.application_drafts'
    return sorted(target for target in targets
                  if target.split('.')[0] not in allowed
                  and not (module == 'provisioner.cli.operator'
                           and (target == internal or target.startswith(internal + '.'))))


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
        """Local owner commands share one service, not peer command modules."""
        for path in _sources(PACKAGE / 'cli'):
            if path.name in TRANSPORT_MODULES | API_ONLY_COMMANDS:
                continue
            with self.subTest(command=_module_name(path)):
                self.assertIn(SERVICE_MODULE, _absolute_imports(path),
                              f'{_module_name(path)} does not use {SERVICE_MODULE}')

    def test_operator_cli_has_only_the_remote_api_boundary(self):
        for name in sorted(API_ONLY_COMMANDS):
            path = PACKAGE / 'cli' / name
            self.assertTrue(path.is_file(), 'declared API-client module is missing')
            with self.subTest(module=name):
                self.assertEqual(_api_client_import_violations(path, _module_name(path)), [])
        self.assertIn('httpx', _absolute_imports(PACKAGE / 'cli' / 'operator.py'))

    def test_api_client_exemptions_are_exact_and_not_local_owner_commands(self):
        self.assertEqual(API_ONLY_COMMANDS, {'operator.py', 'application_drafts.py'})
        for name in sorted(API_ONLY_COMMANDS):
            path = PACKAGE / 'cli' / name
            self.assertNotIn(SERVICE_MODULE, _absolute_imports(path))
        self.assertNotIn('plan.py', API_ONLY_COMMANDS)
        self.assertNotIn('apply.py', API_ONLY_COMMANDS)

    def test_api_client_guard_rejects_direct_relative_and_peer_bypasses(self):
        forbidden = (
            'import provisioner.execution.service',
            'from provisioner.execution import service',
            'from ..execution import service',
            'from .. import controlplane',
            'from ..controlplane.discovery import application_drafts',
            'from . import plan',
            'from .plan import plan_for',
            'import psycopg',
            'from tools import delivery_runner',
            'from scripts import native_lifecycle',
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.py'
            for name in sorted(API_ONLY_COMMANDS):
                module = 'provisioner.cli.' + Path(name).stem
                for text in forbidden:
                    with self.subTest(module=module, statement=text):
                        path.write_text(text + '\n', encoding='utf-8')
                        self.assertTrue(_api_client_import_violations(path, module))
            path.write_text('from . import application_drafts\nimport httpx\nimport certifi\n',
                            encoding='utf-8')
            self.assertEqual(_api_client_import_violations(path, 'provisioner.cli.operator'), [])
            self.assertTrue(_api_client_import_violations(path, 'provisioner.cli.application_drafts'))
            path.write_text('import json\nfrom pathlib import Path\n', encoding='utf-8')
            self.assertEqual(_api_client_import_violations(path, 'provisioner.cli.application_drafts'), [])

    def test_the_package_owned_compiler_has_only_low_level_dependencies(self):
        for filename in ('wsd.py', 'components.py'):
            compiler = PACKAGE / 'compiler' / filename
            self.assertTrue(compiler.is_file())
            for name in _absolute_imports(compiler):
                with self.subTest(module=filename, imports=name):
                    self.assertFalse(name.startswith(('tools', 'scripts')),
                                     f'{filename} imports legacy owner {name}')
                    if name.startswith('provisioner'):
                        self.assertEqual(name, 'provisioner.compiler.components')
            self.assertNotIn('sys.path', compiler.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
