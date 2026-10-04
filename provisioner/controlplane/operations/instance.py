"""A separate, live operating interlock for every native writer.

Logical restoration changes the database OID and is quarantined before any
runtime ACL can be installed. An independently observed retained report and a
different operating owner's handover are necessary to commission the instance.
This never advances native ownership epochs or clears B48 import holds.
"""
from __future__ import annotations

import base64
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from uuid import uuid4

from provisioner.controlplane.authority.service import AuthorityDenied
from provisioner.controlplane.persistence import TenantContext
from provisioner.qualification.target_selection import instant

_SHA = re.compile(r'^[0-9a-f]{64}$')
_REV = re.compile(r'^[0-9a-f]{40}$')
_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$')
HANDOVER_CHECKS = frozenset({
    'CONTROL_DB_STATE', 'TEMPORAL_ORIGINAL_RUNS', 'INDEPENDENT_HIGH_WATER',
    'OLD_PRIMARY_EXCLUSION', 'NATIVE_EPOCH_RECONCILIATION',
    'RESTORED_WRITER_NEGATIVES', 'SERVICE_RECOVERY',
})


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode()


def digest(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _strict(value, fields, label):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise AuthorityDenied('Strict original ' + label + ' required')


def _envelope(value, verifier, key_ids):
    _strict(value, ('payload', 'keyId', 'signature'), 'signed operating artifact')
    if value['keyId'] not in key_ids:
        raise AuthorityDenied('Dedicated current operating/observer key required')
    verifier.verify(value['keyId'], canonical(value['payload']),
                    base64.b64decode(value['signature'], validate=True))
    return value['payload']


def state_digest(connection) -> str:
    """Business state; custody/audit high-water is a separate handover proof.

    Signing and retaining the observation necessarily appends evidence rows.
    They cannot be included in the digest of their own future signatures.
    """
    from .recovery import snapshot_state
    state = snapshot_state(connection)
    excluded = {name for name in state['tables'] if name == 'operating_instance'
                or name == 'audit_events' or name.startswith(('evidence_', 'audit_checkpoint'))}
    for name in excluded:
        state['tables'].pop(name, None)
        state['rls'].pop(name, None)
    state['sequences'] = [row for row in state['sequences']
                          if not row[0].startswith(('audit_', 'evidence_'))]
    return digest(state)


def quarantine(connection, *, manifest_sha256: str) -> dict:
    """Rotate the *control instance*, not a native owner, in isolated restore."""
    if not _SHA.fullmatch(manifest_sha256):
        raise ValueError('Original independent restore manifest digest required')
    row = connection.execute('SELECT generation FROM hosting_controlplane.operating_instance '
                             'WHERE singleton FOR UPDATE').fetchone()
    if row is None:
        raise AuthorityDenied('Restored instance interlock migration is missing')
    instance_id = uuid4().hex
    connection.execute('UPDATE hosting_controlplane.operating_instance SET instance_id=%s,'
        'database_oid=(SELECT oid FROM pg_catalog.pg_database WHERE datname=current_database()),'
        'database_system_identifier=(SELECT system_identifier::text FROM pg_catalog.pg_control_system()),'
        "generation=generation+1,mode='OBSERVATION_ONLY',organization_id=NULL,tenant_id=NULL,"
        'source_commit=NULL,artifact_sha256=NULL,report_event_key=NULL,report_sha256=NULL,'
        'handover_event_key=NULL,handover_sha256=NULL,review_until=NULL,'
        'restore_manifest_sha256=%s,updated_at=clock_timestamp() WHERE singleton',
        (instance_id, manifest_sha256))
    return {'instanceId': instance_id, 'generation': row[0] + 1,
            'mode': 'OBSERVATION_ONLY', 'mutationAuthorized': False}


class OperatingInstanceGate:
    def __init__(self, *, evidence_gate, observer_verifier, observer_key_ids: frozenset,
                 operating_verifier, operating_key_ids: frozenset,
                 source_commit: str, artifact_sha256: str, installed_identity=None):
        if (not callable(getattr(evidence_gate, 'require', None))
                or not callable(getattr(getattr(evidence_gate, 'evidence', None), 'get', None))
                or not callable(getattr(observer_verifier, 'verify', None))
                or not callable(getattr(operating_verifier, 'verify', None))
                or not isinstance(observer_key_ids, frozenset) or not observer_key_ids
                or not isinstance(operating_key_ids, frozenset) or not operating_key_ids
                or observer_key_ids & operating_key_ids
                or not _REV.fullmatch(source_commit) or not _SHA.fullmatch(artifact_sha256)):
            raise ValueError('Installed final bytes and separate observer/operating custody required')
        self.evidence_gate = evidence_gate
        self.observer_verifier, self.observer_keys = observer_verifier, observer_key_ids
        self.operating_verifier, self.operating_keys = operating_verifier, operating_key_ids
        self.source_commit, self.artifact_sha256 = source_commit, artifact_sha256
        if installed_identity is not None:
            from provisioner.controlplane.workflow.installed_identity import InstalledApplicationIdentity
            if (type(installed_identity) is not InstalledApplicationIdentity
                    or (installed_identity.source_commit, installed_identity.artifact_sha256) !=
                       (source_commit, artifact_sha256)):
                raise ValueError('Concrete installed wheel/tree/executable identity must match operating gate')
        self.installed_identity = installed_identity

    def _retained(self, context, key, sha):
        if not _ID.fullmatch(key) or not _SHA.fullmatch(sha):
            raise AuthorityDenied('Original retained operating artifact binding required')
        found = self.evidence_gate.evidence.get(context, key)
        if found is None:
            raise AuthorityDenied('Original independently retained operating artifact missing')
        entry, value = found
        if (entry.event_key != key or entry.evidence_kind != 'VERIFICATION_RESULT'
                or digest(value) != sha):
            raise AuthorityDenied('Retained operating evidence bytes differ')
        return value

    def _proofs(self, row, now, *, proposed_generation=None):
        (instance_id, database_oid, generation, mode, organization, tenant, source,
         artifact, report_key, report_sha, handover_key, handover_sha, review, system_id) = row
        context = TenantContext(organization, tenant)
        self.evidence_gate.require(context)
        report_envelope = self._retained(context, report_key, report_sha)
        report = _envelope(report_envelope, self.observer_verifier, self.observer_keys)
        _strict(report, ('format', 'instanceId', 'generation', 'databaseOid', 'databaseSystemIdentifier', 'sourceCommit',
            'artifactSha256', 'observedAt', 'freshUntil', 'stateDigest', 'checks'), 'handover observation')
        bound_generation = generation if proposed_generation is None else proposed_generation
        if (report['format'] != 'hosting-operating-handover-observation/1'
                or (report['instanceId'], report['generation'], report['databaseOid'],
                    report['sourceCommit'], report['artifactSha256']) !=
                   (instance_id, bound_generation, database_oid, self.source_commit, self.artifact_sha256)
                or report['databaseSystemIdentifier'] != system_id
                or (source, artifact) != (self.source_commit, self.artifact_sha256)
                or not _SHA.fullmatch(report['stateDigest'])):
            raise AuthorityDenied('Operating report belongs to different installed instance/bytes')
        observed, fresh = instant(report['observedAt'], 'observedAt'), instant(report['freshUntil'], 'freshUntil')
        if observed > now or fresh <= observed or now >= fresh:
            raise AuthorityDenied('Independent operating observations are not current')
        facts = report['checks']
        if not isinstance(facts, list) or len(facts) != len(HANDOVER_CHECKS):
            raise AuthorityDenied('Every actual operating handover check needs retained independent proof')
        seen = set()
        for fact in facts:
            _strict(fact, ('id', 'eventKey', 'sha256'), 'operating proof reference')
            if fact['id'] not in HANDOVER_CHECKS or fact['id'] in seen:
                raise AuthorityDenied('Ambiguous operating handover check')
            proof = _envelope(self._retained(context, fact['eventKey'], fact['sha256']),
                              self.observer_verifier, self.observer_keys)
            _strict(proof, ('format', 'checkId', 'instanceId', 'generation', 'sourceCommit',
                'artifactSha256', 'observedAt', 'freshUntil', 'observationEventKey',
                'observationDigest', 'result'),
                'independent operating check')
            if (proof['format'] != 'hosting-independent-operating-check/1'
                    or (proof['checkId'], proof['instanceId'], proof['generation'],
                        proof['sourceCommit'], proof['artifactSha256'], proof['result']) !=
                       (fact['id'], instance_id, bound_generation, source, artifact, 'ACCEPTED')
                    or not _SHA.fullmatch(proof['observationDigest'])):
                raise AuthorityDenied('Operating proof covers different scope or is unaccepted')
            fact_time = instant(proof['observedAt'], 'proof observedAt')
            fact_fresh = instant(proof['freshUntil'], 'proof freshUntil')
            if fact_time > observed or fact_fresh <= fact_time or now >= fact_fresh:
                raise AuthorityDenied('Operating handover proof is stale or future-dated')
            original = self.evidence_gate.evidence.get(context, proof['observationEventKey'])
            if (original is None or original[0].event_key != proof['observationEventKey']
                    or original[0].evidence_kind not in ('OBSERVATION', 'NATIVE_RECEIPT', 'VERIFICATION_RESULT')
                    or digest(original[1]) != proof['observationDigest']
                    or not isinstance(original[1], dict)
                    or not isinstance(original[1].get('measurements'), dict)
                    or not original[1]['measurements']
                    or any(original[1].get(key) != value for key, value in {
                        'instanceId': instance_id, 'checkId': fact['id'],
                        'sourceCommit': source, 'artifactSha256': artifact}.items())):
                raise AuthorityDenied('Independent operating check lacks its exact original observed bytes')
            fresh = min(fresh, fact_fresh)
            seen.add(fact['id'])
        acceptance = _envelope(self._retained(context, handover_key, handover_sha),
                               self.operating_verifier, self.operating_keys)
        _strict(acceptance, ('format', 'instanceId', 'generation', 'sourceCommit',
            'artifactSha256', 'reportSha256', 'acceptedAt', 'reviewUntil', 'changeRef'),
            'operating owner handover')
        if (acceptance['format'] != 'hosting-operating-instance-handover/1'
                or (acceptance['instanceId'], acceptance['generation'], acceptance['sourceCommit'],
                    acceptance['artifactSha256'], acceptance['reportSha256']) !=
                   (instance_id, bound_generation, source, artifact, report_sha)
                or not _ID.fullmatch(acceptance['changeRef'])):
            raise AuthorityDenied('Operating handover does not accept this original observer report')
        accepted = instant(acceptance['acceptedAt'], 'acceptedAt')
        accepted_review = instant(acceptance['reviewUntil'], 'reviewUntil')
        if accepted < observed or accepted > now or accepted_review <= accepted or accepted_review > fresh:
            raise AuthorityDenied('Operating handover exceeds current independent observations')
        if accepted_review != review or now >= review:
            raise AuthorityDenied('Operating acceptance is review-due or withdrawn')
        self.evidence_gate.require(context)
        return report

    def require_write_admission(self, cursor, context: TenantContext, **scope) -> None:
        """Live instance custody, in the same transaction as tenant/native gates."""
        try:
            if self.installed_identity is None:
                raise AuthorityDenied('Concrete current installed application identity required for writes')
            self.installed_identity.require_current()
            if not isinstance(context, TenantContext):
                raise AuthorityDenied('Verified tenant context required')
            cursor.execute("SELECT current_setting('app.organization_id',true),"
                           "current_setting('app.tenant_id',true),clock_timestamp(),"
                           '(SELECT oid FROM pg_catalog.pg_database WHERE datname=current_database())')
            organization, tenant, now, oid = cursor.fetchone()
            if (organization, tenant) != (context.organization_id, context.tenant_id):
                raise AuthorityDenied('Operating writer tenant context changed')
            cursor.execute('SELECT instance_id,database_oid,generation,mode,organization_id,tenant_id,'
                'source_commit,artifact_sha256,report_event_key,report_sha256,handover_event_key,'
                'handover_sha256,review_until,database_system_identifier '
                'FROM hosting_controlplane.lock_operating_instance()')
            row = cursor.fetchone()
            if row is None or row[3] != 'ACTIVE' or row[1] != oid or row[12] is None or now >= row[12]:
                raise AuthorityDenied('Restored/uncommissioned operating instance cannot write')
            self._proofs(row, now)
            self.installed_identity.require_current()
        except AuthorityDenied:
            raise
        except Exception:
            raise AuthorityDenied('Current independently accepted operating instance unavailable') from None

    def require_observation(self, cursor, context: TenantContext) -> None:
        """Independent local/read custody during bootstrap; never a write grant.

        Only the separately authorized fixed DISCOVER_READ owner may consume
        this port. Native mutations must use require_write_admission instead.
        """
        if not isinstance(context, TenantContext):
            raise AuthorityDenied('Verified observation tenant context required')
        cursor.execute("SELECT current_setting('app.organization_id',true),"
                       "current_setting('app.tenant_id',true)")
        if cursor.fetchone() != (context.organization_id, context.tenant_id):
            raise AuthorityDenied('Observation scope changed')
        self.evidence_gate.require(context)

    def accept_handover(self, connection, context: TenantContext, *, report_key: str,
                        report_sha256: str, handover_key: str, handover_sha256: str) -> dict:
        """Dedicated custody only; rehash actual drained state before activation.

        The method does not restart a writer. Scope import/epoch handover remains
        a separate mandatory B48 gate and current native grants are still needed.
        """
        if self.installed_identity is None:
            raise AuthorityDenied('Concrete current installed application identity required for handover')
        self.installed_identity.require_current()
        if connection.autocommit:
            raise AuthorityDenied('Operating handover requires a single explicit transaction')
        # The restored DB default stays read-only for all other sessions. Only
        # this dedicated custody transaction needs to update the interlock.
        connection.execute('SET TRANSACTION ISOLATION LEVEL SERIALIZABLE READ WRITE')
        with connection.cursor() as cursor:
            cursor.execute('SELECT rolsuper,rolbypassrls FROM pg_catalog.pg_roles WHERE rolname=current_user')
            if cursor.fetchone() != (False, True):
                raise AuthorityDenied('Dedicated NOSUPERUSER cross-tenant operating custodian required')
            cursor.execute('SELECT instance_id,database_oid,generation,mode,database_system_identifier FROM '
                           'hosting_controlplane.operating_instance WHERE singleton FOR UPDATE')
            original = cursor.fetchone()
            if original is None or original[3] not in ('UNCOMMISSIONED', 'OBSERVATION_ONLY', 'DRAINED'):
                raise AuthorityDenied('Instance must be drained or observation-only before handover')
            cursor.execute('SELECT clock_timestamp(),'
                '(SELECT oid FROM pg_catalog.pg_database WHERE datname=current_database()),'
                '(SELECT system_identifier::text FROM pg_catalog.pg_control_system()),'
                '(SELECT count(*) FROM hosting_controlplane.native_operation_intents '
                "WHERE state IN ('IN_FLIGHT','TASK_ACCEPTED','UNCERTAIN')),"
                '(SELECT count(*) FROM hosting_controlplane.native_containment_holds),'
                '(SELECT count(*) FROM hosting_controlplane.job_outbox '
                'WHERE first_start_attempted_at IS NOT NULL AND start_run_id IS NULL)')
            now, oid, system_id, unresolved, containment, unknown_start = cursor.fetchone()
            if oid != original[1] or system_id != original[4] or unresolved or containment or unknown_start:
                raise AuthorityDenied('Unresolved work, containment or unknown original starts prevent handover')
            envelope = self._retained(context, handover_key, handover_sha256)
            payload = _envelope(envelope, self.operating_verifier, self.operating_keys)
            review = instant(payload['reviewUntil'], 'reviewUntil')
            proposed = (*original[:2], original[2] + 1, 'ACTIVE', context.organization_id,
                context.tenant_id, self.source_commit, self.artifact_sha256, report_key,
                report_sha256, handover_key, handover_sha256, review, original[4])
            report = self._proofs(proposed, now)
            if state_digest(connection) != report['stateDigest']:
                raise AuthorityDenied('Current drained retained state differs from independent observation')
            self.installed_identity.require_current()
            cursor.execute("UPDATE hosting_controlplane.operating_instance SET generation=generation+1,"
                "mode='ACTIVE',organization_id=%s,tenant_id=%s,source_commit=%s,artifact_sha256=%s,"
                'report_event_key=%s,report_sha256=%s,handover_event_key=%s,handover_sha256=%s,'
                'review_until=%s,updated_at=clock_timestamp() WHERE singleton',
                proposed[4:13])
            self.installed_identity.require_current()
            return {'status': 'INSTANCE_HANDOVER_ACCEPTED', 'instanceId': original[0],
                    'generation': proposed[2], 'nativeEpochAdvanced': False,
                    'writersStarted': False, 'scopeHandoverStillRequired': True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('inspect', 'accept-handover'))
    parser.add_argument('--report-event-key')
    parser.add_argument('--report-sha256')
    parser.add_argument('--handover-event-key')
    parser.add_argument('--handover-sha256')
    args = parser.parse_args(argv)
    try:
        import psycopg
        from .recovery import _tls_dsn
        dsn = os.environ['HOSTING_OPERATING_CUSTODIAN_DSN']
        _tls_dsn(dsn)
        with psycopg.connect(dsn, connect_timeout=5) as connection:
            if args.mode == 'inspect':
                connection.execute('SET TRANSACTION READ ONLY')
                row = connection.execute('SELECT instance_id,generation,mode,database_oid,'
                    'database_oid=(SELECT oid FROM pg_catalog.pg_database WHERE datname=current_database()),'
                    'source_commit,artifact_sha256,review_until,restore_manifest_sha256,database_system_identifier FROM '
                    'hosting_controlplane.operating_instance WHERE singleton').fetchone()
                if row is None:
                    raise AuthorityDenied('Operating instance interlock is missing')
                result = dict(zip(('instanceId', 'generation', 'mode', 'databaseOid',
                    'currentDatabaseOidMatches', 'sourceCommit', 'artifactSha256', 'reviewUntil',
                    'restoreManifestSha256', 'databaseSystemIdentifier'), row))
                result.update(mutationAuthorized=False, writersStarted=False)
                if result['reviewUntil'] is not None:
                    result['reviewUntil'] = result['reviewUntil'].isoformat()
            else:
                from provisioner.controlplane.evidence.runtime import EvidenceRuntimeConfig, build_gate
                from provisioner.controlplane.workflow.installed_identity import InstalledApplicationIdentity
                from .runtime import build_instance_gate
                installed = InstalledApplicationIdentity.from_configuration(
                    Path(os.environ['HOSTING_APPLICATION_RUNTIME_CONFIG']),
                    Path(os.environ['HOSTING_APPLICATION_SOURCE_ROOT']))
                gate = build_instance_gate(build_gate(EvidenceRuntimeConfig.from_environment()),
                    source_commit=installed.source_commit, artifact_sha256=installed.artifact_sha256,
                    installed_identity=installed)
                result = gate.accept_handover(connection,
                    TenantContext(os.environ['HOSTING_OPERATING_ORGANIZATION_ID'], os.environ['HOSTING_OPERATING_TENANT_ID']),
                    report_key=args.report_event_key, report_sha256=args.report_sha256,
                    handover_key=args.handover_event_key, handover_sha256=args.handover_sha256)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception:
        print(json.dumps({'status': 'OPERATING_INSTANCE_HANDOVER_HELD', 'writersStarted': False,
                          'mutationAuthorized': False}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
