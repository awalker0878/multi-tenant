"""Bounded HTTPS alert delivery and an isolated acknowledged-receipt fixture."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import secrets
import ssl
import threading
import urllib.parse
import urllib.request
import uuid

SERVICES = frozenset(('console','governance','catalogue','assurance','planning','inventory','lifecycle'))


def validate(value):
    if not isinstance(value,dict) or set(value)!= {'event_id','service','condition','observed_at','source_revision'}:
        raise ValueError('Invalid alert envelope')
    if value['service'] not in SERVICES or value['condition']!='dependency_unavailable':
        raise ValueError('Invalid alert condition')
    uuid.UUID(value['event_id'])
    datetime.fromisoformat(value['observed_at'])
    if len(value['source_revision'])!=40 or any(c not in '0123456789abcdef' for c in value['source_revision']):
        raise ValueError('Invalid source revision')


def deliver(endpoint, token, ca, alert):
    validate(alert)
    parsed=urllib.parse.urlsplit(endpoint)
    if parsed.scheme!='https' or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Alert delivery requires a credential-free HTTPS URL')
    request=urllib.request.Request(endpoint,data=json.dumps(alert).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+token},method='POST')
    # Redirects cannot forward receiver credentials to another authority.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):return None
    opener=urllib.request.build_opener(NoRedirect,urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=str(ca))))
    with opener.open(request,timeout=5) as response:
        ack=json.loads(response.read(4097))
        if response.status!=202 or set(ack)!={'event_id','acknowledged'} or ack['event_id']!=alert['event_id'] or ack['acknowledged'] is not True:
            raise ValueError('Receiver did not acknowledge the exact alert')
    return ack


@contextmanager
def fixture_receiver(certificates):
    """Synthetic receiver only: no email, chat or person-directed notification."""
    token=secrets.token_urlsafe(32);receipts=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            if self.path!='/alerts' or not hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+token):
                self.send_error(403);return
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=4096:raise ValueError('Invalid size')
                alert=json.loads(self.rfile.read(length));validate(alert)
            except (ValueError,KeyError,TypeError):
                self.send_error(422);return
            receipts.append(alert)
            self.send_response(202);self.send_header('Content-Type','application/json');self.end_headers()
            self.wfile.write(json.dumps({'event_id':alert['event_id'],'acknowledged':True}).encode())
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.daemon_threads=True
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.minimum_version=ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(str(certificates/'console.crt'),str(certificates/'console.key'))
    server.socket=context.wrap_socket(server.socket,server_side=True)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield 'https://localhost:'+str(server.server_port)+'/alerts',token,receipts
    finally:server.shutdown();server.server_close();thread.join(timeout=5)


def observed_alert(service, revision):
    return {'event_id':str(uuid.uuid4()),'service':service,'condition':'dependency_unavailable','observed_at':datetime.now(timezone.utc).isoformat(),'source_revision':revision}
