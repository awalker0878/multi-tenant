"""Staged owner enrollment boundaries and actual opt-in SQL immutability.

Local cases exercise the sealed projection; they do not assert native occupancy.
"""
from dataclasses import replace
import os
from types import MappingProxyType,SimpleNamespace
import unittest

from provisioner.controlplane.reconciliation.staged_resources import (
    StagedApplicationResourceAuthority,StagedPlannedLeaseAuthority)
from provisioner.controlplane.workflow.resource_recovery_activity import ResourceRecoveryActivityRouter
from tests.provisioning.reconciliation import test_planned_creation as pg


class StagedEnrollmentTests(unittest.TestCase):
    def lease_owner(self):
        # Narrow enrollment fixture; constructor-native proof ports have their
        # separate tests. No resource/native action is invoked here.
        from threading import RLock
        owner=object.__new__(StagedPlannedLeaseAuthority)
        owner._connect=lambda:None;owner.resources=object();owner.selections=object()
        owner._enrollment_lock=RLock();owner._worker_sealed=False;owner._staged_enrolled=False
        owner.staged_resources=MappingProxyType({})
        staged=object.__new__(StagedApplicationResourceAuthority)
        staged.connect=owner._connect;staged.resources=owner.resources;staged.selections=owner.selections
        staged.admitted=SimpleNamespace(job_id='cutover-original-approved')
        return owner,staged

    def test_one_time_staged_enrollment_preserves_original_owner_and_immutable_map(self):
        owner,staged=self.lease_owner();mapping={staged.admitted.job_id:staged}
        owner.enroll_staged_resources(mapping);mapping.clear()
        self.assertIs(owner.staged_resources['cutover-original-approved'],staged)
        with self.assertRaises(TypeError):owner.staged_resources['another']=staged
        with self.assertRaises(ValueError):owner.enroll_staged_resources({'cutover-original-approved':staged})

    def test_registered_worker_and_changed_resource_database_cannot_add_handover(self):
        owner,staged=self.lease_owner();owner.seal_for_worker()
        with self.assertRaises(ValueError):owner.enroll_staged_resources({'cutover-original-approved':staged})
        owner,staged=self.lease_owner();staged.resources=object()
        with self.assertRaises(ValueError):owner.enroll_staged_resources({'cutover-original-approved':staged})
        self.assertEqual(dict(owner.staged_resources),{})

    def test_unknown_job_has_no_recovery_effect_owner(self):
        router=object.__new__(ResourceRecoveryActivityRouter);router.owners=MappingProxyType({})
        from tests.provisioning.workflow.test_resource_recovery_job import INPUT
        from provisioner.controlplane.workflow.resource_recovery_job import ResourceRecoveryStageRequest
        result=router.cleanup_native(ResourceRecoveryStageRequest(INPUT,'cleanup-0-native'))
        self.assertEqual(result.status,'HELD')


@unittest.skipUnless(os.environ.get('HOSTING_TEST_POSTGRES_MIGRATION_DSN') and
    os.environ.get('HOSTING_TEST_POSTGRES_RUNTIME_DSN') and
    os.environ.get('HOSTING_TEST_POSTGRES_ENROLLMENT_DSN') and
    os.environ.get('HOSTING_TEST_POSTGRES_ISOLATED')=='1','Requires isolated real PostgreSQL scoped roles')
class StagedAccountingSqlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pg.PlannedCreationPostgresTests.setUpClass()
        cls.psycopg=pg.PlannedCreationPostgresTests.psycopg

    def setUp(self):
        self.original=pg.PlannedCreationPostgresTests();self.original.setUp()
        self.addCleanup(self.original.doCleanups)

    def test_foreign_job_binding_and_original_intent_unknown_do_not_become_handover(self):
        old=self.original;context=old.context
        with old.runtime() as connection:
            old.fixture._tenant(connection)
            with self.assertRaises(self.psycopg.Error):
                connection.execute('INSERT INTO hosting_controlplane.staged_resource_accounting_bindings '
                    '(organization_id,tenant_id,job_id,original_job_id,current_selection_digest,original_selection_digest,'
                    'original_plan_digest,resource_bundle_digest,reservation_digest,handover_digest,binding_digest) '
                    'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                    (context.organization_id,context.tenant_id,'unadmitted-cutover',old.fixture.job_id,*(['a'*64]*7)))
        old.prepare();old.registry.claim_once(context,old.lease,old.operation_id,old.identity)
        old.registry.mark_uncertain(context,old.operation_id,old.identity.subject)
        with self.assertRaises(pg.RecoveryHeld):
            old.registry.acknowledge_created(context,old.lease,old.operation_id,old.identity,old.observation())
        self.assertEqual(old.registry.get(context,old.operation_id).state,'UNCERTAIN')
