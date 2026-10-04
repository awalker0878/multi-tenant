"""Budget signature, retained originals and role failure boundaries.

Signature transport and DB roles are synthetic here; the database role/race
tests are separate. No local signature fixture commissions a native pool.
"""
import base64
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock

from provisioner.controlplane.evidence.gate import EvidenceMutationGate
from provisioner.controlplane.evidence.repository import EvidenceRepository
from provisioner.controlplane.evidence.vault import VaultTransitVerifier
from provisioner.controlplane.jobs.repository import _digest
from provisioner.migration.enterprise_wave import EnterpriseWavePool, PoolDomain
from provisioner.migration.enterprise_wave_commissioning import (
    EnterprisePoolCommissioner, approval_payload, native_budget_record)
from provisioner.migration.wave_schedule import WaveBudget, WaveHeld


class EnterprisePoolCommissioningTests(unittest.TestCase):
    def setUp(self):
        now = datetime.now(timezone.utc)
        prototype = EnterpriseWavePool('pool-01', tuple(PoolDomain('org-01', tenant,
            'domain-01', 'a'*64, (('native-risk','physical-risk'),)) for tenant in ('tenant-a','tenant-b')),
            WaveBudget(2,2,1200,2,256,32,1024**3), (('physical-risk',2),), 'b'*64,
            now-timedelta(minutes=1), now+timedelta(hours=1))
        self.pool = replace(prototype, native_budget_evidence_digest=_digest(native_budget_record(prototype)))
        self.evidence, self.custody, self.verifier = (Mock(spec=EvidenceRepository),
            Mock(spec=EvidenceMutationGate), Mock(spec=VaultTransitVerifier))
        self.keys = {('org-01', tenant): 'budget-'+tenant for tenant in ('tenant-a','tenant-b')}
        def get(context, event):
            if event.startswith('native-budget-'):
                return (SimpleNamespace(evidence_kind='OBSERVATION', subject_id=self.pool.pool_id,
                    blob_digest=self.pool.native_budget_evidence_digest), native_budget_record(self.pool))
            key = self.keys[(context.organization_id, context.tenant_id)]
            return (SimpleNamespace(evidence_kind='VERIFICATION_RESULT', subject_id=self.pool.pool_id),
                {'payload':approval_payload(self.pool,context,key),
                 'signature':base64.b64encode(b'vault:v1:c2ln').decode()})
        self.evidence.get.side_effect = get
        self.cursor = MagicMock()
        self.cursor.fetchone.side_effect = [(False,False,True), (now,), None]
        connection = MagicMock()
        connection.autocommit = False
        connection.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value = self.cursor
        self.connect = Mock(return_value=connection)
        self.owner = EnterprisePoolCommissioner(self.connect, evidence=self.evidence,
            custody=self.custody, verifier=self.verifier, budget_keys=self.keys)

    def test_both_scoped_original_observations_and_current_signatures_precede_enrollment(self):
        self.assertEqual(self.owner.enroll(self.pool, actor='commissioner-01'),self.pool.digest)
        self.assertEqual(self.verifier.verify.call_count,2)
        self.assertEqual(self.custody.require.call_count,2)
        self.assertIn('INSERT INTO',self.cursor.execute.call_args[0][0])

    def test_unavailable_original_native_budget_never_touches_database(self):
        self.evidence.get.side_effect = lambda context,event: None
        with self.assertRaises(WaveHeld):
            self.owner.enroll(self.pool,actor='commissioner-01')
        self.connect.assert_not_called()

    def test_one_tenant_cannot_reuse_foreign_budget_signature(self):
        original = self.evidence.get.side_effect
        def foreign(context,event):
            entry,body = original(context,event)
            if event.startswith('enterprise-pool-'):
                body['payload']['tenantId'] = 'tenant-foreign'
            return entry,body
        self.evidence.get.side_effect = foreign
        with self.assertRaises(WaveHeld):
            self.owner.enroll(self.pool,actor='commissioner-01')
        self.connect.assert_not_called()

    def test_revoked_verifier_and_lost_custody_never_enroll(self):
        for owner,method in ((self.verifier,'verify'),(self.custody,'require')):
            with self.subTest(method=method):
                getattr(owner,method).side_effect = OSError('synthetic owner unavailable')
                with self.assertRaises((WaveHeld,OSError)):
                    self.owner.enroll(self.pool,actor='commissioner-01')
                self.connect.assert_not_called()
                getattr(owner,method).side_effect = None

    def test_bypass_or_tenant_runtime_identity_cannot_enroll(self):
        for role in ((True,False,True),(False,True,True),(False,False,False)):
            with self.subTest(role=role):
                self.cursor.fetchone.side_effect = [role]
                with self.assertRaises(WaveHeld):
                    self.owner.enroll(self.pool,actor='commissioner-01')
                self.assertNotIn('INSERT INTO',self.cursor.execute.call_args[0][0])
