"""Small sealed client for the private per-command guest authority socket."""
import hashlib
import json
import os
from pathlib import Path
import socket
import stat
import struct
import re
import shlex
from uuid import UUID
from uuid import uuid4
from provisioner.execution.guest_native_profiles import NATIVE_GUEST_PROFILES


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def machine_command(command, target, native):
    if (type(command) is not str or not 0 < len(command.encode()) <= 131072
            or '\x00' in command or not re.fullmatch('[0-9a-f]{32}', target['machine_id'])):
        raise ValueError('Bounded owned command and exact guest machine required')
    checks = 'test "$(cat /etc/machine-id)" = ' + shlex.quote(target['machine_id']) + ' || exit 125; '
    if NATIVE_GUEST_PROFILES[native[0]]['dmi_matches_native_id'] or len(native) == 6:
        expected = native[5] if len(native) == 6 else native[4]
        checks += 'test "$(sudo -n cat /sys/class/dmi/id/product_uuid | tr A-F a-f)" = ' + shlex.quote(str(UUID(expected))) + ' || exit 125; '
    return '/bin/sh -c ' + shlex.quote(checks + 'exec /bin/sh -c ' + shlex.quote(command))


def load_session(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077 or info.st_size > 65536:
            raise PermissionError('The original guest command session is not private')
        raw = os.read(descriptor, 65537)
        if len(raw) > 65536:
            raise PermissionError('Guest command session exceeds its bound')
        value = json.loads(raw)
        if type(value) is not dict or value.keys() != {'socket', 'binding_digest', 'target', 'native', 'ssh'}:
            raise PermissionError('Exact original guest command session required')
        return value
    finally:
        os.close(descriptor)


def authorize(session, *, command, in_data=b''):
    """No credentials/identity in this protocol; the server owns the binding."""
    path = Path(session['socket'])
    info = path.lstat()
    if (not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.geteuid()
            or info.st_mode & 0o077 or len(str(path).encode()) > 107
            or path.parent.stat().st_mode & 0o077):
        raise PermissionError('Private original guest command socket unavailable')
    request = {'format': 'hosting-guest-command-check/1', 'request_id': uuid4().hex,
               'binding_digest': session['binding_digest'],
               'command_digest': hashlib.sha256(encoded(command)).hexdigest(),
               'input_digest': hashlib.sha256(in_data or b'').hexdigest()}
    raw = encoded(request)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(15)
        connection.connect(str(path))
        _pid, uid, _gid = struct.unpack('3i', connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        if uid != os.geteuid() or path.lstat().st_ino != info.st_ino:
            raise PermissionError('The original command socket owner changed')
        connection.sendall(raw + b'\n'); connection.shutdown(socket.SHUT_WR)
        chunks, count = [], 0
        while True:
            chunk = connection.recv(1024)
            if not chunk:
                break
            count += len(chunk)
            if count > 4096:
                raise PermissionError('Command authority response exceeds its bound')
            chunks.append(chunk)
    response = json.loads(b''.join(chunks))
    if (type(response) is not dict or response.keys() != {'status', 'request_digest'}
            or response['status'] != 'CURRENT_ORIGINAL_COMMAND'
            or response['request_digest'] != hashlib.sha256(raw).hexdigest()):
        raise PermissionError('The next guest command has no current original authority')
    return response
