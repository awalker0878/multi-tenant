"""Readiness separates interpreter startup from bounded real process effects."""
import select
import unittest

from tests.provisioning.discovery.process_fixture import activate, start_prepared


class PreparedProcessTests(unittest.TestCase):
    @staticmethod
    def close(process):
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=5)

    def test_prepared_child_does_not_execute_until_explicit_activation(self):
        child = start_prepared("fixture_ready()\nprint('ACTIVE', flush=True)\n", [])
        self.addCleanup(self.close, child)
        self.assertFalse(select.select([child.stdout], [], [], .05)[0])
        activate(child)
        output, errors = child.communicate(timeout=5)
        self.assertEqual(child.returncode, 0, errors)
        self.assertEqual(output.strip(), 'ACTIVE')

    def test_unexpected_startup_output_is_not_accepted_as_readiness(self):
        with self.assertRaisesRegex(AssertionError, 'readiness'):
            start_prepared("print('NOT_READY', flush=True)\nfixture_ready()\n", [])

    def test_ready_marker_cannot_turn_a_failed_operation_into_success(self):
        child = start_prepared("fixture_ready()\nraise SystemExit(23)\n", [])
        self.addCleanup(self.close, child)
        activate(child)
        output, errors = child.communicate(timeout=5)
        self.assertEqual(child.returncode, 23)
        self.assertEqual(output, '')
        self.assertEqual(errors, '')


if __name__ == '__main__':
    unittest.main()
