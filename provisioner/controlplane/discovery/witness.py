"""Fresh native IAM/RBAC observations signed by an independent witness.

The witness operator inspects the native role and credential lifecycle, then
publishes this bounded document. The ingest service verifies the independent
signature; it does not infer read-only permission from a collector's claim.
This is an observation transport, not an implementation of a vendor IAM probe.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from threading import RLock

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from provisioner.controlplane.authority.model import PlanScope

from .model import _id, _json, _scope, _scope_json, _unique_pairs, _utc
from .trust import (DiscoveryTrustDenied, ReadOnlyCredentialEvidence, _decode,
                    _keys, _time)

MAX_WITNESS_AGE = timedelta(minutes=5)


@dataclass(frozen=True, slots=True)
class NativeReadCredentialWitness:
    credential_reference: str
    collector_id: str
    environment_id: str
    scope: PlanScope
    observation_reference: str
    policy_digest: str
    observed_at: datetime
    credential_expires_at: datetime
    read_only: bool
    revoked_at: datetime | None = None

    def __post_init__(self) -> None:
        if (not all(_id(value) for value in (self.credential_reference, self.collector_id,
                self.environment_id, self.observation_reference))
                or not _scope(self.scope) or not _utc(self.observed_at)
                or not _utc(self.credential_expires_at)
                or not self.observed_at < self.credential_expires_at
                or type(self.read_only) is not bool
                or self.revoked_at is not None and not _utc(self.revoked_at)
                or not isinstance(self.policy_digest, str) or len(self.policy_digest) != 64
                or any(c not in '0123456789abcdef' for c in self.policy_digest)):
            raise DiscoveryTrustDenied('Invalid native IAM/RBAC credential witness')

    def as_dict(self) -> dict:
        return {'credentialReference': self.credential_reference,
                'collectorId': self.collector_id, 'environmentId': self.environment_id,
                'scope': _scope_json(self.scope), 'observationReference': self.observation_reference,
                'policyDigest': self.policy_digest, 'observedAt': self.observed_at.isoformat(),
                'credentialExpiresAt': self.credential_expires_at.isoformat(),
                'readOnly': self.read_only,
                'revokedAt': self.revoked_at.isoformat() if self.revoked_at else None}


@dataclass(frozen=True, slots=True)
class NativeCredentialWitnessPolicy:
    revision: int
    issued_at: datetime
    expires_at: datetime
    witnesses: tuple[NativeReadCredentialWitness, ...]

    def __post_init__(self) -> None:
        if (type(self.revision) is not int or not 1 <= self.revision <= 2**63 - 1
                or not _utc(self.issued_at) or not _utc(self.expires_at)
                or not timedelta(0) < self.expires_at - self.issued_at <= MAX_WITNESS_AGE
                or not isinstance(self.witnesses, tuple) or len(self.witnesses) > 1000
                or any(not isinstance(item, NativeReadCredentialWitness) for item in self.witnesses)
                or len({(w.credential_reference, w.collector_id, w.environment_id, w.scope)
                        for w in self.witnesses}) != len(self.witnesses)):
            raise DiscoveryTrustDenied('Invalid bounded native credential witness policy')

    def as_dict(self) -> dict:
        return {'format': 'hosting-discovery-native-credential-witness/1',
                'revision': self.revision, 'issuedAt': self.issued_at.isoformat(),
                'expiresAt': self.expires_at.isoformat(),
                'witnesses': [w.as_dict() for w in self.witnesses]}


def credential_witness_signing_bytes(policy: NativeCredentialWitnessPolicy) -> bytes:
    if not isinstance(policy, NativeCredentialWitnessPolicy):
        raise DiscoveryTrustDenied('An immutable native credential witness policy is required')
    return _json(policy.as_dict()).encode('ascii')


def _parse(body: object) -> NativeCredentialWitnessPolicy:
    body = _keys(body, {'format', 'revision', 'issuedAt', 'expiresAt', 'witnesses'})
    if (body['format'] != 'hosting-discovery-native-credential-witness/1'
            or not isinstance(body['witnesses'], list) or len(body['witnesses']) > 1000):
        raise DiscoveryTrustDenied('Invalid native credential witness document')
    witnesses = []
    for raw in body['witnesses']:
        w = _keys(raw, {'credentialReference', 'collectorId', 'environmentId', 'scope',
            'observationReference', 'policyDigest', 'observedAt', 'credentialExpiresAt',
            'readOnly', 'revokedAt'})
        scope = _keys(w['scope'], {'organizationId', 'tenantId', 'locationId',
            'securityDomainId', 'endpointId', 'nativeScopeId', 'platformFamily'})
        witnesses.append(NativeReadCredentialWitness(w['credentialReference'], w['collectorId'],
            w['environmentId'], PlanScope.from_record(scope), w['observationReference'],
            w['policyDigest'], _time(w['observedAt']), _time(w['credentialExpiresAt']),
            w['readOnly'], _time(w['revokedAt']) if w['revokedAt'] is not None else None))
    return NativeCredentialWitnessPolicy(body['revision'], _time(body['issuedAt']),
                                         _time(body['expiresAt']), tuple(witnesses))


class SignedFileDiscoveryCredentialAuthority:
    """No cached fallback: every check reloads an independently signed witness.

    The root key must differ from the discovery trust-policy signing key. The
    runtime enforces that separation. Revisions and bounded freshness reject
    stale/rolled-back witness files. Advance minimum_revision across restarts.
    Revocation is effective on the next verified use after witness publication;
    operators must publish immediately when native roles or leases change.
    """

    def __init__(self, path: str | Path, *, authority_public_key: Ed25519PublicKey,
                 minimum_revision: int):
        if (not isinstance(authority_public_key, Ed25519PublicKey)
                or type(minimum_revision) is not int or minimum_revision < 1):
            raise ValueError('An independent pinned witness key and revision floor are required')
        self._path, self._authority = Path(path), authority_public_key
        self._revision, self._digest = minimum_revision, None
        self._lock = RLock()

    def current_policy(self, checked_at: datetime) -> NativeCredentialWitnessPolicy:
        if not _utc(checked_at):
            raise DiscoveryTrustDenied('A trusted UTC verification clock is required')
        with self._lock:
            try:
                descriptor = os.open(self._path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
                try:
                    info = os.fstat(descriptor)
                    if (not stat.S_ISREG(info.st_mode) or info.st_uid not in (0, os.geteuid())
                            or info.st_mode & 0o022 or info.st_size > 1048576):
                        raise DiscoveryTrustDenied('Native witness file is not protected')
                    with os.fdopen(descriptor, 'rb', closefd=False) as stream:
                        raw = stream.read(1048577)
                finally:
                    os.close(descriptor)
                if len(raw) > 1048576:
                    raise DiscoveryTrustDenied('Native witness document is oversized')
                document = _keys(json.loads(raw, object_pairs_hook=_unique_pairs), {'policy', 'signature'})
                policy = _parse(document['policy'])
                payload = credential_witness_signing_bytes(policy)
                if _json(document['policy']).encode('ascii') != payload:
                    raise DiscoveryTrustDenied('Native witness document is noncanonical')
                self._authority.verify(_decode(document['signature'], 64), payload)
                digest = hashlib.sha256(payload).hexdigest()
                if (not policy.issued_at <= checked_at < policy.expires_at
                        or policy.revision < self._revision
                        or policy.revision == self._revision
                        and self._digest is not None and self._digest != digest):
                    raise DiscoveryTrustDenied('Native witness document is stale or rolled back')
                self._revision, self._digest = policy.revision, digest
                return policy
            except (OSError, ValueError, TypeError, UnicodeError, KeyError,
                    RecursionError, OverflowError, InvalidSignature) as exc:
                raise DiscoveryTrustDenied('Independent native credential witness unavailable') from exc

    def verify_read_only(self, credential_reference: str, *, collector_id: str,
                         environment_id: str, scope: PlanScope,
                         checked_at: datetime) -> ReadOnlyCredentialEvidence:
        policy = self.current_policy(checked_at)
        witness = next((w for w in policy.witnesses if
            (w.credential_reference, w.collector_id, w.environment_id, w.scope) ==
            (credential_reference, collector_id, environment_id, scope)), None)
        if (witness is None or not witness.read_only
                or not witness.observed_at <= checked_at < witness.credential_expires_at
                or checked_at - witness.observed_at >= MAX_WITNESS_AGE
                or witness.revoked_at is not None and checked_at >= witness.revoked_at):
            raise DiscoveryTrustDenied('Native credential is not currently witnessed read-only')
        # Include the independently observed evidence reference and signature
        # policy revision in custody, without exposing any native secret.
        evidence_digest = hashlib.sha256(_json({
            'witness': witness.as_dict(), 'policyRevision': policy.revision,
            'policyDigest': hashlib.sha256(credential_witness_signing_bytes(policy)).hexdigest(),
        }).encode('ascii')).hexdigest()
        return ReadOnlyCredentialEvidence(credential_reference, collector_id,
            environment_id, scope, checked_at, witness.credential_expires_at, evidence_digest)
