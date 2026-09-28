"""Bootstrap requires native effects; planning and a generic acceptance are insufficient."""
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from provisioner.execution import handoff
from tools import delivery_steps as steps, readback_core as c
from tools.run_files import digest, encoded, read_private, utcnow, write_new


SCOPE=dict(environment_key='test',site_key='site',platform='nutanix',tenant_key='tenant',wsd_key='wsd')


def campaign():
    from tools.qualify_target import ASSETS
    return dict(format='hosting-target-campaign/1',scope=SCOPE,source_commit='a'*40,
        origin='https://example.test',assets={key:{'path':'/private/'+key,'sha256':'a'*64} for key in ASSETS},
        cases=[dict(id='health',guest='vm',destination='192.0.2.2',port=443,server_name='example.test',
                    path='/health',body_sha256='b'*64,expect='allow',healthy_control=None)])


class BootstrapPostconditionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)

    def test_transition_draft_cannot_discharge_bootstrap_even_with_external_acceptance(self):
        step=dict(id='accept',kind='acceptance',needs=['draft'])
        plan=dict(scope=SCOPE,steps=[dict(id='draft',kind='platform_transition',needs=[]),step])
        accepted=dict(format='hosting-delivery-acceptance/1',plan_sha256=c.digest(plan),step_id='accept',
            scope=SCOPE,dependencies={'draft':'a'*64},purpose='bootstrap',acceptance_ref='APPROVED',
            valid_from=(utcnow()-timedelta(seconds=1)).isoformat(),valid_until=(utcnow()+timedelta(minutes=5)).isoformat())
        path=self.base/'accepted.json'; write_new(path,encoded(accepted))
        packet=dict(parameters={'purpose':'bootstrap'},dependencies=accepted['dependencies'],
                    files={'acceptance':{'path':str(path),'sha256':digest(read_private(path))}})
        with self.assertRaisesRegex(ValueError,'draft cannot satisfy'):
            steps.validate_packet(step,packet,plan,self.base)

    def test_arbitrary_acceptance_without_native_dependencies_cannot_discharge_bootstrap(self):
        with self.assertRaisesRegex(ValueError,'applied native domain'):
            steps.bootstrap_postconditions(dict(needs=[]),dict(steps=[],scope=SCOPE),self.base)

    def test_owner_success_string_cannot_substitute_for_typed_lifecycle_result(self):
        for kind in ('platform_transition','terraform_plan','terraform_approval','terraform_apply','vsphere_power'):
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError,'typed postcondition'):
                steps.typed_postcondition({'kind':kind},{'status':'SUCCESS'},self.base,{}, {})

    def test_campaign_requires_exact_cases_and_both_native_observations(self):
        plan=campaign(); raw=encoded(plan)
        result=dict(status='COLLECTED_REQUIRES_INDEPENDENT_ACCEPTANCE',scope=SCOPE,
            source_commit='a'*40,plan_sha256=digest(raw),production_qualified=False,
            started_at=(utcnow()-timedelta(seconds=2)).isoformat(),completed_at=utcnow().isoformat(),
            native_before_sha256='b'*64,native_after_sha256='c'*64,cases=[dict(id='health',passed=True)])
        steps.campaign_postcondition(result,plan,raw)
        for change in ({'cases':[]},{'cases':[dict(id='other',passed=True)]},
                       {'cases':[dict(id='health',passed=False)]},{'native_after_sha256':None},
                       {'plan_sha256':'f'*64},{'production_qualified':True}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                steps.campaign_postcondition(result|change,plan,raw)

    def test_platform_specific_graph_requires_every_vm_power_before_observation(self):
        plan=SimpleNamespace(identity=SimpleNamespace(scope=SCOPE|{'platform':'vmware'}),
            environment={'wsds':[{'tenant_key':'tenant','wsd_key':'wsd','domains':[
                {'workloads':{'first':{},'second':{}}}]}]},terraform_scopes=[])
        sequence=handoff.sequence(plan); lookup={item.id:item for item in sequence}
        powers=[item for item in sequence if item.kind=='vsphere_power']
        self.assertEqual(len(powers),2)
        self.assertNotIn('workload-bootstrap',lookup)
        for step_id in ('bootstrap-observe','bootstrap-acceptance'):
            self.assertTrue({item.id for item in powers}<=set(lookup[step_id].needs))
        reviewed=handoff.reviewed_parameters(plan)
        self.assertEqual({reviewed[item.id]['member'] for item in powers},{'first','second'})
        self.assertEqual(reviewed['guest-plan']['workload_step'],'workload-apply')
        self.assertIn('bootstrap-acceptance',lookup['guest-plan'].needs)

    def test_terraform_platforms_have_separate_review_apply_and_observe_steps(self):
        for platform in ('nutanix','openstack'):
            plan=SimpleNamespace(identity=SimpleNamespace(scope=SCOPE|{'platform':platform}))
            lookup={item.id:item for item in handoff.sequence(plan)}
            for prefix in ('bootstrap','workload-bootstrap'):
                self.assertEqual(lookup[prefix].kind,'platform_transition')
                self.assertEqual(lookup[prefix+'-plan'].needs,(prefix,))
                self.assertEqual(lookup[prefix+'-approval'].kind,'terraform_approval')
                self.assertIn(prefix+'-approval',lookup[prefix+'-apply'].needs)
            self.assertIn('workload-bootstrap-apply',lookup['bootstrap-observe'].needs)
            self.assertEqual(handoff.OPERATION_STEPS['guest-configuration'],'guest-apply')


class ExactApprovalIntegrationTests(unittest.TestCase):
    """Run the real saved-plan owner with a fake engine and an explicit gate."""
    def setUp(self):
        from tests.test_delivery_terraform import DeliveryTerraformTests
        self.fixture=DeliveryTerraformTests()
        self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        f=self.fixture
        f.plan['steps'].insert(1,dict(id='review',kind='terraform_approval',needs=['plan']))
        f.plan['steps'][-1]['needs']=['plan','review']
        (f.inbox/'plan.json').unlink()
        f.offer('plan',{},dict(catalog_id=f.args.catalog_id,terraform=str(f.binary),
            terraform_sha256=digest(f.binary.read_bytes())),
            {key:getattr(f.args,key) for key in ('inputs','backend','environment','authority')})

    def reviewed(self):
        f=self.fixture
        waiting=f.run_delivery(); self.assertEqual(waiting['step_id'],'review')
        f.authorize_apply(waiting)
        (f.inbox/'apply.json').unlink()
        f.offer('review',waiting['dependencies'],{'prepared_step':'plan'},
                {'approval':f.base/'apply-authority.json'})
        waiting=f.run_delivery(); self.assertEqual(waiting['step_id'],'apply')
        self.assertEqual(f.apply_calls,[])
        return waiting

    def test_real_saved_plan_requires_explicit_exact_approval_then_applies_once(self):
        f=self.fixture; waiting=self.reviewed()
        f.offer('apply',waiting['dependencies'],{'prepared_step':'plan'},
                {'approval':f.base/'apply-authority.json'})
        complete=f.run_delivery()
        self.assertEqual(complete['status'],'DELIVERY_EXECUTED_REQUIRES_ACCEPTANCE')
        self.assertEqual([call[0] for call in f.apply_calls],['apply','output'])
        self.assertEqual(f.run_delivery(),complete)
        self.assertEqual(len(f.apply_calls),2)

    def test_apply_cannot_substitute_another_approval_after_the_explicit_gate(self):
        from tools.run_files import load_private
        f=self.fixture; waiting=self.reviewed()
        changed=load_private(f.base/'apply-authority.json')|{'change_ref':'OTHER-APPROVAL'}
        path=f.base/'changed-approval.json'; write_new(path,encoded(changed))
        f.offer('apply',waiting['dependencies'],{'prepared_step':'plan'},{'approval':path})
        with self.assertRaisesRegex(ValueError,'explicit reviewed-plan gate'):
            f.run_delivery()
        self.assertEqual(f.apply_calls,[])


if __name__=='__main__': unittest.main()
