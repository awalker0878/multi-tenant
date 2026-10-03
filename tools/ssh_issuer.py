#!/usr/bin/env python3
"""Issue scoped SSH user certificates on the independently accepted signing host.

One CA, principal and retained ledger per accepted profile. Unknown issuance is
never repeated; issuer denial must also be distributed to relying endpoints.
"""
from contextlib import contextmanager
import argparse
import fcntl
import ipaddress
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ''): sys.path.insert(0, str(ROOT))
from cryptography.hazmat.primitives.serialization import (
    Encoding, PublicFormat, SSHCertificate, SSHCertificateType, load_ssh_public_identity)
from tools import execution_journal as journal, owner_install as install, readback_core as c
from provisioner.execution.source_integrity import verify
from tools.run_files import (current_window, digest, encoded, load_private, private_path,
    read_private, require, sync_directory, utcnow, write_new)


def network(value):
    result = ipaddress.ip_network(value, strict=True)
    require(result.version == 4 and str(result) == value and result.prefixlen > 0
            and not result.network_address.is_multicast and not result.network_address.is_unspecified,
            'Explicit canonical IPv4 source range required')
    return result


def validate(config):
    c.exact_keys(config, {'format', 'source_commit', 'machine_id', 'uid', 'source',
        'ssh_keygen', 'ssh_keygen_sha256', 'ca_private', 'ca_public', 'principal',
        'source_ranges', 'maximum_validity_seconds', 'serial_floor', 'data_directory',
        'policy_ref', 'recovery_ref'})
    require(config['format'] == 'hosting-ssh-issuer/1', 'Exact issuer profile required')
    require(isinstance(config['source_commit'], str) and re.fullmatch('[0-9a-f]{40}', config['source_commit'])
            and isinstance(config['machine_id'], str) and re.fullmatch('[0-9a-f]{32}', config['machine_id']),
            'Exact issuer source and host required')
    require(type(config['uid']) is int and config['uid'] >= 0, 'Exact issuer UID required')
    for key in ('source', 'ssh_keygen', 'data_directory'): install.installed_path(config[key])
    c.exact_keys(config['ca_private'], {'path', 'sha256'}); install.installed_path(config['ca_private']['path'])
    for value in (config['ssh_keygen_sha256'], config['ca_private']['sha256']):
        require(isinstance(value, str) and c.HEX.fullmatch(value), 'Exact issuer artifact digest required')
    install.public_key(config['ca_public'])
    require(isinstance(config['principal'], str) and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', config['principal']),
            'One accepted certificate principal required')
    require(isinstance(config['source_ranges'], list) and 1 <= len(config['source_ranges']) <= 32
            and config['source_ranges'] == sorted(set(config['source_ranges'])), 'Bounded unique source ranges required')
    for value in config['source_ranges']: network(value)
    require(type(config['maximum_validity_seconds']) is int and 1 <= config['maximum_validity_seconds'] <= 3600,
            'Accepted certificate lifetime must fit the bounded issuance authority')
    require(type(config['serial_floor']) is int and 1 <= config['serial_floor'] < 2**64, 'Accepted initial serial required')
    for key in ('policy_ref', 'recovery_ref'): c.text(config[key])
    source, data, ca = (Path(config['source']), Path(config['data_directory']), Path(config['ca_private']['path']))
    require(not data.is_relative_to(source) and not source.is_relative_to(data)
            and not ca.is_relative_to(source) and not ca.is_relative_to(data),
            'Keep independent signing material outside source and issuer artifacts')


def validate_request(config, request):
    common = {'format', 'config_sha256', 'operation_id', 'action', 'subject', 'identity_ref'}
    require(isinstance(request, dict) and request.get('action') in {'issue', 'revoke'}, 'Explicit identity action required')
    c.exact_keys(request, common | ({'valid_after', 'valid_before', 'source_range'} if request['action'] == 'issue' else set()))
    require(request['format'] == 'hosting-ssh-issuer-request/1' and request['config_sha256'] == c.digest(config),
            'Request must bind the accepted issuer')
    c.identifier(request['operation_id']); c.text(request['identity_ref']); install.public_key(request['subject'])
    require(request['subject'] != config['ca_public'], 'Signing key cannot be an issued subject')
    if request['action'] == 'issue':
        start, end = request['valid_after'], request['valid_before']
        require(type(start) is int and type(end) is int and 0 < start < end < 2**64
                and end-start <= config['maximum_validity_seconds'], 'Exact bounded absolute certificate validity required')
        selected = network(request['source_range'])
        require(any(selected.subnet_of(network(value)) for value in config['source_ranges']), 'Source exceeds accepted issuer scope')


def authorize(request, authority, *, now=None):
    c.exact_keys(authority, {'format', 'request_sha256', 'action', 'ledger_mode', 'valid_from', 'valid_until', 'change_ref'})
    require(authority['format'] == 'hosting-ssh-issuer-authority/1' and authority['request_sha256'] == c.digest(request)
            and authority['action'] in ({'issue', 'observe'} if request['action'] == 'issue' else {'revoke'}),
            'Exact identity action authority required')
    current_window(authority, now=now); c.text(authority['change_ref'])
    require(authority['ledger_mode'] in {'new', 'retained'}
            and (authority['action'] != 'observe' or authority['ledger_mode'] == 'retained'), 'Explicit issuer ledger custody required')
    if authority['action'] == 'issue':
        instant = (now or utcnow()).timestamp()
        require(c.timestamp(authority['valid_from']).timestamp() <= request['valid_after'] <= instant
                < request['valid_before'] <= c.timestamp(authority['valid_until']).timestamp(),
                'Certificate validity must fit current issuance authority')


def public_bytes(key):
    return key.public_bytes(Encoding.OpenSSH, PublicFormat.OpenSSH)


def verify_certificate(config, request, serial, raw):
    require(len(raw) <= 16384, 'Unexpected certificate size')
    cert = load_ssh_public_identity(raw)
    require(isinstance(cert, SSHCertificate), 'Signed SSH certificate required')
    require(public_bytes(cert.signature_key()) == config['ca_public'].encode()
            and public_bytes(cert.public_key()) == request['subject'].encode(), 'Certificate trust or subject differs')
    require(cert.type == SSHCertificateType.USER and cert.serial == serial
            and cert.key_id == ('hosting:'+c.digest(request)).encode()
            and cert.valid_principals == [config['principal'].encode()]
            and (cert.valid_after, cert.valid_before) == (request['valid_after'], request['valid_before'])
            and cert.critical_options == {b'source-address': request['source_range'].encode()}
            and cert.extensions == {}, 'Certificate grants differ from the exact request')
    cert.verify_cert_signature()
    return cert


class Host:
    def command(self, argv):
        result = subprocess.run(list(map(str, argv)), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=30, umask=0o077,
            env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
        require(result.returncode == 0 and len(result.stdout) <= 16384, 'Issuer native command failed; preserve its serial')
        return result.stdout

    def identity(self, config, root):
        require(os.getuid() == os.geteuid() == config['uid'] and Path('/etc/machine-id').read_text().strip() == config['machine_id'],
                'Wrong issuer account or host')
        require(root == Path(config['source']), 'Issuer source location changed')
        source = verify(root)
        require(source['status'] == 'HASHES_MATCH' and source['commit'] == config['source_commit'], 'Issuer source changed')
        for path in [root, *root.parents, *root.rglob('*')]:
            require(not path.is_symlink(), 'Issuer source symlinks are unsupported')
            info = path.stat()
            require(info.st_uid in {0, config['uid']} and not stat.S_IMODE(info.st_mode) & 0o022,
                    'Issuer source must remain controlled by its custodian')
        path = Path(config['ssh_keygen'])
        require(path.is_file() and os.access(path, os.X_OK) and digest(path.read_bytes()) == config['ssh_keygen_sha256'],
                'Issuer executable changed')
        for parent in {path, path.resolve(strict=True), *path.parents, *path.resolve(strict=True).parents}:
            info = parent.stat()
            require(info.st_uid in {0, config['uid']} and not stat.S_IMODE(info.st_mode) & 0o022,
                    'Issuer executable location is not controlled')
        private_path(Path(config['ca_private']['path']).parent, directory=True)
        require(digest(read_private(config['ca_private']['path'])) == config['ca_private']['sha256'], 'Signing key bytes changed')
        actual = self.command([path, '-y', '-f', config['ca_private']['path']]).decode().split()
        require(' '.join(actual[:2]) == config['ca_public'], 'Signing key identity differs')

    def sign(self, config, request, serial, directory):
        self.command([config['ssh_keygen'], '-q', '-s', config['ca_private']['path'],
            '-I', 'hosting:'+c.digest(request), '-n', config['principal'], '-O', 'clear',
            '-O', 'source-address='+request['source_range'], '-V',
            f"0x{request['valid_after']:x}:0x{request['valid_before']:x}", '-z', str(serial), directory/'subject.pub'])


@contextmanager
def ledger(config, authority):
    directory = Path(config['data_directory']); private_path(directory.parent, directory=True)
    created = False
    if not directory.exists():
        require(authority['ledger_mode'] == 'new', 'Retained issuer history is missing; recover independent custody')
        directory.mkdir(mode=0o700); sync_directory(directory.parent); created = True
    private_path(directory, directory=True)
    fd = os.open(directory/'writer.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        private_path(directory/'writer.lock'); fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        log = journal.Journal(directory, {'owner': 'ssh-issuer', 'ca_sha256': digest(config['ca_public'].encode())})
        if created: log.append('ISSUER_ACCEPTED', {'config': config})
        require(log.events and log.events[0]['kind'] == 'ISSUER_ACCEPTED' and log.events[0]['data'] == {'config': config},
                'Issuer custody or policy changed; preserve all serial and revocation history')
        yield log
    finally: os.close(fd)


def operation_directory(log, request):
    return log.directory/('operation-'+digest(request['operation_id'].encode()))


def history(config, log):
    next_serial, operations, revoked = config['serial_floor'], {}, set()
    for event in log.events[1:]:
        data, kind = event['data'], event['kind']
        if kind in {'ISSUE_STARTED', 'SUBJECT_REVOKED'}:
            c.exact_keys(data, {'request', 'authority'} | ({'serial'} if kind == 'ISSUE_STARTED' else set()))
            request, authority = data['request'], data['authority']
            validate_request(config, request); authorize(request, authority, now=c.timestamp(event['at']))
            action = 'issue' if kind == 'ISSUE_STARTED' else 'revoke'
            require(request['action'] == authority['action'] == action and request['operation_id'] not in operations,
                    'Issuer history operation differs')
            if action == 'issue':
                require(request['subject'] not in revoked and type(data['serial']) is int and data['serial'] == next_serial
                        and next_serial < 2**64, 'Issuer serial or revocation history differs')
                next_serial += 1
            else: revoked.add(request['subject'])
            operations[request['operation_id']] = dict(data, completed=False)
        elif kind == 'CERTIFICATE_OBSERVED':
            c.exact_keys(data, {'operation_id', 'certificate_sha256'})
            operation = operations.get(data['operation_id'])
            require(operation and operation['request']['action'] == 'issue' and not operation['completed'], 'Unknown certificate history')
            raw = read_private(operation_directory(log, operation['request'])/'subject-cert.pub')
            require(digest(raw) == data['certificate_sha256'], 'Retained issued certificate changed')
            verify_certificate(config, operation['request'], operation['serial'], raw)
            operation['completed'] = True
        else: require(False, 'Unknown issuer history event')
    return next_serial, operations, revoked


def execute(config, request, authority, *, host=None, root=ROOT):
    validate(config); validate_request(config, request); authorize(request, authority)
    host = host or Host(); host.identity(config, root)
    with ledger(config, authority) as log:
        next_serial, operations, revoked = history(config, log)
        prior = operations.get(request['operation_id'])
        if prior: require(prior['request'] == request, 'Identity operation cannot change its request')
        authorize(request, authority)
        if request['action'] == 'revoke':
            if not prior: log.append('SUBJECT_REVOKED', {'request': request, 'authority': authority})
            revoked.add(request['subject'])
            result = {'status': 'SUBJECT_DENIED_REQUIRES_ENDPOINT_PROPAGATION', 'revoked_subjects': sorted(revoked)}
        else:
            if authority['action'] == 'issue': require(request['subject'] not in revoked, 'Subject is revoked at this issuer')
            if not prior:
                require(authority['action'] == 'issue' and next_serial < 2**64, 'No recoverable issuance or available serial')
                # Reserve permanently before creating files or invoking the signer.
                log.append('ISSUE_STARTED', {'request': request, 'authority': authority, 'serial': next_serial})
                prior = {'request': request, 'serial': next_serial, 'completed': False}
                directory = operation_directory(log, request)
                directory.mkdir(mode=0o700); sync_directory(log.directory)
                write_new(directory/'subject.pub', (request['subject']+'\n').encode())
                authorize(request, authority)
                host.sign(config, request, next_serial, directory)
            else:
                require(prior['completed'] or authority['action'] == 'observe',
                        'Unknown issuance requires read-only recovery; never repeat signing')
            directory = operation_directory(log, request)
            private_path(directory, directory=True)
            raw = read_private(directory/'subject-cert.pub')
            verify_certificate(config, request, prior['serial'], raw)
            # ssh-keygen closes its output; sync before the journal promises durability.
            fd = os.open(directory/'subject-cert.pub', os.O_RDONLY | os.O_NOFOLLOW)
            try: os.fsync(fd)
            finally: os.close(fd)
            sync_directory(directory)
            authorize(request, authority)
            if not prior['completed']:
                log.append('CERTIFICATE_OBSERVED', {'operation_id': request['operation_id'], 'certificate_sha256': digest(raw)})
            result = {'status': 'SCOPED_CERTIFICATE_OBSERVED', 'serial': prior['serial'],
                'certificate_path': str(directory/'subject-cert.pub'), 'certificate_sha256': digest(raw),
                'subject_revoked': request['subject'] in revoked, 'valid_after': request['valid_after'],
                'valid_before': request['valid_before']}
        result.update(format='hosting-ssh-issuer-receipt/1', config_sha256=c.digest(config),
            request_sha256=c.digest(request), authority_sha256=c.digest(authority), observed_at=c.now(),
            endpoint_revocation_observed=False, existing_sessions_terminated=False, native_fencing=False, production_activation=False)
        write_new(log.directory/('receipt-'+digest(encoded(result))+'.receipt'), encoded(result))
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('config', 'request'): parser.add_argument('--'+key, type=Path, required=True)
    parser.add_argument('--authority', type=Path); parser.add_argument('--execute', action='store_true'); args = parser.parse_args()
    try:
        config, request = load_private(args.config), load_private(args.request)
        validate(config); validate_request(config, request)
        if not args.execute: print('{"status":"VALIDATED_NO_IDENTITY_CHANGE"}'); return 0
        require(args.authority is not None, 'Current exact issuer authority required')
        result = execute(config, request, load_private(args.authority)); print(json.dumps({'status': result['status']})); return 0
    except Exception:
        print('{"status":"SSH_ISSUER_HELD","reason":"Preserve signing identity, reserved serials and revocations; never retry unknown signing"}')
        return 2


if __name__ == '__main__': raise SystemExit(main())
