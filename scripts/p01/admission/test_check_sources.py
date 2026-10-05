"""Reject head-only, stale-attempt, wrong-workflow and altered check evidence."""
import hashlib
import io
import json
import unittest
import zipfile
from check_sources import validate_source
from policy import Denied


class CheckSourceTests(unittest.TestCase):
    def setUp(self):
        self.expected = {'workflow': 'quality.yml', 'job': 'quality'}
        self.run = {'id': 21, 'run_attempt': 1, 'event': 'pull_request', 'head_sha': 'a'*40, 'path': '.github/workflows/quality.yml'}
        self.job = {'run_id': 21, 'name': 'Quality', 'conclusion': 'success'}
        self.record = {'result': 'PASSED', 'source_revision': 'c'*40, 'name': 'Quality', 'event': 'pull_request',
                       'run_id': 21, 'run_attempt': 1, 'job': 'quality',
                       'workflow_ref': 'fixture/repo/.github/workflows/quality.yml@refs/pull/7/merge',
                       'pull_request': {'number': 7, 'head': 'a'*40, 'base': 'b'*40}}

    def invoke(self, artifact_override=None):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as package:package.writestr('report.json', json.dumps(self.record))
        raw = stream.getvalue()
        artifact = {'digest': 'sha256:' + hashlib.sha256(raw).hexdigest(), 'expired': False,
                    'name': 'check-source-quality-21-1'} | (artifact_override or {})
        return validate_source(raw, artifact, self.run, self.job, self.expected, repository='fixture/repo',
                               name='Quality', head='a'*40, base='b'*40, tested='c'*40, number=7)

    def test_actual_merge_checkout_passes(self):self.assertEqual(self.invoke(), self.record)

    def test_head_only_or_old_merge_is_not_tested_merge(self):
        for sha in ['a'*40, 'd'*40]:
            self.record['source_revision'] = sha
            with self.assertRaisesRegex(Denied, '^check_source_mismatch$'):self.invoke()

    def test_stale_base_is_denied(self):
        self.record['pull_request']['base'] = 'd'*40
        with self.assertRaisesRegex(Denied, '^check_source_mismatch$'):self.invoke()

    def test_replay_from_previous_run_attempt_is_denied(self):
        self.run['run_attempt'] = 2
        with self.assertRaisesRegex(Denied, '^check_attempt_mismatch$'):self.invoke()

    def test_wrong_workflow_and_push_event_are_denied(self):
        self.run['path'] = '.github/workflows/forged.yml'
        with self.assertRaisesRegex(Denied, '^check_workflow_mismatch$'):self.invoke()
        self.run['path'] = '.github/workflows/quality.yml';self.run['event'] = 'push'
        with self.assertRaisesRegex(Denied, '^check_run_not_current_pr$'):self.invoke()

    def test_altered_or_expired_artifact_is_denied(self):
        for override in [{'digest': 'sha256:'+'0'*64}, {'expired': True}]:
            with self.assertRaises(Denied):self.invoke(override)

    def test_job_and_workflow_ref_must_match(self):
        self.job['run_id'] = 22
        with self.assertRaisesRegex(Denied, '^check_job_mismatch$'):self.invoke()
        self.job['run_id'] = 21;self.record['workflow_ref'] = 'fixture/repo/.github/workflows/quality.yml@refs/heads/main'
        with self.assertRaisesRegex(Denied, '^check_workflow_ref_mismatch$'):self.invoke()


if __name__ == '__main__':unittest.main()
