"""Exact new recovery credential-fencing admission; no native grant or refund."""
from copy import deepcopy
from dataclasses import asdict
import unittest

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.authority.service import AuthorityDenied
from provisioner.controlplane.persistence import canonical_record_digest
from provisioner.domain.enterprise_records import plan_digest,validate_record
from provisioner.execution import readback_core as c
from tests.provisioning.operations import test_operations_gate as operating_fixture
from tests.provisioning.reconciliation.test_planned_creation import selected_openstack_plan
from tests.provisioning.reconciliation.test_selected_service_bindings import recovery


class RecoveryFencingTests(unittest.TestCase):
    def setUp(self):
        self.fixture=operating_fixture.OperatingGateTests(); self.fixture.setUp()
        fixture=self.fixture
        fixture.selection['resourceBundleDigest']='c'*64
        self.plan=selected_openstack_plan()
        self.plan['metadata'].update(organizationId=fixture.admitted.organization_id,
            tenantId=fixture.admitted.tenant_id,planId=fixture.admitted.plan_id)
        self.plan['spec']['source']=deepcopy(fixture.selection['source'])
        self.plan['spec']['destination']=deepcopy(fixture.selection['destination'])
        for mapping in self.plan['spec']['machineMappings']:
            mapping['sourceBinding'].update({key:self.plan['spec']['source'][key]
                for key in ('platformFamily','endpointId','nativeScopeId')})
        self.recovery=recovery()
        self.recovery.update(originalJobId='old-job',originalOperationIds=['cleanup-old','create-old'],
            resourceBundleDigest=fixture.selection['resourceBundleDigest'])
        self.plan['spec']['resourceRecovery']=self.recovery
        self.plan['spec']['execution']['artifactDigest']=c.digest(fixture.selection)
        self.plan['metadata']['planDigest']=plan_digest(self.plan)
        fixture.admitted.plan_digest=self.plan['metadata']['planDigest']
        self.assertEqual(validate_record(self.plan),[])
        source=asdict(PlanScope.from_record(self.plan['spec']['source']))
        destination=asdict(PlanScope.from_record(self.plan['spec']['destination']))
        def job(identity,status,digest,plan_id):
            return (fixture.admitted.organization_id,fixture.admitted.tenant_id,identity,'key-'+identity,
                plan_id,1,digest,source,destination,'operator-original',[],0,status,0,
                operating_fixture.AS_OF,operating_fixture.AS_OF)
        self.jobs={fixture.admitted.job_id:job(fixture.admitted.job_id,'RUNNING',fixture.admitted.plan_digest,fixture.admitted.plan_id),
            'old-job':job('old-job','CANCELLED',self.recovery['originalPlanDigest'],'old-plan'),
            'older-recovery':job('older-recovery','HELD','e'*64,'older-recovery-plan')}

    def cursor(self,*,unrelated_uncertainty=0,containment=0,current_old=False,originals=None):
        test=self; fixture=self.fixture
        class Cursor:
            def execute(owner,query,parameters=()):
                owner.query,owner.parameters=query,parameters
                if 'i.job_id=ANY' in query:
                    test.assertEqual(parameters[2:4],(['old-job','older-recovery'],['cleanup-old','create-old']))
            def fetchone(owner):
                query=owner.query
                if 'FROM hosting_controlplane.operation_jobs' in query and 'idempotency_key' in query:
                    return test.jobs.get(owner.parameters[-1])
                if 'FROM hosting_controlplane.enterprise_records' in query:
                    return (1,canonical_record_digest(test.plan),test.plan)
                if query.startswith('SELECT plan_digest'):
                    return (test.recovery['originalPlanDigest'],)
                if 'FROM hosting_controlplane.plan_authority_state' in query:
                    identity='old-job' if owner.parameters[-1]=='old-plan' else 'older-recovery'
                    row=test.jobs[identity]
                    return (row[5],row[6],row[11])
                return ('org-fixture','tenant-fixture',operating_fixture.AS_OF,'RUNNING',1,
                    fixture.admitted.plan_digest,0,unrelated_uncertainty,containment)
            def fetchall(owner):
                return originals if originals is not None else [('cleanup-old','older-recovery'),('create-old','old-job')]
        if current_old:
            self.jobs['old-job']=(*self.jobs['old-job'][:12],'RUNNING',*self.jobs['old-job'][13:])
        return Cursor()

    def require(self,cursor,ids=None):
        fixture=self.fixture
        fixture.gate.require_recovery_fencing(cursor,fixture.admitted,fixture.selection,
            original_job_id='old-job',original_operation_ids=ids or self.recovery['originalOperationIds'])

    def test_new_signed_operating_acceptance_fences_exact_stopped_original_and_earlier_cleanup_only(self):
        self.require(self.cursor())
        with self.assertRaises(AuthorityDenied):
            self.fixture.gate.require_action(self.cursor(unrelated_uncertainty=2),
                self.fixture.admitted,self.fixture.selection,'NATIVE_CLEANUP')

    def test_missing_original_new_arbitrary_ids_live_old_job_or_unrelated_uncertainty_hold(self):
        for options in ({'originals':[('create-old','old-job')]},
                        {'current_old':True},{'unrelated_uncertainty':1},{'containment':1}):
            with self.subTest(options=options),self.assertRaises(AuthorityDenied): self.require(self.cursor(**options))
            self.jobs['old-job']=(*self.jobs['old-job'][:12],'CANCELLED',*self.jobs['old-job'][13:])
        with self.assertRaises(AuthorityDenied): self.require(self.cursor(),['create-old','unapproved-extra'])
