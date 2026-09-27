"""Private, ephemeral certificate fixtures for actual TLS handshake tests."""
from __future__ import annotations

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


class TestPki:
    def __init__(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.ca_key = ec.generate_private_key(ec.SECP256R1())
        self.name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Worker test CA')])
        now = datetime.now(timezone.utc)
        self.ca = (x509.CertificateBuilder().subject_name(self.name)
                   .issuer_name(self.name).public_key(self.ca_key.public_key())
                   .serial_number(x509.random_serial_number())
                   .not_valid_before(now - timedelta(days=1))
                   .not_valid_after(now + timedelta(days=2))
                   .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
                   .add_extension(x509.KeyUsage(digital_signature=True,
                                                content_commitment=False,
                                                key_encipherment=False,
                                                data_encipherment=False,
                                                key_agreement=False,
                                                key_cert_sign=True, crl_sign=True,
                                                encipher_only=False,
                                                decipher_only=False), critical=True)
                   .sign(self.ca_key, hashes.SHA256()))
        self.write('ca.pem', self.ca.public_bytes(serialization.Encoding.PEM))
        self.write_crl([])

    def write(self, name, contents):
        path = self.root / name
        path.write_bytes(contents)
        return path

    def issue(self, name, *, client=False, uri=None):
        key = ec.generate_private_key(ec.SECP256R1())
        now = datetime.now(timezone.utc)
        builder = (x509.CertificateBuilder()
                   .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)]))
                   .issuer_name(self.name).public_key(key.public_key())
                   .serial_number(x509.random_serial_number())
                   .not_valid_before(now - timedelta(minutes=1))
                   .not_valid_after(now + timedelta(hours=1))
                   .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
                   .add_extension(x509.KeyUsage(digital_signature=True,
                                                content_commitment=False,
                                                key_encipherment=False,
                                                data_encipherment=False,
                                                key_agreement=False,
                                                key_cert_sign=False, crl_sign=False,
                                                encipher_only=False,
                                                decipher_only=False), critical=True)
                   .add_extension(x509.ExtendedKeyUsage([
                       ExtendedKeyUsageOID.CLIENT_AUTH if client else
                       ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
                   .add_extension(x509.SubjectAlternativeName([
                       x509.UniformResourceIdentifier(uri) if client else
                       x509.DNSName('localhost')]), critical=False))
        cert = builder.sign(self.ca_key, hashes.SHA256())
        self.write(name + '.pem', cert.public_bytes(serialization.Encoding.PEM))
        self.write(name + '.key', key.private_bytes(serialization.Encoding.PEM,
                                                   serialization.PrivateFormat.PKCS8,
                                                   serialization.NoEncryption()))
        return cert

    def write_crl(self, serials):
        now = datetime.now(timezone.utc)
        builder = (x509.CertificateRevocationListBuilder()
                   .issuer_name(self.name).last_update(now - timedelta(minutes=1))
                   .next_update(now + timedelta(hours=1)))
        for serial in serials:
            revoked = (x509.RevokedCertificateBuilder().serial_number(serial)
                       .revocation_date(now - timedelta(seconds=30)).build())
            builder = builder.add_revoked_certificate(revoked)
        self.write('crl.pem', builder.sign(self.ca_key, hashes.SHA256()).public_bytes(
            serialization.Encoding.PEM))

    def close(self):
        self.temporary.cleanup()
