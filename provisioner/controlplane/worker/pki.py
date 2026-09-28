"""mTLS worker identity from a pinned enterprise CA and SPIFFE URI SAN.

Only sockets completed by this verifier's own server TLS context are accepted.
The TLS handshake validates the chain and CRL; the enrollment database is
checked again under lock for each grant and credential use.
"""
from __future__ import annotations

import hashlib
import ssl
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from cryptography import x509
from cryptography.x509.oid import ExtendedKeyUsageOID

from .grants import GrantDenied, VerifiedWorkerIdentity, _ID


class MutualTlsWorkerVerifier:
    """Own the TLS server context used for worker-only listener connections.

    ``trust_bundle`` must contain the approved issuing CA chain; ``crl_bundle``
    contains current CRLs for that chain. The listener must use ``context``
    directly and pass its completed SSLSocket to ``verify``. Proxy headers,
    forwarded certificates, and unverified DER bytes are never evidence.
    """

    def __init__(self, *, server_certificate: str | Path, server_key: str | Path,
                 trust_bundle: str | Path, crl_bundle: str | Path,
                 trust_domain: str):
        if (not isinstance(trust_domain, str) or not trust_domain
                or any(character not in 'abcdefghijklmnopqrstuvwxyz0123456789.-'
                       for character in trust_domain)
                or trust_domain.startswith('.') or trust_domain.endswith('.')
                or '..' in trust_domain):
            raise ValueError('A valid pinned worker trust domain is required')
        self.trust_domain = trust_domain
        self._paths = (server_certificate, server_key, trust_bundle, crl_bundle)
        self._context = self._new_context()

    def _new_context(self) -> ssl.SSLContext:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_cert_chain(str(self._paths[0]), str(self._paths[1]))
        context.load_verify_locations(cafile=str(self._paths[2]))
        context.load_verify_locations(cafile=str(self._paths[3]))
        context.verify_flags |= ssl.VERIFY_CRL_CHECK_CHAIN
        return context

    @property
    def context(self) -> ssl.SSLContext:
        return self._context

    def reload_trust(self) -> ssl.SSLContext:
        """Atomically replace the context after CA/CRL rotation.

        The listener must take the returned context for subsequent handshakes;
        sockets from the previous context fail verification immediately.
        """
        replacement = self._new_context()
        self._context = replacement
        return replacement

    def verify(self, transport_evidence: object) -> VerifiedWorkerIdentity:
        if (type(transport_evidence) is not ssl.SSLSocket
                or transport_evidence.context is not self._context):
            raise GrantDenied('A peer on the pinned mTLS listener is required')
        try:
            der = transport_evidence.getpeercert(binary_form=True)
            if not der:
                raise GrantDenied('Worker certificate is missing')
            certificate = x509.load_der_x509_certificate(der)
            if certificate.extensions.get_extension_for_class(
                    x509.BasicConstraints).value.ca:
                raise GrantDenied('A CA cannot be a worker')
            usage = certificate.extensions.get_extension_for_class(
                x509.KeyUsage).value
            eku = certificate.extensions.get_extension_for_class(
                x509.ExtendedKeyUsage).value
            if not usage.digital_signature or ExtendedKeyUsageOID.CLIENT_AUTH not in eku:
                raise GrantDenied('Worker certificate lacks client authentication usage')
            sans = certificate.extensions.get_extension_for_class(
                x509.SubjectAlternativeName).value
            uris = sans.get_values_for_type(x509.UniformResourceIdentifier)
            if len(uris) != 1:
                raise GrantDenied('Exactly one worker URI SAN is required')
            uri = urlsplit(uris[0])
            if (uri.scheme != 'spiffe' or uri.netloc != self.trust_domain
                    or uri.query or uri.fragment or uri.username or uri.password
                    or uri.port is not None):
                raise GrantDenied('Worker URI SAN is outside the trust domain')
            parts = uri.path.split('/')
            if (len(parts) != 9 or parts[0] != '' or
                    (parts[1], parts[3], parts[5], parts[7]) !=
                    ('org', 'tenant', 'site', 'worker') or
                    any(not _ID.fullmatch(parts[i]) for i in (2, 4, 6, 8))):
                raise GrantDenied('Worker URI SAN is malformed')
            now = datetime.now(timezone.utc)
            if not certificate.not_valid_before_utc <= now < certificate.not_valid_after_utc:
                raise GrantDenied('Worker certificate is outside its validity window')
            return VerifiedWorkerIdentity(parts[2], parts[4], parts[8], parts[6],
                                          hashlib.sha256(der).hexdigest(),
                                          certificate.not_valid_after_utc)
        except (ValueError, x509.ExtensionNotFound, ssl.SSLError, OSError) as exc:
            raise GrantDenied('Worker certificate cannot be verified') from exc
