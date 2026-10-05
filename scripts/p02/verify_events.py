#!/usr/bin/env python3
"""Disposable PostgreSQL/TLS RabbitMQ qualification of Governance event delivery."""
import argparse
import base64
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = {'schema_version': 1, 'result': 'RUNNING', 'scope': 'P02 Governance and installation identity committed notifications; synthetic consumers, no authority or native effects',
              'source_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
              'started_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'checks': [], 'commands': []}
    private_values = [os.environ.get('P02_TEST_PASSWORD', '')]
    name = 'p02-events-' + secrets.token_hex(6)

    def save():
        (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')

    def check(name, condition):
        report['checks'].append({'name': name, 'passed': bool(condition)})
        save()
        if not condition:
            raise RuntimeError(name)

    def run(label, command, *, env=None, timeout=120, expected=0):
        completed = subprocess.run(command, cwd=root, env=env, capture_output=True, timeout=timeout)
        entry = {'name': label, 'exit_code': completed.returncode, 'expected_exit_code': expected}
        for stream in ['stdout', 'stderr']:
            body = getattr(completed, stream).decode(errors='replace')
            for value in private_values:
                if value:
                    body = body.replace(value, '[REDACTED]')
            path = output / (label + '.' + stream + '.log')
            path.write_text(body)
            entry[stream] = {'path': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        report['commands'].append(entry)
        save()
        if completed.returncode != expected:
            raise RuntimeError(label + '_unexpected_exit')
        return completed.stdout.decode().strip()

    try:
        check('disposable-postgres-only', os.environ.get('P02_TEST_POSTGRES') == '1')
        paths = ['services/governance', 'contracts/schemas/events/governance-change-v1.json', 'contracts/asyncapi/governance.yaml', 'contracts/schemas/events/identity-change-v1.json', 'contracts/asyncapi/identity.yaml', 'scripts/p02', '.github/workflows/p02-governance-events.yml']
        tracked = subprocess.check_output(['git', 'ls-files', '--', *paths], cwd=root, text=True).splitlines()
        report['source_sha256'] = {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in tracked}
        check('clean-campaign-source', not subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=all', '--', *paths], cwd=root).strip())
        check('packaged-schema-matches-public-contract', (root / paths[1]).read_bytes() == (root / 'services/governance/resources/contracts/governance-change-v1.json').read_bytes())
        check('packaged-identity-schema-matches-public-contract', (root / 'contracts/schemas/events/identity-change-v1.json').read_bytes() == (root / 'services/governance/resources/contracts/identity-change-v1.json').read_bytes())
        with tempfile.TemporaryDirectory(prefix='p02-events-private-') as directory:
            private = Path(directory)
            for cert in ['broker', 'untrusted']:
                run(cert + '-certificate', ['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', str(private / (cert + '.key')), '-out', str(private / (cert + '.crt')), '-days', '1', '-subj', '/CN=localhost', '-addext', 'subjectAltName=IP:127.0.0.1,DNS:localhost'])
            users = []
            for user in ['governance', 'p02-observer']:
                password = secrets.token_urlsafe(32)
                private_values.append(password)
                (private / (user + '.password')).write_text(password)
                (private / (user + '.password')).chmod(0o600)
                salt = secrets.token_bytes(4)
                users.append({'name': user, 'password_hash': base64.b64encode(salt + hashlib.sha256(salt + password.encode()).digest()).decode(), 'hashing_algorithm': 'rabbit_password_hashing_sha256', 'tags': []})
            definitions = {'users': users, 'vhosts': [{'name': 'product'}], 'permissions': [
                {'user': 'governance', 'vhost': 'product', 'configure': '^$', 'write': '^governance.events$', 'read': '^$'},
                {'user': 'p02-observer', 'vhost': 'product', 'configure': '^$', 'write': '^$', 'read': '^p02\\.(governance|identity)$'}],
                'exchanges': [{'name': 'governance.events', 'vhost': 'product', 'type': 'topic', 'durable': True, 'auto_delete': False, 'internal': False, 'arguments': {}}],
                'queues': [{'name': 'p02.' + family, 'vhost': 'product', 'durable': True, 'auto_delete': False, 'arguments': {'x-queue-type': 'quorum'}} for family in ['governance', 'identity']],
                'bindings': [{'source': 'governance.events', 'vhost': 'product', 'destination': 'p02.' + family, 'destination_type': 'queue', 'routing_key': family + '.#', 'arguments': {}} for family in ['governance', 'identity']]}
            (private / 'definitions.json').write_text(json.dumps(definitions))
            (private / 'rabbitmq.conf').write_text('listeners.tcp = none\nlisteners.ssl.default = 5671\nssl_options.certfile = /config/broker.crt\nssl_options.keyfile = /config/broker.key\nssl_options.cacertfile = /config/broker.crt\nssl_options.verify = verify_none\nssl_options.fail_if_no_peer_cert = false\ndefinitions.import_backend = local_filesystem\ndefinitions.local.path = /config/definitions.json\n')
            for file in ['broker.crt', 'broker.key', 'definitions.json', 'rabbitmq.conf']:
                (private / file).chmod(0o444)
            reference = json.loads((root / 'deploy/dependencies/stateful/inputs.lock.json').read_text())['images']['rabbitmq']['reference']
            report['broker_image'] = reference
            mounts = []
            for file in ['broker.crt', 'broker.key', 'definitions.json']:
                mounts += ['-v', str(private / file) + ':/config/' + file + ':ro']
            run('broker-start', ['docker', 'run', '-d', '--name', name, '--hostname', 'p02-broker', '-p', '127.0.0.1:5679:5671',
                '-e', 'RABBITMQ_SERVER_ADDITIONAL_ERL_ARGS=+S 2:2', '-e', 'RABBITMQ_CTL_ERL_ARGS=+S 2:2',
                '--health-cmd', 'rabbitmq-diagnostics -q check_running', '--health-interval', '2s', '--health-retries', '45',
                '-v', str(private / 'rabbitmq.conf') + ':/etc/rabbitmq/rabbitmq.conf:ro', *mounts, reference], timeout=180)
            deadline = time.monotonic() + 90
            while True:
                state = json.loads(subprocess.check_output(['docker', 'inspect', '--format', '{{json .State}}', name]))
                if state.get('Health', {}).get('Status') == 'healthy':
                    break
                if not state.get('Running') or time.monotonic() >= deadline:
                    run('broker-startup-diagnostic', ['docker', 'logs', name])
                    raise RuntimeError('broker_not_ready')
                time.sleep(1)
            run('broker-ready', ['docker', 'exec', name, 'rabbitmq-diagnostics', '-q', 'check_port_connectivity', '--address', '127.0.0.1'], timeout=20)
            environment = os.environ | {'P02_TEST_BROKER': '1', 'GOVERNANCE_BROKER_HOST': '127.0.0.1', 'GOVERNANCE_BROKER_PORT': '5679',
                'GOVERNANCE_BROKER_PASSWORD_FILE': str(private / 'governance.password'), 'GOVERNANCE_BROKER_CA_FILE': str(private / 'broker.crt'),
                'P02_OBSERVER_PASSWORD_FILE': str(private / 'p02-observer.password'), 'P02_UNTRUSTED_CA_FILE': str(private / 'untrusted.crt')}
            run('postgres-and-broker-features', ['php', 'services/governance/vendor/bin/pest', '--configuration=services/governance/phpunit.xml',
                'services/governance/tests/Feature/GovernanceOutboxTest.php', 'services/governance/tests/Feature/GovernanceBrokerTest.php',
                'services/governance/tests/Feature/IdentityOutboxTest.php', 'services/governance/tests/Feature/IdentityBrokerTest.php',
                'services/governance/tests/Feature/ApprovalTest.php', '--fail-on-warning', '--fail-on-risky', '--colors=never'], env=environment)
            check('real-broker-and-postgres-tests-pass', True)
        report['result'] = 'PASS'
    except Exception as error:
        report.update(result='FAIL', error=type(error).__name__ + ': ' + str(error))
        raise
    finally:
        subprocess.run(['docker', 'rm', '-f', name], capture_output=True, timeout=30)
        report['finished_at'] = dt.datetime.now(dt.timezone.utc).isoformat()
        save()
    print(json.dumps({'result': report['result'], 'checks': len(report['checks'])}))


if __name__ == '__main__':
    main()
