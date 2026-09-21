"""Terraform brownfield adoption plan and writer-fence tests."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from tools import readback_core as c, terraform_adoption as t, terraform_apply
from tools.run_files import digest, encoded, replace_private, write_new


SCOPE={
    'environment_key':'reference','site_key':'site-01','platform':'vmware',
    'tenant_key':'tenant-01','wsd_key':'science-prod','phase':'workloads',
}


def review():
    desired_a={'name':'app-a','num_cpus':2,'memory':4096}
    desired_b={'name':'app-b','num_cpus':4,'memory':8192}
    return {
        'status':'ADOPTION_READY_FOR_EXPLICIT_IMPORT_AND_PLAN_REVIEW',
        'imports':[
            {'address':'module.owned.vm.a','type':'vsphere_virtual_machine','native_id':'vm-1','import_id':'vm-1',
             'current_sha256':c.digest(desired_a),'desired_sha256':c.digest(desired_a),
             'old_writer_fence_ref':'fence/1','discovery_ref':'inventory/1','recovery_ref':'restore/1',
             'evidence_ref':'evidence/1'},
            {'address':'module.owned.vm.b','type':'vsphere_virtual_machine','native_id':'vm-2','import_id':'vm-2',
             'current_sha256':'9'*64,'desired_sha256':c.digest(desired_b),
             'old_writer_fence_ref':'fence/2','discovery_ref':'inventory/2','recovery_ref':'restore/2',
             'evidence_ref':'evidence/2'},
        ],
        'explicit_deltas':[
            {'address':'module.owned.vm.b','change_class':'routine',
             'allowed_update_fields':['memory','num_cpus']},
        ],
    }


def change(address,after,actions,before=None,kind='vsphere_virtual_machine'):
    return {
        'address':address,'mode':'managed','type':kind,
        'provider_name':'registry.terraform.io/hashicorp/vsphere',
        'change':{
            'actions':actions,
            'before':before,
            'after':after,
            'after_unknown':{},
            'before_sensitive':{},
            'after_sensitive':{},
        },
    }


def tfplan(changes):
    return {
        'format_version':'1.2','terraform_version':'1.14.0','complete':True,'errored':False,
        'variables':{},'planned_values':{},'resource_changes':changes,'resource_drift':[],
        'configuration':{},'checks':[],
    }


class TerraformAdoptionTests(unittest.TestCase):
    def test_pre_import_requires_exact_configured_creates(self):
        r=review()
        plan=tfplan([
            change('module.owned.vm.a',{'name':'app-a','num_cpus':2,'memory':4096},['create']),
            change('module.owned.vm.b',{'name':'app-b','num_cpus':4,'memory':8192},['create']),
            change('module.other.noop',{'name':'stable'},['no-op'],{'name':'stable'}),
        ])
        self.assertEqual(t.validate_pre_plan(plan,r),['module.owned.vm.a','module.owned.vm.b'])

    def test_pre_import_rejects_unrelated_change_missing_target_and_wrong_desired_shape(self):
        base=tfplan([
            change('module.owned.vm.a',{'name':'app-a','num_cpus':2,'memory':4096},['create']),
            change('module.owned.vm.b',{'name':'app-b','num_cpus':4,'memory':8192},['create']),
        ])
        for case in ('unrelated','missing','desired'):
            plan=deepcopy(base)
            if case=='unrelated':
                plan['resource_changes'].append(change('module.other.change',{'x':2},['update'],{'x':1}))
            elif case=='missing':
                plan['resource_changes'].pop()
            else:
                plan['resource_changes'][0]['change']['after']['memory']=2048
            with self.subTest(case=case), self.assertRaises(ValueError):
                t.validate_pre_plan(plan,review())

    def test_post_import_accepts_noop_and_bounded_explicit_update(self):
        r=review()
        plan=tfplan([
            change('module.owned.vm.a',{'name':'app-a','num_cpus':2,'memory':4096},['no-op'],
                   {'name':'app-a','num_cpus':2,'memory':4096}),
            change('module.owned.vm.b',{'name':'app-b','num_cpus':4,'memory':8192},['update'],
                   {'name':'app-b','num_cpus':2,'memory':4096}),
            change('module.other.noop',{'name':'stable'},['no-op'],{'name':'stable'}),
        ])
        self.assertEqual(t.validate_post_plan(plan,r),['module.owned.vm.a','module.owned.vm.b'])

    def test_post_import_blocks_create_delete_replace_and_unreviewed_field(self):
        base=tfplan([
            change('module.owned.vm.a',{'name':'app-a','num_cpus':2,'memory':4096},['no-op'],
                   {'name':'app-a','num_cpus':2,'memory':4096}),
            change('module.owned.vm.b',{'name':'app-b','num_cpus':4,'memory':8192},['update'],
                   {'name':'app-b','num_cpus':2,'memory':4096}),
        ])
        for case in ('create','delete','replace','field'):
            plan=deepcopy(base)
            if case=='create':
                plan['resource_changes'][0]['change']['actions']=['create']
            elif case=='delete':
                plan['resource_changes'][0]['change']['actions']=['delete']
            elif case=='replace':
                plan['resource_changes'][0]['change']['actions']=['delete','create']
            else:
                plan['resource_changes'][1]['change']['after']['name']='renamed'
            with self.subTest(case=case), self.assertRaises(ValueError):
                t.validate_post_plan(plan,review())

    def test_incomplete_adoption_attempt_blocks_normal_terraform_writer(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger=Path(tmp); ledger.chmod(0o700)
            address='https://state.example.test/project/state/scope'
            scope=ledger/digest(address.encode()); scope.mkdir(mode=0o700)
            identity=digest(encoded({'operation':'adopt-1','generation':1}))
            started={
                'format':'hosting-terraform-adoption-attempt/1','status':'STARTED_OUTCOME_UNKNOWN',
                'bundle_sha256':'1'*64,'scope':dict(SCOPE),'operation_id':'adopt-1','generation':1,
                'change_ref':'CHANGE-1','started_at':'2026-09-21T13:00:00+00:00',
            }
            write_new(scope/(identity+'.adoption-started.json'),encoded(started))
            replace_private(scope/'adoption-head.json',encoded(started))
            with self.assertRaisesRegex(ValueError,'outcome remains unknown'):
                with terraform_apply.scope_ledger(ledger,address,SCOPE):
                    self.fail('writer lock must not be yielded')

    def test_completed_adoption_history_allows_later_writer(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger=Path(tmp); ledger.chmod(0o700)
            address='https://state.example.test/project/state/scope'
            scope=ledger/digest(address.encode()); scope.mkdir(mode=0o700)
            identity=digest(encoded({'operation':'adopt-1','generation':1}))
            started={
                'format':'hosting-terraform-adoption-attempt/1','status':'STARTED_OUTCOME_UNKNOWN',
                'bundle_sha256':'1'*64,'scope':dict(SCOPE),'operation_id':'adopt-1','generation':1,
                'change_ref':'CHANGE-1','started_at':'2026-09-21T13:00:00+00:00',
            }
            result=started|{
                'status':'ADOPTED_REQUIRES_EXACT_DELTA_PLAN_REVIEW',
                'completed_at':'2026-09-21T13:01:00+00:00',
                'post_plan_sha256':'2'*64,'post_review_sha256':'3'*64,
                'imported_addresses':['module.owned.vm.a'],
            }
            write_new(scope/(identity+'.adoption-started.json'),encoded(started))
            write_new(scope/(identity+'.adoption-result.json'),encoded(result))
            replace_private(scope/'adoption-head.json',encoded(result))
            with terraform_apply.scope_ledger(ledger,address,SCOPE) as held:
                self.assertEqual(held,scope)


if __name__=='__main__':
    unittest.main()
