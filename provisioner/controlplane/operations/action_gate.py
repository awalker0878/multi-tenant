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
                 operating_key_ids: frozenset[str], worker_grants=None,
                 observer_verifier=None, observer_key_ids: frozenset[str] = frozenset()):
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
        if observer_verifier is not None and (not callable(getattr(observer_verifier, 'verify', None))
                or not isinstance(observer_key_ids, frozenset) or not observer_key_ids
                or observer_key_ids & operating_key_ids):
            raise ValueError('Minimum prerequisite observer must be separate from operating acceptance')
        self.observer_verifier, self.observer_keys = observer_verifier, observer_key_ids

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

    def require_database_continuation(self, cursor, admitted, selection: dict, *,
                                      coordination) -> None:
        """Check the three original SQL owners in the caller's transaction.

        Only the concrete selected PostgreSQL owner supplies this context. It
        cannot substitute an operation list or waive a tenant's unresolved
        work. All original grants and authenticated peers remain current even
        before a selected intent has been prepared or after it has resolved.
        """
        try:
            self._require(cursor, admitted, selection, 'RESTORE_DATA',
                          purpose='DATABASE_CONTINUATION', database_coordination=coordination)
        except AuthorityDenied:
            raise
        except Exception:
            raise AuthorityDenied('Current original coordinated database operations are held') from None

    def _database_operations(self, cursor, admitted, selection, coordination):
        from provisioner.controlplane.authority.model import PlanScope
        from provisioner.controlplane.persistence.store import NativeBinding
        from provisioner.controlplane.reconciliation.registry import NativeOperationRegistry
        from provisioner.controlplane.worker.grants import PostgresWorkerGrants
        from provisioner.controlplane.worker.pki import MutualTlsWorkerVerifier
        from provisioner.controlplane.workflow.admitted_job import AdmittedInput
        from provisioner.execution.run_files import encoded, digest
        from provisioner.migration.postgresql_authority import DatabaseOperationContext

        if (type(coordination) is not DatabaseOperationContext
                or not isinstance(admitted, AdmittedInput) or coordination.admitted != admitted
                or coordination.artifact != encoded(selection)
                or selection.get('driver') != 'openstack-linux-application-database/1'
                or selection.get('applicationDatabaseSelectionDigest') != coordination.descriptor.sha256
                or not isinstance(self.worker_grants, PostgresWorkerGrants)):
            raise AuthorityDenied('Exact original typed database selection and current B10 owner required')
        # Revalidate the immutable descriptor and process binding rather than
        # relying on its constructor having run at some earlier epoch.
        coordination.__post_init__()
        selected = coordination.descriptor.to_dict()
        if ((selected['source_scope'], selected['target_scope']) !=
                (selection['source'], selection['destination'])
                or len({row['operationId'] for row in selected['operations'].values()}) != 3
                or len({row['stepId'] for row in selected['operations'].values()}) != 3):
            raise AuthorityDenied('Database operations must be separate exact selected source, target and fence')
        context = TenantContext(admitted.organization_id, admitted.tenant_id)
        claimed = []
        deadlines = []
        original_registry = coordination.workers['source'].registry
        if (not isinstance(original_registry, NativeOperationRegistry)
                or original_registry._grants is not self.worker_grants):
            raise AuthorityDenied('Database continuation changed its actual original native registry')
        # A fixed order keeps the three current grants and owner rows under the
        # same transaction locks. Source and fence share a native dataset owner,
        # with separate grants and native roles; the target owns its own dataset.
        for side in ('source', 'target', 'fence'):
            worker = coordination.workers[side]
            command, grant = worker.command, worker.command.grant
            native = 'source' if side == 'fence' else side
            scope = PlanScope.from_record(selected[native + '_scope'])
            binding = NativeBinding(scope.platform_family, scope.endpoint_id, scope.native_scope_id,
                                    'dataset', selected[native]['nativeDatasetId'])
            row = selected['operations'][side]
            kind = 'SOURCE_FENCE' if side == 'fence' else 'RESTORE_DATA'
            if (command.context != context or command.grants is not self.worker_grants
                    or worker.registry is not original_registry
                    or not isinstance(command.verifier, MutualTlsWorkerVerifier)
                    or command.verifier.verify(command.transport_evidence) != command.identity
                    or not isinstance(command.identity, VerifiedWorkerIdentity)
                    or (command.identity.organization_id, command.identity.tenant_id,
                        command.identity.subject, command.identity.site_id) !=
                       (context.organization_id, context.tenant_id, grant.worker_subject, scope.site_id)
                    or worker.lease.binding != binding
                    or (worker.lease.organization_id, worker.lease.tenant_id, worker.lease.workload_id,
                        worker.lease.security_domain_id, worker.lease.worker_id, worker.lease.epoch) !=
                       (context.organization_id, context.tenant_id, selection['workloadId'],
                        scope.security_domain_id, command.identity.subject, grant.lease_epoch)
                    or (grant.source, grant.destination, grant.step_id, grant.operation_id,
                        grant.operation_kind, grant.operation_scope) !=
                       (PlanScope.from_record(selection['source']), PlanScope.from_record(selection['destination']),
                        row['stepId'], row['operationId'], kind, scope)):
                raise AuthorityDenied('A database owner differs from its exact original peer, dataset or operation')
            verified = self.worker_grants.verify_intent(cursor, context,
                grant_id=grant.grant_id, job_id=admitted.job_id, step_id=row['stepId'],
                operation_id=row['operationId'], operation_kind=kind, operation_scope=scope,
                worker_identity=command.identity, lease_key=grant.lease_key, lease_epoch=grant.lease_epoch)
            if not isinstance(verified, WorkerGrant) or verified != grant:
                raise AuthorityDenied('A database continuation grant changed in the authoritative current ledger')
            owner_deadline = original_registry._owner(cursor, context, worker.lease, live=True)
            deadlines.append(min(owner_deadline, worker.lease.expires_at,
                                 verified.expires_at, command.identity.expires_at))
            original_registry._containment(cursor, binding)
            cursor.execute('SELECT state,job_id,grant_id,step_id,lease_key,owner_epoch,worker_id,'
                'operation_kind,platform_family,endpoint_id,native_scope_id,resource_kind,native_id,'
                'workload_id,security_domain_id,request_digest '
                'FROM hosting_controlplane.native_operation_intents '
                'WHERE organization_id=%s AND tenant_id=%s AND operation_id=%s FOR SHARE',
                (context.organization_id, context.tenant_id, row['operationId']))
            intent = cursor.fetchone()
            if intent is None:
                continue
            if (intent[0] not in ('PREPARED', 'IN_FLIGHT', 'TASK_ACCEPTED', 'RESOLVED')
                    or tuple(intent[1:]) != (admitted.job_id, grant.grant_id, row['stepId'],
                        grant.lease_key, grant.lease_epoch, command.identity.subject, kind,
                        *binding.key(), selection['workloadId'], scope.security_domain_id,
                        digest(encoded({'descriptor': coordination.descriptor.sha256, 'side': side})))):
                raise AuthorityDenied('A selected database intent is uncertain or changed its original custody')
            if intent[0] in ('IN_FLIGHT', 'TASK_ACCEPTED'):
                claimed.append(row['operationId'])
        if min(deadlines) <= original_registry._clock(cursor):
            raise AuthorityDenied('A database original peer, grant or owner expired while acquiring locks')
        for worker in coordination.workers.values():
            if worker.command.verifier.verify(worker.command.transport_evidence) != worker.command.identity:
                raise AuthorityDenied('A database original enrolled mTLS peer changed under the operation locks')
        return tuple(claimed)

    def require_recovery_fencing(self,cursor,admitted,selection,*,original_job_id,original_operation_ids):
        """Only a new canonical recovery may fence original Vault credentials.

        This port is used by the fixed VaultRecoveryRevoker. It cannot claim an
        intent, delete native resources or refund capacity. Exactly selected
        original uncertainty may remain while it disables the old writer.
        """
        try:
            from provisioner.controlplane.jobs.repository import _JOB_SELECT,_ensure_plan,_job
            from provisioner.controlplane.reconciliation.resource_recovery import (
                PostgresResourceRecoveryAuthority,validate_recovery_selection)
            context=TenantContext(admitted.organization_id,admitted.tenant_id)
            cursor.execute(f'SELECT {_JOB_SELECT} FROM hosting_controlplane.operation_jobs '
                'WHERE organization_id=%s AND tenant_id=%s AND job_id=%s FOR SHARE',
                (context.organization_id,context.tenant_id,admitted.job_id))
            row=cursor.fetchone()
            if row is None: raise AuthorityDenied('New recovery admission is missing')
            job=_job(row)
            cursor.execute('SELECT revision,record_digest,record_json FROM hosting_controlplane.enterprise_records '
                "WHERE organization_id=%s AND tenant_id=%s AND record_kind='MigrationPlan' AND record_id=%s FOR SHARE",
                (context.organization_id,context.tenant_id,job.plan_id))
            plan=_ensure_plan(cursor.fetchone(),context,job)
            recovery=validate_recovery_selection(plan['spec'].get('resourceRecovery',{}))
            if (original_job_id==admitted.job_id or recovery['originalJobId']!=original_job_id
                    or recovery['originalOperationIds']!=list(original_operation_ids)
                    or 'cleanup' not in recovery['actions']
                    or recovery['resourceBundleDigest']!=selection['resourceBundleDigest']
                    or plan['spec'].get('execution',{}).get('artifactDigest')!=hashlib.sha256(_canonical(selection)).hexdigest()):
                raise AuthorityDenied('Credential fencing differs from exact newly approved retained recovery')
            cursor.execute('SELECT plan_digest FROM hosting_controlplane.operation_jobs '
                'WHERE organization_id=%s AND tenant_id=%s AND job_id=%s FOR SHARE',
                (context.organization_id,context.tenant_id,original_job_id))
            if cursor.fetchone()!=(recovery['originalPlanDigest'],):
                raise AuthorityDenied('Original recovery plan custody changed')
            cursor.execute('SELECT operation_id,job_id FROM hosting_controlplane.native_operation_intents '
                'WHERE organization_id=%s AND tenant_id=%s AND (job_id=%s OR job_id IN '
                '(SELECT recovery_job_id FROM hosting_controlplane.resource_recovery_bindings '
                'WHERE organization_id=%s AND tenant_id=%s AND original_job_id=%s AND recovery_job_id<>%s '
                'AND original_plan_digest=%s AND original_selection_digest=%s AND resource_bundle_digest=%s '
                'AND reservation_digest=%s)) ORDER BY operation_id FOR SHARE',
                (context.organization_id,context.tenant_id,original_job_id,
                 context.organization_id,context.tenant_id,original_job_id,admitted.job_id,
                 recovery['originalPlanDigest'],recovery['originalSelectionDigest'],
                 recovery['resourceBundleDigest'],recovery['reservationDigest']))
            original_rows=cursor.fetchall()
            if [row[0] for row in original_rows]!=recovery['originalOperationIds']:
                raise AuthorityDenied('Fencing must retain every original operation, including unknown work')
            related_jobs=sorted({row[1] for row in original_rows})
            for related_id in related_jobs:
                cursor.execute(f'SELECT {_JOB_SELECT} FROM hosting_controlplane.operation_jobs '
                    'WHERE organization_id=%s AND tenant_id=%s AND job_id=%s FOR SHARE',
                    (context.organization_id,context.tenant_id,related_id))
                previous=cursor.fetchone()
                if previous is None:
                    raise AuthorityDenied('Original or earlier cleanup custody is missing')
                old=_job(previous)
                if (old.source,old.destination)!=(job.source,job.destination):
                    raise AuthorityDenied('Earlier cleanup differs from the exact approved native scopes')
                PostgresResourceRecoveryAuthority._require_stopped_original(cursor,old)
            self._require(cursor,admitted,selection,'RECOVERY_CREDENTIAL_FENCE',purpose='RECOVERY_FENCE',
                fencing_job_ids=tuple(related_jobs),fencing_operation_ids=tuple(original_operation_ids))
        except AuthorityDenied: raise
        except Exception:
            raise AuthorityDenied('Exact current approved recovery credential fencing is unavailable') from None

    def _require(self, cursor, admitted, selection: dict, operation_kind: str,
                 *, continuation_operation_id: str | None = None,
                 purpose: str = 'ADMISSION',fencing_job_ids=(),fencing_operation_ids=(),
                 database_coordination=None) -> None:
        if purpose not in ('ADMISSION', 'OBSERVATION','RECOVERY_FENCE', 'DATABASE_CONTINUATION'):
            raise AuthorityDenied('Only named admission/observation boundaries are implemented')
        if not isinstance(selection, dict) or not isinstance(operation_kind, str) or not operation_kind:
            raise AuthorityDenied('Selected admitted action required')
        database_operations = (self._database_operations(cursor, admitted, selection, database_coordination)
                               if purpose == 'DATABASE_CONTINUATION' else ())
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
            'AND (%s::text IS NULL OR i.operation_id<>%s) '
            'AND NOT (i.job_id=ANY(%s::text[]) AND i.operation_id=ANY(%s::text[])) '
            "AND NOT (i.job_id=%s AND i.operation_id=ANY(%s::text[]) AND i.state IN ('IN_FLIGHT','TASK_ACCEPTED'))), "
            '(SELECT count(*) FROM hosting_controlplane.native_containment_holds h '
            'WHERE h.organization_id=j.organization_id AND h.tenant_id=j.tenant_id) '
            'FROM hosting_controlplane.operation_jobs j '
            'JOIN hosting_controlplane.plan_authority_state p ON '
            'p.organization_id=j.organization_id AND p.tenant_id=j.tenant_id AND p.plan_id=j.plan_id '
            'WHERE j.organization_id=%s AND j.tenant_id=%s AND j.job_id=%s',
            (continuation_operation_id, continuation_operation_id,list(fencing_job_ids),list(fencing_operation_ids),
             admitted.job_id,list(database_operations),
             context.organization_id, context.tenant_id, admitted.job_id))
        row = cursor.fetchone()
        if row is None:
            raise AuthorityDenied('Current scoped admitted job is missing')
        org, tenant, now, status, revision, plan_digest, epoch, unresolved, containment = row
        if ((org, tenant) != (context.organization_id, context.tenant_id)
                or (revision, plan_digest) != (admitted.plan_revision, admitted.plan_digest)
                or (purpose != 'OBSERVATION' and (status not in ('STARTED', 'RUNNING')
                                              or epoch != admitted.revocation_epoch))):
            raise AuthorityDenied('Current job/authority epoch changed before native effect')
        if purpose != 'OBSERVATION' and (unresolved or containment):
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
            if purpose in ('ADMISSION', 'DATABASE_CONTINUATION'):
                self._require_prerequisite(context, selection, fact)
            seen.add(fact['id'])
        # The restore/high-water verifier is live, so revocation/lag between
        # artifact retrieval and SQL inspection cannot be replaced by its packet.
        self.evidence_gate.require(context)
        if purpose == 'DATABASE_CONTINUATION':
            # Fetching independently retained prerequisite bytes can wait. Keep
            # every original grant/peer/window current at the command boundary.
            if self._database_operations(cursor, admitted, selection, database_coordination) != database_operations:
                raise AuthorityDenied('The original coordinated database operation state changed')

    def _require_prerequisite(self, context, selection, fact):
        if self.observer_verifier is None or not self.observer_keys:
            raise AuthorityDenied('Minimum prerequisite original independent observer custody missing')
        found = self.evidence_gate.evidence.get(context, fact['evidenceRef'])
        if (found is None or found[0].event_key != fact['evidenceRef']
                or found[0].evidence_kind != 'VERIFICATION_RESULT'
                or found[0].subject_id != scope_digest(selection)
                or acceptance_digest(found[1]) != fact['artifactSha256']):
            raise AuthorityDenied('Original minimum operating prerequisite bytes are missing or changed')
        envelope = found[1]
        if (not isinstance(envelope, dict) or set(envelope) != {'payload', 'keyId', 'signature'}
                or envelope['keyId'] not in self.observer_keys):
            raise AuthorityDenied('Dedicated independent prerequisite observer signature missing')
        proof = envelope['payload']
        if (not isinstance(proof, dict) or set(proof) != {'format', 'id', 'scopeDigest', 'sourceCommit',
                'observedAt', 'freshUntil', 'observerRef', 'result', 'observationEventKey', 'observationSha256'}
                or any(proof[key] != value for key, value in {
                    'format': 'hosting-selected-operating-prerequisite/1', 'id': fact['id'],
                    'scopeDigest': scope_digest(selection), 'sourceCommit': selection['sourceCommit'],
                    'observedAt': fact['observedAt'], 'freshUntil': fact['freshUntil'],
                    'observerRef': fact['observerRef'], 'result': 'ACCEPTED'}.items())):
            raise AuthorityDenied('Minimum prerequisite covers different exact code/scope/observation')
        self.observer_verifier.verify(envelope['keyId'], _canonical(proof),
                                      base64.b64decode(envelope['signature'], validate=True))
        target_selection.opaque_ref(proof['observationEventKey'], 'original prerequisite observation')
        if not _SHA.fullmatch(proof['observationSha256']):
            raise AuthorityDenied('Original prerequisite observation digest required')
        raw = self.evidence_gate.evidence.get(context, proof['observationEventKey'])
        if (raw is None or raw[0].event_key != proof['observationEventKey']
                or raw[0].evidence_kind not in ('OBSERVATION', 'VERIFICATION_RESULT', 'NATIVE_RECEIPT')
                or raw[0].subject_id != scope_digest(selection)
                or acceptance_digest(raw[1]) != proof['observationSha256']
                or not isinstance(raw[1], dict)
                or raw[1].get('format') != 'hosting-independent-selected-operating-observation/1'
                or raw[1].get('id') != fact['id'] or raw[1].get('scopeDigest') != scope_digest(selection)
                or raw[1].get('sourceCommit') != selection['sourceCommit']
                or not isinstance(raw[1].get('observations'), dict) or not raw[1]['observations']):
            raise AuthorityDenied('Minimum prerequisite original independent measurements missing')


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

    def require_database_continuation(self, cursor, admitted, selection, *, coordination):
        for kind in ('RESTORE_DATA', 'SOURCE_FENCE'):
            self.qualification.require_action(cursor, admitted, selection, kind)
        self.operations.require_database_continuation(cursor, admitted, selection,
                                                      coordination=coordination)

    def require_recovery_fencing(self,cursor,admitted,selection,*,original_job_id,original_operation_ids):
        self.qualification.require_action(cursor,admitted,selection,'NATIVE_CLEANUP')
        self.operations.require_recovery_fencing(cursor,admitted,selection,
            original_job_id=original_job_id,original_operation_ids=original_operation_ids)
