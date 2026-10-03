"""Delivery drives the real saved-plan preparation/apply code with a fake engine."""
from datetime import timedelta
from pathlib import Path
import unittest
from unittest.mock import patch
from tests.test_terraform_run import TerraformRunFixture
from provisioner.execution import terraform_run as tr, terraform_apply as ta
from tools import delivery_run as d, delivery_steps as s
from provisioner.execution import readback_core as c
from provisioner.compiler.wsd import STATE
from provisioner.execution.run_files import digest, encoded, load_private, read_private, utcnow, write_new


class DeliveryTerraformTests(TerraformRunFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.inbox=self.base/'inbox'; self.inbox.mkdir(mode=0o700)
        self.ledger=self.base/'delivery-ledger'; self.ledger.mkdir(mode=0o700)
        self.plan=dict(format='hosting-delivery/2',source_commit=self.source,operation_id='delivery-01',generation=1,reviewed_plan_digest='0'*64,
            scope={k:v for k,v in self.scope.items() if k!='phase'},
            steps=[dict(id='plan',kind='terraform_plan',needs=[]),dict(id='apply',kind='terraform_apply',needs=['plan'])], operation_bindings={},reviewed_parameters={},compiled_catalog_ids={})
        self.offer('plan',{},dict(catalog_id=self.args.catalog_id,terraform=str(self.binary),terraform_sha256=digest(self.binary.read_bytes())),
                   {key:getattr(self.args,key) for key in ('inputs','backend','environment','authority')})
        self.apply_calls=[]
    def offer(self,identity,dependencies,parameters,files):
        packet=dict(format='hosting-delivery-step/1',plan_sha256=c.digest(self.plan),step_id=identity,dependencies=dependencies,
            parameters=parameters,files={k:{'path':str(v),'sha256':digest(read_private(v))} for k,v in files.items()})
        write_new(self.inbox/(identity+'.json'),encoded(packet))
    def prep_engine(self,binary,directory,argv,environment,output,**kwargs):
        self.args.output=output.parent
        return self.engine(binary,directory,argv,environment,output,**kwargs)
    def apply_engine(self,binary,directory,argv,environment,output,**kwargs):
        self.apply_calls.append(argv)
        outputs={'scope':{'value':self.scope},'delivery_state':{'value':STATE},
                 'members':{'value':{key:{'delivery_state':STATE,'vpc_id':'fixture-only'} for key in self.inputs['members']}}}
        write_new(output,encoded(outputs) if argv[0]=='output' else b'fake-engine-apply\n')
    def run_delivery(self):
        source={'status':'HASHES_MATCH','commit':self.source}
        with patch.object(d,'verify',return_value=source),patch.object(tr,'verify',return_value=source),\
             patch.object(ta,'verify',return_value=source),patch.object(tr,'snapshot',side_effect=self.snapshot),\
             patch.object(tr,'command',side_effect=self.prep_engine),patch.object(ta,'command',side_effect=self.apply_engine):
            return d.run(self.plan,self.inbox,self.ledger,execute=True)
    def authorize_apply(self,waiting):
        prepared=next(self.ledger.glob('*/runs/*/steps/plan/execution')); bundle=load_private(prepared/'bundle.json')
        approval=dict(format='hosting-terraform-approval/1',bundle_sha256=digest(read_private(prepared/'bundle.json')),
            review_sha256=digest(read_private(prepared/'review.json')),operation_id=bundle['operation_id'],generation=bundle['generation'],
            valid_from=(utcnow()-timedelta(seconds=1)).isoformat(),valid_until=(utcnow()+timedelta(minutes=10)).isoformat(),change_ref='TEST-APPLY')
        write_new(self.base/'apply-authority.json',encoded(approval))
        self.offer('apply',waiting['dependencies'],{'prepared_step':'plan'},{'approval':self.base/'apply-authority.json'})
        return prepared
    def test_prepare_review_apply_outputs_and_resume_preserve_one_native_apply(self):
        waiting=self.run_delivery(); self.assertEqual(waiting['step_id'],'apply')
        prepared=self.authorize_apply(waiting)
        completed=self.run_delivery(); self.assertEqual(completed['status'],'DELIVERY_EXECUTED_REQUIRES_ACCEPTANCE')
        self.assertEqual([v[0] for v in self.calls],['version','init','plan','show'])
        self.assertEqual([v[0] for v in self.apply_calls],['apply','output'])
        self.assertEqual(self.apply_calls[0][-1],str(prepared/'saved.tfplan'))
        self.assertEqual(self.run_delivery(),completed)
        self.assertEqual(len(self.apply_calls),2)
        self.assertTrue(list((self.ledger/'owners'/'terraform').glob('*/*.started.json')))
    def test_substituted_prepared_bundle_rejected_before_native_apply(self):
        waiting=self.run_delivery(); prepared=self.authorize_apply(waiting)
        bundle=load_private(prepared/'bundle.json'); bundle['scope']['tenant_key']='foreign'
        (prepared/'bundle.json').write_bytes(encoded(bundle))
        with self.assertRaisesRegex(ValueError,'bundle changed'): self.run_delivery()
        self.assertEqual(self.apply_calls,[])
    def test_owner_interruption_is_not_replayed_by_coordinator(self):
        waiting=self.run_delivery(); self.authorize_apply(waiting)
        original=self.apply_engine
        def broken(*args,**kwargs):
            original(*args,**kwargs)
            raise InterruptedError('controller lost')
        self.apply_engine=broken
        with self.assertRaises(InterruptedError): self.run_delivery()
        with self.assertRaisesRegex(ValueError,'incomplete or uncertain'): self.run_delivery()
        self.assertEqual(len(self.apply_calls),1)
    def test_completed_owner_recovers_when_coordinator_marker_was_never_written(self):
        waiting=self.run_delivery(); self.authorize_apply(waiting)
        with patch.object(s,'complete',side_effect=InterruptedError('crash before marker')),self.assertRaises(InterruptedError): self.run_delivery()
        self.assertEqual(len(self.apply_calls),2)
        self.assertEqual(self.run_delivery()['status'],'DELIVERY_EXECUTED_REQUIRES_ACCEPTANCE')
        self.assertEqual(len(self.apply_calls),2)


if __name__=='__main__': unittest.main()
