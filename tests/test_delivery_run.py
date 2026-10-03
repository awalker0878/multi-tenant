"""Durable delivery boundaries and execution through the actual owner adapters."""
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from provisioner.execution import readback_core as c
from tools import delivery_run as d, delivery_steps as s, execution_journal as j, delivery_containment as incident
from provisioner.execution.run_files import digest, encoded, load_private, read_private, replace_private, utcnow, write_new


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.base=Path(self.temp.name)
        self.inbox=self.base/'inbox'; self.inbox.mkdir(mode=0o700)
        self.ledger=self.base/'ledger'; self.ledger.mkdir(mode=0o700)
        self.plan=dict(format='hosting-delivery/2',source_commit='a'*40,operation_id='op-test',generation=1,reviewed_plan_digest='0'*64,
            scope=dict(environment_key='lab',site_key='site-01',platform='openstack',tenant_key='tenant-01',wsd_key='wsd-01'),
            steps=[{'id':'admit','kind':'acceptance','needs':[]},{'id':'ready','kind':'acceptance','needs':['admit']}], operation_bindings={},reviewed_parameters={},compiled_catalog_ids={})
        self.source=patch.object(d,'verify',return_value={'status':'HASHES_MATCH','commit':'a'*40})
        self.source.start(); self.addCleanup(self.source.stop)
    def run_delivery(self): return d.run(self.plan,self.inbox,self.ledger,execute=True)
    def offer(self, identity, dependencies, purpose='admission'):
        record=dict(format='hosting-delivery-acceptance/1',plan_sha256=c.digest(self.plan),step_id=identity,
            scope=self.plan['scope'],dependencies=dependencies,purpose=purpose,
            valid_from=(utcnow()-timedelta(minutes=1)).isoformat(),valid_until=(utcnow()+timedelta(minutes=20)).isoformat(),acceptance_ref='TEST-ONLY')
        path=self.base/(identity+'-acceptance-'+str(self.plan['generation'])+'.json'); write_new(path,encoded(record))
        packet=dict(format='hosting-delivery-step/1',plan_sha256=c.digest(self.plan),step_id=identity,dependencies=dependencies,
            parameters={'purpose':purpose},files={'acceptance':{'path':str(path),'sha256':digest(read_private(path))}})
        replace_private(self.inbox/(identity+'.json'),encoded(packet)); return path
    def first(self):
        self.offer('admit',{}); return self.run_delivery()
    def test_missing_inputs_resumes_completed_steps_without_dispatch(self):
        waiting=self.run_delivery(); self.assertEqual(waiting['step_id'],'admit')
        waiting=self.first(); self.assertEqual(waiting['step_id'],'ready')
        self.offer('ready',waiting['dependencies'],'services')
        complete=self.run_delivery(); self.assertEqual(complete['status'],'DELIVERY_EXECUTED_REQUIRES_ACCEPTANCE')
        with patch.object(s,'dispatch',side_effect=AssertionError('replayed owner')):
            self.assertEqual(self.run_delivery(),complete)
        self.assertFalse(complete['native_acceptance']); self.assertFalse(complete['production_activation'])
    def test_wrong_dependency_input_or_receipt_bytes_hold_before_next_owner(self):
        waiting=self.first(); path=self.offer('ready',{'admit':'0'*64})
        with self.assertRaises(ValueError): self.run_delivery()
        value=load_private(self.inbox/'ready.json'); value['dependencies']=waiting['dependencies']
        replace_private(self.inbox/'ready.json',encoded(value)); path.write_bytes(read_private(path)+b' ')
        with self.assertRaises(ValueError): self.run_delivery()
        original=next(self.ledger.glob('*/runs/*/steps/admit/acceptance.json'))
        original.write_bytes(read_private(original)+b' ')
        with self.assertRaisesRegex(ValueError,'evidence changed'): self.run_delivery()
    def test_crash_after_owner_completion_recovers_without_reissuing(self):
        self.offer('admit',{}); append=j.Journal.append
        def fail(log,kind,data):
            if kind=='STEP_COMPLETED': raise InterruptedError('crash after owner completion')
            return append(log,kind,data)
        with patch.object(j.Journal,'append',new=fail),self.assertRaises(InterruptedError): self.run_delivery()
        with patch.object(s,'dispatch',side_effect=AssertionError('owner replayed')):
            self.assertEqual(self.run_delivery()['step_id'],'ready')
    def test_unknown_owner_outcome_and_new_operation_remain_held(self):
        self.offer('admit',{})
        with patch.object(s,'dispatch',side_effect=InterruptedError('owner unknown')),self.assertRaises(InterruptedError): self.run_delivery()
        with patch.object(s,'dispatch',side_effect=AssertionError('owner replayed')),self.assertRaises(OSError): self.run_delivery()
        self.plan['operation_id']='renamed'; self.plan['generation']=2
        with self.assertRaisesRegex(ValueError,'held scope'): self.run_delivery()
    def test_complete_generation_allows_new_plan_with_shared_owner_ledgers(self):
        self.plan['steps']=self.plan['steps'][:1]; self.offer('admit',{}); self.run_delivery()
        firstbase=next(self.ledger.glob('*/runs/*')); owner=s.owner_ledger(firstbase,'terraform')
        self.plan['generation']=2; self.plan['operation_id']='next-change'; self.offer('admit',{}); self.run_delivery()
        bases=list(self.ledger.glob('*/runs/*')); self.assertEqual(len(bases),2)
        self.assertEqual(s.owner_ledger(bases[-1],'terraform'),owner)
    def test_expired_transitive_gate_blocks_downstream_work(self):
        waiting=self.first(); self.offer('ready',waiting['dependencies'],'services')
        with patch.object(d,'current_window',side_effect=ValueError('expired gate')):
            with self.assertRaises(ValueError): self.run_delivery()
        self.assertFalse(any(self.ledger.glob('*/runs/*/steps/ready/owner-completion.json')))
    def test_gate_renewal_binds_original_dependencies_without_reexecuting_gate(self):
        waiting=self.first(); self.offer('ready',waiting['dependencies'],'services')
        renewal=load_private(next(self.ledger.glob('*/runs/*/steps/admit/acceptance.json')))
        renewal['acceptance_ref']='TEST-RENEWED'; write_new(self.inbox/'admit.renewal.json',encoded(renewal))
        self.assertEqual(self.run_delivery()['status'],'DELIVERY_EXECUTED_REQUIRES_ACCEPTANCE')
        events=[load_private(p) for p in self.ledger.glob('*/*.json')]
        self.assertEqual(len([e for e in events if e['kind']=='GATE_RENEWED']),1)
        self.assertEqual(self.run_delivery()['status'],'DELIVERY_EXECUTED_REQUIRES_ACCEPTANCE')
    def test_gate_renewal_cannot_replace_scope_or_predecessor_evidence(self):
        waiting=self.first(); self.offer('ready',waiting['dependencies'],'services')
        renewal=load_private(next(self.ledger.glob('*/runs/*/steps/admit/acceptance.json')))
        renewal['scope']['tenant_key']='foreign'; write_new(self.inbox/'admit.renewal.json',encoded(renewal))
        with self.assertRaisesRegex(ValueError,'gate or dependency scope'): self.run_delivery()
    def test_source_opt_in_graph_and_arbitrary_execution_are_rejected(self):
        with self.assertRaises(ValueError): d.run(self.plan,self.inbox,self.ledger)
        for mutation in (lambda x:x['steps'][0].update(kind='shell'),lambda x:x['steps'][0].update(needs=['ready']),
                         lambda x:x['steps'][1].update(needs=[]),lambda x:x.update(generation=True)):
            value=deepcopy(self.plan); mutation(value)
            with self.assertRaises(ValueError): d.validate(value)
        with patch.object(d,'verify',return_value={'status':'FAILED_INTEGRITY_CHECK'}),self.assertRaises(ValueError): self.run_delivery()
    def test_packet_cannot_change_reviewed_parameter_after_approval(self):
        self.plan['reviewed_parameters']={'admit':{'purpose':'admission'}}
        self.offer('admit',{},'services')
        with self.assertRaisesRegex(ValueError,'approved reviewed parameters'):
            self.run_delivery()
        self.assertFalse(any(self.ledger.glob('*/runs/*/steps/*/packet.json')))

    def test_malformed_packet_does_not_reserve_an_attempt(self):
        self.offer('admit',{}); path=self.inbox/'admit.json'; value=load_private(path)
        value['parameters']['command']='arbitrary'; replace_private(path,encoded(value))
        with self.assertRaises(ValueError): self.run_delivery()
        self.assertFalse(any(self.ledger.glob('*/runs/*/steps/*/packet.json')))
    def test_selected_owner_failure_invokes_delegated_containment_and_keeps_hold(self):
        self.offer('admit',{})
        with patch.object(incident,'validate'),patch.object(incident,'execute') as contained,\
             patch.object(s,'dispatch',side_effect=ValueError('native verification failed')):
            with self.assertRaisesRegex(ValueError,'native verification failed'):
                d.run(self.plan,self.inbox,self.ledger,execute=True,containment={'trigger_steps':['admit']})
            self.assertEqual(contained.call_count,1)
            self.assertEqual(contained.call_args.args[2],'admit')
        self.assertFalse(any(self.ledger.glob('*/runs/*/steps/admit/owner-completion.json')))
    def test_missing_post_verification_inputs_contain_instead_of_leaving_exposure(self):
        with patch.object(incident,'validate'),patch.object(incident,'execute') as contained:
            result=d.run(self.plan,self.inbox,self.ledger,execute=True,containment={'trigger_steps':['admit']})
            self.assertEqual(result['status'],'WAITING_STAGE_INPUTS_CONTAINED'); self.assertEqual(contained.call_count,1)
    def test_unselected_failure_and_failed_containment_cannot_advance_workflow(self):
        self.offer('admit',{})
        with patch.object(incident,'validate'),patch.object(incident,'execute',side_effect=OSError('containment unavailable')) as contained,\
             patch.object(s,'dispatch',side_effect=ValueError('original failure')):
            with self.assertRaisesRegex(ValueError,'original failure'):
                d.run(self.plan,self.inbox,self.ledger,execute=True,containment={'trigger_steps':['ready']})
            self.assertEqual(contained.call_count,0)


if __name__=='__main__': unittest.main()
