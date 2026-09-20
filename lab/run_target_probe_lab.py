#!/usr/bin/env python3
"""Exercise the fixed guest probe with real certificate SSH and loopback TLS."""
import argparse
from datetime import timedelta
import json
import os
from pathlib import Path
import pwd
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab.native_readback_fixture import Fixture
from tools.qualify_target import ssh_probe
from tools.run_files import digest, utcnow


def run(user):
    ssh, sshd, keygen = (shutil.which(name) for name in ('ssh', 'sshd', 'ssh-keygen'))
    if os.geteuid() != 0 or not all((ssh, sshd, keygen)) or pwd.getpwnam(user).pw_uid == 0:
        raise RuntimeError('Local SSH fixture requires installed engines and an existing non-root fixture account')
    with tempfile.TemporaryDirectory(prefix='hosting-probe-lab-') as tmp, Fixture() as service:
        directory = Path(tmp)
        # sshd reads the public CA while acting as the fixture account; all
        # private keys/logs remain 0600. No host account/configuration is changed.
        directory.chmod(0o755)
        def command(argv):
            return subprocess.check_output(argv, stderr=subprocess.STDOUT, timeout=10, text=True)
        for name in ('host', 'ca', 'ssh_key'):
            command([keygen, '-q', '-t', 'ed25519', '-N', '', '-f', str(directory / name)])
        command([keygen, '-q', '-s', str(directory / 'ca'), '-I', 'disposable-probe-fixture',
                 '-n', user, '-V', '-1m:+5m', str(directory / 'ssh_key.pub')])
        (directory / 'ssh_key-cert.pub').chmod(0o600)
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1', 0)); port = reservation.getsockname()[1]
        config = directory / 'sshd.conf'
        config.write_text('\n'.join([f'Port {port}', 'ListenAddress 127.0.0.1',
            # Match the Ubuntu guest profile: PAM account/session checks with
            # certificate-only authentication. Do not alter fixture account locks.
            f'HostKey {directory}/host', f'PidFile {directory}/sshd.pid', 'UsePAM yes',
            'PasswordAuthentication no', 'KbdInteractiveAuthentication no', 'PermitRootLogin no',
            'AuthorizedKeysFile none', f'TrustedUserCAKeys {directory}/ca.pub',
            'PubkeyAcceptedAlgorithms ssh-ed25519-cert-v01@openssh.com', f'AllowUsers {user}',
            'AllowAgentForwarding no', 'AllowTcpForwarding no', 'X11Forwarding no', 'PermitTTY no', '']))
        command([sshd, '-t', '-f', str(config)])
        pins = directory / 'known_hosts'
        host_key = ' '.join((directory / 'host.pub').read_text().split()[:2])
        pins.write_text(f'[127.0.0.1]:{port} {host_key}\n'); pins.chmod(0o600)
        service.routes['/health'] = {'status': 200, 'body': {'health': 'ok'}}
        authority = dict(valid_from=(utcnow() - timedelta(seconds=1)).isoformat(),
                         valid_until=(utcnow() + timedelta(minutes=5)).isoformat())
        target = dict(machine_id=Path('/etc/machine-id').read_text().strip(), address='127.0.0.1',
                      port=port, user=user, access_valid_until=authority['valid_until'])
        case = dict(destination='127.0.0.1', port=urlsplit(service.origin).port, server_name='localhost',
                    path='/health', body_sha256=digest(json.dumps({'health': 'ok'}).encode()), expect='allow')
        ca = (service.directory / 'ca.pem').read_bytes()
        with open(directory / 'daemon.log', 'wb') as log:
            daemon = subprocess.Popen([sshd, '-D', '-e', '-f', str(config)], stdout=log, stderr=log)
            try:
                for _ in range(30):
                    try:
                        with socket.create_connection(('127.0.0.1', port), timeout=.2): break
                    except OSError: time.sleep(.1)
                positive = ssh_probe(case, target, authority, directory, ssh, ca, 1)
                wrong = ssh_probe(case, target | {'machine_id': '0' * 32}, authority, directory, ssh, ca, 2)
                pins.write_text(f'[127.0.0.1]:{port} ' + ' '.join((directory / 'ca.pub').read_text().split()[:2]) + '\n')
                replaced = ssh_probe(case, target, authority, directory, ssh, ca, 3)
                if positive['status'] != 'HEALTHY' or wrong['status'] != 'WRONG_GUEST' or replaced['status'] != 'SSH_INCONCLUSIVE':
                    raise RuntimeError('Local probe outcomes: ' + json.dumps([positive, wrong, replaced]) +
                        '; daemon=' + (directory / 'daemon.log').read_text()[-4000:] +
                        '; client=' + (directory / 'ssh-1.log').read_text()[-2000:])
                return dict(status='PASSED_LOCAL_CERTIFICATE_SSH_PROBE_ONLY', pinned_certificate_ssh=True,
                            tls_health_verified=True, wrong_guest_rejected=True, replaced_host_key_rejected=True,
                            native_platform_contacted=False)
            finally:
                daemon.terminate()
                try: daemon.wait(timeout=3)
                except subprocess.TimeoutExpired: daemon.kill(); daemon.wait(timeout=3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--user', required=True)
    args = parser.parse_args()
    try:
        report, code = run(args.user), 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        report, code = {'status': 'FAILED_LOCAL_SSH_PROBE', 'reason': str(exc)}, 2
    output = ROOT / 'build/reports/target_probe_lab.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
