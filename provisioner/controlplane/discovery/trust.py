"""Signed discovery provenance with live, independently administered trust.

The ingestion service pins an offline authority's Ed25519 public key. That
authority signs a bounded policy enrolling exact-scope campaign issuers and
collectors. Replacing the policy revokes an enrollment without restarting the
service; every verification reopens and verifies it. Private signing keys are
never loaded here. A separate credential authority must confirm the collector's
read-only credential at each use; a signature alone cannot prove native RBAC.

This module grants no job, ownership, execution, or native mutation capability.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import stat
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from threading import RLock
from typing import Protocol

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from provisioner.controlplane.authority.model import PlanScope

from .model import (DiscoveryCampaignAuthorization, DiscoveryResult, _id,
                    _json, _scope, _scope_json, _unique_pairs, _utc)
from .persistence import VerificationEvidence


class DiscoveryTrustDenied(ValueError):
    """Independent discovery authority or current provenance was not verified."""


def _decode(value: str, size: int) -> bytes:
    try:
        if not isinstance(value, str) or len(value) > 256:
            raise ValueError('Invalid encoded signature or public key')
        result = base64.b64decode(value, validate=True)
        if len(result) != size or base64.b64encode(result).decode('ascii') != value:
            raise ValueError('Noncanonical signature or public key')
        return result
    except (ValueError, TypeError) as exc:
        raise DiscoveryTrustDenied('Invalid encoded signature or public key') from exc


@dataclass(frozen=True, slots=True)
class DiscoverySignature:
    key_id: str
    signature: str

    def __post_init__(self) -> None:
        if not _id(self.key_id):
            raise DiscoveryTrustDenied('An exact enrolled signing key is required')
        _decode(self.signature, 64)


def campaign_signing_bytes(campaign: DiscoveryCampaignAuthorization,
                           environment_id: str) -> bytes:
    if not isinstance(campaign, DiscoveryCampaignAuthorization) or not _id(environment_id):
        raise DiscoveryTrustDenied('Exact campaign and environment are required')
    return _json({'format': 'hosting-discovery-campaign-signature/1',
                  'environmentId': environment_id,
                  'authorizationDigest': campaign.digest()}).encode('ascii')


def result_signing_bytes(campaign: DiscoveryCampaignAuthorization,
                         result: DiscoveryResult, environment_id: str) -> bytes:
    campaign_signing_bytes(campaign, environment_id)
    if (not isinstance(result, DiscoveryResult)
            or result.campaign_id != campaign.campaign_id
            or result.scope != campaign.scope
            or result.authorization_digest != campaign.digest()):
        raise DiscoveryTrustDenied('Result does not bind the exact campaign')
    return _json({'format': 'hosting-discovery-result-signature/1',
                  'environmentId': environment_id,
                  'authorizationDigest': campaign.digest(),
                  'resultDigest': result.digest}).encode('ascii')


@dataclass(frozen=True, slots=True)
class DiscoveryKeyEnrollment:
    """An authority-approved key for one role and exact environment selector."""

    key_id: str
    subject_id: str
    role: str
    public_key: str
    environment_id: str
    scope: PlanScope
    not_before: datetime
    expires_at: datetime
    credential_reference: str | None = None
    revoked_at: datetime | None = None

    def __post_init__(self) -> None:
        if (not all(_id(value) for value in (self.key_id, self.subject_id,
                                            self.environment_id))
                or self.role not in ('issuer', 'collector') or not _scope(self.scope)
                or not _utc(self.not_before) or not _utc(self.expires_at)
                or not self.not_before < self.expires_at
                or self.revoked_at is not None and not _utc(self.revoked_at)
                or self.role == 'issuer' and self.credential_reference is not None
                or self.role == 'collector' and not _id(self.credential_reference)):
            raise DiscoveryTrustDenied('Invalid exact-scope key enrollment')
        _decode(self.public_key, 32)

    def as_dict(self) -> dict:
        return {'keyId': self.key_id, 'subjectId': self.subject_id,
                'role': self.role, 'publicKey': self.public_key,
                'environmentId': self.environment_id, 'scope': _scope_json(self.scope),
                'notBefore': self.not_before.isoformat(),
                'expiresAt': self.expires_at.isoformat(),
                'credentialReference': self.credential_reference,
                'revokedAt': self.revoked_at.isoformat() if self.revoked_at else None}


@dataclass(frozen=True, slots=True)
class DiscoveryTrustPolicy:
    revision: int
    issued_at: datetime
    expires_at: datetime
    enrollments: tuple[DiscoveryKeyEnrollment, ...]

    def __post_init__(self) -> None:
        if (type(self.revision) is not int or not 1 <= self.revision <= 2**63 - 1
                or not _utc(self.issued_at) or not _utc(self.expires_at)
                or not timedelta(0) < self.expires_at - self.issued_at <= timedelta(hours=24)
                or not isinstance(self.enrollments, tuple) or len(self.enrollments) > 1000
                or any(not isinstance(item, DiscoveryKeyEnrollment)
                       for item in self.enrollments)
                or len({item.key_id for item in self.enrollments}) != len(self.enrollments)):
            raise DiscoveryTrustDenied('Invalid bounded discovery trust policy')
        # An issuer key must never double as a collector result key.
        issuers = {item.public_key for item in self.enrollments if item.role == 'issuer'}
        collectors = {item.public_key for item in self.enrollments if item.role == 'collector'}
        if issuers & collectors:
            raise DiscoveryTrustDenied('Campaign and collector signing keys must be separate')

    def as_dict(self) -> dict:
        return {'format': 'hosting-discovery-trust-policy/1', 'revision': self.revision,
                'issuedAt': self.issued_at.isoformat(),
                'expiresAt': self.expires_at.isoformat(),
                'enrollments': [item.as_dict() for item in self.enrollments]}


def trust_policy_signing_bytes(policy: DiscoveryTrustPolicy) -> bytes:
    if not isinstance(policy, DiscoveryTrustPolicy):
        raise DiscoveryTrustDenied('An immutable trust policy is required')
    return _json(policy.as_dict()).encode('ascii')


def _keys(value: object, expected: set[str]) -> dict:
    if not isinstance(value, dict) or value.keys() != expected:
        raise DiscoveryTrustDenied('Unexpected discovery trust policy fields')
    return value


def _time(value: object) -> datetime:
    if not isinstance(value, str):
        raise DiscoveryTrustDenied('A UTC policy timestamp is required')
    parsed = datetime.fromisoformat(value)
    if not _utc(parsed):
        raise DiscoveryTrustDenied('A UTC policy timestamp is required')
    return parsed


def _parse_policy(value: object) -> DiscoveryTrustPolicy:
    body = _keys(value, {'format', 'revision', 'issuedAt', 'expiresAt', 'enrollments'})
    if body['format'] != 'hosting-discovery-trust-policy/1' or not isinstance(body['enrollments'], list):
        raise DiscoveryTrustDenied('Unsupported discovery trust policy')
    if len(body['enrollments']) > 1000:
        raise DiscoveryTrustDenied('Oversized discovery trust policy')
    enrollments = []
    for raw in body['enrollments']:
        entry = _keys(raw, {'keyId', 'subjectId', 'role', 'publicKey', 'environmentId',
                            'scope', 'notBefore', 'expiresAt', 'credentialReference', 'revokedAt'})
        scope = _keys(entry['scope'], {'organizationId', 'tenantId', 'locationId',
                                      'securityDomainId', 'endpointId', 'nativeScopeId',
                                      'platformFamily'})
        enrollments.append(DiscoveryKeyEnrollment(
            entry['keyId'], entry['subjectId'], entry['role'], entry['publicKey'],
            entry['environmentId'], PlanScope(scope['organizationId'], scope['tenantId'],
                scope['locationId'], scope['securityDomainId'], scope['endpointId'],
                scope['nativeScopeId'], scope['platformFamily']),
            _time(entry['notBefore']), _time(entry['expiresAt']),
            entry['credentialReference'],
            _time(entry['revokedAt']) if entry['revokedAt'] is not None else None))
    return DiscoveryTrustPolicy(body['revision'], _time(body['issuedAt']),
                                _time(body['expiresAt']), tuple(enrollments))


class DiscoveryTrustStore(Protocol):
    def current_policy(self, checked_at: datetime) -> DiscoveryTrustPolicy:
        """Consult the live authority and refuse outages, expiry and rollback."""


class SignedFileDiscoveryTrustStore:
    """Verify an operator-owned policy at every use, with no stale fallback.

    The file is ``{"policy": policy.as_dict(), "signature": base64_signature}``.
    Publish revisions atomically after offline signing; do not place private
    authority keys on the ingest host. ``minimum_revision`` is an independently
    configured deployment floor and must advance across restarts. The process
    also refuses any revision rollback or content change at the same revision.
    Signature validation authenticates policy even if a parent directory can
    replace the file; bounded validity and the revision floor prevent accepting
    unbounded historical policy. External release controls must preserve that
    floor when restoring the service.
    """

    def __init__(self, path: str | Path, *, authority_public_key: Ed25519PublicKey,
                 minimum_revision: int):
        if (not isinstance(authority_public_key, Ed25519PublicKey)
                or type(minimum_revision) is not int or minimum_revision < 1):
            raise ValueError('Pinned authority key and positive revision floor are required')
        self._path = Path(path)
        self._authority = authority_public_key
        self._revision = minimum_revision
        self._digest: str | None = None
        self._lock = RLock()

    def current_policy(self, checked_at: datetime) -> DiscoveryTrustPolicy:
        if not _utc(checked_at):
            raise DiscoveryTrustDenied('A trusted UTC verification clock is required')
        with self._lock:
            try:
                flags = (os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
                descriptor = os.open(self._path, flags)
                try:
                    info = os.fstat(descriptor)
                    if (not stat.S_ISREG(info.st_mode)
                            or info.st_uid not in (0, os.geteuid())
                            or info.st_mode & 0o022 or info.st_size > 1048576):
                        raise DiscoveryTrustDenied('Discovery trust file is not protected')
                    with os.fdopen(descriptor, 'rb', closefd=False) as stream:
                        raw = stream.read(1048577)
                finally:
                    os.close(descriptor)
                if len(raw) > 1048576:
                    raise DiscoveryTrustDenied('Oversized discovery trust policy')
                document = _keys(json.loads(raw, object_pairs_hook=_unique_pairs),
                                 {'policy', 'signature'})
                policy = _parse_policy(document['policy'])
                payload = trust_policy_signing_bytes(policy)
                # Require precisely the canonical semantic policy that was signed.
                if _json(document['policy']).encode('ascii') != payload:
                    raise DiscoveryTrustDenied('Noncanonical discovery trust policy')
                self._authority.verify(_decode(document['signature'], 64), payload)
                digest = hashlib.sha256(payload).hexdigest()
                if (not policy.issued_at <= checked_at < policy.expires_at
                        or policy.revision < self._revision
                        or policy.revision == self._revision
                        and self._digest is not None and self._digest != digest):
                    raise DiscoveryTrustDenied('Expired, equivocated or rolled-back trust policy')
                self._revision, self._digest = policy.revision, digest
                return policy
            except (OSError, UnicodeError, ValueError, TypeError, KeyError,
                    OverflowError, RecursionError, InvalidSignature) as exc:
                raise DiscoveryTrustDenied('Live discovery trust policy is unavailable or invalid') from exc


@dataclass(frozen=True, slots=True)
class ReadOnlyCredentialEvidence:
    """Fresh result from the independently configured native credential authority.

    ``policy_digest`` identifies the checked native RBAC/credential policy. The
    authority must reject disabled credentials, write-capable permissions and
    outages rather than returning a prior decision. No secret is returned.
    """

    credential_reference: str
    collector_id: str
    environment_id: str
    scope: PlanScope
    checked_at: datetime
    expires_at: datetime
    policy_digest: str

    def __post_init__(self) -> None:
        if (not all(_id(value) for value in (self.credential_reference,
                                            self.collector_id, self.environment_id))
                or not _scope(self.scope) or not _utc(self.checked_at)
                or not _utc(self.expires_at) or not self.checked_at < self.expires_at
                or not isinstance(self.policy_digest, str) or len(self.policy_digest) != 64
                or any(c not in '0123456789abcdef' for c in self.policy_digest)):
            raise DiscoveryTrustDenied('Invalid independently verified read credential')


class DiscoveryCredentialAuthority(Protocol):
    def verify_read_only(self, credential_reference: str, *, collector_id: str,
                         environment_id: str, scope: PlanScope,
                         checked_at: datetime) -> ReadOnlyCredentialEvidence:
        """Check live enrollment, native read-only restrictions and revocation."""


class SignedDiscoveryIngestVerifier:
    """Factory for request-bound proofs; safe to share between HTTP requests."""

    def __init__(self, trust_store: DiscoveryTrustStore,
                 credential_authority: DiscoveryCredentialAuthority):
        if (not callable(getattr(trust_store, 'current_policy', None))
                or not callable(getattr(credential_authority, 'verify_read_only', None))):
            raise ValueError('Live discovery trust and credential authorities are required')
        self._trust = trust_store
        self._credentials = credential_authority

    def bind(self, campaign_signature: DiscoverySignature,
             result_signature: DiscoverySignature | None = None) -> BoundDiscoveryIngestVerifier:
        if (not isinstance(campaign_signature, DiscoverySignature)
                or result_signature is not None and not isinstance(result_signature, DiscoverySignature)):
            raise DiscoveryTrustDenied('Signed campaign and collector proof are required')
        return BoundDiscoveryIngestVerifier(self, campaign_signature, result_signature)

    def _verify(self, campaign: DiscoveryCampaignAuthorization,
                result: DiscoveryResult | None, environment_id: str,
                checked_at: datetime, campaign_signature: DiscoverySignature,
                result_signature: DiscoverySignature | None) -> VerificationEvidence:
        campaign_bytes = campaign_signing_bytes(campaign, environment_id)
        if not _utc(checked_at) or not campaign.issued_at <= checked_at < campaign.expires_at:
            raise DiscoveryTrustDenied('Campaign is not currently valid')
        policy = self._trust.current_policy(checked_at)
        if (not isinstance(policy, DiscoveryTrustPolicy)
                or not policy.issued_at <= checked_at < policy.expires_at):
            raise DiscoveryTrustDenied('Current discovery trust policy is required')
        def active(entry: DiscoveryKeyEnrollment, role: str) -> bool:
            return (entry.role == role and entry.environment_id == environment_id
                    and entry.scope == campaign.scope
                    and entry.not_before <= campaign.issued_at
                    and campaign.expires_at <= entry.expires_at
                    and (entry.revoked_at is None or checked_at < entry.revoked_at))
        issuer = next((entry for entry in policy.enrollments
                       if entry.key_id == campaign_signature.key_id and active(entry, 'issuer')), None)
        collectors = [entry for entry in policy.enrollments
                      if entry.subject_id == campaign.collector_id and active(entry, 'collector')]
        if issuer is None or not collectors:
            raise DiscoveryTrustDenied('Issuer or collector enrollment is inactive or outside scope')
        if result is not None:
            if not isinstance(result_signature, DiscoverySignature):
                raise DiscoveryTrustDenied('A collector result signature is required')
            collectors = [entry for entry in collectors if entry.key_id == result_signature.key_id]
        # Registration may have several current rotated keys, but their credential
        # binding must agree so that issuance cannot select a more privileged one.
        if not collectors or len({entry.credential_reference for entry in collectors}) != 1:
            raise DiscoveryTrustDenied('Exact enrolled collector credential is unavailable')
        collector = collectors[0]
        try:
            Ed25519PublicKey.from_public_bytes(_decode(issuer.public_key, 32)).verify(
                _decode(campaign_signature.signature, 64), campaign_bytes)
            if result is not None:
                rebuilt = DiscoveryResult(result.campaign_id, result.authorization_digest,
                    result.scope, result.captured_at, result.completeness, result.objects,
                    result.collection_errors, result.missing_privileges)
                if (rebuilt.digest != result.digest
                        or not campaign.issued_at <= result.captured_at <= checked_at
                        or len(result.objects) > campaign.max_objects
                        or any(obj.identity.resource_kind not in campaign.allowed_kinds
                               for obj in result.objects)):
                    raise DiscoveryTrustDenied('Result exceeds the campaign time or inventory bounds')
                Ed25519PublicKey.from_public_bytes(_decode(collector.public_key, 32)).verify(
                    _decode(result_signature.signature, 64),
                    result_signing_bytes(campaign, result, environment_id))
        except InvalidSignature as exc:
            raise DiscoveryTrustDenied('Discovery campaign or result signature is invalid') from exc
        credential = self._credentials.verify_read_only(
            collector.credential_reference, collector_id=collector.subject_id,
            environment_id=environment_id, scope=campaign.scope, checked_at=checked_at)
        if (not isinstance(credential, ReadOnlyCredentialEvidence)
                or credential.credential_reference != collector.credential_reference
                or credential.collector_id != collector.subject_id
                or credential.environment_id != environment_id
                or credential.scope != campaign.scope or credential.checked_at != checked_at
                or credential.expires_at < campaign.expires_at):
            raise DiscoveryTrustDenied('Live read credential does not bind this exact campaign')
        reference = hashlib.sha256(_json({
            'policyDigest': hashlib.sha256(trust_policy_signing_bytes(policy)).hexdigest(),
            'policyRevision': policy.revision, 'issuerKeyId': issuer.key_id,
            'campaignSignature': campaign_signature.signature,
            'collectorKeyId': collector.key_id,
            'resultSignature': result_signature.signature if result is not None else None,
            'credentialPolicyDigest': credential.policy_digest,
            'checkedAt': checked_at.isoformat(),
        }).encode('ascii')).hexdigest()
        return VerificationEvidence(campaign.digest(), result.digest if result else None,
                                    collector.subject_id if result else issuer.subject_id,
                                    'discovery-signature-v1:' + reference)


@dataclass(frozen=True, slots=True)
class BoundDiscoveryIngestVerifier:
    """Immutable request evidence implementing DiscoveryRepository's verifier."""

    verifier: SignedDiscoveryIngestVerifier
    campaign_signature: DiscoverySignature
    result_signature: DiscoverySignature | None = None

    def verify_campaign(self, campaign: DiscoveryCampaignAuthorization,
                        environment_id: str, checked_at: datetime) -> VerificationEvidence:
        return self.verifier._verify(campaign, None, environment_id, checked_at,
                                     self.campaign_signature, None)

    def verify_result(self, campaign: DiscoveryCampaignAuthorization,
                      result: DiscoveryResult, environment_id: str,
                      checked_at: datetime) -> VerificationEvidence:
        return self.verifier._verify(campaign, result, environment_id, checked_at,
                                     self.campaign_signature, self.result_signature)
