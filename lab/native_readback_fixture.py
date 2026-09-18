"""Disposable localhost HTTPS fixture, not a vendor emulator or production service.

Implements only enumerated GET response shapes needed by candidate observers.
Certificates/keys exist in a TemporaryDirectory and are removed on shutdown.
"""
from __future__ import annotations
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
from pathlib import Path
import ssl
import tempfile
import threading
import time
from urllib.parse import urlsplit
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from tools import readback_core as c
from tools import nsx_observe as nsx, nutanix_observe as nut

VPC='11111111-1111-4111-8111-111111111111'
TASK='ZXJnb24=:22222222-2222-4222-8222-222222222222'
TENANT='33333333-3333-4333-8333-333333333333'
EP='/infra/sites/default/enforcement-points/default'


def manifest(platform,origin):
    base={'platform':platform,'origin':origin,'operation_id':'op-lab-004','tenant_id':'tenant-001',
      'scope_id':'D01O','engineering_record_ref':'LAB-ENGINEERING-ONLY','target_binding_ref':'LAB-TARGET-ONLY',
      'contact_enabled':True}
    if platform=='nsx':
        path='/infra/domains/default/gateway-policies/tenant-001-quarantine'
        rules=[{'id':'deny-all','sequence_number':10,'action':'DROP','direction':'IN_OUT',
          'ip_protocol':'IPV4_IPV6','logged':True,'disabled':False,'source_groups':['ANY'],
          'destination_groups':['ANY'],'sources_excluded':False,'destinations_excluded':False,
          'services':['ANY'],'service_entries':[],'profiles':[],'scope':['/infra/tier-1s/domain-01']}]
        base.update({'profile':nsx.PROFILE,'resources':[{'kind':'gateway_policy','path':path,
          'expected':{'id':path.rsplit('/',1)[1],'path':path,'resource_type':'GatewayPolicy','_revision':7,
            'category':'Emergency','sequence_number':10,'stateful':True,'rules':rules},
          'realization':{'intent_version':'intent-23','enforcement_points':[EP]}}]})
    else:
        base.update({'profile':nut.PROFILE,'resources':[{'kind':'vpc','ext_id':VPC,'expected_etag':'"etag-7"',
          'expected':{'extId':VPC,'$objectType':'networking.v4.config.Vpc','tenantId':TENANT,
          'name':'tenant-001-domain-01','vpcType':'REGULAR','externalSubnets':[],'externallyRoutablePrefixes':[]}}],
          'task':{'ext_id':TASK,'operation':'Create VPC','created_after':(datetime.now(timezone.utc)-timedelta(minutes=2)).isoformat(),'entity_ids':[VPC]}})
    return base


def task_body(m):
    return {'data':{'$objectType':'prism.v4.config.Task','extId':m['task']['ext_id'],
       'operation':m['task']['operation'],'createdTime':(datetime.now(timezone.utc)-timedelta(seconds=30)).isoformat(),
       'completedTime':(datetime.now(timezone.utc)-timedelta(seconds=10)).isoformat(),
       'status':'SUCCEEDED','numberOfSubtasks':0,'numberOfEntitiesAffected':len(m['task']['entity_ids']),
       'entitiesAffected':[{'extId':v,'rel':'networking:config:vpc'} for v in m['task']['entity_ids']]}}


def nsx_status(r):
    return {'intent_path':r['path'],'intent_version':r['realization']['intent_version'],
        'publish_status':'REALIZED','consolidated_status':{'consolidated_status':'SUCCESS'},
        'consolidated_status_per_enforcement_point':[{'enforcement_point_path':p,
          'consolidated_status':{'consolidated_status':'SUCCESS'}} for p in r['realization']['enforcement_points']]}


def responses(m):
    if m['platform']=='nsx':
        return {t: {'status':200,'body':deepcopy(r['expected']) if t.startswith('/policy/api/v1'+r['path']) else nsx_status(r)}
           for r in m['resources'] for t in ('/policy/api/v1'+r['path'],nsx.status_target(r['path']))}
    result={nut.resource_target(r):{'status':200,'body':{'data':deepcopy(r['expected'])},'etag':r['expected_etag']} for r in m['resources']}
    result[nut.task_target(m)]={'status':200,'body':task_body(m)}
    return result


def credentials(directory:Path):
    now=datetime.now(timezone.utc)
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Increment04 disposable test CA')])
    ca=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True,path_length=0),critical=True)
        .add_extension(x509.KeyUsage(digital_signature=True,content_commitment=False,key_encipherment=False,data_encipherment=False,key_agreement=False,key_cert_sign=True,crl_sign=True,encipher_only=False,decipher_only=False),critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()),critical=False).sign(key,hashes.SHA256()))
    leaf=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    cert=(x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'localhost')]))
        .issuer_name(name).public_key(leaf.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True)
        .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address('127.0.0.1')),x509.DNSName('localhost')]),critical=False)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),critical=False)
        .add_extension(x509.KeyUsage(digital_signature=True,content_commitment=False,key_encipherment=True,data_encipherment=False,key_agreement=False,key_cert_sign=False,crl_sign=False,encipher_only=False,decipher_only=False),critical=True)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(key.public_key()),critical=False)
        .sign(key,hashes.SHA256()))
    (directory/'ca.pem').write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    (directory/'server.pem').write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    (directory/'server.key').write_bytes(leaf.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    (directory/'server.key').chmod(0o600)


class Fixture:
    def __init__(self):
        self.temp=tempfile.TemporaryDirectory(prefix='hosting-inc04-')
        self.directory=Path(self.temp.name);credentials(self.directory)
        self.routes={};self.requests=[];self.counts={};self.hook=None
        fixture=self
        class Handler(BaseHTTPRequestHandler):
            protocol_version='HTTP/1.1'
            def log_message(self,*_):pass
            def do_GET(self):
                fixture.requests.append({'method':'GET','path':self.path,'has_basic_auth':self.headers.get('Authorization','').startswith('Basic ')})
                fixture.counts[self.path]=fixture.counts.get(self.path,0)+1
                spec=deepcopy(fixture.routes.get(self.path,{'status':404,'body':{'error':'not in fixture'}}))
                if fixture.hook:
                    spec=fixture.hook(self.path,fixture.counts[self.path],spec)
                raw=spec.get('raw')
                data=raw if raw is not None else json.dumps(spec['body']).encode()
                self.send_response(spec.get('status',200))
                self.send_header('Content-Type',spec.get('content_type','application/json'))
                self.send_header('Content-Length',str(spec.get('length',len(data))))
                self.send_header('Connection','close')
                if 'etag' in spec:self.send_header('ETag',spec['etag'])
                for k,v in spec.get('headers',[]):self.send_header(k,v)
                self.end_headers()
                try:
                    if spec.get('chunk_delay'):
                        for byte in data:
                            self.wfile.write(bytes([byte]));self.wfile.flush();time.sleep(spec['chunk_delay'])
                    else:self.wfile.write(data)
                except (BrokenPipeError,ConnectionResetError,ssl.SSLError):pass
            def do_POST(self):
                fixture.requests.append({'method':'POST','path':self.path});self.send_error(405)
            do_PUT=do_POST;do_PATCH=do_POST;do_DELETE=do_POST
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.server.daemon_threads=True
        ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.minimum_version=ssl.TLSVersion.TLSv1_2
        ctx.load_cert_chain(str(self.directory/'server.pem'),str(self.directory/'server.key'))
        self.server.socket=ctx.wrap_socket(self.server.socket,server_side=True)
        self.thread=threading.Thread(target=self.server.serve_forever,kwargs={'poll_interval':0.02},daemon=True)
        self.thread.start();self.origin=f'https://127.0.0.1:{self.server.server_port}'
    def reset(self,platform):
        self.routes={};self.requests=[];self.counts={};self.hook=None
        m=manifest(platform,self.origin);self.routes=responses(m);return m
    def client(self,m,**kwargs):
        a=nsx if m['platform']=='nsx' else nut
        return c.ReadClient(self.origin,self.origin,'fixture-reader','temporary-fixture-secret',a.targets(m),str(self.directory/'ca.pem'),**kwargs)
    def close(self):
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=2);self.temp.cleanup()
    def __enter__(self):return self
    def __exit__(self,*_):self.close()
