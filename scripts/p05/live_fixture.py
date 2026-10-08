"""Independent controlled Inventory contract and broker observers for E2 only."""
import base64
import copy
import hashlib
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import ssl
import sys
import threading
import urllib.request
import urllib.error

import importlib.util
spec=importlib.util.spec_from_file_location('p04_peer',Path(__file__).resolve().parents[1]/'p04/live_fixture.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
OriginalBroker=module.InventoryBroker
NativePeer=module.NativePeer
TlsProxy=module.TlsProxy


class InventoryContractPeer:
    def __init__(self, certificate, key, caller, governance, destinations, runtime_file=None):
        self.destinations=destinations
        self.reads=[]
        peer=self
        context=ssl.create_default_context(cafile=str(certificate))
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*_):pass
            def do_GET(self):
                parts=self.path.split('/')
                status,body=403,{'error':'denied'}
                if len(parts)==10 and self.headers.get('Authorization')=='Bearer '+caller:
                    _,_,_,tenant,_,application,environment,site,endpoint,generation=parts
                    data={'action':self.headers.get('X-Planning-Action'),'scope':{'site_id':site,'environment':environment,'resource_id':application}}
                    req=urllib.request.Request('https://127.0.0.1:8442/v1/tenants/'+tenant+'/planning-input-checks',data=json.dumps(data).encode(),headers={'Authorization':'Bearer '+governance,'X-Actor-Delegation':self.headers.get('X-Actor-Delegation',''),'Content-Type':'application/json'})
                    try:
                        with urllib.request.urlopen(req,context=context,timeout=5) as response:decision=json.load(response)
                        found=peer.destinations.get(endpoint)
                        if decision.get('allowed') is True and found and all(found[k]==v for k,v in {'tenant_id':tenant,'site_id':site,'generation_id':generation}.items()):
                            status,body=200,copy.deepcopy(found)
                            if runtime_file:
                                runtime=json.loads(Path(runtime_file).read_text())
                                proofs=[(r,json.loads(base64.b64decode(r['content_base64']))) for r in runtime['records'].values()]
                                matched=[(r,p) for r,p in proofs if p.get('inventory',{}).get('endpoint_id')==endpoint]
                                if len(matched)==1:
                                    envelope,payload=matched[0]
                                    body['capability_snapshot']={
                                        'definition_sha256':payload['definition_sha256'],
                                        'source_sha256':envelope['sha256'],
                                        'decision_sha256':payload['decision_sha256'],
                                        'scope_sha256':payload['scope_sha256'],
                                        'observed_at':payload['observed_at'],
                                        'expires_at':payload['expires_at'],
                                        'data':payload['snapshot'],
                                    }
                    except (OSError,ValueError):pass
                peer.reads.append({'path':self.path,'status':status})
                raw=json.dumps(body).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store, private');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        self.server=ThreadingHTTPServer(('127.0.0.1',8448),Handler)
        server_context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);server_context.load_cert_chain(str(certificate),str(key));self.server.socket=server_context.wrap_socket(self.server.socket,server_side=True)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def close(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)


class PlanningBroker(OriginalBroker):
    def __init__(self,root,private,run,private_values):
        super().__init__(root,private,run,private_values)
        definitions=json.loads((private/'broker-definitions.json').read_text())
        for exchange in ['planning.events','catalogue.events']:
            definitions['exchanges'].append({'name':exchange,'vhost':'product','type':'direct','durable':True,'auto_delete':False,'internal':False,'arguments':{}})
        for queue,source,routing in [('planning.inventory','inventory.events','inventory.facts.v1'),('planning.intent','catalogue.events','catalogue.intent.changed.v1'),('p05.observer','planning.events','planning.facts.v1')]:
            definitions['queues'].append({'name':queue,'vhost':'product','durable':True,'auto_delete':False,'arguments':{'x-queue-type':'quorum','x-delivery-limit':-1}})
            definitions['bindings'].append({'source':source,'vhost':'product','destination':queue,'destination_type':'queue','routing_key':routing,'arguments':{}})
        for user in ['planning','catalogue']:
            password=secrets.token_hex(32);private_values.append(password);file=private/(user+'-broker.password');file.write_text(password);salt=secrets.token_bytes(4)
            definitions['users'].append({'name':user,'password_hash':base64.b64encode(salt+hashlib.sha256(salt+password.encode()).digest()).decode(),'hashing_algorithm':'rabbit_password_hashing_sha256','tags':[]})
            definitions['permissions'].append({'user':user,'vhost':'product','configure':'^$','write':'^'+user+'\\.events$','read':'^planning\\.(inventory|intent)$' if user=='planning' else '^$'})
            self.environment[user.upper()+'_BROKER_PASSWORD_FILE']=str(file)
        for permission in definitions['permissions']:
            if permission['user']=='p04-observer':permission['read']='^(p04|p05)\\.observer$'
        self.environment.update(PLANNING_BROKER_HOST='127.0.0.1',PLANNING_BROKER_PORT='5679',PLANNING_BROKER_CA_FILE=str(private/'services.crt'))
        (private/'broker-definitions.json').write_text(json.dumps(definitions))
