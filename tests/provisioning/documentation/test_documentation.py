"""Documentation drift regressions.

These tests keep the active provisioning documents, the retired-interface register
and the command line from drifting apart. They read files only: no platform is
contacted and no engine is run.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

from tests.provisioning import support

DOCS = support.ROOT / 'docs' / 'provisioning'
INDEX = DOCS / 'README.md'

#: The one entry point the active documents are allowed to name.
ENTRY_POINT = 'python -m provisioner.cli '

#: Documents that carry the current entry point and current module paths.
ACTIVE_DOCUMENTS = (INDEX, DOCS / 'plan-workflow.md', DOCS / 'architecture.md',
                    DOCS / 'generation-model.md',
                    support.ROOT / 'README.md', support.ROOT / 'docs' / 'NEXT_WORK.md')

MODULE_PATH = re.compile(r'provisioner/[A-Za-z0-9_./-]+')

#: The active documents the refactor must maintain.
REQUIRED = ('README.md', 'architecture.md', 'request-contract.md', 'profile-model.md',
            'placement-model.md', 'desired-state-model.md', 'generation-model.md',
            'plan-manifest-model.md', 'delivery-handoff-model.md',
            'capacity-reservation-model.md',
            'adapter-contract.md', 'terraform-boundary.md', 'service-owner-boundary.md',
            'plan-workflow.md', 'service-profile-matrix.md')

#: Documents outside the provisioning tree that must link to it.
ENTRY_POINTS = ('README.md', 'docs/README.md', 'docs/implementation/README.md',
                'docs/implementation/code-map.md', 'docs/NEXT_WORK.md')

LIMIT_MARKERS = ('not an authorization', 'not a deployment', 'does not', 'never',
                 'refuses', 'no native', 'cannot')

LINK = re.compile(r'\[[^\]]*\]\(([^)\s]+)\)')


class RequiredDocumentTest(unittest.TestCase):
    def test_every_required_document_exists_and_is_substantial(self):
        for name in REQUIRED:
            path = DOCS / name
            with self.subTest(document=name):
                self.assertTrue(path.is_file(), f'missing {name}')
                self.assertGreater(len(path.read_text(encoding='utf-8')), 1500)

    def test_index_links_every_required_document(self):
        text = INDEX.read_text(encoding='utf-8')
        for name in REQUIRED:
            if name == 'README.md':
                continue
            with self.subTest(document=name):
                self.assertIn(f'({name})', text, f'{name} is not linked from the index')

    def test_entry_points_link_to_the_provisioning_index(self):
        for relative in ENTRY_POINTS:
            with self.subTest(document=relative):
                text = (support.ROOT / relative).read_text(encoding='utf-8')
                self.assertIn('provisioning/README.md', text)

    def test_every_relative_link_resolves(self):
        for path in sorted(DOCS.glob('*.md')):
            text = path.read_text(encoding='utf-8')
            for target in LINK.findall(text):
                if target.startswith(('http://', 'https://', 'mailto:', '#')):
                    continue
                resolved = (path.parent / target.split('#')[0]).resolve()
                with self.subTest(document=path.name, link=target):
                    self.assertTrue(resolved.exists(), f'{path.name} -> {target} is broken')

    def test_documents_state_a_limit(self):
        for name in REQUIRED:
            if name == 'README.md':
                continue
            text = (DOCS / name).read_text(encoding='utf-8').lower()
            with self.subTest(document=name):
                self.assertTrue(any(marker in text for marker in LIMIT_MARKERS),
                                f'{name} states no boundary')

    def test_documents_claim_no_native_contact(self):
        for path in sorted(DOCS.glob('*.md')):
            text = path.read_text(encoding='utf-8')
            with self.subTest(document=path.name):
                self.assertNotIn('native_contact: true', text)
                self.assertNotIn('AUTHORIZED_BY_REPOSITORY', text)


class CommandDocumentationTest(unittest.TestCase):
    def _commands_table(self) -> str:
        text = (DOCS / 'plan-workflow.md').read_text(encoding='utf-8')
        section = text.split('## Commands', 1)[1].split('## ', 1)[0]
        return section

    def test_documented_commands_match_the_command_line(self):
        from provisioner.cli.main import COMMANDS
        documented = set(re.findall(r'^\| `([a-z]+)` \|', self._commands_table(),
                                    flags=re.MULTILINE))
        self.assertEqual(documented, set(COMMANDS))

    def test_documented_options_match_the_command_line(self):
        """The options table is a view of the transport, never a second source of truth."""
        from provisioner.cli.main import build_parser
        text = (DOCS / 'plan-workflow.md').read_text(encoding='utf-8')
        section = text.split('## Options', 1)[1].split('\n## ', 1)[0]
        documented = set(re.findall(r'^\| `(--[a-z-]+)', section, flags=re.MULTILINE))
        declared = {option for action in build_parser()._actions
                    for option in action.option_strings if option.startswith('--')}
        self.assertEqual(documented, declared - {'--help'})

    def test_documented_exit_codes_match_the_transport(self):
        from provisioner.cli.support import EXIT_INTERNAL, EXIT_OK, EXIT_REFUSED
        self.assertEqual((EXIT_OK, EXIT_REFUSED, EXIT_INTERNAL), (0, 2, 3))
        text = (DOCS / 'plan-workflow.md').read_text(encoding='utf-8')
        for value in ('`0`', '`2`', '`3`'):
            with self.subTest(exit_code=value):
                self.assertIn(value, text)

    def test_index_documents_the_module_invocation(self):
        text = INDEX.read_text(encoding='utf-8')
        for command in ('validate', 'resolve', 'plan', 'status', 'verify', 'evidence', 'apply'):
            with self.subTest(command=command):
                self.assertIn(f'{ENTRY_POINT}{command}', text)

    def test_the_documented_entry_point_actually_runs(self):
        """The index names an entry point; it must execute as documented."""
        request = support.REQUESTS / 'internal-production.yaml'
        completed = subprocess.run([sys.executable, '-m', 'provisioner.cli', 'validate',
                                    str(request)], cwd=str(support.ROOT),
                                   capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)['status'], 'VALID')

    def test_only_the_canonical_entry_point_is_documented(self):
        for path in ACTIVE_DOCUMENTS:
            text = path.read_text(encoding='utf-8')
            with self.subTest(document=str(path.relative_to(support.ROOT))):
                self.assertNotIn('python -m provisioner.cli.main', text)

    def test_the_transport_is_not_a_second_entry_point(self):
        package = support.ROOT / 'provisioner' / 'cli'
        self.assertTrue((package / '__main__.py').is_file(),
                        'the documented module entry point is missing')
        self.assertNotIn("__name__ == '__main__'",
                         (package / 'main.py').read_text(encoding='utf-8'),
                         'provisioner/cli/main.py is a transport, not an entry point')


class ModulePathDocumentationTest(unittest.TestCase):
    def test_documented_module_paths_exist(self):
        for path in ACTIVE_DOCUMENTS:
            text = path.read_text(encoding='utf-8')
            for token in sorted(set(MODULE_PATH.findall(text))):
                if token in ('provisioner/',) or token.endswith('...'):
                    continue
                resolved = support.ROOT / token.rstrip('/.')
                with self.subTest(document=path.name, module=token):
                    self.assertTrue(resolved.exists(), f'{path.name} names missing {token}')


class ServiceProfileMatrixTest(unittest.TestCase):
    """The matrix is a view of the catalogs, never a second source of truth."""

    FAMILIES = {'Environment': 'environment', 'Security': 'security',
                'Assurance': 'assurance', 'Availability': 'availability',
                'Recovery': 'recovery', 'Compute': 'compute', 'Storage': 'storage',
                'Network': 'network', 'Placement (region)': 'placement',
                'Service': 'service'}
    ROW = re.compile(r'^\| `([^`]+)` \| (\d+) \| ([^|]+) \| [^|]* \| (\d+) \|', re.MULTILINE)
    REVISION = re.compile(r'^Reviewed as catalog revision `(\d+)`\.$', re.MULTILINE)

    def _documented(self) -> dict:
        text = (DOCS / 'service-profile-matrix.md').read_text(encoding='utf-8')
        documented: dict = {}
        for section in text.split('\n## ')[1:]:
            title = section.split('\n', 1)[0].strip()
            if title not in self.FAMILIES:
                continue
            documented.setdefault(self.FAMILIES[title], []).extend(
                (name, int(rank), status.strip(), int(version))
                for name, rank, status, version in self.ROW.findall(section))
        return documented

    def _catalog(self, family: str) -> dict:
        path = support.ROOT / 'profiles' / family / 'catalog.json'
        return {row['profile']: row
                for row in json.loads(path.read_text(encoding='utf-8'))['profiles']}

    def _documented_revisions(self) -> dict:
        text = (DOCS / 'service-profile-matrix.md').read_text(encoding='utf-8')
        revisions: dict = {}
        for section in text.split('\n## ')[1:]:
            title = section.split('\n', 1)[0].strip()
            if title not in self.FAMILIES:
                continue
            found = self.REVISION.findall(section)
            self.assertEqual(len(found), 1, f'{title} must state exactly one catalog revision')
            revisions[self.FAMILIES[title]] = int(found[0])
        return revisions

    def _catalog_revision(self, family: str) -> int:
        path = support.ROOT / 'profiles' / family / 'catalog.json'
        return int(json.loads(path.read_text(encoding='utf-8'))['version'])

    def test_every_family_is_documented(self):
        documented = self._documented()
        self.assertEqual(sorted(documented), sorted(set(self.FAMILIES.values())))

    def test_documented_catalog_revisions_match_the_catalogs(self):
        revisions = self._documented_revisions()
        self.assertEqual(sorted(revisions), sorted(set(self.FAMILIES.values())))
        for family, revision in revisions.items():
            with self.subTest(family=family):
                self.assertEqual(revision, self._catalog_revision(family))

    def test_documented_profiles_ranks_statuses_and_versions_match_the_catalogs(self):
        for family, rows in self._documented().items():
            catalog = self._catalog(family)
            for name, rank, status, version in rows:
                key = name if name in catalog else name.split('/')[-1]
                with self.subTest(family=family, profile=name):
                    self.assertIn(key, catalog)
                    self.assertEqual(catalog[key]['rank'], rank)
                    self.assertEqual(catalog[key]['status'].startswith('IMPLEMENTED'),
                                     'deferred' not in status.lower())
                    self.assertEqual(int(catalog[key]['version']), version)

    def test_every_catalog_profile_is_documented(self):
        for family, rows in self._documented().items():
            catalog = self._catalog(family)
            documented = {name if name in catalog else name.split('/')[-1]
                          for name, _, _, _ in rows}
            with self.subTest(family=family):
                self.assertEqual(sorted(documented), sorted(catalog))


class CapacityDocumentationTest(unittest.TestCase):
    """The capacity document is a view of the module, never a second source of truth."""

    DOC = DOCS / 'capacity-reservation-model.md'

    def test_the_document_names_every_declared_format(self):
        from provisioner.allocations import owner as capacity
        text = self.DOC.read_text(encoding='utf-8')
        for name in ('VIEW_FORMAT', 'HANDOFF_FORMAT', 'BINDING_FORMAT',
                     'RECONCILIATION_FORMAT', 'REQUEST_FORMAT', 'FACTS_FORMAT'):
            with self.subTest(format=name):
                self.assertIn(getattr(capacity, name), text)

    def test_the_document_names_every_reconciled_state(self):
        from provisioner.allocations import owner as capacity
        text = self.DOC.read_text(encoding='utf-8')
        for state in capacity.STATES:
            with self.subTest(state=state):
                self.assertIn(state, text)

    def test_the_document_names_the_module_and_the_preserved_preflight(self):
        text = self.DOC.read_text(encoding='utf-8')
        self.assertIn('provisioner/allocations/owner.py', text)
        self.assertIn('provisioner/allocations/reservations.py', text)

    def test_the_document_is_indexed_and_states_its_limit(self):
        self.assertIn('(capacity-reservation-model.md)',
                      INDEX.read_text(encoding='utf-8'))
        self.assertIn('does not claim', self.DOC.read_text(encoding='utf-8').lower())

    def test_the_document_claims_no_native_contact(self):
        text = self.DOC.read_text(encoding='utf-8')
        self.assertIn('native_contact: false', text)
        self.assertNotIn('native_contact: true', text)


class RetiredInterfaceTest(unittest.TestCase):
    def test_register_loads_and_is_enforced(self):
        from scripts.check_retired_interfaces import _load_register
        document = _load_register()
        self.assertEqual(document['format'], 'hosting-retired-interfaces/1')
        self.assertIn('ENFORCED', document['status'])
        self.assertGreaterEqual(len(document['retiredInterfaces']), 5)

    def test_no_retired_interface_is_present(self):
        from scripts.check_retired_interfaces import check
        report = check()
        self.assertEqual(report['status'], 'PASSED', report['issues'])
        self.assertGreater(report['interfaces_checked'], 0)

    def test_every_retired_entry_names_a_replacement_and_an_enforcement(self):
        from scripts.check_retired_interfaces import _load_register
        for entry in _load_register()['retiredInterfaces']:
            with self.subTest(interface=entry['interface']):
                self.assertTrue(entry['replacement'])
                self.assertTrue(entry['enforcement'])
                self.assertTrue(entry['reason'])

    def test_frozen_specification_is_excluded_with_a_reason(self):
        from scripts.check_retired_interfaces import _load_register
        excluded = {row['path']: row['reason']
                    for row in _load_register()['scope']['excluded']}
        spec = 'docs/deepseek-master-refactor-provisioning-prompt.md'
        self.assertIn(spec, excluded)
        self.assertIn('forbidden', excluded[spec].lower())


class ReferenceCorpusDocumentationTest(unittest.TestCase):
    def test_corpus_documents_are_indexed(self):
        text = INDEX.read_text(encoding='utf-8')
        for relative in ('examples/requests', 'examples/resolved', 'examples/golden'):
            with self.subTest(path=relative):
                self.assertIn(relative, text)

    def test_examples_readme_names_the_provisioning_corpus(self):
        text = (support.ROOT / 'examples' / 'README.md').read_text(encoding='utf-8')
        self.assertIn('requests', text)
        self.assertIn('golden', text)

    def test_golden_index_matches_the_reference_corpus(self):
        index = json.loads((support.GOLDEN / 'digests.json').read_text(encoding='utf-8'))
        self.assertEqual(sorted(index['subjects']), sorted(support.REFERENCE_REQUESTS))


if __name__ == '__main__':
    unittest.main()