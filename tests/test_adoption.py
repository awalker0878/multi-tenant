"""Brownfield adoption review tests; no Terraform import or native mutation occurs."""
from copy import deepcopy
import unittest

from tools import adoption as a, readback_core as c


NOW='2026-09-21T13:00:00+00:00'


def plan():
    current='1'*64
    desired='2'*64
    return {
        'format':'hosting-adoption/1',
        'source_commit':'a'*40,
        'operation_id':'adopt-001',
        'generation':1,
        'scope':{
            'environment_key':'reference','site_key':'site-01','platform':'vmware',
            'tenant_key':'tenant-01','wsd_key':'science-prod',
        },
        'state':{
            'backend_sha256':'3'*64,
            'state_key':'reference/site-01/vmware/tenant-01/science-prod/workloads',
            'backup_ref':'state-backup/serial-41',
            'lock_ref':'state-lock/change-301',
        },
        'resources':[
            {
                'address':'module.owned.vsphere_virtual_machine.workload',
                'type':'vsphere_virtual_machine',
                'native_id':'vm-4242',
                'current_owner':'legacy-vsphere-runbook',
                'target_owner':'terraform',
                'ownership_mode':'handover_to_terraform',
                'shared':False,
                'import_method':'terraform_import',
                'import_id':'vm-4242',
                'current_sha256':current,
                'desired_sha256':current,
                'delta':'no-op',
                'change_class':'routine',
                'allowed_update_fields':[],
                'discovery_ref':'inventory/vm-4242',
                'recovery_ref':'restore-test/vm-4242',
                'old_writer_fence_ref':'writer-handover/change-301',
            },
            {
                'address':'data.vsphere_distributed_virtual_switch.shared',
                'type':'vsphere_distributed_virtual_switch',
                'native_id':'dvs-20',
                'current_owner':'network-operations',
                'target_owner':'network-operations',
                'ownership_mode':'retain_existing',
                'shared':True,
                'import_method':'observe_only',
                'import_id':None,
                'current_sha256':'4'*64,
                'desired_sha256':'4'*64,
                'delta':'no-op',
                'change_class':'shared_foundation',
                'allowed_update_fields':[],
                'discovery_ref':'inventory/dvs-20',
                'recovery_ref':'network-recovery/dvs-20',
                'old_writer_fence_ref':None,
            },
            {
                'address':'module.owned.vsphere_virtual_machine.resize_candidate',
                'type':'vsphere_virtual_machine',
                'native_id':'vm-4343',
                'current_owner':'legacy-vsphere-runbook',
                'target_owner':'terraform',
                'ownership_mode':'handover_to_terraform',
                'shared':False,
                'import_method':'terraform_import',
                'import_id':'vm-4343',
                'current_sha256':current,
                'desired_sha256':desired,
                'delta':'update',
                'change_class':'routine',
                'allowed_update_fields':['memory','num_cpus'],
                'discovery_ref':'inventory/vm-4343',
                'recovery_ref':'restore-test/vm-4343',
                'old_writer_fence_ref':'writer-handover/change-302',
            },
        ],
    }


def evidence(value):
    rows=[]
    for resource in value['resources']:
        rows.append({
            'address':resource['address'],
            'native_id':resource['native_id'],
            'observed_sha256':resource['current_sha256'],
            'current_owner':resource['current_owner'],
            'old_writer_active':resource['ownership_mode']=='retain_existing',
            'recovery_verified':True,
            'import_supported':True,
            'plan_actions':['no-op'] if resource['delta']=='no-op' else ['update'],
            'replacement':False,
            'delete':False,
            'exposure_change':False,
            'observed_at':NOW,
            'evidence_ref':'evidence/'+resource['native_id'],
        })
    return {
        'format':'hosting-adoption-evidence/1',
        'plan_sha256':c.digest(value),
        'state':{
            'backend_sha256':value['state']['backend_sha256'],
            'state_key':value['state']['state_key'],
            'backup_verified':True,
            'lock_verified':True,
            'observed_at':NOW,
            'evidence_ref':'state-evidence/change-301',
        },
        'resources':rows,
    }


class AdoptionTests(unittest.TestCase):
    def test_review_emits_exact_imports_but_no_automatic_authority(self):
        value=plan()
        result=a.evaluate(value,evidence(value))
        self.assertEqual(result['status'],'ADOPTION_READY_FOR_EXPLICIT_IMPORT_AND_PLAN_REVIEW')
        self.assertEqual([x['native_id'] for x in result['imports']],['vm-4343','vm-4242'])
        self.assertEqual(result['retained_owners'][0]['native_id'],'dvs-20')
        self.assertEqual(result['explicit_deltas'],[{
            'address':'module.owned.vsphere_virtual_machine.resize_candidate',
            'change_class':'routine',
            'allowed_update_fields':['memory','num_cpus'],
        }])
        for key in ('may_import_automatically','may_apply','may_replace','may_delete',
                    'native_acceptance','production_activation'):
            self.assertFalse(result[key])

    def test_state_backup_and_lock_are_mandatory(self):
        value=plan()
        for field in ('backup_verified','lock_verified'):
            record=evidence(value); record['state'][field]=False
            with self.subTest(field=field), self.assertRaisesRegex(ValueError,'backup and writer lock'):
                a.validate_evidence(value,record)

    def test_shared_resource_cannot_transfer_to_terraform(self):
        value=plan(); row=value['resources'][1]
        row.update(ownership_mode='handover_to_terraform',target_owner='terraform',
                   import_method='terraform_import',import_id='dvs-20',
                   old_writer_fence_ref='fake-fence')
        with self.assertRaisesRegex(ValueError,'Shared resources'):
            a.validate_plan(value)

    def test_handover_refuses_active_old_writer(self):
        value=plan(); record=evidence(value)
        record['resources'][0]['old_writer_active']=True
        with self.assertRaisesRegex(ValueError,'Old writer remains active'):
            a.validate_evidence(value,record)

    def test_retained_owner_must_remain_active(self):
        value=plan(); record=evidence(value)
        record['resources'][1]['old_writer_active']=False
        with self.assertRaisesRegex(ValueError,'Retained owner must remain'):
            a.validate_evidence(value,record)

    def test_noop_cannot_hide_configuration_drift(self):
        value=plan(); row=value['resources'][0]
        row['desired_sha256']='9'*64
        with self.assertRaisesRegex(ValueError,'No-op adoption'):
            a.validate_plan(value)

    def test_update_requires_bounded_fields_and_actual_change(self):
        value=plan(); row=value['resources'][2]
        for case in ('same','unbounded'):
            changed=deepcopy(value); target=changed['resources'][2]
            if case=='same': target['desired_sha256']=target['current_sha256']
            else: target['allowed_update_fields']=[]
            with self.subTest(case=case), self.assertRaisesRegex(ValueError,'Explicit update'):
                a.validate_plan(changed)

    def test_replacement_delete_or_exposure_change_is_never_adoption(self):
        value=plan()
        for field in ('replacement','delete','exposure_change'):
            record=evidence(value); record['resources'][0][field]=True
            with self.subTest(field=field), self.assertRaisesRegex(ValueError,'replacement, deletion or new exposure'):
                a.validate_evidence(value,record)

    def test_native_identity_or_configuration_change_holds(self):
        value=plan()
        for field,new in (('native_id','vm-9999'),('observed_sha256','f'*64),('current_owner','someone-else')):
            record=evidence(value); record['resources'][0][field]=new
            with self.subTest(field=field), self.assertRaisesRegex(ValueError,'identity, ownership or configuration'):
                a.validate_evidence(value,record)

    def test_missing_resource_evidence_is_not_partial_success(self):
        value=plan(); record=evidence(value); record['resources'].pop()
        with self.assertRaisesRegex(ValueError,'Complete adoption resource evidence'):
            a.validate_evidence(value,record)

    def test_foreign_plan_digest_is_rejected(self):
        value=plan(); record=evidence(value); record['plan_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'another plan'):
            a.validate_evidence(value,record)

    def test_unsupported_import_mechanism_or_missing_recovery_holds(self):
        value=plan()
        for field in ('recovery_verified','import_supported'):
            record=evidence(value); record['resources'][0][field]=False
            with self.subTest(field=field), self.assertRaisesRegex(ValueError,'Recovery and supported adoption'):
                a.validate_evidence(value,record)


if __name__=='__main__':
    unittest.main()
