"""Native session bindings stay in adapters, not generic read utilities."""
from __future__ import annotations

import ast
from pathlib import Path
import subprocess
import sys
import unittest

from provisioner.controlplane.discovery import native_credentials, native_https
from provisioner.controlplane.discovery.adapters import vmware_credentials, vmware_https

ROOT = Path(__file__).resolve().parents[3]


class NativeCredentialBoundaryTests(unittest.TestCase):
    def test_vmware_binding_implementations_have_one_adapter_owner(self):
        for name in ('selection_digest', 'VmwareSessionMaterial', 'SignedFileVmwareCredentialSource'):
            with self.subTest(owner=name):
                self.assertEqual(getattr(vmware_credentials, name).__module__,
                                 vmware_credentials.__name__)
                self.assertFalse(hasattr(native_credentials, name))
        self.assertIs(vmware_https.SignedFileVmwareCredentialSource,
                      vmware_credentials.SignedFileVmwareCredentialSource)

    def test_protected_read_helpers_have_one_generic_owner(self):
        for name in ('NativeReadHeld', 'read_protected', 'decode_json'):
            with self.subTest(helper=name):
                self.assertEqual(getattr(native_credentials, name).__module__,
                                 native_credentials.__name__)
                self.assertIs(getattr(vmware_credentials, name), getattr(native_credentials, name))
                self.assertIs(getattr(native_https, name), getattr(native_credentials, name))

    def test_https_has_one_provider_neutral_owner(self):
        self.assertEqual(native_https.read_json.__module__, native_https.__name__)
        self.assertIs(vmware_https.read_json, native_https.read_json)
        tree = ast.parse(Path(native_https.__file__).read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertNotIn('adapters', (node.module or '').split('.'))

    def test_shared_utility_has_no_vendor_import_or_dynamic_forwarding(self):
        tree = ast.parse(Path(native_credentials.__file__).read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or '']
            else:
                names = []
            self.assertFalse(any('adapters' in name.split('.') for name in names), names)
        definitions = {node.name for node in tree.body
                       if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
        self.assertEqual(definitions, {'NativeReadHeld', 'read_protected', 'decode_json'})

    def test_generic_helpers_import_with_vendor_adapter_imports_forbidden(self):
        child = r'''
import importlib.abc, sys
sys.path.insert(0, sys.argv[1])
class NoAdapterImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'provisioner.controlplane.discovery.adapters' or fullname.startswith(
                'provisioner.controlplane.discovery.adapters.'):
            raise AssertionError('Shared credential utility imported a vendor: ' + fullname)
sys.meta_path.insert(0, NoAdapterImports())
from provisioner.controlplane.discovery import native_credentials, native_https as shared
assert shared.decode_json(b'{"observed":false}', 1024) == {'observed':False}
try:
    shared.decode_json(b'{"observed":false,"observed":true}', 1024)
except ValueError:
    pass
else:
    raise AssertionError('Duplicate JSON keys accepted')
'''
        completed = subprocess.run([sys.executable, '-I', '-B', '-c', child, str(ROOT)],
                                   cwd=ROOT.parent, text=True, capture_output=True, timeout=15)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)


if __name__ == '__main__':
    unittest.main()
