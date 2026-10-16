"""Prevent an invalid or expired probe from earning isolated fencing evidence."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts/p06'))
from live_execution import epoch_isolation


class LiveEpochControls(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.lifecycle = Path(self.directory.name)/'lifecycle'
        self.simulator = Path(self.directory.name)/'simulator'
        for file in (self.lifecycle, self.simulator):
            file.write_text('original-epoch')
        self.grant = {'epoch': 'original-epoch', 'expires_at': 101}
        self.count, self.requests, self.checks = 0, [], []

    def check(self, name, value):
        self.checks.append(name)
        if not value:
            raise RuntimeError(name)

    def send(self, grant):
        self.assertIs(grant, self.grant)
        state = (self.lifecycle.read_text(), self.simulator.read_text())
        self.requests.append(state)
        if state != ('original-epoch', 'original-epoch'):
            self.assertEqual(state.count('original-epoch'), 1)
            return 403, {}
        duplicate = self.count > 0
        self.count = 1
        return 200, {'accepted': True, 'duplicate': duplicate}

    def run_probe(self, send=None):
        return epoch_isolation(self.grant, self.lifecycle, self.simulator,
                               send or self.send, lambda: self.count, self.check)

    def test_same_fresh_grant_is_denied_by_each_fence_then_accepted_once(self):
        with patch('live_execution.time.time', return_value=100):
            proof = self.run_probe()
        self.assertEqual([row['owner'] for row in proof['negative_controls']],
                         ['effect-owner', 'journal-owner'])
        self.assertEqual(proof['effects_after_positive'], 1)
        self.assertFalse(proof['restore_reenable_authorized'])
        self.assertEqual(len(self.requests), 4)

    def test_expiry_dependency_failure_and_accidental_acceptance_cannot_prove_fence(self):
        for status in (200, 401, 404, 422, 503):
            with self.subTest(status=status), patch('live_execution.time.time', return_value=100):
                with self.assertRaisesRegex(RuntimeError, 'epoch-alone-denies'):
                    self.run_probe(lambda grant: (status, {}))
            for file in (self.lifecycle, self.simulator):
                self.assertEqual(file.read_text(), 'original-epoch')
        with patch('live_execution.time.time', return_value=101):
            with self.assertRaisesRegex(RuntimeError, 'unexpired-before'):
                self.run_probe()
        self.assertEqual(self.requests, [])

    def test_expiring_during_denial_cannot_prove_epoch(self):
        with patch('live_execution.time.time', side_effect=[100, 101]):
            with self.assertRaisesRegex(RuntimeError, 'unexpired-after'):
                self.run_probe()
        self.assertEqual(self.simulator.read_text(), 'original-epoch')

    def test_denied_request_with_a_write_fails_and_restores_fault_mounts(self):
        def mutate(grant):
            self.count += 1
            return 403, {}
        with patch('live_execution.time.time', return_value=100):
            with self.assertRaisesRegex(RuntimeError, 'epoch-alone-denies'):
                self.run_probe(mutate)
        self.assertEqual(self.simulator.read_text(), 'original-epoch')

    def test_all_denials_without_a_positive_control_are_unqualified(self):
        with patch('live_execution.time.time', return_value=100):
            with self.assertRaisesRegex(RuntimeError, 'same-grant-positive-control$'):
                self.run_probe(lambda grant: (403, {}))
        self.assertEqual(self.lifecycle.read_text(), 'original-epoch')

    def test_cannot_run_against_an_already_changed_epoch(self):
        self.lifecycle.write_text('restored-epoch')
        with self.assertRaisesRegex(RuntimeError, 'requires_current_custody'):
            self.run_probe()
        self.assertEqual(self.lifecycle.read_text(), 'restored-epoch')


if __name__ == '__main__':
    unittest.main()
