#!/usr/bin/env python3
"""Render the real role templates and ask installed daemons to validate them.

No daemon is started and no host configuration is changed. The report is local
engine evidence only, not remote guest convergence or service delivery proof.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from lab.native_readback_fixture import credentials


def run(require_engines=False):
    engines = {name: shutil.which(name) for name in ('sshd', 'rsyslogd', 'ssh-keygen')}
    if not all(engines.values()):
        return {'status': 'MISSING_LOCAL_ENGINES', 'missing': [k for k, v in engines.items() if not v],
                'native_contact': False}, 2 if require_engines else 0
    with tempfile.TemporaryDirectory(prefix='hosting-guest-services-') as tmp:
        base = Path(tmp)
        credentials(base)
        key = base / 'host-key'
        subprocess.run([engines['ssh-keygen'], '-q', '-t', 'ed25519', '-N', '', '-f', str(key)],
                       check=True, capture_output=True, timeout=15)
        (base / 'hosting-user-ca.pub').write_bytes(key.with_suffix('.pub').read_bytes())
        (base / 'hosting-revoked-keys').touch()
        env = Environment(loader=FileSystemLoader(ROOT / 'ansible/roles/linux_guest_services/templates'),
                          undefined=StrictUndefined, keep_trailing_newline=True)
        target = dict(port=2222, services=dict(admin_users=['operator'], breakglass={'user': 'recovery'},
                       resolver_addresses=['192.0.2.53'], journal_mib=512,
                       log=dict(address='192.0.2.60', peer_name='logs.example.com', port=6514, queue_mib=256)))
        config = env.get_template('sshd_config.j2').render(hosting_target=target)
        config = config.replace('/etc/ssh/ssh_host_ed25519_key', str(key)).replace('/etc/ssh/', str(base) + '/')
        path = base / 'sshd_config'
        path.write_text(config)
        checks = []
        for account in ('operator', 'recovery'):
            result = subprocess.run([engines['sshd'], '-T', '-f', str(path), '-C',
                        f'user={account},host=localhost,addr=127.0.0.1'], capture_output=True, text=True, timeout=15)
            if result.returncode:
                raise RuntimeError('Local SSH configuration validation failed: ' + result.stderr)
            values = dict(line.split(' ', 1) for line in result.stdout.splitlines() if ' ' in line)
            expected = {'permitrootlogin': 'no', 'passwordauthentication': 'no',
                        'kbdinteractiveauthentication': 'no', 'allowtcpforwarding': 'no',
                        'allowagentforwarding': 'no', 'authenticationmethods': 'publickey',
                        'pubkeyacceptedalgorithms': 'ssh-ed25519' + ('-cert-v01@openssh.com' if account == 'operator' else '')}
            if any(values.get(k) != v for k, v in expected.items()):
                raise RuntimeError('Effective SSH configuration differs from the declared identity boundary')
            checks.append({'engine': 'sshd', 'account': account, 'effective_controls': len(expected), 'status': 'PASS'})
        logging = env.get_template('logging.conf.j2').render(hosting_target=target)
        logging = logging.replace('/etc/hosting-log/ca.pem', str(base / 'ca.pem'))
        logging = logging.replace('/etc/hosting-log/client.pem', str(base / 'server.pem'))
        logging = logging.replace('/etc/hosting-log/client.key', str(base / 'server.key'))
        logging = 'global(workDirectory="' + str(base) + '")\n' + logging
        path = base / 'logging.conf'
        path.write_text(logging)
        result = subprocess.run([engines['rsyslogd'], '-N1', '-f', str(path)], capture_output=True, text=True, timeout=15)
        if result.returncode:
            raise RuntimeError('Local rsyslog configuration validation failed: ' + result.stderr)
        checks.append({'engine': 'rsyslogd', 'status': 'PASS'})
        return {'status': 'PASSED_LOCAL_GUEST_SERVICE_ENGINES_ONLY', 'checks': checks, 'native_contact': False}, 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-engines', action='store_true')
    args = parser.parse_args()
    try:
        report, code = run(args.require_engines)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        report, code = {'status': 'FAILED_LOCAL_GUEST_SERVICE_ENGINES', 'reason': str(exc), 'native_contact': False}, 2
    output = ROOT / 'build/reports/guest_services_lab.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
