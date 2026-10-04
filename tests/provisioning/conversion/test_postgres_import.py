"""Opt-in real PostgreSQL import/epoch authority with synthetic external services.

ObjectLock and HTTPS Vault transports are local test ports; all canonical SQL,
RLS, immutable journals, role permissions and cryptographic checks are real.
These cases are not retained deployment or native migration qualification.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import os
import unittest
from uuid import uuid4

from provisioner.controlplane.authority.service import AuthorityDenied
from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.conversion.handover import RetainedStateHandover, require_write_admission
from provisioner.controlplane.conversion.importer import RetainedStateImporter, prepare_source
from provisioner.controlplane.conversion.originals import RetainedOriginalStore
from provisioner.controlplane.conversion.proofs import ConversionProofs, PURPOSES, scope_digest
from provisioner.controlplane.evidence.audit import AuditCheckpointRepository
from provisioner.controlplane.evidence.gate import EvidenceMutationGate
from provisioner.controlplane.evidence.object_lock import S3ObjectLockArtifactStore, S3ObjectLockCheckpointStore
from provisioner.controlplane.evidence.repository import EvidenceRepository
from provisioner.controlplane.evidence.vault import VaultTransitSigner, VaultTransitVerifier
from provisioner.controlplane.jobs.repository import _tenant
from provisioner.controlplane.persistence import AuditContext, EnterpriseRecordStore, NativeBinding, TenantContext
from provisioner.controlplane.persistence.migrate import apply_migrations
from provisioner.controlplane.reconciliation.registry import NativeLeaseAuthority
from provisioner.controlplane.worker.grants import GrantRequest, PostgresWorkerGrants, VerifiedWorkerIdentity
from provisioner.domain.enterprise_records import plan_digest, validate_record
from provisioner.execution.run_files import encoded
from tests.provisioning.conversion.fixtures import authenticated_source, CryptoTransit, envelope, initial_statements
from tests.provisioning.evidence.test_retained_adapters import FakeObjectLock
from tests.provisioning.schema.test_enterprise_records import plan


@unittest.skipUnless(os.environ.get('HOSTING_TEST_POSTGRES_ADMIN_DSN')
                     and os.environ.get('HOSTING_TEST_POSTGRES_RUNTIME_DSN')
                     and os.environ.get('HOSTING_TEST_POSTGRES_MIGRATION_DSN')
                     and os.environ.get('HOSTING_TEST_POSTGRES_ISOLATED') == '1',
                     'Requires explicitly isolated admin, runtime and non-bypass migration PostgreSQL roles')
class RetainedImportPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        cls.psycopg=psycopg
        cls.admin_dsn=os.environ['HOSTING_TEST_POSTGRES_ADMIN_DSN']
        cls.runtime_dsn=os.environ['HOSTING_TEST_POSTGRES_RUNTIME_DSN']
        cls.migration_dsn=os.environ['HOSTING_TEST_POSTGRES_MIGRATION_DSN']
        apply_migrations(lambda:psycopg.connect(cls.migration_dsn))
        with psycopg.connect(cls.admin_dsn) as connection:
            for role in ('hosting_conversion_test_verifier','hosting_conversion_test_commissioner'):
                connection.execute("DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='"+role+
                    "') THEN CREATE ROLE "+role+" NOLOGIN NOSUPERUSER NOBYPASSRLS; END IF; END $$")
                connection.execute('GRANT USAGE ON SCHEMA hosting_controlplane TO '+role)
            connection.execute('GRANT SELECT ON hosting_controlplane.retained_conversion_keys,'
                'hosting_controlplane.retained_conversion_key_revocations,hosting_controlplane.retained_conversion_proofs,'
                'hosting_controlplane.evidence_entries TO hosting_conversion_test_verifier')
            connection.execute('GRANT INSERT ON hosting_controlplane.retained_conversion_proofs '
                               'TO hosting_conversion_test_verifier')
            connection.execute('GRANT SELECT,INSERT ON hosting_controlplane.retained_conversion_keys,'
                'hosting_controlplane.retained_conversion_key_revocations TO hosting_conversion_test_commissioner')

    @classmethod
    def runtime(cls):return cls.psycopg.connect(cls.runtime_dsn)

    @classmethod
    def role(cls, name):
        if name not in {'hosting_conversion_test_verifier','hosting_conversion_test_commissioner'}:
            raise ValueError('Only fixed independent test roles are allowed')
        connection=cls.psycopg.connect(cls.admin_dsn)
        connection.execute('SET ROLE '+name)
        return connection

    def setUp(self):
        self.f,self.path,self.value=authenticated_source(self,unknown=True)
        self.source=prepare_source(self.path,self.f.source_root,as_of=self.f.as_of)
        self.scope=self.value['inventory']['scope']
        self.batch=self.value['inventory']['batchId']
        self.context=TenantContext(self.scope['organizationId'],self.scope['tenantId'])
        self.foreign=TenantContext(self.context.organization_id,'foreign-tenant')
        self.transit=CryptoTransit()
        self.verifier=VaultTransitVerifier(self.transit,self.transit.trust())
        signer=VaultTransitSigner(self.transit,key_id='checkpoint',mount='transit',key='checkpoint')
        self.lock_service=FakeObjectLock()
        artifacts=S3ObjectLockArtifactStore(self.lock_service,'proof-artifacts',retention_days=365,prefix='artifacts')
        evidence_checkpoints=S3ObjectLockCheckpointStore(self.lock_service,'independent-checkpoints',
            stream='evidence_entries',retention_days=365,prefix='evidence')
        audit_checkpoints=S3ObjectLockCheckpointStore(self.lock_service,'independent-checkpoints',
            stream='audit_events',retention_days=365,prefix='audit')
        self.repository=EvidenceRepository(self.runtime,artifacts,evidence_checkpoints,signer,self.verifier)
        audit=AuditCheckpointRepository(self.runtime,audit_checkpoints,signer,self.verifier)
        self.gate=EvidenceMutationGate(audit,self.repository,max_unanchored_count=0)
        self.repository.initialize(self.context)
        audit.initialize(self.context,expected_sequence=0,expected_head_hash='0'*64)
        self.repository.initialize(self.foreign)
        audit.initialize(self.foreign,expected_sequence=0,expected_head_hash='0'*64)
        self.proofs=ConversionProofs(lambda:self.role('hosting_conversion_test_verifier'),
                                    evidence_gate=self.gate,verifier=self.verifier)
        self.originals=RetainedOriginalStore(self.lock_service,'restricted-originals',retention_days=365,
                                             prefix='originals',kms_key_id='synthetic-restricted-kms')
        self.importer=RetainedStateImporter(self.runtime,proofs=self.proofs,originals=self.originals,
                                           evidence_gate=self.gate)
        self.owner=RetainedStateHandover(self.importer)
        self.store=EnterpriseRecordStore(self.runtime)
        with self.role('hosting_conversion_test_commissioner') as connection,connection.cursor() as cursor:
            _tenant(cursor,self.context)
            for purpose in sorted(PURPOSES):
                cursor.execute('INSERT INTO hosting_controlplane.retained_conversion_keys '
                    '(organization_id,tenant_id,security_domain_id,workload_id,scope_digest,key_id,purpose,'
                    'subject_id,verifier_role,valid_from,valid_until) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,'
                    "clock_timestamp()-interval '1 minute',clock_timestamp()+interval '1 hour')",
                    (self.context.organization_id,self.context.tenant_id,self.scope['securityDomainId'],
                     self.scope['workloadId'],scope_digest(self.scope),purpose.lower(),purpose,
                     purpose.lower()+'-reviewer','hosting_conversion_test_verifier'))
        self.initial=self.publish(initial_statements(self.source))

    def publish(self, statements):
        events={}
        for purpose,statement in statements.items():
            event='proof-'+purpose.lower()+'-'+uuid4().hex
            signed=envelope(self.transit,purpose,self.source,statement)
            self.repository.append(self.context,event_key=event,evidence_kind='RECOVERY_DECISION',
                                   subject_id=self.batch,artifact=signed)
            self.proofs.intake(self.context,self.scope,event_key=event,batch_id=self.batch,
                              manifest_digest=self.source.batch_digest,purpose=purpose)
            events[purpose]=event
        return events

    def import_once(self):
        result=self.importer.import_batch(self.path,self.f.source_root,proof_events=self.initial)
        self.gate.checkpoint(self.context)
        return result

    def handover_events(self, *, outcome='NO_EFFECT'):
        inspected=self.owner.inspect(self.context,self.batch)
        state_digest=inspected['reconciliationDigest']
        current=initial_statements(self.source)
        native=current['NATIVE'];native['reconciliationDigest']=state_digest
        for task in native['tasks']:task.update(outcome=outcome,nativeQuiesced=True)
        exclusion=current['EXCLUSION'];exclusion.update(reconciliationDigest=state_digest,nativeTasksQuiesced=True)
        accepted={'reconciliationDigest':state_digest,'nativeEpochs':[
            {key:row[key] for key in ('binding','sourceEpoch','targetEpoch')}
            for row in inspected['state']['nativeEpochs']],
            'writeAdmissionUntil':(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat()}
        return self.publish({'NATIVE':native,'EXCLUSION':exclusion,'OWNER':accepted,
                             'SECURITY':deepcopy(accepted),'CUSTODY':current['CUSTODY']})

    def require_admission(self, context=None):
        with self.runtime() as connection,connection.cursor() as cursor:
            require_write_admission(cursor,context or self.context,
                security_domain_id=self.scope['securityDomainId'],workload_id=self.scope['workloadId'])

    def test_actual_import_preserves_history_original_bytes_counts_and_unknown_start(self):
        receipt=self.import_once()
        self.assertTrue(receipt.imported)
        self.assertEqual((receipt.history_count,receipt.native_count,receipt.recovery_count),(2,3,1))
        self.assertFalse(receipt.retry_authorized)
        self.assertEqual(self.store.get(self.context,'Workload',self.scope['workloadId']).revision,2)
        self.assertEqual(self.originals.read(self.source.batch_digest),self.path.read_bytes())
        for raw in self.source.snapshot.raw.values():
            from provisioner.execution.run_files import digest
            self.assertEqual(self.originals.read(digest(raw)),raw)
        state=self.owner.inspect(self.context,self.batch)
        self.assertEqual(state['serviceMode'],'OBSERVATION_ONLY')
        self.assertEqual(state['state']['historyCount'],2)
        self.assertEqual(state['state']['recovery'][0]['outcome'],'UNKNOWN')
        self.assertEqual({row['currentEpoch'] for row in state['state']['nativeEpochs']},{1})
        self.assertFalse(self.importer.import_batch(self.path,self.f.source_root,proof_events=self.initial).imported)
        with self.assertRaises(AuthorityDenied):self.require_admission()

    def test_current_independent_handover_advances_once_and_original_start_never_replays(self):
        self.import_once();events=self.handover_events()
        result=self.owner.accept_handover(self.context,self.batch,proof_events=events)
        self.assertTrue(result['advanced']);self.require_admission()
        self.assertFalse(self.owner.accept_handover(self.context,self.batch,proof_events=events)['advanced'])
        state=self.owner.inspect(self.context,self.batch)
        self.assertEqual({row['currentEpoch'] for row in state['state']['nativeEpochs']},{2})
        with self.runtime() as connection,connection.cursor() as cursor:
            _tenant(cursor,self.context)
            cursor.execute('SELECT original_outcome,retry_authorized FROM hosting_controlplane.retained_conversion_recovery '
                'WHERE organization_id=%s AND tenant_id=%s AND batch_id=%s',
                (self.context.organization_id,self.context.tenant_id,self.batch))
            self.assertEqual(cursor.fetchone(),('UNKNOWN',False))
            cursor.execute('SELECT disposition FROM hosting_controlplane.retained_conversion_resolutions '
                'WHERE organization_id=%s AND tenant_id=%s AND batch_id=%s',
                (self.context.organization_id,self.context.tenant_id,self.batch))
            self.assertEqual(cursor.fetchone(),('NO_EFFECT_NO_REPLAY',))

    def test_observation_only_blocks_actual_owner_acquisition_and_raw_epoch_mutation(self):
        self.import_once();binding=NativeBinding.from_record(self.source.epochs[0]['binding'])
        scope={'organizationId':self.context.organization_id,'tenantId':self.context.tenant_id,
               'securityDomainId':self.scope['securityDomainId'],'platformFamily':binding.platform_family,
               'endpointId':binding.endpoint_id,'nativeScopeId':binding.native_scope_id,
               'locationId':self.scope['locationId']}
        with self.assertRaises(AuthorityDenied):
            self.store.acquire_owner_lease(self.context,scope,binding,self.scope['workloadId'],
                                           'new-worker',60,AuditContext('operator','observation-hold'))
        with self.runtime() as connection,connection.cursor() as cursor:
            _tenant(cursor,self.context)
            with self.assertRaises(self.psycopg.errors.RaiseException):
                cursor.execute('UPDATE hosting_controlplane.native_ownership SET lease_epoch=lease_epoch+1 '
                    'WHERE platform_family=%s AND endpoint_id=%s AND native_scope_id=%s AND resource_kind=%s AND native_id=%s',
                    binding.key())
        self.assertEqual({r['currentEpoch'] for r in self.owner.inspect(self.context,self.batch)['state']['nativeEpochs']},{1})

    def test_unknown_original_native_disposition_cannot_arm_or_advance(self):
        self.import_once();events=self.handover_events(outcome='UNKNOWN')
        with self.assertRaisesRegex(ValueError,'Unknown/active'):
            self.owner.accept_handover(self.context,self.batch,proof_events=events)
        with self.assertRaises(AuthorityDenied):self.require_admission()

    def test_new_canonical_revision_invalidates_reviewed_reconciliation_digest(self):
        self.import_once();events=self.handover_events()
        successor=deepcopy(self.source.history[-1]);successor['metadata'].update(revision=3,ownerId='changed-owner')
        self.store.update(self.context,successor,2,AuditContext('actual-record-writer','scope-changed'))
        self.gate.checkpoint(self.context)
        with self.assertRaises(ValueError):
            self.owner.accept_handover(self.context,self.batch,proof_events=events)
        with self.assertRaises(AuthorityDenied):self.require_admission()

    def test_current_signer_revocation_closes_accepted_scope_without_rewriting_history(self):
        self.import_once();self.owner.accept_handover(self.context,self.batch,proof_events=self.handover_events())
        self.require_admission()
        with self.role('hosting_conversion_test_commissioner') as connection,connection.cursor() as cursor:
            _tenant(cursor,self.context)
            cursor.execute('INSERT INTO hosting_controlplane.retained_conversion_key_revocations '
                '(organization_id,tenant_id,scope_digest,key_id,purpose,reason_ref) VALUES(%s,%s,%s,%s,%s,%s)',
                (self.context.organization_id,self.context.tenant_id,scope_digest(self.scope),'native','NATIVE','review-withdrawn'))
        with self.assertRaises(AuthorityDenied):self.require_admission()
        self.assertEqual({r['currentEpoch'] for r in self.owner.inspect(self.context,self.batch)['state']['nativeEpochs']},{2})

    def test_revoked_retained_key_denies_next_use_of_authentic_current_native_worker_grant(self):
        self.import_once();self.owner.accept_handover(self.context,self.batch,proof_events=self.handover_events())
        now=datetime.now(timezone.utc)
        source={key:self.scope[key] for key in ('organizationId','tenantId','securityDomainId',
            'platformFamily','endpointId','nativeScopeId','locationId')}
        destination={**source,'securityDomainId':'wsd-destination',
                     'endpointId':'destination-'+uuid4().hex[:16],'nativeScopeId':'project-destination'}
        selected=plan(source,destination)
        selected['metadata'].update(organizationId=self.context.organization_id,tenantId=self.context.tenant_id,
                                    planId='converted-plan-'+uuid4().hex)
        spec=selected['spec'];spec.update(workloadId=self.scope['workloadId'],workloadRevision=2,
            selectedMachineIds=['machine-1'],selectedDatasetIds=['dataset-1'])
        spec['machineMappings']=spec['machineMappings'][:1]
        spec['machineMappings'][0].update(sourceBinding=next(row['binding'] for row in self.source.epochs
            if row['binding']['resourceKind']=='vm'),diskMappings=[])
        spec['machineMappings'][0]['nicMappings']=spec['machineMappings'][0]['nicMappings'][:1]
        spec['datasetMappings']=spec['datasetMappings'][:1]
        selected['metadata']['planDigest']=plan_digest(selected)
        self.assertEqual(validate_record(selected,workload=self.source.history[-1]),[])
        self.store.create(self.context,selected,AuditContext('converted-plan-author','fixture-approved-plan'))
        source_scope,destination_scope=PlanScope.from_record(source),PlanScope.from_record(destination)
        binding=NativeBinding.from_record(spec['machineMappings'][0]['sourceBinding'])
        identity=VerifiedWorkerIdentity(self.context.organization_id,self.context.tenant_id,'converted-worker',
            source_scope.site_id,uuid4().hex+uuid4().hex,now+timedelta(minutes=30))
        job_id='converted-job-'+uuid4().hex
        approvals=tuple('approval-'+uuid4().hex for _ in range(4))
        with self.psycopg.connect(self.migration_dsn) as connection,connection.cursor() as cursor:
            _tenant(cursor,self.context)
            roles=(('SOURCE_OWNER',source_scope),('DESTINATION_OWNER',destination_scope),
                   ('SOURCE_SECURITY',source_scope),('DESTINATION_SECURITY',destination_scope))
            for index,((role,scope),approval) in enumerate(zip(roles,approvals)):
                cursor.execute('INSERT INTO hosting_controlplane.plan_approvals '
                    '(approval_id,organization_id,tenant_id,plan_id,plan_revision,plan_digest,revocation_epoch,'
                    'role,site_id,security_domain_id,endpoint_id,native_scope_id,platform_family,approver_subject,issued_at,expires_at) '
                    'VALUES(%s,%s,%s,%s,1,%s,0,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                    (approval,self.context.organization_id,self.context.tenant_id,selected['metadata']['planId'],
                     selected['metadata']['planDigest'],role,scope.site_id,scope.security_domain_id,scope.endpoint_id,
                     scope.native_scope_id,scope.platform_family,'independent-plan-reviewer-'+str(index),
                     now-timedelta(minutes=1),now+timedelta(minutes=30)))
            cursor.execute('INSERT INTO hosting_controlplane.operation_jobs '
                '(organization_id,tenant_id,job_id,idempotency_key,plan_id,plan_revision,plan_digest,'
                'source_scope,destination_scope,actor_subject,approval_ids,revocation_epoch,status) '
                "VALUES(%s,%s,%s,%s,%s,1,%s,%s::jsonb,%s::jsonb,'converted-operator',%s::jsonb,0,'STARTED')",
                (self.context.organization_id,self.context.tenant_id,job_id,'key-'+uuid4().hex,
                 selected['metadata']['planId'],selected['metadata']['planDigest'],encoded(asdict(source_scope)).decode(),
                 encoded(asdict(destination_scope)).decode(),encoded(approvals).decode()))
            for table in ('worker_enrollments','worker_certificate_versions'):
                fields='organization_id,tenant_id,worker_subject,certificate_sha256,expires_at'
                values=[self.context.organization_id,self.context.tenant_id,identity.subject,
                        identity.certificate_sha256,identity.expires_at]
                if table=='worker_enrollments':fields+=',site_id';values.append(identity.site_id)
                cursor.execute('INSERT INTO hosting_controlplane.'+table+' ('+fields+') VALUES ('+
                               ','.join(['%s']*len(values))+')',values)
            cursor.execute('INSERT INTO hosting_controlplane.worker_capabilities '
                '(organization_id,tenant_id,worker_subject,site_id,security_domain_id,endpoint_id,'
                'native_scope_id,platform_family,operation_kind,credential_ref) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                (self.context.organization_id,self.context.tenant_id,identity.subject,identity.site_id,
                 source_scope.security_domain_id,source_scope.endpoint_id,source_scope.native_scope_id,
                 source_scope.platform_family,'VM_POWER','vault:conversion-fixture-no-native-use'))
        lease=self.store.acquire_owner_lease(self.context,source,binding,self.scope['workloadId'],
            identity.subject,300,AuditContext('converted-operator','actual-new-owner'))
        leases=NativeLeaseAuthority(self.runtime)
        leases.register(self.context,lease,source_scope,lease_key='converted-lease',job_id=job_id,
                        operation_id='converted-operation',worker_identity=identity,ttl_seconds=300)
        grants=PostgresWorkerGrants(self.runtime,leases)
        request=GrantRequest(job_id,'converted-step','converted-operation','VM_POWER',source_scope,
                             'converted-lease',lease.epoch,timedelta(minutes=3))
        granted=grants.issue_grant(self.context,identity,request)
        calls=[]
        def execute():
            return grants.with_authorized_reference(self.context,identity,granted.grant_id,job_id=job_id,
                step_id=request.step_id,operation_id=request.operation_id,operation_kind=request.operation_kind,
                operation_scope=source_scope,lease_key=request.lease_key,lease_epoch=request.lease_epoch,
                use=lambda *_:calls.append('authorized-fixture-only-no-native-command'))
        execute();self.assertEqual(len(calls),1)
        with self.role('hosting_conversion_test_commissioner') as connection,connection.cursor() as cursor:
            _tenant(cursor,self.context)
            cursor.execute('INSERT INTO hosting_controlplane.retained_conversion_key_revocations '
                '(organization_id,tenant_id,scope_digest,key_id,purpose,reason_ref) VALUES(%s,%s,%s,%s,%s,%s)',
                (self.context.organization_id,self.context.tenant_id,scope_digest(self.scope),'native','NATIVE','key-withdrawn'))
        with self.assertRaises(AuthorityDenied):execute()
        self.assertEqual(len(calls),1)
        with self.runtime() as connection,connection.cursor() as cursor:
            _tenant(cursor,self.context)
            cursor.execute('SELECT expires_at>clock_timestamp() FROM hosting_controlplane.worker_grants '
                'WHERE organization_id=%s AND tenant_id=%s AND grant_id=%s',
                (self.context.organization_id,self.context.tenant_id,granted.grant_id))
            self.assertEqual(cursor.fetchone(),(True,))

    def test_import_runtime_cannot_enroll_signer_certify_proof_or_write_acceptance(self):
        for table in ('retained_conversion_keys','retained_conversion_proofs',
                      'retained_conversion_handovers','retained_conversion_resolutions'):
            with self.subTest(table=table),self.runtime() as connection,connection.cursor() as cursor:
                _tenant(cursor,self.context)
                with self.assertRaises(self.psycopg.errors.InsufficientPrivilege):
                    cursor.execute('INSERT INTO hosting_controlplane.'+table+' SELECT * FROM hosting_controlplane.'+table+' LIMIT 0')

    def test_foreign_scope_cannot_read_original_batch_and_unassociated_scope_is_unchanged(self):
        self.import_once()
        with self.runtime() as connection,connection.cursor() as cursor:
            _tenant(cursor,self.foreign)
            cursor.execute('SELECT batch_id FROM hosting_controlplane.retained_conversion_batches')
            self.assertEqual(cursor.fetchall(),[])
        with self.assertRaises(self.psycopg.errors.RaiseException):self.owner.inspect(self.foreign,self.batch)
        # Conversion adds no authority to an unassociated scope; its normal
        # plan/worker/grant/instance owners still make the actual decision.
        self.require_admission(self.foreign)

    def test_original_mutation_and_missing_custody_version_are_held(self):
        self.import_once();events=self.handover_events()
        raw=self.source.snapshot.raw['workload.json']
        from provisioner.execution.run_files import digest
        key=self.originals._key(digest(raw))
        self.lock_service.markers.append({'Key':key})
        with self.assertRaises(ValueError):self.owner.accept_handover(self.context,self.batch,proof_events=events)
        self.lock_service.markers.clear()
        with self.runtime() as connection,connection.cursor() as cursor:
            _tenant(cursor,self.context)
            with self.assertRaises(self.psycopg.errors.RaiseException):
                cursor.execute('UPDATE hosting_controlplane.retained_conversion_recovery SET retry_authorized=true '
                    'WHERE organization_id=%s AND tenant_id=%s AND batch_id=%s',
                    (self.context.organization_id,self.context.tenant_id,self.batch))


if __name__=='__main__':unittest.main()
