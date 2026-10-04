"""Explicit pinned HTTPS alert-owner delivery and signed receipt verification.

Only a commissioned owner endpoint receives retained freshness alert intents.
This client never sends email or chooses contacts, follows redirects, contacts
native platforms, retries an uncertain POST, or turns an acknowledgement into
workload authority. A signed acknowledgement identifies the external owner's
actor; it does not invent a local operator acknowledgement.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
import hashlib
import http.client
import ipaddress
import re
import socket
import ssl
import time
from pathlib import Path
from threading import Timer
from urllib.parse import urlsplit

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .collector_settings import protected_path, bounded_timeout
from .model import _id, _json, _utc
from .native_credentials import decode_json, read_protected
from .trust import _decode, _keys


class AlertDeliveryHeld(RuntimeError):pass


class AlertDeliveryUnknown(AlertDeliveryHeld):
    """The owner may have accepted the original; explicit replay is required."""


@dataclass(frozen=True, slots=True)
class AlertOwnerTarget:
    owner_id: str
    origin: str
    connect_ip: str
    ca_bundle: Path
    ca_digest: str
    credential_file: Path = field(repr=False)
    receipt_public_key: bytes = field(repr=False)
    timeout_seconds: float = 5
    ownership_public_key: bytes | None = field(default=None,repr=False)
    minimum_ownership_revision: int | None = None

    @classmethod
    def parse(cls, document):
        required={'ownerId','origin','connectIp','caBundle','caDigest','credentialFile','receiptPublicKey','timeoutSeconds'}
        optional={'ownershipPublicKey','minimumOwnershipRevision'}
        if not isinstance(document,dict) or not required<=document.keys() or not document.keys()<=required|optional:
            raise ValueError('Exact alert owner target is required')
        if bool(document.keys()&optional)!=(optional<=document.keys()):raise ValueError('Complete ownership key and revision floor are required')
        doc=document
        url=urlsplit(doc['origin']);address=ipaddress.ip_address(doc['connectIp'])
        if (not _id(doc['ownerId']) or not isinstance(doc['origin'],str) or len(doc['origin'])>512
                or url.scheme!='https' or not url.hostname or url.username is not None or url.password is not None
                or url.path or url.query or url.fragment or url.netloc.endswith(':') or url.port==0
                or not re.fullmatch('[a-z0-9.:-]+',url.hostname)
                or any(char in doc['origin'] for char in '%\\?#')
                or str(address)!=doc['connectIp'] or address.is_unspecified or address.is_multicast
                or not isinstance(doc['caDigest'],str) or not re.fullmatch('[0-9a-f]{64}',doc['caDigest'])):
            raise ValueError('An exact protected alert-owner target is required')
        ownership_key=None;ownership_revision=None
        if optional<=doc.keys():
            ownership_key=_decode(doc['ownershipPublicKey'],32);ownership_revision=doc['minimumOwnershipRevision']
            if ownership_key==_decode(doc['receiptPublicKey'],32) or type(ownership_revision) is not int or not 1<=ownership_revision<2**63:
                raise ValueError('On-call authority must be independent from the alert receiver')
        return cls(doc['ownerId'],doc['origin'],doc['connectIp'],protected_path(doc['caBundle']),
                   doc['caDigest'],protected_path(doc['credentialFile']),
                   _decode(doc['receiptPublicKey'],32),bounded_timeout(doc['timeoutSeconds']),ownership_key,ownership_revision)


def intent_digest(intent):return hashlib.sha256(_json(intent).encode('ascii')).hexdigest()


def verify_receipt(document, intent, target, at):
    """Require the owner's current signature over exact intent and actor facts."""
    owned=target.ownership_public_key is not None
    envelope=_keys(document,{'receipt','signature','ownership'} if owned else {'receipt','signature'})
    required={'format','ownerId','receiptId','alertId','alertDigest','checkRecordDigest','status',
              'acceptedAt','observedAt','expiresAt','acknowledgedBy','acknowledgedAt'}
    receipt=_keys(envelope['receipt'],required|({'ownershipDigest','assignmentId','onCallSubject','deliveredBy'} if owned else set()))
    if not _utc(at):raise AlertDeliveryHeld('Current receipt-verification time is invalid')
    accepted,observed,expires=(datetime.fromisoformat(receipt[k]) for k in ('acceptedAt','observedAt','expiresAt'))
    if (not all(_utc(value) for value in (accepted,observed,expires))
            or receipt['format']!=('hosting-discovery-alert-owner-receipt/2' if owned else 'hosting-discovery-alert-owner-receipt/1')
            or receipt['ownerId']!=target.owner_id or not _id(receipt['receiptId'])
            or receipt['alertId']!=intent['alertId'] or receipt['alertDigest']!=intent_digest(intent)
            or receipt['checkRecordDigest']!=intent['checkRecordDigest']
            or not datetime.fromisoformat(intent['detectedAt'])<=accepted<=observed<=at<expires
            or at-observed>timedelta(minutes=5) or not timedelta(0)<expires-observed<=timedelta(minutes=15)
            or receipt['status'] not in ('DELIVERY_ACCEPTED','ACKNOWLEDGED')):
        raise AlertDeliveryHeld('Alert receipt is stale or differs from the retained intent')
    if receipt['status']=='ACKNOWLEDGED':
        ack=datetime.fromisoformat(receipt['acknowledgedAt'])
        if (not _id(receipt['acknowledgedBy']) or not _utc(ack) or not accepted<=ack<=observed):
            raise AlertDeliveryHeld('Owner acknowledgement is unattributed or inconsistent')
    elif receipt['acknowledgedBy'] is not None or receipt['acknowledgedAt'] is not None:
        raise AlertDeliveryHeld('Delivery acceptance cannot invent operator acknowledgement')
    if owned:
        from .alert_ownership import verify_ownership
        assignment,policy,digest=verify_ownership(envelope['ownership'],public_key=target.ownership_public_key,
            minimum_revision=target.minimum_ownership_revision,owner_id=target.owner_id,intent=intent,at=at)
        if (receipt['ownershipDigest']!=digest or receipt['assignmentId']!=assignment['assignmentId']
                or receipt['onCallSubject']!=assignment['onCallSubject'] or receipt['deliveredBy']!=assignment['monitorSubject']
                or expires>datetime.fromisoformat(policy['expiresAt'])
                or receipt['status']=='ACKNOWLEDGED' and receipt['acknowledgedBy']!=assignment['onCallSubject']):
            raise AlertDeliveryHeld('Receipt differs from independent scoped on-call ownership')
    Ed25519PublicKey.from_public_bytes(target.receipt_public_key).verify(
        _decode(envelope['signature'],64),_json(receipt).encode('ascii'))
    return document


class HttpsAlertOwner:
    def __init__(self,target:AlertOwnerTarget):
        if not isinstance(target,AlertOwnerTarget):raise TypeError('Pinned alert owner is required')
        self.target=target

    def deliver(self,intent,authorize,clock):return self._request('POST',intent,authorize,clock)
    def refresh(self,intent,authorize,clock):return self._request('GET',intent,authorize,clock)

    def _request(self,method,intent,authorize,clock):
        target=self.target;url=urlsplit(target.origin)
        if method not in ('POST','GET') or not re.fullmatch('[0-9a-f]{64}',intent['alertId']):
            raise AlertDeliveryHeld('Invalid alert-owner operation')
        route='/v1/discovery/alerts' if method=='POST' else '/v1/discovery/alerts/'+intent['alertId']+'/receipt'
        body=_json(intent).encode('ascii') if method=='POST' else None
        if body is not None and len(body)>8192:raise AlertDeliveryHeld('Alert intent exceeds its transport bound')
        deadline=time.monotonic()+target.timeout_seconds;active=[None];attempted=False
        response=connection=None
        def current():
            at=clock()
            if not _utc(at):raise AlertDeliveryHeld('Alert-owner clock is invalid')
            authorize(at)
            return at
        def remaining():
            value=deadline-time.monotonic()
            if value<=0:raise AlertDeliveryHeld('Alert-owner request deadline expired')
            return value
        def stop():
            if active[0] is not None:
                try:active[0].shutdown(socket.SHUT_RDWR)
                except OSError:pass
        timer=Timer(target.timeout_seconds,stop);timer.daemon=True;timer.start()
        try:
            current()
            ca=read_protected(target.ca_bundle,1024*1024,secret=False)
            if hashlib.sha256(ca).hexdigest()!=target.ca_digest:raise AlertDeliveryHeld('Alert-owner CA changed')
            token=read_protected(target.credential_file,16384).decode('ascii').strip()
            if not 16<=len(token)<=16384 or any(not 33<=ord(c)<=126 for c in token):
                raise AlertDeliveryHeld('Protected alert-owner credential is invalid')
            context=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.minimum_version=ssl.TLSVersion.TLSv1_2
            context.load_verify_locations(cadata=ca.decode('ascii'))
            raw=socket.create_connection((target.connect_ip,url.port or 443),timeout=remaining());active[0]=raw
            tls=context.wrap_socket(raw,server_hostname=url.hostname,do_handshake_on_connect=False);active[0]=tls
            tls.settimeout(remaining());tls.do_handshake();current()
            connection=http.client.HTTPConnection(url.hostname,url.port or 443,timeout=remaining())
            connection.auto_open=0;connection.sock=tls
            tls.settimeout(remaining());current()
            attempted=True
            connection.request(method,route,body=body,headers={'Authorization':'Bearer '+token,
                'Content-Type':'application/json','Accept':'application/json','Accept-Encoding':'identity',
                'Connection':'close','Idempotency-Key':intent['alertId']})
            response=connection.getresponse();remaining()
            lengths=response.headers.get_all('Content-Length',[])
            if (response.status!=200 or len(lengths)!=1 or not lengths[0].isascii() or not lengths[0].isdigit()
                    or len(lengths[0])>5 or not 1<=int(lengths[0])<=8192
                    or response.headers.get('Transfer-Encoding') is not None
                    or response.headers.get('Content-Encoding') is not None
                    or response.headers.get_all('Content-Type',[])!=['application/json']):
                raise AlertDeliveryHeld('Invalid bounded alert-owner receipt response')
            data=response.read(int(lengths[0])+1);remaining()
            if len(data)!=int(lengths[0]):raise AlertDeliveryHeld('Truncated alert-owner receipt')
            receipt=verify_receipt(decode_json(data,8192),intent,target,current())
            current();remaining()
            return receipt
        except Exception:
            if attempted and method=='POST':raise AlertDeliveryUnknown('Original alert delivery outcome is unknown') from None
            raise AlertDeliveryHeld('Verified alert-owner receipt is unavailable') from None
        finally:
            timer.cancel()
            if response is not None:response.close()
            if connection is not None:connection.close()
            if active[0] is not None:active[0].close()
            timer.join()
