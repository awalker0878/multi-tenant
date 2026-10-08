#!/usr/bin/env python3
"""Independent filesystem custody ceremony; no application/database credentials.

Run on the custody host. Mount only public/ read-only into Governance. Sign on two
separate operators' trusted workstations. This tool cannot enroll real operators
or establish physical independence merely by creating a local directory.
"""
from __future__ import annotations

import argparse
import base64
import contextlib
import fcntl
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import sys
import tempfile
import time
import warnings

DOMAIN = b'governance-identity-recovery-v1\n'
LIMIT = 131072
ROLES = {'recovery_owner', 'security_reviewer'}


class Held(Exception):
    pass


def require(condition):
    if not condition:
        raise Held('identity_recovery_held')


def canonical(value):
    def validate(item):
        require(not isinstance(item, float))
        if isinstance(item, dict):
            require(all(isinstance(key, str) for key in item))
            for child in item.values():
                validate(child)
        elif isinstance(item, list):
            for child in item:
                validate(child)
    validate(value)
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')


def decode(wire):
    value = json.loads(wire)
    require(isinstance(value, dict) and canonical(value) == wire)
    return value


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def uuid(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', value) is not None


def sha(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def read(path, private=False, limit=LIMIT):
    path = Path(path)
    require(path.is_absolute())
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, 'rb') as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and not info.st_mode & (0o077 if private else 0o022))
        wire = stream.read(limit + 1)
        require(len(wire) <= limit)
        return wire.rstrip(b'\n')


def write_new(path, wire, mode=0o600):
    path = Path(path)
    require(path.is_absolute() and path.parent.is_dir() and not path.parent.is_symlink())
    require(not path.parent.stat().st_mode & 0o077)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, mode)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(wire + b'\n')
        stream.flush()
        os.fsync(stream.fileno())
    fsync_directory(path.parent)


def fsync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic(path, wire, mode):
    path = Path(path)
    require(not path.is_symlink() and not path.parent.is_symlink())
    temporary = path.parent / ('.custody-' + secrets.token_hex(16))
    try:
        fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, mode)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(wire + b'\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        if temporary.exists():
            temporary.unlink()


def openssl(arguments, *, data=None, pass_fds=()):
    result = subprocess.run(['openssl', *arguments], input=data, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, pass_fds=pass_fds, timeout=15, check=False)
    require(result.returncode == 0)
    return result.stdout


def public_identity(pem):
    require(isinstance(pem, str) and len(pem) <= 8192)
    wire = pem.encode('ascii')
    details = openssl(['rsa', '-pubin', '-text', '-noout'], data=wire)
    match = re.search(rb'Public-Key: \((\d+) bit\)', details)
    require(match is not None and 3072 <= int(match[1]) <= 8192)
    return hashlib.sha256(openssl(['pkey', '-pubin', '-outform', 'DER'], data=wire)).hexdigest()


def policy(path, *, permit_expired=False):
    value = decode(read(path, limit=32768))
    require(set(value) == {'version', 'installation_id', 'valid_from', 'valid_until', 'principals'})
    require(value['version'] == 1 and uuid(value['installation_id']))
    require(type(value['valid_from']) is int and type(value['valid_until']) is int and value['valid_from'] < value['valid_until'])
    require(permit_expired or value['valid_from'] <= int(time.time()) < value['valid_until'])
    require(isinstance(value['principals'], list) and len(value['principals']) == 2)
    ids, keys, roles = set(), set(), set()
    for principal in value['principals']:
        require(set(principal) == {'id', 'role', 'public_key_pem'} and uuid(principal['id']) and principal['role'] in ROLES)
        identity = public_identity(principal['public_key_pem'])
        require(principal['id'] not in ids and identity not in keys and principal['role'] not in roles)
        ids.add(principal['id']); keys.add(identity); roles.add(principal['role'])
    return value


def payload(wire, trust, purpose=None):
    require(len(wire) <= 65536)
    value = decode(wire)
    now = int(time.time())
    require(value.get('version') == 1 and value.get('purpose') in {'reconcile', 'resume'})
    require(purpose is None or value['purpose'] == purpose)
    require(value.get('installation_id') == trust['installation_id'] and value.get('trust_sha256') == digest(trust))
    require(type(value.get('created_at')) is int and type(value.get('expires_at')) is int)
    require(value['created_at'] <= now < value['expires_at'] and 0 < value['expires_at'] - value['created_at'] <= 900)
    require(uuid(value.get('recovery_id')))
    return value


def verify(wire, signatures, trust, purpose=None):
    value = payload(wire, trust, purpose)
    require(isinstance(signatures, list) and len(signatures) == 2)
    by_id = {principal['id']: principal for principal in trust['principals']}
    seen = set()
    with tempfile.TemporaryDirectory(prefix='custody-verify-') as name:
        directory = Path(name)
        for signature in signatures:
            require(set(signature) == {'principal_id', 'signature'})
            principal = by_id.get(signature['principal_id'])
            require(principal is not None and principal['id'] not in seen)
            seen.add(principal['id'])
            raw = base64.b64decode(signature['signature'], validate=True)
            require(base64.b64encode(raw).decode() == signature['signature'] and len(raw) <= 1024)
            (directory / 'key.pem').write_text(principal['public_key_pem'])
            (directory / 'signature').write_bytes(raw)
            openssl(['dgst', '-sha256', '-verify', str(directory / 'key.pem'), '-signature', str(directory / 'signature')], data=DOMAIN + wire)
    return value


def signed_packet(path, trust, purpose=None):
    packet = decode(read(path, private=True))
    require(set(packet) == {'payload', 'signatures'} and isinstance(packet['payload'], str))
    wire = base64.b64decode(packet['payload'], validate=True)
    require(base64.b64encode(wire).decode() == packet['payload'])
    return packet, verify(wire, packet['signatures'], trust, purpose)


def sign(trust_path, payload_path, principal_id, key_path, output, passphrase=None):
    trust = policy(trust_path)
    wire = read(payload_path, private=True, limit=65536)
    payload(wire, trust)
    principal = next((p for p in trust['principals'] if p['id'] == principal_id), None)
    key = read(key_path, private=True, limit=16384)
    require(principal is not None and key.startswith(b'-----BEGIN ENCRYPTED PRIVATE KEY-----'))
    phrase = passphrase
    if phrase is None:
        require(sys.stdin.isatty())
        with warnings.catch_warnings():
            # Never let getpass fall back to visible/unprotected standard input.
            warnings.simplefilter('error', getpass.GetPassWarning)
            try:
                phrase = getpass.getpass('Private signing key passphrase: ').encode()
            except (getpass.GetPassWarning, EOFError) as error:
                raise Held('identity_recovery_held') from error
    require(isinstance(phrase, bytes) and phrase and b'\n' not in phrase and len(phrase) <= 1024)
    with tempfile.TemporaryDirectory(prefix='custody-sign-') as name:
        private = Path(name) / 'key.pem'
        private.write_bytes(key)
        private.chmod(0o600)
        reader, writer = os.pipe()
        try:
            os.write(writer, phrase + b'\n'); os.close(writer); writer = -1
            signature = openssl(['dgst', '-sha256', '-sign', str(private), '-passin', 'fd:' + str(reader)], data=DOMAIN + wire, pass_fds=(reader,))
        finally:
            os.close(reader)
            if writer >= 0:
                os.close(writer)
    # Prove the selected identity actually matches this key before retaining a signature.
    with tempfile.TemporaryDirectory(prefix='custody-keycheck-') as name:
        directory = Path(name)
        (directory / 'public.pem').write_text(principal['public_key_pem'])
        (directory / 'signature').write_bytes(signature)
        openssl(['dgst', '-sha256', '-verify', str(directory / 'public.pem'), '-signature', str(directory / 'signature')], data=DOMAIN + wire)
    result = {'payload_sha256': hashlib.sha256(wire).hexdigest(), 'principal_id': principal_id, 'signature': base64.b64encode(signature).decode()}
    write_new(output, canonical(result))


def assemble(trust_path, payload_path, signatures, output):
    trust, wire = policy(trust_path), read(payload_path, private=True, limit=65536)
    values = []
    for path in signatures:
        value = decode(read(path, private=True))
        require(set(value) == {'payload_sha256', 'principal_id', 'signature'} and value.pop('payload_sha256') == hashlib.sha256(wire).hexdigest())
        values.append(value)
    verify(wire, values, trust)
    write_new(output, canonical({'payload': base64.b64encode(wire).decode(), 'signatures': values}))


@contextlib.contextmanager
def locked(directory):
    directory = Path(directory)
    require(directory.is_absolute() and not directory.is_symlink())
    info = directory.stat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid() and not info.st_mode & 0o077)
    fd = os.open(directory / 'lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        require(os.fstat(fd).st_nlink == 1)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield directory
    finally:
        os.close(fd)


def journal(directory):
    path = directory / 'journal.jsonl'
    if not path.exists():
        return []
    # Bounded recovery history; capacity exhaustion holds further releases.
    entries, previous = [], '0' * 64
    for line in read(path, private=True, limit=16 * 1024 * 1024).splitlines():
        entry = decode(line)
        recorded = entry.pop('sha256', None)
        require(entry.get('sequence') == len(entries) + 1 and entry.get('previous') == previous and digest(entry) == recorded)
        entry['sha256'] = recorded
        entries.append(entry); previous = recorded
    return entries


def record(directory, entries, kind, descriptor, body):
    entry = {'sequence': len(entries) + 1, 'previous': entries[-1]['sha256'] if entries else '0' * 64,
             'kind': kind, 'occurred_at': int(time.time()), 'descriptor_sha256': digest(descriptor), 'body': body}
    entry['sha256'] = digest(entry)
    fd = os.open(directory / 'journal.jsonl', os.O_CREAT | os.O_APPEND | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'ab') as stream:
        require(os.fstat(stream.fileno()).st_nlink == 1)
        stream.write(canonical(entry) + b'\n'); stream.flush(); os.fsync(stream.fileno())
    atomic(directory / 'state.json', canonical({'sequence': entry['sequence'], 'journal_sha256': entry['sha256'], 'descriptor_sha256': entry['descriptor_sha256']}), 0o600)
    return entry


def admission(directory):
    wire = read(directory / 'public' / 'identity-admission.json', limit=4096)
    value = decode(wire)
    require(set(value) == {'version', 'installation_id', 'epoch', 'state', 'bootstrap_allowed'})
    require(value['version'] == 1 and uuid(value['installation_id']) and sha(value['epoch'])
            and value['state'] in {'active', 'held'} and type(value['bootstrap_allowed']) is bool)
    return value


def enroll(directory, admission_path, trust_path):
    directory = Path(directory)
    require(directory.is_absolute() and not directory.exists() and not directory.is_relative_to(Path(__file__).resolve().parents[2]))
    trust = policy(trust_path)
    value = json.loads(read(admission_path, limit=4096))
    require(set(value) == {'version', 'installation_id', 'epoch', 'state', 'bootstrap_allowed'} and value['version'] == 1
            and value['installation_id'] == trust['installation_id'] and sha(value['epoch']) and value['state'] in {'active', 'held'}
            and type(value['bootstrap_allowed']) is bool)
    # Enrollment never changes the epoch or opens admission. Ownership is established separately.
    directory.mkdir(mode=0o700)
    (directory / 'public').mkdir(mode=0o755)
    atomic(directory / 'public' / 'trust.json', canonical(trust), 0o444)
    atomic(directory / 'public' / 'identity-admission.json', canonical(value), 0o444)
    with locked(directory):
        record(directory, [], 'enrolled', value, {'trust_sha256': digest(trust)})


def hold(directory, case_reference):
    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}', case_reference) is not None)
    with locked(directory) as root:
        current = admission(root)
        # Containment is allowed even if a previous crash left journal/state out of sync.
        held = current | {'state': 'held', 'epoch': secrets.token_hex(32), 'bootstrap_allowed': False}
        atomic(root / 'public' / 'identity-admission.json', canonical(held), 0o444)
        entries = journal(root)
        record(root, entries, 'held', held, {'case_reference': case_reference, 'previous_descriptor_sha256': digest(current)})


def checked(directory):
    entries, current = journal(directory), admission(directory)
    state = decode(read(directory / 'state.json', private=True))
    require(entries and state == {'sequence': len(entries), 'journal_sha256': entries[-1]['sha256'], 'descriptor_sha256': digest(current)})
    require(entries[-1]['descriptor_sha256'] == digest(current))
    return entries, current


def resume(directory, envelope_path, confirmation_path):
    with locked(directory) as root:
        entries, current = checked(root)
        trust = policy(root / 'public' / 'trust.json')
        packet, value = signed_packet(envelope_path, trust, 'resume')
        confirmation = decode(read(confirmation_path, private=True))
        require(current['state'] == 'held' and current['bootstrap_allowed'] is False and current['installation_id'] == trust['installation_id'])
        require(value.get('descriptor_sha256') == digest(current) and value.get('binding_sha256') == hashlib.sha256((current['installation_id'] + ':' + current['epoch']).encode()).hexdigest())
        require(confirmation == {'recovery_id': value['recovery_id'], 'envelope_sha256': digest(packet),
                                 'post_snapshot_sha256': value['post_snapshot_sha256'], 'admission': 'HELD_CONFIRMED'})
        require(not any(e['kind'] == 'resume_authorized' and e['body']['recovery_id'] == value['recovery_id'] for e in entries))
        active = current | {'state': 'active', 'bootstrap_allowed': False}
        # Fsync attributable authorization before making the last, admission-opening write.
        # A crash after journal append remains held and requires a new hold/epoch/ceremony.
        record(root, entries, 'resume_authorized', active, {'recovery_id': value['recovery_id'], 'authorization': packet, 'confirmation_sha256': digest(confirmation)})
        require(int(time.time()) < value['expires_at'])
        atomic(root / 'public' / 'identity-admission.json', canonical(active), 0o444)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    enrollment = commands.add_parser('enroll')
    enrollment.add_argument('--directory', required=True); enrollment.add_argument('--admission', required=True); enrollment.add_argument('--trust', required=True)
    containment = commands.add_parser('hold')
    containment.add_argument('--directory', required=True); containment.add_argument('--case-reference', required=True)
    signing = commands.add_parser('sign')
    for name in ['trust', 'payload', 'principal', 'key', 'output']:
        signing.add_argument('--' + name, required=True)
    combine = commands.add_parser('assemble')
    for name in ['trust', 'payload', 'output']:
        combine.add_argument('--' + name, required=True)
    combine.add_argument('--signature', action='append', required=True)
    release = commands.add_parser('resume')
    for name in ['directory', 'envelope', 'confirmation']:
        release.add_argument('--' + name, required=True)
    verify_store = commands.add_parser('verify')
    verify_store.add_argument('--directory', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'enroll':
            enroll(args.directory, args.admission, args.trust)
        elif args.command == 'hold':
            hold(args.directory, args.case_reference)
        elif args.command == 'sign':
            sign(args.trust, args.payload, args.principal, args.key, args.output)
        elif args.command == 'assemble':
            assemble(args.trust, args.payload, args.signature, args.output)
        elif args.command == 'resume':
            resume(args.directory, args.envelope, args.confirmation)
        else:
            with locked(args.directory) as directory:
                checked(directory)
        print('Custody operation verified. Retain the private signed records independently.')
        return 0
    except (Held, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        print('identity_recovery_held: verify independent custody and exact signed records; admission must remain isolated.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
