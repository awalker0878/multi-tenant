"""The hosting command line, end to end, as a real subprocess."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.provisioning import support

REQUEST = str(support.REQUEST)
MODULE = 'provisioner.cli'


def checkout_commit() -> str:
    """The commit the checkout reports, so a handoff can bind it explicitly."""
    return support.source_commit()


def run(*arguments: str) -> tuple[int, dict]:
    completed = subprocess.run([sys.executable, '-m', MODULE, *arguments],
                               cwd=str(support.ROOT), capture_output=True, text=True,
                               encoding='utf-8')
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        raise AssertionError(
            f'CLI did not emit JSON (exit {completed.returncode}): '
            f'{completed.stdout!r} {completed.stderr!r}')
    return completed.returncode, payload


class ReadOnlyCommandTest(unittest.TestCase):
    def test_validate_is_valid(self):
        code, payload = run('validate', REQUEST)
        self.assertEqual(code, 0)
        self.assertEqual(payload['status'], 'VALID')
        self.assertFalse(payload['native_contact'])

    def test_resolve_is_resolved(self):
        code, payload = run('resolve', REQUEST)
        self.assertEqual(code, 0)
        self.assertEqual(payload['status'], 'RESOLVED')
        self.assertEqual(len(payload['resolution']['profiles']), 10)

    def test_plan_is_planned_and_disabled(self):
        code, payload = run('plan', REQUEST)
        self.assertEqual(code, 0)
        self.assertEqual(payload['status'], 'PLANNED_DISABLED_NOT_AUTHORIZED')
        self.assertEqual(payload['format'], 'hosting-plan-result/1')
        self.assertTrue(payload['digest'])

    def test_plan_without_compilation_still_resolves(self):
        code, payload = run('plan', REQUEST, '--no-compile')
        self.assertEqual(code, 0)
        self.assertEqual(payload['compiled_files'], [])

    def test_status_holds_every_external_stage(self):
        code, payload = run('status', REQUEST)
        self.assertEqual(code, 0)
        held = {row['stage'] for row in payload['stages'] if row['status'] == 'HELD'}
        self.assertTrue(held)
        self.assertEqual(payload['activation'], 'HELD')

    def test_verify_is_blocked_on_external_evidence(self):
        code, payload = run('verify', REQUEST)
        self.assertEqual(code, 0)
        self.assertEqual(payload['status'], 'BLOCKED_ON_EXTERNAL_EVIDENCE')
        self.assertEqual(payload['activation'], 'HELD')
        self.assertTrue(payload['verification_plan'])

    def test_verify_never_reports_absent_observation_as_healthy(self):
        code, payload = run('verify', REQUEST)
        self.assertEqual(code, 0)
        self.assertEqual(payload['health']['status'], 'NOT_OBSERVED')
        self.assertEqual(payload['observations']['count'], 0)

    def test_evidence_records_every_repository_stage(self):
        code, payload = run('evidence', REQUEST)
        self.assertEqual(code, 0)
        self.assertEqual(payload['status'], 'RECORDED')
        kinds = {row['kind'] for row in payload['evidence']}
        self.assertEqual(kinds, {'request', 'validation', 'resolution', 'placement',
                                 'capacity', 'compilation', 'plan', 'generation',
                                 'conformance'})
        self.assertTrue(all(row['authority'] == 'REPOSITORY_SIDE_ONLY'
                            for row in payload['evidence']))
        capacity = next(row for row in payload['evidence'] if row['kind'] == 'capacity')
        self.assertEqual(capacity['status'], 'HOLD_ENVELOPE_NOT_BOUND')
        self.assertEqual(capacity['details']['authority'], 'CAPACITY_OWNER')
        self.assertFalse(capacity['details']['may_allocate'])


class ApplyRefusalTest(unittest.TestCase):
    def test_apply_without_a_digest_is_refused(self):
        code, payload = run('apply', REQUEST)
        self.assertEqual(code, 2)
        self.assertEqual(payload['status'], 'REFUSED')
        self.assertEqual(payload['errors'][0]['code'], 'AUTHORITY_REQUIRED')

    def test_apply_with_a_wrong_digest_is_refused(self):
        code, payload = run('apply', REQUEST, '--approved-plan', 'f' * 64)
        self.assertEqual(code, 2)
        self.assertEqual(payload['errors'][0]['code'], 'ARTIFACT_INTEGRITY_FAILED')

    def test_apply_with_the_right_digest_but_no_approval_is_refused(self):
        code, payload = run('plan', REQUEST)
        self.assertEqual(code, 0)
        code, payload = run('apply', REQUEST, '--approved-plan', payload['digest'])
        self.assertEqual(code, 2)
        self.assertEqual(payload['errors'][0]['code'], 'AUTHORITY_REQUIRED')

    def test_apply_with_a_recorded_approval_still_refuses_execution(self):
        code, plan = run('plan', REQUEST)
        self.assertEqual(code, 0)
        with tempfile.TemporaryDirectory() as directory:
            record = Path(directory) / 'approvals.json'
            record.write_text(json.dumps({'format': 'hosting-plan-approval-set/1',
                                          'approvals': [{'plan_digest': plan['digest'],
                                                         'approved_by': 'reviewer-01',
                                                         'authority_ref': 'CHG-0001'}]}),
                              encoding='utf-8')
            code, payload = run('apply', REQUEST, '--approved-plan', plan['digest'],
                                '--approvals', str(record),
                                '--source-commit', checkout_commit())
        self.assertEqual(code, 2)
        self.assertEqual(payload['status'], 'EXECUTION_REFUSED_HANDOFF_READY')
        self.assertEqual(payload['errors'][0]['code'], 'EXECUTION_REFUSED')
        self.assertTrue(payload['blocking'])
        self.assertTrue(payload['operations'])
        self.assertFalse(payload['native_contact'])
        self.assertEqual(payload['delivery']['format'], 'hosting-delivery/1')
        self.assertEqual(payload['delivery']['source_commit'], checkout_commit())
        self.assertEqual(payload['delivery']['operation_id'], plan['operation_id'])
        self.assertEqual(payload['delivery']['generation'], plan['generation'])

    def test_an_approval_for_another_digest_is_refused(self):
        code, plan = run('plan', REQUEST)
        self.assertEqual(code, 0)
        with tempfile.TemporaryDirectory() as directory:
            record = Path(directory) / 'approvals.json'
            record.write_text(json.dumps({'approvals': [{'plan_digest': 'a' * 64,
                                                         'approved_by': 'reviewer-01',
                                                         'authority_ref': 'CHG-0002'}]}),
                              encoding='utf-8')
            code, payload = run('apply', REQUEST, '--approved-plan', plan['digest'],
                                '--approvals', str(record))
        self.assertEqual(code, 2)
        self.assertEqual(payload['errors'][0]['code'], 'AUTHORITY_REQUIRED')


class TransportTest(unittest.TestCase):
    def test_an_unknown_command_is_a_usage_error(self):
        completed = subprocess.run([sys.executable, '-m', MODULE, 'destroy', REQUEST],
                                   cwd=str(support.ROOT), capture_output=True, text=True)
        self.assertEqual(completed.returncode, 2)

    def test_a_missing_request_is_refused_with_a_syntax_error(self):
        code, payload = run('validate', 'examples/requests/does-not-exist.yaml')
        self.assertEqual(code, 2)
        self.assertEqual(payload['status'], 'REFUSED')
        self.assertEqual(payload['errors'][0]['code'], 'REQUEST_SOURCE_UNREADABLE')
        self.assertEqual(payload['errors'][0]['layer'], 'syntax')

    def test_every_command_is_discoverable_from_help(self):
        completed = subprocess.run([sys.executable, '-m', MODULE, '--help'],
                                   cwd=str(support.ROOT), capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0)
        for command in ('validate', 'resolve', 'plan', 'apply', 'status', 'verify',
                        'evidence'):
            self.assertIn(command, completed.stdout)


if __name__ == '__main__':
    unittest.main()