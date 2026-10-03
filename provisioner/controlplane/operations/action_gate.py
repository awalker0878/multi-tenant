"""Minimum B44–B46 operating acceptance immediately before native writes.

Reads the existing immutable evidence stream and live job/authority/native-intent
tables. A separately trusted receiving/operating signer attests actual prerequisite
campaign evidence. Missing/stale/withdrawn acceptance always holds. This never
clears a containment record, recovers an epoch, or converts an observation into
approval. Existing worker, qualification and ownership gates remain mandatory.
"""
from __future__ import annotations

import base64
from datetime import datetime
import hashlib
import json
import re

from provisioner.controlplane.authority.service import AuthorityDenied
from provisioner.controlplane.authority.model import WorkerGrant
from provisioner.controlplane.persistence import TenantContext
from provisioner.controlplane.worker.grants import VerifiedWorkerIdentity
from provisioner.qualification import target_selection

_SHA = re.compile(r'^[0-9a-f]{64}$')
MINIMUM_PREREQUISITES = frozenset({
    'CONTROL_DB_OBSERVATION_RESTORE', 'INDEPENDENT_EVIDENCE_HIGH_WATER',
    'TEMPORAL_ACCEPTED_JOB_RECOVERY', 'OLD_WRITER_EPOCH_FENCING',
    'HA_STOP_AND_UPGRADE_CONTAINMENT', 'ALERT_DISPATCH_AND_OPERATOR_ACK',
    'LEAST_PRIVILEGE_NEGATIVES', 'TRANSFER_WORKER_ISOLATION',
    'SIGNED_ARTIFACT_PROVENANCE',
})


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def scope_digest(selection: dict) -> str:
    return hashlib.sha256(_canonical({key: selection[key] for key in (
        'sourceCommit', 'driver', 'sourceTuple', 'destinationTuple',
        'guestProfile', 'source', 'destination')})).hexdigest()


def acceptance_digest(envelope: dict) -> str:
    return hashlib.sha256(_canonical(envelope)).hexdigest()


def acceptance_event_key(digest: str) -> str:
    if not isinstance(digest, str) or not _SHA.fullmatch(digest):
        raise ValueError('Exact independently retained operating acceptance digest required')
    return 'ops-acceptance-' + digest


class OperationsActionGate:
    def __init__(self, *, evidence_gate, operating_verifier,
                 operating_key_ids: frozenset[str], worker_grants=None):
        if (not callable(getattr(evidence_gate, 'require', None))
                or not callable(getattr(getattr(evidence_gate, 'evidence', None), 'get', None))
                or not callable(getattr(operating_verifier, 'verify', None))
                or not isinstance(operating_key_ids, frozenset) or not operating_key_ids
                or not all(isinstance(key, str) and key for key in operating_key_ids)):
            raise ValueError('Independent evidence and distinct current operating-signer trust required')
        self.evidence_gate = evidence_gate
        self.verifier = operating_verifier
        self.key_ids = operating_key_ids
        if worker_grants is not None and not callable(getattr(worker_grants, 'verify_intent', None)):
            raise ValueError('Concrete current B10 grant verification is required for continuation')
        self.worker_grants = worker_grants

    def require_action(self, cursor, admitted, selection: dict, operation_kind: str) -> None:
        try:
            self._require(cursor, admitted, selection, operation_kind)
        except AuthorityDenied:
            raise
        except Exception:
            raise AuthorityDenied('Minimum current operating/recovery acceptance is unavailable') from None

    def require_continuation(self, cursor, admitted, selection: dict, *,
                             grant: WorkerGrant, worker_identity: VerifiedWorkerIdentity) -> None:
        """Continue only the original current B10/B11 operation under its locks.

        The ordinary admission method still refuses all unresolved work. This
        path excludes exactly one verified claimed intent, never an UNKNOWN/
        UNCERTAIN intent, another operation, another worker or an expired epoch.
        """
        try:
            if (not isinstance(grant, WorkerGrant) or not isinstance(worker_identity, VerifiedWorkerIdentity)
                    or self.worker_grants is None):
                raise AuthorityDenied('Actual current worker grant and authenticated identity required')
            context = TenantContext(admitted.organization_id, admitted.tenant_id)
            verified = self.worker_grants.verify_intent(cursor, context,
                grant_id=grant.grant_id, job_id=admitted.job_id, step_id=grant.step_id,
                operation_id=grant.operation_id, operation_kind=grant.operation_kind,
                operation_scope=grant.operation_scope, worker_identity=worker_identity,
                lease_key=grant.lease_key, lease_epoch=grant.lease_epoch)
            if not isinstance(verified, WorkerGrant) or verified != grant:
                raise AuthorityDenied('Continuation grant differs from the authoritative current ledger')
            cursor.execute(
                'SELECT state,job_id,grant_id,step_id,lease_key,owner_epoch,worker_id,operation_kind,'
                'endpoint_id,native_scope_id,security_domain_id FROM '
                'hosting_controlplane.native_operation_intents '
                'WHERE organization_id=%s AND tenant_id=%s AND operation_id=%s FOR SHARE',
                (context.organization_id, context.tenant_id, grant.operation_id))
            row = cursor.fetchone()
            if (row is None or row[0] not in ('IN_FLIGHT', 'TASK_ACCEPTED')
                    or tuple(row[1:]) != (admitted.job_id, grant.grant_id, grant.step_id,
                        grant.lease_key, grant.lease_epoch, grant.worker_subject, grant.operation_kind,
                        grant.operation_scope.endpoint_id, grant.operation_scope.native_scope_id,
                        grant.operation_scope.security_domain_id)):
                raise AuthorityDenied('Continuation must be the exact original claimed native intent')
            self._require(cursor, admitted, selection, grant.operation_kind,
                          continuation_operation_id=grant.operation_id)
        except AuthorityDenied:
            raise
        except Exception:
            raise AuthorityDenied('Current original native operation continuation is held') from None

    def require_observation(self, cursor, admitted, selection: dict) -> None:
        """Inspect retained local facts during a hold; grants no native/read credential.

        The caller separately verifies reader authority and the immutable original
        job/plan/artifact binding. Revocation, terminal jobs and unknown native work
        do not hide those retained facts. Custody/signature/scope still must verify.
        """
        try:
            self._require(cursor, admitted, selection, 'LOCAL_RETAINED_OBSERVATION',
                          purpose='OBSERVATION')
        except AuthorityDenied:
            raise
        except Exception:
            raise AuthorityDenied('Retained observation custody is unavailable') from None

    def _require(self, cursor, admitted, selection: dict, operation_kind: str,
                 *, continuation_operation_id: str | None = None,
                 purpose: str = 'ADMISSION') -> None:
        if purpose not in ('ADMISSION', 'OBSERVATION'):
            raise AuthorityDenied('Only named admission/observation boundaries are implemented')
        if not isinstance(selection, dict) or not isinstance(operation_kind, str) or not operation_kind:
            raise AuthorityDenied('Selected admitted action required')
        context = TenantContext(admitted.organization_id, admitted.tenant_id)
        digest = selection['operationsAcceptanceDigest']
        key = acceptance_event_key(digest)
        self.evidence_gate.require(context)
        retained = self.evidence_gate.evidence.get(context, key)
        if retained is None:
            raise AuthorityDenied('Actual retained B44-B46 operating acceptance is missing')
        entry, envelope = retained
        if (entry.evidence_kind != 'VERIFICATION_RESULT' or entry.subject_id != scope_digest(selection)
                or entry.event_key != key or acceptance_digest(envelope) != digest):
            raise AuthorityDenied('Operating acceptance is not bound to selected scope and retained digest')
        if (not isinstance(envelope, dict) or set(envelope) != {'payload', 'keyId', 'signature'}
                or envelope['keyId'] not in self.key_ids):
            raise AuthorityDenied('Current dedicated operating signer is required')
        payload = envelope['payload']
        if not isinstance(payload, dict) or set(payload) != {
                'format', 'scopeDigest', 'sourceCommit', 'planId', 'revocationEpoch',
                'acceptedAt', 'reviewBy', 'reviewerRef', 'prerequisites'}:
            raise AuthorityDenied('Strict actual operating acceptance artifact required')
        self.verifier.verify(envelope['keyId'], _canonical(payload),
                             base64.b64decode(envelope['signature'], validate=True))
        # Observation follows the original immutable job/history. A subsequent
        # approved plan revision cannot hide its retained facts, and cannot
        # grant a native action through this separately named read-only port.
        selected_revision = ('j.plan_revision,j.plan_digest,' if purpose == 'OBSERVATION'
                             else 'p.plan_revision,p.plan_digest,')
        cursor.execute(
            "SELECT current_setting('app.organization_id',true),"
            "current_setting('app.tenant_id',true),clock_timestamp(),"
            'j.status,' + selected_revision + 'p.revocation_epoch,'
            '(SELECT count(*) FROM hosting_controlplane.native_operation_intents i '
            'WHERE i.organization_id=j.organization_id AND i.tenant_id=j.tenant_id '
            "AND i.state IN ('IN_FLIGHT','TASK_ACCEPTED','UNCERTAIN') "
            'AND (%s::text IS NULL OR i.operation_id<>%s)), '
            '(SELECT count(*) FROM hosting_controlplane.native_containment_holds h '
            'WHERE h.organization_id=j.organization_id AND h.tenant_id=j.tenant_id) '
            'FROM hosting_controlplane.operation_jobs j '
            'JOIN hosting_controlplane.plan_authority_state p ON '
            'p.organization_id=j.organization_id AND p.tenant_id=j.tenant_id AND p.plan_id=j.plan_id '
            'WHERE j.organization_id=%s AND j.tenant_id=%s AND j.job_id=%s',
            (continuation_operation_id, continuation_operation_id,
             context.organization_id, context.tenant_id, admitted.job_id))
        row = cursor.fetchone()
        if row is None:
            raise AuthorityDenied('Current scoped admitted job is missing')
        org, tenant, now, status, revision, plan_digest, epoch, unresolved, containment = row
        if ((org, tenant) != (context.organization_id, context.tenant_id)
                or (revision, plan_digest) != (admitted.plan_revision, admitted.plan_digest)
                or (purpose == 'ADMISSION' and (status not in ('STARTED', 'RUNNING')
                                              or epoch != admitted.revocation_epoch))):
            raise AuthorityDenied('Current job/authority epoch changed before native effect')
        if purpose == 'ADMISSION' and (unresolved or containment):
            raise AuthorityDenied('Unresolved native work or active containment prevents a new write')
        if (payload['format'] != 'hosting-selected-operating-acceptance/1'
                or payload['scopeDigest'] != scope_digest(selection)
                or payload['sourceCommit'] != selection['sourceCommit']
                or payload['planId'] != admitted.plan_id
                or type(payload['revocationEpoch']) is not int
                or payload['revocationEpoch'] != (admitted.revocation_epoch if purpose == 'OBSERVATION' else epoch)):
            raise AuthorityDenied('Operating acceptance covers a different code/scope/authority epoch')
        accepted = target_selection.instant(payload['acceptedAt'], 'acceptedAt')
        review = target_selection.instant(payload['reviewBy'], 'reviewBy')
        target_selection.opaque_ref(payload['reviewerRef'], 'reviewerRef')
        if accepted > now or review <= accepted or now >= review:
            raise AuthorityDenied('Operating acceptance is future-dated or review-due')
        facts = payload['prerequisites']
        if not isinstance(facts, list) or len(facts) != len(MINIMUM_PREREQUISITES):
            raise AuthorityDenied('Every minimum B44-B46 prerequisite needs actual retained evidence')
        seen = set()
        for fact in facts:
            if (not isinstance(fact, dict) or set(fact) != {
                    'id', 'result', 'evidenceRef', 'artifactSha256', 'observerRef', 'observedAt', 'freshUntil'}
                    or fact['id'] not in MINIMUM_PREREQUISITES or fact['id'] in seen
                    or fact['result'] != 'ACCEPTED' or not _SHA.fullmatch(fact['artifactSha256'])):
                raise AuthorityDenied('Minimum operating prerequisite is unaccepted or ambiguous')
            for field in ('evidenceRef', 'observerRef'):
                target_selection.opaque_ref(fact[field], field)
            observed = target_selection.instant(fact['observedAt'], 'observedAt')
            fresh = target_selection.instant(fact['freshUntil'], 'freshUntil')
            if observed > accepted or fresh <= observed or now >= fresh:
                raise AuthorityDenied('Minimum operating prerequisite evidence is not current')
            seen.add(fact['id'])
        # The restore/high-water verifier is live, so revocation/lag between
        # artifact retrieval and SQL inspection cannot be replaced by its packet.
        self.evidence_gate.require(context)


class QualifiedOperatingActionGate:
    """Fixed composition of native qualification and minimum operating gates."""
    def __init__(self, qualification_gate, operations_gate: OperationsActionGate):
        if (not callable(getattr(qualification_gate, 'require_action', None))
                or not isinstance(operations_gate, OperationsActionGate)):
            raise ValueError('Existing qualification and minimum operating owners required')
        self.qualification = qualification_gate
        self.operations = operations_gate

    def require_action(self, cursor, admitted, selection, operation_kind):
        self.qualification.require_action(cursor, admitted, selection, operation_kind)
        self.operations.require_action(cursor, admitted, selection, operation_kind)

    def require_continuation(self, cursor, admitted, selection, *, grant, worker_identity):
        self.qualification.require_action(cursor, admitted, selection, grant.operation_kind)
        self.operations.require_continuation(cursor, admitted, selection, grant=grant,
                                             worker_identity=worker_identity)

    def require_observation(self, cursor, admitted, selection):
        # Current native qualification is a prerequisite for native actions,
        # never a prerequisite for inspecting their original retained holds.
        self.operations.require_observation(cursor, admitted, selection)
