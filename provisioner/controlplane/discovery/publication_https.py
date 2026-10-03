"""Bounded collector-to-ingest mTLS publication, never a native API POST client.

Only the existing campaign/result ingest routes are used. Original signed bytes
are retained before any request; no response-loss retry or result re-signing is
automatic. An authenticated acknowledgment is not a native execution grant.
"""
from __future__ import annotations

import hashlib
import http.client
import ipaddress
import re
import socket
import ssl
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock, Timer
from typing import Callable
from urllib.parse import urlsplit

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.x509.oid import ExtendedKeyUsageOID

from .model import _json, _utc
from .native_credentials import decode_json, read_protected
from .publication import DiscoveryPublicationHeld, DiscoverySubmission, PrivateDiscoveryOutbox
from .trust import SignedDiscoveryIngestVerifier


class DiscoveryPublicationUnknown(DiscoveryPublicationHeld):
    """A request may have committed; reconcile or explicitly retry original bytes."""

    def __init__(self, request_digest: str, phase: str):
        self.request_digest, self.phase = request_digest, phase
        super().__init__('Discovery publication acknowledgment is unknown; original request retained')


@dataclass(frozen=True, slots=True)
class DiscoveryPublishTarget:
    """Trusted site configuration, not values accepted from a user HTTP request."""

    origin: str
    connect_ip: str
    trust_domain: str
    ca_bundle: Path
    ca_digest: str
    crl_bundle: Path
    crl_digest: str
    client_certificate: Path
    certificate_digest: str
    client_key: Path = field(repr=False)

    def __post_init__(self):
        try:
            if (not isinstance(self.origin, str) or len(self.origin) > 512
                    or any(not 33 <= ord(c) <= 126 for c in self.origin)
                    or any(c in self.origin for c in '%\\?#')):
                raise ValueError('Invalid origin')
            url = urlsplit(self.origin)
            address = ipaddress.ip_address(self.connect_ip)
            if (url.scheme != 'https' or not url.hostname or url.path
                    or url.username is not None or url.password is not None
                    or url.netloc.endswith(':') or url.port == 0
                    or not re.fullmatch(r'[a-z0-9.:-]+', url.hostname)
                    or str(address) != self.connect_ip or '%' in self.connect_ip
                    or address.is_unspecified or address.is_multicast
                    or not isinstance(self.trust_domain, str)
                    or not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?', self.trust_domain)
                    or '..' in self.trust_domain
                    or any(not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value)
                           for value in (self.ca_digest, self.crl_digest, self.certificate_digest))
                    or any(not isinstance(path, Path) or not path.is_absolute() for path in
                           (self.ca_bundle, self.crl_bundle, self.client_certificate, self.client_key))):
                raise ValueError('Invalid pinned target')
        except (ValueError, TypeError):
            raise ValueError('Exact protected discovery publication target required') from None


@dataclass(frozen=True, slots=True)
class DiscoveryPublishReceipt:
    request_digest: str
    result_digest: str
    campaign_id: str
    environment_id: str
    generation: int
    completeness: str
    execution_authorized: bool = field(default=False, init=False)


class DiscoveryHttpsPublisher:
    """One explicit delivery attempt of one immutable submission.

    A replacement instance may retry the same outbox bytes with fresh authority.
    Never recollect or re-sign merely because an acknowledgment was lost. Campaign
    and result idempotency/conflict resolution remain in the existing repository.
    """

    def __init__(self, target: DiscoveryPublishTarget, *, verifier: SignedDiscoveryIngestVerifier,
                 outbox: PrivateDiscoveryOutbox, timeout: float = 5.0,
                 clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        if (not isinstance(target, DiscoveryPublishTarget)
                or not isinstance(verifier, SignedDiscoveryIngestVerifier)
                or not isinstance(outbox, PrivateDiscoveryOutbox) or not callable(clock)
                or type(timeout) not in (int, float) or not 0 < timeout <= 15):
            raise ValueError('Bounded signed mTLS publication dependencies required')
        self._target, self._verifier, self._outbox = target, verifier, outbox
        self._timeout, self._clock = timeout, clock
        self._lock, self._used = Lock(), False

    def publish(self, submission: DiscoverySubmission) -> DiscoveryPublishReceipt:
        if not isinstance(submission, DiscoverySubmission):
            raise ValueError('An original signed submission is required')
        if not self._lock.acquire(timeout=self._timeout):
            raise DiscoveryPublicationHeld('A discovery publication attempt is already active')
        try:
            if self._used:
                raise DiscoveryPublicationHeld('A publication attempt cannot be reused')
            self._used = True
            previous = submission.campaign.issued_at
            def current():
                nonlocal previous
                at = self._clock()
                if not _utc(at) or not previous <= at < submission.campaign.expires_at:
                    raise DiscoveryPublicationHeld('Publication clock is invalid or campaign expired')
                previous = at
                submission.verify(self._verifier, at)
                return at
            current()
            self._outbox.retain(submission)
            current()
            self._post('CAMPAIGN', submission, current)
            ack = self._post('RESULT', submission, current)
            return DiscoveryPublishReceipt(submission.digest, submission.result.digest,
                submission.campaign.campaign_id, submission.environment_id,
                ack['generation'], submission.result.completeness)
        except DiscoveryPublicationUnknown:
            raise
        except Exception:
            raise DiscoveryPublicationHeld('Discovery publication was not admitted') from None
        finally:
            self._lock.release()

    def _context(self, submission: DiscoverySubmission, at: datetime) -> ssl.SSLContext:
        target = self._target
        ca = read_protected(target.ca_bundle, 1024*1024, secret=False)
        crl = read_protected(target.crl_bundle, 1024*1024, secret=False)
        certificate = read_protected(target.client_certificate, 65536, secret=False)
        key_bytes = read_protected(target.client_key, 8192)
        if any(hashlib.sha256(data).hexdigest() != expected for data, expected in
               ((ca, target.ca_digest), (crl, target.crl_digest),
                (certificate, target.certificate_digest))):
            raise DiscoveryPublicationHeld('Publication trust material changed')
        leaf = x509.load_pem_x509_certificate(certificate)
        scope = submission.campaign.scope
        uri = (f'spiffe://{target.trust_domain}/org/{scope.organization_id}'
               f'/tenant/{scope.tenant_id}/site/{scope.site_id}/worker/{submission.campaign.collector_id}')
        key = serialization.load_pem_private_key(key_bytes, password=None)
        if (leaf.extensions.get_extension_for_class(x509.BasicConstraints).value.ca
                or not leaf.extensions.get_extension_for_class(x509.KeyUsage).value.digital_signature
                or ExtendedKeyUsageOID.CLIENT_AUTH not in leaf.extensions.get_extension_for_class(
                    x509.ExtendedKeyUsage).value
                or leaf.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(
                    x509.UniformResourceIdentifier) != [uri]
                or not leaf.not_valid_before_utc <= at < leaf.not_valid_after_utc
                or submission.campaign.expires_at > leaf.not_valid_after_utc
                or key.public_key().public_bytes(serialization.Encoding.DER,
                    serialization.PublicFormat.SubjectPublicKeyInfo) != leaf.public_key().public_bytes(
                        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)):
            raise DiscoveryPublicationHeld('Client certificate does not bind the collector campaign')
        # Explicit construction avoids SSLKEYLOGFILE's create_default_context
        # side effect. Verified files are snapshotted in a private directory so
        # load_cert_chain cannot reread a replaced operator path.
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.verify_flags |= ssl.VERIFY_CRL_CHECK_CHAIN | ssl.VERIFY_X509_STRICT
        with tempfile.TemporaryDirectory(prefix='discovery-publish-tls-') as temporary:
            root = Path(temporary)
            for name, data in (('trust.pem', ca+b'\n'+crl), ('client.pem', certificate), ('client.key', key_bytes)):
                path = root / name
                with path.open('xb') as stream:
                    path.chmod(0o600)
                    stream.write(data)
            context.load_verify_locations(cafile=str(root/'trust.pem'))
            context.load_cert_chain(str(root/'client.pem'), str(root/'client.key'))
        return context

    @staticmethod
    def _check_ack(phase: str, submission: DiscoverySubmission, ack: object) -> dict:
        expected = {'status': 'CAMPAIGN_REGISTERED', 'campaignId': submission.campaign.campaign_id,
                    'authorizationDigest': submission.campaign.digest(), 'executionAuthorized': False}
        if phase == 'RESULT':
            expected = {'status': 'RESULT_PUBLISHED', 'campaignId': submission.campaign.campaign_id,
                        'environmentId': submission.environment_id, 'resultDigest': submission.result.digest,
                        'completeness': submission.result.completeness, 'executionAuthorized': False}
            if (not isinstance(ack, dict) or type(ack.get('generation')) is not int
                    or not 1 <= ack['generation'] < 2**63):
                raise ValueError('Invalid publication generation')
            expected['generation'] = ack['generation']
        if not isinstance(ack, dict) or ack != expected or ack.get('executionAuthorized') is not False:
            raise ValueError('Acknowledgment does not bind the original submission')
        return ack

    def _post(self, phase: str, submission: DiscoverySubmission, current: Callable) -> dict:
        target = self._target
        url = urlsplit(target.origin)
        body = (_json(submission.campaign_document()).encode('ascii')
                if phase == 'CAMPAIGN' else submission.body)
        route = '/v1/discovery/campaigns' if phase == 'CAMPAIGN' else '/v1/discovery/results'
        seconds = min(self._timeout, (submission.campaign.expires_at-current()).total_seconds())
        deadline, active, attempted = time.monotonic()+seconds, [None], False
        response = connection = None
        def remaining():
            value = deadline-time.monotonic()
            if value <= 0:
                raise DiscoveryPublicationHeld('Publication deadline expired')
            return value
        def stop():
            if active[0] is not None:
                try:
                    active[0].shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
        timer = Timer(seconds, stop)
        timer.daemon = True
        timer.start()
        try:
            context = self._context(submission, current())
            raw = socket.create_connection((target.connect_ip, url.port or 443), timeout=remaining())
            active[0] = raw
            tls = context.wrap_socket(raw, server_hostname=url.hostname, do_handshake_on_connect=False)
            active[0] = tls
            tls.settimeout(remaining())
            tls.do_handshake()
            current()
            tls.settimeout(remaining())
            connection = http.client.HTTPConnection(url.hostname, url.port or 443, timeout=remaining())
            connection.auto_open = 0
            connection.sock = tls
            attempted = True
            connection.request('POST', route, body=body, headers={
                'Content-Type': 'application/json', 'Accept': 'application/json',
                'Accept-Encoding': 'identity', 'Connection': 'close'})
            response = connection.getresponse()
            remaining()
            lengths = response.headers.get_all('Content-Length', [])
            if (response.status != 200 or len(lengths) != 1 or len(lengths[0]) > 5
                    or not lengths[0].isascii() or not lengths[0].isdigit()
                    or not 0 < int(lengths[0]) <= 8192
                    or response.headers.get('Transfer-Encoding') is not None
                    or response.headers.get('Content-Encoding') is not None
                    or response.headers.get_all('Content-Type', []) != ['application/json']):
                raise ValueError('Invalid bounded publication acknowledgment')
            data = response.read(int(lengths[0])+1)
            remaining()
            if len(data) != int(lengths[0]):
                raise ValueError('Truncated publication acknowledgment')
            ack = self._check_ack(phase, submission, decode_json(data, 8192))
            current()
            remaining()
            return ack
        except Exception:
            if attempted:
                raise DiscoveryPublicationUnknown(submission.digest, phase) from None
            raise DiscoveryPublicationHeld('Verified discovery publication connection unavailable') from None
        finally:
            timer.cancel()
            if response is not None:
                response.close()
            if connection is not None:
                connection.close()
            if active[0] is not None:
                active[0].close()
            timer.join()
