"""Containment guard respects explicit non-withdrawal operations holds."""
from pathlib import Path
import unittest
from unittest.mock import patch

from tools import delivery_containment as d
from tools.operations_review import OperationsHold


class DeliveryContainmentGuardTests(unittest.TestCase):
    def setUp(self):
        self.config={'trigger_steps':['operations']}
        self.plan={'scope':{'environment_key':'reference'}}
        self.context={'base':Path('/private/run'),'step_id':'operations'}

    def test_noncontainment_operations_hold_does_not_withdraw(self):
        with patch.object(d,'execute') as execute:
            with self.assertRaises(OperationsHold):
                with d.guard(self.config,self.plan,self.context,Path('/repo')):
                    raise OperationsHold('benign drift',containment_required=False)
        execute.assert_not_called()

    def test_security_operations_hold_invokes_containment(self):
        with patch.object(d,'execute',return_value={'status':'CONTAINED_OBSERVED_NOT_QUALIFIED'}) as execute:
            with self.assertRaises(OperationsHold):
                with d.guard(self.config,self.plan,self.context,Path('/repo')):
                    raise OperationsHold('security drift',containment_required=True)
        execute.assert_called_once_with(self.config,self.plan,'operations',Path('/private/run'),Path('/repo'))

    def test_ordinary_failure_remains_containment_eligible(self):
        with patch.object(d,'execute',return_value={'status':'CONTAINED_OBSERVED_NOT_QUALIFIED'}) as execute:
            with self.assertRaisesRegex(ValueError,'synthetic'):
                with d.guard(self.config,self.plan,self.context,Path('/repo')):
                    raise ValueError('synthetic')
        execute.assert_called_once()


if __name__=='__main__':
    unittest.main()
