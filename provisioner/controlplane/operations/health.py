"""Tenant-scoped scheduled operating signals and restricted ITSM dispatch.

Collects database facts in a read-only transaction. Uncertain native operations
remain held; the monitor neither retries them nor clears authority/containment.
An alert is delivered only after the configured ITSM endpoint echoes its exact
idempotency key and digest. Its ACK is not an operator acknowledgement.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import ssl
from typing import Callable
from urllib.parse import urlsplit

from provisioner.controlplane.evidence.runtime import _private_file
from provisioner.controlplane.persistence import TenantContext
from .recovery import _tls_dsn

_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$')
RUNBOOKS = {
    'JOB_STUCK': 'docs/operations/control-application/1-operating-the-selected-slice.md#stuck-or-held-job',
    'JOB_HELD': 'docs/operations/control-application/1-operating-the-selected-slice.md#stuck-or-held-job',
    'NATIVE_UNCERTAIN': 'docs/operations/control-application/1-operating-the-selected-slice.md#uncertain-native-effect',
    'CONTAINMENT_ACTIVE': 'docs/operations/control-application/1-operating-the-selected-slice.md#active-containment',
    'EVIDENCE_UNAVAILABLE': 'docs/operations/control-application/1-operating-the-selected-slice.md#evidence-or-recovery-hold',
    'DISCOVERY_STALE': 'docs/operations/control-application/1-operating-the-selected-slice.md#stale-discovery',
    'OPERATING_INSTANCE_HELD': 'docs/operations/control-application/3-controlled-ha-and-restore-drills.md#writer-interlock-and-role-separation',
}


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('ascii')


@dataclass(frozen=True)
class MonitorPolicy:
    stuck_seconds: int = 900
    freshness_seconds: int = 3600
    limit: int = 256

    def __post_init__(self):
        if (type(self.stuck_seconds) is not int or not 30 <= self.stuck_seconds <= 86400
                or type(self.freshness_seconds) is not int or not 30 <= self.freshness_seconds <= 604800
                or type(self.limit) is not int or not 1 <= self.limit <= 2048):
            raise ValueError('Monitor requires bounded time and work limits')


def signal(context: TenantContext, code: str, subject_id: str,
           *, epoch: int, detail: str) -> dict:
    if (code not in RUNBOOKS or not _ID.fullmatch(subject_id)
            or type(epoch) is not int or epoch < 0 or len(detail) > 512
            or any(ord(char) < 32 for char in detail)):
        raise ValueError('Bounded scoped operating signal required')
    payload = {'format': 'hosting-operating-signal/1',
               'organizationId': context.organization_id, 'tenantId': context.tenant_id,
               'code': code, 'subjectId': subject_id, 'epoch': epoch,
               'detail': detail, 'runbook': RUNBOOKS[code],
               'severity': 'WARNING' if code == 'DISCOVERY_STALE' else 'CRITICAL',
               'mutationAuthorized': False}
    digest = hashlib.sha256(_canonical(payload)).hexdigest()
    return {**payload, 'signalId': 'ops-' + digest[:48], 'signalSha256': digest}


def collect(connection_factory: Callable, context: TenantContext, policy: MonitorPolicy,
            *, evidence_gate=None) -> dict:
    """Read retained health facts; never create new native observations."""
    if not isinstance(context, TenantContext) or not isinstance(policy, MonitorPolicy):
        raise ValueError('Validated tenant scope and monitor policy required')
    signals = []
    truncated = False
    with connection_factory() as connection:
        connection.execute('SET TRANSACTION READ ONLY')
        role = connection.execute('SELECT rolsuper,rolbypassrls FROM pg_catalog.pg_roles '
                                  'WHERE rolname=current_user').fetchone()
        if role != (False, False):
            raise ValueError('Monitoring identity must retain tenant RLS')
        connection.execute("SELECT set_config('app.organization_id',%s,true),"
                           "set_config('app.tenant_id',%s,true)",
                           (context.organization_id, context.tenant_id))
        instance = connection.execute('SELECT generation,mode,review_until>clock_timestamp(),'
            'database_oid=(SELECT oid FROM pg_catalog.pg_database WHERE datname=current_database()) '
            'FROM hosting_controlplane.operating_instance WHERE singleton').fetchone()
        if instance is None or instance[1] != 'ACTIVE' or not instance[2] or not instance[3]:
            signals.append(signal(context, 'OPERATING_INSTANCE_HELD', 'control-operating-instance',
                epoch=0 if instance is None else instance[0],
                detail='retained-operating-mode:' + ('MISSING' if instance is None else instance[1])))
        jobs = connection.execute(
            'SELECT job_id,status,last_event_sequence FROM hosting_controlplane.operation_jobs '
            'WHERE organization_id=%s AND tenant_id=%s '
            "AND (status='HELD' OR (status IN ('QUEUED','START_REQUESTED','STARTED','RUNNING') "
            "AND updated_at < clock_timestamp()-(%s*interval '1 second'))) "
            'ORDER BY updated_at,job_id LIMIT %s',
            (context.organization_id, context.tenant_id, policy.stuck_seconds, policy.limit + 1)
        ).fetchall()
        truncated |= len(jobs) > policy.limit
        for job_id, status, sequence in jobs[:policy.limit]:
            signals.append(signal(context, 'JOB_HELD' if status == 'HELD' else 'JOB_STUCK',
                                  job_id, epoch=sequence, detail='retained-status:' + status))
        uncertain = connection.execute(
            'SELECT operation_id,owner_epoch,state FROM hosting_controlplane.native_operation_intents '
            'WHERE organization_id=%s AND tenant_id=%s '
            "AND (state='UNCERTAIN' OR (state IN ('IN_FLIGHT','TASK_ACCEPTED') "
            "AND updated_at < clock_timestamp()-(%s*interval '1 second'))) "
            'ORDER BY updated_at,operation_id LIMIT %s',
            (context.organization_id, context.tenant_id, policy.stuck_seconds, policy.limit + 1)
        ).fetchall()
        truncated |= len(uncertain) > policy.limit
        for operation_id, epoch, state in uncertain[:policy.limit]:
            signals.append(signal(context, 'NATIVE_UNCERTAIN', operation_id,
                                  epoch=epoch, detail='retained-native-state:' + state))
        holds = connection.execute(
            'SELECT incident_id FROM hosting_controlplane.native_containment_holds '
            'WHERE organization_id=%s AND tenant_id=%s '
            'ORDER BY created_at,incident_id LIMIT %s',
            (context.organization_id, context.tenant_id, policy.limit + 1)).fetchall()
        truncated |= len(holds) > policy.limit
        for (incident_id,) in holds[:policy.limit]:
            signals.append(signal(context, 'CONTAINMENT_ACTIVE', incident_id, epoch=0,
                                  detail='Containment must be handled by incident authority'))
        freshness = connection.execute(
            'SELECT r.environment_id,COALESCE(f.sequence,0) '
            'FROM hosting_controlplane.environment_registrations r '
            'LEFT JOIN LATERAL (SELECT sequence,recorded_at,report_json '
            'FROM hosting_controlplane.discovery_freshness_checks f '
            'WHERE f.organization_id=r.organization_id AND f.tenant_id=r.tenant_id '
            'AND f.environment_id=r.environment_id ORDER BY sequence DESC LIMIT 1) f ON true '
            'WHERE r.organization_id=%s AND r.tenant_id=%s '
            "AND (f.sequence IS NULL OR f.recorded_at < clock_timestamp()-(%s*interval '1 second') "
            "OR jsonb_array_length(COALESCE(f.report_json::jsonb->'issues','[]'::jsonb))>0) "
            'ORDER BY r.environment_id LIMIT %s',
            (context.organization_id, context.tenant_id, policy.freshness_seconds,
             policy.limit + 1)).fetchall()
        truncated |= len(freshness) > policy.limit
        for environment_id, sequence in freshness[:policy.limit]:
            signals.append(signal(context, 'DISCOVERY_STALE', environment_id, epoch=sequence,
                                  detail='Freshness check is absent, stale or contains retained issues'))
    if evidence_gate is not None:
        try:
            evidence_gate.require(context)
        except Exception:
            signals.append(signal(context, 'EVIDENCE_UNAVAILABLE', 'independent-evidence', epoch=0,
                                  detail='Signed checkpoint or retained artifact cannot be verified'))
    else:
        signals.append(signal(context, 'EVIDENCE_UNAVAILABLE', 'independent-evidence', epoch=0,
                              detail='Independent evidence verifier is not configured'))
    return {'format': 'hosting-operating-health/1',
            'organizationId': context.organization_id, 'tenantId': context.tenant_id,
            'status': 'HEALTH_HELD' if signals or truncated else 'NO_RETAINED_INCIDENT_SIGNALS',
            'observedAt': datetime.now(timezone.utc).isoformat(), 'signals': signals,
            'truncated': truncated, 'nativeContact': False, 'mutationAuthorized': False,
            'serviceReadiness': 'NOT_ASSERTED'}


class IncidentDispatcher:
    """Configured HTTPS ITSM intake; does not send mail/chat or close incidents."""

    def __init__(self, endpoint: str, *, tls_context: ssl.SSLContext,
                 token: Callable[[], str], connection_factory=None):
        parsed = urlsplit(endpoint)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
                or parsed.query or parsed.fragment or parsed.path in ('', '/')
                or tls_context.verify_mode != ssl.CERT_REQUIRED or not tls_context.check_hostname):
            raise ValueError('Dedicated verified HTTPS incident intake is required')
        self.endpoint = parsed
        self.token = token
        self.connection_factory = connection_factory or http.client.HTTPSConnection
        self.tls_context = tls_context

    def dispatch(self, item: dict) -> dict:
        payload = {key: value for key, value in item.items()
                   if key not in ('signalId', 'signalSha256')}
        context = TenantContext(item.get('organizationId'), item.get('tenantId'))
        expected = signal(context, item.get('code'), item.get('subjectId'),
                          epoch=item.get('epoch'), detail=item.get('detail'))
        if item != expected or hashlib.sha256(_canonical(payload)).hexdigest() != item['signalSha256']:
            raise ValueError('Operating signal was changed before dispatch')
        token = self.token()
        if (not isinstance(token, str) or not token or len(token) > 8192
                or any(char.isspace() or ord(char) < 33 or ord(char) > 126 for char in token)):
            raise ValueError('Private scoped incident-intake credential required')
        connection = self.connection_factory(self.endpoint.hostname, self.endpoint.port or 443,
                                             context=self.tls_context, timeout=10)
        try:
            connection.request('POST', self.endpoint.path, body=_canonical(item), headers={
                'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json',
                'Idempotency-Key': item['signalId']})
            response = connection.getresponse()
            data = response.read(16385)
            if response.status not in (200, 201, 202) or len(data) > 16384:
                raise RuntimeError('Incident intake did not accept a bounded receipt')
            receipt = json.loads(data)
            if (not isinstance(receipt, dict) or set(receipt) != {
                    'signalId', 'signalSha256', 'incidentId', 'acknowledgedBy', 'acknowledgedAt'}
                    or receipt['signalId'] != item['signalId']
                    or receipt['signalSha256'] != item['signalSha256']
                    or not isinstance(receipt['incidentId'], str)
                    or not _ID.fullmatch(receipt['incidentId'])):
                raise RuntimeError('Incident receipt does not bind the exact retained signal')
            who, at = receipt['acknowledgedBy'], receipt['acknowledgedAt']
            if (who is None) != (at is None):
                raise RuntimeError('Operator acknowledgement is incomplete')
            if who is not None:
                if not isinstance(who, str) or not _ID.fullmatch(who):
                    raise RuntimeError('Bounded operator identity required')
                instant = datetime.fromisoformat(at.replace('Z', '+00:00'))
                if instant.tzinfo is None or instant > datetime.now(timezone.utc):
                    raise RuntimeError('Operator acknowledgement instant is invalid')
            return {'format': 'hosting-incident-dispatch-receipt/1', **receipt,
                    'deliveryStatus': 'DELIVERED',
                    'operatorAcknowledged': who is not None, 'mutationAuthorized': False}
        finally:
            connection.close()


def retain_delivery(evidence_gate, context: TenantContext, item: dict, receipt: dict) -> dict:
    """Retain exact dispatch/ACK proof through the existing immutable evidence owner."""
    if (not isinstance(receipt, dict) or set(receipt) != {
                'format', 'signalId', 'signalSha256', 'incidentId',
                'acknowledgedBy', 'acknowledgedAt', 'deliveryStatus',
                'operatorAcknowledged', 'mutationAuthorized'}
            or receipt.get('format') != 'hosting-incident-dispatch-receipt/1'
            or receipt.get('signalId') != item.get('signalId')
            or receipt.get('signalSha256') != item.get('signalSha256')
            or receipt.get('deliveryStatus') != 'DELIVERED'
            or receipt.get('mutationAuthorized') is not False
            or not isinstance(receipt['incidentId'], str) or not _ID.fullmatch(receipt['incidentId'])
            or (item.get('organizationId'), item.get('tenantId')) !=
                (context.organization_id, context.tenant_id)):
        raise ValueError('Exact scoped delivery receipt is required')
    who, at = receipt['acknowledgedBy'], receipt['acknowledgedAt']
    if ((who is None) != (at is None)
            or receipt['operatorAcknowledged'] is not (who is not None)):
        raise ValueError('Delivery cannot substitute a Boolean for accountable operator acknowledgement')
    if who is not None:
        if not isinstance(who, str) or not _ID.fullmatch(who) or not isinstance(at, str):
            raise ValueError('Exact operator acknowledgement identity and instant required')
        instant = datetime.fromisoformat(at.replace('Z', '+00:00'))
        if instant.tzinfo is None or instant > datetime.now(timezone.utc):
            raise ValueError('Actual operator acknowledgement instant required')
    evidence_gate.require(context)
    digest = hashlib.sha256(_canonical(receipt)).hexdigest()
    entry = evidence_gate.evidence.append(context, event_key='ops-dispatch-' + digest,
        evidence_kind='VERIFICATION_RESULT', subject_id=item['signalId'], artifact=receipt)
    evidence_gate.checkpoint(context)
    return {**receipt, 'evidenceEventKey': entry.event_key, 'evidenceBlobDigest': entry.blob_digest}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--organization-id', required=True)
    parser.add_argument('--tenant-id', required=True)
    parser.add_argument('--dispatch', action='store_true')
    parser.add_argument('--stuck-seconds', type=int, default=900)
    args = parser.parse_args(argv)
    try:
        import psycopg
        from provisioner.controlplane.evidence.runtime import EvidenceRuntimeConfig, build_gate
        dsn = os.environ['HOSTING_OPS_DSN']
        _tls_dsn(dsn)
        context = TenantContext(args.organization_id, args.tenant_id)
        config = EvidenceRuntimeConfig.from_environment()
        evidence = build_gate(config, allow_signing=args.dispatch)
        report = collect(lambda: psycopg.connect(dsn, connect_timeout=5), context,
                         MonitorPolicy(stuck_seconds=args.stuck_seconds), evidence_gate=evidence)
        if args.dispatch:
            tls = ssl.create_default_context(cafile=os.environ['HOSTING_OPS_INCIDENT_CA'])
            tls.minimum_version = ssl.TLSVersion.TLSv1_2
            dispatcher = IncidentDispatcher(os.environ['HOSTING_OPS_INCIDENT_ENDPOINT'],
                tls_context=tls, token=lambda: _private_file(Path(os.environ['HOSTING_OPS_INCIDENT_TOKEN_FILE'])))
            report['deliveryReceipts'] = [retain_delivery(evidence, context, item, dispatcher.dispatch(item))
                                          for item in report['signals']]
        print(json.dumps(report, sort_keys=True))
        return 2 if report['status'] == 'HEALTH_HELD' else 0
    except Exception:
        print(json.dumps({'status': 'MONITOR_HELD', 'mutationAuthorized': False}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
