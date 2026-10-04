"""Real canonical/legacy parsers, crypto and immutable custody; no native claim."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest

from provisioner.controlplane.authority.service import AuthorityDenied
from provisioner.controlplane.conversion.importer import manifest, native_statement, prepare_source
from provisioner.controlplane.conversion.originals import RetainedOriginalStore
from provisioner.controlplane.conversion.proofs import ConversionProofs, proof_header, require_independent
from provisioner.controlplane.evidence.gate import EvidenceMutationGate, EvidenceHold
from provisioner.controlplane.evidence.repository import _canonical
from provisioner.controlplane.evidence.vault import VaultTransitVerifier
from provisioner.controlplane.persistence import TenantContext
from provisioner.controlplane.worker.grants import GrantDenied, PostgresWorkerGrants
from provisioner.execution.run_files import digest, encoded
from tests.provisioning.conversion.fixtures import authenticated_source, envelope, initial_statements, CryptoTransit
from tests.provisioning.evidence.test_retained_adapters import FakeObjectLock


class AuthenticatedSourceTests(unittest.TestCase):
    def prepare(self, **kwargs):
        self.f,self.path,self.value=authenticated_source(self,**kwargs)
        return prepare_source(self.path,self.f.source_root,as_of=self.f.as_of)

    def test_real_old_writer_and_contiguous_canonical_history_propose_exact_originals(self):
        source=self.prepare()
        self.assertEqual([r['metadata']['revision'] for r in source.history],[1,2])
        self.assertEqual(source.report['observedCounts'],source.report['sourceCounts'])
        self.assertEqual(source.batch_digest,digest(self.path.read_bytes()))
        self.assertEqual(len(source.epochs),3)
        self.assertEqual(source.recoveries[0]['outcome'],'LEGACY_APPLIED_REQUIRES_NATIVE_ACCEPTANCE')
        self.assertFalse(source.proposal()['writesAuthorized'])
        self.assertFalse(source.proposal()['retryAuthorized'])
        self.assertEqual(prepare_source(self.path,self.f.source_root,as_of=self.f.as_of).proposal(),source.proposal())

    def test_authentic_unknown_start_is_importable_only_as_held_no_replay_fact(self):
        source=self.prepare(unknown=True)
        self.assertEqual(source.recoveries[0]['outcome'],'UNKNOWN')
        self.assertEqual(source.report['uncertainAttemptCount'],1)
        statement=initial_statements(source)['NATIVE']
        with self.assertRaisesRegex(ValueError,'Unknown/active'):
            native_statement(statement,[r['binding'] for r in source.epochs],source.recoveries,
                native_digest=statement['retainedNativeDigest'],handover=True)

    def test_gap_or_head_reset_does_not_silently_rebase_canonical_revisions(self):
        self.prepare()
        current=deepcopy(self.f.workload);current['metadata']['revision']=3
        (self.f.source_root/'workload.json').write_bytes(encoded(current))
        self.f.seal();self.value['inventory']=self.f.manifest
        self.path.write_bytes(encoded(self.value))
        with self.assertRaisesRegex(ValueError,'contiguous'):
            prepare_source(self.path,self.f.source_root,as_of=self.f.as_of)

    def test_missing_native_or_unknown_retained_record_remains_held(self):
        self.prepare()
        self.value['inventory']['evidence']['nativeInventory']=None
        self.path.write_bytes(encoded(self.value))
        with self.assertRaisesRegex(ValueError,'Unrecognized, mismatched'):
            prepare_source(self.path,self.f.source_root,as_of=self.f.as_of)

    def test_retained_workflow_inventory_cannot_be_defaulted_or_relabelled(self):
        self.prepare()
        value=deepcopy(self.value);del value['sourceWorkflowBoundary']
        with self.assertRaises(ValueError):manifest(value,as_of=self.f.as_of)
        value=deepcopy(self.value)
        value['sourceWorkflowBoundary'].update(mode='CANONICAL_FILES',recordCount=1,snapshotDigest='a'*64)
        with self.assertRaisesRegex(ValueError,'original workflow export'):
            manifest(value,as_of=self.f.as_of)

    def test_exact_native_task_and_binding_identity_required_even_with_signed_counts(self):
        source=self.prepare(unknown=True)
        original=initial_statements(source)['NATIVE']
        def check(statement):
            native_statement(statement,[r['binding'] for r in source.epochs],source.recoveries,
                             native_digest=original['retainedNativeDigest'])
        check(original)
        for changed in (dict(original,tasks=[]),dict(original,bindings=original['bindings'][:-1]),
                        dict(original,tasks=original['tasks']*2)):
            with self.subTest(changed=changed),self.assertRaises(ValueError):check(changed)
        changed=deepcopy(original);changed['tasks'][0]['generation']+=1
        with self.assertRaisesRegex(ValueError,'count/identity'):check(changed)


class OriginalCustodyTests(unittest.TestCase):
    def setUp(self):
        self.service=FakeObjectLock()
        self.store=RetainedOriginalStore(self.service,'restricted-originals',retention_days=365,
                                        prefix='conversion',kms_key_id='fixture-restricted-kms')

    def test_exact_private_and_empty_originals_are_retained_without_sanitizing_bytes(self):
        for raw in (b'',b'private credential\nSYNTHETIC-DO-NOT-LOG\x00original bytes'):
            expected=digest(raw)
            self.store.retain(expected,raw);self.store.retain(expected,raw)
            self.assertEqual(self.store.read(expected),raw)
            self.assertEqual(len(self.service.objects[self.store._key(expected)]),1)

    def test_missing_retention_or_changed_version_or_container_is_held(self):
        raw=b'original';expected=digest(raw);self.store.retain(expected,raw)
        key=self.store._key(expected);first=self.service.objects[key][0]
        for changed in (('fork',b'changed','COMPLIANCE',first[3]),
                        ('fork',first[1],'GOVERNANCE',first[3]),
                        ('fork',b'hosting-retained-original/1\n99\noriginal','COMPLIANCE',first[3])):
            self.service.objects[key].append(changed)
            with self.assertRaises(ValueError):self.store.read(expected)
            self.service.objects[key].pop()
        self.service.markers.append({'Key':key})
        with self.assertRaises(ValueError):self.store.read(expected)


class ProofCursor:
    """Bounded external SQL facts for crypto/enrollment failure cases only."""
    def __init__(self, now, retained):
        self.now,self.retained=now,retained
        self.enrolled=True;self.received=True;self.row=None
    def execute(self, sql, args=None):
        if sql=='SELECT clock_timestamp()':self.row=(self.now,)
        elif 'retained_conversion_keys k' in sql:
            self.row=(self.retained[1]['payload']['subjectId'],self.now-timedelta(minutes=1),
                      self.now+timedelta(hours=1)) if self.enrolled else None
        elif 'retained_conversion_proofs' in sql:
            self.row=(self.retained[0].blob_digest,self.retained[1]) if self.received else None
        else:raise AssertionError(sql)
    def fetchone(self):return self.row


class ProofAuthenticationTests(unittest.TestCase):
    def setUp(self):
        f,path,value=authenticated_source(self)
        self.source=prepare_source(path,f.source_root,as_of=f.as_of)
        self.transit=CryptoTransit();self.now=datetime.now(timezone.utc)
        signed=envelope(self.transit,'CUSTODY',self.source,initial_statements(self.source)['CUSTODY'],now=self.now)
        self.retained=(SimpleNamespace(evidence_kind='RECOVERY_DECISION',subject_id=value['inventory']['batchId'],
            blob_digest=digest(_canonical(signed))),signed)
        verification=SimpleNamespace(unanchored_count=0)
        self.audit=SimpleNamespace(verify=lambda context:verification)
        self.evidence=SimpleNamespace(verify=lambda context:verification,get=lambda context,event:self.retained)
        gate=EvidenceMutationGate(self.audit,self.evidence,max_unanchored_count=0)
        self.proofs=ConversionProofs(lambda:None,evidence_gate=gate,
            verifier=VaultTransitVerifier(self.transit,self.transit.trust()))
        self.cursor=ProofCursor(self.now,self.retained)
        self.scope=value['inventory']['scope']
        self.context=TenantContext(self.scope['organizationId'],self.scope['tenantId'])
    def verify(self):
        return self.proofs.verify(self.cursor,self.context,self.scope,event_key='proof-custody',
            batch_id=self.source.value['inventory']['batchId'],manifest_digest=self.source.batch_digest,purpose='CUSTODY')

    def test_real_separate_transit_key_verifies_original_retained_statement(self):
        verified=self.verify()
        self.assertEqual(verified.key_id,'custody')
        self.assertIn(('verify','custody'),self.transit.calls)

    def test_statement_or_signature_or_current_enrollment_or_receipt_cannot_be_faked(self):
        self.cursor.enrolled=False
        with self.assertRaisesRegex(ValueError,'unenrolled'):self.verify()
        self.cursor.enrolled=True;self.cursor.received=False
        with self.assertRaisesRegex(ValueError,'receipt'):self.verify()
        self.cursor.received=True
        self.retained[1]['statement']['archiveInventoryDigest']='f'*64
        with self.assertRaisesRegex(ValueError,'statement bytes'):self.verify()
        self.retained[1]['payload']['statementDigest']=digest(encoded(self.retained[1]['statement']))
        with self.assertRaisesRegex(ValueError,'signature was rejected'):self.verify()

    def test_expiry_future_batch_scope_and_independence_have_no_missing_default(self):
        original=deepcopy(self.retained[1])
        for field,new in (('freshUntil',(self.now-timedelta(seconds=1)).isoformat()),
                          ('observedAt',(self.now+timedelta(seconds=1)).isoformat()),
                          ('batchId','foreign-batch'),('scopeDigest','a'*64)):
            self.retained[1].clear();self.retained[1].update(deepcopy(original))
            self.retained[1]['payload'][field]=new
            with self.subTest(field=field),self.assertRaises(ValueError):self.verify()
        self.retained[1].clear();self.retained[1].update(original)
        verified=self.verify()
        with self.assertRaisesRegex(ValueError,'independent'):require_independent([verified,verified])

    def test_same_physical_transit_key_alias_and_custody_outage_are_held(self):
        with self.assertRaisesRegex(ValueError,'alias'):
            ConversionProofs(lambda:None,evidence_gate=self.proofs.evidence,
                verifier=VaultTransitVerifier(self.transit,{'one':('transit','custody'),'two':('transit','custody')}))
        def outage(context):raise OSError('synthetic external service outage')
        self.audit.verify=outage
        with self.assertRaises(EvidenceHold):self.verify()


class CurrentCommandAdmissionTests(unittest.TestCase):
    def setUp(self):
        from tests.provisioning.reconciliation import test_job_scope_storage as storage
        self.facts=storage._StoredJob()
        self.admitted=True;self.current_plan=True;self.calls=[];self.row=None
        self.connection=SimpleNamespace(autocommit=False)

    def execute(self,sql,args=None):
        self.calls.append(sql)
        if sql.startswith('SELECT w.record_id'):
            self.assertEqual(args,(self.facts.context.organization_id,self.facts.context.tenant_id,
                self.facts.job.plan_id,self.facts.job.plan_revision,self.facts.job.plan_digest))
            self.row=(self.facts.record['spec']['workloadId'],) if self.current_plan else None
        elif 'FROM pg_catalog.pg_roles' in sql:self.row=(False,False)
        elif 'set_config(' in sql:self.row=None
        elif 'retained_conversion_write_is_admitted' in sql:
            self.assertEqual(args,(self.facts.context.organization_id,self.facts.context.tenant_id,
                self.facts.scope.security_domain_id,self.facts.record['spec']['workloadId']))
            self.row=(self.admitted,)
        else:raise AssertionError(sql)

    def fetchone(self):return self.row

    def check(self,operation='VM_POWER'):
        PostgresWorkerGrants._conversion(self,self.facts.context,self.facts.job,self.facts.scope,operation)

    def test_current_mutating_use_rechecks_exact_workload_and_revocation_after_initial_permission(self):
        self.check();self.admitted=False
        with self.assertRaises(AuthorityDenied):self.check()
        self.admitted=True;self.current_plan=False
        with self.assertRaises(GrantDenied):self.check()

    def test_observation_discovery_does_not_require_conversion_write_acceptance(self):
        self.admitted=False;self.check('DISCOVER_READ')
        self.assertEqual(self.calls,[])


if __name__=='__main__':unittest.main()
