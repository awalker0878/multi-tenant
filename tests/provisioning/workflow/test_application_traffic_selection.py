"""Traffic cannot bypass rehearsal, current fencing and target write admission."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from provisioner.controlplane.workflow.application_selection import initial_provisioning_steps
from tests.test_application_lifecycle import lifecycle_fixture


class TrafficSelectionTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.lifecycle = lifecycle_fixture(Path(directory.name))
        self.delivery = {'steps': [
            {'id': 'guest-apply', 'kind': 'guest_apply', 'needs': []},
            {'id': 'cutover-dns', 'kind': 'dns_cutover', 'needs': ['guest-apply']},
            {'id': 'cutover-propagation', 'kind': 'dns_propagation', 'needs': ['cutover-dns']},
            {'id': 'return-dns', 'kind': 'dns_cutover', 'needs': ['cutover-propagation']},
            {'id': 'return-propagation', 'kind': 'dns_propagation', 'needs': ['return-dns']},
        ]}

    def test_initial_graph_cannot_dispatch_the_reviewed_traffic_suffix(self):
        self.assertEqual(initial_provisioning_steps(self.delivery, self.lifecycle), ('guest-apply',))

    def test_interleaved_initial_stage_and_dependency_on_traffic_are_rejected(self):
        interleaved = deepcopy(self.delivery)
        interleaved['steps'].insert(2, {'id': 'late-guest', 'kind': 'guest_apply', 'needs': []})
        dependent = deepcopy(self.delivery)
        dependent['steps'][0]['needs'] = ['cutover-dns']
        for delivery in (interleaved, dependent):
            with self.assertRaises(ValueError):
                initial_provisioning_steps(delivery, self.lifecycle)

    def test_omitted_traffic_or_wrong_fixed_owner_is_rejected(self):
        omitted = deepcopy(self.delivery)
        omitted['steps'].pop()
        wrong = deepcopy(self.delivery)
        wrong['steps'][1]['kind'] = 'guest_apply'
        for delivery in (omitted, wrong):
            with self.assertRaises(ValueError):
                initial_provisioning_steps(delivery, self.lifecycle)
