"""Clone completion must bind both source entity and returned VM identity."""
from copy import deepcopy
import json
import unittest
from tests.test_vsphere_task_observe import manifest, task_body
from tests.test_vsphere_observe import ref
from tools import vsphere_task_observe as t


class CloneTaskTests(unittest.TestCase):
    def setUp(self):
        self.m = manifest(); self.record = self.m['task']['records'][0]
        self.record.update(description_id=t.CLONE, source_moid='vm-9')
        self.body = task_body(self.m) | dict(entity=ref('VirtualMachine', 'vm-9'), result=ref('VirtualMachine', 'vm-1'))
    def evaluate(self, body): return t.evaluate_task(self.record, t.task_witness(body))
    def test_success_binds_source_and_result_but_flat_profile_still_refuses_clones(self):
        self.assertTrue(self.evaluate(self.body)['task_completion_observed'])
        with self.assertRaises(ValueError): t.validate(self.m)
        for mutation in ({'entity': ref('VirtualMachine', 'vm-8')}, {'result': ref('VirtualMachine', 'vm-2')}, {'result': None}):
            self.assertEqual(self.evaluate(self.body | mutation)['progress'], 'UNKNOWN')
    def test_pending_failed_and_foreign_results_do_not_complete(self):
        self.assertEqual(self.evaluate(self.body | dict(state='running', result=None, completeTime=None))['progress'], 'PENDING')
        self.assertEqual(self.evaluate(self.body | dict(state='error', error={'message': 'PRIVATE'}))['progress'], 'FAILED')
        self.assertEqual(self.evaluate(self.body | dict(state='running', completeTime=None))['progress'], 'UNKNOWN')
        for value in ('PRIVATE', {'_typeName': 'TaskInfo', 'secret': 'PRIVATE'}, ref('Datastore', 'datastore-1'),
                      ref('VirtualMachine', 'vm-1') | {'extra': 'PRIVATE'}):
            result = self.evaluate(self.body | dict(result=value))
            self.assertEqual(result['progress'], 'UNKNOWN'); self.assertNotIn('PRIVATE', json.dumps(result))
    def test_rehashed_result_flags_cannot_claim_completion(self):
        witness = t.task_witness(self.body)
        for key, value in [('has_result', False), ('result_reference', ref('VirtualMachine', 'vm-2'))]:
            changed = deepcopy(witness); changed[key] = value
            self.assertEqual(t.evaluate_task(self.record, changed)['progress'], 'UNKNOWN')


if __name__ == '__main__': unittest.main()
