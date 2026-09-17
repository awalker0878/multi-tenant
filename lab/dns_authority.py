"""Bounded test-only TCP authority implementing this integration's RFC2136 subset.

Binds loopback only, no recursion/forwarding, no native DNS software claimed.
It parses and authenticates real TSIG wire messages. Transactions are serialized
and prerequisites evaluated before any store swap. Fault switches are for tests.
"""
from __future__ import annotations
import copy
import socket
import socketserver
import struct
import threading
import dns.exception
import dns.flags
import dns.message
import dns.name
import dns.opcode
import dns.rcode
import dns.rdataclass
import dns.rdatatype
import dns.rrset
import dns.tsig
import dns.tsigkeyring


def exact(sock, n):
    out = b''
    while len(out) < n:
        part = sock.recv(n-len(out))
        if not part:
            raise EOFError
        out += part
    return out


class Authority:
    """Context-managed local authority; all test records are disposable memory."""
    def __init__(self, zone, key_name, secret):
        self.zone = dns.name.from_text(zone)
        self.key_name = dns.name.from_text(key_name)
        self.keyring = dns.tsigkeyring.from_text({key_name: secret})
        self.store = {}
        self.allowed_names = set()
        self.lock = threading.RLock()
        self.queries = 0
        self.update_requests = 0
        self.commits = 0
        self.invalid_authentication = 0
        self.before_update = None
        self.drop_update_reply = False
        self.fail_after_commit = False
        self.unsigned_answers = False
        self.authoritative_answers = True
        self.omit_negative_soa = False
        self.refuse_updates = False
        self.listener = None
        self.thread = None

    def __enter__(self):
        authority = self
        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                self.request.settimeout(2)
                try:
                    size = struct.unpack('!H', exact(self.request, 2))[0]
                    if not 12 <= size <= 65535:
                        return
                    msg = dns.message.from_wire(exact(self.request, size), keyring=authority.keyring)
                    if not msg.had_tsig or msg.keyname != authority.key_name or msg.keyalgorithm != dns.tsig.HMAC_SHA256:
                        with authority.lock:
                            authority.invalid_authentication += 1
                        return
                    reply = authority.respond(msg)
                    if reply is not None:
                        raw = reply.to_wire()
                        self.request.sendall(struct.pack('!H', len(raw)) + raw)
                except (EOFError, OSError, dns.exception.DNSException, ValueError):
                    with authority.lock:
                        authority.invalid_authentication += 1
        class Server(socketserver.ThreadingTCPServer):
            daemon_threads = True
            allow_reuse_address = False
        self.listener = Server(('127.0.0.1', 0), Handler)
        self.port = self.listener.server_address[1]
        self.thread = threading.Thread(target=self.listener.serve_forever, kwargs={'poll_interval': .03}, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.listener.shutdown()
        self.listener.server_close()
        self.thread.join(timeout=2)
        self.keyring = {}

    def allow(self, *names):
        self.allowed_names.update(str(dns.name.from_text(x)) for x in names)

    def set(self, name, rtype, ttl, values):
        with self.lock:
            self.store[(str(dns.name.from_text(name)), rtype)] = {'ttl': ttl, 'values': sorted(values)}

    def soa(self):
        return dns.rrset.from_text(str(self.zone), 60, 'IN', 'SOA',
                                   f'ns.fixture.invalid. hostmaster.fixture.invalid. {self.commits+1} 60 60 60 60')

    def respond(self, msg):
        with self.lock:
            if self.fail_after_commit and self.commits:
                return None
            reply = dns.message.make_response(msg)
            if self.authoritative_answers:
                reply.flags |= dns.flags.AA
            if dns.opcode.from_flags(msg.flags) == dns.opcode.QUERY:
                self.queries += 1
                if len(msg.question) != 1:
                    reply.set_rcode(dns.rcode.FORMERR)
                else:
                    q = msg.question[0]
                    key = (str(q.name), dns.rdatatype.to_text(q.rdtype))
                    if not q.name.is_subdomain(self.zone):
                        reply.set_rcode(dns.rcode.REFUSED)
                    elif q.name == self.zone and q.rdtype == dns.rdatatype.SOA:
                        reply.answer.append(self.soa())
                    elif key in self.store:
                        record = self.store[key]
                        vals = record['values']
                        if key[1] == 'TXT':
                            import json
                            vals = [json.dumps(x) for x in vals]
                        reply.answer.append(dns.rrset.from_text(key[0], record['ttl'], 'IN', key[1], *vals))
                    else:
                        if not any(k[0] == key[0] for k in self.store):
                            reply.set_rcode(dns.rcode.NXDOMAIN)
                        if not self.omit_negative_soa:
                            reply.authority.append(self.soa())
                if self.unsigned_answers:
                    reply.tsig = None
                return reply
            if dns.opcode.from_flags(msg.flags) != dns.opcode.UPDATE:
                reply.set_rcode(dns.rcode.NOTIMP)
                return reply
            self.update_requests += 1
            if len(msg.question) != 1 or msg.question[0].name != self.zone:
                reply.set_rcode(dns.rcode.NOTAUTH)
                return reply
            if self.refuse_updates:
                reply.set_rcode(dns.rcode.REFUSED)
                return reply
            if self.before_update:
                action, self.before_update = self.before_update, None
                action(self)
            # This fixture only grants the explicitly installed record names.
            if any(str(rr.name) not in self.allowed_names for rr in msg.authority):
                reply.set_rcode(dns.rcode.REFUSED)
                return reply
            for rr in msg.answer:
                name, typ = str(rr.name), dns.rdatatype.to_text(rr.rdtype)
                actual = self.store.get((name, typ))
                exists = any(k[0] == name for k in self.store) if typ == 'ANY' else actual is not None
                if rr.deleting == dns.rdataclass.NONE:
                    if exists:
                        reply.set_rcode(dns.rcode.YXDOMAIN if typ == 'ANY' else dns.rcode.YXRRSET)
                        return reply
                elif rr.deleting == dns.rdataclass.ANY:
                    if not exists:
                        reply.set_rcode(dns.rcode.NXDOMAIN if typ == 'ANY' else dns.rcode.NXRRSET)
                        return reply
                else:
                    values = sorted(b''.join(r.strings).decode('ascii') if typ == 'TXT' else r.to_text().lower() for r in rr)
                    if actual is None or values != actual['values']:
                        reply.set_rcode(dns.rcode.NXRRSET)
                        return reply
            new = copy.deepcopy(self.store)
            for rr in msg.authority:
                key = (str(rr.name), dns.rdatatype.to_text(rr.rdtype))
                if rr.deleting == dns.rdataclass.ANY:
                    new.pop(key, None)
                elif rr.deleting is not None or key[1] not in ('A', 'AAAA', 'PTR', 'TXT'):
                    reply.set_rcode(dns.rcode.REFUSED)
                    return reply
                else:
                    values = sorted(b''.join(r.strings).decode('ascii') if key[1] == 'TXT' else r.to_text().lower() for r in rr)
                    current = new.get(key, {'ttl': rr.ttl, 'values': []})
                    new[key] = {'ttl': rr.ttl, 'values': sorted(set(current['values']) | set(values))}
            self.store = new
            self.commits += 1
            return None if self.drop_update_reply else reply
