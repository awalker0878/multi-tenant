"""Delivery binding for brownfield adoption review; no Terraform import is executed."""
from pathlib import Path
import tempfile
import unittest

from tools import adoption, delivery_steps as steps, readback_core as c
from tools.run_files import digest, encoded, load_private, read_private, write_new

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
            path=self.base/(name+'.json'); write_new(path,encoded(value))
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


if __name__=='__main__':
    unittest.main()
