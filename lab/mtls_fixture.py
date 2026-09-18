"""Ephemeral TLS1.3 identity fixture, not a PKI/KMS or production service.

One challenge endpoint, no application data. Credentials generated per run and
removed with the temporary directory. Certificate fingerprint grants represent a
local resource authorization example, not enterprise identity federation or CRL.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import hashlib
import ipaddress
import os
from pathlib import Path
import secrets
import socket
import ssl
import threading
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID


def material(directory: Path) -> dict:
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(directory,0o700)
    now=datetime.now(timezone.utc)
    def name(s):return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,s)])
    def authority(label):
        key=ec.generate_private_key(ec.SECP256R1())
        cert=(x509.CertificateBuilder().subject_name(name(label)).issuer_name(name(label))
              .public_key(key.public_key()).serial_number(x509.random_serial_number())
              .not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(hours=2))
              .add_extension(x509.BasicConstraints(ca=True,path_length=0),critical=True)
              .add_extension(x509.KeyUsage(True,False,False,False,False,True,True,False,False),critical=True)
              .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()),critical=False)
              .sign(key,hashes.SHA256()))
        return key,cert
    rootkey,rootcert=authority('Ephemeral fixture root - not a production trust anchor')
    otherkey,othercert=authority('Untrusted fixture root')
    def private(path,content):
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as f:f.write(content)
    private(directory/'ca.pem',rootcert.public_bytes(serialization.Encoding.PEM))
    private(directory/'other-ca.pem',othercert.public_bytes(serialization.Encoding.PEM))
    out={'ca':str(directory/'ca.pem'),'other_ca':str(directory/'other-ca.pem')}
    def leaf(label,identity,server=False,expired=False,foreign=False):
        key=ec.generate_private_key(ec.SECP256R1())
        issuerkey,issuer=(otherkey,othercert) if foreign else (rootkey,rootcert)
        names=[x509.DNSName('data-01.fixture.invalid')] if server else [x509.UniformResourceIdentifier(identity)]
        cert=(x509.CertificateBuilder().subject_name(name(label)).issuer_name(issuer.subject)
              .public_key(key.public_key()).serial_number(x509.random_serial_number())
              .not_valid_before(now-timedelta(hours=2) if expired else now-timedelta(minutes=1))
              .not_valid_after(now-timedelta(minutes=1) if expired else now+timedelta(hours=1))
              .add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True)
              .add_extension(x509.KeyUsage(True,False,False,False,False,False,False,False,False),critical=True)
              .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH if server else ExtendedKeyUsageOID.CLIENT_AUTH]),critical=False)
              .add_extension(x509.SubjectAlternativeName(names),critical=False)
              .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(issuerkey.public_key()),critical=False)
              .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()),critical=False)
              .sign(issuerkey,hashes.SHA256()))
        cp,kp=directory/f'{label}.pem',directory/f'{label}.key'
        private(cp,cert.public_bytes(serialization.Encoding.PEM))
        private(kp,key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
        out[label]={'certificate':str(cp),'key':str(kp),'fingerprint':cert.fingerprint(hashes.SHA256()).hex(), 'identity':identity}
    leaf('server','data-01.fixture.invalid',server=True)
    leaf('client','urn:hosting:tenant-001:processor-01')
    leaf('rotated','urn:hosting:tenant-001:processor-01')
    leaf('other-tenant','urn:hosting:tenant-002:processor-02')
    leaf('expired','urn:hosting:tenant-001:processor-01',expired=True)
    leaf('foreign','urn:hosting:tenant-001:processor-01',foreign=True)
    return out


def recv_exact(sock,n):
    data=b''
    while len(data)<n:
        part=sock.recv(n-len(data))
        if not part:raise EOFError
        data+=part
    return data


class Service:
    def __init__(self,address,port,cert,key,ca,allowed):
        ip=ipaddress.ip_address(address)
        if not ip.is_loopback and not (ip.version==4 and any(ip in ipaddress.ip_network(n) for n in ('192.0.2.0/24','198.51.100.0/24','203.0.113.0/24'))):
            raise ValueError('TLS fixture can only bind loopback/documentation addresses')
        self.context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.context.minimum_version=ssl.TLSVersion.TLSv1_3
        self.context.verify_mode=ssl.CERT_REQUIRED
        self.context.load_verify_locations(cafile=ca)
        self.context.load_cert_chain(cert,key)
        self.context.options|=ssl.OP_NO_TICKET
        self.context.num_tickets=0
        self.allowed=set(allowed)
        self.lock=threading.RLock()
        self.connections={}
        self.counts={'authenticated':0,'authorized':0,'resource_denied':0,'handshake_failed':0,'withdrawn_connections':0}
        self.server=socket.socket(socket.AF_INET6 if ip.version==6 else socket.AF_INET,socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        self.server.bind((address,port));self.server.listen(16);self.server.settimeout(.1)
        self.port=self.server.getsockname()[1]
        self.stopped=threading.Event()
        self.thread=threading.Thread(target=self.accept,daemon=True);self.thread.start()
    def accept(self):
        while not self.stopped.is_set():
            try:conn,_=self.server.accept()
            except socket.timeout:continue
            except OSError:break
            threading.Thread(target=self.client,args=(conn,),daemon=True).start()
    def client(self,raw):
        conn=None
        try:
            raw.settimeout(1)
            conn=self.context.wrap_socket(raw,server_side=True)
            fp=hashlib.sha256(conn.getpeercert(binary_form=True)).hexdigest()
            with self.lock:
                self.counts['authenticated']+=1
                self.connections[conn]=fp
            while not self.stopped.is_set():
                token=recv_exact(conn,24)
                with self.lock:
                    if fp not in self.allowed:
                        self.counts['resource_denied']+=1
                        conn.sendall(b'DENY')
                        return
                    self.counts['authorized']+=1
                    conn.sendall(b'OKAY'+token)
        except ssl.SSLError:
            with self.lock:self.counts['handshake_failed']+=1
        except (OSError,EOFError):pass
        finally:
            with self.lock:self.connections.pop(conn,None)
            if conn:conn.close()
            raw.close()
    def grants(self,allowed):
        with self.lock:
            self.allowed=set(allowed)
            for sock,fp in list(self.connections.items()):
                if fp not in self.allowed:
                    self.counts['withdrawn_connections']+=1
                    try:sock.shutdown(socket.SHUT_RDWR)
                    except OSError:pass
                    sock.close()
                    self.connections.pop(sock,None)
        return self.stats()
    def stats(self):
        with self.lock:return {**self.counts,'active_sessions':len(self.connections),'allowed_fingerprints':sorted(self.allowed)}
    def close(self):
        self.stopped.set();self.server.close();self.grants([]);self.thread.join(timeout=2)


CLIENTS={}

def probe(address,port,ca,certificate=None,key=None,hostname='data-01.fixture.invalid',retained=None):
    sock=CLIENTS.get(retained) if retained else None
    success=False
    try:
        if sock is None:
            context=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.load_verify_locations(cafile=ca)
            context.verify_flags |= ssl.VERIFY_X509_STRICT
            context.minimum_version=ssl.TLSVersion.TLSv1_3
            if certificate:context.load_cert_chain(certificate,key)
            raw=socket.create_connection((address,port),timeout=1)
            try:sock=context.wrap_socket(raw,server_hostname=hostname)
            except Exception:raw.close();raise
        token=secrets.token_bytes(24)
        sock.sendall(token)
        decision=recv_exact(sock,4)
        if decision!=b'OKAY':return {'success':False,'observation':'RESOURCE_DENIED','tls_version':sock.version()}
        success=recv_exact(sock,24)==token
        result={'success':success,'observation':'AUTHENTICATED_RESOURCE_CHALLENGE', 'tls_version':sock.version(),
                'cipher':sock.cipher()[0], 'server_certificate_sha256':hashlib.sha256(sock.getpeercert(binary_form=True)).hexdigest()}
        if retained and success:CLIENTS[retained]=sock
        return result
    except (OSError,EOFError,ValueError) as exc:
        return {'success':False,'observation':type(exc).__name__}
    finally:
        if sock and (not retained or not success):
            sock.close()
            if retained:CLIENTS.pop(retained,None)
