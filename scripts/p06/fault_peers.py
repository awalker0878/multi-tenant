"""Independent transport faults and durable alert acknowledgements, never product shims."""
import http.client
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import ssl
import threading
import uuid

class TlsProxy:
    def __init__(self, port, upstream, certificate, key, fault_file=None):
        peer = self
        self.fault_file = fault_file
        self.forwarded = 0
        self.injected = 0

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def handle_request(self):
                length = int(self.headers.get('Content-Length', '0'))
                if length > 310000:
                    self.send_error(413)
                    return
                body = self.rfile.read(length) if length else None
                connection = http.client.HTTPConnection('127.0.0.1', upstream, timeout=15)
                try:
                    if peer.fault_file and peer.fault_file.exists():
                        rule=json.loads(peer.fault_file.read_text())
                        if rule.get('mode')=='unavailable':
                            raw=b'{"error":"injected_partition"}'
                            self.send_response(503);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
                    connection.request(self.command, self.path, body, dict(self.headers))
                    response = connection.getresponse()
                    wire = response.read()
                    peer.forwarded += 1
                    inject = False
                    if peer.fault_file and peer.fault_file.exists() and self.command == 'POST' and response.status in {201,202}:
                        rule = json.loads(peer.fault_file.read_text())
                        if rule.get('path') == self.path:
                            peer.fault_file.unlink()
                            inject = True
                            peer.injected += 1
                    if inject:
                        wire = b'{"error":"synthetic_response_loss"}'
                    self.send_response(503 if inject else response.status)
                    for name, value in response.getheaders():
                        if name.lower() not in ['content-length', 'transfer-encoding', 'connection']:
                            self.send_header(name, value)
                    self.send_header('Content-Length', str(len(wire)))
                    self.end_headers()
                    self.wfile.write(wire)
                finally:
                    connection.close()

            do_GET = do_POST = do_PUT = handle_request

        self.server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certificate, key)
        self.server.socket = context.wrap_socket(self.server.socket, server_side=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


class AlertReceiver:
    def __init__(self,certificate,key,credential,path):
        peer=self;self.receipts={};self.path=path
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*_):pass
            def do_POST(self):
                length=int(self.headers.get('Content-Length','0'))
                if self.path!='/v1/lifecycle-alerts' or self.headers.get('Authorization')!='Bearer '+credential or not 0<length<65536:
                    self.send_error(403);return
                event=json.loads(self.rfile.read(length));key=event['id']
                if key in peer.receipts and peer.receipts[key]['event']!=event:self.send_error(409);return
                peer.receipts[key]={'event':event,'receipt_id':str(uuid.uuid5(uuid.NAMESPACE_URL,key))}
                peer.path.write_text(json.dumps(list(peer.receipts.values()),indent=2)+'\n')
                raw=json.dumps({'event_id':key,'acknowledged':True,'receipt_id':peer.receipts[key]['receipt_id']}).encode()
                self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        self.server=ThreadingHTTPServer(('127.0.0.1',8451),Handler)
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(certificate,key);self.server.socket=context.wrap_socket(self.server.socket,server_side=True)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def close(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)
