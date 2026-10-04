"""Immutable resource/service selections, not synthetic native acceptance."""
from copy import deepcopy
from dataclasses import replace
import unittest

from provisioner.controlplane.reconciliation.planned import reservation_identity_digest,service_request_digest
from provisioner.controlplane.reconciliation.resource_recovery import validate_recovery_selection
from provisioner.controlplane.reconciliation.registry import OperationConflict
from provisioner.domain.enterprise_records import plan_digest,validate_record
from provisioner.execution import readback_core as c
from tests.provisioning.reconciliation.test_planned_creation import selected_openstack_plan
from tests.provisioning.schema.test_enterprise_records import workload
from tests import test_resource_transactions as resources_fixture


class ServiceSelectionTests(unittest.TestCase):
    def setUp(self):
        self.fixture=resources_fixture.ResourceTransactionTests(); self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        self.artifact={'resourceBundleDigest':self.fixture.bundle.digest,'stageBindings':{
            'address-reserve':{'kind':'ipam','parametersDigest':'a'*64,'inputDigests':{'request':'b'*64}},
            'traffic-switch':{'kind':'dns_cutover','parametersDigest':'c'*64,'inputDigests':{'job':'d'*64}}}}
        self.bundle=replace(self.fixture.bundle,selection_digest=c.digest(self.artifact))

    def test_capacity_lifecycle_change_preserves_identity_but_demand_or_owner_drift_does_not(self):
        original=self.fixture.reserve(); changed=deepcopy(original)
        changed.update(status='CONFIRMED',lease_expires_at=None,native_ids=['actual-vm-01'],observed_at='later')
        self.assertEqual(reservation_identity_digest([original]),reservation_identity_digest([changed]))
        for key in ('request_sha256','owner_id','pool_id','resource_binding_sha256'):
            moved=deepcopy(changed); moved[key]='foreign'
            self.assertNotEqual(reservation_identity_digest([original]),reservation_identity_digest([moved]))

    def test_service_digest_requires_entire_protected_artifact_and_fixed_operation(self):
        address=service_request_digest(self.bundle,self.artifact,'address-reserve')
        traffic=service_request_digest(self.bundle,self.artifact,'traffic-switch')
        self.assertNotEqual(address,traffic)
        for change in (lambda value:value['stageBindings']['address-reserve'].update(kind='execute_command'),
                       lambda value:value['stageBindings']['address-reserve'].update(parametersDigest='e'*64),
                       lambda value:value.update(resourceBundleDigest='f'*64)):
            artifact=deepcopy(self.artifact); change(artifact)
            with self.subTest(),self.assertRaises(OperationConflict):
                service_request_digest(self.bundle,artifact,'address-reserve')


def recovery():
    return {'format':'hosting-resource-recovery-selection/1','originalJobId':'original-job',
        'originalPlanDigest':'a'*64,'originalSelectionDigest':'b'*64,'resourceBundleDigest':'c'*64,
        'reservationDigest':'d'*64,'originalOperationIds':['operation-01','operation-02'],
        'actions':['cleanup','release'],'incidentId':'incident-01'}


class RecoverySelectionTests(unittest.TestCase):
    def test_new_plan_can_bind_new_operating_acceptance_while_retaining_old_selection(self):
        selected=selected_openstack_plan(); selected['metadata']['planId']='new-recovery-plan'
        selected['spec']['resourceRecovery']=recovery()
        selected['metadata']['planDigest']=plan_digest(selected)
        self.assertEqual(validate_record(selected,workload=workload()),[])
        self.assertNotEqual(selected['spec']['execution']['artifactDigest'],recovery()['originalSelectionDigest'])

    def test_exact_recovery_parser_rejects_ad_hoc_proofs_replay_or_ambiguous_originals(self):
        self.assertEqual(validate_recovery_selection(recovery()),recovery())
        for mutate in (lambda value:value.update(native_cleanup_complete=True),
                       lambda value:value.update(actions=['reserve']),
                       lambda value:value.update(originalOperationIds=['operation-02','operation-01']),
                       lambda value:value.update(originalOperationIds=['operation-01','operation-01']),
                       lambda value:value.update(originalPlanDigest='not-a-digest')):
            changed=recovery(); mutate(changed)
            with self.subTest(),self.assertRaises(ValueError): validate_recovery_selection(changed)

    def test_canonical_schema_rejects_unknown_recovery_fields_and_unsorted_originals(self):
        selected=selected_openstack_plan(); selected['spec']['resourceRecovery']=recovery()
        selected['spec']['resourceRecovery']['operatorSuccess']=True
        selected['metadata']['planDigest']=plan_digest(selected)
        self.assertTrue(validate_record(selected,workload=workload()))
        del selected['spec']['resourceRecovery']['operatorSuccess']
        selected['spec']['resourceRecovery']['originalOperationIds']=['operation-02','operation-01']
        selected['metadata']['planDigest']=plan_digest(selected)
        self.assertTrue(validate_record(selected,workload=workload()))
