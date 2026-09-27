"""Bounded JSON evidence and independently signed per-tenant high-water marks.

The repository is server-internal: a verified principal and policy service must
authorize calls before constructing TenantContext. A database role cannot be a
checkpoint signer, and its signing credential must not be in PostgreSQL. Each
read verifies bytes, chain, and external signature before releasing evidence.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Protocol

from provisioner.controlplane.persistence import TenantContext

GENESIS = '0' * 64
_KEY = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$')
_DIGEST = re.compile(r'^[0-9a-f]{64}$')
_SENSITIVE = re.compile(
    r'password|secret|credential|token|privatekey|accesskey|apikey|authorization|cookie|dsn',
    re.IGNORECASE)
_URL = re.compile(r'(?i)\b[a-z][a-z0-9+.-]*://|\b(?:bearer|basic)\s+[a-z0-9+/=-]+')
KINDS = frozenset({'OBSERVATION', 'NATIVE_RECEIPT', 'TRANSFER_MANIFEST',
                   'VERIFICATION_RESULT', 'RECOVERY_DECISION'})


class EvidenceIntegrityError(RuntimeError):
    """A stored byte, hash chain, or independent checkpoint does not agree."""


class EvidenceUnavailable(RuntimeError):
    """Required external storage, verifier or signing service is unavailable."""


class EvidenceConflict(ValueError):
    """An event key was reused for different content."""


class ArtifactStore(Protocol):
    def put(self, digest: str, content: bytes) -> None: ...
    def get(self, digest: str) -> bytes: ...


class CheckpointStore(Protocol):
    def latest(self, organization_id: str, tenant_id: str) -> dict | None: ...
    def publish(self, envelope: dict) -> None: ...


class CheckpointSigner(Protocol):
    @property
    def key_id(self) -> str: ...
    def sign(self, payload: bytes) -> bytes: ...


class CheckpointVerifier(Protocol):
    def verify(self, key_id: str, payload: bytes, signature: bytes) -> None:
        """Raise on unknown, revoked or invalid signing identity/signature."""


@dataclass(frozen=True)
class EvidenceEntry:
    sequence: int
    event_key: str
    evidence_kind: str
    subject_id: str
    blob_digest: str
    blob_size: int
    previous_hash: str
    entry_hash: str
    recorded_at: datetime


@dataclass(frozen=True)
class Checkpoint:
    organization_id: str
    tenant_id: str
    sequence: int
    head_hash: str
    key_id: str


@dataclass(frozen=True)
class Verification:
    head_sequence: int
    anchored_sequence: int
    head_hash: str

    @property
    def unanchored_count(self) -> int:
        return self.head_sequence - self.anchored_sequence


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def _validated_artifact(value: dict) -> bytes:
    if not isinstance(value, dict):
        raise ValueError('Evidence artifact must be a JSON object')

    def inspect(item, depth=0):
        if depth > 20:
            raise ValueError('Evidence artifact nesting limit exceeded')
        if isinstance(item, dict):
            for key, child in item.items():
                if not isinstance(key, str) or _SENSITIVE.search(re.sub(r'[^a-zA-Z]', '', key)):
                    raise ValueError('Evidence contains a forbidden credential field')
                inspect(child, depth + 1)
        elif isinstance(item, list):
            for child in item:
                inspect(child, depth + 1)
        elif isinstance(item, str) and _URL.search(item):
            raise ValueError('Evidence cannot embed URLs or authorization values')
        elif item is not None and not isinstance(item, (str, int, float, bool)):
            raise ValueError('Evidence artifact contains a non-JSON value')

    inspect(value)
    try:
        encoded = _canonical(value)
    except (ValueError, TypeError) as exc:
        raise ValueError('Evidence artifact must be finite JSON') from exc
    if not 2 <= len(encoded) <= 1048576:
        raise ValueError('Evidence artifact exceeds the 1 MiB receipt limit')
    return encoded


def _entry_hash(context: TenantContext, entry: EvidenceEntry) -> str:
    return hashlib.sha256(_canonical({
        'v': 1, 'organizationId': context.organization_id,
        'tenantId': context.tenant_id, 'sequence': entry.sequence,
        'eventKey': entry.event_key, 'kind': entry.evidence_kind,
        'subjectId': entry.subject_id, 'blobDigest': entry.blob_digest,
        'blobSize': entry.blob_size, 'previousHash': entry.previous_hash,
        'recordedAt': entry.recorded_at.astimezone(timezone.utc).isoformat(timespec='microseconds'),
    })).hexdigest()


def _entry(row) -> EvidenceEntry:
    return EvidenceEntry(*row)


class EvidenceRepository:
    def __init__(self, connection_factory: Callable, artifacts: ArtifactStore,
                 checkpoints: CheckpointStore, signer: CheckpointSigner,
                 verifier: CheckpointVerifier):
        if (not callable(connection_factory) or artifacts is None or checkpoints is None
                or signer is None or verifier is None
                or not callable(getattr(signer, 'sign', None))
                or not callable(getattr(verifier, 'verify', None))):
            raise ValueError('Database, artifact, checkpoint, signer and verifier are required')
        self._connect = connection_factory
        self._artifacts = artifacts
        self._checkpoints = checkpoints
        self._signer = signer
        self._verifier = verifier

    @staticmethod
    def _tenant(cursor, context: TenantContext) -> None:
        if not isinstance(context, TenantContext):
            raise TypeError('Trusted tenant context required')
        if cursor.connection.autocommit:
            raise RuntimeError('Evidence writes and reads require a transaction')
        cursor.execute('SELECT rolsuper, rolbypassrls FROM pg_catalog.pg_roles '
                       'WHERE rolname = current_user')
        role = cursor.fetchone()
        if role is None or role[0] or role[1]:
            raise RuntimeError('Evidence runtime role must enforce PostgreSQL row security')
        cursor.execute("SELECT set_config('app.organization_id', %s, true), "
                       "set_config('app.tenant_id', %s, true)",
                       (context.organization_id, context.tenant_id))

    def _anchor(self, context: TenantContext) -> Checkpoint:
        try:
            envelope = self._checkpoints.latest(context.organization_id,
                                                context.tenant_id)
        except (ValueError, TypeError, KeyError) as exc:
            raise EvidenceIntegrityError('Independent checkpoint is malformed') from exc
        except Exception as exc:
            raise EvidenceUnavailable('Independent checkpoint store unavailable') from exc
        if envelope is None:
            raise EvidenceUnavailable('Tenant has no independently signed genesis checkpoint')
        try:
            payload = envelope['payload']
            signature = base64.b64decode(envelope['signature'], validate=True)
            expected = {'v', 'organizationId', 'tenantId', 'sequence', 'headHash', 'keyId'}
            if (set(payload) != expected or set(envelope) != {'payload', 'signature'}
                    or payload['v'] != 1
                    or payload['organizationId'] != context.organization_id
                    or payload['tenantId'] != context.tenant_id
                    or type(payload['sequence']) is not int or payload['sequence'] < 0
                    or not _DIGEST.fullmatch(payload['headHash'])
                    or not _KEY.fullmatch(payload['keyId'])):
                raise ValueError('Checkpoint scope or format mismatch')
            self._verifier.verify(payload['keyId'], _canonical(payload), signature)
            return Checkpoint(context.organization_id, context.tenant_id,
                              payload['sequence'], payload['headHash'], payload['keyId'])
        except Exception as exc:
            raise EvidenceIntegrityError('Independent checkpoint could not be verified') from exc

    def _publish(self, context: TenantContext, sequence: int, head_hash: str) -> Checkpoint:
        key_id = self._signer.key_id
        if not isinstance(key_id, str) or not _KEY.fullmatch(key_id):
            raise EvidenceUnavailable('Signing identity is not configured')
        payload = {'v': 1, 'organizationId': context.organization_id,
                   'tenantId': context.tenant_id, 'sequence': sequence,
                   'headHash': head_hash, 'keyId': key_id}
        try:
            signature = self._signer.sign(_canonical(payload))
            if not isinstance(signature, bytes) or not signature:
                raise ValueError('Signer returned no signature')
            envelope = {'payload': payload,
                        'signature': base64.b64encode(signature).decode('ascii')}
            self._checkpoints.publish(envelope)
        except Exception as exc:
            raise EvidenceUnavailable('Independent checkpoint could not be published') from exc
        anchor = self._anchor(context)
        if anchor.sequence < sequence or (anchor.sequence == sequence
                                          and anchor.head_hash != head_hash):
            raise EvidenceIntegrityError('Published checkpoint differs from signed prefix')
        return anchor

    def initialize(self, context: TenantContext) -> Checkpoint:
        """Operator-only first-use bootstrap; callers must authorize this action.

        A missing external checkpoint after initialization is never silently
        recreated. A corrupt or missing checkpoint requires incident recovery.
        """
        if not isinstance(context, TenantContext):
            raise TypeError('Trusted tenant context required')
        try:
            existing = self._checkpoints.latest(context.organization_id,
                                                context.tenant_id)
        except Exception as exc:
            raise EvidenceUnavailable('Independent checkpoint store unavailable') from exc
        if existing is not None:
            anchor = self._anchor(context)
            self.verify(context)
            return anchor
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._tenant(cursor, context)
                cursor.execute('SELECT last_sequence FROM hosting_controlplane.evidence_streams '
                               'WHERE organization_id = %s AND tenant_id = %s',
                               (context.organization_id, context.tenant_id))
                stream = cursor.fetchone()
                if stream is not None and stream[0] != 0:
                    raise EvidenceIntegrityError('Cannot bootstrap over existing evidence')
        return self._publish(context, 0, GENESIS)

    def verify(self, context: TenantContext) -> Verification:
        anchor = self._anchor(context)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._tenant(cursor, context)
                cursor.execute('SELECT last_sequence, head_hash FROM '
                               'hosting_controlplane.evidence_streams '
                               'WHERE organization_id = %s AND tenant_id = %s FOR SHARE',
                               (context.organization_id, context.tenant_id))
                stream = cursor.fetchone() or (0, GENESIS)
                cursor.execute('SELECT sequence, event_key, evidence_kind, subject_id, '
                               'blob_digest, blob_size, previous_hash, entry_hash, recorded_at '
                               'FROM hosting_controlplane.evidence_entries '
                               'WHERE organization_id = %s AND tenant_id = %s ORDER BY sequence',
                               (context.organization_id, context.tenant_id))
                rows = cursor.fetchall()
        previous = GENESIS
        anchored_hash = GENESIS if anchor.sequence == 0 else None
        for ordinal, row in enumerate(rows, 1):
            entry = _entry(row)
            if (entry.sequence != ordinal or entry.previous_hash != previous
                    or _entry_hash(context, entry) != entry.entry_hash):
                raise EvidenceIntegrityError('Evidence sequence or chain was modified')
            try:
                content = self._artifacts.get(entry.blob_digest)
                if len(content) != entry.blob_size or _validated_artifact(json.loads(content)) != content:
                    raise ValueError('Artifact bytes or JSON validation differ')
            except Exception as exc:
                raise EvidenceIntegrityError('Evidence artifact is missing or modified') from exc
            previous = entry.entry_hash
            if ordinal == anchor.sequence:
                anchored_hash = previous
        if (stream != (len(rows), previous) or anchor.sequence > len(rows)
                or anchored_hash != anchor.head_hash):
            raise EvidenceIntegrityError('Database is stale or differs from independent checkpoint')
        return Verification(len(rows), anchor.sequence, previous)

    def checkpoint(self, context: TenantContext) -> Checkpoint:
        verification = self.verify(context)
        if verification.unanchored_count == 0:
            return self._anchor(context)
        try:
            return self._publish(context, verification.head_sequence,
                                 verification.head_hash)
        except EvidenceUnavailable:
            # Another writer may have published a newer, valid prefix.
            refreshed = self.verify(context)
            if refreshed.unanchored_count == 0:
                return self._anchor(context)
            raise

    def append(self, context: TenantContext, *, event_key: str,
               evidence_kind: str, subject_id: str, artifact: dict) -> EvidenceEntry:
        if (not isinstance(context, TenantContext)
                or not isinstance(event_key, str) or not _KEY.fullmatch(event_key)
                or evidence_kind not in KINDS
                or not isinstance(subject_id, str) or not _KEY.fullmatch(subject_id)):
            raise ValueError('Invalid scoped evidence identity')
        content = _validated_artifact(artifact)
        digest = hashlib.sha256(content).hexdigest()
        # All existing evidence must be anchored before advancing this stream.
        self.checkpoint(context)
        try:
            self._artifacts.put(digest, content)
        except Exception as exc:
            raise EvidenceUnavailable('Content-addressed artifact store unavailable') from exc
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._tenant(cursor, context)
                cursor.execute('INSERT INTO hosting_controlplane.evidence_streams '
                               '(organization_id, tenant_id) VALUES (%s, %s) ON CONFLICT DO NOTHING',
                               (context.organization_id, context.tenant_id))
                cursor.execute('SELECT last_sequence, head_hash FROM '
                               'hosting_controlplane.evidence_streams '
                               'WHERE organization_id = %s AND tenant_id = %s FOR UPDATE',
                               (context.organization_id, context.tenant_id))
                sequence, previous = cursor.fetchone()
                anchor = self._anchor(context)
                if anchor.sequence > sequence:
                    raise EvidenceIntegrityError('Database is older than external checkpoint')
                if anchor.sequence < sequence:
                    raise EvidenceUnavailable('A concurrent evidence suffix needs a checkpoint')
                cursor.execute('SELECT sequence, event_key, evidence_kind, subject_id, '
                               'blob_digest, blob_size, previous_hash, entry_hash, recorded_at '
                               'FROM hosting_controlplane.evidence_entries '
                               'WHERE organization_id = %s AND tenant_id = %s AND event_key = %s',
                               (context.organization_id, context.tenant_id, event_key))
                existing = cursor.fetchone()
                if existing is not None:
                    entry = _entry(existing)
                    if (entry.evidence_kind, entry.subject_id, entry.blob_digest,
                            entry.blob_size) != (evidence_kind, subject_id, digest, len(content)):
                        raise EvidenceConflict('Evidence event key already binds different content')
                else:
                    cursor.execute('SELECT clock_timestamp()')
                    recorded_at = cursor.fetchone()[0]
                    entry = EvidenceEntry(sequence + 1, event_key, evidence_kind,
                                          subject_id, digest, len(content), previous, '', recorded_at)
                    entry = EvidenceEntry(entry.sequence, entry.event_key,
                                          entry.evidence_kind, entry.subject_id,
                                          entry.blob_digest, entry.blob_size,
                                          entry.previous_hash, _entry_hash(context, entry),
                                          recorded_at)
                    cursor.execute('INSERT INTO hosting_controlplane.evidence_entries '
                                   '(organization_id, tenant_id, sequence, event_key, '
                                   'evidence_kind, subject_id, blob_digest, blob_size, '
                                   'previous_hash, entry_hash, recorded_at) VALUES '
                                   '(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                                   (context.organization_id, context.tenant_id,
                                    entry.sequence, entry.event_key, entry.evidence_kind,
                                    entry.subject_id, entry.blob_digest, entry.blob_size,
                                    entry.previous_hash, entry.entry_hash, entry.recorded_at))
                    cursor.execute('UPDATE hosting_controlplane.evidence_streams '
                                   'SET last_sequence = %s, head_hash = %s '
                                   'WHERE organization_id = %s AND tenant_id = %s',
                                   (entry.sequence, entry.entry_hash,
                                    context.organization_id, context.tenant_id))
        # A failed external publish leaves a durable, unanchored suffix. The
        # caller receives an error and can retry the same event_key; a later
        # checkpoint must anchor it before another append is accepted.
        self.checkpoint(context)
        return entry

    def get(self, context: TenantContext, event_key: str) -> tuple[EvidenceEntry, dict] | None:
        if not isinstance(event_key, str) or not _KEY.fullmatch(event_key):
            raise ValueError('Invalid evidence event key')
        self.verify(context)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._tenant(cursor, context)
                cursor.execute('SELECT sequence, event_key, evidence_kind, subject_id, '
                               'blob_digest, blob_size, previous_hash, entry_hash, recorded_at '
                               'FROM hosting_controlplane.evidence_entries '
                               'WHERE organization_id = %s AND tenant_id = %s AND event_key = %s',
                               (context.organization_id, context.tenant_id, event_key))
                row = cursor.fetchone()
        if row is None:
            return None
        entry = _entry(row)
        if entry.sequence > self._anchor(context).sequence:
            raise EvidenceUnavailable('Evidence has not reached an independent checkpoint')
        try:
            return entry, json.loads(self._artifacts.get(entry.blob_digest))
        except Exception as exc:
            raise EvidenceIntegrityError('Evidence artifact cannot be read') from exc
