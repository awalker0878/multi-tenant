"""Execute the native-receipt compiler and transition adapters for all VM stacks."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from tests.test_compile_wsd import example,receipts
from tests.test_lifecycle_transition import fixture as platform_fixture
from tests.test_openstack_transition import fixture as openstack_fixture
from provisioner.execution import readback_core as c
from tools import delivery_steps as d, lifecycle_transition as lifecycle
from provisioner.compiler.wsd import compile_environment
from provisioner.execution.run_files import digest,encoded,load_private,read_private,utcnow,write_new


class DeliveryHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.root=Path(self.temp.name)
    def native(self,base,inputs,outputs):
        directory=base/'steps'/'native-plan'/'execution'; directory.mkdir(mode=0o700,parents=True)
        for path in (base/'steps',base/'steps'/'native-plan'): path.chmod(0o700)
        scope=outputs['scope']['value']
        bundle=dict(format='hosting-terraform-bundle/1',source_commit='a'*40,scope=scope,operation_id='fixture-native',generation=1,
                    artifacts={'inputs.json':digest(encoded(inputs))})
        result=dict(format='hosting-terraform-attempt/1',status='APPLIED_REQUIRES_NATIVE_ACCEPTANCE',scope=scope,operation_id='fixture-native',
                    generation=1,bundle_sha256=digest(encoded(bundle)),outputs_sha256=digest(encoded(outputs)),completed_at=utcnow().isoformat())
        for name,value in {'bundle.json':bundle,'result.json':result,'outputs.json':outputs,'inputs.json':inputs}.items():
            write_new(directory/name,encoded(value))
        applied=base/'steps'/'native-apply'; applied.mkdir(mode=0o700)
        write_new(applied/'packet.json',encoded({'parameters':{'prepared_step':'native-plan'}}))
        for name in ('outputs.json','result.json'): write_new(applied/name,read_private(directory/name))
        return scope
    def execute(self,base,scope,kind,parameters,files):
        step={'id':'handoff','kind':kind,'needs':['native-apply']}
        plan=dict(source_commit='a'*40,scope={k:v for k,v in scope.items() if k!='phase'},
                  steps=[{'id':'native-plan','kind':'terraform_plan','needs':[]},
                         {'id':'native-apply','kind':'terraform_apply','needs':['native-plan']},step])
        packet=dict(parameters=parameters,files={})
        for name,value in files.items():
            path=base/(name+'.json'); write_new(path,encoded(value))
            packet['files'][name]={'path':str(path),'sha256':digest(read_private(path))}
        destination=base/'steps'/'handoff'; destination.mkdir(mode=0o700)
        result,names=d.dispatch(step,packet,destination,base,plan,lifecycle.ROOT)
        return result,destination,names
    def test_three_platforms_compile_exact_native_lifecycle_transition(self):
        for platform in ('nutanix','vmware','openstack'):
            with self.subTest(platform=platform):
                base=self.root/platform; base.mkdir(mode=0o700)
                if platform=='openstack':
                    inputs,record,_=openstack_fixture(); previous=deepcopy(inputs)
                    for member in previous['members'].values(): member['lifecycle_stage']='prepared'
                else:
                    record,_=platform_fixture(platform); inputs=record['requested_inputs']; previous=record['prior_inputs']
                scope=self.native(base,previous,record['prior_outputs'])
                accepted={key:record[key] for key in ('valid_from','valid_until','acceptance_refs')}
                result,output,names=self.execute(base,scope,'platform_transition',{'prior_step':'native-apply','stage':'bootstrap'},
                                                  {'inputs':inputs,'acceptance':accepted})
                self.assertEqual(result['status'],'TRANSITION_REQUIRES_EXACT_PLAN_REVIEW')
                transition=load_private(output/'transition.json'); lifecycle.validate(transition,scope,encoded(inputs))
                self.assertEqual(transition['resources'],record['resources']); self.assertIn('owner-completion.json',names)
    def test_three_platforms_compile_workloads_from_original_domain_receipts(self):
        for platform in ('nutanix','vmware','openstack'):
            with self.subTest(platform=platform):
                base=self.root/platform; base.mkdir(mode=0o700)
                environment=example(platform)
                outputs,bindings=receipts(environment); domains,domain_scopes=compile_environment(environment)
                row=domain_scopes['scopes'][0]; native=next(iter(outputs.values()))
                scope=self.native(base,domains[row['input']],native)
                workloads,scopes=compile_environment(environment,'workloads',outputs,bindings)
                selected=scopes['scopes'][0]['input']
                files={'environment':environment}
                if platform=='vmware': files['vmware_bindings']=bindings
                result,output,_=self.execute(base,scope,'workload_inputs',{'domain_steps':['native-apply'],'selected_input':selected},files)
                self.assertEqual(result['status'],'BOUND_WORKLOAD_DRAFT_REQUIRES_REVIEW')
                actual=load_private(output/'inputs.json')
                self.assertEqual(actual,workloads[selected]); self.assertFalse(actual['allow_restricted_build'])
                provenance=load_private(output/'handoff.json')
                self.assertEqual(provenance['environment_sha256'],c.digest(environment))
                self.assertEqual(provenance['selected_scope'],{k:v for k,v in scope.items() if k!='phase'})


    def test_scoped_handoff_still_validates_other_tenant_intent_and_rejects_foreign_scope(self):
        from tools.wsd_handoff import compile_scope_runs
        environment=example('openstack'); _,scopes=compile_environment(environment)
        scope={k:v for k,v in scopes['scopes'][0]['scope'].items() if k!='phase'}
        foreign=scope|{'tenant_key':'foreign'}
        with self.assertRaisesRegex(ValueError,'absent or ambiguous'):
            compile_scope_runs(environment,[],foreign)
        bad=deepcopy(environment); bad['wsds'][1]['domains'][0]['zone']='UNKNOWN'
        with self.assertRaises(ValueError): compile_scope_runs(bad,[],scope)
        with self.assertRaisesRegex(ValueError,'Every intended WSD'):
            compile_scope_runs(environment,[],scope)


if __name__=='__main__': unittest.main()
