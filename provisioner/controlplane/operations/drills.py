"""Controlled HA switchover and observation-only restore rehearsal owners.

The only remote mutation is an authorized, explicit-candidate Patroni
switchover. No forced promotion, shell, arbitrary command, credential fallback,
workflow start/reset, blind retry or automatic writer restart is available.
Receipts measure observation readiness, never assert a full HA certificate.
"""
from __future__ import annotations

import asyncio
import argparse
import base64
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import ssl
import stat
import subprocess
import time
from urllib.parse import urlsplit

from provisioner.controlplane.authority.service import AuthorityDenied
from provisioner.controlplane.persistence import TenantContext
from provisioner.controlplane.workflow.temporal_adapter import (
    TemporalConnection, _MEMO_KEY, _admitted_input,
)
from provisioner.qualification.target_selection import instant
from . import recovery
from .instance import canonical, digest, state_digest

_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$')
_HEX = re.compile(r'^[0-9a-f]{64}$')
_UNIT = re.compile(r'^hosting-control-(?:application-worker|(?:dispatch|projector)@[A-Za-z0-9_-]{1,64})\.service$')
_READ_PATHS = frozenset({'/patroni', '/cluster', '/history', '/primary'})


@dataclass(frozen=True)
class SwitchoverSpec:
    drill_id: str
    instance_id: str
    generation: int
    source_commit: str
    artifact_sha256: str
    cluster_scope: str
    leader: str
    candidate: str
    leader_origin_sha256: str
    candidate_origin_sha256: str
    source_database_selection_sha256: str
    candidate_database_selection_sha256: str
    drain_database_selection_sha256: str
    writer_units: tuple[str, ...]
    maximum_rpo_seconds: int
    maximum_observation_rto_seconds: int

    def __post_init__(self):
        if (any(not isinstance(getattr(self, key), str) or not _ID.fullmatch(getattr(self, key))
                for key in ('drill_id', 'cluster_scope', 'leader', 'candidate'))
                or self.leader == self.candidate
                or not re.fullmatch(r'[0-9a-f]{32}', self.instance_id)
                or not re.fullmatch(r'[0-9a-f]{40}', self.source_commit)
                or any(not _HEX.fullmatch(getattr(self, key)) for key in (
                    'artifact_sha256', 'leader_origin_sha256', 'candidate_origin_sha256',
                    'source_database_selection_sha256', 'candidate_database_selection_sha256',
                    'drain_database_selection_sha256'))
                or self.leader_origin_sha256 == self.candidate_origin_sha256
                or type(self.generation) is not int or self.generation < 1
                or not isinstance(self.writer_units, tuple) or not 1 <= len(self.writer_units) <= 64
                or len(set(self.writer_units)) != len(self.writer_units)
                or any(not _UNIT.fullmatch(unit) for unit in self.writer_units)
                or type(self.maximum_rpo_seconds) is not int or not 0 <= self.maximum_rpo_seconds <= 3600
                or type(self.maximum_observation_rto_seconds) is not int
                or not 1 <= self.maximum_observation_rto_seconds <= 3600):
            raise ValueError('Exact commissioned HA endpoints, instance, writer units and budgets required')

    @property
    def digest(self):
        return digest(asdict(self))


def database_selection_digest(dsn: str) -> str:
    info = recovery._tls_dsn(dsn)
    # Credential rotation does not change the selected database. Keep secrets
    # out of every run sheet, receipt and signature input.
    return digest({key: info.get(key) for key in ('host', 'hostaddr', 'port', 'dbname',
                   'user', 'sslmode', 'sslrootcert', 'sslcert')})


class DrillAuthority:
    """Live separately signed operating decision and old-writer exclusion."""
    def __init__(self, *, evidence_gate, context: TenantContext, spec: SwitchoverSpec,
                 decision_key: str, decision_sha256: str, operating_verifier,
                 operating_keys: frozenset, observer_verifier, observer_keys: frozenset,
                 installed_identity=None):
        if (not isinstance(context, TenantContext) or not isinstance(spec, SwitchoverSpec)
                or not callable(getattr(evidence_gate, 'require', None))
                or not callable(getattr(getattr(evidence_gate, 'evidence', None), 'get', None))
                or not _ID.fullmatch(decision_key) or not _HEX.fullmatch(decision_sha256)
                or not isinstance(operating_keys, frozenset) or not operating_keys
                or not isinstance(observer_keys, frozenset) or not observer_keys
                or operating_keys & observer_keys):
            raise ValueError('Separate current independent custody and operating authority required')
        self.evidence_gate, self.context, self.spec = evidence_gate, context, spec
        self.decision_key, self.decision_sha256 = decision_key, decision_sha256
        self.operating_verifier, self.operating_keys = operating_verifier, operating_keys
        self.observer_verifier, self.observer_keys = observer_verifier, observer_keys
        if installed_identity is not None:
            from provisioner.controlplane.workflow.installed_identity import InstalledApplicationIdentity
            if (type(installed_identity) is not InstalledApplicationIdentity
                    or (installed_identity.source_commit, installed_identity.artifact_sha256) !=
                       (spec.source_commit, spec.artifact_sha256)):
                raise ValueError('Actual installed control-drill identity differs from selected bytes')
        self.installed_identity = installed_identity

    def _get(self, key, sha, kind, verifier, keys):
        found = self.evidence_gate.evidence.get(self.context, key)
        if (found is None or found[0].event_key != key or found[0].evidence_kind != kind
                or found[0].subject_id != self.spec.digest or digest(found[1]) != sha):
            raise AuthorityDenied('Exact original retained drill authority/proof unavailable')
        envelope = found[1]
        if (not isinstance(envelope, dict) or set(envelope) != {'payload', 'keyId', 'signature'}
                or envelope['keyId'] not in keys):
            raise AuthorityDenied('Independently trusted drill signer required')
        verifier.verify(envelope['keyId'], canonical(envelope['payload']),
                        base64.b64decode(envelope['signature'], validate=True))
        return envelope['payload']

    def require(self, step: str) -> dict:
        if step not in ('DRAIN_CONTROL_WRITERS', 'CONTROL_DB_SWITCHOVER'):
            raise AuthorityDenied('Only controlled stop and healthy switchover are implemented')
        if self.installed_identity is None:
            raise AuthorityDenied('Exact sealed installed drill identity is unavailable')
        self.installed_identity.require_current()
        self.evidence_gate.require(self.context)
        decision = self._get(self.decision_key, self.decision_sha256, 'RECOVERY_DECISION',
                             self.operating_verifier, self.operating_keys)
        if (not isinstance(decision, dict) or set(decision) != {
                'format', 'specificationSha256', 'organizationId', 'tenantId', 'allowedSteps',
                'authorizedAt', 'expiresAt', 'changeRef', 'exclusionEventKey', 'exclusionSha256'}
                or decision['format'] != 'hosting-controlled-ha-drill-authority/1'
                or decision['specificationSha256'] != self.spec.digest
                or (decision['organizationId'], decision['tenantId']) !=
                   (self.context.organization_id, self.context.tenant_id)
                or decision['allowedSteps'] != ['DRAIN_CONTROL_WRITERS', 'CONTROL_DB_SWITCHOVER']
                or not _ID.fullmatch(decision['changeRef'])):
            raise AuthorityDenied('Operating authority covers another exact HA drill')
        now = datetime.now(timezone.utc)
        authorized, expires = instant(decision['authorizedAt'], 'authorizedAt'), instant(decision['expiresAt'], 'expiresAt')
        if authorized > now or now >= expires or expires <= authorized or expires - authorized > timedelta(hours=2):
            raise AuthorityDenied('Controlled drill authority is stale or future-dated')
        if step == 'CONTROL_DB_SWITCHOVER':
            proof = self._get(decision['exclusionEventKey'], decision['exclusionSha256'],
                              'VERIFICATION_RESULT', self.observer_verifier, self.observer_keys)
            if (not isinstance(proof, dict) or set(proof) != {'format', 'specificationSha256',
                    'observedAt', 'freshUntil', 'oldPrimaryName', 'writerSetSha256',
                    'restartExclusionSha256', 'delayedRequestExclusionSha256', 'observationEventKey',
                    'observationSha256'} or proof['format'] != 'hosting-independent-old-primary-exclusion/1'
                    or proof['specificationSha256'] != self.spec.digest
                    or proof['oldPrimaryName'] != self.spec.leader
                    or proof['writerSetSha256'] != digest(list(self.spec.writer_units))
                    or any(not _HEX.fullmatch(proof[key]) for key in (
                        'restartExclusionSha256', 'delayedRequestExclusionSha256', 'observationSha256'))):
                raise AuthorityDenied('Persistent old-primary/writer exclusion is unproven')
            observed, fresh = instant(proof['observedAt'], 'observedAt'), instant(proof['freshUntil'], 'freshUntil')
            if observed > now or now >= fresh or fresh <= observed:
                raise AuthorityDenied('Old-primary exclusion is no longer current')
            original = self.evidence_gate.evidence.get(self.context, proof['observationEventKey'])
            if (original is None or original[0].evidence_kind != 'OBSERVATION'
                    or original[0].subject_id != self.spec.digest
                    or digest(original[1]) != proof['observationSha256']
                    or not isinstance(original[1], dict)
                    or any(original[1].get(key) != value for key, value in {
                        'format': 'hosting-independent-old-primary-observation/1',
                        'specificationSha256': self.spec.digest, 'oldPrimaryName': self.spec.leader,
                        'writerSetSha256': digest(list(self.spec.writer_units))}.items())
                    or not isinstance(original[1].get('observations'), dict) or not original[1]['observations']):
                raise AuthorityDenied('Original independent writer-exclusion observations are missing')
        self.evidence_gate.require(self.context)
        return decision


class PatroniOwner:
    """Fixed verified HTTPS origin; never follows returned member api_url."""
    def __init__(self, origin: str, *, tls_context: ssl.SSLContext):
        parsed = urlsplit(origin)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
                or parsed.path not in ('', '/') or parsed.query or parsed.fragment
                or tls_context.verify_mode != ssl.CERT_REQUIRED or not tls_context.check_hostname):
            raise ValueError('Exact commissioned verified HTTPS Patroni origin required')
        self.origin = origin.rstrip('/')
        self.endpoint, self.tls_context = parsed, tls_context

    @property
    def selection_digest(self):
        return hashlib.sha256(self.origin.encode()).hexdigest()

    def _request(self, method: str, path: str, value=None):
        if not ((method == 'GET' and path in _READ_PATHS and value is None)
                or (method == 'POST' and path == '/switchover' and isinstance(value, dict)
                    and set(value) == {'leader', 'candidate'}
                    and all(_ID.fullmatch(item) for item in value.values())
                    and value['leader'] != value['candidate'])):
            raise ValueError('Only fixed Patroni reads or explicit-candidate switchover permitted')
        connection = http.client.HTTPSConnection(self.endpoint.hostname, self.endpoint.port or 443,
                                                 context=self.tls_context, timeout=10)
        try:
            body = None if value is None else canonical(value)
            connection.request(method, path, body=body, headers={'Content-Type': 'application/json'})
            response = connection.getresponse()
            raw = response.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024 or response.status not in (200, 202, 503):
                raise RuntimeError('Patroni reply unavailable, redirected or outside bounded protocol')
            if method == 'POST':
                # A response body is informational, never promotion proof.
                return {'httpStatus': response.status, 'bodySha256': hashlib.sha256(raw).hexdigest()}
            if path == '/primary':
                return response.status
            if response.status != 200:
                raise RuntimeError('Current Patroni observation unavailable')
            return json.loads(raw)
        finally:
            connection.close()

    def observe(self):
        result = {'patroni': self._request('GET', '/patroni'),
                'cluster': self._request('GET', '/cluster'),
                'history': self._request('GET', '/history'),
                'primaryStatus': self._request('GET', '/primary')}
        # Native api_url is an observation, never a new authority-selected
        # endpoint. Replace it with a digest before independent receipt storage.
        for member in result['cluster'].get('members', []):
            if 'api_url' in member:
                member['apiOriginSha256'] = hashlib.sha256(str(member.pop('api_url')).encode()).hexdigest()
        return result

    def switchover(self, spec: SwitchoverSpec, authority: DrillAuthority):
        if self.selection_digest != spec.leader_origin_sha256 or authority.spec != spec:
            raise AuthorityDenied('Native drill endpoint/specification changed')
        authority.require('CONTROL_DB_SWITCHOVER')
        return self._request('POST', '/switchover', {'leader': spec.leader, 'candidate': spec.candidate})


class WriterDrain:
    """Only named deployed control-writer units, with a reviewed systemctl."""
    def __init__(self, *, systemctl: Path, systemctl_sha256: str):
        path = Path(systemctl).resolve(strict=True)
        info = path.stat()
        if (str(path) not in ('/usr/bin/systemctl', '/usr/local/bin/systemctl', '/bin/systemctl')
                or not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022
                or not _HEX.fullmatch(systemctl_sha256)
                or recovery._digest_file(path) != systemctl_sha256):
            raise ValueError('Reviewed root-owned systemctl binary required')
        self.path, self.sha256 = path, systemctl_sha256

    def stop(self, spec: SwitchoverSpec, authority: DrillAuthority):
        if authority.spec != spec:
            raise AuthorityDenied('Writer stop belongs to another authorized drill')
        receipts = []
        for unit in spec.writer_units:
            authority.require('DRAIN_CONTROL_WRITERS')
            if recovery._digest_file(self.path) != self.sha256:
                raise AuthorityDenied('Reviewed service owner changed')
            env = {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'SYSTEMD_PAGER': 'cat'}
            subprocess.run([str(self.path), '--no-pager', 'stop', unit], env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True, timeout=30)
            authority.require('DRAIN_CONTROL_WRITERS')
            result = subprocess.run([str(self.path), '--no-pager', 'show', unit,
                '--property=LoadState,ActiveState,SubState,MainPID,Result'], env=env,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=10)
            facts = dict(line.split('=', 1) for line in result.stdout.decode('ascii').splitlines())
            if (facts.get('LoadState') != 'loaded' or facts.get('ActiveState') != 'inactive'
                    or facts.get('MainPID') != '0' or facts.get('SubState') != 'dead'):
                raise AuthorityDenied('Writer service did not reach observed stopped state')
            receipts.append({'unit': unit, 'observedAt': datetime.now(timezone.utc).isoformat(),
                             'serviceFacts': facts})
        return receipts


class OperatingInstanceDrain:
    """Fixed SQL transition, separate from the SELECT-only observer identity."""
    def __init__(self, dsn: str):
        recovery._tls_dsn(dsn)
        self.dsn = dsn

    @property
    def selection_digest(self):
        return database_selection_digest(self.dsn)

    def drain(self, spec: SwitchoverSpec, authority: DrillAuthority):
        import psycopg
        if authority.spec != spec or self.selection_digest != spec.drain_database_selection_sha256:
            raise AuthorityDenied('Operating drain database differs from exact authorized selection')
        authority.require('DRAIN_CONTROL_WRITERS')
        with psycopg.connect(self.dsn, connect_timeout=5) as connection:
            if connection.execute('SELECT rolsuper,rolbypassrls FROM pg_catalog.pg_roles '
                                  'WHERE rolname=current_user').fetchone() != (False, True):
                raise AuthorityDenied('Dedicated operating custodian is required to drain')
            row = connection.execute('SELECT instance_id,generation,mode,source_commit,artifact_sha256,'
                'database_oid=(SELECT oid FROM pg_catalog.pg_database WHERE datname=current_database()),'
                'database_system_identifier=(SELECT system_identifier::text FROM pg_catalog.pg_control_system()) '
                'FROM hosting_controlplane.operating_instance WHERE singleton FOR UPDATE').fetchone()
            if row != (spec.instance_id, spec.generation, 'ACTIVE', spec.source_commit, spec.artifact_sha256, True, True):
                raise AuthorityDenied('Current commissioned instance changed before drill drain')
            authority.require('DRAIN_CONTROL_WRITERS')
            connection.execute("UPDATE hosting_controlplane.operating_instance SET mode='DRAINED',"
                               'generation=generation+1,updated_at=clock_timestamp() WHERE singleton')
        return {'instanceId': spec.instance_id, 'generation': spec.generation + 1, 'mode': 'DRAINED'}


class TemporalRetainedObserver:
    def __init__(self, connection: TemporalConnection):
        if not isinstance(connection, TemporalConnection) or connection.insecure_loopback_for_tests:
            raise ValueError('Separate verified read-only Temporal custody required')
        self.connection = connection

    def observe(self, receipts: list, *, prior: dict | None = None) -> dict:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self._observe(receipts, prior=prior))
        raise RuntimeError('Run synchronous drill observer outside an active event loop')

    async def _observe(self, receipts: list, *, prior=None):
        from temporalio.client import Client
        if len(receipts) > 1024:
            raise AuthorityDenied('Bounded drill slice exceeded; partition the commissioned drill')
        client = await Client.connect(self.connection.target_host, namespace=self.connection.namespace,
                                      tls=self.connection.tls())
        deadline = timedelta(seconds=self.connection.rpc_timeout_seconds)
        heads = {}
        for receipt in receipts:
            organization, tenant, job_id, namespace, run_id, payload_sha, payload = receipt
            if namespace != self.connection.namespace or not run_id:
                raise AuthorityDenied('Original Temporal namespace/run identity unavailable')
            admitted = _admitted_input(job_id, payload)
            if (admitted.organization_id, admitted.tenant_id, admitted.payload_digest) != (organization, tenant, payload_sha):
                raise AuthorityDenied('Original workflow payload/start receipt disagrees')
            handle = client.get_workflow_handle(job_id, run_id=run_id)
            description = await handle.describe(rpc_timeout=deadline)
            memo = await description.memo_value(_MEMO_KEY, None)
            expected = {'job_id': job_id, 'organization_id': organization, 'tenant_id': tenant,
                'plan_id': admitted.plan_id, 'plan_revision': admitted.plan_revision,
                'plan_digest': admitted.plan_digest, 'revocation_epoch': admitted.revocation_epoch,
                'payload_digest': payload_sha}
            if (description.id != job_id or description.run_id != run_id
                    or description.workflow_type not in ('AdmittedMigrationJob', 'OpenStackApplicationMigration')
                    or not isinstance(memo, dict) or any(memo.get(key) != value for key, value in expected.items())):
                raise AuthorityDenied('Retained Temporal run/memo differs from original accepted job')
            extras = set(memo) - set(expected)
            if extras and (extras != {'application_input_digest', 'selection_digest'}
                           or any(not _HEX.fullmatch(memo[key]) for key in extras)):
                raise AuthorityDenied('Original application workflow memo is ambiguous')
            key = digest({'organization': organization, 'tenant': tenant, 'job': job_id, 'run': run_id})
            original = prior.get(key) if prior is not None else None
            if prior is not None and original is None:
                raise AuthorityDenied('Recovered Temporal start was absent from original drill inventory')
            history_sha, prefix_sha, count, size = hashlib.sha256(), None, 0, 0
            async for event in handle.fetch_history_events(page_size=256, wait_new_event=False,
                                                           skip_archival=False, rpc_timeout=deadline):
                count += 1
                raw = event.SerializeToString(deterministic=True)
                size += len(raw)
                if event.event_id != count or count > 100000 or size > 64 * 1024**2:
                    raise AuthorityDenied('Retained workflow history gap or bounded inspection exceeded')
                history_sha.update(len(raw).to_bytes(8, 'big'))
                history_sha.update(raw)
                if original is not None and count == original['events']:
                    prefix_sha = history_sha.hexdigest()
            if count < 1:
                raise AuthorityDenied('Original workflow history expired or unavailable')
            head = {'events': count, 'sha256': history_sha.hexdigest(), 'bindingSha256': digest(memo)}
            if original is not None and (prefix_sha != original['sha256']
                                         or head['bindingSha256'] != original['bindingSha256']):
                raise AuthorityDenied('Recovered workflow lost or changed original accepted history')
            heads[key] = head
        if prior is not None and set(heads) != set(prior):
            raise AuthorityDenied('Recovered accepted workflow inventory changed')
        return heads


class ControlStateObserver:
    def __init__(self, dsn: str, temporal: TemporalRetainedObserver):
        recovery._tls_dsn(dsn)
        if not isinstance(temporal, TemporalRetainedObserver):
            raise ValueError('Fixed original Temporal observer required')
        self.dsn, self.temporal = dsn, temporal

    @property
    def selection_digest(self):
        return database_selection_digest(self.dsn)

    def observe(self, *, prior_temporal=None):
        import psycopg
        with psycopg.connect(self.dsn, connect_timeout=5) as connection:
            connection.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            recovery._require_custodian(connection, backup=True)
            at, in_recovery, lsn, replay_at, oid, system_id = connection.execute(
                'SELECT clock_timestamp(),pg_is_in_recovery(),CASE WHEN pg_is_in_recovery() '
                'THEN pg_last_wal_replay_lsn()::text ELSE pg_current_wal_lsn()::text END,'
                'pg_last_xact_replay_timestamp(),'
                '(SELECT oid FROM pg_catalog.pg_database WHERE datname=current_database()),'
                '(SELECT system_identifier::text FROM pg_catalog.pg_control_system())').fetchone()
            state = state_digest(connection)
            high_water = connection.execute('SELECT max(occurred_at) FROM '
                                             'hosting_controlplane.audit_events').fetchone()[0]
            receipts = connection.execute('SELECT organization_id,tenant_id,job_id,start_namespace,'
                'start_run_id,start_payload_digest,payload FROM hosting_controlplane.job_outbox '
                'WHERE first_start_attempted_at IS NOT NULL ORDER BY organization_id,tenant_id,job_id '
                'LIMIT 1025').fetchall()
            if any(row[4] is None for row in receipts):
                raise AuthorityDenied('Unknown original start needs independent reconciliation before drill')
        temporal_heads = self.temporal.observe(receipts, prior=prior_temporal)
        return {'observedAt': at.isoformat(), 'inRecovery': in_recovery, 'walLsn': lsn,
                'lastReplayAt': None if replay_at is None else replay_at.isoformat(),
                'databaseOid': oid, 'databaseSystemIdentifier': system_id,
                'stateDigest': state, 'temporalHeads': temporal_heads,
                'temporalDigest': digest(temporal_heads), 'originalAcceptedRuns': len(receipts),
                'retainedAuditHighWaterAt': None if high_water is None else high_water.isoformat()}


def _node(observed, *, name, scope, system_id=None, primary):
    facts = observed['patroni']
    patroni = facts.get('patroni', {})
    if (patroni.get('name') != name or patroni.get('scope') != scope
            or facts.get('state') not in ('running', 'streaming')
            or type(facts.get('timeline')) is not int or facts['timeline'] < 1
            or not isinstance(facts.get('database_system_identifier'), str)
            or not facts['database_system_identifier'].isdigit()
            or (system_id is not None and facts['database_system_identifier'] != system_id)
            or facts.get('pause') or facts.get('cluster_unlocked') or facts.get('failsafe_mode')
            or facts.get('pending_restart')
            or (primary and (facts.get('role') not in ('primary', 'master') or observed['primaryStatus'] != 200))
            or (not primary and (facts.get('role') not in ('replica', 'sync_standby') or observed['primaryStatus'] != 503))):
        raise AuthorityDenied('Native Patroni role, leader lock, cluster or timeline is unhealthy/ambiguous')
    members = observed['cluster'].get('members', [])
    if len([member for member in members if member.get('name') == name]) != 1:
        raise AuthorityDenied('Selected native member is absent or duplicated')
    if not isinstance(observed['history'], list):
        raise AuthorityDenied('Native timeline history is unavailable')
    return facts


def _write(directory: Path, name: str, value: dict):
    path = directory / name
    with path.open('xb') as output:
        os.chmod(path, 0o600)
        output.write(canonical(value) + b'\n')
        output.flush()
        os.fsync(output.fileno())


class ControlledSwitchover:
    def __init__(self, *, source: PatroniOwner, candidate: PatroniOwner,
                 source_state: ControlStateObserver, candidate_state: ControlStateObserver,
                 writers: WriterDrain, instance: OperatingInstanceDrain, authority: DrillAuthority):
        if (type(source) is not PatroniOwner or type(candidate) is not PatroniOwner
                or type(source_state) is not ControlStateObserver or type(candidate_state) is not ControlStateObserver
                or type(writers) is not WriterDrain or type(instance) is not OperatingInstanceDrain
                or type(authority) is not DrillAuthority):
            raise ValueError('Fixed operating process/native/retained-state owners required')
        self.source, self.candidate = source, candidate
        self.source_state, self.candidate_state = source_state, candidate_state
        self.writers, self.authority = writers, authority
        self.instance = instance

    def run(self, destination: Path) -> dict:
        spec = self.authority.spec
        if (self.source.selection_digest, self.candidate.selection_digest,
                self.source_state.selection_digest, self.candidate_state.selection_digest) != (
                spec.leader_origin_sha256, spec.candidate_origin_sha256,
                spec.source_database_selection_sha256, spec.candidate_database_selection_sha256):
            raise AuthorityDenied('Configured operating endpoints differ from authorized selection')
        directory = Path(destination)
        directory.mkdir(mode=0o700, parents=True, exist_ok=False)
        started, begin = datetime.now(timezone.utc), time.monotonic()
        contact_started = False
        command_started = False
        try:
            self.authority.require('DRAIN_CONTROL_WRITERS')
            contact_started = True
            old, standby = self.source.observe(), self.candidate.observe()
            leader = _node(old, name=spec.leader, scope=spec.cluster_scope, primary=True)
            replica = _node(standby, name=spec.candidate, scope=spec.cluster_scope,
                            system_id=leader['database_system_identifier'], primary=False)
            if replica['timeline'] != leader['timeline']:
                raise AuthorityDenied('Candidate timeline differs before controlled switchover')
            drained = self.instance.drain(spec, self.authority)
            stopped = self.writers.stop(spec, self.authority)
            before = self.source_state.observe()
            if before['inRecovery'] or before['databaseSystemIdentifier'] != leader['database_system_identifier']:
                raise AuthorityDenied('Selected source database is not the observed primary')
            _write(directory, 'before.json', {'specificationSha256': spec.digest,
                'observedAt': started.isoformat(), 'source': old, 'candidate': standby,
                'retained': before, 'stoppedServices': stopped, 'instanceDrain': drained})
            self.authority.require('CONTROL_DB_SWITCHOVER')
            # Publish an original attempt before POST. A crash/timeout can leave
            # this intent uncertain. Existing directories can NEVER be rerun.
            _write(directory, 'switchover-attempt.json', {'format': 'hosting-controlled-switchover-attempt/1',
                'specificationSha256': spec.digest, 'startedAt': datetime.now(timezone.utc).isoformat(),
                'leader': spec.leader, 'candidate': spec.candidate, 'replayPermitted': False})
            command_started = True
            response = self.source.switchover(spec, self.authority)
            _write(directory, 'switchover-response.json', response)
            # Observe once. A site can repeat read-only inspection, but no code
            # path automatically retries a promotion or restarts a writer.
            after_old, after_new = self.source.observe(), self.candidate.observe()
            new = _node(after_new, name=spec.candidate, scope=spec.cluster_scope,
                        system_id=leader['database_system_identifier'], primary=True)
            _node(after_old, name=spec.leader, scope=spec.cluster_scope,
                  system_id=leader['database_system_identifier'], primary=False)
            if new['timeline'] <= leader['timeline'] or not after_new['history']:
                raise AuthorityDenied('Native timeline transition lacks independent readable history')
            after = self.candidate_state.observe(prior_temporal=before['temporalHeads'])
            if (after['inRecovery'] or after['stateDigest'] != before['stateDigest']
                    or after['databaseSystemIdentifier'] != leader['database_system_identifier']):
                raise AuthorityDenied('Recovered control database lost/changed original retained business state')
            observed_rto = time.monotonic() - begin
            # Compare actual retained event clocks. Full service RPO remains
            # unasserted until independent custody and useful writes reconcile;
            # an idle replay timestamp is never treated as zero data loss.
            recovered_rpo = (None if before['retainedAuditHighWaterAt'] is None
                or after['retainedAuditHighWaterAt'] is None else max(0.0,
                    (instant(before['retainedAuditHighWaterAt'], 'source high-water') -
                     instant(after['retainedAuditHighWaterAt'], 'recovered high-water')).total_seconds()))
            report = {'format': 'hosting-controlled-ha-drill-report/1', 'specificationSha256': spec.digest,
                'instanceId': spec.instance_id, 'generation': spec.generation,
                'sourceCommit': spec.source_commit, 'artifactSha256': spec.artifact_sha256,
                'startedAt': started.isoformat(), 'observationReadyAt': datetime.now(timezone.utc).isoformat(),
                'status': 'OBSERVED_DRAINED_STATE_RECOVERED_AWAITING_INDEPENDENT_ACCEPTANCE',
                'observedRecoverySeconds': observed_rto, 'retainedHighWaterLossSeconds': recovered_rpo,
                'rpoBasis': 'ACTUAL_RETAINED_AUDIT_EVENT_CLOCKS_WITHIN_CAPTURED_DRAINED_INVENTORY',
                'serviceRpoSeconds': None, 'serviceRtoSeconds': None,
                'native': {'source': after_old, 'candidate': after_new},
                'retained': after, 'nativeContact': True, 'nativeMutationAttempted': True,
                'mutationAuthorized': False,
                'writersStarted': False, 'haAcceptanceIssued': False,
                'holds': ['INDEPENDENT_EVIDENCE_AUDIT_HIGH_WATER', 'PERSISTENT_OLD_PRIMARY_EXCLUSION',
                          'B48_SCOPED_NATIVE_EPOCH_HANDOVER', 'OPERATING_INSTANCE_HANDOVER',
                          'ACTUAL_USEFUL_SERVICE_RTO_AND_OWNER_ACCEPTANCE']}
            if observed_rto > spec.maximum_observation_rto_seconds:
                report['status'] = 'OBSERVATION_RTO_BUDGET_EXCEEDED'
            if recovered_rpo is None:
                report['holds'].append('ACTUAL_RETAINED_HIGH_WATER_RPO_MEASUREMENT_UNAVAILABLE')
            elif recovered_rpo > spec.maximum_rpo_seconds:
                report['status'] = 'RETAINED_HIGH_WATER_RPO_BUDGET_EXCEEDED'
            _write(directory, 'report.json', report)
            return report
        except Exception:
            report = {'format': 'hosting-controlled-ha-drill-report/1', 'specificationSha256': spec.digest,
                'instanceId': spec.instance_id, 'sourceCommit': spec.source_commit,
                'artifactSha256': spec.artifact_sha256,
                'status': 'SWITCHOVER_UNKNOWN_RECONCILE_NO_REPLAY' if command_started else 'DRILL_HELD',
                'elapsedSeconds': time.monotonic() - begin, 'nativeContact': contact_started,
                'nativeMutationAttempted': command_started,
                'mutationAuthorized': False, 'writersStarted': False, 'haAcceptanceIssued': False}
            _write(directory, 'report.json', report)
            return report


def observation_restore(dsn: str, source: Path, destination: Path, *, manifest_sha256: str,
                        source_commit: str, artifact_sha256: str) -> dict:
    """Execute fixed pg_restore + quarantine; measure readiness, never arm."""
    if not re.fullmatch(r'[0-9a-f]{40}', source_commit) or not _HEX.fullmatch(artifact_sha256):
        raise ValueError('Exact installed final code/artifact required for restore drill')
    directory = Path(destination)
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    started, begin = datetime.now(timezone.utc), time.monotonic()
    _write(directory, 'restore-attempt.json', {'manifestSha256': manifest_sha256,
        'startedAt': started.isoformat(), 'sourceCommit': source_commit,
        'artifactSha256': artifact_sha256, 'replayPermitted': False})
    report = recovery.restore(dsn, source, expected_manifest_sha256=manifest_sha256)
    result = {'format': 'hosting-observation-restore-drill/1', 'sourceCommit': source_commit,
        'artifactSha256': artifact_sha256, 'startedAt': started.isoformat(),
        'observationReadyAt': datetime.now(timezone.utc).isoformat(),
        'observationRecoverySeconds': time.monotonic() - begin, 'serviceRtoSeconds': None,
        'restore': report, 'nativeContact': False, 'mutationAuthorized': False,
        'haAcceptanceIssued': False}
    _write(directory, 'report.json', result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('switchover', 'restore'))
    parser.add_argument('--specification', type=Path)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--directory', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        from provisioner.controlplane.workflow.installed_identity import InstalledApplicationIdentity
        installed = InstalledApplicationIdentity.from_configuration(
            Path(os.environ['HOSTING_APPLICATION_RUNTIME_CONFIG']),
            Path(os.environ['HOSTING_APPLICATION_SOURCE_ROOT']))
        if args.mode == 'restore':
            if args.archive is None:
                raise ValueError('Exact independently retained control archive required')
            report = observation_restore(os.environ['HOSTING_RESTORE_DSN'], args.archive,
                args.directory, manifest_sha256=os.environ['HOSTING_RESTORE_MANIFEST_SHA256'],
                source_commit=installed.source_commit, artifact_sha256=installed.artifact_sha256)
        else:
            from provisioner.controlplane.evidence.runtime import EvidenceRuntimeConfig, build_gate
            from provisioner.controlplane.operations.runtime import build_operating_verifiers
            from provisioner.qualification.action_gate import _protected_index
            if args.specification is None:
                raise ValueError('An independently authorized exact HA specification is required')
            document = _protected_index(args.specification)
            if not isinstance(document, dict) or set(document) != set(SwitchoverSpec.__dataclass_fields__):
                raise ValueError('Strict current operating drill specification required')
            document['writer_units'] = tuple(document['writer_units'])
            spec = SwitchoverSpec(**document)
            if (spec.source_commit, spec.artifact_sha256) != (
                    installed.source_commit, installed.artifact_sha256):
                raise AuthorityDenied('Drill does not select currently installed signed bytes')
            gate = build_gate(EvidenceRuntimeConfig.from_environment())
            (observer, observer_keys), (operating, operating_keys) = build_operating_verifiers()
            authority = DrillAuthority(evidence_gate=gate,
                context=TenantContext(os.environ['HOSTING_DRILL_ORGANIZATION_ID'], os.environ['HOSTING_DRILL_TENANT_ID']),
                spec=spec, decision_key=os.environ['HOSTING_DRILL_DECISION_EVENT_KEY'],
                decision_sha256=os.environ['HOSTING_DRILL_DECISION_SHA256'],
                operating_verifier=operating, operating_keys=operating_keys,
                observer_verifier=observer, observer_keys=observer_keys, installed_identity=installed)
            tls = ssl.create_default_context(cafile=os.environ['HOSTING_PATRONI_CA_FILE'])
            tls.minimum_version = ssl.TLSVersion.TLSv1_2
            tls.load_cert_chain(os.environ['HOSTING_PATRONI_CLIENT_CERT_FILE'],
                                os.environ['HOSTING_PATRONI_CLIENT_KEY_FILE'])
            temporal = TemporalRetainedObserver(TemporalConnection(
                target_host=os.environ['HOSTING_DRILL_TEMPORAL_TARGET'],
                namespace=os.environ['HOSTING_DRILL_TEMPORAL_NAMESPACE'],
                task_queue=os.environ['HOSTING_DRILL_TEMPORAL_TASK_QUEUE'],
                server_ca=Path(os.environ['HOSTING_DRILL_TEMPORAL_CA_FILE']),
                client_cert=Path(os.environ['HOSTING_DRILL_TEMPORAL_CERT_FILE']),
                client_key=Path(os.environ['HOSTING_DRILL_TEMPORAL_KEY_FILE']),
                server_name=os.environ['HOSTING_DRILL_TEMPORAL_SERVER_NAME']))
            runner = ControlledSwitchover(
                source=PatroniOwner(os.environ['HOSTING_PATRONI_LEADER_ORIGIN'], tls_context=tls),
                candidate=PatroniOwner(os.environ['HOSTING_PATRONI_CANDIDATE_ORIGIN'], tls_context=tls),
                source_state=ControlStateObserver(os.environ['HOSTING_DRILL_SOURCE_OBSERVER_DSN'], temporal),
                candidate_state=ControlStateObserver(os.environ['HOSTING_DRILL_CANDIDATE_OBSERVER_DSN'], temporal),
                instance=OperatingInstanceDrain(os.environ['HOSTING_DRILL_CUSTODIAN_DSN']),
                writers=WriterDrain(systemctl=Path(os.environ['HOSTING_SYSTEMCTL_PATH']),
                                   systemctl_sha256=os.environ['HOSTING_SYSTEMCTL_SHA256']),
                authority=authority)
            report = runner.run(args.directory)
        print(json.dumps(report, sort_keys=True))
        ready = (report.get('status') == 'OBSERVED_DRAINED_STATE_RECOVERED_AWAITING_INDEPENDENT_ACCEPTANCE'
                 or report.get('restore', {}).get('status') == 'ARCHIVE_RECONCILED_OBSERVATION_ONLY')
        return 0 if ready else 2
    except Exception:
        print(json.dumps({'status': 'CONTROLLED_OPERATING_DRILL_HELD', 'writersStarted': False,
                          'mutationAuthorized': False, 'haAcceptanceIssued': False}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
