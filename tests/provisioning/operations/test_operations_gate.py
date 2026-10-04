import base64
from copy import deepcopy
from datetime import timedelta
import hashlib
from types import SimpleNamespace
import unittest

from provisioner.controlplane.authority.service import AuthorityDenied
from provisioner.controlplane.authority.model import WorkerGrant, PlanScope
from provisioner.controlplane.worker.grants import VerifiedWorkerIdentity
from provisioner.controlplane.evidence.repository import _validated_artifact
from provisioner.controlplane.operations.action_gate import (
    OperationsActionGate, MINIMUM_PREREQUISITES, scope_digest, acceptance_digest,
    acceptance_event_key, _canonical,
)
from tests.provisioning.operations.campaign_fixtures import AS_OF, fixture
from tests.provisioning.operations.test_release import TestSigner
from tests.provisioning.operations.signed_intake_fixtures import minimum_prerequisite_artifacts


class Cursor:
    def __init__(self, *, epoch=0, unresolved=0, containment=0, tenant='tenant-fixture'):
        self.row = ('org-fixture', tenant, AS_OF, 'RUNNING', 1, 'c' * 64,
                    epoch, unresolved, containment)
    def execute(self, *args):
        pass
    def fetchone(self):
        return self.row


class Evidence:
    def __init__(self):
        self.retained = None
        self.checks = 0
        self.evidence = self
    def get(self, context, key):
        if key in getattr(self, 'artifacts', {}):
            return (SimpleNamespace(event_key=key, evidence_kind='VERIFICATION_RESULT',
                subject_id=self.retained[0].subject_id), self.artifacts[key])
        return self.retained if self.retained and self.retained[0].event_key == key else None
    def require(self, context):
        self.checks += 1


class OperatingGateTests(unittest.TestCase):
    def setUp(self):
        _, _, self.selection = fixture()
        self.admitted = SimpleNamespace(organization_id='org-fixture', tenant_id='tenant-fixture',
            job_id='job-fixture', plan_id='plan-fixture', plan_revision=1,
            plan_digest='c' * 64, revocation_epoch=0)
        self.signer = TestSigner()
        self.observer = TestSigner('synthetic-separate-prerequisite-observer')
        self.payload = {'format': 'hosting-selected-operating-acceptance/1',
            'scopeDigest': scope_digest(self.selection), 'sourceCommit': self.selection['sourceCommit'],
            'planId': self.admitted.plan_id, 'revocationEpoch': 0,
            'acceptedAt': (AS_OF - timedelta(hours=1)).isoformat(),
            'reviewBy': (AS_OF + timedelta(days=30)).isoformat(),
            'reviewerRef': 'controlled-operating-reviewer:synthetic',
            'prerequisites': [{'id': ident, 'result': 'ACCEPTED',
                'evidenceRef': 'controlled-operating-evidence:' + ident,
                'artifactSha256': hashlib.sha256(ident.encode()).hexdigest(),
                'observerRef': 'controlled-independent-observer:synthetic',
                'observedAt': (AS_OF - timedelta(hours=2)).isoformat(),
                'freshUntil': (AS_OF + timedelta(days=30)).isoformat()}
                for ident in sorted(MINIMUM_PREREQUISITES)]}
        self.evidence = Evidence()
        self.gate = OperationsActionGate(evidence_gate=self.evidence, operating_verifier=self.signer,
            operating_key_ids=frozenset({self.signer.key_id}), observer_verifier=self.observer,
            observer_key_ids=frozenset({self.observer.key_id}))
        self.retain()

    def retain(self):
        self.evidence.artifacts = minimum_prerequisite_artifacts(self.payload, self.observer)
        envelope = {'payload': self.payload, 'keyId': self.signer.key_id,
                    'signature': base64.b64encode(self.signer.sign(_canonical(self.payload))).decode()}
        digest = acceptance_digest(envelope)
        self.selection['operationsAcceptanceDigest'] = digest
        self.evidence.retained = (SimpleNamespace(evidence_kind='VERIFICATION_RESULT',
            subject_id=scope_digest(self.selection), event_key=acceptance_event_key(digest)), envelope)
        _validated_artifact(envelope)

    def test_current_actual_signed_retained_prerequisites_and_epoch_pass_synthetic_fixture(self):
        self.gate.require_action(Cursor(), self.admitted, self.selection, 'VM_CREATE')
        self.assertEqual(self.evidence.checks, 2)

    def test_signed_acceptance_with_missing_or_changed_original_prerequisite_is_held(self):
        fact = self.payload['prerequisites'][0]
        original = self.evidence.artifacts.pop(fact['evidenceRef'])
        with self.assertRaisesRegex(AuthorityDenied, 'prerequisite bytes'):
            self.gate.require_action(Cursor(), self.admitted, self.selection, 'VM_CREATE')
        self.evidence.artifacts[fact['evidenceRef']] = original
        original['payload']['observerRef'] = 'controlled-observer:forged'
        with self.assertRaises(AuthorityDenied):
            self.gate.require_action(Cursor(), self.admitted, self.selection, 'VM_CREATE')
        # Original held facts remain locally inspectable and confer no credential.
        self.gate.require_observation(Cursor(), self.admitted, self.selection)

    def test_raw_measurements_and_separate_current_observer_cannot_be_replaced_by_acceptance(self):
        fact = self.payload['prerequisites'][0]
        proof = self.evidence.artifacts[fact['evidenceRef']]
        del self.evidence.artifacts[proof['payload']['observationEventKey']]
        with self.assertRaisesRegex(AuthorityDenied, 'measurements'):
            self.gate.require_action(Cursor(), self.admitted, self.selection, 'VM_CREATE')
        self.retain()
        self.gate.observer_keys = frozenset({'withdrawn-observer'})
        with self.assertRaises(AuthorityDenied):
            self.gate.require_action(Cursor(), self.admitted, self.selection, 'VM_CREATE')

    def test_absent_record_bool_claim_or_modified_signature_never_allows_native_write(self):
        retained = self.evidence.retained
        self.evidence.retained = None
        with self.assertRaisesRegex(AuthorityDenied, 'missing'):
            self.gate.require_action(Cursor(), self.admitted, self.selection, 'VM_CREATE')
        self.evidence.retained = retained
        self.payload['prerequisites'][0]['result'] = True
        self.retain()
        with self.assertRaises(AuthorityDenied):
            self.gate.require_action(Cursor(), self.admitted, self.selection, 'VM_CREATE')
        self.payload['prerequisites'][0]['result'] = 'ACCEPTED'
        self.retain()
        self.evidence.retained[1]['payload']['reviewerRef'] = 'controlled-operating-reviewer:forged'
        with self.assertRaises(AuthorityDenied):
            self.gate.require_action(Cursor(), self.admitted, self.selection, 'VM_CREATE')

    def test_live_epoch_unresolved_operation_containment_and_wrong_scope_hold(self):
        for cursor in (Cursor(epoch=1), Cursor(unresolved=1), Cursor(containment=1),
                       Cursor(tenant='foreign-tenant')):
            with self.assertRaises(AuthorityDenied):
                self.gate.require_action(cursor, self.admitted, self.selection, 'VM_CREATE')
        changed = deepcopy(self.selection)
        changed['source']['endpointId'] = 'another-source'
        with self.assertRaises(AuthorityDenied):
            self.gate.require_action(Cursor(), self.admitted, changed, 'VM_CREATE')

    def test_stale_prerequisite_acceptance_or_withdrawn_operator_key_hold(self):
        self.payload['prerequisites'][0]['freshUntil'] = (AS_OF - timedelta(minutes=30)).isoformat()
        self.retain()
        with self.assertRaises(AuthorityDenied):
            self.gate.require_action(Cursor(), self.admitted, self.selection, 'VM_CREATE')
        self.payload['prerequisites'][0]['freshUntil'] = (AS_OF + timedelta(days=30)).isoformat()
        self.payload['reviewBy'] = AS_OF.isoformat()
        self.retain()
        with self.assertRaises(AuthorityDenied):
            self.gate.require_action(Cursor(), self.admitted, self.selection, 'VM_CREATE')
        self.gate.key_ids = frozenset({'current-different-key'})
        with self.assertRaises(AuthorityDenied):
            self.gate.require_action(Cursor(), self.admitted, self.selection, 'VM_CREATE')

    def continuation(self, *, state='IN_FLIGHT', other_unresolved=0, containment=0, wrong_grant=False):
        scope = PlanScope.from_record(self.selection['destination'])
        identity = VerifiedWorkerIdentity('org-fixture', 'tenant-fixture', 'worker-fixture',
            scope.site_id, 'a' * 64, AS_OF + timedelta(hours=1))
        grant = WorkerGrant('grant-fixture', 'org-fixture', 'tenant-fixture', 'plan-fixture',
            1, 'c' * 64, PlanScope.from_record(self.selection['source']), scope, identity.subject,
            'stage-fixture', 'operation-fixture', 'VM_CREATE', scope, 'lease-fixture', 1,
            ('approval-fixture',), 0, AS_OF - timedelta(minutes=1), AS_OF + timedelta(minutes=3))
        class Grants:
            def verify_intent(owner, cursor, context, **kwargs):
                self.assertEqual(kwargs['operation_id'], grant.operation_id)
                self.assertIs(kwargs['worker_identity'], identity)
                if wrong_grant:
                    return SimpleNamespace(grant_id=grant.grant_id)
                return grant
        class ContinuationCursor(Cursor):
            def execute(owner, query, *args):
                owner.intent_query = query.startswith('SELECT state,job_id,grant_id')
                if 'operation_id<>%s' in query:
                    self.assertEqual(args[0][:2], (grant.operation_id, grant.operation_id))
            def fetchone(owner):
                if owner.intent_query:
                    return (state, self.admitted.job_id, grant.grant_id, grant.step_id,
                        grant.lease_key, grant.lease_epoch, grant.worker_subject, grant.operation_kind,
                        scope.endpoint_id, scope.native_scope_id, scope.security_domain_id)
                return owner.row
        self.gate.worker_grants = Grants()
        return ContinuationCursor(unresolved=other_unresolved, containment=containment), grant, identity

    def test_only_exact_live_original_claim_continues_with_existing_b10_verification(self):
        cursor, grant, identity = self.continuation()
        self.gate.require_continuation(cursor, self.admitted, self.selection,
                                       grant=grant, worker_identity=identity)

    def test_uncertain_foreign_containment_and_nonledger_continuations_hold(self):
        for options in ({'state': 'UNCERTAIN'}, {'other_unresolved': 1},
                        {'containment': 1}, {'wrong_grant': True}):
            cursor, grant, identity = self.continuation(**options)
            with self.assertRaises(AuthorityDenied):
                self.gate.require_continuation(cursor, self.admitted, self.selection,
                                               grant=grant, worker_identity=identity)

    def test_named_local_observation_keeps_holds_visible_without_authorizing_effects(self):
        cursor = Cursor(epoch=1, unresolved=1, containment=1)
        cursor.row = (*cursor.row[:3], 'HELD', *cursor.row[4:])
        self.gate.require_observation(cursor, self.admitted, self.selection)
        with self.assertRaises(AuthorityDenied):
            self.gate.require_action(cursor, self.admitted, self.selection, 'VM_CREATE')
        changed = deepcopy(self.selection)
        changed['destination']['nativeScopeId'] = 'foreign-scope'
        with self.assertRaises(AuthorityDenied):
            self.gate.require_observation(cursor, self.admitted, changed)


if __name__ == '__main__':
    unittest.main()
