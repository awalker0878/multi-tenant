"""Actual mTLS and signed operating gates, explicit synthetic control ledger.

No test here opens a database or produces native qualification. PostgreSQL17
engine and credential custody campaigns remain the separate hosted owners.
"""
from dataclasses import replace
from pathlib import Path
import unittest
from unittest.mock import patch

from provisioner.controlplane.authority.service import AuthorityDenied
from provisioner.controlplane.persistence import canonical_record_digest
from provisioner.controlplane.reconciliation.registry import NativeOperation
from provisioner.controlplane.worker.grants import GrantDenied
from provisioner.execution.run_files import digest,encoded
from provisioner.migration.postgresql_authority import DatabaseCommandAuthority,DatabaseOperationContext
from tests.provisioning.operations import test_database_continuation as continuation_fixture
from tests.provisioning.operations.campaign_fixtures import AS_OF


class DatabaseAuthorityTests(unittest.TestCase):
    def setUp(self):
        fixture=continuation_fixture.DatabaseContinuationTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        self.fixture=fixture
        authority=fixture.workers['source'].command.authority
        authority.require_database_current=self.current
        def authorized(context,identity,grant_id,*,use,**arguments):
            grant=fixture.grants.verify_intent(fixture.cursor,context,grant_id=grant_id,worker_identity=identity,**arguments)
            return use('vault:unused-no-native-credentials',grant,grant.expires_at)
        fixture.grants.with_authorized_reference=authorized
        for target,value in (
            ('provisioner.migration.postgresql_authority.utcnow',lambda:AS_OF),
            ('provisioner.migration.postgresql_authority.verify',lambda root:{'status':'HASHES_MATCH','commit':fixture.selection['sourceCommit']}),
            ('provisioner.migration.postgresql_authority.verify_runtime',lambda root:{'status':'RUNTIME_SOURCES_MATCH'})):
            selected=patch(target,value);selected.start();self.addCleanup(selected.stop)
        registry=fixture.workers['source'].registry
        registry.prepare=self.prepare;registry.claim_once=self.claim_once

    def current(self,admitted,sha,kind,*,coordination):
        fixture=self.fixture
        self.assertEqual(sha,canonical_record_digest(fixture.selection))
        fixture.gate.require_database_continuation(fixture.cursor,admitted,fixture.selection,coordination=coordination)
        return {'spec':{'source':fixture.selection['source'],'destination':fixture.selection['destination']}},fixture.selection

    def prepare(self,context,lease,scope,**arguments):
        fixture=self.fixture;side=next(side for side,row in fixture.descriptor.to_dict()['operations'].items()
            if row['operationId']==arguments['operation_id'])
        fixture.cursor.intents[arguments['operation_id']]=fixture.intent(side,'PREPARED')
        return NativeOperation(arguments['operation_id'],arguments['job_id'],arguments['grant_id'],arguments['step_id'],
            arguments['lease_key'],lease.binding,lease.workload_id,lease.security_domain_id,lease.worker_id,lease.epoch,
            arguments['operation_kind'],arguments['request_digest'],'PREPARED',None,None)

    def claim_once(self,context,lease,scope,operation,identity):
        row=self.fixture.cursor.intents[operation]
        if row[0]!='PREPARED':return False
        self.fixture.cursor.intents[operation]=('IN_FLIGHT',)+row[1:];return True

    def guard(self,side='source'):
        fixture=self.fixture
        return DatabaseCommandAuthority(fixture.workers[side],fixture.admitted,fixture.selection,
            fixture.descriptor,side,Path('/fixture/explicit-unqualified-source'),coordination=fixture.coordination)

    def test_approved_compact_artifact_digest_never_uses_pretty_native_request_digest(self):
        guard=self.guard()
        self.assertEqual(guard.artifact_digest,canonical_record_digest(self.fixture.selection))
        self.assertEqual(self.fixture.coordination.artifact_digest,guard.artifact_digest)
        self.assertNotEqual(guard.artifact_digest,digest(encoded(self.fixture.selection)))

    def test_one_original_claim_and_current_sibling_revocation_prevent_another_command(self):
        source=self.guard();source.claim();target=self.guard('target');target.claim()
        source.require_current();target.require_current()
        with self.assertRaisesRegex(ValueError,'already claimed'):source.claim()
        self.fixture.grants.revoked.add('grant-target')
        with self.assertRaises((AuthorityDenied,GrantDenied)):source.require_current()
        self.assertEqual(self.fixture.cursor.intents['op-source'][0],'IN_FLIGHT')

    def test_original_fence_uses_its_separate_source_grant_and_native_dataset(self):
        fence=self.guard('fence');operation=fence.claim();original=fence.original_intent()
        self.assertEqual(operation.operation_kind,'SOURCE_FENCE')
        self.assertEqual(original['worker_id'],self.fixture.workers['source'].command.identity.subject)
        self.assertEqual(original['binding'],vars(self.fixture.workers['source'].lease.binding))
        self.assertEqual(fence.endpoint['ownerRole'],self.fixture.descriptor.to_dict()['source']['fenceOwnerRole'])
        self.assertNotEqual(original['grant_id'],self.fixture.workers['source'].command.grant.grant_id)

    def test_actual_trust_rotation_and_sealed_writer_stop_before_any_credential_issuance(self):
        guard=self.guard();guard.claim();guard.sealed=True
        with self.assertRaisesRegex(ValueError,'sealed'):guard.require_current()
        guard.sealed=False;self.fixture.verifier.reload_trust()
        with self.assertRaises((ValueError,GrantDenied,AuthorityDenied)):guard.require_current()

    def test_forged_group_or_foreign_original_dataset_is_not_a_native_exemption(self):
        fixture=self.fixture
        with self.assertRaises(ValueError):DatabaseCommandAuthority(fixture.workers['source'],fixture.admitted,
            fixture.selection,fixture.descriptor,'source',Path('/fixture'),coordination={'allow':True})
        changed=dict(fixture.workers)
        changed['target']=replace(changed['target'],lease=replace(changed['target'].lease,workload_id='foreign'))
        with self.assertRaises(ValueError):DatabaseOperationContext(fixture.admitted,encoded(fixture.selection),fixture.descriptor,changed)


if __name__=='__main__':unittest.main()
