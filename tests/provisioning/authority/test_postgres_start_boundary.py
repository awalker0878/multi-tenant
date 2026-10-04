"""Typed authority boundaries using the real quorum and current window policy.

Database reads are explicit synthetic owner facts here. PostgreSQL integration
tests separately exercise the persisted original job and exact outbox binding.
"""
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from provisioner.controlplane.authority import postgres
from provisioner.controlplane.authority.model import (
    ApprovalSnapshot, AuthorizedPlan, PlanApproval)
from provisioner.controlplane.authority.service import AuthorityDenied, _requirements
from provisioner.controlplane.jobs import Job
from provisioner.migration.wave_schedule import WaveHeld
from tests.provisioning.authority.test_policy import NOW, PLAN


class Cursor:
    def __init__(self, window):
        self.window = window
        self.window_queries = []
        self.row = None

    def execute(self, query, params=None):
        if "current_setting('app.organization_id'" in query:
            self.row = (PLAN.organization_id, PLAN.tenant_id)
        elif 'migration_wave_job_window' in query:
            self.window_queries.append(params)
            self.row = self.window
        else:
            raise AssertionError('Unexpected synthetic database owner read: '+query)

    def fetchone(self):
        return self.row


class PostgresStartBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.plan, self.epoch = PLAN, 0
        approvals = tuple(PlanApproval('approval-'+str(index),PLAN.organization_id,
            PLAN.tenant_id,PLAN.plan_id,PLAN.revision,PLAN.digest,role,scope,
            'reviewer-'+str(index),NOW-timedelta(minutes=1),NOW+timedelta(hours=3),0)
            for index,(role,scope) in enumerate(_requirements(PLAN)))
        self.snapshot = ApprovalSnapshot(PLAN.organization_id,PLAN.tenant_id,
            PLAN.plan_id,PLAN.revision,PLAN.digest,0,approvals)
        self.decision = AuthorizedPlan(PLAN.organization_id,PLAN.tenant_id,PLAN.plan_id,
            PLAN.revision,PLAN.digest,PLAN.source,PLAN.destination,
            tuple(a.approval_id for a in approvals),0,NOW+timedelta(seconds=30),'operator')
        self.job = Job(PLAN.organization_id,PLAN.tenant_id,'original-job','original-submit',
            PLAN.plan_id,PLAN.revision,PLAN.digest,PLAN.source,PLAN.destination,'operator',
            self.decision.approval_ids,0,'QUEUED',1,NOW,NOW)
        self.window = ('ADMITTED','e'*64,'e'*64,NOW-timedelta(hours=1),NOW+timedelta(days=1),
            NOW-timedelta(minutes=1),NOW+timedelta(minutes=30),600,
            PLAN.plan_id,PLAN.revision,PLAN.digest)
        self.locked = patch.object(postgres,'_locked_plan',side_effect=lambda *_:(self.plan,self.epoch))
        self.quorum = patch.object(postgres,'_approval_snapshot',side_effect=lambda *_:self.snapshot)
        self.locked.start(); self.quorum.start()
        self.addCleanup(self.locked.stop); self.addCleanup(self.quorum.stop)

    def test_approved_plan_rechecks_quorum_without_claiming_job_or_start_permission(self):
        cursor = Cursor(self.window)
        postgres.revalidate_start(cursor,self.decision,NOW)
        self.assertEqual(cursor.window_queries,[])
        self.snapshot = replace(self.snapshot,approvals=self.snapshot.approvals[:-1])
        with self.assertRaises(AuthorityDenied):
            postgres.revalidate_start(cursor,self.decision,NOW)

    def test_actual_job_always_looks_up_exact_affiliation_even_when_no_wave_is_found(self):
        for window in (self.window,None):
            cursor = Cursor(window)
            postgres.revalidate_start(cursor,self.job,NOW)
            self.assertEqual(cursor.window_queries,[(PLAN.organization_id,PLAN.tenant_id,'original-job')])

    def test_missing_job_id_and_job_shaped_objects_never_skip_the_wave_boundary(self):
        for value in (object(),vars(self.job),SimpleNamespace(**vars(self.job)),
                      SimpleNamespace(**vars(self.decision))):
            cursor = Cursor(None)
            with self.subTest(value=type(value)), self.assertRaises(AuthorityDenied):
                postgres.revalidate_start(cursor,value,NOW)
            self.assertEqual(cursor.window_queries,[])

    def test_current_approvals_cannot_authorize_expired_held_or_rebound_wave_job(self):
        for window,at in ((self.window,self.window[6]),
                (('HELD',)+self.window[1:],NOW),
                (self.window[:2]+('f'*64,)+self.window[3:],NOW),
                (self.window[:-1]+('f'*64,),NOW)):
            cursor = Cursor(window)
            with self.subTest(window=window,at=at), self.assertRaises(WaveHeld):
                postgres.revalidate_start(cursor,self.job,at)
            self.assertEqual(len(cursor.window_queries),1)

    def test_revoked_or_superseded_authority_denies_both_typed_boundaries(self):
        for changed in ('revoked','superseded'):
            self.plan,self.epoch = PLAN,0
            if changed == 'revoked': self.epoch = 1
            else: self.plan = replace(PLAN,revision=2,digest='b'*64)
            for value in (self.decision,self.job):
                cursor = Cursor(self.window)
                with self.subTest(changed=changed,value=type(value)), self.assertRaises(AuthorityDenied):
                    postgres.revalidate_start(cursor,value,NOW)
                self.assertEqual(cursor.window_queries,[])


if __name__ == '__main__':
    unittest.main()
