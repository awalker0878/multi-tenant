"""Real B09 transactions, wave-domain serialization, RLS and independent roles.

External IAM/qualification are explicitly synthetic test owners. The real
protected-descriptor/evidence admission has separate tests. No native method,
conversion, transfer, deployed IAM, concurrent estate or accepted release is
qualified by these isolated database tests.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from provisioner.controlplane.authority import postgres as authority_postgres
from provisioner.controlplane.authority.model import (
    AuthorizedPlan, PlanScope, PortfolioScope, RoleGrant, VerifiedPrincipal)
from provisioner.controlplane.jobs import AdmissionRefused, JobRepository, StartReceipt
from provisioner.controlplane.jobs.repository import _digest, _tenant
from provisioner.controlplane.persistence import TenantContext, canonical_record_digest
from provisioner.controlplane.persistence.migrate import apply_migrations
from provisioner.domain.enterprise_records import plan_digest
from provisioner.migration.wave_schedule import (
    SelectedWaveQualification, WaveBudget, WaveDefinition, WaveDomain, WaveHeld,
    WaveMember, WaveScheduler, require_wave_window)
from tests.provisioning.mobility.test_wave_schedule import member as member_fixture


@unittest.skipUnless(os.environ.get('HOSTING_TEST_POSTGRES_DSN') and
                     os.environ.get('HOSTING_TEST_POSTGRES_MIGRATION_DSN') and
                     os.environ.get('HOSTING_TEST_POSTGRES_ISOLATED') == '1',
                     'Requires explicitly isolated PostgreSQL admin and non-bypass migration roles')
class WavePostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        cls.psycopg = psycopg
        cls.dsn = os.environ['HOSTING_TEST_POSTGRES_DSN']
        cls.migration_dsn = os.environ['HOSTING_TEST_POSTGRES_MIGRATION_DSN']
        apply_migrations(lambda: psycopg.connect(cls.migration_dsn))
        with psycopg.connect(cls.dsn) as connection:
            for role in ('hosting_wave_test_runtime','hosting_wave_test_commissioner','hosting_wave_test_reviewer'):
                connection.execute("DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='"+role+
                    "') THEN CREATE ROLE "+role+" NOLOGIN NOSUPERUSER NOBYPASSRLS; END IF; END $$")
                connection.execute('GRANT USAGE ON SCHEMA hosting_controlplane TO '+role)
            runtime = 'hosting_wave_test_runtime'
            # B09's existing approved plan/workload row locks require UPDATE
            # privilege. This is the normal application role, not an authority
            # or wave-domain/release writer.
            connection.execute('GRANT SELECT,UPDATE ON hosting_controlplane.enterprise_records TO '+runtime)
            connection.execute('GRANT SELECT ON hosting_controlplane.enterprise_records,hosting_controlplane.audit_events,'
                'hosting_controlplane.plan_authority_state,hosting_controlplane.plan_approvals,'
                'hosting_controlplane.native_operation_intents,hosting_controlplane.native_operation_observations,'
                'hosting_controlplane.native_containment_holds,'
                'hosting_controlplane.migration_wave_domains,hosting_controlplane.migration_wave_domain_scopes,'
                'hosting_controlplane.migration_wave_release_acceptances TO '+runtime)
            connection.execute('GRANT SELECT,INSERT,UPDATE ON hosting_controlplane.operation_jobs,'
                'hosting_controlplane.job_outbox,hosting_controlplane.migration_wave_members,'
                'hosting_controlplane.migration_wave_resource_claims TO '+runtime)
            connection.execute('GRANT SELECT,INSERT ON hosting_controlplane.job_events,'
                'hosting_controlplane.migration_waves,hosting_controlplane.migration_wave_events TO '+runtime)
            connection.execute('GRANT EXECUTE ON FUNCTION hosting_controlplane.lock_authority_scope(text,text,text),'
                'hosting_controlplane.lock_migration_wave_domain(text,text,text),'
                'hosting_controlplane.migration_wave_pool_turn(text,text,text,text,text,text,timestamptz),'
                'hosting_controlplane.retained_conversion_write_is_admitted(text,text,text,text),'
                'hosting_controlplane.migration_wave_job_window(text,text,text),'
                'hosting_controlplane.migration_wave_release_is_current(text,text,text,text,timestamptz) TO '+runtime)
            connection.execute('GRANT SELECT,INSERT ON hosting_controlplane.migration_wave_domains,'
                'hosting_controlplane.migration_wave_domain_scopes TO hosting_wave_test_commissioner')
            connection.execute('GRANT SELECT ON hosting_controlplane.migration_wave_members,'
                'hosting_controlplane.migration_waves,hosting_controlplane.operation_jobs,'
                'hosting_controlplane.job_events,hosting_controlplane.job_outbox,'
                'hosting_controlplane.native_operation_intents,hosting_controlplane.native_operation_observations '
                'TO hosting_wave_test_reviewer')
            connection.execute('GRANT SELECT,INSERT ON hosting_controlplane.migration_wave_release_acceptances '
                'TO hosting_wave_test_reviewer')

    @classmethod
    def connection_as(cls, role):
        # Role names are constant reviewed test configuration, never input.
        connection = cls.psycopg.connect(cls.dsn)
        connection.execute('SET ROLE '+role)
        return connection

    @classmethod
    def runtime(cls):
        return cls.connection_as('hosting_wave_test_runtime')

    @classmethod
    def migration(cls):
        """Seed synthetic facts as the explicit non-bypass schema owner.

        Admin access above only provisions reviewed test roles; production
        tenant helpers and seed mutations use this separate forced-RLS owner.
        Runtime/commissioner/reviewer credentials never inherit this factory.
        """
        return cls.psycopg.connect(cls.migration_dsn)

    def setUp(self):
        self.ctx = TenantContext('wave-org-'+uuid4().hex[:12], 'tenant-a')
        self.foreign = TenantContext(self.ctx.organization_id, 'tenant-b')
        self.now = datetime.now(timezone.utc)
        self.members, self.decisions = [], {}
        self.qual = Mock(spec=SelectedWaveQualification)
        self.qual.transfer_resource_keys.return_value = ()
        self.qual.require_member.return_value = None
        self.identity = SimpleNamespace(authenticate=lambda credential:self.principal)
        self.jobs = JobRepository(self.runtime, authority_postgres)
        self.scheduler = WaveScheduler(self.runtime, self.jobs, self.identity, self.qual)

    def add_member(self, name, *, cohort='wsd-a', dependencies=(), start=None, end=None, runtime=600):
        original, observed = member_fixture(name+'-'+uuid4().hex[:8], cohort=cohort,
            start=start or self.now-timedelta(minutes=1), end=end or self.now+timedelta(hours=2),
            runtime=runtime)
        selected = original.plan
        def scoped(value):
            if isinstance(value, dict): return {key:scoped(item) for key,item in value.items()}
            if isinstance(value, list): return [scoped(item) for item in value]
            return {'org-01':self.ctx.organization_id,'tenant-01':self.ctx.tenant_id}.get(value,value) \
                if isinstance(value,str) else value
        selected, observed = scoped(selected), scoped(observed)
        selected['metadata']['planDigest'] = plan_digest(selected)
        member = WaveMember.from_plan(name, selected, original.campaign, depends_on=dependencies,
            window_start=original.window_start, window_end=original.window_end,
            runtime_seconds=original.runtime_seconds, transfer_limits=original.transfer_limits, risk_units=1)
        approval_roles = (('SOURCE_OWNER',member.source),('DESTINATION_OWNER',member.destination),
                          ('SOURCE_SECURITY',member.source),('DESTINATION_SECURITY',member.destination))
        approvals = tuple('approval-'+uuid4().hex for _ in approval_roles)
        decision = AuthorizedPlan(self.ctx.organization_id,self.ctx.tenant_id,member.plan_id,
            member.plan_revision,member.plan_digest,member.source,member.destination,approvals,0,
            self.now+timedelta(hours=1),'operator-wave')
        with self.migration() as connection, connection.cursor() as cursor:
            _tenant(cursor,self.ctx)
            for kind, identity, record in (('Workload',observed['metadata']['workloadId'],observed),
                                           ('MigrationPlan',member.plan_id,selected)):
                connection.execute('INSERT INTO hosting_controlplane.enterprise_records '
                    '(organization_id,tenant_id,record_kind,record_id,revision,record_json,record_digest) '
                    'VALUES(%s,%s,%s,%s,1,%s::jsonb,%s)',
                    (self.ctx.organization_id,self.ctx.tenant_id,kind,identity,json.dumps(record),canonical_record_digest(record)))
            connection.execute('INSERT INTO hosting_controlplane.audit_events '
                '(organization_id,tenant_id,actor_id,correlation_id,action,record_kind,record_id,revision,record_digest) '
                "VALUES(%s,%s,'plan-author',%s,'RECORD_CREATE','MigrationPlan',%s,1,%s)",
                (self.ctx.organization_id,self.ctx.tenant_id,uuid4().hex,member.plan_id,canonical_record_digest(selected)))
            for number, ((role,scope), approval_id) in enumerate(zip(approval_roles,approvals)):
                connection.execute('INSERT INTO hosting_controlplane.plan_approvals '
                    '(approval_id,organization_id,tenant_id,plan_id,plan_revision,plan_digest,revocation_epoch,role,'
                    'site_id,security_domain_id,endpoint_id,native_scope_id,platform_family,approver_subject,issued_at,expires_at) '
                    'VALUES(%s,%s,%s,%s,1,%s,0,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                    (approval_id,self.ctx.organization_id,self.ctx.tenant_id,member.plan_id,member.plan_digest,role,
                     scope.site_id,scope.security_domain_id,scope.endpoint_id,scope.native_scope_id,scope.platform_family,
                     'reviewer-'+str(number),self.now-timedelta(minutes=1),self.now+timedelta(hours=2)))
        self.members.append(member)
        self.decisions[name] = decision
        return member

    def enroll(self, *, cap=8):
        scopes = {scope:'native-risk' for member in self.members for scope in (member.source,member.destination)}
        self.domain = WaveDomain(self.ctx.organization_id,self.ctx.tenant_id,'domain-01',tuple(scopes.items()),
            WaveBudget(cap,8,3600*8,8,256*8,32*8,1024*1024*8),(('native-risk',8),),'e'*64,
            self.now-timedelta(hours=1),self.now+timedelta(days=1))
        with self.connection_as('hosting_wave_test_commissioner') as connection, connection.cursor() as cursor:
            _tenant(cursor,self.ctx)
            cursor.execute('INSERT INTO hosting_controlplane.migration_wave_domains '
                '(organization_id,tenant_id,domain_id,document_digest,document_json,enrolled_by) VALUES(%s,%s,%s,%s,%s,%s)',
                (self.ctx.organization_id,self.ctx.tenant_id,self.domain.domain_id,self.domain.digest,
                 json.dumps(self.domain.to_record(),sort_keys=True,separators=(',',':')),'independent-native-budget-owner'))
        grants = {( 'EXECUTION_OPERATOR',scope) for member in self.members for scope in (member.source,member.destination)}
        grants |= {('WORKLOAD_EDITOR',PortfolioScope(scope.organization_id,scope.tenant_id,scope.security_domain_id))
                   for member in self.members for scope in (member.source,member.destination)}
        self.principal = VerifiedPrincipal('operator-wave',self.ctx.organization_id,self.ctx.tenant_id,'HUMAN',
            self.now-timedelta(minutes=1),self.now+timedelta(hours=1),self.now,
            tuple(RoleGrant(role,scope,self.now+timedelta(hours=1)) for role,scope in grants))
        self.definition = WaveDefinition(self.ctx.organization_id,self.ctx.tenant_id,'domain-01',
                                         self.domain.digest,tuple(self.members))
        return self.definition

    def register(self):
        return self.scheduler.register('synthetic-verified-session',self.ctx,self.definition)

    def admit(self):
        return self.scheduler.admit_next('synthetic-verified-session',self.ctx,'domain-01',
            authorizations={(self.definition.digest,name):value for name,value in self.decisions.items()})

    def counts(self):
        with self.psycopg.connect(self.dsn) as connection:
            return tuple(connection.execute('SELECT count(*) FROM hosting_controlplane.'+table+
                ' WHERE organization_id=%s AND tenant_id=%s', (self.ctx.organization_id,self.ctx.tenant_id)).fetchone()[0]
                for table in ('operation_jobs','job_outbox','migration_wave_resource_claims'))

    def test_concurrent_admission_serializes_one_budget_and_one_existing_outbox(self):
        self.add_member('a'); self.add_member('b')
        self.enroll(cap=1); self.register()
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = [future.result(timeout=20) for future in [executor.submit(self.admit) for _ in range(2)]]
        self.assertEqual(sorted(row.status for row in results), ['HELD_OR_WAITING','JOB_QUEUED'])
        self.assertEqual(self.counts()[:2],(1,1))
        self.assertGreater(self.counts()[2],0)
        admitted = next(row for row in results if row.job_id)
        self.assertEqual(len(self.jobs.events(self.ctx,admitted.job_id)),1)
        self.assertFalse(admitted.mutation_authorized)

    def test_claim_journal_failure_rolls_back_job_outbox_and_every_wave_charge(self):
        self.add_member('a'); self.enroll(); self.register()
        with patch.object(self.scheduler,'_event',side_effect=OSError('synthetic journal disk/connection failure')):
            with self.assertRaises(OSError): self.admit()
        self.assertEqual(self.counts(),(0,0,0))
        self.assertEqual(self.admit().status,'JOB_QUEUED')

    def test_dependency_and_uncertain_original_job_retain_risk_and_never_fake_completion(self):
        self.add_member('a'); self.add_member('b',dependencies=('a',))
        self.enroll(); self.register()
        first = self.admit()
        self.assertEqual(first.member_id,'a')
        self.jobs.append_progress(self.ctx,first.job_id,event_key='lost-native',event_type='NATIVE_OUTCOME_UNKNOWN',
            status='HELD',detail={'stepId':'transfer','phase':'TRANSFER','reasonCode':'NATIVE_UNCERTAIN'})
        self.assertEqual(self.admit().status,'HELD_OR_WAITING')
        self.assertEqual(self.scheduler.reconcile_release('synthetic-verified-session',self.ctx,
            self.definition.digest,'a'),'HELD_NATIVE_RELEASE_ACCEPTANCE_REQUIRED')
        self.assertEqual(self.counts()[:2],(1,1))

    def test_domain_scope_fairness_alternates_verified_wsds_without_new_native_authority(self):
        self.add_member('a1'); self.add_member('a2'); self.add_member('b1',cohort='wsd-b')
        self.enroll(); self.register()
        self.assertEqual(self.admit().member_id,'a1')
        self.assertEqual(self.admit().member_id,'b1')
        self.assertEqual(self.admit().member_id,'a2')
        self.assertEqual(self.counts()[:2],(3,3))

    def test_future_and_expired_windows_create_no_workflow_and_expired_member_is_explicitly_held(self):
        self.add_member('future',start=self.now+timedelta(hours=1),end=self.now+timedelta(hours=2))
        self.add_member('expired',start=self.now-timedelta(hours=2),end=self.now-timedelta(seconds=1))
        self.enroll(); self.register()
        self.assertEqual(self.admit().status,'HELD_OR_WAITING')
        self.assertEqual(self.counts(),(0,0,0))
        with self.runtime() as connection, connection.cursor() as cursor:
            _tenant(cursor,self.ctx)
            cursor.execute('SELECT member_id,status,reason FROM hosting_controlplane.migration_wave_members '
                'WHERE organization_id=%s AND tenant_id=%s ORDER BY member_id',
                (self.ctx.organization_id,self.ctx.tenant_id))
            self.assertEqual(cursor.fetchall(),[('expired','HELD','WINDOW_EXPIRED'),('future','PENDING','PLANNING_ONLY')])

    def test_wrong_member_approval_and_actual_revocation_commit_no_job_or_charge(self):
        self.add_member('a'); self.add_member('b')
        self.enroll(); self.register()
        original = self.decisions['a']; self.decisions['a'] = self.decisions['b']
        with self.assertRaises(WaveHeld): self.admit()
        self.assertEqual(self.counts(),(0,0,0))
        self.decisions['a'] = original
        with self.migration() as connection, connection.cursor() as cursor:
            _tenant(cursor,self.ctx)
            connection.execute('UPDATE hosting_controlplane.plan_authority_state SET revocation_epoch=revocation_epoch+1 '
                'WHERE organization_id=%s AND tenant_id=%s AND plan_id=%s',
                (self.ctx.organization_id,self.ctx.tenant_id,original.plan_id))
        with self.assertRaises(PermissionError): self.admit()
        self.assertEqual(self.counts(),(0,0,0))

    def test_different_tenant_rls_hides_schedule_and_current_job_window_has_no_mutable_inputs(self):
        self.add_member('a'); self.enroll(); self.register()
        admitted = self.admit()
        self.assertIsNone(self.jobs.get(self.foreign,admitted.job_id))
        with self.runtime() as connection, connection.cursor() as cursor:
            _tenant(cursor,self.foreign)
            cursor.execute('SELECT count(*) FROM hosting_controlplane.migration_waves')
            self.assertEqual(cursor.fetchone(),(0,))
            with self.assertRaises(self.psycopg.errors.InsufficientPrivilege):
                cursor.execute('SELECT * FROM hosting_controlplane.migration_wave_job_window(%s,%s,%s)',
                    (self.ctx.organization_id,self.ctx.tenant_id,admitted.job_id))
        job = self.jobs.get(self.ctx,admitted.job_id)
        with self.runtime() as connection, connection.cursor() as cursor:
            _tenant(cursor,self.ctx)
            require_wave_window(cursor,job,self.now,starting=True)
            with self.assertRaises(WaveHeld):
                require_wave_window(cursor,job,self.now+timedelta(hours=3))
        with self.assertRaises(WaveHeld):
            self.scheduler.admit_next('synthetic-verified-session',self.foreign,'domain-01',authorizations={})

    def test_runtime_cannot_author_budget_or_release_and_second_native_budget_owner_is_rejected(self):
        self.add_member('a'); self.enroll(); self.register()
        admitted = self.admit()
        with self.runtime() as connection, connection.cursor() as cursor:
            _tenant(cursor,self.ctx)
            with self.assertRaises(self.psycopg.errors.InsufficientPrivilege):
                cursor.execute('INSERT INTO hosting_controlplane.migration_wave_domains '
                    '(organization_id,tenant_id,domain_id,document_digest,document_json,enrolled_by) VALUES(%s,%s,%s,%s,%s,%s)',
                    (self.ctx.organization_id,self.ctx.tenant_id,'forged','a'*64,'{}','operator-wave'))
        with self.runtime() as connection, connection.cursor() as cursor:
            _tenant(cursor,self.ctx)
            with self.assertRaises(self.psycopg.errors.InsufficientPrivilege):
                cursor.execute('INSERT INTO hosting_controlplane.migration_wave_release_acceptances '
                    '(organization_id,tenant_id,schedule_digest,member_id,job_id,plan_digest,start_payload_digest,'
                    'completion_event_sequence,completion_evidence_digest,transfer_stopped_evidence_digest,'
                    'owner_exclusion_evidence_digest,shared_risk_cleared_evidence_digest,acceptance_digest,'
                    'observed_at,expires_at,accepted_by) VALUES(%s,%s,%s,%s,%s,%s,%s,2,%s,%s,%s,%s,%s,%s,%s,%s)',
                    (self.ctx.organization_id,self.ctx.tenant_id,self.definition.digest,'a',admitted.job_id,
                     self.members[0].plan_digest,*(['a'*64]*6),self.now,self.now+timedelta(minutes=5),'operator-wave'))
        another = replace(self.domain,domain_id='another-owner')
        with self.connection_as('hosting_wave_test_commissioner') as connection, connection.cursor() as cursor:
            _tenant(cursor,self.ctx)
            with self.assertRaises(self.psycopg.errors.CheckViolation):
                cursor.execute('INSERT INTO hosting_controlplane.migration_wave_domains '
                    '(organization_id,tenant_id,domain_id,document_digest,document_json,enrolled_by) VALUES(%s,%s,%s,%s,%s,%s)',
                    (self.ctx.organization_id,self.ctx.tenant_id,another.domain_id,another.digest,
                     json.dumps(another.to_record()),'independent-native-budget-owner'))

    def test_original_outbox_start_uses_typed_job_window_and_retains_approval_revocation(self):
        self.add_member('a',end=self.now+timedelta(minutes=30))
        self.enroll(); self.register()
        admitted = self.admit()
        message = self.jobs.claim_start(self.ctx,dispatcher_id='wave-boundary-dispatcher')
        job = self.jobs.revalidate_start(self.ctx,message)
        self.assertEqual(job.job_id,admitted.job_id)
        with self.runtime() as connection, connection.cursor() as cursor:
            _tenant(cursor,self.ctx)
            # An AuthorizedPlan retains the pre-admission authority-only check.
            # It never replaces the persisted Job used by the B09 outbox.
            authority_postgres.revalidate_start(cursor,self.decisions['a'],self.now)
            delayed = self.members[0].window_end-timedelta(seconds=1)
            authority_postgres.revalidate_start(cursor,job,delayed)
            with self.assertRaises(WaveHeld):
                require_wave_window(cursor,job,delayed,starting=True)
            with self.assertRaises(WaveHeld):
                authority_postgres.revalidate_start(cursor,job,self.members[0].window_end)
        with self.migration() as connection, connection.cursor() as cursor:
            _tenant(cursor,self.ctx)
            connection.execute('UPDATE hosting_controlplane.plan_authority_state '
                'SET revocation_epoch=revocation_epoch+1 WHERE organization_id=%s AND tenant_id=%s AND plan_id=%s',
                (self.ctx.organization_id,self.ctx.tenant_id,job.plan_id))
        with self.assertRaises(PermissionError):
            self.jobs.revalidate_start(self.ctx,message)
        self.assertEqual(self.jobs.get(self.ctx,job.job_id).status,'QUEUED')
        self.assertEqual(self.counts()[:2],(1,1))

    def test_superseded_wave_plan_cannot_start_its_original_queued_outbox(self):
        member = self.add_member('a')
        self.enroll(); self.register(); admitted = self.admit()
        message = self.jobs.claim_start(self.ctx,dispatcher_id='wave-revision-dispatcher')
        self.jobs.revalidate_start(self.ctx,message)
        revised = deepcopy(member.plan)
        revised['metadata']['revision'] += 1
        revised['spec']['maxDowntimeSeconds'] += 1
        revised['metadata']['planDigest'] = plan_digest(revised)
        with self.migration() as connection, connection.cursor() as cursor:
            _tenant(cursor,self.ctx)
            cursor.execute('UPDATE hosting_controlplane.enterprise_records SET revision=%s,record_json=%s::jsonb,'
                'record_digest=%s WHERE organization_id=%s AND tenant_id=%s AND record_kind=%s AND record_id=%s',
                (revised['metadata']['revision'],json.dumps(revised),canonical_record_digest(revised),
                 self.ctx.organization_id,self.ctx.tenant_id,'MigrationPlan',member.plan_id))
        with self.assertRaises(AdmissionRefused):
            self.jobs.revalidate_start(self.ctx,message)
        self.assertEqual(self.jobs.get(self.ctx,admitted.job_id).status,'QUEUED')
        self.assertEqual(self.counts()[:2],(1,1))

    def test_independent_reviewer_cannot_accept_empty_native_inventory_or_a_fake_success_projection(self):
        self.add_member('a'); self.add_member('b',dependencies=('a',))
        self.enroll(); self.register()
        admitted = self.admit()
        job, message, event = self.finished_fixture(admitted)
        with self.assertRaises(self.psycopg.errors.CheckViolation):
            self.accept_fixture(job, message, event)
        self.assertEqual(self.scheduler.reconcile_release('synthetic-verified-session',self.ctx,
            self.definition.digest,'a'),'HELD_NATIVE_RELEASE_ACCEPTANCE_REQUIRED')
        self.assertEqual(self.admit().status,'HELD_OR_WAITING')
        self.assertEqual(self.counts()[:2],(1,1))

    def finished_fixture(self, admitted):
        message = self.jobs.claim_start(self.ctx,dispatcher_id='wave-test-dispatcher')
        self.jobs.revalidate_start(self.ctx,message)
        self.jobs.record_start_attempt(self.ctx,message,namespace='wave-test',retention_seconds=86400)
        job = self.jobs.get(self.ctx,admitted.job_id)
        self.jobs.mark_started(self.ctx,message,StartReceipt('wave-test',job.job_id,'run-'+uuid4().hex,
            job.job_id,job.plan_id,job.plan_revision,job.plan_digest,_digest(message.payload)),namespace='wave-test')
        # The trusted projection is real, but this deliberately synthetic test
        # has never contacted a native target or registered any native intent.
        event = self.jobs.append_progress(self.ctx,job.job_id,event_key='synthetic-finished',
            event_type='WORKFLOW_FINISHED',status='SUCCEEDED',detail={
                'stepId':'verify','phase':'VERIFY','evidenceDigest':'f'*64,'completed':1,'total':1})
        return job, message, event

    def accept_fixture(self, job, message, event):
        at = datetime.now(timezone.utc)
        with self.connection_as('hosting_wave_test_reviewer') as connection, connection.cursor() as cursor:
            _tenant(cursor,self.ctx)
            cursor.execute('INSERT INTO hosting_controlplane.migration_wave_release_acceptances '
                '(organization_id,tenant_id,schedule_digest,member_id,job_id,plan_digest,start_payload_digest,'
                'completion_event_sequence,completion_evidence_digest,transfer_stopped_evidence_digest,'
                'owner_exclusion_evidence_digest,shared_risk_cleared_evidence_digest,acceptance_digest,'
                'observed_at,expires_at,accepted_by) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                (self.ctx.organization_id,self.ctx.tenant_id,self.definition.digest,'a',job.job_id,job.plan_digest,
                 _digest(message.payload),event.sequence,'f'*64,*(['a'*64]*4),at,
                 at+timedelta(minutes=5),'independent-native-release-owner'))

    def native_ledger_fixture(self, job):
        """Tenant-constrained synthetic ledger seeding, never native execution."""
        member = self.members[0]
        binding = member.plan['spec']['machineMappings'][0]['sourceBinding']
        native = (member.source.platform_family,member.source.endpoint_id,member.source.native_scope_id,
                  binding['resourceKind'],binding['nativeId'])
        tenant = (self.ctx.organization_id,self.ctx.tenant_id)
        with self.migration() as connection, connection.cursor() as cursor:
            _tenant(cursor,self.ctx)
            cursor.execute('INSERT INTO hosting_controlplane.native_ownership '
                '(platform_family,endpoint_id,native_scope_id,resource_kind,native_id,organization_id,tenant_id,'
                'security_domain_id,workload_id,worker_id,lease_expires_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                (*native,*tenant,member.source.security_domain_id,member.plan['spec']['workloadId'],
                 'synthetic-fenced-worker',self.now+timedelta(hours=1)))
            cursor.execute('INSERT INTO hosting_controlplane.native_operation_leases '
                '(organization_id,tenant_id,lease_key,job_id,operation_id,platform_family,endpoint_id,native_scope_id,'
                'resource_kind,native_id,site_id,security_domain_id,worker_id,owner_epoch,expires_at) '
                'VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1,%s)',
                (*tenant,'synthetic-release-lease',job.job_id,'synthetic-source-fence',*native,member.source.site_id,
                 member.source.security_domain_id,'synthetic-fenced-worker',self.now+timedelta(hours=1)))
            cursor.execute('INSERT INTO hosting_controlplane.native_operation_intents '
                '(organization_id,tenant_id,operation_id,job_id,grant_id,step_id,lease_key,platform_family,endpoint_id,'
                'native_scope_id,resource_kind,native_id,workload_id,security_domain_id,worker_id,owner_epoch,'
                'operation_kind,request_digest) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1,%s,%s)',
                (*tenant,'synthetic-source-fence',job.job_id,'synthetic-grant','source-fence','synthetic-release-lease',
                 *native,member.plan['spec']['workloadId'],member.source.security_domain_id,
                 'synthetic-fenced-worker','SOURCE_FENCE','d'*64))
            for state in ('IN_FLIGHT','UNCERTAIN'):
                cursor.execute('UPDATE hosting_controlplane.native_operation_intents SET state=%s '
                    'WHERE organization_id=%s AND tenant_id=%s AND operation_id=%s',
                    (state,*tenant,'synthetic-source-fence'))
            self.append_native_observation(cursor,'EFFECT_PRESENT',True)
            cursor.execute("UPDATE hosting_controlplane.native_operation_intents SET state='RESOLVED',"
                "outcome='EFFECT_PRESENT',resolution_evidence_digest=%s WHERE organization_id=%s "
                'AND tenant_id=%s AND operation_id=%s', ('d'*64,*tenant,'synthetic-source-fence'))
        return native

    def append_native_observation(self, cursor, outcome, quiesced):
        cursor.execute('INSERT INTO hosting_controlplane.native_operation_observations '
            '(organization_id,tenant_id,observation_id,operation_id,evidence_digest,observer_subject,'
            'outcome,native_quiesced,observed_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,clock_timestamp())',
            (self.ctx.organization_id,self.ctx.tenant_id,'synthetic-readback-'+uuid4().hex,
             'synthetic-source-fence','d'*64,'synthetic-independent-reader',outcome,quiesced))

    def test_independent_reviewer_positive_release_rechecks_latest_native_observation_before_releasing(self):
        self.add_member('a'); self.add_member('b',dependencies=('a',))
        self.enroll(cap=1); self.register()
        admitted = self.admit()
        job, message, event = self.finished_fixture(admitted)
        self.native_ledger_fixture(job)
        # The independently configured reviewer has no private helper execute
        # or containment read. Owner-definer validation must still work.
        with self.connection_as('hosting_wave_test_reviewer') as connection, connection.cursor() as cursor:
            _tenant(cursor,self.ctx)
            cursor.execute("SELECT has_table_privilege(current_user,'hosting_controlplane.native_containment_holds','SELECT'),"
                "has_function_privilege(current_user,'hosting_controlplane.migration_wave_release_payload_is_current("
                "hosting_controlplane.migration_wave_release_acceptances,timestamp with time zone)','EXECUTE')")
            self.assertEqual(cursor.fetchone(),(False,False))
        self.accept_fixture(job,message,event)
        with self.migration() as connection, connection.cursor() as cursor:
            _tenant(cursor,self.ctx)
            self.append_native_observation(cursor,'IN_PROGRESS',False)
        with self.assertRaises(self.psycopg.errors.CheckViolation):
            self.scheduler.reconcile_release('synthetic-verified-session',self.ctx,self.definition.digest,'a')
        self.assertEqual(self.admit().status,'HELD_OR_WAITING')
        with self.migration() as connection, connection.cursor() as cursor:
            _tenant(cursor,self.ctx)
            self.append_native_observation(cursor,'EFFECT_PRESENT',True)
        # A fresh independent acceptance observation is needed after changed
        # facts; the original acceptance must never inherit this new readback.
        with self.assertRaises(self.psycopg.errors.CheckViolation):
            self.scheduler.reconcile_release('synthetic-verified-session',self.ctx,self.definition.digest,'a')
        self.assertEqual(self.counts()[:2],(1,1))

    def test_independent_reviewer_positive_acceptance_releases_charges_and_unblocks_dependency(self):
        self.add_member('a'); self.add_member('b',dependencies=('a',))
        self.enroll(cap=1); self.register()
        admitted = self.admit()
        job, message, event = self.finished_fixture(admitted)
        self.native_ledger_fixture(job)
        self.accept_fixture(job,message,event)
        self.assertEqual(self.scheduler.reconcile_release('synthetic-verified-session',self.ctx,
            self.definition.digest,'a'),'ACCEPTED_AND_RELEASED')
        self.assertEqual(self.scheduler.reconcile_release('synthetic-verified-session',self.ctx,
            self.definition.digest,'a'),'ALREADY_ACCEPTED_AND_RELEASED')
        self.assertEqual(self.admit().member_id,'b')
        self.assertEqual(self.counts()[:2],(2,2))

    def test_independent_reviewer_refuses_containment_even_with_complete_resolved_native_fixture(self):
        self.add_member('a'); self.enroll(); self.register()
        admitted = self.admit()
        job, message, event = self.finished_fixture(admitted)
        native = self.native_ledger_fixture(job)
        with self.migration() as connection, connection.cursor() as cursor:
            _tenant(cursor,self.ctx)
            cursor.execute('INSERT INTO hosting_controlplane.native_containment_holds '
                '(platform_family,endpoint_id,native_scope_id,resource_kind,native_id,organization_id,tenant_id,'
                'incident_id,actor_subject,reason) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                (*native,self.ctx.organization_id,self.ctx.tenant_id,'synthetic-incident',
                 'independent-incident-owner','Synthetic writer exclusion failed'))
        with self.assertRaises(self.psycopg.errors.CheckViolation):
            self.accept_fixture(job,message,event)
        self.assertEqual(self.scheduler.reconcile_release('synthetic-verified-session',self.ctx,
            self.definition.digest,'a'),'HELD_NATIVE_RELEASE_ACCEPTANCE_REQUIRED')


if __name__ == '__main__':
    unittest.main()
