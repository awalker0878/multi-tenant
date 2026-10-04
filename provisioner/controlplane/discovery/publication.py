"""Original collector signatures and create-only custody for discovery publication.

This is site-side composition, not campaign issuance, native RBAC qualification
or an alternate inventory writer. The existing ingest service remains the only
publication authority. Native credentials never enter these signed submissions.
"""
from __future__ import annotations

import base64
import hashlib
import os
import stat
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from uuid import uuid4

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from provisioner.controlplane.evidence.filesystem import FileArtifactStore, _atomic_new
from provisioner.controlplane.persistence.store import TenantContext

from .ingest import MAX_BODY, _campaign, _result, _signature, campaign_document, result_document
from .model import DiscoveryCampaignAuthorization, DiscoveryResult, _id, _json, _object_json, _utc, assemble_discovery_result
from .native_credentials import decode_json, read_protected
from .trust import DiscoverySignature, SignedDiscoveryIngestVerifier, _keys, result_signing_bytes


class DiscoveryPublicationHeld(RuntimeError):
    """Publication was held; messages must not contain inventory or secret data."""


@dataclass(frozen=True, slots=True)
class DiscoverySubmission:
    """Immutable canonical wire bytes; signatures still need current verification."""

    environment_id: str
    campaign: DiscoveryCampaignAuthorization
    campaign_signature: DiscoverySignature
    result: DiscoveryResult = field(repr=False)
    result_signature: DiscoverySignature
    body: bytes = field(init=False, repr=False)
    digest: str = field(init=False)

    def __post_init__(self):
        if (not _id(self.environment_id) or not isinstance(self.campaign, DiscoveryCampaignAuthorization)
                or not isinstance(self.campaign_signature, DiscoverySignature)
                or not isinstance(self.result_signature, DiscoverySignature)):
            raise ValueError('An exact signed discovery submission is required')
        result_signing_bytes(self.campaign, self.result, self.environment_id)
        # Refuse oversized aggregate content before duplicating the complete
        # object tree into its wire-document representation.
        object_bytes = 0
        for obj in self.result.objects:
            object_bytes += len(_json(_object_json(obj)))
            if object_bytes > MAX_BODY:
                raise ValueError('Signed discovery aggregate exceeds the ingest limit')
        result_body = result_document(self.result)
        canonical_result = _result(result_body)
        if canonical_result.digest != self.result.digest:
            raise ValueError('Canonical result changed the signed observation digest')
        # The existing wire contract sorts the object/fact sets. Retain that
        # representation, not incidental adapter iteration order. Values inside
        # facts (including device-order arrays) are never reordered.
        object.__setattr__(self, 'result', canonical_result)
        document = self.campaign_document()
        document.update(result=result_body,
                        resultSignature=self.signature_document(self.result_signature))
        body = _json(document).encode('ascii')
        if not 0 < len(body) <= MAX_BODY:
            raise ValueError('Signed discovery aggregate exceeds the ingest limit')
        object.__setattr__(self, 'body', body)
        object.__setattr__(self, 'digest', hashlib.sha256(body).hexdigest())

    @staticmethod
    def signature_document(signature: DiscoverySignature) -> dict:
        return {'keyId': signature.key_id, 'signature': signature.signature}

    def campaign_document(self) -> dict:
        return {'environmentId': self.environment_id, 'campaign': campaign_document(self.campaign),
                'campaignSignature': self.signature_document(self.campaign_signature)}

    @classmethod
    def from_bytes(cls, raw: bytes) -> DiscoverySubmission:
        if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_BODY:
            raise ValueError('Bounded original submission bytes are required')
        document = _keys(decode_json(raw, MAX_BODY),
            {'environmentId', 'campaign', 'campaignSignature', 'result', 'resultSignature'})
        value = cls(document['environmentId'], _campaign(document['campaign']),
                    _signature(document['campaignSignature']), _result(document['result']),
                    _signature(document['resultSignature']))
        if value.body != raw:
            raise ValueError('Submission is not the original canonical wire representation')
        return value

    def verify(self, verifier: SignedDiscoveryIngestVerifier, checked_at: datetime) -> None:
        if not isinstance(verifier, SignedDiscoveryIngestVerifier) or not _utc(checked_at):
            raise ValueError('Current signed authority and a trusted UTC clock are required')
        # Reparse the actual retained bytes: mutable references cannot change the
        # result while leaving an older signed body or receipt digest attached.
        restored = self.from_bytes(self.body)
        if (restored.digest != self.digest or restored.campaign != self.campaign
                or restored.result != self.result or restored.environment_id != self.environment_id
                or restored.campaign_signature != self.campaign_signature
                or restored.result_signature != self.result_signature):
            raise ValueError('Submission identity differs from its original bytes')
        verifier.bind(self.campaign_signature, self.result_signature).verify_result(
            self.campaign, self.result, self.environment_id, checked_at)


class PrivateFileDiscoveryResultSigner:
    """Read only the enrolled collector's protected Ed25519 PKCS8 PEM key.

    The native credential, campaign issuer, TLS client key and result key have
    separate roles. Enrollment and current witness checks are mandatory after
    signing, including when a key file changes. No signing key is generated here.
    """

    def __init__(self, path: str | Path, *, key_id: str):
        if not _id(key_id):
            raise ValueError('An enrolled collector key identity is required')
        self._path, self.key_id = Path(path), key_id

    def sign(self, campaign: DiscoveryCampaignAuthorization, result: DiscoveryResult,
             environment_id: str, campaign_signature: DiscoverySignature, *,
             verifier: SignedDiscoveryIngestVerifier, clock: Callable[[], datetime]) -> DiscoverySubmission:
        try:
            before = clock()
            verifier.bind(campaign_signature).verify_campaign(campaign, environment_id, before)
            key = serialization.load_pem_private_key(read_protected(self._path, 8192), password=None)
            if not isinstance(key, Ed25519PrivateKey):
                raise ValueError('An Ed25519 collector key is required')
            signature = DiscoverySignature(self.key_id, base64.b64encode(key.sign(
                result_signing_bytes(campaign, result, environment_id))).decode('ascii'))
            value = DiscoverySubmission(environment_id, campaign, campaign_signature, result, signature)
            after = clock()
            if not _utc(after) or after < before:
                raise ValueError("Signing clock regressed")
            value.verify(verifier, after)
            return value
        except Exception:
            raise DiscoveryPublicationHeld('Collector result signing is not currently authorized') from None


def collect_submission(campaign: DiscoveryCampaignAuthorization, environment_id: str,
                       campaign_signature: DiscoverySignature, *, collect: Callable,
                       signer: PrivateFileDiscoveryResultSigner,
                       verifier: SignedDiscoveryIngestVerifier,
                       clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> DiscoverySubmission:
    """Compose an already-configured collector with signing, preserving all gaps.

    The trusted site supplies the actual adapter's collect method. This function
    does not select platforms, issue credentials, upgrade completeness, or grant
    SQL access. A returned submission has not yet been published.
    """
    if (not isinstance(campaign, DiscoveryCampaignAuthorization) or not _id(environment_id)
            or not isinstance(campaign_signature, DiscoverySignature)
            or not callable(collect) or not callable(clock)
            or not isinstance(signer, PrivateFileDiscoveryResultSigner)
            or not isinstance(verifier, SignedDiscoveryIngestVerifier)):
        raise ValueError('A configured collector and signed publication dependencies are required')
    previous = campaign.issued_at
    def now():
        nonlocal previous
        at = clock()
        if not _utc(at) or not previous <= at < campaign.expires_at:
            raise DiscoveryPublicationHeld('Collection publication clock is invalid')
        previous = at
        return at
    try:
        verifier.bind(campaign_signature).verify_campaign(campaign, environment_id, now())
        pages = collect()
        if not isinstance(pages, tuple):
            raise ValueError('A bounded completed collector page tuple is required')
        result = assemble_discovery_result(campaign, pages, checked_at=now())
        return signer.sign(campaign, result, environment_id, campaign_signature,
                           verifier=verifier, clock=now)
    except Exception:
        raise DiscoveryPublicationHeld('Discovery collection cannot become a signed submission') from None


class PrivateDiscoveryOutbox:
    """Create-only, fsynced exact requests for explicit, currently authorized retry.

    A create-only campaign reference binds one exact submission before publication.
    A durable pre-collection claim excludes competing first captures sharing this
    outbox. An incomplete claim is never expired or automatically taken over.
    There is no automatic dispatcher or deletion. Local custody is not independent
    backup/WORM storage, a global campaign ledger, or a durable authority floor.
    """

    def __init__(self, root: str | Path, context: TenantContext):
        if not isinstance(context, TenantContext):
            raise ValueError('An exact tenant context is required')
        self.root, self.context = Path(root).absolute(), context
        self._check_directory(self.root)

    @staticmethod
    def _check_directory(path: Path) -> None:
        if any(item.is_symlink() for item in (path, *path.parents)):
            raise ValueError('Discovery outbox cannot traverse symlinks')
        info = path.stat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
            raise ValueError('Discovery outbox must be private and service-owned')

    def _tenant_directory(self) -> Path:
        scope = hashlib.sha256(_json([self.context.organization_id,
                                     self.context.tenant_id]).encode('ascii')).hexdigest()
        return self.root / scope

    def _store(self, digest: str) -> FileArtifactStore:
        if (not isinstance(digest, str) or len(digest) != 64
                or any(char not in '0123456789abcdef' for char in digest)):
            raise ValueError('An exact submission digest is required')
        self._check_directory(self.root)
        directory = self._tenant_directory()
        for path in (directory, directory / digest[:2]):
            try:
                path.mkdir(mode=0o700)
            except FileExistsError:
                pass
            else:
                fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
            self._check_directory(path)
        return FileArtifactStore(directory)

    def _check_scope(self, submission: DiscoverySubmission) -> None:
        if (submission.campaign.scope.organization_id != self.context.organization_id
                or submission.campaign.scope.tenant_id != self.context.tenant_id):
            raise ValueError('Submission belongs to a different outbox tenant')

    def _campaign_path(self, campaign_id: str, *, create: bool = True) -> Path:
        if not _id(campaign_id):
            raise ValueError('An exact campaign identity is required')
        # Match the ingest repository's org/tenant/campaign identity. Changing
        # environment, endpoint, authority or scope must conflict, not select a
        # different reference path. User identifiers never become path segments.
        key = hashlib.sha256(_json(['discovery-campaign-outbox/1', campaign_id]).encode('ascii')).hexdigest()
        directory = self._store(key).root if create else self._tenant_directory()
        return directory / key[:2] / (key + '.campaign')

    def _read_inspection_file(self, path: Path, maximum: int) -> bytes | None:
        """Read one known record without creating its namespace or digest shard."""
        self._check_directory(self.root)
        for parent in (self._tenant_directory(), path.parent):
            try:
                self._check_directory(parent)
            except FileNotFoundError:
                return None
        try:
            return read_protected(path, maximum)
        except FileNotFoundError:
            self._check_directory(path.parent)
            return None

    def inspect(self, campaign: DiscoveryCampaignAuthorization, environment_id: str,
                signature: DiscoverySignature, *, verifier: SignedDiscoveryIngestVerifier,
                clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> dict:
        """Inspect current local custody, never collect, repair or query the server.

        Two bounded reads bracket live signature checks. Changed observations hold
        rather than being merged into a misleading recovery verdict. No directory,
        intent, payload or campaign reference is created, promoted or deleted.
        Local absence is not evidence of global absence or permission to recapture.
        """
        if (not isinstance(campaign, DiscoveryCampaignAuthorization) or not _id(environment_id)
                or not isinstance(signature, DiscoverySignature)
                or not isinstance(verifier, SignedDiscoveryIngestVerifier) or not callable(clock)
                or (campaign.scope.organization_id, campaign.scope.tenant_id) !=
                   (self.context.organization_id, self.context.tenant_id)):
            raise ValueError('Exact campaign, verifier and local outbox tenant required')
        previous = campaign.issued_at

        def now():
            nonlocal previous
            at = clock()
            if not _utc(at) or not previous <= at < campaign.expires_at:
                raise DiscoveryPublicationHeld('Inspection campaign expired or clock regressed')
            previous = at
            return at

        def snapshot():
            path = self._campaign_path(campaign.campaign_id, create=False)
            claim = self._read_inspection_file(path.with_suffix('.collection'), 1024)
            reference = self._read_inspection_file(path, 1024)
            payload = None
            if reference is not None:
                ref = _keys(decode_json(reference, 1024),
                    {'format', 'environmentId', 'authorizationDigest', 'requestDigest'})
                digest = ref['requestDigest']
                if (ref['format'] != 'hosting-discovery-outbox-campaign/1'
                        or ref['environmentId'] != environment_id
                        or ref['authorizationDigest'] != campaign.digest()
                        or not isinstance(digest, str) or len(digest) != 64
                        or any(c not in '0123456789abcdef' for c in digest)
                        or _json(ref).encode('ascii') != reference):
                    raise ValueError('Local reference differs from the selected campaign')
                payload = self._read_inspection_file(
                    self._tenant_directory() / digest[:2] / digest, MAX_BODY)
                if payload is None or hashlib.sha256(payload).hexdigest() != digest:
                    raise ValueError('Referenced original is missing or changed')
            return claim, reference, payload

        try:
            verifier.bind(signature).verify_campaign(campaign, environment_id, now())
            first = snapshot()
            claim, reference, payload = first
            original = None
            if payload is not None:
                original = DiscoverySubmission.from_bytes(payload)
                if (original.campaign != campaign or original.environment_id != environment_id
                        or original.campaign_signature != signature
                        or self._binding_bytes(original) != reference):
                    raise ValueError('Original custody differs from the selected campaign')
                original.verify(verifier, now())
            intent = None
            if claim is not None:
                row = _keys(decode_json(claim, 1024), {'format', 'environmentId', 'campaignId',
                    'authorizationDigest', 'campaignSignatureDigest', 'attemptId', 'claimedAt',
                    'executionAuthorized'})
                at, attempt = row['claimedAt'], row['attemptId']
                if (row['format'] != 'hosting-discovery-collection-intent/1'
                        or row['environmentId'] != environment_id
                        or row['campaignId'] != campaign.campaign_id
                        or row['authorizationDigest'] != campaign.digest()
                        or row['campaignSignatureDigest'] != hashlib.sha256(_json(
                            DiscoverySubmission.signature_document(signature)).encode('ascii')).hexdigest()
                        or row['executionAuthorized'] is not False
                        or not isinstance(attempt, str) or len(attempt) != 32
                        or any(c not in '0123456789abcdef' for c in attempt)
                        or not isinstance(at, str) or not 1 <= len(at) <= 40
                        or _json(row).encode('ascii') != claim):
                    raise ValueError('Local capture intent has inconsistent identity')
                claimed_at = datetime.fromisoformat(at)
                if (not _utc(claimed_at)
                        or not campaign.issued_at <= claimed_at < campaign.expires_at
                        or claimed_at > now()):
                    raise ValueError('Local capture intent has inconsistent time')
                intent = {'recordDigest': hashlib.sha256(claim).hexdigest(),
                          'attemptId': attempt, 'claimedAt': at}
            checked_at = now()
            if original is not None:
                original.verify(verifier, checked_at)
            else:
                verifier.bind(signature).verify_campaign(campaign, environment_id, checked_at)
            if snapshot() != first:
                raise ValueError('Local custody changed during inspection')
            now()  # Detect expiry or clock regression during the final filesystem read.
            status = ('STAGED_ORIGINAL' if original is not None else
                      'COLLECTION_UNRESOLVED' if intent is not None else 'LOCAL_REFERENCE_ABSENT')
            return {'format': 'hosting-discovery-outbox-inspection/1', 'status': status,
                'campaignId': campaign.campaign_id, 'environmentId': environment_id,
                'authorizationDigest': campaign.digest(), 'checkedAt': checked_at.isoformat(),
                'collectionIntent': intent,
                'original': None if original is None else {
                    'requestDigest': original.digest, 'resultDigest': original.result.digest,
                    'capturedAt': original.result.captured_at.isoformat(),
                    'completeness': original.result.completeness, 'objectCount': len(original.result.objects)},
                'consistency': 'LOCAL_RECORDS_RECHECKED', 'publicationStatus': 'NOT_CHECKED',
                'reconciliationRequired': original is None, 'localCustodyOnly': True,
                'collectionRequested': False, 'publicationAttempted': False, 'executionAuthorized': False}
        except Exception:
            raise DiscoveryPublicationHeld('Local capture inspection is held; reconcile original custody') from None

    def _claim_collection(self, campaign: DiscoveryCampaignAuthorization,
                          environment_id: str, signature: DiscoverySignature,
                          checked_at: datetime) -> tuple[Path, bytes]:
        """Persist one local capture intent before a native collector is invoked.

        Only the verified staging path calls this method. This is not a lease,
        worker grant, fleet-wide scheduler or native fence. The record is never
        deleted on failure or success: original signed custody permits a later
        resume; an intent without that custody requires reconciliation.
        """
        if (not isinstance(campaign, DiscoveryCampaignAuthorization)
                or not _id(environment_id) or not isinstance(signature, DiscoverySignature)
                or not _utc(checked_at) or not campaign.issued_at <= checked_at < campaign.expires_at
                or campaign.scope.organization_id != self.context.organization_id
                or campaign.scope.tenant_id != self.context.tenant_id):
            raise ValueError('Exact campaign, signature, time and outbox tenant required')
        path = self._campaign_path(campaign.campaign_id).with_suffix('.collection')
        raw = _json({'format': 'hosting-discovery-collection-intent/1',
            'environmentId': environment_id, 'campaignId': campaign.campaign_id,
            'authorizationDigest': campaign.digest(),
            'campaignSignatureDigest': hashlib.sha256(_json(
                DiscoverySubmission.signature_document(signature)).encode('ascii')).hexdigest(),
            'attemptId': uuid4().hex, 'claimedAt': checked_at.isoformat(),
            'executionAuthorized': False}).encode('ascii')
        # Atomic no-replace publication fsyncs the complete record and directory.
        # A competing claim, including a corrupt/inaccessible file, never admits
        # another collection. No PID, timeout or process exit can steal this claim.
        if not _atomic_new(path, raw):
            raise DiscoveryPublicationHeld('Collection intent already exists; reconcile original custody')
        claim = (path, raw)
        self._check_collection_claim(claim)
        return claim

    def _check_collection_claim(self, claim: tuple[Path, bytes]) -> None:
        path, expected = claim
        self._check_directory(self.root)
        self._check_directory(path.parent)
        if read_protected(path, 1024) != expected:
            raise DiscoveryPublicationHeld('Collection intent changed; original custody requires reconciliation')

    @staticmethod
    def _binding_bytes(submission: DiscoverySubmission) -> bytes:
        return _json({'format': 'hosting-discovery-outbox-campaign/1',
                      'environmentId': submission.environment_id,
                      'authorizationDigest': submission.campaign.digest(),
                      'requestDigest': submission.digest}).encode('ascii')

    def for_campaign(self, campaign: DiscoveryCampaignAuthorization,
                     environment_id: str) -> DiscoverySubmission | None:
        """Load original local custody by campaign; this does not renew authority.

        Only a missing reference returns None. Corruption, missing referenced
        payloads and changed campaign bindings hold rather than invite a rescan.
        Pre-reference outboxes require explicit reviewed replay by original digest;
        this lookup does not search or infer authority from historical loose blobs.
        """
        if (not isinstance(campaign, DiscoveryCampaignAuthorization) or not _id(environment_id)
                or campaign.scope.organization_id != self.context.organization_id
                or campaign.scope.tenant_id != self.context.tenant_id):
            raise ValueError('Exact campaign, environment and outbox tenant required')
        path = self._campaign_path(campaign.campaign_id)
        try:
            raw = read_protected(path, 1024)
        except FileNotFoundError:
            self._check_directory(path.parent)
            return None
        document = _keys(decode_json(raw, 1024),
                         {'format', 'environmentId', 'authorizationDigest', 'requestDigest'})
        if (document['format'] != 'hosting-discovery-outbox-campaign/1'
                or document['environmentId'] != environment_id
                or document['authorizationDigest'] != campaign.digest()):
            raise ValueError('Campaign identity is bound to different content or scope')
        original = self.load(document['requestDigest'])
        if (original.campaign != campaign or original.environment_id != environment_id
                or self._binding_bytes(original) != raw):
            raise ValueError('Campaign reference differs from the original signed submission')
        return original

    def retain(self, submission: DiscoverySubmission) -> str:
        if not isinstance(submission, DiscoverySubmission):
            raise ValueError('An original signed submission is required')
        current = DiscoverySubmission.from_bytes(submission.body)
        if current != submission:
            raise ValueError('Submission differs from its original bytes')
        self._check_scope(current)
        previous = self.for_campaign(current.campaign, current.environment_id)
        if previous is not None and previous != current:
            raise ValueError('Campaign already has a different retained submission')
        store = self._store(current.digest)
        path = store.root / current.digest[:2] / current.digest
        if path.exists() or path.is_symlink():
            if read_protected(path, MAX_BODY) != current.body:
                raise ValueError('Existing outbox content differs from the submission')
        store.put(current.digest, current.body)
        if self.load(current.digest) != current:
            raise ValueError('Original submission was not retained')
        # Blob fsync precedes reference publication. The existing create-only
        # primitive uses atomic no-replace linking, then directory fsync. Racing
        # writers can retain identical bytes; a different winner is never replaced.
        # An orphaned blob after failure is evidence, not a reference or an ACK.
        _atomic_new(self._campaign_path(current.campaign.campaign_id), self._binding_bytes(current))
        if self.for_campaign(current.campaign, current.environment_id) != current:
            raise ValueError('Campaign already has a different retained submission')
        return current.digest

    def load(self, digest: str) -> DiscoverySubmission:
        store = self._store(digest)
        raw = read_protected(store.root / digest[:2] / digest, MAX_BODY)
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError('Retained submission digest mismatch')
        submission = DiscoverySubmission.from_bytes(raw)
        self._check_scope(submission)
        return submission


def stage_submission(campaign: DiscoveryCampaignAuthorization, environment_id: str,
                     campaign_signature: DiscoverySignature, *, collect: Callable,
                     signer: PrivateFileDiscoveryResultSigner,
                     verifier: SignedDiscoveryIngestVerifier, outbox: PrivateDiscoveryOutbox,
                     clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> DiscoverySubmission:
    """Resume original custody or collect/sign/retain once before explicit delivery.

    A restart or lost ACK does not recollect, re-sign or change captured-at time.
    This stages bytes only; the existing mTLS publisher and ingest repository still
    own delivery and commit. A persistent local claim precedes collection, so
    concurrent processes sharing this outbox cannot both start the first capture.
    An incomplete claim is held, never retried by expiry or automatic takeover.
    """
    if (not isinstance(campaign, DiscoveryCampaignAuthorization) or not _id(environment_id)
            or not isinstance(campaign_signature, DiscoverySignature)
            or not isinstance(outbox, PrivateDiscoveryOutbox)
            or not isinstance(signer, PrivateFileDiscoveryResultSigner)
            or not isinstance(verifier, SignedDiscoveryIngestVerifier)
            or not callable(collect) or not callable(clock)):
        raise ValueError('Exact signed campaign, collector and private outbox required')
    previous = campaign.issued_at
    def now():
        nonlocal previous
        at = clock()
        if not _utc(at) or not previous <= at < campaign.expires_at:
            raise DiscoveryPublicationHeld('Staging clock is invalid or campaign expired')
        previous = at
        return at
    try:
        verifier.bind(campaign_signature).verify_campaign(campaign, environment_id, now())
        original = outbox.for_campaign(campaign, environment_id)
        if original is not None:
            if original.campaign_signature != campaign_signature:
                raise ValueError('Retained issuer signature cannot be replaced')
            original.verify(verifier, now())
            return original
        claim = outbox._claim_collection(campaign, environment_id, campaign_signature, now())

        def collect_claimed():
            outbox._check_collection_claim(claim)
            return collect()

        submission = collect_submission(campaign, environment_id, campaign_signature,
            collect=collect_claimed, signer=signer, verifier=verifier, clock=now)
        outbox._check_collection_claim(claim)
        outbox.retain(submission)
        submission.verify(verifier, now())
        return submission
    except Exception:
        raise DiscoveryPublicationHeld('Discovery submission staging or recovery is held') from None
