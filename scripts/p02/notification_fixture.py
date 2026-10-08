"""Disposable broker and real application command pump for the P02 browser campaign."""
import base64
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import threading
import time


class NotificationBroker:
    def __init__(self, root: Path, private: Path, run, private_values: list[str]):
        self.root, self.private, self.run = root, private, run
        self.name = 'p02-console-notifications-' + secrets.token_hex(6)
        self.image = json.loads((root / 'deploy/dependencies/stateful/inputs.lock.json').read_text())['images']['rabbitmq']['reference']
        self.environment = {'P02_TEST_BROKER': '1'}
        self.private_values = private_values

    def start(self):
        for cert in ['broker', 'untrusted-broker']:
            self.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', str(self.private / (cert + '.key')),
                      '-out', str(self.private / (cert + '.crt')), '-days', '1', '-subj', '/CN=localhost',
                      '-addext', 'subjectAltName=IP:127.0.0.1,DNS:localhost'])
        definitions = json.loads((self.root / 'deploy/dependencies/stateful/console-notifications.json').read_text())
        definitions['users'] = []
        for user in ['governance', 'console']:
            password = secrets.token_urlsafe(32)
            self.private_values.append(password)
            path = self.private / (user + '-broker.password')
            path.write_text(password)
            path.chmod(0o600)
            salt = secrets.token_bytes(4)
            definitions['users'].append({'name': user, 'password_hash': base64.b64encode(salt + hashlib.sha256(salt + password.encode()).digest()).decode(),
                                         'hashing_algorithm': 'rabbit_password_hashing_sha256', 'tags': []})
            self.environment.update({user.upper() + '_BROKER_' + key: value for key, value in {
                'HOST': '127.0.0.1', 'PORT': '5679', 'PASSWORD_FILE': str(path), 'CA_FILE': str(self.private / 'broker.crt')}.items()})
        # A separate existing queue makes cross-service read denial observable.
        definitions['queues'].append({'name': 'p02.private', 'vhost': 'product', 'durable': True, 'auto_delete': False, 'arguments': {'x-queue-type': 'quorum'}})
        self.environment.update(P02_TEST_PUBLISHER_PASSWORD_FILE=str(self.private / 'governance-broker.password'),
                                P02_UNTRUSTED_CA_FILE=str(self.private / 'untrusted-broker.crt'))
        (self.private / 'notification-definitions.json').write_text(json.dumps(definitions))
        (self.private / 'notification-rabbitmq.conf').write_text(
            'listeners.tcp = none\nlisteners.ssl.default = 5671\nssl_options.certfile = /config/broker.crt\n'
            'ssl_options.keyfile = /config/broker.key\nssl_options.cacertfile = /config/broker.crt\n'
            'ssl_options.verify = verify_none\nssl_options.fail_if_no_peer_cert = false\n'
            'definitions.import_backend = local_filesystem\ndefinitions.local.path = /config/notification-definitions.json\n')
        mounts = []
        for filename in ['broker.crt', 'broker.key', 'notification-definitions.json', 'notification-rabbitmq.conf']:
            path = self.private / filename
            path.chmod(0o444)
            target = '/etc/rabbitmq/rabbitmq.conf' if filename.endswith('.conf') else '/config/' + filename
            mounts.extend(['-v', str(path) + ':' + target + ':ro'])
        self.run(['docker', 'run', '-d', '--name', self.name, '--hostname', 'p02-notification-broker', '-p', '127.0.0.1:5679:5671',
                  '-e', 'RABBITMQ_SERVER_ADDITIONAL_ERL_ARGS=+S 2:2', '-e', 'RABBITMQ_CTL_ERL_ARGS=+S 2:2',
                  '--health-cmd', 'rabbitmq-diagnostics -q check_running', '--health-interval', '2s', '--health-retries', '45',
                  *mounts, self.image], label='notification-broker-start')
        deadline = time.monotonic() + 90
        while True:
            state = json.loads(subprocess.check_output(['docker', 'inspect', '--format', '{{json .State}}', self.name]))
            if state.get('Health', {}).get('Status') == 'healthy':
                break
            if not state.get('Running') or time.monotonic() >= deadline:
                raise RuntimeError('notification_broker_not_ready')
            time.sleep(1)
        self.run(['docker', 'exec', self.name, 'rabbitmq-diagnostics', '-q', 'check_port_connectivity', '--address', '127.0.0.1'], label='notification-broker-ready')

    def close(self):
        subprocess.run(['docker', 'rm', '-f', self.name], capture_output=True, timeout=30)


class NotificationPump:
    """Independent bootstraps: no application imports or cross-service SQL."""
    def __init__(self, root: Path, environments: dict):
        self.root, self.environments = root, environments
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.work, daemon=True)
        self.error = None
        self.totals = {'published': 0, 'recorded': 0, 'duplicate': 0, 'quarantined': 0, 'retry': 0}
        self.cycles = 0

    def work(self):
        try:
            while not self.stop.is_set():
                for service, directory, command in [('governance', 'services/governance', 'governance:publish-outbox'),
                                                     ('governance', 'services/governance', 'identity:publish-outbox'),
                                                     ('console', 'apps/console', 'console:consume-notifications')]:
                    completed = subprocess.run(['php', 'artisan', command, '--limit=100'], cwd=self.root / directory,
                                               env=self.environments[service], capture_output=True, text=True, timeout=20)
                    if completed.returncode != 0:
                        raise RuntimeError(service + '_notification_command_failed')
                    counts = json.loads(completed.stdout)
                    if not isinstance(counts, dict) or any(key not in self.totals or type(value) is not int or value < 0 for key, value in counts.items()):
                        raise RuntimeError('invalid_notification_command_counts')
                    for key, value in counts.items():
                        self.totals[key] += value
                self.cycles += 1
                self.stop.wait(1)
        except Exception as error:
            self.error = type(error).__name__ + ':' + str(error)

    def close(self):
        self.stop.set()
        self.thread.join(timeout=45)
        if self.thread.is_alive():
            raise RuntimeError('notification_pump_did_not_stop')
