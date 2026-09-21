"""Delivery binding for brownfield adoption review; no Terraform import is executed."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

from tools import adoption, delivery_steps as steps, readback_core as c
from tools.run_files import digest, encoded, load_private, read_private, replace_private, write_new

ROOT=Path(__file__).resolve().parents[1]
SOURCE='a'*40
SCOPE={
    'environment_key':'reference','site_key':'site-01','platform':'openstack',
    'tenant_key':'tenant-01','wsd_key':'science-prod',
}


def adoption_plan():
    return {
        'format':'hosting-adoption/1',
        'source_commit':SOURCE,
        'operation_id':'adopt-delivery-01',
        'generation':1,
        'scope':dict(SCOPE),
        'state':{
            'backend_sha256':'1'*64,
            'state_key':'reference/site-01/openstack/tenant-01/science-prod/workloads',
            'backup_ref':'state-backup/17',
            'lock_ref':'state-lock/change-41',
        },
        'resources':[{
            'address':'module.owned.openstack_compute_instance_v2.workload',
            'type':'openstack_compute_instance_v2',
            'native_id':'server-17',
            'current_owner':'legacy-openstack-runbook',
            'target_owner':'terraform',
            'ownership_mode':'handover_to_terraform',
            'shared':False,
            'import_method':'terraform_import',
            'import_id':'server-17',
            'current_sha256':'2'*64,
            'desired_sha256':'2'*64,
            'delta':'no-op',
            'change_class':'routine',
            'allowed_update_fields':[],
            'discovery_ref':'inventory/server-17',
            'recovery_ref':'restore/server-17',
            'old_writer_fence_ref':'writer-handover/change-41',
        }],
    }


def evidence(value):
    return {
        'format':'hosting-adoption-evidence/1',
        'plan_sha256':c.digest(value),
        'state':{
            'backend_sha256':value['state']['backend_sha256'],
            'state_key':value['state']['state_key'],
            'backup_verified':True,
            'lock_verified':True,
            'observed_at':'2026-09-21T13:00:00+00:00',
            'evidence_ref':'state-evidence/change-41',
        },
        'resources':[{
            'address':value['resources'][0]['address'],
            'native_id':'server-17',
            'observed_sha256':'2'*64,
            'current_owner':'legacy-openstack-runbook',
            'old_writer_active':False,
            'recovery_verified':True,
            'import_supported':True,
            'plan_actions':['no-op'],
            'replacement':False,
            'delete':False,
            'exposure_change':False,
            'observed_at':'2026-09-21T13:00:00+00:00',
            'evidence_ref':'native-evidence/server-17',
        }],
    }


class DeliveryAdoptionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)
        self.directory=self.base/'review'; self.directory.mkdir(mode=0o700)
        self.plan={
            'format':'hosting-delivery/1','source_commit':SOURCE,
            'operation_id':'delivery-adoption','generation':1,'scope':dict(SCOPE),
            'steps':[{'id':'adoption','kind':'adoption_review','needs':[]}],
        }
        self.step=self.plan['steps'][0]
        self.adoption=adoption_plan()

    def packet(self):
        files={}
        values={'plan':self.adoption,'evidence':evidence(self.adoption)}
        for name,value in values.items():
            path=self.base/(name+'.json'); replace_private(path,encoded(value))
            files[name]={'path':str(path),'sha256':digest(read_private(path))}
        return {
            'format':'hosting-delivery-step/1',
            'plan_sha256':c.digest(self.plan),
            'step_id':'adoption',
            'dependencies':{},
            'parameters':{},
            'files':files,
        }

    def test_stage_emits_exact_import_handoff_without_apply_authority(self):
        packet=self.packet()
        steps.validate_packet(self.step,packet,self.plan,self.base)
        result,names=steps.dispatch(self.step,packet,self.directory,self.base,self.plan,self.base)
        self.assertEqual(result['status'],'ADOPTION_READY_FOR_EXPLICIT_IMPORT_AND_PLAN_REVIEW')
        self.assertEqual(result['imports'][0]['native_id'],'server-17')
        self.assertFalse(result['may_import_automatically'] or result['may_apply'])
        self.assertIn('adoption-review.json',names)
        self.assertIn('owner-completion.json',names)
        self.assertEqual(load_private(self.directory/'adoption-review.json')['plan_sha256'],c.digest(self.adoption))

    def test_foreign_source_or_scope_is_refused_before_review(self):
        for case in ('source','scope'):
            self.adoption=adoption_plan()
            if case=='source': self.adoption['source_commit']='b'*40
            else: self.adoption['scope']['tenant_key']='tenant-02'
            with self.subTest(case=case), self.assertRaisesRegex(ValueError,'Foreign adoption review'):
                steps.validate_packet(self.step,self.packet(),self.plan,self.base)

    def test_review_never_invokes_import_executor(self):
        packet=self.packet()
        original=adoption.evaluate
        adoption.evaluate=lambda *_args,**_kwargs: original(*_args,**_kwargs)
        try:
            result,_=steps.dispatch(self.step,packet,self.directory,self.base,self.plan,self.base)
        finally:
            adoption.evaluate=original
        self.assertFalse(result['may_import_automatically'])
        self.assertFalse((self.directory/'execution').exists())

    def test_terraform_adoption_delivery_stages_share_exact_prepared_bundle(self):
        inputs=json.loads((ROOT/'terraform/stacks/wsd/openstack/workloads/inputs.tfvars.json.example').read_text())
        inputs.update(environment_key=SCOPE['environment_key'],site_key=SCOPE['site_key'],
                      tenant_key=SCOPE['tenant_key'],wsd_key=SCOPE['wsd_key'],
                      allow_restricted_build=True,test_authorization_ref='TEST-ONLY')
        state_key='/'.join([SCOPE['environment_key'],SCOPE['site_key'],'openstack',
                            SCOPE['tenant_key'],SCOPE['wsd_key'],'workloads'])
        backend={'state_key':state_key,'address':'https://state.example.test/x',
                 'lock_address':'https://state.example.test/x/lock',
                 'unlock_address':'https://state.example.test/x/lock',
                 'lock_method':'POST','unlock_method':'DELETE'}
        adoption_plan={
            'format':'hosting-adoption/1','source_commit':SOURCE,'operation_id':'adopt-delivery-02','generation':2,
            'scope':dict(SCOPE),'state':{'backend_sha256':digest(encoded(backend)),'state_key':state_key,
                                        'backup_ref':'state-backup/2','lock_ref':'state-lock/2'},
            'resources':[{
                'address':'module.owned.openstack_compute_instance_v2.workload',
                'type':'openstack_compute_instance_v2','native_id':'server-22',
                'current_owner':'legacy-runbook','target_owner':'terraform',
                'ownership_mode':'handover_to_terraform','shared':False,
                'import_method':'terraform_import','import_id':'server-22',
                'current_sha256':'4'*64,'desired_sha256':'4'*64,'delta':'no-op',
                'change_class':'routine','allowed_update_fields':[],
                'discovery_ref':'inventory/server-22','recovery_ref':'restore/server-22',
                'old_writer_fence_ref':'writer-handover/22',
            }],
        }
        adoption_evidence={
            'format':'hosting-adoption-evidence/1','plan_sha256':c.digest(adoption_plan),
            'state':{'backend_sha256':adoption_plan['state']['backend_sha256'],'state_key':state_key,
                     'backup_verified':True,'lock_verified':True,'observed_at':'2026-09-21T13:00:00+00:00',
                     'evidence_ref':'state-evidence/22'},
            'resources':[{
                'address':adoption_plan['resources'][0]['address'],'native_id':'server-22',
                'observed_sha256':'4'*64,'current_owner':'legacy-runbook','old_writer_active':False,
                'recovery_verified':True,'import_supported':True,'plan_actions':['no-op'],
                'replacement':False,'delete':False,'exposure_change':False,
                'observed_at':'2026-09-21T13:00:00+00:00','evidence_ref':'native-evidence/22',
            }],
        }
        delivery={
            'format':'hosting-delivery/1','source_commit':SOURCE,'operation_id':'delivery-adopt-native',
            'generation':2,'scope':dict(SCOPE),
            'steps':[{'id':'adopt-plan','kind':'terraform_adoption_plan','needs':[]},
                     {'id':'adopt-apply','kind':'terraform_adoption_apply','needs':['adopt-plan']}],
        }
        binary=Path(sys.executable).resolve()
        def offer(identity,parameters,values):
            files={}
            for name,value in values.items():
                path=self.base/(identity+'-'+name+'.json')
                replace_private(path,encoded(value))
                files[name]={'path':str(path),'sha256':digest(read_private(path))}
            return {'format':'hosting-delivery-step/1','plan_sha256':c.digest(delivery),
                    'step_id':identity,'dependencies':{},'parameters':parameters,'files':files}
        prepared_packet=offer('adopt-plan',
            {'catalog_id':'openstack-wsd-workloads','terraform':str(binary),
             'terraform_sha256':digest(binary.read_bytes())},
            {'inputs':inputs,'backend':backend,'environment':{},'authority':{},
             'adoption_plan':adoption_plan,'adoption_evidence':adoption_evidence})
        steps.validate_packet(delivery['steps'][0],prepared_packet,delivery,self.base)
        upstream=self.base/'steps/adopt-plan'; execution=upstream/'execution'
        execution.mkdir(parents=True,mode=0o700)
        bundle={'format':'hosting-terraform-adoption-bundle/1','source_commit':SOURCE,
                'scope':dict(SCOPE)|{'phase':'workloads'}}
        write_new(upstream/'bundle.json',encoded(bundle)); write_new(execution/'bundle.json',encoded(bundle))
        write_new(upstream/'packet.json',encoded(prepared_packet))
        approval=self.base/'approval.json'; replace_private(approval,b'{}')
        apply_packet={'format':'hosting-delivery-step/1','plan_sha256':c.digest(delivery),
                      'step_id':'adopt-apply','dependencies':{},
                      'parameters':{'prepared_step':'adopt-plan'},
                      'files':{'approval':{'path':str(approval),'sha256':digest(read_private(approval))}}}
        steps.validate_packet(delivery['steps'][1],apply_packet,delivery,self.base)
        self.assertEqual(steps.prepared_directory(delivery['steps'][1],apply_packet,delivery,self.base),execution)


if __name__=='__main__':
    unittest.main()
