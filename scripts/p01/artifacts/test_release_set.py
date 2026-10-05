import json
from pathlib import Path
import shutil
import tempfile
import unittest

from bundle import digest
from release_set import assemble

ROOT = Path(__file__).resolve().parents[3]
RUN = 'verification/p01/artifact-trust/run-37265822363'


class ReleaseSetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / RUN, self.root / RUN)
        (self.root / 'deploy/build').mkdir(parents=True)
        shutil.copyfile(ROOT / 'deploy/build/components.json', self.root / 'deploy/build/components.json')
        self.report = self.root / RUN / 'planning/report.json'

    def mutate_report(self, **updates):
        value = json.loads(self.report.read_bytes());value.update(updates)
        self.report.write_text(json.dumps(value))
        path = self.root / RUN / 'retrieval.json'
        retrieval = json.loads(path.read_bytes())
        retrieval['retained_file_sha256']['planning/report.json'] = digest(self.report)
        path.write_text(json.dumps(retrieval))

    def test_all_nine_held_candidates_are_reproducible(self):
        result = assemble(self.root, RUN)
        self.assertEqual(len(result['components']), 9)
        self.assertEqual(len(result['held_components']), 9)
        self.assertFalse(result['promotion_authorized'])
        self.assertEqual(result, assemble(self.root, RUN))
        self.assertTrue(all(not c['source_blocking_findings'] for c in result['components']))

    def test_missing_report_is_denied(self):
        self.report.unlink()
        with self.assertRaisesRegex(ValueError, 'missing_retained_file'):
            assemble(self.root, RUN)

    def test_mixed_source_is_denied_even_with_rewritten_inventory(self):
        self.mutate_report(source_revision='a' * 40)
        with self.assertRaisesRegex(ValueError, 'invalid_component_report'):
            assemble(self.root, RUN)

    def test_held_candidate_cannot_be_marked_admitted(self):
        self.mutate_report(candidate_admission='ADMITTED_DEVELOPMENT')
        with self.assertRaisesRegex(ValueError, 'candidate_admission_overclaim'):
            assemble(self.root, RUN)

    def test_altered_signature_is_denied(self):
        path = self.root / RUN / 'planning/bundle-record/signature.sigstore.json'
        path.write_bytes(path.read_bytes() + b'changed')
        with self.assertRaisesRegex(ValueError, 'retained_digest_mismatch'):
            assemble(self.root, RUN)

    def test_current_registry_cannot_silently_drop_worker(self):
        path = self.root / 'deploy/build/components.json'
        value = json.loads(path.read_bytes());value['components'].pop()
        path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, 'component_registry_changed'):
            assemble(self.root, RUN)


if __name__ == '__main__':
    unittest.main()
