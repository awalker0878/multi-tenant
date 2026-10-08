"""Installed dependencies must not change authored-document validation results."""

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("documentation_validator", ROOT / "scripts/validate_docs.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DocumentationLinksTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def test_installed_dependencies_do_not_add_broken_upstream_links(self):
        self.write("README.md", "[Guide](docs/guide.md)\n")
        self.write("docs/guide.md", "Authored documentation.\n")
        for package, manifest, dependencies in (
            ("apps/console", "composer.json", "vendor"),
            ("apps/console", "package.json", "node_modules"),
            ("services/planning", "pyproject.toml", ".venv"),
            ("spikes/compatibility/frontend", "package.json", "node_modules"),
        ):
            self.write(f"{package}/{manifest}", "")
            self.write(f"{package}/{dependencies}/upstream/README.md", "[Not packaged](missing.md)\n")
        self.write(".git/notes.md", "[Not a document](missing.md)\n")
        self.write(".venv/lib/package/README.md", "[Not packaged](missing.md)\n")
        documents, errors = MODULE.validate_markdown(self.root)
        self.assertEqual([], errors)
        self.assertEqual({"README.md", "docs/guide.md"}, {str(p.relative_to(self.root)) for p in documents})

    def test_authored_documents_and_arbitrary_vendor_directories_remain_checked(self):
        for name in ("docs/new.md", "docs/vendor/README.md", "docs/node_modules/README.md"):
            self.write(name, "[Missing](missing.md)\n")
        documents, errors = MODULE.validate_markdown(self.root)
        self.assertEqual(3, len(documents))
        self.assertEqual(3, len(errors))
        self.assertTrue(all("Broken local link" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
