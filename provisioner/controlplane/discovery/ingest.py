"""Bounded mTLS discovery admission with signature custody before SQL writes.

Only a real peer on the pinned listener may submit signed, exact-scope inventory.
The ordinary user API remains read-only. Ingest cannot enroll a collector,
issue a campaign, change native RBAC, or authorize workload execution.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import socket
import ssl
import stat
import threading
from dataclasses import dataclass
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.evidence.filesystem import FileArtifactStore
from provisioner.controlplane.persistence.store import TenantContext
from provisioner.controlplane.worker.grants import GrantDenied, VerifiedWorkerIdentity
from provisioner.controlplane.worker.pki import MutualTlsWorkerVerifier

from .model import (DiscoveryCampaignAuthorization, DiscoveryFact, DiscoveryObject,
                    DiscoveryResult, NativeIdentity, _id, _json, _object_json,
                    _scope_json, _unique_pairs)
from .persistence import DiscoveryConflict, DiscoveryRepository, VerificationEvidence
from .trust import (BoundDiscoveryIngestVerifier, DiscoverySignature,
                    DiscoveryTrustDenied, SignedDiscoveryIngestVerifier, _keys, _time)

MAX_BODY = 1048576
_SCOPE_FIELDS = {'organizationId', 'tenantId', 'locationId', 'securityDomainId',
                 'endpointId', 'nativeScopeId', 'platformFamily'}
_CAMPAIGN_FIELDS = {'format', 'campaignId', 'scope', 'authorityReference', 'collectorId',
    'allowedKinds', 'issuedAt', 'expiresAt', 'maxPages', 'maxObjects', 'maxPageSize'}
_RESULT_FIELDS = {'format', 'campaignId', 'authorizationDigest', 'scope', 'capturedAt',
    'completeness', 'objects', 'collectionErrors', 'missingPrivileges'}


def campaign_document(campaign: DiscoveryCampaignAuthorization) -> dict:
    return {'format': 'hosting-discovery-campaign/1', 'campaignId': campaign.campaign_id,
            'scope': _scope_json(campaign.scope), 'authorityReference': campaign.authority_reference,
            'collectorId': campaign.collector_id, 'allowedKinds': list(campaign.allowed_kinds),
            'issuedAt': campaign.issued_at.isoformat(), 'expiresAt': campaign.expires_at.isoformat(),
            'maxPages': campaign.max_pages, 'maxObjects': campaign.max_objects,
            'maxPageSize': campaign.max_page_size}


def result_document(result: DiscoveryResult) -> dict:
    return {'format': 'hosting-discovery-result/1', 'campaignId': result.campaign_id,
            'authorizationDigest': result.authorization_digest, 'scope': _scope_json(result.scope),
            'capturedAt': result.captured_at.isoformat(), 'completeness': result.completeness,
            'objects': [_object_json(obj) for obj in result.objects],
            'collectionErrors': list(result.collection_errors),
            'missingPrivileges': list(result.missing_privileges)}


def _campaign(body: object) -> DiscoveryCampaignAuthorization:
    body = _keys(body, _CAMPAIGN_FIELDS)
    if body['format'] != 'hosting-discovery-campaign/1' or not isinstance(body['allowedKinds'], list):
        raise ValueError('Unsupported campaign document')
    return DiscoveryCampaignAuthorization(body['campaignId'],
        PlanScope.from_record(_keys(body['scope'], _SCOPE_FIELDS)), body['authorityReference'],
        body['collectorId'], tuple(body['allowedKinds']), _time(body['issuedAt']),
        _time(body['expiresAt']), body['maxPages'], body['maxObjects'], body['maxPageSize'])


def _result(body: object) -> DiscoveryResult:
    body = _keys(body, _RESULT_FIELDS)
    if (body['format'] != 'hosting-discovery-result/1'
            or any(not isinstance(body[key], list) for key in
                   ('objects', 'collectionErrors', 'missingPrivileges'))
            or len(body['objects']) > 100000):
        raise ValueError('Unsupported bounded discovery result document')
    objects = []
    for item in body['objects']:
        item = _keys(item, {'binding', 'facts'})
        binding = _keys(item['binding'], {'endpointId', 'nativeScopeId', 'platformFamily',
                                          'resourceKind', 'nativeId'})
        if not isinstance(item['facts'], list) or not 1 <= len(item['facts']) <= 64:
            raise ValueError('Bounded object facts are required')
        facts = []
        for fact in item['facts']:
            fact = _keys(fact, {'name', 'state', 'value', 'reason', 'requiredPrivilege'})
            if fact['state'] == 'KNOWN':
                facts.append(DiscoveryFact(fact['name'], 'KNOWN', _json(fact['value']),
                                           fact['reason'], fact['requiredPrivilege']))
            elif fact['state'] == 'UNKNOWN' and fact['value'] is None:
                facts.append(DiscoveryFact.unknown(fact['name'], fact['reason'],
                                                   required_privilege=fact['requiredPrivilege']))
            else:
                raise ValueError('Invalid explicit fact state')
        objects.append(DiscoveryObject(NativeIdentity(binding['endpointId'],
            binding['nativeScopeId'], binding['platformFamily'], binding['resourceKind'],
            binding['nativeId']), tuple(facts)))
    return DiscoveryResult(body['campaignId'], body['authorizationDigest'],
        PlanScope.from_record(_keys(body['scope'], _SCOPE_FIELDS)), _time(body['capturedAt']),
        body['completeness'], tuple(objects), tuple(body['collectionErrors']), tuple(body['missingPrivileges']))


def _signature(body: object) -> DiscoverySignature:
    body = _keys(body, {'keyId', 'signature'})
    return DiscoverySignature(body['keyId'], body['signature'])


def _nonfinite(_value):
    raise ValueError('Nonfinite discovery JSON is forbidden')


class PrivateDiscoveryEvidenceSink:
    """Create-only, fsynced private blobs for original signed admission bytes.

    The configured root must already exist and be owned by the service user,
    with mode 0700. This is durable local custody, not WORM/independent backup.
    Retention and independently anchored export remain deployment obligations.
    """

    def __init__(self, root: str | Path):
        self.root = Path(root).absolute()
        self._protected_root()

    def _protected_root(self):
        if any(path.is_symlink() for path in (self.root, *self.root.parents)):
            raise ValueError('Discovery evidence root cannot contain symlinks')
        info = self.root.stat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
                or info.st_mode & 0o077):
            raise ValueError('Discovery evidence root must be private and service-owned')

    @staticmethod
    def _private_directory(path: Path):
        try:
            path.mkdir(mode=0o700)
        except FileExistsError:
            pass
        else:
            parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(parent)
            finally:
                os.close(parent)
        info = path.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
            raise ValueError('Discovery evidence directory is not private')

    def retain(self, context: TenantContext, request_bytes: bytes,
               proof: VerificationEvidence, peer: VerifiedWorkerIdentity,
               checked_at: datetime) -> str:
        if (not isinstance(context, TenantContext) or not isinstance(request_bytes, bytes)
                or not 0 < len(request_bytes) <= MAX_BODY
                or not isinstance(proof, VerificationEvidence)):
            raise ValueError('Bounded original admission and verified proof are required')
        self._protected_root()
        scope_digest = hashlib.sha256(_json([context.organization_id,
                                             context.tenant_id]).encode('ascii')).hexdigest()
        # Store original bytes separately so full 1 MiB requests fit the bounded
        # existing artifact store. The small admission record links the proof.
        directory = self.root / scope_digest
        self._private_directory(directory)
        store = FileArtifactStore(directory)
        request_digest = hashlib.sha256(request_bytes).hexdigest()
        self._private_directory(directory / request_digest[:2])
        store.put(request_digest, request_bytes)
        record = _json({'format': 'hosting-discovery-admission-evidence/1',
            'organizationId': context.organization_id, 'tenantId': context.tenant_id,
            'requestDigest': request_digest, 'authorizationDigest': proof.authorization_digest,
            'resultDigest': proof.result_digest, 'verifiedBy': proof.verified_by,
            'verificationReference': proof.verification_reference,
            'peerSubject': peer.subject, 'peerCertificateSha256': peer.certificate_sha256,
            'checkedAt': checked_at.isoformat()}).encode('ascii')
        record_digest = hashlib.sha256(record).hexdigest()
        self._private_directory(directory / record_digest[:2])
        store.put(record_digest, record)
        if store.get(request_digest) != request_bytes or store.get(record_digest) != record:
            raise RuntimeError('Original signed admission was not durably retained')
        return 'discovery-admission-v1:' + record_digest


@dataclass(frozen=True, slots=True)
class _RetainingVerifier:
    verifier: BoundDiscoveryIngestVerifier
    sink: PrivateDiscoveryEvidenceSink
    context: TenantContext
    peer: VerifiedWorkerIdentity
    request_bytes: bytes
    tls_verifier: MutualTlsWorkerVerifier
    transport_evidence: object

    def _retain(self, proof: VerificationEvidence, checked_at: datetime) -> VerificationEvidence:
        if (self.tls_verifier.verify(self.transport_evidence) != self.peer
                or checked_at >= self.peer.expires_at):
            raise DiscoveryTrustDenied('Collector transport certificate expired before admission')
        try:
            reference = self.sink.retain(self.context, self.request_bytes, proof, self.peer, checked_at)
        except (OSError, ValueError) as exc:
            raise RuntimeError('Durable discovery evidence custody is unavailable') from exc
        return VerificationEvidence(proof.authorization_digest, proof.result_digest,
                                    proof.verified_by, reference)

    def verify_campaign(self, campaign, environment_id, checked_at):
        return self._retain(self.verifier.verify_campaign(campaign, environment_id, checked_at), checked_at)

    def verify_result(self, campaign, result, environment_id, checked_at):
        return self._retain(self.verifier.verify_result(campaign, result, environment_id, checked_at), checked_at)


class DiscoveryIngestService:
    def __init__(self, *, connect: Callable, ingest_role: str,
                 tls_verifier: MutualTlsWorkerVerifier,
                 signature_verifier: SignedDiscoveryIngestVerifier,
                 evidence_sink: PrivateDiscoveryEvidenceSink):
        if (not callable(connect) or not isinstance(tls_verifier, MutualTlsWorkerVerifier)
                or not isinstance(signature_verifier, SignedDiscoveryIngestVerifier)
                or not isinstance(evidence_sink, PrivateDiscoveryEvidenceSink)):
            raise ValueError('Pinned transport, signed authority and durable evidence are required')
        # Validate the dedicated SQL role without opening a database connection.
        DiscoveryRepository(connect, ingest_role=ingest_role)
        if ingest_role is None:
            raise ValueError('Dedicated discovery ingest role is required')
        self.connect, self.ingest_role = connect, ingest_role
        self.tls_verifier, self.signature_verifier = tls_verifier, signature_verifier
        self.evidence_sink = evidence_sink

    def submit(self, path: str, request_bytes: bytes, transport_evidence: object) -> dict:
        if path not in ('/v1/discovery/campaigns', '/v1/discovery/results'):
            raise ValueError('Unknown discovery admission route')
        peer = self.tls_verifier.verify(transport_evidence)
        if not isinstance(peer, VerifiedWorkerIdentity):
            raise DiscoveryTrustDenied('Verified collector mTLS identity is required')
        if not isinstance(request_bytes, bytes) or not 0 < len(request_bytes) <= MAX_BODY:
            raise ValueError('Discovery admission exceeds its body limit')
        document = json.loads(request_bytes, object_pairs_hook=_unique_pairs, parse_constant=_nonfinite)
        fields = {'environmentId', 'campaign', 'campaignSignature'}
        if path.endswith('/results'):
            fields |= {'result', 'resultSignature'}
        document = _keys(document, fields)
        if not _id(document['environmentId']):
            raise ValueError('An exact environment identifier is required')
        campaign = _campaign(document['campaign'])
        if (campaign.collector_id, campaign.scope.organization_id, campaign.scope.tenant_id,
                campaign.scope.site_id) != (peer.subject, peer.organization_id,
                                            peer.tenant_id, peer.site_id):
            raise DiscoveryTrustDenied('Campaign does not bind this collector mTLS identity')
        result = _result(document['result']) if path.endswith('/results') else None
        if result is not None and (result.campaign_id != campaign.campaign_id
                or result.authorization_digest != campaign.digest() or result.scope != campaign.scope):
            raise DiscoveryTrustDenied('Result differs from its signed campaign')
        bound = self.signature_verifier.bind(_signature(document['campaignSignature']),
            _signature(document['resultSignature']) if result is not None else None)
        context = TenantContext(peer.organization_id, peer.tenant_id)
        retaining = _RetainingVerifier(bound, self.evidence_sink, context, peer,
                                       request_bytes, self.tls_verifier, transport_evidence)
        repository = DiscoveryRepository(self.connect, ingest_verifier=retaining,
                                          ingest_role=self.ingest_role)
        if result is None:
            repository.register_verified_campaign(context, document['environmentId'], campaign)
            return {'status': 'CAMPAIGN_REGISTERED', 'campaignId': campaign.campaign_id,
                    'authorizationDigest': campaign.digest(), 'executionAuthorized': False}
        stored = repository.publish_verified_result(context, document['environmentId'], result)
        return {'status': 'RESULT_PUBLISHED', 'campaignId': campaign.campaign_id,
                'environmentId': stored.environment_id, 'generation': stored.generation,
                'resultDigest': stored.result_digest, 'completeness': stored.completeness,
                'executionAuthorized': False}


class DiscoveryIngestServer(ThreadingHTTPServer):
    """Bounded collector-only listener; TLS handshakes occupy bounded slots."""

    daemon_threads = True
    allow_reuse_address = False
    request_queue_size = 16

    def __init__(self, address: tuple[str, int], service: DiscoveryIngestService,
                 *, max_connections: int = 16):
        ip = ipaddress.ip_address(address[0])
        if (ip.is_unspecified or len(address) != 2 or type(address[1]) is not int
                or not 0 <= address[1] <= 65535 or not isinstance(service, DiscoveryIngestService)
                or type(max_connections) is not int or not 1 <= max_connections <= 64):
            raise ValueError('Exact management bind and bounded authenticated service are required')
        self.address_family = socket.AF_INET6 if ip.version == 6 else socket.AF_INET
        self.service = service
        self._slots = threading.BoundedSemaphore(max_connections)
        super().__init__(address, _DiscoveryHandler)

    def get_request(self):
        peer, address = super().get_request()
        peer.settimeout(10)
        return peer, address

    def process_request(self, request, client_address):
        if not self._slots.acquire(blocking=False):
            request.close()
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self._slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            with self.service.tls_verifier.context.wrap_socket(request, server_side=True) as peer:
                super().process_request_thread(peer, client_address)
        except (ssl.SSLError, TimeoutError, OSError):
            request.close()
        finally:
            self._slots.release()


class _DiscoveryHandler(BaseHTTPRequestHandler):
    server: DiscoveryIngestServer

    def log_message(self, *_args):
        pass

    def _reply(self, status: int, document: dict):
        body = _json(document).encode('ascii')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def do_POST(self):
        if self.path not in ('/v1/discovery/campaigns', '/v1/discovery/results'):
            self._reply(404, {'error': 'UNKNOWN_ROUTE'})
            return
        try:
            if any(name.lower() in ('forwarded', 'authorization', 'x-client-cert', 'x-ssl-client-cert')
                   or name.lower().startswith('x-forwarded-') for name in self.headers):
                raise ValueError('Forwarded or alternate identity is forbidden')
            lengths = self.headers.get_all('Content-Length', [])
            if (len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdigit()
                    or len(lengths[0]) > 10 or not 0 < int(lengths[0]) <= MAX_BODY
                    or self.headers.get('Transfer-Encoding') is not None
                    or self.headers.get('Content-Encoding') is not None
                    or self.headers.get_all('Content-Type', []) != ['application/json']):
                raise ValueError('A bounded exact JSON admission is required')
            raw = self.rfile.read(int(lengths[0]))
            if len(raw) != int(lengths[0]):
                raise ValueError('Truncated discovery admission')
            result = self.server.service.submit(self.path, raw, self.connection)
            self._reply(200, result)
        except (DiscoveryTrustDenied, GrantDenied):
            self._reply(403, {'error': 'DISCOVERY_AUTHORITY_DENIED'})
        except DiscoveryConflict:
            self._reply(409, {'error': 'DISCOVERY_CAMPAIGN_CONFLICT'})
        except (ValueError, TypeError, KeyError, UnicodeError, RecursionError, OverflowError):
            self._reply(400, {'error': 'INVALID_DISCOVERY_ADMISSION'})
        except Exception:
            self._reply(503, {'error': 'DISCOVERY_INGEST_UNAVAILABLE'})

    def do_GET(self):
        self._reply(405, {'error': 'METHOD_NOT_ALLOWED'})
