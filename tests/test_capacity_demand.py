"""Actual sizing, SQLite admission and Terraform delivery pre-contact gates."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import test_capacity as harness
from tools import capacity,capacity_demand as demand,delivery_run as delivery,delivery_steps as steps,readback_core as c
from tools.run_files import digest,encoded,load_private,read_private,replace_private,write_new

ROOT=Path(__file__).resolve().parents[1]


def fixture(platform,scope):
    inputs=json.loads((ROOT/f'terraform/stacks/wsd/{platform}/workloads/inputs.tfvars.json.example').read_text())
    inputs.update({k:v for k,v in scope.items() if k!='platform'},allow_restricted_build=True,test_authorization_ref='TEST-ONLY')
    placement={key:inputs['members']['processor-01'][key] for key in demand.PLACEMENT[platform]}
    catalog={'format':'hosting-capacity-sizing/1','pool_id':'pool-01','origin':'https://native.example.invalid',
        'native_id':'native-pool-01','platform':platform,'site_key':scope['site_key'],'placements':[placement],
        'provider_selector':{key:inputs[key] for key in ['openstack_cloud' if platform=='openstack' else 'platform_endpoint']},
        'cloud_sha256':digest(encoded({})) if platform=='openstack' else None,
        'flavors':{'mock-flavor':{'vcpu':2,'ram_mib':4096,'root_gib':0,'ephemeral_gib':0,'swap_mib':0}} if platform=='openstack' else {},
        **harness.window(),'acceptance_ref':'TEST-NATIVE-SIZING'}
    return inputs,catalog


class CapacityDemandTests(unittest.TestCase):
    authority=harness.CapacityTests.authority
    def setUp(self):
        harness.CapacityTests.setUp(self); self.base=Path(self.temp.name)
        self.inputs,self.catalog=fixture('openstack',self.request['scope'])
        self.request['units']=demand.derive(self.inputs,self.catalog)['units']
        self.inbox=self.base/'inbox'; self.inbox.mkdir(mode=0o700)
        self.ledger=self.base/'delivery'; self.ledger.mkdir(mode=0o700)
        self.plan={'format':'hosting-delivery/2','source_commit':'a'*40,'operation_id':'delivery-01','generation':1,
            'reviewed_plan_digest':'0'*64,'scope':self.request['scope'],'steps':[{'id':'reserve','kind':'capacity','needs':[]},
            {'id':'plan','kind':'terraform_plan','needs':['reserve']},{'id':'apply','kind':'terraform_apply','needs':['plan']}], 'operation_bindings':{},'reviewed_parameters':{},'compiled_catalog_ids':{}}
        self.offer('reserve',{}, {'action':'reserve','database':str(self.path)},
            {'request':self.request,'authority':self.authority('reserve'),'inputs':self.inputs,'sizing':self.catalog})
        source=patch.object(delivery,'verify',return_value={'status':'HASHES_MATCH','commit':'a'*40})
        source.start(); self.addCleanup(source.stop)
    def offer(self,identity,dependencies,parameters,values):
        files={}
        for name,value in values.items():
            path=self.base/(identity+'-'+name+'.json'); replace_private(path,encoded(value))
            files[name]={'path':str(path),'sha256':digest(read_private(path))}
        packet={'format':'hosting-delivery-step/1','plan_sha256':c.digest(self.plan),'step_id':identity,
            'dependencies':dependencies,'parameters':parameters,'files':files}
        replace_private(self.inbox/(identity+'.json'),encoded(packet)); return packet
    def run_delivery(self): return delivery.run(self.plan,self.inbox,self.ledger,execute=True)
    def test_all_platforms_charge_declared_bytes_and_defaults_consistently(self):
        for platform in demand.PLACEMENT:
            inputs,catalog=fixture(platform,self.request['scope']|{'platform':platform})
            actual=demand.derive(inputs,catalog)
            self.assertEqual(actual['units'],{'vcpu':2,'memory_mb':4295,'storage_gb':43})
            if platform!='openstack':
                inputs['members']['processor-01'].update(vcpu=None,memory_gib=None,boot_disk_gib=None,data_disk_gib=None)
                self.assertEqual(demand.derive(inputs,catalog),actual)
            inputs['members']['second']=deepcopy(inputs['members']['processor-01'])
            self.assertEqual(demand.derive(inputs,catalog)['units'],{'vcpu':4,'memory_mb':8590,'storage_gb':86})
    def test_unknown_flavors_nonvolume_disks_wrong_placement_and_undercharge_hold(self):
        for mutate in (lambda i,s:i['members']['processor-01'].update(flavor_id='unknown'),
                       lambda i,s:i['members']['processor-01'].update(volume_type='another-pool'),
                       lambda i,s:i.update(openstack_cloud='foreign-cloud'),
                       lambda i,s:s['flavors']['mock-flavor'].update(ephemeral_gib=1),
                       lambda i,s:i['members']['processor-01'].update(boot_disk_gib=True)):
            inputs=deepcopy(self.inputs); catalog=deepcopy(self.catalog); mutate(inputs,catalog)
            with self.assertRaises(ValueError): demand.derive(inputs,catalog)
        with self.assertRaisesRegex(ValueError,'smaller than actual'):
            demand.bind_request(self.request|{'units':harness.units(2,4096,40)},self.inputs,self.catalog)
        with self.assertRaisesRegex(ValueError,'another native pool'):
            demand.owner_binding(self.path,self.request,self.catalog|{'native_id':'foreign'},require_live=False)
    def test_reservation_crash_recovers_from_database_without_second_mutation(self):
        with patch.object(steps,'complete',side_effect=InterruptedError('coordinator lost')):
            with self.assertRaises(InterruptedError): self.run_delivery()
        with patch.object(capacity,'event',side_effect=AssertionError('capacity mutated again')):
            self.assertEqual(self.run_delivery()['step_id'],'plan')
        base=next(self.ledger.glob('*/runs/*'))
        self.assertEqual(load_private(base/'steps/reserve/demand.json')['units'],self.request['units'])
    def test_changed_workload_is_rejected_before_terraform_preparation(self):
        waiting=self.run_delivery(); changed=deepcopy(self.inputs)
        changed['members']['processor-01']['data_disk_gib']=1
        binary=Path(sys.executable).resolve()
        self.offer('plan',waiting['dependencies'],{'catalog_id':'openstack-wsd-workloads','terraform':str(binary),
            'terraform_sha256':digest(binary.read_bytes())},{'inputs':changed,'backend':{},'environment':{},'authority':{},'cloud':{}})
        from tools import terraform_run
        with patch.object(terraform_run,'prepare',side_effect=AssertionError('native contact')) as native:
            with self.assertRaises(ValueError): self.run_delivery()
        self.assertEqual(native.call_count,0)
    def test_released_reservation_blocks_both_saved_plan_and_apply(self):
        waiting=self.run_delivery(); base=next(self.ledger.glob('*/runs/*'))
        binary=Path(sys.executable).resolve()
        packet=self.offer('plan',waiting['dependencies'],{'catalog_id':'openstack-wsd-workloads','terraform':str(binary),
            'terraform_sha256':digest(binary.read_bytes())},{'inputs':self.inputs,'backend':{},'environment':{},'authority':{},'cloud':{}})
        steps.validate_packet(self.plan['steps'][1],packet,self.plan,base)
        with self.assertRaisesRegex(ValueError,'cloud configuration differs'):
            demand.check_ancestors(self.plan['steps'][1],self.plan,base,self.inputs,cloud_sha256='0'*64)
        prepared=base/'steps/plan'; prepared.mkdir(mode=0o700); (prepared/'execution').mkdir(mode=0o700)
        bundle={'scope':self.plan['scope']|{'phase':'workloads'},'source_commit':'a'*40}
        for path in [prepared/'bundle.json',prepared/'execution/bundle.json']: write_new(path,encoded(bundle))
        write_new(prepared/'execution/inputs.json',encoded(self.inputs))
        write_new(prepared/'execution/contact.json',encoded({'cloud_sha256':self.catalog['cloud_sha256']}))
        approval=self.base/'approval.json'; write_new(approval,b'{}')
        apply={'parameters':{'prepared_step':'plan'},'files':{'approval':{'path':str(approval),'sha256':digest(b'{}')}}}
        steps.validate_packet(self.plan['steps'][2],apply,self.plan,base)
        current=capacity.operate(self.path,self.request,'inspect',None)
        capacity.operate(self.path,self.request,'release',self.authority('release',previous=current))
        for step,stage in [(self.plan['steps'][1],packet),(self.plan['steps'][2],apply)]:
            with self.assertRaisesRegex(ValueError,'missing, changed or released'):
                steps.validate_packet(step,stage,self.plan,base)


if __name__=='__main__': unittest.main()
