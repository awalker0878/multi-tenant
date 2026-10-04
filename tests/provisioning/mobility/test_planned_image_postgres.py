"""Actual SQL image projection/RLS guards; native facts are explicit fixtures.

These cases do not execute vSphere, Glance or issue native qualification. The
runtime connection is the real non-bypass role, and actual immutable B11 rows
and server triggers decide each original-image admission.
"""
from copy import deepcopy
from dataclasses import replace
import os
import unittest
from unittest.mock import patch
from uuid import uuid4

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.jobs.repository import _tenant
from provisioner.controlplane.persistence import TenantContext
from provisioner.controlplane.reconciliation.planned_image import PlannedImageRegistry
from provisioner.controlplane.reconciliation.registry import NativeObservation
from provisioner.domain.enterprise_records import plan_digest
from tests.provisioning.reconciliation import test_registry as registry_fixture
from tests.provisioning.schema.test_enterprise_records import plan as canonical_plan


def selected_image_scope_plan():
    plan=canonical_plan()
    plan['spec']['destination'].update(platformFamily='openstack',endpointId='openstack-image-fixture',
        nativeScopeId='12345678-1234-1234-1234-123456789012')
    plan['spec']['route']['method']='REBUILD_RESTORE'
    plan['metadata']['planDigest']=plan_digest(plan)
    return plan


@unittest.skipUnless(os.environ.get('HOSTING_TEST_POSTGRES_RUNTIME_DSN')
    and os.environ.get('HOSTING_TEST_POSTGRES_MIGRATION_DSN')
    and os.environ.get('HOSTING_TEST_POSTGRES_ISOLATED')=='1',
    'Requires isolated actual PostgreSQL runtime/migration roles')
class PlannedImagePostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        registry_fixture.NativeRegistryPostgresTest.setUpClass()
        cls.psycopg=registry_fixture.NativeRegistryPostgresTest.psycopg

    def setUp(self):
        # Seed the existing canonical source/job/owner through the existing
        # fixture. Its readback adapter is explicitly synthetic native evidence.
        self.fixture=registry_fixture.NativeRegistryPostgresTest()
        with patch.object(registry_fixture,'plan',selected_image_scope_plan):self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.runtime=self.fixture.runtime; self.ctx=self.fixture.ctx
        self.scope=PlanScope.from_record(self.fixture.plan['spec']['destination'])
        self.resource='image-'+uuid4().hex; self.create_operation='create-'+uuid4().hex
        self.upload_operation='upload-'+uuid4().hex; self.create_lease='lease-'+uuid4().hex
        self.upload_lease='lease-'+uuid4().hex; self.native_image_id=str(uuid4())
        self.owner_request='b'*64; self.capture_digest='c'*64
        self.inputs={'cold_selection_digest':'a'*64,'source_operation_id':self.fixture.operation_id,
            'capture_digest':self.capture_digest,'source_snapshot_moid':'snapshot-1','disk_id':'disk-boot',
            'device_key':2000,'nfc_key':'native-opaque-disk-key','output_sha256':'d'*64,
            'output_sha512':'e'*128,'output_bytes':1234,'virtual_bytes':1024**3,
            'image_name':'retained-fixture-image','request_digest':self.owner_request}
        with self.runtime() as connection,connection.cursor() as cursor:
            self.assertEqual(cursor.execute('SELECT rolsuper,rolbypassrls FROM pg_catalog.pg_roles '
                'WHERE rolname=current_user').fetchone(),(False,False))
        self.fixture.registry.prepare(self.ctx,self.fixture.owner,self.fixture.scope,
            job_id=self.fixture.job_id,grant_id='grant-1',step_id='step-1',lease_key=self.fixture.lease_key,
            worker_identity=self.fixture.identity,operation_id=self.fixture.operation_id,
            operation_kind='SNAPSHOT_EXPORT',request_digest='f'*64)
        self.fixture.registry.claim_once(self.ctx,self.fixture.owner,self.fixture.scope,
                                         self.fixture.operation_id,self.fixture.identity)
        self.fixture.registry.task_accepted(self.ctx,self.fixture.operation_id,self.fixture.identity.subject,'nfclease-1')
        observed=replace(self.fixture.current_observation(),native_task_id='nfclease-1')
        self.fixture.registry.acknowledge_current(self.ctx,self.fixture.owner,self.fixture.scope,
            self.fixture.operation_id,self.fixture.identity,observed)
        self._owner()

    def _owner(self):
        with self.runtime() as connection,connection.cursor() as cursor:
            _tenant(cursor,self.ctx)
            cursor.execute('INSERT INTO hosting_controlplane.planned_resource_ownership '
                '(organization_id,tenant_id,job_id,resource_id,selection_digest,request_digest,reservation_digest,'
                'resource_kind,platform_family,endpoint_id,native_scope_id,site_id,security_domain_id,workload_id,'
                'worker_id,owner_epoch,lease_expires_at) '
                "VALUES (%s,%s,%s,%s,%s,%s,%s,'image','openstack',%s,%s,%s,%s,%s,'image-writer',1,"
                "clock_timestamp()+interval '5 minutes')",(self.ctx.organization_id,self.ctx.tenant_id,
                self.fixture.job_id,self.resource,'0'*64,self.owner_request,'1'*64,self.scope.endpoint_id,
                self.scope.native_scope_id,self.scope.site_id,self.scope.security_domain_id,
                self.fixture.workload['metadata']['workloadId']))

    def _input(self,**changes):
        body=self.inputs|changes
        with self.runtime() as connection,connection.cursor() as cursor:
            _tenant(cursor,self.ctx)
            names=','.join(body)
            cursor.execute('INSERT INTO hosting_controlplane.planned_image_inputs '
                '(organization_id,tenant_id,job_id,resource_id,'+names+') VALUES ('+
                ','.join(['%s']*(4+len(body)))+')',
                (self.ctx.organization_id,self.ctx.tenant_id,self.fixture.job_id,self.resource,*body.values()))

    def _lease(self,phase):
        operation=self.create_operation if phase=='CREATE' else self.upload_operation
        lease=self.create_lease if phase=='CREATE' else self.upload_lease
        with self.runtime() as connection,connection.cursor() as cursor:
            _tenant(cursor,self.ctx)
            cursor.execute('INSERT INTO hosting_controlplane.native_operation_leases '
                '(organization_id,tenant_id,lease_key,job_id,operation_id,platform_family,endpoint_id,native_scope_id,'
                'resource_kind,native_id,planned_resource_id,site_id,security_domain_id,worker_id,owner_epoch,expires_at) '
                "SELECT organization_id,tenant_id,%s,job_id,%s,platform_family,endpoint_id,native_scope_id,'image',"
                'NULL,resource_id,site_id,security_domain_id,worker_id,owner_epoch,lease_expires_at '
                'FROM hosting_controlplane.planned_resource_ownership WHERE organization_id=%s AND tenant_id=%s '
                'AND job_id=%s AND resource_id=%s',
                (lease,operation,self.ctx.organization_id,self.ctx.tenant_id,self.fixture.job_id,self.resource))

    def _binding(self,phase,**changes):
        body={'organization_id':self.ctx.organization_id,'tenant_id':self.ctx.tenant_id,
            'lease_key':self.create_lease if phase=='CREATE' else self.upload_lease,
            'job_id':self.fixture.job_id,'resource_id':self.resource,'step_id':phase.lower()+'-image',
            'phase':phase,'request_digest':'2'*64 if phase=='CREATE' else '3'*64}|changes
        with self.runtime() as connection,connection.cursor() as cursor:
            _tenant(cursor,self.ctx)
            cursor.execute('INSERT INTO hosting_controlplane.planned_image_bindings ('+','.join(body)+
                ') VALUES ('+','.join(['%s']*len(body))+')',tuple(body.values()))

    def _intent(self,phase,**changes):
        body={'organization_id':self.ctx.organization_id,'tenant_id':self.ctx.tenant_id,
            'operation_id':self.create_operation if phase=='CREATE' else self.upload_operation,
            'job_id':self.fixture.job_id,'grant_id':'SQL-FIXTURE-ONLY','step_id':phase.lower()+'-image',
            'lease_key':self.create_lease if phase=='CREATE' else self.upload_lease,
            'platform_family':'openstack','endpoint_id':self.scope.endpoint_id,'native_scope_id':self.scope.native_scope_id,
            'resource_kind':'image','native_id':None,'planned_resource_id':self.resource,
            'workload_id':self.fixture.workload['metadata']['workloadId'],'security_domain_id':self.scope.security_domain_id,
            'worker_id':'image-writer','owner_epoch':1,'operation_kind':'SNAPSHOT_IMPORT',
            'request_digest':'2'*64 if phase=='CREATE' else '3'*64}|changes
        with self.runtime() as connection,connection.cursor() as cursor:
            _tenant(cursor,self.ctx)
            cursor.execute('INSERT INTO hosting_controlplane.native_operation_intents ('+','.join(body)+
                ') VALUES ('+','.join(['%s']*len(body))+')',tuple(body.values()))

    def _state(self,phase,state):
        operation=self.create_operation if phase=='CREATE' else self.upload_operation
        with self.runtime() as connection,connection.cursor() as cursor:
            _tenant(cursor,self.ctx)
            cursor.execute('UPDATE hosting_controlplane.native_operation_intents SET state=%s,'
                'updated_at=clock_timestamp() WHERE organization_id=%s AND tenant_id=%s AND operation_id=%s',
                (state,self.ctx.organization_id,self.ctx.tenant_id,operation))

    def _receipt(self,**changes):
        body={'organization_id':self.ctx.organization_id,'tenant_id':self.ctx.tenant_id,
            'operation_id':self.create_operation,'job_id':self.fixture.job_id,'resource_id':self.resource,
            'native_image_id':self.native_image_id,'native_request_id':'req-'+str(uuid4())}|changes
        with self.runtime() as connection,connection.cursor() as cursor:
            _tenant(cursor,self.ctx)
            cursor.execute('INSERT INTO hosting_controlplane.planned_image_receipts ('+','.join(body)+
                ') VALUES ('+','.join(['%s']*len(body))+')',tuple(body.values()))

    def _observation(self,phase,**changes):
        body={'organization_id':self.ctx.organization_id,'tenant_id':self.ctx.tenant_id,
            'observation_id':'read-'+uuid4().hex,'operation_id':self.create_operation if phase=='CREATE' else self.upload_operation,
            'evidence_digest':'4'*64,'observer_subject':'separate-native-reader','native_task_id':None,
            'outcome':'EFFECT_PRESENT','native_quiesced':True,'created_native_image_id':self.native_image_id}|changes
        with self.runtime() as connection,connection.cursor() as cursor:
            _tenant(cursor,self.ctx)
            cursor.execute('INSERT INTO hosting_controlplane.native_operation_observations ('+','.join(body)+
                ',observed_at) VALUES ('+','.join(['%s']*len(body))+',clock_timestamp())',tuple(body.values()))

    def _resolve(self,phase):
        self._state(phase,'UNCERTAIN')
        with self.runtime() as connection,connection.cursor() as cursor:
            _tenant(cursor,self.ctx)
            cursor.execute("UPDATE hosting_controlplane.native_operation_intents SET state='RESOLVED',"
                "outcome='EFFECT_PRESENT',resolution_evidence_digest=%s,updated_at=clock_timestamp() "
                'WHERE organization_id=%s AND tenant_id=%s AND operation_id=%s',
                ('4'*64,self.ctx.organization_id,self.ctx.tenant_id,
                 self.create_operation if phase=='CREATE' else self.upload_operation))

    def _create(self):
        self._input();self._lease('CREATE');self._binding('CREATE');self._intent('CREATE');self._state('CREATE','IN_FLIGHT')

    def test_original_create_and_upload_use_one_journal_and_keep_logical_identity_without_native_vm(self):
        self._create();self._receipt();self._observation('CREATE');self._resolve('CREATE')
        self._lease('UPLOAD');self._binding('UPLOAD');self._intent('UPLOAD');self._state('UPLOAD','IN_FLIGHT')
        self._observation('UPLOAD');self._resolve('UPLOAD')
        with self.runtime() as connection,connection.cursor() as cursor:
            _tenant(cursor,self.ctx)
            operations=[PlannedImageRegistry._get(cursor,self.ctx,operation,lock=False)
                for operation in (self.create_operation,self.upload_operation)]
            self.assertEqual([(item.phase,item.state,item.outcome) for item in operations],
                             [('CREATE','RESOLVED','EFFECT_PRESENT'),('UPLOAD','RESOLVED','EFFECT_PRESENT')])
            self.assertEqual(cursor.execute('SELECT native_id,planned_resource_id FROM '
                'hosting_controlplane.native_operation_intents WHERE organization_id=%s AND tenant_id=%s '
                'AND operation_id IN (%s,%s) ORDER BY operation_id',
                (self.ctx.organization_id,self.ctx.tenant_id,self.create_operation,self.upload_operation)).fetchall(),
                [(None,self.resource),(None,self.resource)])
            self.assertEqual(cursor.execute('SELECT count(*) FROM hosting_controlplane.native_ownership '
                "WHERE organization_id=%s AND tenant_id=%s AND platform_family='openstack'",
                (self.ctx.organization_id,self.ctx.tenant_id)).fetchone(),(0,))

    def test_receipt_requires_original_claim_and_does_not_authorize_upload_without_independent_acceptance(self):
        self._input();self._lease('CREATE');self._binding('CREATE');self._intent('CREATE')
        with self.assertRaises(self.psycopg.Error):self._receipt()
        self._state('CREATE','IN_FLIGHT');self._receipt();self._lease('UPLOAD')
        with self.assertRaises(self.psycopg.Error):self._binding('UPLOAD')
        self._observation('CREATE');self._resolve('CREATE');self._binding('UPLOAD')

    def test_native_identity_writer_quiescence_and_action_request_cannot_be_borrowed(self):
        self._create();self._receipt()
        for change in ({'created_native_image_id':str(uuid4())},{'observer_subject':'image-writer'},
                       {'native_quiesced':False},{'native_task_id':'fabricated-task'},{'outcome':'UNKNOWN'}):
            with self.subTest(change=change),self.assertRaises(self.psycopg.Error):self._observation('CREATE',**change)
        self._observation('CREATE');self._resolve('CREATE');self._lease('UPLOAD');self._binding('UPLOAD')
        for change in ({'operation_kind':'VM_CREATE'},{'step_id':'another-selected-step'},
                       {'request_digest':'9'*64},{'native_id':str(uuid4())}):
            with self.subTest(change=change),self.assertRaises(self.psycopg.Error):self._intent('UPLOAD',**change)
        self._intent('UPLOAD')

    def test_export_input_requires_exact_original_job_workload_and_independent_native_task(self):
        with self.assertRaises(self.psycopg.Error):self._input(source_operation_id='unknown-native-export')
        with self.assertRaises(self.psycopg.Error):self._input(request_digest='9'*64)
        self._input()

    def test_uncertain_original_create_preserves_receipt_and_cannot_authorize_repeated_upload(self):
        self._create();self._receipt();self._state('CREATE','UNCERTAIN');self._lease('UPLOAD')
        with self.assertRaises(self.psycopg.Error):self._binding('UPLOAD')
        with self.assertRaises(self.psycopg.Error):self._state('CREATE','IN_FLIGHT')
        with self.runtime() as connection,connection.cursor() as cursor:
            _tenant(cursor,self.ctx)
            original=PlannedImageRegistry._get(cursor,self.ctx,self.create_operation,lock=False)
            self.assertEqual(original.state,'UNCERTAIN')
            self.assertEqual(PlannedImageRegistry._receipt(cursor,self.ctx,self.fixture.job_id,self.resource)[0],
                             self.native_image_id)

    def test_runtime_and_foreign_tenant_cannot_rewrite_or_discover_original_image_inputs_receipts_or_bindings(self):
        self._create();self._receipt()
        for table,field in (('planned_image_inputs','capture_digest'),('planned_image_bindings','request_digest'),
                            ('planned_image_receipts','native_image_id')):
            with self.subTest(table=table):
                with self.runtime() as connection,connection.cursor() as cursor:
                    foreign=TenantContext('other-org','other-tenant');_tenant(cursor,foreign)
                    self.assertEqual(cursor.execute('SELECT count(*) FROM hosting_controlplane.'+table+
                        ' WHERE organization_id=%s AND tenant_id=%s',
                        (self.ctx.organization_id,self.ctx.tenant_id)).fetchone(),(0,))
                for mutation in ('UPDATE hosting_controlplane.'+table+' SET '+field+'=%s WHERE organization_id=%s AND tenant_id=%s',
                                 'DELETE FROM hosting_controlplane.'+table+' WHERE organization_id=%s AND tenant_id=%s'):
                    with self.assertRaises(self.psycopg.Error),self.runtime() as connection,connection.cursor() as cursor:
                        _tenant(cursor,self.ctx)
                        params=(self.ctx.organization_id,self.ctx.tenant_id)
                        cursor.execute(mutation,('9'*64,*params) if mutation.startswith('UPDATE') else params)
