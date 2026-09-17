"""Small original rtnetlink helper for per-interface IPv4 fixture forwarding.

Uses RTM_NEWLINK/IFLA_AF_SPEC/IFLA_INET_CONF as specified by Linux UAPI and
net/ipv4/devinet.c. Does not change any host-global setting or mount /proc.
"""
from __future__ import annotations
import os
from pathlib import Path
import socket
import struct


def attribute(kind: int, payload: bytes, nested: bool = False) -> bytes:
    length = len(payload) + 4
    return struct.pack('HH', length, kind | (0x8000 if nested else 0)) + payload + b'\0' * (-length % 4)


def set_forwarding(enabled: bool) -> dict:
    original, master = os.environ.get('HOSTING_LAB_ORIGINAL_NETNS'), os.environ.get('HOSTING_LAB_MASTER_NETNS')
    own = os.readlink('/proc/self/ns/net')
    if not original or not master or own in (original,master):
        raise RuntimeError('Per-interface changes require a disposable worker namespace')
    values = {}
    for index,name in socket.if_nameindex():
        if name == 'lo':
            continue
        if not name.startswith('v') or not name.endswith('b'):
            raise RuntimeError('Unknown non-fixture interface')
        # IPV4_DEVCONF_FORWARDING=1; ACCEPT_REDIRECTS=4; SEND_REDIRECTS=6.
        cfg = b''.join(attribute(k,struct.pack('I',value)) for k,value in [(1,int(enabled)),(4,0),(6,0)])
        spec = attribute(26,attribute(socket.AF_INET,attribute(1,cfg,True),True),True)
        body = struct.pack('BBHiII',socket.AF_UNSPEC,0,0,index,0,0)+spec
        message = struct.pack('IHHII',16+len(body),16,5,1,0)+body  # RTM_NEWLINK, REQUEST|ACK
        with socket.socket(socket.AF_NETLINK,socket.SOCK_RAW,socket.NETLINK_ROUTE) as sock:
            sock.settimeout(2)
            sock.sendto(message,(0,0))
            reply = sock.recv(8192)
        length,kind,_,sequence,_ = struct.unpack('IHHII',reply[:16])
        if kind != 2 or sequence != 1 or length < 20:
            raise RuntimeError('Unexpected rtnetlink acknowledgement')
        error = struct.unpack('i',reply[16:20])[0]
        if error:
            raise OSError(-error,os.strerror(-error))
        actual = Path(f'/proc/sys/net/ipv4/conf/{name}/forwarding').read_text().strip()
        if actual != str(int(enabled)):
            raise RuntimeError('Forwarding read-back mismatch')
        values[name] = actual
    return {'forwarding':str(int(enabled)),'interfaces':values,'mechanism':'rtnetlink-per-interface'}
