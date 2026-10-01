"""Freshness history contract and transaction-protocol fixtures, not SQL qualification."""
from contextlib import AbstractContextManager
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
import unittest

from provisioner.controlplane.discovery import freshness_history as module
from provisioner.controlplane.discovery.freshness import FreshnessChanged, FreshnessPolicy, FreshnessUnavailable
from provisioner.controlplane.discovery.model import _json
from provisioner.controlplane.discovery.persistence import DiscoveryRepository, StoredGeneration
from provisioner.controlplane.persistence.store import AuditContext, TenantContext
from tests.provisioning.api.test_http import NOW, SOURCE_SCOPE


class Rows:
    def __init__(self, rows=()): self.rows = list(rows)
    def fetchone(self): return self.rows[0] if self.rows else None
    def fetchall(self): return self.rows


class Database:
    def __init__(self):
        self.rows, self.events = [], []
        self.now, self.queries, self.reads = NOW, [], 0
        self.autocommit = self.superuser = self.worker = self.audit_failure = False
        self.after_insert = lambda: None
        self.clock = lambda: self.now


class Connection(AbstractContextManager):
    def __init__(self, db): self.db, self.autocommit = db, db.autocommit
    def __enter__(self):
        self.rows, self.events = deepcopy(self.db.rows), deepcopy(self.db.events)
        return self
    def __exit__(self, kind, value, tb):
        if kind is None: self.db.rows, self.db.events = self.rows, self.events
    def execute(self, sql, parameters=()):
        self.db.queries.append((sql, parameters))
        if 'pg_catalog.pg_roles' in sql: return Rows([('runtime', self.db.superuser, False)])
        if 'is_site_worker_role' in sql: return Rows([(self.db.worker,)])
        if sql == 'SELECT clock_timestamp()': return Rows([(self.db.clock(),)])
        if 'set_config' in sql or sql == module._LOCK_SQL: return Rows()
        if sql.startswith('SELECT ') and module._TABLE in sql:
            rows = [r[8:] for r in self.rows if r[:8] == parameters[:8]]
            if 'AND check_id=%s' in sql: rows = [r for r in rows if r[0] == parameters[8]]
            elif 'sequence>%s' in sql: rows = sorted([r for r in rows if r[1] > parameters[8]], key=lambda r: r[1])[:parameters[9]]
            else: rows = sorted(rows, key=lambda r: r[1], reverse=True)[:1]
            return Rows(rows)
        if sql.startswith('INSERT INTO '+module._TABLE):
            self.rows.append(parameters); self.db.after_insert(); return Rows()
        if sql.startswith('INSERT INTO hosting_controlplane.audit_events'):
            if self.db.audit_failure: raise RuntimeError('synthetic audit storage failure')
            self.events.append(parameters); return Rows()
        raise AssertionError('Unexpected SQL in protocol fixture: '+sql)


class Discovery(DiscoveryRepository):
    def __init__(self, db):
        super().__init__(lambda: Connection(db))
        self.db = db
        self.metadata = StoredGeneration('env-01',1,'campaign-1',SOURCE_SCOPE,'a'*64,'b'*64,
            NOW-timedelta(minutes=10),'PARTIAL',('VISIBLE_INVENTORY_ONLY',),(),2)
        self.after_read = lambda: None
    def latest_generation(self, ctx, scope, environment_id):
        self.db.reads += 1
        value = deepcopy(self.metadata)
        self.after_read()
        return value


class FreshnessHistoryTests(unittest.TestCase):
    def setUp(self):
        self.db = Database(); self.discovery = Discovery(self.db)
        self.history = module.FreshnessHistoryRepository(self.discovery)
        self.ctx = TenantContext(SOURCE_SCOPE.organization_id, SOURCE_SCOPE.tenant_id)
        self.authorizations = []
        self.audit = AuditContext('verified-operator', 'request-1')
        self.denied = False
    def authorize(self, scope, at):
        self.assertEqual(scope, SOURCE_SCOPE)
        self.authorizations.append(at)
        if self.denied: raise PermissionError('synthetic revocation')
    def capture(self, check='check-1', **kwargs):
        return self.history.capture(self.ctx,SOURCE_SCOPE,'env-01',check,
            audit=kwargs.pop('audit',self.audit),authorize=kwargs.pop('authorize',self.authorize),**kwargs)
    def get(self, check='check-1'):
        return self.history.get(self.ctx,SOURCE_SCOPE,'env-01',check,authorize=self.authorize)
    def listing(self, **kwargs):
        return self.history.list_checks(self.ctx,SOURCE_SCOPE,'env-01',authorize=self.authorize,**kwargs)

    def test_capture_uses_real_freshness_projection_and_never_native_facts(self):
        value = self.capture()
        self.assertEqual(value['report']['freshness'],'FRESH')
        self.assertEqual(value['report']['issues'],['COLLECTION_PARTIAL','COLLECTION_ERRORS_PRESENT','NATIVE_VISIBILITY_UNVERIFIED'])
        self.assertEqual(value['changeKinds'],['INITIAL_CHECK']); self.assertEqual(value['sequence'],1)
        self.assertEqual(value['recordedBy'],self.audit.actor_id); self.assertEqual(self.db.reads,2)
        self.assertTrue(value['historicalOnly']); self.assertFalse(value['executionAuthorized'])
        self.assertFalse(value['collectionRequested']); self.assertFalse(value['notificationAttempted'])
        self.assertEqual(len(self.db.events),1); self.assertGreaterEqual(len(self.authorizations),6)

    def test_retry_returns_original_without_resampling_or_duplicate_audit(self):
        original = self.capture(); reads = self.db.reads
        self.discovery.metadata = None; self.db.now += timedelta(days=2)
        retry = self.capture(audit=AuditContext(self.audit.actor_id,'different-request'))
        self.assertEqual(retry,original); self.assertEqual(self.db.reads,reads)
        self.assertEqual(len(self.db.rows),1); self.assertEqual(len(self.db.events),1)

    def test_different_actor_cannot_reuse_a_check_id(self):
        self.capture()
        with self.assertRaises(module.FreshnessCheckConflict): self.capture(audit=AuditContext('other','other'))
        self.assertEqual(len(self.db.rows),1)

    def test_elapsed_age_changes_are_recorded_without_rewriting_history(self):
        old = self.capture(); self.db.now += timedelta(days=2); new = self.capture('check-2')
        self.assertEqual(new['changeKinds'],['FRESHNESS_CHANGED'])
        self.assertEqual(new['report']['freshness'],'STALE'); self.assertEqual(new['previousRecordDigest'],old['recordDigest'])
        self.assertEqual(self.get(),old)

    def test_new_inventory_and_health_are_distinct_change_kinds(self):
        self.capture()
        self.discovery.metadata = replace(self.discovery.metadata,generation=2,result_digest='c'*64,
            completeness='COMPLETE',collection_errors=(),captured_at=NOW)
        value = self.capture('check-2')
        self.assertEqual(value['changeKinds'],['OBSERVATION_CHANGED','COLLECTION_HEALTH_CHANGED'])
        self.assertFalse(value['report']['nativeVisibilityVerified'])

    def test_missing_future_and_reappearing_inventory_keep_explicit_states(self):
        metadata = self.discovery.metadata; self.discovery.metadata = None
        first = self.capture(); self.assertEqual(first['report']['freshness'],'MISSING')
        self.discovery.metadata = replace(metadata,captured_at=NOW+timedelta(seconds=1))
        second = self.capture('check-2'); self.assertEqual(second['report']['freshness'],'FUTURE_CAPTURE')
        self.assertEqual(second['report']['ageMicroseconds'],None)

    def test_policy_change_affects_only_new_check_ids(self):
        old = self.capture()
        self.history = module.FreshnessHistoryRepository(self.discovery,policy=FreshnessPolicy(1,2))
        self.assertEqual(self.capture(),old)
        self.assertEqual(self.capture('check-2')['changeKinds'],['POLICY_CHANGED','FRESHNESS_CHANGED'])

    def test_identical_health_still_gets_a_new_audited_check_when_requested(self):
        self.capture(); second = self.capture('check-2')
        self.assertEqual(second['changeKinds'],[]); self.assertEqual(second['sequence'],2)
        self.assertEqual(len(self.db.events),2)

    def test_bounded_history_paginates_original_records(self):
        values = [self.capture('check-'+str(n)) for n in range(3)]
        first = self.listing(limit=2)
        self.assertEqual(first['items'],values[:2]); self.assertEqual(first['nextAfter'],2)
        self.assertEqual(self.listing(after=2,limit=2)['items'],values[2:])
        self.assertIsNone(self.listing(after=2)['nextAfter'])

    def test_empty_and_absent_history_recheck_authority(self):
        self.assertIsNone(self.get()); self.assertEqual(self.listing()['items'],[])
        self.assertGreaterEqual(len(self.authorizations),4)
        self.denied = True
        with self.assertRaises(PermissionError): self.listing()

    def test_invalid_limits_ids_and_scope_refuse_database_access(self):
        for check in ('','bad id','x'*129,True):
            with self.subTest(check=check), self.assertRaises(ValueError): self.capture(check)
        for values in ({'limit':True},{'limit':0},{'limit':51},{'after':-1},{'after':2**63}):
            with self.subTest(values=values), self.assertRaises(ValueError): self.listing(**values)
        with self.assertRaises(ValueError):
            self.history.capture(TenantContext('other','tenant'),SOURCE_SCOPE,'env-01','a',audit=self.audit,authorize=self.authorize)
        self.assertEqual(self.db.queries,[])

    def test_autocommit_privileged_and_site_worker_roles_are_refused(self):
        for field in ('autocommit','superuser','worker'):
            setattr(self.db,field,True)
            with self.subTest(field=field), self.assertRaises((PermissionError,RuntimeError)): self.capture()
            setattr(self.db,field,False)
        self.assertEqual(self.db.rows,[])

    def test_audit_failure_rolls_back_the_sample(self):
        self.db.audit_failure = True
        with self.assertRaises(RuntimeError): self.capture()
        self.assertEqual(self.db.rows,[]); self.assertEqual(self.db.events,[])

    def test_revocation_after_insert_rolls_back_sample_and_audit(self):
        self.db.after_insert = lambda: setattr(self,'denied',True)
        with self.assertRaises(PermissionError): self.capture()
        self.assertEqual(self.db.rows,[]); self.assertEqual(self.db.events,[])

    def test_revoked_retry_cannot_read_retained_result(self):
        self.capture(); self.denied=True
        with self.assertRaises(PermissionError): self.capture()
        self.assertEqual(len(self.db.rows),1)

    def test_changed_inventory_during_capture_is_not_a_missing_sample(self):
        self.discovery.after_read = lambda: setattr(self.discovery,'metadata',None)
        with self.assertRaises(FreshnessChanged): self.capture()
        self.assertEqual(self.db.rows,[])

    def test_regressed_clock_refuses_new_sample(self):
        self.capture(); self.db.now -= timedelta(seconds=1)
        with self.assertRaises(FreshnessUnavailable): self.capture('check-2')
        self.assertEqual(len(self.db.rows),1)

    def test_corrupt_report_digest_or_record_is_not_returned(self):
        self.capture(); original = deepcopy(self.db.rows)
        for index,value in ((10,'{}'),(11,'c'*64),(12,'other'),(16,'c'*64)):
            self.db.rows = deepcopy(original)
            row = list(self.db.rows[0]); row[index]=value; self.db.rows[0]=tuple(row)
            with self.subTest(index=index), self.assertRaises(ValueError): self.get()

    def test_gaps_and_predecessor_mismatches_hold_history_pages(self):
        self.capture(); self.capture('check-2'); self.db.rows.pop(0)
        with self.assertRaises(FreshnessUnavailable): self.listing()

    def test_wire_validator_rejects_false_freshness_or_authority_claims(self):
        report = self.capture()['report']
        for key,value in (('freshness','MISSING'),('ageMicroseconds',False),('refreshDue',1),
                          ('executionAuthorized',True),('nativeVisibilityVerified',True),('issues',[])):
            altered=deepcopy(report); altered[key]=value
            with self.subTest(key=key), self.assertRaises(ValueError): module.validate_report(altered,SOURCE_SCOPE,'env-01')
        altered=deepcopy(report); altered['policy']['maxAgeSeconds']=True
        with self.assertRaises(ValueError): module.validate_report(altered,SOURCE_SCOPE,'env-01')

    def test_returned_documents_do_not_mutate_retained_rows(self):
        first=self.capture(); first['report']['issues'].clear(); first['changeKinds'].clear()
        self.assertEqual(self.get()['changeKinds'],['INITIAL_CHECK'])
        self.assertIn('NATIVE_VISIBILITY_UNVERIFIED',self.get()['report']['issues'])

    def test_returned_record_scope_does_not_mutate_the_trusted_scope(self):
        scope=deepcopy(SOURCE_SCOPE)
        value=self.history.capture(self.ctx,scope,'env-01','record-scope',audit=self.audit,authorize=self.authorize)
        value['scope']['tenant_id']='mutated'
        self.assertEqual(scope.tenant_id,SOURCE_SCOPE.tenant_id)

    def test_returned_history_scope_does_not_mutate_the_trusted_scope(self):
        scope=deepcopy(SOURCE_SCOPE)
        value=self.history.list_checks(self.ctx,scope,'env-01',authorize=self.authorize)
        value['scope']['tenant_id']='mutated'
        self.assertEqual(scope.tenant_id,SOURCE_SCOPE.tenant_id)
