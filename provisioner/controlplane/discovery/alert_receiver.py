"""Installed HTTPS alert receiver with original custody and current on-call IAM.

This owner accepts discovery alert intents and signs delivery/acknowledgement
receipts. It cannot collect, publish inventory, approve jobs or operate native
platforms. The independent signed rota is distinct from its receipt signing key.
"""
import argparse
import base64
from contextlib import contextmanager
from dataclasses import dataclass,field
from datetime import datetime,timezone,timedelta
import hashlib
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import ipaddress
import json
import os
from pathlib import Path
import re
import signal
import socket
import ssl
from threading import BoundedSemaphore,Thread,Timer
import time

import psycopg
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from provisioner.controlplane.authority.directory import PostgresRoleDirectory
from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.authority.oidc import OIDCIdentityProvider
from provisioner.controlplane.authority.service import DISCOVERY_MONITOR,require_scoped_role
from .alert_ownership import SignedFileAlertOwnership
from .alert_transport import AlertDeliveryHeld,intent_digest
from .collector_settings import protected_path
from .model import _id,_json,_scope,_utc
from .monitor_runtime import _secure_dsn,_required
from .native_credentials import decode_json,read_protected
from .review_files import private_parent,publish_once,read_private
from .service_enrollment import ServiceEnrollment
from .trust import _decode,_keys


_SHA=re.compile('[0-9a-f]{64}')


def validate_intent(value):
    doc=_keys(value,{'format','alertId','environmentId','scope','checkId','checkRecordDigest','severity',
        'issueCodes','changeKinds','detectedAt','notificationRequired','notificationAttempted','deliveryOwner',
        'collectionRequested','executionAuthorized'})
    if (doc['format']!='hosting-discovery-freshness-alert-intent/1'
            or any(not isinstance(doc[name],str) or _SHA.fullmatch(doc[name]) is None for name in ('alertId','checkRecordDigest'))
            or any(not _id(doc[name]) for name in ('environmentId','checkId'))
            or doc['severity'] not in ('WARNING','CRITICAL') or doc['deliveryOwner']!='EXTERNAL'
            or doc['notificationRequired'] is not True
            or any(doc[name] is not False for name in ('notificationAttempted','collectionRequested','executionAuthorized'))
            or not isinstance(doc['scope'],dict) or not _scope(PlanScope(**doc['scope']))
            or not _utc(datetime.fromisoformat(doc['detectedAt']))):
        raise AlertDeliveryHeld('Invalid scoped notification intent')
    for name in ('issueCodes','changeKinds'):
        items=doc[name]
        if not isinstance(items,list) or len(items)>32 or any(not _id(item) for item in items) or len(set(items))!=len(items):
            raise AlertDeliveryHeld('Invalid bounded notification issues')
    if not doc['issueCodes'] or len(_json(doc).encode('ascii'))>8192:
        raise AlertDeliveryHeld('Notification intent exceeds its bound')
    return doc


class PrivateAlertInbox:
    """One immutable original acceptance and attributed ack per assignment."""
    def __init__(self,directory):
        self.directory=protected_path(str(directory));self._identity=None
        with private_parent(str(self.directory/'probe')) as (parent,_):
            info=os.fstat(parent);self._identity=(info.st_dev,info.st_ino,info.st_uid)
        if self._identity[2]!=os.geteuid():raise PermissionError('Alert inbox is not owned by this service')

    def path(self,name):return str(self.directory/name)

    def recheck(self):
        with private_parent(self.path('probe')) as (parent,_):
            info=os.fstat(parent)
            if (info.st_dev,info.st_ino,info.st_uid)!=self._identity:
                raise PermissionError('Alert inbox identity changed')

    @contextmanager
    def transaction(self):
        import fcntl
        self.recheck()
        with private_parent(self.path('owner.lock')) as (parent,name):
            fd=os.open(name,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC,0o600,dir_fd=parent)
            try:
                info=os.fstat(fd)
                if info.st_size or info.st_nlink!=1 or info.st_mode&0o077 or info.st_uid!=os.geteuid():
                    raise PermissionError('Alert owner lock is invalid')
                end=time.monotonic()+.5
                while True:
                    try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);break
                    except BlockingIOError:
                        if time.monotonic()>=end:raise AlertDeliveryHeld('Alert receiver is busy')
                        time.sleep(.01)
                self.recheck()
                linked=os.stat(name,dir_fd=parent,follow_symlinks=False)
                if (linked.st_dev,linked.st_ino)!=(info.st_dev,info.st_ino):raise PermissionError('Alert owner lock was replaced')
                yield
            finally:os.close(fd)

    def get(self,alert_id):
        if not isinstance(alert_id,str) or _SHA.fullmatch(alert_id) is None:raise ValueError('Exact alert identity is required')
        try:raw=read_private(self.path(alert_id+'.accepted.json'),16384)
        except FileNotFoundError:return None
        doc=_keys(decode_json(raw,16384),{'intent','ownerId','deliveredBy','acceptedAt','recordDigest'})
        validate_intent(doc['intent'])
        body={key:value for key,value in doc.items() if key!='recordDigest'}
        if (doc['intent']['alertId']!=alert_id or hashlib.sha256(_json(body).encode('ascii')).hexdigest()!=doc['recordDigest']
                or _json(doc).encode('ascii')!=raw):raise AlertDeliveryHeld('Original alert acceptance changed')
        return doc

    def accept(self,intent,owner_id,subject,at,recheck):
        original=self.get(intent['alertId'])
        if original is not None:
            if original['intent']!=intent or (original['ownerId'],original['deliveredBy'])!=(owner_id,subject):
                raise AlertDeliveryHeld('Alert idempotency identity differs from its original')
            return original
        if len(os.listdir(self.directory))>=100001:raise AlertDeliveryHeld('Alert inbox retention ceiling reached')
        body={'intent':intent,'ownerId':owner_id,'deliveredBy':subject,'acceptedAt':at.isoformat()}
        body['recordDigest']=hashlib.sha256(_json(body).encode('ascii')).hexdigest()
        publish_once(self.path(intent['alertId']+'.accepted.json'),_json(body).encode('ascii'),recheck)
        return body

    def acknowledgement(self,alert_id,assignment_id):
        name=hashlib.sha256(assignment_id.encode('ascii')).hexdigest()
        try:raw=read_private(self.path(alert_id+'.ack-'+name+'.json'),8192)
        except FileNotFoundError:return None
        doc=_keys(decode_json(raw,8192),{'alertId','alertDigest','assignmentId','acknowledgedBy','acknowledgedAt','ownershipDigest','recordDigest'})
        body={key:value for key,value in doc.items() if key!='recordDigest'}
        if (doc['alertId']!=alert_id or doc['assignmentId']!=assignment_id or _json(doc).encode('ascii')!=raw
                or hashlib.sha256(_json(body).encode('ascii')).hexdigest()!=doc['recordDigest']):
            raise AlertDeliveryHeld('Retained acknowledgement changed')
        return doc

    def acknowledge(self,intent,assignment,ownership_digest,subject,at,recheck):
        original=self.acknowledgement(intent['alertId'],assignment['assignmentId'])
        if original is not None:
            if (original['alertDigest'],original['acknowledgedBy'],original['ownershipDigest'])!=(intent_digest(intent),subject,ownership_digest):
                raise AlertDeliveryHeld('Acknowledgement identity changed')
            return original
        body={'alertId':intent['alertId'],'alertDigest':intent_digest(intent),'assignmentId':assignment['assignmentId'],
              'acknowledgedBy':subject,'acknowledgedAt':at.isoformat(),'ownershipDigest':ownership_digest}
        body['recordDigest']=hashlib.sha256(_json(body).encode('ascii')).hexdigest()
        suffix=hashlib.sha256(assignment['assignmentId'].encode('ascii')).hexdigest()
        publish_once(self.path(intent['alertId']+'.ack-'+suffix+'.json'),_json(body).encode('ascii'),recheck)
        return body


class AlertReceiver:
    def __init__(self,*,owner_id,inbox:PrivateAlertInbox,ownership:SignedFileAlertOwnership,
                 identities,signing_key:Ed25519PrivateKey,recheck,clock=lambda:datetime.now(timezone.utc)):
        if (not _id(owner_id) or not isinstance(inbox,PrivateAlertInbox) or not isinstance(ownership,SignedFileAlertOwnership)
                or not isinstance(signing_key,Ed25519PrivateKey) or not isinstance(identities,OIDCIdentityProvider)
                or not callable(recheck) or not callable(clock)):
            raise TypeError('Actual enrolled alert receiver owners are required')
        if signing_key.public_key().public_bytes_raw()==ownership.public_key:
            raise ValueError('Receipt and on-call assignment authorities must be independent')
        self.owner_id=owner_id;self.inbox=inbox;self.ownership=ownership;self.identities=identities
        self.signing_key=signing_key;self.recheck=recheck;self.clock=clock;self.last_clock=None

    def now(self):
        at=self.clock()
        if not _utc(at) or self.last_clock is not None and at<self.last_clock:
            raise AlertDeliveryHeld('Alert receiver clock regressed')
        self.last_clock=at;return at

    def current(self,credential,intent,*,acknowledgement=False):
        self.recheck();self.inbox.recheck();at=self.now()
        principal=self.identities.authenticate(credential)
        ownership,assignment,policy,digest=self.ownership.current(intent,at)
        scope=PlanScope(**intent['scope'])
        if (principal.organization_id,principal.tenant_id)!=(scope.organization_id,scope.tenant_id):
            raise PermissionError('Caller is outside the alert tenant')
        if acknowledgement:
            if principal.kind!='HUMAN' or principal.subject!=assignment['onCallSubject']:
                raise PermissionError('Current signed on-call assignment is required')
        else:
            if principal.kind!='SERVICE' or principal.subject!=assignment['monitorSubject']:
                raise PermissionError('Current enrolled monitor service is required')
            require_scoped_role(principal,DISCOVERY_MONITOR,scope,at)
        if not principal.issued_at<=at<principal.expires_at:
            raise PermissionError('Caller session is expired')
        self.ownership.retain_revision(self.inbox.directory,ownership)
        return principal,ownership,assignment,policy,digest,at

    def receipt(self,original,credential):
        intent=original['intent'];principal,ownership,assignment,policy,digest,at=self.current(credential,intent)
        if original['ownerId']!=self.owner_id or original['deliveredBy']!=principal.subject:
            raise AlertDeliveryHeld('Original alert has a different current receiver or monitor')
        accepted=datetime.fromisoformat(original['acceptedAt'])
        if not datetime.fromisoformat(intent['detectedAt'])<=accepted<=at:raise AlertDeliveryHeld('Original alert clock is inconsistent')
        ack=self.inbox.acknowledgement(intent['alertId'],assignment['assignmentId'])
        if ack is not None and (ack['ownershipDigest'],ack['acknowledgedBy'],ack['alertDigest'])!=(digest,assignment['onCallSubject'],intent_digest(intent)):
            raise AlertDeliveryHeld('Historic acknowledgement is outside current on-call ownership')
        value={'format':'hosting-discovery-alert-owner-receipt/2','ownerId':self.owner_id,
            'receiptId':'receipt-'+hashlib.sha256((original['recordDigest']+digest+at.isoformat()).encode('ascii')).hexdigest()[:32],
            'alertId':intent['alertId'],'alertDigest':intent_digest(intent),'checkRecordDigest':intent['checkRecordDigest'],
            'status':'DELIVERY_ACCEPTED' if ack is None else 'ACKNOWLEDGED','acceptedAt':accepted.isoformat(),
            'observedAt':at.isoformat(),'expiresAt':min(at+timedelta(minutes=5),datetime.fromisoformat(policy['expiresAt'])).isoformat(),
            'acknowledgedBy':None if ack is None else ack['acknowledgedBy'],'acknowledgedAt':None if ack is None else ack['acknowledgedAt'],
            'ownershipDigest':digest,'assignmentId':assignment['assignmentId'],'onCallSubject':assignment['onCallSubject'],
            'deliveredBy':principal.subject}
        result={'receipt':value,'signature':base64.b64encode(self.signing_key.sign(_json(value).encode('ascii'))).decode('ascii'),
                'ownership':ownership}
        if len(_json(result).encode('ascii'))>8192:raise AlertDeliveryHeld('Signed scoped ownership receipt exceeds its transport bound')
        self.current(credential,intent)
        return result

    def deliver(self,intent,credential):
        intent=validate_intent(intent)
        with self.inbox.transaction():
            principal,*_,at=self.current(credential,intent)
            if datetime.fromisoformat(intent['detectedAt'])>at:raise AlertDeliveryHeld('Future alert intent')
            original=self.inbox.accept(intent,self.owner_id,principal.subject,at,lambda:self.current(credential,intent))
            return self.receipt(original,credential)

    def refresh(self,alert_id,credential):
        with self.inbox.transaction():
            original=self.inbox.get(alert_id)
            if original is None:raise AlertDeliveryHeld('Original alert is not retained')
            return self.receipt(original,credential)

    def acknowledge(self,alert_id,body,credential):
        with self.inbox.transaction():
            original=self.inbox.get(alert_id)
            if original is None:raise AlertDeliveryHeld('Original alert is not retained')
            intent=original['intent'];_keys(body,{'alertId','alertDigest','checkRecordDigest'})
            if body!={'alertId':alert_id,'alertDigest':intent_digest(intent),'checkRecordDigest':intent['checkRecordDigest']}:
                raise AlertDeliveryHeld('Acknowledgement does not select the original retained intent')
            principal,_,assignment,_,digest,at=self.current(credential,intent,acknowledgement=True)
            if datetime.fromisoformat(original['acceptedAt'])>at:raise AlertDeliveryHeld('Acknowledgement predates acceptance')
            ack=self.inbox.acknowledge(intent,assignment,digest,principal.subject,at,
                lambda:self.current(credential,intent,acknowledgement=True))
            self.current(credential,intent,acknowledgement=True)
            return {'format':'hosting-discovery-on-call-acknowledgement/1','status':'ACKNOWLEDGEMENT_RETAINED',
                    'alertId':alert_id,'assignmentId':assignment['assignmentId'],'recordDigest':ack['recordDigest'],
                    'executionAuthorized':False}


class AlertReceiverServer(ThreadingHTTPServer):
    daemon_threads=True;block_on_close=True
    def __init__(self,address,receiver,*,tls_context,max_connections=16):
        self.receiver=receiver;self.tls_context=tls_context;self.slots=BoundedSemaphore(max_connections)
        super().__init__(address,_Handler)

    def get_request(self):
        raw,address=super().get_request();raw.settimeout(5)
        if not self.slots.acquire(blocking=False):raw.close();raise OSError('Alert receiver connection ceiling')
        try:return self.tls_context.wrap_socket(raw,server_side=True),address
        except BaseException:self.slots.release();raw.close();raise

    def shutdown_request(self,request):
        try:super().shutdown_request(request)
        finally:self.slots.release()


class _Handler(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def log_message(self,*args):pass
    def handle(self):
        def stop():
            try:self.connection.shutdown(socket.SHUT_RDWR)
            except OSError:pass
        timer=Timer(5,stop);timer.daemon=True;timer.start()
        try:
            try:super().handle()
            except (OSError,ssl.SSLError):pass
        finally:timer.cancel();timer.join()
    def do_POST(self):self.dispatch('POST')
    def do_GET(self):self.dispatch('GET')
    def dispatch(self,method):
        self.close_connection=True
        try:
            auth=self.headers.get_all('Authorization',[])
            if len(auth)!=1 or not auth[0].startswith('Bearer ') or not 1<=len(auth[0])<=16391:
                raise PermissionError('Current bearer identity required')
            credential=auth[0][7:]
            owner=self.server.receiver
            if method=='POST':
                lengths=self.headers.get_all('Content-Length',[])
                if (len(lengths)!=1 or not lengths[0].isdigit() or not 1<=int(lengths[0])<=8192
                        or self.headers.get('Transfer-Encoding') is not None or self.headers.get('Content-Encoding') is not None
                        or self.headers.get_all('Content-Type',[])!=['application/json']):
                    raise ValueError('Bounded owner JSON required')
                raw=self.rfile.read(int(lengths[0]));body=decode_json(raw,8192)
            else:body=None
            if method=='POST' and self.path=='/v1/discovery/alerts':
                intent=validate_intent(body)
                if self.headers.get_all('Idempotency-Key',[])!=[intent['alertId']]:raise ValueError('Exact original alert idempotency required')
                result=owner.deliver(intent,credential)
            else:
                match=re.fullmatch('/v1/discovery/alerts/([0-9a-f]{64})/(receipt|acknowledge)',self.path)
                if match is None:raise ValueError('Unsupported alert receiver route')
                alert_id,action=match.groups()
                if method=='GET' and action=='receipt':result=owner.refresh(alert_id,credential)
                elif method=='POST' and action=='acknowledge':result=owner.acknowledge(alert_id,body,credential)
                else:raise ValueError('Unsupported alert receiver method')
            status=200;raw=_json(result).encode('ascii')
        except PermissionError:status=403;raw=b'{"status":"OWNER_HELD"}'
        except Exception:status=409;raw=b'{"status":"OWNER_HELD"}'
        self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)))
        self.send_header('Connection','close');self.end_headers();self.wfile.write(raw)


def create_server(path,values):
    path=protected_path(str(path));raw=read_protected(path,65536)
    config=_keys(decode_json(raw,65536),{'format','ownerId','bindIp','bindPort','certificateFile','keyFile',
        'receiptKeyFile','receiptPublicKey','inboxDirectory','ownershipFile','ownershipPublicKey','minimumOwnershipRevision',
        'serviceEnrollmentFile','serviceEnrollmentDigest','maxConnections'})
    address=ipaddress.ip_address(config['bindIp'])
    if (config['format']!='hosting-discovery-alert-receiver/1' or address.is_unspecified or address.is_multicast
            or str(address)!=config['bindIp'] or type(config['bindPort']) is not int or not 1<=config['bindPort']<=65535
            or type(config['maxConnections']) is not int or not 1<=config['maxConnections']<=64):
        raise ValueError('An exact bounded alert receiver deployment is required')
    enrollment=ServiceEnrollment.from_file(config['serviceEnrollmentFile'],config['serviceEnrollmentDigest'])
    enrollment.require_store('alert-inbox',config['inboxDirectory'])
    digest=hashlib.sha256(raw).hexdigest()
    def recheck():
        enrollment.require_current()
        if hashlib.sha256(read_protected(path,65536)).hexdigest()!=digest:raise PermissionError('Alert receiver deployment changed')
    certificate=protected_path(config['certificateFile']);server_key=protected_path(config['keyFile'])
    cert_raw=read_protected(certificate,1048576,secret=False);key_raw=read_protected(server_key,65536)
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.minimum_version=ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certificate,server_key)
    if read_protected(certificate,1048576,secret=False)!=cert_raw or read_protected(server_key,65536)!=key_raw:
        raise PermissionError('Alert receiver TLS identity changed during loading')
    key=serialization.load_pem_private_key(read_protected(protected_path(config['receiptKeyFile']),65536),password=None)
    if not isinstance(key,Ed25519PrivateKey) or key.public_key().public_bytes_raw()!=_decode(config['receiptPublicKey'],32):
        raise PermissionError('Receipt signing key is not the enrolled receiver key')
    directory_dsn=_secure_dsn(_required(values,'HOSTING_DIRECTORY_DSN'))
    identities=OIDCIdentityProvider(issuer=_required(values,'HOSTING_OIDC_ISSUER'),audience=_required(values,'HOSTING_ALERT_OWNER_AUDIENCE'),
        jwks_uri=_required(values,'HOSTING_OIDC_JWKS_URI'),directory=PostgresRoleDirectory(lambda:psycopg.connect(directory_dsn,connect_timeout=5,autocommit=False)),
        step_up_acr=frozenset({'alert-owner-unused-step-up'}))
    ownership=SignedFileAlertOwnership(config['ownershipFile'],public_key=_decode(config['ownershipPublicKey'],32),
        minimum_revision=config['minimumOwnershipRevision'],owner_id=config['ownerId'])
    receiver=AlertReceiver(owner_id=config['ownerId'],inbox=PrivateAlertInbox(config['inboxDirectory']),ownership=ownership,
        identities=identities,signing_key=key,recheck=recheck)
    recheck()
    return AlertReceiverServer((config['bindIp'],config['bindPort']),receiver,tls_context=context,max_connections=config['maxConnections'])


class _Parser(argparse.ArgumentParser):
    def error(self,message):raise ValueError('Invalid alert owner arguments')


def main(argv=None):
    parser=_Parser(description=__doc__,allow_abbrev=False);parser.add_argument('--config',required=True)
    try:
        args=parser.parse_args(argv);server=create_server(args.config,os.environ)
        def stop(*_):Thread(target=server.shutdown,daemon=True).start()
        for name in ('SIGINT','SIGTERM'):
            if hasattr(signal,name):signal.signal(getattr(signal,name),stop)
        try:server.serve_forever(poll_interval=.1)
        finally:server.server_close()
        return 0
    except KeyboardInterrupt:return 130
    except Exception:
        print('{"format":"hosting-discovery-alert-receiver/1","status":"OWNER_HELD","executionAuthorized":false}')
        return 2


if __name__=='__main__':raise SystemExit(main())
