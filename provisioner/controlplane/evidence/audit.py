"""Independent high-water signatures over every tenant audit event.

The append chain is maintained by the database trigger in migration 0008. An
operator initializes a checkpoint against an independently attested baseline;
normal checkpointing can only advance an already trusted signed prefix.
"""
from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from datetime import timezone
from typing import Callable

from provisioner.controlplane.persistence import TenantContext
from .repository import (Checkpoint, CheckpointSigner, CheckpointStore,
                         CheckpointVerifier, EvidenceIntegrityError,
                         EvidenceUnavailable, GENESIS, _DIGEST, _KEY, _canonical)


@dataclass(frozen=True)
class AuditVerification:
    head_sequence: int
    anchored_sequence: int
    head_hash: str

    @property
    def unanchored_count(self) -> int:
        return self.head_sequence - self.anchored_sequence


def _audit_hash(row) -> str:
    (event_id, organization_id, tenant_id, actor_id, correlation_id, action,
     record_kind, record_id, revision, record_digest, details_text, occurred_at,
     sequence, previous_hash, _stored_hash) = row
    fields = ('audit-v1', str(event_id), organization_id, tenant_id, actor_id,
              correlation_id, action, record_kind, record_id, str(revision),
              record_digest, details_text,
              occurred_at.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
              str(sequence), previous_hash)
    payload = b''.join(str(len(part.encode('utf-8'))).encode('ascii') + b':' +
                       part.encode('utf-8') for part in fields)
    return hashlib.sha256(payload).hexdigest()


class AuditCheckpointRepository:
    """Verify audit chain and sign an independently retained high-water mark.

    The checkpoint store must use a separate namespace from evidence_entries.
    Only a narrowly privileged operator may call ``initialize``. A missing
    checkpoint after initialization is an incident, never a reason to reset.
    """

    def __init__(self, connection_factory: Callable, checkpoints: CheckpointStore,
                 signer: CheckpointSigner, verifier: CheckpointVerifier):
        if (not callable(connection_factory) or checkpoints is None or signer is None
                or verifier is None or not callable(getattr(signer, 'sign', None))
                or not callable(getattr(verifier, 'verify', None))):
            raise ValueError('Database, independent checkpoint store, signer and verifier required')
        self._connect = connection_factory
        self._checkpoints = checkpoints
        self._signer = signer
        self._verifier = verifier

    @staticmethod
    def _tenant(cursor, context: TenantContext) -> None:
        if not isinstance(context, TenantContext):
            raise TypeError('Trusted tenant context required')
        if cursor.connection.autocommit:
            raise RuntimeError('Audit verification requires a transaction')
        cursor.execute('SELECT rolsuper, rolbypassrls FROM pg_catalog.pg_roles '
                       'WHERE rolname = current_user')
        role = cursor.fetchone()
        if role is None or role[0] or role[1]:
            raise RuntimeError('Audit verifier must enforce PostgreSQL row security')
        cursor.execute("SELECT set_config('app.organization_id', %s, true), "
                       "set_config('app.tenant_id', %s, true)",
                       (context.organization_id, context.tenant_id))

    def _chain(self, context: TenantContext) -> tuple[int, str, list[str]]:
        with self._connect() as connection:
            if connection.autocommit:
                raise RuntimeError('Audit verification requires a transaction')
            # No row lock is needed; both queries must see the same snapshot.
            connection.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            with connection.cursor() as cursor:
                self._tenant(cursor, context)
                cursor.execute('SELECT last_sequence, head_hash FROM '
                               'hosting_controlplane.audit_streams '
                               'WHERE organization_id = %s AND tenant_id = %s',
                               (context.organization_id, context.tenant_id))
                stream = cursor.fetchone() or (0, GENESIS)
                cursor.execute('SELECT event_id, organization_id, tenant_id, actor_id, '
                               'correlation_id, action, record_kind, record_id, revision, '
                               'record_digest, details::text, occurred_at, audit_sequence, '
                               'previous_hash, event_hash FROM hosting_controlplane.audit_events '
                               'WHERE organization_id = %s AND tenant_id = %s '
                               'ORDER BY audit_sequence',
                               (context.organization_id, context.tenant_id))
                rows = cursor.fetchall()
        previous = GENESIS
        hashes = []
        for ordinal, row in enumerate(rows, 1):
            if (row[12] != ordinal or row[13] != previous
                    or _audit_hash(row) != row[14]):
                raise EvidenceIntegrityError('Audit event sequence or bytes were modified')
            previous = row[14]
            hashes.append(previous)
        if stream != (len(rows), previous):
            raise EvidenceIntegrityError('Audit stream state does not match audit events')
        return len(rows), previous, hashes

    def _anchor(self, context: TenantContext) -> Checkpoint:
        try:
            envelope = self._checkpoints.latest(context.organization_id,
                                                context.tenant_id)
        except (ValueError, TypeError, KeyError) as exc:
            raise EvidenceIntegrityError('Independent audit checkpoint malformed') from exc
        except Exception as exc:
            raise EvidenceUnavailable('Independent audit checkpoint store unavailable') from exc
        if envelope is None:
            raise EvidenceUnavailable('Tenant has no independently signed audit checkpoint')
        try:
            payload = envelope['payload']
            signature = base64.b64decode(envelope['signature'], validate=True)
            if (set(envelope) != {'payload', 'signature'} or
                    set(payload) != {'v', 'stream', 'organizationId', 'tenantId',
                                     'sequence', 'headHash', 'keyId'} or
                    payload['v'] != 1 or payload['stream'] != 'audit_events' or
                    payload['organizationId'] != context.organization_id or
                    payload['tenantId'] != context.tenant_id or
                    type(payload['sequence']) is not int or payload['sequence'] < 0 or
                    not isinstance(payload['headHash'], str) or
                    not _DIGEST.fullmatch(payload['headHash']) or
                    not isinstance(payload['keyId'], str) or
                    not _KEY.fullmatch(payload['keyId'])):
                raise ValueError('Checkpoint scope or format mismatch')
            self._verifier.verify(payload['keyId'], _canonical(payload), signature)
            return Checkpoint(context.organization_id, context.tenant_id,
                              payload['sequence'], payload['headHash'], payload['keyId'])
        except Exception as exc:
            raise EvidenceIntegrityError('Independent audit checkpoint verification failed') from exc

    def _publish(self, context: TenantContext, sequence: int, head_hash: str) -> Checkpoint:
        key_id = self._signer.key_id
        if not isinstance(key_id, str) or not _KEY.fullmatch(key_id):
            raise EvidenceUnavailable('Audit signing identity is not configured')
        payload = {'v': 1, 'stream': 'audit_events',
                   'organizationId': context.organization_id,
                   'tenantId': context.tenant_id, 'sequence': sequence,
                   'headHash': head_hash, 'keyId': key_id}
        try:
            signature = self._signer.sign(_canonical(payload))
            if not isinstance(signature, bytes) or not signature:
                raise ValueError('Signer returned no signature')
            self._checkpoints.publish({'payload': payload,
                'signature': base64.b64encode(signature).decode('ascii')})
        except Exception as exc:
            raise EvidenceUnavailable('Independent audit checkpoint publish failed') from exc
        anchor = self._anchor(context)
        if anchor.sequence < sequence or (anchor.sequence == sequence and
                                         anchor.head_hash != head_hash):
            raise EvidenceIntegrityError('Published audit checkpoint differs from chain')
        return anchor

    def inspect_baseline(self, context: TenantContext) -> tuple[int, str]:
        """Return checked database head for out-of-band operator attestation."""
        sequence, head, _ = self._chain(context)
        return sequence, head

    def initialize(self, context: TenantContext, *, expected_sequence: int,
                   expected_head_hash: str) -> Checkpoint:
        """Privileged, first-use enrollment after independent baseline review."""
        if (type(expected_sequence) is not int or expected_sequence < 0
                or not isinstance(expected_head_hash, str)
                or not _DIGEST.fullmatch(expected_head_hash)):
            raise ValueError('An attested baseline sequence and hash are required')
        try:
            existing = self._checkpoints.latest(context.organization_id,
                                                context.tenant_id)
        except Exception as exc:
            raise EvidenceUnavailable('Independent audit checkpoint store unavailable') from exc
        if existing is not None:
            self.verify(context)
            return self._anchor(context)
        sequence, head, _ = self._chain(context)
        if (sequence, head) != (expected_sequence, expected_head_hash):
            raise EvidenceIntegrityError('Audit baseline differs from operator attestation')
        return self._publish(context, sequence, head)

    def verify(self, context: TenantContext) -> AuditVerification:
        anchor = self._anchor(context)
        sequence, head, hashes = self._chain(context)
        anchored_hash = GENESIS if anchor.sequence == 0 else (
            hashes[anchor.sequence - 1] if anchor.sequence <= sequence else None)
        if anchored_hash != anchor.head_hash:
            raise EvidenceIntegrityError('Audit database is stale or differs from signed prefix')
        return AuditVerification(sequence, anchor.sequence, head)

    def checkpoint(self, context: TenantContext) -> Checkpoint:
        checked = self.verify(context)
        if checked.unanchored_count == 0:
            return self._anchor(context)
        try:
            return self._publish(context, checked.head_sequence, checked.head_hash)
        except EvidenceUnavailable:
            refreshed = self.verify(context)
            if refreshed.unanchored_count == 0:
                return self._anchor(context)
            raise
