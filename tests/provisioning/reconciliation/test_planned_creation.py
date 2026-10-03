"""Logical creation identities and opt-in real PostgreSQL/B10 transactions.

PostgreSQL tests execute actual RLS, immutable ownership, grant revalidation and
the existing intent journal. Protected-selection/native-readback fixtures remain
synthetic and confer no deployment/native qualification.
"""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

from provisioner.allocations import capacity_owner
from provisioner.allocations.transactions import PoolDemand, ResourceBundle, ResourceTransactions
from provisioner.controlplane.authority import postgres as authority_postgres
from provisioner.controlplane.authority.model import PlanScope, RoleGrant, VerifiedPrincipal
from provisioner.controlplane.jobs import JobRepository
from provisioner.controlplane.jobs.repository import _digest, _payload_from_job
from provisioner.controlplane.persistence import NativeBinding, TenantContext
from provisioner.controlplane.reconciliation.planned import (
    PlannedLeaseAuthority, PlannedNativeCreationRegistry, NativeCreationObservation,
    creation_request_digest, deployment_id)
from provisioner.controlplane.reconciliation.resource_authority import PostgresResourceAuthority
from provisioner.controlplane.reconciliation.registry import (
    NativeObservation, OperationConflict, OwnerRecoveryEvidence, RecoveryHeld)
from provisioner.controlplane.worker.grants import (
    PostgresWorkerGrants, GrantRequest, VerifiedWorkerIdentity, ALLOWED_OPERATIONS)
from provisioner.controlplane.workflow.admitted_job import AdmittedInput
from provisioner.domain.enterprise_records import plan_digest
from provisioner.execution import readback_core as c
from tests.provisioning.worker import test_postgres_worker as worker_fixture


class PlannedCreationValidationTests(unittest.TestCase):
    def test_creation_observation_never_accepts_logical_ids_as_native_bindings(self):
        at=datetime.now(timezone.utc)
        native=NativeObservation('readback-01','a'*64,'independent-reader',None,
                                 'EFFECT_PRESENT',True,at)
        with self.assertRaises(ValueError): NativeCreationObservation(native,())
        with self.assertRaises(ValueError): NativeCreationObservation(native,('deployment-01',))
        actual=NativeBinding('openstack','endpoint-01','project-01','vm','server-native-01')
        self.assertEqual(NativeCreationObservation(native,(actual,)).bindings,(actual,))
        absent=replace(native,outcome='NO_EFFECT')
        with self.assertRaises(ValueError): NativeCreationObservation(absent,(actual,))

    def test_fixed_guest_policy_and_quota_actions_have_distinct_worker_kinds(self):
        self.assertTrue({'GUEST_CONFIG','POLICY_APPLY','QUOTA_CHANGE'}<=ALLOWED_OPERATIONS)
        self.assertNotIn('EXECUTE_COMMAND',ALLOWED_OPERATIONS)


class _Selection:
    def __init__(self): self.artifact={}
    def load_verified(self,digest):
        if digest!='d'*64: raise OperationConflict('Synthetic protected selection digest differs')
        return self.artifact


class _ResourceAuthority:
    """No product mutations are authorized by this test-only readback adapter."""
    def locked(self,*_): raise AssertionError('PG fixture seeds accounting with the real owner explicitly')


class _Evidence:
    def __init__(self):
        self.current=True
        self.fenced=False
        self.bindings=()
    def verify_creation_observation(self,cursor,operation,observed):
        if (not self.current or observed.observation.evidence_digest!='a'*64
                or (observed.observation.outcome=='EFFECT_PRESENT' and observed.bindings!=self.bindings)):
            raise RecoveryHeld('Synthetic independent current creation readback rejected')
    def verify_creation_owner_exclusion(self,cursor,lease,scope,evidence):
        if not self.fenced or evidence.worker_fence_digest!='c'*64:
            raise RecoveryHeld('Synthetic planned worker has not been fenced')
    def verify_resource_observation(self,*_):
        raise RecoveryHeld('Synthetic native readback has no capacity occupancy authority')


@unittest.skipUnless(os.environ.get('HOSTING_TEST_POSTGRES_RUNTIME_DSN') and
                     os.environ.get('HOSTING_TEST_POSTGRES_ENROLLMENT_DSN') and
                     os.environ.get('HOSTING_TEST_POSTGRES_ISOLATED')=='1',
                     'Requires isolated real PostgreSQL runtime/enrollment/migration roles')
class PlannedCreationPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        worker_fixture.WorkerPostgresTests.setUpClass()
        cls.psycopg=worker_fixture.WorkerPostgresTests.psycopg

    def setUp(self):
        original=worker_fixture.plan
        def selected_plan():
            plan=original()
            plan['spec']['destination'].update(platformFamily='openstack',endpointId='openstack-01',
                nativeScopeId='project-01',securityDomainId='wsd-01')
            plan['spec']['route']['method']='APPLICATION_REBUILD_RESTORE'
            plan['spec']['execution']={'format':'hosting-execution-selection/1',
                'driver':'openstack-linux-rebuild/1','artifactDigest':'d'*64}
            plan['metadata']['planDigest']=plan_digest(plan)
            return plan
        self.fixture=worker_fixture.WorkerPostgresTests()
        with patch.object(worker_fixture,'plan',selected_plan): self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.context=self.fixture.context
        self.runtime=self.fixture.runtime
        self.scope=self.fixture.target
        job=JobRepository(self.runtime,authority_postgres).get(self.context,self.fixture.job_id)
        admitted=AdmittedInput(job.job_id,job.organization_id,job.tenant_id,job.plan_id,
            job.plan_revision,job.plan_digest,job.revocation_epoch,_digest(_payload_from_job(job)))
        now=datetime.now(timezone.utc)
        window={'valid_from':(now-timedelta(minutes=1)).isoformat(),
                'valid_until':(now+timedelta(minutes=30)).isoformat()}
        unit=lambda cpu=0,memory=0,storage=0:{'vcpu':cpu,'memory_mb':memory,'storage_gb':storage}
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.database=Path(self.temp.name)/'capacity.db'
        pool={'origin':'https://native.example.invalid','native_id':self.scope.native_scope_id,
              'platform':'openstack','site_key':self.scope.site_id,'capacity':unit(100,100000,1000),
              'reserve':unit(),'capabilities':['internal-ipv4'],'qualification_ref':'LOCAL-PG-ONLY'}
        envelope={'format':'hosting-capacity-envelope/1','owner_id':'capacity-01','revision':1,
                  **window,'acceptance_ref':'LOCAL-PG-ONLY','pools':{'pool-01':pool},
                  'tenants':{self.context.tenant_id:{'limit':unit(100,100000,1000),
                             'pools':['pool-01'],'entitlement_ref':'LOCAL-PG-ONLY'}}}
        capacity_owner.initialize(self.database,envelope)
        placement={'compute_availability_zone':'nova','storage_availability_zone':'nova','volume_type':'standard'}
        catalog={'format':'hosting-capacity-sizing/1','pool_id':'pool-01',
            **{key:pool[key] for key in ('origin','native_id','platform','site_key')},
            'placements':[placement],'provider_selector':{'openstack_cloud':'test-cloud'},
            'cloud_sha256':'0'*64,'flavors':{'flavor-01':{'vcpu':2,'ram_mib':4096,
            'root_gib':0,'ephemeral_gib':0,'swap_mib':0}},**window,'acceptance_ref':'LOCAL-PG-ONLY'}
        inputs={'environment_key':'test','site_key':self.scope.site_id,
                'tenant_key':self.context.tenant_id,'wsd_key':self.scope.security_domain_id,
                'openstack_cloud':'test-cloud','members':{f'target-machine-{i}':
                placement|{'flavor_id':'flavor-01','boot_disk_gib':40,'data_disk_gib':0} for i in (1,2)}}
        demand=PoolDemand.from_workload(scope=self.scope,catalog=catalog,inputs=inputs,
            envelope_sha256=c.digest(envelope),budgets={key:unit() for key in ('staging','snapshots','retained-source')},
            capabilities=('internal-ipv4',))
        self.bundle=ResourceBundle(admitted,'d'*64,self.fixture.workload['metadata']['workloadId'],1,(demand,))
        self.resources=ResourceTransactions(self.database,_ResourceAuthority())
        requests=self.bundle.requests(envelope['owner_id'])
        for request in requests:
            authority={'format':'hosting-capacity-authority/1','request_sha256':c.digest(request),
                'action':'reserve','native_ids_sha256':c.digest([]),'envelope_sha256':c.digest(envelope),
                'previous_receipt_sha256':None,**window,'change_ref':'LOCAL-PG-ONLY','evidence_ref':'LOCAL-PG-ONLY'}
            with capacity_owner.database(self.database) as db:
                capacity_owner._operate_in_database(db,request,'reserve',authority,resource=True)
        self.selection=_Selection()
        self.selection.artifact={'resourceBundleDigest':self.bundle.digest,
            'workloadId':self.bundle.workload_id,'workloadRevision':self.bundle.workload_revision,
            'source':self.fixture.plan['spec']['source'],'destination':self.fixture.plan['spec']['destination']}
        self.leases=PlannedLeaseAuthority(self.runtime,resources=self.resources,selections=self.selection,
            bundle_lookup=lambda requested,artifact:replace(self.bundle,admitted=requested))
        self.identity=VerifiedWorkerIdentity(self.context.organization_id,self.context.tenant_id,
            'creation-worker',self.scope.site_id,uuid4().hex+uuid4().hex,now+timedelta(hours=1))
        with self.psycopg.connect(self.fixture.migration_dsn) as connection:
            self.fixture._tenant(connection)
            connection.execute('INSERT INTO hosting_controlplane.worker_enrollments '
                '(organization_id,tenant_id,worker_subject,site_id,certificate_sha256,expires_at) '
                'VALUES (%s,%s,%s,%s,%s,%s)',(self.context.organization_id,self.context.tenant_id,
                 self.identity.subject,self.scope.site_id,self.identity.certificate_sha256,self.identity.expires_at))
            connection.execute('INSERT INTO hosting_controlplane.worker_certificate_versions '
                '(organization_id,tenant_id,worker_subject,certificate_sha256,expires_at) '
                'VALUES (%s,%s,%s,%s,%s)',(self.context.organization_id,self.context.tenant_id,
                 self.identity.subject,self.identity.certificate_sha256,self.identity.expires_at))
            connection.execute('INSERT INTO hosting_controlplane.worker_capabilities '
                '(organization_id,tenant_id,worker_subject,site_id,security_domain_id,endpoint_id,'
                'native_scope_id,platform_family,operation_kind,credential_ref) '
                "VALUES (%s,%s,%s,%s,%s,%s,%s,'openstack','VM_CREATE','vault:local-pg-only')",
                (self.context.organization_id,self.context.tenant_id,self.identity.subject,self.scope.site_id,
                 self.scope.security_domain_id,self.scope.endpoint_id,self.scope.native_scope_id))
        self.grants=PostgresWorkerGrants(self.runtime,self.leases)
        self.evidence=_Evidence()
        self.registry=PlannedNativeCreationRegistry(self.runtime,leases=self.leases,
            grants=self.grants,evidence=self.evidence)
        self.operation_id='creation-operation'; self.lease_key='creation-lease'
        self.lease=self.leases.register(self.context,self.scope,job_id=job.job_id,
            resource_id=deployment_id(self.bundle,self.scope),lease_key=self.lease_key,
            operation_id=self.operation_id,worker_identity=self.identity,
            ttl_seconds=5 if self._testMethodName.startswith('test_expired') else 300)
        self.grant=self.grants.issue_grant(self.context,self.identity,GrantRequest(
            job.job_id,'creation-step',self.operation_id,'VM_CREATE',self.scope,
            self.lease_key,1,timedelta(minutes=2)))

    def prepare(self):
        return self.registry.prepare(self.context,self.lease,grant_id=self.grant.grant_id,
            step_id='creation-step',lease_key=self.lease_key,operation_id=self.operation_id,
            worker_identity=self.identity)

    def observation(self,outcome='EFFECT_PRESENT',*,observer='independent-reader',at=None):
        bindings=tuple(NativeBinding('openstack',self.scope.endpoint_id,self.scope.native_scope_id,'vm',
            'server-'+uuid4().hex) for _ in range(2)) if outcome=='EFFECT_PRESENT' else ()
        self.evidence.bindings=bindings
        native=NativeObservation('readback-'+uuid4().hex,'a'*64,observer,None,outcome,True,
                                 at or datetime.now(timezone.utc))
        return NativeCreationObservation(native,bindings)

    def test_real_create_claim_and_independent_readback_reuse_the_existing_intent_owner(self):
        self.assertEqual(self.prepare().state,'PREPARED')
        self.assertTrue(self.registry.claim_once(self.context,self.lease,self.operation_id,self.identity))
        self.assertFalse(self.registry.claim_once(self.context,self.lease,self.operation_id,self.identity))
        observation=self.observation()
        self.assertEqual(self.registry.acknowledge_created(self.context,self.lease,self.operation_id,
            self.identity,observation),observation.bindings)
        self.assertEqual(self.registry.get(self.context,self.operation_id).state,'RESOLVED')
        fresh=replace(observation,observation=replace(observation.observation,
            observation_id='fresh-'+uuid4().hex,observed_at=datetime.now(timezone.utc)))
        self.assertEqual(self.registry.reconcile_observed(self.context,self.operation_id,fresh),observation.bindings)
        with self.runtime() as connection:
            self.fixture._tenant(connection)
            row=connection.execute('SELECT native_id,planned_resource_id,resource_kind FROM '
                'hosting_controlplane.native_operation_intents WHERE organization_id=%s '
                'AND tenant_id=%s AND operation_id=%s',
                (self.context.organization_id,self.context.tenant_id,self.operation_id)).fetchone()
            self.assertEqual(row,(None,self.lease.resource_id,'deployment'))
            self.assertEqual(connection.execute('SELECT count(*) FROM hosting_controlplane.native_ownership '
                "WHERE organization_id=%s AND tenant_id=%s AND platform_family='openstack'",
                (self.context.organization_id,self.context.tenant_id)).fetchone()[0],0)

    def test_revocation_before_claim_or_forged_native_success_keeps_prepared_or_uncertain(self):
        self.prepare()
        with self.psycopg.connect(self.fixture.migration_dsn) as connection:
            self.fixture._tenant(connection)
            connection.execute('UPDATE hosting_controlplane.plan_authority_state '
                'SET revocation_epoch=revocation_epoch+1 WHERE organization_id=%s AND tenant_id=%s AND plan_id=%s',
                (self.context.organization_id,self.context.tenant_id,self.fixture.plan['metadata']['planId']))
        with self.assertRaises(Exception):
            self.registry.claim_once(self.context,self.lease,self.operation_id,self.identity)
        self.assertEqual(self.registry.get(self.context,self.operation_id).state,'PREPARED')

    def test_timeout_cannot_create_again_and_operator_booleans_cannot_clear_uncertainty(self):
        self.prepare(); self.registry.claim_once(self.context,self.lease,self.operation_id,self.identity)
        self.registry.mark_uncertain(self.context,self.operation_id,self.identity.subject)
        self.assertFalse(self.registry.claim_once(self.context,self.lease,self.operation_id,self.identity))
        with self.assertRaises(RecoveryHeld):
            self.registry.acknowledge_created(self.context,self.lease,self.operation_id,self.identity,
                self.observation(observer=self.identity.subject))
        self.evidence.current=False
        with self.assertRaises(RecoveryHeld):
            self.registry.acknowledge_created(self.context,self.lease,self.operation_id,self.identity,
                self.observation())
        self.assertEqual(self.registry.get(self.context,self.operation_id).state,'UNCERTAIN')

    def test_planned_identity_is_immutable_and_foreign_tenant_has_no_intent(self):
        self.prepare()
        with self.runtime() as connection:
            self.fixture._tenant(connection)
            with self.assertRaises(self.psycopg.Error):
                connection.execute('DELETE FROM hosting_controlplane.planned_resource_ownership '
                    'WHERE organization_id=%s AND tenant_id=%s',
                    (self.context.organization_id,self.context.tenant_id))
        with self.psycopg.connect(self.fixture.migration_dsn) as connection:
            self.fixture._tenant(connection)
            with self.assertRaisesRegex(self.psycopg.Error,'(?i)append-only'):
                connection.execute('DELETE FROM hosting_controlplane.planned_resource_ownership '
                    'WHERE organization_id=%s AND tenant_id=%s',
                    (self.context.organization_id,self.context.tenant_id))
        with self.assertRaises(OperationConflict):
            self.registry.get(TenantContext(self.context.organization_id,'foreign-tenant'),self.operation_id)

    def test_receipt_drift_prevents_grant_or_second_owner_without_releasing_capacity(self):
        self.prepare()
        self.selection.artifact['resourceBundleDigest']='0'*64
        with self.assertRaises(OperationConflict):
            self.registry.claim_once(self.context,self.lease,self.operation_id,self.identity)
        self.assertEqual(self.registry.get(self.context,self.operation_id).state,'PREPARED')

    def test_aggregate_and_individual_children_cannot_create_the_same_target_twice(self):
        with self.assertRaises(OperationConflict):
            self.leases.register(self.context,self.scope,job_id=self.bundle.admitted.job_id,
                resource_id='target-machine-1',lease_key='second-lease',operation_id='second-operation',
                worker_identity=self.identity)
        with self.runtime() as connection:
            self.fixture._tenant(connection)
            rows=connection.execute('SELECT target_machine_id,resource_id FROM '
                'hosting_controlplane.planned_creation_children WHERE organization_id=%s AND tenant_id=%s '
                'ORDER BY target_machine_id',(self.context.organization_id,self.context.tenant_id)).fetchall()
            self.assertEqual(rows,[(child,self.lease.resource_id) for child in ('target-machine-1','target-machine-2')])

    def test_expired_unknown_creation_needs_actual_exclusion_and_two_independent_reviews(self):
        self.prepare(); self.registry.claim_once(self.context,self.lease,self.operation_id,self.identity)
        self.registry.mark_uncertain(self.context,self.operation_id,self.identity.subject)
        time.sleep(max(0,(self.lease.expires_at-datetime.now(timezone.utc)).total_seconds())+0.05)
        with self.assertRaises(Exception):
            self.registry.claim_once(self.context,self.lease,self.operation_id,self.identity)
        observed=self.observation('NO_EFFECT')
        self.registry.observe(self.context,self.operation_id,observed)
        exclusion=OwnerRecoveryEvidence('b'*64,'c'*64,datetime.now(timezone.utc),'incident-expiry')
        def reviewer(subject):
            now=datetime.now(timezone.utc)
            return VerifiedPrincipal(subject,self.context.organization_id,self.context.tenant_id,'HUMAN',
                now-timedelta(minutes=1),now+timedelta(minutes=5),now,
                (RoleGrant('EXECUTION_OPERATOR',self.scope,now+timedelta(minutes=5)),))
        arguments=(self.context,self.lease,self.operation_id,observed.observation.observation_id)
        with self.assertRaises(RecoveryHeld):
            self.registry.review_outcome(*arguments,reviewer('operator-one'),decision='NO_EFFECT',exclusion=exclusion)
        self.evidence.fenced=True
        self.assertFalse(self.registry.review_outcome(*arguments,reviewer('operator-one'),
            decision='NO_EFFECT',exclusion=exclusion))
        self.assertFalse(self.registry.review_outcome(*arguments,reviewer('operator-one'),
            decision='NO_EFFECT',exclusion=exclusion))
        self.assertTrue(self.registry.review_outcome(*arguments,reviewer('operator-two'),
            decision='NO_EFFECT',exclusion=exclusion))
        self.assertEqual(self.registry.get(self.context,self.operation_id).outcome,'NO_EFFECT')
        with capacity_owner.database(self.database) as db:
            self.assertEqual(db.execute('SELECT status FROM reservation').fetchall(),[('RESERVED',)])

    def test_database_operation_vocabulary_rejects_generic_executor_privilege(self):
        for name in ('GUEST_CONFIG','POLICY_APPLY','QUOTA_CHANGE'):
            with self.runtime() as connection:
                self.assertEqual(connection.execute('SELECT %s::hosting_controlplane.worker_operation_kind',
                                                    (name,)).fetchone(),(name,))
        with self.runtime() as connection,self.assertRaises(self.psycopg.Error):
            connection.execute("SELECT 'EXECUTE_COMMAND'::hosting_controlplane.worker_operation_kind")

    def test_actual_postgres_job_resource_gate_prevents_revoked_reservation_effects(self):
        resources=ResourceTransactions(self.database,PostgresResourceAuthority(
            self.runtime,authority_postgres,self.selection,self.evidence))
        result=resources.require_ready(self.bundle)
        self.assertEqual(result['receipts'][0]['status'],'RESERVED')
        with self.psycopg.connect(self.fixture.migration_dsn) as connection:
            self.fixture._tenant(connection)
            connection.execute('UPDATE hosting_controlplane.plan_authority_state '
                'SET revocation_epoch=revocation_epoch+1 WHERE organization_id=%s AND tenant_id=%s AND plan_id=%s',
                (self.context.organization_id,self.context.tenant_id,self.fixture.plan['metadata']['planId']))
        with self.assertRaises(Exception): resources.reserve(self.bundle)
        with capacity_owner.database(self.database) as db:
            self.assertEqual(db.execute('SELECT status FROM reservation').fetchall(),[('RESERVED',)])


if __name__=='__main__': unittest.main()
