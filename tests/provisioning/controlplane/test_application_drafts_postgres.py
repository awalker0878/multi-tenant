"""Real database tests: unreviewed drafts remain append-only and tenant scoped."""
import copy
import hashlib
import os
import threading
import unittest
from dataclasses import replace

from provisioner.controlplane.discovery.application_drafts import ApplicationDraftRepository, ApplicationDraftConflict
from provisioner.controlplane.discovery.grouping import GroupingHeld
from provisioner.controlplane.discovery.model import _json
from provisioner.controlplane.discovery.persistence import DiscoveryRepository
from provisioner.controlplane.persistence.store import AuditContext, TenantContext
from tests.provisioning.controlplane import test_discovery_persistence as support


@unittest.skipUnless(os.environ.get('HOSTING_TEST_POSTGRES_DISCOVERY_DSN') and
                     os.environ.get('HOSTING_TEST_POSTGRES_RUNTIME_DSN'),
                     'Requires disposable PostgreSQL discovery/runtime roles')
class ApplicationDraftPostgresTests(unittest.TestCase):
    setUpClass = classmethod(support.DiscoveryPersistenceTests.setUpClass.__func__)
    _campaign = support.DiscoveryPersistenceTests._campaign
    _object = support.DiscoveryPersistenceTests._object
    _publish = support.DiscoveryPersistenceTests._publish

    def setUp(self):
        support.DiscoveryPersistenceTests.setUp(self)
        self.repo=ApplicationDraftRepository(lambda:self.psycopg.connect(self.runtime_dsn))
        self.source=self._publish(self._campaign('first'),'PARTIAL',
            (self._object('vm-1','Database'),self._object('vm-2','Frontend')),('VISIBLE_INVENTORY_ONLY',))
        self.audit=AuditContext('oidc|author@example.org','draft-test')
        self.checks=[]
        self.content={'draft':{'applicationGroupId':'app-1','name':'Application','ownerId':'owner-ref',
            'members':[{'workloadId':logical,'nativeVm':list(self._object(native,logical).identity.key())}
                       for logical,native in (('db','vm-1'),('web','vm-2'))],
            'datasetIds':['data-1'],'consistencyGroups':[{'groupId':'cg-1','datasetIds':['data-1']}],
            'startupOrder':['db','web']},
            'dependencies':[{'assertionId':'edge-1','sourceWorkloadId':'web','targetWorkloadId':None,
                'relation':'SERVICE_CALL','state':'UNKNOWN','source':'MONITORING','sourceReference':'trace-1',
                'observedAt':self.source.captured_at.isoformat(),'unknownReason':'UNRESOLVED_TARGET'}]}

    def authorize(self,scope,at):
        self.assertEqual(scope,self.scope); self.assertIsNotNone(at.tzinfo); self.checks.append(at)

    def save(self,**changes):
        values=dict(generation=1,result_digest=self.source.result_digest,content=self.content,
                    expected_revision=0,audit=self.audit,authorize=self.authorize)
        values.update(changes)
        return self.repo.save(self.ctx,self.scope,self.environment_id,**values)

    def get(self,**changes):
        return self.repo.get(self.ctx,self.scope,self.environment_id,'app-1',authorize=self.authorize,**changes)

    def test_partial_draft_preserves_unknowns_and_authenticated_attribution(self):
        saved=self.save(); value=self.get()
        self.assertEqual(saved.revision,1)
        self.assertEqual(value['status'],'UNREVIEWED')
        self.assertEqual(value['recordedBy'],self.audit.actor_id)
        self.assertEqual(value['proposal']['draft']['ownerId'],'owner-ref')
        self.assertEqual(value['proposal']['dependencies'],self.content['dependencies'])
        self.assertFalse(value['ownershipAccepted']); self.assertFalse(value['executionAuthorized'])
        self.assertFalse(value['sourceSuperseded'])
        self.assertGreaterEqual(len(self.checks),5)

    def test_identical_retry_retains_revision_time_and_one_audit_event(self):
        first=self.save(); second=self.save()
        self.assertEqual(first,second)
        with self.repo._session(self.ctx,self.scope,self.environment_id,self.authorize) as con:
            count=con.execute("SELECT count(*) FROM hosting_controlplane.audit_events WHERE "
                "record_kind='ApplicationDraft' AND record_id='app-1'").fetchone()[0]
            self.assertEqual(count,1)

    def test_changed_actor_or_payload_cannot_replay_original_append(self):
        self.save()
        with self.assertRaises(ApplicationDraftConflict):
            self.save(audit=AuditContext('another-subject','other-request'))
        value=copy.deepcopy(self.content); value['draft']['name']='Different'
        with self.assertRaises(ApplicationDraftConflict): self.save(content=value)

    def test_append_and_historical_read_do_not_rewrite_previous_record(self):
        self.save(); value=copy.deepcopy(self.content); value['draft']['name']='Changed'
        self.save(content=value,expected_revision=1)
        self.assertEqual(self.get()['revision'],2)
        self.assertEqual(self.get(revision=1)['proposal']['draft']['name'],'Application')
        self.assertIsNone(self.get(revision=3))

    def test_new_generation_blocks_changed_draft_but_exact_retry_stays_historical(self):
        self.save()
        self._publish(self._campaign('new'),'PARTIAL',(self._object('vm-1','New'),),('VISIBLE_INVENTORY_ONLY',))
        with self.assertRaises(ApplicationDraftConflict): self.save(expected_revision=1)
        self.assertEqual(self.save().revision,1)
        self.assertTrue(self.get()['sourceSuperseded'])
        self.assertEqual(self.get()['latestGeneration'],2)

    def test_wrong_digest_unobserved_member_and_empty_members_never_append(self):
        with self.assertRaises(ApplicationDraftConflict): self.save(result_digest='f'*64)
        for native in ('foreign','vm-3'):
            value=copy.deepcopy(self.content); value['draft']['members'][1]['nativeVm'][-1]=native
            with self.assertRaises(GroupingHeld): self.save(content=value)
        value=copy.deepcopy(self.content); value['draft']['members']=[]
        with self.assertRaises(GroupingHeld): self.save(content=value)
        self.assertIsNone(self.get())

    def test_revocation_after_insert_rolls_back_record_and_audit(self):
        calls=[]
        def revoked(scope,at):
            calls.append(at)
            if len(calls)==3: raise PermissionError('revoked')
        with self.assertRaises(PermissionError): self.save(authorize=revoked)
        self.assertIsNone(self.get())
        with self.repo._session(self.ctx,self.scope,self.environment_id,self.authorize) as con:
            self.assertEqual(con.execute("SELECT count(*) FROM hosting_controlplane.audit_events "
                "WHERE record_kind='ApplicationDraft'").fetchone()[0],0)

    def test_concurrent_editors_have_one_winner_and_no_revision_gap(self):
        self.save(); barrier=threading.Barrier(2); outcomes=[]
        def worker(name):
            value=copy.deepcopy(self.content); value['draft']['name']=name
            barrier.wait(timeout=5)
            try: outcomes.append(self.save(content=value,expected_revision=1).revision)
            except ApplicationDraftConflict: outcomes.append('conflict')
        threads=[threading.Thread(target=worker,args=(name,)) for name in ('one','two')]
        for thread in threads: thread.start()
        for thread in threads: thread.join(timeout=10); self.assertFalse(thread.is_alive())
        self.assertCountEqual(outcomes,[2,'conflict'])
        self.assertEqual(self.get()['revision'],2)

    def test_authority_is_rechecked_after_waiting_for_source_lock(self):
        initial=threading.Event(); revoked=threading.Event(); outcomes=[]
        args=DiscoveryRepository._scope_args(self.ctx,self.scope,self.environment_id)
        key=int.from_bytes(hashlib.sha256(_json(args).encode()).digest()[:8],'big',signed=True)
        def authorize(scope,at):
            initial.set()
            if revoked.is_set(): raise PermissionError('revoked while waiting')
        def worker():
            try: self.save(authorize=authorize); outcomes.append('saved')
            except PermissionError: outcomes.append('held')
        with self.psycopg.connect(self.runtime_dsn) as con:
            con.execute('SELECT pg_advisory_xact_lock(%s::bigint)',(key,))
            thread=threading.Thread(target=worker); thread.start()
            self.assertTrue(initial.wait(timeout=3)); revoked.set()
        thread.join(timeout=10); self.assertFalse(thread.is_alive())
        self.assertEqual(outcomes,['held']); self.assertIsNone(self.get())

    def test_cross_scope_and_tenant_cannot_read_saved_proposal(self):
        self.save()
        foreign=TenantContext(self.ctx.organization_id,'other-tenant')
        scope=replace(self.scope,tenant_id=foreign.tenant_id)
        self.assertIsNone(self.repo.get(foreign,scope,self.environment_id,'app-1',authorize=lambda *_:None))
        self.assertIsNone(self.repo.get(self.ctx,replace(self.scope,endpoint_id='foreign'),
                                       self.environment_id,'app-1',authorize=lambda *_:None))
        with self.assertRaises(ValueError):
            self.repo.get(foreign,self.scope,self.environment_id,'app-1',authorize=lambda *_:None)

    def test_update_delete_and_forged_status_are_not_available_to_runtime(self):
        self.save()
        for sql in ("UPDATE hosting_controlplane.application_draft_revisions SET status='APPROVED'",
                    'DELETE FROM hosting_controlplane.application_draft_revisions'):
            with self.assertRaises(self.psycopg.errors.InsufficientPrivilege):
                with self.repo._session(self.ctx,self.scope,self.environment_id,self.authorize) as con: con.execute(sql)
        self.assertEqual(self.get()['revision'],1)

    def test_site_worker_is_rejected_before_access(self):
        if not self.site_dsn: self.skipTest('Requires disposable site role')
        repo=ApplicationDraftRepository(lambda:self.psycopg.connect(self.site_dsn))
        with self.assertRaises(PermissionError):
            repo.get(self.ctx,self.scope,self.environment_id,'app-1',authorize=lambda *_:None)


if __name__=='__main__': unittest.main()
